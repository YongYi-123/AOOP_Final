"""Defer single clicks so a double click never applies a stray mark."""


class TerritoryClickRouter:
    WINDOW = .28

    def __init__(self):
        self.pending = None

    def clear(self):
        self.pending = None

    def click(self, cell, now, mark, cat):
        if self.pending:
            previous, stamp = self.pending
            if previous == cell and now-stamp <= self.WINDOW:
                self.pending = None
                cat(*cell)
                return
            mark(*previous)
        self.pending = (cell,now)

    def update(self, now, mark):
        if self.pending and now-self.pending[1] > self.WINDOW:
            cell,_ = self.pending
            self.pending = None
            mark(*cell)
