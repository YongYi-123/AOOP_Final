"""Cosmetic effects: scrolling starfield, pixel explosions, shockwave rings and screen shake. Nothing
here touches the rules; reduced mode drops the shake and flashes and halves the particles."""
import random

from . import config as cfg

BURST_COLORS = {"scout": ((165, 110, 255), (130, 255, 150)), "dash": ((255, 100, 200), (255, 226, 100)),
                "tank": ((118, 128, 200), (255, 100, 200)), "boss": ((255, 160, 60), (255, 226, 100)),
                "player": ((80, 235, 255), (255, 255, 255)), "spark": ((80, 235, 255), (255, 255, 255)),
                "pierce": ((255, 100, 200), (255, 255, 255)), "core": ((255, 226, 100), (255, 255, 255))}


class Starfield:
    LAYERS = ((12.0, (60, 64, 130), 46), (28.0, (120, 130, 210), 30), (60.0, (205, 220, 255), 14))

    def __init__(self, rng=None):
        rng = rng or random.Random(7)
        self.stars = [[rng.uniform(0, cfg.FIELD_W), rng.uniform(0, cfg.FIELD_H), speed, color]
                      for speed, color, count in self.LAYERS for _ in range(count)]

    def update(self, dt, boost=1.0):
        for star in self.stars:
            star[1] += star[2] * dt * boost
            if star[1] >= cfg.FIELD_H:
                star[1] -= cfg.FIELD_H


class Fx:
    def __init__(self, reduced=False, rng=None):
        self.reduced = reduced
        self.rng = rng or random.Random(11)
        self.particles = []              # [x, y, vx, vy, life, max_life, color, size]
        self.rings = []                  # [x, y, age, life, max_radius, color]
        self.shake = 0.0
        self.flash = 0.0
        self.popups = []                 # [text, x, y, age, color]

    def burst(self, x, y, kind, big=False):
        count = (26 if big else 9) // (2 if self.reduced else 1)
        colors = BURST_COLORS.get(kind, BURST_COLORS["spark"])
        for _ in range(count):
            angle_x, angle_y = self.rng.uniform(-1, 1), self.rng.uniform(-1, 1)
            speed = self.rng.uniform(30, 120 if big else 80)
            life = self.rng.uniform(0.3, 0.7)
            self.particles.append([x, y, angle_x * speed, angle_y * speed, life, life,
                                   self.rng.choice(colors), 3 if big and self.rng.random() < .4 else 2])
        del self.particles[:-220]        # hard cap, however long the run
        self.ring(x, y, 26 if big else 12, colors[0])

    def ring(self, x, y, radius, color, life=0.35):
        if not self.reduced:
            self.rings.append([x, y, 0.0, life, radius, color])
            del self.rings[:-12]

    def muzzle(self, x, y, kind=""):
        if not self.reduced:
            colors = BURST_COLORS.get(kind or "spark")
            for dx in (-1, 1):
                self.particles.append([x, y, dx * 22, -10, 0.12, 0.12, colors[0], 1])

    def hit_shake(self, amount=0.25):
        if not self.reduced:
            self.shake = max(self.shake, amount)

    def pulse(self, amount=0.12):
        if not self.reduced:
            self.flash = max(self.flash, amount)

    def popup(self, text, x, y, color=(255, 226, 100)):
        self.popups.append([text, x, y, 0.0, color])
        del self.popups[:-6]

    def offset(self):
        if self.shake <= 0:
            return 0, 0
        amp = 1 + int(self.shake * 8)
        return self.rng.randint(-amp, amp), self.rng.randint(-amp, amp)

    def update(self, dt):
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for r in self.rings:
            r[2] += dt
        self.rings = [r for r in self.rings if r[2] < r[3]]
        for pop in self.popups:
            pop[3] += dt
        self.popups = [p for p in self.popups if p[3] < 1.2]
