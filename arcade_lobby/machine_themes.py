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
W_BODY, H_BODY_END = 36, 59      # cabinet width; row below which the kick plate (checkered flag for the racer) starts


TICKER_STYLES = ("volley", "racer", "galaxy", "maze")      # marquees too long for 32px: they scroll the whole name


def marquee_frames(style, label):
    """How many marquee frames a style cycles through (a ticker needs a full scroll)."""
    if style in TICKER_STYLES:
        period = get_font().size(label + TICKER_GAP)[0]
        return -(-period // TICKER_STEP)
    return 4


def _ticker(s, r, label, frame, style, text_color, lit, dim):
    """A scrolling marquee: `label` passes through `r` once per loop (seamless: the offset is spread
    evenly over the frames), with chase lights along the top and bottom rails."""
    s.fill((6, 10, 32), r)
    text = label + TICKER_GAP
    glyphs = get_font().render(text, text_color)
    period, n = glyphs.get_width(), marquee_frames(style, label)
    offset = frame * period // n
    led = frame * 24 // n                                            # 6 whole chase cycles per scroll
    clip = pygame.Rect(r.x + 1, r.y + 1, r.w - 2, r.h - 2)
    s.set_clip(clip)
    x = r.x + 1 - offset
    while x < clip.right:
        s.blit(glyphs, (x, r.y + 1))
        x += period
    s.set_clip(None)
    for i in range(0, r.w, 3):
        on = ((i // 3) - led) % 4 == 0
        s.fill(lit if on else dim, (r.x + i, r.y, 2, 1))
        s.fill(dim if on else lit, (r.x + i, r.bottom - 1, 2, 1))


def _bezel_leds(s, frame, n, lit_a, lit_b, dim):
    """A ring of LEDs chasing round the screen bezel (6 whole cycles per loop)."""
    bez = pygame.Rect(4, 13, 28, 20)
    step = frame * 18 // n
    for i, x in enumerate(range(bez.x + 1, bez.right - 1, 3)):
        for y in (bez.y, bez.bottom - 1):
            s.fill(lit_a if (i - step) % 3 == 0 else dim, (x, y, 1, 1))
    for i, y in enumerate(range(bez.y + 2, bez.bottom - 1, 3)):
        for x in (bez.x, bez.right - 1):
            s.fill(lit_b if (i + step) % 3 == 0 else dim, (x, y, 1, 1))


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
    _ticker(s, r, label, frame, "volley", VOLLEY_YELLOW, VOLLEY_YELLOW, scale_color(VOLLEY_ORANGE, 0.45))


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
    _bezel_leds(s, frame, n, VOLLEY_YELLOW, VOLLEY_ORANGE, scale_color(VOLLEY_BLUE, 0.7))


# ----------------------------------------------------------------- Starfall Assault
GALAXY_CYAN = (90, 240, 255)
GALAXY_VIOLET = (170, 110, 255)
GALAXY_ORANGE = (255, 160, 60)
_GALAXY_STARS = ((3, 2, 8), (11, 9, 16), (19, 5, 24), (7, 13, 8), (15, 0, 16), (22, 11, 8))


def _galaxy_ship(s, x, y):
    """A tiny fighter: pointed nose, swept wings and an orange engine glow."""
    s.set_at((x + 2, y), (255, 255, 255))
    s.fill(GALAXY_CYAN, (x + 1, y + 1, 3, 2))
    s.fill(GALAXY_CYAN, (x, y + 2, 5, 1))
    s.set_at((x, y + 3), GALAXY_CYAN)
    s.set_at((x + 4, y + 3), GALAXY_CYAN)
    s.set_at((x + 2, y + 1), (60, 110, 230))
    s.set_at((x + 2, y + 3), GALAXY_ORANGE)


def _galaxy_drone(s, x, y, color):
    """A tiny saucer drone with a glowing eye."""
    s.fill(color, (x, y + 1, 5, 1))
    s.fill(color, (x + 1, y, 3, 1))
    s.set_at((x + 2, y), (130, 255, 150))
    s.set_at((x + 1, y + 2), color)
    s.set_at((x + 3, y + 2), color)


def screen_galaxy(s, p, accent, neon):
    """Endless starfield, a marching formation of alien drones and the fighter firing upwards."""
    s.fill((12, 8, 38))
    for sx, sy, speed in _GALAXY_STARS:
        s.set_at((sx, int(sy + p * 2.0 * speed) % 16), (200, 190, 255))
    sway = int(math.sin(p * math.tau) * 3)
    for row in range(2):
        for col in range(4):
            _galaxy_drone(s, 3 + col * 5 + sway, 1 + row * 3, GALAXY_VIOLET if row else (255, 100, 200))
    sx = 9 + int(math.sin(p * math.tau * 2) * 7)
    _galaxy_ship(s, sx, 12)
    shot = 11 - int(p * 4 * 14) % 12
    s.fill(GALAXY_CYAN, (sx + 2, shot, 1, 2))


def marquee_galaxy(s, r, label, frame, neon, accent):
    _ticker(s, r, label, frame, "galaxy", GALAXY_CYAN, GALAXY_ORANGE, scale_color(GALAXY_VIOLET, 0.5))


def decorate_galaxy(s, frame, n, neon, accent):
    """The lower door is a window onto space: stars, a drone drifting past and the fighter below."""
    d = DOOR
    s.fill((8, 6, 30), d)
    for i, (sx, sy) in enumerate(((3, 2), (9, 8), (15, 4), (21, 10), (6, 11), (18, 1))):
        s.set_at((d.x + sx, d.y + (sy + frame * (1 + i % 2) // 8) % (d.h - 3)), (200, 190, 255))
    u = frame / n
    _galaxy_drone(s, d.x + 4 + int((1 - abs(2 * u - 1)) * (d.w - 12)), d.y + 3, (255, 100, 200))
    _galaxy_ship(s, d.centerx - 2, d.bottom - 6)
    s.fill(GALAXY_CYAN, (d.centerx, d.bottom - 10 - (frame * 2) % 8, 1, 2))
    s.fill((6, 4, 14), (d.centerx - 1, d.bottom - 1, 3, 1))
    _bezel_leds(s, frame, n, GALAXY_CYAN, GALAXY_ORANGE, scale_color(GALAXY_VIOLET, 0.6))


# ----------------------------------------------------------------- Retro Racer
RACER_RED = (255, 64, 80)
RACER_BLUE = (70, 150, 255)
RACER_PURPLE = (150, 80, 255)
CHARCOAL = (30, 32, 44)
CHARCOAL_SIDE = (46, 48, 68)
ASPHALT = (44, 46, 64)


def screen_racer(s, p, accent, neon):
    """Sunset over a perspective road: scrolling rumble strips and lane dashes, rivals, the player's car."""
    horizon = 6
    for y in range(horizon):                                       # synthwave sky: purple -> red
        s.fill(mix_color((40, 18, 96), (255, 70, 90), y / horizon), (0, y, 24, 1))
    pygame.draw.circle(s, (255, 150, 70), (12, horizon), 4)         # sun, cut by the horizon
    s.fill((22, 14, 44), (0, horizon, 24, 16 - horizon))
    for x in (1, 3, 4, 19, 20, 22):                                 # skyline silhouette
        s.fill((20, 12, 52), (x, horizon - 2 - x % 2, 1, 2 + x % 2))
    for y in range(horizon, 16):
        d = y - horizon + 1
        half = 1 + int(d * 1.15)
        z = 1.0 / (d + 0.6)
        stripe = ((z * 5 + p * 8) % 1.0) < 0.5                      # bands that rush towards the player
        s.fill(ASPHALT if stripe else (36, 38, 54), (12 - half, y, half * 2, 1))
        edge = RACER_RED if stripe else (240, 240, 250)
        s.fill(edge, (12 - half - 1, y, 1, 1))
        s.fill(edge, (12 + half, y, 1, 1))
        if ((z * 4 + p * 8) % 1.0) < 0.45 and d > 1:                # lane dashes
            s.fill((255, 226, 90), (11, y, 2, 1))
    for lane, phase, color in ((-0.45, 0.0, RACER_BLUE), (0.4, 0.5, RACER_PURPLE)):   # rival cars
        y = horizon + 1 + int(((p * 1.0 + phase) % 1.0) * 8)
        d = y - horizon + 1
        w = 1 + d // 3
        x = 12 + int(lane * (1 + d * 1.15)) - w // 2
        s.fill(color, (x, y - w // 2, w, max(1, w // 2 + 1)))
        s.fill((255, 230, 230), (x, y, 1, 1))
    cx = 12 + int(math.sin(p * math.tau) * 2) - 3                   # the player's car, swaying
    s.fill((70, 74, 100), (cx, 11, 7, 1))                           # spoiler
    s.fill(RACER_RED, (cx, 12, 7, 2))
    s.fill((120, 20, 40), (cx, 14, 7, 1))
    bright = int(p * 12) % 4 != 3
    for tx in (cx, cx + 5):
        s.fill((255, 235, 210) if bright else (150, 24, 44), (tx, 12, 2, 1))
    s.fill((10, 10, 16), (cx - 1, 13, 1, 2))
    s.fill((10, 10, 16), (cx + 7, 13, 1, 2))
    for i in range(3):                                              # tiny speed LEDs
        s.set_at((1 + i * 2, 1), RACER_BLUE if int(p * 12) % 3 >= i else (30, 40, 90))


def marquee_racer(s, r, label, frame, neon, accent):
    """RETRO RACER in red-hot letters, scrolling, with red/blue chase lights."""
    _ticker(s, r, label, frame, "racer", (255, 96, 110), RACER_BLUE, scale_color(RACER_RED, 0.55))


def decorate_racer(s, frame, n, neon, accent):
    d = DOOR
    u = frame / n
    s.fill((16, 18, 28), d)
    # headlights (flash-to-pass) in the top corners of the door
    on = int(u * 8) % 2 == 0
    for x in (d.x + 2, d.right - 5):
        s.fill((230, 250, 255) if on else (50, 70, 110), (x, d.y + 1, 3, 2))
        if on:
            s.fill((120, 190, 255), (x - 1, d.y + 1, 1, 2))
            s.fill((120, 190, 255), (x + 3, d.y + 1, 1, 2))
    # a pixel sports car seen from behind, with neon underglow
    x0, y0 = d.centerx - 8, d.y + 4
    s.fill(scale_color(RACER_BLUE, 0.55), (x0 - 1, y0 + 8, 20, 1))              # underglow
    s.fill((70, 74, 100), (x0 + 1, y0, 16, 1))                                    # spoiler
    s.fill((70, 74, 100), (x0 + 3, y0 + 1, 1, 1))
    s.fill((70, 74, 100), (x0 + 14, y0 + 1, 1, 1))
    s.fill((22, 34, 86), (x0 + 4, y0 + 1, 10, 2))                                 # rear glass
    s.fill((90, 130, 220), (x0 + 5, y0 + 1, 3, 1))
    s.fill(RACER_RED, (x0, y0 + 3, 18, 4))                                        # body
    s.fill((255, 130, 150), (x0 + 2, y0 + 3, 14, 1))
    s.fill((128, 20, 44), (x0, y0 + 6, 18, 1))
    bright = int(u * 24) % 4 != 3                                                 # tail lights flicker
    for tx in (x0 + 1, x0 + 13):
        s.fill((255, 235, 210) if bright else (160, 24, 44), (tx, y0 + 3, 4, 2))
        s.fill(RACER_RED if bright else (90, 12, 30), (tx, y0 + 5, 4, 1))
    s.fill((240, 240, 250), (x0 + 7, y0 + 4, 4, 2))                               # plate
    s.fill((60, 70, 160), (x0 + 8, y0 + 5, 2, 1))
    for tx in (x0 - 1, x0 + 17):
        s.fill((8, 8, 14), (tx, y0 + 5, 2, 3))                                    # tyres
    flame = (170, 220, 255) if frame % 2 else RACER_BLUE
    s.fill(flame, (x0 + 4, y0 + 7, 1, 1))
    s.fill(flame, (x0 + 13, y0 + 7, 1, 1))
    # LED strips down both cabinet edges
    led = frame * 18 // n
    for y in range(14, H_BODY_END):
        if (y - led) % 6 in (0, 1):
            for x, color in ((0, RACER_BLUE), (W_BODY - 1, RACER_BLUE)):
                s.set_at((x, y), color)

    _bezel_leds(s, frame, n, RACER_RED, RACER_BLUE, (60, 60, 110))
    # control panel: a little steering wheel in place of the joystick
    s.fill((46, 34, 80), (6, 33, 7, 7))
    s.fill((80, 70, 110), (9, 38, 1, 2))
    pygame.draw.circle(s, RACER_RED, (9, 36), 3, 1)
    tilt = round(math.sin(u * math.tau * 2) * 1.5)
    pygame.draw.line(s, (240, 240, 250), (6, 36 + tilt), (12, 36 - tilt))
    s.set_at((9, 36), (255, 226, 90))
    # checkered flag along the kick plate, scrolling
    shift = frame * 8 // n
    for x in range(W_BODY):
        for row in range(2):
            s.set_at((x, H_BODY_END + 1 + row), (240, 240, 250) if ((x + shift) // 2 + row) % 2 == 0 else (16, 16, 24))


def headroom_racer(s, pad, frame, neon, accent):
    """A rear wing on top of the cabinet, its centre brake light pulsing."""
    s.fill((70, 74, 100), (3, pad - 2, 30, 1))
    s.fill(RACER_RED, (3, pad - 3, 30, 1))
    for x in (3, 32):
        s.fill((70, 74, 100), (x, pad - 3, 1, 4))
    on = (frame // 6) % 2 == 0
    s.fill((255, 235, 210) if on else (150, 24, 44), (16, pad - 2, 4, 1))
    s.fill(CHARCOAL_SIDE, (6, pad - 1, 2, 1))
    s.fill(CHARCOAL_SIDE, (28, pad - 1, 2, 1))


def mix_color(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# ----------------------------------------------------------------- Neon Cat Maze
MAZE_CYAN = (70, 235, 255)
MAZE_PURPLE = (190, 100, 255)
MAZE_BODY, MAZE_SIDE = (62, 32, 112), (38, 20, 76)
_MAZE_LOOP = (2, 2, 21, 13)                 # the corridor loop on the 24x16 attract screen: x0, y0, x1, y1
_MAZE_LAP = 2 * ((21 - 2) + (13 - 2))       # 60 steps round it
_MAZE_NIP = 49                              # where the catnip sits on the loop (the bottom-left corner)


def _maze_pos(d):
    """The pixel `d` steps along the corridor loop (clockwise from the top-left corner)."""
    x0, y0, x1, y1 = _MAZE_LOOP
    w, h = x1 - x0, y1 - y0
    d %= _MAZE_LAP
    if d < w:
        return x0 + d, y0
    if d < w + h:
        return x1, y0 + d - w
    if d < 2 * w + h:
        return x1 - (d - w - h), y1
    return x0, y1 - (d - 2 * w - h)


def _tiny_cat(s, x, y, glow):
    s.fill((255, 176, 96), (x - 1, y - 1, 3, 3))
    s.set_at((x - 1, y - 2), (255, 176, 96))
    s.set_at((x + 1, y - 2), (255, 176, 96))
    s.set_at((x, y), (40, 240, 255))
    if glow:
        for dx, dy in ((-2, -1), (2, -1), (-2, 1), (2, 1), (0, 2), (0, -3)):
            s.set_at((x + dx, y + dy), (130, 255, 160))


def _tiny_robot(s, x, y, scared, flash):
    body = (255, 255, 255) if scared and flash else (70, 110, 255) if scared else (255, 70, 110)
    s.fill(body, (x - 1, y - 1, 3, 3))
    s.set_at((x, y - 2), body)
    s.set_at((x, y), (255, 255, 255) if scared and not flash else (255, 240, 120))


def screen_maze(s, p, accent, neon):
    """A tiny maze: the cat runs the corridor eating fish with a robot on its tail, grabs the glowing catnip, the
    robot turns blue and flees - and gets caught."""
    s.fill((10, 6, 30))
    x0, y0, x1, y1 = _MAZE_LOOP
    wall = scale_color(MAZE_CYAN, 0.55)
    pygame.draw.rect(s, wall, (x0 - 2, y0 - 2, x1 - x0 + 5, y1 - y0 + 5), 1)           # outer wall
    pygame.draw.rect(s, wall, (x0 + 2, y0 + 2, x1 - x0 - 3, y1 - y0 - 3), 1)           # the block inside the loop
    s.fill(wall, (x0 + 7, y0 + 5, 5, 1))
    cat_d = p * 2 * _MAZE_LAP
    lap = cat_d % _MAZE_LAP
    for d in range(3, _MAZE_LAP, 4):                                                    # fish treats along the path
        if d != _MAZE_NIP and d >= lap:
            x, y = _maze_pos(d)
            s.set_at((x, y), PINK_FISH if (d // 4) % 3 else Col.YELLOW)
    nip = _MAZE_NIP / (2 * _MAZE_LAP)
    if p < nip:                                                                          # the catnip, pulsing
        x, y = _maze_pos(_MAZE_NIP)
        k = (1.0, 0.6)[int(p * 24) % 2]
        s.fill(scale_color((130, 255, 160), k), (x - 1, y - 1, 3, 3))
        s.set_at((x, y), (255, 255, 255))
    glow = p >= nip
    cx, cy = _maze_pos(cat_d)
    _tiny_cat(s, cx, cy, glow)
    if p < nip:
        rx, ry = _maze_pos(cat_d - 12)
        _tiny_robot(s, rx, ry, False, False)
    else:
        flee = _MAZE_NIP - 12 - (cat_d - _MAZE_NIP)
        if p < 0.6:
            rx, ry = _maze_pos(flee)
            _tiny_robot(s, rx, ry, True, p > 0.52 and int(p * 40) % 2 == 0)
        elif p < 0.68:                                                                   # caught: a little burst
            rx, ry = _maze_pos(_MAZE_NIP - 12 - (0.6 * 2 * _MAZE_LAP - _MAZE_NIP))
            r = int((p - 0.6) * 40)
            for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r)):
                s.set_at((rx + dx, ry + dy), Col.YELLOW)


PINK_FISH = (255, 130, 200)


def marquee_maze(s, r, label, frame, neon, accent):
    """A scrolling CAT MAZE in neon cyan, with a purple chase-light rail above and below."""
    _ticker(s, r, label, frame, "maze", MAZE_CYAN, MAZE_PURPLE, scale_color(MAZE_PURPLE, 0.4))


def decorate_maze(s, frame, n, neon, accent):
    """The lower door is a maze map: a winding path whose LEDs chase along it, glowing fish and a coin slot."""
    d = DOOR
    s.fill((14, 8, 36), d)
    path = [(3, 2), (3, 3), (3, 4), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5), (7, 4), (7, 3), (7, 2), (8, 2), (9, 2), (10, 2),
            (11, 2), (12, 2), (12, 3), (12, 4), (12, 5), (13, 5), (14, 5), (15, 5), (16, 5), (17, 5), (18, 5), (18, 4),
            (18, 3), (18, 2), (19, 2), (20, 2), (21, 2), (22, 2)]
    head = frame * len(path) // n
    for i, (px, py) in enumerate(path):
        lit = (i - head) % 8 == 0
        dist = (i - head) % 8
        colour = Col.YELLOW if lit else MAZE_CYAN if dist in (1, 7) else scale_color(MAZE_CYAN, 0.28)
        s.set_at((d.x + px, d.y + py), colour)
    for fx, fy in ((6, 8), (14, 8), (21, 8)):                                           # glowing fish symbols
        bright = (frame + fx) % 4 < 2
        body = PINK_FISH if bright else scale_color(PINK_FISH, 0.5)
        s.fill(body, (d.x + fx, d.y + fy, 3, 2))
        s.set_at((d.x + fx + 3, d.y + fy - 1), body)
        s.set_at((d.x + fx + 3, d.y + fy + 2), body)
        s.set_at((d.x + fx, d.y + fy), (255, 255, 255) if bright else body)
    s.fill((6, 4, 14), (d.centerx - 1, d.bottom - 1, 3, 1))
    s.fill(MAZE_PURPLE, (d.centerx - 2, d.bottom - 2, 5, 1))
    _bezel_leds(s, frame, n, MAZE_CYAN, MAZE_PURPLE, scale_color(MAZE_PURPLE, 0.5))


def headroom_maze(s, pad, frame, neon, accent):
    """Tall cat ears on the marquee housing: cyan-lined, pink inside, an LED at each tip, one ear flicking now and then."""
    flick = 1 if frame == 3 else 0
    for tip_x, base_x0, base_x1, ear_flick in ((5, 1, 11, 0), (30 + flick, 25, 35, flick)):
        tip_y = pad - 6 + (1 if ear_flick else 0)
        pts = [(base_x0, pad), (tip_x, tip_y), (base_x1, pad)]
        pygame.draw.polygon(s, MAZE_BODY, pts)
        pygame.draw.polygon(s, MAZE_CYAN, pts, 1)
        inner = [(base_x0 + 3, pad - 1), (tip_x, tip_y + 3), (base_x1 - 3, pad - 1)]
        pygame.draw.polygon(s, CAT_PINK, inner)
        s.set_at((tip_x, tip_y), Col.YELLOW if frame % 2 == 0 else (255, 255, 255))
    s.fill(MAZE_CYAN, (1, pad, 10, 1))
    s.fill(MAZE_CYAN, (25, pad, 10, 1))


# ----------------------------------------------------------------- registry
SCREEN_PAINTERS = {"cat": screen_cat, "volley": screen_volley, "racer": screen_racer, "galaxy": screen_galaxy,
                   "maze": screen_maze}
MARQUEES = {"cat": marquee_cat, "volley": marquee_volley, "racer": marquee_racer, "galaxy": marquee_galaxy,
            "maze": marquee_maze}
BODY_DECORATORS = {"cat": lambda s, f, n, neon, accent: decorate_cat(s, f, neon, accent),
                   "volley": decorate_volley, "racer": decorate_racer, "galaxy": decorate_galaxy,
                   "maze": decorate_maze}
BODY_COLORS = {"racer": (CHARCOAL, CHARCOAL_SIDE), "maze": (MAZE_BODY, MAZE_SIDE)}   # cabinet body / side colours where not the default
HEADROOM = {"cat": (5, headroom_cat), "racer": (4, headroom_racer), "maze": (6, headroom_maze)}              # style -> (extra rows above the cabinet, painter)
