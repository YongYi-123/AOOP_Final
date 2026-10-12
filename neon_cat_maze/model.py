"""The simulation: grid movers, the cat, the robots and one Run (lives, score, levels). No pygame.

Movement is tile based and advanced in fixed STEP slices, so a run plays out identically at 30, 60 or 144 fps. A mover
only ever changes direction while it stands exactly on a tile centre (the single exception is turning round), which
makes wall collisions exact and corner clipping impossible."""
import math
from collections import namedtuple

from . import ai
from . import config as cfg
from .mazes import maze_for_level
from .pathing import distance_field
from .settlement import RunResult

Event = namedtuple("Event", "name x y amount kind", defaults=(0, ""))
STOP = (0, 0)


def neg(d):
    return (-d[0], -d[1])


class Mover:
    """A thing on the grid: standing on `tile`, moving towards tile+dir, `t` (0..1) of the way there."""

    def __init__(self, tile, facing=(1, 0)):
        self.tile, self.dir, self.t, self.facing = tile, STOP, 0.0, facing

    @property
    def pos(self):
        return self.tile[0] + self.dir[0] * self.t, self.tile[1] + self.dir[1] * self.t

    def nearest_tile(self):
        x, y = self.pos
        return math.floor(x + 0.5), math.floor(y + 0.5)

    def place(self, tile, facing=None):
        self.tile, self.dir, self.t = tile, STOP, 0.0
        if facing:
            self.facing = facing

    def turn_round(self):
        """Reverse on the spot. The position does not change: (tile, dir, t) -> (tile + dir, -dir, 1 - t)."""
        if self.dir != STOP:
            self.tile = (self.tile[0] + self.dir[0], self.tile[1] + self.dir[1])
            self.dir, self.t = neg(self.dir), 1.0 - self.t
            self.facing = self.dir

    def advance(self, distance, choose):
        """Move `distance` tiles, asking `choose(self)` for the next direction at every tile centre reached."""
        while distance > 1e-9:
            if self.dir == STOP:
                self.dir = choose(self)
                if self.dir == STOP:
                    return
                self.facing = self.dir
            room = 1.0 - self.t
            if distance < room:
                self.t += distance
                return
            distance -= room
            self.tile = (self.tile[0] + self.dir[0], self.tile[1] + self.dir[1])
            self.t = 0.0
            self.dir = choose(self)
            if self.dir == STOP:
                return
            self.facing = self.dir


class Cat(Mover):
    def __init__(self, tile):
        super().__init__(tile)
        self.buffer, self.buffer_ttl = STOP, 0.0       # the wanted turn, kept until the next intersection
        self.walk = 0.0                                # walk-cycle phase (for the sprite)

    def reset(self, tile):
        self.place(tile, (1, 0))
        self.buffer, self.buffer_ttl = STOP, 0.0

    def steer(self, d):
        """The player pressed (or holds) direction `d`. Reversing is instant; a turn waits for the next intersection."""
        if d == STOP:
            return
        self.buffer, self.buffer_ttl = d, cfg.TURN_BUFFER
        if self.dir != STOP and d == neg(self.dir):
            self.turn_round()
            self.buffer = STOP                          # a reversal needs no buffering

    def chooser(self, maze):
        def choose(mover):
            want = self.buffer
            if want != STOP and self.buffer_ttl > 0 and self._free(maze, want):
                self.buffer = STOP
                return want
            if mover.dir != STOP and self._free(maze, mover.dir):
                return mover.dir
            return STOP
        return choose

    def _free(self, maze, d):
        nxt = (self.tile[0] + d[0], self.tile[1] + d[1])
        return maze.is_open(nxt) and nxt not in maze.restricted


class Robot(Mover):
    def __init__(self, kind, tile, route, release_in):
        super().__init__(tile, (0, 1))
        self.kind, self.route, self.waypoint = kind, route, 0
        self.mode = "den"                  # den (waiting) -> exit (leaving) -> active -> eyes (disabled, going home) -> den
        self.release_in = release_in
        self.fright = False
        self.home = tile
        self.anim = 0.0

    @property
    def hostile(self):
        return self.mode in ("exit", "active")


class Run:
    def __init__(self, rng, level=1, lives=cfg.START_LIVES):
        self.rng = rng
        self.score, self.lives, self.level = 0, lives, max(1, level)
        self.levels_cleared = 0
        self.fish_eaten = self.goldens = self.disabled_total = 0
        self.extra_life_given = False
        self.events = []
        self.phase = "ready"               # ready | run | dying | clear | over
        self.phase_time = 0.0
        self.time = 0.0
        self._acc = 0.0
        self.golden = None                 # (tile, seconds left) while a golden fish is out
        self._golden_given = 0
        self.last_clear_bonus = 0
        self._load_level()

    # ------------------------------------------------------------ level set-up
    def _load_level(self):
        self.maze = maze_for_level(self.level)
        self.diff = cfg.difficulty_for(self.level)
        self.fish = set(self.maze.fish) | set(self.maze.catnip)
        self.fish_total = len(self.fish)
        self.golden, self._golden_given = None, 0
        self.cat = Cat(self.maze.start)
        corners = self.maze.corners
        self.robots = [Robot(kind, self.maze.den[i], tuple(corners[(i + j) % 4] for j in range(4)), 0.0)
                       for i, kind in enumerate(cfg.ROBOTS)]
        self.catnip_left = 0.0
        self.chain = 0
        self._reset_positions()

    def _reset_positions(self):
        """Back to the start of a try: after a life is lost, or at the start of a level. Eaten fish stay eaten."""
        self.cat.reset(self.maze.start)
        for i, robot in enumerate(self.robots):
            robot.place(self.maze.den[i], (0, 1))
            robot.mode, robot.fright, robot.waypoint = "den", False, 0
            robot.release_in = self.diff.release_first + self.diff.release_gap * i
        self.catnip_left, self.chain = 0.0, 0
        self.scattering, self.phase_clock = True, self.diff.scatter
        self.invulnerable = 0.0
        self.phase, self.phase_time = "ready", 0.0
        self.golden = None

    # ------------------------------------------------------------ queries
    @property
    def fish_left(self):
        return len(self.fish)

    @property
    def over(self):
        return self.phase == "over"

    @property
    def catnip_active(self):
        return self.catnip_left > 0

    @property
    def banner_active(self):
        return self.phase == "ready"

    def take_events(self):
        events, self.events = self.events, []
        return events

    def result(self):
        return RunResult.of(self.score, self.level, self.levels_cleared)

    def _emit(self, name, x=0.0, y=0.0, amount=0, kind=""):
        self.events.append(Event(name, x, y, amount, kind))

    def _add_score(self, points):
        self.score += points
        if not self.extra_life_given and self.score >= cfg.EXTRA_LIFE_AT:
            self.extra_life_given = True
            if self.lives < cfg.MAX_LIVES:
                self.lives += 1
                self._emit("extra_life", *self.cat.pos)

    # ------------------------------------------------------------ input
    def steer(self, d):
        if self.phase in ("ready", "run"):
            self.cat.steer(d)

    def skip_clear(self):
        if self.phase == "clear" and self.phase_time >= cfg.CLEAR_SKIP_AFTER:
            self._next_level()

    # ------------------------------------------------------------ the frame
    def update(self, dt):
        self._acc += min(max(0.0, dt), cfg.MAX_FRAME)
        while self._acc >= cfg.STEP:
            self._acc -= cfg.STEP
            self._step(cfg.STEP)

    def _step(self, dt):
        self.time += dt
        self.phase_time += dt
        if self.phase == "ready":
            if self.phase_time >= cfg.READY_SECONDS:
                self.phase, self.phase_time = "run", 0.0
                self.invulnerable = cfg.RESPAWN_GRACE
        elif self.phase == "run":
            self._step_run(dt)
        elif self.phase == "dying":
            if self.phase_time >= cfg.DYING_SECONDS:
                if self.lives <= 0:
                    self.phase, self.phase_time = "over", 0.0
                    self._emit("game_over", *self.cat.pos)
                else:
                    self._reset_positions()
        elif self.phase == "clear":
            if self.phase_time >= cfg.CLEAR_SECONDS:
                self._next_level()

    def _tick_cat_timers(self, dt):
        self.cat.buffer_ttl = max(0.0, self.cat.buffer_ttl - dt)

    def _step_run(self, dt):
        self._tick_cat_timers(dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self._tick_catnip(dt)
        self._tick_phase(dt)
        self._tick_golden(dt)
        self.cat.advance(cfg.CAT_SPEED * dt, self.cat.chooser(self.maze))
        if self.cat.dir != STOP:
            self.cat.walk += dt
        self._eat()
        for robot in self.robots:
            self._move_robot(robot, dt)
        self._collide()
        if self.phase == "run" and not self.fish:
            self._clear_level()

    # ------------------------------------------------------------ timers
    def _tick_catnip(self, dt):
        if self.catnip_left > 0:
            self.catnip_left -= dt
            if self.catnip_left <= 0:
                self.catnip_left, self.chain = 0.0, 0
                for robot in self.robots:
                    robot.fright = False
                self._emit("catnip_end", *self.cat.pos)

    def _tick_phase(self, dt):
        if self.catnip_left > 0:                         # the scatter/chase clock waits while the robots are scared
            return
        self.phase_clock -= dt
        if self.phase_clock <= 0:
            self.scattering = not self.scattering
            self.phase_clock = self.diff.scatter if self.scattering else self.diff.chase

    def _tick_golden(self, dt):
        if self.golden:
            tile, left = self.golden
            left -= dt
            self.golden = (tile, left) if left > 0 else None
        eaten = 1 - self.fish_left / self.fish_total
        if self._golden_given < len(cfg.GOLDEN_AT) and eaten >= cfg.GOLDEN_AT[self._golden_given] and not self.golden:
            self._golden_given += 1
            self._spawn_golden()

    def _spawn_golden(self):
        """Put a golden fish on a corridor tile at least 7 steps from the cat (seeded choice, so tests can replay it)."""
        field = distance_field(self.maze, self.cat.nearest_tile())
        spots = sorted(t for t in self.maze.floor() if t not in self.maze.restricted and field.get(t, 0) >= 7)
        if spots:
            tile = self.rng.choice(spots)
            self.golden = (tile, cfg.GOLDEN_SECONDS)
            self._emit("golden_spawn", *tile)

    # ------------------------------------------------------------ eating
    def _eat(self):
        x, y = self.cat.pos
        tile = self.cat.nearest_tile()
        if abs(x - tile[0]) > 0.5 or abs(y - tile[1]) > 0.5:
            return
        if tile in self.fish:
            self.fish.discard(tile)
            self.fish_eaten += 1
            if tile in self.maze.catnip:
                self._add_score(cfg.SCORES["catnip"])
                self._start_catnip()
                self._emit("catnip", *tile, amount=cfg.SCORES["catnip"])
            else:
                self._add_score(cfg.SCORES["fish"])
                self._emit("fish", *tile, amount=cfg.SCORES["fish"])
        if self.golden and self.golden[0] == tile:
            self.golden = None
            self.goldens += 1
            self._add_score(cfg.SCORES["golden"])
            self._emit("golden", *tile, amount=cfg.SCORES["golden"])

    def _start_catnip(self):
        """CATNIP POWER. Collecting more while it is running only refills the timer to the normal length."""
        was_active = self.catnip_left > 0
        self.catnip_left = self.diff.catnip
        if not was_active:
            self.chain = 0
        for robot in self.robots:
            if robot.mode in ("den", "exit", "active"):
                robot.fright = True
                if not was_active and robot.mode in ("exit", "active"):
                    robot.turn_round()

    # ------------------------------------------------------------ robots
    def _move_robot(self, robot, dt):
        robot.anim += dt
        if robot.mode == "den":
            robot.release_in -= dt
            if robot.release_in <= 0:
                robot.mode = "exit"
            return
        if robot.mode == "eyes":
            speed = cfg.EYES_SPEED * cfg.CAT_SPEED
        elif robot.fright:
            speed = cfg.FRIGHT_SPEED * cfg.CAT_SPEED
        else:
            speed = self.diff.speed[robot.kind]
        robot.advance(speed * dt, self._robot_chooser(robot))

    def _robot_chooser(self, robot):
        centre = self.maze.den[len(self.maze.den) // 2]

        def choose(mover):
            if robot.mode == "exit" and mover.tile == self.maze.door:
                robot.mode = "active"
            elif robot.mode == "eyes" and mover.tile == centre:      # home: rest in the den, then come out again
                robot.place(robot.home)
                robot.mode, robot.fright, robot.release_in = "den", False, cfg.DISABLED_SECONDS
                self._emit("robot_back", *robot.pos)
                return STOP
            return ai.choose(self.maze, robot, self.cat, self.scattering, self.diff, self.rng)
        return choose

    # ------------------------------------------------------------ contact
    def _collide(self):
        cx, cy = self.cat.pos
        for robot in self.robots:
            if not robot.hostile:
                continue
            rx, ry = robot.pos
            if math.hypot(rx - cx, ry - cy) >= cfg.CATCH_DISTANCE:
                continue
            if robot.fright:
                self._disable(robot)
            elif self.invulnerable <= 0:
                self._caught(robot)
                return

    def _disable(self, robot):
        points = cfg.SCORES["disable"][min(self.chain, len(cfg.SCORES["disable"]) - 1)]
        self.chain += 1
        self.disabled_total += 1
        robot.mode, robot.fright = "eyes", False
        self._add_score(points)
        self._emit("disable", *robot.pos, amount=points, kind=robot.kind)

    def _caught(self, robot):
        self.lives -= 1
        self.phase, self.phase_time = "dying", 0.0
        self._emit("life_lost", *self.cat.pos, amount=self.lives, kind=robot.kind)

    # ------------------------------------------------------------ level flow
    def _clear_level(self):
        self.phase, self.phase_time = "clear", 0.0
        self.levels_cleared += 1
        self.last_clear_bonus = cfg.SCORES["level_clear"] + cfg.SCORES["level_clear_per_level"] * (self.level - 1)
        self._add_score(self.last_clear_bonus)
        self.golden = None
        self._emit("level_clear", *self.cat.pos, amount=self.last_clear_bonus)

    def _next_level(self):
        self.level += 1
        self._load_level()
