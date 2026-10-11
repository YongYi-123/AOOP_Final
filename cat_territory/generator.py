"""Connected 8x8 puzzles verified by independent search and logical deduction."""
from dataclasses import dataclass
import random
from .solver import TerritorySolver
from .logic import TerritoryLogic


@dataclass(frozen=True)
class TerritoryPuzzle:
    regions: tuple
    solution: tuple
    unique: bool


class TerritoryGenerator:
    # Verified offline: exactly one solution, connected regions, logically solvable.
    FALLBACK = TerritoryPuzzle(
        ((7,7,1,7,0,0,0,7),(7,1,1,7,0,7,7,7),(7,7,7,7,0,7,2,2),(7,5,3,7,7,7,2,2),
         (5,5,3,3,7,7,4,7),(5,5,5,5,7,7,7,7),(5,7,7,6,7,7,7,7),(7,7,7,7,7,7,7,7)),
        (4,1,7,2,6,0,3,5), True)

    def __init__(self, rng=None, attempts=80, max_generations=25):
        self.rng = rng or random.Random()
        self.attempts = attempts
        self.max_generations = max_generations
        self.used_fallback = False

    @classmethod
    def accept(cls, regions):
        """True only if the board has exactly one solution under the game rules."""
        return (TerritorySolver.count(regions, limit=2) == 1
                and all(cls.connected(regions, c) for c in range(len(regions))))

    def _placement(self, size):
        def search(chosen):
            if len(chosen) == size:
                return chosen
            candidates = sorted(set(range(size)) - set(chosen))
            self.rng.shuffle(candidates)
            for column in candidates:
                if chosen and abs(column-chosen[-1]) <= 1:
                    continue
                result = search(chosen+[column])
                if result:
                    return result
        return search([])

    @staticmethod
    def connected(grid, color):
        cells = {(x,y) for y,row in enumerate(grid) for x,c in enumerate(row) if c == color}
        if not cells:
            return False
        pending, reached = [next(iter(cells))], set()
        while pending:
            x,y = pending.pop()
            if (x,y) in reached:
                continue
            reached.add((x,y))
            pending.extend(p for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
                           if p in cells and p not in reached)
        return reached == cells

    def generate(self, size=8):
        if size != 8:
            raise ValueError('Cat Territory uses a single 8x8 board')
        self.used_fallback = False
        for _ in range(self.max_generations):
            regions = self._candidate(size)
            if self.accept(regions):
                solutions = TerritorySolver.solutions(regions, limit=2)
                return TerritoryPuzzle(regions, solutions[0], True)
        self.used_fallback = True
        return self.FALLBACK

    def _candidate(self, size):
        placement = self._placement(size)
        seeds = {(x,y) for y,x in enumerate(placement)}
        # Seven isolated clues and one connected background provide a guaranteed
        # logical starting puzzle. Grow boundaries only when deduction survives.
        grid = [[7]*8 for _ in range(8)]
        for y,x in enumerate(placement[:-1]):
            grid[y][x] = y
        for _ in range(self.attempts * 2):
            x,y = self.rng.randrange(8), self.rng.randrange(8)
            if (x,y) in seeds:
                continue
            old = grid[y][x]
            colors = sorted({grid[ny][nx] for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
                             if 0 <= nx < 8 and 0 <= ny < 8 and grid[ny][nx] != old})
            if not colors:
                continue
            new = self.rng.choice(colors)
            grid[y][x] = new
            if not self.connected(grid, old) or not TerritoryLogic.solve(grid).solved:
                grid[y][x] = old
        return tuple(tuple(row) for row in grid)
