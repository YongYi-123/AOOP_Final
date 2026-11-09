"""HAPPY BREAKOUT.EXE: the rules of the little Breakout game on the old computer in Trial 01 (no drawing, no pygame).

A paddle, a ball and a wall of bricks. Move the paddle with the arrow keys (or A / D), launch the ball with E / SPACE /
UP. Clear every brick to win. Three lives; losing them all just lets you start again, free. Meant to be easy: a slow ball,
a wide paddle and about two to four minutes of play.

`step(dt, direction)` advances the game (in small fixed sub-steps so a fast frame can never let the ball tunnel through a
brick) and records what happened in `events` as (name, x, y, colour index) for the screen to turn into sounds and sparks:
"launch", "wall", "paddle", "brick", "lose", "clear", "over".

The ball can never get stuck: it always keeps a real vertical speed (so it cannot bounce sideways forever), a brick is
removed the moment it is hit, and a ball that finds itself inside a brick or the paddle is pushed out first.
"""
import math
import random

FIELD_W, FIELD_H = 240, 176
COLS, ROWS = 8, 5
BRICK_W, BRICK_H, GAP = 28, 8, 2
TOP = 14                                        # where the first row of bricks starts
PADDLE_W, PADDLE_H = 40, 5
PADDLE_Y = FIELD_H - 14
PADDLE_SPEED = 200.0                            # pixels per second
BALL = 4                                        # the ball is a 4x4 square
BASE_SPEED, MAX_SPEED = 105.0, 150.0
MIN_VERTICAL = 0.5                              # |vy| / speed never drops below this, so the ball cannot run sideways forever
MAX_BOUNCE = math.radians(55)                   # steepest angle off the paddle's edge
LIVES = 3
SUBSTEP = 1 / 240
POINTS = 10


class Brick:
    __slots__ = ("x", "y", "colour", "alive")

    def __init__(self, x, y, colour):
        self.x, self.y, self.colour, self.alive = x, y, colour, True

    @property
    def rect(self):
        return (self.x, self.y, BRICK_W, BRICK_H)


class Breakout:
    def __init__(self):
        self.reset()

    # ------------------------------------------------------------ setup
    def reset(self):
        """A brand new game: full wall, three lives, ball on the paddle. Free, as often as you like."""
        left = (FIELD_W - (COLS * (BRICK_W + GAP) - GAP)) // 2
        self.bricks = [Brick(left + c * (BRICK_W + GAP), TOP + r * (BRICK_H + GAP), r) for r in range(ROWS) for c in range(COLS)]
        self.lives = LIVES
        self.score = 0
        self.state = "ready"                    # ready (ball on the paddle) / playing / over / clear
        self.paddle_x = (FIELD_W - PADDLE_W) / 2
        self.events = []
        self.hits = 0
        self.idle = 0.0                                   # seconds since the last brick fell
        self.speed = BASE_SPEED
        self._rng = random.Random(1989)                  # a little wobble on every paddle hit, so no rally can repeat for ever
        self._park()

    def _park(self):
        """The ball sits on the paddle, waiting for the launch."""
        self.ball_x = self.paddle_x + PADDLE_W / 2 - BALL / 2
        self.ball_y = PADDLE_Y - BALL
        self.vx = self.vy = 0.0
        self.state = "ready" if self.lives > 0 else "over"

    @property
    def remaining(self):
        return sum(1 for b in self.bricks if b.alive)

    # ------------------------------------------------------------ input
    def launch(self):
        if self.state == "ready":
            angle = math.radians(-12 if int(self.paddle_x) % 2 else 12)          # a gentle, slightly different first angle
            self.vx = self.speed * math.sin(angle)
            self.vy = -self.speed * math.cos(angle)
            self.state = "playing"
            self.events.append(("launch", self.ball_x, self.ball_y, 0))
        elif self.state in ("over", "clear"):
            self.reset()

    # ------------------------------------------------------------ the loop
    def step(self, dt, direction=0):
        """Advance by `dt` seconds. `direction`: -1 left, 0 still, +1 right."""
        dt = min(dt, 0.1)
        n = max(1, int(math.ceil(dt / SUBSTEP)))
        for _ in range(n):
            self._sub(dt / n, direction)

    def _sub(self, h, direction):
        if self.state in ("over", "clear"):
            return
        self.paddle_x = max(0.0, min(FIELD_W - PADDLE_W, self.paddle_x + direction * PADDLE_SPEED * h))
        if self.state == "ready":
            self.ball_x = self.paddle_x + PADDLE_W / 2 - BALL / 2
            return
        self.idle += h
        self.ball_x += self.vx * h
        self.ball_y += self.vy * h
        self._walls()
        self._paddle()
        self._bricks()
        if self.ball_y > FIELD_H:
            self._lose()

    def _walls(self):
        if self.ball_x < 0:
            self.ball_x, self.vx = 0.0, abs(self.vx)
            self._bounce_event("wall")
        elif self.ball_x + BALL > FIELD_W:
            self.ball_x, self.vx = FIELD_W - BALL, -abs(self.vx)
            self._bounce_event("wall")
        if self.ball_y < 0:
            self.ball_y, self.vy = 0.0, abs(self.vy)
            self._bounce_event("wall")

    def _bounce_event(self, name):
        self._keep_moving()
        self.events.append((name, self.ball_x, self.ball_y, 0))

    def _paddle(self):
        if self.vy <= 0:
            return
        bottom = self.ball_y + BALL
        if bottom < PADDLE_Y or self.ball_y > PADDLE_Y + PADDLE_H:
            return
        if self.ball_x + BALL < self.paddle_x or self.ball_x > self.paddle_x + PADDLE_W:
            return
        offset = (self.ball_x + BALL / 2 - (self.paddle_x + PADDLE_W / 2)) / (PADDLE_W / 2)       # -1 (left edge) .. +1
        offset = max(-1.0, min(1.0, offset))
        wobble = 0.09 + min(0.5, self.idle / 12.0 * 0.5)         # the longer a rally goes without a brick, the more each hit is shaken up
        angle = max(-MAX_BOUNCE, min(MAX_BOUNCE, offset * MAX_BOUNCE + self._rng.uniform(-wobble, wobble)))
        self.vx = self.speed * math.sin(angle)
        self.vy = -self.speed * math.cos(angle)
        self.ball_y = PADDLE_Y - BALL                                              # on top of the paddle, never inside it
        self._keep_moving()
        self.events.append(("paddle", self.ball_x, self.ball_y, 0))

    def _bricks(self):
        cx, cy = self.ball_x + BALL / 2, self.ball_y + BALL / 2
        hit = None
        best = None
        for b in self.bricks:
            if not b.alive:
                continue
            if self.ball_x + BALL <= b.x or self.ball_x >= b.x + BRICK_W or self.ball_y + BALL <= b.y or self.ball_y >= b.y + BRICK_H:
                continue
            d = (cx - (b.x + BRICK_W / 2)) ** 2 + (cy - (b.y + BRICK_H / 2)) ** 2
            if best is None or d < best:
                hit, best = b, d
        if hit is None:
            return
        hit.alive = False
        self.idle = 0.0
        self.score += POINTS
        self.hits += 1
        self.speed = min(MAX_SPEED, BASE_SPEED + self.hits * 0.9)
        # bounce off the side the ball is nearest to (the smaller overlap), and move out of the brick
        over_x = min(self.ball_x + BALL - hit.x, hit.x + BRICK_W - self.ball_x)
        over_y = min(self.ball_y + BALL - hit.y, hit.y + BRICK_H - self.ball_y)
        if over_x < over_y:
            self.vx = -self.vx
            self.ball_x += -over_x if cx < hit.x + BRICK_W / 2 else over_x
        else:
            self.vy = -self.vy
            self.ball_y += -over_y if cy < hit.y + BRICK_H / 2 else over_y
        self._keep_moving()
        self.events.append(("brick", hit.x + BRICK_W / 2, hit.y + BRICK_H / 2, hit.colour))
        if self.remaining == 0:
            self.state = "clear"
            self.vx = self.vy = 0.0
            self.events.append(("clear", cx, cy, 0))

    def _lose(self):
        self.lives -= 1
        self.events.append(("lose", self.ball_x, FIELD_H, 0))
        self._park()
        if self.lives <= 0:
            self.state = "over"
            self.events.append(("over", self.ball_x, FIELD_H, 0))

    def _keep_moving(self):
        """Hold the speed at its current value and keep the ball from running (almost) sideways."""
        speed = max(1.0, self.speed)
        vy = self.vy
        if abs(vy) < MIN_VERTICAL * speed:
            vy = math.copysign(MIN_VERTICAL * speed, vy if vy else -1.0)
        vx_sq = max(0.0, speed * speed - vy * vy)
        vx = math.copysign(math.sqrt(vx_sq), self.vx if self.vx else 1.0)
        self.vx, self.vy = vx, vy

    def take_events(self):
        out, self.events = self.events, []
        return out
