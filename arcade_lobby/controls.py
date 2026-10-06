"""Data-driven key bindings. A ControlScheme says which keys one local player
uses; nothing else in the game names a movement / interact / bag key, so a
binding is changed here (or by building a scheme from a settings file later).

SOLO is the one-player scheme and keeps the original bindings (WASD *and* the
arrow keys, E, I). In a two-player session each player gets a scheme whose keys
do not overlap, so both can use the one keyboard.
"""
from dataclasses import dataclass, field

import pygame


@dataclass(frozen=True, eq=False)
class ControlScheme:
    name: str
    move: dict                      # key -> (dx, dy)
    interact: tuple                 # keys that press E-style "use"
    inventory: tuple                # keys that open the bag
    move_hint: str = ""             # short labels for the controls box
    interact_hint: str = ""
    inventory_hint: str = ""
    keys: frozenset = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "keys", frozenset(self.move) | frozenset(self.interact)
                           | frozenset(self.inventory))

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

SOLO_CONTROLS = ControlScheme("SOLO", {**WASD, **ARROWS}, (pygame.K_e,), (pygame.K_i,),
                              "WASD", "E", "I")
P1_CONTROLS = ControlScheme("P1", dict(WASD), (pygame.K_e,), (pygame.K_i,), "WASD", "E", "I")
P2_CONTROLS = ControlScheme("P2", dict(ARROWS), (pygame.K_RETURN, pygame.K_RCTRL, pygame.K_KP_ENTER),
                            (pygame.K_o,), "ARROWS", "ENTER", "O")

# how many local players -> one scheme per player
SCHEMES = {1: (SOLO_CONTROLS,), 2: (P1_CONTROLS, P2_CONTROLS)}


def schemes_for(player_count):
    try:
        return SCHEMES[player_count]
    except KeyError:
        raise ValueError(f"no control schemes for {player_count} players") from None
