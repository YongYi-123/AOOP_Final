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
        self.marks_seen = []                    # the "mark"s of pages that have been on screen (the cat drawings)
        self._seen_page()

    def _seen_page(self):
        mark = self.pages[self.index].get("mark") if self.pages else None
        if mark and mark not in self.marks_seen:
            self.marks_seen.append(mark)

    def _turn(self, delta):
        i = max(0, min(len(self.pages) - 1, self.index + delta))
        if i != self.index:
            self.index = i
            self.play("page_turn")
            self._seen_page()

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
            if data.get("picture"):
                pic = A.picture(data["picture"])
                rect = pic.get_rect(midtop=(page.centerx, page.top + 30))
                pygame.draw.rect(surf, (30, 18, 12), rect.inflate(4, 4))
                surf.blit(pic, rect)
                if data.get("label"):
                    draw_text(surf, data["label"], (rect.centerx, rect.centery + 1), (90, 70, 100), 1, "midtop")
                y = rect.bottom + 8
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
    if clue_key == "cartridge":
        return [dict(p) for p in C.CARTRIDGE_PAGES]
    if clue_key == "index":
        return [dict(C.INDEX_STRIP, picture="index_strip", label=C.INDEX_LOCATION)]
    if clue_key == "catnote":
        return [dict(C.CAT_NOTE), dict(C.CAT_SKETCH)]
    if clue_key == "carving":
        return [dict(C.CARVING_PAGE)]
    if clue_key.startswith("photo_"):
        return [photo_page(clue_key[6:])]
    if clue_key in C.BOOKS:
        return [dict(p) for p in C.BOOKS[clue_key][2]]
    raise KeyError(clue_key)


def photo_page(key, title="AN OLD PHOTOGRAPH"):
    """One photograph, full size, with what is scribbled on its back."""
    return {"title": title, "picture": f"photo_{key}", "text": C.PHOTO_BACKS[key]}


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
    Playing is free, there is no life limit (a missed ball just goes back on the paddle), and a cleared game stays cleared."""
    LINE_TIME = 0.85

    def __init__(self, play=None, cleared=False, on_clear=None, indexed=True, index_lines=False):
        self.play = play or (lambda name: None)
        self.indexed = indexed                  # the archive index is in hand (or not needed): LOCKED FILES can find the archive
        self.files_lines = (C.INDEX_LINES if index_lines else ()) + C.ARCHIVE_LINES
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
            if act in ("ok", "back") and self.stage_time > self.files_ready:
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
            what = d.choose(self.cleared, self.indexed)
            if what == "play":
                self._start_game()
            elif what == "scores":
                self._go("scores")
            elif what == "files":
                self.play("confirm")
                self._go("files")
            elif what in ("locked", "noindex"):
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
            if label == "LOCKED FILES" and not (self.cleared and self.indexed):
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

    LINE_GAP = 1.0

    @property
    def files_ready(self):
        """Seconds into the files screen before E goes on (every line typed, the card up)."""
        return self.card_at + 1.6

    @property
    def card_at(self):
        return 0.2 + len(self.files_lines) * self.LINE_GAP + 0.2

    def _draw_files(self, view, x0):
        t = self.stage_time
        for i, text in enumerate(self.files_lines):
            start = 0.2 + i * self.LINE_GAP
            if t > start:
                draw_text(view, "SYSTEM: " + text[:int((t - start) * 40)], (12, 16 + i * 14), PHOSPHOR)
        top = 30 + len(self.files_lines) * 14
        if t > self.card_at:
            k = min(1.0, (t - self.card_at) / 0.8)
            card = pygame.Rect(SCREEN.w // 2 - 118, top + 18, 236, 90)
            pygame.draw.rect(view, scale_color((24, 84, 62), k), card)
            pygame.draw.rect(view, scale_color(PHOSPHOR, k), card, 1)
            draw_text(view, C.ADMIN_CARD[0], (card.centerx, card.top + 18), scale_color((200, 255, 225), k), 3, "midtop", glow=scale_color((20, 90, 60), k))
            draw_text(view, C.ADMIN_CARD[1], (card.centerx, card.top + 58), scale_color(PHOSPHOR, k), 1, "midtop")
        if t > self.files_ready and int(self.time * 2) % 2 == 0:
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

    def inventory_rows(self):
        """(icon, label) for the Trial Inventory: the things carried, and the photos still in hand (not on the board)."""
        rows = []
        for item in self.run.inventory:
            rows.append((A.index_icon() if item == C.ARCHIVE_INDEX else A.disk_icon(), item))
        loose = len(self.run.photos_in_hand) if not self.run.photos_solved else 0
        if loose:
            rows.append((A.photo_icon(), "OLD PHOTOGRAPH" + (f" X{loose}" if loose > 1 else "")))
        return rows

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
        rows = self.inventory_rows()
        if not rows:
            draw_text(surf, "EMPTY", (x, y + 12), (130, 106, 80))
        for i, (icon, item) in enumerate(rows):
            surf.blit(icon, (x, y + 12 + i * 16))
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
    """The end of a Secret Trial, the same for every trial: the room fades to black, MEMORY FRAGMENT 0N RECOVERED. and
    TRIAL 0N COMPLETE. come up, then the card (REWARD: MEMORY FRAGMENT 0N) offers the way back, or a little longer here.
    E during the black skips straight to the card. prelude=False: the scene has already shown the black and the lines."""
    FADE = 0.8
    LINE_TIMES = (0.9, 1.9)
    CARD_AT = 3.4
    LINE_COLORS = ((255, 230, 170), (180, 230, 255))

    def __init__(self, first_time, number=1, title="THE GOLDEN AGE", prelude=True, stay_label="STAY IN THE ROOM"):
        self.first_time = first_time
        self.number = number
        self.title = title
        self.stay_label = stay_label
        self.index = 0
        self.time = 0.0
        self.card_at = self.CARD_AT if prelude else 0.0
        self.prelude = prelude

    @property
    def lines(self):
        return (f"MEMORY FRAGMENT {self.number:02d} RECOVERED.", f"TRIAL {self.number:02d} COMPLETE.")

    @property
    def ready(self):
        """The card is up and takes keys."""
        return self.time >= self.card_at

    def handle_event(self, event):
        act = nav(event)
        if not self.ready:
            if act == "ok":
                self.time = self.card_at                    # skip the black
            return
        if act in ("up", "down", "left", "right"):
            self.index = 1 - self.index
        elif act == "ok":
            self.close("return" if self.index == 0 else "stay")
        elif act == "back":
            self.close("stay")

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        black = pygame.Surface((VIEW_W, VIEW_H))
        black.set_alpha(int(255 * min(1.0, self.time / self.FADE)) if self.prelude else 255)
        surf.blit(black, (0, 0))
        if not self.ready:
            for i, (line, at) in enumerate(zip(self.lines, self.LINE_TIMES)):
                k = max(0.0, min(1.0, (self.time - at) / 0.5))
                if k > 0:
                    draw_text(surf, line, (VIEW_W // 2, 128 + i * 20), scale_color(self.LINE_COLORS[i], k), 1, "midtop", glow=(80, 50, 20))
            return
        k = min(1.0, (self.time - self.card_at) / 0.8)
        frame = pygame.Rect(0, 0, 300, 196)
        frame.center = (VIEW_W // 2, 148)
        warm_panel(surf, frame)
        draw_text(surf, f"TRIAL {self.number:02d} COMPLETE", (frame.centerx, frame.top + 16), scale_color(A.BRASS_LT, k), 2, "midtop", glow=(90, 56, 20))
        draw_text(surf, self.title, (frame.centerx, frame.top + 38), scale_color(INK, k), 1, "midtop")
        surf.fill(PANEL_IN, (frame.left + 20, frame.top + 54, frame.w - 40, 1))
        draw_text(surf, "REWARD:", (frame.centerx, frame.top + 64), scale_color(INK_SOFT, k), 1, "midtop")
        cx, cy = frame.centerx, frame.top + 96
        glow = A.soft_light(26, (120, 90, 30))
        surf.blit(glow, glow.get_rect(center=(cx, cy)), special_flags=pygame.BLEND_RGB_ADD)
        bob = int(2 * math.sin(self.time * 3))
        for i, c in enumerate(((255, 120, 190), (120, 230, 255))):
            off = -6 + i * 12
            pygame.draw.polygon(surf, scale_color(c, k), [(cx + off, cy - 12 + bob), (cx + off + 8, cy + bob), (cx + off, cy + 12 + bob), (cx + off - 8, cy + bob)])
        pygame.draw.polygon(surf, scale_color((255, 250, 220), k), [(cx, cy - 7 + bob), (cx + 4, cy + bob), (cx, cy + 7 + bob), (cx - 4, cy + bob)])
        text = f"MEMORY FRAGMENT {self.number:02d}" + ("" if self.first_time else "  (ALREADY KEPT)")
        draw_text(surf, text, (frame.centerx, frame.top + 118), scale_color(A.BRASS_LT, k), 1, "midtop")
        for i, label in enumerate(("RETURN TO ARCADE", self.stay_label)):
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


# ------------------------------------------------------------------ PUZZLE 05: the photo board
class PhotoBoardPanel(Panel):
    """The wooden photo board, up close: four slots in a row on the board, the photos in hand on the desk below it.
    Arrows move, E picks a photo up and puts it down (onto a slot, or back on the desk), V looks at one full size, ESC puts
    a held photo back or closes. No timer, no penalty. When the board is right it clicks and swings open: the panel closes
    with result "solved". A solved board can still be looked at (nothing moves any more)."""
    OPEN_TIME = 2.2

    def __init__(self, run, play=None):
        self.run = run
        self.play = play or (lambda name: None)
        self.row, self.col = (0, 0)              # row 0: the board's slots, row 1: the photos in hand
        self.held = None                         # the photo picked up (it stays where it was until it is put down)
        self.zoom = None                         # the photo shown full size
        self.time = 0.0
        self.opening = None                      # seconds since the board clicked open
        self.wrong = 0.0                         # a little rattle after a full but wrong board
        if not run.photos_in_hand and not any(run.board.slots):
            self.row = 0
        elif run.photos_in_hand and not run.photos_solved:
            self.row = 1

    @property
    def solved(self):
        return self.run.photos_solved

    @property
    def hand(self):
        return self.run.photos_in_hand

    def under_cursor(self):
        if self.row == 0:
            return self.run.board.slots[self.col]
        hand = self.hand
        return hand[self.col] if self.col < len(hand) else None

    def _width(self, row):
        return G.PHOTO_SLOTS if row == 0 else max(1, len(self.hand))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.opening is not None:
            return
        if self.zoom is not None:                                   # any key puts the close look away
            self.zoom = None
            return
        act = nav(event)
        if event.key == pygame.K_v:
            photo = self.held or self.under_cursor()
            if photo:
                self.zoom = photo
                self.play("page_turn")
            return
        if act == "back":
            if self.held:
                self.held = None
            else:
                self.close("closed")
        elif act in ("left", "right"):
            self.col = (self.col + (1 if act == "right" else -1)) % self._width(self.row)
        elif act in ("up", "down"):
            if not self.solved:
                self.row = 1 - self.row
                self.col = min(self.col, self._width(self.row) - 1)
        elif act == "ok":
            self._use()

    def _use(self):
        if self.solved:
            photo = self.under_cursor()
            if photo:
                self.zoom = photo
            return
        target = self.under_cursor()
        if self.held is None:
            if target:
                self.held = target
                self.play("card")
            return
        if self.row == 0:
            self.run.place_photo(self.held, self.col)
            self.play("card")
        else:
            self.run.take_photo(self.held)
            self.play("card")
            self.col = min(self.col, self._width(1) - 1)
        self.held = None
        self._check()

    def _check(self):
        board = self.run.board
        if not board.full:
            return
        if self.run.check_board():
            self.opening = 0.0
            self.play("board_click")
        else:
            self.wrong = 0.6
            self.play("circuit_click")

    def update(self, dt):
        self.time += dt
        self.wrong = max(0.0, self.wrong - dt)
        if self.opening is not None:
            self.opening += dt
            if self.opening >= self.OPEN_TIME:
                self.close("solved")

    # ------------------------------------------------------------ drawing
    def slot_rect(self, i):
        w, h = A.PHOTO_SIZE[0] + 8, A.PHOTO_SIZE[1] + 8
        x0 = VIEW_W // 2 - (4 * w + 3 * 6) // 2
        return pygame.Rect(x0 + i * (w + 6), 62, w, h)

    def hand_rect(self, i):
        w, h = A.PHOTO_SIZE[0] + 4, A.PHOTO_SIZE[1] + 4
        n = max(1, len(self.hand))
        x0 = VIEW_W // 2 - (n * w + (n - 1) * 8) // 2
        return pygame.Rect(x0 + i * (w + 8), 160, w, h)

    def _thumb(self, photo, size):
        return pygame.transform.scale(A.photo(photo), size)

    def draw(self, surf):
        if self.zoom:
            self._draw_zoom(surf)
            return
        dim(surf, 170)
        frame = pygame.Rect(0, 0, 344, 232)
        frame.center = (VIEW_W // 2, 140)
        warm_panel(surf, frame, C.PHOTO_BOARD_TITLE)
        board = pygame.Rect(0, 0, 326, 72)
        board.midtop = (VIEW_W // 2, 54)
        shake = int(2 * math.sin(self.time * 70)) if self.wrong > 0 else 0
        if self.solved:                                              # the little drawer that drops out from under the board
            k = 1.0 if self.opening is None else min(1.0, max(0.0, (self.opening - 0.3) / 0.9))
            tray = pygame.Rect(0, 0, 150, 44)
            tray.midtop = (board.centerx, board.bottom - 44 + int(46 * k))
            pygame.draw.rect(surf, A.WOOD_DK, tray.inflate(4, 2))
            pygame.draw.rect(surf, (24, 14, 10), tray.inflate(-8, -8))
            strip = pygame.Rect(0, 0, 112, 20)
            strip.center = (tray.centerx, tray.centery - 1)
            surf.fill((250, 244, 222), strip)
            surf.fill((184, 70, 56), (strip.x, strip.y, strip.w, 4))
            draw_text(surf, "A:/MEMORY/01", (strip.centerx, strip.y + 8), (90, 70, 100), 1, "midtop")
            surf.fill(A.WOOD, (tray.x, tray.bottom - 5, tray.w, 5))
            surf.fill(A.BRASS, (tray.centerx - 5, tray.bottom - 4, 10, 2))
        b = board.move(shake, 0)
        pygame.draw.rect(surf, A.WOOD_DK, b.inflate(4, 4), border_radius=2)
        pygame.draw.rect(surf, A.WOOD_MD, b, border_radius=2)
        for y in range(b.top + 6, b.bottom, 7):
            surf.fill(A.mul(A.WOOD_MD, 0.9), (b.left + 3, y, b.w - 6, 1))
        for i in range(G.PHOTO_SLOTS):
            r = self.slot_rect(i).move(shake, 0)
            pygame.draw.rect(surf, (52, 32, 20), r)
            pygame.draw.rect(surf, A.WOOD_DK, r, 1)
            photo = self.run.board.slots[i]
            if photo:
                img = A.photo(photo).copy()
                if photo == self.held:
                    img.set_alpha(80)
                surf.blit(img, (r.x + 4, r.y + 4))
            surf.fill(A.BRASS_LT, (r.centerx - 1, r.y - 2, 3, 3))       # the brass pin
            if self.row == 0 and self.col == i and self.opening is None:
                self._cursor(surf, r)
        if not self.solved:                                          # the photos in hand, on the desk under the board
            draw_text(surf, "IN HAND", (frame.left + 14, 146), INK_SOFT)
            if not self.hand:
                draw_text(surf, "NOTHING", (VIEW_W // 2, 178), (130, 106, 80), 1, "midtop")
            for i, photo in enumerate(self.hand):
                r = self.hand_rect(i)
                img = A.photo(photo).copy()
                if photo == self.held:
                    img.set_alpha(80)
                surf.blit(img, (r.x + 2, r.y + 2))
                if self.row == 1 and self.col == i:
                    self._cursor(surf, r)
        if self.held:                                               # the lifted photo floats by the cursor
            r = self.slot_rect(self.col) if self.row == 0 else self.hand_rect(min(self.col, max(0, len(self.hand) - 1)))
            img = pygame.transform.scale(A.photo(self.held), (48, 36))
            bob = int(2 * math.sin(self.time * 5))
            pygame.draw.rect(surf, (20, 12, 8), (r.centerx - 17, r.top - 19 + bob, 50, 38))
            surf.blit(img, (r.centerx - 18, r.top - 20 + bob))
        status = ""
        if self.opening is not None:
            status = C.PHOTO_BOARD_CLICK
        elif self.wrong > 0 or (self.run.board.full and not self.solved):
            status = C.PHOTO_BOARD_WRONG
        if status:
            draw_text(surf, status, (VIEW_W // 2, frame.bottom - 34), INK, 1, "midtop")
        keys = "ARROWS MOVE  [E] PICK UP/PUT DOWN  [V] LOOK  [ESC] CLOSE"
        if self.solved:
            keys = "LEFT/RIGHT MOVE   [E] LOOK CLOSER   [ESC] CLOSE"
        hint_line(surf, keys, frame.bottom - 18)

    def _cursor(self, surf, r):
        col = (255, 240, 170) if int(self.time * 3) % 2 == 0 else (210, 170, 70)
        pygame.draw.rect(surf, col, r.inflate(4, 4), 2)

    def _draw_zoom(self, surf):
        dim(surf, 236)
        img = A.photo(self.zoom, 4)
        rect = img.get_rect(center=(VIEW_W // 2, 128))
        pygame.draw.rect(surf, (20, 12, 8), rect.inflate(6, 6))
        surf.blit(img, rect)
        for i, row in enumerate(wrap_text(C.PHOTO_BACKS[self.zoom], 300)):
            draw_text(surf, row, (VIEW_W // 2, rect.bottom + 8 + i * 10), INK, 1, "midtop")
        hint_line(surf, "ANY KEY: BACK", VIEW_H - 18)


# ------------------------------------------------------------------ OPTIONAL: the plushie's coin-bell
class BellPanel(Panel):
    """The Miao Meow Plushie in your hands, its little coin-bell turned up: three tiny dials, each showing a little cat.
    LEFT / RIGHT pick a dial, UP / DOWN turn it, E jingles the bell. A wrong jingle is just a dull little clink. Right:
    the bell rings softly and the panel closes with "rang". Afterwards the dials stay put and the bell still rings."""
    RING_TIME = 1.6
    CREAM_BG, STITCH = (250, 232, 220), (214, 150, 150)

    def __init__(self, run, play=None):
        self.run = run
        self.play = play or (lambda name: None)
        self.cursor = 0
        self.time = 0.0
        self.ringing = None                     # seconds since the right ring
        self.wobble = 0.0                       # a wrong jingle
        self.turned = 0
        self.last = None                        # "dull" / "ring" / "open"

    @property
    def bell(self):
        return self.run.bell

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.ringing is not None:
            return
        act = nav(event)
        if act == "back":
            self.close("closed")
        elif act in ("left", "right"):
            self.cursor = (self.cursor + (1 if act == "right" else -1)) % 3
        elif act in ("up", "down") and not self.run.bell_solved:
            self.bell.turn(self.cursor, -1 if act == "up" else 1)
            self.turned += 1
            self.play("bell_tick")
        elif act == "ok":
            self.last = self.run.jingle()
            if self.last == "dull":
                self.wobble = 0.5
                self.play("bell_dull")
            else:
                self.play("bell_ring")
                if self.last == "open":
                    self.ringing = 0.0
                else:
                    self.wobble = 0.5

    def update(self, dt):
        self.time += dt
        self.wobble = max(0.0, self.wobble - dt)
        if self.ringing is not None:
            self.ringing += dt
            if self.ringing >= self.RING_TIME:
                self.close("rang")

    def draw(self, surf):
        dim(surf, 160)
        frame = pygame.Rect(0, 0, 276, 248)
        frame.center = (VIEW_W // 2, 146)
        pygame.draw.rect(surf, (60, 34, 30), frame.inflate(4, 4), border_radius=8)
        pygame.draw.rect(surf, self.CREAM_BG, frame, border_radius=8)
        for x in range(frame.left + 6, frame.right - 6, 6):           # a stitched hem, like the plushie's
            surf.fill(self.STITCH, (x, frame.top + 5, 3, 1))
            surf.fill(self.STITCH, (x, frame.bottom - 6, 3, 1))
        draw_text(surf, C.BELL_TITLE, (frame.centerx, frame.top + 11), (150, 80, 70), 1, "midtop")
        tilt = math.sin(self.time * 30) * self.wobble * 0.6
        plush = pygame.transform.scale(A.plushie(), (21 * 5, 21 * 5))
        if self.ringing is not None:
            tilt = math.sin(self.ringing * 18) * max(0.0, 1.0 - self.ringing / self.RING_TIME) * 6
        plush = pygame.transform.rotate(plush, tilt)
        surf.blit(plush, plush.get_rect(midtop=(frame.centerx, frame.top + 26)))
        # the coin-bell, held up close: gold, with three little windows
        bell = pygame.Rect(0, 0, 150, 52)
        bell.center = (frame.centerx, 206)
        bell.x += int(3 * math.sin(self.time * 40) * self.wobble)
        glow = 0.0 if self.ringing is None else max(0.0, 1.0 - self.ringing / self.RING_TIME)
        if glow:
            g = A.soft_light(60, (120, 90, 30))
            surf.blit(g, g.get_rect(center=bell.center), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.ellipse(surf, (172, 116, 40), bell.inflate(4, 4))
        pygame.draw.ellipse(surf, (236, 182, 64), bell)
        pygame.draw.ellipse(surf, (255, 232, 140), (bell.x + 16, bell.y + 4, 60, 10))
        for i, sym in enumerate(self.bell.symbols):
            r = pygame.Rect(0, 0, 40, 40)
            r.center = (bell.centerx + (i - 1) * 46, bell.centery)
            pygame.draw.rect(surf, (172, 116, 40), r.inflate(2, 2), border_radius=4)
            pygame.draw.rect(surf, (255, 246, 220), r, border_radius=4)
            icon = pygame.transform.scale(A.cat_icon(sym, (60, 46, 52), (255, 246, 220), (150, 120, 200)), (36, 36))
            surf.blit(icon, icon.get_rect(center=r.center))
            if i == self.cursor and self.ringing is None:
                col = (255, 140, 150) if int(self.time * 3) % 2 == 0 else (220, 110, 120)
                pygame.draw.rect(surf, col, r.inflate(6, 6), 2, border_radius=5)
                if not self.run.bell_solved:
                    pygame.draw.polygon(surf, col, [(r.centerx - 4, r.top - 6), (r.centerx + 4, r.top - 6), (r.centerx, r.top - 10)])
                    pygame.draw.polygon(surf, col, [(r.centerx - 4, r.bottom + 6), (r.centerx + 4, r.bottom + 6), (r.centerx, r.bottom + 10)])
        status = ""
        if self.ringing is not None or (self.last in ("ring", "open") and self.wobble > 0):
            status = "RING... RING..."
        elif self.last == "dull" and self.wobble > 0:
            status = "CLINK."
        if status:
            draw_text(surf, status, (frame.centerx, frame.bottom - 32), (150, 80, 70), 1, "midtop")
        keys = "ARROWS PICK / TURN   [E] JINGLE   [ESC] PUT DOWN"
        if self.run.bell_solved:
            keys = "[E] JINGLE   [ESC] PUT DOWN"
        draw_text(surf, keys, (frame.centerx, frame.bottom - 18), (150, 110, 100), 1, "midtop")
