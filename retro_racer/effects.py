"""Temporary effects on a car (boost, slow, shield, spin). Each is a small polymorphic object with a timer.

A car keeps a list of ActiveEffect objects; physics multiplies in `multipliers`, so no timer variables leak
into PlayerCar / RacerCar. Effects also draw their own decoration (shield bubble, flames...).
"""
import math
import pygame
import settings as S
from assets import CYAN, ORANGE, YELLOW, WHITE


class ActiveEffect:
    key = "effect"
    hostile = False              # hostile effects can be blocked by a shield and cleared by REPAIR
    duration = 1.0
    multipliers = {}             # stat -> factor: "max_speed", "acceleration", "steering"

    def __init__(self, duration=None):
        self.duration = self.duration if duration is None else duration
        self.elapsed = 0.0
        self.consumed = False

    def begin(self, car):        # called once when applied
        pass

    @property
    def remaining(self):
        return max(0.0, self.duration - self.elapsed)

    def merge(self, old):
        """Combination rule when the same kind of effect is applied again while `old` is still running:
        the new one takes over but never shortens what was left."""
        self.duration = max(self.duration, old.remaining)

    def update(self, dt, car):
        self.elapsed += dt

    @property
    def expired(self):
        return self.consumed or self.elapsed >= self.duration

    def expire(self, car):       # called once when removed
        pass

    def absorbs_hostile(self, car):
        """True if this effect swallows an incoming hostile effect / crash (and is used up doing so)."""
        return False

    def decorate(self, surf, cx, bottom, width):
        """Draw over/under the car sprite. (cx, bottom) = bottom centre, width in px."""


class SpeedBoostEffect(ActiveEffect):
    key = "boost"
    duration = 2.6
    multipliers = {"max_speed": 1.30, "acceleration": 2.5}

    def begin(self, car):
        car.speed += 0.10 * S.MAX_SPEED          # instant kick

    def decorate(self, surf, cx, bottom, width):
        flick = int(self.elapsed * 30) % 2
        for side in (-1, 1):
            x = cx + side * width * 0.28
            h = width * (0.30 if flick else 0.42)
            pygame.draw.polygon(surf, ORANGE, ((x - width * 0.07, bottom - width * 0.05), (x + width * 0.07, bottom - width * 0.05), (x, bottom + h)))
            pygame.draw.polygon(surf, YELLOW, ((x - width * 0.035, bottom - width * 0.05), (x + width * 0.035, bottom - width * 0.05), (x, bottom + h * 0.6)))


class SlowEffect(ActiveEffect):
    """Oil / pulse: lose top speed and grip for a moment."""
    key = "slow"
    hostile = True
    duration = 1.8

    def __init__(self, duration=None, speed=0.6, grip=0.6):
        super().__init__(duration)
        self.multipliers = {"max_speed": speed, "steering": grip}

    def merge(self, old):
        """Slow on top of slow: keep the stronger penalty of each stat and the longer time (no stacking spiral)."""
        super().merge(old)
        self.multipliers = {k: min(v, old.multipliers.get(k, 1.0)) for k, v in self.multipliers.items()}

    def decorate(self, surf, cx, bottom, width):
        if int(self.elapsed * 8) % 2:
            for dx in (-0.3, 0.0, 0.3):
                pygame.draw.circle(surf, (20, 20, 30), (cx + dx * width, bottom - width * 0.12), max(2, int(width * 0.05)))


class ShieldEffect(ActiveEffect):
    key = "shield"
    duration = 12.0

    def absorbs_hostile(self, car):
        self.consumed = True
        return True

    def decorate(self, surf, cx, bottom, width):
        r = int(width * (0.62 + 0.03 * math.sin(self.elapsed * 10)))
        pygame.draw.circle(surf, CYAN, (cx, bottom - width * 0.2), r, max(2, int(width * 0.025)))


class ShieldBreakEffect(ActiveEffect):
    """Pure feedback: the bubble popping when a shield blocks something. Multiplies nothing."""
    key = "shield_break"
    duration = 0.35

    def decorate(self, surf, cx, bottom, width):
        t = self.elapsed / self.duration
        r = int(width * (0.62 + 0.5 * t))
        pygame.draw.circle(surf, WHITE if t < 0.5 else CYAN, (cx, bottom - width * 0.2), r, max(1, int(width * 0.03 * (1 - t))))


class SpinEffect(ActiveEffect):
    """Seeker hit: brief loss of control and speed."""
    key = "spin"
    hostile = True
    duration = 1.1
    multipliers = {"max_speed": 0.5, "steering": 0.0}

    def begin(self, car):
        car.push += (1.6 if car.x <= 0 else -1.6)

    def decorate(self, surf, cx, bottom, width):
        for k in range(3):
            a = self.elapsed * 12 + k * 2.1
            pygame.draw.circle(surf, YELLOW, (cx + math.cos(a) * width * 0.4, bottom - width * 0.5 + math.sin(a) * width * 0.08), max(2, int(width * 0.04)))
