"""RETRO GAMING - ISSUE 1986: an old pixel-games magazine in the rack beside HOME's couch.

It is plain scenery with an [E] prompt: walk up, press E, and a page-turning reader opens (a cover and seven pages of
ordinary magazine: arcade history, a Gradius review, design trivia, difficulty, reader mail, useless facts). Reading is
free and repeatable and changes nothing: no tokens, no tickets, no notification, no quest event. Nothing in it points
anywhere; the vending machine's secret only counts when the REAL hidden screen opens.

MagazineStation  the magazine rack beside the couch (small, against the wall, so it never blocks anybody)
MagazineScene    the reader (a MenuScene owned by whoever pressed E; the other player spectates)
ARTICLES         the text of every page, as data (so it can be proofread and tested)
"""
import math

import pygame

from font import LINE_H
from gfx import scale_color
from menu_kit import FRAME, MenuScene
from settings import Col, Lofi
from stations import Station
from ui import draw_text, wrap_text

TITLE = "RETRO GAMING"
ISSUE = "ISSUE 1986"

PAPER = pygame.Rect(14, 46, FRAME.w - 16, 162)       # the page, inside the menu frame (above its footer)
FLIP_TIME = 0.24
MARGIN = 10
COL_GAP = 10
COL_W = (PAPER.w - 2 * MARGIN - COL_GAP) // 2        # two text columns per page
BODY_TOP = 44                                         # first line of body text (below title and byline)
BODY_BOTTOM = PAPER.h - 17                            # last pixel of body text (above the footer rule)
INK = (44, 30, 74)
INK_SOFT = (96, 78, 128)
PAPER_COLOR = (238, 228, 200)
PAPER_SHADE = (214, 200, 170)
HOT_PINK = (206, 40, 122)
DEEP_BLUE = (36, 70, 170)
GAP = 4                                               # space between paragraphs

# ------------------------------------------------------------------ the text
# blocks: ("h", heading) / ("p", paragraph) / ("row", left, right) / ("col",) = continue in the second column.
# `art` is (name, column, height).
ARTICLES = (
    None,                                             # 0: the cover
    {"section": "CONTENTS", "title": "IN THIS ISSUE", "byline": "RETRO GAMING  -  25 CENTS", "art": None,
     "blocks": (
         ("h", "INSIDE"),
         ("row", "2", "THE GOLDEN AGE OF ARCADES"),
         ("row", "3", "GRADIUS: THE REVIEW"),
         ("row", "4", "BEHIND THE PIXELS"),
         ("row", "5", "HARD AS NAILS"),
         ("row", "6", "READER MAIL AND SCORES"),
         ("row", "7", "USELESS FACTS"),
         ("col",),
         ("h", "FROM THE EDITOR"),
         ("p", "Welcome back, high-score hunters! This month our office fought over one joystick and nobody won. "
               "We tested 14 new games, wore out 3 buttons and ate far too many pretzels."),
         ("p", "Remember: a game is only unfair until you learn its pattern."),
     )},
    {"section": "FEATURE", "title": "THE GOLDEN AGE OF ARCADES", "byline": "BY P. QUARTERMAN", "art": ("cabinet", 1, 46),
     "blocks": (
         ("h", "QUARTERS EVERYWHERE"),
         ("p", "Walk into any mall in 1986 and you will hear beeps, zaps and clattering coins."),
         ("h", "A NEW KIND OF HERO"),
         ("p", "Pac-Man turned non-gamers into players. Space Invaders and Donkey Kong followed, and kids "
               "learned to read a screen like sailors read the sky."),
     )},
    {"section": "GAME REVIEW", "title": "GRADIUS: THE REVIEW", "byline": "KONAMI  -  ARCADE 1985  -  HOME 1986",
     "art": ("viper", 1, 46),
     "blocks": (
         ("h", "SPACE, BUT SPICY"),
         ("p", "In GRADIUS you fly the VIC VIPER. Cross volcanoes, caves and stone heads that spit "
               "rings. Yes, really."),
         ("h", "THE POWER-UP METER"),
         ("p", "Shoot glowing enemies to drop capsules. Each one moves a cursor along the meter. Cash in "
               "for upgrades."),
         ("h", "VERDICT"),
         ("p", "Gorgeous and tough. Lose a life, lose your upgrades."),
     )},
    {"section": "DESIGN", "title": "BEHIND THE PIXELS", "byline": "EARLY GAME DESIGN TRIVIA", "art": ("aliens", 1, 40),
     "blocks": (
         ("h", "TINY BOXES, BIG TRICKS"),
         ("p", "Early cabinets had almost no memory, so designers got clever. One alien often comes back "
               "in new colors."),
         ("h", "LITTLE SURPRISES"),
         ("p", "In 1979 a programmer hid his own name in a secret room of ATARI ADVENTURE. Some developers "
               "even left behind little surprises, like the famous Konami Code, which eventually became part "
               "of gaming folklore."),
     )},
    {"section": "OPINION", "title": "HARD AS NAILS", "byline": "ON DIFFICULTY AND CONTROLS", "art": ("stick", 1, 44),
     "blocks": (
         ("h", "ONE STICK, TWO BUTTONS"),
         ("p", "No tutorials here. A joystick, a button or two and a screen full of danger."),
         ("h", "THE ONE-CREDIT CLUB"),
         ("p", "Arcade games are hard on purpose: every try costs a quarter. The trick is learning "
               "patterns. Die, learn, try again."),
         ("h", "OUR ADVICE"),
         ("p", "Stay near the middle and never trust a quiet corner."),
     )},
    {"section": "YOUR PAGES", "title": "READER MAIL AND SCORES", "byline": "LETTERS, REVIEWS AND HIGH SCORES",
     "art": None,
     "blocks": (
         ("h", "DEAR RETRO GAMING"),
         ("p", "My cat walked across the joystick and set a high score. Is that cheating? - M. from Cherry Lane"),
         ("p", "Not at all. Please send us the cat's initials. - ED."),
         ("p", "I beat my brother's score by one point. He has not spoken to me in a week. Worth it. - T."),
         ("h", "TOP SCORES THIS MONTH"),
         ("row", "1", "MEW   120400"),
         ("row", "2", "ACE    98750"),
         ("row", "3", "ZAP    87200"),
         ("row", "4", "CAT    64100"),
         ("row", "5", "BOB    50300"),
     )},
    {"section": "FUN AND GAMES", "title": "USELESS FACTS", "byline": "NOBODY ASKED, BUT HERE THEY ARE", "art": None,
     "blocks": (
         ("h", "DID YOU KNOW?"),
         ("p", "Pac-Man was called Puck Man in Japan, until people worried what a prankster could do to the P."),
         ("p", "Donkey Kong exists because a plan to make a Popeye game fell through."),
         ("p", "The tallest stack of quarters ever fed to one cabinet in our office: 41. We counted."),
         ("h", "NEXT ISSUE"),
         ("p", "Racing games, pinball wizards and a very serious test of arcade pretzels."),
         ("p", "Until then, keep your thumbs warm and your coins handy."),
     )},
)
LAST_PAGE = len(ARTICLES) - 1
PAGE_NAMES = ("COVER",) + tuple(a["title"] for a in ARTICLES[1:])


# ------------------------------------------------------------------ art
def _paint(rows, colors, scale=1):
    s = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in colors:
                s.set_at((x, y), colors[ch])
    return pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale)) if scale > 1 else s


_VIPER = (
    "....rr..........",
    "...rrrr.........",
    "..wwwwww........",
    ".wwwwwwwwwww....",
    "bwwwwwwwwwwwwcc.",
    ".wwwwwwwwwww....",
    "..wwwwww........",
    "...rrrr.........",
    "....rr..........",
)
_VIPER_COLORS = {"r": (255, 70, 90), "w": (222, 228, 244), "b": (80, 200, 255), "c": (110, 240, 255)}
_ALIEN = (
    "..a....a..",
    "...a..a...",
    "..aaaaaa..",
    ".aa.aa.aa.",
    "aaaaaaaaaa",
    "a.aaaaaa.a",
    "a.a....a.a",
    "...aa.aa..",
)


def viper(scale=1):
    """The little starfighter of the cover and of the Gradius page."""
    return _paint(_VIPER, _VIPER_COLORS, scale)


def rack_sprite():
    """A small wooden magazine rack, 14x26, with a few magazines standing in it (one of them pink and cyan)."""
    s = pygame.Surface((14, 26), pygame.SRCALPHA)
    covers = ((70, 120, 200), HOT_PINK, (240, 190, 70), (90, 190, 150))
    for i, c in enumerate(covers):                               # magazines leaning in the pockets
        y = 2 + i * 5
        s.fill(c, (2, y, 10, 5))
        s.fill(scale_color(c, 1.3), (2, y, 10, 1))
        s.fill(PAPER_COLOR, (3 + i % 3, y + 2, 4, 1))
    s.fill((60, 200, 230), (8, 12, 3, 3))
    s.fill(Lofi.WOOD, (0, 0, 2, 24))                             # frame
    s.fill(Lofi.WOOD, (12, 0, 2, 24))
    s.fill(Lofi.WOOD_HI, (0, 0, 1, 24))
    for y in (6, 11, 16, 21):                                    # front rails
        s.fill(Lofi.WOOD_DARK, (0, y, 14, 1))
    s.fill(Lofi.WOOD_DARK, (1, 24, 3, 2))                        # feet
    s.fill(Lofi.WOOD_DARK, (10, 24, 3, 2))
    return s


def art_cabinet(surf, rect, t):
    """An upright arcade cabinet, with a screen that scrolls a few stars."""
    cab = pygame.Rect(0, 0, 36, rect.h - 10)
    cab.midtop = (rect.centerx, rect.y)
    surf.fill((52, 40, 110), cab)
    surf.fill((226, 60, 150), (cab.x, cab.y, cab.w, 6))
    draw_text(surf, "ARCADE", (cab.centerx, cab.y), (255, 240, 220), anchor="midtop")
    screen = pygame.Rect(cab.x + 4, cab.y + 9, cab.w - 8, 20)
    surf.fill((8, 6, 28), screen)
    for i in range(7):
        surf.fill((255, 255, 255), (screen.x + (i * 11 + int(t * 20)) % screen.w, screen.y + 2 + (i * 5) % 16, 1, 1))
    surf.fill((255, 214, 90), (screen.x + 6, screen.centery - 1, 4, 3))
    surf.fill((30, 22, 66), (cab.x, cab.y + 32, cab.w, cab.h - 32))
    surf.fill((226, 60, 150), (cab.x + 8, cab.y + 32, 3, 3))                 # stick and buttons
    surf.fill((80, 230, 255), (cab.x + 18, cab.y + 33, 3, 3))
    surf.fill((255, 214, 90), (cab.x + 24, cab.y + 33, 3, 3))
    pygame.draw.rect(surf, INK, cab, 1)
    draw_text(surf, "A 1986 CABINET", (rect.centerx, rect.bottom - 8), INK_SOFT, anchor="midtop")


def art_viper(surf, rect, t):
    """The Vic Viper over a starfield, shooting, with the power-up meter underneath."""
    box = pygame.Rect(rect.x, rect.y, rect.w, rect.h - 20)
    surf.fill((14, 10, 40), box)
    pygame.draw.rect(surf, INK, box, 1)
    for i in range(16):
        surf.fill((255, 255, 255) if i % 3 else (130, 120, 200),
                  (box.x + (i * 37 + int(t * 24 * (1 + i % 3))) % box.w, box.y + 3 + (i * 19) % (box.h - 6), 1, 1))
    ship = viper(2)
    surf.blit(ship, ship.get_rect(center=(box.x + 34, box.centery + int(math.sin(t * 2.5) * 2))))
    surf.fill(Col.YELLOW, (box.x + 56, box.centery, 12, 2))
    surf.fill((255, 90, 80), (box.right - 24, box.centery - 6, 9, 12))
    names = ("SPD", "MSL", "DBL", "LSR", "OPT", "?")
    lit = int(t * 1.5) % len(names)
    cell = (box.w - 5) // len(names)
    for i, name in enumerate(names):
        r = pygame.Rect(box.x + i * (cell + 1), box.bottom + 3, cell, 11)
        surf.fill((255, 214, 90) if i == lit else (60, 52, 110), r)
        pygame.draw.rect(surf, INK, r, 1)
        draw_text(surf, name, r.center, INK if i == lit else (200, 196, 236), anchor="center")


def art_aliens(surf, rect, t):
    """The same little alien in three palettes: the memory-saving trick the text talks about."""
    box = pygame.Rect(rect.x, rect.y, rect.w, rect.h)
    surf.fill((14, 10, 40), box)
    pygame.draw.rect(surf, INK, box, 1)
    palettes = ((90, 240, 120), (255, 120, 190), (90, 220, 255))
    for i, color in enumerate(palettes):
        alien = _paint(_ALIEN, {"a": color}, 2)
        bob = int(math.sin(t * 4 + i) * 1.5)
        surf.blit(alien, (box.x + 12 + i * 52, box.y + 6 + bob))
    draw_text(surf, "ONE SPRITE, THREE COLORS", (box.centerx, box.bottom - 11), (200, 196, 236), anchor="midtop")


def art_stick(surf, rect, t):
    """A joystick and two buttons."""
    base = pygame.Rect(0, 0, 72, 22)
    base.midbottom = (rect.centerx, rect.bottom - 12)
    surf.fill((52, 40, 110), base)
    surf.fill((86, 70, 160), (base.x, base.y, base.w, 3))
    pygame.draw.rect(surf, INK, base, 1)
    tilt = int(math.sin(t * 3) * 3)
    surf.fill((150, 150, 170), (base.x + 20 + tilt // 2, base.y - 12, 3, 12))
    pygame.draw.circle(surf, (226, 40, 70), (base.x + 21 + tilt, base.y - 14), 6)
    pygame.draw.circle(surf, (255, 150, 160), (base.x + 19 + tilt, base.y - 16), 2)
    for i, c in enumerate(((255, 214, 90), (80, 230, 255))):
        pygame.draw.circle(surf, scale_color(c, 0.6), (base.x + 46 + i * 12, base.y + 12), 4)
        pygame.draw.circle(surf, c, (base.x + 46 + i * 12, base.y + 11), 4)
    draw_text(surf, "ONE STICK, TWO BUTTONS", (rect.centerx, rect.bottom - 8), INK_SOFT, anchor="midtop")


ART = {"cabinet": art_cabinet, "viper": art_viper, "aliens": art_aliens, "stick": art_stick}


# ------------------------------------------------------------------ the prop
class MagazineStation(Station):
    """A magazine rack beside the couch (RETRO GAMING is in it). Furniture first: a small base against the wall."""
    prompt_label = "READ MAGAZINE"
    REACH = (36, 30)

    def __init__(self, pos=(212, 40)):
        x, y = pos
        super().__init__(rack_sprite(), pos, (x, y + 18, 14, 8), Col.CYAN, Col.YELLOW, 0.12)

    def interact(self, scene):
        scene.open_magazine()

    def draw(self, surf):
        super().draw(surf)
        if int(self.time * 2.5) % 9 < 2:                      # a little glint on the cover now and then
            x, y = self.rect.x + 9, self.rect.y + 12
            for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                surf.fill((255, 255, 255) if (dx, dy) == (0, 0) else (255, 236, 160), (x + dx, y + dy, 1, 1))


# ------------------------------------------------------------------ the reader
class MagazineScene(MenuScene):
    title = TITLE
    accent = Col.MAGENTA
    glow = Col.CYAN

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.page = 0
        self.flip = None                    # None, or {"t": 0..1, "from": page, "to": page}
        self.content_bottom = 0             # the lowest pixel of text on the last page rendered (layout checks)
        self.overflow = False               # did the last page rendered run out of room?
        interact = owner.controls.label("interact") or "E"
        self.hints = ("LEFT/RIGHT TURN PAGE", f"{interact} NEXT", "ESC CLOSE")

    # ------------------------------------------------------------ lifecycle
    def on_enter(self):
        self.play("card")                   # picking it up

    # ------------------------------------------------------------ input
    def on_action(self, action):
        if self.flip is not None:
            return                          # let the page land first
        if action == "back":
            self.close_reader()
        elif action == "right":
            self.turn(1)
        elif action == "left":
            self.turn(-1)
        elif action == "interact":
            if self.page >= LAST_PAGE:
                self.close_reader()
            else:
                self.turn(1)

    def close_reader(self):
        self.play("cancel")
        self.close()

    def turn(self, step):
        target = self.page + step
        if not 0 <= target <= LAST_PAGE:
            return
        self.flip = {"t": 0.0, "from": self.page, "to": target}
        self.page = target
        self.play("card")

    def update(self, dt):
        super().update(dt)
        if self.flip is not None:
            self.flip["t"] += dt / FLIP_TIME
            if self.flip["t"] >= 1.0:
                self.flip = None

    # ------------------------------------------------------------ draw
    def idle_message(self):
        return "COVER" if self.page == 0 else f"PAGE {self.page} OF {LAST_PAGE}  -  {PAGE_NAMES[self.page]}"

    def draw_balance(self, surf):
        """No ticket balance here - nothing in a magazine costs anything."""
        right = FRAME.right - 10
        draw_text(surf, ISSUE, (right, 12), Col.YELLOW, 2, anchor="topright", glow=(120, 80, 10))
        draw_text(surf, "FREE TO READ", (right, 30), Col.TEXT_MUTED, anchor="topright")

    def draw_body(self, surf):
        self.draw_frame(surf, TITLE)
        self.draw_page_area(surf)
        self.draw_arrows(surf)
        self.draw_footer(surf)

    def draw_page_area(self, surf):
        surf.fill((8, 5, 22), PAPER.inflate(6, 6))                         # the table under the magazine
        pygame.draw.rect(surf, scale_color(self.accent, 0.5), PAPER.inflate(6, 6), 1)
        if self.flip is None:
            surf.blit(self.render_page(self.page), PAPER.topleft)
            return
        t = self.flip["t"]
        forward = self.flip["to"] > self.flip["from"]
        surf.blit(self.render_page(self.flip["to"] if forward else self.flip["from"]), PAPER.topleft)
        # the turning leaf hinges on the left edge: forward it shrinks away (old page), backward it grows back (new page)
        leaf = self.render_page(self.flip["from"] if forward else self.flip["to"])
        k = (1.0 - t) if forward else t
        k = k * k * (3 - 2 * k)                                             # ease in/out
        width = max(1, int(PAPER.w * k))
        if k > 0.02:
            surf.blit(pygame.transform.scale(leaf, (width, PAPER.h)), PAPER.topleft)
            edge = PAPER.x + width
            surf.fill((70, 56, 100), (edge - 1, PAPER.y, 1, PAPER.h))      # the curling edge
            surf.fill((196, 184, 156), (edge, PAPER.y, 2, PAPER.h))

    def draw_arrows(self, surf):
        """Clickable < > under the corners of the page, plus the page dots."""
        y = PAPER.bottom + 4
        n = LAST_PAGE + 1
        for i in range(n):
            color = Col.YELLOW if i == self.page else (70, 56, 110)
            surf.fill(color, (FRAME.centerx - n * 5 + i * 10 + 1, y, 6, 2))
        left = pygame.Rect(PAPER.x, y - 3, 40, 9)
        right = pygame.Rect(PAPER.right - 44, y - 3, 44, 9)
        if self.page > 0:
            draw_text(surf, "< BACK", left.topleft, Col.CYAN)
            self.hit(left, lambda: self.on_action("left"))
        draw_text(surf, "CLOSE >" if self.page >= LAST_PAGE else "NEXT >", right.topright, Col.CYAN, anchor="topright")
        self.hit(right, lambda: self.on_action("interact"))

    # ------------------------------------------------------------ pages
    def render_page(self, index):
        page = pygame.Surface(PAPER.size)
        self.content_bottom, self.overflow = 0, False
        if index == 0:
            self._cover(page)
        else:
            self._article(page, index, ARTICLES[index])
        return page

    def _chrome(self, page, section, number):
        """Newsprint, the running header and footer shared by every inside page."""
        w, h = page.get_size()
        page.fill(PAPER_COLOR)
        for x in range(0, w, 4):                                            # faint newsprint dots
            page.fill(PAPER_SHADE, (x, 2, 1, 1))
        page.fill(HOT_PINK, (0, 0, w, 12))
        draw_text(page, section, (MARGIN, 3), (255, 246, 236))
        draw_text(page, f"{TITLE} {ISSUE}", (w - MARGIN, 3), (255, 214, 232), anchor="topright")
        page.fill(INK_SOFT, (MARGIN, h - 13, w - 2 * MARGIN, 1))
        draw_text(page, str(number), (w - MARGIN, h - 10), INK_SOFT, anchor="topright")
        draw_text(page, "PRESS START", (MARGIN, h - 10), INK_SOFT)

    def _article(self, page, number, article):
        self._chrome(page, article["section"], number)
        draw_text(page, article["title"], (MARGIN, 16), HOT_PINK, 2)
        draw_text(page, article["byline"], (MARGIN, 33), DEEP_BLUE)
        bottoms = [BODY_BOTTOM, BODY_BOTTOM]
        art = article["art"]
        if art:                                                             # the picture sits at the foot of its column
            name, col, height = art
            rect = pygame.Rect(MARGIN + col * (COL_W + COL_GAP), BODY_BOTTOM - height, COL_W, height)
            ART[name](page, rect, self.time)
            bottoms[col] = rect.y - GAP - 1
        self._flow(page, article["blocks"], bottoms)

    def _flow(self, page, blocks, bottoms):
        """Pour the blocks into two columns, line by line. Every body line is drawn the same way (one ink, one size):
        nothing in an article is dressed up more than its neighbours. A ("col",) block starts the second column."""
        state = {"col": 0, "y": BODY_TOP}

        def next_column():
            if state["col"] == 1:
                self.overflow = True
            state["col"], state["y"] = 1, BODY_TOP

        def put(text, color, dx=0, rank=None):
            if state["y"] + LINE_H > bottoms[state["col"]]:
                next_column()
            x = MARGIN + state["col"] * (COL_W + COL_GAP)
            if rank is not None:
                draw_text(page, rank, (x, state["y"]), HOT_PINK)
            draw_text(page, text, (x + dx, state["y"]), color)
            state["y"] += LINE_H
            self.content_bottom = max(self.content_bottom, state["y"])

        for block in blocks:
            kind = block[0]
            if kind == "col":
                if state["col"] == 0:
                    state["col"], state["y"] = 1, BODY_TOP
            elif kind == "h":
                if state["y"] + 2 * LINE_H > bottoms[state["col"]]:                   # never leave a heading alone at the bottom
                    next_column()
                put(block[1], HOT_PINK)
            elif kind == "row":
                put(block[2], INK, dx=14, rank=block[1])
                state["y"] += 2
            else:
                for line in wrap_text(block[1], COL_W):
                    put(line, INK)
                state["y"] += GAP

    # --- cover
    def _cover(self, page):
        w, h = page.get_size()
        for y in range(h):                                                  # a deep space gradient
            k = y / h
            page.fill((int(14 + 36 * k), int(8 + 10 * k), int(44 + 40 * k)), (0, y, w, 1))
        for i in range(46):                                                 # fixed star field that slowly twinkles
            sx, sy = (i * 83 + 17) % w, (i * 47 + 9) % (h - 20)
            on = (i + int(self.time * 2)) % 5
            page.fill((255, 255, 255) if on else (120, 110, 190), (sx, sy, 1, 1))
        pygame.draw.rect(page, Col.MAGENTA, page.get_rect(), 2)
        draw_text(page, "THE MAGAZINE FOR VIDEO GAME FANS", (w // 2, 8), Col.CYAN, anchor="midtop")
        draw_text(page, "RETRO", (w // 2, 22), Col.YELLOW, 4, anchor="midtop", glow=(150, 70, 10))
        draw_text(page, "GAMING", (w // 2, 54), Col.MAGENTA, 4, anchor="midtop", glow=(110, 20, 90))
        bob = int(math.sin(self.time * 3) * 2)
        ship = viper(4)
        page.blit(ship, ship.get_rect(center=(w // 2, 108 + bob)))
        for i in range(3):                                                  # laser shots
            page.fill(Col.CYAN, (w // 2 + 40 + i * 24, 108 + bob, 12, 2))
        banner = pygame.Rect(0, 0, 150, 16)
        banner.midbottom = (w // 2, h - 14)
        page.fill(HOT_PINK, banner)
        pygame.draw.rect(page, Col.YELLOW, banner, 1)
        draw_text(page, ISSUE, banner.center, (255, 250, 236), 2, anchor="center")
        draw_text(page, "GRADIUS  -  ARCADE HISTORY  -  HIGH SCORES", (w // 2, h - 10), Col.TEXT, anchor="midtop")
        self.content_bottom = h - 10 + LINE_H
