"""Input routing: ControlScheme -> InputRouter -> HubPlayer / minigame.

Nothing downstream reads the keyboard directly. A ControlScheme says which
keys are one player's; PlayerInput is that player's whole view of the
keyboard (only their keys, as logical actions, with held-state tracked from
events); InputRouter hands each event to the player it belongs to. A minigame
is given the PlayerInput of the people actually playing, so another player's
keys cannot reach it - and a controller later only needs another source of the
same actions.
"""
import pygame

from settings import BACK_KEYS

# Keys no player owns that every scene may still use (ESC is the explicit,
# global "back": the one rule that any player can leave a screen with).
SHARED_KEYS = frozenset(BACK_KEYS) | {pygame.K_BACKSPACE, pygame.K_q, pygame.K_m, pygame.K_n,
                                      pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET, pygame.K_v}


class PlayerInput:
    """One player's keys as actions: up / down / left / right / interact / menu /
    item / pause, plus the shared "back" (ESC)."""

    def __init__(self, scheme):
        self.scheme = scheme
        self._down = set()

    def action(self, event):
        """The action a KEYDOWN event means for this player, else None (it is
        another player's key, or means nothing)."""
        if event.type != pygame.KEYDOWN:
            return None
        if self.scheme.owns(event.key):
            return self.scheme.action_for(event.key)
        return "back" if event.key in BACK_KEYS else None

    def is_shared(self, event):
        """Is this one of the shared keys (back, map, mute, volume, effects)?"""
        return event.type == pygame.KEYDOWN and event.key in SHARED_KEYS \
            and not self.scheme.owns(event.key)

    def feed(self, event):
        """Track held keys from events. Returns the action of a KEYDOWN, or None."""
        if event.type == pygame.KEYUP:
            self._down.discard(event.key)
        elif event.type == pygame.KEYDOWN and self.scheme.owns(event.key):
            self._down.add(event.key)
        elif event.type == pygame.WINDOWFOCUSLOST:
            self._down.clear()
        return self.action(event)

    def held(self, action):
        return any(self.scheme.action_for(k) == action for k in self._down)

    def axis(self, negative, positive):
        return int(self.held(positive)) - int(self.held(negative))


class InputRouter:
    """Sends each key event to the player whose scheme owns it."""

    def __init__(self, session):
        self.session = session

    def route(self, event):
        """(LocalPlayer, action) for a KEYDOWN, or (None, None) if no player owns the key."""
        if event.type != pygame.KEYDOWN:
            return None, None
        player = self.session.player_for_key(event.key)
        if player is None:
            return None, None
        return player, player.controls.action_for(event.key)

    def input_for(self, player):
        """A fresh PlayerInput for `player` (one per minigame run)."""
        return PlayerInput(player.controls)
