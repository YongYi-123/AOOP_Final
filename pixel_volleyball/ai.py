"""Reaction-limited AI strategies; all opponents use the same player physics."""
import math


class VolleyAI:
    """Sandra reacts every 90 ms, with bounded error and ordinary player inputs."""
    REACTION = .09
    ERROR = 4

    def __init__(self):
        self.wait = 0
        self.decisions = 0
        self.target = 290
        self.jump_wait = 0.0

    @staticmethod
    def predict(ball):
        """Simulate gravity, ceiling and side walls until receiving height."""
        x, y, vx, vy = ball.x, ball.y, ball.vx, ball.vy
        step = 1 / 120
        for _ in range(360):
            vy += 620 * step
            x += vx * step
            y += vy * step
            if x < 26 or x > 374:
                x = max(26, min(374, x))
                vx = -vx
            if y < 58:
                y, vy = 58, abs(vy)
            if y >= 224 and vy > 0:
                return x
        return x

    def controls(self, player, ball, dt=1/120):
        from .model import VolleyInput
        self.wait -= dt
        self.jump_wait = max(0, self.jump_wait - dt)
        if self.wait <= 0:
            self.decisions += 1
            error = self.ERROR * math.sin(self.decisions * 1.7)
            target = self.predict(ball)
            self.target = max(218, min(366, target + error)) if target > 200 else 290
            self.wait = self.REACTION
        delta = self.target - player.x
        move = 0 if abs(delta) < 4 else (1 if delta > 0 else -1)
        near = abs(ball.x - player.x) < 28 and ball.x > 207
        # A jump takes ~0.2 seconds to meet a descending ball above the net.
        jump = (near and 80 < ball.y < 145 and -40 < ball.vy < 180
                and player.y >= 258-player.radius and player.hit_cooldown == 0
                and self.jump_wait == 0)
        if jump:
            self.jump_wait = 1.1
        # Press once shortly before head contact, respecting the same windup.
        relative_y = ball.y - player.y
        closing = ball.vy - player.vy
        approaching = (-45 < relative_y < -12 and closing > 0)
        time_to_contact = max(0, (-18-relative_y) / max(1, closing))
        spike = (near and player.y < 190 and ball.y < 156
                 and approaching and time_to_contact < .09
                 and player.attack.age >= .38 and not player.attack.held)
        return VolleyInput(move, jump, spike)
