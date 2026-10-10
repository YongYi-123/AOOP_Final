"""Presentation-only driving feedback. Never mutates a car or road."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DriftState:
    amount: float = 0.0
    braking: bool = False

    @classmethod
    def detect(cls, speed, steer, curve, brake):
        speed = max(0.0, min(1.0, speed))
        if speed <= 0.55:
            return cls()
        turn = max(-1.0, min(1.0, steer * 0.75 + curve * 0.18))
        amount = turn * (speed - 0.55) / 0.45 if abs(turn) > 0.2 else 0.0
        return cls(amount, bool(brake))


class DriftEffects:
    """Own visual state for one racer; intensity 0 disables all feedback."""

    def __init__(self, intensity=1.0):
        self.intensity = intensity
        self.reset()

    @property
    def intensity(self):
        return self._intensity

    @intensity.setter
    def intensity(self, value):
        self._intensity = max(0.0, min(2.0, float(value)))

    def reset(self):
        self.state = DriftState()
        self.offset = 0.0

    @property
    def rear_offset(self):
        return self.offset * 16 * self.intensity

    @property
    def yaw(self):
        return self.offset * 6 * self.intensity

    def update(self, dt, player, road, controls):
        self.state = DriftState.detect(player.speed_percent, controls["steer"],
                                       road.segment_at(player.front_z).curve, controls["brake"])
        target = self.state.amount if self.intensity else 0.0
        self.offset += (target - self.offset) * (1 - math.exp(-10 * max(0.0, dt)))
