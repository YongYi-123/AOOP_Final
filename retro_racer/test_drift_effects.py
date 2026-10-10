"""Headless visual tests and physics isolation checks."""
import os
import unittest
import random
from types import SimpleNamespace as NS

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from drift_effects import DriftEffects, DriftState, SkidMark
import pygame


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

    def test_inactive_menus_and_end_screens_emit_nothing(self):
        effects = DriftEffects()
        player, road, controls = inputs(brake=True)
        player.collisions = 1
        effects.update(0.1, player, road, controls, active=False)
        self.assertEqual(effects.state, DriftState())
        self.assertEqual((effects.smoke, effects.skids, effects.sparks), ([], [], []))


class SmokeTests(unittest.TestCase):
    def test_smoke_emits_expires_and_stays_bounded(self):
        effects = DriftEffects()
        for _ in range(600):
            effects.update(1 / 60, *inputs())
        self.assertTrue(0 < len(effects.smoke) <= 80)
        for _ in range(60):
            effects.update(1 / 60, *inputs(speed=0))
        self.assertEqual(effects.smoke, [])

    def test_visual_rng_does_not_change_gameplay_rng(self):
        before = random.getstate()
        effects = DriftEffects()
        effects.update(0.1, *inputs())
        self.assertEqual(random.getstate(), before)

    def test_draw_is_visible_and_disabled_is_empty(self):
        effects = DriftEffects()
        effects.update(0.1, *inputs())
        surface = pygame.Surface((800, 600))
        effects.draw_smoke(surface)
        self.assertTrue(any(pygame.image.tobytes(surface, "RGB")))
        effects.intensity = 0
        surface.fill((0, 0, 0))
        effects.draw_smoke(surface)
        self.assertFalse(any(pygame.image.tobytes(surface, "RGB")))


class SkidTests(unittest.TestCase):
    def test_acceleration_takes_priority_over_brake_as_in_physics(self):
        effects = DriftEffects()
        player, road, controls = inputs(steer=0, curve=0, brake=True)
        controls["accelerate"] = True
        effects.update(0.1, player, road, controls)
        self.assertFalse(effects.state.braking)
        self.assertEqual((effects.skids, effects.smoke), ([], []))

    def test_only_high_speed_braking_emits_world_marks(self):
        effects = DriftEffects()
        effects.update(0.1, *inputs(brake=False))
        self.assertEqual(effects.road_drawables(), [])
        effects.update(0.1, *inputs(speed=0.3, brake=True))
        self.assertEqual(effects.road_drawables(), [])
        player, road, controls = inputs(brake=True)
        player.front_z = road.length - 20
        effects.update(0.1, player, road, controls)
        self.assertEqual(effects.road_drawables()[0].z, 50)
        for _ in range(20):
            effects.update(0.1, *inputs(speed=0))
        self.assertEqual(effects.road_drawables(), [])

    def test_projected_marks_scale_with_road_and_reset_clears(self):
        surface = pygame.Surface((800, 600))
        mark = SkidMark(0, 1000, 1, 1)
        mark.draw(surface, 400, 570, 750)
        self.assertTrue(any(pygame.image.tobytes(surface, "RGB")))
        effects = DriftEffects()
        effects.update(0.1, *inputs(brake=True))
        effects.reset()
        self.assertEqual((effects.skids, effects.smoke), ([], []))


class CollisionTests(unittest.TestCase):
    def test_one_burst_per_collision_and_expiry(self):
        effects = DriftEffects()
        player, road, controls = inputs(speed=0)
        effects.update(0.01, player, road, controls)
        self.assertEqual(effects.sparks, [])
        player.collisions = 1
        effects.update(0.01, player, road, controls)
        self.assertEqual(len(effects.sparks), 18)
        effects.update(0.01, player, road, controls)
        self.assertEqual(len(effects.sparks), 18)
        surface = pygame.Surface((800, 600))
        effects.draw_sparks(surface)
        self.assertTrue(any(pygame.image.tobytes(surface, "RGB")))
        for _ in range(5):
            effects.update(0.1, player, road, controls)
        self.assertEqual(effects.sparks, [])

    def test_shake_is_small_and_intensity_zero_disables(self):
        effects = DriftEffects(rng=random.Random(7))
        for _ in range(100):
            x, y = effects.shake_offset(1)
            self.assertTrue(abs(x) <= 4 and abs(y) <= 2)
        effects.intensity = 0
        self.assertEqual(effects.shake_offset(1), (0, 0))
        player, road, controls = inputs()
        player.collisions = 1
        effects.update(0.1, player, road, controls)
        self.assertEqual(effects.sparks, [])
