"""Territory rules, hearts and scoring; no pygame dependency."""
from dataclasses import dataclass
from enum import Enum
from .generator import TerritoryGenerator


@dataclass(frozen=True)
class Difficulty:
    size: int
    name: str
    win_tickets: int


DIFFICULTIES = (Difficulty(6,'EASY 6X6',10),Difficulty(8,'NORMAL 8X8',20),Difficulty(10,'HARD 10X10',35))


class BoardState(Enum):
    READY = 'ready'
    PLAYING = 'playing'
    WON = 'won'
    LOST = 'lost'


@dataclass(frozen=True)
class TerritoryOutcome:
    won: bool
    score: int
    tickets: int
    elapsed: float


class TerritoryRules:
    @staticmethod
    def conflicts(regions, cats, point):
        x,y = point
        return tuple((cx,cy) for cx,cy in cats if
                     cx == x or cy == y or regions[cy][cx] == regions[y][x]
                     or (abs(cx-x) <= 1 and abs(cy-y) <= 1))

    @staticmethod
    def solved(regions, cats):
        size = len(regions)
        return len(cats) == size and all(not TerritoryRules.conflicts(regions,cats-{cat},cat)
                                        for cat in cats)


class TerritoryBoard:
    def __init__(self, difficulty=DIFFICULTIES[0], rng=None, puzzle=None):
        self.difficulty, self.size = difficulty, difficulty.size
        self.puzzle = puzzle or TerritoryGenerator(rng).generate(self.size)
        self.regions = self.puzzle.regions
        self.cats, self.marks = set(), set()
        self.hearts, self.errors = 3, 0
        self.state = BoardState.READY
        self.elapsed = 0.0
        self.outcome = None
        self.error_cell = None

    def contains(self,x,y):
        return 0 <= x < self.size and 0 <= y < self.size

    def _active(self,x,y):
        if not self.contains(x,y) or self.outcome is not None:
            return False
        self.state = BoardState.PLAYING
        return True

    def toggle_mark(self,x,y):
        if not self._active(x,y):
            return False
        point = (x,y)
        self.cats.discard(point)
        if point in self.marks:
            self.marks.remove(point)
        else:
            self.marks.add(point)
        return True

    def toggle_cat(self,x,y):
        if not self._active(x,y):
            return False
        point = (x,y)
        self.error_cell = None
        if point in self.cats:
            self.cats.remove(point)
            return True
        if TerritoryRules.conflicts(self.regions,self.cats,point):
            self.hearts -= 1
            self.errors += 1
            self.error_cell = point
            if self.hearts == 0:
                self._finish(False)
            return False
        self.marks.discard(point)
        self.cats.add(point)
        if TerritoryRules.solved(self.regions,self.cats):
            self._finish(True)
        return True

    def update(self,dt):
        if self.state is BoardState.PLAYING:
            self.elapsed += max(0,dt)

    @property
    def score(self):
        return len(self.cats)*20 + (self.size*200+max(0,1200-int(self.elapsed)-100*self.errors)
                                    if self.state is BoardState.WON else 0)

    def _finish(self,won):
        self.state = BoardState.WON if won else BoardState.LOST
        self.outcome = TerritoryOutcome(won,self.score,self.difficulty.win_tickets if won else 0,self.elapsed)
