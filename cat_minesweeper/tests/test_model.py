import random
import unittest
from cat_minesweeper.model import *


class MinesweeperRulesTests(unittest.TestCase):
    def test_first_click_and_neighbors_are_safe_on_every_difficulty(self):
        for difficulty in DIFFICULTIES:
            for point in ((0, 0), (difficulty.size // 2, difficulty.size // 2),
                          (difficulty.size - 1, difficulty.size - 1)):
                board = MineBoard(difficulty, random.Random(7))
                board.reveal(*point)
                self.assertFalse(board.cells[point[1]][point[0]].mine)
                self.assertEqual(board.cells[point[1]][point[0]].adjacent, 0)
                self.assertEqual(sum(c.mine for row in board.cells for c in row), difficulty.mines)
                self.assertGreater(board.revealed_count, 1)

    def test_adjacent_counts_are_correct_and_generation_is_seeded(self):
        a, b = MineBoard(rng=random.Random(9)), MineBoard(rng=random.Random(9))
        a.reveal(2, 2)
        b.reveal(2, 2)
        self.assertEqual(a.cells, b.cells)
        for y, row in enumerate(a.cells):
            for x, cell in enumerate(row):
                self.assertEqual(cell.adjacent, sum(a.cells[ny][nx].mine for nx, ny in a.neighbors(x, y)))

    def test_flags_block_reveal_and_do_not_start_timer(self):
        board = MineBoard()
        board.toggle_flag(0, 0)
        self.assertFalse(board.reveal(0, 0))
        board.update(10)
        self.assertEqual(board.elapsed, 0)
        board.toggle_flag(0, 0)
        self.assertTrue(board.reveal(0, 0))
        self.assertFalse(board.toggle_flag(0, 0))

    def test_loss_freezes_time_and_result_and_pays_no_tickets(self):
        board = MineBoard(rng=random.Random(5))
        board.reveal(2, 2)
        board.update(3)
        mine = next((x, y) for y, row in enumerate(board.cells) for x, c in enumerate(row) if c.mine)
        board.reveal(*mine)
        self.assertEqual(board.state, BoardState.LOST)
        result = board.outcome
        board.update(100)
        self.assertIs(board.outcome, result)
        self.assertEqual(result.elapsed, 3)
        self.assertEqual(result.tickets, 0)
        self.assertFalse(board.reveal(0, 0))

    def test_win_requires_all_safe_cells_not_correct_flags(self):
        for difficulty in DIFFICULTIES:
            board = MineBoard(difficulty, random.Random(2))
            board.reveal(0, 0)
            board.update(5)
            for y, row in enumerate(board.cells):
                for x, cell in enumerate(row):
                    if not cell.mine:
                        board.reveal(x, y)
            self.assertEqual(board.state, BoardState.WON)
            self.assertEqual(board.outcome.tickets, difficulty.win_tickets)
            self.assertGreater(board.outcome.score, board.revealed_count * 10)
            self.assertEqual(board.flag_count, 0)

    def test_flagged_safe_cells_are_not_auto_expanded(self):
        board = MineBoard(rng=random.Random(7))
        board.toggle_flag(1, 1)
        board.reveal(2, 2)
        self.assertFalse(board.cells[1][1].revealed)
        self.assertTrue(board.cells[1][1].flagged)

    def test_invalid_clicks_and_invalid_board_are_rejected(self):
        board = MineBoard()
        self.assertFalse(board.reveal(-1, 0))
        self.assertFalse(board.toggle_flag(6, 0))
        self.assertEqual(board.state, BoardState.READY)
        with self.assertRaises(ValueError):
            MineBoard(Difficulty(6, 30, "BAD", 0))
