"""WARDROBE: change what the avatar looks like and wears.

Two kinds of tab. The LOOK tabs (skin, eyes, hair, dye, shirt) are the FREE basic
appearance (avatar_style.py): nothing to own or buy, E simply applies the choice.
The ITEM tabs are the cosmetic slots. The highlighted item is tried on the avatar
straight away (a preview, even for items the player does not own yet); E wears
it - only if it is owned and made for that slot, which CosmeticService checks -
and E on the item that is already worn takes it off. The first row of every
tab is the plain default. Everything is that player's own profile: P1 and P2
change their own avatar.
"""
import pygame

from avatar_style import FIELD_NAMES, FIELDS, OPTIONS, apply_basic, option, swatch_color
from cosmetics import SLOT_NAMES, SLOTS, CosmeticService, cosmetics_for
from font import LINE_H, get_font
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
    LOOK_TABS = tuple(("look", f) for f in FIELDS)              # free: skin, eyes, hair, dye, shirt
    ITEM_TABS = tuple(("item", s) for s in SLOTS)               # owned cosmetics
    TABS = ITEM_TABS + LOOK_TABS

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.service = CosmeticService(owner.profile)
        self.tab = 0
        self.index = 0
        self.first = 0
        self.turn = 0.0                     # the preview turns by itself
        self.manual_facing = None
        self.hints = ("UP/DOWN ITEM", "LEFT/RIGHT PART", "E APPLY", "TAB TURN", "ESC BACK")
        self.set_tab(0)

    # ------------------------------------------------------------ data
    @property
    def kind(self):
        return self.TABS[self.tab][0]

    @property
    def is_look(self):
        return self.kind == "look"

    @property
    def slot(self):
        """The cosmetic slot of an item tab (None on a look tab)."""
        return self.TABS[self.tab][1] if not self.is_look else None

    @property
    def field(self):
        """The basic-appearance field of a look tab (None on an item tab)."""
        return self.TABS[self.tab][1] if self.is_look else None

    @property
    def tab_names(self):
        """The tab strip of the current section (LOOK is free, ITEMS are owned cosmetics)."""
        if self.is_look:
            return [FIELD_NAMES[f] for _, f in self.LOOK_TABS]
        return [SLOT_NAMES[s] for _, s in self.ITEM_TABS]

    @property
    def rows(self):
        """Look tab: its options. Item tab: [None] + the cosmetics of the slot (row 0 is the default)."""
        if self.is_look:
            return [o.id for o in OPTIONS[self.field]]
        return [NONE_ROW] + [c.item_id for c in cosmetics_for(self.slot)]

    @property
    def highlighted(self):
        rows = self.rows
        return rows[min(self.index, len(rows) - 1)]

    def worn(self):
        return self.service.worn()

    def current_choice(self):
        return self.profile.basic_appearance.get(self.field)

    def preview_appearance(self):
        """What the avatar shows: what is worn, with the highlighted row tried on."""
        appearance = dict(self.worn())
        if self.is_look:
            return appearance
        item = self.highlighted
        if item is None:
            appearance.pop(self.slot, None)
        else:
            appearance[self.slot] = item
        return appearance

    def preview_look(self):
        """The avatar's look with the highlighted free option tried on (nothing is saved)."""
        basic = self.profile.basic_appearance
        if self.is_look:
            basic = basic.with_choice(self.field, self.highlighted)
        return apply_basic(self.owner.avatar.base_look, basic)

    # ------------------------------------------------------------ input
    def on_action(self, action):
        if action == "back":
            self.close()
        elif action in ("left", "right"):
            self.set_tab((self.tab + (-1 if action == "left" else 1)) % len(self.TABS))
        elif action in ("up", "down"):
            self.select((self.index + (-1 if action == "up" else 1)) % len(self.rows))
        elif action == "tab":
            current = self.manual_facing or FACING_CYCLE[int(self.turn / 1.4) % 4]
            self.manual_facing = FACING_CYCLE[(FACING_CYCLE.index(current) + 1) % 4]
        elif action == "interact":
            self.activate()

    def set_tab(self, tab):
        self.tab, self.index, self.first = tab, 0, 0
        if self.is_look:                                # start on the current choice
            self.select(self.rows.index(self.current_choice()))
            return
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
        if self.is_look:
            if self.profile.set_basic_appearance(self.profile.basic_appearance, self.field, item):
                self.say(f"{FIELD_NAMES[self.field]}: {option(self.field, item).name} - FREE", Col.GREEN)
                self.play("equip")
                self.owner.avatar.play_action("equip")
            else:
                self.say("ALREADY SELECTED", Col.TEXT_MUTED)
            return
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
            self.play("equip")
            self.owner.avatar.play_action("equip")
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
        offset = len(self.ITEM_TABS) if self.is_look else 0
        end = self.draw_tabs(surf, self.tab_names, self.tab - offset,
                             on_click=lambda i: self.set_tab(i + offset))
        for name, tab, on in (("LOOK - FREE", len(self.ITEM_TABS), self.is_look), ("ITEMS", 0, not self.is_look)):
            w = get_font().size(name)[0] + 10
            rect = pygame.Rect(0, 44, w, 12)
            rect.x = (FRAME.right - 10 - w) if tab else (FRAME.right - 10 - w - 3 - (get_font().size("LOOK - FREE")[0] + 10))
            pygame.draw.rect(surf, Col.GREEN if on else (60, 46, 100), rect, 1)
            draw_text(surf, name, rect.center, Col.GREEN if on else Col.TEXT_MUTED, anchor="center")
            self.hit(rect, lambda t=tab: self.set_tab(t))
        self._draw_list(surf)
        self._draw_stage(surf)
        self.draw_footer(surf)

    def _row_label(self, item):
        if self.is_look:
            return option(self.field, item).name
        if item is None:
            return "DEFAULT" if self.slot == "palette" else "NONE"
        return ITEM_REGISTRY.get(item).name

    def _draw_list(self, surf):
        rows = self.rows
        worn = self.current_choice() if self.is_look else self.worn().get(self.slot)
        for slot_i in range(self.VISIBLE):
            i = self.first + slot_i
            if i >= len(rows):
                break
            item = rows[i]
            rect = pygame.Rect(LIST.x, LIST.y + slot_i * ROW_H, LIST.w - 6, ROW_H - 2)
            owned = self.is_look or item is None or self.service.owns(item)
            on = item == worn
            self.draw_row_bg(surf, rect, i == self.index, owned=on)
            self.hit(rect, lambda i=i: self._click_row(i))
            if self.is_look:
                colour = swatch_color(self.field, option(self.field, item))
                if colour is not None:
                    chip = pygame.Rect(rect.x + 5, rect.centery - 5, 11, 10)
                    surf.fill(colour, chip)
                    pygame.draw.rect(surf, Col.TEXT_MUTED, chip, 1)
            elif item is not None:
                icon = item_icon(ITEM_REGISTRY.get(item))
                surf.blit(icon, icon.get_rect(midleft=(rect.x + 4, rect.centery)))
            color = Col.TEXT if i == self.index else Col.TEXT_MUTED
            if not owned:
                color = scale_color(Col.TEXT_MUTED, 0.6)
            draw_text(surf, fit_text(self._row_label(item), 82), (rect.x + 22, rect.y + 5), color)
            if self.is_look:
                if on:
                    draw_text(surf, "ON", (rect.right - 5, rect.y + 5), Col.GREEN, anchor="topright")
                else:
                    draw_text(surf, "FREE", (rect.right - 5, rect.y + 5), Col.CYAN, anchor="topright")
            elif item is None:
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

    def _click_row(self, i):
        if i == self.index:
            self.activate()
        else:
            self.select(i)

    def _draw_stage(self, surf):
        box = STAGE
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(Col.MAGENTA, 0.5), box, 1)
        facing = self.manual_facing or FACING_CYCLE[int(self.turn / 1.4) % 4]
        frame = int(self.turn * 2.5) % 8
        image = scaled(avatar_image(self.preview_look(), self.preview_appearance(), facing, frame), 4)
        floor = pygame.Rect(box.centerx - 30, box.y + 98, 60, 6)
        surf.blit(pedestal(floor.size, Col.MAGENTA), floor.topleft)
        surf.blit(image, image.get_rect(midbottom=(box.centerx, floor.y + 2)))
        item = self.highlighted
        name = self._row_label(item)
        draw_text(surf, fit_text(name, box.w - 12), (box.centerx, box.y + 6), Col.TEXT, anchor="midtop",
                  glow=scale_color(Col.MAGENTA, 0.5))
        y = box.y + 108
        if self.is_look:
            lines = ["A FREE LOOK: NO TICKETS NEEDED.", "CHANGE IT ANY TIME."]
            draw_text(surf, "ON YOU" if item == self.current_choice() else "E TO APPLY",
                      (box.x + 6, box.bottom - 6 - LINE_H), Col.GREEN if item == self.current_choice() else Col.CYAN)
        elif item is None:
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
        if self.is_look:
            pass
        elif item is not None and not self.service.owns(item):
            draw_text(surf, "TRY-ON ONLY - NOT OWNED", (box.x + 6, box.bottom - 6 - LINE_H), ROSE)
        elif item is not None:
            worn = self.worn().get(self.slot) == item
            draw_text(surf, "WORN - E TO REMOVE" if worn else "OWNED - E TO WEAR",
                      (box.x + 6, box.bottom - 6 - LINE_H), Col.GREEN if worn else Col.CYAN)
