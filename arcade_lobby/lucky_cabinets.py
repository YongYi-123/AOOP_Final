"""Cabinet art for the Lucky Corner: three distinct 28x40 machines (SPIN,
HI-LO, NEON 21) with animated screen previews.

build_cabinet(kind) returns the static sprite (marquee and screen left blank);
draw_marquee / draw_screen paint the animated parts each frame. All three keep
the Lucky Corner footprint, so collision and prompt zones do not change.
"""
import math

import pygame

from font import get_font
from gfx import scale_color, shade
from neon21_art import EMERALD, GOLD, RED_SUIT, suit_icon
from settings import Col

SIZE = (28, 40)
SCREEN = pygame.Rect(4, 10, 20, 14)         # bezel, in sprite coordinates
INNER = SCREEN.inflate(-2, -2)

KINDS = {
    "spin": {"neon": (255, 70, 200), "accent": GOLD, "label": "SPIN"},
    "hilo": {"neon": (80, 240, 255), "accent": (90, 255, 150), "label": "HI-LO"},
    "neon21": {"neon": GOLD, "accent": EMERALD, "label": "NEON"},
}


def build_cabinet(kind):
    spec = KINDS[kind]
    neon, accent = spec["neon"], spec["accent"]
    w, h = SIZE
    s = pygame.Surface(SIZE, pygame.SRCALPHA)
    body = (16, 8, 30) if kind == "neon21" else Col.CABINET
    side = (30, 18, 52) if kind == "neon21" else Col.CABINET_SIDE
    s.fill(side, (0, 8, w, h - 8))
    s.fill(body, (3, 8, w - 6, h - 8))
    s.fill(neon, (0, 8, 1, h - 8))
    s.fill(scale_color(neon, 0.5), (w - 1, 8, 1, h - 8))            # lit left edge, shaded right
    s.fill(shade(body, 0.12), (3, 8, 1, h - 10))                    # bevel highlight
    s.fill(body, (0, 0, w, 9))                                       # marquee box
    s.fill(neon, (0, 0, w, 1))
    s.fill(scale_color(neon, 0.45), (0, 8, w, 1))
    # screen bezel
    s.fill((6, 4, 14), SCREEN)
    pygame.draw.rect(s, scale_color(accent, 0.7), SCREEN, 1)
    s.fill(shade(accent, 0.3), (SCREEN.x, SCREEN.y, 2, 1))           # bezel glint
    # control panel (differs per game)
    s.fill((46, 34, 80), (2, 26, w - 4, 5))
    s.fill(shade((46, 34, 80), 0.2), (2, 26, w - 4, 1))
    if kind == "spin":
        pygame.draw.circle(s, (255, 80, 90), (14, 28), 2)             # big SPIN button
        s.fill((255, 190, 190), (13, 27, 1, 1))
        for x, c in ((6, GOLD), (21, GOLD)):
            s.fill(c, (x, 28, 2, 1))
        for y in range(13, 24, 4):                                    # gold side studs
            s.fill(GOLD, (1, y, 1, 2))
            s.fill(GOLD, (w - 2, y, 1, 2))
        for x, y in ((0, 0), (w - 1, 0)):                              # rounded top corners
            s.set_at((x, y), (0, 0, 0, 0))
        s.set_at((1, 0), scale_color(neon, 0.6))
        s.set_at((w - 2, 0), scale_color(neon, 0.6))
    elif kind == "hilo":
        for x, c, up in ((8, (90, 255, 150), True), (17, (255, 120, 120), False)):
            pygame.draw.polygon(s, c, [(x, 30), (x + 4, 30), (x + 2, 27)] if up else
                                [(x, 27), (x + 4, 27), (x + 2, 30)])
        for y, up in ((12, True), (18, False)):                       # arrow decals on the flanks
            for x in (1, w - 3):
                pts = [(x, y + 2), (x + 2, y + 2), (x + 1, y)] if up else [(x, y), (x + 2, y), (x + 1, y + 2)]
                pygame.draw.polygon(s, neon, pts)
        s.fill(neon, (3, 0, w - 6, 1))
    else:                                                              # neon21
        for i, suit in enumerate("SHDC"):                              # the suit motif on the panel
            color = EMERALD if suit in "SC" else RED_SUIT
            s.blit(suit_icon(suit, color), (3 + i * 6, 26))
        for y in range(10, 38, 3):                                     # emerald side piping
            s.fill(EMERALD, (2, y, 1, 2))
            s.fill(EMERALD, (w - 3, y, 1, 2))
        for x in (0, 1, w - 2, w - 1):                                 # crown-stepped top
            s.set_at((x, 0), (0, 0, 0, 0))
        s.fill(GOLD, (2, 0, w - 4, 1))
        s.fill(shade(GOLD, 0.4), (w // 2 - 1, 0, 2, 1))
    s.fill((18, 12, 34), (6, 33, w - 12, 5))                          # token slot
    s.fill(accent, (12, 35, 4, 1))
    s.fill((10, 6, 20), (0, h - 2, w, 2))
    return s


# ----------------------------------------------------------------- animation
def draw_marquee(surf, kind, origin, t):
    """The marquee text (NEON 21 alternates NEON / 21) and chase lights."""
    spec = KINDS[kind]
    x, y = origin
    font = get_font()
    label = spec["label"]
    if kind == "neon21" and int(t / 1.1) % 2:
        label = "21"
    glow = scale_color(spec["neon"], 0.3 + 0.06 * math.sin(t * 3))
    img = font.render_glow(label, GOLD if kind != "hilo" else (200, 252, 255), glow)
    surf.blit(img, img.get_rect(midtop=(x + SIZE[0] // 2, y)))
    for i in range(5):
        lit = int(t * 6) % 5 == i
        surf.fill(Col.YELLOW if lit else scale_color(spec["neon"], 0.7), (x + 3 + i * 5, y + 8, 2, 1))


def draw_screen(surf, kind, origin, t):
    inner = INNER.move(origin)
    {"spin": _screen_spin, "hilo": _screen_hilo, "neon21": _screen_neon21}[kind](surf, inner, t)


def _screen_spin(surf, inner, t):
    surf.fill((38, 8, 46), inner)
    cx, cy, r = inner.centerx, inner.centery + 1, 5
    colors = ((255, 70, 200), GOLD, (80, 240, 255), (150, 90, 255))
    for i in range(8):
        a0 = t * 2.5 + i * math.pi / 4
        pts = [(cx, cy)] + [(cx + math.cos(a0 + k * math.pi / 16) * r, cy + math.sin(a0 + k * math.pi / 16) * r)
                            for k in range(5)]
        pygame.draw.polygon(surf, colors[i % 4], pts)
    pygame.draw.circle(surf, (20, 8, 30), (cx, cy), 1)
    surf.fill(GOLD, (cx, inner.top, 1, 2))                             # pointer


def _flip(face_from, face_to, k):
    """Which face and what width fraction at flip progress k in 0..1."""
    return (face_from, 1 - 2 * k) if k < 0.5 else (face_to, 2 * k - 1)


def _mini_card(surf, x, y, face, width_frac):
    w = max(1, round(7 * abs(width_frac)))
    rect = pygame.Rect(x + (7 - w) // 2, y, w, 10)
    if face is None:
        surf.fill((70, 36, 150), rect)
        if w > 2:
            surf.fill(scale_color(GOLD, 0.6), rect.inflate(-2, -2).clip(rect))
            surf.fill((70, 36, 150), rect.inflate(-4, -4))
        return
    label, color = face
    surf.fill((248, 242, 255), rect)
    if w >= 5:
        surf.blit(get_font().render(label, color), (rect.x + 1, rect.y + 1))
    surf.fill((20, 10, 40), (rect.x, rect.bottom - 1, rect.w, 1))


def _screen_hilo(surf, inner, t):
    surf.fill((6, 28, 40), inner)
    phase = t % 3.0
    left = ("K", (44, 32, 78))
    right = (("5", RED_SUIT) if phase < 1.5 else ("A", (44, 32, 78)))
    k = min(1.0, (phase % 1.5) / 0.4)
    face, frac = _flip(None, right, k)
    _mini_card(surf, inner.x + 1, inner.y + 1, left, 1)
    _mini_card(surf, inner.x + 8, inner.y + 1, face, frac)
    up = phase >= 1.5                                                  # arrow shows the call
    c = (90, 255, 150) if up else (255, 120, 120)
    ax, ay = inner.right - 2, inner.centery
    pts = [(ax - 1, ay + 1), (ax + 1, ay + 1), (ax, ay - 1)] if up else \
          [(ax - 1, ay - 1), (ax + 1, ay - 1), (ax, ay + 1)]
    if int(t * 4) % 4:
        pygame.draw.polygon(surf, c, pts)


def _screen_neon21(surf, inner, t):
    surf.fill((6, 40, 34), inner)
    surf.fill((10, 58, 48), inner.inflate(-2, -2))
    p = t % 4.8

    def face_at(keys, at):
        """keys: [(start, face)] with each change a 0.4s flip; returns (face, width)."""
        face = None
        for start, new in keys:
            if at >= start + 0.4:
                face = new
            elif at >= start:
                return _flip(face, new, (at - start) / 0.4)
        return face, 1
    a = face_at([(0.0, ("A", (44, 32, 78))), (4.4, None)], p)
    b = face_at([(0.4, ("K", (44, 32, 78))), (2.4, ("7", RED_SUIT)), (4.4, None)], p)
    _mini_card(surf, inner.x + 1, inner.y + 1, *a)
    _mini_card(surf, inner.x + 8, inner.y + 1, *b)
    for i, c in enumerate((GOLD, (255, 90, 170), GOLD)):               # little chip stack
        surf.fill(c, (inner.right - 3, inner.bottom - 2 - i * 2, 2, 1))
    if int(t * 2) % 2:
        surf.set_at((inner.right - 2, inner.top + 2), shade(GOLD, 0.5))   # twinkle
