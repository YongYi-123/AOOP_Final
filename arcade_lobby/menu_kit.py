"""Shared building blocks for the full-screen Prize Plaza / Home menus (shop,
wardrobe, collection, decoration mode), so they all look and behave alike.

MenuScene is a scene owned by ONE local player: only that player's keys (and
the shared ESC) drive it and everything it shows or changes is that player's
profile. Subclasses draw into the 400x300 logical canvas (the same pixel art
scaling as the rest of the game) using the helpers here: a neon frame with an
animated light chase, a header with the ticket balance, tabs, list rows with
a scrollbar, a footer with a message line and key hints. Mouse: clicks and the
wheel are converted to canvas pixels (`mouse_pos`).
"""
import math

import pygame

from font import LINE_H, get_font
from gfx import scale_color, shade
from input_router import PlayerInput
from scene_base import BaseScene
from settings import VIEW_H, VIEW_W, Col
from ui import dim_screen, draw_text, neon_panel

GOLD, ROSE = Col.YELLOW, (255, 110, 190)
ROW_H = 18
FRAME = pygame.Rect(6, 6, VIEW_W - 12, VIEW_H - 12)


def fit_text(text, width, scale=1):
    """`text` shortened with '..' so it is never wider than `width` pixels."""
    font = get_font()
    if font.size(text, scale)[0] <= width:
        return text
    while text and font.size(text + "..", scale)[0] > width:
        text = text[:-1]
    return text.rstrip() + ".."


_ticket_cache = {}


def item_icon_for_ticket(color):
    icon = _ticket_cache.get(color)
    if icon is None:
        s = pygame.Surface((9, 6), pygame.SRCALPHA)
        s.fill(color, (0, 0, 9, 6))
        s.fill((0, 0, 0, 0), (0, 2, 1, 2))
        s.fill((0, 0, 0, 0), (8, 2, 1, 2))
        s.fill(shade(color, -0.45), (6, 1, 1, 1))
        s.fill(shade(color, -0.45), (6, 3, 1, 1))
        s.fill(shade(color, -0.45), (6, 5, 1, 1))
        s.fill(shade(color, 0.55), (1, 1, 4, 1))
        _ticket_cache[color] = icon = s
    return icon


class MenuScene(BaseScene):
    """A pushed, single-owner menu. Subclasses implement `on_action(action)`
    (up / down / left / right / interact / menu / back) and `draw_body(surf)`."""
    title = "MENU"
    accent = GOLD
    glow = ROSE
    hints = ("UP/DOWN SELECT", "E OK", "ESC BACK")

    def __init__(self, game, owner):
        super().__init__(game)
        self.owner = owner                      # the LocalPlayer
        self.profile = owner.profile
        self.input = PlayerInput(owner.controls)
        self.spectators = [p for p in game.session if p is not owner]
        self.time = 0.0
        self.message = ""
        self.message_color = Col.TEXT_MUTED
        self.message_time = 0.0
        self.modal = None                       # a DialogueBox drawn over the screen
        self._hit = []                          # [(Rect, callback)] rebuilt every frame

    # ------------------------------------------------------------ plumbing
    def say(self, text, color=Col.TEXT_MUTED, seconds=2.5):
        self.message, self.message_color, self.message_time = text, color, seconds

    def close(self):
        self.game.scenes.pop()

    def play(self, sound):
        audio = getattr(self.game, "audio", None)
        if audio is not None:
            audio.play(sound)

    def mouse_pos(self, pos):
        w, h = self.game.screen.get_size()
        return int(pos[0] * VIEW_W / w), int(pos[1] * VIEW_H / h)

    def update(self, dt):
        self.time += dt
        self.message_time = max(0.0, self.message_time - dt)
        if self.modal is not None:
            self.modal.update(dt)

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        action = self.input.feed(event)
        if self.modal is not None:
            if event.type == pygame.KEYDOWN and (self.owner.controls.owns(event.key) or action == "back"):
                self.modal.handle_event(event)
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._click(event)
        elif event.type == pygame.MOUSEWHEEL:
            self.on_action("up" if event.y > 0 else "down")
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:       # a shared key: any player may use it on their own menu
                self.on_action("tab")
            elif action:
                self.on_action(action)

    def _click(self, event):
        if event.button != 1:
            return
        pos = self.mouse_pos(event.pos)
        for rect, callback in reversed(self._hit):
            if rect.collidepoint(pos):
                callback()
                return

    def on_action(self, action):
        raise NotImplementedError

    def hit(self, rect, callback):
        """Make `rect` (canvas pixels) clickable for this frame."""
        self._hit.append((pygame.Rect(rect), callback))

    # ------------------------------------------------------------ drawing helpers
    def draw_frame(self, surf, title=None, subtitle=None):
        """Backdrop, neon frame with a chasing light, the title, the owner and tickets."""
        surf.fill((12, 7, 30))
        for y in range(0, VIEW_H, 12):
            pygame.draw.line(surf, (24, 15, 46), (0, y), (VIEW_W, y))
        for x in range(0, VIEW_W, 16):
            pygame.draw.line(surf, (20, 12, 40), (x, 0), (x, VIEW_H))
        surf.blit(neon_panel(FRAME.w, FRAME.h, self.accent, self.glow, 235), FRAME.topleft)
        self._chase(surf)
        draw_text(surf, title or self.title, (16, 12), shade(self.accent, 0.4), 2,
                  glow=scale_color(self.glow, 0.8))
        draw_text(surf, subtitle or self.owner.tag, (16, 30), self.owner.avatar.look.accent
                  if self.owner.label else Col.CYAN)
        self.draw_balance(surf)

    def draw_balance(self, surf):
        text = str(self.profile.tickets)
        w = get_font().size(text, 2)[0]
        right = FRAME.right - 10
        draw_text(surf, text, (right, 12), GOLD, 2, anchor="topright", glow=(120, 80, 10))
        surf.blit(item_icon_for_ticket(GOLD), (right - w - 13, 15))
        draw_text(surf, "TICKETS", (right, 30), Col.TEXT_MUTED, anchor="topright")

    def _chase(self, surf):
        """A string of lights running round the frame (cheap: a few pixels per frame)."""
        perimeter = 2 * (FRAME.w + FRAME.h)
        for i in range(0, perimeter, 14):
            d = (i + int(self.time * 26)) % perimeter
            if d < FRAME.w:
                p = (FRAME.x + d, FRAME.y)
            elif d < FRAME.w + FRAME.h:
                p = (FRAME.right - 1, FRAME.y + d - FRAME.w)
            elif d < 2 * FRAME.w + FRAME.h:
                p = (FRAME.right - 1 - (d - FRAME.w - FRAME.h), FRAME.bottom - 1)
            else:
                p = (FRAME.x, FRAME.bottom - 1 - (d - 2 * FRAME.w - FRAME.h))
            color = (GOLD, ROSE, Col.CYAN)[(i // 14) % 3]
            surf.fill(color, (*p, 2, 2))

    def draw_tabs(self, surf, names, active, y=44, x=14, on_click=None):
        """A row of tabs; returns nothing. `on_click(index)` makes them clickable."""
        font = get_font()
        for i, name in enumerate(names):
            w = font.size(name)[0] + 12
            rect = pygame.Rect(x, y, w, 12)
            if i == active:
                surf.fill(scale_color(self.accent, 0.35), rect)
                surf.fill(self.accent, (rect.x, rect.bottom - 1, rect.w, 1))
            else:
                surf.fill((26, 18, 52), rect)
            draw_text(surf, name, (rect.x + 6, rect.y + 3), Col.TEXT if i == active else Col.TEXT_MUTED)
            if on_click:
                self.hit(rect, lambda i=i: on_click(i))
            x += w + 3
        return x

    def draw_scrollbar(self, surf, rect, first, visible, total):
        if total <= visible:
            return
        surf.fill((30, 22, 60), (rect.right - 3, rect.y, 2, rect.h))
        bar_h = max(6, rect.h * visible // total)
        top = rect.y + (rect.h - bar_h) * first // max(1, total - visible)
        surf.fill(self.accent, (rect.right - 3, top, 2, bar_h))

    def draw_row_bg(self, surf, rect, selected, owned=False, dim=False):
        surf.fill((18, 12, 40) if not selected else scale_color(self.accent, 0.28), rect)
        if selected:
            pulse = 0.65 + 0.35 * math.sin(self.time * 8)
            pygame.draw.rect(surf, scale_color(self.accent, pulse), rect, 1)
        elif owned:
            surf.fill((70, 200, 130), (rect.x, rect.y, 1, rect.h))

    def draw_footer(self, surf, hints=None):
        box = pygame.Rect(14, 229, FRAME.w - 16, 14)
        surf.fill((16, 10, 36), box)
        pygame.draw.rect(surf, scale_color(self.accent, 0.4), box, 1)
        if self.message_time > 0 and self.message:
            draw_text(surf, fit_text(self.message, box.w - 12), box.center, self.message_color, anchor="center")
        else:
            draw_text(surf, fit_text(self.idle_message(), box.w - 12), box.center, Col.TEXT_MUTED, anchor="center")
        y = 248
        for line in self.hint_lines(hints or self.hints):
            draw_text(surf, line, (VIEW_W // 2, y), scale_color(Col.TEXT_MUTED, 0.9), anchor="midtop")
            y += LINE_H + 2

    def hint_lines(self, hints):
        """Hints split into two centred lines that never overflow the frame."""
        width = FRAME.w - 24
        font = get_font()
        lines, line = [], ""
        for hint in hints:
            trial = f"{line}   {hint}".strip()
            if font.size(trial)[0] <= width:
                line = trial
            else:
                lines.append(line)
                line = hint
        if line:
            lines.append(line)
        return lines

    def idle_message(self):
        return ""

    spectator_pos = "bottom"            # "bottom": inside the frame; "topright": over a room view

    def draw_overlay(self, surf, px=1):
        """The quiet 'P2 BO - SPECTATING' tag, kept inside the menu frame (the default
        corner tag would sit on top of the frame's border)."""
        if not self.spectators:
            return
        text = "  ".join(f"{p.tag} - SPECTATING" for p in self.spectators)
        img = get_font().render_glow(text, Col.TEXT_MUTED, (40, 30, 70), scale=px)
        if self.spectator_pos == "topright":
            rect = img.get_rect(topright=(surf.get_width() - 6 * px, 4 * px))
        else:
            rect = img.get_rect(midbottom=(surf.get_width() // 2, surf.get_height() - 9 * px))
        surf.blit(img, rect)

    def draw(self, surf):
        self._hit = []
        self.draw_body(surf)
        if self.modal is not None:
            dim_screen(surf, 175)           # the question stands out from the busy screen behind it
            self.modal.draw(surf)

    def draw_body(self, surf):
        raise NotImplementedError
