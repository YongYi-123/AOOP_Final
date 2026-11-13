"""THE FORGOTTEN CORRIDOR: a walled-up service passage behind NEON CAT MAZE's top-left corner. Pure rules (no pygame).

The package stays hub-agnostic. Whoever runs the game says whether the corridor may exist at all
(CatMazeGame.secret_enabled) and whether it is already there from the first level (secret_ready: the ACE route was
earned before, or enough meaningful tries were made; the hub keeps that in the profile). Otherwise a run earns it by
skill: once ACE_LEVELS_CLEARED levels are COMPLETED in one run, the game reports "unlocked" and the corridor is there
from the next level on.

While it is available, the outer wall beside the top-left corner (GATE) only shows a faint hairline crack. Nothing
announces it. The cat must walk into that crack: the old wall crumbles (`revealed`) and a narrow passage leads down the
left margin to a dead end. Only the cat may walk it: robots path on the maze itself, so they never follow. On the
dead end's wall hangs an old plaque, dusty until the cat reaches it: reaching the end is the discovery, and the plaque
lights up as a golden STAR engraved with the Roman numeral I (drawn by the renderer, in the world, never as a pop-up).
The numeral is the symbol's place in Chapter 02's three-symbol lock.

Every layout has floor in its top-left corner (1, 1) and a solid outer wall at (0, 1), so the same crack works in each
maze.

A run that ends in GAME OVER (all lives lost, not a restart or a quit) after scoring at least TRY_MIN_SCORE is a
"meaningful try": the game reports it and the hub decides what (if anything) it counts towards.
"""
from .mazes import COLS, ROWS

GATE = (0, 1)                                           # the outer-wall tile beside the top-left corner that cracks
TILES = ((0, 1), (-1, 1), (-1, 2), (-1, 3), (-1, 4))    # the gate, then the passage down the left margin
ENTRANCE = (1, 1)                                       # the corner tile in front of the gate
END = TILES[-1]
PLAQUE = (-1, 5)                                        # the dead end's wall, where the plaque hangs
ACE_LEVELS_CLEARED = 3                                  # skill route: COMPLETE level 3 (three levels cleared in a run)
TRY_MIN_SCORE = 600                                     # a game over with at least this many points is a real try
OPEN_SECONDS = 1.2                                      # how long the wall takes to crumble once found (drawing only)
SYMBOL = "STAR"                                         # what the plaque at the end shows ...
NUMERAL = "I"                                           # ... and its place in the lock (engraved beside it)
STAR_PIXELS = ("....#....",                             # the engraving, 9 x 9 (renderer draws it at any scale)
               "....#....",
               "...###...",
               "#########",
               ".#######.",
               "..#####..",
               "..##.##..",
               ".##...##.",
               ".#.....#.")
NUMERAL_PIXELS = ("###", ".#.", ".#.", ".#.", ".#.", ".#.", "###")     # a Roman I, 3 x 7


class Corridor:
    """The passage of one level. `revealed` turns True when the cat first walks into the cracked wall; `found` (once)
    when it reaches the end."""

    def __init__(self, revealed=False):
        self.tiles = frozenset(TILES)
        self.age = 0.0                                  # seconds since it was revealed
        self.revealed = revealed
        self.found = False
        self.visits = 0                                 # how often the cat has stood at the end (drawing)

    @property
    def opening(self):
        """0..1 while the old wall crumbles (only drawn). 0 while it is still a hairline crack."""
        return min(1.0, self.age / OPEN_SECONDS) if self.revealed else 0.0

    def update(self, dt):
        if self.revealed:
            self.age += dt

    def reveal(self, tile):
        """The cat stands on `tile`. True only the first time it pushes into the cracked wall."""
        if self.revealed or tile != GATE:
            return False
        self.revealed = True
        return True

    def contains(self, tile):
        return tile in self.tiles

    def visit(self, tile):
        """The cat stands on `tile`. True only the first time it reaches the end."""
        if tile != END:
            return False
        self.visits += 1
        if self.found:
            return False
        self.found = True
        return True


class CorridorMaze:
    """The maze as the CAT sees it while the corridor is open: the passage tiles are floor too."""

    def __init__(self, maze, corridor):
        self.maze, self.corridor = maze, corridor
        self.restricted = maze.restricted

    def is_open(self, tile):
        return self.corridor.contains(tile) or self.maze.is_open(tile)


def inside_grid(tile):
    return 0 <= tile[0] < COLS and 0 <= tile[1] < ROWS
