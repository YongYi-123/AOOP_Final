"""Mouse interaction across the whole arcade UI at many window sizes: every clickable element of each screen is
clicked at its centre through the real event pipeline (window pixels -> DisplayManager -> scene), clicks in the
black bars are shown to do nothing, and hovering, dragging and the wheel are checked where the screens use them.

Synthetic windows (SDL dummy driver): this proves the arithmetic and the routing, not a physical monitor.
Run from this folder:  python -m unittest test_display_mouse -v
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from audio_settings_ui import AudioSettingsScene  # noqa: E402
from display_settings_ui import ROWS  # noqa: E402
from display import DisplayManager, DisplaySettings, screen_to_window  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402

DT = 1 / 60
SIZES = [("integer", (800, 600)), ("integer", (1280, 720)), ("integer", (1920, 1080)), ("integer", (2560, 1440)),
         ("integer", (3440, 1440)), ("fit", (1366, 768)), ("fit", (600, 1000)), ("integer", (330, 250))]


class MouseCase(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(DisplayManager, "desktop_size", lambda self: (7680, 4320))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.game = Game(session=LocalSession([PlayerProfile(profile_id="m", tickets=500, tokens=50)]),
                         audio_prefs=os.path.join(self.dir, "audio.json"))
        self.addCleanup(self.game.quit)
        self.display = self.game.display

    def frames(self, n=1):
        for _ in range(n):
            self.game.step([], DT)

    def window_pos(self, canvas_pos):
        lay = self.display.layout
        return screen_to_window(lay, (canvas_pos[0] * lay.screen_size[0] / VIEW_W,
                                      canvas_pos[1] * lay.screen_size[1] / VIEW_H))

    def click(self, canvas_pos=None, window=None, up=True):
        pos = window if window is not None else self.window_pos(canvas_pos)
        evs = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)]
        if up:
            evs.append(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))
        self.game.step(evs, DT)

    def bar_points(self):
        """Window points that lie in a black bar (empty when the viewport fills the window)."""
        lay = self.display.layout
        w, h = lay.window
        r = lay.rect
        pts = []
        if r.x > 2:
            pts += [(1, h // 2), (r.x - 1, h // 2), (r.x // 2, 5)]
        if r.right < w - 2:
            pts += [(r.right, h // 2), (w - 1, h // 2)]
        if r.y > 2:
            pts += [(w // 2, 0), (w // 2, r.y - 1)]
        if r.bottom < h - 2:
            pts += [(w // 2, r.bottom), (w // 2, h - 1)]
        return [p for p in pts if not r.collidepoint(p) and 0 <= p[0] < w and 0 <= p[1] < h]

    def hit_rects(self, scene):
        self.frames(2)
        return [(rect.copy(), cb) for rect, cb in scene._hit]


class MenuScreenTests(MouseCase):
    def scenes(self):
        from character_creator import CharacterCreatorScene
        from collection_ui import CollectionScene
        from decor_ui import DecorationScene
        from shop_ui import ShopScene
        from wardrobe_ui import WardrobeScene
        owner = self.game.session.players[0]
        home = goto_room(self.game, "home")
        self.frames(3)
        flow = type("Flow", (), {})()
        return {"PRIZE COUNTER": ShopScene(self.game, owner), "WARDROBE": WardrobeScene(self.game, owner),
                "COLLECTION": CollectionScene(self.game, owner), "HOME DECORATION": DecorationScene(self.game, owner, home),
                "CHARACTER CREATOR": CharacterCreatorScene(self.game, flow, "TEST", owner.profile.look if hasattr(owner.profile, "look") else owner.avatar.look,
                                                           lambda basic: None, lambda: None)}

    def test_every_clickable_element_is_hit_at_every_window_size(self):
        for name, scene in self.scenes().items():
            self.game.scenes.push(scene, fade=False)
            for scaling, size in SIZES:
                self.display.apply(DisplaySettings("windowed", scaling, size))
                rects = self.hit_rects(scene)
                self.assertTrue(rects, f"{name}: nothing clickable")
                for i, (rect, _cb) in enumerate(rects):
                    calls = []
                    scene._hit = [(r, (lambda j=j: calls.append(j))) for j, (r, _c) in enumerate(rects)]
                    centre = rect.center
                    if rect.w < 3 or rect.h < 3:
                        continue
                    self.click(centre)
                    with self.subTest(scene=name, size=size, scaling=scaling, rect=tuple(rect)):
                        self.assertTrue(calls, "the click reached no element")
                        self.assertTrue(rects[calls[-1]][0].collidepoint(centre))          # ... and it is the right one
            self.game.scenes.pop(fade=False)
            self.frames(2)

    def test_clicks_in_the_black_bars_never_reach_a_screen(self):
        for name, scene in self.scenes().items():
            self.game.scenes.push(scene, fade=False)
            for scaling, size in SIZES:
                self.display.apply(DisplaySettings("windowed", scaling, size))
                rects = self.hit_rects(scene)
                bars = self.bar_points()
                calls = []
                scene._hit = [(r, (lambda: calls.append(1))) for r, _c in rects]
                for pos in bars:
                    self.click(window=pos)
                with self.subTest(scene=name, size=size):
                    self.assertEqual(calls, [])
            self.game.scenes.pop(fade=False)
            self.frames(2)

    def test_the_wheel_works_over_the_game_and_not_over_the_bars(self):
        from shop_ui import ShopScene
        shop = ShopScene(self.game, self.game.session.players[0])
        self.game.scenes.push(shop, fade=False)
        self.display.apply(DisplaySettings("windowed", "integer", (1920, 1080)))
        self.frames(2)
        actions = []
        wheel = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1)
        with patch.object(shop, "on_action", lambda action: actions.append(action)):
            with patch("pygame.mouse.get_pos", return_value=(20, 500)):                  # a bar
                self.game.step([wheel], DT)
            self.assertEqual(actions, [])
            with patch("pygame.mouse.get_pos", return_value=(960, 540)):                 # the game
                self.game.step([wheel], DT)
            self.assertEqual(actions, ["down"])


class Neon21Tests(MouseCase):
    def test_hover_and_click_every_button_at_every_size_and_bars_clear_the_hover(self):
        from neon21_scene import Neon21Scene
        scene = Neon21Scene(self.game, self.game.session.players[0])
        self.game.scenes.push(scene, fade=False)
        self.frames(3)
        pressed = []
        with patch.object(scene, "_press", lambda name: pressed.append(name)):
            for scaling, size in SIZES:
                self.display.apply(DisplaySettings("windowed", scaling, size))
                self.frames(2)
                enabled = {n: r for n, (r, _l, e) in scene.buttons.items() if e}
                self.assertTrue(enabled)
                for name, rect in enabled.items():
                    pos = self.window_pos(rect.center)
                    self.game.step([pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(1, 1), buttons=(0, 0, 0))], DT)
                    with self.subTest(button=name, size=size):
                        self.assertEqual(scene.hover, name)
                    pressed.clear()
                    self.click(rect.center)
                    with self.subTest(button=name, size=size, what="click"):
                        self.assertEqual(pressed, [name])
                for pos in self.bar_points():
                    pressed.clear()
                    self.game.step([pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(1, 1), buttons=(0, 0, 0))], DT)
                    self.assertIsNone(scene.hover)
                    self.click(window=pos)
                    self.assertEqual(pressed, [])


class LayoutDefectTests(MouseCase):
    def test_neon21_header_text_is_not_covered_by_the_felt(self):
        """Found in the audit: the TICKETS line was drawn 2 px into the felt table, which then covered its bottom rows."""
        from neon21_scene import Neon21Scene
        scene = Neon21Scene(self.game, self.game.session.players[0])
        self.game.scenes.push(scene, fade=False)
        self.frames(3)
        header = [r for r in scene.text_rects if r.x < 100 and r.y < 30]
        self.assertTrue(header)
        self.assertLessEqual(max(r.bottom for r in header), 22)         # the felt's outer rim starts at y=22


class SettingsTests(MouseCase):
    def open(self):
        self.game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F4, mod=0, unicode="")], DT)
        self.frames(60)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, AudioSettingsScene)
        return scene

    def test_audio_sliders_click_drag_and_wheel_at_every_size(self):
        scene = self.open()
        for scaling, size in SIZES:
            self.display.apply(DisplaySettings("windowed", scaling, size))
            self.frames(2)
            for row in (0, 1):
                track = scene.slider_rect(row)
                self.click((track.x + track.w * .3, track.centery), up=False)
                v = self.game.audio.bgm_volume if row == 0 else self.game.audio.sfx_volume
                self.assertAlmostEqual(v, .3, delta=.05, msg=(size, row))
                for frac in (.5, .9):                                                 # a drag
                    self.game.step([pygame.event.Event(pygame.MOUSEMOTION, pos=self.window_pos((track.x + track.w * frac, track.centery)),
                                                       rel=(3, 0), buttons=(1, 0, 0))], DT)
                v = self.game.audio.bgm_volume if row == 0 else self.game.audio.sfx_volume
                self.assertAlmostEqual(v, .9, delta=.05, msg=(size, row))
                self.game.step([pygame.event.Event(pygame.MOUSEBUTTONUP, pos=self.window_pos((track.x, track.centery)), button=1)], DT)
                self.assertIsNone(scene.dragging)

    def test_a_drag_that_ends_in_a_black_bar_still_releases_the_slider(self):
        scene = self.open()
        self.display.apply(DisplaySettings("windowed", "integer", (1920, 1080)))
        self.frames(2)
        track = scene.slider_rect(0)
        self.click((track.x + track.w * .5, track.centery), up=False)
        self.game.step([pygame.event.Event(pygame.MOUSEMOTION, pos=(5, 540), rel=(-9, 0), buttons=(1, 0, 0))], DT)
        self.assertEqual(self.game.audio.bgm_volume, 0.0)                              # clamped to the track's end
        self.game.step([pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(5, 540), button=1)], DT)
        self.assertIsNone(scene.dragging)
        self.game.step([pygame.event.Event(pygame.MOUSEMOTION, pos=self.window_pos((track.x + track.w, track.centery)),
                                           rel=(5, 0), buttons=(0, 0, 0))], DT)
        self.assertEqual(self.game.audio.bgm_volume, 0.0)                              # no longer dragging

    def test_clicks_in_the_bars_change_neither_settings_page(self):
        scene = self.open()
        self.display.apply(DisplaySettings("windowed", "integer", (1920, 1080)))
        self.frames(2)
        before = (self.game.audio.bgm_volume, self.game.audio.sfx_volume, self.game.audio.muted, scene.row, scene.tab)
        for pos in self.bar_points():
            self.click(window=pos)
        self.assertEqual((self.game.audio.bgm_volume, self.game.audio.sfx_volume, self.game.audio.muted, scene.row, scene.tab), before)
        self.click(scene.tab_rect(1).center)
        page = scene.display_page
        rows_before = (page.row, page.mode, page.scaling, page.size)
        for pos in self.bar_points():
            self.click(window=pos)
        self.assertEqual((page.row, page.mode, page.scaling, page.size), rows_before)
        self.assertFalse(page.confirming)

    def test_every_display_row_and_button_is_clickable_at_every_size(self):
        scene = self.open()
        self.click(scene.tab_rect(1).center)
        page = scene.display_page
        for scaling, size in SIZES[:6]:
            self.display.apply(DisplaySettings("windowed", scaling, size))
            page.sync()
            self.frames(2)
            for row, name in enumerate(ROWS):
                if name in ("APPLY", "RESTORE DEFAULTS", "BACK"):
                    continue                                       # those change the window or leave; covered elsewhere
                page.row = (row + 1) % 3
                self.click(page.row_rect(row).center)
                with self.subTest(size=size, row=row):
                    self.assertEqual(page.row, row)


class HomeDecorDragTests(MouseCase):
    def test_a_press_and_release_in_a_bar_do_not_move_anything_in_the_decorating_screen(self):
        from decor_ui import DecorationScene
        home = goto_room(self.game, "home")
        self.frames(3)
        scene = DecorationScene(self.game, self.game.session.players[0], home)
        self.game.scenes.push(scene, fade=False)
        self.display.apply(DisplaySettings("windowed", "integer", (1920, 1080)))
        self.frames(2)
        state = (scene.slot, scene.index, scene.choosing)
        for pos in self.bar_points():
            self.click(window=pos)
            self.game.step([pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(4, 0), buttons=(1, 0, 0))], DT)
        self.assertEqual((scene.slot, scene.index, scene.choosing), state)


class CatTerritoryTests(MouseCase):
    def test_cells_under_the_pointer_are_right_and_bar_clicks_place_nothing(self):
        from cat_territory_scene import CatTerritoryScene
        room = goto_room(self.game, "arcade_floor")
        self.frames(20)
        machine = next(m for m in room.machines if m.id == "cat_minesweeper")
        room._start_game(machine, player=room.players[0])
        self.frames(60)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, CatTerritoryScene)
        calls = []
        with patch.object(scene.territory, "click", lambda point, button: calls.append((point, button))):
            for scaling, size in SIZES:
                self.display.apply(DisplaySettings("windowed", scaling, size))
                self.frames(2)
                calls.clear()
                for canvas in ((60, 60), (200, 150), (340, 250)):
                    self.click(canvas)
                with self.subTest(size=size):
                    self.assertEqual(len(calls), 3)
                    for (point, _b), canvas in zip(calls, ((60, 60), (200, 150), (340, 250))):
                        self.assertLessEqual(abs(point[0] - canvas[0]), 3)
                        self.assertLessEqual(abs(point[1] - canvas[1]), 3)
                calls.clear()
                for pos in self.bar_points():
                    self.click(window=pos)
                self.assertEqual(calls, [], size)
        self.game.scenes.pop()
        self.frames(60)


if __name__ == "__main__":
    unittest.main()
