import random
import unittest
from cat_territory.model import TerritoryBoard
from cat_territory.solver import TerritorySolver


class RecoveryTests(unittest.TestCase):
    def test_legal_dead_end_warns_without_punishing_and_undo_recovers(self):
        board = TerritoryBoard(rng=random.Random(9))
        wrong = next((x,y) for y in range(8) for x in range(8) if x != board.puzzle.solution[y])
        self.assertTrue(board.toggle_cat(*wrong))
        self.assertEqual(board.hearts,3)
        self.assertIn('CATS BLOCK',board.completion_status)
        self.assertTrue(board.undo())
        self.assertEqual(board.completion_status,'OK')
        for y,x in enumerate(board.puzzle.solution):self.assertTrue(board.toggle_cat(x,y))
        self.assertTrue(board.outcome.won)

    def test_marks_do_not_change_answer_and_can_be_cleared(self):
        board = TerritoryBoard(rng=random.Random(9))
        board.toggle_mark(board.puzzle.solution[0],0)
        self.assertIn('MARKS BLOCK',board.completion_status)
        self.assertTrue(board.clear_marks())
        self.assertEqual(board.completion_status,'OK')
        self.assertEqual(board.hearts,3)

    def test_every_solution_prefix_can_complete_for_100_seeds(self):
        for seed in range(100):
            board = TerritoryBoard(rng=random.Random(seed))
            for y,x in enumerate(board.puzzle.solution):
                self.assertTrue(board.toggle_cat(x,y))
                self.assertEqual(board.completion_status,'OK')
                self.assertTrue(TerritorySolver.solutions(board.regions,cats=board.cats))

    def test_conflicting_fixed_cats_and_all_marks_are_unsatisfiable(self):
        board = TerritoryBoard(rng=random.Random(9))
        self.assertFalse(TerritorySolver.solutions(board.regions,cats={(0,0),(2,0)}))
        self.assertFalse(TerritorySolver.solutions(board.regions,marks={(x,y) for y in range(8) for x in range(8)}))
