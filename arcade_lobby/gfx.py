"""Small pixel-art drawing helpers shared by sprites, the room and the UI.
Everything here is meant to be called once at load time and cached."""
import pygame

from settings import Col


def shade(color, amount):
    """Lighten (amount > 0) or darken (amount < 0) an RGB colour."""
    if amount >= 0:
        return tuple(int(c + (255 - c) * amount) for c in color[:3])
    return tuple(int(c * (1 + amount)) for c in color[:3])


def scale_color(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color[:3])


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def outlined(surf, color=Col.OUTLINE):
    """Return a copy of `surf` with a 1px pixel-art outline around its shape."""
    w, h = surf.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    silhouette = pygame.mask.from_surface(surf).to_surface(
        setcolor=color, unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(silhouette, (dx, dy))
    out.blit(surf, (1, 1))
    return out


def flash_overlay(surf, level=110):
    """Additive white silhouette of a sprite, for 'brighten' flashes."""
    return pygame.mask.from_surface(surf).to_surface(
        setcolor=(level, level, level, 255), unsetcolor=(0, 0, 0, 0))


def radial_glow(radius, color, bands=6, squash=1.0):
    """Banded radial light, meant to be blitted with BLEND_ADD."""
    w, h = radius * 2, max(2, int(radius * 2 * squash))
    surf = pygame.Surface((w, h))
    surf.fill((0, 0, 0))
    for i in range(bands, 0, -1):
        k = (bands - i + 1) / bands
        rect = pygame.Rect(0, 0, int(w * i / bands), int(h * i / bands))
        rect.center = (w // 2, h // 2)
        pygame.draw.ellipse(surf, scale_color(color, k), rect)
    return surf


def neon_rect_glow(w, h, color, spread=8, strength=0.6):
    """Soft halo around a w x h rectangle (layered rects, for BLEND_ADD).
    The returned surface is (w + 2*spread) x (h + 2*spread)."""
    surf = pygame.Surface((w + spread * 2, h + spread * 2))
    surf.fill((0, 0, 0))
    for i in range(spread, 0, -1):
        k = ((spread - i + 1) / spread) ** 1.6 * strength
        rect = pygame.Rect(spread - i, spread - i, w + i * 2, h + i * 2)
        pygame.draw.rect(surf, scale_color(color, k), rect, border_radius=i)
    return surf


def glow_line(length, color, vertical=False, spread=4, strength=0.5):
    """Halo for a thin neon strip (for BLEND_ADD)."""
    w, h = (1, length) if vertical else (length, 1)
    return neon_rect_glow(w, h, color, spread, strength)


def soft_shadow(width, height, alpha=110):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (*Col.SHADOW, alpha), surf.get_rect())
    return surf
