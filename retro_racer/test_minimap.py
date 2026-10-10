import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from minimap import MiniMap, RouteProjection, PLAYER_COLOR, AI_COLOR
from tracks import TRACKS


class MiniMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_all_route_projections_fit_and_preserve_aspect(self):
        for track in TRACKS:
            route = track.build()
            projection = RouteProjection(route, (10, 20, 160, 100))
            self.assertEqual(projection.points[0], projection.points[-1])
            for x, y in projection.points:
                self.assertTrue(9.99 <= x <= 170.01)
                self.assertTrue(19.99 <= y <= 120.01)
            a, b = route.points[:2]
            p, q = projection.points[:2]
            self.assertAlmostEqual(q[0] - p[0], (b[0] - a[0]) * projection.scale)
            self.assertAlmostEqual(q[1] - p[1], (b[1] - a[1]) * projection.scale)

    def test_markers_follow_actual_position_and_wrap_laps(self):
        route = TRACKS[0].build()
        minimap = MiniMap(route)
        racer = SimpleNamespace(front_z=12345)
        first = minimap.marker_position(racer)
        racer.front_z += route.length
        self.assertEqual(minimap.marker_position(racer), first)
        racer.front_z += route.length / 3
        self.assertNotEqual(minimap.marker_position(racer), first)

    def test_draw_distinguishes_player_and_ai_without_mutating_racers(self):
        minimap = MiniMap(TRACKS[0].build())
        player = SimpleNamespace(front_z=0)
        opponent = SimpleNamespace(front_z=minimap.route.length / 2)
        screen = pygame.Surface((800, 600))
        minimap.draw(screen, player, [opponent])
        for racer, color in ((player, PLAYER_COLOR), (opponent, AI_COLOR)):
            point = tuple(round(v) for v in minimap.marker_position(racer))
            self.assertEqual(screen.get_at(point)[:3], color)
        self.assertEqual(player.front_z, 0)
        self.assertEqual(opponent.front_z, minimap.route.length / 2)

    def test_hidden_map_draws_nothing_and_route_switch_preserves_visibility(self):
        minimap = MiniMap(TRACKS[0].build())
        minimap.toggle()
        screen = pygame.Surface((800, 600))
        screen.fill((1, 2, 3))
        before = pygame.image.tobytes(screen, "RGB")
        minimap.draw(screen, SimpleNamespace(front_z=0))
        self.assertEqual(pygame.image.tobytes(screen, "RGB"), before)
        minimap.set_route(TRACKS[1].build())
        self.assertFalse(minimap.visible)
        self.assertIs(minimap.projection.route, minimap.route)

    def test_original_circuits_have_distinct_geometry_previews(self):
        images = [pygame.image.tobytes(MiniMap.preview(t.build(), (240, 160)), "RGB") for t in TRACKS]
        self.assertEqual(len(set(images)), 3)
