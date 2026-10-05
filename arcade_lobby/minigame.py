"""Base class for every scene launched from an arcade machine."""
from rewards import RewardResult
from scene_base import BaseScene
from settings import PLACEHOLDER_REWARD_TICKETS


class MinigameScene(BaseScene):
    """A minigame owns its scoring rules: when it is popped, the arcade room
    asks `get_reward()` and pays it out once against the play session.

    Real minigames override get_reward() to turn their own score into
    tickets, e.g.  return RewardResult(self.machine.id, score // 100, score)
    """

    def __init__(self, game, machine):
        super().__init__(game)
        self.machine = machine

    @property
    def failed(self):
        """True if the game could not start; the play is then refunded
        instead of rewarded."""
        return False

    def get_reward(self):
        # Temporary flat payout until the game has real scoring.
        return RewardResult(self.machine.id, tickets_earned=PLACEHOLDER_REWARD_TICKETS)
