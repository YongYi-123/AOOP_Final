"""Hud: all 2D overlay drawing in a chunky arcade style (pixel fonts, outlined text, no panels)."""
import math
import pygame
import settings as S
from race import State
from modes import GameMode
from endless import fmt_time
from assets import PixelFont, BLACK, WHITE, YELLOW, ORANGE, RED, CYAN, GREEN
from menu_layout import (CARD_SIZE, CHECKER_Y, CONTENT, FOOTER, MARGIN, PANEL_HOT, SCREEN, TITLE_Y,
                         fit_font, mix, panel, pulse)

DIM = (140, 140, 170)
PINK = (255, 110, 150)          # lock messages

# The key names printed on the screens. An embedding program (the arcade) swaps in
# the playing player's real keys through Hud.keys; standalone they are the defaults.
DEFAULT_KEYS = {
    "accelerate": "UP", "brake": "DOWN", "steer": "LEFT/RIGHT", "confirm": "ENTER",
    "back": "ESC", "item": "SPACE / SHIFT", "item_long": "SPACE  (OR SHIFT / Z / X / CTRL)",
    "resume": "P / ENTER / ESC", "menu": "BACKSPACE", "quit": "Q",
}


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
        self.keys = dict(DEFAULT_KEYS)
        self.trace = None        # tests set a list here; every text() then records (rect, message)
        self._dim = pygame.Surface(SCREEN.size, pygame.SRCALPHA)       # darkens the race behind the pause card
        self._dim.fill((0, 0, 20, 150))
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
        if self.trace is not None:
            self.trace.append((pygame.Rect(x - pad, y - pad, *img.get_size()), msg))

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
                self.text(surf, self.keys["item"], (74, 214), WHITE, self.small)
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

    BANNER_Y = 112      # between the two HUD columns, under the TIME readout: never over the stat blocks

    def draw_banner(self, surf, manager):
        """CHECKPOINT! / LEVEL n message; fades out over the last part of its lifetime. Kept to the
        centre strip (smaller than the title screens) so the road and the HUD stay readable."""
        if manager.banner_time <= 0:
            return
        a = int(255 * min(1.0, manager.banner_alpha * 2))
        cx, y = S.WIDTH // 2, self.BANNER_Y
        for i, line in enumerate(manager.banner):
            if i == 0 and a == 255:
                self.extruded(surf, line, (cx, y), YELLOW, (150, 60, 0), self.huge, 4)
            elif i == 0:            # fading out: plain text (alpha can't be applied to the stacked copies)
                self.text(surf, line, (cx, y), YELLOW, self.huge, "center", a)
            else:
                self.text(surf, line, (cx, y + 52 + (i - 1) * 40), WHITE, self.big, "center", a)

    def draw_countdown(self, surf, label):
        """Giant 3 / 2 / 1."""
        colors = {"3": RED, "2": ORANGE, "1": YELLOW}
        self.text(surf, label, (S.WIDTH // 2, 150), colors.get(label, GREEN), self.giant, "center")

    def draw_go(self, surf, remaining):
        a = int(255 * min(1.0, remaining / (S.GO_TIME * 0.5)))
        self.text(surf, "GO!", (S.WIDTH // 2, 150), GREEN, self.giant, "center", a)

    def draw_pause(self, surf, t):
        surf.blit(self._dim, (0, 0))
        surf.blit(self.scanlines, (0, 0))
        k, cx = self.keys, S.WIDTH // 2
        box = pygame.Rect(0, 0, 600, 290)
        box.center = (cx, 300)
        panel(surf, box)
        self.extruded(surf, "PAUSED", (cx, box.y + 22), YELLOW, (150, 60, 0), self.huge, 3)
        rows = [(k["resume"], "RESUME"), (k["menu"], "QUIT TO MENU"), (k["quit"], "QUIT GAME")]
        self.key_table(surf, pygame.Rect(box.x, box.y + 100, box.w, 130), rows)
        self.text(surf, f"ITEM: {k['item_long']}", (cx, box.bottom - 44), CYAN, self.small, "center")

    def draw_toast(self, surf, msg):
        self.text(surf, msg, (S.WIDTH // 2, S.HEIGHT - 110), WHITE, self.font, "center")

    # ---- full-screen screens ------------------------------------------------
    @staticmethod
    def _checker(surf, y, cell=16):
        for i in range(S.WIDTH // cell + 1):
            pygame.draw.rect(surf, WHITE if i % 2 else BLACK, (i * cell, y, cell, cell // 2))
            pygame.draw.rect(surf, BLACK if i % 2 else WHITE, (i * cell, y + cell // 2, cell, cell // 2))

    def card_size(self, n=3):
        """Preview size of a track card (one size for every card, whatever the track count)."""
        return CARD_SIZE

    def key_table(self, surf, rect, rows, pitch=38):
        """Rows of (keys, action): keys right-aligned to one column, actions left-aligned to the next,
        the pair centred in `rect`. Falls back to the small font when a player's key names are long."""
        for font in (self.font, self.small):
            kw = max(font.render(k, False, WHITE).get_width() for k, _ in rows)
            aw = max(font.render(a, False, WHITE).get_width() for _, a in rows)
            if kw + 28 + aw <= rect.w - 32 or font is self.small:
                break
        x0 = rect.centerx - (kw + 28 + aw) // 2
        for i, (keys, action) in enumerate(rows):
            y = rect.y + i * pitch
            self.text(surf, keys, (x0 + kw, y), YELLOW, font, "right")
            self.text(surf, action, (x0 + kw + 28, y), WHITE, font)

    def footer_hints(self, surf, items):
        """The footer panel: [(keys, action)] centred as KEYS ACTION, keys in yellow. The player's own
        key names go in `keys`, so P1 and P2 each see their own."""
        panel(surf, FOOTER)
        widths = [(self.small.render(k, False, WHITE).get_width() if k else 0,
                   self.small.render(a, False, WHITE).get_width()) for k, a in items]
        sep, gap = 8, 26
        total = lambda g: sum(kw + (sep if kw else 0) + aw for kw, aw in widths) + g * (len(items) - 1)
        while gap > 10 and total(gap) > FOOTER.w - 24:
            gap -= 2
        x, y = FOOTER.centerx - total(gap) // 2, FOOTER.centery - 8
        for (keys, action), (kw, aw) in zip(items, widths):
            if keys:
                self.text(surf, keys, (x, y), YELLOW, self.small)
                x += kw + sep
            self.text(surf, action, (x, y), CYAN, self.small)
            x += aw + gap

    def _prompt(self, surf, t, msg, y):
        """The primary call to action: a panel whose border and text breathe between white and yellow.
        (The modes' texts say ENTER; the player's own confirm key is printed instead.)"""
        msg = msg.replace("ENTER", self.keys["confirm"])
        font = fit_font((self.big, self.font, self.small), msg, S.WIDTH - 2 * MARGIN - 48)
        w, h = font.render(msg, False, WHITE).get_size()
        rect = pygame.Rect(0, y, w + 48, h + 20)
        rect.centerx = S.WIDTH // 2
        k = pulse(t)
        panel(surf, rect, edge=mix((140, 120, 40), PANEL_HOT, k), alpha=230)
        self.text(surf, msg, (rect.centerx, rect.y + 10), mix(WHITE, YELLOW, k), font, "center")
        return rect

    def draw_start(self, surf, t):
        surf.blit(self.scanlines, (0, 0))
        cx, k = S.WIDTH // 2, self.keys
        self.extruded(surf, "RETRO", (cx, 20), RED, (110, 0, 20), self.huge, 3)
        self.extruded(surf, "GRAND PRIX", (cx, 76), YELLOW, (150, 60, 0), self.huge, 3)
        self._checker(surf, 140)
        rows = [(k["accelerate"], "ACCELERATE"), (k["brake"], "BRAKE"), (k["steer"], "STEER"), (k["back"], "QUIT")]
        box = pygame.Rect(0, 176, 500, len(rows) * 38 + 26)
        box.centerx = cx
        panel(surf, box)
        self.key_table(surf, pygame.Rect(box.x, box.y + 14, box.w, box.h - 14), rows)
        strip = pygame.Rect(0, box.bottom + 12, box.w, 34)          # the secondary shortcuts: smaller, apart
        strip.centerx = cx
        panel(surf, strip, alpha=190)
        self.text(surf, "M = MAP    N = MUTE    [ ] = VOLUME", (cx, strip.y + 9), CYAN, self.small, "center")
        self._prompt(surf, t, "PRESS ENTER TO START", strip.bottom + 22)

    def menu_frame(self, surf, title):
        surf.blit(self.scanlines, (0, 0))
        self._checker(surf, CHECKER_Y)
        self.extruded(surf, title, (S.WIDTH // 2, TITLE_Y), YELLOW, (150, 60, 0), self.huge, 3)

    def draw_mode_select(self, surf, options, index, t):
        """options: [(name, description, ai level name or None)]. The AI row and its hint appear only
        while a mode that has AI opponents is highlighted."""
        k = self.keys
        self.menu_frame(surf, "SELECT MODE")
        has_ai = options[index][2] is not None
        self.footer_hints(surf, [(f"{k['accelerate']}/{k['brake']}", "MODE")]
                          + ([(k["steer"], "AI LEVEL")] if has_ai else [])
                          + [(k["confirm"], "SELECT"), (k["back"], "BACK")])
        card_h, gap = 132, 24
        top = CONTENT.y + (CONTENT.h - (len(options) * card_h + (len(options) - 1) * gap)) // 2
        cx = S.WIDTH // 2
        for i, (name, desc, ai) in enumerate(options):
            on = i == index
            rect = pygame.Rect(0, top + i * (card_h + gap), 560, card_h)
            rect.centerx = cx
            panel(surf, rect, edge=mix((120, 100, 40), PANEL_HOT, pulse(t)) if on else None, alpha=228 if on else 150)
            self.text(surf, name, (cx, rect.y + 10), YELLOW if on else DIM, self.huge, "center")
            self.text(surf, desc, (cx, rect.y + 72), WHITE if on else (130, 130, 165), self.small, "center")
            if ai and on:
                self.text(surf, f"AI LEVEL:  < {ai} >", (cx, rect.y + 94), ORANGE, self.font, "center")
            if on and int(t * 3) % 2 == 0:
                self.text(surf, ">", (rect.x + 30, rect.y + 10), RED, self.huge)
                self.text(surf, "<", (rect.right - 30 - 33, rect.y + 10), RED, self.huge)

    def draw_track_select(self, surf, cards, index, t, scenery="", track_lock="", scenery_lock=""):
        """cards: [(name, preview_surface, tagline[, locked])]. Three previews (previous, selected, next)
        with no names under them; the selected track's name, tagline and unlock status go in one info
        panel. `track_lock` / `scenery_lock` are the lock messages (with price) of the selected items."""
        k, n, cx = self.keys, len(cards), S.WIDTH // 2
        self.menu_frame(surf, "SELECT TRACK")
        self.footer_hints(surf, [(f"{k['accelerate']}/{k['brake']}", "TRACK"), (k["steer"], "SCENERY"),
                                 (k["confirm"], "OK"), (k["back"], "BACK")])
        self.text(surf, f"TRACK {index + 1} / {n}", (cx, 112), CYAN, self.small, "center")
        w, h = CARD_SIZE
        gap, y = 16, 140
        offsets = (-1, 0, 1) if n >= 3 else tuple(range(n))
        total = len(offsets) * w + (len(offsets) - 1) * gap
        x0 = (S.WIDTH - total) // 2
        for slot, off in enumerate(offsets):
            name, preview, tagline, *rest = cards[(index + off) % n]
            x, on = x0 + slot * (w + gap), off == 0
            pygame.draw.rect(surf, (YELLOW if int(t * 4) % 2 == 0 else WHITE) if on else (40, 40, 70),
                             (x - 6, y - 6, w + 12, h + 12))
            surf.blit(preview, (x, y))
            if not on:
                shade = pygame.Surface((w, h), pygame.SRCALPHA)
                shade.fill((0, 0, 20, 130))
                surf.blit(shade, (x, y))
            if rest and rest[0]:                                        # a small LOCKED tag, top-left
                tag = pygame.Rect(x + 4, y + 4, 74, 21)
                pygame.draw.rect(surf, (20, 10, 35), tag)
                self.text(surf, "LOCKED", (tag.x + 5, tag.y + 2), PINK, self.small, shadow=False)
        name, _, tagline, *_ = cards[index]
        info = pygame.Rect(x0 - 6, 284, total + 12, 96)
        panel(surf, info, edge=PANEL_HOT, alpha=228)
        self.text(surf, name, (info.x + 18, info.y + 12), YELLOW, fit_font((self.big, self.font), name, info.w - 36 - 190))
        self.text(surf, track_lock or "UNLOCKED", (info.right - 18, info.y + 22), PINK if track_lock else GREEN,
                  self.small, "right")
        self.text(surf, tagline, (info.x + 18, info.y + 58), CYAN, self.small)
        self.text(surf, f"SCENERY: {scenery}", (info.x, 390), CYAN, self.small)
        if scenery_lock:
            self.text(surf, scenery_lock, (info.right, 390), PINK, self.small, "right")

    def draw_end(self, surf, manager, state, t, end_t):
        surf.blit(self.scanlines, (0, 0))
        cx, k = S.WIDTH // 2, self.keys
        title, rows = manager.summary(state, end_t)
        flash = (YELLOW, WHITE, ORANGE) if state is State.FINISHED else (RED, WHITE, RED)
        self._checker(surf, CHECKER_Y)
        self.extruded(surf, title, (cx, TITLE_Y), flash[int(t * 5) % 3], (110, 40, 0),
                      fit_font((self.huge, self.big), title, S.WIDTH - 2 * MARGIN - 20), 3)
        order = manager.standings_lines(state)
        top = 126
        if order:       # race results: stats on the left, finishing order on the right
            stats = pygame.Rect(MARGIN, top, 360, 300)
            board = pygame.Rect(stats.right + 16, top, S.WIDTH - MARGIN - stats.right - 16, 300)
            panel(surf, stats)
            panel(surf, board)
            for i, (label, value) in enumerate(rows):
                y = stats.y + 22 + i * 62
                self.text(surf, label, (stats.x + 18, y), CYAN, self.small)
                self.text(surf, value, (stats.x + 18, y + 20), YELLOW, self.font)
            self.text(surf, "FINAL ORDER", (board.x + 18, board.y + 12), CYAN, self.small)
            swatches = manager.standings_colors(state)
            for i, line in enumerate(order):
                y, mine = board.y + 40 + i * 41, line.endswith("PLAYER")
                if mine:        # highlighted band + arrow so the player's row can't be missed
                    band = pygame.Rect(board.x + 10, y - 3, board.w - 20, 38)
                    pygame.draw.rect(surf, (96, 72, 0), band)
                    pygame.draw.rect(surf, YELLOW, band, 2)
                    pygame.draw.polygon(surf, YELLOW, ((band.x + 8, y + 6), (band.x + 8, y + 26), (band.x + 22, y + 16)))
                if i < len(swatches):
                    pygame.draw.rect(surf, swatches[i], (board.x + 34, y + 8, 18, 18))
                    pygame.draw.rect(surf, YELLOW if mine else (0, 0, 0), (board.x + 34, y + 8, 18, 18), 2)
                self.text(surf, line, (board.x + 64, y), YELLOW if mine else WHITE, self.font)
        else:
            box = pygame.Rect(0, top, 520, 300)
            box.centerx = cx
            panel(surf, box)
            step = 62 if len(rows) <= 4 else 52
            for i, (label, value) in enumerate(rows):
                y = box.y + 24 + i * step
                self.text(surf, label, (box.x + 26, y), CYAN, self.big)
                self.text(surf, value, (box.right - 26, y), YELLOW, self.big, "right")
        self._prompt(surf, t, manager.again_text, 446)
        self.footer_hints(surf, [(k["menu"], "MENU")])
