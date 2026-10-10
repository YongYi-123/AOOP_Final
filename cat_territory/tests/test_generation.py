import json
import random
from pathlib import Path
import unittest
from cat_territory.generator import TerritoryGenerator
from cat_territory.solver import TerritorySolver
from cat_territory.logic import TerritoryLogic
from cat_territory.model import TerritoryRules, TerritoryBoard


class VerifiedGenerationTests(unittest.TestCase):
    def test_one_thousand_seeds_unique_logical_connected(self):
        failures = []
        for seed in range(1000):
            try:
                puzzle = TerritoryGenerator(random.Random(seed)).generate()
                solutions = TerritorySolver.solutions(puzzle.regions)
                self.assertEqual(len(solutions),1)
                logical = TerritoryLogic.solve(puzzle.regions)
                self.assertTrue(logical.solved)
                self.assertTrue(TerritoryRules.solved(puzzle.regions,set(logical.cats)))
                self.assertEqual(tuple(x for x,y in sorted(logical.cats,key=lambda p:p[1])),solutions[0])
                for color in range(8):
                    self.assertTrue(TerritoryGenerator.connected(puzzle.regions,color))
            except Exception as exc:
                failures.append({'seed':seed,'error':repr(exc)})
        path = Path('/tmp/aoop-territory-generation-failures.json')
        path.write_text(json.dumps(failures,indent=2))
        self.assertEqual(failures,[],f'failed seeds saved in {path}')

    def test_unforced_legal_move_never_costs_heart(self):
        board = TerritoryBoard(rng=random.Random(8))
        # Deliberately pick a legal first cat outside the unique final answer.
        wrong = next((x,y) for y in range(8) for x in range(8) if board.puzzle.solution[y] != x)
        self.assertTrue(board.toggle_cat(*wrong))
        self.assertEqual(board.hearts,3)

    def test_logic_does_not_guess_on_ambiguous_row_regions(self):
        regions = tuple(tuple([y]*8) for y in range(8))
        self.assertFalse(TerritoryLogic.solve(regions).solved)
        self.assertEqual(len(TerritorySolver.solutions(regions)),2)

    def test_rejects_removed_sizes(self):
        for size in (6,10):
            with self.assertRaises(ValueError):
                TerritoryGenerator().generate(size)
