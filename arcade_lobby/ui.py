"""Neon arcade UI: translucent panels, pixel-font text helpers, the [E] PLAY
prompt, the controls box and the machine dialogue. Static parts are
pre-rendered; only small pieces are drawn per frame."""
import math
from functools import lru_cache

import pygame

from font import LINE_H, get_font
from gfx import scale_color, shade
from settings import (BACK_KEYS, CONFIRM_KEYS, Col, NEXT_KEYS, PREV_KEYS,
                      VIEW_H, VIEW_W)


def draw_text(surf, text, pos, color=Col.TEXT, scale=1, anchor="topleft", glow=None):
    """Blit cached pixel-font text. Returns the text rect."""
    font = get_font()
    img = font.render_glow(text, color, glow, scale) if glow else font.render(text, color, scale)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


def wrap_text(text, width, scale=1):
    font = get_font()
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial, scale)[0] <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


@lru_cache(maxsize=32)
def neon_panel(w, h, border=Col.CYAN, inner=Col.MAGENTA, alpha=225):
    """Dark translucent panel with a double neon border (cached per size)."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*border, 45), (0, 0, w, h), 1, border_radius=3)   # outer glow
    body = pygame.Rect(1, 1, w - 2, h - 2)
    pygame.draw.rect(s, (*Col.PANEL, alpha), body, border_radius=2)
    for y in range(body.y + 2, body.bottom - 2, 3):                         # faint scanlines
        s.fill((255, 255, 255, 7), (body.x + 2, y, body.w - 4, 1))
    pygame.draw.rect(s, border, body, 1, border_radius=2)
    if inner:
        pygame.draw.rect(s, (*inner, 150), body.inflate(-4, -4), 1)
    for cx, cy in ((body.x + 1, body.y + 1), (body.right - 4, body.y + 1),
                   (body.x + 1, body.bottom - 2), (body.right - 4, body.bottom - 2)):
        s.fill(Col.YELLOW, (cx, cy, 3, 1))
    return s


_dim = None


def dim_screen(surf, alpha):
    """Darken the whole view (the overlay surface is created once)."""
    global _dim
    if _dim is None:
        _dim = pygame.Surface((VIEW_W, VIEW_H))
        _dim.fill(Col.FADE)
    _dim.set_alpha(alpha)
    surf.blit(_dim, (0, 0))


class PromptBubble:
    """Animated '[E] PLAY' prompt: fades in, bobs and pulses."""
    FADE_SPEED = 6.0

    def __init__(self):
        self.frames = [self._build(Col.CYAN, Col.TEXT), self._build(shade(Col.CYAN, 0.5), Col.YELLOW)]
        self.alpha = 0.0
        self.anchor = None

    def _build(self, border, key_color):
        font = get_font()
        key = font.render_glow("[E]", key_color, scale_color(key_color, 0.35))
        label = font.render_glow("PLAY", Col.TEXT, scale_color(Col.MAGENTA, 0.6))
        w = key.get_width() + label.get_width() + 12
        h = 15
        s = pygame.Surface((w, h + 4), pygame.SRCALPHA)
        s.blit(neon_panel(w, h, border, None, 235), (0, 0))
        s.blit(key, (5, 4))
        s.blit(label, (8 + key.get_width(), 4))
        cx = w // 2
        pygame.draw.polygon(s, border, [(cx - 3, h - 1), (cx + 3, h - 1), (cx, h + 3)])
        return s

    def update(self, dt, anchor):
        """anchor: point above the nearby machine, or None to fade out."""
        target = 1.0 if anchor else 0.0
        step = self.FADE_SPEED * dt
        if target > self.alpha:
            self.alpha = min(target, self.alpha + step)
        else:
            self.alpha = max(target, self.alpha - step)
        if anchor:
            self.anchor = anchor

    def draw(self, surf, time):
        if self.alpha <= 0 or not self.anchor:
            return
        frame = self.frames[int(time * 3) % 2]
        bob = int(round(math.sin(time * 5) * 1.5))
        rise = int((1 - self.alpha) * 6)
        rect = frame.get_rect(midbottom=(self.anchor[0], self.anchor[1] + bob + rise))
        rect.clamp_ip(pygame.Rect(2, 2, VIEW_W - 4, VIEW_H - 4))
        frame.set_alpha(int(255 * self.alpha))
        surf.blit(frame, rect)


class InstructionBox:
    """Small always-visible controls reminder (pre-rendered)."""

    def __init__(self):
        self.image = neon_panel(84, 30).copy()
        draw_text(self.image, "MOVE: WASD", (7, 6), Col.TEXT)
        x = draw_text(self.image, "INTERACT:", (7, 17), Col.TEXT).right
        draw_text(self.image, "E", (x + 4, 17), Col.YELLOW)

    def draw(self, surf):
        surf.blit(self.image, (4, VIEW_H - self.image.get_height() - 4))


class DialogueBox:
    """Modal neon popup: glowing title, description and a vertical menu.

    `on_choice` is called with the chosen option label, or None when the
    box is dismissed with ESC.
    """
    W = 236

    def __init__(self, title, body, options, on_choice, accent=Col.CYAN, glow=Col.MAGENTA):
        self.title = title
        self.options = options
        self.on_choice = on_choice
        self.selected = 0
        self.anim = 0.0
        self.time = 0.0

        # Everything static is drawn once into self.image.
        lines = wrap_text(body, self.W - 24)
        h = 36 + len(lines) * LINE_H + 8 + len(options) * 13 + 20
        self.image = neon_panel(self.W, h, accent, glow).copy()
        draw_text(self.image, title, (self.W // 2, 9), shade(accent, 0.55), 2,
                  anchor="midtop", glow=scale_color(glow, 0.8))
        self.image.fill(scale_color(accent, 0.6), (12, 29, self.W - 24, 1))
        y = 36
        for line in lines:
            draw_text(self.image, line, (12, y), Col.TEXT_MUTED)
            y += LINE_H
        self.menu_y = y + 8
        draw_text(self.image, "UP/DOWN SELECT  E/ENTER OK  ESC BACK",
                  (self.W // 2, h - 13), scale_color(Col.TEXT_MUTED, 0.75), anchor="midtop")

        font = get_font()
        self.option_imgs = [(font.render(o, scale_color(Col.TEXT_MUTED, 0.9)),
                             font.render_glow(o, Col.TEXT, scale_color(accent, 0.7)))
                            for o in options]
        self.cursor = font.render_glow(">", Col.YELLOW, scale_color(Col.YELLOW, 0.4))
        self.bar = pygame.Surface((self.W - 40, 11), pygame.SRCALPHA)
        self.bar.fill((*accent, 45))
        self.bar.fill((*accent, 170), (0, 0, 2, 11))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in PREV_KEYS:
            self.selected = (self.selected - 1) % len(self.options)
        elif event.key in NEXT_KEYS:
            self.selected = (self.selected + 1) % len(self.options)
        elif event.key in CONFIRM_KEYS:
            self.on_choice(self.options[self.selected])
        elif event.key in BACK_KEYS:
            self.on_choice(None)

    def update(self, dt):
        self.anim = min(1.0, self.anim + dt * 7)
        self.time += dt

    def draw(self, surf):
        dim_screen(surf, int(140 * self.anim))
        ease = 1 - (1 - self.anim) ** 3
        rect = self.image.get_rect(center=(VIEW_W // 2, VIEW_H // 2 + int((1 - ease) * 14)))
        self.image.set_alpha(int(255 * min(1.0, self.anim * 1.5)))
        surf.blit(self.image, rect)

        for i, (plain, lit) in enumerate(self.option_imgs):
            y = rect.y + self.menu_y + i * 13
            if i == self.selected:
                surf.blit(self.bar, (rect.x + 20, y - 2))
                surf.blit(lit, (rect.x + 34, y - 1))
                nudge = int(math.sin(self.time * 9) * 1.5 + 1.5)
                if int(self.time * 4) % 4 != 3:  # blink
                    surf.blit(self.cursor, (rect.x + 24 + nudge, y - 1))
            else:
                surf.blit(plain, (rect.x + 35, y))
