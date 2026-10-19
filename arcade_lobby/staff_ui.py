"""The BROKEN CAT-CADE's screens: a fake maintenance terminal, and behind its password MOCHI'S STAFF PANEL.

One MenuScene owned by the player who pressed the use key: only their profile is ever paid, their own keys
(and the shared ESC) drive the panel, and the room underneath is paused while it is up (it is a pushed scene,
so no hub interaction can happen meanwhile).

Typing: while the password box is up the scene says `captures_text`, so the Game does not let the keyboard
double as shortcuts (an M typed into the box would otherwise mute the audio). Letters and digits are accepted
from the shared keyboard - there is no other way to type a word on one keyboard in a two-player session - but
ENTER only submits for the player who owns it, TAB submits for anyone, and nothing typed can buy, move or
grant anything. The panel's buttons answer only to the owner.
"""
import math

import pygame

from font import get_font
from gfx import scale_color, shade
from menu_kit import FRAME, MenuScene
from settings import BACK_KEYS, VIEW_H, VIEW_W, Col
from staff_cheat import (BALANCE_CAP, GRANT_AMOUNTS, HINT_LINE, MAX_INPUT, PasswordEntry, StaffService)
from player_profile import PlayerProfile
from ui import draw_text, neon_panel, wrap_text

NAME = "CAT-CADE 404"
PANEL_TITLE = "MOCHI'S STAFF PANEL"
PANEL_SUBTITLE = "EMPLOYEE STATUS: QUESTIONABLE"
PASSWORD_PHASE, PANEL_PHASE = "password", "panel"
ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)
ACTION_LOCK = 0.3           # seconds after a press in which the panel ignores the next one
BANNER_TIME = 1.6
DUCK = 0.55                 # the room music dips a little while the maintenance screen is up
TERMINAL = (96, 255, 170)
TERMINAL_DIM = (40, 120, 90)

DANCE, EXIT = "dance", "exit"
# the panel's buttons, row by row: (kind, currency, amount)
ROWS = (
    tuple((PlayerProfile.TOKEN, a) for a in GRANT_AMOUNTS),
    tuple((PlayerProfile.TICKET, a) for a in GRANT_AMOUNTS),
    ((DANCE, None),),
    ((EXIT, None),),
)
UNITS = {PlayerProfile.TOKEN: "TOKENS", PlayerProfile.TICKET: "TICKETS"}
COLORS = {PlayerProfile.TOKEN: Col.YELLOW, PlayerProfile.TICKET: Col.CYAN}


class MaintenanceScene(MenuScene):
    title = PANEL_TITLE
    accent = (180, 140, 255)
    glow = Col.MAGENTA

    def __init__(self, game, owner, room=None):
        super().__init__(game, owner)
        self.room = room                    # the hub room (for ALL CATS DANCE); None in isolation
        self.service = StaffService(owner.profile)
        self.entry = PasswordEntry()
        self.phase = PASSWORD_PHASE
        self.sel = [0, 0]                   # (row, column) on the panel
        self.lock = 0.0
        self._latched = False               # the use key is still down since the last press
        self.closing = False
        self.music_duck = None
        self.shake = 0.0
        self.banner = None                  # {"text", "color", "t"} - the last grant's confirmation
        self.flash = {}                     # (row, col) -> seconds of button glow left
        self.granted = []                   # [(currency, added)] this visit (display / tests)
        self.dance_started = False
        self.hints = ("TYPE", "ENTER OK", "BACKSPACE ERASE", "ESC LEAVE")

    # ------------------------------------------------------------ lifecycle
    @property
    def captures_text(self):
        """Read by Game.step: while True the keyboard types, so global shortcuts (mute ...) stand aside."""
        return self.phase == PASSWORD_PHASE and not self.closing

    def on_enter(self):
        self.music_duck = DUCK
        self.play("glitch")

    def on_exit(self):
        self.music_duck = None
        self.entry.clear()
        self._latched = False

    def close(self):
        if not self.closing:
            self.closing = True
            self.music_duck = None
            super().close()

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if self.closing:
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.input.feed(event)
            self._latched = False
            return
        if event.type == pygame.KEYUP:
            self.input.feed(event)
            if self.owner.controls.action_for(event.key) == "interact" or event.key in ENTER_KEYS:
                self._latched = False
            return
        if self.phase == PASSWORD_PHASE:
            self._password_event(event)
        else:
            super().handle_event(event)

    def _password_event(self, event):
        if event.type != pygame.KEYDOWN:            # (no mouse here)
            return
        key = event.key
        if key in BACK_KEYS:
            self.close()
        elif key == pygame.K_BACKSPACE:
            if self.entry.backspace():
                self.play("vend_select")
        elif key == pygame.K_DELETE:
            if self.entry.clear():
                self.play("cancel")
        elif key == pygame.K_TAB or (key in ENTER_KEYS and self.owner.controls.owns(key)):
            self._submit(key)
        else:
            ch = PasswordEntry.char_for(event)
            if ch and self.entry.type(ch):
                self.play("vend_select")

    def _submit(self, key=None):
        if not self.entry.text:
            return
        if self.entry.submit():
            self.phase = PANEL_PHASE
            self._latched = key in ENTER_KEYS       # the ENTER that opened the panel must not also press a button
            self.lock = ACTION_LOCK + 0.1
            self.hints = ("ARROWS/WASD SELECT", f"{self.owner.controls.label('interact') or 'E'} OK", "ESC EXIT")
            self.play("coin_gold")
            self.say("WELCOME BACK, EMPLOYEE.", Col.GREEN, 3.0)
        else:
            self.shake = 0.4
            self.play("cancel")
            self.play("glitch")

    def on_action(self, action):
        if self.phase != PANEL_PHASE or self.closing:
            return
        rows = ROWS
        row, col = self.sel
        if action == "back":
            self.close()
        elif action == "up":
            self._select((row - 1) % len(rows), col)
        elif action == "down":
            self._select((row + 1) % len(rows), col)
        elif action == "left":
            self._select(row, (col - 1) % len(rows[row]))
        elif action == "right":
            self._select(row, (col + 1) % len(rows[row]))
        elif action == "interact":
            if self._latched or self.lock > 0:      # a held key, or a double tap: one press is one action
                return
            self._latched = True
            self._press(row, col)

    def _select(self, row, col):
        col = min(col, len(ROWS[row]) - 1)
        if [row, col] != self.sel:
            self.sel = [row, col]
            self.play("vend_select")

    def _click(self, event):
        if self.phase == PANEL_PHASE and not self.closing:
            super()._click(event)

    def _click_button(self, row, col):
        self.sel = [row, col]
        if self.lock > 0 or self.closing:
            return
        self._press(row, col)

    def _press(self, row, col):
        kind, amount = ROWS[row][col]
        self.lock = ACTION_LOCK
        if kind == EXIT:
            self.play("cancel")
            self.close()
        elif kind == DANCE:
            self._dance()
        else:
            self._grant(row, col, kind, amount)

    # ------------------------------------------------------------ actions
    def _grant(self, row, col, currency, amount):
        result = self.service.grant(currency, amount)
        unit = UNITS[currency]
        if result.code == "invalid":
            self.play("cancel")
            return
        if result.code == "full":
            self.play("cancel")
            self.say(f"{unit} ARE FULL ({BALANCE_CAP}). MOCHI SAYS NO.", Col.MAGENTA)
            return
        self.granted.append((currency, result.added))
        self.flash[(row, col)] = 0.6
        self.play("token" if currency == PlayerProfile.TOKEN else "ticket")
        color = COLORS[currency]
        text = f"+{result.added} {unit}"
        self.banner = {"text": text, "color": color, "t": 0.0}
        tail = "  (WALLET FULL)" if result.code == "partial" else ""
        self.say(f"GRANTED {text}!  NOW {self.service.balance(currency)}{tail}", Col.GREEN, 3.0)

    def _dance(self):
        colony = getattr(self.room, "cats", None)
        if colony is None or not colony.start_dance():
            self.play("cancel")
            self.say("NO CATS AVAILABLE FOR DANCING.", Col.MAGENTA)
            return
        self.dance_started = True
        self.play("meow")
        self.close()                                # so you can watch them

    # ------------------------------------------------------------ update
    def update(self, dt):
        super().update(dt)
        self.lock = max(0.0, self.lock - dt)
        self.shake = max(0.0, self.shake - dt)
        for key in list(self.flash):
            self.flash[key] -= dt
            if self.flash[key] <= 0:
                del self.flash[key]
        if self.banner is not None:
            self.banner["t"] += dt
            if self.banner["t"] > BANNER_TIME:
                self.banner = None

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        self._hit = []
        if self.phase == PASSWORD_PHASE:
            self._draw_terminal(surf)
        else:
            self._draw_panel(surf)

    # the fake maintenance terminal
    def _draw_terminal(self, surf):
        t = self.time
        surf.fill((4, 8, 14))
        for y in range(0, VIEW_H, 2):
            pygame.draw.line(surf, (7, 14, 22), (0, y), (VIEW_W, y))
        pygame.draw.rect(surf, TERMINAL_DIM, FRAME.inflate(-8, -8), 1)
        glitch = 1 if (t % 3.4) < 0.12 else 0                      # the odd torn frame
        draw_text(surf, NAME, (22 + glitch * 3, 24), TERMINAL, 2, glow=TERMINAL_DIM)
        draw_text(surf, "ERROR: OPERATOR MISSING", (22, 46), (255, 100, 120))
        y = 66
        for line in wrap_text("THIS MACHINE HAS NOT BEEN SERVICED IN 9999 DAYS.", VIEW_W - 60):
            draw_text(surf, line, (22, y), TERMINAL)
            y += 11
        draw_text(surf, "ENTER MAINTENANCE PASSWORD:", (22, 106), TERMINAL)
        box = pygame.Rect(22 + (int(math.sin(t * 60) * 3) if self.shake > 0 else 0), 122, 20 + MAX_INPUT * 12, 20)
        surf.fill((6, 22, 24), box)
        pygame.draw.rect(surf, (255, 100, 120) if self.shake > 0 else TERMINAL, box, 1)
        shown = self.entry.text + ("_" if int(t * 2.2) % 2 == 0 else " ")
        draw_text(surf, shown, (box.x + 6, box.y + 4), TERMINAL, 2)
        if self.shake > 0 and self.entry.attempts:
            for i, line in enumerate(wrap_text(self.entry.wrong_line(), VIEW_W - 60)):
                draw_text(surf, line, (22, 150 + i * 11), (255, 100, 120))
        if self.entry.wants_hint:
            draw_text(surf, HINT_LINE, (22, 184), TERMINAL_DIM)
        draw_text(surf, "TYPE   BACKSPACE ERASE   DEL CLEAR   ENTER OR TAB OK   ESC LEAVE",
                  (VIEW_W // 2, VIEW_H - 22), TERMINAL_DIM, anchor="midtop")
        if (t % 5.0) < 0.1:                                         # a flicker across the whole tube
            surf.fill((20, 30, 40), special_flags=pygame.BLEND_RGB_ADD)

    # MOCHI'S STAFF PANEL
    def draw_balance(self, surf):
        right = FRAME.right - 10
        for i, currency in enumerate((PlayerProfile.TOKEN, PlayerProfile.TICKET)):
            value = self.service.balance(currency)
            draw_text(surf, f"{UNITS[currency]} {value}", (right, 12 + i * 11), COLORS[currency], anchor="topright")

    def _draw_panel(self, surf):
        self.draw_frame(surf, PANEL_TITLE, PANEL_SUBTITLE)
        draw_text(surf, self.owner.tag, (16, 44), self.owner.avatar.look.accent if self.owner.label else Col.CYAN)
        top = 62
        for r, row in enumerate(ROWS[:2]):
            currency = row[0][0]
            y = top + r * 40
            draw_text(surf, f"ADD {UNITS[currency]}", (16, y + 7), COLORS[currency])
            for c, (_, amount) in enumerate(row):
                rect = pygame.Rect(120 + c * 86, y, 80, 28)
                self._button(surf, rect, f"+{amount}", (r, c), COLORS[currency])
        self._button(surf, pygame.Rect(16, 142, 184, 24), "ALL CATS DANCE", (2, 0), Col.MAGENTA)
        self._button(surf, pygame.Rect(16, 172, 184, 20), "EXIT", (3, 0), Col.TEXT_MUTED)
        draw_text(surf, f"WALLET LIMIT {BALANCE_CAP}", (VIEW_W - 16, 150), Col.TEXT_MUTED, anchor="topright")
        draw_text(surf, "STAFF GRANTS DO NOT COUNT TOWARD STATS OR DAILY LIMITS.", (16, 198), Col.TEXT_MUTED)
        if self.message_time > 0:
            draw_text(surf, self.message, (16, 210), self.message_color)
        hint = "   ".join(self.hints)
        draw_text(surf, hint, (VIEW_W // 2, VIEW_H - 24), Col.TEXT_MUTED, anchor="midtop")
        if self.banner is not None:
            self._draw_banner(surf)

    def _button(self, surf, rect, label, index, color):
        selected = self.sel == list(index)
        glow = self.flash.get(index, 0.0)
        fill = scale_color(color, 0.32 + (0.5 if glow else 0.0)) if selected else (22, 15, 46)
        surf.fill(fill, rect)
        edge = shade(color, 0.4) if selected else scale_color(color, 0.5)
        pygame.draw.rect(surf, edge, rect, 1)
        if selected:
            pulse = 0.65 + 0.35 * math.sin(self.time * 8)
            pygame.draw.rect(surf, scale_color(color, pulse), rect.inflate(2, 2), 1)
        size = 2 if rect.h >= 24 and len(label) < 8 else 1
        draw_text(surf, label, rect.center, Col.TEXT if selected else color, size, anchor="center")
        self.hit(rect, lambda i=index: self._click_button(*i))

    def _draw_banner(self, surf):
        b = self.banner
        k = b["t"] / BANNER_TIME
        text = b["text"]
        w = get_font().size(text, 3)[0] + 28
        panel = neon_panel(w, 40, b["color"], Col.PURPLE, int(235 * (1 - k ** 3))).copy()
        rect = panel.get_rect(center=(VIEW_W // 2, 248 - int(k * 12)))
        surf.blit(panel, rect)
        draw_text(surf, text, rect.center, b["color"], 3, anchor="center", glow=scale_color(b["color"], 0.4))
