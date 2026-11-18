"""TRIAL 02's pop-up screens: the documents (poster, ticket, ledger, leaderboard, maintenance log), the registration
terminal and its three code wheels, and the finish card. They follow golden_age_ui's Panel contract (handle_event /
update / draw, then `closed` and `result`) and its warm wooden frame; they never touch the story or the save.
"""
import math
import random

import pygame

import golden_age_ui as GU
import unbeaten_art as A
import unbeaten_content as C
import unbeaten_record as T
from gfx import scale_color
from settings import VIEW_H, VIEW_W
from ui import draw_text, wrap_text

Panel, nav, warm_panel, dim, hint_line = GU.Panel, GU.nav, GU.warm_panel, GU.dim, GU.hint_line
ConfirmPanel = GU.ConfirmPanel
INK, INK_SOFT, BRASS, GREEN = GU.INK, GU.INK_SOFT, GU.BRASS, GU.GREEN
RED = (255, 110, 120)
PAPER, PAPER_INK, PAPER_SOFT = (240, 226, 196), (60, 40, 30), (130, 104, 84)


class DocumentPanel(Panel):
    """One document, read on screen. E / ESC closes it."""

    def __init__(self, kind, play=None):
        self.kind = kind
        self.doc = C.DOCS[kind]
        self.play = play
        self.time = 0.0
        if play:
            play("page_turn")

    def handle_event(self, event):
        if nav(event) in ("ok", "back"):
            self.close("closed")

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        dim(surf, 160)
        getattr(self, "_" + self.kind)(surf)
        hint_line(surf, "[E] DONE", VIEW_H - 22)

    # ---- the pages
    def _poster(self, surf):
        d = self.doc
        width = 336
        lines = [r for line in d["lines"] for r in wrap_text(line, width - 24)]
        footer = [r for line in d["footer"] for r in wrap_text(line, width - 24)]
        height = 40 + len(lines) * 11 + 6 + len(d["table"]) * 13 + 8 + len(footer) * 11 + 10
        frame = pygame.Rect(0, 0, width, height)
        frame.center = (VIEW_W // 2, 134)
        pygame.draw.rect(surf, (20, 10, 30), frame.inflate(4, 4))
        for y in range(frame.h):
            surf.fill(A.mix((60, 24, 90), (24, 14, 50), y / frame.h), (frame.x, frame.y + y, frame.w, 1))
        pygame.draw.rect(surf, A.NEON_GOLD, frame, 1)
        draw_text(surf, "NEON CORNER ARCADE PRESENTS", (frame.centerx, frame.y + 8), A.NEON_CYAN, anchor="midtop")
        draw_text(surf, d["title"], (frame.centerx, frame.y + 20), A.NEON_GOLD, 1, "midtop", glow=(90, 50, 20))
        y = frame.y + 36
        for line in lines:
            draw_text(surf, line, (frame.centerx, y), (230, 220, 250), anchor="midtop")
            y += 11
        y += 6
        cols = (frame.x + 14, frame.x + 106, frame.x + 250)
        for i, row in enumerate(d["table"]):
            color = A.NEON_PINK if i == 0 else (240, 232, 250)
            if i:
                surf.fill((50, 28, 80), (frame.x + 8, y - 2, frame.w - 16, 11))
            for x, cell in zip(cols, row):
                draw_text(surf, cell, (x, y), color)
            y += 13
        y += 8
        for line in footer:
            draw_text(surf, line, (frame.centerx, y), A.NEON_CYAN, anchor="midtop")
            y += 11

    def _ticket(self, surf):
        """The stub from the lost and found: what was paid is printed; the check-in stamp sits on the torn edge, so only
        the start of its time survives."""
        d = self.doc
        w, h = 200, 128
        tk = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        tk.fill((40, 26, 20))
        tk.fill(PAPER, (2, 2, w, h))
        tk.fill((214, 90, 100), (2, 2, 26, h))                                # the stub band
        for y in range(6, h - 2, 6):
            tk.fill(PAPER, (27, y, 2, 3))
        draw_text(tk, "NO.", (6, 10), PAPER)
        draw_text(tk, d["title"], (36, 10), (180, 50, 70), 2)
        printed, (label, value) = d["lines"][:-1], d["lines"][-1].split(": ")
        for i, line in enumerate(printed):
            draw_text(tk, line, (36, 30 + i * 12), PAPER_INK)
        y = 30 + len(printed) * 12 + 4
        lab = draw_text(tk, label + ":", (36, y + 4), PAPER_INK)
        stamp = pygame.Rect(lab.right + 4, y - 2, 60, 20)                   # the red rubber stamp, over the torn edge
        pygame.draw.rect(tk, (200, 70, 80), stamp, 1)
        img = draw_text(tk, value, (stamp.x + 4, stamp.y + 3), (200, 70, 80), 2)
        tear = img.right + 2
        tk.fill((200, 70, 80), (tear - 1, stamp.y + 3, 1, 4))                 # a sliver of the next digit
        tk.fill((150, 110, 90), (40, h - 12, 60, 1))
        draw_text(tk, "NAME", (36, h - 9), PAPER_SOFT)
        rng = random.Random(7)
        points = [(tear + rng.randint(0, 3), -1)] + [(tear + rng.randint(0, 4), yy) for yy in range(0, h + 6, 6)]
        pygame.draw.polygon(tk, (0, 0, 0, 0), [(w + 5, -1)] + points + [(w + 5, h + 5)])     # torn away: nothing there
        pygame.draw.lines(tk, (200, 180, 150), False, points, 1)
        rect = tk.get_rect(center=(VIEW_W // 2 + (w - tear) // 2, 126))
        surf.blit(tk, rect)
        draw_text(surf, "THE NAME LINE IS BLURRED. THE RIGHT EDGE IS TORN OFF.", (VIEW_W // 2, rect.bottom + 10), INK_SOFT, anchor="midtop")

    def _ledger(self, surf):
        d = self.doc
        rows = d["rows"]
        frame = pygame.Rect(0, 0, 300, 50 + len(rows) * 12 + 22)
        frame.center = (VIEW_W // 2, 128)
        pygame.draw.rect(surf, (90, 30, 30), frame.inflate(6, 6))
        surf.fill(PAPER, frame)
        surf.fill((214, 200, 170), (frame.centerx - 1, frame.y, 2, frame.h))
        draw_text(surf, d["title"], (frame.centerx, frame.y + 6), (120, 40, 40), anchor="midtop")
        cols = (frame.x + 14, frame.x + 46, frame.x + 186, frame.x + 252)
        y = frame.y + 22
        for x, cell in zip(cols, d["head"]):
            draw_text(surf, cell, (x, y), (120, 40, 40))
        surf.fill((180, 150, 120), (frame.x + 10, y + 10, frame.w - 20, 1))
        y += 14
        top = y
        for i, (n, name, paid, clock, note) in enumerate(rows):
            if clock >= T.WAITING_LIST_FROM and (i == 0 or rows[i - 1][3] < T.WAITING_LIST_FROM):
                surf.fill((200, 80, 80), (frame.x + 10, y - 2, frame.w - 20, 1))     # registration closed here
            draw_text(surf, n, (cols[0], y), PAPER_INK)
            if name is None:
                for k in range(9):
                    surf.fill((150, 110, 70), (cols[1] + k * 9 + (k % 3), y + 2 + (k % 2) * 2, 7, 3))
            else:
                draw_text(surf, name, (cols[1], y), PAPER_INK)
            draw_text(surf, paid, (cols[2], y), PAPER_INK)
            draw_text(surf, clock, (cols[3], y), PAPER_INK)
            if note:
                pygame.draw.line(surf, (190, 40, 50), (frame.x + 10, y + 3), (frame.right - 10, y + 3), 1)
                draw_text(surf, note, (cols[1] + 86, y), (190, 40, 50))
            y += 12
        stain = pygame.Surface((100, (len(rows) - 2) * 12), pygame.SRCALPHA)
        for i in range(10):
            pygame.draw.ellipse(stain, (190, 130, 60, 26), (i * 3, i * 6, 100 - i * 6, stain.get_height() - i * 11))
        surf.blit(stain, (cols[1] - 8, top + 12))
        draw_text(surf, d["note"], (frame.right - 12, frame.bottom - 14), (200, 80, 80), anchor="topright")

    def _leaderboard(self, surf):
        d = self.doc
        frame = pygame.Rect(0, 0, 330, 150)
        frame.center = (VIEW_W // 2, 124)
        pygame.draw.rect(surf, A.WOOD_DK, frame.inflate(8, 8))
        surf.fill((14, 16, 30), frame)
        draw_text(surf, d["title"], (frame.centerx, frame.y + 8), A.NEON_GOLD, 2, "midtop", glow=(90, 60, 10))
        y = frame.y + 34
        flick = int(self.time * 10) % 23 == 0 or 1.6 < self.time % 5.0 < 1.75
        for i, (rank, name, score, when) in enumerate(d["rows"]):
            top = i == 0
            color = A.NEON_GOLD if top else (180, 190, 230)
            if top and flick:
                name, color = d["glitch_name"], (255, 90, 130)
            draw_text(surf, rank, (frame.x + 12, y), color)
            draw_text(surf, name, (frame.x + 36, y), color)
            draw_text(surf, score, (frame.x + 140, y), color)
            draw_text(surf, when, (frame.x + 200, y), scale_color(color, 0.8))
            y += 16
        draw_text(surf, d["note"], (frame.centerx, frame.bottom - 14), (150, 160, 200), anchor="midtop")

    def _slips(self, surf):
        d = self.doc
        frame = pygame.Rect(0, 0, 340, 200)
        frame.center = (VIEW_W // 2, 128)
        pygame.draw.rect(surf, A.WOOD_DK, frame.inflate(8, 8))
        surf.fill((150, 110, 70), frame)
        draw_text(surf, d["title"], (frame.centerx, frame.y + 6), (255, 240, 200), anchor="midtop")
        for i, (head, winner, time, note) in enumerate(d["slips"]):
            box = pygame.Rect(frame.x + 8 + (i % 2) * 166, frame.y + 22 + (i // 2) * 76, 158, 70)
            surf.fill((250, 246, 230), box)
            for k in range(box.x + 3, box.right - 3, 6):                     # the perforated top edge
                surf.fill((150, 110, 70), (k, box.y, 3, 1))
            draw_text(surf, head, (box.x + 6, box.y + 5), (60, 50, 70))
            for k in range(2):                                              # the printer's smudge, where names were
                surf.fill((170, 160, 170), (box.x + 6 + k * 70, box.y + 17, 60, 6))
            draw_text(surf, winner, (box.x + 6, box.y + 27), (150, 40, 60))
            draw_text(surf, time, (box.x + 96, box.y + 27), (60, 50, 70))
            for j, row in enumerate(wrap_text(note, box.w - 12)):
                draw_text(surf, row, (box.x + 6, box.y + 40 + j * 10), (60, 50, 70))
        draw_text(surf, d["note"], (frame.centerx, frame.bottom - 12), (255, 240, 200), anchor="midtop")

    def _champ_note(self, surf):
        d = self.doc
        frame = pygame.Rect(0, 0, 300, 164)
        frame.center = (VIEW_W // 2, 126)
        pygame.draw.rect(surf, (40, 26, 20), frame.inflate(4, 4))
        surf.fill((236, 220, 170), frame)
        for k in range(0, frame.w, 7):                                       # an old fold, and some age
            surf.fill((220, 200, 150), (frame.x + k, frame.centery, 4, 1))
        draw_text(surf, d["title"], (frame.x + 14, frame.y + 10), (110, 60, 40))
        for i, line in enumerate(d["lines"]):
            draw_text(surf, line, (frame.x + 14 + (i % 3 == 1), frame.y + 26 + i * 12), (70, 50, 40))

    def _notes(self, surf):
        d = self.doc
        frame = pygame.Rect(0, 0, 300, 120)
        frame.center = (VIEW_W // 2, 126)
        pygame.draw.rect(surf, (40, 26, 20), frame.inflate(4, 4))
        surf.fill((250, 244, 200), frame)
        for yy in range(frame.y + 24, frame.bottom, 14):
            surf.fill((200, 210, 230), (frame.x + 4, yy + 9, frame.w - 8, 1))
        surf.fill((240, 150, 150), (frame.x + 24, frame.y, 1, frame.h))
        draw_text(surf, d["title"], (frame.centerx, frame.y + 6), (60, 60, 120), anchor="midtop")
        for i, line in enumerate(d["lines"]):
            draw_text(surf, line, (frame.x + 30, frame.y + 24 + i * 14), (50, 50, 90))


class BracketPanel(Panel):
    """THE BROKEN BRACKET: the board, to put right. UP/DOWN pick a slot (or CHECK), LEFT/RIGHT change the name in it,
    E marks the slot's player as the winner of its match (or, on CHECK, asks the board). Slots 1 and 2 are fixed.
    X / BACKSPACE / DELETE empties the slot under the cursor; CLEAR wipes every name and winner mark in one go.
    Names already placed are skipped; nothing is ever filled in for the player. Solved: the board is read only."""
    ROW_H = 21

    def __init__(self, run, draft, play=None):
        self.run = run
        self.draft = draft
        self.play = play
        self.row = 0                        # 0..5 the open slots 3..8, 6 = CHECK, 7 = CLEAR
        self.reply = None
        self.time = 0.0
        self.solved = run.bracket

    def _sound(self, name):
        if self.play:
            self.play(name)

    ROWS = 8
    CLEAR_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_DELETE)

    def handle_event(self, event):
        if wants_evidence(event):
            self.close("evidence")
            return
        act = nav(event)
        if act is None and event.type == pygame.KEYDOWN and event.key in self.CLEAR_KEYS and not self.solved:
            if self.row < 6:
                self.draft.clear_slot(T.BRACKET_SLOTS[self.row])
            else:
                self.draft.clear()
            self.reply = None
            self._sound("circuit_click")
            return
        if act is None:
            return
        if act == "back":
            self.close("solved" if self.solved else "closed")
            return
        if self.solved:
            if act == "ok":
                self.close("solved")
            return
        if act in ("up", "down"):
            self.row = (self.row + (-1 if act == "up" else 1)) % self.ROWS
            self._sound("vend_select")
        elif act in ("left", "right") and self.row < 6:
            self.draft.cycle(T.BRACKET_SLOTS[self.row], -1 if act == "left" else 1)
            self.reply = None
            self._sound("circuit_click")
        elif act == "ok":
            if self.row < 6:
                self.draft.mark_winner(T.BRACKET_SLOTS[self.row])
                self._sound("confirm")
            elif self.row == 7:
                self.draft.clear()
                self.reply = None
                self._sound("cancel")
            else:
                result = self.run.solve_bracket(self.draft)
                self.reply = result
                if result == "ok":
                    self.solved = True
                    self._sound("power_on")
                else:
                    self._sound("cancel")

    def update(self, dt):
        self.time += dt

    def slot_name(self, slot):
        if slot in T.BRACKET_FIXED:
            return T.BRACKET_FIXED[slot]
        return self.draft.slots.get(slot)

    def draw(self, surf):
        dim(surf, 170)
        frame = pygame.Rect(6, 6, VIEW_W - 12, VIEW_H - 12)
        pygame.draw.rect(surf, A.WOOD_DK, frame)
        board = frame.inflate(-6, -6)
        surf.fill((20, 16, 36), board)
        draw_text(surf, "TONIGHT'S BRACKET", (board.centerx, board.y + 4), A.NEON_GOLD, anchor="midtop")
        draw_text(surf, "[TAB] EVIDENCE", (board.right - 6, board.y + 4), (150, 150, 185), anchor="topright")
        x0, y0, bw = board.x + 40, board.y + 18, 106
        for m in range(len(T.MATCHES)):                     # MATCH 1..4 down the left, as the referee's slips number them
            top = y0 + m * 2 * self.ROW_H + m * 2
            mid = top + (2 * self.ROW_H - 6) // 2
            col = (150, 140, 190) if m else (110, 100, 150)
            draw_text(surf, "MATCH", (board.x + 21, mid - 5), col, anchor="midtop")
            draw_text(surf, str(m + 1), (board.x + 21, mid + 4), A.NEON_GOLD if m else col, anchor="midtop")
            pygame.draw.line(surf, (90, 80, 130), (x0 - 4, top + 3), (x0 - 4, top + 2 * self.ROW_H - 9))
        for i in range(8):
            slot = i + 1
            y = y0 + i * self.ROW_H + (i // 2) * 2
            box = pygame.Rect(x0, y, bw, 15)
            open_row = slot in T.BRACKET_SLOTS
            sel = open_row and not self.solved and self.row == T.BRACKET_SLOTS.index(slot)
            surf.fill((44, 34, 70) if open_row else (34, 30, 50), box)
            pygame.draw.rect(surf, A.NEON_CYAN if sel else (90, 80, 130), box, 1)
            name = self.slot_name(slot)
            draw_text(surf, str(slot), (box.x + 3, box.y + 4), (150, 140, 190))
            draw_text(surf, name or "- - -", (box.x + 14, box.y + 4), (240, 232, 250) if name else (110, 100, 150))
            if slot in self.draft.winners:
                pygame.draw.polygon(surf, A.NEON_GOLD, [(box.right + 2, box.y + 3), (box.right + 8, box.centery), (box.right + 2, box.bottom - 3)])
            if sel and int(self.time * 3) % 2 == 0:
                draw_text(surf, "<", (box.x - 7, box.y + 4), A.NEON_CYAN)
                draw_text(surf, ">", (box.right - 7, box.y + 4), A.NEON_CYAN)
        # the semifinal and final columns follow the winner marks
        sx = x0 + bw + 14
        for m in range(2):
            names = []
            for pair in T.MATCHES[m * 2:m * 2 + 2]:
                win = next((s for s in pair if s in self.draft.winners), None)
                names.append(self.slot_name(win) if win else None)
            for k, name in enumerate(names):
                y = y0 + (m * 4 + k * 2) * self.ROW_H + m * 4 + k * 2 + self.ROW_H // 2
                box = pygame.Rect(sx, y, 104, 15)
                surf.fill((50, 30, 60), box)
                pygame.draw.rect(surf, A.NEON_PINK, box, 1)
                draw_text(surf, name or "?", (box.x + 4, box.y + 4), (240, 232, 250))
        fx = sx + 112
        box = pygame.Rect(fx, y0 + 4 * self.ROW_H - 6, 54, 15)
        surf.fill((40, 30, 20), box)
        pygame.draw.rect(surf, A.NEON_GOLD, box, 1)
        draw_text(surf, "FINAL", box.center, A.NEON_GOLD, 1, "center")
        ry = y0 + 8 * self.ROW_H + 8
        for i, rule in enumerate(T.BRACKET_RULES):
            draw_text(surf, rule, (board.x + 8, ry + i * 9), (180, 190, 230))
        check = pygame.Rect(board.right - 64, board.bottom - 40, 56, 16)
        sel = self.row == 6 and not self.solved
        pygame.draw.rect(surf, (90, 56, 30) if sel else (46, 28, 20), check)
        pygame.draw.rect(surf, A.BRASS_LT if sel else GU.PANEL_IN, check, 1)
        draw_text(surf, "CHECK", check.center, INK if sel else INK_SOFT, 1, "center")
        clear = check.move(-62, 0)
        if not self.solved:
            sel = self.row == 7
            pygame.draw.rect(surf, (90, 40, 40) if sel else (46, 24, 24), clear)
            pygame.draw.rect(surf, A.BRASS_LT if sel else GU.PANEL_IN, clear, 1)
            draw_text(surf, "CLEAR", clear.center, INK if sel else INK_SOFT, 1, "center")
        if self.solved:
            draw_text(surf, "BRACKET RESTORED", (check.x - 8, check.y + 4), GREEN, anchor="topright")
        elif self.reply == "wrong":
            draw_text(surf, "IT STILL DOESN'T ADD UP.", (clear.x - 8, clear.y + 4), RED, anchor="topright")
        elif self.reply == "incomplete":
            draw_text(surf, "EVERY SLOT NEEDS A NAME.", (clear.x - 8, clear.y + 4), RED, anchor="topright")
        hint = "[E] DONE" if self.solved else "UP/DOWN SLOT  LEFT/RIGHT NAME  [E] WINNER  [X] EMPTY  [ESC] BACK"
        draw_text(surf, hint, (board.centerx, board.bottom - 12), (150, 150, 185), anchor="midtop")


def wants_evidence(event):
    """TAB, inside a puzzle: look at the evidence file (the puzzle waits, exactly as it was)."""
    return event.type == pygame.KEYDOWN and event.key == pygame.K_TAB


class EvidencePanel(Panel):
    """The evidence file. Two pages (LEFT/RIGHT): ITEMS (every document and board found) and WHAT PEOPLE SAID (every
    clue heard from someone). UP/DOWN pick, E reads it again, ESC (or TAB) closes. Results: an item key, or
    "said:<person>:<phase>"."""
    LABELS = {"poster": "TOURNAMENT POSTER", "ticket": "OLD TICKET", "ledger": "REGISTRATION LEDGER",
              "bracket": "TOURNAMENT BRACKET", "slips": "MATCH RECORDS", "photos": "TROPHY PHOTOGRAPHS",
              "champ_note": "CHAMPION'S NOTE"}
    TABS = ("ITEMS", "WHAT PEOPLE SAID")
    ROWS = 9

    def __init__(self, items, said=(), play=None):
        self.items = list(items)
        self.said = list(said)              # (tag, name, when)
        self.tab = 0
        self.index = 0
        self.top = 0
        self.play = play
        self.time = 0.0

    @property
    def rows(self):
        return self.items if self.tab == 0 else self.said

    def handle_event(self, event):
        act = nav(event)
        if act == "back" or wants_evidence(event):
            self.close(None)
        elif act in ("left", "right"):
            self.tab = 1 - self.tab
            self.index = self.top = 0
            if self.play:
                self.play("page_turn")
        elif act in ("up", "down") and self.rows:
            self.index = (self.index + (-1 if act == "up" else 1)) % len(self.rows)
            self.top = min(max(self.top, self.index - self.ROWS + 1), self.index)
            if self.play:
                self.play("vend_select")
        elif act == "ok" and self.rows:
            row = self.rows[self.index]
            self.close(row if self.tab == 0 else "said:" + row[0])

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        dim(surf, 150)
        rect = pygame.Rect(0, 0, 250, 52 + self.ROWS * 15)
        rect.center = (VIEW_W // 2, VIEW_H // 2 - 8)
        warm_panel(surf, rect, "EVIDENCE")
        for i, name in enumerate(self.TABS):
            x = rect.x + 14 + i * 76
            on = i == self.tab
            label = f"{name} ({len(self.items) if i == 0 else len(self.said)})"
            w = len(label) * 6 + 8
            if on:
                surf.fill((70, 44, 26), (x - 4, rect.y + 25, w, 11))
            draw_text(surf, label, (x, rect.y + 27), INK if on else INK_SOFT)
        rows = self.rows
        if not rows:
            empty = "NOTHING FOUND YET." if self.tab == 0 else "NOBODY HAS TOLD YOU ANYTHING USEFUL YET."
            draw_text(surf, empty, (rect.centerx, rect.y + 48), INK_SOFT, 1, "midtop")
        for i in range(self.top, min(len(rows), self.top + self.ROWS)):
            y = rect.y + 44 + (i - self.top) * 15
            sel = i == self.index
            if sel:
                surf.fill((70, 44, 26), (rect.x + 10, y - 3, rect.w - 20, 13))
                if int(self.time * 3) % 2 == 0:
                    draw_text(surf, ">", (rect.x + 14, y), BRASS)
            row = rows[i]
            label = self.LABELS[row] if self.tab == 0 else row[1]
            draw_text(surf, label, (rect.x + 26, y), INK if sel else INK_SOFT)
            if self.tab == 1:
                draw_text(surf, row[2], (rect.right - 14, y), (150, 120, 90), anchor="topright")
        if self.top > 0:
            draw_text(surf, "^", (rect.right - 10, rect.y + 40), BRASS)
        if self.top + self.ROWS < len(rows):
            draw_text(surf, "V", (rect.right - 10, rect.bottom - 14), BRASS)
        hint_line(surf, "LEFT/RIGHT PAGE  UP/DOWN PICK  [E] READ  [ESC] CLOSE", rect.bottom + 6)


class SaidPanel(Panel):
    """One thing somebody told you, written down in the evidence file. E / ESC closes it."""

    def __init__(self, name, when, lines, play=None):
        self.name, self.when = name, when
        self.lines = [r for text in lines for r in wrap_text(text, 276)]
        self.time = 0.0
        if play:
            play("page_turn")

    def handle_event(self, event):
        if nav(event) in ("ok", "back"):
            self.close("closed")

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        dim(surf, 160)
        frame = pygame.Rect(0, 0, 310, 46 + len(self.lines) * 14)
        frame.center = (VIEW_W // 2, 126)
        pygame.draw.rect(surf, (40, 26, 20), frame.inflate(4, 4))
        surf.fill((250, 244, 200), frame)
        for yy in range(frame.y + 30, frame.bottom - 10, 14):
            surf.fill((200, 210, 230), (frame.x + 4, yy + 9, frame.w - 8, 1))
        surf.fill((240, 150, 150), (frame.x + 18, frame.y, 1, frame.h))
        draw_text(surf, self.name, (frame.x + 26, frame.y + 8), (60, 60, 120))
        draw_text(surf, self.when, (frame.right - 10, frame.y + 8), (130, 120, 150), anchor="topright")
        for i, line in enumerate(self.lines):
            draw_text(surf, line, (frame.x + 26, frame.y + 30 + i * 14), (50, 50, 90))
        hint_line(surf, "[E] DONE", VIEW_H - 22)


class PhotoPanel(Panel):
    """The photo wall, one photo at a time (LEFT/RIGHT)."""

    def __init__(self, play=None):
        self.index = 0
        self.play = play
        self.time = 0.0
        self.seen = {0}

    def handle_event(self, event):
        act = nav(event)
        if act in ("ok", "back"):
            self.close("closed")
        elif act in ("left", "right"):
            self.index = (self.index + (-1 if act == "left" else 1)) % len(C.PHOTOS)
            self.seen.add(self.index)
            if self.play:
                self.play("page_turn")

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        dim(surf, 170)
        img = pygame.transform.scale(A.photo_image(C.PHOTOS[self.index], C.PHOTO_STAMP), (300, 224))
        rect = img.get_rect(center=(VIEW_W // 2, 132))
        surf.fill((20, 12, 8), rect.move(3, 3))
        surf.blit(img, rect)
        surf.fill((220, 60, 70), (rect.centerx - 2, rect.y - 3, 5, 5))           # the pin
        draw_text(surf, f"PHOTO {self.index + 1} / {len(C.PHOTOS)}", (VIEW_W // 2, 8), INK, anchor="midtop")
        hint_line(surf, "LEFT/RIGHT ANOTHER PHOTO   [E] DONE", VIEW_H - 16)


class TrophyPanel(Panel):
    """THE CHAMPION'S TROPHY: the cabinet, close up. LEFT/RIGHT move along the shelf (and to the lever), E lifts a
    trophy and puts it down on another slot (they swap), UP/DOWN turn the one under the cursor, E on the lever tries.
    A wrong try only clunks. Right: the hidden compartment slides open and E takes the key."""

    def __init__(self, case, play=None):
        self.case = case
        self.play = play
        self.time = 0.0
        self.clunk = 0.0
        self.opened_at = None
        self.taken = False

    def _sound(self, name):
        if self.play:
            self.play(name)

    def handle_event(self, event):
        if wants_evidence(event):
            self.close("evidence")
            return
        act = nav(event)
        if act is None:
            return
        c = self.case
        if act == "back":
            self.close("closed")
            return
        if c.open:
            if act == "ok" and self.opened_at is not None and self.time - self.opened_at > 0.8:
                self.taken = True
                self.close("key")
            return
        if act in ("left", "right"):
            c.move(-1 if act == "left" else 1)
            self._sound("vend_select")
        elif act in ("up", "down"):
            if c.turn(1 if act == "down" else -1):
                self._sound("circuit_click")
        elif act == "ok":
            if c.cursor == 3:
                if c.pull():
                    self.opened_at = self.time
                    self._sound("drawer_open")
                else:
                    self.clunk = 0.6
                    self._sound("cancel")
            elif c.lift():
                self._sound("equip" if c.held is not None else "drawer_open")

    def update(self, dt):
        self.time += dt
        self.clunk = max(0.0, self.clunk - dt)

    def draw(self, surf):
        dim(surf, 170)
        c = self.case
        frame = pygame.Rect(0, 0, 300, 220)
        frame.center = (VIEW_W // 2, 130)
        pygame.draw.rect(surf, A.WOOD_DK, frame)
        inner = frame.inflate(-14, -14)
        surf.fill((36, 22, 34), inner)
        pygame.draw.rect(surf, A.BRASS, inner, 1)
        draw_text(surf, "TROPHY CABINET", (frame.centerx, frame.y + 10), A.BRASS_LT, anchor="midtop")
        shelf_y = inner.y + 118
        surf.fill(A.WOOD_LT, (inner.x + 6, shelf_y, inner.w - 50, 4))
        for i, (kind, facing) in enumerate(c.slots):
            cx = inner.x + 42 + i * 72
            lifted = c.held == i
            img = pygame.transform.scale(A.trophy_piece(kind, facing, T.TROPHY_MARKS[kind]), (44, 68))
            y = shelf_y - 68 - (10 if lifted else 0) + (int(math.sin(self.time * 6)) if lifted else 0)
            surf.blit(img, (cx - 22, y))
            if c.cursor == i and not c.open:
                pygame.draw.polygon(surf, A.NEON_CYAN, [(cx - 5, shelf_y + 12), (cx + 5, shelf_y + 12), (cx, shelf_y + 7)])
        # the lever, on the right
        lx, ly = inner.right - 22, inner.y + 60
        pulled = c.open or self.clunk > 0
        surf.fill(A.BRASS, (lx - 3, ly + 20, 10, 8))
        end = (lx + 2, ly + (30 if pulled else 2))
        pygame.draw.line(surf, (200, 200, 210), (lx + 2, ly + 24), end, 2)
        pygame.draw.circle(surf, (220, 60, 70), end, 4)
        if c.cursor == 3 and not c.open:
            pygame.draw.polygon(surf, A.NEON_CYAN, [(lx - 3, ly + 44), (lx + 7, ly + 44), (lx + 2, ly + 39)])
        # the hidden compartment under the shelf
        drawer = pygame.Rect(inner.x + 60, shelf_y + 24, 140, 30)
        k = 0.0 if self.opened_at is None else min(1.0, (self.time - self.opened_at) / 0.7)
        surf.fill((60, 36, 24), drawer)
        pygame.draw.rect(surf, A.WOOD_HI if k else (70, 44, 30), drawer, 1)
        if k > 0:
            slide = drawer.move(0, int(10 * k))
            surf.fill((30, 18, 12), slide.inflate(-10, -8))
            if not self.taken:
                surf.blit(pygame.transform.scale(A.key_icon(), (36, 22)), (slide.centerx - 18, slide.centery - 11))
        if self.clunk > 0:
            draw_text(surf, "CLUNK. NOTHING HAPPENS.", (frame.centerx, frame.bottom - 30), RED, anchor="midtop")
        if c.open and k >= 1:
            draw_text(surf, "A HIDDEN COMPARTMENT!", (frame.centerx, frame.bottom - 30), GREEN, anchor="midtop")
        hint = "[E] TAKE THE KEY" if c.open else ("[E] PUT IT DOWN HERE" if c.held is not None else
                                                  "LEFT/RIGHT MOVE  UP/DOWN TURN  [E] LIFT / PULL  [ESC] BACK")
        hint_line(surf, hint, VIEW_H - 16)
        draw_text(surf, "[TAB] EVIDENCE", (frame.right - 16, frame.y + 10), INK_SOFT, anchor="topright")


class TerminalPanel(Panel):
    """The registration terminal: ENTRY RECORD NOT FOUND. Three wheels (LETTER, TENS, UNITS); E submits the code.
    The wheels are never filled in: wrong codes keep them where they are, with the terminal's reply."""

    def __init__(self, run, play=None):
        self.run = run
        self.play = play
        self.wheels = T.CodeWheels()
        self.reply = None                   # (result, message)
        self.reply_age = 0.0
        self.time = 0.0

    def handle_event(self, event):
        if wants_evidence(event) and not (self.reply and self.reply[0] == "ok"):
            self.close("evidence")
            return
        act = nav(event)
        if act is None:
            return
        if act == "back":
            self.close("closed")
            return
        if self.reply and self.reply[0] == "ok":
            if act == "ok":
                self.close("registered")
            return
        if act in ("left", "right"):
            self.wheels.move(-1 if act == "left" else 1)
            self._sound("circuit_click")
        elif act in ("up", "down"):
            self.wheels.turn(-1 if act == "up" else 1)
            self._sound("vend_select")
        elif act == "ok":
            self.reply = self.run.try_code(self.wheels.code)
            self.reply_age = 0.0
            self._sound("power_on" if self.reply[0] == "ok" else "cancel")

    def _sound(self, name):
        if self.play:
            self.play(name)

    def update(self, dt):
        self.time += dt
        self.reply_age += dt

    def draw(self, surf):
        dim(surf, 150)
        frame = pygame.Rect(0, 0, 300, 196)
        frame.center = (VIEW_W // 2, 132)
        pygame.draw.rect(surf, (150, 140, 112), frame.inflate(10, 10), border_radius=4)
        pygame.draw.rect(surf, (206, 196, 168), frame.inflate(6, 6), border_radius=3)
        surf.fill((10, 22, 16), frame)
        for y in range(frame.y, frame.bottom, 2):
            surf.fill((14, 30, 22), (frame.x, y, frame.w, 1))
        g = (110, 255, 170)
        ok = self.reply and self.reply[0] == "ok"
        draw_text(surf, "NEON CORNER REGISTRATION", (frame.centerx, frame.y + 8), g, anchor="midtop")
        surf.fill(scale_color(g, 0.4), (frame.x + 12, frame.y + 20, frame.w - 24, 1))
        if not ok:
            blink = int(self.time * 2) % 2 == 0
            draw_text(surf, "ENTRY RECORD NOT FOUND" if blink else "", (frame.centerx, frame.y + 28), RED, anchor="midtop")
            draw_text(surf, "ENTER YOUR ENTRY CODE", (frame.centerx, frame.y + 42), g, anchor="midtop")
            draw_text(surf, "DIVISION     NUMBER", (frame.centerx, frame.y + 56), scale_color(g, 0.7), anchor="midtop")
        for i in range(3):
            x = frame.centerx - 54 + i * 40 + (8 if i else 0)
            y = frame.y + 72
            sel = i == self.wheels.cursor and not ok
            box = pygame.Rect(x, y, 30, 36)
            pygame.draw.rect(surf, (20, 50, 34), box)
            pygame.draw.rect(surf, g if sel else scale_color(g, 0.45), box, 1)
            draw_text(surf, self.wheels.symbol(i), box.center, g if not ok else (255, 240, 160), 2, "center")
            if sel:
                bob = int(math.sin(self.time * 6))
                pygame.draw.polygon(surf, g, [(box.centerx - 4, box.y - 4 + bob), (box.centerx + 4, box.y - 4 + bob), (box.centerx, box.y - 8 + bob)])
                pygame.draw.polygon(surf, g, [(box.centerx - 4, box.bottom + 4 - bob), (box.centerx + 4, box.bottom + 4 - bob), (box.centerx, box.bottom + 8 - bob)])
        y = frame.y + 124
        if self.reply:
            result, message = self.reply
            draw_text(surf, message, (frame.centerx, y), g if result == "ok" else RED, anchor="midtop")
            if result == "ok":
                draw_text(surf, "PLEASE SEE THE DESK FOR YOUR BADGE.", (frame.centerx, y + 14), g, anchor="midtop")
        hint = "[E] CONTINUE" if ok else "ARROWS: PICK AND TURN  [E] ENTER  [ESC] BACK"
        draw_text(surf, hint, (frame.centerx, frame.bottom - 14), scale_color(g, 0.75), anchor="midtop")
        if not ok:
            draw_text(surf, "[TAB] EVIDENCE", (frame.right, frame.bottom + 8), INK_SOFT, anchor="topright")


class CompletePanel(GU.CompletePanel):
    """TRIAL 02's finish card: the same card as every trial's. The hall has already faded to black and shown
    MEMORY FRAGMENT 02 RECOVERED. / TRIAL 02 COMPLETE. itself (the ending's last beats), so there is no prelude here."""

    def __init__(self, first_time):
        super().__init__(first_time, 2, "THE UNBEATEN RECORD", prelude=False, stay_label="STAY IN THE HALL")
