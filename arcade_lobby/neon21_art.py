"""Pixel art for NEON 21: suit symbols, playing cards and betting chips.
Everything is built once and cached; callers just ask for a surface."""
import pygame

from font import get_font
from gfx import scale_color, shade

CARD_W, CARD_H = 38, 54
CHIP = 15

RED_SUIT = (226, 48, 96)
BLACK_SUIT = (44, 32, 78)
CARD_FACE = (248, 242, 255)
CARD_EDGE = (18, 10, 40)
GOLD = (255, 214, 90)
EMERALD = (60, 230, 150)

_SUIT_7 = {
    "H": "0110110 1111111 1111111 1111111 0111110 0011100 0001000",
    "D": "0001000 0011100 0111110 1111111 0111110 0011100 0001000",
    "S": "0001000 0011100 0111110 1111111 1111111 0001000 0011100",
    "C": "0011100 0011100 1101011 1111111 1101011 0001000 0011100",
}
_SUIT_5 = {
    "H": "01010 11111 11111 01110 00100",
    "D": "00100 01110 11111 01110 00100",
    "S": "00100 01110 11111 00100 01110",
    "C": "01110 11111 01110 00100 01110",
}
_cache = {}


def suit_color(suit):
    return RED_SUIT if suit in ("H", "D") else BLACK_SUIT


def suit_icon(suit, color=None, big=False):
    """A 5x5 (or 7x7) suit symbol."""
    key = ("suit", suit, color, big)
    if key not in _cache:
        rows = (_SUIT_7 if big else _SUIT_5)[suit].split()
        s = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, bit in enumerate(row):
                if bit == "1":
                    s.set_at((x, y), color or suit_color(suit))
        _cache[key] = s
    return _cache[key]


def _face(card):
    s = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    pygame.draw.rect(s, CARD_FACE, s.get_rect(), border_radius=3)
    pygame.draw.rect(s, shade(CARD_FACE, -0.18), s.get_rect().inflate(-4, -4), 1, border_radius=2)
    color = suit_color(card.suit)
    font = get_font()
    s.blit(font.render(card.label, color), (3, 3))
    s.blit(suit_icon(card.suit), (3, 11))
    flipped = pygame.transform.rotate(s.subsurface((3, 3, 12, 14)).copy(), 180)
    s.blit(flipped, (CARD_W - 3 - flipped.get_width(), CARD_H - 3 - flipped.get_height()))
    big = pygame.transform.scale_by(suit_icon(card.suit, big=True), 2)
    s.blit(big, big.get_rect(center=(CARD_W // 2 + 2, CARD_H // 2 + 1)))
    pygame.draw.rect(s, CARD_EDGE, s.get_rect(), 1, border_radius=3)
    return s


def _back():
    s = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    pygame.draw.rect(s, (46, 20, 104), s.get_rect(), border_radius=3)
    inner = s.get_rect().inflate(-6, -6)
    pygame.draw.rect(s, (28, 12, 70), inner, border_radius=2)
    for y in range(inner.top + 1, inner.bottom - 1, 4):          # diamond lattice
        for x in range(inner.left + 1, inner.right - 1, 4):
            if ((x - inner.left) // 4 + (y - inner.top) // 4) % 2 == 0:
                s.fill(scale_color(GOLD, 0.55), (x + 1, y + 1, 2, 2))
    pygame.draw.rect(s, GOLD, inner, 1, border_radius=2)
    pygame.draw.rect(s, CARD_EDGE, s.get_rect(), 1, border_radius=3)
    return s


def card_surface(card, face_up=True, width=None):
    """The card (or its back), optionally squeezed to `width` pixels for a flip."""
    key = ("card", card.rank, card.suit, face_up) if face_up else ("back",)
    if key not in _cache:
        _cache[key] = _face(card) if face_up else _back()
    img = _cache[key]
    if width is not None and int(width) != CARD_W:
        img = pygame.transform.scale(img, (max(2, int(width)), CARD_H))
    return img


CHIP_COLORS = {1: (230, 236, 255), 2: (255, 90, 170), 5: (70, 220, 140), 10: GOLD}


def chip_surface(value, dim=False):
    key = ("chip", value, dim)
    if key not in _cache:
        color = CHIP_COLORS.get(value, GOLD)
        if dim:
            color = scale_color(color, 0.4)
        s = pygame.Surface((CHIP, CHIP), pygame.SRCALPHA)
        c = CHIP // 2
        pygame.draw.circle(s, scale_color(color, 0.55), (c, c + 1), c)         # thickness
        pygame.draw.circle(s, color, (c, c), c)
        pygame.draw.circle(s, shade(color, 0.55), (c, c), c, 1)
        for dx, dy in ((0, -6), (5, -4), (6, 0), (5, 4), (0, 6), (-5, 4), (-6, 0), (-5, -4)):   # edge stripes
            s.fill(CARD_FACE if not dim else scale_color(CARD_FACE, 0.4), (c + dx, c + dy, 1, 1))
        pygame.draw.circle(s, shade(color, 0.6), (c, c), 5)                      # light face for the number
        label = get_font().render(str(value), (28, 14, 60) if not dim else (40, 30, 70))
        s.blit(label, label.get_rect(center=(c, c)))
        _cache[key] = s
    return _cache[key]


def chips_for(amount, denominations=(10, 5, 2, 1)):
    """Greedy chip breakdown of an amount, biggest first: 17 -> [10, 5, 2]."""
    out = []
    for d in denominations:
        while amount >= d:
            out.append(d)
            amount -= d
    return out
