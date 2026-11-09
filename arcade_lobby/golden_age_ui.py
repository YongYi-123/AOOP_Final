"""The screens of TRIAL 01 that open over the room: fuse board, telephone, cabinet keypad, paper / journal pages, the old
computer, the notes list, the confirm card and the finish card, plus the small hint bubble Miao Meow speaks from.

Each panel is a tiny object the scene holds in `scene.panel`:
    handle_event(event)    keys only (arrows / WASD move, E / ENTER / SPACE confirm, ESC backs out)
    update(dt)
    draw(surf)
    closed, result         set when the panel is done; the scene reads them and carries on
They never touch the story or the save: they report what the player did, and golden_age_scene.py decides what it means.
"""
import math

import pygame

import golden_age as G
import golden_age_art as A
import golden_age_content as C
import happy_breakout as hb
from font import get_font
from gfx import scale_color
from settings import BACK_KEYS, CONFIRM_KEYS, VIEW_H, VIEW_W
from ui import draw_text, wrap_text

PANEL_BG, PANEL_EDGE, PANEL_IN = (36, 22, 16), (214, 164, 62), (120, 78, 46)
INK, INK_SOFT = (244, 228, 192), (176, 146, 112)
BRASS, GREEN = A.BRASS, (118, 255, 170)
UP, DOWN, LEFT, RIGHT = (pygame.K_UP, pygame.K_w), (pygame.K_DOWN, pygame.K_s), (pygame.K_LEFT, pygame.K_a), (pygame.K_RIGHT, pygame.K_d)


def nav(event):
    """A KEYDOWN as one of up / down / left / right / ok / back, else None."""
    if event.type != pygame.KEYDOWN:
        return None
    k = event.key
    for name, keys in (("up", UP), ("down", DOWN), ("left", LEFT), ("right", RIGHT), ("ok", CONFIRM_KEYS), ("back", BACK_KEYS)):
        if k in keys:
            return name
    return None


def warm_panel(surf, rect, title=None, edge=PANEL_EDGE):
    """A dark wooden card with a brass edge (the trial's own frame: warm, not neon)."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, (20, 12, 8), rect.inflate(4, 4), border_radius=3)
    pygame.draw.rect(surf, PANEL_BG, rect, border_radius=3)
    pygame.draw.rect(surf, edge, rect, 1, border_radius=3)
    pygame.draw.rect(surf, PANEL_IN, rect.inflate(-6, -6), 1, border_radius=2)
    for cx, cy in ((rect.left + 2, rect.top + 2), (rect.right - 3, rect.top + 2), (rect.left + 2, rect.bottom - 3), (rect.right - 3, rect.bottom - 3)):
        surf.fill(A.BRASS_LT, (cx, cy, 1, 1))
    if title:
        draw_text(surf, title, (rect.centerx, rect.top + 9), BRASS, 1, "midtop", glow=(80, 50, 20))
        surf.fill(PANEL_IN, (rect.left + 12, rect.top + 20, rect.w - 24, 1))


def dim(surf, alpha=150):
    shade = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    shade.fill((6, 3, 0, alpha))
    surf.blit(shade, (0, 0))


def hint_line(surf, text, y=None, color=INK_SOFT):
    draw_text(surf, text, (VIEW_W // 2, y if y is not None else VIEW_H - 36), color, 1, "midtop")


class Panel:
    closed = False
    result = None
    captures_text = False

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass

    def close(self, result=None):
        self.closed = True
        self.result = result


# ------------------------------------------------------------------ the fuse board
class CircuitPanel(Panel):
    """Turn the tiles until one wire runs from the battery to the lamp. No timer, no penalty."""
    CELL = 34
    SURGE = 2.0

    def __init__(self, circuit, play=None):
        self.circuit = circuit
        self.play = play or (lambda name: None)
        size = self.CELL * G.SIZE
        self.board = pygame.Rect((VIEW_W - size) // 2, 66, size, size)
        self.cursor = [0, 0]
        self.time = 0.0
        self.surge = None                       # seconds since the board was solved
        self.route = list(G.ROUTE)               # the order the current runs through the route (for the surge animation)

    @property
    def locked(self):
        return self.surge is not None

    def handle_event(self, event):
        act = nav(event)
        if act is None or self.locked:
            return
        if act == "back":
            self.close("closed")
        elif act in ("up", "down", "left", "right"):
            dr, dc = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}[act]
            self.cursor = [max(0, min(G.SIZE - 1, self.cursor[0] + dr)), max(0, min(G.SIZE - 1, self.cursor[1] + dc))]
        elif act == "ok":
            self.circuit.rotate(*self.cursor)
            self.play("circuit_click")
            if self.circuit.solved:
                self.surge = 0.0
                self.play("circuit_connect")

    def update(self, dt):
        self.time += dt
        if self.surge is not None:
            self.surge += dt
            if self.surge >= self.SURGE:
                self.close("solved")

    # ------------------------------------------------------------ drawing
    def _cell_rect(self, r, c):
        return pygame.Rect(self.board.x + c * self.CELL, self.board.y + r * self.CELL, self.CELL, self.CELL)

    def _wire(self, surf, rect, d, color, edge):
        """One arm of a wire, from the middle of the tile to the edge it points at."""
        cx, cy = rect.center
        half = self.CELL // 2
        arm = {G.N: (cx - 2, rect.top, 4, half), G.S: (cx - 2, cy, 4, half),
               G.W: (rect.left, cy - 2, half, 4), G.E: (cx, cy - 2, half, 4)}[d]
        x, y, w, h = arm
        surf.fill(edge, (x - 1, y, w + 2, h) if d in (G.N, G.S) else (x, y - 1, w, h + 2))
        surf.fill(color, arm)

    def draw(self, surf):
        dim(surf, 170)
        frame = pygame.Rect(0, 0, 252, 236)
        frame.center = (VIEW_W // 2, 144)
        warm_panel(surf, frame, "FUSE BOARD")
        lit = self.circuit.powered()
        fully = self.circuit.solved
        for r in range(G.SIZE):
            for c in range(G.SIZE):
                rect = self._cell_rect(r, c)
                pygame.draw.rect(surf, (24, 16, 12), rect.inflate(-2, -2))
                pygame.draw.rect(surf, (70, 46, 30), rect.inflate(-2, -2), 1)
                cell = (r, c)
                on = cell in lit
                flash = 0.0
                if self.surge is not None and cell in self.route:
                    flash = max(0.0, min(1.0, (self.surge - self.route.index(cell) * 0.12) * 5))
                color = (255, 214, 90) if on else (156, 100, 58)
                edge = (90, 56, 24) if on else (60, 36, 24)
                if flash:
                    color = tuple(int(v + (255 - v) * flash * 0.8) for v in color)
                for d in sorted(self.circuit.openings_of(cell)):
                    self._wire(surf, rect, d, color, edge)
                pygame.draw.rect(surf, edge, (rect.centerx - 4, rect.centery - 4, 8, 8))
                pygame.draw.rect(surf, color, (rect.centerx - 3, rect.centery - 3, 6, 6))
                if on:
                    surf.fill((255, 250, 200), (rect.centerx - 1, rect.centery - 1, 2, 2))
        # the battery on the left and the lamp on the right
        sy = self._cell_rect(*G.SOURCE).centery
        ey = self._cell_rect(*G.OUTPUT).centery
        src_on = G.W in self.circuit.openings_of(G.SOURCE)
        surf.fill((60, 36, 24), (self.board.x - 22, sy - 3, 22, 6))
        surf.fill((255, 214, 90) if src_on else (156, 100, 58), (self.board.x - 22, sy - 2, 22, 4))
        bat = pygame.Rect(self.board.x - 44, sy - 12, 22, 24)
        pygame.draw.rect(surf, (60, 90, 70), bat, border_radius=2)
        pygame.draw.rect(surf, (130, 200, 150), bat, 1, border_radius=2)
        draw_text(surf, "+", (bat.centerx - 2, bat.centery - 3), (240, 255, 240))
        out_on = fully or (G.OUTPUT in lit and G.E in self.circuit.openings_of(G.OUTPUT))
        end = self.board.right
        surf.fill((60, 36, 24), (end, ey - 3, 18, 6))
        surf.fill((255, 214, 90) if out_on else (156, 100, 58), (end, ey - 2, 18, 4))
        bx, by = end + 28, ey
        glow = 6 + (int(2 * math.sin(self.time * 8)) if out_on else 0)
        if out_on:
            pygame.draw.circle(surf, (110, 84, 30), (bx, by), glow + 5)
        pygame.draw.circle(surf, (255, 236, 150) if out_on else (84, 76, 70), (bx, by), 7)
        pygame.draw.circle(surf, (40, 30, 20), (bx, by), 7, 1)
        surf.fill((140, 130, 120), (bx - 3, by + 7, 6, 4))
        # the cursor
        rect = self._cell_rect(*self.cursor)
        if not self.locked:
            blink = int(self.time * 3) % 2 == 0
            col = (255, 240, 170) if blink else (210, 170, 70)
            for (x, y, w, h) in ((rect.x, rect.y, 8, 2), (rect.x, rect.y, 2, 8), (rect.right - 8, rect.y, 8, 2), (rect.right - 2, rect.y, 2, 8),
                                 (rect.x, rect.bottom - 2, 8, 2), (rect.x, rect.bottom - 8, 2, 8), (rect.right - 8, rect.bottom - 2, 8, 2),
                                 (rect.right - 2, rect.bottom - 8, 2, 8)):
                surf.fill(col, (x, y, w, h))
        status = "THE CURRENT FINDS ITS WAY." if self.locked else ("CURRENT FLOWING..." if lit else "NO CURRENT. TURN THE TILES.")
        draw_text(surf, status, (VIEW_W // 2, self.board.bottom + 10), GREEN if self.locked else INK, 1, "midtop")
        hint_line(surf, "ARROWS MOVE   [E] TURN   [ESC] CLOSE", self.board.bottom + 28)


# ------------------------------------------------------------------ the telephone
class PhonePanel(Panel):
    """The old telephone plays a short message in tones. Press E to hear it again, as often as you like."""

    def __init__(self, on_start=None, play=None, word=G.ANSWER, has_chart=None):
        self.has_chart = has_chart or (lambda: False)         # is the Morse note from the drawer in hand?
        self.word = word
        self.play = play or (lambda name: None)
        self.on_start = on_start or (lambda: None)
        self.playback = None
        self.shown = []                         # pulses that have sounded in the transmission on screen
        self.time = 0.0
        self.plays = 0

    @property
    def playing(self):
        return self.playback is not None and self.playback.playing

    def start(self):
        if self.playing:
            return False
        self.playback = G.MorsePlayback(self.word)
        self.shown = []
        self.plays += 1
        self.on_start()
        return True

    def handle_event(self, event):
        act = nav(event)
        if act == "back":
            self.close("closed")
        elif act == "ok":
            self.start()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_c and self.has_chart() and not self.playing:
            self.close("note")                  # look at the Morse note (the scene brings the phone back afterwards)

    def update(self, dt):
        self.time += dt
        if self.playback is not None:
            for pulse in self.playback.advance(dt):
                self.shown.append(pulse)
                self.play(pulse.sound)                  # the tone starts on the very step the lamp lights

    @property
    def lit(self):
        return self.playback is not None and self.playback.lit

    def draw(self, surf):
        dim(surf, 170)
        frame = pygame.Rect(0, 0, 300, 190)
        frame.center = (VIEW_W // 2, 140)
        warm_panel(surf, frame, "TELEPHONE")
        img = pygame.transform.scale(A.phone(self.lit), (24 * 4, 15 * 4))
        surf.blit(img, img.get_rect(midtop=(VIEW_W // 2, frame.top + 30)))
        if self.lit:                                    # the signal lamp (the sprite's lamp, scaled) glows
            lamp = (VIEW_W // 2 - 48 + 21 * 4, frame.top + 30 + 9 * 4)
            glow = A.soft_light(18, (255, 200, 90))
            surf.blit(glow, glow.get_rect(center=lamp), special_flags=pygame.BLEND_RGB_ADD)
        status = "RECEIVING..." if self.playing else ("END OF MESSAGE. LISTEN AGAIN IF YOU LIKE." if self.shown else "THE LINE IS HUMMING.")
        draw_text(surf, status, (VIEW_W // 2, frame.top + 122), GREEN if self.playing else INK, 1, "midtop")
        if self.has_chart():
            draw_text(surf, "YOU HAVE A MORSE NOTE: [C] READ IT", (VIEW_W // 2, frame.top + 140), A.BRASS_LT, 1, "midtop")
        hint_line(surf, "[E] PLAY MESSAGE    [ESC] HANG UP", frame.bottom - 22)


# ------------------------------------------------------------------ the cabinet's keypad
class KeypadPanel(Panel):
    """Type a password with the keyboard. ENTER sends it, BACKSPACE takes a letter back."""
    captures_text = True
    LENGTH = len(G.ANSWER)

    def __init__(self, try_code, play=None):
        self.try_code = try_code                # callable(text) -> "open" / "wrong" / "again" / "locked"
        self.play = play or (lambda name: None)
        self.text = ""
        self.time = 0.0
        self.flash = 0.0
        self.state = None                       # None / "wrong" / "open"
        self.timer = 0.0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.state == "open":
            return
        k = event.key
        if k in BACK_KEYS:
            self.close("closed")
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if len(self.text) < self.LENGTH:
                self.state, self.timer = "short", 0.9
                self.play("cancel")
                return
            outcome = self.try_code(self.text)
            if outcome in ("open", "again"):
                self.state, self.timer = "open", 1.1
            else:
                self.state, self.timer = "wrong", 1.0
                self.play("cancel")
        elif k == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            self.state = None
        elif pygame.K_a <= k <= pygame.K_z and len(self.text) < self.LENGTH and self.state not in ("wrong",):
            self.text += chr(k).upper()
            self.state = None
            self.play("circuit_click")

    def update(self, dt):
        self.time += dt
        if self.state is not None and self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                if self.state == "open":
                    self.close("open")
                elif self.state == "wrong":
                    self.text = ""
                self.state = None if self.state != "open" else "open"

    def draw(self, surf):
        dim(surf, 170)
        frame = pygame.Rect(0, 0, 250, 150)
        frame.center = (VIEW_W // 2, 140)
        warm_panel(surf, frame, "FILE CABINET LOCK")
        draw_text(surf, "TYPE THE PASSWORD", (frame.centerx, frame.top + 30), INK, 1, "midtop")
        w, gap = 24, 6
        x0 = frame.centerx - (self.LENGTH * w + (self.LENGTH - 1) * gap) // 2
        shake = int(3 * math.sin(self.time * 60)) if self.state == "wrong" else 0
        for i in range(self.LENGTH):
            rect = pygame.Rect(x0 + i * (w + gap) + shake, frame.top + 48, w, 32)
            ok = self.state == "open"
            pygame.draw.rect(surf, (18, 28, 24) if not ok else (20, 70, 50), rect, border_radius=2)
            edge = (110, 255, 170) if ok else ((255, 110, 90) if self.state == "wrong" else (130, 100, 60))
            pygame.draw.rect(surf, edge, rect, 1, border_radius=2)
            if i < len(self.text):
                draw_text(surf, self.text[i], rect.center, (150, 255, 190), 2, "center")
            elif i == len(self.text) and int(self.time * 2) % 2 == 0 and self.state is None:
                surf.fill((150, 255, 190), (rect.centerx - 4, rect.bottom - 7, 8, 2))
        msg = {"wrong": ("ACCESS DENIED", (255, 120, 100)), "short": ("NOT ENOUGH LETTERS", (255, 190, 100)),
               "open": ("UNLOCKED", (130, 255, 180)), None: ("", INK)}[self.state]
        draw_text(surf, msg[0], (frame.centerx, frame.top + 90), msg[1], 1, "midtop")
        hint_line(surf, "TYPE LETTERS   [ENTER] SEND   [BACKSPACE] DELETE   [ESC] CLOSE", frame.bottom - 20)


# ------------------------------------------------------------------ paper, the chart and the journal
def morse_glyph(surf, code, x, y, color=(60, 36, 24)):
    """Draw a Morse letter's dots and dashes; returns the width used."""
    for sym in code:
        w = 3 if sym == G.DOT else 9
        surf.fill(color, (x, y, w, 3))
        x += w + 2
    return x


PAGE_W, PAGE_H = 300, 254
TEXT_W = 246                                    # width of the writing on a page (about 40 letters)
MAX_ROWS = 15                                   # rows of writing that fit under the title


def page_rows(text, scale=1, width=TEXT_W):
    """The rows a page's text is wrapped into (\\n starts a new row). The reader and the tests share this."""
    rows = []
    for para in text.split("\n"):
        rows += wrap_text(para, width, scale) or [""]
    return rows


class PagedPanel(Panel):
    """Pages of paper: a note, the Morse chart, a book, the notebook. LEFT / RIGHT turn, E goes on, the last E finishes it.
    Text is the hub's pixel font (English), wrapped to the page; a page's "scale" (default 1) makes short notes bigger."""

    def __init__(self, pages, play=None, finish_label="DONE", title=None, tag=None):
        self.pages = pages                      # [{"title", "text", "scale", "chart"}]
        self.play = play or (lambda name: None)
        self.finish_label = finish_label
        self.title = title
        self.tag = tag                          # what is being read ("notebook", a book key, ...): the scene tells them apart
        self.index = 0
        self.time = 0.0

    def _turn(self, delta):
        i = max(0, min(len(self.pages) - 1, self.index + delta))
        if i != self.index:
            self.index = i
            self.play("page_turn")

    def handle_event(self, event):
        act = nav(event)
        if act == "back":
            # closing the book while its last page is open counts as having read it through (E there does the same)
            self.close("finished" if self.index >= len(self.pages) - 1 else "closed")
        elif act in ("left", "up"):
            self._turn(-1)
        elif act == "right" or act == "down":
            self._turn(1)
        elif act == "ok":
            if self.index >= len(self.pages) - 1:
                self.close("finished")
            else:
                self._turn(1)

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        dim(surf, 170)
        page = pygame.Rect(0, 0, PAGE_W, PAGE_H)
        page.center = (VIEW_W // 2, 140)
        pygame.draw.rect(surf, (30, 18, 12), page.inflate(10, 10), border_radius=4)
        pygame.draw.rect(surf, (200, 168, 110), page.inflate(6, 6), border_radius=3)      # leather / table edge
        pygame.draw.rect(surf, (246, 234, 202), page, border_radius=2)
        data = self.pages[self.index]
        scale = data.get("scale", 1)
        pitch = 7 * scale + 5 if not data.get("chart") else 11
        for y in range(page.top + 40 + 7 * scale + 2, page.bottom - 22, pitch):         # ruled lines: the writing sits on them
            surf.fill((226, 208, 170), (page.left + 14, y, page.w - 28, 1))
        surf.fill((214, 120, 100), (page.left + 28, page.top + 8, 1, page.h - 16))        # margin line
        ink = (70, 44, 30)
        title = data.get("title") or self.title
        if title:
            for k, row in enumerate(wrap_text(title, TEXT_W)[:2]):
                draw_text(surf, row, (page.centerx, page.top + 10 + k * 9), (150, 60, 44), 1, "midtop")
        if data.get("chart"):
            self._chart(surf, page)
        else:
            y = page.top + 40
            for row in page_rows(data.get("text", ""), scale):
                draw_text(surf, row, (page.left + 36, y), ink, scale)
                y += pitch
        draw_text(surf, f"{self.index + 1}/{len(self.pages)}", (page.right - 12, page.bottom - 14), (150, 120, 90), 1, "topright")
        last = self.index >= len(self.pages) - 1
        keys = f"[E] {self.finish_label}" if last else "[E] NEXT PAGE"
        if len(self.pages) > 1:
            keys = "LEFT/RIGHT TURN    " + keys
        hint_line(surf, keys + "    [ESC] CLOSE", page.bottom + 10, (200, 176, 140))

    def _chart(self, surf, page):
        letters = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        cols = (letters[0:9], letters[9:18], letters[18:])
        for ci, col in enumerate(cols):
            x = page.left + 40 + ci * 76
            for ri, ch in enumerate(col):
                y = page.top + 34 + ri * 19
                draw_text(surf, ch, (x, y), (150, 60, 44), 2)
                morse_glyph(surf, G.MORSE[ch], x + 16, y + 5)
        draw_text(surf, "SHORT = DOT   LONG = DASH", (page.centerx, page.bottom - 40), (110, 80, 60), 1, "midtop")


def paper_pages(clue_key):
    """The pages for a clue in the notes / the drawer."""
    if clue_key == "paper":
        return [{"title": "A FOLDED PAPER", "text": '"When words fail, patterns speak."', "scale": 2}]
    if clue_key == "chart":
        return [{"title": "MORSE CODE", "chart": True}]
    if clue_key == "note":
        return [{"title": "AN OLD NOTE", "text": "\n".join(G.CABINET_NOTE), "scale": 2}]
    if clue_key == "journal":
        return [dict(p) for p in C.JOURNAL_PAGES]
    if clue_key == "sticky":
        return [dict(p) for p in C.STICKY_NOTES]
    if clue_key == "homework":
        return [dict(p) for p in C.HOMEWORK_PAGES]
    if clue_key == "textbook":
        return [dict(p) for p in C.TEXTBOOK_PAGES]
    if clue_key == "trash":
        return [dict(p) for p in C.TRASH_PAGES]
    if clue_key in C.BOOKS:
        return [dict(p) for p in C.BOOKS[clue_key][2]]
    raise KeyError(clue_key)


# ------------------------------------------------------------------ the bookshelf
class BookshelfPanel(Panel):
    """A browser of the books on the shelf: pick one to take it down and read it. Nothing is handed out by the shelf itself."""

    def __init__(self, keys):
        self.keys = list(keys)
        self.index = 0
        self.time = 0.0

    def handle_event(self, event):
        act = nav(event)
        n = len(self.keys)
        if act == "back":
            self.close("closed")
        elif act in ("up", "left") and n:
            self.index = (self.index - 1) % n
        elif act in ("down", "right") and n:
            self.index = (self.index + 1) % n
        elif act == "ok" and n:
            self.close(("book", self.keys[self.index]))

    def update(self, dt):
        self.time += dt

    @staticmethod
    def spine(key):
        if key == C.NOTEBOOK_KEY:
            return C.NOTEBOOK_TITLE, C.NOTEBOOK_COLOUR
        title, colour, _ = C.BOOKS[key]
        return title, colour

    def draw(self, surf):
        dim(surf, 170)
        frame = pygame.Rect(0, 0, 300, 52 + 16 * len(self.keys) + 26)
        frame.center = (VIEW_W // 2, 146)
        warm_panel(surf, frame, C.BOOKSHELF_TITLE)
        draw_text(surf, "PICK A BOOK TO TAKE DOWN.", (frame.centerx, frame.top + 26), INK_SOFT, 1, "midtop")
        for i, key in enumerate(self.keys):
            title, colour = self.spine(key)
            y = frame.top + 42 + i * 16
            sel = i == self.index
            if sel:
                surf.fill((70, 44, 28), (frame.left + 12, y - 2, frame.w - 24, 15))
            surf.fill(A.mul(colour, 1.15 if sel else 0.85), (frame.left + 18, y, 8, 11))        # the spine
            surf.fill(A.mul(colour, 0.6), (frame.left + 18, y + 9, 8, 2))
            surf.fill(A.BRASS_LT, (frame.left + 20, y + 3, 4, 1))
            draw_text(surf, ("> " if sel else "  ") + title, (frame.left + 34, y + 2), INK if sel else INK_SOFT)
        hint_line(surf, "UP/DOWN PICK   [E] TAKE IT DOWN   [ESC] BACK", frame.bottom - 18)


# ------------------------------------------------------------------ the old computer
SCREEN = pygame.Rect(54, 32, 292, 224)             # the glass of the CRT (canvas pixels)
FIELD_X, FIELD_Y = (SCREEN.w - hb.FIELD_W) // 2, 30  # where the Breakout field sits on the glass
BRICK_COLOURS = ((240, 150, 150), (240, 190, 120), (240, 230, 130), (150, 220, 160), (140, 190, 240))      # soft pastels
NUMBER_KEYS = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4, pygame.K_KP1: 1, pygame.K_KP2: 2, pygame.K_KP3: 3, pygame.K_KP4: 4}
PHOSPHOR, PHOSPHOR_DIM, AMBER = GREEN, (80, 170, 130), (255, 200, 110)


class ComputerPanel(Panel):
    """INSERT BOOT DISK? > BOOTING... > the desktop (PLAY GAME / HIGH SCORES / LOCKED FILES / EXIT) > HAPPY BREAKOUT.EXE.
    The locked files only open once the game has been cleared; then they show the archive and PLAYER_000, and E ends it.
    Playing is free, losing all three lives just lets you start again, and a cleared game stays cleared."""
    LINE_TIME = 0.85

    def __init__(self, play=None, cleared=False, on_clear=None):
        self.play = play or (lambda name: None)
        self.cleared = cleared                  # HAPPY BREAKOUT has been cleared (before, or just now)
        self.on_clear = on_clear or (lambda: None)
        self.stage = "ask"                      # ask > boot > desktop > game / scores / clear / files
        self.yes = True
        self.desktop = G.Desktop()
        self.game = hb.Breakout()
        self.held = set()                       # movement keys held down (left / right) while playing
        self.paused = False
        self.sparks = []                        # [x, y, vx, vy, life, colour] hit sparks
        self.best = 0
        self.time = 0.0
        self.stage_time = 0.0
        self.shake = 0.0
        self.booted_sound = True

    def _go(self, stage):
        self.stage, self.stage_time = stage, 0.0

    @property
    def direction(self):
        return int(bool(self.held & set(RIGHT))) - int(bool(self.held & set(LEFT)))

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type == pygame.KEYUP:
            self.held.discard(event.key)
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key in LEFT or event.key in RIGHT:
            self.held.add(event.key)
        act = nav(event)
        if self.stage == "ask":
            self._ask(act)
        elif self.stage == "desktop":
            self._desktop(event, act)
        elif self.stage == "game":
            self._game(event, act)
        elif self.stage in ("scores", "clear"):
            if act in ("ok", "back"):
                self._go("desktop")
        elif self.stage == "files":
            if act in ("ok", "back") and self.stage_time > 4.0:
                self.close("done")

    def _ask(self, act):
        if act in ("left", "right", "up", "down"):
            self.yes = not self.yes
        elif act == "back" or (act == "ok" and not self.yes):
            self.close("no")
        elif act == "ok":
            self.play("disk_insert")
            self._go("boot")
            self.booted_sound = False

    def _desktop(self, event, act):
        d = self.desktop
        if event.key in NUMBER_KEYS:
            d.pick(NUMBER_KEYS[event.key])
            act = "ok"
        if act == "back":
            self.close("closed")
        elif act == "up":
            d.move(-1)
        elif act == "down":
            d.move(1)
        elif act == "ok":
            what = d.choose(self.cleared)
            if what == "play":
                self._start_game()
            elif what == "scores":
                self._go("scores")
            elif what == "files":
                self.play("confirm")
                self._go("files")
            elif what == "locked":
                self.play("cancel")
                self.shake = 0.3
            elif what == "exit":
                self.close("closed")

    def _start_game(self):
        self.game.reset()
        self.held.clear()
        self.paused = False
        self.sparks = []
        self._go("game")

    def _game(self, event, act):
        g = self.game
        if self.paused:
            if act == "ok":
                self.paused = False
            elif act == "back":
                self.paused = False
                self.held.clear()
                self._go("desktop")
            return
        if act == "back":
            self.paused = True
            self.held.clear()
        elif event.key in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_UP, pygame.K_w):
            g.launch()

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        self.stage_time += dt
        self.shake = max(0.0, self.shake - dt)
        if self.stage == "boot":
            if not self.booted_sound and self.stage_time > 0.7:
                self.booted_sound = True
                self.play("crt_boot")
            if self.stage_time > len(G.BOOT_LINES) * self.LINE_TIME + 1.4:
                self._go("desktop")
        elif self.stage == "game" and not self.paused:
            self.game.step(dt, self.direction)
            self._events(self.game.take_events())
            if self.game.state == "clear":
                self._cleared()
        for sp in self.sparks:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[3] += 160 * dt
            sp[4] -= dt
        self.sparks = [sp for sp in self.sparks if sp[4] > 0]

    def _events(self, events):
        for name, x, y, colour in events:
            if name == "brick":
                self.play("breakout_brick")
                for k in range(7):
                    self.sparks.append([x, y, (k - 3) * 14.0, -40.0 - 8 * (k % 3), 0.45, BRICK_COLOURS[colour % len(BRICK_COLOURS)]])
            elif name in ("paddle", "wall", "lose"):
                self.play("breakout_" + name)
            elif name == "launch":
                self.play("breakout_paddle")
        self.best = max(self.best, self.game.score)

    def _cleared(self):
        self.play("breakout_clear")
        if not self.cleared:
            self.cleared = True
        self.on_clear()
        self._go("clear")

    # ------------------------------------------------------------ drawing
    def _bezel(self, surf):
        bezel = pygame.Rect(34, 14, 332, 272)
        pygame.draw.rect(surf, (20, 14, 10), bezel.inflate(6, 6), border_radius=10)
        pygame.draw.rect(surf, (214, 204, 176), bezel, border_radius=8)
        pygame.draw.rect(surf, (170, 160, 134), bezel, 2, border_radius=8)
        pygame.draw.rect(surf, (10, 22, 18), SCREEN, border_radius=10)
        draw_text(surf, "RETRO-VISION 9000", (bezel.centerx, bezel.bottom - 14), (130, 120, 98), 1, "midtop")
        surf.fill((255, 170, 60), (bezel.right - 24, bezel.bottom - 16, 4, 4))          # the power light

    def draw(self, surf):
        dim(surf, 200)
        self._bezel(surf)
        view = pygame.Surface(SCREEN.size)
        view.fill((8, 24, 18))
        x0 = 12 + int(self.shake * 40 % 2)
        draw = getattr(self, "_draw_" + self.stage)
        draw(view, x0)
        view.blit(A.scanlines(SCREEN.size, 52), (0, 0))
        edge = pygame.Surface(SCREEN.size, pygame.SRCALPHA)
        for i in range(10):
            pygame.draw.rect(edge, (0, 0, 0, int(80 * (1 - i / 9) ** 2)), (i, i, SCREEN.w - 2 * i, SCREEN.h - 2 * i), 1)
        view.blit(edge, (0, 0))
        band = int(self.time * 50) % (SCREEN.h + 40) - 20                      # a slow bright bar rolling down the glass
        bar = pygame.Surface((SCREEN.w, 10), pygame.SRCALPHA)
        bar.fill((140, 255, 200, 14))
        view.blit(bar, (0, band))
        mask = pygame.Surface(SCREEN.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=10)
        view = view.convert_alpha()
        view.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(view, SCREEN)

    def _draw_ask(self, view, x0):
        draw_text(view, "OLD BOOT DISK DETECTED", (x0, 12), PHOSPHOR)
        draw_text(view, "INSERT BOOT DISK?", (SCREEN.w // 2, 58), PHOSPHOR, 2, "midtop", glow=(20, 90, 60))
        for i, (label, sel) in enumerate((("YES", self.yes), ("NO", not self.yes))):
            r = pygame.Rect(SCREEN.w // 2 - 80 + i * 90, 110, 70, 26)
            pygame.draw.rect(view, (30, 110, 80) if sel else (14, 40, 30), r)
            pygame.draw.rect(view, PHOSPHOR if sel else (60, 130, 100), r, 1)
            draw_text(view, ("> " if sel else "") + label, r.center, PHOSPHOR if sel else PHOSPHOR_DIM, 1, "center")
        draw_text(view, "[E] CHOOSE    [ESC] BACK", (SCREEN.w // 2, SCREEN.h - 24), PHOSPHOR_DIM, 1, "midtop")

    def _draw_boot(self, view, x0):
        n = min(len(G.BOOT_LINES), int(self.stage_time / self.LINE_TIME) + 1) if self.stage_time > 0.7 else 0
        draw_text(view, "FLOPPY DRIVE: ACTIVE", (x0, 12), PHOSPHOR_DIM)
        for i, line in enumerate(G.BOOT_LINES[:n]):
            draw_text(view, line, (x0, 44 + i * 18), PHOSPHOR, 2)
        if n >= len(G.BOOT_LINES) and self.stage_time > len(G.BOOT_LINES) * self.LINE_TIME + 0.2:
            draw_text(view, "READY.", (x0, 44 + n * 18 + 8), PHOSPHOR, 2)
        if int(self.time * 3) % 2 == 0:
            view.fill(PHOSPHOR, (x0, 44 + max(n, 1) * 18 + 30, 8, 12))

    def _draw_desktop(self, view, x0):
        draw_text(view, "PERSONAL COMPUTER", (x0, 12), PHOSPHOR, 1, glow=(20, 90, 60))
        draw_text(view, "DISK A:", (x0, 24), PHOSPHOR_DIM)
        draw_text(view, C.BREAKOUT_TITLE, (x0, 44), PHOSPHOR, 2, glow=(20, 90, 60))
        draw_text(view, C.BREAKOUT_BLURB, (x0, 64), AMBER)
        d = self.desktop
        for i, label in enumerate(d.items):
            y = 96 + i * 20
            sel = i == d.cursor
            if sel:
                pygame.draw.rect(view, (24, 84, 62), (x0 - 4, y - 4, SCREEN.w - 2 * x0 + 8, 16))
            text = f"[{i + 1}] {label}"
            if label == "LOCKED FILES" and not self.cleared:
                text += "  (LOCKED)"
            draw_text(view, ("> " if sel else "  ") + text, (x0, y), PHOSPHOR if sel else PHOSPHOR_DIM)
        if d.message:
            for i, row in enumerate(wrap_text(d.message, SCREEN.w - 2 * x0)):
                draw_text(view, row, (x0, 184 + i * 10), AMBER)
        draw_text(view, "UP/DOWN OR 1-4   [E] SELECT   [ESC] LEAVE", (SCREEN.w // 2, SCREEN.h - 18), PHOSPHOR_DIM, 1, "midtop")

    def _draw_scores(self, view, x0):
        draw_text(view, "HIGH SCORES", (x0, 12), PHOSPHOR, 2, glow=(20, 90, 60))
        rows = list(C.HIGH_SCORES) + ([("YOU", self.best)] if self.best else [])
        for i, (name, score) in enumerate(sorted(rows, key=lambda r: -r[1])):
            draw_text(view, f"{i + 1}. {name:<5} {score:06d}", (x0 + 20, 54 + i * 16), PHOSPHOR if name == "YOU" else PHOSPHOR_DIM)
        draw_text(view, "NOBODY HAS TO BEAT THEM.", (x0 + 20, 54 + 5 * 16 + 8), AMBER)
        draw_text(view, "[E] BACK", (SCREEN.w // 2, SCREEN.h - 20), PHOSPHOR_DIM, 1, "midtop")

    def _draw_game(self, view, x0):
        g = self.game
        draw_text(view, f"SCORE {g.score:04d}", (FIELD_X, 8), PHOSPHOR)
        draw_text(view, "HAPPY BREAKOUT", (SCREEN.w // 2, 8), PHOSPHOR_DIM, 1, "midtop")
        for i in range(g.lives):                                               # lives: little paddles
            view.fill((236, 232, 200), (FIELD_X + hb.FIELD_W - 18 - i * 14, 10, 10, 3))
        field = pygame.Rect(FIELD_X, FIELD_Y, hb.FIELD_W, hb.FIELD_H)
        pygame.draw.rect(view, (12, 34, 28), field)
        pygame.draw.rect(view, PHOSPHOR_DIM, field.inflate(2, 2), 1)
        for b in g.bricks:
            if b.alive:
                c = BRICK_COLOURS[b.colour % len(BRICK_COLOURS)]
                r = pygame.Rect(FIELD_X + b.x, FIELD_Y + b.y, hb.BRICK_W, hb.BRICK_H)
                view.fill(c, r)
                view.fill(A.mul(c, 1.2), (r.x, r.y, r.w, 1))
                view.fill(A.mul(c, 0.7), (r.x, r.bottom - 1, r.w, 1))
        pad = pygame.Rect(FIELD_X + int(g.paddle_x), FIELD_Y + hb.PADDLE_Y, hb.PADDLE_W, hb.PADDLE_H)
        view.fill((236, 232, 200), pad)
        view.fill((255, 255, 240), (pad.x, pad.y, pad.w, 1))
        view.fill((236, 232, 200), (FIELD_X + int(g.ball_x), FIELD_Y + int(g.ball_y), hb.BALL, hb.BALL))
        for x, y, _, _, life, colour in self.sparks:
            view.fill(colour, (FIELD_X + int(x), FIELD_Y + int(y), 2, 2))
        mid = field.centerx
        if g.state == "ready":
            draw_text(view, "[E] / SPACE: LAUNCH    ARROWS / A D: MOVE", (SCREEN.w // 2, field.bottom + 6), PHOSPHOR_DIM, 1, "midtop")
        elif g.state == "over":
            self._card(view, field, ["OUT OF LIVES", "NO WORRIES. IT'S FREE.", "[E] TRY AGAIN    [ESC] DESKTOP"])
        if self.paused:
            self._card(view, field, ["PAUSED", "[E] RESUME    [ESC] DESKTOP"])

    @staticmethod
    def _card(view, field, rows):
        card = pygame.Rect(0, 0, 200, 22 + 14 * len(rows))
        card.center = field.center
        pygame.draw.rect(view, (8, 24, 18), card)
        pygame.draw.rect(view, PHOSPHOR, card, 1)
        for i, row in enumerate(rows):
            draw_text(view, row, (card.centerx, card.top + 10 + i * 14), PHOSPHOR if i == 0 else PHOSPHOR_DIM, 1, "midtop")

    def _draw_clear(self, view, x0):
        t = self.stage_time
        lines = C.GAME_CLEAR
        draw_text(view, lines[0], (SCREEN.w // 2, 40), PHOSPHOR, 3, "midtop", glow=(20, 90, 60))
        for i, row in enumerate(lines[1:]):
            if t > 0.6 + i * 0.9:
                shown = row[:int((t - 0.6 - i * 0.9) * 40)]
                if i == 0:
                    shown = '"' + shown                                       # the three lines are one quotation
                if i == len(lines) - 2 and len(shown) >= len(row):
                    shown += '"'
                draw_text(view, shown, (SCREEN.w // 2, 92 + i * 16), AMBER if i < 2 else PHOSPHOR, 1, "midtop")
        if t > 3.6 and int(self.time * 2) % 2 == 0:
            draw_text(view, "[E] BACK TO THE DESKTOP", (SCREEN.w // 2, SCREEN.h - 22), PHOSPHOR_DIM, 1, "midtop")
        for k in range(14):                                                     # a little confetti
            x = (k * 53 + int(t * 30)) % SCREEN.w
            y = (k * 29 + int(t * 50)) % SCREEN.h
            view.fill(BRICK_COLOURS[k % 5], (x, y, 2, 2))

    def _draw_files(self, view, x0):
        t = self.stage_time
        for i, text in enumerate(C.ARCHIVE_LINES):
            start = 0.2 + i * 1.0
            if t > start:
                draw_text(view, "SYSTEM: " + text[:int((t - start) * 40)], (12, 16 + i * 14), PHOSPHOR)
        if t > 2.4:
            k = min(1.0, (t - 2.4) / 0.8)
            card = pygame.Rect(SCREEN.w // 2 - 118, 76, 236, 90)
            pygame.draw.rect(view, scale_color((24, 84, 62), k), card)
            pygame.draw.rect(view, scale_color(PHOSPHOR, k), card, 1)
            draw_text(view, C.ADMIN_CARD[0], (card.centerx, card.top + 18), scale_color((200, 255, 225), k), 3, "midtop", glow=scale_color((20, 90, 60), k))
            draw_text(view, C.ADMIN_CARD[1], (card.centerx, card.top + 58), scale_color(PHOSPHOR, k), 1, "midtop")
        if t > 4.0 and int(self.time * 2) % 2 == 0:
            draw_text(view, "[E] CONTINUE", (SCREEN.w // 2, SCREEN.h - 22), PHOSPHOR_DIM, 1, "midtop")


# ------------------------------------------------------------------ notes, confirm and finish cards
class NotesPanel(Panel):
    """Objective, the clues found so far (open one to read it again) and the Trial Inventory."""

    def __init__(self, run):
        self.run = run
        self.index = 0
        self.time = 0.0

    @property
    def entries(self):
        return list(self.run.clues)

    def handle_event(self, event):
        act = nav(event)
        n = len(self.entries)
        if act == "back" or (event.type == pygame.KEYDOWN and event.key in (pygame.K_TAB, pygame.K_n)):
            self.close("closed")
        elif act == "up" and n:
            self.index = (self.index - 1) % n
        elif act == "down" and n:
            self.index = (self.index + 1) % n
        elif act == "ok" and n:
            self.close(("clue", self.entries[self.index]))

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        dim(surf, 170)
        frame = pygame.Rect(0, 0, 330, 238)
        frame.center = (VIEW_W // 2, 146)
        warm_panel(surf, frame, "NOTES AND CLUES")
        x, y = frame.left + 16, frame.top + 28
        draw_text(surf, "CLUES FOUND", (x, y), INK_SOFT)
        names = {k: c.title for k, c in G.CLUES.items()}
        if not self.run.clues:
            draw_text(surf, "NOTHING YET. LOOK AROUND THE ROOM.", (x, y + 12), (130, 106, 80))
        for i, key in enumerate(self.run.clues):
            yy = y + 12 + i * 12
            sel = i == self.index
            if sel:
                surf.fill((70, 44, 28), (x - 4, yy - 2, 300, 11))
            draw_text(surf, ("> " if sel else "  ") + names[key], (x, yy), INK if sel else INK_SOFT)
        y = frame.top + 150
        draw_text(surf, "TRIAL INVENTORY", (x, y), INK_SOFT)
        if not self.run.inventory:
            draw_text(surf, "EMPTY", (x, y + 12), (130, 106, 80))
        for i, item in enumerate(self.run.inventory):
            surf.blit(A.disk_icon(), (x, y + 12 + i * 16))
            draw_text(surf, item, (x + 20, y + 16 + i * 16), INK)
        hint_line(surf, "UP/DOWN PICK A CLUE   [E] READ IT   [TAB] CLOSE", frame.bottom - 18)


class ConfirmPanel(Panel):
    def __init__(self, title, lines, yes="YES", no="NO", default_yes=False):
        self.title, self.lines, self.yes_label, self.no_label = title, lines, yes, no
        self.yes = default_yes

    def handle_event(self, event):
        act = nav(event)
        if act in ("left", "right", "up", "down"):
            self.yes = not self.yes
        elif act == "back":
            self.close("no")
        elif act == "ok":
            self.close("yes" if self.yes else "no")

    def draw(self, surf):
        dim(surf, 150)
        rows = [r for line in self.lines for r in wrap_text(line, 220)]
        frame = pygame.Rect(0, 0, 252, 78 + len(rows) * 10)
        frame.center = (VIEW_W // 2, 140)
        warm_panel(surf, frame, self.title)
        for i, row in enumerate(rows):
            draw_text(surf, row, (frame.centerx, frame.top + 28 + i * 10), INK, 1, "midtop")
        for i, (label, sel) in enumerate(((self.yes_label, self.yes), (self.no_label, not self.yes))):
            r = pygame.Rect(0, 0, 100, 18)
            r.center = (frame.centerx - 56 + i * 112, frame.bottom - 22)
            pygame.draw.rect(surf, (90, 56, 30) if sel else (46, 28, 20), r)
            pygame.draw.rect(surf, A.BRASS_LT if sel else PANEL_IN, r, 1)
            draw_text(surf, ("> " if sel else "") + label, r.center, INK if sel else INK_SOFT, 1, "center")


class CompletePanel(Panel):
    """TRIAL 01 COMPLETE. THE GOLDEN AGE. REWARD: MEMORY FRAGMENT 01. Then back to the arcade, or stay a little longer."""

    def __init__(self, first_time):
        self.first_time = first_time
        self.index = 0
        self.time = 0.0

    def handle_event(self, event):
        act = nav(event)
        if act in ("up", "down", "left", "right"):
            self.index = 1 - self.index
        elif act == "ok":
            self.close("return" if self.index == 0 else "stay")
        elif act == "back":
            self.close("stay")

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        dim(surf, 190)
        k = min(1.0, self.time / 0.8)
        frame = pygame.Rect(0, 0, 300, 196)
        frame.center = (VIEW_W // 2, 148)
        warm_panel(surf, frame)
        draw_text(surf, "TRIAL 01 COMPLETE", (frame.centerx, frame.top + 16), scale_color(A.BRASS_LT, k), 2, "midtop", glow=(90, 56, 20))
        draw_text(surf, "THE GOLDEN AGE", (frame.centerx, frame.top + 38), scale_color(INK, k), 1, "midtop")
        surf.fill(PANEL_IN, (frame.left + 20, frame.top + 54, frame.w - 40, 1))
        draw_text(surf, "REWARD:", (frame.centerx, frame.top + 64), scale_color(INK_SOFT, k), 1, "midtop")
        cx, cy = frame.centerx, frame.top + 96
        glow = A.soft_light(26, (120, 90, 30))
        surf.blit(glow, glow.get_rect(center=(cx, cy)), special_flags=pygame.BLEND_RGB_ADD)
        bob = int(2 * math.sin(self.time * 3))
        pygame.draw.polygon(surf, scale_color((255, 214, 90), k), [(cx, cy - 12 + bob), (cx + 9, cy + bob), (cx, cy + 12 + bob), (cx - 9, cy + bob)])
        pygame.draw.polygon(surf, scale_color((255, 250, 210), k), [(cx, cy - 8 + bob), (cx + 4, cy + bob), (cx, cy + 8 + bob), (cx - 4, cy + bob)])
        text = "MEMORY FRAGMENT 01" + ("" if self.first_time else "  (ALREADY KEPT)")
        draw_text(surf, text, (frame.centerx, frame.top + 118), scale_color(A.BRASS_LT, k), 1, "midtop")
        for i, label in enumerate(("RETURN TO ARCADE", "STAY IN THE ROOM")):
            r = pygame.Rect(0, 0, 124, 18)
            r.center = (frame.centerx - 66 + i * 134, frame.bottom - 24)
            sel = i == self.index
            pygame.draw.rect(surf, (90, 56, 30) if sel else (46, 28, 20), r)
            pygame.draw.rect(surf, A.BRASS_LT if sel else PANEL_IN, r, 1)
            draw_text(surf, label, r.center, INK if sel else INK_SOFT, 1, "center")


# ------------------------------------------------------------------ Miao's hint bubble (never modal)
class HintBubble:
    """A speech bubble over Miao Meow that fades by itself. Only appears when the player asks; it covers no puzzle screen
    (the panels hide it) and takes no keys."""
    HOLD = 6.5
    FADE = 0.4

    def __init__(self):
        self.text = None
        self.age = 0.0

    @property
    def visible(self):
        return self.text is not None

    def show(self, text):
        self.text, self.age = text, 0.0

    def clear(self):
        self.text = None

    def update(self, dt):
        if self.text is not None:
            self.age += dt
            if self.age >= self.HOLD + self.FADE:
                self.text = None

    def draw(self, surf, anchor):
        if self.text is None:
            return
        rows = wrap_text(self.text, 150)
        w, h = 168, 12 + len(rows) * 10 + 8
        img = pygame.Surface((w, h + 5), pygame.SRCALPHA)
        pygame.draw.rect(img, A.LINE, (0, 0, w, h), border_radius=3)
        pygame.draw.rect(img, (250, 240, 214), (1, 1, w - 2, h - 2), border_radius=3)
        draw_text(img, "MIAO MEOW", (6, 4), (160, 100, 30))
        for i, row in enumerate(rows):
            draw_text(img, row, (6, 15 + i * 10), (70, 44, 30))
        pygame.draw.polygon(img, A.LINE, [(w // 2 - 4, h - 1), (w // 2 + 4, h - 1), (w // 2, h + 4)])
        pygame.draw.polygon(img, (250, 240, 214), [(w // 2 - 3, h - 2), (w // 2 + 3, h - 2), (w // 2, h + 2)])
        a = min(1.0, self.age / self.FADE, (self.HOLD + self.FADE - self.age) / self.FADE)
        img.set_alpha(int(255 * max(0.0, a)))
        rect = img.get_rect(midbottom=(anchor[0], anchor[1]))
        rect.clamp_ip(pygame.Rect(4, 4, VIEW_W - 8, VIEW_H - 8))
        surf.blit(img, rect)
