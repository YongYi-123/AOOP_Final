"""Pixel art and the board-to-screen projection for NEON COIN PUSHER (drawing helpers only).

The physics board is top-down; the picture is tilted a little: the back of the stage is a bit
narrower and shorter than the front (a pseudo-perspective), so coins read as flattened discs.
"""

import pygame

import coin_pusher as cp
from gfx import scale_color, shade

# ---- screen layout (canvas pixels; the canvas is 400 x 300)
CX = 200                    # the stage's centre line
K = 1.75                    # horizontal pixels per board unit at the front
S0 = 0.78                   # the back of the stage is drawn at this fraction of the front's scale
PY0, PY1 = 78, 190          # screen y of the back wall and of the front edge
CABINET = pygame.Rect(36, 4, 328, 292)
CHUTE_Y = 66                # the rail the coin chute slides on
TRAY_TOP = PY1 + 4

_NORM = S0 * 1.0 + (1 - S0) / 2     # integral of the scale, to normalise the depth mapping

NAVY, VIOLET, VIOLET_DARK = (14, 12, 44), (58, 40, 130), (30, 22, 78)
GLASS = (80, 240, 255)
PINK = (255, 120, 200)
GOLD = (255, 206, 84)

PALETTE = {
    cp.NORMAL: {"face": (255, 208, 84), "rim": (150, 96, 24), "edge": (206, 140, 40), "hi": (255, 244, 176)},
    cp.SILVER: {"face": (216, 226, 240), "rim": (96, 110, 140), "edge": (150, 166, 192), "hi": (255, 255, 255)},
    cp.GOLDEN: {"face": (255, 226, 110), "rim": (190, 100, 30), "edge": (236, 150, 50), "hi": (255, 255, 220)},
    cp.MYSTERY: {"face": (156, 100, 255), "rim": (62, 34, 140), "edge": (104, 64, 200), "hi": (226, 200, 255)},
}


def depth_scale(y):
    """Horizontal scale (pixels per board unit) at board depth y."""
    z = max(0.0, min(1.2, y / cp.D))
    return K * (S0 + (1 - S0) * z)


def project(x, y):
    """(screen x, screen y, scale) of the board point (x, y)."""
    z = y / cp.D
    g = (S0 * z + (1 - S0) * z * z / 2) / _NORM
    return CX + (x - cp.W / 2) * depth_scale(y), PY0 + (PY1 - PY0) * g, depth_scale(y)


def coin_diameter(y):
    return 2 * cp.R * depth_scale(y)


_SPRITES = {}
_QMARK = ("111", "001", "011", "000", "010")


def coin_sprite(kind, diameter):
    """A flattened coin of about `diameter` pixels wide (cached per kind and size)."""
    d = max(10, min(22, int(round(diameter))))
    key = (kind, d)
    sprite = _SPRITES.get(key)
    if sprite is None:
        sprite = _SPRITES[key] = _build_coin(kind, d)
    return sprite


def _build_coin(kind, d):
    pal = PALETTE[kind]
    h = round(d * 0.72)
    thick = 2 if d >= 14 else 1
    s = pygame.Surface((d, h + thick), pygame.SRCALPHA)
    body = pygame.Rect(0, 0, d, h)
    pygame.draw.ellipse(s, pal["rim"], body.move(0, thick))                    # the coin's edge, seen from slightly above
    pygame.draw.ellipse(s, pal["edge"], body.move(0, thick - 1))
    pygame.draw.ellipse(s, pal["rim"], body)
    face = body.inflate(-2, -2)
    pygame.draw.ellipse(s, pal["face"], face)
    inner = face.inflate(-max(2, d // 4), -max(2, d // 5))
    if kind == cp.NORMAL:
        pygame.draw.ellipse(s, shade(pal["face"], -0.18), inner, 1)           # a stamped ring
    elif kind == cp.SILVER:
        pygame.draw.ellipse(s, shade(pal["face"], -0.2), inner, 1)
        if d >= 14:                                                           # a star: a plus of lit pixels
            cx, cy = face.centerx, face.centery
            for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                s.set_at((cx + dx, cy + dy), (120, 134, 170))
    elif kind == cp.GOLDEN:
        pygame.draw.ellipse(s, (255, 170, 60), inner, 1)
        ear = PINK
        for ex in (face.left + 1, face.right - 4):                           # pink cat ears on the rim
            pygame.draw.polygon(s, ear, [(ex, face.top + 2), (ex + 1, face.top - 1), (ex + 3, face.top + 2)])
        cx, cy = face.centerx, face.centery
        for dx in (-2, 2):
            s.set_at((cx + dx, cy - 1), (80, 30, 10))                         # eyes
        s.set_at((cx, cy), PINK)                                              # nose
        if d >= 17:
            s.set_at((cx - 1, cy + 1), (80, 30, 10))
            s.set_at((cx + 1, cy + 1), (80, 30, 10))
    else:
        gx, gy = face.centerx - 1, face.centery - 2                           # a "?" glyph
        for row, bits in enumerate(_QMARK):
            for col, bit in enumerate(bits):
                if bit == "1":
                    s.set_at((gx + col, gy + row), (255, 250, 255))
    s.set_at((face.left + 2, face.top + 1), pal["hi"])                       # glint
    if d >= 14:
        s.set_at((face.left + 3, face.top + 1), pal["hi"])
    return s


# ------------------------------------------------------------------ static scenery
def build_background():
    """The room behind the cabinet: deep navy with soft neon stripes."""
    from settings import VIEW_H, VIEW_W
    bg = pygame.Surface((VIEW_W, VIEW_H))
    for y in range(VIEW_H):
        k = y / VIEW_H
        bg.fill((int(10 + 14 * k), int(8 + 6 * k), int(30 + 26 * k)), (0, y, VIEW_W, 1))
    for x in range(-VIEW_H, VIEW_W, 28):                                      # faint diagonal wallpaper
        pygame.draw.line(bg, (20, 16, 52), (x, 0), (x + VIEW_H, VIEW_H))
    return bg


def build_cabinet():
    """The casing, marquee backing, glass stage floor, walls and loss chutes (everything static)."""
    from settings import VIEW_H, VIEW_W
    s = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    cab = CABINET
    pygame.draw.rect(s, VIOLET_DARK, cab, border_radius=6)
    pygame.draw.rect(s, NAVY, cab.inflate(-8, -8), border_radius=5)
    pygame.draw.rect(s, GLASS, cab, 1, border_radius=6)                        # cyan glass edge
    pygame.draw.rect(s, scale_color(GLASS, 0.45), cab.inflate(-4, -4), 1, border_radius=5)
    for ex in (cab.left + 14, cab.right - 14):                                # the pink cat ears
        pygame.draw.polygon(s, PINK, [(ex - 12, cab.top + 4), (ex, cab.top - 3), (ex + 12, cab.top + 4)])
        pygame.draw.polygon(s, (120, 40, 110), [(ex - 6, cab.top + 4), (ex, cab.top + 1), (ex + 6, cab.top + 4)])
    # the glass stage floor: a trapezoid between the back wall and the front edge
    back_l, back_r = project(0, 0), project(cp.W, 0)
    front_l, front_r = project(0, cp.D), project(cp.W, cp.D)
    floor = [(back_l[0], back_l[1]), (back_r[0], back_r[1]), (front_r[0], front_r[1]), (front_l[0], front_l[1])]
    pygame.draw.polygon(s, (16, 12, 52), floor)
    for i in range(1, 12):                                                     # lane lines in perspective
        x = cp.W * i / 12
        a, b = project(x, 0), project(x, cp.D)
        pygame.draw.line(s, (26, 22, 76), (a[0], a[1]), (b[0], b[1]))
    for yy in range(8, int(cp.D), 12):
        a, b = project(0, yy), project(cp.W, yy)
        pygame.draw.line(s, (24, 20, 70), (a[0], a[1]), (b[0], b[1]))
    # solid side walls up to SIDE_Y, open loss chutes beyond
    for side, x in ((-1, 0), (1, cp.W)):
        a, b, c = project(x, 0), project(x, cp.SIDE_Y), project(x, cp.D)
        wall = [(a[0], a[1]), (b[0], b[1]), (b[0] + side * 7, b[1] + 3), (a[0] + side * 5, a[1] - 4)]
        pygame.draw.polygon(s, VIOLET, wall)
        pygame.draw.line(s, GLASS, (a[0], a[1]), (b[0], b[1]), 2)
        pygame.draw.line(s, shade(VIOLET, 0.4), (a[0] + side * 3, a[1] - 2), (b[0] + side * 3, b[1] + 1))
        chute = [(b[0], b[1]), (c[0], c[1]), (c[0] + side * 26, c[1] + 12), (b[0] + side * 22, b[1] + 3)]
        pygame.draw.polygon(s, (30, 8, 36), chute)                             # the dark loss chute
        pygame.draw.line(s, (255, 70, 120), (b[0], b[1]), (c[0], c[1]), 1)
        mx, my = (b[0] + c[0]) / 2 + side * 11, (b[1] + c[1]) / 2 + 4
        pygame.draw.polygon(s, (255, 70, 120), [(mx - 3, my - 2), (mx + 3, my - 2), (mx, my + 3)])
    return s


def build_front():
    """The front glass lip and the payout tray (drawn over the coins that fall past it)."""
    from settings import VIEW_H, VIEW_W
    s = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    fl, fr = project(0, cp.D), project(cp.W, cp.D)
    tray = pygame.Rect(int(fl[0]) - 4, PY1 + 1, int(fr[0] - fl[0]) + 8, 24)
    pygame.draw.rect(s, (10, 6, 30), tray, border_radius=3)
    pygame.draw.rect(s, (36, 120, 160), tray, 1, border_radius=3)
    s.fill((22, 70, 100), (tray.x + 2, tray.bottom - 6, tray.w - 4, 4))
    lip = [(fl[0] - 6, PY1 - 1), (fr[0] + 6, PY1 - 1), (fr[0] + 4, PY1 + 3), (fl[0] - 4, PY1 + 3)]
    pygame.draw.polygon(s, GLASS, lip)
    pygame.draw.line(s, (220, 255, 255), (fl[0] - 5, PY1 - 1), (fr[0] + 5, PY1 - 1))
    return s


def build_glass():
    """Soft reflections over the whole stage (drawn last, very faint)."""
    from settings import VIEW_H, VIEW_W
    s = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    for i, (x0, w) in enumerate(((84, 16), (120, 6), (270, 10))):
        poly = [(x0, PY0 - 4), (x0 + w, PY0 - 4), (x0 + w - 36, PY1 + 2), (x0 - 36, PY1 + 2)]
        pygame.draw.polygon(s, (200, 240, 255, 16 - i * 3), poly)
    return s


def draw_pusher(surf, face, t):
    """The pusher: a violet plate from the back wall to its face, with a lit cyan lip and a paw."""
    bl, br = project(0, 0), project(cp.W, 0)
    fl, fr = project(0, face), project(cp.W, face)
    plate = [(bl[0], bl[1]), (br[0], br[1]), (fr[0], fr[1]), (fl[0], fl[1])]
    pygame.draw.polygon(surf, (74, 50, 160), plate)
    for i in range(1, 5):                                                      # grooves that slide with the plate
        yy = face * i / 5
        a, b = project(0, yy), project(cp.W, yy)
        pygame.draw.line(surf, (60, 40, 132), (a[0], a[1]), (b[0], b[1]))
    cx, cy, sc = project(cp.W / 2, face * 0.45)
    paw = (255, 150, 214)
    pygame.draw.ellipse(surf, paw, (cx - 6, cy - 2, 12, 7))                   # a pink paw print
    for dx in (-8, -3, 3, 8):
        pygame.draw.ellipse(surf, paw, (cx + dx - 2, cy - 7 - (1 if abs(dx) < 5 else 0), 4, 4))
    lip_a, lip_b = project(0, face), project(cp.W, face)
    h = max(3, int(5 * depth_scale(face) / K))
    pygame.draw.polygon(surf, (150, 230, 255), [(lip_a[0], lip_a[1]), (lip_b[0], lip_b[1]),
                                                (lip_b[0], lip_b[1] + h), (lip_a[0], lip_a[1] + h)])
    pygame.draw.line(surf, (255, 255, 255), (lip_a[0], lip_a[1]), (lip_b[0], lip_b[1]))
    pygame.draw.line(surf, (60, 120, 190), (lip_a[0], lip_a[1] + h), (lip_b[0], lip_b[1] + h))
    for i in range(0, 14):                                                     # chase lights on the lip
        x = lip_a[0] + (lip_b[0] - lip_a[0]) * (i + 0.5) / 14
        lit = int(t * 8) % 3 == i % 3
        surf.fill((255, 120, 220) if lit else (90, 50, 150), (int(x) - 1, int(lip_a[1]) + 1, 2, 1))
