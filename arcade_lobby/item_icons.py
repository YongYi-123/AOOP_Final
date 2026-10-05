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


PAINTERS = {"sticker": _sticker, "cap": _cap, "ticket": _ticket, "badge": _badge}
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
