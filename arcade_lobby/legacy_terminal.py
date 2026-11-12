"""ARCADE LEGACY SYSTEM: the mission terminal behind the vending machine's secret.

Reached from the vending machine's hidden screen (vending_ui.py keeps the secret code, the glitch and the first
page exactly as they were; once that page is typed, the use key opens this). It is the way in to the three Secret
Trials and shows the shared story's real progress and the real wallet of the player who opened it.

    SECRET ITEMS 0 / 3        SECRET TRIALS 0 / 3
    [01] THE GOLDEN AGE            STATUS: AVAILABLE
    [02] THE FORGOTTEN GAMES       STATUS: LOCKED        <- chapter 01 is not finished
    [03] THE FINAL CHALLENGE       STATUS: NEED EARNINGS <- chapter open, too little earned so far (TOKENS EARNED 8 / 30 ...)
    EXIT PROTOCOL: LOCKED

Rules live in quests.py (trial_status / exit_status): one trial per chapter, strictly in order, and each asks the
player to have EARNED Tokens and Tickets in total (settings.SECRET_TRIAL_EARNINGS; lifetime totals, never the wallet). Looking at this screen, or choosing a trial, never takes
anything from the wallet and never records progress; a completed trial stays open to replay whatever the wallet holds. The three escape rooms are not built yet:
choosing an available trial shows TRIAL NOT YET AVAILABLE. When one is built it registers a scene factory in
TRIAL_SCENES and the terminal starts it; nothing else here changes.

It is a MenuScene, and answers to the player's keys.
"""
import random

import pygame

from font import get_font
from golden_age_scene import GoldenAgeScene
from gfx import scale_color
from menu_kit import MenuScene
from quest_ui import _door_icon, _gem_icon
from quests import (CHAPTERS, FINAL_CHAPTER_TITLE, LOCK_CHAPTER, LOCK_EARNINGS, SECRET_ITEMS_NEEDED, SECRET_TRIALS_NEEDED,
                    TRIALS, exit_status, trial_status)
from settings import VIEW_H, VIEW_W, Col
from story_dialogue import solid_panel
from ui import draw_text, wrap_text

TITLE = "ARCADE LEGACY SYSTEM"
MUSIC_DUCK = 0.3                    # the secret page's own music level (vending_ui.SECRET_DUCK), kept while this is open
BG_TOP, BG_BOTTOM = (6, 8, 26), (22, 10, 44)
CYAN, SOFT_MAGENTA = Col.CYAN, (230, 110, 200)
GREEN = (110, 255, 170)
YELLOW = Col.YELLOW
ROW_Y, ROW_H = 84, 17
DETAIL = pygame.Rect(16, 142, VIEW_W - 32, 82)
BOOT_LINES = (("SYSTEM OVERRIDE", 2), ("", 1), ("USER: UNKNOWN", 1), ("ACCESS LEVEL: 01", 1), ("", 1), ("THE ARCADE REMEMBERS.", 1))
BOOT_RATE = 34                      # characters per second (the same typing speed the old page had)
BOOT_HOLD = 0.7                     # a beat after the last line before the system comes up

# trial id -> factory(game, owner) returning the escape-room scene. Trial 01 (THE GOLDEN AGE) is built; 02 and 03 are not yet.
TRIAL_SCENES = {"trial_01": GoldenAgeScene}

_static = {}


def _backdrop():
    """Dark navy-to-purple screen, a thin cyan frame with a soft magenta inner line, and faint scanlines (built once)."""
    bg = _static.get("bg")
    if bg is None:
        bg = pygame.Surface((VIEW_W, VIEW_H))
        for y in range(VIEW_H):
            t = y / (VIEW_H - 1)
            bg.fill(tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)), (0, y, VIEW_W, 1))
        pygame.draw.rect(bg, scale_color(CYAN, 0.7), (4, 4, VIEW_W - 8, VIEW_H - 8), 1)
        pygame.draw.rect(bg, scale_color(SOFT_MAGENTA, 0.45), (7, 7, VIEW_W - 14, VIEW_H - 14), 1)
        for cx, cy in ((4, 4), (VIEW_W - 8, 4), (4, VIEW_H - 5), (VIEW_W - 8, VIEW_H - 5)):
            bg.fill(Col.YELLOW, (cx, cy, 4, 1))
        _static["bg"] = bg
    return bg


def _crt():
    """Scanlines and a soft dark vignette over everything (built once)."""
    crt = _static.get("crt")
    if crt is None:
        crt = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        for y in range(0, VIEW_H, 2):
            crt.fill((0, 0, 0, 46), (0, y, VIEW_W, 1))
        for i in range(10):                                           # vignette: darker towards the edges
            a = int(70 * (1 - i / 9) ** 2)
            pygame.draw.rect(crt, (0, 0, 0, a), (i, i, VIEW_W - 2 * i, VIEW_H - 2 * i), 1)
        _static["crt"] = crt
    return crt


class LegacyTerminalScene(MenuScene):
    title = TITLE
    accent = CYAN
    glow = SOFT_MAGENTA
    music_duck = MUSIC_DUCK                 # (Game.duck_for reads this: the music stays low while the terminal is up)

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.manager = game.hub.story.manager
        self.index = 0
        self.notice = None                  # None, or {"title", "lines", "color"}: a card over the list
        self.hints = ("UP/DOWN", "SELECT", "BACK")
        self.confirm_label = owner.controls.label("interact") or "ENTER"
        self.boot_time = sum(len(text) + 4 for text, _ in BOOT_LINES) / BOOT_RATE + BOOT_HOLD   # the old secret page, typed first

    # ------------------------------------------------------------ data (the real thing, read every time)
    @property
    def trial(self):
        return TRIALS[self.index]

    def status(self, trial=None):
        return trial_status(self.manager, self.profile, trial or self.trial)

    def exit_state(self):
        return exit_status(self.manager)

    # ------------------------------------------------------------ input
    @property
    def booting(self):
        return self.time < self.boot_time

    def on_action(self, action):
        if self.booting:
            if action == "back":
                self.play("cancel")
                self.close()
            elif action == "interact":
                self.time = self.boot_time                                  # skip the typing
            return
        if self.notice is not None:
            if action in ("interact", "back"):
                self.notice = None
                self.play("cancel" if action == "back" else "confirm")
            return
        if action == "back":
            self.play("cancel")
            self.close()
        elif action in ("up", "left"):
            self.index = (self.index - 1) % len(TRIALS)
            self.play("vend_select")
        elif action in ("down", "right"):
            self.index = (self.index + 1) % len(TRIALS)
            self.play("vend_select")
        elif action == "interact":
            self.select()

    def select(self):
        """Choose the highlighted trial. Never charges, never records progress."""
        trial, status = self.trial, self.status()
        n = f"{trial.number:02d}"
        if status.code == "done" and trial.id in TRIAL_SCENES:
            self.game.scenes.push(TRIAL_SCENES[trial.id](self.game, self.owner))                  # a finished room can be played again
        elif status.code == "done":
            self.notice = {"title": f"TRIAL {n} COMPLETE", "lines": ["YOU HAVE ALREADY BEATEN THIS ONE."], "color": GREEN}
        elif status.code == "locked":
            self.play("cancel")
            if status.lock == LOCK_EARNINGS:
                self.notice = {"title": "EARNINGS REQUIRED", "color": YELLOW,
                               "lines": list(status.reasons) + ["SPENDING NEVER LOWERS WHAT YOU HAVE EARNED.", "NOTHING WAS CHARGED."]}
            else:
                self.notice = {"title": "ACCESS DENIED", "lines": list(status.reasons), "color": SOFT_MAGENTA}
        elif trial.id in TRIAL_SCENES:
            self.game.scenes.push(TRIAL_SCENES[trial.id](self.game, self.owner))
        else:
            self.notice = {"title": "TRIAL NOT YET AVAILABLE",
                           "lines": ["THIS ESCAPE ROOM IS STILL BEING BUILT.", "NOTHING WAS CHARGED OR RECORDED."],
                           "color": CYAN}

    # ------------------------------------------------------------ drawing
    def _boot(self, surf):
        """The page the secret screen always had (SYSTEM OVERRIDE ... THE ARCADE REMEMBERS), typed out in the terminal's colours."""
        shown = int(self.time * BOOT_RATE)
        x, y = 40, 70
        cursor = (x, y)
        for text, scale in BOOT_LINES:
            part = text[:max(0, shown)]
            shown -= len(text) + 4
            if part:
                rect = draw_text(surf, part, (x, y), CYAN if scale > 1 else Col.TEXT, scale, glow=scale_color(CYAN, 0.3) if scale > 1 else None)
                cursor = (rect.right + 2, y)
            y += 7 * scale + 7
        if int(self.time * 2.2) % 2 == 0:
            surf.fill(CYAN, (cursor[0], cursor[1], 5, 8))

    def draw(self, surf):
        surf.blit(_backdrop(), (0, 0))
        if self.booting:
            self._boot(surf)
            surf.blit(_crt(), (0, 0))
            return
        t = self.time
        shown = int((t - self.boot_time) * 30)
        self._header(surf, shown)
        if shown > 4:
            self._counters(surf)
            self._list(surf)
            self._detail(surf)
            self._footer(surf)
        if self.notice is not None:
            self._card(surf)
        surf.blit(_crt(), (0, 0))
        roll = (t * 40) % (VIEW_H + 60) - 30                          # a slow, faint bar rolling down the glass
        band = pygame.Surface((VIEW_W, 14), pygame.SRCALPHA)
        band.fill((120, 200, 255, 10))
        surf.blit(band, (0, int(roll)))
        if random.Random(int(t * 12)).random() < 0.04:                # an occasional one-line jitter
            y = random.Random(int(t * 12) + 1).randrange(12, VIEW_H - 14)
            surf.blit(surf.subsurface((8, y, VIEW_W - 16, 2)).copy(), (9, y))

    def _header(self, surf, shown):
        font = get_font()
        x0 = (VIEW_W - font.size(TITLE, 2)[0]) // 2                      # fixed left edge: the title types out in place
        part = TITLE[:max(0, shown)]
        if part:
            draw_text(surf, part, (x0, 14), CYAN, 2, glow=scale_color(CYAN, 0.35))
        if shown < len(TITLE) or int(self.time * 2) % 2 == 0:             # a blinking block cursor
            surf.fill(CYAN, (x0 + (font.size(part, 2)[0] + 3 if part else 0), 14, 7, 14))
        surf.fill(scale_color(CYAN, 0.5), (16, 34, VIEW_W - 32, 1))
        draw_text(surf, f"USER: {(self.profile.display_name or 'PLAYER').upper()}     {self.chapter_line()}", (VIEW_W // 2, 38),
                  scale_color(Col.TEXT_MUTED, 0.9), anchor="midtop")

    def chapter_line(self):
        """The chapter the story is in (the same one the Quest Log names)."""
        n = self.manager.current_chapter
        if n > len(CHAPTERS):
            return f"FINAL CHAPTER  {FINAL_CHAPTER_TITLE}"
        ch = CHAPTERS[max(n, 1) - 1]
        return f"{ch.label}  {ch.title}"

    def _counters(self, surf):
        m = self.manager
        y = 52
        for i, (label, have, need, icon, color) in enumerate(
                (("SECRET ITEMS", m.secret_items, SECRET_ITEMS_NEEDED, lambda k: _gem_icon(k, k < m.secret_items), CYAN),
                 ("SECRET TRIALS", m.secret_trials, SECRET_TRIALS_NEEDED, lambda k: _door_icon(k < m.secret_trials, False), SOFT_MAGENTA))):
            x = 18 + i * 190
            draw_text(surf, label, (x, y), color)
            draw_text(surf, f"{have} / {need}", (x + get_font().size(label)[0] + 8, y), Col.TEXT)
            for k in range(need):
                surf.blit(icon(k), (x + k * 19, y + 11))

    def _list(self, surf):
        for i, trial in enumerate(TRIALS):
            st = self.status(trial)
            y = ROW_Y + i * ROW_H
            selected = i == self.index
            if selected:
                bar = pygame.Surface((VIEW_W - 32, ROW_H - 2), pygame.SRCALPHA)
                bar.fill((*CYAN, 38))
                bar.fill((*CYAN, 170), (0, 0, 2, ROW_H - 2))
                surf.blit(bar, (16, y - 2))
                if int(self.time * 4) % 4 != 3:
                    draw_text(surf, ">", (22, y + 1), Col.YELLOW)
            name_color = Col.TEXT if st.code != "locked" else scale_color(Col.TEXT_MUTED, 0.9)
            draw_text(surf, f"[{trial.number:02d}] {trial.title}", (34, y + 1), name_color)
            color = YELLOW if st.lock == LOCK_EARNINGS else {"done": GREEN, "available": CYAN, "locked": SOFT_MAGENTA}[st.code]
            draw_text(surf, f"STATUS: {st.short}", (VIEW_W - 22, y + 1), color, anchor="topright")

    def detail_rows(self, trial=None):
        """What the detail panel says about `trial`: [(text, ok or None, extra)]. ok None is a plain line. Never names a
        puzzle's answer: a locked chapter says only which chapter to finish."""
        trial = trial or self.trial
        st = self.status(trial)
        rows = []
        built = trial.id in TRIAL_SCENES
        if st.code == "done":
            rows.append(("COMPLETE. REPLAYABLE." if built else "COMPLETE.", None, ""))
            if built:
                rows.append((f"[{self.confirm_label}] VISIT THE ROOM AGAIN. NOTHING MORE CAN BE EARNED.", None, ""))
            if self.manager.has_memory_fragment(trial.id):
                rows.append((f"MEMORY FRAGMENT {trial.number:02d} KEPT.", None, ""))
            return rows
        ch = CHAPTERS[trial.chapter - 1]
        if st.lock == LOCK_CHAPTER:
            rows.append((f"{ch.label} IS LOCKED.", None, ""))
            rows.append((st.reasons[0], False, ""))
        else:
            for key, name in trial.needs_items:
                rows.append((name, self.manager.has_secret_item(key), ""))
        if st.needs_earnings:
            rows.append((f"TOKENS EARNED: {st.tokens_earned} / {st.tokens_needed}", st.tokens_earned >= st.tokens_needed, ""))
            rows.append((f"TICKETS EARNED: {st.tickets_earned} / {st.tickets_needed}", st.tickets_earned >= st.tickets_needed, ""))
        if st.code == "available":
            rows.append((f"[{self.confirm_label}] ENTER THE ROOM." if built else "THE ESCAPE ROOM ITSELF IS NOT BUILT YET.", None, ""))
        return rows

    def _detail(self, surf):
        trial, st = self.trial, self.status()
        surf.blit(solid_panel(DETAIL.w, DETAIL.h, scale_color(CYAN, 0.7), None, 235), DETAIL.topleft)
        x, y = DETAIL.x + 8, DETAIL.y + 7
        draw_text(surf, f"TRIAL {trial.number:02d}  {trial.title}", (x, y), Col.YELLOW)
        color = YELLOW if st.lock == LOCK_EARNINGS else {"done": GREEN, "available": CYAN, "locked": SOFT_MAGENTA}[st.code]
        draw_text(surf, st.short, (DETAIL.right - 8, y), color, anchor="topright")
        y += 13
        for text, ok, extra in self.detail_rows(trial):
            if ok is None:
                c = GREEN if st.code in ("done", "available") else Col.TEXT_MUTED
                draw_text(surf, text, (x, y + 1), c)
            else:
                self._requirement(surf, x, y, text, ok, extra)
            y += 11
        if st.needs_earnings and st.code != "done":
            draw_text(surf, "LIFETIME EARNINGS. SPENDING NEVER LOWERS THEM.", (x, DETAIL.bottom - 12),
                      scale_color(Col.TEXT_MUTED, 0.8))

    @staticmethod
    def _requirement(surf, x, y, text, ok, extra=""):
        pygame.draw.rect(surf, GREEN if ok else SOFT_MAGENTA, (x, y, 7, 7), 1)
        if ok:
            for ox, oy in ((1, 3), (2, 4), (3, 3), (4, 2), (5, 1)):
                surf.set_at((x + ox, y + oy), GREEN)
        draw_text(surf, text, (x + 12, y), Col.TEXT if ok else scale_color(Col.TEXT, 0.85))
        if extra:
            draw_text(surf, extra, (x + 150, y), GREEN if ok else SOFT_MAGENTA)

    def _footer(self, surf):
        unlocked, reasons = self.exit_state()
        y = 232
        label = "UNLOCKED" if unlocked else "LOCKED"
        draw_text(surf, f"EXIT PROTOCOL: {label}", (18, y), GREEN if unlocked else SOFT_MAGENTA)
        if not unlocked:
            draw_text(surf, "  /  ".join(reasons), (18, y + 11), scale_color(Col.TEXT_MUTED, 0.85))
        else:
            draw_text(surf, "FINAL CHAPTER OPEN. THE REOPENING ITSELF IS NOT BUILT YET.", (18, y + 11), scale_color(Col.TEXT_MUTED, 0.85))
        key = self.confirm_label
        draw_text(surf, f"[{key}] SELECT      [ESC] BACK", (VIEW_W // 2, VIEW_H - 26), scale_color(CYAN, 0.9), anchor="midtop")

    def _card(self, surf):
        n = self.notice
        rows = []
        for line in n["lines"]:
            rows += wrap_text(line, 270)
        w, h = 292, 44 + len(rows) * 10
        x, y = (VIEW_W - w) // 2, (VIEW_H - h) // 2 - 6
        dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        surf.blit(dim, (0, 0))
        surf.blit(solid_panel(w, h, n["color"], SOFT_MAGENTA, 248), (x, y))
        draw_text(surf, n["title"], (x + w // 2, y + 9), n["color"], 1, "midtop", glow=scale_color(n["color"], 0.3))
        surf.fill(scale_color(n["color"], 0.5), (x + 12, y + 21, w - 24, 1))
        for i, row in enumerate(rows):
            draw_text(surf, row, (x + w // 2, y + 28 + i * 10), Col.TEXT, anchor="midtop")
        draw_text(surf, f"[{self.confirm_label}] OK", (x + w // 2, y + h - 12), scale_color(Col.TEXT_MUTED, 0.9), anchor="midtop")
