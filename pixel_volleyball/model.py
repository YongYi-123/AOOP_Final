"""Deterministic court rules and fixed-substep physics, with no pygame import."""
from dataclasses import dataclass
from enum import Enum
import math
from .ai import VolleyAI

WIDTH, HEIGHT, FLOOR, NET_X, NET_TOP = 400, 300, 258, 200, 162
GRAVITY = 620.0


class MatchState(Enum):
    TITLE = "title"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


@dataclass(frozen=True)
class VolleyInput:
    move: float = 0
    jump: bool = False
    spike: bool = False


@dataclass
class VolleyPlayer:
    side: int
    x: float
    y: float = FLOOR - 14
    vy: float = 0
    radius: int = 14
    hit_cooldown: float = 0
    spike_time: float = 0
    moving: float = 0
    hit_flash: float = 0


@dataclass
class VolleyBall:
    x: float
    y: float
    vx: float
    vy: float
    radius: int = 6


@dataclass(frozen=True)
class MatchOutcome:
    points: tuple
    winner: int
    elapsed: float


class VolleyMatch:
    def __init__(self, local_players=1, target=5, difficulty="NORMAL"):
        if local_players not in (1, 2) or target < 1:
            raise ValueError("volleyball needs 1-2 players and a positive target")
        self.local_players, self.target = local_players, target
        self.players = [VolleyPlayer(0, 90), VolleyPlayer(1, 310)]
        self.points = [0, 0]
        self.state = MatchState.TITLE
        self.elapsed = 0.0
        self.outcome = None
        self.events = []
        self.ai = VolleyAI(difficulty)
        self._serve(0)

    def _serve(self, side):
        self.ball = VolleyBall(90 if side == 0 else 310, 185,
                               170 if side == 0 else -170, -290)
        self.serve_delay = 0.8
        for player in self.players:
            player.x = 90 if player.side == 0 else 310
            player.y, player.vy = FLOOR - player.radius, 0
            player.hit_cooldown = player.spike_time = 0

    def start(self):
        if self.state is MatchState.TITLE:
            self.state = MatchState.PLAYING

    def toggle_pause(self):
        if self.state in (MatchState.PLAYING, MatchState.PAUSED):
            self.state = (MatchState.PAUSED if self.state is MatchState.PLAYING
                          else MatchState.PLAYING)

    def update(self, dt, controls=()):
        self.events = []
        if self.state is not MatchState.PLAYING or dt <= 0:
            return
        remaining = min(dt, 0.1)
        while remaining > 1e-8 and self.state is MatchState.PLAYING:
            # Relative travel stays below half the yarn radius, including
            # unusually fast shots; both net and player tests see contact.
            speed = math.hypot(self.ball.vx, self.ball.vy) + 500
            step = min(remaining, 1 / 120, self.ball.radius * .5 / speed)
            inputs = list(controls[:self.local_players])
            inputs.extend([VolleyInput()] * (self.local_players - len(inputs)))
            if self.local_players == 1:
                inputs.append(self.ai.controls(self.players[1], self.ball, step))
            self._step(step, inputs)
            remaining -= step

    def _step(self, dt, inputs):
        self.elapsed += dt
        for player, control in zip(self.players, inputs):
            lo, hi = ((20 + player.radius, NET_X - 4 - player.radius) if player.side == 0
                      else (NET_X + 4 + player.radius, WIDTH - 20 - player.radius))
            player.moving = max(-1, min(1, control.move))
            player.hit_flash = max(0, player.hit_flash - dt)
            player.x = max(lo, min(hi, player.x + max(-1, min(1, control.move)) * 155 * dt))
            if control.jump and player.y >= FLOOR - player.radius:
                player.vy = -330
            player.vy += GRAVITY * dt
            player.y = min(FLOOR - player.radius, player.y + player.vy * dt)
            if player.y == FLOOR - player.radius:
                player.vy = 0
            player.hit_cooldown = max(0, player.hit_cooldown - dt)
            player.spike_time = 0.15 if control.spike else max(0, player.spike_time - dt)
        if self.serve_delay > 0:
            self.serve_delay = max(0, self.serve_delay - dt)
            return
        ball = self.ball
        ball.vy += GRAVITY * dt
        previous_x = ball.x
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt
        if ball.x < 20 + ball.radius or ball.x > WIDTH - 20 - ball.radius:
            ball.x = max(20 + ball.radius, min(WIDTH - 20 - ball.radius, ball.x))
            ball.vx = -ball.vx
        if ball.y < 52 + ball.radius:
            ball.y, ball.vy = 52 + ball.radius, abs(ball.vy)
        self._net_collision(previous_x)
        for player in self.players:
            self._player_collision(player)
        if ball.y >= FLOOR - ball.radius:
            self.award_point(1 if ball.x < NET_X else 0)

    def _net_collision(self, previous_x):
        ball = self.ball
        nx = max(NET_X - 3, min(NET_X + 3, ball.x))
        ny = max(NET_TOP, min(FLOOR, ball.y))
        dx, dy = ball.x - nx, ball.y - ny
        distance = math.hypot(dx, dy)
        if distance >= ball.radius:
            return
        if distance < 1e-8:
            dx, dy, distance = (-1 if previous_x < NET_X else 1), 0, 1
            nx = NET_X + dx * 3
        ux, uy = dx / distance, dy / distance
        ball.x, ball.y = nx + ux * (ball.radius + 0.1), ny + uy * (ball.radius + 0.1)
        normal_speed = ball.vx * ux + ball.vy * uy
        if normal_speed < 0:
            ball.vx -= 1.8 * normal_speed * ux
            ball.vy -= 1.8 * normal_speed * uy
            self.events.append("bounce")

    def _player_collision(self, player):
        ball = self.ball
        dx, dy = ball.x - player.x, ball.y - player.y
        distance = math.hypot(dx, dy)
        radius = ball.radius + player.radius
        if distance >= radius:
            return
        if player.hit_cooldown > 0:
            # Suppress repeated hits, never let a cooldown erase the body.
            ux, uy = (dx / distance, dy / distance) if distance > 1e-8 else (0, -1)
            ball.x = player.x + ux * (radius + .1)
            ball.y = player.y + uy * (radius + .1)
            inward = ball.vx * ux + (ball.vy - player.vy) * uy
            if inward < 0:
                ball.vx -= inward * ux
                ball.vy -= inward * uy
            return
        direction = 1 if player.side == 0 else -1
        ball.y = player.y - radius - 0.1
        ball.vx = direction * 190
        ball.vy = -360
        spike = player.spike_time > 0 and player.y < FLOOR - player.radius - 8
        if spike:
            ball.vx, ball.vy = direction * 285, 90
            if player.side == 1 and self.local_players == 1:
                ball.vx, ball.vy = self.ai.attack_velocity(ball, self.players[0])
        player.hit_flash = .2
        player.hit_cooldown = 0.18
        self.events.append("spike" if spike else "hit")

    def award_point(self, side):
        if self.state is not MatchState.PLAYING:
            return
        self.points[side] += 1
        self.events.append("point")
        if self.points[side] >= self.target:
            self.state = MatchState.FINISHED
            self.outcome = MatchOutcome(tuple(self.points), side, self.elapsed)
            self.events.append("win")
        else:
            self._serve(side)
