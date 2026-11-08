"""The main quest's screens: the corner objective tracker, the NEW MAIN QUEST / LEGACY PROTOCOL banner and the
Quest Log (Q). All pixel-art neon panels from ui.py, drawn on the same 400x300 canvas as the rooms.

* ObjectiveTracker  small, bottom-right, sitting just above the TOKENS / TICKETS box (so it never covers the wallet,
                    the controls box on the left, a machine prompt or the player). A little pulse when the objective
                    or its progress changes.
* QuestBanner       slides in from the top for a few seconds, one announcement after another, then leaves.
* QuestLogUI        a room modal: main quest, current objective, completed quests, Miao Meow's hint, secret items
                    and trials, the wallet. Q or ESC closes it. It never opens the quest system's own state: it only reads.
"""
import math
from collections import deque

import pygame

from font import get_font
from gfx import scale_color
from hud import _ticket_icon, _token_icon
from miao_meow import miao_frame
from quests import SECRET_ITEMS_NEEDED, SECRET_TRIALS_NEEDED
from settings import BACK_KEYS, Col, VIEW_H, VIEW_W
from story_dialogue import framed_portrait, solid_panel
from ui import dim_screen, draw_text, wrap_text


def _key_chip(surf, key, pos, color=Col.CYAN):
    w = get_font().size(key)[0] + 6
    r = pygame.Rect(pos, (w, 11))
    pygame.draw.rect(surf, Col.PANEL, r)
    pygame.draw.rect(surf, color, r, 1)
    draw_text(surf, key, (r.x + 3, r.y + 2), color)
    return r


def _star(surf, cx, cy, color, size=3):
    for d in range(-size, size + 1):
        surf.set_at((cx + d, cy), color)
        surf.set_at((cx, cy + d), color)
    for d in (-1, 1):
        surf.set_at((cx + d, cy + d), scale_color(color, 0.7))
        surf.set_at((cx + d, cy - d), scale_color(color, 0.7))


# ------------------------------------------------------------------ objective tracker
class ObjectiveTracker:
    """The corner readout of the active quest, drawn bottom-right just above the TOKENS / TICKETS box(es).

        MAIN QUEST                [Q]       <- small label on the left, the Q shortcut alone in the right corner
        ------------------------------
        THE WAY OUT                         <- the title (wraps onto more rows when it is long)
        ITEMS 0/3    TRIALS 0/3             <- the objective, or the two secret counters, legible and apart

    The panel is as wide as its text needs (MIN_W..MAX_W, never wider than the free space left of the wallet box), has
    a single border and no glow on the text, and never overflows: long titles and objectives wrap onto more rows."""
    PAD = 6                     # space between the border and the text
    GAP = 8                     # minimum space between two things on the same row
    ROW = 10                    # row pitch of wrapped text
    MIN_W, MAX_W = 118, 196

    def __init__(self, manager):
        self.manager = manager
        self.pulse = 0.0
        self.appear = 0.0
        self._cache = (None, None)
        manager.on_change(self._changed)

    def _changed(self, kind):
        if kind in ("progress", "complete", "opening"):
            self.pulse = 1.0

    def update(self, dt):
        self.pulse = max(0.0, self.pulse - dt / 1.0)
        shown = self.manager.opening_done and self.manager.active is not None
        self.appear = min(1.0, self.appear + dt * 4) if shown else 0.0

    # ------------------------------------------------------------ layout (separate from drawing so it can be tested)
    def _detail(self):
        """The third line: the objective, or [(text, colour), ...] groups for the secret counters."""
        m, q = self.manager, self.manager.active
        if q.trigger[0] == "counters":
            return [(f"ITEMS {m.secret_items}/{SECRET_ITEMS_NEEDED}", Col.CYAN if m.secret_items < SECRET_ITEMS_NEEDED else Col.GREEN),
                    (f"TRIALS {m.secret_trials}/{SECRET_TRIALS_NEEDED}",
                     Col.PURPLE if m.secret_trials < SECRET_TRIALS_NEEDED else Col.GREEN)]
        return [(m.hud_text(), Col.TEXT)]

    def layout(self, max_width=None):
        """Where everything goes: {"size": (w, h), "label": Rect, "chip": Rect, "title": [(text, Rect)], "detail": [(text, colour, Rect)]}.
        All rects are inside the panel with PAD to spare; none overlap. `max_width` caps the panel (free space on screen)."""
        font = get_font()
        q = self.manager.active
        cap = min(self.MAX_W, max_width or self.MAX_W)
        inner_cap = cap - 2 * self.PAD
        label, chip_w = "MAIN QUEST", font.size("Q")[0] + 6
        header_w = font.size(label)[0] + self.GAP + chip_w
        title_rows = wrap_text(q.title.upper(), inner_cap)
        groups = self._detail()
        if len(groups) == 1:
            detail_rows = [[(t, c)] for t, c in
                           [(row, groups[0][1]) for row in wrap_text(groups[0][0], inner_cap)]]
        else:
            joined = sum(font.size(t)[0] for t, _ in groups) + self.GAP * 2 * (len(groups) - 1)
            detail_rows = [groups] if joined <= inner_cap else [[g] for g in groups]
        content_w = max([header_w] + [font.size(r)[0] for r in title_rows]
                        + [sum(font.size(t)[0] for t, _ in row) + self.GAP * 2 * (len(row) - 1) for row in detail_rows])
        w = max(self.MIN_W, min(cap, content_w + 2 * self.PAD))
        y = self.PAD
        label_rect = pygame.Rect(self.PAD, y, font.size(label)[0], 7)
        chip_rect = pygame.Rect(w - self.PAD - chip_w, y - 1, chip_w, 11)
        y += 15                                                             # header row + a hairline + air
        title = []
        for row in title_rows:
            title.append((row, pygame.Rect(self.PAD, y, font.size(row)[0], 7)))
            y += self.ROW
        y += 2
        detail = []
        for row in detail_rows:
            x = self.PAD
            for text, colour in row:
                r = pygame.Rect(x, y, font.size(text)[0], 7)
                detail.append((text, colour, r))
                x = r.right + self.GAP * 2 if len(row) > 1 else r.right
            y += self.ROW
        h = y + self.PAD - 3
        return {"size": (w, h), "label": label_rect, "chip": chip_rect, "title": title, "detail": detail,
                "rule_y": self.PAD + 11}

    def _free_width(self, room):
        """The width the tracker may use: from the right margin back to the controls box (plus a gap), never the whole screen."""
        box = getattr(getattr(room, "instructions", None), "image", None)
        left = (4 + box.get_width() + 8) if box is not None else 0
        return VIEW_W - 4 - max(left, VIEW_W - 4 - self.MAX_W)

    def _image(self, room=None):
        q = self.manager.active
        lit = self.pulse > 0 and int(self.pulse * 8) % 2 == 0
        free = self._free_width(room) if room is not None else self.MAX_W
        spec = self.layout(free)
        key = (q.id, tuple(t for t, _, _ in spec["detail"]), tuple(c for _, c, _ in spec["detail"]), lit, spec["size"])
        if self._cache[0] == key:
            return self._cache[1]
        w, h = spec["size"]
        img = solid_panel(w, h, Col.YELLOW if lit else Col.MAGENTA, None, 240)
        draw_text(img, "MAIN QUEST", spec["label"].topleft, scale_color(Col.MAGENTA, 0.95))
        _key_chip(img, "Q", spec["chip"].topleft, Col.CYAN)
        img.fill(scale_color(Col.MAGENTA, 0.45), (self.PAD, spec["rule_y"], w - 2 * self.PAD, 1))
        for text, rect in spec["title"]:
            draw_text(img, text, rect.topleft, Col.YELLOW)
        for text, colour, rect in spec["detail"]:
            draw_text(img, text, rect.topleft, colour)
        self._cache = (key, img)
        return img

    def rect(self, room, animated=True):
        """Where the tracker sits: bottom-right, just above the TOKENS / TICKETS box (or both boxes in a two-player game)."""
        img = self._image(room)
        tops = [h.rect.top for h in room.huds if getattr(h, "rect", None) is not None]
        bottom = (min(tops) if tops else VIEW_H - 34) - 3
        rise = int((1 - self.appear) * 8) + int(math.sin(self.pulse * math.pi * 3) * 2 * (self.pulse > 0)) if animated else 0
        return img.get_rect(bottomright=(VIEW_W - 4, bottom + rise))

    def draw(self, surf, room):
        if self.appear <= 0 or not self.manager.opening_done or self.manager.active is None:
            return
        img = self._image(room)
        img.set_alpha(int(255 * self.appear))
        surf.blit(img, self.rect(room))


# ------------------------------------------------------------------ banner
class QuestBanner:
    """NEW MAIN QUEST / LEGACY PROTOCOL ACTIVE, from the top edge, one at a time."""
    SLIDE = 0.35
    HOLD = {"quest": 3.4, "protocol": 4.6}

    def __init__(self):
        self.queue = deque()
        self.current = None
        self.age = 0.0
        self._images = {}

    @property
    def busy(self):
        return self.current is not None or bool(self.queue)

    def push(self, notification):
        self.queue.append(notification)

    def clear(self):
        self.queue.clear()
        self.current = None

    def update(self, dt):
        if self.current is None:
            if self.queue:
                self.current, self.age = self.queue.popleft(), 0.0
            return
        self.age += dt
        if self.age >= self.SLIDE * 2 + self.HOLD[self.current.kind]:
            self.current = None

    def _make(self, n):
        font = get_font()
        if n.kind == "protocol":
            w, h = 262, 52
            img = solid_panel(w, h, Col.GREEN, scale_color(Col.GREEN, 0.5), 246)
            draw_text(img, n.lines[0], (w // 2, 8), Col.GREEN, 1, "midtop", glow=(8, 60, 22))
            img.fill(scale_color(Col.GREEN, 0.5), (14, 20, w - 28, 1))
            draw_text(img, n.lines[1], (w // 2, 26), Col.TEXT, anchor="midtop")
            draw_text(img, n.lines[2], (w // 2, 37), Col.TEXT, anchor="midtop")
            return img
        q = n.quest
        w = max(236, font.size(q.title.upper())[0] * 2 + 28)
        rows = wrap_text("OBJECTIVE: " + q.objective.rstrip("."), w - 30)
        h = 46 + len(rows) * 10
        img = solid_panel(w, h, Col.MAGENTA, Col.YELLOW, 246)
        draw_text(img, "NEW MAIN QUEST", (w // 2, 7), Col.YELLOW, 1, "midtop", glow=scale_color(Col.MAGENTA, 0.9))
        img.fill(scale_color(Col.MAGENTA, 0.7), (14, 19, w - 28, 1))
        draw_text(img, q.title, (w // 2, 25), Col.CYAN, 2, "midtop", glow=scale_color(Col.CYAN, 0.4))
        for i, row in enumerate(rows):
            draw_text(img, row, (w // 2, 45 + i * 10), Col.TEXT_MUTED, anchor="midtop")
        for sx in (11, w - 12):
            _star(img, sx, 11, Col.YELLOW, 3)
        return img

    def draw(self, surf):
        if self.current is None:
            return
        n = self.current
        img = self._images.get(id(n))
        if img is None:
            img = self._images[id(n)] = self._make(n)
        total = self.SLIDE * 2 + self.HOLD[n.kind]
        k = min(1.0, self.age / self.SLIDE, (total - self.age) / self.SLIDE)
        ease = 1 - (1 - max(0.0, k)) ** 3
        y = int(-img.get_height() + (img.get_height() + 8) * ease)
        surf.blit(img, img.get_rect(midtop=(VIEW_W // 2, y)))


# ------------------------------------------------------------------ the quest log
def _gem_icon(index, found):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    c = (Col.CYAN, Col.MAGENTA, Col.YELLOW)[index % 3]
    pygame.draw.rect(s, (8, 6, 20, 255), (0, 0, 16, 16), border_radius=2)
    pygame.draw.rect(s, c if found else (70, 60, 110), (0, 0, 16, 16), 1, border_radius=2)
    if found:
        pygame.draw.polygon(s, c, [(8, 2), (13, 7), (8, 13), (3, 7)])
        pygame.draw.polygon(s, tuple(int(v * 0.55) for v in c), [(8, 7), (13, 7), (8, 13)])
        s.set_at((6, 5), (255, 255, 255))
    else:
        for x, y in ((7, 4), (8, 4), (9, 5), (9, 6), (8, 7), (8, 8), (8, 10)):
            s.set_at((x, y), (86, 76, 130))
    return s


def _door_icon(done, locked):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    border = Col.GREEN if done else ((70, 60, 110) if locked else Col.PURPLE)
    pygame.draw.rect(s, (8, 6, 20, 255), (0, 0, 16, 16), border_radius=2)
    pygame.draw.rect(s, border, (0, 0, 16, 16), 1, border_radius=2)
    pygame.draw.rect(s, (36, 26, 66), (4, 3, 8, 11))
    pygame.draw.rect(s, border, (4, 3, 8, 11), 1)
    if done:
        for x, y in ((5, 8), (6, 9), (7, 10), (8, 9), (9, 8), (10, 7), (11, 6)):
            s.set_at((x, y), Col.GREEN)
    else:
        pygame.draw.rect(s, (130, 120, 180), (6, 8, 4, 4))
        pygame.draw.rect(s, (130, 120, 180), (7, 6, 2, 3), 1)
    return s


class QuestLogUI:
    """The Quest Log modal (Q). Read-only view of the QuestManager plus one profile's wallet."""
    hides_hud = False

    def __init__(self, manager, profile, on_close=None):
        self.manager = manager
        self.profile = profile
        self.on_close = on_close
        self.extra_players = ()
        self.closed = False
        self.time = 0.0
        self._hint_face = framed_portrait(miao_frame(eyes="happy", level=3), 2)

    def handle_event(self, event):
        if self.closed or event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_q or event.key in BACK_KEYS:
            self.close()

    def close(self):
        if not self.closed:
            self.closed = True
            if self.on_close:
                self.on_close()

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        m = self.manager
        dim_screen(surf, 210)
        x, y, w, h = 20, 10, 360, 280
        surf.blit(solid_panel(w, h, Col.CYAN, Col.MAGENTA, 250), (x, y))
        draw_text(surf, "QUEST LOG", (x + w // 2, y + 8), Col.YELLOW, 2, "midtop", glow=scale_color(Col.MAGENTA, 0.9))
        surf.fill(scale_color(Col.CYAN, 0.6), (x + 12, y + 26, w - 24, 1))
        q = m.active
        lx = x + 14

        # ---- main quest + current objective
        draw_text(surf, "MAIN QUEST", (lx, y + 33), Col.CYAN)
        draw_text(surf, (q.title if q else "ALL QUESTS DONE"), (lx, y + 44), Col.YELLOW, glow=scale_color(Col.YELLOW, 0.3))
        draw_text(surf, "CURRENT OBJECTIVE", (lx, y + 62), Col.CYAN)
        if q:
            for i, row in enumerate(wrap_text(q.objective, 190)[:3]):
                draw_text(surf, row, (lx + 8, y + 74 + i * 10), Col.TEXT)
            p = m.progress(q)
            if p:
                bar = pygame.Rect(lx + 8, y + 106, 120, 5)
                pygame.draw.rect(surf, (40, 30, 80), bar)
                pygame.draw.rect(surf, Col.CYAN, (bar.x, bar.y, int(bar.w * p[0] / p[1]), 5))
                pygame.draw.rect(surf, scale_color(Col.CYAN, 0.55), bar, 1)
                draw_text(surf, f"{p[0]}/{p[1]}", (bar.right + 6, bar.y - 1), Col.CYAN)
            surf.fill(Col.YELLOW, (lx, y + 75, 2, 2))
        draw_text(surf, "COMPLETED", (lx, y + 122), Col.CYAN)
        done = m.completed
        if not done:
            draw_text(surf, "NOTHING YET", (lx + 8, y + 134), scale_color(Col.TEXT_MUTED, 0.8))
        for i, quest in enumerate(done[-4:]):
            oy = y + 134 + i * 10
            pygame.draw.rect(surf, Col.GREEN, (lx, oy, 7, 7), 1)
            for ox, dy in ((1, 3), (2, 4), (3, 3), (4, 2), (5, 1)):
                surf.set_at((lx + ox, oy + dy), Col.GREEN)
            draw_text(surf, quest.title.upper(), (lx + 12, oy), scale_color(Col.TEXT_MUTED, 0.9))

        # ---- hint from Miao Meow
        rx = x + 214
        draw_text(surf, "HINT FROM MIAO MEOW", (rx, y + 33), Col.MAGENTA, glow=scale_color(Col.MAGENTA, 0.3))
        surf.blit(self._hint_face, (rx, y + 45))
        hint = m.current_hint()
        draw_text(surf, "TALK TO HER", (rx + 50, y + 90), scale_color(Col.TEXT_MUTED, 0.9))
        draw_text(surf, "FOR MORE HINTS", (rx + 50, y + 100), scale_color(Col.TEXT_MUTED, 0.9))
        box = pygame.Rect(rx, y + 114, 132, 56)
        pygame.draw.rect(surf, (246, 242, 255), box)
        pygame.draw.rect(surf, Col.OUTLINE, box, 1)
        pygame.draw.polygon(surf, (246, 242, 255), [(rx + 16, box.y), (rx + 22, box.y - 6), (rx + 28, box.y)])
        if hint:
            rows = wrap_text(hint, box.w - 10)[:6]
            for i, row in enumerate(rows):
                draw_text(surf, row, (box.x + 5, box.y + 4 + i * 8), Col.OUTLINE)

        # ---- secrets and wallet
        by = y + 186
        surf.fill(scale_color(Col.CYAN, 0.45), (x + 12, by - 6, w - 24, 1))
        unlocked = m.protocol_active
        dim = Col.CYAN if unlocked else scale_color(Col.TEXT_MUTED, 0.8)
        draw_text(surf, "SECRET ITEMS", (lx, by), dim)
        draw_text(surf, f"{m.secret_items}/{SECRET_ITEMS_NEEDED}", (lx + 78, by), dim)
        for i in range(SECRET_ITEMS_NEEDED):
            surf.blit(_gem_icon(i, i < m.secret_items), (lx + i * 22, by + 12))
        tx = x + 118
        dim2 = Col.PURPLE if unlocked else scale_color(Col.TEXT_MUTED, 0.8)
        draw_text(surf, "SECRET TRIALS", (tx, by), dim2)
        draw_text(surf, f"{m.secret_trials}/{SECRET_TRIALS_NEEDED}", (tx + 84, by), dim2)
        for i in range(SECRET_TRIALS_NEEDED):
            surf.blit(_door_icon(i < m.secret_trials, not unlocked), (tx + i * 22, by + 12))
        if not unlocked:
            draw_text(surf, "LOCKED", (lx, by + 32), scale_color(Col.TEXT_MUTED, 0.7))
        wx = x + 246
        draw_text(surf, "WALLET", (wx, by), Col.YELLOW)
        surf.blit(_token_icon(), (wx, by + 14))
        draw_text(surf, "TOKENS", (wx + 11, by + 14), Col.TEXT_MUTED)
        draw_text(surf, f"{self.profile.tokens:02d}", (wx + 96, by + 13), Col.YELLOW, glow=scale_color(Col.YELLOW, 0.4),
                  anchor="topright")
        surf.blit(_ticket_icon(), (wx, by + 27))
        draw_text(surf, "TICKETS", (wx + 11, by + 27), Col.TEXT_MUTED)
        draw_text(surf, f"{self.profile.tickets:03d}", (wx + 96, by + 26), Col.MAGENTA, glow=scale_color(Col.MAGENTA, 0.4),
                  anchor="topright")

        # ---- footer
        surf.fill(scale_color(Col.CYAN, 0.45), (x + 12, y + h - 42, w - 24, 1))
        if unlocked:
            draw_text(surf, "THE ARCADE IS SEALED. FIND 3 SECRET ITEMS, BEAT 3 SECRET TRIALS.",
                      (x + w // 2, y + h - 35), scale_color(Col.TEXT_MUTED, 0.95), anchor="midtop")
        else:
            draw_text(surf, "KEEP EXPLORING THE ARCADE WITH MIAO MEOW.", (x + w // 2, y + h - 35),
                      scale_color(Col.TEXT_MUTED, 0.95), anchor="midtop")
        r = _key_chip(surf, "Q", (x + w // 2 - 54, y + h - 20), Col.CYAN)
        draw_text(surf, "/ ESC   CLOSE", (r.right + 5, y + h - 18), Col.TEXT_MUTED)
