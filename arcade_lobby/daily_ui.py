"""Neon UI for the daily systems: the DAILY BONUS! popup shown once when the
arcade is entered on a new day, and the DAILY CHALLENGES panel opened at the
board."""
import math

import pygame

from font import LINE_H, get_font
from gfx import scale_color, shade
from settings import (BACK_KEYS, CONFIRM_KEYS, NEXT_KEYS, PREV_KEYS, VIEW_H,
                      VIEW_W, Col)
from ui import dim_screen, draw_text, neon_panel


def token_icon(size=1):
    """The token coin (same look as the HUD icon), optionally scaled up."""
    s = pygame.Surface((7, 7), pygame.SRCALPHA)
    pygame.draw.circle(s, shade(Col.YELLOW, -0.45), (3, 3), 3)
    pygame.draw.circle(s, Col.YELLOW, (3, 3), 2)
    s.fill(shade(Col.YELLOW, 0.6), (2, 1, 1, 2))
    return pygame.transform.scale_by(s, size) if size != 1 else s


class DailyBonusPopup:
    """Modal 'DAILY BONUS!' card: streak day, the reward and a [CLAIM] button.

    `on_claim` runs at most once (the first confirm); after it the card
    flashes, a burst of tokens flies up, and `done` turns True. ESC closes it
    without claiming, so the bonus is offered again next time the arcade opens.
    """
    W, H = 172, 124
    CLAIM_TIME = 0.55

    def __init__(self, day, reward_lines, on_claim):
        """reward_lines: RewardBundle.lines(); the first is the headline."""
        self.day, self.on_claim = day, on_claim
        reward_lines = list(reward_lines) or ["+0 TOKENS"]
        self.reward_lines = reward_lines
        self.claimed = False
        self.dismissed = False
        self.anim = 0.0
        self.claim_age = 0.0
        self.time = 0.0
        font = get_font()
        self.image = neon_panel(self.W, self.H, Col.YELLOW, Col.MAGENTA).copy()
        cx = self.W // 2
        for text, y, color, scale, glow in (
                ("DAILY BONUS!", 8, shade(Col.YELLOW, 0.5), 2, scale_color(Col.MAGENTA, 0.8)),
                (f"DAY {day}", 30, Col.CYAN, 1, scale_color(Col.CYAN, 0.4))):
            img = font.render_glow(text, color, glow, scale)
            self.image.blit(img, img.get_rect(midtop=(cx, y)))
        self.image.fill(scale_color(Col.YELLOW, 0.5), (12, 26, self.W - 24, 1))
        self.reward = font.render_glow(reward_lines[0], Col.YELLOW, scale_color(Col.YELLOW, 0.45), 2)
        self.extras = [font.render_glow(t, Col.GREEN, scale_color(Col.GREEN, 0.4)) for t in reward_lines[1:]]
        self.button = font.render_glow("CLAIM", Col.TEXT, scale_color(Col.GREEN, 0.7), 1)
        self.coin = token_icon(2)

    @property
    def done(self):
        return self.dismissed or (self.claimed and self.claim_age >= self.CLAIM_TIME)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.claimed or self.dismissed:
            return
        if event.key in CONFIRM_KEYS:
            self.claimed = True          # set first: a second key press in the
            self.on_claim()              # same frame cannot claim again
        elif event.key in BACK_KEYS:
            self.dismissed = True

    def update(self, dt):
        self.time += dt
        self.anim = min(1.0, self.anim + dt * 6)
        if self.claimed:
            self.claim_age += dt

    def draw(self, surf):
        ease = 1 - (1 - self.anim) ** 3
        dim_screen(surf, int(150 * self.anim))
        rect = self.image.get_rect(center=(VIEW_W // 2, VIEW_H // 2 + int((1 - ease) * 16)))
        self.image.set_alpha(int(255 * min(1.0, self.anim * 1.5)))
        surf.blit(self.image, rect)

        bob = int(math.sin(self.time * 4) * 2)
        surf.blit(self.coin, self.coin.get_rect(midright=(rect.centerx - self.reward.get_width() // 2 - 4,
                                                            rect.y + 58 + bob)))
        surf.blit(self.reward, self.reward.get_rect(center=(rect.centerx + 8, rect.y + 58)))
        for i, line in enumerate(self.extras[:2]):
            surf.blit(line, line.get_rect(midtop=(rect.centerx, rect.y + 70 + i * LINE_H)))
        if not self.claimed:
            pulse = 0.55 + 0.45 * math.sin(self.time * 6)
            btn = pygame.Rect(0, 0, 64, 16)
            btn.midbottom = (rect.centerx, rect.bottom - 24)
            pygame.draw.rect(surf, scale_color(Col.GREEN, 0.25 + 0.2 * pulse), btn, border_radius=3)
            pygame.draw.rect(surf, scale_color(Col.GREEN, 0.6 + 0.4 * pulse), btn, 1, border_radius=3)
            surf.blit(self.button, self.button.get_rect(center=btn.center))
            draw_text(surf, "E/ENTER CLAIM  ESC LATER", (rect.centerx, rect.bottom - 15),
                      scale_color(Col.TEXT_MUTED, 0.75), anchor="midtop")
        else:
            self._draw_claim_effect(surf, rect)

    def _draw_claim_effect(self, surf, rect):
        k = min(1.0, self.claim_age / self.CLAIM_TIME)
        flash = pygame.Surface(rect.size)                   # small satisfying flash
        level = int(150 * (1 - k) ** 2)
        flash.fill((level, level, level * 3 // 4))
        surf.blit(flash, rect, special_flags=pygame.BLEND_RGB_ADD)
        for i in range(10):                                  # tokens burst upward
            a = -math.pi / 2 + (i - 4.5) * 0.28
            dist = 10 + k * (40 + (i % 3) * 14)
            pos = (rect.centerx + math.cos(a) * dist, rect.centery + 6 + math.sin(a) * dist)
            icon = self.coin if i % 2 else token_icon()
            icon.set_alpha(int(255 * (1 - k)))
            surf.blit(icon, icon.get_rect(center=(round(pos[0]), round(pos[1]))))


class TaskPanel:
    """The DAILY CHALLENGES list. UP/DOWN pick a task, E/ENTER claims it (when
    finished), ESC closes. The panel redraws only when a task changes."""
    W = 270
    ROW_H = 36

    def __init__(self, profile):
        self.profile = profile
        self.selected = 0
        self.closed = False
        self.anim = 0.0
        self.time = 0.0
        self._key = None
        self.image = None

    @property
    def tasks(self):
        return self.profile.daily_tasks

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.closed:
            return
        n = len(self.tasks)
        if event.key in BACK_KEYS:
            self.closed = True
        elif n and event.key in PREV_KEYS:
            self.selected = (self.selected - 1) % n
        elif n and event.key in NEXT_KEYS:
            self.selected = (self.selected + 1) % n
        elif n and event.key in CONFIRM_KEYS:
            self.profile.claim_task(self.tasks[self.selected].id)   # pays only if claimable

    def update(self, dt):
        self.anim = min(1.0, self.anim + dt * 7)
        self.time += dt

    # ------------------------------------------------------------ build
    def _snapshot(self):
        return (self.selected, tuple((t.id, t.progress, t.claimed) for t in self.tasks))

    def _rebuild(self):
        font = get_font()
        tasks = self.tasks
        h = 56 + max(1, len(tasks)) * self.ROW_H + 8
        img = neon_panel(self.W, h, Col.CYAN, Col.PURPLE).copy()
        title = font.render_glow("DAILY CHALLENGES", shade(Col.CYAN, 0.55), scale_color(Col.MAGENTA, 0.8), 2)
        img.blit(title, title.get_rect(midtop=(self.W // 2, 8)))
        img.fill(scale_color(Col.CYAN, 0.6), (12, 27, self.W - 24, 1))
        for i, task in enumerate(tasks):
            self._draw_task(img, font, task, 34 + i * self.ROW_H, i == self.selected)
        if not tasks:
            draw_text(img, "NO CHALLENGES TODAY", (self.W // 2, 40), Col.TEXT_MUTED, anchor="midtop")
        draw_text(img, "UP/DOWN SELECT  E CLAIM  ESC BACK", (self.W // 2, h - 13),
                  scale_color(Col.TEXT_MUTED, 0.75), anchor="midtop")
        self.image = img

    def _draw_task(self, img, font, task, y, selected):
        row = pygame.Rect(10, y, self.W - 20, self.ROW_H - 4)
        if selected:
            img.fill((*scale_color(Col.CYAN, 0.2),), row)
            img.fill(Col.CYAN, (row.x, row.y, 2, row.h))
        done_color = Col.GREEN if task.completed else Col.TEXT_MUTED
        box = pygame.Rect(row.x + 6, y + 3, 7, 7)
        pygame.draw.rect(img, done_color, box, 1)
        if task.completed:                                     # tick mark
            pygame.draw.lines(img, Col.GREEN, False, [(box.x + 1, box.y + 3), (box.x + 3, box.y + 5),
                                                      (box.x + 6, box.y + 1)], 1)
        dim = task.claimed
        draw_text(img, task.description, (row.x + 18, y + 3), Col.TEXT_MUTED if dim else Col.TEXT)
        bar = pygame.Rect(row.x + 18, y + 14, 110, 4)
        img.fill((52, 42, 96), bar)
        fill = int(bar.w * task.progress / task.target)
        img.fill(Col.GREEN if task.completed else Col.CYAN, (bar.x, bar.y, fill, bar.h))
        draw_text(img, f"{task.progress} / {task.target}", (bar.right + 6, y + 13), Col.TEXT_MUTED)
        reward = "  ".join(task.reward_bundle.lines())
        draw_text(img, reward, (row.x + 18, y + 22), shade(Col.YELLOW, -0.2) if dim else Col.YELLOW)
        if task.claimed:
            draw_text(img, "CLAIMED", (row.right - 6, y + 22), Col.TEXT_MUTED, anchor="topright")
        elif task.completed:
            draw_text(img, "[CLAIM]", (row.right - 6, y + 22), Col.GREEN, anchor="topright",
                      glow=scale_color(Col.GREEN, 0.4))

    def draw(self, surf):
        key = self._snapshot()
        if key != self._key:
            self._key = key
            self._rebuild()
        dim_screen(surf, int(140 * self.anim))
        ease = 1 - (1 - self.anim) ** 3
        rect = self.image.get_rect(center=(VIEW_W // 2, VIEW_H // 2 + int((1 - ease) * 14)))
        self.image.set_alpha(int(255 * min(1.0, self.anim * 1.5)))
        surf.blit(self.image, rect)
