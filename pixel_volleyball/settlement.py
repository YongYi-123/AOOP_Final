"""Completed-match rewards; quitting an unfinished match grants nothing."""
from dataclasses import dataclass


@dataclass(frozen=True)
class VolleyReward:
    score: int = 0
    tickets: int = 0

    @classmethod
    def from_outcome(cls, outcome, side):
        if outcome is None:
            return cls()
        won = outcome.winner == side
        points = outcome.points[side]
        return cls(points * 100 + (500 if won else 0), points * 2 + (10 if won else 0))
