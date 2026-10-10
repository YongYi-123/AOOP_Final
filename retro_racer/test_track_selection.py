import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import Game
from race import State
from modes import GameMode


class TrackSelectionTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.addCleanup(self.game.audio.stop_engine)
        self.game.press_enter()
        self.game.press_enter()

    def test_each_selected_route_rebuilds_all_geometry_dependents(self):
        game = self.game
        for index in range(len(game.tracks)):
            self.assertEqual(game.track_index, index)
            self.assertEqual(game.road.route.key, game.tracks[index].key)
            manager = game.managers[GameMode.COMPETITIVE]
            self.assertIs(manager.road, game.road)
            self.assertIs(game.traffic.road, game.road)
            self.assertIs(manager.field.road, game.road)
            self.assertEqual(manager.field.length, game.road.length)
            self.assertEqual(manager.checkpoints, game.road.checkpoint_z)
            game.menu_move(1)

    def test_cancel_preview_restores_confirmed_route_and_scenery(self):
        game = self.game
        original = game.road.route
        theme = game.theme
        game.menu_move(1)
        game.menu_move(1, horizontal=True)
        self.assertNotEqual(game.road.route, original)
        game.back()
        self.assertEqual(game.state, State.MODE_SELECT)
        self.assertIs(game.road.route, original)
        self.assertIs(game.theme, theme)

    def test_scenery_can_change_without_changing_route(self):
        game = self.game
        original = game.road
        game.menu_move(1, horizontal=True)
        self.assertIs(game.road, original)

    def test_confirm_replay_and_finish_work_for_each_circuit(self):
        game = self.game
        for track in game.tracks:
            game.track = track
            game.apply_look()
            game.state = State.TRACK_SELECT
            game.press_enter()
            game.press_enter()
            self.assertEqual(game.state, State.COUNTDOWN)
            self.assertIs(game.selected_track, track)
            game.begin_playing()
            game.player.distance = game.road.length * game.manager.laps
            game.update(1 / 60, {"accelerate": False, "brake": False, "steer": 0})
            self.assertEqual(game.state, State.FINISHED)
            self.assertIn("score", game.manager.result)
            game.press_enter()
            self.assertEqual(game.state, State.COUNTDOWN)
            self.assertEqual(game.road.route.key, track.key)
