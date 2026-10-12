"""The little shows the novelty items put on over the room (burps, rainbows, flickers ...).

NoveltyFX is owned by a room scene and anchored to the avatar that used the item. It only draws
particles and a speech bubble and darkens the room briefly for the battery: it never touches
movement, collision, scores or any profile data, and it runs on game time (dt), so it is
frame-rate independent.
"""
import math
import random

import pygame

from font import get_font
from gfx import scale_color
from settings import VIEW_H, VIEW_W, Col
from ui import draw_text

RAINBOW = ((255, 70, 90), (255, 160, 60), (255, 230, 80), (90, 230, 120), (80, 170, 255), (170, 120, 255))
DURATION = {"burp": 1.6, "munch": 1.8, "rainbow": 2.0, "squeak": 1.4, "flicker": 1.6, "mystery": 3.2}


class Show:
    def __init__(self, player, result, seed):
        self.player, self.result = player, result
        self.kind, self.text = result.effect, result.message
        self.duration = DURATION.get(self.kind, 1.6)
        self.t = 0.0
        self.rng = random.Random(seed)
        self.parts = []             # [x, y, vx, vy, life, color]

    @property
    def done(self):
        return self.t >= self.duration

    def anchor(self):
        return int(self.player.x), int(self.player.y) - 26

    def update(self, dt):
        self.t += dt
        ax, ay = self.anchor()
        if self.kind == "burp" and self.t < 1.0 and self.rng.random() < dt * 22:
            self.parts.append([ax + self.rng.randint(-5, 5), ay + 14, self.rng.uniform(-6, 6),
                               self.rng.uniform(-26, -14), 0.9, (170, 255, 150)])
        elif self.kind == "rainbow" and self.t < 0.9 and self.rng.random() < dt * 40:
            self.parts.append([ax + self.rng.randint(-12, 12), ay - 4, self.rng.uniform(-8, 8),
                               self.rng.uniform(-18, 4), 1.0, self.rng.choice(RAINBOW)])
        elif self.kind == "munch" and self.t < 1.4 and self.rng.random() < dt * 9:
            self.parts.append([ax + self.rng.randint(-3, 3), ay + 16, self.rng.uniform(-14, 14),
                               self.rng.uniform(-8, 6), 0.5, (255, 255, 255)])   # invisible crumbs, barely there
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]

    # ------------------------------------------------------------ drawing
    def draw(self, surf):
        ax, ay = self.anchor()
        for x, y, _, _, life, color in self.parts:
            if self.kind == "burp":
                pygame.draw.circle(surf, color, (int(x), int(y)), 1 + int(life * 2), 1)
            else:
                surf.fill(color, (int(x), int(y), 1 + (self.kind == "rainbow"), 1 + (self.kind == "rainbow")))
        if self.kind == "rainbow":
            self._rainbow(surf, ax, ay - 12)
        elif self.kind == "munch":
            self._munch(surf, ax, ay + 18)
        elif self.kind == "squeak":
            self._duck(surf, ax, ay - 4)
        elif self.kind == "flicker":
            self._battery(surf, ax, ay - 4)
        self._bubble(surf, ax, ay - 12)

    def _rainbow(self, surf, x, y):
        grow = min(1.0, self.t / 0.35)
        for i, color in enumerate(RAINBOW):
            r = int((16 - i * 2) * grow)
            if r > 1:
                pygame.draw.arc(surf, color, (x - r, y - r + 10, r * 2, r * 2), 0.0, math.pi, 1)

    def _munch(self, surf, x, y):
        open_ = int(self.t * 7) % 2                                 # chomp chomp
        pygame.draw.rect(surf, (255, 255, 255), (x - 4, y - 3 - open_, 8, 1))        # the sandwich (outline only)
        pygame.draw.rect(surf, (200, 210, 240), (x - 4, y - 2 - open_, 8, 4 + open_), 1)

    def _duck(self, surf, x, y):
        hop = int(abs(math.sin(self.t * 9)) * 5) if self.t < 1.0 else 0
        surf.fill((255, 214, 60), (x - 4, y - hop - 4, 8, 5))
        surf.fill((255, 214, 60), (x + 1, y - hop - 8, 4, 4))
        surf.fill((255, 130, 40), (x + 5, y - hop - 6, 3, 2))
        surf.fill((20, 12, 40), (x + 3, y - hop - 7, 1, 1))

    def _battery(self, surf, x, y):
        on = self.rng.random() > 0.35
        color = Col.GREEN if on else (40, 70, 50)
        surf.fill((190, 200, 210), (x - 3, y - 11, 6, 2))
        surf.fill(color, (x - 4, y - 9, 8, 11))
        if on:
            surf.fill(Col.YELLOW, (x - 1, y - 6, 2, 5))

    BUBBLE_MAX = 150
    HAS_SPRITE = ("rainbow", "squeak", "flicker")        # these draw something right above the head; the bubble sits over it

    def _bubble(self, surf, x, y):
        if self.t > self.duration - 0.25:
            return
        lines = _wrap(self.text, self.BUBBLE_MAX - 8)
        font = get_font()
        w = max(font.size(line)[0] for line in lines) + 8
        h = len(lines) * 9 + 5
        rect = pygame.Rect(0, 0, w, h)
        rect.midbottom = (x, y + 8 - (14 if self.kind in self.HAS_SPRITE else 0))
        rect.clamp_ip(pygame.Rect(3, 3, VIEW_W - 6, VIEW_H - 6))
        surf.fill((14, 10, 34), rect)
        pygame.draw.rect(surf, Col.CYAN if self.kind != "mystery" else Col.YELLOW, rect, 1)
        for i, line in enumerate(lines):
            draw_text(surf, line, (rect.centerx, rect.y + 3 + i * 9), Col.TEXT, anchor="midtop")

    def darkness(self):
        """0..1 how much the room dims (the battery's flicker)."""
        if self.kind != "flicker" or self.t > 1.3:
            return 0.0
        return 0.55 if int(self.t * 14) % 3 == 0 or int(self.t * 23) % 5 == 0 else 0.0


def _wrap(text, width):
    from ui import wrap_text
    return wrap_text(text, width) or [text]


class NoveltyFX:
    def __init__(self):
        self.shows = []
        self._seed = 0
        self._dim = None

    def start(self, player, result):
        self._seed += 1
        self.shows = [s for s in self.shows if s.player is not player]      # one show per player at a time
        self.shows.append(Show(player, result, self._seed))

    @property
    def active(self):
        return bool(self.shows)

    def clear(self):
        self.shows.clear()

    def update(self, dt):
        for s in self.shows:
            s.update(dt)
        self.shows = [s for s in self.shows if not s.done]

    def draw(self, surf):
        dark = max((s.darkness() for s in self.shows), default=0.0)
        if dark:
            if self._dim is None:
                self._dim = pygame.Surface((VIEW_W, VIEW_H))
            self._dim.set_alpha(int(150 * dark))
            surf.blit(self._dim, (0, 0))
        for s in self.shows:
            s.draw(surf)
