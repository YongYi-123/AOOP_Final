"""Neon arcade UI: translucent panels, pixel-font text helpers, the [E] PLAY
prompt, the controls box and the machine dialogue. Static parts are
pre-rendered; only small pieces are drawn per frame."""
import math
from functools import lru_cache

import pygame

from font import LINE_H, get_font
from gfx import scale_color, shade
from settings import (BACK_KEYS, CONFIRM_KEYS, Col, NEXT_KEYS, PREV_KEYS,
                      ROOM_TITLE_TIME, VIEW_H, VIEW_W)


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
    """Animated '[E] PLAY' prompt: fades in, bobs and pulses. The label can
    change per target ('PLAY', 'PET', ...); each label is rendered once."""
    FADE_SPEED = 6.0

    def __init__(self, label="PLAY"):
        self._frames = {}
        self.label = label
        self.alpha = 0.0
        self.anchor = None

    @property
    def frames(self):
        frames = self._frames.get(self.label)
        if frames is None:
            frames = self._frames[self.label] = [
                self._build(Col.CYAN, Col.TEXT, self.label),
                self._build(shade(Col.CYAN, 0.5), Col.YELLOW, self.label)]
        return frames

    def _build(self, border, key_color, text):
        font = get_font()
        key = font.render_glow("[E]", key_color, scale_color(key_color, 0.35))
        label = font.render_glow(text, Col.TEXT, scale_color(Col.MAGENTA, 0.6))
        w = key.get_width() + label.get_width() + 12
        h = 15
        s = pygame.Surface((w, h + 4), pygame.SRCALPHA)
        s.blit(neon_panel(w, h, border, None, 235), (0, 0))
        s.blit(key, (5, 4))
        s.blit(label, (8 + key.get_width(), 4))
        cx = w // 2
        pygame.draw.polygon(s, border, [(cx - 3, h - 1), (cx + 3, h - 1), (cx, h + 3)])
        return s

    def update(self, dt, anchor, label=None):
        """anchor: point above the nearby target, or None to fade out. A new
        label only takes effect while shown, so a fading prompt keeps its text."""
        if anchor and label:
            self.label = label
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


_bubbles = {}


def speech_bubble_image(text):
    """Small pixel-art speech bubble with a tail at the bottom (cached)."""
    img = _bubbles.get(text)
    if img is None:
        label = get_font().render(text, (70, 44, 110))
        w, h = label.get_width() + 8, 13
        img = pygame.Surface((w, h + 3), pygame.SRCALPHA)
        img.fill(Col.OUTLINE, (1, 0, w - 2, h))
        img.fill(Col.OUTLINE, (0, 1, w, h - 2))
        img.fill((246, 240, 255), (2, 1, w - 4, h - 2))
        img.fill((246, 240, 255), (1, 2, w - 2, h - 4))
        img.fill((214, 200, 240), (2, h - 2, w - 4, 1))         # soft bottom shade
        cx = w // 2
        img.fill(Col.OUTLINE, (cx - 2, h - 1, 5, 1))            # tail
        img.fill((246, 240, 255), (cx - 1, h - 1, 3, 1))
        img.fill(Col.OUTLINE, (cx - 1, h, 3, 1))
        img.fill((246, 240, 255), (cx, h, 1, 1))
        img.fill(Col.OUTLINE, (cx, h + 1, 1, 1))
        img.blit(label, (4, 3))
        _bubbles[text] = img
    return img


class SpeechBubble:
    """A tiny bubble over an NPC: fades in, holds briefly, fades out."""
    FADE_IN, HOLD, FADE_OUT = 0.12, 0.9, 0.35

    def __init__(self):
        self.text = None
        self.age = 0.0

    @property
    def visible(self):
        return self.text is not None

    @property
    def duration(self):
        return self.FADE_IN + self.HOLD + self.FADE_OUT

    def show(self, text):
        self.text = text
        self.age = 0.0

    def clear(self):
        self.text = None

    def update(self, dt):
        if self.text is not None:
            self.age += dt
            if self.age >= self.duration:
                self.text = None

    @property
    def alpha(self):
        if self.text is None:
            return 0.0
        if self.age < self.FADE_IN:
            return self.age / self.FADE_IN
        return min(1.0, (self.duration - self.age) / self.FADE_OUT)

    def draw(self, surf, anchor):
        """anchor: the point the bubble's tail points at."""
        if self.text is None:
            return
        img = speech_bubble_image(self.text)
        rise = int((1 - min(1.0, self.age / self.FADE_IN)) * 3)
        rect = img.get_rect(midbottom=(anchor[0], anchor[1] + rise))
        rect.clamp_ip(pygame.Rect(2, 2, VIEW_W - 4, VIEW_H - 4))
        img.set_alpha(int(255 * self.alpha))
        surf.blit(img, rect)


class InstructionBox:
    """Small always-visible controls reminder (pre-rendered). Each room gives
    its own rows, so only the hints that matter there are on screen. A row is
    a list of (text, colour) pieces drawn left to right."""
    ROW_H = 11

    def __init__(self, rows=None):
        rows = rows or DEFAULT_HINTS
        font = get_font()
        widths = [sum(font.size(t)[0] + 4 for t, _ in row) for row in rows]
        w = max(84, max(widths) + 11)
        self.image = neon_panel(w, 8 + self.ROW_H * len(rows)).copy()
        for i, row in enumerate(rows):
            x, y = 7, 6 + i * self.ROW_H
            for text, color in row:
                x = draw_text(self.image, text, (x, y), color).right + 4

    def draw(self, surf):
        surf.blit(self.image, (4, VIEW_H - self.image.get_height() - 4))


DEFAULT_HINTS = (
    [("MOVE: WASD", Col.TEXT)],
    [("INTERACT:", Col.TEXT), ("E", Col.YELLOW)],
    [("I :", Col.TEXT), ("BAG", Col.YELLOW)],
)


class RoomTitle:
    """The neon name of a room (HOME, ARCADE FLOOR ...) that fades in when you
    walk in and fades away again. Pre-rendered; only the alpha changes."""
    FADE_IN, FADE_OUT = 0.3, 0.7

    def __init__(self, text, color, glow, hold=ROOM_TITLE_TIME, y=34):
        img = get_font().render_glow(text, color, glow, scale=3)
        self.image = img.copy()
        self.y = y
        self.hold = hold
        self.age = None         # None: not showing
        self.delay = 0.0

    @property
    def visible(self):
        return self.age is not None and self.age >= 0

    def show(self, delay=0.0):
        self.age = -delay

    def clear(self):
        self.age = None

    def update(self, dt):
        if self.age is not None:
            self.age += dt
            if self.age >= self.hold:
                self.age = None

    def alpha(self):
        if self.age is None or self.age < 0:
            return 0
        if self.age < self.FADE_IN:
            return int(255 * self.age / self.FADE_IN)
        left = self.hold - self.age
        return int(255 * min(1.0, left / self.FADE_OUT))

    def draw(self, surf):
        a = self.alpha()
        if a <= 0:
            return
        self.image.set_alpha(a)
        surf.blit(self.image, self.image.get_rect(midtop=(VIEW_W // 2, self.y)))


class DialogueBox:
    """Modal neon popup: glowing title, description and a vertical menu.

    `on_choice` is called with the chosen option label, or None when the
    box is dismissed with ESC - at most once, so a burst of key presses
    cannot confirm twice. `details` are extra (text, colour) lines shown
    under the body; options whose index is in `locked` are drawn dimmed
    (they can still be chosen, so the caller can explain why it failed).
    """
    W = 236

    def __init__(self, title, body, options, on_choice, accent=Col.CYAN, glow=Col.MAGENTA,
                 details=(), locked=(), input_delay=0.0):
        self.title = title
        self.body = body
        self.options = options
        self.on_choice = on_choice
        self.closed = False
        self.input_delay = input_delay   # seconds the box ignores keys after opening
        self.selected = 0
        self.anim = 0.0
        self.time = 0.0

        # Everything static is drawn once into self.image.
        lines = wrap_text(body, self.W - 24)
        details_h = len(details) * LINE_H + 4 if details else 0
        h = 36 + len(lines) * LINE_H + details_h + 8 + len(options) * 13 + 20
        self.image = neon_panel(self.W, h, accent, glow).copy()
        draw_text(self.image, title, (self.W // 2, 9), shade(accent, 0.55), 2,
                  anchor="midtop", glow=scale_color(glow, 0.8))
        self.image.fill(scale_color(accent, 0.6), (12, 29, self.W - 24, 1))
        y = 36
        for line in lines:
            draw_text(self.image, line, (12, y), Col.TEXT_MUTED)
            y += LINE_H
        if details:
            y += 4
            for text, color in details:
                draw_text(self.image, text, (12, y), color)
                y += LINE_H
        self.menu_y = y + 8
        draw_text(self.image, "UP/DOWN SELECT  E/ENTER OK  ESC BACK",
                  (self.W // 2, h - 13), scale_color(Col.TEXT_MUTED, 0.75), anchor="midtop")

        font = get_font()
        self.option_imgs = [
            (font.render(o, scale_color(Col.TEXT_MUTED, 0.55)),
             font.render_glow(o, Col.TEXT_MUTED, scale_color(Col.MAGENTA, 0.45))) if i in locked else
            (font.render(o, scale_color(Col.TEXT_MUTED, 0.9)),
             font.render_glow(o, Col.TEXT, scale_color(accent, 0.7)))
            for i, o in enumerate(options)]
        self.cursor = font.render_glow(">", Col.YELLOW, scale_color(Col.YELLOW, 0.4))
        self.bar = pygame.Surface((self.W - 40, 11), pygame.SRCALPHA)
        self.bar.fill((*accent, 45))
        self.bar.fill((*accent, 170), (0, 0, 2, 11))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.closed or self.time < self.input_delay:
            return
        if event.key in PREV_KEYS:
            self.selected = (self.selected - 1) % len(self.options)
        elif event.key in NEXT_KEYS:
            self.selected = (self.selected + 1) % len(self.options)
        elif event.key in CONFIRM_KEYS:
            self._close(self.options[self.selected])
        elif event.key in BACK_KEYS:
            self._close(None)

    def _close(self, choice):
        self.closed = True
        self.on_choice(choice)

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


class Notice:
    """Short non-blocking message card (e.g. GAME COMPLETE / NOT ENOUGH COINS)
    that pops in near the top of the room and fades out by itself."""
    DURATION = 2.2
    FADE = 0.25

    def __init__(self, center=(VIEW_W // 2, 140)):
        self.center = center
        self.image = None
        self.left = 0.0

    def show(self, title, lines=(), color=Col.CYAN):
        """lines: (text, colour) pairs under the title."""
        font = get_font()
        head = font.render_glow(title, shade(color, 0.6), scale_color(color, 0.7), scale=2)
        w = max([head.get_width()] + [font.size(t)[0] for t, _ in lines]) + 24
        h = 12 + head.get_height() + len(lines) * LINE_H + 6
        self.image = neon_panel(w, h, color, Col.PURPLE, 235).copy()
        self.image.blit(head, head.get_rect(midtop=(w // 2, 7)))
        y = 10 + head.get_height() + 2
        for text, c in lines:
            draw_text(self.image, text, (w // 2, y), c, anchor="midtop")
            y += LINE_H
        self.left = self.DURATION

    def clear(self):
        self.left = 0.0

    @property
    def visible(self):
        return self.left > 0

    def update(self, dt):
        self.left = max(0.0, self.left - dt)

    def draw(self, surf):
        if not self.visible:
            return
        shown = self.DURATION - self.left
        k = min(1.0, shown / self.FADE, self.left / self.FADE)
        rect = self.image.get_rect(center=(self.center[0], self.center[1] + int((1 - k) * 6)))
        self.image.set_alpha(int(255 * k))
        surf.blit(self.image, rect)
