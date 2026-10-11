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


class SolutionCountTests(unittest.TestCase):
    def test_zero_solutions(self):
        # Every region is a single 2-row block pair: two rows share one color -> impossible.
        regions = tuple(tuple([min(y // 2, 7)]*8) for y in range(8))
        self.assertEqual(TerritorySolver.count(regions), 0)
        self.assertFalse(TerritoryGenerator.accept(regions))

    def test_multiple_solutions_stops_at_two(self):
        regions = tuple(tuple([y]*8) for y in range(8))
        self.assertEqual(TerritorySolver.count(regions, limit=2), 2)
        self.assertFalse(TerritoryGenerator.accept(regions))

    def test_unique_solution(self):
        self.assertEqual(TerritorySolver.count(TerritoryGenerator.FALLBACK.regions), 1)
        self.assertTrue(TerritoryGenerator.accept(TerritoryGenerator.FALLBACK.regions))

    def test_solver_matches_game_rules(self):
        for seed in range(20):
            p = TerritoryGenerator(random.Random(seed)).generate()
            cats = {(x, y) for y, x in enumerate(p.solution)}
            self.assertTrue(TerritoryRules.solved(p.regions, cats))

    def test_rejected_candidates_are_regenerated(self):
        gen = TerritoryGenerator(random.Random(1))
        good, calls = gen._candidate, []
        bad = tuple(tuple([y]*8) for y in range(8))
        def fake(size):
            calls.append(1)
            return bad if len(calls) < 3 else good(size)
        gen._candidate = fake
        puzzle = gen.generate()
        self.assertEqual(len(calls), 3)
        self.assertFalse(gen.used_fallback)
        self.assertEqual(TerritorySolver.count(puzzle.regions), 1)

    def test_fallback_after_attempt_limit(self):
        gen = TerritoryGenerator(max_generations=3)
        gen._candidate = lambda size: tuple(tuple([y]*8) for y in range(8))
        puzzle = gen.generate()
        self.assertTrue(gen.used_fallback)
        self.assertIs(puzzle, TerritoryGenerator.FALLBACK)

    def test_generation_performance(self):
        import time
        start = time.time()
        for seed in range(50):
            TerritoryGenerator(random.Random(seed)).generate()
        self.assertLess((time.time() - start) / 50, 0.5)
