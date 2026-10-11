"""Pixel-art previews for the Prize Plaza menus: the real sprite of whatever is
being looked at, scaled up with nearest-neighbour so it stays crisp.

Decorations use their own painters (the sprite that will appear at HOME),
cosmetics are shown on the player's own avatar (so what you preview is what
you will wear) and everything else uses its inventory icon.
"""
import pygame

from cosmetics import COSMETICS
from decorations import NEON_SIGN, decoration_item_id, default_catalog
from gfx import scale_color
from item_icons import item_icon
from item_registry import ITEM_REGISTRY
from player import FACINGS, styled_sheet


def scaled(surface, scale):
    return pygame.transform.scale(surface, (surface.get_width() * scale, surface.get_height() * scale))


def avatar_image(look, appearance, facing="down", frame=0, scale=1):
    """The avatar with base `look` wearing `appearance` ({slot: item id})."""
    if facing not in FACINGS:
        facing = "down"
    sheet = styled_sheet(look, appearance)
    image = sheet[facing]["idle"][frame % len(sheet[facing]["idle"])]
    return scaled(image, scale) if scale != 1 else image


def with_item(appearance, item_id):
    """`appearance` with `item_id` worn in its own slot (a cosmetic only)."""
    c = COSMETICS.get(item_id)
    if c is None:
        return dict(appearance)
    return {**appearance, c.slot: item_id}


_CATALOG = default_catalog()
_SPRITES = {}


def decoration_by_item(item_id):
    """(DecorationDefinition) for an inventory item id, or None."""
    return next((d for d in _CATALOG if decoration_item_id(d.decoration_id) == item_id), None)


def decoration_image(definition):
    """The decoration's sprite (painted once); a neon sign (a white tube
    shape) gets its colours."""
    sprite = _SPRITES.get(definition.decoration_id)
    if sprite is None:
        sprite = _SPRITES[definition.decoration_id] = definition.painter()
    if definition.slot_type == NEON_SIGN:
        tinted = sprite.copy()
        tinted.fill((*definition.neon[1], 255), special_flags=pygame.BLEND_RGBA_MULT)
        return tinted
    return sprite


def fit_scale(size, box, limit=6):
    """The biggest whole-number scale that keeps `size` inside `box`."""
    return max(1, min(limit, box[0] // max(1, size[0]), box[1] // max(1, size[1])))


def preview_for_item(item_id, look, appearance, box):
    """A Surface showing `item_id`, scaled to fit `box` (w, h)."""
    definition = ITEM_REGISTRY.get(item_id)
    cosmetic = COSMETICS.get(item_id)
    if cosmetic is not None:
        image = avatar_image(look, with_item(appearance, item_id))
        return scaled(image, fit_scale(image.get_size(), box))
    deco = decoration_by_item(item_id)
    if deco is not None:
        image = decoration_image(deco)
        return scaled(image, fit_scale(image.get_size(), box))
    if definition is None:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    icon = item_icon(definition)
    return scaled(icon, fit_scale(icon.get_size(), box))


def pedestal(size, color):
    """A little lit stage to stand a preview on."""
    w, h = size
    s = pygame.Surface(size, pygame.SRCALPHA)
    for i in range(h):
        s.fill((*scale_color(color, 0.35 + 0.4 * i / h), 255), (0, i, w, 1))
    s.fill(color, (0, 0, w, 1))
    return s
