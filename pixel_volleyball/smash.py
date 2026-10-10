"""Timed swings shared by human players and Sandra, independent of rendering."""
from dataclasses import dataclass
import math


@dataclass
class SmashAttack:
    age: float = 1.0
    held: bool = False
    connected: bool = False

    @property
    def active(self):
        return .025 <= self.age < .19 and not self.connected

    @property
    def animating(self):
        return self.age < .38

    def update(self, dt, pressed, airborne):
        self.age += dt
        if pressed and not self.held and airborne and self.age >= .38:
            self.age, self.connected = 0.0, False
        self.held = pressed

    def can_hit(self, player, ball):
        direction = 1 if player.side == 0 else -1
        return (self.active and player.y < 236 and ball.y + ball.radius < 162
                and ball.y <= player.y - 6
                and (ball.x - player.x) * direction >= -6)

    @staticmethod
    def velocity(player, ball, aim=None):
        direction = 1 if player.side == 0 else -1
        speed = 330 + 30 * player.moving * direction
        if aim is not None:
            speed = max(300, min(360, abs(aim - ball.x) * 2.4))
        vx = direction * speed
        # Ensure the descending shot clears the net, even from the back court.
        crossing = abs(200 - ball.x) / speed
        clearance = 152 - ball.y
        vy = min(130, (clearance - 310 * crossing**2) / max(.02, crossing))
        return vx, max(-260, vy)
