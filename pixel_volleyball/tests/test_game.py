import os
import unittest
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from pixel_volleyball.game import VolleyGame
from pixel_volleyball.model import MatchState


class VolleyLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_completed_results_are_independent_and_replays_do_not_sum_rewards(self):
        game = VolleyGame(2)
        self.addCleanup(game.audio.stop)
        game.confirm()
        game.match.award_point(1)
        for _ in range(5):
            game.match.award_point(0)
        game.update(.01)
        self.assertEqual([(r.score, r.tickets) for r in game.best], [(1000, 20), (100, 2)])
        first = tuple(game.best)
        game.observe_result()
        self.assertEqual(tuple(game.best), first)
        game.confirm()
        self.assertEqual(game.match.state, MatchState.PLAYING)
        self.assertEqual(tuple(game.best), first)

    def test_abandoned_match_gives_no_tickets_and_all_states_render(self):
        game = VolleyGame()
        self.addCleanup(game.audio.stop)
        surface = pygame.Surface((400, 300))
        game.draw(surface)
        game.confirm()
        game.match.award_point(0)
        game.update(.01)
        self.assertEqual(game.best[0].tickets, 0)
        game.draw(surface)
        game.match.toggle_pause()
        game.draw(surface)
        game.confirm()
        for _ in range(5):
            game.match.award_point(1)
        game.update(.01)
        game.draw(surface)
