"""Run results and the ticket formula. Pure data, so the payout can be tested without a window."""
from dataclasses import dataclass

from .config import TICKETS


def tickets_for(score, waves_cleared):
    """Never negative, capped, and 0 for a run that scored nothing."""
    score, waves_cleared = max(0, int(score)), max(0, int(waves_cleared))
    if score == 0:
        return 0
    return min(TICKETS["cap"], waves_cleared * TICKETS["per_wave_cleared"] + score // TICKETS["per_score"])


@dataclass(frozen=True)
class RunResult:
    score: int = 0
    wave: int = 0              # highest wave reached
    waves_cleared: int = 0
    tickets: int = 0

    @classmethod
    def of(cls, score, wave, waves_cleared):
        return cls(max(0, score), max(0, wave), max(0, waves_cleared), tickets_for(score, waves_cleared))

    def better_than(self, other):
        """Ranking of two runs of one play session: only the best run is ever paid."""
        return (self.tickets, self.score, self.wave) > (other.tickets, other.score, other.wave)
