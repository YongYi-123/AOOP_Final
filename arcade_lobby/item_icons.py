"""Pixel icons for items, painted from an ItemDefinition's `icon` data.
Each shape is a small function; icons are cached per (shape, colours)."""
import pygame

from gfx import outlined, shade
from settings import Col

SIZE = 14


def _sticker(s, c, a):
    pygame.draw.circle(s, c, (7, 7), 6)
    pygame.draw.circle(s, a, (7, 7), 6, 1)
    s.fill(a, (4, 4, 2, 2))                          # ears-and-eyes cat face
    s.fill(a, (9, 4, 2, 2))
    s.fill(Col.OUTLINE, (5, 7, 1, 1))
    s.fill(Col.OUTLINE, (8, 7, 1, 1))
    s.fill(shade(c, -0.4), (6, 9, 2, 1))


def _cap(s, c, a):
    pygame.draw.ellipse(s, c, (1, 3, 12, 9))
    s.fill((0, 0, 0, 0), (0, 8, 14, 6))
    s.fill(c, (1, 8, 12, 2))
    s.fill(a, (1, 9, 12, 1))
    s.fill(shade(c, -0.35), (9, 10, 5, 2))           # brim
    s.fill(a, (6, 3, 2, 1))


def _ticket(s, c, a):
    s.fill(c, (0, 3, 14, 8))
    s.fill(shade(c, 0.5), (1, 4, 12, 2))
    for x in (0, 13):
        s.fill((0, 0, 0, 0), (x, 6, 1, 2))
    for y in range(4, 11, 2):
        s.fill(a, (9, y, 1, 1))
    s.fill(a, (3, 7, 4, 1))


def _badge(s, c, a):
    pygame.draw.polygon(s, a, [(7, 0), (13, 4), (11, 13), (3, 13), (1, 4)])
    pygame.draw.polygon(s, c, [(7, 2), (11, 5), (10, 11), (4, 11), (3, 5)])
    s.fill(shade(c, 0.6), (6, 5, 2, 3))


def _unknown(s, c, a):
    s.fill(Col.TEXT_MUTED, (1, 1, 12, 12))
    s.fill(Col.PANEL, (2, 2, 10, 10))
    s.fill(Col.TEXT_MUTED, (6, 4, 2, 2))
    s.fill(Col.TEXT_MUTED, (6, 7, 2, 3))


def _lamp(s, c, a):
    pygame.draw.polygon(s, c, [(4, 1), (9, 1), (12, 7), (1, 7)])
    s.fill(shade(c, 0.5), (5, 2, 2, 3))
    s.fill(a, (6, 7, 2, 4))
    s.fill(shade(a, -0.4), (3, 11, 8, 2))


def _plush(s, c, a):
    pygame.draw.circle(s, c, (7, 8), 5)
    s.fill(c, (2, 2, 3, 3))
    s.fill(c, (9, 2, 3, 3))
    s.fill(a, (3, 3, 1, 1))
    s.fill(a, (10, 3, 1, 1))
    s.fill(Col.OUTLINE, (5, 7, 1, 2))
    s.fill(Col.OUTLINE, (8, 7, 1, 2))
    s.fill(a, (6, 10, 2, 1))


def _plant(s, c, a):
    pygame.draw.ellipse(s, c, (3, 0, 8, 8))
    pygame.draw.ellipse(s, shade(c, 0.35), (5, 1, 3, 4))
    s.fill(c, (1, 5, 4, 3))
    s.fill(c, (9, 5, 4, 3))
    s.fill(a, (3, 9, 8, 4))
    s.fill(shade(a, 0.3), (3, 9, 8, 1))


def _clock(s, c, a):
    pygame.draw.circle(s, c, (7, 7), 6)
    pygame.draw.circle(s, (20, 14, 40), (7, 7), 4)
    s.fill(a, (7, 4, 1, 4))
    s.fill(a, (7, 7, 3, 1))
    s.fill(shade(c, 0.6), (7, 1, 1, 1))


def _frame(s, c, a):
    s.fill(a, (2, 1, 10, 12))
    s.fill((24, 18, 50), (3, 2, 8, 10))
    s.fill(c, (4, 3, 6, 4))
    s.fill(shade(c, -0.4), (4, 8, 6, 1))
    s.fill(shade(c, -0.4), (4, 10, 4, 1))


def _rug(s, c, a):
    s.fill(c, (1, 3, 12, 8))
    s.fill(a, (2, 4, 10, 6))
    s.fill(c, (3, 5, 8, 4))
    s.fill(shade(a, 0.5), (6, 6, 2, 2))


def _star(s, c, a):
    pygame.draw.polygon(s, c, [(7, 0), (9, 5), (13, 5), (10, 8), (11, 13), (7, 10), (3, 13), (4, 8), (1, 5), (5, 5)])
    s.fill(a, (6, 4, 2, 3))


def _ears(s, c, a):
    pygame.draw.polygon(s, c, [(1, 12), (2, 2), (6, 8)])
    pygame.draw.polygon(s, c, [(13, 12), (12, 2), (8, 8)])
    s.fill(a, (3, 6, 1, 3))
    s.fill(a, (10, 6, 1, 3))
    s.fill(c, (1, 10, 12, 3))


def _glasses(s, c, a):
    s.fill(c, (1, 4, 5, 5))
    s.fill(c, (8, 4, 5, 5))
    s.fill(c, (5, 5, 4, 1))
    s.fill(a, (2, 5, 2, 1))
    s.fill(a, (9, 5, 2, 1))
    s.fill(shade(c, 0.3), (0, 4, 1, 1))
    s.fill(shade(c, 0.3), (13, 4, 1, 1))


def _swatch(s, c, a):
    s.fill(c, (1, 1, 12, 7))
    s.fill(a, (1, 8, 12, 5))
    s.fill(shade(c, 0.5), (2, 2, 4, 1))


def _trophy(s, c, a):
    s.fill(c, (3, 1, 8, 6))
    s.fill(c, (1, 2, 2, 3))
    s.fill(c, (11, 2, 2, 3))
    s.fill(c, (6, 7, 2, 3))
    s.fill(shade(c, -0.35), (3, 11, 8, 2))
    s.fill(a, (4, 2, 1, 4))


def _coin(s, c, a):
    pygame.draw.circle(s, a, (7, 7), 6)
    pygame.draw.circle(s, c, (7, 7), 5)
    s.fill(a, (6, 3, 2, 8))
    s.fill(shade(c, 0.6), (4, 4, 1, 2))


def _clover(s, c, a):
    for cx, cy in ((4, 4), (10, 4), (4, 10), (10, 10)):
        pygame.draw.circle(s, c, (cx, cy), 3)
    s.fill(a, (4, 4, 1, 1))
    s.fill(shade(c, -0.4), (6, 6, 2, 2))


def _cabinet(s, c, a):
    s.fill(c, (3, 0, 8, 14))
    s.fill((10, 8, 28), (4, 2, 6, 5))
    s.fill(a, (5, 3, 4, 3))
    s.fill(shade(c, 0.5), (4, 9, 6, 1))
    s.fill(a, (5, 11, 1, 1))
    s.fill(Col.YELLOW, (8, 11, 1, 1))


def _headphones(s, c, a):
    pygame.draw.arc(s, a, (2, 1, 10, 11), 0.0, 3.1416, 2)
    s.fill(c, (1, 6, 3, 6))
    s.fill(c, (10, 6, 3, 6))
    s.fill(a, (2, 8, 1, 2))
    s.fill(a, (11, 8, 1, 2))


def _crown(s, c, a):
    pygame.draw.polygon(s, c, [(1, 11), (1, 3), (4, 7), (7, 1), (10, 7), (13, 3), (13, 11)])
    s.fill(shade(c, -0.3), (1, 10, 12, 2))
    s.fill(a, (6, 7, 2, 2))
    s.fill(shade(c, 0.6), (2, 4, 1, 2))


def _visor(s, c, a):
    s.fill(a, (0, 4, 14, 6))
    s.fill(c, (1, 5, 12, 2))
    s.fill((255, 255, 255), (2, 5, 2, 1))
    s.fill(shade(a, 0.3), (0, 8, 14, 1))


def _medal(s, c, a):
    s.fill(a, (4, 0, 2, 5))
    s.fill(c, (8, 0, 2, 5))
    pygame.draw.circle(s, c, (7, 9), 5)
    pygame.draw.circle(s, shade(c, -0.35), (7, 9), 5, 1)
    s.fill(a, (6, 7, 2, 4))
    s.fill(shade(c, 0.6), (4, 7, 1, 2))


def _clip(s, c, a):
    s.fill(shade(c, -0.4), (1, 9, 12, 2))
    pygame.draw.polygon(s, c, [(7, 0), (9, 4), (13, 4), (10, 7), (11, 11), (7, 9), (3, 11), (4, 7), (1, 4), (5, 4)])
    s.fill(a, (6, 3, 2, 3))


def _tail(s, c, a):
    for x, y, w in ((1, 11, 4), (4, 9, 4), (7, 6, 3), (9, 3, 3), (10, 1, 3)):
        s.fill(c, (x, y, w, 3))
    s.fill(shade(c, -0.3), (4, 12, 3, 1))
    s.fill(a, (11, 1, 2, 2))


def _jacket(s, c, a):
    for i, color in enumerate(((255, 70, 90), (255, 160, 60), (255, 230, 80), (90, 230, 120), (80, 170, 255))):
        s.fill(color, (3, 3 + i * 2, 8, 2))
    s.fill((140, 96, 230), (0, 3, 3, 8))
    s.fill((140, 96, 230), (11, 3, 3, 8))
    s.fill((24, 18, 50), (6, 3, 2, 10))


def _soda(s, c, a):
    s.fill(c, (4, 3, 6, 10))                          # a fizzy can
    s.fill(shade(c, 0.5), (5, 4, 1, 8))
    s.fill(a, (4, 6, 6, 3))
    s.fill((190, 200, 210), (4, 2, 6, 1))
    s.fill((190, 200, 210), (4, 13, 6, 1))
    s.fill(a, (10, 0, 1, 1))
    s.fill(a, (8, 1, 1, 1))                            # bubbles


def _sandwich(s, c, a):
    # dashed outline only: the sandwich is invisible
    for x in range(1, 13, 2):
        s.fill(c, (x, 4, 1, 1))
        s.fill(c, (x, 10, 1, 1))
    for y in range(5, 10, 2):
        s.fill(c, (1, y, 1, 1))
        s.fill(c, (12, y, 1, 1))
    s.fill(a, (5, 6, 1, 2))
    s.fill(a, (8, 6, 1, 2))


def _rainbow(s, c, a):
    colors = ((255, 70, 90), (255, 160, 60), (255, 230, 80), (90, 230, 120), (80, 170, 255))
    for i, color in enumerate(colors):
        pygame.draw.arc(s, color, (1 + i, 3 + i, 12 - 2 * i, 14 - 2 * i), 0.0, 3.1416, 1)
    s.fill(a, (0, 11, 3, 2))
    s.fill(a, (11, 11, 3, 2))


def _duck(s, c, a):
    pygame.draw.ellipse(s, c, (2, 6, 10, 7))
    pygame.draw.circle(s, c, (9, 4), 3)
    s.fill(a, (11, 4, 3, 2))                           # beak
    s.fill(Col.OUTLINE, (9, 3, 1, 1))
    s.fill(shade(c, 0.5), (4, 8, 4, 1))


def _battery(s, c, a):
    s.fill((60, 66, 90), (3, 2, 8, 11))
    s.fill(c, (4, 4, 6, 8))
    s.fill((190, 200, 210), (5, 1, 4, 1))
    s.fill(a, (6, 6, 2, 1))
    s.fill(a, (5, 8, 2, 1))
    s.fill(a, (7, 9, 2, 1))                            # a crooked bolt


def _mystery(s, c, a):
    s.fill(c, (3, 2, 8, 11))
    s.fill(shade(c, 0.4), (4, 3, 1, 9))
    s.fill((190, 200, 210), (3, 1, 8, 1))
    s.fill((190, 200, 210), (3, 13, 8, 1))
    s.fill(a, (6, 4, 3, 1))                            # a big question mark
    s.fill(a, (8, 5, 1, 2))
    s.fill(a, (7, 7, 1, 1))
    s.fill(a, (7, 9, 1, 1))


def _paw(s, c, a):
    pygame.draw.circle(s, c, (7, 9), 4)
    for x, y in ((2, 6), (5, 3), (9, 3), (12, 6)):
        pygame.draw.circle(s, c, (x, y), 2)
    s.fill(a, (6, 8, 2, 2))


def _yarn(s, c, a):
    pygame.draw.circle(s, c, (6, 7), 6)
    pygame.draw.arc(s, a, (1, 2, 10, 10), 0.4, 3.0, 1)
    pygame.draw.arc(s, a, (2, 1, 9, 12), 3.4, 5.8, 1)
    s.fill(c, (10, 11, 4, 1))
    s.fill(c, (13, 12, 1, 1))


def _heart(s, c, a):
    pygame.draw.circle(s, c, (4, 5), 3)
    pygame.draw.circle(s, c, (9, 5), 3)
    pygame.draw.polygon(s, c, [(1, 6), (12, 6), (7, 12)])
    s.fill(a, (3, 3, 2, 2))


def _joystick(s, c, a):
    s.fill(shade(c, -0.4), (2, 10, 10, 3))
    s.fill(c, (3, 9, 8, 2))
    s.fill(a, (6, 4, 2, 6))
    pygame.draw.circle(s, a, (7, 3), 3)
    s.fill(shade(a, 0.6), (6, 2, 1, 1))


def _cartridge(s, c, a):
    s.fill(c, (2, 1, 10, 12))
    s.fill((0, 0, 0, 0), (2, 1, 2, 1))
    s.fill(shade(c, -0.4), (3, 11, 8, 2))
    s.fill(a, (4, 3, 6, 4))
    s.fill(shade(c, -0.5), (5, 4, 4, 1))
    for x in (4, 6, 8):
        s.fill(Col.YELLOW, (x, 12, 1, 1))


def _bell(s, c, a):
    pygame.draw.circle(s, c, (7, 7), 5)
    s.fill(c, (2, 8, 10, 3))
    s.fill(a, (4, 4, 2, 2))
    s.fill(shade(c, -0.5), (6, 8, 2, 1))
    s.fill(a, (6, 11, 2, 2))
    s.fill(shade(c, -0.4), (6, 1, 2, 2))


def _fish(s, c, a):
    pygame.draw.ellipse(s, c, (1, 3, 9, 8))
    pygame.draw.polygon(s, c, [(9, 7), (13, 3), (13, 11)])
    s.fill(a, (3, 6, 2, 2))
    s.fill(Col.OUTLINE, (3, 6, 1, 1))
    s.fill(shade(c, 0.5), (5, 9, 3, 1))


PAINTERS = {"sticker": _sticker, "cap": _cap, "ticket": _ticket, "badge": _badge,
            "lamp": _lamp, "plush": _plush, "plant": _plant, "clock": _clock, "frame": _frame,
            "rug": _rug, "star": _star, "ears": _ears, "glasses": _glasses, "swatch": _swatch,
            "headphones": _headphones, "crown": _crown, "visor": _visor, "medal": _medal,
            "clip": _clip, "tail": _tail, "jacket": _jacket, "trophy": _trophy, "coin": _coin, "clover": _clover, "cabinet": _cabinet,
            "soda": _soda, "sandwich": _sandwich, "rainbow": _rainbow, "duck": _duck,
            "battery": _battery, "mystery": _mystery,
            "paw": _paw, "yarn": _yarn, "heart": _heart, "joystick": _joystick, "cartridge": _cartridge,
            "bell": _bell, "fish": _fish}
_cache = {}


def item_icon(definition, scale=1):
    """The icon surface for an item (a '?' tile if its icon data is missing)."""
    data = definition.icon
    shape = data.get("shape")
    key = (shape, tuple(data.get("color", ())), tuple(data.get("accent", ())), scale)
    icon = _cache.get(key)
    if icon is None:
        s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
        painter = PAINTERS.get(shape, _unknown)
        painter(s, data.get("color", Col.PURPLE), data.get("accent", Col.TEXT))
        icon = outlined(s)
        if scale != 1:
            icon = pygame.transform.scale_by(icon, scale)
        _cache[key] = icon
    return icon
