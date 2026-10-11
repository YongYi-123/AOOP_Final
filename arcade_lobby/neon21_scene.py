"""Neon21Scene: the NEON 21 table, shown full-screen from the Lucky Corner.

The scene only draws and routes input. Every rule is in blackjack.py and every
Token / Ticket movement is in neon21.py (Neon21Table), so nothing here can pay
twice: a key press just asks the table, which refuses anything illegal.

Three screens share one felt table:  BETTING (wager, payout currency, deal),
PLAYING (HIT / STAND / DOUBLE) and RESULT (banner, what was paid, next round).
Cards are dealt and flipped as a short scripted animation; the rules have
already settled by then, and the balance readout is held back until the result
banner appears so it never spoils the flip.

Controls follow the acting player's own scheme (the other player only watches):
    betting   left/right wager    up/down payout currency    E/ENTER/SPACE deal
    playing   left HIT   right STAND   up DOUBLE DOWN
    ESC       leave (twice mid-hand: the hand stands and settles)
Mouse clicks on the buttons work too.
"""
import math
import random

import pygame

from blackjack import Outcome, hand_value
from chance_game import draw_chance_backdrop
from controls import SOLO_CONTROLS
from daily_ui import token_icon
from font import get_font
from gfx import scale_color, shade
from neon21 import TICKETS, TOKENS, Neon21Table
from neon21_art import (CARD_H, CARD_W, CHIP, EMERALD, GOLD, card_surface,
                        chip_surface, chips_for, suit_icon)
from scene_base import BaseScene
from settings import (BACK_KEYS, CONFIRM_KEYS, NEON21_DAILY_TICKET_CAP,
                      NEON21_WAGERS, PIXEL_SCALE, VIEW_H, VIEW_W, Col)

FELT = (9, 58, 52)
FELT_DARK = (6, 40, 38)
RED = (255, 90, 100)
MIN_SPACING = 14            # a fanned card still shows its corner index
SHOE = (344, 32)
DEALER_BOUNDS = (24, SHOE[0] - 6)     # the dealer's row stops short of the shoe
PLAYER_BOUNDS = (24, VIEW_W - 24)
DEAL_STEP = 0.28            # seconds between cards
FLIP_TIME = 0.32
SLIDE_TIME = 0.22
AGAIN_DELAY = 0.7           # after the banner, before E can start the next hand
DEAL_ARM = 0.45             # after 'next hand', before DEAL works again
LEAVE_CONFIRM = 2.0         # seconds the second ESC is accepted for

BANNERS = {
    Outcome.BLACKJACK: ("BLACKJACK!", GOLD),
    Outcome.WIN: ("YOU WIN!", Col.GREEN),
    Outcome.DEALER_BUST: ("DEALER BUSTS!", Col.GREEN),
    Outcome.PUSH: ("PUSH", Col.CYAN),
    Outcome.LOSE: ("DEALER WINS", Col.MAGENTA),
    Outcome.BUST: ("BUST!", RED),
}


def unit(n, currency):
    word = "TOKEN" if currency == TOKENS else "TICKET"
    return f"{n} {word}" + ("" if n == 1 else "S")


class CardView:
    """One card on the table: where it came from and when it shows / flips."""

    def __init__(self, card, vis_at, hole=False):
        self.card, self.vis_at, self.hole = card, vis_at, hole
        self.flip_at = None             # when a face-down hole card turns over


class Neon21Scene(BaseScene):
    spectator_corner = "bottomright"
    spectator_offset = (4, 3)

    def __init__(self, game, player=None, rng=None, table=None):
        """player: the LocalPlayer at the cabinet - their profile pays and wins,
        the other player (if any) only watches."""
        super().__init__(game)
        self.player = player
        if player is not None:
            self.spectators = [p for p in game.session if p is not player]
        self.table = table or Neon21Table(self.profile, rng=rng)
        self.time = 0.0
        self.player_views, self.dealer_views = [], []
        self.busy_until = 0.0           # dealing / revealing: actions wait
        self.banner_at = None           # when the result banner appears
        self.frozen = None              # (tokens, tickets) shown until the banner
        self.leave_until = 0.0
        self.deal_ready_at = 0.0
        self.buttons = {}
        self.hover = None
        self.text_rects = []            # every text drawn last frame (for layout tests)
        self.card_rects = {"dealer": [], "player": []}
        self.particles = []
        self.rand = random.Random()
        self.icon = token_icon()
        self.notice = self.table.notice
        if self.table.round is not None:        # a round recovered after a restart
            self._show_all_now()

    # ------------------------------------------------------------ plumbing
    @property
    def profile(self):
        return self.player.profile if self.player else self.game.profile

    @property
    def controls(self):
        return self.player.controls if self.player else SOLO_CONTROLS

    def key_hint(self, action):
        return self.controls.label(action, limit=1) or "?"

    def on_exit(self):
        result = self.table.finish()       # leaving mid-hand: stand, settle once
        if result is not None and self.table.round is not None and self._left_mid_hand:
            self._tell_hub(result)

    _left_mid_hand = False

    def on_quit(self):
        self.table.finish()

    def _tell_hub(self, result):
        room = self.game.scenes.current
        if not hasattr(room, "resume_notice"):
            return
        title, color = BANNERS[result.outcome]
        lines = [(text, c) for text, c in self._detail_lines(result)]
        room.resume_notice = (title.rstrip("!"), lines, color)

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self._button_at(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            name = self._button_at(event.pos)
            if name:
                self._press(name)
        elif event.type == pygame.KEYDOWN:
            if self.player and not self.game.session.allows(self.player, event.key):
                return                      # the other player's keys do nothing here
            if event.key in BACK_KEYS:
                self._press("exit")
                return
            action = self.controls.action_for(event.key)
            if event.key in CONFIRM_KEYS or action in ("interact", "confirm"):
                self._press("confirm")
            elif action == "left":
                self._press("left")
            elif action == "right":
                self._press("right")
            elif action in ("up", "down"):
                self._press(action)

    def _button_at(self, pos):
        x, y = pos[0] // PIXEL_SCALE, pos[1] // PIXEL_SCALE
        for name, (rect, _label, enabled) in self.buttons.items():
            if enabled and rect.collidepoint(x, y):
                return name
        return None

    def _press(self, name):
        """One logical input. The table decides whether it is legal."""
        t = self.table
        if name == "exit":
            self._try_exit()
            return
        if t.phase == t.PLAYING:
            if self.time < self.busy_until:
                return
            if name in ("left", "hit"):
                self._act(t.hit)
            elif name in ("right", "stand"):
                self._act(t.stand)
            elif name in ("up", "double"):
                self._act(t.double)
            return
        if t.phase == t.DONE:
            if name in ("confirm", "next") and self._banner_visible() and \
                    self.time >= self.banner_at + AGAIN_DELAY:
                self._clear_table()
                t.next_round()
                self.deal_ready_at = self.time + DEAL_ARM      # a mashed key must not also deal
            return
        # IDLE: betting
        if name == "left":
            t.step_wager(-1)
        elif name == "right":
            t.step_wager(1)
        elif name in ("up", "down", "tokens", "tickets"):
            t.set_currency(name) if name in ("tokens", "tickets") else t.toggle_currency()
        elif name.startswith("chip"):
            t.set_wager(int(name[4:]))
        elif name in ("confirm", "deal") and self.time >= self.deal_ready_at:
            self._deal()

    def _try_exit(self):
        t = self.table
        if t.phase == t.PLAYING and not t.round.settled:
            if self.time < self.leave_until:
                self._left_mid_hand = True
                self.game.scenes.pop()          # on_exit settles the hand
            else:
                self.leave_until = self.time + LEAVE_CONFIRM
        else:
            self.game.scenes.pop()

    # ------------------------------------------------------------ actions + animation script
    def _snapshot(self):
        return self.profile.tokens, self.profile.tickets

    def _deal(self):
        snap = self._snapshot()
        if not self.table.deal():
            return
        self._clear_table()
        r, now = self.table.round, self.time
        self.player_views = [CardView(r.player[0], now), CardView(r.player[1], now + 2 * DEAL_STEP)]
        self.dealer_views = [CardView(r.dealer[0], now + DEAL_STEP),
                             CardView(r.dealer[1], now + 3 * DEAL_STEP, hole=True)]
        self._script(now + 4 * DEAL_STEP + SLIDE_TIME, snap)

    def _act(self, action):
        snap = self._snapshot()
        before = len(self.table.round.player)
        if not action():
            return
        r = self.table.round
        for card in r.player[len(self.player_views):]:
            self.player_views.append(CardView(card, self.time))
        self._script(self.time + SLIDE_TIME + (0.1 if len(r.player) > before else 0), snap)

    def _script(self, cursor, snap):
        """Queue the dealer's reveal and the banner after `cursor`. The state
        has already settled; this only decides when each thing appears."""
        r, t = self.table.round, self.table
        if not r.hole_hidden:                       # the dealer plays out
            hole = self.dealer_views[1]
            if hole.flip_at is None:
                hole.flip_at = cursor
                cursor += FLIP_TIME + 0.15
            for card in r.dealer[len(self.dealer_views):]:
                self.dealer_views.append(CardView(card, cursor))
                cursor += 0.5
        self.busy_until = cursor
        if t.phase == t.DONE:
            self.banner_at = cursor + 0.15
            self.frozen = snap
        self._pending_burst = t.phase == t.DONE

    def _show_all_now(self):
        """A recovered round: everything is already on the table."""
        r = self.table.round
        self.player_views = [CardView(c, -9) for c in r.player]
        self.dealer_views = [CardView(c, -9, hole=i == 1) for i, c in enumerate(r.dealer)]
        self.dealer_views[1].flip_at = -9
        self.banner_at, self.busy_until, self.frozen = -9, -9, None
        self._pending_burst = False

    def _clear_table(self):
        self.player_views, self.dealer_views = [], []
        self.banner_at, self.frozen, self.particles = None, None, []
        self._pending_burst = False

    def _banner_visible(self):
        return self.banner_at is not None and self.time >= self.banner_at

    _pending_burst = False

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        if self.frozen and self._banner_visible():
            self.frozen = None
        if self._pending_burst and self._banner_visible():
            self._pending_burst = False
            result = self.table.result
            if result and result.outcome in (Outcome.BLACKJACK, Outcome.WIN, Outcome.DEALER_BUST):
                self._burst(50 if result.outcome is Outcome.BLACKJACK else 28)
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 60 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]

    def _burst(self, n):
        for _ in range(n):
            side = self.rand.choice((self.rand.randint(14, 62), self.rand.randint(338, 386)))
            self.particles.append([side, self.rand.randint(26, 80), self.rand.uniform(-18, 18),
                                   self.rand.uniform(-60, -10), self.rand.uniform(1.0, 1.9),
                                   self.rand.choice((GOLD, EMERALD, Col.MAGENTA, Col.CYAN))])

    # ------------------------------------------------------------ drawing helpers
    def text(self, surf, s, x, y, color=Col.TEXT, scale=1, anchor="midtop", glow=None, max_w=None):
        font = get_font()
        while max_w and scale > 1 and font.size(s, scale)[0] > max_w:
            scale -= 1
        img = font.render_glow(s, color, glow, scale) if glow else font.render(s, color, scale)
        rect = img.get_rect(**{anchor: (x, y)})
        surf.blit(img, rect)
        self.text_rects.append(rect)
        return rect

    def button(self, surf, name, rect, label, enabled=True, color=Col.CYAN, hot=False):
        rect = pygame.Rect(rect)
        self.buttons[name] = (rect, label, enabled)
        hovered = enabled and self.hover == name
        base = color if enabled else scale_color(color, 0.3)
        fill = scale_color(color, 0.22 if (hot or hovered) else 0.12) if enabled else (16, 12, 30)
        pygame.draw.rect(surf, fill, rect, border_radius=3)
        pygame.draw.rect(surf, base, rect, 1 + (1 if hot and enabled else 0), border_radius=3)
        self.text(surf, label, rect.centerx, rect.centery - 3, Col.TEXT if enabled else Col.TEXT_MUTED,
                  anchor="midtop", max_w=rect.w - 6)

    def _balance(self):
        return self.frozen or self._snapshot()

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        self.text_rects = []
        self.card_rects = {"dealer": [], "player": []}
        self.buttons = {}
        t = self.table
        draw_chance_backdrop(surf, (8, 4, 22), (24, 6, 44), GOLD, self.time)
        self._draw_header(surf)
        self._draw_felt(surf)
        self._draw_hands(surf)
        self._draw_center(surf)
        self._draw_stake(surf)
        for x, y, _vx, _vy, life, color in ((p[0], p[1], 0, 0, p[4], p[5]) for p in self.particles):
            px, py = int(x), int(y)
            surf.fill(color, (px, py, 2, 2))
            if life > 0.6:                                                  # little four-point glints
                surf.fill(scale_color(color, 0.7), (px - 1, py, 4, 1))
                surf.fill(scale_color(color, 0.7), (px, py - 1, 1, 4))
        self._draw_panel(surf)

    def _draw_header(self, surf):
        tokens, tickets = self._balance()
        surf.blit(self.icon, (8, 6))
        self.text(surf, f"TOKENS {tokens}", 18, 6, Col.YELLOW, anchor="topleft")
        self.text(surf, f"TICKETS {tickets}", 18, 16, Col.MAGENTA, anchor="topleft")
        pulse = 0.75 + 0.25 * math.sin(self.time * 3)
        glow = scale_color(GOLD, 0.45 * pulse)
        r = self.text(surf, "NEON 21", VIEW_W // 2, 4, GOLD, 2, glow=glow)
        surf.blit(suit_icon("S", EMERALD, big=True), (r.left - 14, 6))
        surf.blit(suit_icon("H", RED, big=True), (r.right + 7, 6))
        if self.player and self.player.label:
            self.text(surf, self.player.tag, VIEW_W - 8, 6, Col.TEXT_MUTED, anchor="topright", max_w=120)

    def _draw_felt(self, surf):
        felt = pygame.Rect(12, 24, VIEW_W - 24, 208)
        pygame.draw.rect(surf, scale_color(GOLD, 0.35), felt.inflate(4, 4), border_radius=14)
        pygame.draw.rect(surf, FELT, felt, border_radius=12)
        pygame.draw.rect(surf, FELT_DARK, felt.inflate(-10, -10), 1, border_radius=9)
        pygame.draw.rect(surf, GOLD, felt, 1, border_radius=12)
        for x in range(felt.left + 18, felt.right - 12, 12):             # lit rail bulbs
            lit = int(self.time * 3 + x / 12) % 4 == 0
            surf.fill(GOLD if lit else scale_color(GOLD, 0.4), (x, felt.top, 2, 1))
        if self.table.phase == self.table.IDLE:
            self.text(surf, "NEON 21", VIEW_W // 2, 104, (14, 84, 72), 3)
            for views_y in (38, 146):                                       # empty card slots
                for i in range(2):
                    x = VIEW_W // 2 - 40 + i * 42
                    pygame.draw.rect(surf, (14, 84, 72), (x, views_y, CARD_W, CARD_H), 1, border_radius=3)
        for i in range(3):                                                  # the shoe
            surf.blit(card_surface(None, False), (SHOE[0] - i, SHOE[1] - i))

    def _spread(self, n, bounds):
        """(left x, spacing) for n cards inside bounds=(min_x, max_x). Cards are
        centred on the table with a 6px gap; a long hand fans out, each card
        overlapping the one before it by just enough to fit, so the rank/suit
        index in every card's top-left corner stays readable (spacing >= 14).
        The hand is shifted away from whatever limits it (the dealer's shoe)."""
        lo, hi = bounds
        spacing = min(CARD_W + 6, (hi - lo - CARD_W) // max(1, n - 1)) if n > 1 else 0
        spacing = max(spacing, MIN_SPACING)
        total = CARD_W + (n - 1) * spacing
        left = VIEW_W // 2 - total // 2
        left = max(lo, min(left, hi - total))
        return left, spacing

    def _draw_hand(self, surf, views, y, bounds, side):
        left, spacing = self._spread(len(views), bounds)
        shown = []
        for i, v in enumerate(views):
            age = self.time - v.vis_at
            if age < 0:
                continue
            x = left + i * spacing
            self.card_rects[side].append(pygame.Rect(x, y, CARD_W, CARD_H))
            k = min(1.0, age / SLIDE_TIME)
            k = 1 - (1 - k) ** 2
            px, py = SHOE[0] + (x - SHOE[0]) * k, SHOE[1] + (y - SHOE[1]) * k
            face_up, width = True, None
            if v.hole:
                flip = None if v.flip_at is None else (self.time - v.flip_at) / FLIP_TIME
                if flip is None or flip < 0:
                    face_up = False
                elif flip < 1:
                    face_up, width = flip >= 0.5, CARD_W * abs(1 - 2 * flip)
            img = card_surface(v.card, face_up, width)
            surf.blit(img, (int(px) + (CARD_W - img.get_width()) // 2, int(py)))
            if face_up and width is None:
                shown.append(v.card)
            elif v.hole and not face_up:
                pass
        return shown

    def _draw_hands(self, surf):
        dealer_cards = self._draw_hand(surf, self.dealer_views, 38, DEALER_BOUNDS, "dealer")
        player_cards = self._draw_hand(surf, self.player_views, 146, PLAYER_BOUNDS, "player")
        d_text = "DEALER"
        if dealer_cards:
            d_text += f" {hand_value(dealer_cards)[0]}"
        self.text(surf, d_text, VIEW_W // 2, 28, Col.TEXT, glow=(10, 40, 40))
        p_text = "YOU"
        if player_cards:
            value, soft = hand_value(player_cards)
            p_text += f" {value}" + (" SOFT" if soft and value < 21 else "")
        r = self.table.round
        color = RED if player_cards and hand_value(player_cards)[0] > 21 else Col.TEXT
        self.text(surf, p_text, VIEW_W // 2, 136, color, glow=(10, 40, 40))

    def _detail_lines(self, res):
        """(text, colour) lines describing exactly what was paid."""
        lines = []
        if res.outcome in (Outcome.LOSE, Outcome.BUST):
            lines.append((f"-{unit(res.stake, TOKENS)}", Col.TEXT_MUTED))
        elif res.outcome is Outcome.PUSH:
            lines.append((f"STAKE RETURNED: {unit(res.stake_returned, TOKENS)}", Col.CYAN))
        else:
            parts = []
            if res.tickets_paid:
                parts.append(f"+{unit(res.tickets_paid, TICKETS)}")
            if res.profit_tokens:
                parts.append(f"+{unit(res.profit_tokens, TOKENS)}")
            lines.append((" AND ".join(parts) + f"  (STAKE {res.stake_returned} BACK)", Col.GREEN))
            if res.capped:
                lines.append((f"DAILY TICKET CAP REACHED - {unit(res.profit_tokens, TOKENS)} PAID INSTEAD",
                              Col.YELLOW))
        return lines

    def _draw_center(self, surf):
        t = self.table
        cx = VIEW_W // 2
        if t.phase == t.IDLE:
            return
        if t.phase == t.DONE and self._banner_visible():
            res = t.result
            title, color = BANNERS[res.outcome]
            age = self.time - self.banner_at
            dy = 0 if age > 0.25 else int((0.25 - age) * 24)
            jitter = 1 if res.outcome is Outcome.BUST and age < 0.3 and int(age * 30) % 2 else 0
            self.text(surf, title, cx + jitter, 97 - dy, color, 2, glow=scale_color(color, 0.45), max_w=330)
            y = 114
            for line, c in self._detail_lines(res):
                self.text(surf, line, cx, y, c, max_w=330)
                y += 9
            if self.notice:
                self.text(surf, self.notice, cx, 126, Col.YELLOW, max_w=330)
        elif t.phase == t.PLAYING and self.time >= self.busy_until:
            blink = int(self.time * 2) % 2 == 0
            self.text(surf, "YOUR MOVE", cx, 108, GOLD if blink else scale_color(GOLD, 0.6))
        elif t.phase == t.PLAYING:
            self.text(surf, "DEALING..." if len(self.dealer_views) <= 2 else "DEALER PLAYS...", cx, 108,
                      Col.TEXT_MUTED)
        else:
            self.text(surf, "...", cx, 108, Col.TEXT_MUTED)

    def _draw_stake(self, surf):
        t = self.table
        stake = t.stake
        stack = chips_for(stake)
        x0, y0 = 22, 210
        for i, value in enumerate(stack[:8]):
            surf.blit(chip_surface(value), (x0 + (i // 4) * 9, y0 - (i % 4) * 2))
        label_x = x0 + 22 + (9 if len(stack) > 4 else 0)
        self.text(surf, f"STAKE {unit(stake, TOKENS)}", label_x, 208, Col.TEXT, anchor="topleft", max_w=150)
        cur = t.currency
        win, nat = t.preview(stake)
        if t.phase == t.PLAYING and t.round.doubled:
            self.text(surf, "DOUBLED DOWN", label_x, 217, GOLD, anchor="topleft", max_w=150)
        right = VIEW_W - 22
        self.text(surf, f"WIN PAYS +{unit(win, cur)}", right, 208, Col.GREEN, anchor="topright", max_w=190)
        self.text(surf, f"BLACKJACK +{unit(nat, cur)}", right, 217, GOLD, anchor="topright", max_w=190)

    # ------------------------------------------------------------ bottom panel
    def _draw_panel(self, surf):
        t = self.table
        panel = pygame.Rect(12, 236, VIEW_W - 24, 60)
        pygame.draw.rect(surf, (12, 8, 30), panel, border_radius=4)
        pygame.draw.rect(surf, scale_color(GOLD, 0.5), panel, 1, border_radius=4)
        if t.phase == t.IDLE:
            self._panel_betting(surf, panel)
        elif t.phase == t.PLAYING:
            self._panel_playing(surf, panel)
        else:
            self._panel_result(surf, panel)

    def _panel_betting(self, surf, panel):
        t, left = self.table, self.key_hint("left")
        self.text(surf, "WAGER", 22, 247, Col.TEXT_MUTED, anchor="topleft")
        tokens = self.profile.tokens
        for i, w in enumerate(NEON21_WAGERS):
            can = tokens >= w
            sel = w == t.wager
            x = 74 + i * 34
            self.buttons[f"chip{w}"] = (pygame.Rect(x - 4, 240, CHIP + 8, CHIP + 8), str(w), can)
            if sel:
                pygame.draw.circle(surf, GOLD, (x + 7, 249), 11, 1)
            surf.blit(chip_surface(w, dim=not can), (x, 242 - (2 if sel else 0)))
        self.text(surf, "PAID IN", 22, 266, Col.TEXT_MUTED, anchor="topleft")
        room = self.profile.neon21_ticket_room()
        self.button(surf, "tokens", (74, 262, 62, 14), "TOKENS", True, Col.YELLOW, t.currency == TOKENS)
        self.button(surf, "tickets", (142, 262, 62, 14), "TICKETS", True, Col.MAGENTA, t.currency == TICKETS)
        if t.currency == TICKETS:
            self.text(surf, f"ROOM TODAY {room}/{NEON21_DAILY_TICKET_CAP}", 212, 266,
                      Col.MAGENTA if room else Col.YELLOW, anchor="topleft", max_w=96)
        else:
            self.text(surf, "TOKEN WINS", 212, 266, Col.TEXT_MUTED, anchor="topleft", max_w=96)
        can = t.can_deal
        self.button(surf, "deal", (316, 242, 64, 26), "DEAL" if can else "NO TOKENS", can, EMERALD, True)
        hint = f"{left}/{self.key_hint('right')} WAGER  {self.key_hint('up')}/{self.key_hint('down')} PAID IN  " \
               f"{self.key_hint('interact')} DEAL  ESC EXIT"
        self.text(surf, hint, VIEW_W // 2, 279, Col.TEXT_MUTED, max_w=372)

    def _panel_playing(self, surf, panel):
        t, ready = self.table, self.time >= self.busy_until
        r = t.round
        live = ready and not r.settled
        self.button(surf, "hit", (28, 244, 104, 28), f"{self.key_hint('left')} HIT", live, Col.CYAN, live)
        self.button(surf, "stand", (148, 244, 104, 28), f"{self.key_hint('right')} STAND", live, Col.GREEN, live)
        dbl = live and t.can_double
        label = f"{self.key_hint('up')} DOUBLE +{r.bet}"
        self.button(surf, "double", (268, 244, 104, 28), label, dbl, GOLD, dbl)
        if self.time < self.leave_until:
            self.text(surf, "ESC AGAIN: HAND STANDS AND SETTLES", VIEW_W // 2, 279, Col.YELLOW, max_w=372)
        else:
            why = "" if live and not r.can_double or dbl or not live else "  (DOUBLE: NEED MORE TOKENS)"
            self.text(surf, "ESC: LEAVE (YOUR HAND STANDS)" + why, VIEW_W // 2, 279, Col.TEXT_MUTED, max_w=372)

    def _panel_result(self, surf, panel):
        ready = self._banner_visible() and self.time >= self.banner_at + AGAIN_DELAY
        again = self.table.profile.can_afford_tokens(min(NEON21_WAGERS))
        self.button(surf, "next", (96, 244, 100, 28), f"{self.key_hint('interact')} NEXT HAND",
                    ready, EMERALD, ready)
        self.button(surf, "exit", (204, 244, 100, 28), "ESC EXIT", True, Col.MAGENTA, False)
        if self._banner_visible() and not again:
            self.text(surf, "OUT OF TOKENS - EARN MORE IN THE ARCADE", VIEW_W // 2, 279, Col.YELLOW, max_w=372)
        else:
            self.text(surf, "WAGER AND PAYOUT CAN BE CHANGED BEFORE THE NEXT DEAL", VIEW_W // 2, 279,
                      Col.TEXT_MUTED, max_w=372)
