"""TRIAL 02's pictures: the Tournament Hall of NEON CORNER ARCADE on championship night (procedural pixel art, cached).

Warm wood and brass from TRIAL 01's palette, with the arcade's neon on top: a stage with a big screen, championship
banners, the registration desk, the prize counter and its trophy shelf, spectator benches, a row of cabinets, the snack
bar, string lights and confetti. Everything is drawn at the hub's own scale (400x300 canvas, 12x18 people).

The layout (where things stand and what is solid) lives here too, so the scene and the pictures always agree.
"""
import math
import random

import pygame

import golden_age_art as GA
from font import get_font
from gfx import outlined
from player import PlayerLook, player_sheet
from ui import draw_text

R, put, mul, mix, sprite = GA.R, GA.put, GA.mul, GA.mix, GA.sprite
LINE = GA.LINE
WOOD_DK, WOOD_MD, WOOD, WOOD_LT, WOOD_HI = GA.WOOD_DK, GA.WOOD_MD, GA.WOOD, GA.WOOD_LT, GA.WOOD_HI
BRASS, BRASS_LT, CREAM, CREAM_DK = GA.BRASS, GA.BRASS_LT, GA.CREAM, GA.CREAM_DK
NEON_PINK, NEON_CYAN, NEON_GOLD, NEON_RED = (255, 90, 170), (80, 230, 245), (255, 214, 90), (255, 70, 70)
CARPET, CARPET_DK, CARPET_HI = (92, 36, 58), (70, 26, 46), (124, 52, 74)

# ------------------------------------------------------------------ layout (canvas pixels)
WALL_BOTTOM = 66                    # the back wall is drawn down to here ...
WALL_SOLID = 78                     # ... and feet may not go above this line
FLOOR_BOTTOM = 288
SIDE = 8
START = (34, 176)                   # just inside the door
DOOR = pygame.Rect(0, 148, 12, 50)
DOOR_ZONE = pygame.Rect(8, 152, 22, 42)
EXIT_SIGN = pygame.Rect(4, 136, 24, 10)

# name: (draw rect, solid rect or None)
FURNITURE = {
    "reg_counter": ((8, 78, 64, 24), (8, 86, 64, 16)),
    "lost_found": ((8, 116, 20, 16), (8, 122, 20, 10)),
    "stage": ((118, 60, 164, 42), (118, 64, 164, 36)),
    "prize_counter": ((318, 78, 72, 24), (318, 86, 72, 16)),
    "bench_left": ((92, 128, 60, 12), (92, 132, 60, 8)),
    "bench_right": ((248, 128, 60, 12), (248, 132, 60, 8)),
    "schedule": ((340, 110, 22, 28), (344, 130, 14, 8)),
    "cab_0": ((24, 194, 22, 36), (24, 216, 22, 14)),
    "cab_1": ((50, 194, 22, 36), (50, 216, 22, 14)),
    "cab_2": ((76, 194, 22, 36), (76, 216, 22, 14)),
    "cab_3": ((102, 194, 22, 36), (102, 216, 22, 14)),
    "snack_bar": ((298, 206, 88, 24), (298, 214, 88, 16)),
    "magazines": ((160, 256, 22, 22), (160, 268, 22, 10)),
    "photo_board": ((230, 250, 30, 28), (232, 270, 26, 8)),
    "bracket_board": ((262, 250, 32, 28), (264, 270, 28, 8)),
}
POSTER = pygame.Rect(78, 8, 28, 46)
CLOCK = pygame.Rect(33, 8, 14, 14)
LEADERBOARD = pygame.Rect(292, 6, 32, 52)
SCREEN = pygame.Rect(128, 6, 144, 50)
TROPHY_SHELF = pygame.Rect(326, 8, 60, 46)
TERMINAL = pygame.Rect(12, 68, 18, 16)
LEDGER_POS = (46, 80)
TROPHY = (232, 64)
STAGE_CABS = ((124, 58), (256, 58))
OFF_CABINET = 2                     # cab_2 is OUT OF ORDER (the one that wakes up by itself at the end)
BULB_XS = tuple(range(22, 392, 22))


# ------------------------------------------------------------------ the empty hall
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


@cached
def hall_shell():
    """Walls, wainscot, carpet and edges (400x300, opaque)."""
    s = pygame.Surface((400, 300))
    rng = random.Random(1991)
    # wallpaper: deep plum with a faint gold diamond lattice
    s.fill((54, 30, 58), (0, 0, 400, WALL_BOTTOM))
    for y in range(0, 44, 8):
        for x in range((y // 8) % 2 * 8, 400, 16):
            R(s, (72, 42, 74), x, y + 3, 2, 2)
            R(s, (96, 64, 70), x + 1, y + 4, 1, 1)
    # neon strip under the cornice
    R(s, (30, 14, 34), 0, 0, 400, 3)
    R(s, NEON_PINK, 0, 3, 400, 1)
    # wainscot: warm wood panels
    R(s, WOOD_DK, 0, 44, 400, 2)
    R(s, WOOD_MD, 0, 46, 400, WALL_BOTTOM - 46)
    for x in range(0, 400, 25):
        R(s, WOOD, x + 2, 48, 21, WALL_BOTTOM - 52)
        R(s, WOOD_LT, x + 2, 48, 21, 1)
        R(s, WOOD_DK, x + 2, WALL_BOTTOM - 5, 21, 1)
    R(s, BRASS, 0, 45, 400, 1)
    R(s, (40, 22, 16), 0, WALL_BOTTOM - 2, 400, 2)
    # carpet: the arcade's own pattern (warm magenta with tiny gold stars and cyan squiggles)
    s.fill(CARPET, (0, WALL_BOTTOM, 400, FLOOR_BOTTOM - WALL_BOTTOM))
    for y in range(WALL_BOTTOM, FLOOR_BOTTOM, 12):
        for x in range(((y // 12) % 2) * 12, 400, 24):
            R(s, CARPET_HI, x + 5, y + 5, 2, 2)
            R(s, (200, 160, 70), x + 6, y + 4, 1, 1)
            R(s, (200, 160, 70), x + 6, y + 7, 1, 1)
            if rng.random() < 0.5:
                R(s, (60, 110, 130), x + 14, y + 9, 3, 1)
                R(s, (60, 110, 130), x + 16, y + 10, 2, 1)
    for _ in range(260):
        R(s, CARPET_DK, rng.randrange(0, 400), rng.randrange(WALL_BOTTOM, FLOOR_BOTTOM), 1, 1)
    # a soft shadow under the wall
    for i in range(6):
        sh = pygame.Surface((400, 1), pygame.SRCALPHA)
        sh.fill((10, 2, 6, 90 - i * 15))
        s.blit(sh, (0, WALL_BOTTOM + i))
    # side walls and the front edge
    R(s, (34, 18, 26), 0, 0, SIDE, 300)
    R(s, WOOD_DK, SIDE - 1, WALL_BOTTOM, 1, FLOOR_BOTTOM - WALL_BOTTOM)
    R(s, (34, 18, 26), 400 - SIDE, 0, SIDE, 300)
    R(s, WOOD_DK, 400 - SIDE, WALL_BOTTOM, 1, FLOOR_BOTTOM - WALL_BOTTOM)
    R(s, (24, 12, 18), 0, FLOOR_BOTTOM, 400, 300 - FLOOR_BOTTOM)
    R(s, BRASS, 0, FLOOR_BOTTOM, 400, 1)
    # the red runner up the aisle to the stage
    R(s, (150, 40, 44), 166, 100, 68, FLOOR_BOTTOM - 100)
    R(s, (186, 62, 58), 166, 100, 68, 1)
    for y in range(104, FLOOR_BOTTOM, 6):
        R(s, (120, 30, 36), 168, y, 64, 1)
    R(s, BRASS, 166, 100, 1, FLOOR_BOTTOM - 100)
    R(s, BRASS, 233, 100, 1, FLOOR_BOTTOM - 100)
    return s


# ------------------------------------------------------------------ wall pieces
@cached
def poster():
    """THE NEON CORNER CHAMPIONSHIP: a tall poster with a fighter silhouette and a fee table."""
    w, h = POSTER.size
    s = sprite(w, h)
    R(s, (34, 20, 60), 0, 0, w, h)
    R(s, (255, 214, 90), 0, 0, w, 1)
    for y in range(4, 22):
        R(s, mix((255, 90, 170), (120, 40, 160), (y - 4) / 18), 2, y, w - 4, 1)
    R(s, (20, 10, 30), 10, 9, 8, 10)            # a fighter, fist raised
    R(s, (20, 10, 30), 16, 6, 3, 4)
    R(s, (255, 230, 150), 12, 10, 4, 3)
    for i, c in enumerate(((255, 214, 90), (230, 220, 250), (230, 220, 250), (230, 220, 250), (255, 120, 170))):
        R(s, c, 4, 25 + i * 4, w - 8 - (i % 2) * 6, 2)
    R(s, (80, 230, 245), 4, h - 5, w - 8, 2)
    return outlined(s, LINE)


@cached
def wall_clock(minutes):
    """The clock above the registration desk. `minutes` past six o'clock (it runs a little behind, of course)."""
    s = sprite(CLOCK.w, CLOCK.h)
    c = CLOCK.w // 2
    pygame.draw.circle(s, BRASS, (c, c), c)
    pygame.draw.circle(s, CREAM, (c, c), c - 2)
    for k in range(12):
        a = k * math.tau / 12
        R(s, LINE, int(c + math.sin(a) * (c - 3)), int(c - math.cos(a) * (c - 3)))
    hour = (6 + minutes / 60) % 12
    for angle, length in ((hour / 12 * math.tau, c - 5), (minutes % 60 / 60 * math.tau, c - 3)):
        pygame.draw.line(s, LINE, (c, c), (int(c + math.sin(angle) * length), int(c - math.cos(angle) * length)))
    return outlined(s, LINE)


def leaderboard(time, glitch=0.0):
    """The old all-time board: a dark slate with gold rows. The top row flickers when `glitch` is up."""
    w, h = LEADERBOARD.size
    s = sprite(w, h)
    R(s, WOOD_DK, 0, 0, w, h)
    R(s, (16, 18, 30), 2, 2, w - 4, h - 4)
    R(s, BRASS, 2, 2, w - 4, 1)
    draw_text(s, "BEST", (w // 2, 4), NEON_GOLD, anchor="midtop")
    for i in range(5):
        y = 15 + i * 7
        top = i == 0
        color = NEON_GOLD if top else (150, 160, 200)
        if top and glitch > 0 and int(time * 30) % 3:
            color = (255, 80, 120)
            R(s, color, 3 + int(time * 50) % 5, y, w - 9, 4)
        else:
            R(s, color, 4, y + 1, 11, 2)
            R(s, mul(color, 0.7), 18, y + 1, w - 22, 2)
    R(s, (60, 66, 100), 4, h - 6, w - 8, 1)
    return outlined(s, LINE)


def stage_screen(time, mode="title", round_no=1, glitch=0.0):
    """The big screen above the stage. mode: title / round / win / complete / off."""
    w, h = SCREEN.size
    s = pygame.Surface((w, h))
    s.fill((8, 6, 20))
    if mode == "off":
        pygame.draw.rect(s, (40, 36, 60), (0, 0, w, h), 2)
        return s
    for y in range(2, h - 2, 2):
        R(s, (14, 12, 34), 2, y, w - 4, 1)
    font = get_font()
    if mode == "title":
        k = (math.sin(time * 2.2) + 1) / 2
        draw_text(s, "NEON CORNER", (w // 2, 8), mix(NEON_PINK, NEON_GOLD, k), 2, "midtop")
        draw_text(s, "CHAMPIONSHIP", (w // 2, 27), NEON_CYAN, 1, "midtop")
        x = int(w - (time * 30) % (w + 160))
        draw_text(s, "TONIGHT ONLY  THREE ROUNDS  ONE CHAMPION", (x, 39), (200, 190, 230))
    elif mode == "round":
        draw_text(s, f"ROUND {round_no:02d}", (w // 2, 8), NEON_GOLD, 2, "midtop")
        name = ("QUALIFIER", "SEMIFINAL", "GRAND FINAL")[max(0, min(2, round_no - 1))]
        draw_text(s, name, (w // 2, 27), NEON_CYAN, 1, "midtop")
        if int(time * 2) % 2:
            draw_text(s, "NEXT MATCH", (w // 2, 38), (230, 220, 250), 1, "midtop")
    elif mode == "win":
        k = int(time * 6) % 2
        draw_text(s, "WINNER!", (w // 2, 10), NEON_GOLD if k else NEON_PINK, 2, "midtop")
        draw_text(s, "MOVES ON", (w // 2, 32), NEON_CYAN, 1, "midtop")
    elif mode == "bracket":
        draw_text(s, "SEMIFINAL", (w // 2, 8), NEON_GOLD, 1, "midtop")
        rng = random.Random(int(time * 6))
        junk = "".join(rng.choice("?#_X0") if rng.random() < 0.7 else "?" for _ in range(6)).replace("#", "?")
        draw_text(s, f"{junk}  VS  ???", (w // 2, 22), (255, 90, 130), 1, "midtop")
        draw_text(s, "BRACKET ERROR", (w // 2, 36), (200, 190, 230) if int(time * 2) % 2 else (90, 80, 120), 1, "midtop")
    elif mode == "offline":
        draw_text(s, "STAGE OFFLINE", (w // 2, 12), (200, 190, 230), 1, "midtop")
        if int(time * 2) % 2:
            draw_text(s, "KEY REQUIRED", (w // 2, 28), NEON_GOLD, 1, "midtop")
    elif mode == "complete":
        draw_text(s, "TOURNAMENT COMPLETE", (w // 2, 6), NEON_GOLD, 1, "midtop")
        draw_text(s, "PLAYER SATISFACTION:", (w // 2, 19), (230, 220, 250), 1, "midtop")
        draw_text(s, "99%", (w // 2, 30), NEON_PINK if int(time * 3) % 2 else NEON_CYAN, 2, "midtop")
    if glitch > 0:
        rng = random.Random(int(time * 24))
        for _ in range(4):
            y = rng.randrange(0, h - 3)
            band = s.subsurface((0, y, w, 3)).copy()
            s.blit(band, (rng.randrange(-8, 9), y))
        if mode == "complete" and rng.random() < 0.6:
            R(s, (8, 6, 20), 4, 30, w - 8, 15)
            draw_text(s, "99999999", (w // 2, 30), (255, 70, 110), 2, "midtop")
    pygame.draw.rect(s, (60, 50, 90), (0, 0, w, h), 1)
    pygame.draw.rect(s, mix(NEON_PINK, NEON_CYAN, (math.sin(time * 1.3) + 1) / 2), (1, 1, w - 2, h - 2), 1)
    return s


@cached
def banner(color):
    """A tall championship banner: a pointed hem and a gold star."""
    w, h = 14, 44
    s = sprite(w, h)
    pygame.draw.polygon(s, color, [(0, 0), (w - 1, 0), (w - 1, h - 6), (w // 2, h - 1), (0, h - 6)])
    R(s, mul(color, 0.7), 0, 0, 2, h - 6)
    R(s, BRASS_LT, 0, 0, w, 2)
    cx, cy = w // 2, 14
    pygame.draw.polygon(s, NEON_GOLD, [(cx, cy - 4), (cx + 1, cy - 1), (cx + 4, cy - 1), (cx + 2, cy + 1), (cx + 3, cy + 4),
                                       (cx, cy + 2), (cx - 3, cy + 4), (cx - 2, cy + 1), (cx - 4, cy - 1), (cx - 1, cy - 1)])
    for i in range(3):
        R(s, CREAM, 3, 24 + i * 4, w - 6, 1)
    return outlined(s, LINE)


@cached
def trophy_shelf():
    w, h = TROPHY_SHELF.size
    s = sprite(w, h)
    R(s, WOOD_DK, 0, 0, w, h)
    R(s, (30, 18, 30), 2, 2, w - 4, h - 4)
    for row in (20, 42):
        R(s, WOOD_LT, 2, row, w - 4, 2)
    for i, x in enumerate((6, 20, 34, 48)):
        cup = (NEON_GOLD, (200, 210, 230), (214, 140, 80), NEON_GOLD)[i]
        R(s, cup, x, 9, 7, 5)
        R(s, mul(cup, 0.7), x + 2, 14, 3, 3)
        R(s, cup, x + 1, 17, 5, 3)
        R(s, mul(cup, 1.2), x + 1, 10, 1, 3)
    for x in (8, 26, 44):
        R(s, (90, 160, 220), x, 30, 9, 11)
        R(s, CREAM, x + 2, 32, 5, 1)
        R(s, NEON_GOLD, x + 3, 36, 3, 3)
    R(s, (120, 160, 200, 60), 2, 2, 3, h - 4)
    return outlined(s, LINE)


# ------------------------------------------------------------------ furniture
@cached
def counter(w, h, top, front, sign=None, sign_color=NEON_CYAN):
    s = sprite(w, h)
    R(s, mul(top, 0.7), 0, 0, w, 8)
    R(s, top, 0, 0, w, 7)
    R(s, mul(top, 1.2), 0, 0, w, 1)
    R(s, front, 0, 8, w, h - 8)
    for x in range(4, w - 4, 12):
        R(s, mul(front, 1.15), x, 11, 8, h - 15)
        R(s, mul(front, 0.75), x, h - 4, 8, 1)
    R(s, BRASS, 0, 8, w, 1)
    if sign:
        tw = get_font().size(sign)[0]
        R(s, (14, 10, 24), (w - tw) // 2 - 3, 11, tw + 6, 10)
        draw_text(s, sign, (w // 2, 13), sign_color, anchor="midtop")
    return outlined(s, LINE)


@cached
def terminal(state="red"):
    """The registration terminal on the desk: a little beige computer. state: red (NOT FOUND) / green (registered)."""
    s = sprite(TERMINAL.w, TERMINAL.h)
    R(s, (206, 196, 168), 0, 0, 18, 13)
    R(s, (160, 150, 124), 0, 12, 18, 2)
    R(s, (20, 30, 24), 2, 2, 14, 8)
    color = (255, 90, 90) if state == "red" else (110, 255, 170)
    R(s, color, 4, 4, 10, 1)
    R(s, mul(color, 0.6), 4, 6, 7, 1)
    R(s, (140, 130, 110), 3, 14, 12, 2)
    return outlined(s, LINE)


@cached
def ledger_book():
    s = sprite(22, 8)
    R(s, (120, 40, 40), 0, 0, 22, 8)
    R(s, CREAM, 1, 1, 9, 6)
    R(s, CREAM, 12, 1, 9, 6)
    for y in (2, 4):
        R(s, (150, 130, 110), 2, y, 7, 1)
        R(s, (150, 130, 110), 13, y, 7, 1)
    R(s, (170, 120, 60), 15, 3, 4, 3)               # the soda stain
    return outlined(s, LINE)


@cached
def lost_found():
    w, h = FURNITURE["lost_found"][0][2:]
    s = sprite(w, h)
    R(s, (176, 130, 80), 0, 4, w, h - 4)
    R(s, (140, 100, 60), 0, 4, w, 2)
    R(s, (90, 60, 100), 3, 0, 4, 6)                  # a glove
    R(s, (255, 80, 120), 9, 1, 4, 4)                 # a yo-yo
    R(s, CREAM, 14, 2, 4, 3)                         # a ticket stub
    draw_text(s, "L+F", (w // 2, 8), LINE, anchor="midtop")
    return outlined(s, LINE)


@cached
def stage():
    """The platform: planks, a lit front edge (bulbs drawn live), steps on the aisle."""
    x0, y0, w, h = FURNITURE["stage"][0]
    s = sprite(w, h)
    R(s, (120, 70, 40), 0, 4, w, h - 14)
    for y in range(6, h - 10, 5):
        R(s, (140, 86, 50), 0, y, w, 1)
    for x in range(0, w, 23):
        R(s, (96, 56, 32), x, 4, 1, h - 14)
    R(s, (54, 26, 40), 0, h - 10, w, 10)             # the front skirt
    R(s, BRASS, 0, h - 10, w, 1)
    R(s, (200, 60, 90), 0, h - 3, w, 1)
    # steps at the aisle
    for i in range(3):
        R(s, (150, 96, 56), 52 - i * 2, h - 8 + i * 3, 60 + i * 4, 3)
        R(s, (110, 66, 38), 52 - i * 2, h - 6 + i * 3, 60 + i * 4, 1)
    return outlined(s, LINE)


def stage_bulbs(surf, time, party=False):
    x0, y0, w, h = FURNITURE["stage"][0]
    y = y0 + h - 7
    for i, x in enumerate(range(x0 + 4, x0 + w - 2, 8)):
        if 48 < x - x0 < 116:
            continue
        on = (i + int(time * (8 if party else 3))) % 3 != 0
        surf.fill(NEON_GOLD if on else (90, 60, 30), (x, y, 2, 2))


@cached
def trophy():
    s = sprite(14, 22)
    R(s, NEON_GOLD, 2, 0, 10, 8)
    R(s, mul(NEON_GOLD, 0.75), 2, 6, 10, 2)
    R(s, NEON_GOLD, 0, 1, 2, 4)
    R(s, NEON_GOLD, 12, 1, 2, 4)
    R(s, (255, 250, 200), 4, 1, 1, 5)
    R(s, mul(NEON_GOLD, 0.8), 5, 8, 4, 6)
    R(s, NEON_GOLD, 3, 14, 8, 2)
    R(s, WOOD_DK, 2, 16, 10, 6)
    R(s, BRASS_LT, 4, 18, 6, 1)
    return outlined(s, LINE)


def cabinet(color, screen, on=True, time=0.0, glitch=False):
    """An upright cabinet (22x36). `screen` is what it shows: attract / continue. Frames are cached (8 per second)."""
    return _cabinet(tuple(color), screen, bool(on), int(time * 8) % 48, bool(glitch))


@cached
def _cabinet(color, screen, on, k, glitch):
    time = k / 8
    s = sprite(22, 36)
    R(s, mul(color, 0.6), 0, 2, 22, 34)
    R(s, color, 1, 2, 20, 33)
    R(s, mul(color, 1.25), 1, 2, 20, 1)
    R(s, (20, 14, 30), 2, 0, 18, 6)                  # marquee
    R(s, mul(color, 1.3) if on else mul(color, 0.5), 3, 1, 16, 4)
    R(s, (14, 10, 22), 3, 8, 16, 12)                 # screen bezel
    if on:
        if screen == "continue":
            k = int(time * 3) % 2
            R(s, (10, 30, 40), 4, 9, 14, 10)
            draw_text(s, "?", (11, 10), (255, 214, 90) if k else (255, 90, 170), anchor="midtop")
        else:
            glow = mix((40, 90, 160), (200, 60, 160), (math.sin(time * 3 + color[0]) + 1) / 2)
            R(s, glow, 4, 9, 14, 10)
            for k in range(3):
                R(s, (255, 240, 200), 5 + int((time * 9 + k * 5) % 12), 11 + k * 3, 2, 1)
        if glitch:
            R(s, (255, 255, 255), 4, 9 + int(time * 40) % 10, 14, 1)
    else:
        R(s, (24, 26, 34), 4, 9, 14, 10)
        R(s, (40, 44, 56), 5, 10, 4, 1)
    R(s, (30, 24, 40), 1, 21, 20, 6)                 # control panel
    R(s, (230, 60, 80), 5, 22, 3, 2)
    R(s, (80, 200, 240), 12, 22, 2, 2)
    R(s, (255, 214, 90), 15, 23, 2, 2)
    R(s, mul(color, 0.5), 1, 30, 20, 1)
    R(s, (40, 30, 30), 8, 31, 6, 3)                  # coin door
    R(s, NEON_GOLD, 10, 32, 2, 1)
    return outlined(s, LINE)


@cached
def out_of_order_sign():
    s = sprite(18, 7)
    R(s, CREAM, 0, 0, 18, 7)
    R(s, (200, 60, 60), 1, 1, 16, 1)
    R(s, (120, 100, 90), 2, 3, 14, 1)
    R(s, (120, 100, 90), 2, 5, 10, 1)
    return outlined(s, LINE)


@cached
def bench(w):
    s = sprite(w, 12)
    R(s, WOOD, 0, 0, w, 5)
    R(s, WOOD_LT, 0, 0, w, 1)
    R(s, WOOD_DK, 0, 5, w, 2)
    for x in (2, w - 6):
        R(s, (60, 40, 30), x, 7, 4, 5)
    R(s, (60, 40, 30), w // 2 - 2, 7, 4, 5)
    return outlined(s, LINE)


@cached
def schedule_board():
    s = sprite(22, 28)
    R(s, WOOD_DK, 9, 18, 4, 10)
    R(s, (20, 16, 36), 0, 0, 22, 19)
    R(s, BRASS, 0, 0, 22, 1)
    for i in range(3):
        R(s, NEON_GOLD if i == 0 else (180, 190, 230), 3, 4 + i * 5, 6, 2)
        R(s, (120, 130, 170), 11, 4 + i * 5, 8, 2)
    return outlined(s, LINE)


@cached
def snack_bar():
    w, h = FURNITURE["snack_bar"][0][2:]
    s = counter(w, h, (190, 70, 70), (120, 40, 50), "SNACKS", NEON_GOLD).copy()
    return s


@cached
def popcorn():
    s = sprite(14, 18)
    R(s, (200, 40, 50), 0, 6, 14, 12)
    R(s, (255, 240, 200), 2, 8, 10, 6)
    for x, y in ((3, 9), (6, 8), (9, 10), (4, 12), (8, 12)):
        R(s, (255, 214, 120), x, y, 2, 2)
    R(s, (200, 40, 50), 1, 0, 12, 6)
    R(s, NEON_GOLD, 2, 2, 10, 2)
    return outlined(s, LINE)


@cached
def soda_cups():
    s = sprite(16, 9)
    for i, c in enumerate(((255, 90, 120), (80, 200, 240), (255, 214, 90))):
        R(s, c, i * 5, 2, 4, 7)
        R(s, CREAM, i * 5 + 2, 0, 1, 3)
    return outlined(s, LINE)


@cached
def magazine_rack():
    s = sprite(22, 22)
    R(s, WOOD_DK, 0, 10, 22, 12)
    R(s, WOOD, 1, 10, 20, 2)
    for i, c in enumerate(((255, 90, 170), (80, 200, 240), (255, 214, 90), (120, 230, 140))):
        R(s, c, 1 + i * 5, 2 + (i % 2) * 2, 5, 10)
        R(s, CREAM, 2 + i * 5, 4 + (i % 2) * 2, 3, 1)
    return outlined(s, LINE)


@cached
def photo_board():
    s = sprite(30, 28)
    R(s, WOOD_DK, 4, 20, 3, 8)
    R(s, WOOD_DK, 23, 20, 3, 8)
    R(s, (150, 110, 70), 0, 0, 30, 21)
    R(s, (120, 86, 56), 1, 1, 28, 19)
    for i, (x, y) in enumerate(((3, 3), (12, 2), (21, 4), (4, 11), (14, 11), (22, 12))):
        R(s, CREAM, x, y, 7, 6)
        R(s, ((90, 120, 180), (200, 120, 90), (120, 170, 110))[i % 3], x + 1, y + 1, 5, 3)
        R(s, (255, 80, 90), x + 3, y, 1, 1)
    return outlined(s, LINE)


@cached
def door():
    s = sprite(12, 50)
    R(s, WOOD_DK, 0, 0, 12, 50)
    R(s, WOOD, 2, 2, 8, 46)
    R(s, WOOD_LT, 2, 2, 8, 1)
    R(s, BRASS_LT, 8, 26, 2, 3)
    return outlined(s, LINE)


def exit_sign(lit=1.0, locked=False):
    return _exit_sign(round(max(0.0, min(1.0, lit)), 1), bool(locked))


@cached
def _exit_sign(lit, locked):
    s = sprite(EXIT_SIGN.w, EXIT_SIGN.h)
    R(s, (30, 10, 10), 0, 0, EXIT_SIGN.w, EXIT_SIGN.h)
    color = mix((70, 20, 20), NEON_RED, max(0.0, min(1.0, lit)))
    draw_text(s, "EXIT", (EXIT_SIGN.w // 2, 2), color, anchor="midtop")
    if locked:
        R(s, NEON_GOLD, EXIT_SIGN.w - 4, 1, 3, 3)
    return outlined(s, LINE)


@cached
def padlock():
    s = sprite(7, 8)
    pygame.draw.rect(s, (200, 200, 210), (1, 0, 5, 5), 1)
    R(s, NEON_GOLD, 0, 3, 7, 5)
    R(s, LINE, 3, 5, 1, 2)
    return outlined(s, LINE)


def string_lights(surf, time, party=False):
    """Bulbs on a wire across the top of the hall."""
    for i, x in enumerate(BULB_XS):
        y = 58 + int(3 * math.sin(i * 0.9))
        if i:
            px = BULB_XS[i - 1]
            pygame.draw.line(surf, (40, 26, 30), (px, 58 + int(3 * math.sin((i - 1) * 0.9))), (x, y))
        c = (NEON_GOLD, NEON_PINK, NEON_CYAN, (140, 240, 150))[i % 4]
        on = party or (i + int(time * 1.5)) % 5 != 0
        surf.fill(c if on else mul(c, 0.35), (x - 1, y + 1, 3, 3))


@cached
def badge_icon():
    """The temporary TOURNAMENT BADGE (a trial keepsake, not a Secret Item)."""
    s = sprite(13, 16)
    R(s, (255, 90, 170), 2, 0, 3, 5)
    R(s, (80, 200, 240), 8, 0, 3, 5)
    pygame.draw.circle(s, NEON_GOLD, (6, 10), 5)
    pygame.draw.circle(s, (255, 250, 200), (6, 10), 3)
    R(s, (200, 120, 40), 5, 8, 3, 5)
    R(s, (200, 120, 40), 4, 9, 1, 1)
    return outlined(s, LINE)


# ------------------------------------------------------------------ people
def person_look(key, shirt, hair, skin=None, hair_style="short", eyes="dot", hat_color=None, pants=None):
    """A visitor's colours on the hub's own character sprite. No hat: the beanie rows are painted as hair."""
    sk = skin or ((250, 214, 180), (255, 140, 170), (30, 20, 50))
    top = hat_color or hair
    return PlayerLook(f"npc_{key}", shirt=shirt, shirt_dark=mul(shirt, 0.72), beanie=top, beanie_dark=mul(top, 0.8),
                      pom=hat_color and mix(hat_color, (255, 255, 255), 0.4) or mul(hair, 1.1), outline=(36, 20, 30),
                      skin=sk[0], blush=sk[1], eye=sk[2], hair=hair, hair_style=hair_style, eyes=eyes)


def person_sheet(look, outfit=None):
    return player_sheet(look, tuple(outfit) if outfit else (None,) * 6)


def confetti_colors():
    return (NEON_PINK, NEON_CYAN, NEON_GOLD, (140, 240, 150), (255, 140, 90), (200, 150, 255))


# ------------------------------------------------------------------ PUZZLE 03: trophies and photos
MARKS = {
    "heart": (".X.X.", "XXXXX", "XXXXX", ".XXX.", "..X.."),
    "bolt": ("..XX.", ".XX..", "XXXXX", "..XX.", ".XX.."),
    "coin": (".XXX.", "X...X", "X.X.X", "X...X", ".XXX."),
}
TROPHY_COLORS = {"cup": ((255, 214, 90), (200, 150, 50)), "rocket": ((210, 220, 236), (150, 160, 184)),
                 "joystick": ((240, 90, 100), (180, 50, 70))}


@cached
def trophy_piece(kind, facing, mark):
    """One trophy of the cabinet puzzle (22x34), seen with `facing` 0..3 towards the viewer. Its engraved mark is on
    the front of the brass base: facing 0 shows it, 2 shows the plain back with a little label, 1 and 3 the sides."""
    s = sprite(22, 34)
    c, d = TROPHY_COLORS[kind]
    side = facing in (1, 3)
    if kind == "cup":
        R(s, c, 5, 2, 12, 9)
        R(s, mul(c, 1.2), 6, 3, 2, 6)
        R(s, d, 5, 10, 12, 2)
        if not side:
            R(s, c, 2, 3, 3, 2)
            R(s, c, 2, 3, 2, 6)
            R(s, c, 17, 3, 3, 2)
            R(s, c, 18, 3, 2, 6)
        else:
            hx = 17 if facing == 1 else 2
            R(s, c, hx, 3, 3, 2)
            R(s, c, hx + (1 if facing == 1 else 0), 3, 2, 6)
        R(s, d, 9, 12, 4, 6)
        R(s, c, 7, 18, 8, 2)
    elif kind == "rocket":
        R(s, c, 8, 1, 6, 15)
        R(s, mul(c, 1.15), 9, 2, 2, 12)
        R(s, (220, 70, 80), 9, 0, 4, 2)
        R(s, (90, 160, 230), 9, 5, 4, 3) if not facing == 2 else R(s, d, 9, 5, 4, 3)
        if side:
            R(s, (220, 70, 80), 13 if facing == 1 else 5, 12, 4, 5)
        else:
            R(s, (220, 70, 80), 5, 12, 3, 5)
            R(s, (220, 70, 80), 14, 12, 3, 5)
        R(s, (255, 180, 80), 9, 16, 4, 2)
        R(s, d, 10, 17, 2, 3)
    else:                                                       # joystick
        pygame.draw.circle(s, c, (11, 5), 4)
        R(s, mul(c, 1.3), 9, 3, 2, 2)
        R(s, (60, 60, 70), 10, 9, 2, 7)
        R(s, (30, 30, 40), 4, 15, 14, 5)
        if facing == 0:
            R(s, (255, 214, 90), 6, 16, 2, 2)
            R(s, (80, 200, 240), 14, 16, 2, 2)
        elif facing == 2:
            R(s, (90, 90, 100), 6, 17, 10, 1)
    # the brass base
    bx, bw = (4, 14) if side else (2, 18)
    R(s, (150, 104, 40), bx, 20, bw, 13)
    R(s, (214, 164, 62), bx, 20, bw, 2)
    R(s, (110, 74, 30), bx, 31, bw, 2)
    if facing == 0:
        for y, row in enumerate(MARKS[mark]):
            for x, ch in enumerate(row):
                if ch == "X":
                    R(s, (70, 42, 16), 8 + x, 23 + y, 1, 1)                       # engraved
                    if y == 4 or MARKS[mark][y + 1][x] != "X":
                        R(s, (250, 218, 120), 8 + x, 24 + y, 1, 1)                # its bright lower lip
    elif facing == 2:
        R(s, (230, 226, 210), 7, 24, 8, 4)
        R(s, (150, 140, 130), 8, 25, 6, 1)
    else:
        R(s, (110, 74, 30), bx + bw // 2 - 1, 25, 2, 2)                 # a screw
    return outlined(s, LINE)


def photo_image(photo, stamp):
    """One photo of the wall (150x112): the night's banner with its year, a winner holding the trophy up, the crowd,
    a caption written on the white border, the reprint stamp in the corner."""
    w, h = 150, 112
    s = pygame.Surface((w, h))
    s.fill((244, 238, 222))
    inner = pygame.Rect(6, 6, w - 12, 78)
    tint = {"cup": (110, 70, 60), "rocket": (60, 80, 120), "joystick": (90, 60, 110)}[photo["trophy"]]
    for y in range(inner.h):
        s.fill(mix(tint, (30, 20, 30), y / inner.h), (inner.x, inner.y + y, inner.w, 1))
    band = pygame.Rect(inner.x + 8, inner.y + 5, inner.w - 16, 14)
    s.fill((200, 60, 70), band)
    text = f"{photo['banner']} {photo['year']}"
    draw_text(s, text, band.center, (255, 240, 200), 1, "center")
    for i in range(9):                                          # the crowd
        x = inner.x + 4 + i * 15
        pygame.draw.circle(s, mul(tint, 0.5), (x, inner.bottom - 8), 6)
        s.fill(mul(tint, 0.5), (x - 6, inner.bottom - 6, 12, 6))
    cx = inner.centerx
    s.fill((40, 30, 40), (cx - 6, inner.y + 44, 12, 22))       # the winner
    s.fill((230, 180, 140), (cx - 4, inner.y + 34, 8, 8))
    s.fill((40, 30, 40), (cx + 6, inner.y + 36, 3, 10))
    big = pygame.transform.scale(trophy_piece(photo["trophy"], 0, "heart"), (24, 37))
    big.fill((0, 0, 0, 0), (0, 22, 24, 15))                     # (the base is behind the winner's hand)
    s.blit(big, (cx + 4, inner.y + 18))
    draw_text(s, photo["caption"], (w // 2, inner.bottom + 8), (90, 70, 60), 1, "midtop")
    draw_text(s, stamp, (w - 8, h - 11), (200, 90, 90), 1, "topright")
    pygame.draw.rect(s, (200, 190, 170), (0, 0, w, h), 1)
    return s


@cached
def bracket_board(scrambled):
    w, h = 32, 28
    s = sprite(w, h)
    R(s, WOOD_DK, 4, 20, 3, 8)
    R(s, WOOD_DK, 25, 20, 3, 8)
    R(s, (20, 16, 36), 0, 0, w, 21)
    R(s, BRASS, 0, 0, w, 1)
    rng = random.Random(4 if scrambled else 2)
    for i in range(8):
        y = 2 + i * 2 + (i // 2)
        x = 2 + (rng.randint(0, 8) if scrambled else 0)
        R(s, (230, 220, 250) if i % 2 == 0 else (180, 190, 230), x, y, 7, 1)
    for i in range(4):
        R(s, NEON_GOLD, 12, 3 + i * 5, 6, 1)
    R(s, NEON_PINK, 21, 6, 6, 1)
    R(s, NEON_PINK, 21, 14, 6, 1)
    R(s, NEON_CYAN, 28, 10, 3, 1)
    if scrambled:
        R(s, (255, 80, 110), 1, 17, w - 2, 1)
    return outlined(s, LINE)


def key_icon():
    s = sprite(16, 10)
    pygame.draw.circle(s, NEON_GOLD, (4, 5), 4)
    R(s, (40, 26, 20), 3, 4, 2, 2)
    R(s, NEON_GOLD, 8, 4, 8, 2)
    R(s, NEON_GOLD, 12, 6, 2, 3)
    R(s, NEON_GOLD, 15, 6, 1, 2)
    R(s, (200, 40, 50), 0, 0, 2, 3)
    return outlined(s, LINE)
