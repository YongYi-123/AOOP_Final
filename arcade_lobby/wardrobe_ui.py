"""WARDROBE: change what the avatar wears (colours, hat, face, pin).

Tabs are the cosmetic slots. The highlighted item is tried on the avatar
straight away (a preview, even for items the player does not own yet); E wears
it - only if it is owned and made for that slot, which CosmeticService checks -
and E on the item that is already worn takes it off. The first row of every
tab is the plain default. Everything is that player's own profile: P1 and P2
change their own avatar.
"""
import pygame

from cosmetics import SLOT_NAMES, SLOTS, CosmeticService, cosmetics_for
from font import LINE_H
from gfx import scale_color
from item_icons import item_icon
from item_registry import ITEM_REGISTRY
from menu_kit import FRAME, GOLD, ROSE, ROW_H, MenuScene, fit_text, item_icon_for_ticket
from preview_art import avatar_image, pedestal, scaled
from prize_shop import entry_for
from settings import Col
from ui import draw_text, wrap_text

LIST = pygame.Rect(14, 60, 168, 9 * ROW_H + 2)
STAGE = pygame.Rect(188, 60, FRAME.right - 188 - 8, 9 * ROW_H + 2)
FACING_CYCLE = ("down", "left", "up", "right")
NONE_ROW = None             # the "no cosmetic" row of every tab


class WardrobeScene(MenuScene):
    title = "WARDROBE"
    accent = Col.MAGENTA
    glow = Col.CYAN
    VISIBLE = 9

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.service = CosmeticService(owner.profile)
        self.tab = 0
        self.index = 0
        self.first = 0
        self.turn = 0.0                     # the preview turns by itself
        self.manual_facing = None
        self.hints = ("UP/DOWN ITEM", "LEFT/RIGHT PART", "E WEAR/REMOVE", "TAB TURN", "ESC BACK")

    # ------------------------------------------------------------ data
    @property
    def slot(self):
        return SLOTS[self.tab]

    @property
    def rows(self):
        """[None] + the cosmetics of this slot: row 0 is the default."""
        return [NONE_ROW] + [c.item_id for c in cosmetics_for(self.slot)]

    @property
    def highlighted(self):
        rows = self.rows
        return rows[min(self.index, len(rows) - 1)]

    def worn(self):
        return self.service.worn()

    def preview_appearance(self):
        """What the avatar shows: what is worn, with the highlighted row tried on."""
        appearance = dict(self.worn())
        item = self.highlighted
        if item is None:
            appearance.pop(self.slot, None)
        else:
            appearance[self.slot] = item
        return appearance

    # ------------------------------------------------------------ input
    def on_action(self, action):
        if action == "back":
            self.close()
        elif action in ("left", "right"):
            self.set_tab((self.tab + (-1 if action == "left" else 1)) % len(SLOTS))
        elif action in ("up", "down"):
            self.select((self.index + (-1 if action == "up" else 1)) % len(self.rows))
        elif action == "tab":
            current = self.manual_facing or FACING_CYCLE[int(self.turn / 1.4) % 4]
            self.manual_facing = FACING_CYCLE[(FACING_CYCLE.index(current) + 1) % 4]
        elif action == "interact":
            self.activate()

    def set_tab(self, tab):
        self.tab, self.index, self.first = tab, 0, 0
        worn = self.worn().get(self.slot)               # start on what is worn
        if worn in self.rows:
            self.select(self.rows.index(worn))

    def select(self, index):
        self.index = index
        if index < self.first:
            self.first = index
        elif index >= self.first + self.VISIBLE:
            self.first = index - self.VISIBLE + 1

    def activate(self):
        item = self.highlighted
        if item is None:
            if self.service.unequip(self.slot):
                self.say("TAKEN OFF", Col.TEXT_MUTED)
            else:
                self.say("ALREADY THE DEFAULT", Col.TEXT_MUTED)
            return
        name = ITEM_REGISTRY.get(item).name
        if self.worn().get(self.slot) == item:
            self.service.unequip(self.slot)
            self.say(f"REMOVED {name}", Col.TEXT_MUTED)
        elif self.service.equip(self.slot, item):
            self.say(f"NOW WEARING {name}", Col.GREEN)
            self.play("confirm")
        else:
            entry = entry_for(item)
            price = f" - {entry.cost} TICKETS" if entry else ""
            self.say(f"NOT OWNED{price}. BUY IT AT THE PRIZE COUNTER", Col.MAGENTA, 3.5)
            self.play("cancel")

    def update(self, dt):
        super().update(dt)
        self.turn += dt

    # ------------------------------------------------------------ draw
    def idle_message(self):
        return "PREVIEW: WHAT YOU SEE IS WHAT YOU WEAR"

    def draw_body(self, surf):
        self.draw_frame(surf, subtitle=self.owner.tag)
        self.draw_tabs(surf, [SLOT_NAMES[s] for s in SLOTS], self.tab, on_click=self.set_tab)
        self._draw_list(surf)
        self._draw_stage(surf)
        self.draw_footer(surf)

    def _row_label(self, item):
        if item is None:
            return "DEFAULT" if self.slot == "palette" else "NONE"
        return ITEM_REGISTRY.get(item).name

    def _draw_list(self, surf):
        rows, worn = self.rows, self.worn().get(self.slot)
        for slot_i in range(self.VISIBLE):
            i = self.first + slot_i
            if i >= len(rows):
                break
            item = rows[i]
            rect = pygame.Rect(LIST.x, LIST.y + slot_i * ROW_H, LIST.w - 6, ROW_H - 2)
            owned = item is None or self.service.owns(item)
            on = item == worn
            self.draw_row_bg(surf, rect, i == self.index, owned=on)
            self.hit(rect, lambda i=i: self._click(i))
            if item is not None:
                icon = item_icon(ITEM_REGISTRY.get(item))
                surf.blit(icon, icon.get_rect(midleft=(rect.x + 4, rect.centery)))
            color = Col.TEXT if i == self.index else Col.TEXT_MUTED
            if not owned:
                color = scale_color(Col.TEXT_MUTED, 0.6)
            draw_text(surf, fit_text(self._row_label(item), 82), (rect.x + 22, rect.y + 5), color)
            if item is None:
                if worn is None:
                    draw_text(surf, "ON", (rect.right - 5, rect.y + 5), Col.GREEN, anchor="topright")
            elif on:
                draw_text(surf, "WORN", (rect.right - 5, rect.y + 5), Col.GREEN, anchor="topright")
            elif not owned:
                entry = entry_for(item)
                draw_text(surf, "LOCKED", (rect.right - 5, rect.y + 5), ROSE, anchor="topright")
            else:
                draw_text(surf, "OWNED", (rect.right - 5, rect.y + 5), Col.CYAN, anchor="topright")
        self.draw_scrollbar(surf, LIST, self.first, self.VISIBLE, len(rows))

    def _click(self, i):
        if i == self.index:
            self.activate()
        else:
            self.select(i)

    def _draw_stage(self, surf):
        box = STAGE
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(Col.MAGENTA, 0.5), box, 1)
        facing = self.manual_facing or FACING_CYCLE[int(self.turn / 1.4) % 4]
        look = self.owner.avatar.look
        frame = int(self.turn * 2.5) % 8
        image = scaled(avatar_image(look, self.preview_appearance(), facing, frame), 4)
        floor = pygame.Rect(box.centerx - 30, box.y + 98, 60, 6)
        surf.blit(pedestal(floor.size, Col.MAGENTA), floor.topleft)
        surf.blit(image, image.get_rect(midbottom=(box.centerx, floor.y + 2)))
        item = self.highlighted
        name = self._row_label(item)
        draw_text(surf, fit_text(name, box.w - 12), (box.centerx, box.y + 6), Col.TEXT, anchor="midtop",
                  glow=scale_color(Col.MAGENTA, 0.5))
        y = box.y + 108
        if item is None:
            lines = ["THE STANDARD LOOK."]
        else:
            lines = wrap_text(ITEM_REGISTRY.get(item).description, box.w - 12)[:2]
            if not self.service.owns(item):
                entry = entry_for(item)
                if entry:
                    draw_text(surf, f"{entry.cost}", (box.right - 16, box.y + 18), GOLD, anchor="topright")
                    surf.blit(item_icon_for_ticket(GOLD), (box.right - 13, box.y + 19))
        for line in lines:
            draw_text(surf, line, (box.x + 6, y), Col.TEXT_MUTED)
            y += LINE_H
        if item is not None and not self.service.owns(item):
            draw_text(surf, "TRY-ON ONLY - NOT OWNED", (box.x + 6, box.bottom - 6 - LINE_H), ROSE)
        elif item is not None:
            worn = self.worn().get(self.slot) == item
            draw_text(surf, "WORN - E TO REMOVE" if worn else "OWNED - E TO WEAR",
                      (box.x + 6, box.bottom - 6 - LINE_H), Col.GREEN if worn else Col.CYAN)
