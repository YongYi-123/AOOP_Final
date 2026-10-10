"""Bounded yarn trail advanced by simulation time, never by drawing frames."""
import pygame


class SmashTrail:
    LIFETIME = .18
    LIMIT = 16

    def __init__(self):
        self.points = []
        self.ball = None
        self.time = 0

    def update(self, dt, ball):
        if self.ball is not ball:
            self.points.clear()
            self.time = 0
            self.ball = ball
        self.time += dt
        self.points = [p for p in self.points if self.time - p[2] < self.LIFETIME]
        if ball.smash_left > 0 and dt > 0:
            self.points.append((ball.x, ball.y, self.time))
            self.points = self.points[-self.LIMIT:]

    def draw(self, surface):
        for x, y, stamp in self.points:
            fade = max(0, 1 - (self.time - stamp) / self.LIFETIME)
            color = (int(120*fade), int(55*fade), int(140*fade))
            pygame.draw.circle(surface, color, (round(x), round(y)), max(1, int(4*fade)))
