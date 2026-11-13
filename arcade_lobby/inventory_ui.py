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
from controls import key_label
from novelty import is_usable
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
INSPECT = pygame.Rect(GRID_X, GRID_Y - 2, W - 12 - GRID_X, DETAIL.h)      # the inspect view covers the grid too


def _ellipsis(text, width):
    """`text` cut so that it plus "..." fits `width` pixels."""
    font = get_font()
    while text and font.size(text + "...")[0] > width:
        text = text[:-1].rstrip()
    return text + "..."


class InventoryUI:
    def __init__(self, inventory, owner=None, accent=Col.CYAN, use_keys=(), on_use=None):
        """owner: whose bag this is, shown in the header; None for no owner line. use_keys / on_use: the owner's "use item" keys and the callback
        `on_use(item_id)` that uses one (novelty items); without them the bag is read-only."""
        self.inventory = inventory
        self.owner, self.accent = owner, accent
        self.use_keys, self.on_use = tuple(use_keys), on_use
        self.tab = 0
        self.selected = 0           # slot index within the current tab
        self.first_row = 0          # the first grid row on screen (moves only when the cursor would leave the view)
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
    def can_use(self):
        """Is the selected item one that can be used from the bag?"""
        entry = self.selected_entry
        return entry is not None and is_usable(entry[0].id)

    @property
    def use_label(self):
        return key_label(self.use_keys[0]) if self.use_keys else ""

    @property
    def slot_count(self):
        rows = max(ROWS, math.ceil(len(self.entries) / COLS))
        return rows * COLS

    @property
    def scroll_row(self):
        """First visible grid row: it only moves when the selection would leave the view (so moving back up a row does
        not scroll), and never past the last row."""
        row = self.selected // COLS
        last = max(0, self.slot_count // COLS - ROWS)
        if row < self.first_row:
            self.first_row = row
        elif row >= self.first_row + ROWS:
            self.first_row = row - ROWS + 1
        self.first_row = max(0, min(self.first_row, last))
        return self.first_row

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
            self.selected, self.inspecting, self.first_row = 0, False, 0
        elif key in self.use_keys and self.on_use and self.can_use:
            self.on_use(self.selected_entry[0].id)         # the bag closes so the effect can be seen
            self.closed = True
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
        return (self.tab, self.selected, self.scroll_row, self.inspecting,
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
        footer = ("ARROWS MOVE  E INSPECT  " + f"{self.use_label} USE  ESC CLOSE"
                  if self.on_use and self.can_use else "ARROWS MOVE  TAB CATEGORY  E INSPECT  ESC CLOSE")
        draw_text(img, footer, (W // 2, H - 12),
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

    def detail_rect(self):
        """The detail box: beside the grid, or (while inspecting) over the whole grid so everything fits."""
        return INSPECT if self.inspecting else DETAIL

    def detail_lines(self, definition, qty):
        """[(text, colour, x, y)] the detail box shows for one item. Rows flow top to bottom and never overlap: text
        that does not fit is cut with "..." (the full text is in the inspect view, which has room for all of it)."""
        box = self.detail_rect()
        rows = []
        if self.inspecting:
            x, width = box.x + 64, box.right - 6 - (box.x + 64)
            y = box.y + 6
        else:
            x, width = box.x + 26, box.right - 6 - (box.x + 26)
            y = box.y + 6
        for line in wrap_text(definition.name, width)[:2]:
            rows.append((line, Col.TEXT, x, y))
            y += LINE_H
        rows.append((definition.category, RARITY_COLORS[definition.rarity], x, y))
        y += LINE_H
        kind = f"STACKS TO {definition.limit}" if definition.stackable else "ONE ONLY"
        if self.inspecting:
            rows.append((f"{definition.rarity}  {kind}", scale_color(Col.TEXT_MUTED, 0.85), x, y))
            y += LINE_H
            rows.append((f"OWNED: {qty}", Col.YELLOW, x, y))
            y += LINE_H + 3
        else:
            x, width = box.x + 6, box.w - 12                  # below the icon the text uses the full width
            y = max(y, box.y + 24) + 3
        footer = []
        if self.on_use and is_usable(definition.id):
            footer.append((f"{self.use_label}: USE", Col.GREEN))
        if not self.inspecting:
            footer.append((f"OWNED: {qty}", Col.YELLOW))
        bottom = box.bottom - 5 - LINE_H * len(footer)       # the last row the text may use
        body = [(line, Col.TEXT_MUTED) for line in wrap_text(definition.description, width)]
        if definition.use_hint:
            body += [(line, Col.CYAN) for line in wrap_text(definition.use_hint, width)]
        room = max(0, (bottom - y) // LINE_H)
        if len(body) > room and room:
            body = body[:room]
            last, colour = body[-1]
            body[-1] = (_ellipsis(last, width), colour)
        else:
            body = body[:room]
        for text, colour in body:
            rows.append((text, colour, x, y))
            y += LINE_H
        fy = box.bottom - 5 - LINE_H * len(footer)
        for text, colour in footer:
            rows.append((text, colour, box.x + 6, fy))
            fy += LINE_H
        return rows

    def _draw_detail(self, img, font):
        box = self.detail_rect()
        img.fill((10, 6, 26), box)
        pygame.draw.rect(img, scale_color(Col.PURPLE, 0.8), box, 1)
        entry = self.selected_entry
        if entry is None:
            msg = "EMPTY SLOT" if self.entries else "NOTHING HERE YET"
            draw_text(img, msg, box.center, Col.TEXT_MUTED, anchor="center")
            return
        definition, qty = entry
        if self.inspecting:
            icon = item_icon(definition, 3)
            img.blit(icon, icon.get_rect(center=(box.x + 32, box.y + 6 + 26)))
        else:
            icon = item_icon(definition)
            img.blit(icon, (box.x + 5, box.y + 4))
        for i, (text, colour, x, y) in enumerate(self.detail_lines(definition, qty)):
            glow = scale_color(Col.CYAN, 0.4) if colour == Col.TEXT and i < 2 else None
            draw_text(img, text, (x, y), colour, glow=glow)

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
