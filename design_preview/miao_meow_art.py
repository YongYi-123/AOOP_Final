"""Miao Meow pixel art, drawn procedurally onto exact pixel grids (design preview only).

Nothing here is imported by the game. Sprites are painted at their native size
(32x32 sprite, 40x40 portraits, small icons) and only ever scaled up with
nearest-neighbour, so every preview shows the real pixels.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "arcade_lobby"))

import pygame  # noqa: E402

from gfx import outlined  # noqa: E402
from settings import Col  # noqa: E402

# ---------------------------------------------------------------- palette
PAL = {
    "F": (44, 50, 104),        # fur, deep navy-black (lifted a little so it reads on the dark floor)
    "H": (82, 92, 160),       # fur highlight
    "S": (32, 36, 80),        # fur shade
    "R": (112, 100, 226),     # rim light (violet) on the lit edges
    "E": (255, 70, 200),      # inner ear / ear glow  (Col.MAGENTA)
    "G": (190, 255, 60),      # eye, fluorescent yellow-green
    "g": (14, 10, 30),        # pupil
    "W": (255, 255, 255),     # eye sparkle
    "N": (255, 140, 180),     # nose
    "M": (150, 152, 214),     # pale muzzle
    "B": (255, 110, 170),     # blush
    "P": (128, 72, 232),      # jacket purple
    "p": (86, 46, 176),       # jacket shade
    "L": (172, 124, 255),     # jacket light
    "C": (80, 240, 255),      # cyan neon trim   (Col.CYAN)
    "X": (255, 70, 200),      # magenta neon trim (Col.MAGENTA)
    "Y": (255, 214, 90),      # token bell        (Col.YELLOW)
    "y": (196, 142, 40),      # token bell edge
    "T": (120, 255, 255),     # tail tip glow
    "K": (12, 8, 22),         # outline (Col.OUTLINE)
}


class Grid:
    """A small painting surface addressed by palette letters."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cells = [["." for _ in range(w)] for _ in range(h)]

    def px(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.cells[y][x] = ch

    def span(self, y, x0, x1, ch):
        for x in range(x0, x1 + 1):
            self.px(x, y, ch)

    def rect(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            self.span(y, x0, x1, ch)

    def mspan(self, y, x0, x1, ch):
        """Span plus its mirror image (the grid is symmetric about its centre)."""
        self.span(y, x0, x1, ch)
        self.span(y, self.w - 1 - x1, self.w - 1 - x0, ch)

    def mpx(self, x, y, ch):
        self.px(x, y, ch)
        self.px(self.w - 1 - x, y, ch)

    def get(self, x, y):
        return self.cells[y][x] if 0 <= x < self.w and 0 <= y < self.h else "."

    def rim(self, fur="FHS"):
        """Light the fur pixels whose top or left neighbour is empty."""
        todo = []
        for y in range(self.h):
            for x in range(self.w):
                if self.cells[y][x] in fur and (self.get(x, y - 1) == "." or self.get(x - 1, y) == "."):
                    todo.append((x, y))
        for x, y in todo:
            self.cells[y][x] = "R"

    def surface(self):
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for y, row in enumerate(self.cells):
            for x, ch in enumerate(row):
                if ch != ".":
                    s.set_at((x, y), (*PAL[ch], 255))
        return s

    def ascii(self):
        return "\n".join("".join(r) for r in self.cells)


# ---------------------------------------------------------------- world sprite (Mochi's own pipeline)
# Not redrawn by hand: this reuses the game's cat painter (cat_sprites.draw_cat) and Mochi's own eye painter, so
# the body, head, ears, eyes, outline and proportions are exactly Mochi's. Only the fur colour changes (black cat)
# and the body wears a hoodie.
from cat_sprites import _SIT_TAILS, CatLook, draw_cat  # noqa: E402
import shopkeeper as _mochi  # noqa: E402

GOLD = (255, 214, 90)                    # Mochi's iris colour: kept
SOFT_GREY = (176, 178, 206)             # replaces Mochi's pink: inner ears and nose
FUR_HI, FUR_LO = (92, 98, 154), (36, 38, 72)
LOOK = CatLook(fur=(58, 62, 104), shade=(40, 43, 80), belly=(158, 162, 206), lid=GOLD, nose=SOFT_GREY)
CREAM = (255, 244, 220)

# name: colours + style. Styles: pocket (pullover), heart (pullover with a chest patch), zip (zip-up), stripe (pullover with a band)
HOODIES = {
    "purple": dict(label="LAVENDER PULLOVER", main=(156, 118, 228), shade=(116, 82, 190), light=(192, 160, 246),
                   string=CREAM, style="pocket"),
    "pink": dict(label="STRAWBERRY HEART", main=(255, 156, 194), shade=(226, 116, 160), light=(255, 194, 218),
                 string=CREAM, style="heart"),
    "cream": dict(label="MILK ZIP-UP", main=(255, 244, 220), shade=(222, 206, 176), light=(255, 252, 238),
                  string=(210, 150, 120), style="zip"),
    "blue": dict(label="SKY STRIPE", main=(104, 158, 240), shade=(70, 116, 204), light=(150, 194, 255),
                 string=CREAM, style="stripe"),
}



def _fur_layers(s, hy):
    """Give the black fur light and dark steps so the face and body parts stay readable."""
    for x, y in ((3, 3), (4, 3), (4, 4), (1, 2), (7, 3), (8, 5), (9, 5), (10, 6)):   # forehead, ear edges, top of the back
        s.set_at((x, y), FUR_HI)
    for x, y in ((2, 8), (3, 8), (4, 8), (5, 8), (3, 7), (7, 8),                      # under the chin, cheek edge
                 (8, 12), (9, 12), (10, 12), (11, 12), (8, 13), (9, 13), (7, 12)):       # belly side
        if s.get_at((x, y))[:3] == LOOK.fur:
            s.set_at((x, y), FUR_LO)


def _hoodie(s, tail, h):
    """Dress the sitting body: one flat colour with a soft highlight and shade, a hood rim under the chin,
    ribbed cuffs and hem, and a style detail. Head, legs, paws and tail keep their fur."""
    main, shade, light = h["main"], h["shade"], h["light"]
    tail_px = set(_SIT_TAILS[tail])
    for y in range(5, 15):
        for x in range(4, 14):
            c = s.get_at((x, y))[:3]
            if (x, y) in tail_px or (x <= 7 and y <= 8):
                continue                                   # tail / head
            if c not in (LOOK.fur, LOOK.belly):
                continue
            if x in (4, 6) and y >= 11:                    # the two front legs: sleeves
                if y == 11:
                    s.set_at((x, y), main)
                elif y == 12:
                    s.set_at((x, y), shade)                # ribbed cuff
                continue
            if y == 13:
                col = shade                                # ribbed hem
            elif y <= 6:
                col = light                                # soft highlight on the back
            elif x >= 12:
                col = shade                                # shade on the far side
            else:
                col = main
            s.set_at((x, y), col)
    for x in range(1, 7):                                  # hood rim under the chin (where Mochi's bowtie sits)
        s.set_at((x, 9), light)
        s.set_at((x, 10), shade) if x in (1, 6) else None
    for x in (8, 9):                                       # the folded hood bulging behind the neck
        s.set_at((x, 7), shade)
        s.set_at((x, 8), shade)
    st = h["style"]
    if st in ("pocket", "stripe"):
        for x in (3, 4):
            s.set_at((x, 10), h["string"]); s.set_at((x, 11), h["string"]) if x == 3 else None   # drawstrings
    if st == "pocket":
        for x in range(7, 12):
            s.set_at((x, 11), light)
            s.set_at((x, 12), shade)
    elif st == "heart":
        for x in (3, 4):
            s.set_at((x, 10), h["string"])
        s.set_at((3, 11), h["string"])
        for p in ((8, 10), (10, 10), (8, 11), (9, 11), (10, 11), (9, 12)):
            s.set_at(p, CREAM)
    elif st == "zip":
        for y in range(10, 13):
            s.set_at((5, y), (150, 140, 160))
        s.set_at((5, 10), GOLD)                             # zip pull
        for x in range(8, 12):
            s.set_at((x, 12), shade)
    elif st == "stripe":
        for x in range(7, 14):
            if s.get_at((x, 10))[:3] == main or s.get_at((x, 10))[:3] == shade:
                s.set_at((x, 10), CREAM)
        for x in range(8, 12):
            s.set_at((x, 12), shade)



# ---------------------------------------------------------------- outfits (small, flat, 2-3 colours each)
CR = (255, 246, 226)                      # cream
OUTFITS = {
    "varsity": dict(label="LAVENDER VARSITY JACKET", main=(186, 162, 242), shade=(144, 118, 210), trim=CR, note="OVERSIZED, CREAM RIBS"),
    "neckerchief": dict(label="BUTTER NECKERCHIEF", main=(255, 230, 140), shade=(230, 190, 96), trim=(255, 252, 226), note="BLACK CAT STAYS BLACK"),
    "neckerchief_lav": dict(label="LAVENDER NECKERCHIEF", main=(196, 170, 246), shade=(150, 122, 214), trim=(240, 232, 255), note="ALT COLOUR"),
    "overalls": dict(label="SKY MINI OVERALLS", main=(150, 198, 255), shade=(108, 156, 226), trim=(255, 214, 90), note="STRAP + BIB + BUTTON"),
    "vest": dict(label="CREAM STAFF VEST", main=(255, 246, 226), shade=(222, 206, 176), trim=(120, 96, 190), note="LILAC PIPING + BADGE"),
}


def _body_pixels(s, tail, x0=7):
    """Body (not head, tail or the two front legs) pixel coordinates that are painted."""
    tail_px = set(_SIT_TAILS[tail])
    out = []
    for y in range(5, 14):
        for x in range(x0, 14):
            if (x, y) in tail_px or s.get_at((x, y))[3] == 0:
                continue
            out.append((x, y))
    return out


def _outfit(s, tail, key):
    o = OUTFITS[key]
    m, sh, tr = o["main"], o["shade"], o["trim"]
    P = lambda x, y, c: s.set_at((x, y), c)                       # noqa: E731
    if key == "varsity":
        for x, y in _body_pixels(s, tail, 4):
            if x <= 7 and y <= 8:
                continue
            if x in (4, 6) and y >= 11:
                continue
            P(x, y, sh if x >= 11 else m)
        for y in range(8, 13):                                    # oversized: the jacket hangs out past the back
            P(13, y, sh)
        for x in range(7, 13):
            P(x, 13, tr)                                          # ribbed hem
        P(13, 13, tr) if (13, 13) not in set(_SIT_TAILS[tail]) else None
        for x in (4, 6):                                          # sleeves with ribbed cuffs
            P(x, 11, m); P(x, 12, tr)
        for x in range(3, 8):                                     # ribbed collar
            P(x, 9, tr)
        for p in ((7, 8), (8, 8), (8, 7)):
            P(p[0], p[1], tr)
        for y in range(10, 13):                                   # front placket
            P(5, y, tr)
        P(9, 10, tr); P(10, 10, tr); P(9, 11, tr); P(10, 11, tr)   # letter patch
        P(9, 10, m); P(10, 11, m)
    elif key.startswith("neckerchief"):
        for x in range(2, 8):
            P(x, 9, m)
        for x in range(3, 7):
            P(x, 10, m)
        P(4, 11, m); P(5, 11, m)
        P(7, 9, sh); P(6, 10, sh); P(5, 11, sh)                   # shade edge
        P(2, 9, tr); P(4, 10, tr)                                 # knot highlight + one polka dot
        P(3, 9, sh) if False else None
    elif key == "overalls":
        for x, y in _body_pixels(s, tail, 7):
            if y >= 10:
                P(x, y, sh if x >= 11 else m)
        for p in ((4, 9), (5, 9), (6, 9), (4, 10), (5, 10), (6, 10), (5, 11), (5, 12)):
            P(p[0], p[1], m)                                       # bib
        P(5, 10, sh)
        for p in ((7, 9), (8, 8), (9, 7), (10, 6)):
            P(p[0], p[1], m)                                       # strap over the shoulder
        P(6, 9, tr); P(7, 9, m)                                    # button
        P(4, 9, sh) if False else None
    elif key == "vest":
        for x, y in _body_pixels(s, tail, 7):
            if y >= 6:
                P(x, y, sh if x >= 12 else m)
        for p in ((4, 9), (5, 9), (6, 9), (4, 10), (5, 10), (6, 10), (5, 11)):
            P(p[0], p[1], m)                                       # closed front
        for y in range(9, 12):
            P(5, y, sh)
        for x in range(7, 13):
            if s.get_at((x, 13))[3] and (x, 13) not in set(_SIT_TAILS[tail]):
                P(x, 13, tr)                                       # piped hem
        for y in range(6, 9):
            P(8, y, tr)                                            # piped armhole / shoulder
        P(8, 10, (255, 214, 90)); P(9, 10, (255, 214, 90))         # STAFF name badge
        P(7, 8, tr)


# Eye colour studies. Mochi's eye is three blocks: iris (gold), pupil (dark) and a 1px shine (white).
# Only iris and shine change between studies; the pupil, the face and every other colour stay as they are.
EYE_STYLES = {
    "original": dict(label="ORIGINAL", iris=_mochi.IRIS, shine=_mochi.SHINE, pupil=_mochi.PUPIL,
                     note="WHITE SHINE + GOLD IRIS"),
    "warm": dict(label="WARM CREAM", iris=_mochi.IRIS, shine=(255, 247, 208), pupil=_mochi.PUPIL,
                 note="CREAM-YELLOW SHINE + GOLD IRIS"),
    "light_gold": dict(label="LIGHT GOLD + AMBER", iris=(228, 156, 44), shine=(255, 226, 140), pupil=_mochi.PUPIL,
                       note="LIGHT GOLD SHINE + AMBER IRIS"),
}



# ---------------------------------------------------------------- the coin-bell lamp (chest, 2x2 pixels)
# Off: a dull bronze coin. On: the same coin lights up warm, with a faint wash on the pixels right around it.
LAMP_OFF = dict(hl=(128, 112, 100), main=(98, 86, 82), edge=(66, 58, 62), glow=None, label="OFF")
LAMPS = {
    "cream": dict(hl=(255, 252, 232), main=(255, 238, 186), edge=(224, 190, 120), glow=(255, 236, 180), label="WARM CREAM"),
    "gold": dict(hl=(255, 240, 168), main=(255, 212, 98), edge=(214, 156, 56), glow=(255, 210, 100), label="SOFT GOLD"),
    "apricot": dict(hl=(255, 232, 200), main=(255, 198, 150), edge=(222, 148, 104), glow=(255, 190, 140), label="APRICOT"),
}
COIN_AT = (4, 10)                          # top-left pixel of the 2x2 coin: hangs at the front of the chest


def _blend(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _lamp(s, state, plain):
    """state: None (no lamp), 'off' or a key of LAMPS."""
    if state is None:
        return
    cfg = LAMP_OFF if state == "off" else LAMPS[state]
    x, y = COIN_AT
    if plain:                                              # a thin collar string so the bare chest has something to hang from
        for cx in (4, 5, 6):
            s.set_at((cx, 9), (122, 100, 74))
    if cfg["glow"]:
        for gx in range(x - 1, x + 3):
            for gy in range(y - 1, y + 3):
                if x <= gx < x + 2 and y <= gy < y + 2:
                    continue
                if s.get_at((gx, gy))[3] == 0:
                    continue
                corner = gx in (x - 1, x + 2) and gy in (y - 1, y + 2)
                c = s.get_at((gx, gy))
                s.set_at((gx, gy), (*_blend(c[:3], cfg["glow"], 0.12 if corner else 0.26), 255))
    s.set_at((x, y), cfg["hl"])
    s.set_at((x + 1, y), cfg["main"])
    s.set_at((x, y + 1), cfg["main"])
    s.set_at((x + 1, y + 1), cfg["edge"])



# ---------------------------------------------------------------- tiny hats (head only: rows 0-3, eyes start at row 4)
HATS = {
    "beret": dict(label="LAVENDER BERET", main=(190, 166, 240), shade=(150, 124, 210), light=(226, 212, 255),
                  note="TILTED A LITTLE"),
    "cap": dict(label="SKY BASEBALL CAP", main=(150, 198, 255), shade=(104, 152, 224), light=(232, 244, 255),
                note="BRIM POINTS FORWARD"),
    "newsboy": dict(label="BUTTER NEWSBOY CAP", main=(255, 230, 140), shade=(224, 186, 92), light=(255, 248, 206),
                    note="RETRO, SOFT AND ROUND"),
}


def _hat(s, key):
    """Hats sit between the ear tips: the two outer ear columns (x1, x7) always stay, and nothing touches rows 4+ (eyes)."""
    h = HATS[key]
    m, sh, li = h["main"], h["shade"], h["light"]
    P = lambda x, y, c: s.set_at((x, y), c)                       # noqa: E731
    if key == "beret":                                            # a flat puffy beret, tipped to the right
        P(5, 0, sh)                                               # little stalk
        for x in (3, 4, 5, 6):
            P(x, 1, m)
        for x in range(2, 7):
            P(x, 2, m)
        P(2, 3, sh); P(3, 3, sh)                                  # the low side of the tilt
        P(6, 1, sh); P(6, 2, sh); P(3, 1, li); P(4, 1, li); P(3, 2, li)
    elif key == "cap":                                            # dome, band, button and a short pale brim at the front
        P(4, 0, li)                                               # button
        for x in (3, 4, 5):
            P(x, 1, m)
        for x in range(2, 7):
            P(x, 2, m)
        P(5, 1, sh); P(6, 2, sh); P(4, 1, li)
        P(1, 3, li); P(2, 3, li); P(3, 3, li)                     # the brim sticks out to the left
        P(4, 3, sh); P(5, 3, sh)
    elif key == "newsboy":                                        # soft round crown, button on top, short peak
        P(4, 0, sh)                                               # button
        for x in (3, 4, 5, 6):
            P(x, 1, m)
        for x in range(2, 7):
            P(x, 2, m)
        for x in (3, 4, 5):
            P(x, 3, sh)
        P(2, 3, sh); P(1, 3, sh)                                  # short peak
        P(3, 1, li); P(4, 1, li); P(6, 2, sh)



# ---------------------------------------------------------------- tiny crown (between the ear tips, rows 0-3)
CROWN = dict(gold=(255, 214, 90), light=(255, 240, 168), shade=(214, 156, 56), gem=(190, 130, 255), gem_hl=(232, 206, 255))


def _crown(s, variant, gem):
    """variant: 'a' (3 rounded points, 3px wide), 'b' (2 points + valley), 'c' (5px wide)."""
    g, li, sh = CROWN["gold"], CROWN["light"], CROWN["shade"]
    P = lambda x, y, c: s.set_at((x, y), c)                       # noqa: E731
    if variant == "a":
        P(4, 0, li)                                               # centre point
        P(3, 1, g); P(4, 1, g); P(5, 1, g)
        P(3, 2, g); P(4, 2, g); P(5, 2, g)
        for x in (3, 4, 5):
            P(x, 3, sh)                                           # band
        P(3, 1, li)
    elif variant == "b":
        P(3, 1, li); P(5, 1, g)                                   # two points with a valley between
        P(3, 2, g); P(4, 2, g); P(5, 2, g)
        for x in (3, 4, 5):
            P(x, 3, sh)
    else:
        P(2, 1, li); P(4, 0, li); P(6, 1, g)                      # three points
        for x in range(2, 7):
            P(x, 2, g)
        P(4, 1, g)
        for x in range(2, 7):
            P(x, 3, sh)
    if gem:
        P(4, 2, CROWN["gem"])
        P(4, 3, CROWN["gem"]) if variant == "c" else None
    else:
        P(4, 2, li)


def miao_meow_frame(pose="sit", mood="open", tail=0, gaze=(0, 1), hoodie="purple", eyes="original", lamp=None, hat=None, crown=None):
    """One left-facing, outlined 20x17 frame, exactly Mochi's size. mood: open, happy, sleepy, surprised.
    hoodie: a key of HOODIES, or None for the plain black cat."""
    base = "happy" if mood == "happy" else "closed"
    s = draw_cat(LOOK, pose, tail, base)
    hy = 2
    if mood in ("open", "sleepy", "surprised"):
        es = EYE_STYLES[eyes]
        saved = (_mochi.IRIS, _mochi.SHINE, _mochi.PUPIL)
        _mochi.IRIS, _mochi.SHINE, _mochi.PUPIL = es["iris"], es["shine"], es["pupil"]
        try:
            _mochi._eyes(s, hy, "sleepy" if mood == "sleepy" else "open", gaze)
        finally:
            _mochi.IRIS, _mochi.SHINE, _mochi.PUPIL = saved            # Mochi's own constants are always restored
    _mochi._px(s, SOFT_GREY, 2, hy, 1, 1)                      # inner ear, as on Mochi (grey instead of pink)
    _fur_layers(s, hy)
    if mood == "surprised":
        _mochi._px(s, (22, 14, 40), 1, hy + 5, 1, 1)           # a little round 'o'
    if hoodie in HOODIES:
        _hoodie(s, tail, HOODIES[hoodie])
    elif hoodie in OUTFITS:
        _outfit(s, tail, hoodie)
    _lamp(s, lamp, plain=hoodie is None)
    if hat:
        _hat(s, hat)
    if crown:
        _crown(s, *crown)
    return outlined(s)


def miao_meow_sprite(frame=0, mood="open", hoodie="purple", eyes="original", lamp=None, hat=None, crown=None):
    """Idle frame 0/1 (tail swish). 20x17, the same grid as Mochi and every other cat in the game."""
    return miao_meow_frame("sit", mood, tail=(0, 1, 2, 1)[frame % 4], hoodie=hoodie, eyes=eyes, lamp=lamp, hat=hat, crown=crown)


def miao_meow_sprite32(frame=0, mood="open"):
    """The same sprite centred, unscaled, in a 32x32 cell (for engines that want a fixed cell)."""
    cell = pygame.Surface((32, 32), pygame.SRCALPHA)
    spr = miao_meow_sprite(frame, mood)
    cell.blit(spr, spr.get_rect(midbottom=(16, 30)))
    return cell


def soft_shadow_img(w, h):
    from gfx import soft_shadow
    return soft_shadow(w, h, 110)


def portrait_framed(mood, hoodie="purple"):
    """Dialogue portrait, 44x44: a 3x crop of the head, like Mochi's shop portrait is her sprite enlarged."""
    inner = pygame.Surface((40, 40))
    for y in range(40):
        t = y / 39
        inner.fill((int(40 + 24 * t), int(24 + 10 * t), int(84 + 40 * t)), (0, y, 40, 1))
    for i in range(0, 40, 4):
        inner.set_at((i, 1), (255, 214, 90) if (i // 4) % 2 else (80, 240, 255))
    for x, y in ((3, 9), (35, 12), (5, 20), (36, 24)):
        inner.set_at((x, y), (255, 255, 255))
    spr = miao_meow_sprite(0, mood, hoodie)          # the whole sprite at 2x, like Mochi's shop portrait
    big = pygame.transform.scale(spr, (spr.get_width() * 2, spr.get_height() * 2))
    inner.blit(soft_shadow_img(30, 5), (5, 34))
    inner.blit(big, big.get_rect(midbottom=(20, 38)))
    frame = pygame.Surface((44, 44), pygame.SRCALPHA)
    frame.blit(inner, (2, 2))
    pygame.draw.rect(frame, Col.CYAN, (1, 1, 42, 42), 1)
    pygame.draw.rect(frame, (*Col.MAGENTA, 255), (0, 0, 44, 44), 1)
    for cx, cy in ((1, 1), (41, 1), (1, 42), (41, 42)):
        frame.fill(Col.YELLOW, (cx, cy, 2, 1))
    return frame


def miao_meow_portrait(mood="happy", hoodie="purple"):
    """Unframed 40x40 portrait (the framed one without its border)."""
    return portrait_framed(mood, hoodie).subsurface(pygame.Rect(2, 2, 40, 40)).copy()


# ---------------------------------------------------------------- icons
def icon_secret_item(index, found):
    """14x14 secret-item slot. Three different crystals so the slots read apart even when dark."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    colors = (Col.CYAN, Col.MAGENTA, Col.YELLOW)
    c = colors[index % 3]
    pygame.draw.rect(s, (8, 6, 20, 255), (0, 0, 16, 16), border_radius=2)
    pygame.draw.rect(s, c if found else (70, 60, 110), (0, 0, 16, 16), 1, border_radius=2)
    if found:
        light = tuple(min(255, v + 90) for v in c)
        dark = tuple(int(v * 0.55) for v in c)
        pts = [(8, 2), (13, 7), (8, 13), (3, 7)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dark, [(8, 7), (13, 7), (8, 13)])
        pygame.draw.polygon(s, light, [(8, 2), (8, 7), (3, 7)])
        s.set_at((6, 5), (255, 255, 255))
    else:
        for (x, y) in ((7, 4), (8, 4), (9, 5), (9, 6), (8, 7), (8, 8), (8, 10)):
            s.set_at((x, y), (86, 76, 130))
    return s


def icon_trial(index, state):
    """16x16 secret-trial door: 'locked', 'open' or 'done'."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.rect(s, (8, 6, 20, 255), (0, 0, 16, 16), border_radius=2)
    border = {"locked": (70, 60, 110), "open": Col.PURPLE, "done": Col.GREEN}[state]
    pygame.draw.rect(s, border, (0, 0, 16, 16), 1, border_radius=2)
    door = pygame.Rect(4, 3, 8, 11)
    pygame.draw.rect(s, (36, 26, 66), door)
    pygame.draw.rect(s, border, door, 1)
    if state == "locked":
        pygame.draw.rect(s, (130, 120, 180), (6, 8, 4, 4))
        pygame.draw.rect(s, (130, 120, 180), (7, 6, 2, 3), 1)
    elif state == "open":
        pygame.draw.rect(s, (255, 214, 90), (5, 4, 6, 9))
    else:
        for x, y in ((5, 8), (6, 9), (7, 10), (8, 9), (9, 8), (10, 7), (11, 6)):
            s.set_at((x, y), Col.GREEN)
    return s


def icon_token():
    s = pygame.Surface((7, 7), pygame.SRCALPHA)
    pygame.draw.circle(s, (123, 87, 24), (3, 3), 3)
    pygame.draw.circle(s, Col.YELLOW, (3, 3), 2)
    s.fill((255, 245, 200), (2, 1, 1, 2))
    return s


def icon_ticket():
    s = pygame.Surface((9, 7), pygame.SRCALPHA)
    s.fill(Col.MAGENTA, (0, 1, 9, 5))
    s.fill((255, 170, 230), (1, 2, 7, 3))
    for x in (0, 8):
        s.fill((0, 0, 0, 0), (x, 3, 1, 1))
    s.fill(Col.MAGENTA, (3, 2, 1, 3))
    return s


if __name__ == "__main__":
    print(miao_meow_core(0).ascii())
