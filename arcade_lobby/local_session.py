"""The play session: the one player in the arcade right now.

    LocalSession
    +-- LocalPlayer -- PlayerProfile   saved progress, owned by the ProfileManager
                    +- HubPlayer       the in-world body
                    +- ControlScheme   its keys

The game is single-player. Any number of profiles can be SAVED (the
ProfileManager's business), but a session always holds exactly one of them;
switching profile means going back to the profile screen. `players`,
`primary`, `profiles` and `avatars` stay as list-shaped accessors of that one
player so the rooms, the story and the minigames keep their one call path.

GameEvent / LocalSession.dispatch give every personal event an owner (the
profile that did it), and the story / quest system listens to them.
"""
from dataclasses import dataclass

from controls import SOLO_CONTROLS
from input_router import InputRouter
from player import DEFAULT_LOOK, HubPlayer
from settings import PLAYER_START


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
    # story events: nothing happens to the profile itself; the quest system hears them through add_listener()
    "vending_secret": lambda profile, e: None,
    "secret_item_found": lambda profile, e: None,
    "easter_egg_found": lambda profile, e: None,            # (OUT OF TIME: only the story keeps a note of it)
    "secret_trial_done": lambda profile, e: None,
    "arcade_reopened": lambda profile, e: None,             # (the final chapter's reopening, for when it is built)
}


class LocalPlayer:
    """The person at the keyboard: a profile, its body and its keys."""

    def __init__(self, profile, controls=SOLO_CONTROLS, look=DEFAULT_LOOK):
        self.profile = profile
        self.controls = controls
        self.avatar = HubPlayer(PLAYER_START, controls, profile, look)

    @property
    def player_id(self):
        """Who owns events: the profile id (a bare, unmanaged profile falls back to a fixed name)."""
        return self.profile.profile_id or "player1"

    @property
    def name(self):
        return (self.profile.display_name or "PLAYER").upper()

    tag = name                  # the heading of this player's panels


class LocalSession:
    """A session for exactly one profile. `LocalSession(profile)`; a
    one-item list is accepted too (older callers), any other count is refused."""

    def __init__(self, profile):
        if isinstance(profile, (list, tuple)):
            if len(profile) != 1:
                raise ValueError(f"a session has exactly one player, got {len(profile)}")
            profile = profile[0]
        self.players = [LocalPlayer(profile)]
        self.input = InputRouter(self)
        self._listeners = []

    @property
    def primary(self):
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

    # ------------------------------------------------------------ events
    def dispatch(self, event):
        """Deliver `event` to its owner's profile only. Returns False for an
        unknown owner or event type (nothing happens)."""
        owner = self.player_for_profile_id(event.player_id)
        handler = EVENT_HANDLERS.get(event.type)
        if owner is None or handler is None:
            return False
        handler(owner.profile, event)
        for callback in list(self._listeners):
            callback(owner, event)
        return True

    def add_listener(self, callback):
        """callback(LocalPlayer, GameEvent) hears every event that was delivered (the story / quest system)."""
        self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)


@dataclass(frozen=True)
class MachineInteraction:
    """A player's use of a machine: who started it, so their tokens, coupons,
    profile and rewards are the ones used."""
    machine: object
    initiating_player: LocalPlayer

    @property
    def profile(self):
        return self.initiating_player.profile
