"""NEON CAT MAZE flow: title, how to play, pause, restart, game over, results and the per-session payout, plus the
layout of every screen (nothing clipped, nothing overlapping) and a render of every screen without errors."""
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from neon_cat_maze import config as cfg
from neon_cat_maze.game import CatMazeGame, Screen
from neon_cat_maze.settlement import tickets_for
from neon_cat_maze.tests.helpers import DT
from neon_cat_maze.tests.autopilot import steer_for

CANVAS = (cfg.FIELD_W, cfg.FIELD_H)


class Recorder:
    def __init__(self):
        self.names = []

    def play(self, name):
        self.names.append(name)


def started(seed=1, audio=None):
    game = CatMazeGame(random.Random(seed), audio=audio)
    game.act("confirm")                               # START
    game.update(cfg.READY_SECONDS + 0.1)
    for _ in range(int(cfg.READY_SECONDS / DT) + 5):
        game.update(DT)
    return game


def tick(game, seconds):
    for _ in range(round(seconds / DT)):
        game.update(DT)


def die(game):
    """Lose every life, one touch at a time."""
    while not game.run.over:
        run = game.run
        if run.phase == "run":
            run.invulnerable = 0.0
            robot = run.robots[1]
            robot.mode, robot.fright = "active", False
            robot.place(run.cat.nearest_tile())
        tick(game, 0.1)


class FlowTests(unittest.TestCase):
    def test_title_howto_and_start(self):
        game = CatMazeGame(random.Random(1))
        self.assertEqual(game.screen, Screen.TITLE)
        game.act("down")
        game.act("confirm")
        self.assertEqual(game.screen, Screen.HOWTO)
        game.act("confirm")
        self.assertEqual((game.screen, game.cursor), (Screen.TITLE, 1))
        game.act("up")
        game.act("confirm")
        self.assertEqual(game.screen, Screen.PLAYING)
        self.assertEqual(game.run.phase, "ready")

    def test_menus_wrap_and_back_leaves_from_the_title(self):
        game = CatMazeGame(random.Random(1))
        game.act("up")
        self.assertEqual(game.cursor, 1)
        game.act("down")
        self.assertEqual(game.cursor, 0)
        game.act("back")
        self.assertTrue(game.wants_exit)

    def test_directions_steer_only_while_playing(self):
        game = CatMazeGame(random.Random(1))
        game.act("right")                             # on the title: just a menu key
        self.assertEqual(game.run.cat.buffer, (0, 0))
        game = started()
        game.act("right")
        self.assertEqual(game.run.cat.buffer, (1, 0))
        tick(game, 0.5)
        self.assertGreater(game.run.cat.pos[0], game.run.maze.start[0])

    def test_pause_freezes_everything_and_resume_continues(self):
        game = started()
        game.steer("right")
        tick(game, 0.3)
        game.pause()
        self.assertEqual(game.screen, Screen.PAUSED)
        self.assertTrue(game.paused)
        before = (game.run.cat.pos, game.run.time, [r.pos for r in game.run.robots])
        tick(game, 3.0)
        self.assertEqual(before, (game.run.cat.pos, game.run.time, [r.pos for r in game.run.robots]))
        game.act("back")                              # ESC resumes
        self.assertEqual(game.screen, Screen.PLAYING)
        self.assertFalse(game.paused)
        tick(game, 0.3)
        self.assertGreater(game.run.cat.pos[0], before[0][0])

    def test_pause_menu_resume_restart_and_return(self):
        game = started()
        game.steer("right")
        tick(game, 1.0)
        score = game.run.score
        self.assertGreater(score, 0)
        game.pause()
        game.act("confirm")                           # RESUME
        self.assertEqual(game.screen, Screen.PLAYING)
        game.pause()
        game.act("down")
        game.act("confirm")                           # RESTART
        self.assertEqual((game.screen, game.run.score, game.run.phase), (Screen.PLAYING, 0, "ready"))
        self.assertEqual(game.run.lives, cfg.START_LIVES)
        game.pause()
        game.act("up")
        game.act("confirm")                           # RETURN TO LOBBY (up from RESUME wraps to the last item)
        self.assertTrue(game.wants_exit)

    def test_pause_is_not_possible_during_the_game_over_banner(self):
        game = started()
        die(game)
        game.pause()
        self.assertNotEqual(game.screen, Screen.PAUSED)

    def test_game_over_banner_then_results_then_play_again(self):
        game = started()
        game.steer("right")
        tick(game, 1.5)
        die(game)
        self.assertEqual((game.screen, game.run.phase), (Screen.PLAYING, "over"))
        tick(game, cfg.OVER_SECONDS + 0.2)
        self.assertEqual(game.screen, Screen.OVER)
        game.act("confirm")                           # PLAY AGAIN
        self.assertEqual((game.screen, game.run.lives, game.run.phase), (Screen.PLAYING, cfg.START_LIVES, "ready"))

    def test_confirm_skips_the_game_over_banner_after_a_moment(self):
        game = started()
        die(game)
        game.act("confirm")
        self.assertEqual(game.screen, Screen.PLAYING)                         # too soon: still the banner
        tick(game, 0.5)
        game.act("confirm")
        self.assertEqual(game.screen, Screen.OVER)

    def test_results_menu_returns_to_the_lobby(self):
        game = started()
        die(game)
        tick(game, cfg.OVER_SECONDS + 0.2)
        game.act("down")
        game.act("confirm")
        self.assertTrue(game.wants_exit)

    def test_confirm_skips_the_level_clear_panel(self):
        game = started()
        game.run.fish.clear()
        tick(game, 0.1)
        self.assertEqual(game.run.phase, "clear")
        game.act("confirm")
        self.assertEqual(game.run.phase, "clear")                              # not for the first second
        tick(game, cfg.CLEAR_SKIP_AFTER)
        game.act("confirm")
        self.assertEqual((game.run.level, game.run.phase), (2, "ready"))


class SessionBestTests(unittest.TestCase):
    def test_nothing_is_paid_for_a_run_that_scored_nothing(self):
        game = started()
        die(game)
        game.observe()
        self.assertFalse(game.has_played)
        self.assertEqual(game.best.tickets, 0)

    def test_the_best_run_of_the_session_is_the_one_kept(self):
        game = started()
        game.run.score, game.run.levels_cleared, game.run.level = 3000, 2, 3
        game.observe()
        best = game.best
        self.assertGreater(best.tickets, 0)
        game.new_run()
        game.run.score = 100
        game.observe()
        self.assertEqual(game.best, best)             # a worse run never replaces it
        game.new_run()
        game.run.score, game.run.levels_cleared = 9000, 4
        game.observe()
        self.assertGreater(game.best.score, best.score)
        self.assertGreater(game.best.tickets, best.tickets)

    def test_folding_a_run_in_again_never_double_counts_and_only_ever_raises_records(self):
        game = started()
        game.run.score = 1000
        game.observe()
        first = game.best
        game.observe()
        game.observe()
        self.assertEqual((game.best, game.session_score), (first, 1000))
        game.run.score = 1500                         # the same run kept going after an early fold: not lost
        game.observe()
        self.assertEqual(game.session_score, 1500)

    def test_a_record_score_survives_a_later_run_that_earns_more_tickets(self):
        """3000 points and no level cleared pays 6 tickets; two cleared levels for 1100 points pay 8. The tickets of the
        second run are paid, but the 3000 must still be what is reported as the score record."""
        game = started()
        game.run.score, game.run.levels_cleared, game.run.level = 3000, 0, 1
        game.observe()
        game.new_run()
        game.run.score, game.run.levels_cleared, game.run.level = 1100, 2, 3
        game.observe()
        self.assertEqual(game.best.tickets, max(tickets_for(3000, 0), tickets_for(1100, 2)))
        self.assertGreater(tickets_for(1100, 2), tickets_for(3000, 0))
        self.assertEqual(game.session_score, 3000)
        self.assertEqual(game.session_level, 3)

    def test_personal_best_and_new_record(self):
        game = started()
        game.saved_score = 500
        game.run.score = 400
        self.assertFalse(game.new_record)
        self.assertEqual(game.personal_best, 500)
        game.run.score = 800
        self.assertTrue(game.new_record)
        self.assertEqual(game.personal_best, 800)

    def test_leaving_folds_the_progress_in(self):
        game = started()
        game.run.score = 700
        game.leave()
        self.assertTrue(game.wants_exit)
        self.assertEqual(game.best.score, 700)


class SoundTests(unittest.TestCase):
    def test_every_event_has_its_own_sound(self):
        rec = Recorder()
        game = started(audio=rec)
        run = game.run
        run.steer((1, 0))
        tick(game, 0.6)
        self.assertIn("maze_fish", rec.names)
        self.assertIn("maze_fish_b", rec.names)                               # two alternating pitches
        run.cat.place((18, 13))
        run.fish.add((19, 13))
        run.steer((1, 0))
        tick(game, 0.3)
        self.assertIn("maze_catnip", rec.names)
        robot = run.robots[0]
        robot.mode, robot.fright = "active", True
        robot.place(run.cat.nearest_tile())
        tick(game, 0.05)
        self.assertIn("maze_disable", rec.names)
        run.catnip_left = 0.01
        tick(game, 0.1)
        self.assertIn("maze_catnip_end", rec.names)
        run.fish.clear()
        run.fish.add((3, 3))
        run.fish.discard((3, 3))
        tick(game, 0.1)
        self.assertIn("maze_clear", rec.names)
        game = started(audio=rec)
        rec.names.clear()
        die(game)
        self.assertIn("maze_life", rec.names)
        self.assertIn("maze_over", rec.names)

    def test_golden_fish_sounds(self):
        rec = Recorder()
        game = started(audio=rec)
        run = game.run
        for tile in sorted(run.fish)[:int(run.fish_total * 0.4)]:
            run.fish.discard(tile)
        tick(game, 0.1)
        self.assertIn("maze_golden_spawn", rec.names)
        run.cat.place(run.golden[0])
        tick(game, 0.05)
        self.assertIn("maze_golden", rec.names)

    def test_menu_navigation_uses_the_shared_click_sound(self):
        rec = Recorder()
        game = CatMazeGame(random.Random(1), audio=rec)
        game.act("down")
        game.act("up")
        self.assertEqual(rec.names, ["confirm", "confirm"])

    def test_it_is_silent_without_an_audio_bus(self):
        game = started()
        game.run.steer((1, 0))
        tick(game, 1.0)                               # must simply not fail


class LayoutTests(unittest.TestCase):
    """Every screen draws without error and every piece of text fits the canvas without touching other text."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def screens(self):
        """Yield (name, game) for each distinct screen, mid-flight."""
        game = CatMazeGame(random.Random(1))
        yield "title", game
        game.act("down")
        game.act("confirm")
        yield "howto", game
        game.act("confirm")
        game.act("up")
        game.act("confirm")
        yield "ready", game
        tick(game, cfg.READY_SECONDS + 0.2)
        game.steer("right")
        tick(game, 2.5)
        yield "playing", game
        run = game.run
        run.cat.place((19, 13))
        run.fish.add((19, 13))
        tick(game, 0.1)
        for r in run.robots:
            r.mode, r.fright = "active", True
        tick(game, 0.5)
        yield "catnip", game
        run.catnip_left = 1.0
        yield "catnip-warning", game
        game.pause()
        yield "paused", game
        game.resume()
        run.golden = ((10, 9), 6.0)
        run.fish_total, run.lives = 999, 5
        yield "golden-5-lives", game
        run.fish.clear()
        tick(game, 1.5)
        yield "clear", game
        tick(game, cfg.CLEAR_SECONDS)
        yield "level2", game
        die(game)
        yield "gameover", game
        tick(game, cfg.OVER_SECONDS + 0.2)
        game.run.score = 123456
        yield "results", game

    def test_every_screen_renders(self):
        for name, game in self.screens():
            canvas = pygame.Surface(CANVAS)
            game.draw(canvas)
            colours = {tuple(canvas.get_at((x, y)))[:3] for x in range(0, 400, 7) for y in range(0, 300, 7)}
            self.assertGreater(len(colours), 6, name)

    def test_text_fits_the_canvas_and_never_overlaps(self):
        for name, game in self.screens():
            game.renderer.record = []
            canvas = pygame.Surface(CANVAS)
            game.draw(canvas)
            rects = game.renderer.record
            game.renderer.record = None
            self.assertTrue(rects, name)
            bounds = pygame.Rect(0, 0, *CANVAS)
            for text, rect in rects:
                self.assertTrue(bounds.contains(rect), f"{name}: {text!r} {rect} leaves the canvas")
            for i, (a, ra) in enumerate(rects):
                for b, rb in rects[i + 1:]:
                    self.assertFalse(ra.colliderect(rb), f"{name}: {a!r} {ra} overlaps {b!r} {rb}")

    def test_the_spectator_tag_corner_stays_clear_of_the_footer(self):
        """The lobby puts 'P2 NAME - SPECTATING' in the bottom-right corner (~140 px wide)."""
        for name, game in self.screens():
            if name not in ("playing", "catnip", "ready", "title"):
                continue
            game.renderer.record = []
            game.draw(pygame.Surface(CANVAS))
            rects = game.renderer.record
            game.renderer.record = None
            tag = pygame.Rect(cfg.FIELD_W - 150, cfg.FIELD_H - 14, 150, 14)
            for text, rect in rects:
                self.assertFalse(rect.colliderect(tag), f"{name}: {text!r} runs into the spectator tag")

    def test_the_hud_shows_score_lives_level_fish_and_the_catnip_timer(self):
        for name, game in self.screens():
            if name != "catnip":
                continue
            game.renderer.record = []
            game.draw(pygame.Surface(CANVAS))
            labels = " | ".join(t for t, _ in game.renderer.record)
            game.renderer.record = None
            for needle in ("SCORE", "LEVEL 1", "FISH LEFT", "LIVES", "CATNIP POWER"):
                self.assertIn(needle, labels)

    def test_it_looks_right_at_the_common_window_sizes(self):
        """The canvas is scaled as a whole by the lobby; check the picture survives 800x600, 1280x720 and 1920x1080."""
        game = started()
        game.steer("right")
        tick(game, 1.0)
        canvas = pygame.Surface(CANVAS)
        game.draw(canvas)
        for size in ((800, 600), (1280, 720), (1920, 1080)):
            scale = min(size[0] // CANVAS[0], size[1] // CANVAS[1])
            scaled = pygame.transform.scale(canvas, (CANVAS[0] * scale, CANVAS[1] * scale))
            self.assertGreaterEqual(scaled.get_width(), 800)
            self.assertEqual(scaled.get_width() % CANVAS[0], 0)                # whole pixels only: crisp, never blurred
            self.assertLessEqual(scaled.get_width(), size[0])
            self.assertLessEqual(scaled.get_height(), size[1])

    def test_reduced_effects_toggle_changes_nothing_in_the_rules(self):
        a, b = started(seed=5), started(seed=5)
        b.toggle_reduced()
        for game in (a, b):
            game.steer("right")
            tick(game, 5.0)
        self.assertEqual((a.run.score, a.run.cat.pos), (b.run.score, b.run.cat.pos))

    def test_a_full_autopilot_run_draws_every_frame(self):
        game = started(seed=2)
        canvas = pygame.Surface(CANVAS)
        for i in range(60 * 20):
            d = steer_for(game.run)
            if d:
                game.steer(d)
            game.update(DT)
            if i % 20 == 0:
                game.draw(canvas)


if __name__ == "__main__":
    unittest.main()
