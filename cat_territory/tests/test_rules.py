import random
import unittest
from cat_territory.model import *
from cat_territory.generator import TerritoryGenerator, TerritoryPuzzle
from cat_territory.solver import TerritorySolver


class TerritoryTests(unittest.TestCase):
    def test_generated_boards_are_solvable_connected_and_have_n_regions(self):
        for size in (6,8,10):
            for seed in range(4):
                puzzle = TerritoryGenerator(random.Random(seed)).generate(size)
                self.assertTrue(TerritorySolver.solutions(puzzle.regions))
                self.assertEqual(set(sum(puzzle.regions,())),set(range(size)))
                for color in range(size):
                    cells = {(x,y) for y,row in enumerate(puzzle.regions) for x,c in enumerate(row) if c == color}
                    pending = [next(iter(cells))]; visited=set()
                    while pending:
                        x,y=pending.pop()
                        if (x,y) in visited: continue
                        visited.add((x,y))
                        pending.extend(p for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if p in cells and p not in visited)
                    self.assertEqual(visited,cells)

    def test_three_invalid_placements_lose_and_removal_is_free(self):
        board = TerritoryBoard(rng=random.Random(4))
        x = board.puzzle.solution[0]
        self.assertTrue(board.toggle_cat(x,0))
        for hearts in (2,1,0):
            self.assertFalse(board.toggle_cat((x+1)%6,0))
            self.assertEqual(board.hearts,hearts)
        self.assertIs(board.state,BoardState.LOST)
        self.assertEqual(board.outcome.tickets,0)
        self.assertFalse(board.toggle_cat(x,0))

    def test_alternate_legal_solution_is_accepted(self):
        regions=tuple(tuple([y]*6) for y in range(6))
        solutions=TerritorySolver.solutions(regions)
        self.assertEqual(len(solutions),2)
        puzzle=TerritoryPuzzle(regions,solutions[0],False)
        board=TerritoryBoard(puzzle=puzzle)
        for y,x in enumerate(solutions[1]):
            self.assertTrue(board.toggle_cat(x,y))
        self.assertIs(board.state,BoardState.WON)
        self.assertEqual(board.hearts,3)
        self.assertEqual(board.outcome.tickets,10)

    def test_adjacency_row_column_and_region_constraints(self):
        regions=tuple(tuple([y]*6) for y in range(6))
        cats={(2,2)}
        for point in ((0,2),(2,5),(3,3),(1,1)):
            self.assertTrue(TerritoryRules.conflicts(regions,cats,point))
        self.assertFalse(TerritoryRules.conflicts(regions,cats,(4,3)))

    def test_unique_flag_matches_solver_and_generation_is_deterministic(self):
        a=TerritoryGenerator(random.Random(5)).generate(6)
        b=TerritoryGenerator(random.Random(5)).generate(6)
        self.assertEqual(a,b)
        self.assertEqual(a.unique,len(TerritorySolver.solutions(a.regions))==1)

    def test_region_rule_and_diagonals_are_independent_of_rows_columns(self):
        regions=[[y]*6 for y in range(6)]
        regions[3][2]=regions[0][0]
        self.assertTrue(TerritoryRules.conflicts(regions,{(0,0)},(2,3)))
        self.assertTrue(TerritoryRules.conflicts(regions,{(0,0)},(1,1)))
        # Far diagonals are legal: this is adjacent-cat logic, not chess queens.
        self.assertFalse(TerritoryRules.conflicts(regions,{(0,0)},(3,3)))
