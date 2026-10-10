"""Board lifecycle, pause and mouse coordinates, separated from mine rules."""
from .model import MineBoard, MineOutcome, BoardState, DIFFICULTIES
from .rendering import MineGridLayout, MineRenderer
from .audio import MineSounds


class MineGame:
    def __init__(self, rng=None):
        self.rng = rng
        self.difficulty_index = 0
        self.board = MineBoard(DIFFICULTIES[0], rng)
        self.layout = MineGridLayout(self.board.size)
        self.renderer = MineRenderer()
        self.audio = MineSounds()
        self.selecting = True
        self.paused = False
        self.time = 0.0
        self.best = None

    def move_selection(self, step):
        if self.selecting:
            self.difficulty_index = (self.difficulty_index + step) % len(DIFFICULTIES)

    def restart(self):
        self.observe_result()
        self.audio.stop()
        self.board = MineBoard(DIFFICULTIES[self.difficulty_index], self.rng)
        self.layout = MineGridLayout(self.board.size)
        self.selecting = self.paused = False

    def confirm(self):
        if self.selecting or self.board.state in (BoardState.WON, BoardState.LOST):
            self.restart()
        elif self.paused:
            self.paused = False

    def toggle_pause(self):
        if not self.selecting and self.board.state in (BoardState.READY, BoardState.PLAYING):
            self.paused = not self.paused

    def select_difficulty(self):
        self.observe_result()
        self.selecting, self.paused = True, False

    def click(self, point, button):
        if self.selecting or self.paused:
            return False
        cell = self.layout.cell_at(point)
        if cell is None:
            return False
        changed = (self.board.reveal(*cell) if button == 1 else
                   self.board.toggle_flag(*cell) if button == 3 else False)
        if changed:
            event = ("win" if self.board.state is BoardState.WON else
                     "loss" if self.board.state is BoardState.LOST else
                     "reveal" if button == 1 else "flag")
            self.audio.play(event, self.time)
        self.observe_result()
        return changed

    def observe_result(self):
        result = self.board.outcome
        if result is not None:
            if self.best is None:
                self.best = result
            else:
                previous = self.best
                self.best = MineOutcome(previous.won or result.won,
                                        max(previous.score, result.score),
                                        max(previous.tickets, result.tickets),
                                        result.elapsed if result.score > previous.score else previous.elapsed)

    def update(self, dt):
        self.time += max(0, dt)
        if not self.selecting and not self.paused:
            self.board.update(dt)

    def draw(self, surface):
        self.renderer.draw(surface, self)

    def outcome(self):
        self.observe_result()
        return self.best or MineOutcome(False, 0, 0, 0)
