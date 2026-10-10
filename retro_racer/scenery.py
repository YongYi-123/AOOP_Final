"""Scenery variants and thumbnails rendered with the actual race renderer."""
from dataclasses import replace

import pygame
import settings as S
from assets import LayerSpec
from road import Road
from theme import BEACH, CITY, DESERT, SUBURBS, Placement, W


SUNSET_COAST = replace(
    BEACH, key="sunset_coast", name="SUNSET SEA", tagline="WARM COASTAL SUNSET",
    sky_bands=SUBURBS.sky_bands,
    sun=replace(SUBURBS.sun, x_frac=0.76),
    layers=[LayerSpec("mountains", 44, (100, 62, 125), 0.25,
                      params={"freqs": (2, 5, 8), "phase": 1.1}),
            LayerSpec("ocean", 30, (100, 75, 150), 0.05)],
    water=((125, 105, 175), (98, 82, 155), -3.3))

FOREST = replace(
    SUBURBS, key="forest", name="FOREST", tagline="PINE FOREST / MOUNTAIN RIDGES",
    sky_bands=((18, 42, 72), (30, 65, 95), (48, 92, 122), (68, 118, 144),
               (90, 145, 162), (118, 169, 175), (148, 192, 188),
               (185, 214, 202), (222, 232, 214)),
    sun=replace(BEACH.sun, x_frac=0.30, radius=32),
    layers=[LayerSpec("mountains", 130, (42, 82, 86), 0.25,
                      params={"freqs": (3, 5, 7), "phase": 0.7}),
            LayerSpec("mountains", 80, (25, 62, 64), 0.5,
                      params={"freqs": (2, 6, 9), "phase": 1.9})],
    ground=((35, 114, 57), (28, 99, 48)), preview=(),
    placements=[Placement(W(("tree", 5), ("bush", 1)), every=4,
                          near=1.4, far=3.4, sides=1),
                Placement(W(("post_wood", 1),), every=16, near=1.25, far=1.25, sides=2),
                Placement(every=45, phase=20, near=1.35, far=1.35,
                          curve_signs=("sign_l", "sign_r", "sign"))])

SCENERY_THEMES = (SUBURBS, CITY, BEACH, DESERT, SUNSET_COAST, FOREST)


class SceneryPreviewRenderer:
    """Own cached screenshots; never project or recolour the live game's Road."""

    def __init__(self, themes):
        self.themes = themes
        self._previews = {}

    def preview(self, theme, route, size=(96, 72), markers=True):
        key = (theme.key, route, size, markers)
        if key not in self._previews:
            canvas = pygame.Surface((S.WIDTH, S.HEIGHT))
            canvas.fill(theme.ground[1])
            self.themes.backdrop(theme, S.WIDTH, S.HEIGHT // 2).draw(canvas, 0)
            Road(theme, markers=markers, route=route).draw(canvas, 0, 0)
            self._previews[key] = pygame.transform.scale(canvas, size)
        return self._previews[key]
