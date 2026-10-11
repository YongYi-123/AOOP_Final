"""COLLECTION: every collectible the arcade has, found ones in colour and the
missing ones as dark silhouettes, with a progress bar. Inspect a found item,
and pin up to three of them on HOME's display case (E).

Purely for show: nothing here is a bonus of any kind.
"""
import pygame

from collection import DISPLAY_SLOTS, CollectionService
from font import LINE_H
from gfx import scale_color
from item_icons import item_icon
from menu_kit import FRAME, GOLD, MenuScene, fit_text
from preview_art import pedestal, scaled
from prize_shop import entry_for
from settings import Col
from ui import draw_text, wrap_text

COLS = 3
CELL_W, CELL_H, GAP = 56, 58, 6
GRID = pygame.Rect(14, 66, COLS * CELL_W + (COLS - 1) * GAP, 2 * CELL_H + GAP)
DETAIL = pygame.Rect(GRID.right + 14, 60, FRAME.right - GRID.right - 14 - 8, 9 * 18 + 2)


STAR = ("0001000", "0001000", "1111111", "0111110", "0011100", "0110110", "0100010")


def silhouette(icon):
    """The icon as a flat dark shape (nothing but its outline's worth of detail)."""
    mask = pygame.mask.from_surface(icon)
    return mask.to_surface(setcolor=(46, 36, 84, 255), unsetcolor=(0, 0, 0, 0))


class CollectionScene(MenuScene):
    title = "COLLECTION"
    accent = GOLD
    glow = Col.CYAN

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.service = CollectionService(owner.profile)
        self.index = 0
        self.hints = ("ARROWS SELECT", "E PIN / UNPIN ON THE HOME CASE", "ESC BACK")

    # ------------------------------------------------------------ data
    @property
    def entries(self):
        return self.service.entries()

    @property
    def selected(self):
        entries = self.entries
        return entries[min(self.index, len(entries) - 1)] if entries else None

    # ------------------------------------------------------------ input
    def on_action(self, action):
        total = len(self.entries)
        if not total:
            if action == "back":
                self.close()
            return
        if action == "back":
            self.close()
        elif action == "left":
            self.index = (self.index - 1) % total
        elif action == "right":
            self.index = (self.index + 1) % total
        elif action in ("up", "down"):
            new = self.index + (-COLS if action == "up" else COLS)
            if new < 0:                         # off the top: the last row, same column
                new = min(total - 1, (total - 1) // COLS * COLS + self.index % COLS)
            elif new >= total:                  # off the bottom: the first row
                new = self.index % COLS
            self.index = new
        elif action == "interact":
            self.activate()

    def activate(self):
        definition, owned = self.selected
        if not owned:
            self.say("NOT FOUND YET - FIND OR BUY IT TO UNLOCK", Col.MAGENTA, 3.0)
            self.play("cancel")
        elif self.service.is_displayed(definition.id):
            self.service.toggle_display(definition.id)
            self.say(f"{definition.name} TAKEN OFF THE CASE", Col.TEXT_MUTED)
        elif self.service.toggle_display(definition.id):
            self.say(f"{definition.name} IS ON THE CASE", Col.GREEN)
            self.play("confirm")
        else:
            self.say(f"THE CASE HOLDS {DISPLAY_SLOTS}. UNPIN ONE FIRST", Col.YELLOW, 3.0)
            self.play("cancel")

    def _click(self, i):
        if i == self.index:
            self.activate()
        else:
            self.index = i

    # ------------------------------------------------------------ draw
    def idle_message(self):
        owned, total = self.service.progress()
        return "COLLECTION COMPLETE!" if owned == total else f"{total - owned} STILL TO FIND"

    def draw_body(self, surf):
        self.draw_frame(surf)
        owned, total = self.service.progress()
        self._draw_progress(surf, owned, total)
        self._draw_grid(surf)
        self._draw_detail(surf)
        self.draw_footer(surf)

    def _draw_progress(self, surf, owned, total):
        bar = pygame.Rect(14, 46, GRID.w, 8)
        surf.fill((18, 12, 40), bar)
        if total:
            surf.fill(GOLD, (bar.x + 1, bar.y + 1, (bar.w - 2) * owned // total, bar.h - 2))
        pygame.draw.rect(surf, scale_color(GOLD, 0.6), bar, 1)
        draw_text(surf, f"{owned} / {total} COLLECTED", (bar.x, bar.bottom + 3), Col.TEXT)

    def _draw_grid(self, surf):
        shown = set(self.service.displayed())
        for i, (definition, owned) in enumerate(self.entries):
            row, col = divmod(i, COLS)
            rect = pygame.Rect(GRID.x + col * (CELL_W + GAP), GRID.y + row * (CELL_H + GAP) + 8, CELL_W, CELL_H)
            self.draw_row_bg(surf, rect, i == self.index, owned=owned)
            self.hit(rect, lambda i=i: self._click(i))
            icon = item_icon(definition)
            image = scaled(icon if owned else silhouette(icon), 2)
            surf.blit(image, image.get_rect(midtop=(rect.centerx, rect.y + 3)))
            label = definition.name if owned else "???"
            for n, line in enumerate(wrap_text(label, CELL_W - 4)[:2]):
                draw_text(surf, line, (rect.centerx, rect.bottom - 22 + n * LINE_H), Col.TEXT if owned
                          else Col.TEXT_MUTED, anchor="midtop")
            if definition.id in shown:                       # a little gold star: on the home case
                for dy, row in enumerate(STAR):
                    for dx, ch in enumerate(row):
                        if ch == "1":
                            surf.fill(GOLD, (rect.right - 10 + dx, rect.y + 3 + dy, 1, 1))

    def _draw_detail(self, surf):
        box = DETAIL
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(GOLD, 0.5), box, 1)
        definition, owned = self.selected
        icon = item_icon(definition)
        stage = pygame.Rect(box.x + 4, box.y + 4, box.w - 8, 54)
        surf.fill((8, 5, 22), stage)
        surf.blit(pedestal((stage.w - 40, 5), GOLD), (stage.x + 20, stage.bottom - 8))
        image = scaled(icon if owned else silhouette(icon), 3)
        surf.blit(image, image.get_rect(midbottom=(stage.centerx, stage.bottom - 8)))
        y = stage.bottom + 6
        name = definition.name if owned else "UNKNOWN COLLECTIBLE"
        for line in wrap_text(name, box.w - 12)[:2]:
            draw_text(surf, line, (box.x + 6, y), Col.TEXT, glow=scale_color(GOLD, 0.4))
            y += LINE_H
        draw_text(surf, definition.rarity if owned else "???", (box.x + 6, y), Col.CYAN)
        y += LINE_H + 3
        text = definition.description if owned else "NOT FOUND YET."
        for line in wrap_text(text, box.w - 12)[:3]:
            draw_text(surf, line, (box.x + 6, y), Col.TEXT_MUTED)
            y += LINE_H
        if owned:
            on = self.service.is_displayed(definition.id)
            draw_text(surf, "ON THE CASE - E TO UNPIN" if on else "E: PIN ON THE CASE",
                      (box.x + 6, box.bottom - 6 - LINE_H), Col.GREEN if on else Col.CYAN)
        else:
            entry = entry_for(definition.id)
            hint = f"PRIZE COUNTER: {entry.cost} TICKETS" if entry else "KEEP PLAYING TO FIND IT"
            draw_text(surf, fit_text(hint, box.w - 12), (box.x + 6, box.bottom - 6 - LINE_H), GOLD)
