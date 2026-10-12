"""coin_pusher.py: the physics and the board of NEON COIN PUSHER (no pygame, no profile).

A fixed-step, top-down 2D simulation. Units are "board units"; the stage is W wide and D deep:

    y = 0   back wall            (the chute drops coins just in front of the pusher)
    y = FACE  the pusher face    (a motor sweeps it between FACE_MIN and FACE_MAX)
    y < SIDE_Y   solid side walls
    y >= SIDE_Y  open sides: a coin whose centre passes x < 0 or x > W falls into a LOSS chute
    y = D   the front edge: a coin whose centre passes it falls into the PAYOUT tray

Coins are equal circles (radius R) of equal mass, so the coin type never changes how it moves.
Contacts use position-based separation (4 solver passes) with a little restitution, velocity
damping and sleeping, which keeps piles calm. The pusher is kinematic and resolved last, and
its speed times the step (<0.4) and the speed cap times the step (<1.0) are both far under R,
so nothing tunnels. Everything is deterministic: the same board and the same drops give the
same result, whatever the frame rate (the world only ever advances in whole STEPs).

The World reports what happened as events; the money side lives in coin_pusher_table.py.
"""
import math
import random
from dataclasses import dataclass, field

W, D = 130.0, 96.0
R = 5.5
SIDE_Y = 68.0
FACE_MIN, FACE_MAX = 12.0, 40.0
PUSH_PERIOD = 4.0
STEP = 1 / 60
MAX_STEPS_PER_UPDATE = 6        # a long hitch is dropped, never replayed in one frame
DROP_TIME = 0.34                # a coin falls from the chute to the stage this long
DROP_Y = FACE_MIN + R + 1.0     # where a coin lands when the pusher is back
MAX_COINS = 80                  # on the stage (a drop is refused beyond this)
MAX_PENDING = 3                 # coins still falling from the chute
FRICTION = 4.2                  # exponential velocity damping per second
SLIDE_DECEL = 34.0              # constant "floor friction" in units / s^2
MAX_SPEED = 42.0
SLEEP_SPEED = 1.1
RESTITUTION = 0.28
SOLVER_PASSES = 4
MAX_CORRECTION = 1.6            # the most one pass may move a coin to separate it

NORMAL, SILVER, GOLDEN, MYSTERY = "normal", "silver", "golden", "mystery"
KINDS = (NORMAL, SILVER, GOLDEN, MYSTERY)
KIND_CODE = {NORMAL: "n", SILVER: "s", GOLDEN: "g", MYSTERY: "m"}
CODE_KIND = {v: k for k, v in KIND_CODE.items()}
# a mystery coin's surprise is decided when the coin is made, so closing the machine cannot reroll it
MYSTERY_PRIZES = (("tokens", 2), ("tokens", 2), ("tokens", 2), ("tokens", 4), ("tickets", 3))

# what the machine puts on the stage when it restocks (weights out of 100)
RESTOCK_WEIGHTS = ((NORMAL, 80), (SILVER, 12), (GOLDEN, 3), (MYSTERY, 5))
RESTOCK_BELOW = 30              # fewer coins than this (stage + falling): the machine restocks
RESTOCK_EVERY = 0.9             # seconds between restock coins


def pusher_face(t):
    """The pusher face's depth at motor time t (starts fully back, smooth at both ends)."""
    mid, amp = (FACE_MIN + FACE_MAX) / 2, (FACE_MAX - FACE_MIN) / 2
    return mid - amp * math.cos(2 * math.pi * t / PUSH_PERIOD)


def pusher_speed(t):
    amp = (FACE_MAX - FACE_MIN) / 2
    return amp * 2 * math.pi / PUSH_PERIOD * math.sin(2 * math.pi * t / PUSH_PERIOD)


def make_coin_spec(rng, weights=RESTOCK_WEIGHTS):
    """(kind, prize) for one new machine coin. prize is only set for MYSTERY."""
    pick = rng.uniform(0, sum(w for _, w in weights))
    for kind, weight in weights:
        pick -= weight
        if pick <= 0:
            break
    prize = rng.choice(MYSTERY_PRIZES) if kind == MYSTERY else None
    return kind, prize


class Coin:
    __slots__ = ("x", "y", "vx", "vy", "kind", "prize", "age", "sleep", "uid", "z")

    def __init__(self, x, y, kind=NORMAL, prize=None, uid=0):
        self.x, self.y, self.vx, self.vy = x, y, 0.0, 0.0
        self.kind, self.prize, self.uid = kind, prize, uid
        self.age = 0.0
        self.sleep = 0.0
        self.z = 0.0

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)


@dataclass
class Drop:
    """A coin still falling from the chute. It joins the physics when `land_at` is reached."""
    x: float
    kind: str
    prize: tuple
    land_at: float
    born: float
    paid: bool = True       # a player's coin (False: restocked by the machine)


@dataclass
class Event:
    kind: str                   # "tray" | "lost" | "land" | "clink" | "restock"
    coin: Coin = None
    side: int = 0               # for "lost": -1 left, +1 right
    strength: float = 0.0       # for "clink"
    x: float = 0.0
    y: float = 0.0


@dataclass
class Falling:
    """A coin on its way down (already settled): only the picture still needs it."""
    kind: str
    x: float
    y: float
    side: int               # 0: into the tray; -1/+1: into a side chute
    age: float = 0.0
    prize: tuple = None


class PusherWorld:
    def __init__(self, coins=(), drops=(), time=0.0):
        self.coins = list(coins)
        self.drops = list(drops)
        self.falling = []
        self.time = time            # game time, for the drop-in animation
        self.motor = 0.0            # pusher motor time (the pusher always starts fully back)
        self._acc = 0.0
        self._uid = max([c.uid for c in self.coins], default=0) + 1
        self._clink_cool = 0.0
        self.last_clink = 0.0

    # ------------------------------------------------------------ pusher
    @property
    def face(self):
        return pusher_face(self.motor)

    @property
    def face_speed(self):
        return pusher_speed(self.motor)

    @property
    def count(self):
        return len(self.coins) + len(self.drops)

    def can_accept(self):
        return len(self.drops) < MAX_PENDING and self.count < MAX_COINS

    # ------------------------------------------------------------ adding coins
    def add_drop(self, x, kind=NORMAL, prize=None, paid=True):
        x = min(W - R, max(R, float(x)))
        self.drops.append(Drop(x, kind, prize, self.time + DROP_TIME, self.time, paid))

    def _land(self, drop):
        y = max(DROP_Y, self.face + R + 0.3)
        coin = Coin(drop.x, y, drop.kind, drop.prize, self._uid)
        self._uid += 1
        coin.vy = 6.0               # a coin that has just dropped, still settling
        self.coins.append(coin)
        return Event("land", coin, x=coin.x, y=coin.y)

    def flush_drops(self):
        """Land every coin still falling from the chute at once (leaving / saving)."""
        events = [self._land(d) for d in self.drops]
        self.drops.clear()
        return events

    def place(self, x, y, kind=NORMAL, prize=None):
        """Put a settled coin on the stage (loading a board)."""
        coin = Coin(min(W - R, max(R, x)), min(D - 1.0, max(self.face + R, y)), kind, prize, self._uid)
        self._uid += 1
        self.coins.append(coin)
        return coin

    # ------------------------------------------------------------ stepping
    def advance(self, dt):
        """Advance the world by dt seconds in whole STEPs. Returns the events, in order."""
        self._acc += max(0.0, dt)
        events, steps = [], 0
        while self._acc >= STEP - 1e-9:        # (the epsilon keeps 1/30 s frames at exactly two steps)
            self._acc = max(0.0, self._acc - STEP)
            steps += 1
            if steps > MAX_STEPS_PER_UPDATE:
                self._acc = 0.0         # drop the backlog instead of spiralling
                break
            self.step(events)
        return events

    def step(self, events):
        self.time += STEP
        self.motor += STEP
        for f in self.falling:
            f.age += STEP
        self.falling = [f for f in self.falling if f.age < 0.6]
        self._clink_cool = max(0.0, self._clink_cool - STEP)
        ready = [d for d in self.drops if d.land_at <= self.time]
        if ready:
            self.drops = [d for d in self.drops if d.land_at > self.time]
            for d in ready:
                events.append(self._land(d))
        face, pv = self.face, self.face_speed
        damp = math.exp(-FRICTION * STEP)
        for c in self.coins:
            c.age += STEP
            c.vx *= damp
            c.vy *= damp
            sp = math.hypot(c.vx, c.vy)
            if sp > 0:
                k = max(0.0, sp - SLIDE_DECEL * STEP) / sp
                c.vx, c.vy = c.vx * k, c.vy * k
                if sp > MAX_SPEED:
                    c.vx, c.vy = c.vx * MAX_SPEED / sp, c.vy * MAX_SPEED / sp
            c.x += c.vx * STEP
            c.y += c.vy * STEP
        loudest = 0.0
        for _ in range(SOLVER_PASSES):
            loudest = max(loudest, self._collide_pairs())
            for c in self.coins:
                self._walls(c)
                if c.y - R < face:      # the pusher face is kinematic and wins
                    c.y = face + R
                    if c.vy < pv:
                        c.vy = pv
                        loudest = max(loudest, abs(pv) * 0.4)
                    c.sleep = 0.0
        self._sleep()
        if loudest > 2.5 and self._clink_cool <= 0:
            self._clink_cool = 0.09
            events.append(Event("clink", strength=min(1.0, loudest / 14)))
        self._edges(events)

    # ------------------------------------------------------------ contacts
    def _collide_pairs(self):
        grid = {}
        size = 2 * R
        for c in self.coins:
            grid.setdefault((int(c.x // size), int(c.y // size)), []).append(c)
        loudest = 0.0
        min_d2 = size * size
        for (gx, gy), cell in grid.items():
            near = []
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 1)):
                other = grid.get((gx + dx, gy + dy))
                if other:
                    near.append((dx, dy, other))
            for dx, dy, other in near:
                for i, a in enumerate(cell):
                    for j, b in enumerate(other):
                        if dx == 0 and dy == 0 and j <= i:
                            continue
                        ddx, ddy = b.x - a.x, b.y - a.y
                        d2 = ddx * ddx + ddy * ddy
                        if d2 >= min_d2:
                            continue
                        loudest = max(loudest, self._resolve(a, b, ddx, ddy, d2))
        return loudest

    def _resolve(self, a, b, dx, dy, d2):
        if d2 < 1e-9:       # exactly on top of each other: a deterministic nudge
            ang = (a.uid * 2.399963 + b.uid) % (2 * math.pi)
            dx, dy, d2 = math.cos(ang) * 0.01, math.sin(ang) * 0.01, 1e-4
        d = math.sqrt(d2)
        nx, ny = dx / d, dy / d
        push = min(MAX_CORRECTION, (2 * R - d) * 0.5)
        a.x -= nx * push
        a.y -= ny * push
        b.x += nx * push
        b.y += ny * push
        rel = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny      # < 0: approaching
        loud = 0.0
        if rel < 0:
            e = RESTITUTION if -rel > 6 else 0.0
            j = -(1 + e) * rel / 2
            a.vx -= j * nx
            a.vy -= j * ny
            b.vx += j * nx
            b.vy += j * ny
            loud = -rel
        a.sleep = b.sleep = 0.0
        return loud

    def _walls(self, c):
        if c.y < SIDE_Y:
            if c.x < R:
                c.x = R
                c.vx = abs(c.vx) * 0.3
            elif c.x > W - R:
                c.x = W - R
                c.vx = -abs(c.vx) * 0.3
        if c.y < R:
            c.y = R
            c.vy = abs(c.vy) * 0.3

    def _sleep(self):
        for c in self.coins:
            if c.speed < SLEEP_SPEED:
                c.sleep += STEP
                if c.sleep > 0.15:
                    c.vx = c.vy = 0.0
            else:
                c.sleep = 0.0

    def _edges(self, events):
        """Coins past an edge leave the stage. A coin is removed from `coins` in the very
        step it is reported, so it can never be reported (or paid) twice."""
        keep = []
        for c in self.coins:
            if c.y > D:
                self.falling.append(Falling(c.kind, c.x, c.y, 0, prize=c.prize))
                events.append(Event("tray", c, x=c.x, y=c.y))
            elif c.y >= SIDE_Y and (c.x < 0 or c.x > W):
                side = -1 if c.x < 0 else 1
                self.falling.append(Falling(c.kind, c.x, c.y, side, prize=c.prize))
                events.append(Event("lost", c, side=side, x=c.x, y=c.y))
            else:
                keep.append(c)
        self.coins = keep

    # ------------------------------------------------------------ board (de)serialisation
    def snapshot(self):
        """Everything that must survive a restart, as plain JSON data. Velocities are not
        kept: a saved board is at rest (coins that were mid-slide stop where they are)."""
        def prize(p):
            return [p[0], p[1]] if p else None
        return {
            "coins": [[round(c.x, 2), round(c.y, 2), KIND_CODE[c.kind], prize(c.prize)] for c in self.coins],
            "drops": [[round(d.x, 2), KIND_CODE[d.kind], prize(d.prize), d.paid] for d in self.drops],
        }

    @classmethod
    def from_snapshot(cls, data):
        """Rebuild a world from snapshot(); None if the data is not usable. Bad entries are
        skipped, coins are pulled inside the stage and out of the pusher's reach."""
        if not isinstance(data, dict) or not isinstance(data.get("coins"), list):
            return None
        world = cls()
        for row in data["coins"][:MAX_COINS]:
            parsed = _parse_coin(row)
            if parsed:
                x, y, kind, prize = parsed
                world.place(x, y, kind, prize)
        for row in (data.get("drops") or [])[:MAX_PENDING * 2]:
            if (isinstance(row, list) and len(row) >= 3 and _num(row[0]) and row[1] in CODE_KIND):
                kind = CODE_KIND[row[1]]
                world.add_drop(row[0], kind, _parse_prize(row[2], kind), paid=bool(row[3]) if len(row) > 3 else True)
        world.relax()
        return world

    def relax(self, passes=40):
        """Settle small overlaps (a freshly loaded board) without letting anything leave."""
        for _ in range(passes):
            self._collide_pairs()
            for c in self.coins:
                self._walls(c)
                c.y = max(c.y, self.face + R)
                c.y = min(c.y, D - 0.5)
                c.x = min(W - 0.5, max(0.5, c.x)) if c.y >= SIDE_Y else c.x
        for c in self.coins:
            c.vx = c.vy = 0.0


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _parse_prize(raw, kind):
    if kind != MYSTERY:
        return None
    if (isinstance(raw, list) and len(raw) == 2 and raw[0] in ("tokens", "tickets")
            and isinstance(raw[1], int) and not isinstance(raw[1], bool) and 1 <= raw[1] <= 5):
        return (raw[0], raw[1])
    return MYSTERY_PRIZES[0]


def _parse_coin(row):
    if not (isinstance(row, list) and len(row) >= 3 and _num(row[0]) and _num(row[1]) and row[2] in CODE_KIND):
        return None
    kind = CODE_KIND[row[2]]
    return row[0], row[1], kind, _parse_prize(row[3] if len(row) > 3 else None, kind)


def initial_board(seed):
    """The first board of a profile: a loose hex-packed block in front of the pusher with
    a handful of special coins, fully decided by `seed` (so it is the same on every run)."""
    rng = random.Random(f"coin-pusher-board:{seed}")
    world = PusherWorld()
    weights = ((NORMAL, 80), (SILVER, 11), (GOLDEN, 3), (MYSTERY, 6))
    row = 0
    y = 51.6
    while y <= 92.0:
        shift = R if row % 2 else 0.0
        x = R + 1.0 + shift
        while x <= W - R - 1.0:
            kind, prize = make_coin_spec(rng, weights)
            lean = rng.uniform(0.0, 3.6) if y > 88 else 0.0      # the front row teeters on the edge
            world.place(x + rng.uniform(-0.6, 0.6), y + lean + rng.uniform(-0.6, 0.6), kind, prize)
            x += 2 * R + 0.8
        y += 2 * R * 0.87 + 0.4
        row += 1
    world.relax()
    return world
