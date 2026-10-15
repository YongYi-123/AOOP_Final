"""PinballScene: LUCKY CAT PINBALL, shown full-screen from the Lucky Corner.

The scene only draws and routes input. The physics is pinball.py and every Token / Ticket
movement is pinball_table.py, so nothing here can pay twice: a key press just asks the table.

Controls follow the acting player's own scheme (the other player only watches):
    left / right (hold)   left / right flipper     (solo A/D or arrows, P1 A/D, P2 arrows)
    launch (hold, release) pull the plunger back, let go to launch; also starts a run (1 Token)
                          (the player's item key or interact key: SPACE/E, SPACE/E, RSHIFT/ENTER)
    pause key             pause / resume           (solo P, P1 I, P2 O)
    ESC                   leave (a run in progress is cashed out first; ESC while playing pauses first)
"""
import math
import random

import pygame

import pinball as pb
import pinball_art as art
from controls import SOLO_CONTROLS
from daily_ui import token_icon
from font import get_font
from gfx import scale_color
from pinball_table import PinballTable
from scene_base import BaseScene
from settings import BACK_KEYS, PINBALL_MAX_TICKETS, PINBALL_POINTS_PER_TICKET, PINBALL_RUN_COST, Col

ALERT_TIME = 1.4
TICKER_HOLD = 2.2
TRAIL = 7


class PinballScene(BaseScene):
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
        self.table = table or PinballTable(self.profile)
        self.rand = rng or random.Random()
        self.time = 0.0                  # animation clock (stops while paused)
        self.held = set()                # flipper keys physically held down
        self.launch_held = set()         # launch keys physically held down (for the plunger)
        self.icon = token_icon()
        self.text_rects = []
        self.particles = []              # [x, y, vx, vy, life, color]
        self.popups = []                 # [text, x, y, life, color]
        self.trail = []
        self.ticker, self.ticker_until = None, 0.0
        self.alert, self.alert_until = None, 0.0
        self.shake_until = 0.0
        self.drain_flash = 0.0
        self.confirm_leave = False       # ESC during a run pauses and asks; a second ESC leaves
        self.last_tokens = self.profile.tokens
        self.token_flash = (0.0, Col.TEXT)
        self.bg = art.build_background()
        self.cabinet = art.build_cabinet()
        self.felt = art.build_table()
        self.font = get_font()
        self.result_seen = self.table.result            # a recovered run is shown, not replayed

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
            self._key_up(event.key)
            return
        if event.type != pygame.KEYDOWN or getattr(event, "repeat", False):
            return
        if self.player and not self.game.session.allows(self.player, event.key):
            return                           # the other player's keys do nothing here (they only watch)
        if event.key in BACK_KEYS:
            self._escape()
            return
        action = self.controls.action_for(event.key)
        if action in ("pause", "menu"):
            self.toggle_pause()
        elif action in ("left", "right"):
            self.held.add(event.key)
            self._apply_flippers()
        elif action in ("interact", "item"):
            self._launch_key_down(event.key)

    def _key_up(self, key):
        if key in self.held:
            self.held.discard(key)
            self._apply_flippers()
        if key in self.launch_held:
            self.launch_held.discard(key)
            if not self.launch_held:
                self._plunger(False)

    def _escape(self):
        if self.table.live and not self.paused and not self.confirm_leave:
            self.confirm_leave = True
            self.toggle_pause()
            return
        self.game.scenes.pop()

    def toggle_pause(self):
        if self.table.closed:
            return
        if self.table.paused:
            self.confirm_leave = False
            self.table.resume()
            self._apply_flippers()
        else:
            self.table.pause()

    def _launch_key_down(self, key):
        if self.paused:
            return
        if not self.table.live:
            self.try_start()                 # this press only starts the run; it does not pull the plunger
            return
        self.launch_held.add(key)
        self._plunger(True)

    def _plunger(self, held):
        for e in self.table.hold_plunger(held):
            self._on_event(e)

    def _apply_flippers(self):
        left = right = False
        for key in self.held:
            action = self.controls.action_for(key)
            left |= action == "left"
            right |= action == "right"
        for e in self.table.set_flippers(left, right):
            self._on_event(e)

    def try_start(self):
        """One START press: ask the table (it charges exactly once, or not at all)."""
        if self.table.start():
            self.token_flash = (0.35, Col.CYAN)
            self.result_seen = None
            self.held.clear()
            self._sound("machine")
            self._ticker("BALL 1  -  HOLD LAUNCH, RELEASE TO SHOOT")
            return True
        reason = self.table.start_block_reason()
        if reason == "NO TOKENS":
            self.alert, self.alert_until = "OUT OF TOKENS!", self.time + ALERT_TIME
            self.shake_until = self.time + 0.45
            self._sound("cancel")
        return False

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.table.paused or self.table.closed:
            return
        self.time += dt
        for e in self.table.update(dt):
            self._on_event(e)
        w = self.table.world
        if w.phase == "play" and w.captured <= 0:
            self.trail.append((w.bx, w.by))
            del self.trail[:-TRAIL]
        else:
            self.trail.clear()
        tokens = self.profile.tokens
        if tokens != self.last_tokens:
            self.token_flash = (0.45, Col.GREEN if tokens > self.last_tokens else Col.CYAN)
            self.last_tokens = tokens
        self._update_fx(dt)
        if self.table.result is not self.result_seen and self.table.state == "result":
            self.result_seen = self.table.result
            self._on_result(self.table.result)

    def _ticker(self, text):
        self.ticker, self.ticker_until = text, self.time + TICKER_HOLD

    def _popup(self, text, x, y, color):
        sx, sy = art.P(x, y)
        self.popups.append([text, sx, sy, 0.9, color])

    def _on_event(self, e):
        k = e.kind
        if k == "launch":
            self._sound("pin_launch")
            self._burst(*art.P(e.x, e.y), 8, (Col.CYAN, (255, 255, 255)), 0.5)
        elif k == "flipper":
            self._sound("pin_flipper")
        elif k == "bumper":
            self._sound("pin_bumper")
            self._popup(str(e.points), e.x, e.y - 12, art.GOLD if e.points > 100 else (255, 190, 235))
            self._burst(*art.P(e.x, e.y), 7, (art.PINK, (255, 255, 255), art.GOLD if e.points > 100 else Col.CYAN))
        elif k == "rail":
            self._sound("pin_rail")
        elif k == "lane":
            self._sound("pin_rail")
            self._popup(str(e.points), e.x, e.y + 10, Col.CYAN)
        elif k == "lanes_done":
            self._sound("pin_bonus")
            self._ticker(f"LANES COMPLETE  -  BONUS X{e.extra}  -  SCOOP LIT")
            self._popup(f"+{e.points}", e.x, e.y + 14, art.GOLD)
        elif k == "target":
            self._sound("pin_target")
            self._popup(str(e.points), e.x - 22, e.y, art.GOLD)
        elif k == "cat":
            self._sound("pin_bonus")
            self._ticker(f"C-A-T COMPLETE!  +{e.points}")
            self._popup(f"+{e.points}", e.x, e.y - 16, art.PINK)
            self._burst(*art.P(e.x, e.y), 30, (art.GOLD, art.PINK, (255, 255, 255)), 1.2)
        elif k == "lucky_start":
            self._ticker("LUCKY CAT MODE!  BUMPERS PAY MORE")
            self.shake_until = self.time + 0.25
        elif k == "lucky_end":
            self._ticker("LUCKY CAT MODE OVER")
        elif k == "scoop":
            self._sound("pin_scoop")
            self._popup(f"+{e.points}", e.x + 10, e.y - 8, art.GOLD)
            self._ticker("SCOOP!" if e.points > pb.SCOOP_UNLIT else "SCOOP  -  DARK UNTIL LANES / CAT")
        elif k == "eject":
            self._sound("pin_scoop")
        elif k == "drain":
            self._sound("pin_drain")
            self.drain_flash = 0.9
            self.shake_until = self.time + 0.3
            self._ticker(f"BALL {e.extra} LOST")
        elif k == "ball_start":
            if e.extra > 1:
                self._ticker(f"BALL {e.extra}  -  HOLD LAUNCH, RELEASE TO SHOOT")

    def _on_result(self, r):
        self._sound("ticket" if r.tickets else "confirm")
        if r.new_best and r.score:
            self._sound("pin_bonus")
        self._burst(art.CX, 140, 30 if r.tickets else 8, (art.GOLD, art.PINK, Col.CYAN), 1.3)

    def _burst(self, x, y, n, colors, life=0.8):
        for _ in range(n):
            self.particles.append([x + self.rand.uniform(-3, 3), y, self.rand.uniform(-70, 70),
                                   self.rand.uniform(-110, 20), self.rand.uniform(0.3, 1.0) * life + 0.2,
                                   self.rand.choice(colors)])

    def _update_fx(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 240 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for p in self.popups:
            p[2] -= 22 * dt
            p[3] -= dt
        self.popups = [p for p in self.popups if p[3] > 0]
        self.token_flash = (max(0.0, self.token_flash[0] - dt), self.token_flash[1])
        self.drain_flash = max(0.0, self.drain_flash - dt)

    # ------------------------------------------------------------ drawing helpers
    def text(self, surf, s, x, y, color=Col.TEXT, scale=1, anchor="midtop", glow=None, max_w=None):
        font = self.font
        while max_w and scale > 1 and font.size(s, scale)[0] > max_w:
            scale -= 1
        img = font.render_glow(s, color, glow, scale) if glow else font.render(s, color, scale)
        rect = img.get_rect(**{anchor: (int(x), int(y))})
        if max_w and rect.w > max_w:
            clip = surf.get_clip()
            surf.set_clip(pygame.Rect(rect.x, rect.y, max_w, rect.h))
            surf.blit(img, rect)
            surf.set_clip(clip)
        else:
            surf.blit(img, rect)
        self.text_rects.append(rect)
        return rect

    def controls_lines(self):
        """The player's real keys, as (keys, what) rows."""
        c = self.controls
        launch = "/".join(n for n in (c.label("item", limit=1), c.label("interact", limit=1)) if n) or "?"
        pause = c.label("pause", limit=1) or c.label("menu", limit=1) or "?"
        return [(c.label("left", limit=1) or "?", "L FLIPPER"), (c.label("right", limit=1) or "?", "R FLIPPER"),
                (launch, "PLUNGER"), (pause, "PAUSE"), ("ESC", "LEAVE")]

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        self.text_rects = []
        world = self.table.world
        lucky = world.lucky_left > 0 and self.table.live
        surf.blit(self.bg, (0, 0))
        surf.blit(self.cabinet, (self.rand.randint(-1, 1), 0) if self.time < self.shake_until else (0, 0))
        self._draw_header(surf, lucky)
        surf.blit(self.felt, art.TABLE_POS)
        self._draw_table(surf, world, lucky)
        self._draw_panels(surf, world, lucky)
        self._draw_ticker(surf)
        if not self.paused:
            self._draw_fx(surf)
        self._draw_overlay(surf, world)

    def _draw_header(self, surf, lucky):
        glow = scale_color(Col.MAGENTA, 0.4 + 0.08 * math.sin(self.time * 3))
        if lucky:
            title, color = "LUCKY CAT MODE!", art.PINK if int(self.time * 5) % 2 else art.GOLD
        else:
            title, color = "LUCKY CAT PINBALL", art.GOLD
        self.text(surf, title, art.CX, 11, color, 2, glow=glow, max_w=250)
        for i in range(27):                                                   # chase bulbs under the title
            lit = int(self.time * 7) % 4 == i % 4
            surf.fill(Col.YELLOW if lit else scale_color(Col.MAGENTA, 0.6), (art.CX - 130 + i * 10, 30, 3, 2))
        if lucky:                                                             # the playfield glows gold
            k = 0.5 + 0.5 * math.sin(self.time * 6)
            r = pygame.Rect(art.TX - 5, art.TY - 5, int(pb.W) + 10, int(pb.H) + 10)
            pygame.draw.rect(surf, scale_color(art.GOLD, 0.55 + 0.4 * k), r, 2, border_radius=8)

    def _draw_table(self, surf, world, lucky):
        t = self.time
        px, py = art.TABLE_POS
        art.cat_face(surf, art.TX + 61, art.TY + 144, lucky, t)
        art.draw_scoop(surf, world, t)
        art.draw_lanes(surf, world, t)
        art.draw_targets(surf, world, t, self.font)
        for i in range(len(pb.BUMPERS)):
            art.draw_bumper(surf, i, world.bumper_flash[i], lucky, t)
        art.draw_plunger(surf, world)
        for f in world.flippers.values():
            art.draw_flipper(surf, f, lucky)
        if world.phase in ("ready", "play") and world.captured <= 0:
            by = world.by + (world.pull * 7 if world.pulling else 0)
            art.draw_ball(surf, world.bx, by, self.trail, lucky)
        if world.captured > 0 and int(t * 10) % 2:
            pygame.draw.circle(surf, (255, 250, 220), art.P(*pb.SCOOP), 4, 1)
        if self.drain_flash > 0:                                              # red drain wash along the bottom
            k = self.drain_flash / 0.9
            wash = pygame.Surface((int(pb.LANE_X), 22), pygame.SRCALPHA)
            for y in range(22):
                wash.fill((255, 60, 100, int(110 * k * (y / 22))), (0, y, int(pb.LANE_X), 1))
            surf.blit(wash, (px, py + int(pb.H) - 22))
        if lucky:
            frac = world.lucky_left / pb.LUCKY_TIME                          # the mode's remaining time, under the title
            surf.fill((60, 30, 90), (art.CX - 60, 33, 120, 3))
            surf.fill(art.GOLD, (art.CX - 60, 33, int(120 * frac), 3))
        if self.table.live and world.phase == "ready" and not self.paused:
            self._draw_plunger_hint(surf, world)

    def _draw_plunger_hint(self, surf, world):
        x = art.TX + int(pb.PLUNGER_REST[0])
        y = art.TY + int(pb.H) - 32
        arrow = [(x, y - 5 - int(math.sin(self.time * 6) * 2)), (x - 4, y), (x + 4, y)]
        pygame.draw.polygon(surf, Col.GREEN, arrow)
        gauge = pygame.Rect(art.TX + int(pb.W) + 4, art.TY + int(pb.H) - 74, 5, 60)
        pygame.draw.rect(surf, (10, 8, 34), gauge)
        pygame.draw.rect(surf, scale_color(Col.CYAN, 0.6), gauge, 1)
        fill = int((gauge.h - 2) * world.pull)
        color = Col.GREEN if world.pull < 0.75 else Col.YELLOW if world.pull < 0.95 else (255, 120, 140)
        surf.fill(color, (gauge.x + 1, gauge.bottom - 1 - fill, gauge.w - 2, fill))

    def _draw_ticker(self, surf):
        box = pygame.Rect(art.CX - 118, art.TY + int(pb.H) + 6, 236, 12)
        pygame.draw.rect(surf, (6, 4, 20), box)
        pygame.draw.rect(surf, scale_color(art.CYAN, 0.5), box, 1)
        if self.ticker and self.time < self.ticker_until:
            if int(self.time * 6) % 8:
                self.text(surf, self.ticker, box.centerx, box.y + 3, art.GOLD, 1, max_w=box.w - 4)
        else:
            self.text(surf, "CAT TARGETS - TOP LANES - SCOOP - BUMPERS", box.centerx, box.y + 3, Col.TEXT_MUTED, 1, max_w=box.w - 4)

    # ---- the two side panels
    def _draw_panels(self, surf, world, lucky):
        left, right = pygame.Rect(16, 40, 106, 232), pygame.Rect(278, 40, 106, 232)
        who = f"{self.player.tag} " if self.player and self.player.label else ""
        cx = left.centerx
        self.text(surf, f"{who}SCORE", cx, left.y + 6, Col.TEXT_MUTED, max_w=left.w - 6)
        score = world.score if self.table.state != "idle" or self.table.result is None else self.table.result.score
        self.text(surf, f"{score:,}", cx, left.y + 17, art.GOLD, 2, glow=scale_color(art.GOLD, 0.3), max_w=left.w - 8)
        self.text(surf, "BALL", cx, left.y + 42, Col.TEXT_MUTED)
        for i in range(pb.BALLS):
            x = cx - 22 + i * 22
            used = self.table.live and i + 1 < world.ball_no or self.table.state == "result"
            now = self.table.live and i + 1 == world.ball_no
            color = (70, 60, 110) if used else art.BALL if not now else Col.GREEN
            pygame.draw.circle(surf, (10, 6, 30), (x, left.y + 60), 7)
            pygame.draw.circle(surf, color, (x, left.y + 60), 5)
            if now:
                pygame.draw.circle(surf, scale_color(Col.GREEN, 0.5), (x, left.y + 60), 7, 1)
        timer, flash = self.token_flash
        color = flash if timer > 0 else Col.YELLOW
        self.text(surf, f"{who}TOKENS", cx, left.y + 80, Col.TEXT_MUTED, max_w=left.w - 6)
        rect = self.text(surf, f"{self.profile.tokens}", cx + 5, left.y + 92, color, 2, glow=scale_color(color, 0.3), max_w=left.w - 26)
        surf.blit(self.icon, self.icon.get_rect(midright=(rect.left - 4, rect.centery)))
        self.text(surf, f"RUN COST {PINBALL_RUN_COST} TOKEN", cx, left.y + 112, Col.TEXT_MUTED, max_w=left.w - 6)
        self.text(surf, "BEST", cx, left.y + 132, Col.TEXT_MUTED)
        self.text(surf, f"{self.profile.high_score('lucky_cat_pinball'):,}", cx, left.y + 143, art.PINK, 1, max_w=left.w - 6)
        self.text(surf, "TICKETS", cx, left.y + 166, Col.TEXT_MUTED)
        self.text(surf, f"{self.profile.tickets}", cx, left.y + 177, art.PINK, 2, glow=scale_color(art.PINK, 0.3), max_w=left.w - 8)
        self.text(surf, f"WON {self.table.session_tickets}", cx, left.y + 200, Col.TEXT_MUTED, max_w=left.w - 6)
        self.text(surf, f"1 PER {PINBALL_POINTS_PER_TICKET} PTS", cx, left.y + 212, Col.TEXT_MUTED, max_w=left.w - 6)
        # right: the controls then the table's status
        rx = right.centerx
        self.text(surf, "CONTROLS", rx, right.y + 6, Col.CYAN)
        for i, (keys, what) in enumerate(self.controls_lines()):
            y = right.y + 20 + i * 15
            if self.font.size(keys)[0] > 42:                                  # R-SHIFT/ENTER: show the first key only
                keys = keys.split("/")[0]
            self.text(surf, keys, right.x + 6, y, Col.CYAN, anchor="topleft", max_w=42)
            self.text(surf, what, right.right - 5, y, Col.TEXT, anchor="topright", max_w=right.w - 54)
        self.text(surf, "STATUS", rx, right.y + 106, Col.CYAN)
        mult = f"BONUS X{world.mult}"
        self.text(surf, mult, rx, right.y + 120, art.GOLD if world.mult > 1 else Col.TEXT, max_w=right.w - 6)
        letters = "".join(l if world.targets[i] else "-" for i, l in enumerate(pb.TARGET_LETTERS))
        self.text(surf, "CAT " + " ".join(letters), rx, right.y + 134, art.GOLD if all(world.targets) else Col.TEXT, max_w=right.w - 6)
        self.text(surf, "SCOOP LIT" if world.scoop_lit else "SCOOP DARK", rx, right.y + 148,
                  Col.GREEN if world.scoop_lit else Col.TEXT_MUTED, max_w=right.w - 6)
        if lucky:
            self.text(surf, f"LUCKY {world.lucky_left:0.0f}S", rx, right.y + 162, art.PINK, 1, glow=scale_color(art.PINK, 0.4), max_w=right.w - 6)
        else:
            self.text(surf, "CAT: LUCKY MODE", rx, right.y + 162, Col.TEXT_MUTED, max_w=right.w - 6)
        self.text(surf, "PAYOUT", rx, right.y + 186, Col.CYAN)
        self.text(surf, f"MAX {PINBALL_MAX_TICKETS} TICKETS", rx, right.y + 199, Col.TEXT_MUTED, max_w=right.w - 6)
        self.text(surf, f"{self.profile.pinball_ticket_room()} LEFT TODAY", rx, right.y + 211, Col.TEXT_MUTED, max_w=right.w - 6)

    # ---- effects
    def _draw_fx(self, surf):
        for x, y, vx, vy, life, color in self.particles:
            surf.fill(color, (int(x), int(y), 2, 2))
        for text, x, y, life, color in self.popups:
            self.text(surf, text, x, y, color, glow=scale_color(color, 0.3))
        if self.alert and self.time < self.alert_until:
            box = pygame.Rect(0, 0, 150, 30)
            box.center = (art.CX - 9, art.TY + 218)
            pygame.draw.rect(surf, (40, 6, 24), box, border_radius=4)
            pygame.draw.rect(surf, (255, 80, 110), box, 2, border_radius=4)
            self.text(surf, self.alert, box.centerx, box.y + 6, (255, 120, 150), 1)
            self.text(surf, "EARN TOKENS IN THE ARCADE", box.centerx, box.y + 17, Col.TEXT_MUTED, max_w=box.w - 8)

    # ---- overlays: title, end-of-ball bonus, result, pause
    def _panel(self, surf, h, y=70):
        box = pygame.Rect(0, 0, 124, h)
        box.midtop = (art.CX - 9, art.TY + y)
        veil = pygame.Surface(box.inflate(8, 8).size, pygame.SRCALPHA)
        veil.fill((4, 2, 20, 205))
        surf.blit(veil, box.inflate(8, 8).topleft)
        pygame.draw.rect(surf, (16, 10, 48), box, border_radius=4)
        pygame.draw.rect(surf, art.CYAN, box, 1, border_radius=4)
        return box

    def _draw_overlay(self, surf, world):
        if self.paused:
            box = self._panel(surf, 82, 60)
            self.text(surf, "PAUSED", box.centerx, box.y + 7, Col.YELLOW, 2)
            pause_key = self.controls.label("pause", limit=1) or self.controls.label("menu", limit=1)
            self.text(surf, f"{pause_key}: RESUME", box.centerx, box.y + 29, Col.TEXT, max_w=box.w - 6)
            if self.table.live:
                self.text(surf, "ESC: LEAVE", box.centerx, box.y + 43, (255, 150, 170) if self.confirm_leave else Col.TEXT, max_w=box.w - 6)
                self.text(surf, "SCORE SO FAR IS PAID", box.centerx, box.y + 56, Col.TEXT_MUTED, max_w=box.w - 6)
                self.text(surf, "UNPLAYED BALLS ARE LOST", box.centerx, box.y + 67, Col.TEXT_MUTED, max_w=box.w - 6)
            else:
                self.text(surf, "ESC: LEAVE", box.centerx, box.y + 43, Col.TEXT, max_w=box.w - 6)
            return
        state = self.table.state
        if world.phase == "bonus" and world.last_bonus:
            bumpers, targets, mult, total = world.last_bonus
            box = self._panel(surf, 74, 66)
            self.text(surf, f"BALL {world.ball_no} LOST", box.centerx, box.y + 6, (255, 130, 150), 1)
            self.text(surf, "END OF BALL BONUS", box.centerx, box.y + 18, Col.CYAN, max_w=box.w - 6)
            self.text(surf, f"BUMPERS {bumpers}  TARGETS {targets}", box.centerx, box.y + 31, Col.TEXT_MUTED, max_w=box.w - 6)
            self.text(surf, f"X{mult}", box.centerx, box.y + 42, art.GOLD)
            self.text(surf, f"+{total:,}", box.centerx, box.y + 54, art.GOLD, 2, glow=scale_color(art.GOLD, 0.3), max_w=box.w - 6)
        elif state == "idle":
            box = self._panel(surf, 104, 56)
            self.text(surf, "LUCKY CAT", box.centerx, box.y + 6, art.GOLD, 2, glow=scale_color(art.PINK, 0.5), max_w=box.w - 6)
            self.text(surf, "PINBALL", box.centerx, box.y + 24, art.PINK, 2, max_w=box.w - 6)
            self.text(surf, f"{pb.BALLS} BALLS  -  {PINBALL_RUN_COST} TOKEN", box.centerx, box.y + 46, Col.TEXT, max_w=box.w - 6)
            self._start_prompt(surf, box, 62)
        elif state == "result":
            r = self.table.result
            box = self._panel(surf, 128, 44)
            title = "RUN RECOVERED" if r.recovered else "RUN ENDED" if r.forfeited else "GAME OVER"
            self.text(surf, title, box.centerx, box.y + 6, Col.YELLOW, 1)
            self.text(surf, f"{r.score:,}", box.centerx, box.y + 17, art.GOLD, 2, glow=scale_color(art.GOLD, 0.3), max_w=box.w - 6)
            if r.new_best and r.score:
                self.text(surf, "NEW BEST!", box.centerx, box.y + 36, art.PINK if int(self.time * 4) % 2 else art.GOLD, 1)
            else:
                self.text(surf, f"BEST {r.best:,}", box.centerx, box.y + 36, Col.TEXT_MUTED, max_w=box.w - 6)
            self.text(surf, f"+{r.tickets} TICKETS", box.centerx, box.y + 50, art.PINK, 1, glow=scale_color(art.PINK, 0.3), max_w=box.w - 6)
            if r.tokens:
                self.text(surf, f"+{r.tokens} TOKEN", box.centerx, box.y + 62, Col.YELLOW)
            if r.capped:
                self.text(surf, "DAILY LIMIT REACHED", box.centerx, box.y + 74, (255, 150, 170), max_w=box.w - 6)
            else:
                self.text(surf, f"1 PER {PINBALL_POINTS_PER_TICKET} PTS", box.centerx, box.y + 74,
                          Col.TEXT_MUTED, max_w=box.w - 6)
            self._start_prompt(surf, box, 92, again=True)

    def _start_prompt(self, surf, box, y, again=False):
        keys = "/".join(n for n in (self.controls.label("item", limit=1), self.controls.label("interact", limit=1)) if n)
        if int(self.time * 2) % 2 or not self.table.can_start():
            ok = self.table.can_start()
            self.text(surf, f"{keys}: {'PLAY AGAIN' if again else 'START'}", box.centerx, box.y + y,
                      Col.GREEN if ok else (255, 130, 150), 1, max_w=box.w - 6)
        self.text(surf, "ESC: LEAVE", box.centerx, box.y + y + 12, Col.TEXT_MUTED)
