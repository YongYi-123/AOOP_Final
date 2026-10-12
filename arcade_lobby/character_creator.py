"""CHARACTER CREATOR: pick a new profile's look BEFORE it enters the hub.

Shown by the startup flow after a new profile's name has been typed and before
the profile exists: BACK leaves nothing behind, CONFIRM creates the profile
with the chosen look. Every option here (skin tone, eyes, hair, hair colour,
shirt colour) is free - see avatar_style.py. The avatar is previewed live
from the front and from the side with the real sprite painter (player.py),
so what is previewed is exactly what walks into the hub.

Keyboard: UP/DOWN pick a row, LEFT/RIGHT change it, E/ENTER next row (CONFIRM
on the button), ESC back. Mouse: click a swatch or arrow, or a button.
"""
import random

import pygame

from avatar_style import (FIELD_NAMES, FIELDS, OPTIONS, BasicAppearance, option, random_basic,
                          swatch_color)
from font import LINE_H
from gfx import scale_color, shade
from menus import MenuScene, draw_centered
from player import styled_sheet
from preview_art import pedestal, scaled
from display import screen_to_canvas
from settings import BACK_KEYS, CONFIRM_KEYS, VIEW_H, VIEW_W, Col
from ui import draw_text, neon_panel

PANEL = pygame.Rect(14, 10, VIEW_W - 28, VIEW_H - 20)
STAGE = pygame.Rect(30, 52, 150, 150)
LIST_X, LIST_W = 196, 176
BUTTONS = ("BACK", "CONFIRM")
PREVIEW_SCALE = 5
MINI_SCALE = 2


class CharacterCreatorScene(MenuScene):
    """`on_confirm(basic)` / `on_back()` are called by the flow's hooks; the scene never touches saves."""

    def __init__(self, game, flow, name, look, on_confirm, on_back, basic=None):
        super().__init__(game, flow)
        self.name = name
        self.look = look                        # P1_LOOK / P2_LOOK / DEFAULT_LOOK: its outline stays
        self.basic = basic or BasicAppearance()
        self.on_confirm_cb, self.on_back_cb = on_confirm, on_back
        self.row = 0                            # 0..4 the fields, 5 BACK, 6 CONFIRM
        self.done = False
        self._hit = []
        self.mini_cache = {}

    # ------------------------------------------------------------ state
    @property
    def rows(self):
        return len(FIELDS) + len(BUTTONS)

    @property
    def on_button(self):
        return self.row >= len(FIELDS)

    @property
    def field(self):
        return FIELDS[self.row] if not self.on_button else None

    def choose(self, field, option_id):
        self.basic = self.basic.with_choice(field, option_id)

    def cycle(self, step, field=None):
        """Move the highlighted (or given) field to its next / previous option."""
        field = field or self.field
        if field is None:
            return
        options = OPTIONS[field]
        index = next(i for i, o in enumerate(options) if o.id == self.basic.get(field))
        self.choose(field, options[(index + step) % len(options)].id)

    def confirm(self):
        if not self.done:
            self.done = True
            self.on_confirm_cb(self.basic)

    def back(self):
        if not self.done:
            self.done = True
            self.on_back_cb()

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if self.done:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.mouse_pos(event.pos)
            for rect, callback in reversed(self._hit):
                if rect.collidepoint(pos):
                    callback()
                    return
            return
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        step = self.move_of(key)
        if key in BACK_KEYS:
            self.back()
        elif key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            self.row = (self.row + step) % self.rows
        elif key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            direction = -1 if key in (pygame.K_LEFT, pygame.K_a) else 1
            if self.on_button:
                self.row = len(FIELDS) + (self.row - len(FIELDS) + direction) % len(BUTTONS)
            else:
                self.cycle(direction)
        elif key == pygame.K_r:
            self.basic = random_basic(random)
        elif key in CONFIRM_KEYS:
            if not self.on_button:
                self.row += 1                           # next row; the last field leads on to the buttons
            elif BUTTONS[self.row - len(FIELDS)] == "BACK":
                self.back()
            else:
                self.confirm()

    def mouse_pos(self, pos):
        return screen_to_canvas(pos, self.game.screen.get_size())

    def hit(self, rect, callback):
        self._hit.append((pygame.Rect(rect), callback))

    # ------------------------------------------------------------ drawing
    def avatar(self, facing, frame=0, basic=None):
        sheet = styled_sheet(self.look, {}, basic or self.basic)
        idle = sheet[facing]["idle"]
        return idle[frame % len(idle)]

    def mini_head(self, field, opt):
        """A small crop of the head wearing option `opt`, shown on the eyes / hair rows."""
        key = (field, opt.id, self.basic.skin, self.basic.hair_color, self.basic.eyes, self.basic.hair, self.look)
        image = self.mini_cache.get(key)
        if image is None:
            frame = self.avatar("down", basic=self.basic.with_choice(field, opt.id))
            image = scaled(frame.subsurface(pygame.Rect(0, 0, frame.get_width(), 11)).copy(), MINI_SCALE)
            self.mini_cache[key] = image
        return image

    def draw(self, surf):
        self._hit = []
        super().draw(surf)
        surf.fill((16, 9, 36), PANEL)
        surf.blit(neon_panel(PANEL.w, PANEL.h, Col.MAGENTA, Col.CYAN, 255), PANEL.topleft)
        draw_centered(surf, "CREATE YOUR CHARACTER", 18, shade(Col.CYAN, 0.5), 2, scale_color(Col.MAGENTA, 0.8))
        draw_centered(surf, self.name.upper(), 38, Col.YELLOW)
        self._draw_stage(surf)
        self._draw_rows(surf)
        self._draw_buttons(surf)
        draw_centered(surf, "ALL LOOKS ARE FREE - YOU CAN CHANGE THEM LATER IN THE WARDROBE", 262,
                      scale_color(Col.TEXT_MUTED, 0.9))
        draw_centered(surf, "UP/DOWN ROW   LEFT/RIGHT CHANGE   R RANDOM   E NEXT   ESC BACK", 276,
                      scale_color(Col.TEXT_MUTED, 0.8))

    def _draw_stage(self, surf):
        surf.fill((14, 9, 34), STAGE)
        pygame.draw.rect(surf, scale_color(Col.MAGENTA, 0.5), STAGE, 1)
        frame = int(self.time * 2.5) % 8
        for facing, cx, label in (("down", STAGE.x + 40, "FRONT"), ("left", STAGE.x + 110, "SIDE")):
            image = scaled(self.avatar(facing, frame), PREVIEW_SCALE)
            floor = pygame.Rect(0, 0, 56, 7)
            floor.midtop = (cx, STAGE.y + 112)
            surf.blit(pedestal(floor.size, Col.MAGENTA), floor.topleft)
            surf.blit(image, image.get_rect(midbottom=(cx, floor.y + 3)))
            draw_text(surf, label, (cx, STAGE.bottom - 14), Col.TEXT_MUTED, anchor="midtop")

    def _draw_rows(self, surf):
        y = 50
        for i, field in enumerate(FIELDS):
            selected = i == self.row and not self.on_button
            options = OPTIONS[field]
            colour_row = swatch_color(field, options[0]) is not None
            height = 26 if colour_row else 36
            rect = pygame.Rect(LIST_X - 6, y - 2, LIST_W + 8, height)
            if selected:
                surf.fill(scale_color(Col.CYAN, 0.2), rect)
                pygame.draw.rect(surf, Col.CYAN, rect, 1)
            current = option(field, self.basic.get(field))
            draw_text(surf, FIELD_NAMES[field], (LIST_X, y + 1), Col.YELLOW if selected else Col.TEXT)
            draw_text(surf, current.name, (LIST_X + LIST_W - 4, y + 1), Col.TEXT, anchor="topright")
            self.hit(pygame.Rect(LIST_X, y - 2, 40, 12), lambda i=i: setattr(self, "row", i))
            x, row_y = LIST_X, y + 12
            for opt in options:
                chosen = opt.id == self.basic.get(field)
                if colour_row:
                    box = pygame.Rect(x, row_y, 14, 11)
                    surf.fill(swatch_color(field, opt), box)
                    pygame.draw.rect(surf, Col.TEXT if chosen else (24, 16, 48), box, 1)
                    if chosen:
                        pygame.draw.rect(surf, Col.YELLOW, box.inflate(4, 4), 1)
                    x += 20
                else:
                    head = self.mini_head(field, opt)
                    box = pygame.Rect(x, row_y - 1, 31, 25)
                    surf.fill((24, 16, 48), box)
                    surf.blit(head, head.get_rect(midtop=(box.centerx, box.y + 1)))
                    pygame.draw.rect(surf, Col.YELLOW if chosen else (60, 46, 100), box, 1)
                    x += 34
                self.hit(box, lambda f=field, o=opt: (setattr(self, "row", FIELDS.index(f)), self.choose(f, o.id)))
            y += height + 4
        self._draw_arrows(surf)

    def _draw_arrows(self, surf):
        """Little < > markers on the highlighted field (clickable)."""
        if self.on_button:
            return
        blink = int(self.time * 3) % 2
        y = 51 + sum((26 if swatch_color(f, OPTIONS[f][0]) is not None else 36) + 4 for f in FIELDS[:self.row])
        draw_text(surf, "<", (LIST_X - 12 - blink, y + 1), Col.YELLOW)
        self.hit(pygame.Rect(LIST_X - 16, y - 2, 12, 12), lambda: self.cycle(-1))
        draw_text(surf, ">", (LIST_X + LIST_W + 6 + blink, y + 1), Col.YELLOW)
        self.hit(pygame.Rect(LIST_X + LIST_W + 2, y - 2, 12, 12), lambda: self.cycle(1))

    def _draw_buttons(self, surf):
        for i, label in enumerate(BUTTONS):
            rect = pygame.Rect(LIST_X + i * 90, 236, 82, 16)
            selected = self.row == len(FIELDS) + i
            accent = Col.GREEN if label == "CONFIRM" else Col.MAGENTA
            surf.fill(scale_color(accent, 0.35 if selected else 0.15), rect)
            pygame.draw.rect(surf, accent if selected else scale_color(accent, 0.55), rect, 1)
            draw_text(surf, label, rect.center, Col.TEXT if selected else Col.TEXT_MUTED, anchor="center")
            self.hit(rect, self.confirm if label == "CONFIRM" else self.back)
