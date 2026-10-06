"""InventoryUI: the keyboard-driven inventory screen.

It only reads: items come from the player's Inventory, their names, text and
icons from the ItemDefinitions. Nothing here owns item state.

Controls: arrows / WASD move, TAB (SHIFT+TAB) changes the category tab,
ENTER / E inspects the selected item, ESC leaves the inspect view, then closes.
"""
import math

import pygame

from font import LINE_H, get_font
from gfx import scale_color, shade
from item_icons import item_icon
from item_registry import (ARCADE, COLLECTIBLE, COMMON, CONSUMABLE, COSMETIC, EPIC,
                           RARE, UNCOMMON)
from settings import (BACK_KEYS, CONFIRM_KEYS, MOVE_KEYS, VIEW_H, VIEW_W, Col)
from ui import dim_screen, draw_text, neon_panel, wrap_text

TABS = (("ALL", None), ("COSMETICS", COSMETIC), ("ARCADE", ARCADE),
        ("CONSUMABLES", CONSUMABLE), ("COLLECTIBLES", COLLECTIBLE))
RARITY_COLORS = {COMMON: Col.TEXT_MUTED, UNCOMMON: Col.GREEN, RARE: Col.CYAN, EPIC: Col.MAGENTA}
COLS, ROWS = 4, 3
SLOT, GAP = 30, 4
W, H = 330, 186
GRID_X, GRID_Y = 12, 50
DETAIL = pygame.Rect(GRID_X + COLS * (SLOT + GAP) + 8, GRID_Y - 2, W - 12 - (GRID_X + COLS * (SLOT + GAP) + 8), 3 * (SLOT + GAP) + 2)


class InventoryUI:
    def __init__(self, inventory, owner=None, accent=Col.CYAN):
        """owner: whose bag this is ('P1 YONGYI'), shown in the header; None
        in a one-player session."""
        self.inventory = inventory
        self.owner, self.accent = owner, accent
        self.tab = 0
        self.selected = 0           # slot index within the current tab
        self.inspecting = False
        self.closed = False
        self.anim = 0.0
        self.time = 0.0
        self._key = None
        self.image = None

    # ------------------------------------------------------------ queries
    @property
    def tab_name(self):
        return TABS[self.tab][0]

    @property
    def entries(self):
        """[(ItemDefinition, quantity)] shown in the current tab."""
        return self.inventory.get_all_items(TABS[self.tab][1])

    @property
    def selected_entry(self):
        entries = self.entries
        return entries[self.selected] if self.selected < len(entries) else None

    @property
    def slot_count(self):
        rows = max(ROWS, math.ceil(len(self.entries) / COLS))
        return rows * COLS

    @property
    def scroll_row(self):
        """First visible grid row, kept so the selection is on screen."""
        return max(0, self.selected // COLS - ROWS + 1)

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.closed:
            return
        key = event.key
        if key in BACK_KEYS:
            if self.inspecting:
                self.inspecting = False
            else:
                self.closed = True
        elif key == pygame.K_TAB:
            step = -1 if event.mod & pygame.KMOD_SHIFT else 1
            self.tab = (self.tab + step) % len(TABS)
            self.selected, self.inspecting = 0, False
        elif key in CONFIRM_KEYS:
            self.inspecting = (not self.inspecting) and self.selected_entry is not None
        elif key in MOVE_KEYS and not self.inspecting:
            self._move(*MOVE_KEYS[key])

    def _move(self, dx, dy):
        col = (self.selected % COLS + dx) % COLS
        row = self.selected // COLS + dy
        rows = self.slot_count // COLS
        self.selected = (row % rows) * COLS + col

    def update(self, dt):
        self.anim = min(1.0, self.anim + dt * 7)
        self.time += dt

    # ------------------------------------------------------------ build
    def _snapshot(self):
        return (self.tab, self.selected, self.inspecting,
                tuple((d.id, q) for d, q in self.inventory.get_all_items()))

    def _rebuild(self):
        font = get_font()
        img = neon_panel(W, H, Col.CYAN, Col.PURPLE).copy()
        title = font.render_glow("INVENTORY", shade(Col.CYAN, 0.55), scale_color(Col.MAGENTA, 0.8), 2)
        img.blit(title, title.get_rect(midtop=(W // 2, 7)))
        img.fill(scale_color(Col.CYAN, 0.6), (12, 25, W - 24, 1))
        if self.owner:
            draw_text(img, self.owner, (W - 12, 10), self.accent, anchor="topright",
                      glow=scale_color(self.accent, 0.4))
        self._draw_tabs(img, font)
        self._draw_grid(img, font)
        self._draw_detail(img, font)
        draw_text(img, "ARROWS MOVE  TAB CATEGORY  E INSPECT  ESC CLOSE", (W // 2, H - 12),
                  scale_color(Col.TEXT_MUTED, 0.75), anchor="midtop")
        self.image = img

    def _draw_tabs(self, img, font):
        x = 12
        for i, (name, _) in enumerate(TABS):
            w = font.size(name)[0] + 8
            active = i == self.tab
            if active:
                img.fill(scale_color(Col.CYAN, 0.3), (x, 29, w, 11))
                img.fill(Col.CYAN, (x, 39, w, 1))
            draw_text(img, name, (x + 4, 31), Col.TEXT if active else Col.TEXT_MUTED)
            x += w + 2

    def slot_rect(self, index):
        row, col = divmod(index, COLS)
        return pygame.Rect(GRID_X + col * (SLOT + GAP), GRID_Y + (row - self.scroll_row) * (SLOT + GAP),
                           SLOT, SLOT)

    def _draw_grid(self, img, font):
        entries = self.entries
        first = self.scroll_row * COLS
        for index in range(first, first + ROWS * COLS):
            rect = self.slot_rect(index)
            img.fill((10, 6, 26), rect)
            entry = entries[index] if index < len(entries) else None
            border = RARITY_COLORS[entry[0].rarity] if entry else (44, 36, 80)
            pygame.draw.rect(img, scale_color(border, 0.8 if entry else 1.0), rect, 1)
            if entry:
                definition, qty = entry
                icon = item_icon(definition)
                img.blit(icon, icon.get_rect(center=rect.center))
                if qty > 1:
                    label = font.render_glow(f"X{qty}", Col.YELLOW, (60, 46, 10))
                    img.blit(label, label.get_rect(bottomright=(rect.right - 1, rect.bottom)))
        rows = self.slot_count // COLS
        if rows > ROWS:                                       # scroll hint
            more = "MORE" if self.scroll_row + ROWS < rows else "TOP"
            draw_text(img, more, (GRID_X + COLS * (SLOT + GAP) - GAP, GRID_Y + ROWS * (SLOT + GAP)),
                      Col.TEXT_MUTED, anchor="topright")

    def _draw_detail(self, img, font):
        box = DETAIL
        img.fill((10, 6, 26), box)
        pygame.draw.rect(img, scale_color(Col.PURPLE, 0.8), box, 1)
        entry = self.selected_entry
        if entry is None:
            msg = "EMPTY SLOT" if self.entries else "NOTHING HERE YET"
            draw_text(img, msg, box.center, Col.TEXT_MUTED, anchor="center")
            return
        definition, qty = entry
        pad, y = box.x + 6, box.y + 6
        if self.inspecting:
            icon = item_icon(definition, 3)
            img.blit(icon, icon.get_rect(midtop=(box.centerx, y)))
            y += icon.get_height() + 4
        else:
            icon = item_icon(definition)
            img.blit(icon, (pad, y - 2))
        name_x = pad if self.inspecting else pad + 20
        for line in wrap_text(definition.name, box.right - name_x - 4):
            draw_text(img, line, (name_x, y), Col.TEXT, glow=scale_color(Col.CYAN, 0.4))
            y += LINE_H
        draw_text(img, definition.category, (name_x, y), RARITY_COLORS[definition.rarity])
        y += LINE_H + 6
        for line in wrap_text(definition.description, box.w - 12):
            draw_text(img, line, (pad, y), Col.TEXT_MUTED)
            y += LINE_H
        bottom = box.bottom - 6 - LINE_H
        draw_text(img, f"OWNED: {qty}", (pad, bottom), Col.YELLOW)
        if self.inspecting:
            kind = f"STACKS TO {definition.limit}" if definition.stackable else "ONE ONLY"
            draw_text(img, f"{definition.rarity}  {kind}", (pad, bottom - LINE_H), scale_color(Col.TEXT_MUTED, 0.85))

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        key = self._snapshot()
        if key != self._key:
            self._key = key
            self._rebuild()
        dim_screen(surf, int(150 * self.anim))
        ease = 1 - (1 - self.anim) ** 3
        rect = self.image.get_rect(center=(VIEW_W // 2, VIEW_H // 2 + int((1 - ease) * 14)))
        self.image.set_alpha(int(255 * min(1.0, self.anim * 1.5)))
        surf.blit(self.image, rect)
        if not self.inspecting:                               # the cursor pulses over the cached panel
            slot = self.slot_rect(self.selected).move(rect.topleft)
            pulse = 0.6 + 0.4 * math.sin(self.time * 7)
            pygame.draw.rect(surf, scale_color(Col.YELLOW, pulse), slot.inflate(2, 2), 1)
