import os
import random
import unittest
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from cat_minesweeper.game import MineGame
from cat_minesweeper.model import BoardState, MineOutcome


class MineGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_mouse_coordinates_and_flags_work_on_every_grid(self):
        game = MineGame(random.Random(4))
        for index in range(3):
            game.difficulty_index = index
            game.restart()
            rect = game.layout.cell_rect(1, 1)
            self.assertEqual(game.layout.cell_at(rect.center), (1, 1))
            self.assertTrue(game.click(rect.center, 3))
            self.assertTrue(game.board.cells[1][1].flagged)
            self.assertFalse(game.click(rect.center, 1))
            self.assertIsNone(game.layout.cell_at(game.layout.rect.bottomright))
            self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(game.layout.rect))

    def test_pause_blocks_clicks_and_freezes_timer_and_ready_does_not_tick(self):
        game = MineGame(random.Random(4))
        game.confirm()
        game.update(10)
        self.assertEqual(game.board.elapsed, 0)
        game.click(game.layout.cell_rect(0, 0).center, 1)
        game.update(2)
        self.assertEqual(game.board.elapsed, 2)
        game.toggle_pause()
        before = game.board.revealed_count
        self.assertFalse(game.click(game.layout.cell_rect(5, 5).center, 1))
        game.update(5)
        self.assertEqual((game.board.elapsed, game.board.revealed_count), (2, before))

    def test_abandonment_pays_zero_and_winning_result_survives_replay(self):
        game = MineGame(random.Random(4))
        game.confirm()
        game.click(game.layout.cell_rect(0, 0).center, 1)
        self.assertEqual(game.outcome().tickets, 0)
        for y, row in enumerate(game.board.cells):
            for x, cell in enumerate(row):
                if not cell.mine:
                    game.click(game.layout.cell_rect(x, y).center, 1)
        self.assertEqual(game.board.state, BoardState.WON)
        result = game.outcome()
        self.assertEqual(result.tickets, 10)
        game.confirm()
        self.assertEqual(game.board.state, BoardState.READY)
        self.assertEqual(game.outcome(), result)

    def test_all_difficulties_and_end_states_render(self):
        game = MineGame(random.Random(4))
        surface = pygame.Surface((400, 300))
        game.draw(surface)
        for index in range(3):
            game.difficulty_index = index
            game.restart()
            game.draw(surface)
            game.click(game.layout.cell_rect(0, 0).center, 1)
            game.toggle_pause()
            game.draw(surface)
            game.confirm()
            mine = next((x, y) for y, row in enumerate(game.board.cells) for x, c in enumerate(row) if c.mine)
            game.click(game.layout.cell_rect(*mine).center, 1)
            game.draw(surface)

    def test_higher_scoring_loss_cannot_remove_prior_win_tickets(self):
        game = MineGame()
        game.board.outcome = MineOutcome(True, 900, 10, 800)
        game.observe_result()
        game.restart()
        game.board.outcome = MineOutcome(False, 1190, 0, 60)
        game.observe_result()
        self.assertEqual((game.outcome().score, game.outcome().tickets), (1190, 10))
        game.observe_result()
        self.assertEqual(game.outcome().tickets, 10)
