"""DECORATION MODE: arrange HOME with the decorations the player owns.

The room stays on screen. Step 1, pick a slot with the arrow keys (every slot
is outlined, the selected one pulses); step 2, E opens the list of owned
decorations that fit it; the highlighted one is shown as a see-through preview
right in the room, and E places it. "REMOVE" puts the slot's default back - a
removed decoration stays owned and can be placed again. Every change goes
through HomeDecorationManager.place()/remove(), which saves the layout.
"""
import math

import pygame

from decorations import FLAT_TYPES, NEON_SIGN
from font import get_font
from gfx import scale_color
from menu_kit import GOLD, MenuScene, fit_text
from preview_art import decoration_image, fit_scale, scaled
from settings import VIEW_H, VIEW_W, Col
from ui import draw_text, neon_panel

ROWS = 4
ROW = 13


def slot_label(slot):
    return slot.slot_id.replace("_", " ").upper()


def slot_rect(slot):
    """The screen area a slot can fill: where its decoration will appear."""
    if slot.slot_type in FLAT_TYPES or slot.slot_type == NEON_SIGN:
        return pygame.Rect(slot.position, slot.size)
    px, py = slot.position
    w, h = slot.size
    return pygame.Rect(px - w // 2, py - h, w, h)


def sprite_rect(slot, sprite):
    """Where `sprite` really lands in this slot (flat: top-left, props: bottom-centre)."""
    w, h = sprite.get_size()
    if slot.slot_type in FLAT_TYPES or slot.slot_type == NEON_SIGN:
        return pygame.Rect(slot.position, (w, h))
    px, py = slot.position
    return pygame.Rect(px - w // 2, py - h, w, h)


def next_slot(slots, current, direction):
    """The slot nearest to `current` in `direction` ((dx, dy) unit step), or
    `current` itself if nothing lies that way."""
    cx, cy = slot_rect(current).center
    best, best_score = current, None
    for slot in slots:
        if slot is current:
            continue
        x, y = slot_rect(slot).center
        dx, dy = x - cx, y - cy
        along = dx * direction[0] + dy * direction[1]
        if along <= 0:
            continue
        across = abs(dx * direction[1]) + abs(dy * direction[0])
        score = along + 2 * across
        if best_score is None or score < best_score:
            best, best_score = slot, score
    return best


class DecorationScene(MenuScene):
    title = "DECORATE"
    spectator_pos = "topright"

    def __init__(self, game, owner, room):
        super().__init__(game, owner)
        self.room = room
        self.manager = room.decorations
        self.slots = list(self.manager.slots.values())
        self.slot = self.slots[0]
        self.choosing = False
        self.index = 0
        self.first = 0
        self.rows = []
        self.slot_hints = ("ARROWS PICK A SLOT", "E CHOOSE", "ESC DONE")
        self.choose_hints = ("UP/DOWN ITEM", "E PLACE", "ESC BACK")

    # ------------------------------------------------------------ lifecycle
    def on_enter(self):
        self.room.edit_mode = True

    def on_exit(self):
        self.room.edit_mode = False

    # ------------------------------------------------------------ data
    def _build_rows(self):
        """[None] (= remove) + every owned decoration that fits the slot."""
        self.rows = [None] + [d.decoration_id for d in self.manager.choices_for(self.slot.slot_id)]
        current = self.manager.current_id(self.slot.slot_id)
        self.index = self.rows.index(current) if current in self.rows else 0
        self.first = max(0, min(self.index, len(self.rows) - ROWS))

    @property
    def candidate(self):
        """The decoration being previewed in the room."""
        item = self.rows[self.index] if self.choosing and self.rows else None
        if not self.choosing:
            return None
        return self.manager.catalog.get(item or self.slot.default_id)

    def row_label(self, decoration_id):
        if decoration_id is None:
            return "REMOVE (USE DEFAULT)"
        return self.manager.catalog.get(decoration_id).name.upper()

    # ------------------------------------------------------------ input
    def on_action(self, action):
        if self.choosing:
            self._choose_action(action)
            return
        steps = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        if action == "back":
            self.close()
        elif action in steps:
            self.slot = next_slot(self.slots, self.slot, steps[action])
        elif action == "tab":
            i = (self.slots.index(self.slot) + 1) % len(self.slots)
            self.slot = self.slots[i]
        elif action == "interact":
            self.start_choosing()

    def start_choosing(self):
        self._build_rows()
        self.choosing = True

    def _choose_action(self, action):
        if action == "back":
            self.choosing = False
        elif action in ("up", "down"):
            self.select((self.index + (-1 if action == "up" else 1)) % len(self.rows))
        elif action == "interact":
            self.place()

    def select(self, index):
        self.index = index
        if index < self.first:
            self.first = index
        elif index >= self.first + ROWS:
            self.first = index - ROWS + 1

    def place(self):
        item = self.rows[self.index]
        slot_id = self.slot.slot_id
        if item is None:
            if self.manager.current_id(slot_id) == self.slot.default_id:
                self.say("ALREADY THE DEFAULT", Col.TEXT_MUTED)
            else:
                self.manager.remove(slot_id)
                self.say("REMOVED - STILL OWNED, PLACE IT ANYTIME", Col.GREEN)
                self.play("confirm")
        elif self.manager.current_id(slot_id) == item:
            self.say("ALREADY PLACED HERE", Col.TEXT_MUTED)
        elif self.manager.place(slot_id, item):
            self.say(f"PLACED {self.row_label(item)}", Col.GREEN)
            self.play("confirm")
        else:
            self.say("CANNOT PLACE THAT HERE", Col.MAGENTA)
            self.play("cancel")

    def _click_slot(self, slot):
        if self.choosing:
            return
        if slot is self.slot:
            self.start_choosing()
        else:
            self.slot = slot

    def _click_row(self, i):
        if i == self.index:
            self.place()
        else:
            self.select(i)

    # ------------------------------------------------------------ update
    def update(self, dt):
        super().update(dt)
        self.room.renderer.update(dt)
        self.manager.update(dt)

    # ------------------------------------------------------------ draw
    def draw_body(self, surf):
        self.room.draw(surf)
        self._draw_slots(surf)
        self._draw_ghost(surf)
        if self.choosing:
            self._draw_chooser(surf)
        else:
            self._draw_slot_bar(surf)

    def _brackets(self, surf, rect, color, arm=4):
        for x, sx in ((rect.left, 1), (rect.right - 1, -1)):
            for y, sy in ((rect.top, 1), (rect.bottom - 1, -1)):
                surf.fill(color, (x if sx > 0 else x - arm + 1, y, arm, 1))
                surf.fill(color, (x, y if sy > 0 else y - arm + 1, 1, arm))

    def _draw_slots(self, surf):
        pulse = 0.55 + 0.45 * math.sin(self.time * 7)
        for slot in self.slots:
            rect = slot_rect(slot).inflate(2, 2)
            self.hit(rect, lambda slot=slot: self._click_slot(slot))
            if slot is self.slot:
                continue
            self._brackets(surf, rect, scale_color(Col.CYAN, 0.55))
        rect = slot_rect(self.slot).inflate(4, 4)
        pygame.draw.rect(surf, scale_color(GOLD, 0.25 + 0.2 * pulse), rect.inflate(2, 2), 1)
        self._brackets(surf, rect, scale_color(GOLD, 0.5 + 0.5 * pulse), 5)
        tag = slot_label(self.slot)
        w = get_font().size(tag)[0] + 8
        label = pygame.Rect(0, 0, w, 11)
        label.midbottom = (rect.centerx, rect.top - 2)
        if label.top < 4:
            label.midtop = (rect.centerx, rect.bottom + 2)
        label.clamp_ip(pygame.Rect(2, 2, VIEW_W - 4, VIEW_H - 4))
        surf.fill((14, 10, 34), label)
        pygame.draw.rect(surf, GOLD, label, 1)
        draw_text(surf, tag, (label.x + 4, label.y + 2), GOLD)

    def _draw_ghost(self, surf):
        """The decoration being previewed, see-through, exactly where it would stand."""
        d = self.candidate
        if d is None or d.decoration_id == self.manager.current_id(self.slot.slot_id):
            return
        sprite = decoration_image(d).copy()
        sprite.set_alpha(int(150 + 60 * math.sin(self.time * 6)))
        rect = sprite_rect(self.slot, sprite)
        backing = pygame.Surface(rect.size, pygame.SRCALPHA)
        backing.fill((8, 4, 20, 150))
        surf.blit(backing, rect)
        surf.blit(sprite, rect)

    def _panel_rect(self, height):
        # keep the panel off the slot being edited: top if the slot is low, bottom otherwise
        low = slot_rect(self.slot).centery > VIEW_H // 2
        return pygame.Rect(6, 6 if low else VIEW_H - height - 6, VIEW_W - 12, height)

    def _draw_slot_bar(self, surf):
        panel = self._panel_rect(36)
        surf.blit(neon_panel(panel.w, panel.h, Col.CYAN, GOLD), panel.topleft)
        current = self.manager.decoration_for(self.slot.slot_id)
        draw_text(surf, "DECORATE", (panel.x + 8, panel.y + 6), GOLD, 2, glow=(120, 70, 10))
        draw_text(surf, fit_text(f"{slot_label(self.slot)}: {current.name.upper()}", 200), (panel.right - 8, panel.y + 7),
                  Col.TEXT, anchor="topright")
        draw_text(surf, "  ".join(self.slot_hints), (panel.centerx, panel.bottom - 13), Col.TEXT_MUTED,
                  anchor="midtop")
        if self.message_time > 0:
            draw_text(surf, fit_text(self.message, 200), (panel.right - 8, panel.y + 18), self.message_color,
                      anchor="topright")

    def _draw_chooser(self, surf):
        panel = self._panel_rect(ROWS * ROW + 52)
        surf.blit(neon_panel(panel.w, panel.h, GOLD, Col.CYAN), panel.topleft)
        draw_text(surf, fit_text(slot_label(self.slot), 120), (panel.x + 8, panel.y + 6), GOLD)
        draw_text(surf, f"{len(self.rows) - 1} OWNED", (panel.x + 190, panel.y + 6), Col.TEXT_MUTED, anchor="topright")
        current = self.manager.current_id(self.slot.slot_id)
        list_rect = pygame.Rect(panel.x + 8, panel.y + 18, 190, ROWS * ROW)
        for n in range(ROWS):
            i = self.first + n
            if i >= len(self.rows):
                break
            item = self.rows[i]
            rect = pygame.Rect(list_rect.x, list_rect.y + n * ROW, list_rect.w - 4, ROW - 1)
            self.draw_row_bg(surf, rect, i == self.index, owned=item == current)
            self.hit(rect, lambda i=i: self._click_row(i))
            color = Col.TEXT if i == self.index else Col.TEXT_MUTED
            draw_text(surf, fit_text(self.row_label(item), 142), (rect.x + 4, rect.y + 3), color)
            if item is not None and item == current:
                draw_text(surf, "PLACED", (rect.right - 3, rect.y + 3), Col.GREEN, anchor="topright")
        self.draw_scrollbar(surf, list_rect, self.first, ROWS, len(self.rows))
        d = self.candidate
        thumb = pygame.Rect(panel.x + 206, panel.y + 18, panel.w - 214, ROWS * ROW)
        surf.fill((8, 5, 22), thumb)
        pygame.draw.rect(surf, scale_color(GOLD, 0.4), thumb, 1)
        sprite = decoration_image(d)
        image = scaled(sprite, fit_scale(sprite.get_size(), (thumb.w - 6, thumb.h - 6), 3))
        surf.blit(image, image.get_rect(center=thumb.center))
        draw_text(surf, fit_text(d.name.upper(), thumb.w), (thumb.x, thumb.y - 11), Col.TEXT)
        if self.message_time > 0:
            draw_text(surf, fit_text(self.message, 250), (panel.x + 8, panel.bottom - 12), self.message_color)
        else:
            draw_text(surf, "  ".join(self.choose_hints), (panel.x + 8, panel.bottom - 12), Col.TEXT_MUTED)
        if len(self.rows) == 1:
            draw_text(surf, "NOTHING ELSE OWNED - BUY MORE AT THE PRIZE COUNTER",
                      (panel.x + 8, panel.bottom - 24), Col.YELLOW)
