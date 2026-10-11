"""Timed Smash swing shared by human players and Sandra, independent of rendering."""
from dataclasses import dataclass
import math
from .court import BALL_GRAVITY, FLOOR, NET_TOP, NET_X


@dataclass
class SmashAttack:
    WINDUP = .025       # the paw is still rising; contact before this is a normal hit
    ACTIVE_END = .30    # last moment the paw can still connect
    RECOVER = .34       # earliest a new swing can start after the previous one
    ANIMATION = .38     # pose length
    BUFFER = .16        # a press this early is remembered until the swing may start
    MAX_SPEED_X = 470   # keeps long cross-court Smashes defendable
    MIN_FLIGHT = .40
    QUICK_FLIGHT = .50  # a human Smash slower than this (seconds to the floor) looks for a deeper, quicker landing
    QUICK_REACH = 40        # ...but no more than this much deeper, so steering with the move key still matters
    SMASH_MAX_DEPTH = 150   # how far past the net such a Smash may land (the back wall is 180 away)

    age: float = 1.0
    held: bool = False
    connected: bool = False
    buffer: float = 0.0

    @property
    def active(self):
        return self.WINDUP <= self.age < self.ACTIVE_END and not self.connected

    @property
    def animating(self):
        return self.age < self.ANIMATION

    def update(self, dt, pressed, airborne):
        """A swing needs a fresh press (a held key never repeats) while airborne.
        A press made just before take-off or the end of recovery is buffered."""
        self.age += dt
        self.buffer = max(0.0, self.buffer - dt)
        if pressed and not self.held:
            self.buffer = self.BUFFER
        if self.buffer > 0 and airborne and self.age >= self.RECOVER:
            self.age, self.connected, self.buffer = 0.0, False, 0.0
        self.held = pressed

    def can_hit(self, player, ball):
        direction = 1 if player.side == 0 else -1
        return (self.active and player.y < 236 and ball.y + ball.radius < NET_TOP
                and ball.y <= player.y - 6
                and (ball.x - player.x) * direction >= -6)

    @classmethod
    def velocity(cls, player, ball, aim=None):
        """Aim a steep ballistic shot at a landing spot in the opponent's court.

        The quickest flight that still clears the net is used, so a Smash is
        far faster and steeper than a normal lob (rally.lob_velocity), and
        steeper the closer to the net it is struck. `aim` is a landing x
        (Sandra's tactics); humans get a depth that grows with distance from
        the net and with moving toward it."""
        direction = 1 if player.side == 0 else -1
        to_net = (NET_X - ball.x) * direction
        if aim is None:
            depth = 62 + .5 * max(0, to_net) + 22 * player.moving * direction
            target = NET_X + direction * max(50, min(150, depth))
        else:
            target = aim
        # Always the opponent's half, a net's width or more from the tape and inside the wall.
        target = NET_X + direction * max(35, min(170, (target - NET_X) * direction))
        vx, vy, flight = cls._quickest(ball, target, to_net, direction)
        if aim is None and flight > cls.QUICK_FLIGHT:
            # The net forced a slow, floaty arc to this landing spot. A Smash should feel like a
            # Smash, so look for a deeper spot (never past SMASH_MAX_DEPTH) that it can reach faster.
            depth = (target - NET_X) * direction
            for deeper in range(int(depth) + 10, min(cls.SMASH_MAX_DEPTH, int(depth) + cls.QUICK_REACH) + 1, 10):
                spot = NET_X + direction * deeper
                cand = cls._quickest(ball, spot, to_net, direction)
                if cand[2] < flight - .03:
                    vx, vy, flight = cand
        return vx, vy

    @classmethod
    def _quickest(cls, ball, target, to_net, direction):
        """(vx, vy, flight) of the quickest ballistic shot to `target` that clears the net."""
        dx, dy = target - ball.x, FLOOR - ball.radius - ball.y
        flight = max(cls.MIN_FLIGHT, abs(dx) / cls.MAX_SPEED_X)
        far_edge = to_net + 3       # the ball must be over the tape until it passes the net's far side
        while True:
            vx, vy = dx / flight, (dy - .5 * BALL_GRAVITY * flight**2) / flight
            if far_edge <= 0 or flight >= 1.4 or cls._clears_net(ball, vx, vy, direction):
                return vx, vy, flight
            flight += .02

    @staticmethod
    def _clears_net(ball, vx, vy, direction, margin=None):
        """Walk the arc past the tape; the round ball must stay `margin` clear of
        the net's real shape (its top corners included), not just of its centre line."""
        margin = ball.radius + 2 if margin is None else margin     # default covers the physics' integration error
        t = 0.0
        while True:
            x = ball.x + vx * t
            y = ball.y + vy * t + .5 * BALL_GRAVITY * t * t
            if (x - NET_X) * direction > 3 + margin or t > 3:
                return True
            nearest_x = max(NET_X - 3, min(NET_X + 3, x))
            if math.hypot(x - nearest_x, y - max(NET_TOP, min(FLOOR, y))) < margin:
                return False
            t += .004
