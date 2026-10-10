"""Connected colored regions grown around a guaranteed legal cat placement."""
from dataclasses import dataclass
import random
from .solver import TerritorySolver


@dataclass(frozen=True)
class TerritoryPuzzle:
    regions: tuple
    solution: tuple
    unique: bool


class TerritoryGenerator:
    def __init__(self, rng=None, attempts=80):
        self.rng = rng or random.Random()
        self.attempts = attempts

    def _placement(self, size):
        def search(chosen):
            if len(chosen) == size:
                return chosen
            candidates = list(set(range(size))-set(chosen))
            self.rng.shuffle(candidates)
            for column in candidates:
                if chosen and abs(column-chosen[-1]) <= 1:
                    continue
                result = search(chosen+[column])
                if result:
                    return result
        return search([])

    def _refine(self, grid, placement):
        """Remove alternate solutions by legal boundary transfers of non-seed cells."""
        size = len(grid)
        seeds = {(x,y) for y,x in enumerate(placement)}
        seen = set()
        for _ in range(size*size):
            regions = tuple(tuple(row) for row in grid)
            if regions in seen:
                break
            seen.add(regions)
            solutions = TerritorySolver.solutions(regions)
            if len(solutions) == 1:
                return regions, True
            alternate = next(solution for solution in solutions if solution != tuple(placement))
            candidates = [(x,y) for y,x in enumerate(alternate) if (x,y) not in seeds]
            self.rng.shuffle(candidates)
            changed = False
            for x,y in candidates:
                old = grid[y][x]
                cells = {(cx,cy) for cy,row in enumerate(grid) for cx,color in enumerate(row)
                         if color == old and (cx,cy) != (x,y)}
                reached = set()
                pending = [next(iter(cells))]
                while pending:
                    cx,cy = pending.pop()
                    if (cx,cy) in reached:
                        continue
                    reached.add((cx,cy))
                    pending.extend(p for p in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1))
                                   if p in cells and p not in reached)
                if reached != cells:
                    continue
                colors = [grid[ny][nx] for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
                          if 0 <= nx < size and 0 <= ny < size and grid[ny][nx] != old]
                if colors:
                    grid[y][x] = self.rng.choice(colors)
                    changed = True
                    break
            if not changed:
                break
        return tuple(tuple(row) for row in grid), False

    def generate(self, size):
        if size not in (6,8,10):
            raise ValueError('territory sizes are 6, 8 or 10')
        best = None
        for _ in range(self.attempts):
            placement = self._placement(size)
            grid = [[-1]*size for _ in range(size)]
            frontier = []
            for row, column in enumerate(placement):
                grid[row][column] = row
                frontier.append((column,row))
            while frontier:
                x,y = frontier.pop(self.rng.randrange(len(frontier)))
                for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if 0 <= nx < size and 0 <= ny < size and grid[ny][nx] == -1:
                        grid[ny][nx] = grid[y][x]
                        frontier.append((nx,ny))
            regions, unique = self._refine(grid, placement)
            solutions = TerritorySolver.solutions(regions)
            if not solutions:
                raise RuntimeError('generator lost its planted legal solution')
            best = TerritoryPuzzle(regions,tuple(placement),len(solutions)==1)
            if best.unique:
                return best
        # A bounded generator always returns a solvable board. Alternate legal
        # solutions are intentionally accepted when uniqueness was not found.
        return best
