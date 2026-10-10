import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import settings as S
from scenery import SCENERY_THEMES, FOREST, SUNSET_COAST, SceneryPreviewRenderer
from theme import BEACH, CITY, SUBURBS, TrackThemeManager
from tracks import TRACKS
from road import Road


class SceneryPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.themes = TrackThemeManager(SCENERY_THEMES)
        self.renderer = SceneryPreviewRenderer(self.themes)
        self.route = TRACKS[0].build(S.SEGMENT_LENGTH)

    def test_original_themes_remain_and_variants_do_not_change_them(self):
        self.assertIs(SCENERY_THEMES[0], SUBURBS)
        self.assertIs(SCENERY_THEMES[1], CITY)
        self.assertIs(SCENERY_THEMES[2], BEACH)
        self.assertEqual(len({t.key for t in SCENERY_THEMES}), 6)
        self.assertIsNot(SUNSET_COAST.layers, BEACH.layers)
        self.assertIsNot(FOREST.placements, SUBURBS.placements)
        self.assertNotEqual(SUNSET_COAST.sky_bands, BEACH.sky_bands)
        self.assertEqual({kind for p in FOREST.placements for kind, _ in p.kinds},
                         {"tree", "bush", "post_wood"})

    def test_each_thumbnail_equals_downscaled_actual_backdrop_and_road(self):
        for theme in SCENERY_THEMES:
            with self.subTest(theme=theme.key):
                actual = pygame.Surface((S.WIDTH, S.HEIGHT))
                actual.fill(theme.ground[1])
                self.themes.backdrop(theme, S.WIDTH, S.HEIGHT // 2).draw(actual, 0)
                Road(theme, route=self.route).draw(actual, 0, 0)
                actual = pygame.transform.scale(actual, (96, 72))
                preview = self.renderer.preview(theme, self.route)
                self.assertEqual(pygame.image.tobytes(preview, "RGB"),
                                 pygame.image.tobytes(actual, "RGB"))

    def test_previews_are_distinct_and_cached_per_route_size_and_markers(self):
        previews = [self.renderer.preview(t, self.route) for t in SCENERY_THEMES]
        self.assertEqual(len({pygame.image.tobytes(p, "RGB") for p in previews}), 6)
        self.assertIs(self.renderer.preview(SUBURBS, self.route), previews[0])
        self.assertIsNot(self.renderer.preview(SUBURBS, TRACKS[1].build()), previews[0])
        self.assertEqual(self.renderer.preview(SUBURBS, self.route, (80, 60)).get_size(), (80, 60))
        self.assertIsNot(self.renderer.preview(SUBURBS, self.route, markers=False), previews[0])

    def test_preview_rendering_does_not_change_ai_random_stream_or_live_geometry(self):
        live = Road(SUBURBS, route=self.route)
        colors = [s.colors for s in live.segments]
        sprites = [list(s.sprites) for s in live.segments]
        before = random.getstate()
        self.renderer.preview(FOREST, self.route)
        self.assertEqual(random.getstate(), before)
        self.assertEqual([s.colors for s in live.segments], colors)
        self.assertEqual([s.sprites for s in live.segments], sprites)
