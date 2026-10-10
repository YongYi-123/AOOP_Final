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
