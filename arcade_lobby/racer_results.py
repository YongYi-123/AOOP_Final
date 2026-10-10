"""Immutable racer outcomes and a pure ticket policy, independent of pygame.

One paid visit rewards its best ended run, never the sum of free replays.
Competitive finishes earn 10 base tickets plus 5 per opponent beaten;
all ended runs earn one ticket per 1000 points, capped at 50 score tickets.
Abandoned runs earn nothing and do not record a high score.
"""
from dataclasses import dataclass

from minigame import MiniGameResult, PlayerResult
from rewards import RewardBundle


@dataclass(frozen=True)
class RacerOutcome:
    mode: str
    status: str
    score: int
    position: int | None = None
    field_size: int = 1

    @classmethod
    def from_racer(cls, racer):
        mode = racer.mode.value
        state = racer.state.value
        stats = racer.manager.result
        if state not in ("FINISHED", "GAME_OVER") or stats is None:
            return cls(mode, "abandoned", max(0, int(racer.player.score)))
        return cls(mode, "completed" if state == "FINISHED" else "game_over",
                   max(0, int(stats["score"])),
                   stats.get("position") if mode == "COMPETITIVE" else None,
                   stats.get("field_size", 1))

    @property
    def tickets(self):
        if self.status == "abandoned":
            return 0
        score_tickets = min(50, self.score // 1000)
        if self.mode == "COMPETITIVE" and self.status == "completed":
            return score_tickets + 10 + 5 * max(0, self.field_size - (self.position or self.field_size))
        return score_tickets

    def player_result(self, profile_id):
        return PlayerResult(profile_id,
                            None if self.status == "abandoned" else self.score,
                            RewardBundle(tickets=self.tickets, reason="RETRO RACER"))


class RacerVisitResults:
    """Keep a stable best result while the embedded racer resets on replay."""

    def __init__(self):
        self.best = None
        self.latest = None

    def observe(self, racer):
        outcome = RacerOutcome.from_racer(racer)
        self.latest = outcome
        if outcome.status != "abandoned":
            if self.best is None or (outcome.tickets, outcome.score) > (self.best.tickets, self.best.score):
                self.best = outcome

    @property
    def outcome(self):
        return self.best or self.latest or RacerOutcome("COMPETITIVE", "abandoned", 0)

    def get_result(self, participants):
        return MiniGameResult(tuple(self.outcome.player_result(p.profile_id) for p in participants))
