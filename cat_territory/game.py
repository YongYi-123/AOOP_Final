"""Puzzle lifecycle, deferred mouse input and best-result settlement."""
from .model import TerritoryBoard, TerritoryOutcome, BoardState, BOARD_RULES
from .input import TerritoryClickRouter
from .rendering import TerritoryGridLayout, TerritoryRenderer
from cat_minesweeper.audio import MineSounds


class TerritoryGame:
    def __init__(self,rng=None):
        self.rng = rng
        self.board = TerritoryBoard(rng=rng)
        self.layout = TerritoryGridLayout(self.board.size)
        self.renderer = TerritoryRenderer()
        self.audio = MineSounds()
        self.clicks = TerritoryClickRouter()
        self.selecting, self.paused = True, False
        self.time, self.error_left = 0.0, 0.0
        self.best = None
        self.cursor = (0,0)

    def restart(self):
        self.observe_result()
        self.clicks.clear()
        self.board = TerritoryBoard(BOARD_RULES,self.rng)
        self.layout = TerritoryGridLayout(self.board.size)
        self.selecting, self.paused = False,False
        self.cursor = (0,0)
        self.error_left = 0

    def confirm(self):
        if self.selecting or self.board.outcome is not None:
            self.restart()
        elif self.paused:
            self.paused = False
        else:
            self.place_cat(*self.cursor)

    def toggle_pause(self):
        self.clicks.clear()
        if not self.selecting and self.board.outcome is None:
            self.paused = not self.paused

    @property
    def active(self):
        return not self.selecting and not self.paused and self.board.outcome is None

    def move_cursor(self,dx,dy):
        if self.active:
            x,y = self.cursor
            self.cursor = (max(0,min(self.board.size-1,x+dx)),max(0,min(self.board.size-1,y+dy)))

    def mark(self,x,y):
        if self.active and self.board.toggle_mark(x,y):
            self.audio.play('flag',self.time)

    def place_cat(self,x,y):
        if not self.active:
            return False
        self.clicks.clear()
        placed = self.board.toggle_cat(x,y)
        if not placed:
            self.error_left = .6
        event = ('win' if self.board.state is BoardState.WON else
                 'loss' if self.board.state is BoardState.LOST else 'reveal' if placed else 'cancel')
        self.audio.play(event,self.time)
        self.observe_result()
        return placed

    def click(self,point,button):
        if not self.active or button not in (1,3):
            return False
        cell = self.layout.cell_at(point)
        if cell is None:
            return False
        self.cursor = cell
        if button == 3:
            self.clicks.clear()
            self.mark(*cell)
        else:
            self.clicks.click(cell,self.time,self.mark,self.place_cat)
        return True

    def update(self,dt):
        self.time += max(0,dt)
        if self.active:
            self.board.update(dt)
            self.clicks.update(self.time,self.mark)
            self.error_left = max(0,self.error_left-dt)

    def observe_result(self):
        result = self.board.outcome
        if result is not None:
            if self.best is None:
                self.best = result
            else:
                previous=self.best
                self.best = TerritoryOutcome(previous.won or result.won,max(previous.score,result.score),
                    max(previous.tickets,result.tickets), result.elapsed if result.score>previous.score else previous.elapsed)

    def outcome(self):
        self.observe_result()
        return self.best or TerritoryOutcome(False,0,0,0)

    def draw(self,surface):
        self.renderer.draw(surface,self)
