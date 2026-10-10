"""Deduce forced cats using rules alone; never consult a planted answer."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LogicReport:
    cats: frozenset
    steps: tuple
    solved: bool


class TerritoryLogic:
    @staticmethod
    def solve(regions):
        size = len(regions)
        candidates = {(x,y) for y in range(size) for x in range(size)}
        cats, steps = set(), []
        groups = ([{(x,y) for x in range(size)} for y in range(size)] +
                  [{(x,y) for y in range(size)} for x in range(size)] +
                  [{(x,y) for y in range(size) for x in range(size) if regions[y][x] == c}
                   for c in range(size)])
        while len(cats) < size:
            forced = next((next(iter(group & candidates)) for group in groups
                           if not group & cats and len(group & candidates) == 1), None)
            if forced is None:
                break
            x,y = forced
            cats.add(forced)
            steps.append(forced)
            candidates = {(cx,cy) for cx,cy in candidates if cx != x and cy != y
                          and regions[cy][cx] != regions[y][x]
                          and not (abs(cx-x) <= 1 and abs(cy-y) <= 1)}
        return LogicReport(frozenset(cats), tuple(steps), len(cats) == size)
