"""MOCHI'S CAPSULE EXCHANGE screen (opened from the EXCHANGE tab of the Prize Counter).

Two views: RECYCLE (turn spare capsule collectibles into Capsule Stamps) and REDEEM (spend Stamps on
a chosen capsule prize). One local player owns the screen; only their keys (and ESC) drive it and
only their profile changes. All the rules live in capsule_exchange.ExchangeService - this file only
shows them, asks "RECYCLE?" before giving anything up and plays a short reveal.

Keys: UP/DOWN item, LEFT/RIGHT quantity (RECYCLE) or the other view (REDEEM), TAB / bag key the
other view, E recycle (asks first) / redeem, ESC back. Mouse: tabs and rows are clickable.
"""
import math

import pygame

from capsule_exchange import ExchangeService, recycle_value
from capsule_ui import _pod_big
from font import LINE_H, get_font
from gfx import scale_color
from item_icons import item_icon
from item_registry import ITEM_REGISTRY
from menu_kit import FRAME, GOLD, ROSE, ROW_H, MenuScene, fit_text
from plaza_stations import _LOOK
from preview_art import pedestal, scaled
from settings import Col
from shopkeeper import Shopkeeper
from ui import DialogueBox, draw_text, wrap_text

RECYCLE, REDEEM = "RECYCLE", "REDEEM"
VIEWS = (RECYCLE, REDEEM)
LIST = pygame.Rect(14, 60, 206, 9 * ROW_H + 2)
SIDE = pygame.Rect(226, 60, FRAME.right - 226 - 8, 9 * ROW_H + 2)
VISIBLE = 9
KEEPER_BOX = pygame.Rect(262, 6, 44, 36)
BUBBLE_W = 88
ACTION_LOCK = 0.7           # seconds after a recycle / redeem in which E does nothing (no double operations)
CONFIRM_DELAY = 0.25        # the confirmation box ignores keys this long (a held E cannot answer it)
ANIM_TIME = {RECYCLE: 0.8, REDEEM: 1.0}
STATUS_TEXT = {"owned": "OWNED", "full": "FULL", "need_stamps": "", "ok": ""}

MOCHI = {
    "open": "HELLO! BRING ME YOUR SPARES.",
    "recycle": ("THANK YOU! STAMPED WITH LOVE.", "MEOW! THEY GO TO A GOOD HOME.", "PURR... SO NEAT AND TIDY!"),
    "redeem": ("ENJOY YOUR NEW TREASURE!", "A PERFECT PICK! MEOW!", "FOR YOU, WITH A PAW STAMP!"),
    "keep": "A COLLECTOR ALWAYS KEEPS ONE!",
    "poor": "COME BACK WITH MORE STAMPS!",
    "owned": "YOU ALREADY HAVE THAT ONE!",
    "full": "YOUR BAG HAS ENOUGH OF THESE!",
    "book": "YOUR STAMP BOOK IS FULL! SPEND SOME!",
}

_stamp_cache = {}


def stamp_icon(color=GOLD, size=1):
    """The small paw-stamp icon (9x9, scaled by `size`): a rounded stamp with a paw print."""
    key = (tuple(color), size)
    icon = _stamp_cache.get(key)
    if icon is None:
        s = pygame.Surface((9, 9), pygame.SRCALPHA)
        s.fill(scale_color(color, 0.35), (1, 1, 7, 7))
        s.fill((0, 0, 0, 0), (1, 1, 1, 1))
        s.fill((0, 0, 0, 0), (7, 1, 1, 1))
        s.fill((0, 0, 0, 0), (1, 7, 1, 1))
        s.fill((0, 0, 0, 0), (7, 7, 1, 1))
        pygame.draw.rect(s, color, (0, 0, 9, 9), 1)
        s.fill(color, (3, 5, 3, 2))                 # the pad
        s.fill(color, (2, 3, 1, 1))                 # four toes
        s.fill(color, (4, 2, 1, 1))
        s.fill(color, (6, 3, 1, 1))
        s.fill(color, (3, 3, 1, 1))
        icon = scaled(s, size) if size != 1 else s
        _stamp_cache[key] = icon
    return icon


class ExchangeScene(MenuScene):
    title = "EXCHANGE"
    accent = GOLD
    glow = ROSE

    def __init__(self, game, owner, view=RECYCLE, keeper=None):
        super().__init__(game, owner)
        self.service = ExchangeService(owner.profile)
        self.keeper = keeper or Shopkeeper(sound=self.play)
        self.view = view if view in VIEWS else RECYCLE
        self.index = [0, 0]                 # cursor per view
        self.first = [0, 0]
        self.quantity = 1
        self.lock = 0.0
        self.anim = None                    # (kind, seconds so far, payload) while a reveal plays
        e = owner.controls.label("interact") or "E"
        self._hints = {RECYCLE: ("UP/DOWN ITEM", "LEFT/RIGHT AMOUNT", f"{e} RECYCLE", "TAB REDEEM", "ESC BACK"),
                       REDEEM: ("UP/DOWN PRIZE", f"{e} REDEEM", "TAB RECYCLE", "ESC BACK")}
        self.keeper.say(MOCHI["open"])

    # ------------------------------------------------------------ data
    @property
    def v(self):
        return VIEWS.index(self.view)

    @property
    def rows(self):
        return self.service.recycle_entries() if self.view == RECYCLE else self.service.redeem_entries()

    @property
    def entry(self):
        rows = self.rows
        i = self.index[self.v]
        return rows[min(i, len(rows) - 1)] if rows else None

    def _clamp_quantity(self):
        entry = self.entry
        top = self.service.max_recycle(entry.item_id) if self.view == RECYCLE and entry else 1
        self.quantity = max(1, min(self.quantity, max(1, top)))

    @property
    def busy(self):
        return self.lock > 0 or self.anim is not None or self.modal is not None

    # ------------------------------------------------------------ input
    def on_action(self, action):
        rows = self.rows
        if action == "back":
            self.play("cancel")
            self.close()
        elif action in ("tab", "menu"):
            self.set_view(VIEWS[(self.v + 1) % 2])
        elif action in ("up", "down") and rows:
            self.select((self.index[self.v] + (-1 if action == "up" else 1)) % len(rows))
        elif action in ("left", "right"):
            if self.view == RECYCLE:
                self.quantity += -1 if action == "left" else 1
                self._clamp_quantity()
            else:
                self.set_view(RECYCLE)
        elif action == "interact":
            self.activate()

    def set_view(self, view):
        if view != self.view:
            self.view, self.quantity = view, 1
            self.index[self.v] = min(self.index[self.v], max(0, len(self.rows) - 1))
            self._clamp_quantity()

    def select(self, i):
        v = self.v
        self.index[v] = i
        if i < self.first[v]:
            self.first[v] = i
        elif i >= self.first[v] + VISIBLE:
            self.first[v] = i - VISIBLE + 1
        self.quantity = 1
        self._clamp_quantity()

    def mochi(self, text):
        self.keeper.say(text)

    def activate(self):
        if self.busy:
            return
        entry = self.entry
        if entry is None:
            return
        if self.view == RECYCLE:
            self._ask_recycle(entry)
        else:
            self._redeem(entry)

    # ------------------------------------------------------------ RECYCLE
    def _ask_recycle(self, entry):
        if entry.spare < 1:
            self.say("KEEP YOUR LAST COPY", Col.YELLOW)
            self.mochi(MOCHI["keep"])
            self.play("cancel")
            return
        self._clamp_quantity()
        if self.service.max_recycle(entry.item_id) < 1:
            self.say("STAMP BOOK IS FULL", Col.MAGENTA)
            self.mochi(MOCHI["book"])
            self.play("cancel")
            return
        qty, pay = self.quantity, self.service.preview(entry.item_id, self.quantity)
        details = [(f"GIVE: {qty} X {entry.name}", Col.TEXT), (f"GET: +{pay} STAMPS", GOLD),
                   (f"YOU KEEP: {entry.owned - qty}", Col.GREEN)]
        self.modal = DialogueBox("RECYCLE?", "MOCHI WILL TAKE THE SPARES", ["RECYCLE", "CANCEL"],
                                 on_choice=lambda choice, e=entry, q=qty: self._recycle_answered(e, q, choice),
                                 accent=GOLD, glow=ROSE, details=details, input_delay=CONFIRM_DELAY)

    def _recycle_answered(self, entry, qty, choice):
        self.modal = None
        if choice != "RECYCLE":
            self.play("cancel")
            return
        self.lock = ACTION_LOCK
        result = self.service.recycle(entry.item_id, qty)
        if result.success:
            self.anim = (RECYCLE, 0.0, (entry.item_id, result.quantity, result.stamps))
            self.say(f"{result.quantity} X {result.name} -> {result.message}", Col.GREEN, 3.0)
            self.mochi(MOCHI["recycle"][self.profile.capsule_stamps % 3])
            self.play("capsule_drop")
            self._clamp_quantity()
        else:
            self.say(result.message, Col.MAGENTA)
            self.mochi(MOCHI["keep"] if result.code == "no_spare" else MOCHI["book"])
            self.play("cancel")

    # ------------------------------------------------------------ REDEEM
    def _redeem(self, entry):
        result = self.service.redeem(entry.item_id)
        self.lock = ACTION_LOCK
        if result.success:
            self.anim = (REDEEM, 0.0, (entry.item_id, result.stamps))
            self.say(f"{result.name} IS YOURS!", Col.GREEN, 3.0)
            self.mochi(MOCHI["redeem"][self.profile.capsule_stamps % 3])
            self.keeper.notify("purchase", self.owner.avatar)
            self.keeper.say(MOCHI["redeem"][self.profile.capsule_stamps % 3])
            self.play("purchase")
            self.owner.avatar.play_action("cheer", "down", emote="sparkle")
        else:
            self.say(result.message, Col.MAGENTA)
            self.mochi({"need_stamps": MOCHI["poor"], "owned": MOCHI["owned"], "full": MOCHI["full"]}.get(
                result.code, MOCHI["poor"]))
            self.play("cancel")

    def _click_row(self, i):
        if i == self.index[self.v]:
            self.activate()
        else:
            self.select(i)

    # ------------------------------------------------------------ update
    def update(self, dt):
        super().update(dt)
        self.keeper.update(dt)
        self.lock = max(0.0, self.lock - dt)
        if self.anim:
            kind, t, payload = self.anim
            t += dt
            self.anim = (kind, t, payload) if t < ANIM_TIME[kind] else None

    # ------------------------------------------------------------ draw
    def idle_message(self):
        entry = self.entry
        if entry is None:
            return "NOTHING HERE YET"
        if self.view == RECYCLE:
            return f"{entry.name}: {entry.value} STAMPS PER SPARE COPY"
        return f"{entry.name}: {entry.price} STAMPS"

    def draw_body(self, surf):
        self.hints = self._hints[self.view]
        self.draw_frame(surf, subtitle=self.owner.tag)
        self._draw_keeper(surf)
        self.draw_tabs(surf, list(VIEWS), self.v, on_click=lambda i: self.set_view(VIEWS[i]))
        self._draw_stamp_balance(surf)
        self._draw_list(surf)
        self._draw_side(surf)
        self.draw_footer(surf)

    def _draw_stamp_balance(self, surf):
        text = f"{self.profile.capsule_stamps}"
        x = LIST.right - 4
        draw_text(surf, text, (x, 46), GOLD, anchor="topright")
        w = get_font().size(text)[0]
        surf.blit(stamp_icon(GOLD), (x - w - 11, 45))
        draw_text(surf, "STAMPS", (x - w - 14, 47), Col.TEXT_MUTED, anchor="topright")

    def _draw_keeper(self, surf):
        box = KEEPER_BOX
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(GOLD, 0.5), box, 1)
        image, dy = self.keeper.portrait()
        surf.set_clip(box.inflate(-2, -2))
        surf.blit(image, image.get_rect(midbottom=(box.centerx, box.bottom - 2 + dy)))
        surf.set_clip(None)
        lines = self.keeper.speech_lines(BUBBLE_W - 8)
        if lines:
            panel = pygame.Rect(box.x - BUBBLE_W - 4, box.y + 1, BUBBLE_W, box.h - 2)
            surf.fill((246, 240, 255), panel)
            pygame.draw.rect(surf, Col.OUTLINE, panel, 1)
            pygame.draw.polygon(surf, (246, 240, 255), [(panel.right, panel.centery - 3),
                                                        (panel.right + 3, panel.centery), (panel.right, panel.centery + 3)])
            y = panel.centery - len(lines[:3]) * LINE_H // 2
            for line in lines[:3]:
                draw_text(surf, line, (panel.centerx, y), (60, 36, 100), anchor="midtop")
                y += LINE_H

    def _draw_list(self, surf):
        rows, v = self.rows, self.v
        if not rows:
            draw_text(surf, "NO CAPSULE COLLECTIBLES YET", (LIST.x + 6, LIST.y + 8), Col.TEXT_MUTED)
            draw_text(surf, "PLAY THE CAPSULE MACHINES", (LIST.x + 6, LIST.y + 8 + LINE_H + 2), Col.TEXT_MUTED)
            draw_text(surf, "AND COME BACK WITH SPARES!", (LIST.x + 6, LIST.y + 8 + 2 * (LINE_H + 2)), Col.TEXT_MUTED)
            return
        for slot in range(VISIBLE):
            i = self.first[v] + slot
            if i >= len(rows):
                break
            e = rows[i]
            rect = pygame.Rect(LIST.x, LIST.y + slot * ROW_H, LIST.w - 6, ROW_H - 2)
            selected = i == self.index[v]
            self.hit(rect, lambda i=i: self._click_row(i))
            if self.view == RECYCLE:
                self.draw_row_bg(surf, rect, selected, owned=e.spare > 0)
                icon = item_icon(ITEM_REGISTRY.get(e.item_id))
                surf.blit(icon, icon.get_rect(midleft=(rect.x + 4, rect.centery)))
                draw_text(surf, fit_text(e.name, 88), (rect.x + 22, rect.y + 5),
                          Col.TEXT if selected else Col.TEXT_MUTED)
                if e.spare:
                    draw_text(surf, f"+{e.spare} SPARE", (rect.right - 5, rect.y + 5), Col.GREEN, anchor="topright")
                else:
                    draw_text(surf, "KEEP", (rect.right - 5, rect.y + 5), Col.TEXT_MUTED, anchor="topright")
                draw_text(surf, f"X{e.owned}", (rect.right - 62, rect.y + 5), Col.CYAN, anchor="topright")
            else:
                got = e.status in ("owned", "full")
                self.draw_row_bg(surf, rect, selected, owned=got)
                icon = item_icon(ITEM_REGISTRY.get(e.item_id))
                surf.blit(icon, icon.get_rect(midleft=(rect.x + 4, rect.centery)))
                name_color = Col.TEXT if selected else Col.TEXT_MUTED
                draw_text(surf, fit_text(e.name, 92), (rect.x + 22, rect.y + 5), scale_color(Col.GREEN, 0.9) if got else name_color)
                if got:
                    draw_text(surf, STATUS_TEXT[e.status], (rect.right - 5, rect.y + 5), Col.GREEN, anchor="topright")
                else:
                    color = GOLD if e.status == "ok" else scale_color(ROSE, 0.9)
                    price = draw_text(surf, str(e.price), (rect.right - 17, rect.y + 5), color, anchor="topright")
                    surf.blit(stamp_icon(color), (rect.right - 14, rect.y + 4))
                    if e.owned:
                        draw_text(surf, f"X{e.owned}", (price.left - 6, rect.y + 5), Col.CYAN, anchor="topright")
        self.draw_scrollbar(surf, LIST, self.first[v], VISIBLE, len(rows))

    def _draw_side(self, surf):
        box = SIDE
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(GOLD, 0.5), box, 1)
        entry = self.entry
        stage = pygame.Rect(box.x + 4, box.y + 4, box.w - 8, 62)
        surf.fill((8, 5, 22), stage)
        pulse = 0.5 + 0.5 * math.sin(self.time * 3)
        pygame.draw.rect(surf, scale_color(ROSE, 0.35 + 0.25 * pulse), stage, 1)
        surf.blit(pedestal((stage.w - 40, 5), GOLD), (stage.x + 20, stage.bottom - 8))
        if entry is None:
            return
        definition = ITEM_REGISTRY.get(entry.item_id)
        icon = scaled(item_icon(definition), 2)
        surf.blit(icon, icon.get_rect(midbottom=(stage.centerx, stage.bottom - 8 + int(math.sin(self.time * 3)))))
        self._draw_anim(surf, stage)
        y = stage.bottom + 4
        for line in wrap_text(entry.name, box.w - 12)[:1]:
            draw_text(surf, line, (box.x + 6, y), Col.TEXT, glow=scale_color(GOLD, 0.4))
            y += LINE_H
        draw_text(surf, f"{definition.rarity}", (box.x + 6, y), Col.CYAN)
        y += LINE_H + 2
        if self.view == RECYCLE:
            self._side_recycle(surf, box, entry, y)
        else:
            self._side_redeem(surf, box, entry, definition, y)

    def _side_recycle(self, surf, box, entry, y):
        draw_text(surf, f"YOU OWN X{entry.owned}", (box.x + 6, y), Col.TEXT_MUTED)
        y += LINE_H
        draw_text(surf, f"{entry.value} STAMPS EACH", (box.x + 6, y), GOLD)
        y += LINE_H
        if entry.displayed:
            draw_text(surf, "ON YOUR SHOWCASE", (box.x + 6, y), Col.GREEN)
        y += LINE_H
        bottom = box.bottom - 6 - LINE_H
        if entry.spare < 1:
            draw_text(surf, "KEEP YOUR LAST COPY", (box.x + 6, bottom), Col.YELLOW)
            return
        qty, cap = self.quantity, self.service.max_recycle(entry.item_id)
        draw_text(surf, f"< {qty} >  OF {cap}", (box.x + 6, bottom - LINE_H - 2), Col.TEXT)
        pay = self.service.preview(entry.item_id, qty)
        surf.blit(stamp_icon(GOLD), (box.x + 6, bottom - 1))
        draw_text(surf, f"+{pay} STAMPS", (box.x + 18, bottom), GOLD)

    def _side_redeem(self, surf, box, entry, definition, y):
        for line in wrap_text(definition.description, box.w - 12)[:3]:
            draw_text(surf, line, (box.x + 6, y), Col.TEXT_MUTED)
            y += LINE_H
        bottom = box.bottom - 6 - LINE_H
        if entry.status == "owned":
            text, color = "ALREADY OWNED", Col.GREEN
        elif entry.status == "full":
            text, color = f"HAVE X{entry.owned} (FULL)", Col.YELLOW
        elif entry.status == "need_stamps":
            text, color = f"NEED {entry.price - self.profile.capsule_stamps} MORE", ROSE
        else:
            text, color = f"{entry.price} STAMPS", GOLD
        surf.blit(stamp_icon(color), (box.x + 6, bottom - 1))
        draw_text(surf, fit_text(text, box.w - 28), (box.x + 18, bottom), color)

    def _draw_anim(self, surf, stage):
        if not self.anim:
            return
        kind, t, payload = self.anim
        k = t / ANIM_TIME[kind]
        cx = stage.centerx
        if kind == RECYCLE:
            item_id, qty, stamps = payload
            top, bottom = _LOOK["cat"]["pods"][0] if item_id.startswith("cat_") else _LOOK["retro"]["pods"][1]
            for n in range(min(qty, 4)):                    # a few capsules drop into the slot one after another
                kk = max(0.0, min(1.0, (k * 1.4 - n * 0.18) / 0.5))
                if 0 < kk < 1:
                    _pod_big(surf, (cx - 18 + n * 12, stage.y + 6 + int(kk * 34)), top, bottom, radius=5)
            if k > 0.45:                                    # the stamp pops and "+N" floats up
                pop = min(1.0, (k - 0.45) / 0.2)
                icon = stamp_icon(GOLD, 2)
                surf.blit(icon, icon.get_rect(center=(cx, stage.centery - int(10 * pop))))
                draw_text(surf, f"+{stamps}", (cx, stage.centery - 22 - int(8 * pop)), GOLD, 2, anchor="center",
                          glow=(120, 80, 10))
        else:
            for i in range(10):                             # sparkles rising round the prize
                a = i * math.tau / 10 + t * 3
                r = 10 + 26 * k
                x, y = cx + math.cos(a) * r, stage.centery + math.sin(a) * r * 0.6 - 10 * k
                surf.fill(GOLD if i % 2 else (255, 255, 255), (int(x), int(y), 2, 2))
            draw_text(surf, "ENJOY!", (cx, stage.y + 5), GOLD, anchor="midtop", glow=(120, 80, 10))
