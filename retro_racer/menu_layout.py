"""Shared layout rules for every Retro Racer menu screen (the 800x600 logical surface).

Every full-screen menu is built from the same regions, so screens line up with each other
and nothing can drift outside the screen:

    y   0 ..  24   margin
    y  24 ..  40   checkered band
    y  46 .. 110   screen title (HUGE font, shallow 3px extrusion)
    y 118 .. 514   CONTENT: panels, cards, lists (never wider than SAFE)
    y 524 .. 576   FOOTER panel: the key hints of the screen

Fonts: `small` is the 17px body text, `font` the 34px row text, `big` the 36px name text and `huge`
the 54px title text. A label that could be long is drawn with `fit_font`, never at a fixed size.
"""
import math

import pygame

import settings as S

MARGIN = 24
SCREEN = pygame.Rect(0, 0, S.WIDTH, S.HEIGHT)
SAFE = SCREEN.inflate(-2 * MARGIN, -2 * MARGIN)         # nothing is drawn outside this
CHECKER_Y = 24
TITLE_Y = 46
CONTENT = pygame.Rect(MARGIN, 118, S.WIDTH - 2 * MARGIN, 396)
FOOTER = pygame.Rect(MARGIN, 524, S.WIDTH - 2 * MARGIN, 52)

PANEL_FILL = (8, 8, 30)
PANEL_EDGE = (70, 74, 150)
PANEL_HOT = (255, 224, 70)

CARD_SIZE = (208, 124)           # a track preview card; three of them sit side by side


def mix(a, b, k):
    """Blend colour `a` towards `b` by k (0..1)."""
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def pulse(t, speed=4.0):
    """A smooth 0..1 wave, for prompts and highlights that breathe instead of flashing."""
    return 0.5 + 0.5 * math.sin(t * speed)


def panel(surf, rect, edge=None, alpha=215):
    """The one panel style of every menu: dark translucent fill, 2px pixel border, notched corners."""
    rect = pygame.Rect(rect)
    shade = pygame.Surface(rect.size, pygame.SRCALPHA)
    shade.fill((*PANEL_FILL, alpha))
    surf.blit(shade, rect.topleft)
    pygame.draw.rect(surf, edge or PANEL_EDGE, rect, 2)
    for x, y in (rect.topleft, (rect.right - 2, rect.y), (rect.x, rect.bottom - 2), (rect.right - 2, rect.bottom - 2)):
        surf.fill((0, 0, 0), (x, y, 2, 2))


def fit_font(fonts, text, max_width):
    """The first (largest) of `fonts` that renders `text` within `max_width`, else the last."""
    for font in fonts:
        if font.render(text, False, (255, 255, 255)).get_width() <= max_width:
            return font
    return fonts[-1]
