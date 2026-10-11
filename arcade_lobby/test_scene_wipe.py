"""The scene-transition wipe must survive any window / surface size.

A real-window run once crashed inside SceneManager._draw_wipe with
"range() arg 3 must not be zero": the window surface was shorter than the
300-pixel canvas, so the pixel scale (height // 300) became 0 and so did the
wipe's band height. Run headless:   python -m unittest test_scene_wipe -v
"""
import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from scene_base import BaseScene, SceneManager  # noqa: E402
from settings import SCREEN_H, SCREEN_W, VIEW_H, VIEW_W, Col  # noqa: E402


def reference_wipe(screen, fade, band_px=SceneManager.BAND):
    """The original algorithm, verbatim, for normal-size windows."""
    px = screen.get_height() // VIEW_H
    band = band_px * px
    h = math.ceil(band * fade)
    w = screen.get_width()
    for y in range(0, screen.get_height(), band):
        screen.fill(Col.FADE, (0, y, w, h))
        if fade < 1.0:
            screen.fill(Col.MAGENTA if (y // band) % 2 else Col.CYAN, (0, y + h, w, px))


class FullResolutionScene(BaseScene):
    full_resolution = True

    def draw(self, surf):
        surf.fill((10, 20, 30))


SIZES = [(800, 600), (SCREEN_W, SCREEN_H), (800, 599), (800, 300), (800, 299), (800, 150), (800, 100),
         (800, 60), (800, 1), (800, 0), (0, 600), (0, 0), (1, 1), (7, 3), (10, 10), (299, 299), (300, 300),
         (1600, 1200), (3840, 2160), (333, 777)]
FADES = (0.0, 0.001, 0.25, 0.5, 0.75, 0.999, 1.0)


class WipeTests(unittest.TestCase):
    def manager(self, scene=None):
        m = SceneManager()
        m.push(scene or BaseScene(None), fade=False)
        return m

    def test_no_surface_size_crashes_the_wipe(self):
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        for size in SIZES:
            for fade in FADES:
                m = self.manager()
                m.fade = fade
                screen = pygame.Surface(size)
                m.draw(canvas, screen)                                  # must not raise
                self.assertEqual(screen.get_size(), size)

    def test_out_of_range_fade_values_are_clamped(self):
        screen = pygame.Surface((800, 600))
        for fade in (-5.0, -0.0001, 1.0001, 7.0, float("inf")):
            m = self.manager()
            m.fade = fade
            m.draw(pygame.Surface((VIEW_W, VIEW_H)), screen)

    def test_full_resolution_scenes_survive_tiny_windows_too(self):
        for size in ((800, 100), (5, 5), (0, 0), (800, 299)):
            m = self.manager(FullResolutionScene(None))
            m.fade = 0.5
            m.draw(pygame.Surface((VIEW_W, VIEW_H)), pygame.Surface(size))

    def test_direct_wipe_calls_with_degenerate_surfaces(self):
        m = SceneManager()
        for size in ((0, 0), (1, 1), (800, 0), (0, 600), (800, 1), (3, 299)):
            for fade in (0.0, 0.5, 1.0):
                m.fade = fade
                m._draw_wipe(pygame.Surface(size))

    def test_normal_resolution_looks_exactly_as_before(self):
        for size in ((800, 600), (1600, 1200), (1200, 900)):
            for fade in FADES:
                new, old = pygame.Surface(size), pygame.Surface(size)
                for s in (new, old):
                    s.fill((40, 30, 90))
                m = SceneManager()
                m.fade = fade
                m._draw_wipe(new)
                reference_wipe(old, fade)
                self.assertEqual(pygame.image.tobytes(new, "RGB"), pygame.image.tobytes(old, "RGB"),
                                 f"{size} fade={fade}")

    def test_small_windows_still_draw_a_visible_wipe(self):
        screen = pygame.Surface((400, 150))
        screen.fill((90, 90, 90))
        m = SceneManager()
        m.fade = 1.0
        m._draw_wipe(screen)
        self.assertEqual(screen.get_at((10, 10))[:3], Col.FADE)             # fully covered at fade 1.0

    def test_a_whole_transition_runs_on_a_shrinking_window(self):
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        m = self.manager()
        m.push(BaseScene(None))                                          # starts the wipe
        for height in (600, 450, 301, 299, 120, 1, 0, 120, 600):
            m.update(0.04)
            m.draw(canvas, pygame.Surface((800, height)))
        for _ in range(30):
            m.update(0.04)
        self.assertFalse(m.transitioning)


if __name__ == "__main__":
    unittest.main()
