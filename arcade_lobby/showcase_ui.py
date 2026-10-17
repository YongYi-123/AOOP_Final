"""SHOWCASE screen: choose the car, collectible and trophy your Prize Plaza stand displays.

Opened from the stand for ONE local player; only their keys (and ESC) drive it and only their
profile changes. LEFT/RIGHT picks the bay (CAR / COLLECTIBLE / TROPHY), UP/DOWN an owned item
(or EMPTY), E puts it on display. The choice is saved at once (PlayerProfile.showcase).
"""
import math

import pygame

from font import LINE_H
from gfx import scale_color
from menu_kit import FRAME, GOLD, ROW_H, MenuScene, fit_text
from plaza_stations import option_icon
from preview_art import pedestal
from settings import Col
from showcase import SHOWCASE_SLOTS, SLOT_NAMES, ShowcaseService
from ui import draw_text, wrap_text

LIST = pygame.Rect(14, 60, 206, 9 * ROW_H + 2)
SIDE = pygame.Rect(226, 60, FRAME.right - 226 - 8, 9 * ROW_H + 2)
VISIBLE = 9
EMPTY = None        # the first row of every bay: take the item off display


class ShowcaseScene(MenuScene):
    title = "SHOWCASE"
    accent = GOLD
    glow = (255, 110, 190)

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.service = ShowcaseService(owner.profile)
        self.tab = 0
        self.index = 0
        self.first = 0
        self.hints = ("LEFT/RIGHT BAY", "UP/DOWN ITEM", f"{owner.controls.label('interact') or 'E'} DISPLAY", "ESC LEAVE")
        self._select_current()

    # ------------------------------------------------------------ data
    @property
    def slot(self):
        return SHOWCASE_SLOTS[self.tab]

    @property
    def rows(self):
        """[None (EMPTY)] + every owned item that fits the bay."""
        return [EMPTY] + self.service.options(self.slot)

    @property
    def option(self):
        rows = self.rows
        return rows[min(self.index, len(rows) - 1)]

    def _select_current(self):
        """Start the cursor on whatever the bay already displays."""
        shown = self.service.displayed(self.slot)
        rows = self.rows
        self.index = rows.index(shown) if shown in rows else 0
        self.first = max(0, min(self.index, len(rows) - VISIBLE))

    # ------------------------------------------------------------ input
    def on_action(self, action):
        if action == "back":
            self.play("cancel")
            self.close()
        elif action in ("left", "right", "tab"):
            self.set_tab((self.tab + (-1 if action == "left" else 1)) % len(SHOWCASE_SLOTS))
        elif action in ("up", "down"):
            self.select((self.index + (-1 if action == "up" else 1)) % len(self.rows))
        elif action == "interact":
            self.display()

    def set_tab(self, tab):
        if tab != self.tab:
            self.tab = tab
            self._select_current()

    def select(self, index):
        self.index = index
        if index < self.first:
            self.first = index
        elif index >= self.first + VISIBLE:
            self.first = index - VISIBLE + 1

    def display(self):
        """E: put the highlighted item on the stand (or take the bay's item off)."""
        option = self.option
        if option is EMPTY:
            changed = self.service.clear(self.slot)
            self.say("BAY CLEARED" if changed else "ALREADY EMPTY", Col.TEXT_MUTED)
            self.play("cancel" if not changed else "confirm")
        elif self.service.displayed(self.slot) == option:
            self.say("ALREADY ON DISPLAY", Col.YELLOW)
            self.play("cancel")
        elif self.service.choose(self.slot, option.value):
            self.say(f"{option.name} ON DISPLAY!", Col.GREEN, 3.0)
            self.play("equip")
        else:
            self.say("YOU DO NOT OWN THAT", Col.MAGENTA)
            self.play("cancel")

    def _click_row(self, i):
        if i == self.index:
            self.display()
        else:
            self.select(i)

    # ------------------------------------------------------------ draw
    def idle_message(self):
        shown = self.service.displayed(self.slot)
        return f"{SLOT_NAMES[self.slot]} ON DISPLAY: {shown.name if shown else 'NOTHING'}"

    def draw_body(self, surf):
        self.draw_frame(surf)
        self.draw_tabs(surf, [SLOT_NAMES[s] for s in SHOWCASE_SLOTS], self.tab, on_click=self.set_tab)
        self._draw_list(surf)
        self._draw_side(surf)
        self.draw_footer(surf)

    def _draw_list(self, surf):
        rows = self.rows
        shown = self.service.displayed(self.slot)
        for slot in range(VISIBLE):
            i = self.first + slot
            if i >= len(rows):
                break
            option = rows[i]
            rect = pygame.Rect(LIST.x, LIST.y + slot * ROW_H, LIST.w - 6, ROW_H - 2)
            on_display = option is not EMPTY and option == shown
            self.draw_row_bg(surf, rect, i == self.index, owned=on_display)
            self.hit(rect, lambda i=i: self._click_row(i))
            if option is EMPTY:
                draw_text(surf, "- EMPTY -", (rect.x + 8, rect.y + 5),
                          Col.TEXT if i == self.index else Col.TEXT_MUTED)
                if shown is None:
                    draw_text(surf, "ON DISPLAY", (rect.right - 5, rect.y + 5), Col.GREEN, anchor="topright")
                continue
            icon = option_icon(option, 1, self.profile)
            surf.blit(icon, icon.get_rect(midleft=(rect.x + 4, rect.centery)))
            draw_text(surf, fit_text(option.name, 98), (rect.x + 24, rect.y + 5),
                      Col.TEXT if i == self.index else Col.TEXT_MUTED)
            if on_display:
                draw_text(surf, "ON DISPLAY", (rect.right - 5, rect.y + 5), Col.GREEN, anchor="topright")
            elif option.count > 1:
                draw_text(surf, f"X{option.count}", (rect.right - 5, rect.y + 5), Col.CYAN, anchor="topright")
        if len(rows) == 1:
            draw_text(surf, f"YOU OWN NO {SLOT_NAMES[self.slot]} YET", (LIST.x + 8, LIST.y + ROW_H + 8), Col.TEXT_MUTED)
            hint = {"car": "CARS ARE SOLD AT THE RACING COUNTER", "collectible": "TRY THE CAPSULE MACHINES",
                    "trophy": "TRY THE RETRO CAPSULE"}[self.slot]
            draw_text(surf, hint, (LIST.x + 8, LIST.y + ROW_H + 8 + LINE_H), Col.TEXT_MUTED)
        self.draw_scrollbar(surf, LIST, self.first, VISIBLE, len(rows))

    def _draw_side(self, surf):
        box = SIDE
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(GOLD, 0.5), box, 1)
        stage = pygame.Rect(box.x + 4, box.y + 4, box.w - 8, 80)
        surf.fill((8, 5, 22), stage)
        glow = 0.5 + 0.5 * math.sin(self.time * 3)
        pygame.draw.rect(surf, scale_color(self.glow, 0.35 + 0.25 * glow), stage, 1)
        surf.blit(pedestal((stage.w - 40, 5), GOLD), (stage.x + 20, stage.bottom - 10))
        option = self.option
        if option is not EMPTY:
            icon = option_icon(option, 2, self.profile)
            surf.blit(icon, icon.get_rect(midbottom=(stage.centerx, stage.bottom - 10 + int(math.sin(self.time * 3)))))
        else:
            draw_text(surf, "?", stage.center, scale_color(Col.TEXT_MUTED, 0.7), 3, anchor="center")
        y = stage.bottom + 6
        if option is EMPTY:
            for line in wrap_text("LEAVE THIS BAY EMPTY", box.w - 12)[:2]:
                draw_text(surf, line, (box.x + 6, y), Col.TEXT)
                y += LINE_H
            return
        for line in wrap_text(option.name, box.w - 12)[:2]:
            draw_text(surf, line, (box.x + 6, y), Col.TEXT, glow=scale_color(GOLD, 0.4))
            y += LINE_H
        if option.count > 1:
            draw_text(surf, f"YOU OWN X{option.count}", (box.x + 6, y), Col.CYAN)
