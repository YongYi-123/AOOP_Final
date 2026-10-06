"""Base class for every scene launched from an arcade machine, plus the
description of how many players a minigame supports and what it reports."""
from dataclasses import dataclass, field

from rewards import RewardBundle, RewardResult
from scene_base import BaseScene
from settings import MAX_LOCAL_PLAYERS, PLACEHOLDER_REWARD_TICKETS


@dataclass(frozen=True)
class MiniGameDefinition:
    """How many local players a minigame can run with. A machine whose game
    supports 2 offers a PLAYERS choice when two people are playing; a
    1-player game is played by whoever started it while the other watches."""
    game_id: str
    min_players: int = 1
    max_players: int = 1

    def __post_init__(self):
        if not 1 <= self.min_players <= self.max_players <= MAX_LOCAL_PLAYERS:
            raise ValueError(f"bad player range {self.min_players}-{self.max_players} for {self.game_id!r}")

    def supports(self, players):
        return self.min_players <= players <= self.max_players

    @property
    def multiplayer(self):
        return self.max_players > 1


@dataclass(frozen=True)
class PlayerResult:
    """One player's outcome. The reward is theirs alone."""
    profile_id: str
    score: int | None = None
    reward: RewardBundle = field(default_factory=RewardBundle)


@dataclass(frozen=True)
class MiniGameResult:
    player_results: tuple = ()

    def for_profile(self, profile_id):
        return next((r for r in self.player_results if r.profile_id == profile_id), None)


class MinigameScene(BaseScene):
    """A minigame owns its scoring rules: when it is popped, the arcade room
    asks `get_result()` and pays each player's part out once against their
    own play session.

    A one-player game only overrides get_reward(), turning its own score into
    tickets, e.g.  return RewardResult(self.machine.id, score // 100, score).
    A game that supports two players overrides get_result() and returns one
    PlayerResult per participant (`self.participants`: their profiles).
    """

    def __init__(self, game, machine):
        super().__init__(game)
        self.machine = machine
        self.participants = []      # the PlayerProfiles playing; set by the room before it starts
        self.players = []           # the LocalPlayers playing (the rest are spectators)
        self._inputs = {}

    def attach_players(self, players, spectators=()):
        """Say who plays and who only watches. Only the players' keys reach the game."""
        self.players = list(players)
        self.spectators = list(spectators)
        self.participants = [p.profile for p in self.players]
        self._inputs = {p: self.game.session.input.input_for(p) for p in self.players}

    def input_for(self, player):
        """The PlayerInput of one participant (the starter by default)."""
        if not self._inputs:
            from controls import SOLO_CONTROLS
            from input_router import PlayerInput
            self._inputs = {None: PlayerInput(SOLO_CONTROLS)}
        return self._inputs.get(player) or next(iter(self._inputs.values()))

    @property
    def input(self):
        """The starter's PlayerInput. Games read actions from here, never keys."""
        return self.input_for(self.players[0] if self.players else None)

    @property
    def failed(self):
        """True if the game could not start; the play is then refunded
        instead of rewarded."""
        return False

    def get_reward(self):
        # Temporary flat payout until the game has real scoring.
        return RewardResult(self.machine.id, tickets_earned=PLACEHOLDER_REWARD_TICKETS)

    def get_result(self):
        """A MiniGameResult. By default every participant is scored by
        get_reward() separately (never one shared bundle)."""
        results = []
        for profile in self.participants:
            reward = self.get_reward()
            results.append(PlayerResult(profile.profile_id, reward.score,
                                        RewardBundle(tickets=reward.tickets_earned,
                                                     reason=self.machine.name.upper())))
        return MiniGameResult(tuple(results))
