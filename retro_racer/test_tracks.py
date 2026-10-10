import math
import unittest

from tracks import TRACKS, CURVE_GAIN


class RouteTests(unittest.TestCase):
    def test_three_distinct_closed_routes_with_uniform_distance(self):
        routes = [t.build() for t in TRACKS]
        self.assertEqual(len({r.points for r in routes}), 3)
        for route in routes:
            with self.subTest(track=route.key):
                self.assertEqual(route.points[0], route.points[-1])
                self.assertEqual(len(route.points), len(route.curves) + 1)
                self.assertEqual(route.length, len(route.curves) * 200)
                steps = [math.dist(a, b) for a, b in zip(route.points, route.points[1:])]
                self.assertTrue(all(199 < step <= 200.01 for step in steps))
                self.assertTrue(all(math.isfinite(c) and abs(c) < 6 for c in route.curves))

    def test_curvature_is_derived_from_same_points_used_by_map(self):
        for track in TRACKS:
            route = track.build()
            for i, curve in enumerate(route.curves):
                a, b, c = route.points[(i - 1) % len(route.curves)], route.points[i], route.points[i + 1]
                u, v = (b[0]-a[0], b[1]-a[1]), (c[0]-b[0], c[1]-b[1])
                expected = math.atan2(u[0]*v[1]-u[1]*v[0], u[0]*v[0]+u[1]*v[1]) * CURVE_GAIN
                self.assertAlmostEqual(curve, expected)

    def test_distance_wrap_and_interpolation(self):
        route = TRACKS[0].build()
        self.assertEqual(route.point_at(0), route.point_at(route.length * 3))
        self.assertEqual(route.point_at(-200), route.points[-2])
        a, b = route.points[:2]
        self.assertEqual(route.point_at(100), ((a[0]+b[0])/2, (a[1]+b[1])/2))

    def test_routes_have_straights_and_both_turn_directions(self):
        for track in TRACKS:
            curves = track.build().curves
            self.assertLess(min(curves), -1)
            self.assertGreater(max(curves), 1)
            self.assertGreater(sum(abs(c) < 0.04 for c in curves), 80)

    def test_cached_build_and_invalid_segment_length(self):
        self.assertIs(TRACKS[0].build(), TRACKS[0].build())
        with self.assertRaises(ValueError):
            TRACKS[0].build(0)
