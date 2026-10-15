"""Starfall Assault flow: title, how to play, pause, restart, game over and the per-session payout."""
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from galaxy_defender.game import GalaxyGame, Screen

DT = 1 / 60


class Recorder:
    def __init__(self):
        self.names = []

    def play(self, name):
        self.names.append(name)


def playing(seed=1):
    game = GalaxyGame(random.Random(seed))
    game.act("confirm")                               # START
    game.run.banner = 0.001
    game.update(0.01)
    return game


def lose(game):
    game.run.hp = 1
    game.run.invuln = 0
    game.run.damage()
    game.update(DT)


class FlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def test_title_has_start_and_how_to_play(self):
        game = GalaxyGame()
        self.assertEqual(game.screen, Screen.TITLE)
        self.assertEqual(game.menu(), ("START", "HOW TO PLAY"))
        game.act("down")
        game.act("confirm")
        self.assertEqual(game.screen, Screen.HOWTO)
        game.act("back")
        self.assertEqual(game.screen, Screen.TITLE)
        game.act("up")
        game.act("confirm")
        self.assertEqual(game.screen, Screen.PLAYING)

    def test_escape_on_the_title_leaves(self):
        game = GalaxyGame()
        game.act("back")
        self.assertTrue(game.wants_exit)

    def test_menu_cursor_wraps(self):
        game = GalaxyGame()
        game.act("up")
        self.assertEqual(game.cursor, 1)
        game.act("down")
        self.assertEqual(game.cursor, 0)

    def test_escape_pauses_and_resumes(self):
        game = playing()
        game.act("back")
        self.assertEqual(game.screen, Screen.PAUSED)
        game.act("back")
        self.assertEqual(game.screen, Screen.PLAYING)

    def test_paused_game_does_not_advance(self):
        game = playing()
        game.act("back")
        run, snapshot = game.run, (game.run.x, game.run.time, [e.x for e in game.run.enemies])
        for _ in range(60):
            game.update(DT, move=1, fire=True)
        self.assertEqual((run.x, run.time, [e.x for e in run.enemies]), snapshot)
        self.assertEqual(run.player_bolts, [])

    def test_pause_menu_has_resume_restart_and_return(self):
        game = playing()
        game.pause()
        self.assertEqual(game.menu(), ("RESUME", "RESTART", "RETURN TO LOBBY"))
        game.act("confirm")                            # RESUME
        self.assertEqual(game.screen, Screen.PLAYING)

    def test_restart_fully_resets_the_run_but_not_the_records(self):
        game = playing()
        game.saved_score, game.saved_wave = 900, 7
        game.run.score, game.run.wave, game.run.hp = 400, 4, 1
        game.run.shield, game.run.power["rapid"], game.run.combo = True, 5, 7
        game.run.enemy_bolts.append(object())
        old = game.run
        game.pause()
        game.act("down")
        game.act("confirm")                            # RESTART
        run = game.run
        self.assertIsNot(run, old)
        self.assertEqual((run.score, run.wave, run.hp, run.shield, run.power["rapid"], run.combo), (0, 1, 3, False, 0, 0))
        self.assertEqual((run.enemy_bolts, run.enemies, run.powerups, run.player_bolts), ([], [], [], []))
        self.assertEqual(game.screen, Screen.PLAYING)
        self.assertEqual((game.saved_score, game.saved_wave), (900, 7))
        self.assertEqual(game.best.score, 400)         # the abandoned run still counts, once

    def test_return_to_lobby_from_pause(self):
        game = playing()
        game.pause()
        game.act("down")
        game.act("down")
        game.act("confirm")
        self.assertTrue(game.wants_exit)

    def test_game_over_screen_and_menu(self):
        game = playing()
        game.run.score = 120
        lose(game)
        self.assertEqual(game.screen, Screen.OVER)
        self.assertEqual(game.menu(), ("RETRY", "RETURN TO LOBBY"))
        surface = pygame.Surface((400, 300))
        game.draw(surface)                              # every screen must render
        game.act("confirm")
        self.assertEqual(game.screen, Screen.PLAYING)
        self.assertFalse(game.run.over)

    def test_every_screen_draws(self):
        game = GalaxyGame()
        surface = pygame.Surface((400, 300))
        game.draw(surface)
        game.act("down")
        game.act("confirm")
        game.draw(surface)
        game.act("back")
        game.act("up")
        game.act("confirm")
        game.run.wave = 5
        game.run.banner = 0.001
        for _ in range(120):
            game.update(DT, fire=True)
            game.draw(surface)
        game.pause()
        game.draw(surface)

    def test_sounds_are_triggered(self):
        game = GalaxyGame(random.Random(1), audio=Recorder())
        game.act("confirm")
        game.run.banner = 0.001
        game.update(0.01)
        game.update(DT, fire=True)
        self.assertIn("laser", game.audio.names)


class RecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def test_session_pays_only_the_best_run(self):
        game = playing()
        game.run.score, game.run.waves_cleared, game.run.reached = 3000, 5, 6
        lose(game)
        first = game.best
        self.assertGreater(first.tickets, 0)
        game.act("confirm")                              # RETRY
        game.run.score, game.run.waves_cleared = 200, 0
        lose(game)
        self.assertEqual(game.best, first)               # a worse run cannot lower it, nor add to it
        game.run.score = 0

    def test_observing_twice_is_harmless(self):
        game = playing()
        game.run.score = 700
        lose(game)
        best = game.best
        for _ in range(5):
            game.observe()
        self.assertEqual(game.best, best)

    def test_quitting_mid_run_cashes_out_once(self):
        game = playing()
        game.run.score, game.run.reached = 1000, 3
        game.pause()
        game.act("down")
        game.act("down")
        game.act("confirm")
        best = game.best
        self.assertEqual(best.score, 1000)
        game.observe()
        game.leave()
        self.assertEqual(game.best, best)

    def test_unscored_run_pays_nothing(self):
        game = playing()
        game.leave()
        self.assertFalse(game.has_played)
        self.assertEqual(game.best.tickets, 0)

    def test_personal_best_and_new_record_flag(self):
        game = playing()
        game.saved_score = 500
        game.run.score = 300
        lose(game)
        self.assertEqual(game.personal_best, 500)
        self.assertFalse(game.new_record)
        game.act("confirm")
        game.run.score = 800
        lose(game)
        self.assertEqual(game.personal_best, 800)
        self.assertTrue(game.new_record)

    def test_session_wave_is_the_highest_reached(self):
        game = playing()
        game.run.score, game.run.reached = 50, 4
        lose(game)
        game.act("confirm")
        game.run.score, game.run.reached = 60, 2
        lose(game)
        self.assertEqual(game.session_wave, 4)

    def test_reduced_effects_toggle_removes_shake_and_flash(self):
        game = playing()
        game.toggle_reduced()
        game.fx.hit_shake()
        game.fx.pulse()
        self.assertEqual((game.fx.shake, game.fx.flash, game.fx.offset()), (0.0, 0.0, (0, 0)))
        game.new_run()
        self.assertTrue(game.fx.reduced)                # the choice survives a restart

    def test_particles_are_capped(self):
        game = playing()
        for _ in range(100):
            game.fx.burst(100, 100, "boss", True)
        self.assertLessEqual(len(game.fx.particles), 220)


if __name__ == "__main__":
    unittest.main()
