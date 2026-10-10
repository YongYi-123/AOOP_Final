"""Headless visual tests and physics isolation checks."""
import os
import unittest
from types import SimpleNamespace as NS

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from drift_effects import DriftEffects, DriftState


def inputs(speed=1.0, steer=1, curve=3, brake=False):
    player = NS(speed_percent=speed, front_z=1200, x=0, collisions=0, spec=NS(width=1))
    road = NS(segment_at=lambda z: NS(curve=curve), length=10000)
    return player, road, {"steer": steer, "brake": brake}


class DriftStateTests(unittest.TestCase):
    def test_only_high_speed_turns_drift(self):
        self.assertEqual(DriftState.detect(0.4, 1, 4, True), DriftState())
        self.assertEqual(DriftState.detect(1, 0, 0, False).amount, 0)
        self.assertGreater(DriftState.detect(1, 1, 3, False).amount, 0)
        self.assertLess(DriftState.detect(1, -1, -3, False).amount, 0)

    def test_hard_braking_is_separate_from_drift(self):
        state = DriftState.detect(1, 0, 0, True)
        self.assertTrue(state.braking)
        self.assertEqual(state.amount, 0)

    def test_smoothing_does_not_snap_and_recovers(self):
        effects = DriftEffects()
        effects.update(1 / 60, *inputs())
        self.assertTrue(0 < effects.rear_offset < 16)
        for _ in range(120):
            effects.update(1 / 60, *inputs(speed=0))
        self.assertAlmostEqual(effects.rear_offset, 0, places=5)

    def test_intensity_zero_disables_offset(self):
        effects = DriftEffects(0)
        effects.update(1, *inputs())
        self.assertEqual((effects.rear_offset, effects.yaw), (0, 0))
        effects.intensity = 100
        self.assertEqual(effects.intensity, 2)

    def test_observer_never_mutates_player(self):
        player, road, controls = inputs()
        before = vars(player).copy()
        DriftEffects().update(0.1, player, road, controls)
        self.assertEqual(vars(player), before)
