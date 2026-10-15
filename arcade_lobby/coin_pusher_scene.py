"""CoinPusherScene: NEON COIN PUSHER - KITTY FORTUNE, shown full-screen from the Lucky Corner.

The scene only draws and routes input. The physics is coin_pusher.py and every Token / Ticket
movement is coin_pusher_table.py, so nothing here can pay twice: a key press just asks the table.

Controls follow the acting player's own scheme (the other player only watches):
    left / right (hold)   slide the coin chute          (solo A/D or arrows, P1 A/D, P2 arrows)
    DROP                  spend 1 Token and drop a coin (the player's item key or interact key)
    pause key             pause / resume               (solo P, P1 I, P2 O)
    ESC                   leave (the board is saved; any coin in the air lands first)
"""
import math
import random

import pygame

import coin_pusher as cp
import coin_pusher_art as art
from controls import SOLO_CONTROLS
from daily_ui import token_icon
from font import get_font
from gfx import scale_color
from scene_base import BaseScene
from coin_pusher_table import CoinPusherTable
from settings import BACK_KEYS, COIN_PUSHER_DROP_COST, Col

LED_BG = (6, 4, 20)
IDLE_MESSAGE = "KITTY FORTUNE  -  MOVE THE CHUTE  -  DROP A COIN  -  WATCH THE PUSHER  "
ALERT_TIME = 1.4
LED_HOLD = 2.4
GOLD_TIME = 2.2


class CoinPusherScene(BaseScene):
    music_id = "lucky_corner"            # the Lucky Corner theme (no new music: the machine's own sounds carry it)
    spectator_corner = "topleft"
    spectator_offset = (4, 3)

    def __init__(self, game, player=None, table=None, rng=None):
        """player: the LocalPlayer at the cabinet - their profile pays and wins, the other player
        (if any) only watches."""
        super().__init__(game)
        self.player = player
        if player is not None:
            self.spectators = [p for p in game.session if p is not player]
        self.table = table or CoinPusherTable(self.profile)
        self.rand = rng or random.Random()
        self.time = 0.0                  # animation clock (stops while paused)
        self.held = set()                # chute keys physically held down
        self.icon = token_icon()
        self.text_rects = []
        self.particles = []              # [x, y, vx, vy, life, color]
        self.popups = []                 # [text, x, y, life, color]
        self.led_message, self.led_until = None, 0.0
        self.alert, self.alert_until = None, 0.0
        self.shake_until = 0.0
        self.gold_until = 0.0
        self.gold_text = ""
        self.token_flash = (0.0, Col.TEXT)
        self.last_tokens = self.profile.tokens
        self.hum_cycle = -1
        self.tray_coins = []             # recently collected coins resting in the tray: (x offset, kind)
        self.bg = art.build_background()
        self.cabinet = art.build_cabinet()
        self.front = art.build_front()
        self.glass = art.build_glass()
        self.notice = self.table.notice

    # ------------------------------------------------------------ plumbing
    @property
    def profile(self):
        return self.player.profile if self.player else self.game.profile

    @property
    def controls(self):
        return self.player.controls if self.player else SOLO_CONTROLS

    @property
    def paused(self):
        return self.table.paused

    def _sound(self, name):
        audio = getattr(self.game, "audio", None)
        if audio is not None:
            audio.play(name)

    def on_exit(self):
        self.table.close()

    def on_quit(self):
        self.table.close()

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type == pygame.KEYUP:
            self.held.discard(event.key)
            return
        if event.type != pygame.KEYDOWN or getattr(event, "repeat", False):
            return
        if self.player and not self.game.session.allows(self.player, event.key):
            return                           # the other player's keys do nothing here (they only watch)
        if event.key in BACK_KEYS:
            self.game.scenes.pop()
            return
        action = self.controls.action_for(event.key)
        if action in ("pause", "menu"):
            self.toggle_pause()
        elif action in ("left", "right"):
            self.held.add(event.key)
        elif action in ("interact", "item"):
            self.try_drop()

    def toggle_pause(self):
        if self.table.closed:
            return
        if self.table.paused:
            self.table.resume()
        else:
            self.held.clear()
            self.table.pause()

    def try_drop(self):
        """One DROP press: ask the table (it charges exactly once, or not at all)."""
        if self.table.drop():
            self.token_flash = (0.35, Col.CYAN)
            self._sound("coin_drop")
            return True
        reason = self.table.drop_block_reason()
        if reason == "NO TOKENS":
            self.alert, self.alert_until = "OUT OF TOKENS!", self.time + ALERT_TIME
            self.shake_until = self.time + 0.45
            self._sound("cancel")
        elif reason == "MACHINE FULL":
            self.alert, self.alert_until = "MACHINE FULL - WAIT", self.time + ALERT_TIME
            self._sound("cancel")
        return False

    def direction(self):
        d = 0
        for key in self.held:
            action = self.controls.action_for(key)
            d += -1 if action == "left" else 1 if action == "right" else 0
        return max(-1, min(1, d))

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.table.paused or self.table.closed:
            return
        self.time += dt
        self.table.move_chute(self.direction(), dt)
        events, payouts = self.table.update(dt)
        for e in events:
            if e.kind == "clink":
                self._sound("coin_clink")
        for p in payouts:
            self._on_payout(p)
        cycle = int(self.table.world.motor // cp.PUSH_PERIOD)
        if cycle != self.hum_cycle:
            self.hum_cycle = cycle
            self._sound("pusher_hum")
        tokens = self.profile.tokens
        if tokens != self.last_tokens:
            self.token_flash = (0.45, Col.GREEN if tokens > self.last_tokens else Col.CYAN)
            self.last_tokens = tokens
        self._update_fx(dt)

    def _on_payout(self, p):
        sx, sy, _ = art.project(min(cp.W, max(0.0, p.x)), cp.D)
        golden = p.kind == cp.GOLDEN
        self._sound("coin_tray")
        if golden:
            self._sound("coin_gold")
            self.gold_until, self.gold_text = self.time + GOLD_TIME, "GOLDEN CAT COIN!"
            self._burst(sx, sy - 6, 46, (art.GOLD, art.PINK, Col.CYAN, (255, 255, 255)))
        elif p.kind in (cp.SILVER, cp.MYSTERY) or p.tickets:
            self._sound("coin_win")
            self._burst(sx, sy - 4, 12, (art.GOLD, (255, 255, 255)))
        label = p.text + (" (DAILY CAP)" if p.capped else "")
        self.popups.append([p.text, sx, sy + 8, 1.1, art.GOLD if not golden else art.PINK])
        prefix = {cp.GOLDEN: "GOLDEN CAT! ", cp.SILVER: "SILVER! ", cp.MYSTERY: "MYSTERY! "}.get(p.kind, "")
        self.led_message, self.led_until = prefix + label, self.time + LED_HOLD
        self.tray_coins.append((sx - art.CX, p.kind))
        del self.tray_coins[:-14]

    def _burst(self, x, y, n, colors):
        for _ in range(n):
            self.particles.append([x + self.rand.uniform(-6, 6), y, self.rand.uniform(-60, 60),
                                   self.rand.uniform(-110, -20), self.rand.uniform(0.6, 1.4),
                                   self.rand.choice(colors)])

    def _update_fx(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 220 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for p in self.popups:
            p[2] -= 18 * dt
            p[3] -= dt
        self.popups = [p for p in self.popups if p[3] > 0]
        self.token_flash = (max(0.0, self.token_flash[0] - dt), self.token_flash[1])

    # ------------------------------------------------------------ drawing helpers
    def text(self, surf, s, x, y, color=Col.TEXT, scale=1, anchor="midtop", glow=None, max_w=None):
        font = get_font()
        while max_w and scale > 1 and font.size(s, scale)[0] > max_w:
            scale -= 1
        img = font.render_glow(s, color, glow, scale) if glow else font.render(s, color, scale)
        rect = img.get_rect(**{anchor: (int(x), int(y))})
        surf.blit(img, rect)
        self.text_rects.append(rect)
        return rect

    def controls_lines(self):
        """The player's real keys, as (keys, what) rows."""
        c = self.controls
        move = f"{c.label('left', limit=1) or '?'}/{c.label('right', limit=1) or '?'}"
        drop = "/".join(n for n in (c.label("item", limit=1), c.label("interact", limit=1)) if n) or "?"
        pause = c.label("pause", limit=1) or c.label("menu", limit=1) or "?"
        return [(move, "MOVE CHUTE"), (drop, "DROP COIN"), (pause, "PAUSE"), ("ESC", "LEAVE")]

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        self.text_rects = []
        surf.blit(self.bg, (0, 0))
        shake = (self.rand.randint(-1, 1), 0) if self.time < self.shake_until else (0, 0)
        stage = surf
        surf.blit(self.cabinet, shake)
        self._draw_marquee(surf)
        self._draw_led(surf)
        world = self.table.world
        art.draw_pusher(stage, world.face, self.time)
        self._draw_coins(stage, world)
        self._draw_chute(stage)
        surf.blit(self.front, (0, 0))
        self._draw_falling(surf, world)
        surf.blit(self.glass, (0, 0))
        self._draw_tray(surf)
        self._draw_panel(surf)
        if self.paused:
            self._draw_pause(surf)
        else:
            self._draw_fx(surf)

    # ---- marquee and LED
    def _draw_marquee(self, surf):
        glow = scale_color(Col.MAGENTA, 0.4 + 0.08 * math.sin(self.time * 3))
        self.text(surf, "NEON COIN PUSHER", art.CX, 11, Col.YELLOW, 2, glow=glow, max_w=240)
        self.text(surf, "KITTY FORTUNE", art.CX, 30, art.PINK, 1, glow=scale_color(art.PINK, 0.35))
        for i in range(24):                                                    # chase bulbs around the marquee
            lit = int(self.time * 7) % 4 == i % 4
            x = art.CABINET.left + 20 + i * 12
            surf.fill(Col.YELLOW if lit else scale_color(Col.MAGENTA, 0.6), (x, art.CABINET.top + 40, 3, 2))

    def _draw_led(self, surf):
        box = pygame.Rect(art.CX - 118, 48, 236, 12)
        pygame.draw.rect(surf, LED_BG, box)
        pygame.draw.rect(surf, scale_color(art.GLASS, 0.6), box, 1)
        message, color = IDLE_MESSAGE, Col.CYAN
        scroll = True
        if self.led_message and self.time < self.led_until:
            message, color, scroll = self.led_message, art.GOLD, False
        font = get_font()
        img = font.render(message, color)
        clip = surf.get_clip()
        surf.set_clip(box.inflate(-4, -2))
        if scroll:
            x = box.right - 4 - int((self.time * 34) % (img.get_width() + box.w))
            surf.blit(img, (x, box.y + 3))
        elif int(self.time * 6) % 8:
            surf.blit(img, img.get_rect(center=box.center))
        surf.set_clip(clip)
        self.text_rects.append(box)

    # ---- the stage
    def _draw_coins(self, surf, world):
        items = []
        for c in world.coins:
            items.append((c.y, "coin", c))
        for d in world.drops:
            items.append((cp.D + 1, "drop", d))
        items.sort(key=lambda it: it[0])
        golden = []
        for _, what, obj in items:
            if what == "coin":
                sx, sy, _ = art.project(obj.x, obj.y)
                d = art.coin_diameter(obj.y)
                sprite = art.coin_sprite(obj.kind, d)
                shadow = pygame.Rect(0, 0, sprite.get_width() - 2, 4)
                shadow.center = (sx, sy + sprite.get_height() // 2 - 1)
                pygame.draw.ellipse(surf, (6, 4, 22), shadow)
                surf.blit(sprite, sprite.get_rect(center=(sx, sy - 1)))
                if obj.kind == cp.GOLDEN:
                    golden.append((sx, sy))
            else:
                self._draw_drop(surf, obj)
        for i, (sx, sy) in enumerate(golden):                                  # a glint travelling over Golden Cat Coins
            if int(self.time * 3 + i) % 3 == 0:
                surf.fill((255, 255, 255), (int(sx) - 3 + int((self.time * 6) % 7), int(sy) - 4, 1, 1))
                surf.fill((255, 255, 255), (int(sx), int(sy) - 5, 1, 3))

    def _draw_drop(self, surf, d):
        k = max(0.0, min(1.0, (self.table.world.time - d.born) / cp.DROP_TIME))
        land_y = max(cp.DROP_Y, self.table.world.face + cp.R + 0.3)
        lx, ly, _ = art.project(d.x, land_y)
        fy = art.CHUTE_Y + 6
        sy = fy + (ly - fy) * k * k
        sprite = art.coin_sprite(d.kind, art.coin_diameter(land_y) * (0.75 + 0.25 * k))
        pygame.draw.ellipse(surf, (6, 4, 22), pygame.Rect(0, 0, sprite.get_width() - 2, 4).move(lx - sprite.get_width() // 2 + 1, ly + 3))
        surf.blit(sprite, sprite.get_rect(center=(lx, sy)))

    def _draw_chute(self, surf):
        x, _, _ = art.project(self.table.chute_x, 0)
        y = art.CHUTE_Y
        rail = pygame.Rect(art.CX - 118, y - 4, 236, 5)
        pygame.draw.rect(surf, (36, 28, 96), rail, border_radius=2)
        pygame.draw.line(surf, art.GLASS, (rail.left, rail.top), (rail.right, rail.top))
        blocked = self.table.drop_block_reason() == "NO TOKENS"
        ready = self.table.can_drop()
        color = (255, 80, 110) if blocked else Col.GREEN if ready else Col.YELLOW
        body = [(x - 8, y - 6), (x + 8, y - 6), (x + 4, y + 7), (x - 4, y + 7)]       # the chute funnel
        pygame.draw.polygon(surf, (110, 90, 220), body)
        pygame.draw.polygon(surf, art.GLASS, body, 1)
        surf.fill(color, (int(x) - 2, y + 6, 4, 2))
        pygame.draw.polygon(surf, art.PINK, [(x - 8, y - 6), (x - 5, y - 11), (x - 2, y - 6)])    # little cat ears on the chute
        pygame.draw.polygon(surf, art.PINK, [(x + 8, y - 6), (x + 5, y - 11), (x + 2, y - 6)])
        if ready and not self.paused:                                              # the aim line down to where it lands
            land_y = max(cp.DROP_Y, self.table.world.face + cp.R + 0.3)
            lx, ly, _ = art.project(self.table.chute_x, land_y)
            for yy in range(int(y + 9), int(ly), 5):
                surf.set_at((int(lx), yy), scale_color(Col.GREEN, 0.7))
            pygame.draw.circle(surf, scale_color(Col.GREEN, 0.8), (int(lx), int(ly)), 3, 1)

    def _draw_falling(self, surf, world):
        for f in world.falling:
            k = f.age / 0.6
            if f.side == 0:
                sx, sy, _ = art.project(f.x, cp.D)
                sy += 4 + 26 * k * k
                sprite = art.coin_sprite(f.kind, art.coin_diameter(cp.D) * (1 - 0.15 * k))
                surf.blit(sprite, sprite.get_rect(center=(sx, sy)))
            else:
                bx, by, _ = art.project(0 if f.side < 0 else cp.W, f.y)
                sx = bx + f.side * (6 + 26 * k)
                sy = by + 4 + 22 * k * k
                sprite = art.coin_sprite(f.kind, art.coin_diameter(f.y) * (1 - 0.4 * k))
                sprite = sprite.copy()
                sprite.set_alpha(int(255 * (1 - k)))
                surf.blit(sprite, sprite.get_rect(center=(sx, sy)))

    def _draw_tray(self, surf):
        for i, (dx, kind) in enumerate(self.tray_coins):
            sprite = art.coin_sprite(kind, 14)
            surf.blit(sprite, sprite.get_rect(center=(art.CX + dx * 0.9 + (i % 3 - 1) * 3, art.PY1 + 17 - (i % 2))))

    # ---- the panel under the stage
    def _draw_panel(self, surf):
        panel_y = art.PY1 + 32
        boxes = (pygame.Rect(46, panel_y, 100, 62), pygame.Rect(152, panel_y, 108, 62), pygame.Rect(266, panel_y, 88, 62))
        for box in boxes:
            pygame.draw.rect(surf, (10, 8, 34), box, border_radius=3)
            pygame.draw.rect(surf, scale_color(art.GLASS, 0.5), box, 1, border_radius=3)
        # tokens
        left = boxes[0]
        who = f"{self.player.tag} " if self.player and self.player.label else ""
        self.text(surf, f"{who}TOKENS", left.centerx, left.y + 5, Col.TEXT_MUTED, max_w=left.w - 6)
        timer, flash = self.token_flash
        color = flash if timer > 0 else Col.YELLOW
        rect = self.text(surf, f"{self.profile.tokens}", left.centerx + 5, left.y + 17, color, 2,
                         glow=scale_color(color, 0.3), max_w=left.w - 22)
        surf.blit(self.icon, self.icon.get_rect(midright=(rect.left - 4, rect.centery)))
        self.text(surf, f"COIN COST {COIN_PUSHER_DROP_COST} TOKEN", left.centerx, left.y + 38, Col.TEXT_MUTED, max_w=left.w - 6)
        self.text(surf, f"DROPPED {self.table.session_drops}", left.centerx, left.y + 49, Col.TEXT_MUTED, max_w=left.w - 6)
        # controls
        mid = boxes[1]
        for i, (keys, what) in enumerate(self.controls_lines()):
            y = mid.y + 5 + i * 14
            self.text(surf, keys, mid.x + 6, y, Col.CYAN, anchor="topleft", max_w=54)
            self.text(surf, what, mid.right - 6, y, Col.TEXT, anchor="topright", max_w=mid.w - 66)
        # winnings
        right = boxes[2]
        self.text(surf, "WON THIS VISIT", right.centerx, right.y + 5, Col.TEXT_MUTED, max_w=right.w - 6)
        self.text(surf, f"{self.table.session_tickets}", right.centerx, right.y + 17, art.PINK, 2,
                  glow=scale_color(art.PINK, 0.3))
        self.text(surf, "TICKETS", right.centerx, right.y + 34, art.PINK)
        self.text(surf, f"+{self.table.session_tokens} TOKENS", right.centerx, right.y + 47, Col.YELLOW, max_w=right.w - 6)

    # ---- effects
    def _draw_fx(self, surf):
        for x, y, vx, vy, life, color in self.particles:
            surf.fill(color, (int(x), int(y), 2, 2))
        for text, x, y, life, color in self.popups:
            self.text(surf, text, x, y, color, glow=scale_color(color, 0.3))
        if self.alert and self.time < self.alert_until:
            box = pygame.Rect(0, 0, 190, 30)
            box.center = (art.CX, 128)
            pygame.draw.rect(surf, (40, 6, 24), box, border_radius=4)
            pygame.draw.rect(surf, (255, 80, 110), box, 2, border_radius=4)
            self.text(surf, self.alert, box.centerx, box.y + 6, (255, 120, 150), 1)
            self.text(surf, "EARN TOKENS IN THE ARCADE", box.centerx, box.y + 17, Col.TEXT_MUTED, max_w=box.w - 8)
        if self.time < self.gold_until:
            k = (self.gold_until - self.time) / GOLD_TIME
            flash = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            flash.fill((255, 220, 120, int(46 * k)))
            surf.blit(flash, (0, 0))
            self.text(surf, self.gold_text, art.CX, 96 + int(math.sin(self.time * 9) * 2), art.GOLD, 2,
                      glow=scale_color(art.PINK, 0.6), max_w=250)
            pygame.draw.rect(surf, art.PINK if int(self.time * 10) % 2 else art.GOLD, art.CABINET, 2, border_radius=6)

    def _draw_pause(self, surf):
        veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        veil.fill((4, 2, 20, 170))
        surf.blit(veil, (0, 0))
        box = pygame.Rect(0, 0, 200, 66)
        box.center = (art.CX, 128)
        pygame.draw.rect(surf, (16, 10, 48), box, border_radius=4)
        pygame.draw.rect(surf, art.GLASS, box, 1, border_radius=4)
        self.text(surf, "PAUSED", box.centerx, box.y + 8, Col.YELLOW, 2)
        pause_key = self.controls.label("pause", limit=1) or self.controls.label("menu", limit=1)
        self.text(surf, f"{pause_key}: RESUME", box.centerx, box.y + 30, Col.TEXT)
        self.text(surf, "ESC: LEAVE (BOARD IS SAVED)", box.centerx, box.y + 43, Col.TEXT_MUTED, max_w=box.w - 8)
