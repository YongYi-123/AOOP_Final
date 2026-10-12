"""NEON VEND-O-MATIC screen: the shop opened from the vending machine on the Arcade Floor.

A MenuScene owned by one player: only their keys drive it and every ticket / item it touches is
theirs (VendingService works on their profile). Arrow / WASD keys move over the six products, the use
key buys, ESC leaves.

The screen also hosts the hidden sequence (secret_input.py). A SecretSequenceListener lives only
here, sees the same key events as normal navigation, and never buys: its keys are not the use key.
When it completes, ONLY this screen freezes: a short glitch, the music dips (music_duck, read by the
game's duck_for), and a terminal page appears. ESC leaves it and closes the screen.
"""
import math
import random

import pygame

from font import LINE_H, get_font
from gfx import scale_color, shade
from item_icons import item_icon
from item_registry import ITEM_REGISTRY, NOVELTY_STACK
from menu_kit import FRAME, GOLD, MenuScene, fit_text, item_icon_for_ticket
from secret_input import SecretSequenceListener
from settings import VIEW_H, VIEW_W, Col
from ui import draw_text, wrap_text
from vending_shop import VEND_ENTRIES, VendingService

TITLE = "NEON VEND-O-MATIC"
SECRET_FLAG = "vending_konami_discovered"
COLS, ROWS = 3, 2
BODY = pygame.Rect(14, 50, 196, 174)
MARQUEE = pygame.Rect(18, 54, 188, 13)
WINDOW = pygame.Rect(20, 71, 136, 114)
CELL_W, CELL_H = 44, 56
KEYPAD = pygame.Rect(160, 71, 46, 114)
LCD = pygame.Rect(163, 75, 40, 24)
SLOT = pygame.Rect(170, 112, 26, 34)
TRAY = pygame.Rect(20, 190, 136, 30)
DETAIL = pygame.Rect(220, 50, 166, 174)

BUY_LOCK = 1.1              # seconds after a purchase in which the use key does nothing (no double buys)
INSERT_TIME, DROP_AT, DROP_TIME = 0.35, 0.4, 0.45
GLITCH_TIME = 1.25
TYPE_RATE = 34              # terminal characters per second
SECRET_DUCK = 0.3
GREEN = (70, 255, 120)
TERMINAL_LINES = (("SYSTEM OVERRIDE", 2), ("", 1), ("USER: UNKNOWN", 1), ("ACCESS LEVEL: 01", 1),
                  ("", 1), ("THE ARCADE REMEMBERS.", 1))


TERMINAL_TYPED = sum(len(text) + 4 for text, _ in TERMINAL_LINES) / TYPE_RATE    # seconds until the page is fully typed


class VendingScene(MenuScene):
    title = TITLE
    accent = Col.CYAN
    glow = Col.MAGENTA

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.service = VendingService(owner.profile)
        self.entries = VEND_ENTRIES
        self.index = 0
        self.lock = 0.0
        self.purchase = None            # {"index", "t", "dropped"} while the machine is dispensing
        self.shake = 0.0                # a refused purchase rattles the product
        self.flash = 0.0                # the LCD blinks red after a refusal
        self.music_duck = None          # set while the secret page is up (see Game.duck_for)
        self.listener = SecretSequenceListener(owner.controls)
        self.secret = None              # None, or {"t": seconds, "new": first discovery?}
        self._frozen = None             # the frozen shop frame the glitch tears apart
        self._scan = None
        interact = owner.controls.label("interact") or "E"
        self.hints = ("ARROWS SELECT", f"{interact} BUY", "ESC LEAVE")

    # ------------------------------------------------------------ lifecycle
    def on_enter(self):
        self.play("vend_hum")

    def on_exit(self):
        self.music_duck = None
        self.listener.reset()

    # ------------------------------------------------------------ data
    @property
    def entry(self):
        return self.entries[self.index]

    def can_buy_now(self):
        return self.lock <= 0 and self.secret is None

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if self.secret is not None:
            self._secret_event(event)
            return
        if self.listener.feed(event):
            self._start_secret()
            return
        super().handle_event(event)

    def _click(self, event):
        if self.secret is None:
            super()._click(event)

    def on_action(self, action):
        if self.secret is not None:
            return
        if action == "back":
            self.play("cancel")
            self.close()
        elif action in ("left", "right"):
            col = (self.index % COLS + (1 if action == "right" else -1)) % COLS
            self.select(self.index // COLS * COLS + col)
        elif action in ("up", "down"):
            self.select((self.index + COLS) % len(self.entries))
        elif action == "interact":
            self.buy()

    def select(self, index):
        if index != self.index:
            self.index = index
            self.play("vend_select")

    def buy(self):
        if not self.can_buy_now():
            return
        entry = self.entry
        result = self.service.purchase(entry.item_id)
        if result.success:
            self.lock = BUY_LOCK
            self.purchase = {"index": self.index, "t": 0.0, "dropped": False}
            self.play("token")
            self.say(f"{entry.name} - {entry.cost} TICKETS", Col.GREEN, 2.5)
        else:
            self.play("cancel")
            self.shake = self.flash = 0.4
            if result.code == "need_tickets":
                self.say(f"NEED {entry.cost - self.profile.tickets} MORE TICKETS", Col.MAGENTA)
            else:
                self.say(result.message, Col.MAGENTA)

    # ------------------------------------------------------------ the secret
    def _start_secret(self):
        self.secret = {"t": 0.0, "new": self.profile.discover_secret(SECRET_FLAG)}
        self.music_duck = SECRET_DUCK
        self.play("glitch")

    def _secret_event(self, event):
        """While the secret is up the shop is frozen; ESC leaves at any time, the use key once the page is typed."""
        if event.type != pygame.KEYDOWN:
            return
        leave = event.key == pygame.K_ESCAPE or (self.secret["t"] > GLITCH_TIME + TERMINAL_TYPED
                                                 and self.input.action(event) == "interact")
        if leave:
            self.play("cancel")
            self.close()

    # ------------------------------------------------------------ update
    def update(self, dt):
        super().update(dt)
        self.lock = max(0.0, self.lock - dt)
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)
        if self.secret is not None:
            self.secret["t"] += dt
        if self.purchase is not None:
            p = self.purchase
            p["t"] += dt
            if not p["dropped"] and p["t"] >= DROP_AT + DROP_TIME:
                p["dropped"] = True
                self.play("vend_drop")
            if p["t"] > BUY_LOCK + 1.0:
                self.purchase = None

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        if self.secret is None:
            super().draw(surf)
            return
        self._hit = []
        t = self.secret["t"]
        if self._frozen is None:
            self._frozen = pygame.Surface(surf.get_size())
            self.draw_body(self._frozen)
        if t < GLITCH_TIME:
            self._draw_glitch(surf, t)
        else:
            self._draw_terminal(surf, t - GLITCH_TIME)

    def cell_rect(self, index):
        return pygame.Rect(WINDOW.x + 2 + index % COLS * CELL_W, WINDOW.y + 1 + index // COLS * CELL_H,
                           CELL_W, CELL_H)

    def draw_body(self, surf):
        self.draw_frame(surf, TITLE, self.owner.tag)
        self._draw_machine(surf)
        self._draw_details(surf)
        self.draw_footer(surf)
        self.draw_overlay(surf)

    def idle_message(self):
        return "PICK A SNACK"

    def _draw_machine(self, surf):
        pygame.draw.rect(surf, (30, 40, 90), BODY)
        pygame.draw.rect(surf, scale_color(Col.CYAN, 0.8), BODY, 1)
        self._draw_marquee(surf)
        self._draw_window(surf)
        self._draw_keypad(surf)
        self._draw_tray(surf)

    def _draw_marquee(self, surf):
        surf.fill((8, 10, 28), MARQUEE)
        pygame.draw.rect(surf, scale_color(Col.MAGENTA, 0.6), MARQUEE, 1)
        font = get_font()
        text = "VEND-O-MATIC"
        total = font.size(text)[0] + len(text) - 1
        x = MARQUEE.centerx - total // 2
        colors = (Col.MAGENTA, Col.CYAN, Col.YELLOW, Col.GREEN)
        for i, ch in enumerate(text):
            glyph_color = colors[(i + int(self.time * 3)) % 4]
            if ch == "O" and int(self.time * 5) % 7 == i % 7:
                glyph_color = shade(glyph_color, -0.5)               # a tube that sputters
            img = font.render_glow(ch, glyph_color, scale_color(glyph_color, 0.4))
            surf.blit(img, (x, MARQUEE.y + 3))
            x += img.get_width() + 1

    def _draw_window(self, surf):
        surf.fill((10, 14, 40), WINDOW)
        pulse = 0.08 + 0.06 * math.sin(self.time * 2.4)
        glass = pygame.Surface(WINDOW.size)
        glass.fill(scale_color(Col.CYAN, pulse))
        sheen = int(self.time * 40) % (WINDOW.h + 40) - 20
        if 0 <= sheen < WINDOW.h:
            pygame.draw.line(glass, scale_color((200, 250, 255), 0.35), (0, sheen), (WINDOW.w, sheen))
        surf.blit(glass, WINDOW.topleft, special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(surf, scale_color(Col.CYAN, 0.6), WINDOW, 1)
        for i, entry in enumerate(self.entries):
            self._draw_cell(surf, i, entry)

    def _draw_cell(self, surf, i, entry):
        cell = self.cell_rect(i)
        definition = ITEM_REGISTRY.get(entry.item_id)
        full = self.service.blocked(entry) == "stack_full"
        affordable = self.service.can_afford(entry)
        selected = i == self.index
        p = self.purchase if self.purchase and self.purchase["index"] == i else None
        icon = item_icon(definition, 2)
        pos = icon.get_rect(midtop=(cell.centerx, cell.y + 5))
        if selected and self.shake > 0:
            pos.x += int(math.sin(self.shake * 70) * 2)
        hidden = p is not None and p["t"] >= DROP_AT              # the product has left its spot
        if not hidden:
            if not affordable or full:
                icon = icon.copy()
                icon.fill((90, 90, 110), special_flags=pygame.BLEND_RGB_MULT)
            surf.blit(icon, pos)
        elif p["t"] > BUY_LOCK:                                    # the shelf refills
            surf.blit(icon, pos)
        surf.fill((80, 90, 150), (cell.x + 2, cell.y + 40, cell.w - 4, 2))
        label = "FULL" if full else str(entry.cost)
        color = Col.TEXT_MUTED if full else (GOLD if affordable else Col.MAGENTA)
        w = get_font().size(label)[0] + (0 if full else 11)
        x = cell.centerx - w // 2
        if not full:
            surf.blit(item_icon_for_ticket(color), (x, cell.y + 45))
            x += 11
        draw_text(surf, label, (x, cell.y + 45), color)
        if selected:
            pulse = 0.65 + 0.35 * math.sin(self.time * 8)
            pygame.draw.rect(surf, scale_color(GOLD, pulse), cell.inflate(-2, -2), 1)
        self.hit(cell, lambda i=i: self._click_cell(i))
        if p is not None and DROP_AT <= p["t"] < DROP_AT + DROP_TIME:   # falling to the tray
            k = (p["t"] - DROP_AT) / DROP_TIME
            y = pos.y + (TRAY.y + 2 - pos.y) * k * k
            surf.blit(item_icon(definition, 2), (pos.x, int(y)))

    def _click_cell(self, i):
        if i == self.index:
            self.buy()
        else:
            self.select(i)

    def _draw_keypad(self, surf):
        surf.fill((50, 70, 150), KEYPAD)
        pygame.draw.rect(surf, scale_color(Col.CYAN, 0.5), KEYPAD, 1)
        surf.fill((6, 10, 24), LCD)
        entry = self.entry
        lcd_color = Col.MAGENTA if self.flash > 0 and int(self.time * 16) % 2 else (
            Col.GREEN if self.service.can_afford(entry) else Col.YELLOW)
        draw_text(surf, "COST", (LCD.centerx, LCD.y + 3), scale_color(lcd_color, 0.6), anchor="midtop")
        draw_text(surf, str(entry.cost), (LCD.centerx, LCD.y + 12), lcd_color, anchor="midtop")
        surf.fill((16, 20, 50), SLOT)
        pygame.draw.rect(surf, (90, 100, 170), SLOT, 1)
        draw_text(surf, "TICKET", (SLOT.centerx, SLOT.y - 9), Col.TEXT_MUTED, anchor="midtop")
        lit = int(self.time * 2) % 2
        surf.fill(Col.YELLOW if lit else shade(Col.YELLOW, -0.5), (SLOT.centerx - 7, SLOT.y + 13, 14, 3))
        if self.purchase and self.purchase["t"] < INSERT_TIME:          # the ticket slides into the slot
            k = self.purchase["t"] / INSERT_TIME
            ticket = item_icon_for_ticket(GOLD)
            surf.blit(ticket, (SLOT.centerx - 5, SLOT.y - 8 + int(k * 20)))
        for i in range(6):
            surf.fill(Col.CYAN if i % 2 else (160, 190, 255),
                      (KEYPAD.x + 11 + (i % 2) * 14, KEYPAD.bottom - 24 + (i // 2) * 7, 3, 3))

    def _draw_tray(self, surf):
        surf.fill((8, 8, 24), TRAY)
        pygame.draw.rect(surf, scale_color(Col.CYAN, 0.45), TRAY, 1)
        p = self.purchase
        if p is not None and p["t"] >= DROP_AT + DROP_TIME:
            definition = ITEM_REGISTRY.get(self.entries[p["index"]].item_id)
            rest = p["t"] - DROP_AT - DROP_TIME
            bob = 2 if rest < 0.1 else 0                           # one small bounce on landing
            icon = item_icon(definition, 2)
            if rest > BUY_LOCK - 0.3:
                icon = icon.copy()
                icon.set_alpha(max(0, int(255 * (1 - (rest - BUY_LOCK + 0.3) / 0.9))))
            surf.blit(icon, icon.get_rect(midbottom=(TRAY.centerx, TRAY.bottom - 2 - bob)))
        else:
            draw_text(surf, "PICK UP HERE", TRAY.center, scale_color(Col.TEXT_MUTED, 0.6), anchor="center")

    def _draw_details(self, surf):
        box = DETAIL
        surf.fill((14, 10, 34), box)
        pygame.draw.rect(surf, scale_color(Col.PURPLE, 0.9), box, 1)
        entry = self.entry
        definition = ITEM_REGISTRY.get(entry.item_id)
        pad, y = box.x + 8, box.y + 8
        icon = item_icon(definition, 2)
        surf.blit(icon, (pad, y))
        tx = pad + 38
        for line in wrap_text(definition.name, box.right - tx - 6):
            draw_text(surf, line, (tx, y), Col.TEXT, glow=scale_color(Col.CYAN, 0.4))
            y += LINE_H
        draw_text(surf, definition.rarity, (tx, y), Col.TEXT_MUTED)
        y = box.y + 50
        surf.blit(item_icon_for_ticket(GOLD), (pad, y + 3))
        draw_text(surf, f"{entry.cost} TICKETS", (pad + 13, y), GOLD, 2, glow=(120, 80, 10))
        y += 22
        owned = self.service.quantity(entry)
        draw_text(surf, f"YOU HAVE: {owned}/{NOVELTY_STACK}", (pad, y), Col.GREEN if owned else Col.TEXT_MUTED)
        y += LINE_H + 5
        for line in wrap_text(definition.description, box.w - 16):
            draw_text(surf, line, (pad, y), Col.TEXT_MUTED)
            y += LINE_H
        y += 4
        bag = self.owner.controls.label("menu") or "I"
        for line in wrap_text(f"USE IT FROM THE BAG ({bag})", box.w - 16):
            draw_text(surf, line, (pad, y), Col.CYAN)
            y += LINE_H
        blocked = self.service.blocked(entry)
        if blocked:
            status, color = "POCKETS FULL", Col.TEXT_MUTED
        elif self.service.can_afford(entry):
            status, color = "READY TO VEND", Col.GREEN
        else:
            status, color = f"NEED {entry.cost - self.profile.tickets} MORE", Col.MAGENTA
        draw_text(surf, fit_text(status, box.w - 16), (pad, box.bottom - 6 - LINE_H), color)

    # ------------------------------------------------------------ glitch + terminal
    def _draw_glitch(self, surf, t):
        frozen = self._frozen
        w, h = frozen.get_size()
        k = min(1.0, t / (GLITCH_TIME * 0.7))
        rng = random.Random(int(t * 24))           # a new look 24 times a second, whatever the frame rate
        surf.blit(frozen, (0, 0))
        y = 0
        while y < h:
            band = rng.randint(4, 18)
            if rng.random() < 0.2 + 0.55 * k:
                dx = rng.randint(-2 - int(34 * k), 2 + int(34 * k))
                rows = min(band, h - y)
                piece = frozen.subsurface((0, y, w, rows)).copy()
                surf.fill((0, 0, 0), (0, y, w, rows))
                surf.blit(piece, (dx, y))
            y += band
        for color, dx in (((255, 0, 60), 3), ((0, 255, 255), -3)):         # colour fringing
            tint = surf.copy()
            tint.fill(color, special_flags=pygame.BLEND_RGB_MULT)
            tint.fill(scale_color((255, 255, 255), 0.35), special_flags=pygame.BLEND_RGB_MULT)
            surf.blit(tint, (int(dx * k), 0), special_flags=pygame.BLEND_RGB_ADD)
        for _ in range(int(2 + 6 * k)):
            bar = pygame.Rect(0, rng.randrange(h), w, rng.randint(1, 5))
            surf.fill(scale_color(rng.choice((GREEN, Col.MAGENTA, Col.CYAN)), 0.3), bar,
                      special_flags=pygame.BLEND_RGB_ADD)
        if t > GLITCH_TIME - 0.25:                                          # collapse to black
            veil = pygame.Surface((w, h))
            veil.set_alpha(int(255 * (t - GLITCH_TIME + 0.25) / 0.25))
            surf.blit(veil, (0, 0))

    def _scanlines(self, size):
        if self._scan is None or self._scan.get_size() != size:
            self._scan = pygame.Surface(size, pygame.SRCALPHA)
            for y in range(0, size[1], 2):
                self._scan.fill((0, 0, 0, 90), (0, y, size[0], 1))
        return self._scan

    def _draw_terminal(self, surf, t):
        surf.fill((3, 6, 4))
        pygame.draw.rect(surf, scale_color(GREEN, 0.25), (8, 8, VIEW_W - 16, VIEW_H - 16), 1)
        shown = int(t * TYPE_RATE)
        x, y = 28, 54
        cursor = (x, y)
        for text, scale in TERMINAL_LINES:
            height = 7 * scale + 7
            part = text[:max(0, shown)]
            shown -= len(text) + 4                                           # a short beat between lines
            if part:
                rect = draw_text(surf, part, (x, y), GREEN, scale, glow=(8, 60, 22))
                cursor = (rect.right + 2, y)
            elif text == "" and shown >= 0:
                cursor = (x, y)
            y += height
        rng = random.Random(int(t * 16))
        blink = int(t * 2.2) % 2 == 0
        if blink and rng.random() > 0.15:                                    # a cursor that flickers
            surf.fill(GREEN, (cursor[0], cursor[1], 5, 8))
        if shown > 12:
            lit = 0.5 + 0.5 * math.sin(t * 3)
            draw_text(surf, "* UNUSUAL SECRET FOUND *" if self.secret["new"] else "* SECRET REVISITED *",
                      (VIEW_W // 2, VIEW_H - 46), scale_color(GREEN, 0.55 + 0.3 * lit), anchor="midtop")
            draw_text(surf, "ESC TO CLOSE", (VIEW_W // 2, VIEW_H - 30), scale_color(GREEN, 0.4), anchor="midtop")
        if rng.random() < 0.06:                                              # an occasional horizontal tear
            ty = rng.randrange(VIEW_H - 8)
            band = surf.subsurface((0, ty, VIEW_W, 6)).copy()
            surf.blit(band, (rng.randint(-5, 5), ty))
        surf.blit(self._scanlines(surf.get_size()), (0, 0))
