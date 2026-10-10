import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from game import Game, IDLE
from race import State
from modes import GameMode


class MiniMapIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.addCleanup(self.game.audio.stop_engine)

    def key(self, key):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))

    def test_m_toggles_map_and_n_only_toggles_audio(self):
        game = self.game
        muted = game.audio.muted
        self.key(pygame.K_m)
        self.assertFalse(game.minimap.visible)
        self.assertEqual(game.audio.muted, muted)
        self.key(pygame.K_n)
        self.assertNotEqual(game.audio.muted, muted)
        self.assertFalse(game.minimap.visible)

    def test_toggle_while_paused_and_restart_preserve_preference(self):
        game = self.game
        game.start_race()
        game.set_paused(True)
        self.key(pygame.K_m)
        self.assertTrue(game.paused)
        game.start_race()
        self.assertFalse(game.minimap.visible)
        self.key(pygame.K_m)
        self.assertTrue(game.minimap.visible)

    def test_route_switch_and_all_game_screens_render(self):
        game = self.game
        for track in game.tracks:
            game.track = track
            game.apply_look()
            self.assertIs(game.minimap.route, game.road.route)
            game.state = State.TRACK_SELECT
            game.render()
            game.start_race()
            game.render()
            game.begin_playing()
            game.render()
            self.assertEqual(len(game.manager.field.racers), 5)

    def test_live_positions_move_and_pause_freezes_them(self):
        game = self.game
        game.start_race()
        game.begin_playing()
        racers = [game.player] + game.manager.field.racers
        game.player.speed = game.player.max_speed
        initial = [game.minimap.marker_position(r) for r in racers]
        game.update(0.1, IDLE)
        moved = [game.minimap.marker_position(r) for r in racers]
        self.assertNotEqual(initial[0], moved[0])
        self.assertNotEqual(initial[1:], moved[1:])
        game.set_paused(True)
        game.update(0.1, IDLE)
        self.assertEqual([game.minimap.marker_position(r) for r in racers], moved)

    def test_endless_map_renders_without_ai_race_field(self):
        game = self.game
        game.mode = GameMode.ENDLESS
        game.start_race()
        game.begin_playing()
        game.render()
