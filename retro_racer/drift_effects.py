"""Presentation-only driving feedback. Never mutates a car or road."""
from dataclasses import dataclass
import math
import random

import pygame


@dataclass
class CollisionSpark:
    x: float
    y: float
    vx: float
    vy: float
    age: float = 0.0
    lifetime: float = 0.4

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 100 * dt

    def draw(self, surf, anchor, intensity):
        fade = max(0, 1 - self.age / self.lifetime)
        x, y = anchor[0] + self.x, anchor[1] + self.y
        color = (int(255 * fade), int(190 * fade), int(70 * fade))
        pygame.draw.line(surf, color, (int(x), int(y)),
                         (int(x - self.vx * 0.025), int(y - self.vy * 0.025)),
                         max(1, int(2 * intensity)))


@dataclass
class SkidMark:
    """Road drawable with the same x/z projection contract as traffic cars."""
    x: float
    z: float
    width: float
    strength: float
    age: float = 0.0
    lifetime: float = 1.2

    def draw(self, surf, cx, bottom, road_width):
        width = road_width * 0.2 * self.width
        shade = int(35 + 55 * min(1, self.age / self.lifetime))
        thickness = max(1, int(width * 0.065 * min(1, self.strength)))
        length = max(2, int(width * 0.22))
        for side in (-1, 1):
            x = int(cx + side * width * 0.35)
            pygame.draw.line(surf, (shade, shade, shade), (x, int(bottom) - length),
                             (x, int(bottom)), thickness)


@dataclass
class TireSmoke:
    x: float
    y: float
    vx: float
    age: float = 0.0
    lifetime: float = 0.65

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += 50 * dt

    def draw(self, surf, anchor, intensity):
        progress = self.age / self.lifetime
        radius = max(1, int((5 + progress * 13) * intensity))
        puff = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(puff, (185, 175, 190, int(105 * (1 - progress))), (radius, radius), radius)
        surf.blit(puff, (anchor[0] + self.x - radius, anchor[1] + self.y - radius))


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

    def __init__(self, intensity=1.0, rng=None):
        self.rng = rng or random.Random()  # Separate from traffic, AI and item RNG.
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
        self.smoke = []
        self._smoke_time = 0.0
        self.skids = []
        self._skid_time = 0.0
        self.sparks = []
        self._collisions = 0

    @property
    def rear_offset(self):
        return self.offset * 16 * self.intensity

    @property
    def yaw(self):
        return self.offset * 6 * self.intensity

    def update(self, dt, player, road, controls):
        dt = max(0.0, min(0.1, dt))
        for puff in self.smoke:
            puff.update(dt)
        self.smoke = [p for p in self.smoke if p.age < p.lifetime]
        for mark in self.skids:
            mark.age += dt
        self.skids = [mark for mark in self.skids if mark.age < mark.lifetime]
        for spark in self.sparks:
            spark.update(dt)
        self.sparks = [spark for spark in self.sparks if spark.age < spark.lifetime]
        crashed = player.collisions > self._collisions
        self._collisions = player.collisions
        self.state = DriftState.detect(player.speed_percent, controls["steer"],
                                       road.segment_at(player.front_z).curve, controls["brake"])
        target = self.state.amount if self.intensity else 0.0
        self.offset += (target - self.offset) * (1 - math.exp(-10 * max(0.0, dt)))
        if not self.intensity:
            self.smoke.clear()
            self._smoke_time = 0
            self.skids.clear()
            self._skid_time = 0
            self.sparks.clear()
            return
        if crashed:
            for _ in range(max(1, int(18 * self.intensity))):
                self.sparks.append(CollisionSpark(self.rear_offset, -40,
                                                  self.rng.uniform(-180, 180),
                                                  self.rng.uniform(-130, 70)))
            self.sparks = self.sparks[-72:]
        if self.state.braking:
            self._skid_time += dt
            if self._skid_time >= 0.035:
                self._skid_time %= 0.035
                self.skids.append(SkidMark(player.x, (player.front_z + 70) % road.length,
                                           player.spec.width, self.intensity))
                self.skids = self.skids[-64:]
        else:
            self._skid_time = 0
        if abs(self.state.amount) > 0.15 or self.state.braking:
            self._smoke_time += dt
            while self._smoke_time >= 0.04:
                self._smoke_time -= 0.04
                for side in (-1, 1):
                    self.smoke.append(TireSmoke(side * 52 * player.spec.width + self.rear_offset,
                                               -8, self.rng.uniform(-18, 18)))
            self.smoke = self.smoke[-80:]
        else:
            self._smoke_time = 0

    def draw_smoke(self, surf):
        if self.intensity:
            for puff in self.smoke:
                puff.draw(surf, (surf.get_width() / 2, surf.get_height() - 30), self.intensity)

    def road_drawables(self):
        return list(self.skids) if self.intensity else []

    def draw_sparks(self, surf):
        if self.intensity:
            for spark in self.sparks:
                spark.draw(surf, (surf.get_width() / 2, surf.get_height() - 30), self.intensity)

    def shake_offset(self, strength):
        amplitude = 4 * self.intensity * max(0, min(1, strength))
        if not amplitude:
            return (0, 0)
        return (int(self.rng.uniform(-amplitude, amplitude)),
                int(self.rng.uniform(-amplitude * 0.6, amplitude * 0.6)))
