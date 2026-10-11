"""Layout regression tests for every Retro Racer menu screen: all text stays inside the 800x600 surface,
no two labels overlap, and the panels of a screen never collide - for the default keys, a P1 key set
and a P2 key set with long names, and for every track / scenery / car (locked or not).

Run with:  python -m unittest test_menu_layout
"""
import itertools
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import settings as S
from game import Game
from hud import DEFAULT_KEYS
from menu_layout import CONTENT, FOOTER, MARGIN, SCREEN
from race import State

P1_KEYS = {**DEFAULT_KEYS, "accelerate": "W", "brake": "S", "steer": "A  D", "confirm": "E",
           "resume": "I/ESC", "item": "SPACE/SHIFT", "item_long": "SPACE/SHIFT/I"}
P2_KEYS = {**DEFAULT_KEYS, "accelerate": "UP", "brake": "DOWN", "steer": "LEFT  RIGHT", "confirm": "ENTER/RCTRL",
           "resume": "O/ESC", "item": "RSHIFT/KP0", "item_long": "RSHIFT/KP0/RCTRL"}
KEY_SETS = {"default": DEFAULT_KEYS, "p1": P1_KEYS, "p2": P2_KEYS}
IDLE = {"accelerate": False, "brake": False, "steer": 0}


class LockedGarage:
    """Owns only the free starter items, like a new profile."""
    FREE = {("car", "falcon"), ("track", "emerald"), ("scenery", "suburbs")}
    PRICE = {"car": 120, "track": 150, "scenery": 40}

    def owns(self, kind, key):
        return (kind, key) in self.FREE

    def lock_message(self, kind, key):
        return f"LOCKED - {self.PRICE[kind]} TICKETS"

    def select(self, kind, key):
        pass

    paint_color = None

    def selected(self, kind):
        return {"car": "falcon", "track": "emerald", "scenery": "suburbs"}.get(kind, "factory")


def shrunk(rect, by=3):
    """A label's rect without its outline padding, so touching outlines don't count as overlap."""
    return rect.inflate(-2 * by, -2 * by)


class MenuLayoutTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.addCleanup(self.game.audio.stop_engine)
        self.game.configure_progression(LockedGarage())

    def render(self, state, keys):
        game = self.game
        game.hud.keys.clear()
        game.hud.keys.update(keys)
        game.state = state
        game.hud.trace = []
        game.render()
        trace, game.hud.trace = game.hud.trace, None
        return trace

    def assert_clean(self, trace, label):
        self.assertTrue(trace, label)
        frame = SCREEN.inflate(-8, -8)
        for rect, msg in trace:
            self.assertTrue(frame.contains(rect), f"{label}: {msg!r} {rect} leaves the screen")
        for (ra, ma), (rb, mb) in itertools.combinations(trace, 2):
            self.assertFalse(shrunk(ra).colliderect(shrunk(rb)), f"{label}: {ma!r} overlaps {mb!r}")

    def select(self, track=None, scenery=None):
        game = self.game
        if track is not None:
            game.track_index, game.track = track, game.tracks[track]
        if scenery is not None:
            game.theme_index, game.theme = scenery, game.themes.themes[scenery]
        game.apply_look()

    def test_title_mode_and_pause_for_every_key_set(self):
        for name, keys in KEY_SETS.items():
            for state in (State.TITLE, State.MODE_SELECT):
                if state is State.MODE_SELECT:
                    for mode_index in (0, 1):
                        self.game.mode_index = mode_index
                        self.assert_clean(self.render(state, keys), f"{state.name}/{mode_index}/{name}")
                else:
                    self.assert_clean(self.render(state, keys), f"{state.name}/{name}")
            self.game.hud.trace = []
            self.game.hud.keys.clear()
            self.game.hud.keys.update(keys)
            self.game.hud.draw_pause(pygame.Surface(SCREEN.size), 0.0)
            trace, self.game.hud.trace = self.game.hud.trace, None
            self.assert_clean(trace, f"PAUSE/{name}")

    def test_every_track_and_scenery_combination_fits(self):
        game = self.game
        for name, keys in KEY_SETS.items():
            for track, scenery in itertools.product(range(len(game.tracks)), range(len(game.themes.themes))):
                self.select(track, scenery)
                self.assert_clean(self.render(State.TRACK_SELECT, keys),
                                  f"TRACK {game.tracks[track].name}/{game.themes.themes[scenery].name}/{name}")

    def test_the_longest_track_names_stay_inside_the_info_panel(self):
        game = self.game
        longest = sorted(game.tracks, key=lambda t: -len(t.name))[:2]
        self.assertTrue(any(len(t.name) >= 17 for t in longest))
        for track in longest:
            self.select(game.tracks.index(track), 1)
            trace = self.render(State.TRACK_SELECT, P2_KEYS)
            rect = next(r for r, m in trace if m == track.name)
            self.assertLessEqual(rect.right, SCREEN.w - MARGIN - 190, track.name)    # leaves room for the status

    def test_prices_are_shown_only_for_the_selected_locked_items(self):
        self.select(5, 4)
        trace = self.render(State.TRACK_SELECT, P1_KEYS)
        prices = [m for _, m in trace if "TICKETS" in m]
        self.assertEqual(sorted(prices), ["LOCKED - 150 TICKETS", "LOCKED - 40 TICKETS"])
        self.select(0, 0)                                                    # everything free: no price at all
        trace = self.render(State.TRACK_SELECT, P1_KEYS)
        self.assertFalse([m for _, m in trace if "TICKETS" in m])
        self.assertIn("UNLOCKED", [m for _, m in trace])

    def test_only_the_selected_track_name_is_drawn(self):
        self.select(3, 2)
        trace = self.render(State.TRACK_SELECT, P1_KEYS)
        names = [m for _, m in trace if m in {t.name for t in self.game.tracks}]
        self.assertEqual(names, [self.game.tracks[3].name])

    def test_scenery_names_and_locked_tags_sit_below_their_thumbnails(self):
        game = self.game
        self.select(0, 4)
        trace = self.render(State.TRACK_SELECT, P1_KEYS)
        rects = game.scenery_gallery.thumbnail_rects()
        for theme, rect in zip(game.themes.themes, rects):
            label = next(r for r, m in trace if m == theme.name)
            self.assertGreaterEqual(label.top, rect.bottom, theme.name)
            self.assertLess(label.width, SCREEN.w / len(rects), theme.name)
        locked = [r for r, m in trace if m == "LOCKED" and r.top > rects[0].bottom]
        self.assertEqual(len(locked), len(rects) - 1)                    # every scenery but the free one
        for rect in rects:
            self.assertTrue(CONTENT.contains(rect.inflate(8, 8)))

    def test_regions_do_not_collide(self):
        game = self.game
        thumbs = game.scenery_gallery.thumbnail_rects()
        lowest = max(r.bottom for r in thumbs) + 23 + 17 + 2                  # the LOCKED tag row, with its outline
        self.assertLess(lowest, FOOTER.top)
        self.assertLess(CONTENT.bottom, FOOTER.top)

    def test_car_select_for_every_car_and_key_set(self):
        game = self.game
        for name, keys in KEY_SETS.items():
            for i in range(len(game.car_menu.catalog)):
                game.car_menu.index = i
                game.player.spec = game.car_menu.selected
                self.assert_clean(self.render(State.CAR_SELECT, keys), f"CAR {i}/{name}")

    def finish_race(self, finished=True):
        game = self.game
        game.mode_index = 0
        game.state = State.MODE_SELECT
        for _ in range(3):
            game.press_enter()
        game.begin_playing()
        if finished:
            game.player.distance = game.road.length * game.manager.laps
        else:
            game.manager.time_left = 0.0
        for _ in range(240):
            game.update(1 / 60, IDLE)
        return game.state

    def test_result_screens_fit(self):
        for finished in (True, False):
            self.setUp()
            state = self.finish_race(finished)
            self.assertIn(state, (State.FINISHED, State.GAME_OVER))
            for name, keys in KEY_SETS.items():
                self.assert_clean(self.render(state, keys), f"{state.name}/{name}")


if __name__ == "__main__":
    unittest.main()
