"""pinball.py: the physics and the rules of LUCKY CAT PINBALL (no pygame, no profile).

A fixed-step 2D simulation in table units (1 unit = 1 canvas pixel, y grows downwards):

    the table is W x H; the playfield is x < LANE_X, the plunger lane is LANE_X..W
    a top arc turns the launched ball into the playfield, a divider keeps it out of the lane
    below the flippers is the drain (y > DRAIN_Y inside the playfield)

The ball is a circle of radius R. Everything it touches - walls, rails, posts, bumpers,
the C-A-T targets and the two flippers - is a segment / circle it is pushed out of, with a
little restitution; bumpers add a kick and a moving flipper adds its own surface speed. The
world only ever advances in whole STEPs (240 Hz) and uses no random numbers, so the same
inputs always give the same table, whatever the frame rate. The speed cap times STEP stays
under the ball radius, so nothing tunnels.

The world scores and reports what happened as events; the Token / Ticket side of a run lives
in pinball_table.py.

Run flow:  idle -> start_run() -> ready (ball in the plunger lane) -> play (ball launched)
           -> bonus (ball drained, end-of-ball bonus on show) -> ready again ... -> over
"""
import math

W, H = 140.0, 236.0
LANE_X = 122.0                  # the divider between the playfield and the plunger lane
R = 3.5                         # ball radius
STEP = 1 / 240
MAX_STEPS_PER_UPDATE = 40       # a long hitch is dropped, never replayed in one frame
GRAVITY = 330.0                 # the table is tilted: units / s^2
DAMPING = 0.12                  # exponential speed loss per second
MAX_SPEED = 560.0
WALL_E, POST_E, TARGET_E, FLIPPER_E = 0.42, 0.55, 0.5, 0.45
REST_SPEED = 28.0               # below this a bounce is perfectly soft (the ball rolls instead of buzzing)
BUMPER_KICK = 250.0             # the bumper pushes the ball off at least this fast
BUMPER_R = 8.0
DRAIN_Y = H + 8
LAUNCH_MIN, LAUNCH_MAX = 245.0, 585.0
PULL_TIME = 0.85                # seconds to fully pull the plunger back
PLUNGER_REST = (LANE_X + (W - LANE_X) / 2, H - 6 - R)

BALLS = 3
LUCKY_TIME = 12.0               # seconds of play that LUCKY CAT MODE lasts
BONUS_TIME = 2.4                # the end-of-ball bonus stays on show this long
CAT_FLASH = 1.0                 # the CAT letters flash this long, then reset
SCOOP_HOLD = 0.9
SCOOP_EJECTS = ((95.0, -330.0), (150.0, -300.0), (45.0, -345.0))      # taken in turn, so the ball never repeats one path
STUCK_AFTER = 2.0               # seconds: a ball that has hardly moved this long gets a nudge

# ---- scoring
BUMPER_POINTS, LUCKY_BUMPER_POINTS = 100, 250
LANE_POINTS, LANE_REPEAT_POINTS, LANES_DONE_POINTS = 250, 50, 1000
TARGET_POINTS, TARGET_REPEAT_POINTS = 300, 50
CAT_POINTS, CAT_STEP, CAT_MAX = 3000, 1000, 6000
SCOOP_POINTS, LUCKY_SCOOP_POINTS = 1000, 2000       # only while the scoop is lit (see below); an unlit scoop pays SCOOP_UNLIT
BONUS_PER_BUMPER, BONUS_PER_TARGET, BONUS_BUMPER_CAP = 50, 100, 40
SCOOP_UNLIT = 100
MAX_MULT = 4

# ---- the table
POSTS = [(48.0, 30.0), (70.0, 30.0), (92.0, 30.0)]          # the posts between the two top lanes
POST_R = 2.0
LANES = [(52.0, 24.0, 14.0, 14.0), (74.0, 24.0, 14.0, 14.0)]   # x, y, w, h of the rollover sensors
BUMPERS = [(61.0, 58.0), (36.0, 84.0), (86.0, 84.0), (61.0, 110.0)]
SCOOP = (13.0, 122.0)
SCOOP_R = 5.0
TARGET_LETTERS = "CAT"
TARGETS = [((121.0, 98.0), (121.0, 110.0)), ((121.0, 114.0), (121.0, 126.0)), ((121.0, 130.0), (121.0, 142.0))]
WALL_R = 1.5


def _arc():
    cx, cy, r = W / 2, W / 2, W / 2
    pts = [(cx + r * math.cos(math.pi + math.pi * i / 18), cy + r * math.sin(math.pi + math.pi * i / 18)) for i in range(19)]
    return [(pts[i], pts[i + 1]) for i in range(18)]


WALLS = _arc() + [
    ((0.0, W / 2), (0.0, H + 20)),                           # left wall (the left outlane runs down it)
    ((W, W / 2), (W, H)),                                    # right wall (the plunger lane's outer side)
    ((LANE_X, 92.0), (LANE_X, H - 6)),                       # the divider
    ((LANE_X, H - 6), (W, H - 6)),                           # the plunger's floor
    ((10.0, 150.0), (21.0, 194.0)),                          # inlane guides: ball above rolls to the flipper,
    ((LANE_X - 10.0, 150.0), (LANE_X - 21.0, 194.0)),        # ball beside them goes down the outlane
    ((8.0, 46.0), (24.0, 60.0)),                             # the two shelves under the top corners
    ((LANE_X - 8.0, 46.0), (LANE_X - 24.0, 60.0)),
]
# the floor of the outlane on each side is open: that is the drain
# a one-way gate on top of the plunger lane: a ball going up passes, a ball coming back down slides off it into the playfield
GATE = ((LANE_X, 92.0), (W, 80.0))

FLIPPER_L = 28.0                # length
FLIPPER_R = 3.2                 # half thickness (the ball touches a capsule)
FLIPPER_REST, FLIPPER_UP = 0.49, -0.49          # radians below / above horizontal
TAP_HOLD = 0.07                 # seconds
FLIPPER_SPEED = 22.0            # radians / second
PIVOTS = {-1: (24.0, 200.0), 1: (LANE_X - 24.0, 200.0)}


class Event:
    """What just happened: kind, where, how many points (0 = none), and a little extra."""
    __slots__ = ("kind", "x", "y", "points", "extra")

    def __init__(self, kind, x=0.0, y=0.0, points=0, extra=None):
        self.kind, self.x, self.y, self.points, self.extra = kind, x, y, points, extra

    def __repr__(self):
        return f"Event({self.kind!r}, points={self.points}, extra={self.extra!r})"


class Flipper:
    def __init__(self, side):
        self.side = side                    # -1 left, +1 right
        self.pivot = PIVOTS[side]
        self.angle = FLIPPER_REST
        self.omega = 0.0
        self.pressed = False
        self.min_up = 0.0               # a quick tap still swings the flipper up for at least this long

    def direction(self, angle=None):
        """Unit vector from the pivot to the tip. The left flipper (side -1) points to the right."""
        a = self.angle if angle is None else angle
        return (-self.side * math.cos(a), math.sin(a))

    def tip(self, angle=None):
        dx, dy = self.direction(angle)
        return (self.pivot[0] + dx * FLIPPER_L, self.pivot[1] + dy * FLIPPER_L)

    def update(self):
        self.min_up = max(0.0, self.min_up - STEP)
        goal = FLIPPER_UP if self.pressed or self.min_up > 0 else FLIPPER_REST
        step = FLIPPER_SPEED * STEP
        new = self.angle + max(-step, min(step, goal - self.angle))
        self.omega = (new - self.angle) / STEP
        self.angle = new

    @property
    def raised(self):
        """0 (resting) .. 1 (fully up)."""
        return (FLIPPER_REST - self.angle) / (FLIPPER_REST - FLIPPER_UP)


def closest_on_segment(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
    return ax + dx * t, ay + dy * t, t


class PinballWorld:
    def __init__(self):
        self.flippers = {-1: Flipper(-1), 1: Flipper(1)}
        self.acc = 0.0
        self.time = 0.0
        self.phase = "idle"             # idle / ready / play / bonus / over
        self.score = 0
        self.ball_no = 0
        self.lucky_left = 0.0
        self.pull = 0.0                 # plunger pulled back 0..1
        self.pulling = False
        self.bumper_flash = [0.0] * len(BUMPERS)
        self.target_flash = [0.0] * len(TARGETS)
        self.cat_flash = 0.0
        self.last_bonus = None          # (bumpers, targets, mult, total) of the latest end-of-ball bonus
        self.bonus_left = 0.0
        self.reset_run_state()
        self.bx = self.by = self.vx = self.vy = 0.0
        self.captured = 0.0             # time left held in the scoop (0 = free)
        self.scoop_cool = 0.0
        self.tick_cool = 0.0
        self.slow = 0.0
        self.nudges = 0
        self.in_lane = [False, False]

    def reset_run_state(self):
        self.lanes = [False, False]
        self.targets = [False, False, False]
        self.scoop_lit = True           # lit at the start of every ball; scoring it darkens it until a lane set or CAT relights it
        self.mult = 1
        self.cats = 0                   # C-A-T completions this run
        self.ball_bumpers = 0
        self.ball_targets = 0
        self.stats = {"bumpers": 0, "lanes": 0, "targets": 0, "cats": 0, "scoops": 0, "lucky": 0}

    # ------------------------------------------------------------ run control
    def start_run(self, score=0):
        self.score = score
        self.ball_no = 1
        self.lucky_left = 0.0
        self.cat_flash = 0.0
        self.reset_run_state()
        self._load_ball()
        return [Event("ball_start", extra=1)]

    def _load_ball(self):
        self.phase = "ready"
        self.bx, self.by = PLUNGER_REST
        self.vx = self.vy = 0.0
        self.captured = 0.0
        self.scoop_cool = 0.0
        self.slow = 0.0
        self.pull, self.pulling = 0.0, False
        self.ball_bumpers = 0
        self.ball_targets = 0
        self.mult = 1
        self.scoop_lit = True
        self.in_lane = [False, False]

    def end_run(self):
        """Stop the run where it stands (the player left): no ball, no more points."""
        self.phase = "over"
        self.lucky_left = 0.0
        self.pulling = False

    def set_flippers(self, left, right):
        """The flipper buttons. A fresh press also shifts the lit top lanes (lane change)."""
        events = []
        for side, pressed in ((-1, left), (1, right)):
            f = self.flippers[side]
            if pressed and not f.pressed:
                f.min_up = TAP_HOLD
                events.append(Event("flipper", extra=side))
                if self.phase in ("ready", "play"):
                    self.lanes.reverse()
            f.pressed = bool(pressed)
        return events

    # ------------------------------------------------------------ plunger
    def can_launch(self):
        return (self.phase in ("ready", "play") and self.captured <= 0 and self.bx > LANE_X
                and self.by > H - 24 and math.hypot(self.vx, self.vy) < 40)

    def hold_plunger(self, held):
        """Pull the plunger back while the button is held; releasing it launches. Returns events."""
        if held:
            if self.can_launch():
                self.pulling = True
            return []
        if not self.pulling:
            return []
        self.pulling = False
        return self.launch()

    def launch(self):
        pull = self.pull
        self.pull = 0.0
        if not self.can_launch():
            return []
        pull = max(0.12, pull)
        self.vx, self.vy = 0.0, -(LAUNCH_MIN + (LAUNCH_MAX - LAUNCH_MIN) * pull)
        self.phase = "play"
        self.slow = 0.0
        return [Event("launch", self.bx, self.by, 0, extra=pull)]

    # ------------------------------------------------------------ simulation
    def advance(self, dt):
        """Run the whole steps that fit in dt; returns the events in order."""
        self.acc = min(self.acc + dt, STEP * MAX_STEPS_PER_UPDATE)
        events = []
        while self.acc >= STEP:
            self.acc -= STEP
            self._step(events)
        return events

    def _step(self, events):
        self.time += STEP
        for f in self.flippers.values():
            f.update()
        for lst in (self.bumper_flash, self.target_flash):
            for i, v in enumerate(lst):
                lst[i] = max(0.0, v - STEP)
        self.tick_cool = max(0.0, self.tick_cool - STEP)
        if self.pulling:
            self.pull = min(1.0, self.pull + STEP / PULL_TIME)
        if self.cat_flash > 0:
            self.cat_flash -= STEP
            if self.cat_flash <= 0:
                self.targets = [False, False, False]
        if self.phase == "bonus":
            self.bonus_left -= STEP
            if self.bonus_left <= 0:
                self._next_ball(events)
            return
        if self.phase not in ("ready", "play"):
            return
        if self.phase == "play" and self.lucky_left > 0:
            self.lucky_left -= STEP
            if self.lucky_left <= 0:
                self.lucky_left = 0.0
                events.append(Event("lucky_end"))
        if self.captured > 0:
            self.captured -= STEP
            if self.captured <= 0:
                self.captured = 0.0
                self.scoop_cool = 0.7
                self.vx, self.vy = SCOOP_EJECTS[self.stats["scoops"] % len(SCOOP_EJECTS)]
                events.append(Event("eject", self.bx, self.by))
            return
        self.scoop_cool = max(0.0, self.scoop_cool - STEP)
        self._move_ball(events)

    def _move_ball(self, events):
        resting_in_lane = self.phase == "ready" or (self.bx > LANE_X and self.by > H - 24 and abs(self.vy) < 3)
        self.vy += GRAVITY * STEP
        k = 1.0 - DAMPING * STEP
        self.vx *= k
        self.vy *= k
        speed = math.hypot(self.vx, self.vy)
        if speed > MAX_SPEED:
            self.vx, self.vy = self.vx * MAX_SPEED / speed, self.vy * MAX_SPEED / speed
        self.bx += self.vx * STEP
        self.by += self.vy * STEP
        hit = False
        for a, b in WALLS:
            hit |= self._bounce_segment(a, b, WALL_R, WALL_E, events, rail=True)
        if self.vy > 0 and self.by < GATE[0][1] + (GATE[1][1] - GATE[0][1]) * (self.bx - GATE[0][0]) / (GATE[1][0] - GATE[0][0]):
            self._bounce_segment(*GATE, WALL_R, WALL_E, events, rail=True)
        for px, py in POSTS:
            hit |= self._bounce_point(px, py, POST_R, POST_E, events, rail=True)
        self._bumpers(events)
        self._targets(events)
        for f in self.flippers.values():
            self._flipper(f, events)
        self._sensors(events)
        if self.phase == "play" and not resting_in_lane:
            self._anti_stuck()
        if self.phase == "play" and (self.by > DRAIN_Y and self.bx < LANE_X or not self._finite()):
            self._drain(events)

    def _finite(self):
        return all(math.isfinite(v) for v in (self.bx, self.by, self.vx, self.vy)) and self.by < H + 60

    def _tick(self, events, impact):
        if impact > 130 and self.tick_cool <= 0:
            self.tick_cool = 0.07
            events.append(Event("rail", self.bx, self.by, 0, extra=impact))

    def _bounce_segment(self, a, b, radius, e, events, rail=False):
        cx, cy, _ = closest_on_segment(self.bx, self.by, a, b)
        return self._push_out(cx, cy, radius, e, events, rail)

    def _bounce_point(self, px, py, radius, e, events, rail=False):
        return self._push_out(px, py, radius, e, events, rail)

    def _push_out(self, cx, cy, radius, e, events, rail=False, surface=(0.0, 0.0)):
        dx, dy = self.bx - cx, self.by - cy
        dist = math.hypot(dx, dy)
        if dist >= R + radius:
            return False
        if dist < 1e-6:
            dx, dy, dist = 0.0, -1.0, 1.0
        nx, ny = dx / dist, dy / dist
        self.bx, self.by = cx + nx * (R + radius), cy + ny * (R + radius)
        rvx, rvy = self.vx - surface[0], self.vy - surface[1]
        vn = rvx * nx + rvy * ny
        if vn < 0:
            if rail:
                self._tick(events, -vn)
            bounce = 0.0 if -vn < REST_SPEED else e
            rvx -= (1 + bounce) * vn * nx
            rvy -= (1 + bounce) * vn * ny
            self.vx, self.vy = rvx + surface[0], rvy + surface[1]
        return True

    def _bumpers(self, events):
        for i, (px, py) in enumerate(BUMPERS):
            dx, dy = self.bx - px, self.by - py
            dist = math.hypot(dx, dy)
            if dist >= R + BUMPER_R:
                continue
            if dist < 1e-6:
                dx, dy, dist = 0.0, -1.0, 1.0
            nx, ny = dx / dist, dy / dist
            self.bx, self.by = px + nx * (R + BUMPER_R), py + ny * (R + BUMPER_R)
            vn = self.vx * nx + self.vy * ny
            if vn < BUMPER_KICK:
                self.vx += (BUMPER_KICK - vn) * nx
                self.vy += (BUMPER_KICK - vn) * ny
            if self.bumper_flash[i] <= 0.04:
                points = LUCKY_BUMPER_POINTS if self.lucky_left > 0 else BUMPER_POINTS
                self.bumper_flash[i] = 0.18
                self._score(points)
                self.ball_bumpers += 1
                self.stats["bumpers"] += 1
                events.append(Event("bumper", px, py, points, extra=i))

    def _targets(self, events):
        for i, (a, b) in enumerate(TARGETS):
            if self.cat_flash > 0:
                continue
            if self._bounce_segment(a, b, WALL_R, TARGET_E, events):
                lit = self.targets[i]
                points = TARGET_REPEAT_POINTS if lit else TARGET_POINTS
                self.targets[i] = True
                self.target_flash[i] = 0.25
                self._score(points)
                if not lit:
                    self.ball_targets += 1
                    self.stats["targets"] += 1
                events.append(Event("target", (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, points, extra=i))
                if all(self.targets):
                    self._cat_complete(events)

    def _cat_complete(self, events):
        points = min(CAT_MAX, CAT_POINTS + CAT_STEP * self.cats)
        self.cats += 1
        self.stats["cats"] += 1
        self._score(points)
        self.cat_flash = CAT_FLASH
        self.scoop_lit = True
        events.append(Event("cat", 61.0, 150.0, points, extra=self.cats))
        if self.lucky_left <= 0:
            self.stats["lucky"] += 1
            events.append(Event("lucky_start", extra=LUCKY_TIME))
        self.lucky_left = LUCKY_TIME

    def _flipper(self, f, events):
        tip = f.tip()
        cx, cy, t = closest_on_segment(self.bx, self.by, f.pivot, tip)
        dx, dy = self.bx - cx, self.by - cy
        if math.hypot(dx, dy) >= R + FLIPPER_R:
            return
        s = t * FLIPPER_L
        a = f.angle
        # surface velocity of the flipper at the touching point (omega is d(angle)/dt)
        sx, sy = f.side * s * f.omega * math.sin(a), s * f.omega * math.cos(a)
        before = self.vx * self.vx + self.vy * self.vy
        self._push_out(cx, cy, FLIPPER_R, FLIPPER_E, events, surface=(sx, sy))
        if abs(f.omega) > 3 and self.vx * self.vx + self.vy * self.vy > before + 400:
            events.append(Event("flip_hit", self.bx, self.by, 0, extra=f.side))

    def _sensors(self, events):
        for i, (x, y, w, h) in enumerate(LANES):
            inside = x <= self.bx <= x + w and y <= self.by <= y + h
            if inside and not self.in_lane[i]:
                lit = self.lanes[i]
                points = LANE_REPEAT_POINTS if lit else LANE_POINTS
                self.lanes[i] = True
                self._score(points)
                if not lit:
                    self.stats["lanes"] += 1
                events.append(Event("lane", x + w / 2, y + h / 2, points, extra=i))
                if all(self.lanes):
                    self.lanes = [False, False]
                    self.mult = min(MAX_MULT, self.mult + 1)
                    self.scoop_lit = True
                    self._score(LANES_DONE_POINTS)
                    events.append(Event("lanes_done", 61.0, 44.0, LANES_DONE_POINTS, extra=self.mult))
            self.in_lane[i] = inside
        if self.scoop_cool <= 0 and math.hypot(self.bx - SCOOP[0], self.by - SCOOP[1]) < SCOOP_R:
            self.bx, self.by = SCOOP
            self.vx = self.vy = 0.0
            self.captured = SCOOP_HOLD
            points = (LUCKY_SCOOP_POINTS if self.lucky_left > 0 else SCOOP_POINTS) if self.scoop_lit else SCOOP_UNLIT
            self.scoop_lit = False
            self._score(points)
            self.stats["scoops"] += 1
            events.append(Event("scoop", SCOOP[0], SCOOP[1], points))

    def _anti_stuck(self):
        if math.hypot(self.vx, self.vy) < 10:
            self.slow += STEP
            if self.slow >= STUCK_AFTER:
                self.slow = 0.0
                self.nudges += 1
                self.vx, self.vy = (70.0 if self.nudges % 2 else -70.0), -150.0
        else:
            self.slow = 0.0

    def _score(self, points):
        self.score += points

    def _drain(self, events):
        bonus = (min(self.ball_bumpers, BONUS_BUMPER_CAP) * BONUS_PER_BUMPER
                 + self.ball_targets * BONUS_PER_TARGET) * self.mult
        self.last_bonus = (self.ball_bumpers, self.ball_targets, self.mult, bonus)
        self._score(bonus)
        self.phase = "bonus"
        self.bonus_left = BONUS_TIME
        self.vx = self.vy = 0.0
        events.append(Event("drain", self.bx, H - 4, bonus, extra=self.ball_no))

    def _next_ball(self, events):
        if self.ball_no >= BALLS:
            self.phase = "over"
            self.lucky_left = 0.0
            events.append(Event("run_over", points=self.score))
            return
        self.ball_no += 1
        self._load_ball()
        events.append(Event("ball_start", extra=self.ball_no))
