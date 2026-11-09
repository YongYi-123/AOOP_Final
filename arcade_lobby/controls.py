"""Data-driven key bindings. A ControlScheme says which keys one local player
uses; nothing else in the game names a movement / interact / bag key, so a
binding is changed here (or by building a scheme from a settings file later).

The game is single-player: SOLO is the one scheme (WASD *and* the arrow keys,
E/ENTER, I).
"""
from dataclasses import dataclass, field

import pygame


_KEY_NAMES = {pygame.K_RETURN: "ENTER", pygame.K_KP_ENTER: "ENTER", pygame.K_RCTRL: "R-CTRL",
              pygame.K_LSHIFT: "SHIFT", pygame.K_RSHIFT: "R-SHIFT", pygame.K_KP0: "KP0",
              pygame.K_ESCAPE: "ESC"}


def key_label(key):
    return _KEY_NAMES.get(key) or pygame.key.name(key).upper()


DIRECTION_ACTIONS = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}


@dataclass(frozen=True, eq=False)
class ControlScheme:
    name: str
    move: dict                      # key -> (dx, dy)
    interact: tuple                 # keys that press E-style "use"
    inventory: tuple                # keys that open the bag (and pause inside a minigame)
    move_hint: str = ""             # short labels for the controls box
    interact_hint: str = ""
    inventory_hint: str = ""
    item: tuple = ()                # "use item" in minigames
    pause: tuple = ()               # extra pause keys in minigames
    confirm: tuple = ()             # extra "OK" keys for menus / minigames (not used in the hub)
    emote: tuple = ()               # wave / celebrate in the hub
    keys: frozenset = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "keys", frozenset(self.move) | frozenset(self.interact)
                           | frozenset(self.inventory) | frozenset(self.item) | frozenset(self.pause)
                           | frozenset(self.confirm) | frozenset(self.emote))

    def label(self, *actions, limit=2):
        """Short readable names of the keys for `actions` ('W/UP'), for on-screen hints."""
        names = []
        for key in (*self.move, *self.interact, *self.inventory, *self.item, *self.pause, *self.confirm):
            if self.action_for(key) in actions:
                name = key_label(key)
                if name not in names:
                    names.append(name)
        return "/".join(names[:limit])

    def action_for(self, key):
        """The logical action `key` triggers for this player, or None:
        up / down / left / right, interact, menu, item, pause. Everything that
        reads input (hub, minigames) speaks these names, not key codes."""
        if key in self.move:
            return DIRECTION_ACTIONS[self.move[key]]
        for action, keys in (("interact", self.interact), ("menu", self.inventory),
                             ("item", self.item), ("pause", self.pause), ("confirm", self.confirm),
                             ("emote", self.emote)):
            if key in keys:
                return action
        return None

    def owns(self, key):
        return key in self.keys

    def direction(self, held):
        """The (dx, dy) of the movement keys in `held`, each axis -1..1."""
        dx = dy = 0
        for key in held:
            vx, vy = self.move[key]
            dx, dy = dx + vx, dy + vy
        return max(-1, min(1, dx)), max(-1, min(1, dy))

    def held_now(self):
        """Movement keys physically down right now (so walking carries on
        through a doorway)."""
        try:
            pressed = pygame.key.get_pressed()
            return [k for k in self.move if pressed[k]]
        except (pygame.error, IndexError):
            return []


WASD = {pygame.K_w: (0, -1), pygame.K_s: (0, 1), pygame.K_a: (-1, 0), pygame.K_d: (1, 0)}
ARROWS = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}

SOLO_CONTROLS = ControlScheme("SOLO", {**WASD, **ARROWS},
                              (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER), (pygame.K_i,),
                              "WASD", "E/ENTER", "I",
                              item=(pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_z, pygame.K_x),
                              pause=(pygame.K_p,), confirm=(pygame.K_RETURN, pygame.K_KP_ENTER),
                              emote=(pygame.K_t,))
