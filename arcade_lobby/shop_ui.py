"""PRIZE COUNTER: the ticket shop opened from the counter in PRIZE PLAZA.

Tabs (FREE PLAY, HOME, COSMETICS, COLLECT, RACING), a list of prizes with
price / ownership on the left and a pixel-art preview with the description on
the right. E asks "BUY?" (a confirmation box); the purchase itself is
ShopService.purchase(), so this screen never touches tickets or inventory.

Keys (the owning player's own): UP/DOWN item, LEFT/RIGHT or TAB category, E buy,
ESC leave. Mouse: click a tab or item (click the selected item to buy), wheel scrolls.
"""
import math

import pygame

from font import LINE_H
from gfx import scale_color
from item_registry import ITEM_REGISTRY
from item_icons import item_icon
from menu_kit import FRAME, GOLD, ROSE, ROW_H, MenuScene, fit_text, item_icon_for_ticket
from preview_art import pedestal, preview_for_item
from prize_shop import CATEGORIES, ShopService, entries_in
from settings import Col
from ui import DialogueBox, draw_text, wrap_text

RACING = "RACING"
TABS = CATEGORIES + (RACING,)
LIST = pygame.Rect(14, 60, 206, 9 * ROW_H + 2)          # 9 rows
SIDE = pygame.Rect(226, 60, FRAME.right - 226 - 8, 9 * ROW_H + 2)
BUY_LOCK = 0.4              # seconds after a purchase in which E does nothing (no double buys)
CONFIRM_DELAY = 0.25        # the confirmation box ignores keys this long (a held E cannot answer it)


class ShopScene(MenuScene):
    title = "PRIZE COUNTER"
    VISIBLE = 9

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.shop = ShopService(owner.profile)
        self.tab = 0
        self.index = 0
        self.first = 0
        self.lock = 0.0
        self.banner = None              # (text, seconds left) after a purchase
        self.hints = ("UP/DOWN ITEM", "LEFT/RIGHT CATEGORY", f"{owner.controls.label('interact') or 'E'} BUY",
                      "ESC LEAVE")

    # ------------------------------------------------------------ data
    @property
    def category(self):
        return TABS[self.tab]

    @property
    def rows(self):
        return entries_in(self.category) if self.category != RACING else []

    @property
    def entry(self):
        rows = self.rows
        return rows[self.index] if rows else None

    # ------------------------------------------------------------ input
    def on_action(self, action):
        rows = self.rows
        if action == "back":
            self.play("cancel")
            self.close()
        elif action in ("left", "right", "tab"):
            self.set_tab((self.tab + (-1 if action == "left" else 1)) % len(TABS))
        elif action in ("up", "down") and rows:
            self.select((self.index + (-1 if action == "up" else 1)) % len(rows))
        elif action == "interact":
            self.activate()

    def set_tab(self, tab):
        if tab != self.tab:
            self.tab, self.index, self.first = tab, 0, 0

    def select(self, index):
        self.index = index
        if index < self.first:
            self.first = index
        elif index >= self.first + self.VISIBLE:
            self.first = index - self.VISIBLE + 1

    def activate(self):
        """E on the highlighted prize: open the BUY? box (or explain why not)."""
        if self.category == RACING:
            self.open_racing()
            return
        entry = self.entry
        if entry is None or self.lock > 0:
            return
        why = self.shop.blocked(entry)
        if why == "owned":
            self.say("YOU ALREADY OWN THIS", Col.GREEN)
            self.play("cancel")
        elif why == "stack_full":
            self.say("YOU HAVE ENOUGH ALREADY", Col.YELLOW)
            self.play("cancel")
        elif not self.shop.can_afford(entry):
            self.say(f"NEED {entry.cost - self.shop.tickets} MORE TICKETS", Col.MAGENTA)
            self.play("cancel")
        else:
            self.confirm(entry)

    def open_racing(self):
        from racing_progression.ui import PrizeCounterScene
        self.game.scenes.push(PrizeCounterScene(self.game, self.owner))

    def confirm(self, entry):
        left = self.shop.tickets - entry.cost
        details = [(f"PRICE: {entry.cost} TICKETS", GOLD), (f"YOU HAVE: {self.shop.tickets}", Col.TEXT_MUTED),
                   (f"LEFT AFTER: {left}", Col.GREEN)]
        if not self.shop.is_unique(entry) and self.shop.quantity(entry):
            details.insert(0, (f"YOU OWN: {self.shop.quantity(entry)}", Col.CYAN))
        self.modal = DialogueBox(
            "BUY?", entry.name, ["BUY", "CANCEL"], on_choice=lambda choice: self._answered(entry, choice),
            accent=GOLD, glow=ROSE, details=details, input_delay=CONFIRM_DELAY)

    def _answered(self, entry, choice):
        self.modal = None
        if choice != "BUY":
            self.play("cancel")
            return
        self.lock = BUY_LOCK
        result = self.shop.purchase(entry.item_id)
        if result.success:
            self.say(f"{result.message}  {entry.name}", Col.GREEN, 3.0)
            self.banner = (entry.name, 1.6)
            self.play("purchase")
            self.owner.avatar.play_action("cheer", "down", emote="sparkle")    # plays when the room is back
        else:
            self.say(result.message, Col.MAGENTA)
            self.play("cancel")

    def _click_row(self, i):
        if i == self.index and self.lock <= 0:
            self.activate()
        else:
            self.select(i)

    def update(self, dt):
        super().update(dt)
        self.lock = max(0.0, self.lock - dt)
        if self.banner:
            text, left = self.banner
            self.banner = (text, left - dt) if left - dt > 0 else None

    # ------------------------------------------------------------ draw
    def idle_message(self):
        if self.category == RACING:
            return "CARS, TRACKS AND PAINTS FOR RETRO RACER"
        entry = self.entry
        if entry is None:
            return ""
        if self.shop.blocked(entry) == "owned":
            return "OWNED - USE IT FROM HOME"
        return f"{entry.name}: {entry.cost} TICKETS"

    def draw_body(self, surf):
        self.draw_frame(surf)
        self.draw_tabs(surf, TABS, self.tab, on_click=self.set_tab)
        if self.category == RACING:
            self._draw_racing(surf)
        else:
            self._draw_list(surf)
            self._draw_side(surf, self.entry)
        self.draw_footer(surf)

    def _draw_list(self, surf):
        rows = self.rows
        for slot in range(self.VISIBLE):
            i = self.first + slot
            if i >= len(rows):
                break
            entry = rows[i]
            rect = pygame.Rect(LIST.x, LIST.y + slot * ROW_H, LIST.w - 6, ROW_H - 2)
            owned = self.shop.is_owned(entry)
            unique = self.shop.is_unique(entry)
            self.draw_row_bg(surf, rect, i == self.index, owned=owned and unique)
            self.hit(rect, lambda i=i: self._click_row(i))
            definition = ITEM_REGISTRY.get(entry.item_id)
            icon = item_icon(definition)
            surf.blit(icon, icon.get_rect(midleft=(rect.x + 4, rect.centery)))
            afford = self.shop.can_afford(entry)
            name_color = Col.TEXT if i == self.index else Col.TEXT_MUTED
            if owned and unique:
                name_color = scale_color(Col.GREEN, 0.9)
            draw_text(surf, fit_text(entry.name, 98), (rect.x + 22, rect.y + 5), name_color)
            if owned and unique:
                draw_text(surf, "OWNED", (rect.right - 5, rect.y + 5), Col.GREEN, anchor="topright")
            else:
                price = str(entry.cost)
                color = GOLD if afford else scale_color(ROSE, 0.9)
                draw_text(surf, price, (rect.right - 17, rect.y + 5), color, anchor="topright")
                surf.blit(item_icon_for_ticket(color), (rect.right - 14, rect.y + 6))
                if owned:                           # a stackable: how many you hold
                    draw_text(surf, f"X{self.shop.quantity(entry)}", (rect.right - 45, rect.y + 5),
                              Col.CYAN, anchor="topright")
        self.draw_scrollbar(surf, LIST, self.first, self.VISIBLE, len(rows))

    def _draw_side(self, surf, entry):
        box = SIDE
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(GOLD, 0.5), box, 1)
        if entry is None:
            return
        stage = pygame.Rect(box.x + 4, box.y + 4, box.w - 8, 76)
        surf.fill((8, 5, 22), stage)
        glow = 0.5 + 0.5 * math.sin(self.time * 3)
        pygame.draw.rect(surf, scale_color(ROSE, 0.35 + 0.25 * glow), stage, 1)
        surf.blit(pedestal((stage.w - 40, 5), GOLD), (stage.x + 20, stage.bottom - 8))
        image = self._preview(entry, (stage.w - 12, stage.h - 14))
        surf.blit(image, image.get_rect(midbottom=(stage.centerx, stage.bottom - 7 + int(math.sin(self.time * 3)))))
        if self.banner:
            tag = pygame.Rect(stage.x, stage.y, stage.w, 11)
            surf.fill((30, 120, 70), tag)
            draw_text(surf, "PURCHASED!", tag.center, Col.TEXT, anchor="center")
        y = stage.bottom + 5
        definition = ITEM_REGISTRY.get(entry.item_id)
        for line in wrap_text(entry.name, box.w - 12)[:2]:
            draw_text(surf, line, (box.x + 6, y), Col.TEXT, glow=scale_color(GOLD, 0.4))
            y += LINE_H
        draw_text(surf, f"{definition.rarity}  {self._kind(entry)}", (box.x + 6, y), Col.CYAN)
        y += LINE_H + 3
        for line in wrap_text(definition.description, box.w - 12)[:3]:
            draw_text(surf, line, (box.x + 6, y), Col.TEXT_MUTED)
            y += LINE_H
        self._draw_status(surf, entry, box)

    def _kind(self, entry):
        return {"FREE PLAY": "COUPON", "HOME": "DECORATION", "COSMETICS": "COSMETIC",
                "COLLECT": "COLLECTIBLE"}.get(entry.category, "")

    def _draw_status(self, surf, entry, box):
        owned = self.shop.quantity(entry)
        why = self.shop.blocked(entry)
        if why == "owned":
            text, color = "OWNED", Col.GREEN
        elif why == "stack_full":
            text, color = f"OWNED X{owned} (FULL)", Col.YELLOW
        elif not self.shop.can_afford(entry):
            text, color = f"NEED {entry.cost - self.shop.tickets} MORE", ROSE
        else:
            text, color = f"{entry.cost} TICKETS", GOLD
            if owned:
                text += f"  OWN X{owned}"
        draw_text(surf, fit_text(text, box.w - 12), (box.x + 6, box.bottom - 6 - LINE_H), color)

    def _preview(self, entry, size):
        avatar = self.owner.avatar
        return preview_for_item(entry.item_id, avatar.look, avatar.appearance, size)

    def _draw_racing(self, surf):
        box = pygame.Rect(LIST.x, LIST.y, FRAME.w - 16, LIST.h)
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(Col.CYAN, 0.5), box, 1)
        draw_text(surf, "RETRO RACER PRIZES", (box.centerx, box.y + 14), Col.CYAN, 2, anchor="midtop",
                  glow=scale_color(ROSE, 0.6))
        for i, line in enumerate(("CARS, TRACKS, SCENERY AND PAINTS", "ARE SOLD AT THE RACING COUNTER.",
                                  "TICKETS ARE SHARED - YOUR OWN WALLET.")):
            draw_text(surf, line, (box.centerx, box.y + 48 + i * (LINE_H + 2)), Col.TEXT_MUTED, anchor="midtop")
        button = pygame.Rect(box.centerx - 60, box.y + 112, 120, 18)
        self.draw_row_bg(surf, button, True)
        draw_text(surf, "OPEN RACING PRIZES", button.center, Col.TEXT, anchor="center")
        self.hit(button, self.open_racing)
