"""THE OLD SPECTATOR TICKET: a ticket stub from the empty stands, found after a match. Pure rules (no pygame).

The package stays hub-agnostic. Whoever runs the game says whether the ticket may appear at all
(VolleyGame.secret_enabled) and whether it is already due (secret_ready: the ACE route was earned before, or enough
meaningful tries were made; the hub keeps that in the profile). Otherwise a match earns it by skill: BEATING Sandra
(the game's only CPU opponent) reports "unlocked".

It never appears during a rally, so it can never touch the match, its score, its controls or Sandra. Once it is due,
after every COMPLETED match (won or lost), until it has been found, a short scene plays before the result card: an old
stub slips out of the stands and flutters into the player's cat's paws (that moment is the discovery: "found"), then
it is held up large for a moment, showing ADMIT ONE, a PAW PRINT and the Roman numeral III (the symbol's place in
Chapter 02's three-symbol lock), and finally it is pinned over the stands and the result card comes up as usual. It is
drawn in the world, never as a pop-up. Leaving before it reaches the cat skips it for now: it comes after the next
completed match.

A match you LOSE (played to the end, not restarted or left) after scoring at least TRY_MIN_POINTS is a "meaningful
try": the game reports it and the hub decides what (if anything) it counts towards.
"""
import math

from .court import FLOOR

TRY_MIN_POINTS = 1              # a lost match with at least this many points counts as a real try
START = (54.0, 120.0)           # where it slips out of the stands
FLY_SECONDS = 0.75              # ... fluttering into the cat's paws
SHOW_SECONDS = 1.5              # ... held up large in the middle of the court
SETTLE_SECONDS = 0.45           # ... and pinned over the stands; then the result card
TOTAL_SECONDS = FLY_SECONDS + SHOW_SECONDS + SETTLE_SECONDS
SWAY = 9.0                      # px of side-to-side flutter while it flies
W, H = 10, 5                    # the small stub
PINNED = (26, 50, 72, 38)       # where it ends up: over the stands, above the result card (x, y, w, h)
HEADER = "ADMIT ONE"            # printed at the top of the stub
SYMBOL = "PAW"                  # the print in its middle ...
NUMERAL = "III"                 # ... and its place in the lock, printed beside it
PAW_PIXELS = ("......##.....",  # an outlined paw print, 13 x 13: three toe beans and the big pad, hollow
              ".....#..#....",  # (the renderer draws it at any scale)
              ".....#..#....",
              ".##..#..#.##.",
              "#..#..##.#..#",
              "#..#.....#..#",
              ".##.......##.",
              "....#####....",
              "...#.....#...",
              "..#.......#..",
              "..#.......#..",
              "...#.....#...",
              "....#####....")
PAW_AT, NUMERAL_AT = (5, 11), (34, 17)    # where the print sits on the stub (pixels, at scale 2 / at scale 2)
NUMERAL_PIXELS = ("#######", ".#.#.#.", ".#.#.#.", ".#.#.#.", ".#.#.#.", ".#.#.#.", "#######")   # a Roman III, 7 x 7


class OldTicket:
    """The ticket scene after one match. update() returns "found" exactly once, when the stub reaches the cat."""

    def __init__(self):
        self.age = 0.0
        self.x, self.y = START
        self.found = False

    @property
    def phase(self):
        """"fly", "show", "settle" or "pinned"."""
        if self.age < FLY_SECONDS:
            return "fly"
        if self.age < FLY_SECONDS + SHOW_SECONDS:
            return "show"
        return "settle" if self.age < TOTAL_SECONDS else "pinned"

    @property
    def blocking(self):
        """While it plays, the result card (and a rematch) waits."""
        return self.age < TOTAL_SECONDS

    @property
    def settle(self):
        """0..1 while it shrinks onto its pin."""
        return min(1.0, max(0.0, (self.age - FLY_SECONDS - SHOW_SECONDS) / SETTLE_SECONDS))

    def update(self, dt, cat):
        self.age += dt
        if self.found:
            return None
        k = min(1.0, self.age / FLY_SECONDS)
        ease = k * k * (3 - 2 * k)
        tx, ty = (cat.x, cat.y - 12) if cat is not None else START
        self.x = START[0] + (tx - START[0]) * ease + math.sin(self.age * 9) * SWAY * (1 - k)
        self.y = START[1] + (ty - START[1]) * ease
        if k >= 1.0:
            self.found = True
            return "found"
        return None
