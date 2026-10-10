"""Reaction-limited AI strategies; all opponents use the same player physics."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class AIDifficulty:
    name: str
    reaction: float
    error: float
    attack: bool


DIFFICULTIES = (AIDifficulty('EASY', .28, 24, False),
                AIDifficulty('NORMAL', .12, 5, True),
                AIDifficulty('HARD', .05, 0, True))


class VolleyAI:
    def __init__(self, difficulty='NORMAL'):
        self.difficulty = next((d for d in DIFFICULTIES if d.name == difficulty.upper()), None)
        if self.difficulty is None:
            raise ValueError('unknown volleyball AI difficulty')
        self.wait = 0
        self.decisions = 0
        self.target = 290

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
        if self.wait <= 0:
            self.decisions += 1
            error = self.difficulty.error * math.sin(self.decisions * 1.7)
            target = self.predict(ball)
            self.target = max(218, min(366, target + error)) if target > 200 else 290
            self.wait = self.difficulty.reaction
        delta = self.target - player.x
        move = 0 if abs(delta) < 4 else (1 if delta > 0 else -1)
        near = abs(ball.x - player.x) < 28 and ball.x > 207
        # A jump takes ~0.2 seconds to meet a descending ball above the net.
        jump = near and 125 < ball.y < 205 and -100 < ball.vy < 220
        spike = (self.difficulty.attack and near and player.y < 190
                 and ball.y < 156 and ball.vy > -100)
        return VolleyInput(move, jump, spike)

    def attack_velocity(self, ball, opponent):
        if self.difficulty.name != 'HARD':
            return -285, 90
        # Aim at open court using a physically bounded shot, not teleportation.
        target = 45 if opponent.x > 105 else 155
        flight = (30 + math.sqrt(30**2 + 2 * 620 * max(1, 252-ball.y))) / 620
        return max(-300, min(-125, (target-ball.x) / flight)), -30
