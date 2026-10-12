"""The handcrafted mazes, their parser and the automatic validation. Pure data and logic (no pygame).

Legend:  # wall   . fish treat   o catnip   P cat start   R robot den (robots start here)   space = empty floor
Each layout is written as its LEFT half (columns 0..10, column 10 is the centre) and mirrored, so every maze is
21 x 15 and left-right symmetric. The den has a one-tile door in the middle of its top wall.
"""
from collections import deque
from dataclasses import dataclass, field

COLS, ROWS = 21, 15
DIRS = ((0, -1), (-1, 0), (0, 1), (1, 0))          # up, left, down, right: the fixed order that breaks every tie

LAYOUTS = (
    dict(name="NEON ALLEY", wall=(26, 18, 74), edge=(70, 235, 255), accent=(255, 120, 205), half=(
        "###########",
        "#o........#",
        "#.###.###.#",
        "#.....#....",
        "#.###.#.###",
        "#.....#....",
        "###.#.#.## ",
        "#.....#.#RR",
        "###.#.#.###",
        "#.....#....",
        "#.###.#.###",
        "#.....#....",
        "#.###.###.#",
        "#o........P",
        "###########")),
    dict(name="CIRCUIT GARDEN", wall=(34, 16, 70), edge=(120, 255, 170), accent=(255, 214, 90), half=(
        "###########",
        "#o.......#.",
        "#.##.###...",
        "#.#.......#",
        "#.#.#####.#",
        "#...#......",
        "###.#.#.## ",
        "#.....#.#RR",
        "#.###.#.###",
        "#...#......",
        "#.#.#.##.##",
        "#.#.....#..",
        "#.#.###...#",
        "#o....#...P",
        "###########")),
    dict(name="ROBOT FACTORY", wall=(40, 14, 60), edge=(255, 140, 220), accent=(110, 245, 255), half=(
        "###########",
        "#o....#....",
        "#.###.#.###",
        "#.....#....",
        "#.#.###.#.#",
        "#.#........",
        "#.#.#.#.## ",
        "#.....#.#RR",
        "#.#.#.#.###",
        "#.#.......#",
        "#.#.###.#.#",
        "#.....#....",
        "#.###.#.###",
        "#o........P",
        "###########")),
)


def _mirror(half):
    return tuple(row + row[:-1][::-1] for row in half)


@dataclass(frozen=True)
class Maze:
    name: str
    rows: tuple
    wall_color: tuple
    edge_color: tuple
    accent_color: tuple
    walls: frozenset = field(repr=False, default=frozenset())
    fish: frozenset = field(repr=False, default=frozenset())
    catnip: frozenset = field(repr=False, default=frozenset())
    den: tuple = ()                    # the tiles robots start in
    start: tuple = (0, 0)
    door: tuple = (0, 0)               # the tile just outside the den's door: where a robot steps out to

    def is_open(self, tile):
        c, r = tile
        return 0 <= c < COLS and 0 <= r < ROWS and tile not in self.walls

    def neighbours(self, tile):
        """[(direction, tile)] of the open tiles around `tile`, in the fixed DIRS order."""
        return [(d, (tile[0] + d[0], tile[1] + d[1])) for d in DIRS if self.is_open((tile[0] + d[0], tile[1] + d[1]))]

    @property
    def gate(self):
        """The doorway tile between the den and the corridor above it."""
        return (self.door[0], self.door[1] + 1)

    @property
    def restricted(self):
        """Tiles only robots (leaving, or returning as eyes) may enter: the den and its gate."""
        return frozenset(self.den) | {self.gate}

    def floor(self):
        return [(c, r) for r in range(ROWS) for c in range(COLS) if (c, r) not in self.walls]

    @property
    def corners(self):
        """The floor tile nearest each corner of the maze (top-left, top-right, bottom-right, bottom-left)."""
        floor = [t for t in self.floor() if t not in self.den]
        out = []
        for cc, cr in ((0, 0), (COLS - 1, 0), (COLS - 1, ROWS - 1), (0, ROWS - 1)):
            out.append(min(floor, key=lambda t: (abs(t[0] - cc) + abs(t[1] - cr), t[1], t[0])))
        return tuple(out)


def parse(layout):
    rows = _mirror(layout["half"])
    walls, fish, catnip, den, start = set(), set(), set(), [], None
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == "#":
                walls.add((c, r))
            elif ch == ".":
                fish.add((c, r))
            elif ch == "o":
                catnip.add((c, r))
            elif ch == "R":
                den.append((c, r))
            elif ch == "P":
                start = (c, r)
    door_row = next(r for r, line in enumerate(rows) if "R" in line) - 1
    return Maze(layout["name"], rows, layout["wall"], layout["edge"], layout["accent"], frozenset(walls),
                frozenset(fish), frozenset(catnip), tuple(den), start, (COLS // 2, door_row - 1))


def validate(maze):
    """A list of problems (empty: the maze is sound). Used by the tests and checked once when the module loads."""
    problems = []
    if len(maze.rows) != ROWS or any(len(row) != COLS for row in maze.rows):
        return [f"{maze.name}: not {COLS}x{ROWS}"]
    if maze.start in maze.walls or not maze.den or len(maze.den) < 3:
        problems.append(f"{maze.name}: bad start or den")
        return problems
    open_tiles = set(maze.floor())
    # 1) fully traversable: every floor tile (the den included) is reachable from the cat's start
    seen = reach(maze, maze.start)
    if seen != open_tiles:
        problems.append(f"{maze.name}: unreachable tiles {sorted(open_tiles - seen)}")
    # 2) every collectible is reachable without going through the den
    outside = reach(maze, maze.start, avoid=set(maze.den))
    for what, tiles in (("fish", maze.fish), ("catnip", maze.catnip)):
        lost = sorted(set(tiles) - outside)
        if lost:
            problems.append(f"{maze.name}: {what} not reachable {lost}")
    if len(maze.catnip) < 2:
        problems.append(f"{maze.name}: needs at least 2 catnip")
    # 3) a fair start: no dead end close to the cat, and the den is a real walk away
    dist = distances(maze, maze.start)
    for tile in open_tiles - set(maze.den):
        if len(maze.neighbours(tile)) == 1 and dist.get(tile, 99) <= 6:
            problems.append(f"{maze.name}: dead end {tile} next to the start")
    if dist.get(maze.door, 0) < 10:
        problems.append(f"{maze.name}: the den door is only {dist.get(maze.door)} tiles from the cat")
    if maze.start not in maze.corners and len(maze.neighbours(maze.start)) < 2:
        problems.append(f"{maze.name}: the start is a dead end")
    # 4) several routes: enough loops to run round, and plenty of intersections
    outside_tiles = open_tiles - set(maze.den)
    edges = sum(len(maze.neighbours(t)) for t in outside_tiles) // 2
    if edges - len(outside_tiles) + 1 < 8:
        problems.append(f"{maze.name}: too few loops to escape along")
    if sum(1 for t in outside_tiles if len(maze.neighbours(t)) >= 3) < 10:
        problems.append(f"{maze.name}: too few intersections")
    return problems


def reach(maze, source, avoid=frozenset()):
    seen, queue = {source}, deque([source])
    while queue:
        tile = queue.popleft()
        for _, nxt in maze.neighbours(tile):
            if nxt not in seen and nxt not in avoid:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def distances(maze, source):
    dist, queue = {source: 0}, deque([source])
    while queue:
        tile = queue.popleft()
        for _, nxt in maze.neighbours(tile):
            if nxt not in dist:
                dist[nxt] = dist[tile] + 1
                queue.append(nxt)
    return dist


MAZES = tuple(parse(layout) for layout in LAYOUTS)


def maze_for_level(level):
    """Level 1..3 play the three layouts; after that they repeat (the difficulty keeps rising, see config)."""
    return MAZES[(max(1, level) - 1) % len(MAZES)]
