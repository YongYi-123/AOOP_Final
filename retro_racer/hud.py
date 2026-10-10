"""Hud: all 2D overlay drawing in a chunky arcade style (pixel fonts, outlined text, no panels)."""
import math
import pygame
import settings as S
from race import State
from modes import GameMode
from endless import fmt_time
from assets import PixelFont, BLACK, WHITE, YELLOW, ORANGE, RED, CYAN, GREEN

DIM = (140, 140, 170)


class Hud:
    def __init__(self):
        # Non-bold at 22+ px: the built-in font's bold M turns into a solid block at smaller sizes.
        self.small = PixelFont(22, 1)
        self.font = PixelFont(22, 2)
        self.big = PixelFont(24, 2)
        self.huge = PixelFont(24, 3)
        self.title = PixelFont(24, 5)
        self.giant = PixelFont(24, 10)
        self._outlined = {}
        self.time = 0.0          # animation clock, set by Game each frame
        # Every other scanline darkened: the classic arcade-monitor look, used behind full-screen screens.
        self.scanlines = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        for y in range(0, S.HEIGHT, 2):
            self.scanlines.fill((0, 0, 24, 170), (0, y, S.WIDTH, 1))

    def prewarm(self):
        """Render the big, one-off overlays once at load time.

        Profiling showed the remaining frame spikes were the first draw of GO!, the countdown digits and the
        CHECKPOINT / LAP banners (10x-scaled outlined pixel text). Building them here moves that cost to
        start-up, where nobody is racing.
        """
        scratch = pygame.Surface((S.WIDTH, S.HEIGHT))

        class _Banner:                      # stand-in for a mode manager's banner fields
            def __init__(self, lines, alpha):
                self.banner, self.banner_time, self.banner_alpha = lines, 1.0, alpha
        for label in ("3", "2", "1"):
            self.draw_countdown(scratch, label)
        self.draw_go(scratch, S.GO_TIME)
        self.draw_go(scratch, S.GO_TIME * 0.25)
        for lines in (["CHECKPOINT!", f"+{S.CHECKPOINT_BONUS} SEC"], ["FINAL LAP!"], ["LAP 2"], ["LAP 3"]) +                 tuple([f"LEVEL {n}", "TRAFFIC UP"] for n in range(2, S.ENDLESS_LEVELS + 1)):
            self.draw_banner(scratch, _Banner(lines, 1.0))          # extruded (full alpha) version
            self.draw_banner(scratch, _Banner(lines, 0.2))          # fading version
        self.draw_pause(scratch, 0.0)
        for pos in range(1, S.RACE_OPPONENTS + 2):
            self.text(scratch, f"{pos}/{S.RACE_OPPONENTS + 1}", (0, 0), YELLOW, self.big)

    # ---- text primitives ----------------------------------------------------
    def _outline(self, font, msg, color):
        key = (id(font), msg, color)
        img = self._outlined.get(key)
        if img is None:
            if len(self._outlined) > 400:
                for old in list(self._outlined)[:150]:       # evict the oldest, never a wholesale clear (no hitch)
                    del self._outlined[old]
            o = getattr(font, "scale", 1)
            base, dark = font.render(msg, False, color), font.render(msg, False, BLACK)
            img = pygame.Surface((base.get_width() + 2 * o, base.get_height() + 2 * o), pygame.SRCALPHA)
            for dx in (0, o, 2 * o):
                for dy in (0, o, 2 * o):
                    if (dx, dy) != (o, o):
                        img.blit(dark, (dx, dy))
            img.blit(base, (o, o))
            self._outlined[key] = img
        return img

    def text(self, surf, msg, pos, color=YELLOW, font=None, align="left", alpha=255, shadow=True):
        """`shadow` = draw the black arcade outline (turned off for text on a bright highlight)."""
        font = font or self.font
        if shadow:
            img, pad = self._outline(font, msg, color), getattr(font, "scale", 1)
        else:
            img, pad = font.render(msg, False, color), 0
        x, y = pos
        if align == "right":
            x -= img.get_width() - pad
        elif align == "center":
            x -= img.get_width() // 2
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        surf.blit(img, (x - pad, y - pad))

    def extruded(self, surf, msg, pos, color, shade, font, depth=6, align="center"):
        """Chunky 3D block lettering: a stack of offset dark copies under the coloured text."""
        x, y = pos
        plain = font.render(msg, False, shade)
        w = plain.get_width()
        x0 = x - w // 2 if align == "center" else x
        step = getattr(font, "scale", 1)
        for d in range(depth, 0, -1):
            surf.blit(plain, (x0 + d * step // 2, y + d * step // 2))
        self.text(surf, msg, (x0 + w // 2, y), color, font, "center")

    # ---- in-race HUD (one layout per mode, same screen positions) -----------
    def draw_hud(self, surf, player, manager):
        kmh = int(player.speed_ratio * S.DISPLAY_MAX_KMH)
        km = player.distance / S.SEGMENT_LENGTH / 100     # 1 segment = 10 m
        self.text(surf, "SPEED", (20, 12), CYAN)
        self.text(surf, f"{kmh:3d} KM/H", (20, 38), RED if player.speed_percent > 0.9 else YELLOW, self.big)
        self.text(surf, "SCORE", (20, 84), CYAN)
        self.text(surf, f"{int(player.score):07d}", (20, 110), YELLOW, self.big)
        self.text(surf, "DISTANCE", (S.WIDTH - 230, 84), CYAN, align="right")
        self.text(surf, f"{km:5.2f} KM", (S.WIDTH - 230, 110), YELLOW, self.big, align="right")
        hot = player.hit_cooldown > 0
        if manager.mode is GameMode.ENDLESS:
            self.text(surf, "SURVIVAL TIME", (S.WIDTH // 2, 8), CYAN, self.small, align="center")
            self.text(surf, fmt_time(manager.elapsed), (S.WIDTH // 2, 30), YELLOW, self.huge, align="center")
            self.text(surf, "LEVEL", (S.WIDTH - 230, 12), CYAN, align="right")
            self.text(surf, f"{manager.level}", (S.WIDTH - 230, 38), YELLOW, self.big, align="right")
            crashes = f"{player.collisions}/{manager.max_crashes}"
        else:
            blink = manager.time_left <= 10 and int(manager.time_left * 3) % 2 == 0
            self.text(surf, "TIME", (S.WIDTH // 2, 8), CYAN, align="center")
            self.text(surf, f"{math.ceil(manager.time_left):02d}", (S.WIDTH // 2, 30),
                      RED if blink or manager.time_left <= 5 else YELLOW, self.huge, align="center")
            self.text(surf, "LAP", (S.WIDTH - 230, 12), CYAN, align="right")
            self.text(surf, f"{manager.lap}/{manager.laps}", (S.WIDTH - 230, 38), YELLOW, self.big, align="right")
            crashes = f"{player.collisions:02d}"
            self._draw_race_extras(surf, player, manager)
        self.text(surf, "COLLISIONS", (20, S.HEIGHT - 66), CYAN)
        self.text(surf, crashes, (20, S.HEIGHT - 44), RED if hot else YELLOW, self.big)

    def _draw_race_extras(self, surf, player, manager):
        """Competitive-only HUD: race position (right) and the held item (left)."""
        pos = manager.position_of(player)
        if pos:
            self.text(surf, "POSITION", (S.WIDTH - 20, 156), CYAN, align="right")
            self.text(surf, f"{pos[0]}/{pos[1]}", (S.WIDTH - 20, 182), YELLOW, self.big, align="right")
        self.text(surf, "ITEM", (20, 156), CYAN)
        if player.item is not None:
            player.item.draw_icon(surf, pygame.Rect(20, 182, 44, 44))
            self.text(surf, player.item.name, (74, 186), YELLOW, self.font)
            if int(self.time * 3) % 2 == 0:
                self.text(surf, "SPACE / SHIFT", (74, 214), WHITE, self.small)
        else:
            self.text(surf, "NONE", (20, 184), DIM, self.font)

    def card_size(self, n):
        """Preview size for n track cards side by side."""
        w = (S.WIDTH - 48 - 16 * (n - 1)) // n
        return w, int(w * 0.6)

    def draw_track_name(self, surf, name, note=""):
        self.text(surf, name, (S.WIDTH - 20, S.HEIGHT - 34), DIM, self.small, "right")
        if note:
            self.text(surf, note, (S.WIDTH - 20, S.HEIGHT - 58), DIM, self.small, "right")

    def draw_banner(self, surf, manager):
        """CHECKPOINT! / LEVEL n message; fades out over the last part of its lifetime."""
        if manager.banner_time <= 0:
            return
        a = int(255 * min(1.0, manager.banner_alpha * 2))
        cx = S.WIDTH // 2
        for i, line in enumerate(manager.banner):
            if i == 0 and a == 255:
                self.extruded(surf, line, (cx, 150), YELLOW, (150, 60, 0), self.title, 4)
            elif i == 0:            # fading out: plain text (alpha can't be applied to the stacked copies)
                self.text(surf, line, (cx, 150), YELLOW, self.title, "center", a)
            else:
                self.text(surf, line, (cx, 150 + 100 + (i - 1) * 60), WHITE, self.huge, "center", a)

    def draw_countdown(self, surf, label):
        """Giant 3 / 2 / 1."""
        colors = {"3": RED, "2": ORANGE, "1": YELLOW}
        self.text(surf, label, (S.WIDTH // 2, 150), colors.get(label, GREEN), self.giant, "center")

    def draw_go(self, surf, remaining):
        a = int(255 * min(1.0, remaining / (S.GO_TIME * 0.5)))
        self.text(surf, "GO!", (S.WIDTH // 2, 150), GREEN, self.giant, "center", a)

    def draw_pause(self, surf, t):
        surf.blit(self.scanlines, (0, 0))
        cx = S.WIDTH // 2
        self.extruded(surf, "PAUSED", (cx, 140), YELLOW, (150, 60, 0), self.title, 8)
        for i, (key, action) in enumerate((("P / ENTER / ESC", "RESUME"), ("BACKSPACE", "QUIT TO MENU"), ("Q", "QUIT GAME"))):
            self.text(surf, key, (cx - 20, 290 + i * 40), YELLOW, self.font, "right")
            self.text(surf, action, (cx + 20, 290 + i * 40), WHITE, self.font)
        self.text(surf, "ITEM: SPACE  (OR SHIFT / Z / X / CTRL)", (cx, 440), CYAN, self.small, "center")

    def draw_toast(self, surf, msg):
        self.text(surf, msg, (S.WIDTH // 2, S.HEIGHT - 110), WHITE, self.font, "center")

    # ---- full-screen screens ------------------------------------------------
    @staticmethod
    def _checker(surf, y, cell=16):
        for i in range(S.WIDTH // cell + 1):
            pygame.draw.rect(surf, WHITE if i % 2 else BLACK, (i * cell, y, cell, cell // 2))
            pygame.draw.rect(surf, BLACK if i % 2 else WHITE, (i * cell, y + cell // 2, cell, cell // 2))

    def _prompt(self, surf, t, msg, y):
        if int(t * 2.5) % 2 == 0:
            self.text(surf, msg, (S.WIDTH // 2, y), WHITE, self.big, "center")

    def draw_start(self, surf, t):
        surf.blit(self.scanlines, (0, 0))
        cx = S.WIDTH // 2
        self.extruded(surf, "RETRO", (cx, 36), RED, (110, 0, 20), self.title, 8)
        self.extruded(surf, "GRAND PRIX", (cx, 118), YELLOW, (150, 60, 0), self.title, 8)
        self._checker(surf, 210)
        rows = [("UP", "ACCELERATE"), ("DOWN", "BRAKE"), ("LEFT/RIGHT", "STEER"), ("ESC", "QUIT")]
        for i, (key, action) in enumerate(rows):
            self.text(surf, key, (cx - 20, 262 + i * 36), YELLOW, self.font, "right")
            self.text(surf, action, (cx + 20, 262 + i * 36), WHITE, self.font)
        self.text(surf, "M = MAP    N = MUTE    [ ] = VOLUME", (cx, 424), CYAN, self.small, "center")
        self._prompt(surf, t, "PRESS ENTER TO START", 480)

    def menu_frame(self, surf, title, footer):
        surf.blit(self.scanlines, (0, 0))
        self._checker(surf, 30)
        self.extruded(surf, title, (S.WIDTH // 2, 70), YELLOW, (150, 60, 0), self.huge, 6)
        self.text(surf, footer, (S.WIDTH // 2, S.HEIGHT - 56), CYAN, self.small, "center")

    def _arrows(self, surf, cx, cy, kind, color):
        """Little triangle pair: kind 'ud' (up/down) or 'lr' (left/right), centred at (cx, cy)."""
        d = 7
        if kind == "ud":
            pts = (((cx, cy - 12), (cx - d, cy - 3), (cx + d, cy - 3)), ((cx, cy + 12), (cx - d, cy + 3), (cx + d, cy + 3)))
        else:
            pts = (((cx - 14, cy), (cx - 5, cy - d), (cx - 5, cy + d)), ((cx + 14, cy), (cx + 5, cy - d), (cx + 5, cy + d)))
        for tri in pts:
            pygame.draw.polygon(surf, BLACK, tri, 3)
            pygame.draw.polygon(surf, color, tri)

    def hint_row(self, surf, y, items):
        """Centered control hints. items: [(icon 'ud' / 'lr' / None, label)] drawn as [arrows] LABEL."""
        parts = []
        for icon, label in items:
            w = self.small.render(label, False, WHITE).get_width()
            parts.append((icon, label, w + (32 if icon else 0)))
        total = sum(p[2] for p in parts) + 34 * (len(parts) - 1)
        x = (S.WIDTH - total) // 2
        for icon, label, w in parts:
            if icon:
                self._arrows(surf, x + 12, y + 10, icon, YELLOW)
                self.text(surf, label, (x + 32, y), CYAN, self.small)
            else:
                self.text(surf, label, (x, y), CYAN, self.small)
            x += w + 34

    def draw_mode_select(self, surf, options, index, t):
        """options: [(name, description, ai level name or None)]. The AI row and its hint appear only
        while a mode that has AI opponents is highlighted."""
        self.menu_frame(surf, "SELECT MODE", "")
        has_ai = options[index][2] is not None
        hints = [("ud", "MODE")] + ([("lr", "AI LEVEL")] if has_ai else []) + [(None, "ENTER SELECT"), (None, "ESC BACK")]
        self.hint_row(surf, S.HEIGHT - 60, hints)
        cx = S.WIDTH // 2
        for i, (name, desc, ai) in enumerate(options):
            y = 165 + i * 160
            on = i == index
            self.text(surf, name, (cx, y), YELLOW if on else DIM, self.huge, "center")
            self.text(surf, desc, (cx, y + 62), WHITE if on else (100, 100, 130), self.small, "center")
            if ai and on:
                self.text(surf, f"AI LEVEL:  < {ai} >", (cx, y + 92), ORANGE, self.font, "center")
            if on and int(t * 3) % 2 == 0:
                self.text(surf, ">", (cx - 250, y), RED, self.huge, "center")
                self.text(surf, "<", (cx + 250, y), RED, self.huge, "center")

    def draw_track_select(self, surf, cards, index, t, scenery=""):
        """cards: [(name, preview_surface, tagline)]."""
        self.menu_frame(surf, "SELECT TRACK", "UP/DOWN TRACK  LEFT/RIGHT SCENERY  ENTER OK  ESC BACK")
        self.text(surf, f"SCENERY: {scenery}", (S.WIDTH // 2, 160), CYAN, self.small, "center")
        n, gap = len(cards), 16
        w = cards[0][1].get_width()
        x0 = (S.WIDTH - (n * w + (n - 1) * gap)) // 2
        for i, (name, preview, tagline) in enumerate(cards):
            x, y = x0 + i * (w + gap), 200
            on = i == index
            border = (YELLOW if int(t * 4) % 2 == 0 else WHITE) if on else (40, 40, 70)
            pygame.draw.rect(surf, border, (x - 6, y - 6, preview.get_width() + 12, preview.get_height() + 12))
            surf.blit(preview, (x, y))
            if not on:
                shade = pygame.Surface(preview.get_size(), pygame.SRCALPHA)
                shade.fill((0, 0, 20, 120))
                surf.blit(shade, (x, y))
            self.text(surf, name, (x + w // 2, y + preview.get_height() + 22), YELLOW if on else DIM, self.font, "center")
        self.text(surf, cards[index][2], (S.WIDTH // 2, 420), CYAN, self.font, "center")

    def draw_end(self, surf, manager, state, t, end_t):
        surf.blit(self.scanlines, (0, 0))
        cx = S.WIDTH // 2
        title, rows = manager.summary(state, end_t)
        flash = (YELLOW, WHITE, ORANGE) if state is State.FINISHED else (RED, WHITE, RED)
        self._checker(surf, 60)
        self._checker(surf, 500)
        self.extruded(surf, title, (cx, 96), flash[int(t * 5) % 3], (110, 40, 0),
                      self.title if len(title) <= 8 else self.huge, 6)
        order = manager.standings_lines(state)
        if order:       # race results: stats on the left, finishing order on the right
            for i, (label, value) in enumerate(rows):
                y = 190 + i * 50
                self.text(surf, label, (40, y), CYAN, self.font)
                self.text(surf, value, (400, y), YELLOW, self.font, "right")
            self.text(surf, "FINAL ORDER", (450, 158), CYAN, self.small)
            swatches = manager.standings_colors(state)
            for i, line in enumerate(order):
                y, mine = 190 + i * 36, line.endswith("PLAYER")
                if mine:        # highlighted band + arrow so the player's row can't be missed
                    pygame.draw.rect(surf, (96, 72, 0), (420, y - 5, 372, 38))
                    pygame.draw.rect(surf, YELLOW, (420, y - 5, 372, 38), 2)
                    pygame.draw.polygon(surf, YELLOW, ((428, y + 2), (428, y + 22), (442, y + 12)))
                if i < len(swatches):
                    pygame.draw.rect(surf, swatches[i], (452, y + 4, 18, 18))
                    pygame.draw.rect(surf, YELLOW if mine else (0, 0, 0), (452, y + 4, 18, 18), 2)
                self.text(surf, line, (480, y), YELLOW if mine else WHITE, self.font)
        else:
            step = 56 if len(rows) > 3 else 62
            for i, (label, value) in enumerate(rows):
                y = 196 + i * step
                self.text(surf, label, (150, y), CYAN, self.big)
                self.text(surf, value, (S.WIDTH - 150, y), YELLOW, self.big, "right")
        self._prompt(surf, t, manager.again_text, 432)
        self.text(surf, "BACKSPACE = MENU", (cx, 470), DIM, self.small, "center")
