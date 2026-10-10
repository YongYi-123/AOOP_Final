import unittest
from tracks import TRACKS


class CircuitFeatureTests(unittest.TestCase):
    def test_curvature_transition_is_bounded_including_lap_seam(self):
        for track in TRACKS:
            curves=track.build().curves
            self.assertLess(max(abs(curves[(i+1)%len(curves)]-curve)
                                for i,curve in enumerate(curves)),.8)

    def test_harbor_has_longer_straights_and_tighter_hairpins(self):
        routes={track.key:track.build() for track in TRACKS}
        straights={key:sum(abs(c)<.04 for c in route.curves) for key,route in routes.items()}
        self.assertGreater(straights['harbor'],straights['emerald'])
        self.assertGreater(straights['harbor'],straights['summit'])
        self.assertGreater(max(abs(c) for c in routes['harbor'].curves),4)
        for route in routes.values():
            self.assertLess(min(route.curves),-1)
            self.assertGreater(max(route.curves),1)

    def test_periodic_elevation_has_smooth_lap_boundary(self):
        for track in TRACKS:
            route=track.build()
            self.assertEqual(route.heights[0],route.heights[-1])
            self.assertEqual(route.elevation_at(0),route.elevation_at(route.length))
            self.assertLess(max(abs(a-b) for a,b in zip(route.heights,route.heights[1:])),4)
        routes={t.key:t.build() for t in TRACKS}
        self.assertGreater(max(routes['summit'].heights),max(routes['emerald'].heights))
        self.assertGreater(max(routes['emerald'].heights),max(routes['harbor'].heights))

    def test_terrain_projection_and_landmarks_remain_finite_at_lap_seam(self):
        import pygame,math
        from road import Road
        from theme import SUBURBS
        from dataclasses import replace
        for track in TRACKS:
            route=track.build()
            road=Road(SUBURBS,route=route)
            self.assertTrue(all(mark.kind==track.key for mark in road.landmarks))
            for z in (0,route.length-100,route.length/3):
                visible=road.project(z,0)
                self.assertTrue(all(math.isfinite(s.sy1) and math.isfinite(s.sy2)
                                    for s in visible if not s.behind))
                road.draw(pygame.Surface((800,600)),z,0)
            flat=Road(SUBURBS,route=replace(route,heights=()))
            curved=pygame.Surface((800,600)); level=pygame.Surface((800,600))
            road.draw(curved,route.length/8,0); flat.draw(level,route.length/8,0)
            self.assertNotEqual(pygame.image.tobytes(curved,'RGB'),pygame.image.tobytes(level,'RGB'))
