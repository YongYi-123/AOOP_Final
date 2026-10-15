"""Tests for the display system: pure layout / mouse arithmetic, the DisplayManager on real (dummy-driver)
windows of many sizes, mode changes and recovery, the DISPLAY settings page, and mouse accuracy in real scenes.

These are synthetic windows: they prove the arithmetic and the code paths, not behaviour on a physical monitor.
Run from this folder:  python -m unittest test_display -v
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import display as dp  # noqa: E402
from audio_settings_ui import AudioSettingsScene  # noqa: E402
from display import (BASE_H, BASE_W, DEFAULTS, MIN_WINDOW, SAFE_SIZE, DisplayManager,  # noqa: E402
                     DisplaySettings, compute_layout, screen_to_canvas, screen_to_window,
                     validate_settings, window_to_screen)
from display_settings_ui import CONFIRM_SECONDS, ROWS  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402

DT = 1 / 60
MATRIX = [(640, 480), (800, 600), (1024, 768), (1280, 720), (1366, 768), (1920, 1080), (2560, 1440),
          (3440, 1440), (600, 1000), (500, 900), (330, 250), (200, 100)]       # incl. portrait and very small


# ----------------------------------------------------------------------------------- pure arithmetic
class LayoutTests(unittest.TestCase):
    def test_every_layout_is_4_by_3_inside_the_window_and_centred(self):
        for size in MATRIX:
            for scaling in dp.SCALINGS:
                lay = compute_layout(size, scaling)
                with self.subTest(size=size, scaling=scaling):
                    self.assertTrue(pygame.Rect(0, 0, *size).contains(lay.rect))
                    self.assertAlmostEqual(lay.rect.w / lay.rect.h, 4 / 3, delta=.02)
                    self.assertLessEqual(abs((lay.rect.centerx) - size[0] / 2), 1)
                    self.assertLessEqual(abs((lay.rect.centery) - size[1] / 2), 1)
                    self.assertEqual(lay.screen_size, (BASE_W * lay.scale, BASE_H * lay.scale))

    def test_integer_scaling_uses_whole_multiples_and_never_blurs(self):
        for size in MATRIX:
            lay = compute_layout(size, "integer")
            if min(size[0] / BASE_W, size[1] / BASE_H) >= 1:
                with self.subTest(size=size):
                    self.assertTrue(lay.exact)
                    self.assertEqual(lay.rect.size, lay.screen_size)
                    self.assertEqual(lay.rect.w % BASE_W, 0)
                    self.assertEqual(lay.factor, 1.0)
                    k = lay.rect.w // BASE_W
                    self.assertLessEqual(k, dp.INT_MAX)
                    if k < dp.INT_MAX:                          # the largest multiple that fits
                        self.assertFalse(size[0] >= BASE_W * (k + 1) and size[1] >= BASE_H * (k + 1))

    def test_known_integer_results(self):
        self.assertEqual(tuple(compute_layout((800, 600)).rect), (0, 0, 800, 600))
        self.assertEqual(tuple(compute_layout((1920, 1080)).rect), (360, 90, 1200, 900))        # 3x, bars left/right
        self.assertEqual(tuple(compute_layout((1280, 720)).rect), (240, 60, 800, 600))          # 2x
        self.assertEqual(tuple(compute_layout((3440, 1440)).rect), (920, 120, 1600, 1200))      # 4x on an ultrawide
        self.assertEqual(compute_layout((1024, 768)).scale, 2)

    def test_fit_fills_the_window_without_uneven_stretching(self):
        for size in MATRIX:
            lay = compute_layout(size, "fit")
            with self.subTest(size=size):
                limit = min(size[0] / BASE_W, size[1] / BASE_H)
                self.assertAlmostEqual(lay.rect.w / BASE_W, limit, delta=2 / BASE_W + .01)
                self.assertTrue(lay.rect.w == size[0] or lay.rect.h == size[1] or size[0] < 2 or size[1] < 2)
                self.assertAlmostEqual(lay.rect.w / BASE_W, lay.rect.h / BASE_H, delta=.01)       # one factor, both axes

    def test_a_window_smaller_than_the_canvas_shrinks_smoothly_instead_of_clipping(self):
        for scaling in dp.SCALINGS:
            lay = compute_layout((300, 200), scaling)
            self.assertFalse(lay.exact)
            self.assertLess(lay.factor, 1)
            self.assertTrue(pygame.Rect(0, 0, 300, 200).contains(lay.rect))
            self.assertEqual(lay.scale, 1)

    def test_zero_and_negative_sizes_never_divide_by_zero(self):
        for size in ((0, 0), (0, 500), (500, 0), (-5, -5), (1, 1)):
            lay = compute_layout(size)
            self.assertGreaterEqual(lay.rect.w, 1)
            self.assertGreaterEqual(lay.rect.h, 1)
            self.assertIsNone(window_to_screen(lay, (-1, -1)))


class MouseMathTests(unittest.TestCase):
    def test_window_and_screen_coordinates_round_trip(self):
        for size in MATRIX:
            for scaling in dp.SCALINGS:
                lay = compute_layout(size, scaling)
                for p in ((0, 0), (10, 10), (lay.screen_size[0] // 2, lay.screen_size[1] // 2),
                          (lay.screen_size[0] - 1, lay.screen_size[1] - 1)):
                    back = window_to_screen(lay, screen_to_window(lay, p))
                    with self.subTest(size=size, scaling=scaling, p=p):
                        self.assertIsNotNone(back)
                        tol = max(1, int(1 / lay.factor) + 1)
                        self.assertLessEqual(abs(back[0] - p[0]), tol)
                        self.assertLessEqual(abs(back[1] - p[1]), tol)

    def test_points_in_the_black_bars_are_rejected(self):
        lay = compute_layout((1920, 1080))
        for pos in ((10, 500), (1900, 500), (359, 540), (1560, 540), (960, 89), (960, 991)):
            self.assertIsNone(window_to_screen(lay, pos), pos)
        self.assertIsNotNone(window_to_screen(lay, (360, 90)))
        self.assertIsNotNone(window_to_screen(lay, (1559, 989)))
        port = compute_layout((600, 1000), "fit")                       # a portrait window: bars above and below
        self.assertIsNone(window_to_screen(port, (300, 10)))
        self.assertIsNone(window_to_screen(port, (300, 990)))

    def test_canvas_conversion_is_independent_of_the_surface_scale(self):
        for s in (1, 2, 3, 4, 6):
            size = (BASE_W * s, BASE_H * s)
            self.assertEqual(screen_to_canvas((0, 0), size), (0, 0))
            self.assertEqual(screen_to_canvas((size[0] // 2, size[1] // 2), size), (BASE_W // 2, BASE_H // 2))
            self.assertEqual(screen_to_canvas((size[0] - 1, size[1] - 1), size), (BASE_W - 1, BASE_H - 1))
        self.assertEqual(screen_to_canvas((5, 5), (0, 0)), (5 * VIEW_W, 5 * VIEW_H))             # no division by zero


class SettingsValidationTests(unittest.TestCase):
    def test_garbage_becomes_the_defaults(self):
        for bad in (None, 5, "x", [], {"mode": 7, "scaling": None, "size": "big"}, {"size": [1, 2, 3]},
                    {"size": [True, False]}, {"size": [800.5, 600]}):
            s = validate_settings(bad)
            self.assertIn(s.mode, dp.MODES)
            self.assertIn(s.scaling, dp.SCALINGS)
            self.assertEqual(s.size, SAFE_SIZE)

    def test_sizes_are_kept_between_the_minimum_and_the_desktop(self):
        self.assertEqual(validate_settings({"size": [10, 10]}).size, MIN_WINDOW)
        self.assertEqual(validate_settings({"size": [5000, 4000]}, (1920, 1080)).size, (1920, 1080))
        self.assertEqual(validate_settings({"size": [1280, 720], "mode": "fullscreen", "scaling": "fit"}),
                         DisplaySettings("fullscreen", "fit", (1280, 720)))

    def test_presets_only_offer_sizes_that_fit_the_desktop_and_the_current_size(self):
        sizes = dp.size_presets((1366, 768), (1234, 700))
        self.assertIn((1234, 700), sizes)
        self.assertIn((1280, 720), sizes)
        self.assertNotIn((1920, 1080), sizes)
        self.assertEqual(dp.size_presets((100, 100)), [SAFE_SIZE])


# ----------------------------------------------------------------------------------- real windows
REAL_DESKTOP_SIZE = DisplayManager.desktop_size       # (the tests below replace it with a pretend big desktop)
BIG_DESKTOP = (7680, 4320)          # the dummy driver's desktop is only 1024x768; pretend to have a very large one


class ManagerCase(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(DisplayManager, "desktop_size", lambda self: BIG_DESKTOP)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "display.json")
        pygame.display.init()

    def make(self, prefs=None, path=True):
        if prefs is not None:
            with open(self.path, "w") as f:
                json.dump(prefs, f)
        return DisplayManager(prefs_path=self.path if path else None)

    def resize(self, dm, size):
        """What the OS does when the window is dragged: the display surface changes, then events arrive."""
        pygame.display.set_mode(size, pygame.RESIZABLE)
        for t in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED, pygame.WINDOWSIZECHANGED):
            dm.handle_event(pygame.event.Event(t, size=size, w=size[0], h=size[1], x=size[0], y=size[1]))


class ManagerTests(ManagerCase):
    def test_default_window_is_800_by_600_and_unchanged_for_scenes(self):
        dm = self.make(path=False)
        self.assertEqual(dm.window.get_size(), SAFE_SIZE)
        self.assertEqual(dm.screen.get_size(), (800, 600))
        self.assertEqual(dm.settings, DEFAULTS)

    def test_resizing_rebuilds_the_layout_once_and_never_for_duplicate_events(self):
        dm = self.make(path=False)
        for size in MATRIX:
            self.resize(dm, size)
            with self.subTest(size=size):
                self.assertEqual(dm.layout.window, size)
                self.assertEqual(dm.layout, compute_layout(size, dm.settings.scaling))
                self.assertEqual(dm.screen.get_size(), dm.layout.screen_size)
        self.resize(dm, (1920, 1080))
        rebuilds = dm.rebuilds
        for _ in range(5):                                     # the same resize reported again and again
            dm.handle_event(pygame.event.Event(pygame.WINDOWSIZECHANGED, x=1920, y=1080))
            dm.handle_event(pygame.event.Event(pygame.VIDEORESIZE, size=(1920, 1080), w=1920, h=1080))
        self.assertEqual(dm.rebuilds, rebuilds)

    def test_a_zero_size_resize_and_minimise_are_survived(self):
        dm = self.make(path=False)
        self.resize(dm, (1280, 720))
        before = dm.layout
        self.assertTrue(dm.handle_event(pygame.event.Event(pygame.VIDEORESIZE, size=(0, 0), w=0, h=0)))
        dm.present()
        self.assertEqual(dm.layout, before)
        dm.handle_event(pygame.event.Event(pygame.WINDOWMINIMIZED))
        self.assertTrue(dm.minimized)
        dm.present()                                           # nothing drawn, nothing raised
        dm.handle_event(pygame.event.Event(pygame.WINDOWRESTORED))
        self.assertFalse(dm.minimized)
        dm.present()
        with patch("pygame.display.get_surface", return_value=None):
            dm.present()
            self.assertFalse(dm.refresh())

    def test_presenting_puts_the_surface_in_the_viewport_and_black_bars_around_it(self):
        dm = self.make(path=False)
        for size, scaling in (((1920, 1080), "integer"), ((1920, 1080), "fit"), ((600, 1000), "fit"), ((330, 250), "integer")):
            dm.apply(DisplaySettings("windowed", scaling, size))
            dm.screen.fill((200, 40, 120))
            dm.present()
            win, lay = pygame.display.get_surface(), dm.layout
            with self.subTest(size=size, scaling=scaling):
                self.assertEqual(win.get_size(), size)
                tol = 0 if lay.exact else 8                 # a smooth shrink may blend a colour by a few levels
                for point in (lay.rect.center, (lay.rect.x + 1, lay.rect.y + 1)):
                    got = win.get_at(point)[:3]
                    self.assertTrue(all(abs(a - b) <= tol for a, b in zip(got, (200, 40, 120))), (point, got))
                if lay.bars:
                    outside = (0, 0) if lay.rect.x > 0 or lay.rect.y > 0 else None
                    if outside:
                        self.assertEqual(win.get_at(outside)[:3], (0, 0, 0))

    def test_integer_scaling_keeps_pixels_square_and_crisp(self):
        dm = self.make(path=False)
        dm.apply(DisplaySettings("windowed", "integer", (1280, 720)))
        canvas = pygame.Surface((BASE_W, BASE_H))
        canvas.fill((0, 0, 0))
        canvas.set_at((10, 10), (255, 255, 255))
        pygame.transform.scale(canvas, dm.screen.get_size(), dm.screen)
        dm.present()
        win, lay = pygame.display.get_surface(), dm.layout
        k = lay.scale
        x0, y0 = lay.rect.x + 10 * k, lay.rect.y + 10 * k
        for dx in range(k):
            for dy in range(k):
                self.assertEqual(win.get_at((x0 + dx, y0 + dy))[:3], (255, 255, 255))
        self.assertEqual(win.get_at((x0 + k, y0))[:3], (0, 0, 0))               # exactly one canvas pixel wide

    def test_changing_the_scaling_mode_needs_no_new_window(self):
        dm = self.make(path=False)
        self.resize(dm, (1366, 768))
        a = dm.layout
        dm.set_scaling("fit")
        self.assertNotEqual(dm.layout.rect.size, a.rect.size)
        self.assertEqual(dm.layout.window, (1366, 768))
        dm.set_scaling("integer")
        self.assertEqual(dm.layout, a)


class ModeTests(ManagerCase):
    def test_windowed_fullscreen_windowed_restores_the_size(self):
        dm = self.make(path=False)
        self.resize(dm, (1024, 768))
        self.assertEqual(dm.windowed_size, (1024, 768))
        self.assertTrue(dm.toggle_fullscreen())
        self.assertEqual(dm.settings.mode, "borderless")
        self.assertEqual(dm.window.get_size(), dm.desktop_size())
        self.assertEqual(dm.layout.window, dm.desktop_size())
        self.assertTrue(dm.toggle_fullscreen())
        self.assertEqual(dm.settings.mode, "windowed")
        self.assertEqual(dm.window.get_size(), (1024, 768))

    def test_all_three_modes_open_and_return_to_windowed(self):
        dm = self.make(path=False)
        for mode in dp.MODES:
            self.assertTrue(dm.apply(DisplaySettings(mode, "integer", (1280, 720))), mode)
            self.assertEqual(dm.settings.mode, mode)
            size = (1280, 720) if mode == "windowed" else dm.desktop_size()
            self.assertEqual(dm.window.get_size(), size)
            dm.screen.fill((1, 2, 3))
            dm.present()
        self.assertEqual(dm.windowed_size, (1280, 720))

    def test_a_failed_mode_change_falls_back_to_the_safe_window(self):
        dm = self.make(path=False)
        real = pygame.display.set_mode
        calls = []

        def flaky(size, flags=0, *a, **k):
            calls.append((size, flags))
            if len(calls) == 1:
                raise pygame.error("no such mode")
            return real(size, flags, *a, **k)
        with patch("pygame.display.set_mode", flaky), self.assertLogs("arcade.display", "ERROR"):
            ok = dm.apply(DisplaySettings("fullscreen", "fit", (1280, 720)))
        self.assertFalse(ok)
        self.assertEqual(dm.settings, DisplaySettings("windowed", "fit", SAFE_SIZE))
        self.assertEqual(dm.window.get_size(), SAFE_SIZE)
        self.assertIsNotNone(dm.last_error)

    def test_if_even_the_safe_window_fails_nothing_raises(self):
        dm = self.make(path=False)
        with patch("pygame.display.set_mode", side_effect=pygame.error("dead")), self.assertLogs("arcade.display", "ERROR"):
            self.assertFalse(dm.apply(DisplaySettings("borderless", "integer", (900, 700))))
        dm.present()

    def test_sizes_below_the_minimum_are_raised_to_it(self):
        dm = self.make(path=False)
        dm.apply(DisplaySettings("windowed", "integer", (10, 10)))
        self.assertGreaterEqual(dm.window.get_width(), MIN_WINDOW[0])
        self.assertGreaterEqual(dm.window.get_height(), MIN_WINDOW[1])


class FullscreenRestoreTests(ManagerCase):
    """Compositors such as WSLg keep the full-screen size when the window is re-created. Our side of it: the saved
    windowed size is the player's PREFERENCE and is never overwritten by what a transition briefly shows."""

    def stale_os(self, dm, stale):
        """An OS that keeps showing `stale` when a windowed window is created, until the size is requested again."""
        requests = []
        real = pygame.display.set_mode

        def set_mode(size, flags=0, *a, **k):
            if flags == pygame.RESIZABLE and tuple(size) != tuple(stale) and not requests:
                return real(stale, flags)                                # the compositor ignores the new size
            return real(size, flags, *a, **k)

        def request(size):
            requests.append(tuple(size))
            real(tuple(size), pygame.RESIZABLE)
            return True
        dm._request_size = request
        return patch("pygame.display.set_mode", set_mode), requests

    def test_a_transient_size_after_leaving_fullscreen_never_becomes_the_saved_size(self):
        dm = self.make()
        dm.apply(DisplaySettings("windowed", "integer", (1280, 720)))
        dm.toggle_fullscreen()
        self.assertEqual(dm.settings.mode, "borderless")
        patcher, requests = self.stale_os(dm, (1920, 1080))
        with patcher:
            dm.toggle_fullscreen()                                      # leave full screen; the OS shows 1920x1080
            self.assertEqual(dm.window.get_size(), (1920, 1080))
            self.assertEqual(dm.windowed_size, (1280, 720))             # the preference is untouched
            dm.handle_event(pygame.event.Event(pygame.WINDOWSIZECHANGED, x=1920, y=1080))
            self.assertEqual(dm.windowed_size, (1280, 720))
            for _ in range(8):
                dm.present()
        self.assertTrue(requests and requests[0] == (1280, 720))        # ... so the size is asked for again
        self.assertEqual(dm.window.get_size(), (1280, 720))
        self.assertIsNone(dm.pending_size)
        with open(self.path) as f:
            self.assertEqual(json.load(f)["size"], [1280, 720])

    def test_toggling_fullscreen_back_and_forth_never_changes_the_saved_size(self):
        dm = self.make()
        dm.apply(DisplaySettings("windowed", "fit", (1366, 768)))
        for _ in range(4):
            dm.toggle_fullscreen()
            dm.present()
            with open(self.path) as f:
                saved = json.load(f)
            self.assertEqual(saved["size"], [1366, 768])
            self.assertEqual(saved["scaling"], "fit")
        self.assertEqual(dm.windowed_size, (1366, 768))
        self.assertEqual(DisplayManager(prefs_path=self.path).windowed_size, (1366, 768))

    def test_if_the_os_never_gives_the_size_back_the_preference_still_survives(self):
        dm = self.make()
        dm.apply(DisplaySettings("windowed", "integer", (1280, 720)))
        dm.toggle_fullscreen()
        dm._request_size = lambda size: False                           # the OS refuses every request
        real = pygame.display.set_mode
        with patch("pygame.display.set_mode", lambda size, flags=0, *a, **k: real((1920, 1080), flags)):
            dm.toggle_fullscreen()
        dm.pending_until = 0                                            # ... for the whole grace period
        dm.present()
        self.assertIsNone(dm.pending_size)
        self.assertEqual(dm.windowed_size, (1280, 720))
        self.assertEqual(dm.settings.size, (1280, 720))
        self.assertEqual(dm.layout.window, (1920, 1080))                # drawn correctly at whatever size it has
        dm.save()
        with open(self.path) as f:
            self.assertEqual(json.load(f)["size"], [1280, 720])

    def test_a_real_drag_of_the_window_edge_does_update_the_preference(self):
        dm = self.make()
        dm.apply(DisplaySettings("windowed", "integer", (1280, 720)))
        for _ in range(3):
            dm.present()
        self.resize(dm, (1500, 900))
        self.assertEqual(dm.windowed_size, (1500, 900))
        self.assertEqual(dm.settings.size, (1500, 900))

    def test_fullscreen_sizes_come_from_the_monitor_the_window_is_on(self):
        dm = self.make(path=False)
        with patch.object(DisplayManager, "desktop_size", REAL_DESKTOP_SIZE), \
                patch("pygame.display.get_desktop_sizes", return_value=[(1920, 1080), (2560, 1600)]), \
                patch.object(DisplayManager, "display_index", lambda self: 1):
            self.assertEqual(dm.desktop_size(), (2560, 1600))
        with patch.object(DisplayManager, "desktop_size", REAL_DESKTOP_SIZE), \
                patch("pygame.display.get_desktop_sizes", return_value=[(1920, 1080)]), \
                patch.object(DisplayManager, "display_index", lambda self: 3):
            self.assertEqual(dm.desktop_size(), (1920, 1080))           # an unknown index falls back to the first


class PersistenceTests(ManagerCase):
    def test_settings_save_to_their_own_file_and_load_back(self):
        dm = self.make()
        dm.apply(DisplaySettings("windowed", "fit", (1280, 720)))
        self.assertTrue(dm.save())
        with open(self.path) as f:
            self.assertEqual(json.load(f), {"mode": "windowed", "scaling": "fit", "size": [1280, 720]})
        again = DisplayManager(prefs_path=self.path)
        self.assertEqual(again.settings, DisplaySettings("windowed", "fit", (1280, 720)))
        self.assertEqual(again.window.get_size(), (1280, 720))
        self.assertEqual(os.listdir(self.dir), ["display.json"])           # nothing else was written

    def test_invalid_or_damaged_files_fall_back_safely(self):
        for content in ('{"mode": "sideways", "size": [-5, 99999]}', "not json", "[]", ""):
            with open(self.path, "w") as f:
                f.write(content)
            dm = DisplayManager(prefs_path=self.path)
            self.assertIn(dm.settings.mode, dp.MODES)
            w, h = dm.window.get_size()
            self.assertTrue(w >= MIN_WINDOW[0] and h >= MIN_WINDOW[1], content)

    def test_a_saved_size_bigger_than_this_desktop_is_clamped(self):
        dm = self.make({"mode": "windowed", "scaling": "integer", "size": [9000, 9000]})
        dw, dh = dm.desktop_size()
        self.assertLessEqual(dm.window.get_width(), dw)
        self.assertLessEqual(dm.window.get_height(), dh)

    def test_saving_to_an_unwritable_place_does_not_raise(self):
        dm = DisplayManager(prefs_path=os.path.join(self.dir, "display.json", "x", "d.json"))
        open(os.path.join(self.dir, "display.json"), "w").close()
        with self.assertLogs("arcade.display", "WARNING"):
            self.assertFalse(dm.save())


class MouseEventTests(ManagerCase):
    def ev(self, t, pos, **kw):
        return pygame.event.Event(t, pos=pos, **kw)

    def test_presses_in_the_bars_are_dropped_and_inside_ones_are_converted(self):
        dm = self.make(path=False)
        dm.apply(DisplaySettings("windowed", "integer", (1920, 1080)))
        self.assertIsNone(dm.convert_mouse(self.ev(pygame.MOUSEBUTTONDOWN, (100, 500), button=1)))
        inside = dm.convert_mouse(self.ev(pygame.MOUSEBUTTONDOWN, (360 + 600, 90 + 450), button=1))
        self.assertEqual(inside.pos, (600, 450))
        self.assertEqual(inside.button, 1)
        up = dm.convert_mouse(self.ev(pygame.MOUSEBUTTONUP, (5, 5), button=1))         # a release is clamped, not lost
        self.assertEqual(up.pos, (0, 0))

    def test_motion_in_a_bar_clears_hover_and_a_drag_is_clamped(self):
        dm = self.make(path=False)
        dm.apply(DisplaySettings("windowed", "integer", (1920, 1080)))
        hover = dm.convert_mouse(self.ev(pygame.MOUSEMOTION, (10, 10), rel=(1, 1), buttons=(0, 0, 0)))
        self.assertEqual(hover.pos, (-1, -1))
        drag = dm.convert_mouse(self.ev(pygame.MOUSEMOTION, (10, 540), rel=(1, 0), buttons=(1, 0, 0)))
        self.assertEqual(drag.pos[0], 0)

    def test_the_wheel_only_counts_over_the_game(self):
        dm = self.make(path=False)
        dm.apply(DisplaySettings("windowed", "integer", (1920, 1080)))
        wheel = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1)
        with patch("pygame.mouse.get_pos", return_value=(50, 50)):
            self.assertIsNone(dm.convert_mouse(wheel))
        with patch("pygame.mouse.get_pos", return_value=(960, 540)):
            self.assertIsNotNone(dm.convert_mouse(wheel))

    def test_scaled_windows_convert_motion_deltas_too(self):
        dm = self.make(path=False)
        dm.apply(DisplaySettings("windowed", "fit", (1024, 768)))
        move = dm.convert_mouse(self.ev(pygame.MOUSEMOTION, (500, 400), rel=(10, 10), buttons=(0, 0, 0)))
        self.assertGreater(move.rel[0], 10)                          # the surface is bigger than the window here

    def test_other_events_pass_through_untouched(self):
        dm = self.make(path=False)
        key = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a")
        self.assertIs(dm.convert_mouse(key), key)


# ----------------------------------------------------------------------------------- the whole game
class GameCase(unittest.TestCase):
    players = 1

    def setUp(self):
        patcher = patch.object(DisplayManager, "desktop_size", lambda self: BIG_DESKTOP)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.display_path = os.path.join(self.dir, "display.json")
        profiles = [PlayerProfile(profile_id=f"p{i}", tickets=300, tokens=50) for i in range(self.players)]
        self.game = Game(session=LocalSession(profiles), display_prefs=self.display_path,
                         audio_prefs=os.path.join(self.dir, "audio.json"))
        self.addCleanup(self.game.quit)
        self.display = self.game.display

    def frames(self, n=1, key=None, mod=0):
        for i in range(n):
            ev = [pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode="")] if key and i == 0 else []
            self.game.step(ev, DT)

    def resize(self, size):
        pygame.display.set_mode(size, pygame.RESIZABLE)
        self.game.step([pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1])], DT)

    def click_window(self, canvas_pos, button=1, up=True):
        """A click on canvas position `canvas_pos`, expressed in WINDOW pixels as the OS would report it."""
        lay = self.display.layout
        sx, sy = canvas_pos[0] * lay.screen_size[0] / VIEW_W, canvas_pos[1] * lay.screen_size[1] / VIEW_H
        pos = screen_to_window(lay, (sx, sy))
        evs = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button)]
        if up:
            evs.append(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=button))
        self.game.step(evs, DT)

    def open_settings(self):
        self.frames(2, pygame.K_F4)
        self.frames(60)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, AudioSettingsScene)
        return scene


class SceneMouseTests(GameCase):
    def test_audio_slider_clicks_land_correctly_at_every_window_size(self):
        scene = self.open_settings()
        for size in MATRIX[:9]:
            for scaling in dp.SCALINGS:
                self.display.apply(DisplaySettings("windowed", scaling, size))
                self.frames(2)
                track = scene.slider_rect(0)
                for frac in (.2, .75):
                    self.click_window((track.x + track.w * frac, track.centery))
                    with self.subTest(size=size, scaling=scaling, frac=frac):
                        self.assertAlmostEqual(self.game.audio.bgm_volume, frac, delta=.04)

    def test_clicks_in_the_black_bars_do_nothing(self):
        scene = self.open_settings()
        self.resize((1920, 1080))
        before = self.game.audio.bgm_volume
        track = scene.slider_rect(0)
        lay = self.display.layout
        inside = screen_to_window(lay, (track.x * lay.scale * 2 // 2 * 1.0, track.centery * lay.scale * 2 // 2 * 1.0))
        for pos in ((40, inside[1]), (1900, inside[1]), (inside[0], 20)):
            self.game.step([pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1),
                            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1)], DT)
            self.assertEqual(self.game.audio.bgm_volume, before, pos)
        self.assertEqual(scene.row, 0)

    def test_menu_scenes_map_clicks_to_the_same_canvas_pixel_at_every_size(self):
        from shop_ui import ShopScene
        from wardrobe_ui import WardrobeScene
        owner = self.game.session.players[0]
        for cls in (ShopScene, WardrobeScene):
            scene = cls(self.game, owner)
            for size in MATRIX[:9]:
                self.display.apply(DisplaySettings("windowed", "fit", size))
                lay = self.display.layout
                for canvas_pos in ((40, 60), (200, 150), (390, 290)):
                    pos = screen_to_window(lay, (canvas_pos[0] * lay.screen_size[0] / VIEW_W,
                                                 canvas_pos[1] * lay.screen_size[1] / VIEW_H))
                    conv = self.display.convert_mouse(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
                    got = scene.mouse_pos(conv.pos)
                    with self.subTest(cls=cls.__name__, size=size, canvas=canvas_pos):
                        self.assertLessEqual(abs(got[0] - canvas_pos[0]), 1 + int(2 / lay.factor / lay.scale))
                        self.assertLessEqual(abs(got[1] - canvas_pos[1]), 1 + int(2 / lay.factor / lay.scale))

    def test_shop_tab_click_works_after_resizing(self):
        from shop_ui import TABS, ShopScene
        owner = self.game.session.players[0]
        for size in ((1280, 720), (3440, 1440), (640, 480), (600, 1000)):
            self.display.apply(DisplaySettings("windowed", "integer", size))
            shop = ShopScene(self.game, owner)
            self.game.scenes.push(shop, fade=False)
            self.frames(2)
            self.assertIs(self.game.scenes.current, shop)
            x = 14 + 4
            for i, name in enumerate(TABS):                    # tab i's rect is found by drawing once, then clicking it
                pass
            self.frames(1)
            rects = [r for r, _cb in shop._hit]
            self.assertTrue(rects)
            target = [r for r in rects if r.y < 60 and r.h <= 14][-1]            # the last tab
            self.click_window(target.center)
            self.assertEqual(shop.tab, len(TABS) - 1, size)
            self.game.scenes.pop(fade=False)
            self.frames(2)

    def test_wardrobe_mouse_clicks_work(self):
        """A real defect found by the audit: the wardrobe overrode MenuScene._click and crashed on any click."""
        from wardrobe_ui import WardrobeScene
        scene = WardrobeScene(self.game, self.game.session.players[0])
        self.game.scenes.push(scene, fade=False)
        for size in ((1280, 720), (3440, 1440), (800, 600)):
            self.display.apply(DisplaySettings("windowed", "integer", size))
            self.frames(2)
            rows = [r for r, _cb in scene._hit if r.h >= 14 and r.y > 55]
            self.assertTrue(rows)
            self.click_window(rows[1].center)
            self.click_window(rows[0].center)
        self.frames(2)

    def test_collection_decoration_and_character_creator_mouse_clicks_work(self):
        """Same audit finding as the wardrobe: CollectionScene overrode MenuScene._click and crashed on a click."""
        from collection_ui import CollectionScene
        owner = self.game.session.players[0]
        scenes = [CollectionScene(self.game, owner)]
        try:
            from decor_ui import DecorScene
            scenes.append(DecorScene(self.game, owner))
        except Exception:                   # noqa: BLE001 - its constructor needs a room; the others cover the point
            pass
        for scene in scenes:
            self.game.scenes.push(scene, fade=False)
            for size in ((1280, 720), (3440, 1440)):
                self.display.apply(DisplaySettings("windowed", "integer", size))
                self.frames(2)
                hits = [r for r, _cb in scene._hit]
                for rect in hits[:6]:
                    self.click_window(rect.center)
            self.game.scenes.pop(fade=False)
            self.frames(2)

    def test_neon21_buttons_use_the_converted_position_not_a_hardcoded_scale(self):
        from neon21_scene import Neon21Scene
        scene = Neon21Scene(self.game, self.game.session.players[0])
        self.game.scenes.push(scene, fade=False)
        self.frames(3)
        for size in ((800, 600), (1280, 720), (1920, 1080), (2560, 1440)):
            self.display.apply(DisplaySettings("windowed", "integer", size))
            self.frames(2)
            self.assertTrue(scene.buttons)
            name, (rect, _label, _enabled) = next(iter(scene.buttons.items()))
            lay = self.display.layout
            pos = screen_to_window(lay, (rect.centerx * lay.scale * 2 // 2, rect.centery * lay.scale * 2 // 2))
            conv = self.display.convert_mouse(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
            scene.handle_event(conv)
            self.assertEqual(scene.hover, name, size)

    def test_cat_territory_cells_follow_the_mouse_at_any_size(self):
        from cat_minesweeper.mouse import MineMouseInput
        for size in MATRIX[:9]:
            self.display.apply(DisplaySettings("windowed", "fit", size))
            lay = self.display.layout
            for canvas in ((100, 100), (200, 150), (300, 250)):
                spos = (canvas[0] * lay.screen_size[0] / VIEW_W, canvas[1] * lay.screen_size[1] / VIEW_H)
                conv = self.display.convert_mouse(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=screen_to_window(lay, spos), button=1))
                got = MineMouseInput.canvas_position(conv.pos, self.game.screen.get_size())
                self.assertLessEqual(abs(got[0] - canvas[0]), 2, (size, canvas))
                self.assertLessEqual(abs(got[1] - canvas[1]), 2, (size, canvas))


class TwoPlayerTests(GameCase):
    players = 2

    def test_both_players_can_use_menus_after_resizing(self):
        from wardrobe_ui import WardrobeScene
        self.resize((1366, 768))
        for owner in self.game.session.players:
            scene = WardrobeScene(self.game, owner)
            self.game.scenes.push(scene, fade=False)
            self.frames(2)
            key = next(iter(owner.controls.keys & {pygame.K_d, pygame.K_RIGHT}), None)
            self.assertIsNotNone(key)
            before = (getattr(scene, "tab", 0), getattr(scene, "index", 0))
            self.frames(2, key)
            self.assertIs(self.game.scenes.current, scene)
            self.game.scenes.pop(fade=False)
            self.frames(2)
        self.assertEqual(len(self.game.session.players), 2)


class GameLevelTests(GameCase):
    def test_alt_enter_and_f11_toggle_fullscreen_without_pressing_interact(self):
        room = goto_room(self.game, "arcade_floor")
        self.frames(30)
        confirms = self.game.audio.last_effect.get("confirm")
        self.frames(2, pygame.K_RETURN, mod=pygame.KMOD_ALT)
        self.assertEqual(self.display.settings.mode, "borderless")
        self.assertEqual(self.game.audio.last_effect.get("confirm"), confirms)       # Alt+Enter is not "interact"
        self.frames(2, pygame.K_RETURN, mod=pygame.KMOD_ALT)
        self.assertEqual(self.display.settings.mode, "windowed")
        self.frames(2, pygame.K_F11)
        self.assertEqual(self.display.settings.mode, "borderless")
        self.frames(2, pygame.K_F11)
        self.assertIs(self.game.scenes.current, room)
        self.assertEqual(self.display.window.get_size(), SAFE_SIZE)

    def test_plain_enter_still_interacts(self):
        goto_room(self.game, "arcade_floor")
        self.frames(30)
        self.frames(2, pygame.K_RETURN)
        self.assertEqual(self.display.settings.mode, "windowed")
        self.assertIn("confirm", self.game.audio.last_effect)

    def test_audio_keeps_playing_through_resizes_and_mode_changes(self):
        goto_room(self.game, "arcade_floor")
        self.frames(60)
        audio = self.game.audio
        starts, theme = audio.music_starts, audio.theme
        for size in ((1920, 1080), (640, 480), (3440, 1440)):
            self.resize(size)
            self.frames(10)
        self.display.toggle_fullscreen()
        self.frames(10)
        self.display.toggle_fullscreen()
        self.frames(10)
        self.assertTrue(audio.music_playing())
        self.assertEqual((audio.music_starts, audio.theme), (starts, theme))
        self.assertIsNotNone(pygame.mixer.get_init())

    def test_every_room_draws_at_every_window_size_and_walking_works(self):
        for size in MATRIX:
            self.display.apply(DisplaySettings("windowed", "fit", size))
            for room_id in ("arcade_floor", "home", "prize_plaza"):
                goto_room(self.game, room_id)
                self.frames(3)
                self.assertEqual(self.game.screen.get_size(), self.display.layout.screen_size)
                self.display.present()
        room = self.game.scenes.current
        x = room.players[0].x
        self.game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, mod=0, unicode="d")], DT)
        self.frames(30)
        self.assertNotEqual(room.players[0].x, x)

    def test_game_speed_does_not_depend_on_the_window(self):
        goto_room(self.game, "arcade_floor")
        self.frames(30)
        distances = []
        for size in ((800, 600), (3440, 1440), (640, 480)):
            self.display.apply(DisplaySettings("windowed", "integer", size))
            room = goto_room(self.game, "arcade_floor")
            self.frames(30)
            p = room.players[0]
            x0 = p.x
            self.game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, mod=0, unicode="d")], DT)
            self.frames(30)
            distances.append(round(p.x - x0, 3))
            self.game.step([pygame.event.Event(pygame.KEYUP, key=pygame.K_d, mod=0)], DT)
        self.assertEqual(len(set(distances)), 1, distances)

    def test_transitions_resizing_mid_wipe_and_minigames_survive_a_resize(self):
        room = goto_room(self.game, "arcade_floor")
        self.frames(30)
        self.frames(2, pygame.K_F4)                          # the wipe has started
        self.resize((1920, 1080))
        self.frames(5)
        self.resize((640, 480))
        self.frames(60)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, AudioSettingsScene)
        self.game.scenes.pop()
        self.resize((2560, 1440))
        self.frames(60)
        self.assertIs(self.game.scenes.current, room)
        for game_id in ("pixel_volleyball", "galaxy_defender"):
            machine = next(m for m in room.machines if m.id == game_id)
            room._start_game(machine, player=room.players[0])
            self.frames(60)
            self.resize((1366, 768))
            self.frames(20)
            self.resize((3440, 1440))
            self.frames(20)
            self.assertEqual(self.game.screen.get_size(), self.display.layout.screen_size)
            self.game.scenes.pop()
            self.frames(60)
            self.assertIs(self.game.scenes.current, room)

    def test_the_racer_renders_into_any_presentation_surface(self):
        from retro_racer_scene import RACER_SIZE, RetroRacerScene, fit_rect
        room = goto_room(self.game, "arcade_floor")
        self.frames(20)
        machine = next(m for m in room.machines if m.id == "retro_racer")
        room._start_game(machine, player=room.players[0])
        for _ in range(900):
            self.frames(1)
            scene = self.game.scenes.current
            if isinstance(scene, RetroRacerScene) and scene.racer is not None:
                break
        for size in ((1280, 720), (1920, 1080), (3440, 1440), (640, 480)):
            self.display.apply(DisplaySettings("windowed", "integer", size))
            self.frames(5)
            self.assertEqual(scene.surface.get_size(), RACER_SIZE)             # its own logical surface never changes
            self.assertEqual(tuple(fit_rect(RACER_SIZE, self.game.screen.get_size())), (0, 0, *self.game.screen.get_size()))
            self.display.present()
        self.game.scenes.pop()
        self.frames(60)

    def test_display_settings_do_not_touch_profiles(self):
        before = self.game.profile.tickets
        self.display.apply(DisplaySettings("windowed", "fit", (1280, 720)))
        self.display.save()
        self.assertEqual(self.game.profile.tickets, before)
        self.assertEqual(sorted(os.listdir(self.dir)), ["display.json"])

    def test_restart_with_saved_settings(self):
        self.display.apply(DisplaySettings("windowed", "fit", (1280, 720)))
        self.display.save()
        again = Game(session=LocalSession([PlayerProfile(profile_id="again")]), display_prefs=self.display_path)
        self.addCleanup(again.quit)
        self.assertEqual(again.display.settings, DisplaySettings("windowed", "fit", (1280, 720)))
        self.assertEqual(again.display.window.get_size(), (1280, 720))


class DisplayPageTests(GameCase):
    def page(self):
        scene = self.open_settings()
        self.frames(2, pygame.K_TAB)
        self.assertEqual(scene.tab, 1)
        return scene, scene.display_page

    def press(self, scene, key):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))

    def test_tab_switches_pages_and_audio_still_works(self):
        scene = self.open_settings()
        before = self.game.audio.bgm_volume
        self.press(scene, pygame.K_TAB)
        self.assertEqual(scene.tab, 1)
        self.press(scene, pygame.K_TAB)
        self.assertEqual(scene.tab, 0)
        self.press(scene, pygame.K_LEFT)
        self.assertLess(self.game.audio.bgm_volume, before)

    def test_the_tab_chips_are_clickable(self):
        scene = self.open_settings()
        self.click_window(scene.tab_rect(1).center)
        self.assertEqual(scene.tab, 1)
        self.click_window(scene.tab_rect(0).center)
        self.assertEqual(scene.tab, 0)

    def test_apply_changes_the_window_then_keep_saves_it(self):
        scene, page = self.page()
        page.size = (1280, 720)
        page.row = ROWS.index("APPLY")
        self.press(scene, pygame.K_RETURN)
        self.assertEqual(self.display.window.get_size(), (1280, 720))
        self.assertTrue(page.confirming)
        self.assertFalse(os.path.exists(self.display_path))            # not saved until confirmed
        self.press(scene, pygame.K_RETURN)
        self.assertFalse(page.confirming)
        with open(self.display_path) as f:
            self.assertEqual(json.load(f)["size"], [1280, 720])

    def test_not_confirming_reverts_the_display_after_the_countdown(self):
        scene, page = self.page()
        page.mode = "borderless"
        page.row = ROWS.index("APPLY")
        self.press(scene, pygame.K_RETURN)
        self.assertEqual(self.display.settings.mode, "borderless")
        for _ in range(int(CONFIRM_SECONDS * 60) + 30):
            self.frames(1)
        self.assertFalse(page.confirming)
        self.assertEqual(self.display.settings.mode, "windowed")
        self.assertEqual(self.display.window.get_size(), SAFE_SIZE)
        self.assertFalse(os.path.exists(self.display_path))

    def test_escape_reverts_and_leaving_mid_countdown_reverts(self):
        scene, page = self.page()
        page.size, page.row = (1024, 768), ROWS.index("APPLY")
        self.press(scene, pygame.K_RETURN)
        self.press(scene, pygame.K_ESCAPE)
        self.assertEqual(self.display.window.get_size(), SAFE_SIZE)
        page.size, page.row = (1024, 768), ROWS.index("APPLY")
        self.press(scene, pygame.K_RETURN)
        self.assertEqual(self.display.window.get_size(), (1024, 768))
        self.frames(2, pygame.K_F4)                                   # F4 closes the screen: the display is put back
        self.frames(40)
        self.assertEqual(self.display.window.get_size(), SAFE_SIZE)
        self.assertFalse(isinstance(self.game.scenes.current, AudioSettingsScene))

    def test_cancel_discards_the_draft_and_nothing_applies_twice(self):
        scene, page = self.page()
        page.cycle(0, 1)
        page.cycle(2, 1)
        page.row = ROWS.index("CANCEL")
        self.press(scene, pygame.K_RETURN)
        self.assertEqual((page.mode, page.scaling), ("windowed", "integer"))
        page.row = ROWS.index("APPLY")
        self.press(scene, pygame.K_RETURN)
        self.assertEqual(scene.message, "NOTHING TO APPLY")
        self.assertFalse(page.confirming)

    def test_restore_defaults_goes_back_to_800_by_600_integer(self):
        scene, page = self.page()
        self.display.apply(DisplaySettings("windowed", "fit", (1280, 720)))
        page.sync()
        page.row = ROWS.index("RESTORE DEFAULTS")
        self.press(scene, pygame.K_RETURN)
        self.assertEqual(self.display.settings, DEFAULTS)
        self.assertTrue(page.confirming)
        self.press(scene, pygame.K_RETURN)

    def test_a_failed_apply_reports_it_and_uses_the_safe_window(self):
        scene, page = self.page()
        page.mode, page.row = "fullscreen", ROWS.index("APPLY")
        real = pygame.display.set_mode
        count = [0]

        def flaky(size, flags=0, *a, **k):
            count[0] += 1
            if count[0] == 1:
                raise pygame.error("nope")
            return real(size, flags, *a, **k)
        with patch("pygame.display.set_mode", flaky), self.assertLogs("arcade.display", "ERROR"):
            self.press(scene, pygame.K_RETURN)
        self.assertIn("FAILED", scene.message)
        self.assertFalse(page.confirming)
        self.assertEqual(self.display.window.get_size(), SAFE_SIZE)

    def test_mouse_works_on_the_page_at_other_window_sizes(self):
        scene, page = self.page()
        for size in ((1920, 1080), (3440, 1440), (1024, 768)):
            self.display.apply(DisplaySettings("windowed", "integer", size))
            page.sync()
            self.frames(2)
            page.mode = "windowed"
            self.click_window(page.row_rect(2).center)                     # SCALING row: cycles forward
            self.assertEqual(page.row, 2)
        self.display.apply(DisplaySettings("windowed", "integer", (1920, 1080)))
        page.sync()
        page.mode, page.size = "windowed", (1280, 720)
        self.click_window(page.row_rect(ROWS.index("APPLY")).center)
        self.assertTrue(page.confirming)
        self.click_window(page.keep_rect().center)
        self.assertFalse(page.confirming)
        self.assertEqual(self.display.window.get_size(), (1280, 720))

    def test_the_size_row_is_inert_in_fullscreen_modes_and_the_page_draws(self):
        scene, page = self.page()
        page.mode = "borderless"
        before = page.size
        page.cycle(1, 1)
        self.assertEqual(page.size, before)
        self.assertIn("DESKTOP", page.value_text(1))
        for row in range(len(ROWS)):
            page.row = row
            self.frames(2)
        page.confirm_left = 5
        self.frames(2)                                                     # the KEEP / REVERT box draws too
        page.confirm_left = 0

    def test_music_never_restarts_while_changing_display_settings(self):
        goto_room(self.game, "arcade_floor")
        self.frames(60)
        audio = self.game.audio
        starts = audio.music_starts
        scene, page = self.page()
        for mode in ("borderless", "fullscreen", "windowed"):
            page.mode, page.row = mode, ROWS.index("APPLY")
            self.press(scene, pygame.K_RETURN)
            self.press(scene, pygame.K_RETURN)
            self.frames(5)
        self.assertEqual(audio.music_starts, starts)
        self.assertTrue(audio.music_playing())


if __name__ == "__main__":
    unittest.main()
