"""Bounded impact flashes, speed trail and screen shake, advanced by simulation time only."""
import math
import pygame

NEON_PINK, NEON_YELLOW, NEON_CYAN, WHITE = (255, 110, 210), (255, 224, 90), (90, 240, 255), (255, 255, 255)


class SmashTrail:
    LIFETIME = .30
    LIMIT = 24
    BURST_LIFE = {"spike": .32, "hit": .14}
    SHAKE_TIME = .16
    SHAKE_PIXELS = 3
    POPUP_LIFE = .6

    def __init__(self):
        self.points = []
        self.bursts = []        # [x, y, kind, age]
        self.popups = []        # [x, y, age]
        self.shake_left = 0.0
        self.ball = None
        self.time = 0

    def update(self, dt, ball, impacts=()):
        if self.ball is not ball:
            self.points.clear()
            self.time = 0
            self.ball = ball
        self.time += dt
        self.points = [p for p in self.points if self.time - p[2] < self.LIFETIME]
        if ball.smash_left > 0 and dt > 0:
            self.points.append((ball.x, ball.y, self.time))
            self.points = self.points[-self.LIMIT:]
        for burst in self.bursts:
            burst[3] += dt
        self.bursts = [b for b in self.bursts if b[3] < self.BURST_LIFE[b[2]]]
        for popup in self.popups:
            popup[2] += dt
        self.popups = [p for p in self.popups if p[2] < self.POPUP_LIFE]
        self.shake_left = max(0.0, self.shake_left - dt)
        for x, y, kind, _side in impacts:
            self.bursts.append([x, y, kind, 0.0])
            if kind == "spike":
                self.popups.append([x, y, 0.0])
                self.shake_left = self.SHAKE_TIME

    def shake_offset(self):
        """Deterministic jitter that decays to nothing; never random, never stored."""
        if self.shake_left <= 0:
            return 0, 0
        amount = max(1, round(self.SHAKE_PIXELS * self.shake_left / self.SHAKE_TIME))
        phase = int(self.shake_left * 400)
        return (amount if phase % 2 else -amount), (amount if phase // 2 % 2 else -amount) // 2

    def draw(self, surface):
        self._draw_trail(surface)
        for x, y, kind, age in self.bursts:
            self._draw_burst(surface, round(x), round(y), kind, age / self.BURST_LIFE[kind])

    def _draw_trail(self, surface):
        previous = None
        for x, y, stamp in self.points:
            fade = max(0, 1 - (self.time - stamp) / self.LIFETIME)
            if previous is not None:
                pygame.draw.line(surface, tuple(int(c * fade) for c in NEON_PINK),
                                 previous, (round(x), round(y)), max(1, int(7 * fade)))
                pygame.draw.line(surface, tuple(int(c * fade) for c in NEON_YELLOW),
                                 previous, (round(x), round(y)), max(1, int(3 * fade)))
            previous = (round(x), round(y))

    @staticmethod
    def _draw_burst(surface, x, y, kind, progress):
        if kind == "hit":
            pygame.draw.circle(surface, NEON_CYAN, (x, y), 5 + int(8 * progress), 1)
            return
        if progress < .25:   # white-hot flash on the first frames of the impact
            pygame.draw.circle(surface, WHITE, (x, y), 11 - int(8 * progress))
        pygame.draw.circle(surface, NEON_YELLOW, (x, y), 6 + int(20 * progress), 2)
        pygame.draw.circle(surface, NEON_PINK, (x, y), 3 + int(13 * progress), 1)
        for i in range(8):
            angle = i * math.pi / 4 + .39
            inner, outer = 8 + 16 * progress, 14 + 22 * progress
            pygame.draw.line(surface, NEON_YELLOW if i % 2 else WHITE,
                             (x + math.cos(angle) * inner, y + math.sin(angle) * inner),
                             (x + math.cos(angle) * outer, y + math.sin(angle) * outer), 2)
