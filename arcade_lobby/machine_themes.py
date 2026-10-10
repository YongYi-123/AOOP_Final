"""Hand-drawn looks for the CAT and VOLLEY cabinets (see machine.STYLES).

machine.py owns the shared cabinet; this module only supplies what makes these two
different: the attract-mode screen, the marquee, a little extra art on the cabinet
body and, for the cat cabinet, ears standing above the marquee. Everything is
drawn once at load time (frames are played back by machine.ArcadeMachine).
"""
import math

import pygame

from font import get_font
from gfx import scale_color, shade
from settings import Col

# ----------------------------------------------------------------- palettes
CAT_PINK = (255, 120, 205)
CAT_LAVENDER = (200, 160, 255)
CAT_EYE = (110, 250, 255)
VOLLEY_BLUE = (50, 140, 255)
VOLLEY_ORANGE = (255, 150, 40)
VOLLEY_YELLOW = (255, 226, 80)
SKIN = (255, 214, 168)

TICKER_GAP = "    "            # blank run between two passes of a scrolling marquee
TICKER_STEP = 2                # pixels the ticker moves per marquee frame

# Door of the cabinet (the lower panel); machine._build_cabinet draws a plain one first.
DOOR = pygame.Rect(5, 43, 26, 14)


def marquee_frames(style, label):
    """How many marquee frames a style cycles through (the volley ticker needs a full scroll)."""
    if style == "volley":
        period = get_font().size(label + TICKER_GAP)[0]
        return -(-period // TICKER_STEP)
    return 4


# ----------------------------------------------------------------- Cat Territory
# A miniature Cat Territory board: coloured regions, hearts, a timer bar, cats popping in.
_CAT_REGIONS = ("AABBB",
                "ACCBE",
                "ACDEE",
                "DDDEE",
                "DDDEE")
_CAT_COLORS = {"A": (150, 90, 200), "B": (96, 110, 190), "C": (78, 160, 104),
               "D": (190, 104, 72), "E": (62, 160, 152)}
_CAT_SOLUTION = ((1, 0), (3, 1), (0, 2), (2, 3), (4, 4))      # (column, row): one per row and column
_CAT_X = ((4, 0), (0, 4))


def _mini_cat(s, x, y, nose=CAT_PINK):
    for dx, dy in ((0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (2, 2)):
        s.set_at((x + dx, y + dy), (250, 248, 255))
    s.set_at((x + 1, y + 2), nose)


def _heart(s, x, y, color):
    for dx, dy in ((0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (1, 2)):
        s.set_at((x + dx, y + dy), color)


def screen_cat(s, p, accent, neon):
    s.fill((22, 10, 44))
    cell, ox = 3, 2
    for row, line in enumerate(_CAT_REGIONS):
        for col, ch in enumerate(line):
            s.fill(_CAT_COLORS[ch], (ox + col * cell, row * cell, cell, cell))
            # the dark region borders of the real game: a line wherever the region changes
            if col + 1 < 5 and line[col + 1] != ch:
                s.fill((18, 8, 34), (ox + col * cell + 2, row * cell, 1, cell))
            if row + 1 < 5 and _CAT_REGIONS[row + 1][col] != ch:
                s.fill((18, 8, 34), (ox + col * cell, row * cell + 2, cell, 1))
    placed = min(len(_CAT_SOLUTION), int(p / 0.14))
    win = p > 0.86
    for i, (col, row) in enumerate(_CAT_SOLUTION[:placed]):
        _mini_cat(s, ox + col * cell, row * cell, CAT_PINK if not win or int(p * 24) % 2 else Col.YELLOW)
    if p > 0.3:
        for col, row in _CAT_X:
            for d in range(3):
                s.set_at((ox + col * cell + d, row * cell + d), (255, 255, 255))
                s.set_at((ox + col * cell + 2 - d, row * cell + d), (255, 255, 255))
    if placed < len(_CAT_SOLUTION) and int(p * 16) % 2 == 0:      # blinking cursor on the next cell
        col, row = _CAT_SOLUTION[placed]
        pygame.draw.rect(s, Col.YELLOW, (ox + col * cell - 1, row * cell - 1, cell + 2, cell + 2), 1)
    for i in range(3):                                            # hearts, timer
        _heart(s, 19, 1 + i * 4, CAT_PINK)
    bar = max(1, int(15 * (1 - p)))
    s.fill(scale_color(accent, 0.4), (18, 14, 5, 1))
    s.fill(accent, (18, 14, max(1, bar // 3), 1))


def marquee_cat(s, r, label, frame, neon, accent):
    s.fill((16, 6, 34), r)
    font = get_font()
    tw, _ = font.size(label)
    colors = (CAT_PINK, accent, CAT_LAVENDER, CAT_PINK)
    x = r.centerx - tw // 2
    for i, ch in enumerate(label):
        glyph = font.render(ch, colors[(i + frame) % 4])
        s.blit(glyph, (x, r.y + 1))
        x += glyph.get_width() + 1
    for i in range(2, r.w - 2, 4):                                   # twinkling rail lights
        lit = (i // 4 + frame) % 2 == 0
        s.set_at((r.x + i, r.y), accent if lit else scale_color(neon, 0.5))
        s.set_at((r.x + i + 1, r.bottom - 1), scale_color(neon, 0.5) if lit else accent)


def decorate_cat(s, frame, neon, accent):
    """Cat face on the lower door (glowing eyes that blink, nose, whiskers) and paw prints."""
    d = DOOR
    s.fill((22, 10, 40), d)
    blink = frame == 2
    for cx in (d.x + 7, d.right - 8):
        if blink:
            s.fill(CAT_EYE, (cx - 2, d.y + 3, 5, 1))
        else:
            for dy, half in ((0, 1), (1, 2), (2, 1)):
                s.fill(CAT_EYE, (cx - half, d.y + 2 + dy, half * 2 + 1, 1))
            s.fill((20, 6, 40), (cx, d.y + 2, 1, 3))                  # slit pupil
            s.set_at((cx - 1, d.y + 2), (230, 255, 255))              # eye shine
    s.fill(CAT_PINK, (d.centerx - 1, d.y + 6, 3, 1))                  # nose
    s.set_at((d.centerx, d.y + 7), CAT_PINK)
    for dy in (6, 8):                                                 # whiskers
        s.fill(scale_color(CAT_LAVENDER, 0.8), (d.x + 1, d.y + dy, 5, 1))
        s.fill(scale_color(CAT_LAVENDER, 0.8), (d.right - 6, d.y + dy, 5, 1))
    s.fill((6, 2, 14), (d.centerx - 1, d.y + 9, 2, 4))                # the coin slot is the mouth
    s.fill(accent, (d.centerx - 2, d.y + 9, 1, 4))
    s.fill(accent, (d.centerx + 1, d.y + 9, 1, 4))
    # a pair of paw prints that take turns lighting up on the control panel
    for lit, px in ((frame % 2 == 0, 3), (frame % 2 == 1, 31)):
        col = CAT_PINK if lit else scale_color(CAT_PINK, 0.3)
        for dx, dy in ((0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (1, 2)):
            s.set_at((px + dx, 35 + dy), col)


def headroom_cat(s, pad, frame, neon, accent):
    """Cat ears standing on the marquee housing (`s` is the cabinet with `pad` extra rows above)."""
    twitch = 1 if frame == 2 else 0
    for tip_x, base_x0, base_x1 in ((4 - twitch, 2, 10), (31 + twitch, 26, 34)):
        pts = [(base_x0, pad), (tip_x, pad - 5), (base_x1, pad)]
        pygame.draw.polygon(s, Col.CABINET, pts)
        pygame.draw.polygon(s, neon, pts, 1)
        inner = [(base_x0 + 2, pad - 1), (tip_x, pad - 3), (base_x1 - 2, pad - 1)]
        pygame.draw.polygon(s, CAT_PINK, inner)
    s.fill(neon, (2, pad, 8, 1))
    s.fill(neon, (26, pad, 8, 1))


# ----------------------------------------------------------------- Cat Volleyball
def _player(s, x, top, shirt, cap):
    s.fill(cap, (x, top, 3, 1))
    s.fill(SKIN, (x, top + 1, 3, 1))
    s.fill(shirt, (x, top + 2, 3, 2))
    s.fill((20, 20, 40), (x, top + 4, 1, 2))
    s.fill((20, 20, 40), (x + 2, top + 4, 1, 2))
    s.fill(SKIN, (x - 1, top + 2, 1, 1))
    s.fill(SKIN, (x + 3, top + 2, 1, 1))


def screen_volley(s, p, accent, neon):
    for y in range(0, 16, 4):                                      # evening sky bands
        s.fill(lerp_sky(y / 12), (0, y, 24, 4))
    s.fill(VOLLEY_ORANGE, (0, 13, 24, 3))                          # court
    s.fill(VOLLEY_YELLOW, (0, 13, 24, 1))
    s.fill((250, 250, 255), (12, 6, 1, 7))                         # net pole and mesh
    s.fill((250, 250, 255), (11, 6, 3, 1))
    for y in range(7, 13):
        s.set_at((11, y), (150, 180, 255) if y % 2 else (90, 120, 220))
        s.set_at((13, y), (90, 120, 220) if y % 2 else (150, 180, 255))
    leg, u = int(p * 2) % 2, (p * 2) % 1.0
    jump_l = int(max(0.0, math.sin(p * math.tau * 2)) * 3) if leg == 1 else 0
    jump_r = int(max(0.0, math.sin(p * math.tau * 2)) * 3) if leg == 0 else 0
    _player(s, 4 + (1 if leg else 0), 7 - jump_l, VOLLEY_BLUE, VOLLEY_YELLOW)
    _player(s, 17 - (1 if not leg else 0), 7 - jump_r, VOLLEY_ORANGE, (255, 255, 255))
    x_from, x_to = (6, 18) if leg == 0 else (18, 6)
    bx = int(x_from + (x_to - x_from) * u)
    by = int(9 - math.sin(math.pi * u) * 7)
    s.fill((255, 255, 255), (bx, by, 2, 2))
    s.set_at((bx + 1, by + 1), VOLLEY_ORANGE)
    s.set_at((bx, by), (200, 200, 235))
    for i in range(3):                                             # score LEDs, right player leading
        s.set_at((1 + i * 2, 1), VOLLEY_YELLOW if i < 1 + leg else (60, 70, 120))
        s.set_at((22 - i * 2, 1), VOLLEY_ORANGE if i < 2 - leg else (60, 70, 120))


def lerp_sky(k):
    top, bottom = (14, 40, 130), (80, 150, 240)
    return tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))


def marquee_volley(s, r, label, frame, neon, accent):
    """A bold scrolling CAT VOLLEYBALL with chase lights above and below."""
    s.fill((6, 10, 32), r)
    font = get_font()
    text = label + TICKER_GAP
    glyphs = font.render(text, VOLLEY_YELLOW)
    period = glyphs.get_width()
    offset = frame * period // marquee_frames("volley", label)     # spreads the period evenly, so it loops seamlessly
    led = frame * 24 // marquee_frames("volley", label)               # 6 whole chase cycles per scroll
    clip = pygame.Rect(r.x + 1, r.y + 1, r.w - 2, r.h - 2)
    s.set_clip(clip)
    x = r.x + 1 - offset
    while x < clip.right:
        s.blit(glyphs, (x, r.y + 1))
        x += period
    s.set_clip(None)
    for i in range(0, r.w, 3):                                      # LED chase along both rails
        lit = ((i // 3) - led) % 4 == 0
        s.fill(VOLLEY_YELLOW if lit else scale_color(VOLLEY_ORANGE, 0.45), (r.x + i, r.y, 2, 1))
        s.fill(scale_color(VOLLEY_ORANGE, 0.45) if lit else VOLLEY_YELLOW, (r.x + i, r.bottom - 1, 2, 1))


def decorate_volley(s, frame, n, neon, accent):
    """The lower door becomes a volleyball court: net, floor line and a ball arcing over it."""
    d = DOOR
    s.fill((8, 16, 46), d)
    top = d.y + 6                                                   # net top
    for x in range(d.x + 3, d.right - 3):
        for y in range(top + 1, top + 5):
            s.set_at((x, y), (120, 160, 255) if (x + y) % 2 == 0 else (30, 56, 140))
    s.fill((250, 250, 255), (d.x + 3, top, d.w - 6, 1))             # white tape on top of the net
    for x in (d.x + 2, d.right - 3):                                # posts
        s.fill((230, 230, 245), (x, top - 2, 1, 8))
    s.fill(VOLLEY_ORANGE, (d.x + 1, d.bottom - 3, d.w - 2, 1))      # court line
    s.fill(scale_color(VOLLEY_ORANGE, 0.5), (d.x + 1, d.bottom - 2, d.w - 2, 1))
    u = frame / n
    tri = 1 - abs(2 * u - 1)                                        # to the far side and back
    bx = d.x + 4 + int(tri * (d.w - 11))
    by = d.y + 4 - int(math.sin(math.pi * ((u * 2) % 1.0)) * 3)
    s.fill((255, 255, 255), (bx, by, 3, 3))                         # pixel volleyball
    s.set_at((bx + 1, by), VOLLEY_ORANGE)
    s.set_at((bx, by + 1), VOLLEY_BLUE)
    s.set_at((bx + 2, by + 1), VOLLEY_BLUE)
    s.set_at((bx + 1, by + 2), VOLLEY_ORANGE)
    s.fill((6, 4, 14), (d.centerx - 1, d.bottom - 1, 3, 1))         # coin slot under the net
    # the screen bezel gets a ring of chasing LEDs
    bez = pygame.Rect(4, 13, 28, 20)
    step = frame * 18 // n                                          # 6 whole cycles per loop
    for i, x in enumerate(range(bez.x + 1, bez.right - 1, 3)):
        lit = (i - step) % 3 == 0
        for y in (bez.y, bez.bottom - 1):
            s.fill(VOLLEY_YELLOW if lit else scale_color(VOLLEY_BLUE, 0.7), (x, y, 1, 1))
    for i, y in enumerate(range(bez.y + 2, bez.bottom - 1, 3)):
        lit = (i + step) % 3 == 0
        for x in (bez.x, bez.right - 1):
            s.fill(VOLLEY_ORANGE if lit else scale_color(VOLLEY_BLUE, 0.7), (x, y, 1, 1))


# ----------------------------------------------------------------- registry
SCREEN_PAINTERS = {"cat": screen_cat, "volley": screen_volley}
MARQUEES = {"cat": marquee_cat, "volley": marquee_volley}
BODY_DECORATORS = {"cat": lambda s, f, n, neon, accent: decorate_cat(s, f, neon, accent),
                   "volley": decorate_volley}
HEADROOM = {"cat": (5, headroom_cat)}              # style -> (extra rows above the cabinet, painter)
