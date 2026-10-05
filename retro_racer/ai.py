"""AIDriver: the brain of a computer racer. It turns what it can see into keyboard-style controls.

    controls = driver.drive(car, field, dt)     ->  {"accelerate": bool, "brake": bool, "steer": -1..1}

The pseudo-3D road already gives the racing path (track position + lane offset + curvature), so there is no
path-finding: the driver keeps a preferred lane, looks a short way ahead for slower cars, shifts lane to
overtake, slows for tight bends, and makes small human-like mistakes. It also decides when to use its item.
"""
import random
import settings as S
from difficulty import DEFAULT_DIFFICULTY

LANES = (-0.66, 0.0, 0.66)
CLEAR_ENOUGH = 0.5           # lateral gap (road half-widths) that counts as "room to pass"


class AIDriver:
    """skill 0..1 (speed + tidiness), aggression 0..1 (how early it goes for a pass),
    line = preferred lane, reaction = seconds between decisions."""

    def __init__(self, skill, aggression, line, reaction, rng=None, difficulty=DEFAULT_DIFFICULTY):
        self.skill, self.aggression, self.line, self.reaction = skill, aggression, line, reaction
        self.difficulty = difficulty
        self.rng = rng or random.Random()
        self.target = line            # lane it is steering for right now
        self.noise = 0.0              # small lateral error (imperfection)
        self.timer = self.rng.uniform(0.0, reaction)
        self.brake_for = None         # speed of the car it is stuck behind
        self.item_wait = self.rng.uniform(0.6, 2.5) * difficulty.item_delay
        self.item_check = 0.0
        self.act_in = None            # seconds until a decided item use actually happens (reaction lag)
        self.wasting = False          # the decision was a poor one (fires the item regardless of advice)
        self.recovering = False       # RECOVERING state: got knocked off line, priority is getting back
        self.calm = 0.0               # short lockout on lane changes right after recovering
        self.top_fraction = (difficulty.pace[0] + difficulty.pace[1] * skill) * difficulty.speed   # share of top speed it dares to use

    # ---- decisions (every `reaction` seconds) ---------------------------------------------------
    def _think(self, car, field):
        speed = max(car.speed, 1500.0)
        look = 2500.0 + speed * 0.6
        ahead = field.obstacles_ahead(car, look)
        slower = [(d, o) for d, o in ahead if o.speed < car.speed * 1.05 + 300]
        self.brake_for = None
        if self.recovering:                 # no overtaking, no lane-hopping while getting back on the road
            self.target = max(-0.5, min(0.5, self.line))
            return
        can_change = self.calm <= 0.0       # ... and no chain of lane changes straight after recovering

        blockers = [(d, o) for d, o in slower if abs(o.x - self.target) < 0.42]
        if blockers and can_change:
            dist, obstacle = min(blockers, key=lambda t: t[0])
            if dist < 2200 + 2600 * self.aggression:              # aggressive drivers start the pass earlier
                best, best_score = None, -9.0
                for lane in LANES + (self.line,):
                    clearance = min([abs(lane - o.x) for d, o in slower if d < 2500] or [9.0])   # only near-term traffic matters
                    score = min(clearance, 1.0) - 0.15 * abs(lane - self.target)   # prefer small lane changes
                    if clearance > CLEAR_ENOUGH and score > best_score:
                        best, best_score = lane, score
                if best is not None:
                    self.target = best
        elif can_change and not any(abs(o.x - self.line) < 0.5 for d, o in slower):
            self.target = self.line                                  # pass done: return to the racing line

        # still stuck behind someone in our lane? brake only if we are actually closing on them
        stuck = [(d, o) for d, o in slower if abs(o.x - self.target) < 0.42]
        if stuck:
            dist, obstacle = min(stuck, key=lambda t: t[0])
            if dist < 300.0 + max(0.0, car.speed - obstacle.speed) * 0.6:
                self.brake_for = obstacle.speed

        # imperfection: small wobble, and now and then a lapse of attention
        sloppy = min(1.0, (1.0 - self.skill) * self.difficulty.mistakes)
        self.noise = self.rng.uniform(-0.25, 0.25) * sloppy
        if self.rng.random() < 0.10 * sloppy:
            self.timer += self.reaction * 2.5
            self.noise += self.rng.uniform(-0.3, 0.3)

    # ---- per-frame controls ---------------------------------------------------------------------
    def _update_recovery(self, car, dt):
        """NORMAL <-> RECOVERING. Entered when well off the road (or hurt and drifting); left once back on it."""
        off = abs(car.x)
        self.calm = max(0.0, self.calm - dt)
        if not self.recovering and (off > 1.1 or (car.has_hostile_effect() and off > 0.9)):
            self.recovering = True
        elif self.recovering and off < 0.75 and not car.has_effect("spin"):
            self.recovering = False
            self.calm = 1.2

    def drive(self, car, field, dt):
        self._update_recovery(car, dt)
        self.timer -= dt
        if self.timer <= 0:
            self._think(car, field)
            self.timer = self.reaction * self.rng.uniform(0.8, 1.3)

        sr = car.speed_ratio
        curve_here = field.road.segment_at(car.front_z).curve
        curve_ahead = field.road.segment_at(car.front_z + 900).curve
        lane = 0.0 if self.recovering else self.target + self.noise        # recovering: head for the middle
        ff = curve_here * (S.CENTRIFUGAL / car.spec.centrifugal_resistance) * sr / car.spec.steering
        gain = 2.4 if self.recovering else 4.0                             # ... smoothly, not with a snap
        steer = max(-1.0, min(1.0, gain * (lane - car.x) + ff))

        target_speed = car.max_speed * self.top_fraction * (1.0 + field.catch_up(car))
        # Corner speed: the fastest ratio at which steering can still cancel the centrifugal push
        # (feed-forward <= margin). Better drivers dare a bigger margin, so weaker ones run wide more often.
        tightest = max(abs(curve_here), abs(curve_ahead), abs(field.road.segment_at(car.front_z + 1800).curve))
        if tightest > 0.5:
            margin = self.difficulty.cornering[0] + self.difficulty.cornering[1] * self.skill + self.difficulty.corner_margin
            limit = margin * car.spec.steering * car.spec.centrifugal_resistance / (S.CENTRIFUGAL * tightest)
            target_speed = min(target_speed, max(0.32, limit) * S.MAX_SPEED)
        if self.recovering:
            # keep just under the off-road slowdown limit: fast enough to steer with, slow enough not to be dragged down
            target_speed = min(target_speed, S.OFFROAD_LIMIT * 0.95) if abs(car.x) > 1.0 else target_speed * 0.85
        over = car.speed > target_speed * 1.12                             # arcade braking into a bend
        brake = over or (self.brake_for is not None and car.speed > self.brake_for * 1.1)
        accelerate = car.speed < target_speed and not brake
        return {"accelerate": accelerate, "brake": brake, "steer": steer}

    # ---- items ----------------------------------------------------------------------------------
    def maybe_use_item(self, car, field, dt):
        """Ask the held item whether now is a good time (each item knows its own situation)."""
        if car.item is None:
            self.act_in, self.wasting = None, False
            return
        if self.act_in is not None:              # decided already: wait out the reaction lag, then act
            self.act_in -= dt
            if self.act_in <= 0:
                self.act_in = None
                if self.wasting or car.item.advice(car, field) or car.item_age > 14.0:      # still a good idea?
                    field.items.use(car, field)
                self.wasting = False
            return
        self.item_check -= dt
        if car.item_age < self.item_wait or self.item_check > 0:
            return
        self.item_check = 0.5
        good = car.item.advice(car, field) or car.item_age > 14.0             # never sit on an item forever
        self.wasting = (not good) and self.rng.random() < 0.15 * self.difficulty.item_waste
        if good or self.wasting:
            self.act_in = self.rng.uniform(0.1, 0.5) * self.difficulty.item_delay
