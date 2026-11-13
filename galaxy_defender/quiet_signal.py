"""THE QUIET SIGNAL: a faded, non-hostile ship that drifts across the sky in the calm between two waves. Pure rules.

The package stays hub-agnostic. Whoever runs the game says whether the ship may appear at all
(GalaxyGame.secret_enabled) and whether it is already due (secret_ready: the ACE route was earned before, or enough
meaningful tries were made; the hub keeps that in the profile). Otherwise a run earns it by skill: once the run has
CLEARED wave ACE_WAVES_CLEARED (the second MOTHERSHIP), the game reports "unlocked" and the ship comes from the very
next calm on.

Once it is due it is NOT a one-off: it crosses in EVERY calm between two waves (and in the calm before wave 1) until it
has been tuned in. While it crosses, the next wave waits for it, but only for as long as it is crossing: it never stops
and always leaves the screen after about nine seconds, so the wave always comes (no soft-lock, no endless wait). A ship
that leaves untuned simply comes back in the next calm, or in a later game. It never shoots, it cannot be hit (lasers
pass straight through) and touching it does nothing. It sends a pale beam straight down; staying inside the beam for
TUNE_SECONDS tunes the fighter's radio in, and the ship projects a glowing hologram above itself for as long as it is
still on screen: a crescent MOON marked with the Roman numeral II (its place in Chapter 02's three-symbol lock). That is
the discovery: drawn in the world, never as a pop-up.

A run that ends in GAME OVER (the ship destroyed or the line breached, not a restart or a quit) after scoring at least
TRY_MIN_SCORE is a "meaningful try": the game reports it and the hub decides what (if anything) it counts towards.
"""
from . import config as cfg

ACE_WAVES_CLEARED = 10          # skill route: clear wave 10, the second MOTHERSHIP
TRY_MIN_SCORE = 250             # a game over after this many points counts as a real try (wave 1 cleared and more)
Y = 70                          # its height on screen
WIDTH, HEIGHT = 34, 12
SPEED = 46.0                    # px/s: about nine seconds across
BEAM_HALF = 16                  # the beam's half-width at the fighter's height
TUNE_SECONDS = 1.1              # in the beam this long: the message comes through
DETUNE_RATE = 0.6               # out of the beam the tuning fades this fast (a brush past does not reset it)
SYMBOL = "MOON"                 # the hologram it projects once tuned in ...
NUMERAL = "II"                  # ... and its place in the lock, marked beside it
MOON_PIXELS = ("...####..",     # a crescent, 9 x 9 (the renderer draws it at any scale)
               ".#####...",
               ".####....",
               "####.....",
               "####.....",
               "####.....",
               ".####....",
               ".#####...",
               "...####..")
NUMERAL_PIXELS = ("#####", ".#.#.", ".#.#.", ".#.#.", ".#.#.", ".#.#.", "#####")    # a Roman II, 5 x 7


class Signal:
    """One crossing of the quiet ship. update() returns "received" exactly once, the moment it is tuned in."""

    def __init__(self, from_left=True):
        self.dir = 1 if from_left else -1
        self.x = -WIDTH if from_left else cfg.FIELD_W + WIDTH
        self.y = float(Y)
        self.tuned = 0.0
        self.received = False
        self.age = 0.0

    @property
    def gone(self):
        return (self.dir > 0 and self.x > cfg.FIELD_W + WIDTH) or (self.dir < 0 and self.x < -WIDTH)

    @property
    def strength(self):
        """0..1: how far the radio is tuned in."""
        return 1.0 if self.received else min(1.0, self.tuned / TUNE_SECONDS)

    def in_beam(self, player_x):
        return abs(player_x - self.x) <= BEAM_HALF and 0 <= self.x <= cfg.FIELD_W

    def update(self, dt, player_x):
        self.age += dt
        self.x += self.dir * SPEED * dt
        if self.received:
            return None
        if self.in_beam(player_x):
            self.tuned += dt
            if self.tuned >= TUNE_SECONDS:
                self.received = True
                return "received"
        else:
            self.tuned = max(0.0, self.tuned - DETUNE_RATE * dt)
        return None

    @property
    def projecting(self):
        """Is the MOON hologram showing? Only once tuned in (and for as long as the ship is still on screen)."""
        return self.received and not self.gone
