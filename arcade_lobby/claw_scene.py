"""ClawScene: NEON CLAW - KITTY CATCHER, full screen, opened from the claw machine in Prize Plaza.

The scene only draws and routes input. Every rule, every Token and every Ticket is claw_machine.ClawGame, so a key
press can only ask: start() charges once, drop() works once per attempt, and a prize is paid once, when it is in the
chute.

Controls follow the player's control scheme:
    left / right (hold)   slide the claw                     (A/D or arrows)
    interact / item       IDLE: pay and start   AIM: drop     (E, or the item key)
    ESC                   back to Prize Plaza. An attempt in progress is played out at once first (a claw being aimed
                          drops where it is), and a prize it wins is paid exactly as if the player had watched.
"""
import math
import random

import pygame

import claw_art as art
import claw_machine as cm
from claw_lock import ClawLockScene, lock_pending
from forgotten_games import GOLDEN_CAT, GOLDEN_SLOT, golden_cat_for, story_manager
from controls import SOLO_CONTROLS
from daily_ui import token_icon
from font import get_font
from gfx import scale_color, shade
from scene_base import BaseScene
from settings import BACK_KEYS, Col, VIEW_H, VIEW_W

# ---- screen layout (canvas pixels)
CABINET = pygame.Rect(30, 4, 262, 292)
GLASS = pygame.Rect(46, 48, 230, 140)
FX = GLASS.x + 5                        # the field's x = 0
GANTRY_Y = GLASS.y + 6                  # the rail the carriage runs on
TIP0 = GANTRY_Y + 20                    # where the claw's tips hang when parked (field y = 0)
FLOOR = TIP0 + cm.FLOOR_Y               # where the plushies' feet are
DECK = pygame.Rect(CABINET.x + 6, GLASS.bottom + 4, CABINET.w - 12, 40)
DOOR = pygame.Rect(CABINET.x + 18, DECK.bottom + 8, 58, 34)
PANEL = pygame.Rect(298, 4, 98, 292)
INPUT_DELAY = 0.3                       # the press that opened the screen is not a START
ALERT_TIME = 1.4
MOTOR_GAP = 0.3                         # seconds between two motor whirrs while the claw keeps moving

QUALITY_COLOR = {"centre": Col.GREEN, "fair": Col.YELLOW, "edge": (255, 120, 170), None: (120, 110, 170)}


def aim_quality(game):
    """How good a drop right now would be: 'centre', 'fair', 'edge' or None (nothing under the claw)."""
    target = game.target_under()
    if target is None:
        return None, None
    odds = cm.grab_odds(game.x - target.x, target.spec)
    if odds >= target.spec.grip:
        return "centre", target
    if odds > cm.CLAW_GRIP_EDGE:
        return "fair", target
    return "edge", target


class ClawScene(BaseScene):
    music_id = "prize_plaza"            # the room's own theme carries on (the machine's sounds sit on top)
    own_audio = True                    # its keys make their own sounds (no generic confirm blip on E)

    def __init__(self, game, player=None, claw=None, rng=None):
        """player: the LocalPlayer at the cabinet - their profile pays and wins."""
        super().__init__(game)
        self.player = player
        # Chapter 02's Golden Cat joins the stock only while it waits (forgotten_games.py); otherwise no special at all
        self.claw = claw or cm.ClawGame(self.profile, rng=rng, special=golden_cat_for(self))
        self.rand = random.Random(7)    # cosmetic only (sparkles, shake); never decides an outcome
        self.time = 0.0
        self.lock = INPUT_DELAY
        self.held = set()
        self.particles = []             # [x, y, vx, vy, life, color]
        self.alert, self.alert_until = None, 0.0
        self.shake_until = 0.0
        self.token_flash = 0.0
        self.last_result = None         # the Attempt shown on the banner (WON / LOST)
        self.slipped = False
        self.left_early = False
        self.motor_at = -1.0
        self.bg = _background()
        self.cabinet = _cabinet()
        self.icon = token_icon()
        self.back_row = _back_row()

    # ------------------------------------------------------------ plumbing
    @property
    def profile(self):
        return self.player.profile if self.player else self.game.profile

    @property
    def controls(self):
        return self.player.controls if self.player else SOLO_CONTROLS

    def _sound(self, name):
        audio = getattr(self.game, "audio", None)
        if audio is not None:
            audio.play(name)

    def _settle_now(self):
        """Leaving (or closing the game) mid-attempt: play it out so the Tokens paid always buy a real attempt."""
        if self.claw.busy:
            self.left_early = True
            self.claw.finish()

    def on_exit(self):
        self._settle_now()

    def on_quit(self):
        self._settle_now()

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type == pygame.KEYUP:
            self.held.discard(event.key)
            return
        if event.type != pygame.KEYDOWN or getattr(event, "repeat", False):
            return
        if event.key in BACK_KEYS:
            self._sound("cancel")
            self._settle_now()
            self.game.scenes.pop()
            return
        action = self.controls.action_for(event.key)
        if action in ("left", "right"):
            self.held.add(event.key)
        elif action in ("interact", "item") and self.lock <= 0:
            self.press()
        elif action == "up" and self.lock <= 0 and self.lock_waiting and self.claw.phase == cm.IDLE:
            self.open_lock()

    # ------------------------------------------------------------ Chapter 02: the prize lock (claw_lock.py)
    @property
    def lock_waiting(self):
        """Is the old prize lock on this cabinet, still shut? (Only once all three symbols are found.)"""
        return lock_pending(story_manager(self.game))

    def open_lock(self):
        self.held.clear()
        self._sound("confirm")
        owner = self.player or self.game.session.primary
        self.game.scenes.push(ClawLockScene(self.game, owner))

    def _wake_golden_cat(self):
        """The lock was just opened: the Golden Cat drops into its spot (once the claw is idle)."""
        if self.claw.special is not None or self.claw.phase != cm.IDLE:
            return
        special = golden_cat_for(self)
        if special is None:
            return
        self.claw.special = special
        spot = next((p for p in self.claw.plushies if p.slot == GOLDEN_SLOT), None)
        if spot is not None and spot.spec is not GOLDEN_CAT:
            spot.spec = GOLDEN_CAT
            self._burst(FX + spot.x, FLOOR - 8, 24, (art.GOLD, (255, 250, 220), art.PINK))
            self._sound("win")

    def press(self):
        """START when idle, DROP while aiming; anything else (mid-drop, mid-lift ...) is ignored."""
        claw = self.claw
        if claw.phase == cm.AIM:
            return claw.drop()
        if claw.phase != cm.IDLE:
            return False
        if claw.start():
            self.token_flash = 0.5
            self.slipped = False
            self.last_result = None
            return True
        if claw.start_block_reason() == "NO TOKENS":
            self.alert, self.alert_until = "NOT ENOUGH TOKENS", self.time + ALERT_TIME
            self.shake_until = self.time + 0.4
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
        self.time += dt
        self.lock = max(0.0, self.lock - dt)
        self._wake_golden_cat()
        self.token_flash = max(0.0, self.token_flash - dt)
        claw = self.claw
        claw.update(dt, self.direction() if claw.phase == cm.AIM else 0)
        for event in claw.take_events():
            self._on_event(event)
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 160 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]

    def _on_event(self, event):
        sound = {"start": "token", "move": "claw_move", "drop": "claw_drop", "grab": "claw_grab",
                 "slip": "claw_slip", "release": "claw_chute", "win": "claw_win", "lose": "claw_lose"}.get(event)
        if event == "slip":
            self.slipped = True
        if event in ("win", "lose"):
            self.last_result = self.claw.attempt
        if event == "win":
            self._burst(DOOR.centerx, DOOR.y + 8, 40, (art.GOLD, art.PINK, art.CYAN, (255, 255, 255)))
            self._burst(FX + cm.HOME_X, FLOOR - 4, 14, (art.GOLD, (255, 255, 255)))
        if event == "ready":
            for p in self.claw.plushies:                     # a twinkle on every plushie, the new one included
                self.particles.append([FX + p.x, FLOOR - p.spec.height - 2, 0, -10, 0.5, (255, 255, 255)])
        if event == "move":                                  # the motor: at most one whirr per MOTOR_GAP, never stacked
            if self.time - self.motor_at < MOTOR_GAP:
                return
            self.motor_at = self.time
        if sound:
            self._sound(sound)

    def _burst(self, x, y, n, colors):
        for _ in range(n):
            self.particles.append([x + self.rand.uniform(-6, 6), y, self.rand.uniform(-70, 70),
                                   self.rand.uniform(-120, -30), self.rand.uniform(0.6, 1.3), self.rand.choice(colors)])

    # ------------------------------------------------------------ text
    @staticmethod
    def text(surf, s, x, y, color=Col.TEXT, scale=1, anchor="midtop", glow=None, max_w=None):
        font = get_font()
        while max_w and scale > 1 and font.size(s, scale)[0] > max_w:
            scale -= 1
        img = font.render_glow(s, color, glow, scale) if glow else font.render(s, color, scale)
        rect = img.get_rect(**{anchor: (int(x), int(y))})
        surf.blit(img, rect)
        return rect

    def controls_lines(self):
        c = self.controls
        move = f"{c.label('left', limit=1) or '?'}/{c.label('right', limit=1) or '?'}"
        use = c.label("interact", limit=1) or c.label("item", limit=1) or "?"
        lines = [(move, "MOVE"), (use, "PLAY/DROP"), ("ESC", "LEAVE")]
        if self.lock_waiting:
            lines.insert(2, (c.label("up", limit=1) or "W", "PRIZE LOCK"))
        return lines

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        dx = self.rand.randint(-1, 1) if self.time < self.shake_until else 0
        surf.blit(self.cabinet, (dx, 0))
        self._draw_lights(surf)
        clip = surf.get_clip()
        surf.set_clip(GLASS.inflate(-2, -2))
        self._draw_field(surf)
        surf.set_clip(clip)
        self._draw_glass_front(surf)
        self._draw_deck(surf)
        self._draw_door(surf)
        self._draw_panel(surf)
        for x, y, _, _, life, color in self.particles:
            surf.fill(color, (int(x), int(y), 2, 2))
        self._draw_banner(surf)

    # ---- the machine
    def _draw_lights(self, surf):
        t = self.time
        for i in range(20):                                          # chase bulbs under the marquee
            lit = int(t * 6) % 4 == i % 4
            x = CABINET.x + 12 + i * 12
            surf.fill(art.GOLD if lit else scale_color(art.PINK, 0.5), (x, 42, 3, 2))
        pulse = 0.5 + 0.5 * math.sin(t * 2.0)
        for x in (GLASS.x - 6, GLASS.right + 3):                     # the neon posts breathe
            y = GLASS.y + 8 + int(pulse * (GLASS.h - 30))
            surf.fill(shade(art.PINK, 0.5), (x, y, 3, 14))
        glow = scale_color(art.HOT_PINK, 0.4 + 0.1 * math.sin(t * 3))
        self.text(surf, "NEON CLAW", CABINET.centerx, 10, art.GOLD, 2, glow=glow)
        self.text(surf, "KITTY CATCHER", CABINET.centerx, 29, art.PINK, glow=scale_color(art.PINK, 0.35))

    def _draw_field(self, surf):
        claw = self.claw
        surf.blit(self.back_row, (FX, FLOOR - 14))                  # a dim pile behind (decoration only)
        # the chute: a hole in the floor behind a see-through acrylic wall
        hole = pygame.Rect(FX - 4, FLOOR - 1, cm.CHUTE_W + 2, GLASS.bottom - FLOOR + 2)
        surf.fill((6, 2, 16), hole)
        wall_x = FX + cm.CHUTE_W
        quality, target = aim_quality(claw) if claw.phase == cm.AIM else (None, None)
        for p in sorted(claw.plushies, key=lambda q: q.spec.height):
            self._plush(surf, p, outline=QUALITY_COLOR[quality] if p is target else None)
        for p in claw.falling:
            self._plush(surf, p)
        if claw.in_chute is not None:
            self._plush(surf, claw.in_chute)
        acrylic = pygame.Surface((3, 30), pygame.SRCALPHA)
        acrylic.fill((255, 160, 220, 90))
        surf.blit(acrylic, (wall_x - 1, FLOOR - 30))
        surf.fill(art.PINK, (wall_x - 1, FLOOR - 30, 3, 1))
        self.text(surf, "PRIZE", FX + cm.CHUTE_W // 2 - 2, FLOOR - 22, scale_color(art.PINK, 0.9))
        surf.fill(scale_color(art.PINK, 0.9), (FX + cm.CHUTE_W // 2 - 4, FLOOR - 12, 5, 1))
        pygame.draw.polygon(surf, scale_color(art.PINK, 0.9), [(FX + cm.CHUTE_W // 2 - 4, FLOOR - 10),
                                                              (FX + cm.CHUTE_W // 2, FLOOR - 10),
                                                              (FX + cm.CHUTE_W // 2 - 2, FLOOR - 7)])
        # the aim guide while aiming: a dotted drop line, coloured by how good the grab would be
        cx = FX + claw.x
        if claw.phase == cm.AIM:
            color = QUALITY_COLOR[quality]
            stop = (target.top if target is not None else cm.FLOOR_Y) + TIP0
            for y in range(int(TIP0 + claw.y + 4), int(stop), 4):
                surf.fill(scale_color(color, 0.75), (int(cx), y, 1, 2))
        # gantry, carriage, cable, claw
        surf.fill(art.METAL_DARK, (GLASS.x + 2, GANTRY_Y - 2, GLASS.w - 4, 3))
        surf.fill(art.METAL, (GLASS.x + 2, GANTRY_Y - 2, GLASS.w - 4, 1))
        surf.fill(art.METAL, (int(cx) - 7, GANTRY_Y - 4, 15, 5))
        surf.fill(art.PINK, (int(cx) - 1, GANTRY_Y - 3, 3, 2))
        hub_y = TIP0 + claw.y - 20
        surf.fill(art.METAL_DARK, (int(cx), GANTRY_Y + 1, 1, max(0, int(hub_y - GANTRY_Y - 1))))
        if claw.held is not None:
            self._plush(surf, claw.held, wobble=claw.phase in (cm.LIFT, cm.CARRY))
        art.draw_claw(surf, cx, hub_y, claw.open, scale=2)

    def _plush(self, surf, p, outline=None, wobble=False):
        img = art.plush_sprite(p.spec)
        x = FX + p.x + (int(round(math.sin(self.time * 9) * 1)) if wobble else 0)
        rect = img.get_rect(midbottom=(int(round(x)), int(round(TIP0 + p.y))))
        surf.blit(img, rect)
        if p.spec.look.get("kind") == "golden" and int(self.time * 3 + p.x) % 4 == 0:      # the Golden Cat twinkles
            surf.fill((255, 255, 255), (rect.right - 3, rect.top + 2, 1, 1))
        if outline is not None and int(self.time * 4) % 2 == 0:
            surf.fill(outline, (rect.centerx - 1, rect.top - 4, 3, 2))                 # a little marker above it

    def _draw_glass_front(self, surf):
        phase = (self.time % 6.0) / 1.5                             # a slow shine sweeping the glass
        if phase < 1:
            gx = GLASS.x + 4 + int(phase * (GLASS.w - 30))
            shine = pygame.Surface((GLASS.w, GLASS.h), pygame.SRCALPHA)
            for i in range(GLASS.h):
                shine.fill((220, 240, 255, 26), (gx - GLASS.x + i // 3, i, 6, 1))
            surf.blit(shine, GLASS.topleft)
        pygame.draw.rect(surf, art.CYAN, GLASS, 1)
        if self.lock_waiting:                                        # the old brass prize lock, hanging on the glass
            x, y = GLASS.right - 22, GLASS.bottom - 24
            pygame.draw.rect(surf, (120, 84, 30), (x + 3, y - 7, 10, 10), 2, border_radius=4)
            surf.fill((196, 150, 64), (x, y, 16, 13))
            pygame.draw.rect(surf, (120, 84, 30), (x, y, 16, 13), 1)
            surf.fill((60, 40, 16), (x + 7, y + 4, 2, 5))
            if int(self.time * 2) % 2 == 0:
                surf.fill((255, 240, 180), (x + 2, y + 2, 1, 1))

    def _draw_deck(self, surf):
        claw = self.claw
        d = self.direction() if claw.phase == cm.AIM else 0
        jx, jy = DECK.x + 34, DECK.y + 20                             # the joystick tilts with the claw
        pygame.draw.line(surf, (30, 20, 40), (jx, jy + 8), (jx + d * 4, jy - 2), 3)
        pygame.draw.circle(surf, (255, 80, 110), (jx + d * 4, jy - 4), 6)
        surf.fill((255, 200, 210), (jx + d * 4 - 3, jy - 7, 2, 2))
        ready = claw.phase == cm.AIM or (claw.phase == cm.IDLE and claw.can_start())
        lit = ready and int(self.time * 3) % 2 == 0
        bx, by = DECK.x + 78, DECK.y + 18                             # the big DROP button
        pygame.draw.circle(surf, shade(art.CYAN, -0.5), (bx, by + 2), 9)
        pygame.draw.circle(surf, art.CYAN if lit else scale_color(art.CYAN, 0.55), (bx, by), 8)
        surf.fill((230, 255, 255), (bx - 4, by - 4, 2, 2))
        self.text(surf, "DROP" if claw.phase != cm.IDLE else "START", bx, by + 11, Col.TEXT_MUTED)
        # the LED strip
        led = pygame.Rect(DECK.x + 102, DECK.y + 6, DECK.right - DECK.x - 108, 14)
        pygame.draw.rect(surf, (6, 4, 20), led)
        pygame.draw.rect(surf, scale_color(art.CYAN, 0.6), led, 1)
        message, color = self._led()
        self.text(surf, message, led.centerx, led.y + 4, color, max_w=led.w - 4)
        # the price plate
        plate = pygame.Rect(led.x, led.bottom + 4, led.w, 12)
        afford = self.profile.can_afford_tokens(claw.cost)
        price_color = art.GOLD if afford else (255, 110, 150)
        rect = self.text(surf, f"{claw.cost} TOKENS A TRY", plate.centerx + 6, plate.y + 2, price_color)
        surf.blit(self.icon, self.icon.get_rect(midright=(rect.left - 3, rect.centery)))

    def _led(self):
        claw, a = self.claw, self.claw.attempt
        phase = claw.phase
        if phase == cm.IDLE:
            if claw.can_start():
                use = self.controls.label("interact", limit=1) or "E"
                return f"PRESS {use} TO PLAY", Col.CYAN if int(self.time * 2) % 2 else Col.TEXT
            return "NEED MORE TOKENS", (255, 120, 150)
        if phase == cm.AIM:
            return f"AIM AND DROP  {int(math.ceil(claw.aim_left)):02d}", Col.YELLOW
        if phase in (cm.DROP, cm.GRAB):
            return "DROPPING...", Col.CYAN
        if phase in (cm.LIFT, cm.CARRY):
            if claw.held is not None:
                return "HOLD ON...", Col.YELLOW
            return "EMPTY CLAW", Col.TEXT_MUTED
        if phase == cm.RELEASE:
            return "RELEASE!", Col.CYAN
        if phase == cm.WON:
            return f"+{a.tickets} TICKETS", art.GOLD
        return ("IT SLIPPED" if self.slipped else "MISSED"), (255, 140, 180)

    def _draw_door(self, surf):
        """The prize door: a won plushie sits there while the result shows."""
        claw = self.claw
        if claw.phase == cm.WON and claw.attempt is not None and claw.attempt.won:
            spec = self.last_result_spec()
            if spec is not None:
                img = art.plush_sprite(spec)
                bob = int(round(math.sin(self.time * 6) * 1))
                surf.blit(img, img.get_rect(midbottom=(DOOR.centerx, DOOR.bottom - 6 + bob)))

    def last_result_spec(self):
        a = self.last_result
        return a.target.spec if a is not None and a.target is not None else None

    def _draw_panel(self, surf):
        box = PANEL
        pygame.draw.rect(surf, (12, 8, 32), box, border_radius=4)
        pygame.draw.rect(surf, scale_color(art.PINK, 0.6), box, 1, border_radius=4)
        y = box.y + 6
        self.text(surf, "TOKENS", box.centerx, y, Col.TEXT_MUTED)
        color = Col.CYAN if self.token_flash > 0 else Col.YELLOW
        rect = self.text(surf, str(self.profile.tokens), box.centerx + 6, y + 11, color, 2, max_w=box.w - 24)
        surf.blit(self.icon, self.icon.get_rect(midright=(rect.left - 3, rect.centery)))
        y += 32
        self.text(surf, "TICKETS", box.centerx, y, Col.TEXT_MUTED)
        self.text(surf, str(self.profile.tickets), box.centerx, y + 11, art.PINK, 2, max_w=box.w - 8)
        y += 32
        self.text(surf, f"WON HERE +{self.claw.session_tickets}", box.centerx, y, art.GOLD, max_w=box.w - 6)
        y += 14
        surf.fill(scale_color(art.PINK, 0.4), (box.x + 6, y, box.w - 12, 1))
        y += 5
        self.text(surf, "PRIZES", box.centerx, y, Col.TEXT)
        y += 12
        ordinary = [p for p in cm.PLUSHIES if not p.hidden]
        for i, spec in enumerate(ordinary):                          # 2 x 3: the plushie and its Ticket value
            col, row = i % 2, i // 2
            cx = box.x + 26 + col * 46
            cy = y + row * 30
            img = art.plush_sprite(spec)
            surf.blit(img, img.get_rect(midbottom=(cx, cy + 20)))
            self.text(surf, f"{spec.tickets}T", cx, cy + 21, art.GOLD)
        y += 92
        surf.fill(scale_color(art.PINK, 0.4), (box.x + 6, y, box.w - 12, 1))
        y += 6
        for keys, what in self.controls_lines():
            self.text(surf, keys, box.x + 6, y, Col.CYAN, anchor="topleft")
            self.text(surf, what, box.right - 6, y, Col.TEXT, anchor="topright")
            y += 11
        y += 2
        self.text(surf, "CENTRE THE CLAW", box.centerx, y, Col.TEXT_MUTED, max_w=box.w - 4)
        self.text(surf, "FOR A FIRM GRIP", box.centerx, y + 10, Col.TEXT_MUTED, max_w=box.w - 4)

    def _draw_banner(self, surf):
        claw = self.claw
        if self.alert and self.time < self.alert_until:
            self._card(surf, self.alert, "EARN TOKENS IN THE ARCADE", (255, 110, 150))
        elif claw.phase == cm.WON and self.last_result is not None:
            spec = self.last_result_spec()
            name = spec.name if spec is not None else "A PRIZE"
            y = 92 + int(math.sin(self.time * 8) * 2)
            box = pygame.Rect(0, 0, 200, 46)
            box.center = (GLASS.centerx, y)
            pygame.draw.rect(surf, (40, 10, 50), box, border_radius=5)
            pygame.draw.rect(surf, art.GOLD if int(self.time * 8) % 2 else art.PINK, box, 2, border_radius=5)
            self.text(surf, "YOU GOT IT!", box.centerx, box.y + 5, art.GOLD, 2, glow=scale_color(art.PINK, 0.5))
            self.text(surf, f"{name}  +{self.last_result.tickets} TICKETS", box.centerx, box.y + 26, Col.TEXT,
                      max_w=box.w - 8)
            golden = spec is not None and spec.item_id == GOLDEN_CAT.item_id
            note = "SECRET ITEM 02 FOUND" if golden else \
                "ADDED TO YOUR BAG" if self.last_result.item_added else "BAG FULL - TICKETS ONLY"
            self.text(surf, note, box.centerx, box.y + 36, Col.YELLOW if golden else Col.TEXT_MUTED, max_w=box.w - 8)
        elif claw.phase == cm.LOST:
            self._card(surf, "SO CLOSE!" if self.slipped else "MISSED!", "CENTRE THE CLAW AND TRY AGAIN",
                       (255, 140, 180))

    def _card(self, surf, title, line, color):
        box = pygame.Rect(0, 0, 190, 32)
        box.center = (GLASS.centerx, 96)
        pygame.draw.rect(surf, (30, 8, 34), box, border_radius=4)
        pygame.draw.rect(surf, color, box, 2, border_radius=4)
        self.text(surf, title, box.centerx, box.y + 5, color)
        self.text(surf, line, box.centerx, box.y + 18, Col.TEXT_MUTED, max_w=box.w - 8)


# ------------------------------------------------------------------ static art
def _background():
    s = pygame.Surface((VIEW_W, VIEW_H))
    for y in range(VIEW_H):
        k = y / VIEW_H
        s.fill((int(14 + 12 * k), int(8 + 6 * k), int(30 + 18 * k)), (0, y, VIEW_W, 1))
    rng = random.Random(42)
    for _ in range(40):                                              # soft neon bokeh in the dark
        x, y = rng.randrange(VIEW_W), rng.randrange(VIEW_H)
        color = rng.choice(((60, 20, 70), (20, 40, 80), (70, 30, 60)))
        pygame.draw.circle(s, color, (x, y), rng.randint(2, 5))
    for x in range(0, VIEW_W, 16):                                   # a faint floor grid at the bottom
        s.fill((34, 22, 60), (x, 270, 1, VIEW_H - 270))
    s.fill((40, 26, 70), (0, 270, VIEW_W, 1))
    return s


def _cabinet():
    s = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    c = CABINET
    pygame.draw.rect(s, art.PURPLE, c, border_radius=8)
    pygame.draw.rect(s, art.PINK, c, 2, border_radius=8)
    pygame.draw.rect(s, art.PURPLE_DARK, (c.x + 8, c.y + 6, c.w - 16, 32), border_radius=4)       # marquee plate
    pygame.draw.rect(s, art.GOLD, (c.x + 8, c.y + 6, c.w - 16, 32), 1, border_radius=4)
    for hx in (c.x + 18, c.right - 26):                                                             # hearts
        pygame.draw.circle(s, art.PINK, (hx + 2, c.y + 18), 3)
        pygame.draw.circle(s, art.PINK, (hx + 6, c.y + 18), 3)
        pygame.draw.polygon(s, art.PINK, [(hx - 1, c.y + 19), (hx + 9, c.y + 19), (hx + 4, c.y + 25)])
    s.fill(art.CYAN, (c.x + 2, 44, c.w - 4, 1))
    for x in (GLASS.x - 7, GLASS.right + 2):                                                        # neon posts
        s.fill(art.HOT_PINK, (x, GLASS.y, 5, GLASS.h))
        s.fill(shade(art.HOT_PINK, 0.4), (x + 1, GLASS.y, 1, GLASS.h))
    for y in range(GLASS.top, GLASS.bottom):                                                        # the velvet back
        k = (y - GLASS.top) / GLASS.h
        s.fill((int(18 + 26 * k), int(14 + 12 * k), int(48 + 40 * k)), (GLASS.x, y, GLASS.w, 1))
    for x in range(GLASS.x + 8, GLASS.right - 4, 24):                                               # a few stars on it
        s.fill((80, 60, 140), (x, GLASS.y + 30 + (x * 7) % 30, 1, 1))
    s.fill((70, 44, 120), (GLASS.x, FLOOR, GLASS.w, GLASS.bottom - FLOOR))                          # the floor
    s.fill((96, 60, 150), (GLASS.x, FLOOR, GLASS.w, 1))
    # the deck
    d = DECK
    pygame.draw.rect(s, (130, 64, 196), d, border_radius=3)
    pygame.draw.rect(s, art.CYAN, d, 1, border_radius=3)
    s.fill(art.PURPLE_DARK, (d.x + 4, d.bottom - 3, d.w - 8, 2))
    # the base: prize door, coin slot, paw prints
    door = DOOR
    pygame.draw.rect(s, (8, 4, 20), door, border_radius=3)
    pygame.draw.rect(s, art.PINK, door, 2, border_radius=3)
    s.fill(shade(art.PINK, 0.4), (door.x + 4, door.y + 4, door.w - 8, 1))
    font = get_font()
    label = font.render("PRIZE", art.PINK)
    s.blit(label, (door.right + 6, door.bottom - 9))
    slot = pygame.Rect(c.right - 70, DOOR.y + 4, 40, 18)
    pygame.draw.rect(s, (24, 12, 44), slot, border_radius=2)
    pygame.draw.rect(s, art.GOLD, slot, 1, border_radius=2)
    s.fill((4, 2, 10), (slot.centerx - 1, slot.y + 4, 3, 12))
    coin = font.render("COIN", art.GOLD)
    s.blit(coin, (slot.centerx - coin.get_width() // 2, slot.bottom + 3))
    for px, py in ((c.centerx - 6, DOOR.y + 6), (c.centerx + 10, DOOR.y + 14)):              # two paw prints
        s.fill(art.PINK, (px, py + 2, 5, 4))
        for dx, dy in ((-1, 0), (1, -1), (3, -1), (5, 0)):
            s.fill(art.PINK, (px + dx, py + dy, 1, 1))
    s.fill(art.PURPLE_DARK, (c.x + 4, c.bottom - 6, c.w - 8, 3))
    return s


def _back_row():
    """A dim heap of plushies behind the real ones, so the machine looks full."""
    w = cm.FIELD_W
    s = pygame.Surface((w, 16), pygame.SRCALPHA)
    ordinary = [p for p in cm.PLUSHIES if not p.hidden]
    for i, x in enumerate(range(cm.CHUTE_W + 10, w - 6, 13)):
        spec = ordinary[(i * 4 + 1) % len(ordinary)]
        img = art.plush_sprite(spec).copy()
        img.fill((84, 74, 128, 255), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(img, img.get_rect(midbottom=(x, 16 - (i % 2) * 2)))
    return s
