"""Particles, rings, score pop-ups, shake and flash. Visual only: nothing here affects the simulation."""
import math
import random

CYAN, PINK, GOLD, GREEN, WHITE = (90, 240, 255), (255, 120, 205), (255, 214, 90), (130, 255, 160), (255, 255, 255)

BURSTS = {                      # kind -> (count, speed, life, colours, size)
    "fish": (5, 26, 0.35, (PINK, WHITE), 1),
    "golden": (14, 52, 0.7, (GOLD, WHITE, (255, 240, 160)), 2),
    "catnip": (22, 70, 0.8, (GREEN, CYAN, WHITE), 2),
    "disable": (18, 64, 0.65, ((255, 150, 60), WHITE, (120, 180, 255)), 2),
    "death": (26, 58, 1.0, ((255, 190, 110), (255, 120, 205), WHITE), 2),
    "confetti": (3, 60, 1.6, (PINK, CYAN, GOLD, GREEN), 2),
}


class Fx:
    def __init__(self, reduced=False):
        self.reduced = reduced
        self.rng = random.Random(7)              # cosmetic only: never touches the game's rng
        self.particles = []                      # [x, y, vx, vy, life, max_life, colour, size] in canvas pixels
        self.rings = []                          # [x, y, radius, max_radius, life, max_life, colour]
        self.popups = []                         # [text, x, y, life, colour]
        self.shake = 0.0
        self.flash = 0.0
        self.flash_colour = (255, 90, 160)
        self.confetti_clock = 0.0

    def burst(self, kind, x, y):
        count, speed, life, colours, size = BURSTS[kind]
        if self.reduced:
            count = max(2, count // 3)
        for _ in range(count):
            a, v = self.rng.uniform(0, math.tau), self.rng.uniform(0.3, 1.0) * speed
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, life * self.rng.uniform(0.6, 1.0), life,
                                   self.rng.choice(colours), size])

    def ring(self, x, y, radius, colour, life=0.5):
        self.rings.append([x, y, 2.0, radius, life, life, colour])

    def popup(self, text, x, y, colour=WHITE, life=0.9):
        self.popups.append([text, x, y, life, colour])

    def hit_shake(self, amount=0.3):
        if not self.reduced:
            self.shake = max(self.shake, amount)

    def pulse(self, amount=0.18, colour=(255, 90, 160)):
        if not self.reduced:
            self.flash, self.flash_colour = max(self.flash, amount), colour

    def offset(self):
        if self.shake <= 0 or self.reduced:
            return 0, 0
        k = min(1.0, self.shake / 0.3) * 3
        return round(self.rng.uniform(-k, k)), round(self.rng.uniform(-k, k))

    def confetti(self, dt, width):
        """Keep a level-clear celebration raining down."""
        self.confetti_clock -= dt
        if self.confetti_clock <= 0:
            self.confetti_clock = 0.05 if not self.reduced else 0.2
            x = self.rng.uniform(20, width - 20)
            colour = self.rng.choice(BURSTS["confetti"][3])
            self.particles.append([x, -4, self.rng.uniform(-14, 14), self.rng.uniform(40, 80), 3.0, 3.0, colour, 2])

    def update(self, dt):
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 30 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for r in self.rings:
            r[4] -= dt
            r[2] = r[3] * (1 - max(0.0, r[4]) / r[5])
        self.rings = [r for r in self.rings if r[4] > 0]
        for pop in self.popups:
            pop[2] -= 14 * dt
            pop[3] -= dt
        self.popups = [p for p in self.popups if p[3] > 0]
        del self.particles[400:]
