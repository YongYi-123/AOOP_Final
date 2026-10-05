"""What a minigame pays out (RewardResult) and the paid credit it pays out
against (PlaySession).

The flow for every machine is:

    session = machine.start_play(profile)    # tokens taken exactly once
    ... the minigame runs ...
    session.settle(minigame.get_reward())     # tickets paid exactly once

The arcade room never knows how a minigame scores; it only passes the
minigame's RewardResult to the session.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RewardResult:
    game_id: str
    tickets_earned: int = 0
    score: int | None = None    # None: the game has no score to record


class PlaySession:
    """One paid play on one machine. Created only after the tokens were
    taken; ends exactly once, by either `settle` (pay the reward) or
    `refund` (return the tokens). Every later call is ignored."""

    def __init__(self, profile, game_id, cost, name=None):
        self.profile = profile
        self.game_id = game_id
        self.cost = cost
        self.name = name or game_id.upper()
        self._settled = False

    @property
    def settled(self):
        return self._settled

    def settle(self, result):
        """The game was played: count it and pay `result` (a RewardResult, or
        None for no reward). Returns the result paid, or None if this session
        was already settled or refunded."""
        if self._settled:
            return None
        if result is not None and result.game_id != self.game_id:
            raise ValueError(f"reward for {result.game_id!r} settled on a {self.game_id!r} session")
        self._settled = True
        self.profile.record_game_played(self.game_id)
        if result is None:
            return None
        if result.score is not None:
            self.profile.record_score(self.game_id, result.score)
        self.profile.add_tickets(result.tickets_earned)
        return result

    def refund(self):
        """The game never ran (failed to start, or the app closed before it
        opened): give the tokens back. Returns False if already settled."""
        if self._settled:
            return False
        self._settled = True
        self.profile.refund_tokens(self.cost, self.name)
        return True
