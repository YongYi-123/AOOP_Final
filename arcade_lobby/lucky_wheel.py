"""LuckyWheelGame: pay 1 token, watch the wheel spin, win 0-10 tokens.

The reward is drawn from the weight table (settings.LUCKY_WHEEL_REWARDS) the
moment the round starts - the animation only reveals it - so closing the game
mid-spin settles the same prize instead of losing or re-rolling it. The odds
are shown on screen and never depend on the player.
"""
import math

import pygame

from chance_game import (ChanceGame, draw_centered, draw_chance_backdrop,
                         token_text)
from font import get_font
from gfx import scale_color, shade
from settings import (LUCKY_WHEEL_COST, LUCKY_WHEEL_REWARDS, LUCKY_WHEEL_SLICES, Col)

SLICE_COLORS = {0: (74, 56, 122), 1: (60, 170, 205), 2: (70, 190, 120), 3: (225, 190, 70),
                5: (225, 80, 170), 10: (250, 235, 200)}
CENTER, RADIUS = (118, 140), 66
SPIN_TIME = 3.6
SPIN_TURNS = 4          # full turns before stopping on the result
REVEAL_HOLD = 0.9       # the result is paid after the wheel has rested this long


class LuckyWheelGame(ChanceGame):
    id = "lucky_wheel"
    name = "LUCKY WHEEL"
    ready_text = "SPIN"

    def __init__(self, rewards=LUCKY_WHEEL_REWARDS, slices=LUCKY_WHEEL_SLICES,
                 cost=LUCKY_WHEEL_COST, rng=None):
        super().__init__(cost, rng)
        if not rewards or any(r["weight"] <= 0 for r in rewards):
            raise ValueError("every wheel reward needs a positive weight")
        self.rewards = [dict(r) for r in rewards]
        self.slices = tuple(slices)
        shown = {r["tokens"] for r in self.rewards}
        if not slices or set(self.slices) - shown or shown - set(self.slices):
            raise ValueError("the painted slices must show exactly the rewards in the table")
        self.rotation = 0.0         # degrees, clockwise
        self.time = 0.0
        self.spin_time = 0.0
        self.rest_time = 0.0
        self.prize = None           # tokens the wheel will stop on, fixed at start
        self._from = self._extra = 0.0

    # ------------------------------------------------------------ odds
    @property
    def total_weight(self):
        return sum(r["weight"] for r in self.rewards)

    def probabilities(self):
        """Reward tokens -> chance of landing on it (sums to 1)."""
        return {r["tokens"]: r["weight"] / self.total_weight for r in self.rewards}

    def expected_payout(self):
        return sum(tokens * p for tokens, p in self.probabilities().items())

    def _draw_prize(self):
        pick = self.rng.uniform(0, self.total_weight)
        for r in self.rewards:
            pick -= r["weight"]
            if pick < 0:
                return r["tokens"]
        return self.rewards[-1]["tokens"]

    # ------------------------------------------------------------ round
    @property
    def slice_angle(self):
        return 360 / len(self.slices)

    def _begin(self):
        self.prize = self._draw_prize()
        target = self.rng.choice([i for i, t in enumerate(self.slices) if t == self.prize])
        jitter = self.rng.uniform(-0.35, 0.35) * self.slice_angle
        stop = (-(target + 0.5) * self.slice_angle + jitter) % 360
        self._from = self.rotation % 360
        self._extra = SPIN_TURNS * 360 + (stop - self._from) % 360

    def slice_under_pointer(self):
        return int((-self.rotation % 360) // self.slice_angle)

    def _settle_unfinished(self):
        self.rotation = self._from + self._extra
        self._resolve(self.prize, self._summary())

    def _summary(self):
        if self.prize == 0:
            return "NO LUCK THIS TIME"
        return f"YOU WON {token_text(self.prize)}!"

    def update(self, dt):
        self.time += dt
        if self.phase != self.PLAYING:
            return
        if self.spin_time < SPIN_TIME:
            self.spin_time = min(SPIN_TIME, self.spin_time + dt)
            k = self.spin_time / SPIN_TIME
            self.rotation = self._from + self._extra * (1 - (1 - k) ** 3)
        else:
            self.rest_time += dt
            if self.rest_time >= REVEAL_HOLD:
                self._resolve(self.prize, self._summary())

    # ------------------------------------------------------------ draw
    def _point(self, angle, r):
        a = math.radians(angle)
        return (CENTER[0] + math.sin(a) * r, CENTER[1] - math.cos(a) * r)

    def draw(self, surf):
        draw_chance_backdrop(surf, (14, 6, 34), (52, 12, 60), Col.MAGENTA, self.time)
        font = get_font()
        draw_centered(surf, "LUCKY WHEEL", 12, shade(Col.MAGENTA, 0.55), 2, scale_color(Col.MAGENTA, 0.8))
        self._draw_wheel(surf)
        self._draw_odds(surf)
        self._draw_result(surf, font)

    def _draw_wheel(self, surf):
        step = self.slice_angle
        spinning = self.phase == self.PLAYING and self.spin_time < SPIN_TIME
        pygame.draw.circle(surf, scale_color(Col.MAGENTA, 0.35), CENTER, RADIUS + 7)
        for i, tokens in enumerate(self.slices):
            a0 = self.rotation + i * step
            color = SLICE_COLORS.get(tokens, Col.PURPLE)
            if self.phase != self.IDLE and i == self.slice_under_pointer() and not spinning:
                color = shade(color, 0.35)
            arc = [self._point(a0 + step * k / 4, RADIUS) for k in range(5)]
            pygame.draw.polygon(surf, color, [CENTER] + arc)
            pygame.draw.line(surf, Col.PANEL, CENTER, arc[0])
            label = get_font().render(str(tokens), Col.PANEL if tokens in (3, 10) else Col.TEXT)
            x, y = self._point(a0 + step / 2, RADIUS * 0.72)
            surf.blit(label, label.get_rect(center=(round(x), round(y))))
        pygame.draw.circle(surf, Col.MAGENTA, CENTER, RADIUS, 2)
        for i in range(24):                                    # rim lamps
            lit = (int(self.time * (14 if spinning else 3)) + i) % 3 == 0
            x, y = self._point(i * 15, RADIUS + 3)
            surf.fill(Col.YELLOW if lit else scale_color(Col.YELLOW, 0.3), (round(x) - 1, round(y) - 1, 2, 2))
        pygame.draw.circle(surf, Col.PANEL, CENTER, 9)
        pygame.draw.circle(surf, Col.YELLOW, CENTER, 9, 1)
        tip, x = CENTER[1] - RADIUS - 2, CENTER[0]                # pointer
        pygame.draw.polygon(surf, Col.YELLOW, [(x - 6, tip - 9), (x + 6, tip - 9), (x, tip + 6)])
        pygame.draw.polygon(surf, Col.OUTLINE, [(x - 6, tip - 9), (x + 6, tip - 9), (x, tip + 6)], 1)

    def _draw_odds(self, surf):
        """Every possible reward with its rarity and chance, so nothing is hidden."""
        font = get_font()
        x0, y0, w = 214, 52, 170
        panel = pygame.Surface((w, 12 * len(self.rewards) + 30), pygame.SRCALPHA)
        panel.fill((10, 6, 26, 215))
        pygame.draw.rect(panel, scale_color(Col.MAGENTA, 0.8), panel.get_rect(), 1)
        surf.blit(panel, (x0, y0))
        surf.blit(font.render("PRIZES AND ODDS", Col.TEXT_MUTED), (x0 + 8, y0 + 6))
        for i, r in enumerate(self.rewards):
            y = y0 + 20 + i * 12
            color = SLICE_COLORS.get(r["tokens"], Col.TEXT)
            if self.prize == r["tokens"] and self.phase == self.DONE:
                surf.fill((*scale_color(color, 0.4),), (x0 + 3, y - 2, w - 6, 11))
            surf.blit(font.render(token_text(r["tokens"]), color), (x0 + 8, y))
            surf.blit(font.render(r["rarity"], Col.TEXT_MUTED), (x0 + 70, y))
            chance = f"{r['weight']}/{self.total_weight}"
            surf.blit(font.render(chance, Col.TEXT), (x0 + w - 8 - font.size(chance)[0], y))

    def _draw_result(self, surf, font):
        if self.phase == self.DONE:
            result = self.get_result()
            color = Col.GREEN if result.payout else Col.TEXT_MUTED
            draw_centered(surf, result.summary, 224, color, 2, scale_color(color, 0.4))
            draw_centered(surf, "E: SPIN AGAIN", 244, Col.YELLOW)
        elif self.phase == self.PLAYING:
            dots = "." * (1 + int(self.time * 4) % 3)
            draw_centered(surf, f"SPINNING{dots}", 228, Col.CYAN)
