"""Territory rules, hearts and scoring; no pygame dependency."""
from dataclasses import dataclass
from enum import Enum
from .generator import TerritoryGenerator
from .solver import TerritorySolver


@dataclass(frozen=True)
class Difficulty:
    size: int
    name: str
    win_tickets: int


BOARD_RULES = Difficulty(8,'8X8 TERRITORY',20)


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
    def __init__(self, difficulty=BOARD_RULES, rng=None, puzzle=None):
        self.difficulty, self.size = difficulty, difficulty.size
        self.puzzle = puzzle or TerritoryGenerator(rng).generate(self.size)
        self.regions = self.puzzle.regions
        self.cats, self.marks = set(), set()
        self.hearts, self.errors = 3, 0
        self.state = BoardState.READY
        self.elapsed = 0.0
        self.outcome = None
        self.error_cell = None
        self.history = []
        self.completion_status = "OK"

    def _remember(self):
        self.history.append((self.cats.copy(),self.marks.copy()))
        self.history = self.history[-64:]

    def _check_completion(self):
        if not TerritorySolver.solutions(self.regions,limit=1,cats=self.cats):
            self.completion_status = "CATS BLOCK COMPLETION - U UNDO"
        elif not TerritorySolver.solutions(self.regions,limit=1,cats=self.cats,marks=self.marks):
            self.completion_status = "MARKS BLOCK COMPLETION - C CLEAR X"
        else:
            self.completion_status = "OK"

    def undo(self):
        if self.outcome is not None or not self.history:
            return False
        self.cats,self.marks = self.history.pop()
        self.error_cell = None
        self._check_completion()
        return True

    def clear_marks(self):
        if self.outcome is not None or not self.marks:
            return False
        self._remember()
        self.marks.clear()
        self._check_completion()
        return True

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
        self._remember()
        self.cats.discard(point)
        if point in self.marks:
            self.marks.remove(point)
        else:
            self.marks.add(point)
        self._check_completion()
        return True

    def toggle_cat(self,x,y):
        if not self._active(x,y):
            return False
        point = (x,y)
        self.error_cell = None
        if point in self.cats:
            self._remember()
            self.cats.remove(point)
            self._check_completion()
            return True
        if TerritoryRules.conflicts(self.regions,self.cats,point):
            self.hearts -= 1
            self.errors += 1
            self.error_cell = point
            if self.hearts == 0:
                self._finish(False)
            return False
        self._remember()
        self.marks.discard(point)
        self.cats.add(point)
        self._check_completion()
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
