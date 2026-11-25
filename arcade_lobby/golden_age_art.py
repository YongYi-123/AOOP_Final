"""Pixel art for TRIAL 01 - THE GOLDEN AGE: a cosy wooden bedroom that is also somebody's game studio.

Everything is drawn from code onto small surfaces (once, then cached), in the hub's own pixel density (the same 400x300
canvas, the same 1px outlines), but in warm wood, wallpaper and lamplight instead of the neon arcade's navy and purple.

Each sprite function returns an OUTLINED surface, so it is blitted at (x - 1, y - 1) of the spot it was designed for
(`put()` does that). The Miao Meow Plushie is built on purpose as a stuffed toy (round, stitched, button-nosed) and
shares no pixels with the NPC's sprite.
"""
import math
import random

import pygame

from gfx import outlined

VIEW = (400, 300)
LINE = (46, 28, 20)                       # the warm dark brown every outline uses

# wood and wallpaper
WOOD_DK, WOOD_MD, WOOD, WOOD_LT, WOOD_HI = (78, 48, 30), (110, 70, 42), (140, 92, 54), (172, 120, 70), (204, 154, 96)
PAPER, PAPER_ST, PAPER_MOTIF = (226, 188, 132), (216, 174, 118), (196, 148, 98)
CREAM, CREAM_DK = (244, 228, 192), (214, 192, 150)
BRASS, BRASS_LT = (214, 164, 62), (250, 218, 120)
RED, RED_DK = (184, 70, 56), (132, 46, 40)
TEAL, TEAL_DK = (62, 140, 138), (40, 98, 100)
PLUM, MUSTARD, SAGE = (120, 76, 110), (222, 170, 60), (126, 150, 98)

# layout (canvas pixels). The back wall ends at WALL_BOTTOM; feet may not go above WALL_SOLID_BOTTOM.
WALL_BOTTOM = 74
FLOOR_BOTTOM = 282
SIDE = 20
WALL_SOLID_BOTTOM = 86

_cache = {}


def cached(fn):
    def inner(*a):
        key = (fn.__name__, a)
        if key not in _cache:
            _cache[key] = fn(*a)
        return _cache[key]
    inner.__name__ = fn.__name__
    inner.__doc__ = fn.__doc__
    return inner


def R(s, color, x, y, w=1, h=1):
    s.fill(color, (x, y, w, h))


def mul(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sprite(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def finish(s, color=LINE):
    return outlined(s, color)


def put(surf, image, x, y):
    """Blit a sprite designed for (x, y): the outline hangs 1px outside."""
    surf.blit(image, (x - 1, y - 1))


# ------------------------------------------------------------------ the room itself
@cached
def room_shell():
    """Walls, wainscot, floorboards and the side walls: the empty room (400x300, opaque)."""
    w, h = VIEW
    s = pygame.Surface(VIEW)
    rng = random.Random(1989)
    # wallpaper: soft vertical stripes with a tiny diamond motif
    for x in range(0, w, 8):
        R(s, PAPER if (x // 8) % 2 == 0 else PAPER_ST, x, 0, 8, WALL_BOTTOM)
    for x in range(4, w, 16):
        for y in (14, 30, 46):
            for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
                R(s, PAPER_MOTIF, x + dx, y + dy)
    # wainscot (the wooden panelling under the wallpaper) and baseboard
    R(s, WOOD_MD, 0, 54, w, 20)
    for x in range(0, w, 20):
        R(s, WOOD, x + 1, 58, 18, 12)
        R(s, WOOD_LT, x + 1, 58, 18, 1)
        R(s, WOOD_DK, x + 1, 69, 18, 1)
    R(s, WOOD_HI, 0, 54, w, 2)
    R(s, WOOD_DK, 0, 56, w, 1)
    R(s, WOOD_DK, 0, 72, w, 2)
    # ceiling moulding
    R(s, WOOD_DK, 0, 0, w, 5)
    R(s, WOOD, 0, 5, w, 2)
    R(s, mul(PAPER, 0.7), 0, 7, w, 3)                      # the wall darkens a little under the moulding
    # floor: long boards laid in rows, seams staggered, a little grain
    tones = [(150, 100, 58), (158, 108, 64), (144, 94, 54), (164, 114, 68)]
    y, row = WALL_BOTTOM, 0
    while y < FLOOR_BOTTOM:
        bh = 13
        x = -rng.randrange(0, 60)
        while x < w:
            bw = rng.randrange(60, 110)
            base = tones[rng.randrange(len(tones))]
            R(s, base, max(0, x), y, min(bw, w - max(0, x)), bh)
            R(s, mul(base, 0.78), max(0, x), y + bh - 1, min(bw, w - max(0, x)), 1)
            R(s, mul(base, 0.72), max(0, x), y, 1, bh)
            for _ in range(3):
                gx, gy = x + rng.randrange(2, bw - 8), y + rng.randrange(2, bh - 2)
                R(s, mul(base, 1.1), gx, gy, rng.randrange(4, 14), 1)
            x += bw
        y += bh
        row += 1
    # the wall casts a soft shadow onto the floor
    shade_h = 10
    for i in range(shade_h):
        band = sprite(w, 1)
        band.fill((20, 8, 0, int(70 * (1 - i / shade_h) ** 2)))
        s.blit(band, (0, WALL_BOTTOM + i))
    # side walls and the bottom wall: dark wooden panelling
    for x0 in (0, w - SIDE):
        R(s, WOOD_DK, x0, 0, SIDE, FLOOR_BOTTOM + 18)
        for yy in range(8, FLOOR_BOTTOM + 18, 22):
            R(s, WOOD_MD, x0 + 3, yy, SIDE - 6, 18)
            R(s, WOOD, x0 + 3, yy, SIDE - 6, 1)
        R(s, WOOD_HI if x0 == 0 else WOOD, x0 + (SIDE - 2 if x0 == 0 else 0), 0, 2, FLOOR_BOTTOM + 18)
    R(s, WOOD_DK, 0, FLOOR_BOTTOM, w, h - FLOOR_BOTTOM)
    R(s, WOOD_MD, SIDE, FLOOR_BOTTOM, w - 2 * SIDE, 6)
    R(s, WOOD_HI, SIDE, FLOOR_BOTTOM, w - 2 * SIDE, 1)
    R(s, WOOD_DK, SIDE, FLOOR_BOTTOM + 6, w - 2 * SIDE, 1)
    return s


@cached
def rug(w=124, h=64):
    s = sprite(w, h)
    pygame.draw.rect(s, RED_DK, (0, 0, w, h), border_radius=10)
    pygame.draw.rect(s, RED, (3, 3, w - 6, h - 6), border_radius=8)
    pygame.draw.rect(s, CREAM, (7, 7, w - 14, h - 14), 1, border_radius=6)
    pygame.draw.rect(s, MUSTARD, (11, 11, w - 22, h - 22), 1, border_radius=4)
    for i in range(7):                                    # a row of diamonds down the middle
        cx = 20 + i * ((w - 40) // 6)
        cy = h // 2
        pygame.draw.polygon(s, MUSTARD if i % 2 == 0 else TEAL, [(cx, cy - 7), (cx + 6, cy), (cx, cy + 7), (cx - 6, cy)])
        pygame.draw.polygon(s, CREAM, [(cx, cy - 3), (cx + 3, cy), (cx, cy + 3), (cx - 3, cy)])
    for x in range(2, w - 2, 4):                          # tassels
        R(s, CREAM_DK, x, 0, 1, 1)
        R(s, CREAM_DK, x, h - 1, 1, 1)
    return s


# ------------------------------------------------------------------ wall dressing
@cached
def window():
    """A night window with the curtains drawn back; 54x40."""
    s = sprite(54, 40)
    R(s, WOOD_DK, 0, 0, 54, 40)
    sky = sprite(46, 32)
    for y in range(32):
        R(sky, mix((20, 28, 70), (60, 66, 120), y / 31), 0, y, 46, 1)
    rng = random.Random(7)
    for _ in range(14):
        R(sky, (210, 214, 240), rng.randrange(1, 45), rng.randrange(1, 18))
    pygame.draw.circle(sky, (238, 236, 206), (33, 9), 5)
    pygame.draw.circle(sky, (20, 28, 70), (35, 8), 4)           # a crescent
    R(sky, (14, 18, 46), 0, 26, 46, 6)                          # roofs far away
    for x, hh in ((2, 4), (10, 6), (20, 3), (30, 5), (38, 4)):
        R(sky, (14, 18, 46), x, 26 - hh, 7, hh)
        R(sky, (240, 200, 110), x + 2, 26 - hh + 1)
    s.blit(sky, (4, 4))
    R(s, WOOD_HI, 26, 4, 2, 32)                                  # sash bars
    R(s, WOOD_HI, 4, 19, 46, 2)
    R(s, WOOD_LT, 0, 0, 54, 1)
    R(s, WOOD_DK, 0, 38, 54, 2)
    for x, flip in ((0, 1), (46, -1)):                           # curtains
        for i in range(8):
            c = RED if i % 2 == 0 else RED_DK
            R(s, c, x + i * flip if flip == 1 else x + 7 - i, 0, 1, 40)
    R(s, BRASS, 0, 0, 54, 2)
    return finish(s)


@cached
def poster(kind):
    """22x30 posters in thin frames."""
    s = sprite(22, 30)
    R(s, CREAM, 0, 0, 22, 30)
    if kind == "quest":                                     # a hero with a sword under a big sun
        R(s, (46, 84, 140), 1, 1, 20, 28)
        pygame.draw.circle(s, MUSTARD, (11, 12), 7)
        R(s, (30, 56, 100), 1, 20, 20, 9)
        R(s, (40, 130, 70), 1, 22, 20, 7)
        R(s, (30, 30, 50), 9, 14, 4, 7)                        # hero
        R(s, (230, 190, 150), 9, 12, 4, 3)
        R(s, (200, 200, 220), 14, 11, 1, 8)
        R(s, CREAM, 3, 3, 16, 2)
    elif kind == "pilot":                                   # a little spaceship over stars
        R(s, (24, 20, 56), 1, 1, 20, 28)
        for x, y in ((4, 4), (16, 6), (8, 10), (18, 14), (3, 18), (14, 22)):
            R(s, CREAM, x, y)
        pygame.draw.polygon(s, (230, 90, 80), [(11, 8), (15, 20), (11, 17), (7, 20)])
        R(s, CREAM, 10, 12, 2, 3)
        R(s, MUSTARD, 10, 20, 2, 3)
        R(s, TEAL, 3, 25, 16, 2)
    else:                                                    # "arcade": a joystick and big letters
        R(s, (110, 40, 90), 1, 1, 20, 28)
        R(s, MUSTARD, 3, 4, 16, 3)
        R(s, MUSTARD, 3, 9, 10, 2)
        R(s, (240, 90, 70), 10, 17, 2, 6)
        pygame.draw.circle(s, (240, 90, 70), (11, 15), 3)
        R(s, CREAM, 5, 23, 12, 3)
    out = sprite(22, 30)                                     # the thin wooden frame goes round the picture
    R(out, WOOD_MD, 0, 0, 22, 30)
    out.blit(s, (1, 1), (1, 1, 20, 28))
    R(out, WOOD_HI, 0, 0, 22, 1)
    return finish(out)


@cached
def corkboard():
    """Pinned photos and design sketches; 44x34."""
    s = sprite(44, 34)
    R(s, WOOD_MD, 0, 0, 44, 34)
    R(s, (186, 134, 86), 2, 2, 40, 30)
    rng = random.Random(3)
    for _ in range(40):
        R(s, (164, 116, 74), rng.randrange(2, 42), rng.randrange(2, 32))
    # a sketch on squared paper (a little sprite drawn on a grid)
    R(s, (240, 240, 228), 4, 4, 15, 13)
    for i in range(0, 15, 3):
        R(s, (190, 210, 230), 4 + i, 4, 1, 13)
        R(s, (190, 210, 230), 4, 4 + i, 15, 1)
    for x, y in ((9, 7), (10, 7), (8, 8), (9, 8), (10, 8), (11, 8), (8, 9), (11, 9), (9, 10), (10, 10)):
        R(s, (60, 50, 70), x, y)
    R(s, RED, 11, 4, 2, 2)                                   # pin
    # polaroids
    for (x, y, c) in ((22, 5, (130, 170, 200)), (31, 12, (210, 160, 110))):
        R(s, CREAM, x, y, 10, 12)
        R(s, c, x + 1, y + 1, 8, 8)
        R(s, mul(c, 0.7), x + 2, y + 5, 3, 4)
        R(s, TEAL, x + 4, y - 1, 2, 2)
    R(s, (250, 240, 150), 6, 20, 12, 9)                     # a yellow sticky note with scribbles
    for i in range(3):
        R(s, (150, 130, 60), 8, 22 + i * 2, 8 - i * 2, 1)
    R(s, (220, 120, 140), 22, 22, 10, 8)                    # pink note
    R(s, (150, 70, 90), 24, 24, 6, 1)
    R(s, (150, 70, 90), 24, 26, 4, 1)
    return finish(s)


@cached
def wall_clock():
    s = sprite(13, 13)
    pygame.draw.circle(s, WOOD_DK, (6, 6), 6)
    pygame.draw.circle(s, CREAM, (6, 6), 5)
    R(s, LINE, 6, 3, 1, 4)
    R(s, LINE, 6, 6, 3, 1)
    for x, y in ((6, 1), (11, 6), (6, 11), (1, 6)):
        R(s, WOOD_MD, x, y)
    return finish(s)


@cached
def photo_frame():
    s = sprite(13, 11)
    R(s, WOOD_MD, 0, 0, 13, 11)
    R(s, (150, 190, 220), 2, 2, 9, 7)
    R(s, (90, 140, 90), 2, 6, 9, 3)
    R(s, (240, 220, 160), 8, 3, 2, 2)
    R(s, WOOD_HI, 0, 0, 13, 1)
    return finish(s)


@cached
def trophy_shelf():
    """A little wall shelf with two trophies and a pixel-art robot toy; 40x16."""
    s = sprite(40, 16)
    R(s, WOOD_LT, 0, 12, 40, 3)
    R(s, WOOD_DK, 0, 15, 40, 1)
    R(s, WOOD_MD, 3, 12, 2, 4)
    R(s, WOOD_MD, 35, 12, 2, 4)
    for x in (5, 14):                                        # trophies
        R(s, BRASS, x + 2, 2, 5, 4)
        R(s, BRASS_LT, x + 2, 2, 1, 4)
        R(s, BRASS, x + 4, 6, 1, 3)
        R(s, mul(BRASS, 0.8), x + 1, 9, 7, 3)
        R(s, BRASS, x, 3, 1, 2)
        R(s, BRASS, x + 8, 3, 1, 2)
    R(s, (150, 160, 170), 28, 4, 8, 8)                       # robot
    R(s, (90, 100, 110), 30, 6, 1, 2)
    R(s, (90, 100, 110), 33, 6, 1, 2)
    R(s, RED, 31, 9, 3, 1)
    R(s, (150, 160, 170), 31, 1, 2, 3)
    R(s, RED, 31, 0)
    return finish(s)


LIGHT_XS = (50, 98, 160, 232, 284, 352)         # clear of the clock, the window and the corkboard


def string_light_positions():
    """(x, y) of each bulb in the string of lights along the top of the back wall, in canvas pixels."""
    return [(x, 11) for x in LIGHT_XS]


def draw_string_lights(surf):
    """The wire and the little drops the bulbs hang from (the bulbs themselves are drawn by the scene, lit or not)."""
    R(surf, LINE, 22, 8, 356, 1)
    for x in range(22, 378, 60):
        R(surf, (96, 60, 36), x, 6, 2, 3)               # the clips
    for x, y in string_light_positions():
        R(surf, LINE, x, 9, 1, y - 9)


@cached
def bulb(lit):
    s = sprite(5, 6)
    R(s, LINE, 2, 0, 1, 1)
    col = (255, 226, 140) if lit else (150, 120, 70)
    R(s, col, 1, 1, 3, 3)
    R(s, col, 2, 4, 1, 1)
    if lit:
        R(s, (255, 250, 210), 2, 2)
    return s


# ------------------------------------------------------------------ furniture
@cached
def bed():
    """A wooden bed with a patchwork quilt, head to the wall; 64x62."""
    s = sprite(64, 62)
    R(s, WOOD_DK, 0, 0, 64, 12)                              # headboard
    R(s, WOOD_MD, 2, 2, 60, 9)
    R(s, WOOD_LT, 2, 2, 60, 1)
    for x in (4, 20, 36, 52):
        R(s, WOOD, x, 4, 8, 6)
        R(s, WOOD_HI, x, 4, 8, 1)
    R(s, WOOD_DK, 0, 10, 64, 2)
    R(s, CREAM_DK, 1, 12, 62, 46)                            # mattress & sheet
    R(s, CREAM, 2, 12, 60, 8)
    for x0 in (6, 36):                                       # two pillows
        pygame.draw.rect(s, CREAM, (x0, 12, 22, 12), border_radius=4)
        pygame.draw.rect(s, (255, 248, 226), (x0 + 2, 13, 18, 4), border_radius=2)
        R(s, CREAM_DK, x0 + 3, 21, 16, 1)
    quilt = (TEAL, MUSTARD, RED, SAGE, PLUM)
    for r in range(5):                                       # the patchwork quilt
        for c in range(7):
            col = quilt[(r * 2 + c) % len(quilt)]
            R(s, col, 3 + c * 8, 26 + r * 6, 8, 6)
            R(s, mul(col, 1.18), 3 + c * 8, 26 + r * 6, 8, 1)
            R(s, mul(col, 0.8), 3 + c * 8, 31 + r * 6, 8, 1)
            R(s, mul(col, 0.82), 3 + c * 8, 26 + r * 6, 1, 6)
    R(s, CREAM, 2, 24, 60, 3)                                # the folded-over sheet
    R(s, CREAM_DK, 2, 26, 60, 1)
    R(s, WOOD_DK, 0, 54, 64, 8)                              # footboard
    R(s, WOOD_MD, 2, 55, 60, 5)
    R(s, WOOD_HI, 2, 55, 60, 1)
    for x in (0, 60):
        R(s, WOOD_DK, x, 12, 4, 50)
        R(s, WOOD_LT, x + 1, 12, 1, 50)
    return finish(s)


@cached
def plushie():
    """The Miao Meow Plushie: a stuffed black cat with a gold felt crown, big gold button eyes and a coin-bell. Round and
    soft on purpose (stitched seams, a lighter belly patch, stubby paws): not the NPC's sprite scaled up. 19x19."""
    s = sprite(19, 19)
    FUR, FUR_HI, FUR_LO = (66, 66, 80), (96, 96, 114), (44, 44, 56)
    BELLY, SEAM, INNER = (118, 118, 134), (132, 130, 146), (148, 112, 124)
    GOLD, GOLD_HI, GOLD_LO = (236, 182, 64), (255, 232, 140), (172, 116, 40)
    # body, a plump pear
    pygame.draw.ellipse(s, FUR, (3, 10, 13, 9))
    pygame.draw.ellipse(s, BELLY, (6, 12, 7, 6))
    pygame.draw.ellipse(s, FUR, (1, 15, 5, 4))                 # paws
    pygame.draw.ellipse(s, FUR, (13, 15, 5, 4))
    R(s, FUR_LO, 3, 17, 2, 1)
    R(s, FUR_LO, 14, 17, 2, 1)
    # tail curling up behind
    R(s, FUR, 16, 11, 2, 5)
    R(s, FUR, 17, 9, 2, 3)
    R(s, FUR_HI, 18, 9, 1, 2)
    # head, wide and round
    pygame.draw.ellipse(s, FUR, (1, 3, 17, 12))
    pygame.draw.ellipse(s, FUR_HI, (3, 4, 9, 4))               # soft highlight on the forehead
    # ears
    pygame.draw.polygon(s, FUR, [(1, 7), (2, 1), (7, 4)])
    pygame.draw.polygon(s, FUR, [(17, 7), (16, 1), (11, 4)])
    pygame.draw.polygon(s, INNER, [(3, 5), (3, 3), (5, 4)])
    pygame.draw.polygon(s, INNER, [(15, 5), (15, 3), (13, 4)])
    # the little crown, felt gold with three points
    R(s, GOLD, 6, 2, 7, 3)
    for x in (6, 9, 12):
        R(s, GOLD, x, 0, 1, 3)
    R(s, GOLD_HI, 9, 0)
    R(s, GOLD_HI, 6, 2)
    R(s, GOLD_LO, 6, 4, 7, 1)
    R(s, (210, 80, 70), 9, 3)                                  # one red stitched jewel
    # warm gold eyes: big and round, with a dark slit and a shine
    for ex in (4, 11):
        R(s, GOLD, ex, 8, 4, 4)
        R(s, GOLD_HI, ex, 8, 4, 1)
        R(s, GOLD_LO, ex, 11, 4, 1)
        R(s, (30, 26, 36), ex + 2, 8, 1, 4)
        R(s, (255, 255, 235), ex + 1, 9)
    R(s, INNER, 9, 12, 1, 1)                                   # button nose
    R(s, (30, 26, 36), 8, 13)
    R(s, (30, 26, 36), 10, 13)
    # stitched seam down the front and a cross-stitch on the cheek
    for y in (14, 16):
        R(s, SEAM, 9, y)
    R(s, SEAM, 3, 12)
    R(s, SEAM, 4, 13)
    R(s, SEAM, 3, 14)
    # a collar and the simplified coin-bell
    R(s, RED, 6, 14, 7, 1)
    pygame.draw.circle(s, GOLD, (9, 16), 2)
    R(s, GOLD_HI, 8, 15)
    R(s, GOLD_LO, 9, 17)
    return finish(s)


@cached
def small_lamp(on):
    """A little table lamp with a cream shade (bedside / desk); 14x20."""
    s = sprite(14, 20)
    shade_c = (255, 238, 180) if on else (204, 184, 140)
    pygame.draw.polygon(s, shade_c, [(3, 1), (10, 1), (13, 10), (0, 10)])
    R(s, mul(shade_c, 0.84), 8, 2, 4, 8)
    R(s, mul(shade_c, 1.06) if on else CREAM, 3, 1, 6, 1)
    R(s, BRASS, 6, 10, 2, 6)
    R(s, WOOD_DK, 3, 16, 8, 3)
    R(s, WOOD_MD, 4, 16, 6, 1)
    if on:
        R(s, (255, 252, 220), 5, 4, 4, 3)
    return finish(s)


@cached
def bookshelf():
    """A tall wooden bookshelf full of books, a globe and a toy robot; 46x66."""
    s = sprite(46, 66)
    R(s, WOOD_DK, 0, 0, 46, 66)
    R(s, WOOD_MD, 2, 2, 42, 62)
    rng = random.Random(21)
    colors = [RED, TEAL, MUSTARD, PLUM, SAGE, (70, 90, 150), (200, 120, 60), (96, 60, 40), CREAM_DK]
    for row in range(4):
        y0 = 4 + row * 15
        R(s, (50, 30, 22), 3, y0, 40, 11)                     # the dark inside of the shelf
        x = 4
        while x < 41:
            bw = rng.randrange(2, 5)
            bh = rng.randrange(7, 11)
            if row == 1 and 22 <= x <= 30:                     # a gap with a globe on the shelf
                break
            c = colors[rng.randrange(len(colors))]
            if x + bw > 41:
                break
            R(s, c, x, y0 + 11 - bh, bw, bh)
            R(s, mul(c, 1.25), x, y0 + 11 - bh, 1, bh)
            R(s, mul(c, 0.7), x + bw - 1, y0 + 11 - bh, 1, bh)
            R(s, BRASS if rng.random() < 0.5 else CREAM, x, y0 + 11 - bh + 2, bw, 1)
            x += bw
        if row == 1:
            pygame.draw.circle(s, (70, 120, 170), (36, y0 + 6), 4)
            R(s, (80, 150, 90), 34, y0 + 4, 3, 3)
            R(s, BRASS, 36, y0 + 10, 1, 1)
        if row == 2:                                           # a leaning book and a little robot
            pygame.draw.polygon(s, TEAL, [(30, y0 + 10), (33, y0 + 2), (36, y0 + 3), (35, y0 + 10)])
            R(s, (160, 170, 180), 38, y0 + 4, 4, 7)
            R(s, RED, 39, y0 + 6, 2, 1)
        R(s, WOOD_LT, 2, y0 + 11, 42, 3)
        R(s, WOOD_DK, 2, y0 + 13, 42, 1)
    R(s, WOOD_HI, 0, 0, 46, 1)
    R(s, WOOD_LT, 1, 0, 1, 66)
    return finish(s)


@cached
def power_box():
    """The electric panel on the wall; 18x24. The status light is drawn by the scene (it blinks)."""
    s = sprite(18, 24)
    R(s, (96, 104, 104), 0, 0, 18, 24)
    R(s, (128, 138, 136), 1, 1, 16, 22)
    R(s, (150, 160, 156), 1, 1, 16, 1)
    R(s, (88, 96, 96), 1, 22, 16, 1)
    R(s, (108, 116, 114), 3, 3, 12, 15)                      # the door panel
    R(s, (86, 92, 92), 3, 10, 12, 1)
    R(s, (64, 70, 70), 14, 7, 1, 5)                          # handle
    R(s, (70, 76, 76), 2, 5, 1, 2)                           # hinges
    R(s, (70, 76, 76), 2, 14, 1, 2)
    R(s, (234, 190, 50), 5, 12, 8, 5)                        # a warning sticker
    R(s, LINE, 8, 12, 2, 2)
    R(s, LINE, 9, 14, 2, 2)
    R(s, LINE, 7, 15, 1, 1)
    R(s, (60, 66, 66), 4, 19, 10, 2)                         # a few spare fuse slots
    for x in (5, 8, 11):
        R(s, (200, 200, 190), x, 19, 2, 2)
    return finish(s)


@cached
def desk():
    """The writing desk: a deep wooden top, a drawer pedestal on the right and open knee space; 122x40."""
    s = sprite(122, 40)
    R(s, WOOD_LT, 0, 0, 122, 16)                              # the top, seen from above
    R(s, WOOD_HI, 0, 0, 122, 1)
    rng = random.Random(5)
    for _ in range(14):
        R(s, WOOD, rng.randrange(1, 110), rng.randrange(2, 14), rng.randrange(6, 16), 1)
    for x, y in ((12, 5), (40, 9), (77, 4)):                  # coffee rings
        pygame.draw.circle(s, WOOD, (x, y), 3, 1)
    R(s, WOOD_MD, 0, 16, 122, 3)                              # the front edge
    R(s, WOOD_DK, 0, 19, 122, 1)
    R(s, (54, 32, 22), 3, 20, 72, 20)                         # the dark knee space
    R(s, WOOD_MD, 80, 20, 38, 20)                             # the pedestal with two drawers
    R(s, WOOD_LT, 80, 20, 1, 20)
    for y in (22, 31):
        R(s, WOOD, 82, y, 34, 8)
        R(s, WOOD_HI, 82, y, 34, 1)
        R(s, WOOD_DK, 82, y + 7, 34, 1)
        R(s, BRASS, 97, y + 3, 5, 2)
        R(s, BRASS_LT, 97, y + 3, 5, 1)
    R(s, WOOD_DK, 0, 20, 3, 20)
    R(s, WOOD_LT, 1, 20, 1, 20)
    return finish(s)

@cached
def crt(state):
    """The old computer: a beige CRT on a stand. state: "off", "standby" (a faint glow and an amber light) or "on"; 36x34."""
    s = sprite(36, 34)
    case, case_dk, case_hi = (214, 204, 176), (170, 160, 134), (238, 230, 206)
    R(s, case_dk, 0, 0, 36, 28)
    R(s, case, 0, 0, 36, 27)
    R(s, case_hi, 0, 0, 36, 1)
    R(s, case_hi, 0, 0, 1, 27)
    R(s, (60, 54, 48), 3, 3, 30, 20)                         # bezel
    screen = {"off": (22, 30, 28), "standby": (26, 44, 40), "on": (40, 150, 110)}[state]
    R(s, screen, 5, 5, 26, 16)
    if state != "off":
        R(s, mul(screen, 1.5), 5, 5, 26, 1)
    R(s, mul(screen, 1.35), 7, 7, 5, 1)    # a curve of reflected light
    R(s, mul(screen, 1.35), 7, 7, 1, 4)
    R(s, case_dk, 2, 24, 32, 2)
    R(s, (80, 74, 66), 24, 25, 4, 1)                         # drive slot area
    R(s, LINE, 5, 25, 14, 1)                                 # the floppy slot
    led = {"off": (90, 40, 30), "standby": (255, 170, 40), "on": (110, 255, 150)}[state]
    R(s, led, 30, 24, 2, 2)
    R(s, case_dk, 6, 28, 24, 3)                              # neck and base
    R(s, case, 4, 30, 28, 3)
    R(s, case_hi, 4, 30, 28, 1)
    return finish(s)


@cached
def keyboard():
    s = sprite(30, 7)
    R(s, (200, 190, 164), 0, 0, 30, 6)
    R(s, (236, 228, 204), 0, 0, 30, 1)
    for r in range(3):
        for c in range(10):
            R(s, (96, 90, 82) if (c + r) % 5 else (150, 110, 80), 2 + c * 2 + (r % 2), 1 + r * 2, 1, 1)
    R(s, (96, 90, 82), 8, 5, 14, 1)
    return finish(s)


@cached
def phone(lit):
    """A retro telephone in cream and brick-red; 24x15. `lit`: its signal lamp is glowing."""
    s = sprite(24, 15)
    body, body_dk = (196, 84, 64), (140, 54, 44)
    R(s, body_dk, 1, 6, 22, 9)
    pygame.draw.rect(s, body, (1, 5, 22, 9), border_radius=3)
    R(s, (230, 130, 104), 3, 5, 18, 1)
    pygame.draw.circle(s, CREAM, (12, 10), 3)                 # the rotary dial
    pygame.draw.circle(s, LINE, (12, 10), 3, 1)
    R(s, LINE, 12, 10)
    for dx, dy in ((-2, -2), (0, -2), (2, -2), (2, 0), (2, 2), (-2, 2), (-2, 0)):
        R(s, body_dk, 12 + dx, 10 + dy)
    R(s, LINE, 1, 3, 22, 3)                                    # the handset on the cradle
    R(s, (60, 40, 40), 0, 1, 4, 5)
    R(s, (60, 40, 40), 20, 1, 4, 5)
    R(s, (96, 66, 62), 3, 2, 18, 3)
    R(s, (150, 112, 100), 3, 2, 18, 1)
    R(s, (255, 220, 120) if lit else (90, 70, 40), 20, 8, 2, 2)  # the signal lamp
    return finish(s)


@cached
def cabinet():
    """A tall wooden filing cabinet with three drawers and a small electronic keypad; 30x50."""
    s = sprite(30, 50)
    R(s, WOOD_DK, 0, 0, 30, 50)
    R(s, WOOD_MD, 1, 1, 28, 48)
    R(s, WOOD_HI, 0, 0, 30, 2)
    for i in range(3):
        y = 4 + i * 15
        R(s, WOOD, 3, y, 24, 13)
        R(s, WOOD_LT, 3, y, 24, 1)
        R(s, WOOD_DK, 3, y + 12, 24, 1)
        R(s, CREAM, 9, y + 2, 12, 5)                          # label card
        R(s, (150, 120, 90), 10, y + 4, 8, 1)
        R(s, BRASS, 11, y + 9, 8, 2)
        R(s, BRASS_LT, 11, y + 9, 8, 1)
    R(s, (40, 40, 48), 21, 1, 7, 9)                            # the keypad on the top-right corner
    R(s, (30, 90, 70), 22, 2, 5, 2)
    for r in range(2):
        for c in range(3):
            R(s, (150, 150, 160), 22 + c * 2, 5 + r * 2, 1, 1)
    R(s, WOOD_DK, 2, 48, 5, 2)
    R(s, WOOD_DK, 23, 48, 5, 2)
    return finish(s)


@cached
def plant():
    s = sprite(16, 26)
    for x, y, hh, c in ((7, 0, 12, (70, 130, 70)), (3, 4, 9, (88, 150, 80)), (10, 3, 10, (58, 112, 66))):
        pygame.draw.ellipse(s, c, (x - 3, y, 7, hh))
        R(s, mul(c, 1.3), x, y + 2, 1, hh - 4)
    pygame.draw.ellipse(s, (60, 110, 62), (1, 7, 8, 8))
    pygame.draw.ellipse(s, (80, 140, 76), (7, 8, 8, 7))
    R(s, RED_DK, 3, 15, 10, 11)
    R(s, RED, 3, 15, 10, 2)
    R(s, RED, 4, 17, 8, 8)
    R(s, mul(RED, 1.2), 4, 17, 2, 8)
    R(s, (60, 40, 30), 4, 15, 8, 1)
    return finish(s)


@cached
def game_boxes():
    """A tidy stack of cardboard game boxes with a row of old cartridges on top; 30x24."""
    s = sprite(30, 24)
    for (x, y, w, h, c) in ((0, 14, 28, 10, (190, 150, 100)), (2, 7, 24, 8, (168, 126, 82))):
        R(s, c, x, y, w, h)
        R(s, mul(c, 1.2), x, y, w, 1)
        R(s, mul(c, 0.72), x, y + h - 1, w, 1)
        R(s, mul(c, 0.8), x + w - 2, y, 2, h)
    R(s, RED, 4, 17, 8, 4)
    R(s, CREAM, 5, 18, 6, 1)
    R(s, TEAL, 15, 17, 8, 4)
    for i, c in enumerate(((120, 120, 132), (96, 96, 108), (140, 110, 90))):          # three cartridges standing on top
        x = 4 + i * 7
        R(s, c, x, 0, 6, 8)
        R(s, mul(c, 1.3), x, 0, 6, 1)
        R(s, CREAM, x + 1, 2, 4, 3)
        R(s, mul(c, 0.6), x + 1, 6, 4, 1)
    R(s, MUSTARD, 24, 3, 3, 4)
    return finish(s)

@cached
def pouf():
    s = sprite(28, 18)
    pygame.draw.ellipse(s, mul(TEAL, 0.7), (0, 4, 28, 14))
    pygame.draw.ellipse(s, TEAL, (0, 1, 28, 14))
    pygame.draw.ellipse(s, mul(TEAL, 1.2), (4, 2, 14, 5))
    R(s, TEAL_DK, 13, 8, 2, 1)
    R(s, MUSTARD, 20, 5, 4, 2)                                 # a cassette tape left on it
    R(s, LINE, 21, 5)
    R(s, LINE, 23, 5)
    return finish(s)


@cached
def door():
    """The way out, a wooden door set into the left wall (seen from the side, so narrow); 20x54."""
    s = sprite(20, 54)
    R(s, WOOD_DK, 0, 0, 20, 54)
    R(s, WOOD_MD, 2, 2, 16, 52)
    for y in (4, 29):
        R(s, WOOD, 4, y, 12, 21)
        R(s, WOOD_HI, 4, y, 12, 1)
        R(s, WOOD_DK, 4, y + 20, 12, 1)
    R(s, BRASS, 14, 28, 3, 3)
    R(s, BRASS_LT, 14, 28, 3, 1)
    return finish(s)


# ------------------------------------------------------------------ icons for the Trial Inventory and the notes
@cached
def disk_icon(size=14):
    """The OLD BOOT DISK: a 3.5in floppy with a metal shutter and a hand-written label."""
    s = sprite(14, 14)
    R(s, (40, 40, 52), 0, 0, 14, 14)
    R(s, (60, 62, 80), 1, 1, 12, 12)
    R(s, (200, 200, 210), 4, 1, 6, 5)
    R(s, (90, 90, 100), 8, 2, 1, 3)
    R(s, CREAM, 2, 8, 10, 5)
    R(s, (120, 90, 70), 3, 10, 6, 1)
    R(s, RED, 3, 9, 3, 1)
    R(s, (40, 40, 52), 0, 0, 2, 2)
    return s


@cached
def paper_icon():
    s = sprite(12, 14)
    R(s, CREAM, 0, 0, 12, 14)
    R(s, CREAM_DK, 9, 0, 3, 3)
    for y in range(3, 12, 2):
        R(s, (130, 110, 90), 2, y, 8, 1)
    return s


@cached
def book_icon():
    s = sprite(13, 14)
    R(s, RED_DK, 0, 0, 13, 14)
    R(s, RED, 1, 1, 11, 12)
    R(s, BRASS, 3, 3, 7, 2)
    R(s, BRASS, 3, 7, 5, 1)
    R(s, CREAM, 11, 1, 2, 12)
    return s


# ------------------------------------------------------------------ light
_lights = {}


def soft_light(radius, color, squash=1.0, steps=12):
    """A soft radial light (black outside, `color` at the centre, quadratic falloff in a few pixel-art bands) for
    BLEND_RGB_ADD. Cached. Built from nested ellipses, so even a big one costs next to nothing."""
    key = (radius, tuple(color), squash)
    img = _lights.get(key)
    if img is None:
        w, h = radius * 2, max(2, int(radius * 2 * squash))
        img = pygame.Surface((w, h))
        img.fill((0, 0, 0))
        for i in range(steps, 0, -1):
            k = ((steps - i + 1) / steps) ** 2
            rect = pygame.Rect(0, 0, max(2, int(w * i / steps)), max(2, int(h * i / steps)))
            rect.center = (w // 2, h // 2)
            pygame.draw.ellipse(img, tuple(int(c * k) for c in color), rect)
        _lights[key] = img
    return img


def tinted_light(radius, color, level, squash=1.0):
    """soft_light in `color`, scaled by `level` (0..1) without building a new gradient for every level."""
    base = soft_light(radius, (255, 255, 255), squash)
    img = base.copy()
    img.fill(tuple(int(c * max(0.0, min(1.0, level))) for c in color), special_flags=pygame.BLEND_RGB_MULT)
    return img


def vignette():
    """A faint dark edge for the whole view (alpha surface, cached)."""
    img = _cache.get("vignette")
    if img is None:
        img = sprite(*VIEW)
        w, h = VIEW
        for i in range(12):
            a = int(80 * (1 - i / 11) ** 2)
            pygame.draw.rect(img, (10, 4, 0, a), (i, i, w - 2 * i, h - 2 * i), 1)
        _cache["vignette"] = img
    return img


def scanlines(rect_size, alpha=34):
    """Faint horizontal lines for a CRT screen of the given size."""
    key = ("scan", rect_size, alpha)
    img = _cache.get(key)
    if img is None:
        img = sprite(*rect_size)
        for y in range(0, rect_size[1], 2):
            img.fill((0, 0, 0, alpha), (0, y, rect_size[0], 1))
        _cache[key] = img
    return img


# ------------------------------------------------------------------ the little things (every one of them can be inspected)
@cached
def alarm_clock():
    """A twin-bell alarm clock reading 3:47; 11x11."""
    s = sprite(11, 11)
    R(s, RED_DK, 1, 0, 3, 2)
    R(s, RED_DK, 7, 0, 3, 2)
    pygame.draw.circle(s, RED, (5, 6), 5)
    pygame.draw.circle(s, CREAM, (5, 6), 4)
    R(s, LINE, 5, 3, 1, 3)                                   # hands: just before four
    R(s, LINE, 5, 6, 3, 1)
    R(s, RED_DK, 2, 10, 2, 1)
    R(s, RED_DK, 7, 10, 2, 1)
    return finish(s)


@cached
def noodle_cup():
    """An instant-noodle cup with the lid half peeled; 12x13."""
    s = sprite(12, 13)
    pygame.draw.polygon(s, CREAM, [(0, 3), (11, 3), (9, 12), (2, 12)])
    R(s, RED, 1, 5, 10, 3)
    R(s, MUSTARD, 3, 6, 6, 1)
    R(s, CREAM_DK, 0, 2, 12, 2)
    R(s, (214, 184, 110), 1, 0, 8, 2)                        # noodles peeking out
    R(s, (214, 184, 110), 4, 1, 6, 1)
    R(s, mul(CREAM, 0.8), 9, 3, 2, 8)
    return finish(s)


@cached
def coffee_mug():
    """A mug of long-cold coffee; 10x9."""
    s = sprite(10, 9)
    R(s, (230, 226, 214), 0, 1, 7, 8)
    R(s, (96, 60, 40), 1, 1, 5, 2)
    R(s, (230, 226, 214), 7, 3, 2, 1)
    R(s, (230, 226, 214), 8, 3, 1, 4)
    R(s, (230, 226, 214), 7, 6, 2, 1)
    R(s, TEAL, 1, 5, 5, 1)
    R(s, (190, 186, 174), 0, 8, 7, 1)
    return finish(s)


@cached
def cookie_jar():
    """A glass cookie jar with a few crumbs and nothing else; 12x15."""
    s = sprite(12, 15)
    R(s, (150, 190, 200), 1, 3, 10, 12)
    R(s, (200, 228, 232), 2, 4, 2, 9)
    R(s, (120, 150, 160), 1, 14, 10, 1)
    R(s, WOOD_MD, 2, 0, 8, 3)
    R(s, WOOD_HI, 2, 0, 8, 1)
    R(s, (186, 126, 70), 4, 13, 2, 1)
    R(s, (186, 126, 70), 8, 12, 1, 1)
    return finish(s)


@cached
def low_table():
    """A low wooden coffee table; 58x26."""
    s = sprite(58, 26)
    R(s, WOOD_LT, 0, 0, 58, 12)
    R(s, WOOD_HI, 0, 0, 58, 1)
    R(s, WOOD_MD, 0, 12, 58, 3)
    R(s, WOOD_DK, 0, 15, 58, 1)
    for x in (2, 51):
        R(s, WOOD_DK, x, 15, 5, 11)
        R(s, WOOD_MD, x + 1, 15, 1, 11)
    rng = random.Random(9)
    for _ in range(6):
        R(s, WOOD, rng.randrange(2, 50), rng.randrange(2, 10), rng.randrange(4, 10), 1)
    return finish(s)


@cached
def homework():
    """Homework scattered on the floor: loose sheets with scribbles; 32x18."""
    s = sprite(32, 18)
    for (x, y, tilt) in ((1, 3, 0), (10, 0, 1), (18, 4, -1), (6, 8, 1)):
        R(s, CREAM, x, y, 12, 9)
        R(s, CREAM_DK, x, y + 8, 12, 1)
        for i in range(3):
            R(s, (140, 110, 90), x + 2, y + 2 + i * 2, 8 - i * 2 - tilt, 1)
    R(s, RED, 22, 6, 4, 1)                                    # a red mark
    R(s, RED, 23, 5, 2, 3)
    R(s, (60, 60, 90), 8, 12, 5, 1)
    return finish(s)


@cached
def textbook():
    """A fat textbook lying on the floor; 20x12."""
    s = sprite(20, 12)
    R(s, (70, 90, 150), 0, 2, 20, 10)
    R(s, mul((70, 90, 150), 1.3), 0, 2, 20, 1)
    R(s, CREAM, 2, 0, 17, 3)
    R(s, (220, 220, 230), 4, 5, 12, 2)
    R(s, BRASS, 4, 8, 7, 1)
    R(s, mul((70, 90, 150), 0.7), 0, 11, 20, 1)
    return finish(s)


@cached
def trash_bin():
    """A wire-mesh bin overflowing with crumpled paper; 14x19."""
    s = sprite(14, 19)
    R(s, (120, 126, 132), 1, 6, 12, 13)
    for y in range(7, 19, 2):
        R(s, (84, 90, 96), 1, y, 12, 1)
    for x in range(2, 13, 3):
        R(s, (84, 90, 96), x, 6, 1, 13)
    R(s, (150, 156, 160), 0, 5, 14, 2)
    for (x, y, c) in ((2, 1, CREAM), (6, 0, (240, 232, 200)), (9, 2, CREAM), (4, 3, (230, 220, 190))):
        R(s, c, x, y, 4, 4)
        R(s, CREAM_DK, x + 3, y, 1, 4)
    return finish(s)


@cached
def side_frame():
    """A framed photo seen on the side wall (narrow); 10x14."""
    s = sprite(10, 14)
    R(s, WOOD_MD, 0, 0, 10, 14)
    R(s, (140, 180, 210), 2, 2, 6, 10)
    R(s, (90, 140, 90), 2, 9, 6, 3)
    R(s, (240, 220, 160), 3, 3, 2, 2)
    return finish(s)


@cached
def side_poster():
    """A game poster seen on the side wall (narrow); 10x30."""
    s = sprite(10, 30)
    R(s, CREAM, 0, 0, 10, 30)
    R(s, (46, 84, 140), 1, 1, 8, 28)
    pygame.draw.circle(s, MUSTARD, (5, 10), 3)
    R(s, (40, 130, 70), 1, 21, 8, 8)
    R(s, (30, 30, 50), 4, 14, 3, 6)
    R(s, CREAM, 2, 3, 6, 1)
    return finish(s)


# ------------------------------------------------------------------ PUZZLE 05: the four old photographs
# The same desk four times, from the same spot. Nothing is written on the fronts: the order is read from what changes
# (golden_age.PHOTO_FACTS): the computer goes from a pile of wires to an open case to a working machine, the game on the
# screen gets its colours, the little plant grows a leaf each time, the idea sheet moves from the desk to the wall, the
# mug and the notebook wander, and at the end the room is full of friends.
PHOTO_SIZE = (64, 48)
SKIN = ((236, 196, 160), (196, 140, 100), (150, 100, 70))


def _photo_room(s):
    W, H = PHOTO_SIZE
    R(s, (214, 182, 136), 0, 0, W, 30)                       # wallpaper
    for x in range(0, W, 6):
        R(s, (204, 170, 124), x, 0, 3, 30)
    R(s, (120, 150, 196), 3, 3, 13, 11)                      # the window (the same patch of sky in every photo)
    R(s, (170, 196, 230), 3, 3, 13, 4)
    R(s, WOOD_DK, 9, 3, 1, 11)
    R(s, WOOD_DK, 3, 8, 13, 1)
    R(s, WOOD_MD, 2, 2, 15, 1)
    R(s, WOOD_MD, 2, 14, 15, 1)
    R(s, WOOD_LT, 0, 30, W, 3)                                # the desk top
    R(s, WOOD_HI, 0, 30, W, 1)
    R(s, WOOD_MD, 0, 33, W, H - 33)
    R(s, WOOD, 40, 36, 20, 7)                                 # its drawer
    R(s, BRASS, 48, 39, 4, 1)
    R(s, WOOD_DK, 0, 33, W, 1)


def _plant(s, stage):
    R(s, RED_DK, 56, 25, 6, 5)
    R(s, RED, 56, 25, 6, 1)
    leaf = (90, 160, 80)
    R(s, (60, 110, 60), 58, 21, 1, 4)                         # the stem
    if stage >= 1:
        R(s, leaf, 59, 22, 2, 1)
    if stage >= 2:
        R(s, leaf, 56, 21, 2, 1)
    if stage >= 3:
        R(s, (60, 110, 60), 58, 17, 1, 4)
        R(s, leaf, 59, 18, 2, 1)
    if stage >= 4:
        R(s, (255, 150, 180), 57, 15, 3, 2)                    # a flower
        R(s, (255, 230, 120), 58, 15)


def _mug(s, x, y):
    R(s, CREAM, x, y, 4, 4)
    R(s, (90, 60, 40), x, y, 4, 1)
    R(s, CREAM_DK, x + 4, y + 1, 1, 2)


def _notebook(s, x, y, open_book=False):
    if open_book:
        R(s, (246, 240, 220), x, y, 10, 3)
        R(s, (150, 130, 110), x + 5, y, 1, 3)
        R(s, (120, 120, 160), x + 1, y + 1, 3, 1)
        R(s, (120, 120, 160), x + 6, y + 1, 3, 1)
    else:
        R(s, (70, 110, 160), x, y + 1, 9, 2)
        R(s, (184, 70, 56), x + 1, y, 8, 1)


def _idea_sheet(s, x, y):
    """The handwritten game idea: a paddle, a ball and an arrow, scribbled on lined paper."""
    R(s, (250, 246, 230), x, y, 9, 11)
    for i in range(3):
        R(s, (150, 150, 190), x + 1, y + 1 + i * 2, 7 - i, 1)
    R(s, (60, 60, 80), x + 2, y + 9, 4, 1)                     # the paddle
    R(s, (184, 70, 56), x + 5, y + 7)                          # the ball
    R(s, (60, 60, 80), x + 6, y + 6)


def _monitor(s, on, art):
    R(s, (206, 196, 168), 22, 12, 22, 18)                     # the beige case of the monitor
    R(s, (176, 166, 140), 22, 28, 22, 2)
    R(s, (150, 140, 116), 30, 30, 6, 1)
    if not on:
        R(s, (40, 46, 44), 24, 14, 18, 12)
        R(s, (70, 80, 76), 25, 15, 4, 1)                       # a dull glint on dead glass
        return
    R(s, (20, 60, 46), 24, 14, 18, 12)
    if art == 1:                                              # the first version: plain grey-green bricks
        for r in range(2):
            for c in range(4):
                R(s, (110, 200, 150), 25 + c * 4, 15 + r * 2, 3, 1)
    else:                                                     # the finished art: three rows of colours
        cols = ((240, 150, 150), (240, 230, 130), (140, 190, 240))
        for r in range(3):
            for c in range(4):
                R(s, cols[r], 25 + c * 4, 15 + r * 2, 3, 1)
    R(s, (236, 232, 200), 30, 24, 5, 1)                       # paddle
    R(s, (236, 232, 200), 33, 21)                             # ball


def _person(s, x, y, hair, shirt, skin, laugh=False):
    R(s, shirt, x - 1, y + 6, 8, 8)
    R(s, mul(shirt, 1.2), x - 1, y + 6, 8, 1)
    R(s, skin, x, y, 6, 6)
    R(s, hair, x, y - 1, 6, 2)
    R(s, hair, x - 1, y, 1, 3)
    R(s, (40, 30, 30), x + 1, y + 2)
    R(s, (40, 30, 30), x + 4, y + 2)
    if laugh:
        R(s, (150, 50, 60), x + 2, y + 4, 2, 1)
        R(s, (40, 30, 30), x + 1, y + 3)
        R(s, (40, 30, 30), x + 4, y + 3)
    else:
        R(s, (40, 30, 30), x + 2, y + 4, 2, 1)
        R(s, (40, 30, 30), x + 1, y + 3)
        R(s, (40, 30, 30), x + 4, y + 3)


@cached
def photo_base(key):
    """One photograph at its own size (64x48, opaque, with a white border)."""
    W, H = PHOTO_SIZE
    s = pygame.Surface((W, H))
    _photo_room(s)
    if key == "desk":
        _plant(s, 1)
        _mug(s, 4, 26)
        _notebook(s, 10, 27)
        _notebook(s, 11, 25)
        _idea_sheet(s, 24, 21)
        for i, c in enumerate(((184, 70, 56), (70, 150, 90), (70, 110, 180))):       # loose wires all over the desk
            for k in range(14):
                R(s, c, 36 + k, 28 + int(1.4 * math.sin(k * 0.9 + i * 1.7)) - i % 2)
    elif key == "build":
        _plant(s, 2)
        _notebook(s, 36, 29)                                     # the notebook has wandered right, the mug sits on it
        _idea_sheet(s, 46, 6)
        R(s, (220, 60, 60), 50, 6)                               # pinned
        _monitor(s, False, 0)
        R(s, (206, 196, 168), 4, 18, 14, 12)                    # the computer case, its side panel off
        R(s, (40, 110, 70), 6, 20, 10, 8)
        for (x, y) in ((7, 21), (10, 22), (13, 21), (8, 25), (12, 25)):
            R(s, (30, 30, 36), x, y, 2, 2)                      # chips
        R(s, (220, 190, 80), 6, 27, 9, 1)
        R(s, (190, 190, 200), 45, 27, 7, 1)                     # a screwdriver
        R(s, (220, 70, 60), 51, 26, 3, 3)
        R(s, (30, 30, 36), 18, 28, 2, 2)                        # loose parts on the desk
        R(s, (30, 30, 36), 46, 23, 2, 2)
        R(s, (184, 70, 56), 20, 29, 6, 1)
        _mug(s, 38, 25)
    elif key == "game":
        _plant(s, 3)
        _idea_sheet(s, 46, 6)
        R(s, (220, 60, 60), 50, 6)
        _monitor(s, True, 1)
        R(s, (206, 196, 168), 4, 18, 14, 12)                    # the case, closed now, its light on
        R(s, (176, 166, 140), 4, 22, 14, 1)
        R(s, (120, 255, 150), 15, 27)
        R(s, (200, 194, 170), 24, 31, 18, 2)                    # keyboard
        for (x, y) in ((18, 12), (44, 13), (44, 19)):            # sticky notes stuck round the screen
            R(s, (250, 236, 130), x, y, 4, 4)
            R(s, (170, 140, 60), x + 1, y + 1, 2, 1)
        R(s, (250, 246, 230), 46, 28, 6, 3)                      # debug notes, one with a red X
        R(s, (220, 60, 60), 47, 29)
        R(s, (220, 60, 60), 49, 29)
        R(s, (250, 246, 230), 20, 28, 4, 2)
        _mug(s, 52, 26)
        _notebook(s, 6, 31, open_book=True)
    elif key == "friends":
        _plant(s, 4)
        _idea_sheet(s, 46, 6)
        R(s, (220, 60, 60), 50, 6)
        _monitor(s, True, 2)
        R(s, (206, 196, 168), 4, 18, 14, 12)
        R(s, (176, 166, 140), 4, 22, 14, 1)
        R(s, (120, 255, 150), 15, 27)
        R(s, (200, 194, 170), 24, 31, 18, 2)
        _person(s, 8, 32, (60, 40, 30), (120, 160, 220), SKIN[0], laugh=True)
        _person(s, 30, 34, (30, 30, 40), (230, 140, 90), SKIN[1], laugh=True)
        _person(s, 50, 32, (150, 90, 50), (130, 190, 120), SKIN[2])
        R(s, (250, 250, 250), 27, 33)                            # somebody's hand up, cheering
        R(s, SKIN[1], 27, 34, 1, 3)
    # an old print: a little faded, then the white border
    fade = pygame.Surface((W, H), pygame.SRCALPHA)
    fade.fill((255, 236, 200, 34))
    s.blit(fade, (0, 0))
    pygame.draw.rect(s, (244, 238, 222), (0, 0, W, H), 2)
    return s


@cached
def photo(key, scale=1):
    base = photo_base(key)
    return base if scale == 1 else pygame.transform.scale(base, (PHOTO_SIZE[0] * scale, PHOTO_SIZE[1] * scale))


# ------------------------------------------------------------------ the little cats (bell dials, doodles, carvings)
CAT_SHAPES = {
    "sit": ("...#...#....",
            "...##.##....",
            "...#####....",
            "...#o#o#....",
            "...#####....",
            "....###.....",
            "...#####....",
            "..#######...",
            "..#######.#.",
            "..#######.#.",
            "..########..",
            "...##.##...."),
    "sleep": ("..........z.",
              ".........z..",
              "........zzz.",
              "............",
              "..#.#.......",
              "..###.......",
              ".#-#-###....",
              ".##########.",
              "###########.",
              "###########.",
              ".#########..",
              "............"),
    "play": ("............",
             "#...........",
             "#...#..#....",
             "#...####....",
             "##.#o##o#...",
             ".#.######...",
             ".#########..",
             ".########.y.",
             ".########yyy",
             "..##..##.yyy",
             "..##..##..y.",
             "............"),
    "fish": ("............",
             "............",
             "............",
             "...#####..#.",
             "..#######.#.",
             ".#o#######..",
             ".#########..",
             "..#######.#.",
             "...#####..#.",
             "............",
             "............",
             "............"),
}


@cached
def cat_icon(kind, ink, eye=None, extra=None):
    """A little cat (12x12): # in `ink`, o for its eyes (`eye`, or the paper showing through), - a closed eye, z and y the
    sleeping Zs and the ball of yarn in `extra`."""
    s = sprite(12, 12)
    for y, row in enumerate(CAT_SHAPES[kind]):
        for x, ch in enumerate(row):
            if ch == "#":
                R(s, ink, x, y)
            elif ch == "o" and eye:
                R(s, eye, x, y)
            elif ch == "-":
                R(s, mul(ink, 2.2) if eye is None else eye, x, y)
            elif ch in "zy":
                R(s, extra or ink, x, y)
    return s


def _scaled(surf, k):
    return pygame.transform.scale(surf, (surf.get_width() * k, surf.get_height() * k))


@cached
def picture(name):
    """A picture for a page of the reader (already at the size it is shown)."""
    if name.startswith("photo_"):
        return photo(name[6:], 3)
    if name == "doodle_sit":                                   # blue ballpoint on the textbook's back cover
        s = pygame.Surface((96, 72))
        s.fill((236, 226, 196))
        for y in range(6, 72, 8):
            R(s, (214, 202, 170), 0, y, 96, 1)
        s.blit(_scaled(cat_icon("sit", (60, 70, 150)), 4), (24, 12))
        R(s, (60, 70, 150), 70, 54, 14, 1)                       # a scribbled line under it
        return s
    if name == "cartridge_sleep":
        s = pygame.Surface((120, 72))
        s.fill((96, 96, 108))
        R(s, (120, 120, 132), 0, 0, 120, 4)
        R(s, (70, 70, 80), 0, 68, 120, 4)
        R(s, (232, 222, 196), 8, 12, 104, 48)                    # the label along its side
        R(s, (184, 70, 56), 8, 12, 104, 6)
        s.blit(_scaled(cat_icon("sleep", (70, 60, 70), None, (120, 120, 200)), 3), (38, 20))
        return s
    if name == "carving_play":
        s = pygame.Surface((120, 72))
        s.fill(WOOD)
        rng = random.Random(41)
        for _ in range(60):
            R(s, mul(WOOD, rng.choice((0.9, 1.08))), rng.randrange(0, 116), rng.randrange(0, 72), rng.randrange(3, 9), 1)
        cut = _scaled(cat_icon("play", WOOD_DK, None, mul(WOOD_DK, 1.7)), 4)
        s.blit(cut, (36, 10))
        hi = _scaled(cat_icon("play", WOOD_HI, None, WOOD_HI), 4)          # a light edge under each cut
        hi.set_alpha(70)
        s.blit(hi, (37, 11))
        s.blit(cut, (36, 10))
        return s
    if name == "sketch":
        s = pygame.Surface((96, 80))
        s.fill((240, 232, 210))
        pencil = (70, 66, 70)
        body = _scaled(cat_icon("sit", pencil, (240, 232, 210)), 5)
        s.blit(body, (18, 16))
        for (x, y) in ((33, 14), (37, 11), (41, 14), (45, 11), (49, 14)):       # a tiny crown, in yellow pencil
            R(s, (214, 170, 60), x, y, 3, 4)
        R(s, (214, 170, 60), 33, 16, 19, 3)
        rng = random.Random(77)
        for _ in range(70):                                                     # a rough hand: stray strokes around the lines
            x, y = rng.randrange(14, 82), rng.randrange(14, 78)
            if any(s.get_at((x + dx, y + dy))[:3] == pencil for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
                   if 0 <= x + dx < 96 and 0 <= y + dy < 80):
                R(s, (120, 116, 122), x, y, rng.choice((1, 2, 3)), 1)
        for k in range(8):                                                      # the line it sits on
            R(s, (150, 146, 150), 14 + k * 9, 72 - (k % 3), 6, 1)
        return s
    if name == "index_strip":
        s = pygame.Surface((176, 40))
        s.fill((40, 40, 48))
        R(s, (250, 244, 222), 4, 6, 168, 28)
        R(s, (184, 70, 56), 4, 6, 168, 4)
        for i in range(3):
            R(s, (200, 200, 220), 8, 16 + i * 6, 160, 1)
        return s
    raise KeyError(name)


# ------------------------------------------------------------------ the photo board and the bedside cabinet's states
@cached
def side_photo_board(slots=(None, None, None, None), opened=False):
    """The wooden photo board on the right-hand wall (seen from the side, like the frames opposite): four slots, one
    above the other, holding whatever is pinned there. Opened: it has swung a little away from the wall; 12x46."""
    s = sprite(12, 46)
    R(s, WOOD_LT, 0, 0, 12, 46)                                 # a light frame, so it reads against the dark side wall
    R(s, WOOD_HI, 0, 0, 12, 1)
    R(s, WOOD_HI, 11, 0, 1, 46)
    R(s, WOOD_MD, 0, 45, 12, 1)
    R(s, (206, 154, 100), 1, 1, 10, 44)                         # cork face
    for (x, y) in ((3, 12), (8, 22), (4, 31), (7, 41), (9, 6)):
        R(s, (184, 134, 86), x, y)
    tones = {"desk": (214, 186, 140), "build": (170, 168, 150), "game": (110, 170, 140), "friends": (220, 160, 150)}
    for i, p in enumerate(slots):
        y = 3 + i * 10
        if p is None:                                           # an empty paper outline waiting for a photo
            R(s, CREAM_DK, 2, y, 8, 8)
            R(s, (150, 106, 66), 3, y + 1, 6, 6)
        else:
            R(s, (244, 238, 222), 2, y, 8, 8)
            R(s, tones[p], 3, y + 1, 6, 6)
            R(s, mul(tones[p], 0.7), 3, y + 4, 6, 3)
        R(s, BRASS_LT, 5, y - 1, 2, 1)
    if opened:
        R(s, (20, 12, 8), 0, 0, 2, 46)                          # the gap behind it
        R(s, (250, 244, 222), 0, 20, 2, 4)                      # a pale corner of something tucked in there
    return finish(s)


@cached
def bedside_table(state="shut"):
    """A little wooden nightstand with a drawer, wide enough for a lamp and an alarm clock; 28x26. A tiny cat is scratched
    into its front (you would only notice it close up). state: "shut", "note" (the hidden compartment at the bottom is
    open with a folded paper in it) or "empty" (open, the note taken)."""
    s = sprite(28, 26)
    R(s, WOOD_MD, 0, 8, 28, 18)
    R(s, WOOD_HI, 0, 8, 28, 2)
    R(s, WOOD, 2, 12, 24, 7)
    R(s, WOOD_HI, 2, 12, 24, 1)
    R(s, BRASS, 12, 15, 4, 1)
    R(s, WOOD_DK, 1, 22, 3, 4)
    R(s, WOOD_DK, 24, 22, 3, 4)
    for (x, y) in ((21, 20), (22, 19), (23, 20), (22, 21)):     # the scratched little cat, barely there
        R(s, mul(WOOD_MD, 0.86), x, y)
    if state in ("note", "empty"):
        R(s, (24, 14, 10), 6, 20, 14, 3)
        if state == "note":
            R(s, CREAM, 9, 20, 6, 2)
    return finish(s)


@cached
def index_icon(size=14):
    s = sprite(size, size)
    R(s, (250, 244, 222), 1, 4, 12, 6)
    R(s, (184, 70, 56), 1, 4, 12, 2)
    R(s, (150, 150, 180), 3, 7, 8, 1)
    return finish(s)


@cached
def photo_icon(size=14):
    s = sprite(size, size)
    R(s, (244, 238, 222), 1, 2, 12, 10)
    R(s, (150, 180, 200), 2, 3, 10, 5)
    R(s, (150, 120, 90), 2, 8, 10, 3)
    return finish(s)
