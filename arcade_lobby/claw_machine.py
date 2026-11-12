"""NEON CLAW - KITTY CATCHER: the claw machine's rules and money, without any drawing (claw_scene.py draws it).

The play field is the inside of the glass, measured in screen pixels: x runs from the left wall (0) to FIELD_W,
y is how far the claw's tips hang below the gantry (0 = parked at the top, FLOOR_Y = the floor the plushies sit on).
The prize chute is the hole at the left, x < CHUTE_W; the claw is parked above it.

One attempt, in phases:
    IDLE     waiting. start() charges CLAW_PLAY_COST Tokens exactly once (refused, nothing charged, without them).
    AIM      the player slides the claw left / right (smooth: it speeds up and slows down); drop() or the timer drops it.
    DROP     the claw falls until its tips touch the plushie under it (or the floor).
    GRAB     the prongs close. The outcome is rolled ONCE here (grab_odds), from how centred the claw is.
    LIFT     the claw rises. A grab that failed lets the plushie slip back down on the way up.
    CARRY    the claw slides home over the chute.
    RELEASE  the prongs open; a held plushie falls into the chute.
    WON / LOST  a short result; then IDLE again, and an empty spot is restocked.

Money: ClawGame is the only code that moves currency. start() spends the Tokens; a prize is paid in _settle(), which
runs once per attempt (the attempt carries a `settled` flag), only after the plushie is really in the chute.
Tickets use profile.award_prize_tickets (lifetime Tickets, but not an Arcade Floor win for the story) and the
plushie goes into the bag as a stackable collectible (item_registry), inside
one profile.batch(), so the save holds both or neither. Key presses only ask; mashing cannot pay or charge twice.

Hidden prizes (later): a PlushSpec with hidden=True never appears in the normal stock. A `special` object passed to
ClawGame can place one (special.stock(game, slot) -> PlushSpec or None) and hears about wins
(special.on_win(game, spec, profile)); the machine itself needs no other change. Nothing uses this yet.
"""
import random
from dataclasses import dataclass, field

from settings import (CLAW_AIM_TIME, CLAW_GRIP_EDGE, CLAW_GRIP_FAIR, CLAW_PLAY_COST,
                      CLAW_PLUSH_TICKETS)

REASON = "CLAW MACHINE"
GAME_ID = "claw_machine"

# ---- the field (screen pixels)
FIELD_W = 220
FLOOR_Y = 112               # where the plushies' feet are, below the gantry
CHUTE_W = 36                # the prize hole on the left
HOME_X = CHUTE_W / 2        # where the claw parks (over the chute)
MIN_X = HOME_X              # the claw may hover anywhere from the chute ...
MAX_X = FIELD_W - 12        # ... to just short of the right wall
SLOTS = (60, 88, 116, 144, 172, 200)    # where the plushies sit (centres)

# ---- motion
MOVE_SPEED = 62.0           # px/s at full speed
MOVE_ACCEL = 480.0          # px/s^2: a tap nudges, a hold glides (letting go at full speed coasts ~4 px)
DROP_SPEED = 78.0
LIFT_SPEED = 52.0
CARRY_SPEED = 70.0
GRAB_TIME = 0.45
RELEASE_TIME = 0.35
WIN_TIME = 1.8
LOSE_TIME = 1.3
PRONG_REACH = 4             # how far past a plushie's side a prong can still catch it
GRIP_DEPTH = 8              # how far below a plushie's top the prongs reach when they close
FALL_GRAVITY = 420.0

IDLE, AIM, DROP, GRAB, LIFT, CARRY, RELEASE, WON, LOST = (
    "idle", "aim", "drop", "grab", "lift", "carry", "release", "won", "lost")
BUSY = (AIM, DROP, GRAB, LIFT, CARRY, RELEASE, WON, LOST)


@dataclass(frozen=True)
class PlushSpec:
    """One kind of plushie. `item_id` is its collectible in item_registry; its Ticket value lives in settings."""
    item_id: str
    name: str
    width: int
    height: int
    grip: float                 # chance a CENTRED grab holds all the way to the chute
    weight: int                 # how often it is stocked
    look: dict = field(default_factory=dict, hash=False, compare=False)
    hidden: bool = False        # a special prize: never stocked by the ordinary machine

    @property
    def tickets(self):
        return CLAW_PLUSH_TICKETS.get(self.item_id, 0)


PLUSHIES = (
    PlushSpec("claw_plush_berry", "BERRY KITTY", 16, 14, 0.9, 30,
              dict(kind="cat", body=(255, 140, 190), dark=(214, 86, 150), accent=(255, 230, 240), eye=(60, 20, 50))),
    PlushSpec("claw_plush_snowball", "SNOWBALL", 16, 14, 0.9, 30,
              dict(kind="cat", body=(240, 240, 255), dark=(184, 186, 222), accent=(255, 160, 200), eye=(40, 60, 120))),
    PlushSpec("claw_plush_marmalade", "MARMALADE", 16, 15, 0.86, 24,
              dict(kind="tabby", body=(255, 170, 80), dark=(214, 112, 40), accent=(255, 236, 200), eye=(70, 40, 20))),
    PlushSpec("claw_plush_midnight", "MIDNIGHT KITTY", 16, 15, 0.84, 14,
              dict(kind="cat", body=(64, 60, 110), dark=(40, 36, 76), accent=(150, 240, 255), eye=(255, 220, 110))),
    PlushSpec("claw_plush_bunny", "NEON BUNNY", 14, 19, 0.78, 14,
              dict(kind="bunny", body=(196, 160, 255), dark=(146, 106, 222), accent=(255, 190, 230), eye=(50, 30, 90))),
    PlushSpec("claw_plush_chonk", "BIG CHONK", 22, 16, 0.7, 6,
              dict(kind="chonk", body=(170, 176, 204), dark=(120, 124, 160), accent=(255, 200, 220), eye=(40, 40, 70))),
)
PLUSH_BY_ID = {p.item_id: p for p in PLUSHIES}


def grab_odds(offset, spec):
    """The chance a grab `offset` px from the plushie's centre carries it to the chute.

    Centred (within ~45% of its half-width, at least 3 px) keeps the plushie's own grip; anywhere else over it keeps
    CLAW_GRIP_FAIR of that; a prong just catching its side (PRONG_REACH px beyond it) CLAW_GRIP_EDGE; further off, 0."""
    half = spec.width / 2
    offset = abs(offset)
    if offset <= max(3.0, half * 0.45):
        return spec.grip
    if offset <= half:
        return spec.grip * CLAW_GRIP_FAIR
    if offset <= half + PRONG_REACH:
        return CLAW_GRIP_EDGE
    return 0.0


def default_stock(rng, specs=PLUSHIES):
    """A weighted pick among the ordinary plushies (hidden prizes are never stocked here)."""
    pool = [s for s in specs if not s.hidden]
    return rng.choices(pool, weights=[s.weight for s in pool])[0]


class Plush:
    """One plushie in the machine: what it is, where it sits, and (while it moves) how it is falling."""
    __slots__ = ("spec", "x", "y", "vy", "wobble", "slot")

    def __init__(self, spec, x, slot=None):
        self.spec, self.x, self.slot = spec, float(x), slot
        self.y = float(FLOOR_Y)             # its feet
        self.vy = 0.0
        self.wobble = 0.0

    @property
    def top(self):
        return self.y - self.spec.height


class Attempt:
    """One paid try. `settled` makes paying it a one-time thing."""
    __slots__ = ("number", "target", "odds", "holds", "slip_at", "settled", "won", "tickets", "item_added")

    def __init__(self, number):
        self.number = number
        self.target = None          # the Plush under the claw at the drop
        self.odds = 0.0
        self.holds = False          # rolled once, at the grab
        self.slip_at = None         # claw depth where a failed grab lets go on the way up
        self.settled = False
        self.won = False
        self.tickets = 0
        self.item_added = False


class ClawGame:
    """The claw machine for one profile. Feed it update(dt, direction) every frame; ask it to start() / drop()."""

    def __init__(self, profile, rng=None, special=None, cost=CLAW_PLAY_COST, aim_time=CLAW_AIM_TIME):
        self.profile = profile
        self.rng = rng or random.Random()
        self.special = special
        self.cost = cost
        self.aim_time = aim_time
        self.phase = IDLE
        self.phase_time = 0.0
        self.x = HOME_X             # claw centre
        self.y = 0.0                # claw depth (its tips)
        self.vx = 0.0
        self.open = 1.0             # prongs: 1 open .. 0 shut
        self.held = None            # the Plush hanging in the prongs
        self.falling = []           # plushies dropping back to the floor
        self.in_chute = None        # the Plush dropping into the chute (until the result is shown)
        self.attempt = None         # the current (or last) Attempt
        self.attempts = 0
        self.wins = 0
        self.session_tickets = 0
        self.events = []            # what happened this frame, for sounds: "start", "move", "drop", "grab", ...
        self.plushies = [Plush(self._stock(i), x, i) for i, x in enumerate(SLOTS)]

    # ------------------------------------------------------------ queries
    @property
    def busy(self):
        return self.phase in BUSY

    @property
    def aim_left(self):
        return max(0.0, self.aim_time - self.phase_time) if self.phase == AIM else 0.0

    def can_start(self):
        return self.phase == IDLE and self.profile.can_afford_tokens(self.cost)

    def start_block_reason(self):
        if self.phase != IDLE:
            return "BUSY"
        if not self.profile.can_afford_tokens(self.cost):
            return "NO TOKENS"
        return None

    def target_under(self, x=None):
        """The plushie a drop at `x` would land on: the nearest one a prong can reach, or None."""
        x = self.x if x is None else x
        best = None
        for p in self.plushies:
            offset = abs(p.x - x)
            if offset <= p.spec.width / 2 + PRONG_REACH and (best is None or offset < abs(best.x - x)):
                best = p
        return best

    def take_events(self):
        """What happened since the last call (for sounds and effects), oldest first."""
        events, self.events = self.events, []
        return events

    # ------------------------------------------------------------ actions
    def start(self):
        """Pay for one attempt and hand the claw to the player. False (nothing charged) if refused."""
        if not self.can_start():
            return False
        with self.profile.batch():
            if not self.profile.spend_tokens(self.cost, REASON):
                return False
        self.attempts += 1
        self.attempt = Attempt(self.attempts)
        self.in_chute = None
        self._enter(AIM)
        self.events.append("start")
        return True

    def drop(self):
        """Let go of the joystick: the claw falls. Only while aiming (a second press does nothing)."""
        if self.phase != AIM:
            return False
        self.vx = 0.0
        self.attempt.target = self.target_under()
        self._enter(DROP)
        self.events.append("drop")
        return True

    def finish(self, limit=2000, dt=1 / 60):
        """Play the current attempt out at once (leaving the machine mid-attempt): a claw still being aimed drops where
        it is, and a prize won on the way is paid exactly as if the player had watched. Returns the Attempt."""
        if self.phase == AIM:
            self.drop()
        for _ in range(limit):
            if self.phase == IDLE:
                break
            self.update(dt)
        self.events.clear()
        return self.attempt

    # ------------------------------------------------------------ motion
    def update(self, dt, direction=0):
        self.phase_time += dt
        self._update_falling(dt)
        if self.phase == AIM:
            self._aim(dt, direction)
            if self.phase_time >= self.aim_time:
                self.drop()
        elif self.phase == DROP:
            stop = self._stop_depth()
            self.y = min(stop, self.y + DROP_SPEED * dt)
            if self.y >= stop:
                self._enter(GRAB)
                self._roll()
                self.events.append("grab")
        elif self.phase == GRAB:
            shut = self._shut_level()
            self.open = max(shut, 1.0 - (1.0 - shut) * self.phase_time / GRAB_TIME)
            if self.phase_time >= GRAB_TIME:
                target = self.attempt.target
                if target is not None and self.attempt.odds > 0:
                    self.held = target                  # it comes up with the claw, for now
                    self.plushies.remove(target)
                self._enter(LIFT)
                self.events.append("lift")
        elif self.phase == LIFT:
            self.y = max(0.0, self.y - LIFT_SPEED * dt)
            if self.held is not None:
                self._hang()
                slip = self.attempt.slip_at
                if not self.attempt.holds and slip is not None and self.y <= slip:
                    self._let_slip()
            if self.y <= 0:
                self._enter(CARRY)
        elif self.phase == CARRY:
            step = CARRY_SPEED * dt
            self.x = max(HOME_X, self.x - step) if self.x > HOME_X else min(HOME_X, self.x + step)
            if self.held is not None:
                self._hang()
            if abs(self.x - HOME_X) < 1e-6:
                self._enter(RELEASE)
                if self.held is not None:
                    self.in_chute, self.held = self.held, None
                    self.in_chute.vy = 0.0
                    self.events.append("release")
        elif self.phase == RELEASE:
            self.open = min(1.0, self.open + dt / RELEASE_TIME)
            if self.in_chute is not None:
                self.in_chute.vy += FALL_GRAVITY * dt
                self.in_chute.y += self.in_chute.vy * dt
            if self.phase_time >= RELEASE_TIME:
                won = self.in_chute is not None
                self._settle(won)
                self._enter(WON if won else LOST)
                self.events.append("win" if won else "lose")
        elif self.phase in (WON, LOST):
            if self.in_chute is not None:
                self.in_chute.vy += FALL_GRAVITY * dt
                self.in_chute.y += self.in_chute.vy * dt
            if self.phase_time >= (WIN_TIME if self.phase == WON else LOSE_TIME):
                self.in_chute = None
                self._restock()
                self._enter(IDLE)
                self.events.append("ready")

    def _aim(self, dt, direction):
        want = max(-1, min(1, direction)) * MOVE_SPEED
        if self.vx < want:
            self.vx = min(want, self.vx + MOVE_ACCEL * dt)
        elif self.vx > want:
            self.vx = max(want, self.vx - MOVE_ACCEL * dt)
        if self.vx:
            self.x += self.vx * dt
            if self.x <= MIN_X or self.x >= MAX_X:
                self.x = min(MAX_X, max(MIN_X, self.x))
                self.vx = 0.0
            else:
                self.events.append("move")

    def _stop_depth(self):
        target = self.attempt.target
        if target is None:
            return float(FLOOR_Y)
        return min(float(FLOOR_Y), target.top + GRIP_DEPTH)   # the prongs close round the plushie's head

    def _shut_level(self):
        target = self.attempt.target
        if target is None or self.attempt.odds <= 0:
            return 0.0
        return 0.35 if self.attempt.holds else 0.5         # a good grip squeezes tighter

    def _roll(self):
        """The one random moment of an attempt: will this grab hold? (and if not, where does it slip?)"""
        a = self.attempt
        target = a.target
        if target is None:
            return
        a.odds = grab_odds(self.x - target.x, target.spec)
        if a.odds <= 0:
            return
        a.holds = self.rng.random() < a.odds
        if not a.holds:
            # a weak catch drops at once, a decent one wiggles free part way up
            a.slip_at = self.y * (0.85 if a.odds <= CLAW_GRIP_EDGE else self.rng.uniform(0.25, 0.7))

    def _hang(self):
        p = self.held
        p.x = self.x
        p.y = self.y - GRIP_DEPTH + p.spec.height     # held round the head, inside the prongs
        p.wobble = (p.wobble + 0.25) % 6.283

    def _let_slip(self):
        p, self.held = self.held, None
        p.vy = 0.0
        home = SLOTS[p.slot] if p.slot is not None else p.x       # it tumbles back to (about) its own spot
        p.x = home + self.rng.uniform(-2.0, 2.0)
        self.falling.append(p)
        self.events.append("slip")

    def _update_falling(self, dt):
        for p in list(self.falling):
            p.vy += FALL_GRAVITY * dt
            p.y = min(float(FLOOR_Y), p.y + p.vy * dt)
            if p.y >= FLOOR_Y:
                p.vy = 0.0
                self.falling.remove(p)
                self.plushies.append(p)
                self.events.append("thud")

    # ------------------------------------------------------------ money
    def _settle(self, won):
        a = self.attempt
        if a is None or a.settled:
            return
        a.settled = True
        if not won:
            return
        spec = self.in_chute.spec
        with self.profile.batch():
            if spec.tickets:
                self.profile.award_prize_tickets(spec.tickets)
            try:
                a.item_added = self.profile.inventory.add_item(spec.item_id) > 0
            except ValueError:              # not in the registry (a future prize registered elsewhere): tickets only
                a.item_added = False
        a.won, a.tickets = True, spec.tickets
        self.wins += 1
        self.session_tickets += spec.tickets
        if self.special is not None and hasattr(self.special, "on_win"):
            self.special.on_win(self, spec, self.profile)

    # ------------------------------------------------------------ stock
    def _stock(self, slot):
        if self.special is not None and hasattr(self.special, "stock"):
            spec = self.special.stock(self, slot)
            if spec is not None:
                return spec
        return default_stock(self.rng)

    def _restock(self):
        """Fill every empty spot with a new plushie (the machine never runs dry)."""
        taken = {p.slot for p in self.plushies}
        for i, x in enumerate(SLOTS):
            if i not in taken:
                self.plushies.append(Plush(self._stock(i), x, i))

    def _enter(self, phase):
        self.phase, self.phase_time = phase, 0.0
        if phase == IDLE:
            self.open, self.y, self.x, self.vx = 1.0, 0.0, HOME_X, 0.0
