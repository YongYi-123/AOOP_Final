"""The local play session: who is playing right now (1 or 2 people).

    LocalSession
    +-- LocalPlayer (P1) -- PlayerProfile   saved progress, owned by the ProfileManager
    |                    +- HubPlayer       the in-world body
    |                    +- ControlScheme   its keys
    +-- LocalPlayer (P2) ...

PlayerProfile (persistent data) and HubPlayer (the character walking around)
are separate objects that a LocalPlayer ties together. A session is at most
MAX_LOCAL_PLAYERS players; how many profiles are SAVED is the ProfileManager's
business and unlimited.

GameEvent / LocalSession.dispatch give every personal event an owner, so
"P2 petted a cat" can only ever advance P2's daily tasks.
"""
from dataclasses import dataclass

from controls import schemes_for
from input_router import InputRouter
from player import LOOKS, HubPlayer
from settings import MAX_LOCAL_PLAYERS, PLAYER_START


@dataclass(frozen=True)
class GameEvent:
    """Something a particular player did. `player_id` is the owner's
    profile id (LocalPlayer.player_id)."""
    type: str                   # "cat_petted", "machine_visited", "coupon_used", "game_played"
    player_id: str
    amount: int = 1
    key: str | None = None      # e.g. the machine id
    game_id: str | None = None


# event type -> how it reaches the owner's profile
EVENT_HANDLERS = {
    "cat_petted": lambda profile, e: profile.record_cat_petted(),
    "machine_visited": lambda profile, e: profile.record_machine_visit(e.key),
    "coupon_used": lambda profile, e: profile.record_coupon_used(),
    "game_played": lambda profile, e: profile.record_game_played(e.game_id),
}


class LocalPlayer:
    """One person at the keyboard: a profile, its body and its keys."""

    def __init__(self, player_index, profile, controls, look, label=""):
        self.player_index = player_index        # 0-based; the order in the session
        self.profile = profile
        self.controls = controls
        self.label = label                      # "P1" / "P2"; "" in a one-player session
        self.avatar = HubPlayer(PLAYER_START, controls, profile, look, label)

    @property
    def number(self):
        return self.player_index + 1

    @property
    def player_id(self):
        """Who owns events: the profile id (a bare, unmanaged profile falls back to its slot)."""
        return self.profile.profile_id or f"player{self.number}"

    @property
    def name(self):
        return (self.profile.display_name or f"PLAYER {self.number}").upper()

    @property
    def tag(self):
        """'P2 ALICE' - or just the name when playing alone."""
        return f"{self.label} {self.name}" if self.label else self.name


class LocalSession:
    MAX_PLAYERS = MAX_LOCAL_PLAYERS

    def __init__(self, profiles):
        profiles = list(profiles)
        if not 1 <= len(profiles) <= self.MAX_PLAYERS:
            raise ValueError(f"a session has 1 to {self.MAX_PLAYERS} players, got {len(profiles)}")
        ids = {id(p) if p.profile_id is None else p.profile_id for p in profiles}
        if len(ids) != len(profiles):
            raise ValueError("the same profile cannot be two players")
        count = len(profiles)
        schemes, looks = schemes_for(count), LOOKS[count]
        self.players = [LocalPlayer(i, p, schemes[i], looks[i], f"P{i + 1}" if count > 1 else "")
                        for i, p in enumerate(profiles)]
        self.input = InputRouter(self)

    @property
    def player_count(self):
        return len(self.players)

    @property
    def primary(self):
        """P1: owns HOME, and is the player a one-player session is about."""
        return self.players[0]

    @property
    def profiles(self):
        return [p.profile for p in self.players]

    @property
    def avatars(self):
        return [p.avatar for p in self.players]

    def __iter__(self):
        return iter(self.players)

    def __len__(self):
        return len(self.players)

    # ------------------------------------------------------------ lookups
    def player_for_key(self, key):
        """The player whose scheme uses `key`, or None."""
        return next((p for p in self.players if p.controls.owns(key)), None)

    def player_for_avatar(self, avatar):
        return next((p for p in self.players if p.avatar is avatar), None)

    def player_for_profile_id(self, player_id):
        return next((p for p in self.players if p.player_id == player_id), None)

    def allows(self, player, key):
        """May `player` use `key` in a menu? Keys that only another player's
        scheme uses are theirs; shared keys (ESC, TAB, SPACE ...) are anyone's."""
        if player.controls.owns(key):
            return True
        return not any(o is not player and o.controls.owns(key) for o in self.players)

    # ------------------------------------------------------------ events
    def dispatch(self, event):
        """Deliver `event` to its owner's profile only. Returns False for an
        unknown owner or event type (nothing happens)."""
        owner = self.player_for_profile_id(event.player_id)
        handler = EVENT_HANDLERS.get(event.type)
        if owner is None or handler is None:
            return False
        handler(owner.profile, event)
        return True


@dataclass(frozen=True)
class MachineInteraction:
    """A player's use of a machine: who started it, so their tokens, coupons,
    profile and rewards are the ones used."""
    machine: object
    initiating_player: LocalPlayer

    @property
    def profile(self):
        return self.initiating_player.profile
