"""Run results and the ticket formula. Pure data, so the payout can be tested without a window."""
from dataclasses import dataclass

from .config import TICKETS


def tickets_for(score, levels_cleared):
    """Never negative, capped, and 0 for a run that scored nothing."""
    score, levels_cleared = max(0, int(score)), max(0, int(levels_cleared))
    if score == 0:
        return 0
    return min(TICKETS["cap"], levels_cleared * TICKETS["per_level_cleared"] + score // TICKETS["per_score"])


@dataclass(frozen=True)
class RunResult:
    score: int = 0
    level: int = 0             # highest level reached
    levels_cleared: int = 0
    tickets: int = 0

    @classmethod
    def of(cls, score, level, levels_cleared):
        return cls(max(0, score), max(0, level), max(0, levels_cleared), tickets_for(score, levels_cleared))

    def better_than(self, other):
        """Ranking of two runs of one play session: only the best run is ever paid."""
        return (self.tickets, self.score, self.level) > (other.tickets, other.score, other.level)
