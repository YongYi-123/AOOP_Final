"""What a minigame pays out (RewardResult) and the paid credit it pays out
against (PlaySession).

The flow for every machine is:

    session = machine.start_play(profile)    # coins taken exactly once
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
    """One paid play on one machine. Created only after the coins were
    taken; ends exactly once, by either `settle` (pay the reward) or
    `refund` (return the coins). Every later call is ignored."""

    def __init__(self, profile, game_id, cost):
        self.profile = profile
        self.game_id = game_id
        self.cost = cost
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
        self.profile.record_game_played()
        if result is None:
            return None
        if result.score is not None:
            self.profile.record_score(self.game_id, result.score)
        self.profile.add_tickets(result.tickets_earned)
        return result

    def refund(self):
        """The game never ran (failed to start, or the app closed before it
        opened): give the coins back. Returns False if already settled."""
        if self._settled:
            return False
        self._settled = True
        self.profile.add_coins(self.cost)
        return True
