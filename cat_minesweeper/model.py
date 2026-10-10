"""First-click-safe minesweeper and scoring, independent of pygame."""
from dataclasses import dataclass
from enum import Enum
import random


@dataclass(frozen=True)
class Difficulty:
    size: int
    mines: int
    name: str
    win_tickets: int


DIFFICULTIES = (Difficulty(6, 6, "COZY 6X6", 10), Difficulty(9, 12, "CURIOUS 9X9", 20),
                Difficulty(12, 24, "CLEVER 12X12", 35))


class BoardState(Enum):
    READY = "ready"
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass
class MineCell:
    mine: bool = False
    adjacent: int = 0
    revealed: bool = False
    flagged: bool = False


@dataclass(frozen=True)
class MineOutcome:
    won: bool
    score: int
    tickets: int
    elapsed: float


class MineBoard:
    def __init__(self, difficulty=DIFFICULTIES[0], rng=None):
        self.difficulty = difficulty
        if difficulty.size < 3 or not 0 < difficulty.mines <= difficulty.size ** 2 - 9:
            raise ValueError("board must leave a safe opening around any first click")
        self.size = difficulty.size
        self.rng = rng or random.Random()
        self.cells = [[MineCell() for _ in range(self.size)] for _ in range(self.size)]
        self.state = BoardState.READY
        self.elapsed = 0.0
        self.outcome = None
        self.exploded = None

    def contains(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def neighbors(self, x, y):
        return ((nx, ny) for ny in range(y - 1, y + 2) for nx in range(x - 1, x + 2)
                if self.contains(nx, ny) and (nx, ny) != (x, y))

    @property
    def revealed_count(self):
        return sum(c.revealed and not c.mine for row in self.cells for c in row)

    @property
    def flag_count(self):
        return sum(c.flagged for row in self.cells for c in row)

    def _generate(self, first_x, first_y):
        safe = set(self.neighbors(first_x, first_y)) | {(first_x, first_y)}
        available = [(x, y) for y in range(self.size) for x in range(self.size) if (x, y) not in safe]
        for x, y in self.rng.sample(available, self.difficulty.mines):
            self.cells[y][x].mine = True
        for y, row in enumerate(self.cells):
            for x, cell in enumerate(row):
                cell.adjacent = sum(self.cells[ny][nx].mine for nx, ny in self.neighbors(x, y))
        self.state = BoardState.PLAYING

    def toggle_flag(self, x, y):
        if not self.contains(x, y) or self.state in (BoardState.WON, BoardState.LOST):
            return False
        cell = self.cells[y][x]
        if cell.revealed:
            return False
        cell.flagged = not cell.flagged
        return True

    def reveal(self, x, y):
        if not self.contains(x, y) or self.state in (BoardState.WON, BoardState.LOST):
            return False
        cell = self.cells[y][x]
        if cell.flagged or cell.revealed:
            return False
        if self.state is BoardState.READY:
            self._generate(x, y)
        if cell.mine:
            cell.revealed = True
            self.exploded = (x, y)
            self._finish(False)
            return True
        pending = [(x, y)]
        while pending:
            cx, cy = pending.pop()
            current = self.cells[cy][cx]
            if current.revealed or current.flagged or current.mine:
                continue
            current.revealed = True
            if current.adjacent == 0:
                pending.extend(self.neighbors(cx, cy))
        if self.revealed_count == self.size ** 2 - self.difficulty.mines:
            self._finish(True)
        return True

    def update(self, dt):
        if self.state is BoardState.PLAYING:
            self.elapsed += max(0, dt)

    def _finish(self, won):
        self.state = BoardState.WON if won else BoardState.LOST
        self.outcome = MineOutcome(won, self.score, self.difficulty.win_tickets if won else 0,
                                   self.elapsed)

    @property
    def score(self):
        base = self.revealed_count * 10
        if self.state is BoardState.WON:
            base += self.size * 100 + max(0, 600 - int(self.elapsed))
        return base
