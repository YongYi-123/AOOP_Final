"""Actual racer loop: effects must not change driving or scoring."""
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import settings as S
from game import Game
from car import PlayerCar
from drift_effects import DriftEffects
from race import State


class DriftIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original = S.DRIVING_FX_INTENSITY
        self.addCleanup(setattr, S, "DRIVING_FX_INTENSITY", self.original)
        self.game = Game()
        self.addCleanup(self.game.audio.stop_engine)
        self.game.start_race()
        self.game.begin_playing()
        self.game.player.speed = self.game.player.max_speed
        self.controls = {"accelerate": False, "brake": False, "steer": 1}

    def test_game_loop_keeps_normal_turn_and_braking_marks(self):
        for _ in range(10):
            self.game.update(1 / 60, self.controls)
        self.assertEqual(self.game.drift.rear_offset, 0)
        self.assertEqual(self.game.drift.smoke, [])
        self.controls["brake"] = True
        for _ in range(3):
            self.game.update(1 / 60, self.controls)
        self.assertGreater(len(self.game.drift.road_drawables()), 0)
        self.game.render()

    def test_collision_emits_once_and_shield_does_not_emit(self):
        other = PlayerCar()
        other.speed = self.game.player.speed
        self.game.player.collide(other)
        self.game.update(1 / 60, self.controls)
        self.assertGreater(len(self.game.drift.sparks), 0)
        self.game.render()
        self.game.reset()
        from effects import ShieldEffect
        self.game.player.add_effect(ShieldEffect())
        self.assertFalse(self.game.player.collide(other))
        self.game.state = State.PLAYING
        self.game.update(1 / 60, self.controls)
        self.assertEqual(self.game.drift.sparks, [])

    def test_ai_rear_end_nudge_triggers_visuals_without_new_crash_count(self):
        field = self.game.manager.field
        ai = field.racers[0]
        ai.z, ai.x = self.game.player.front_z - 100, self.game.player.x
        field.entities = [self.game.player, ai]
        field._collide_entities()
        self.assertIn("bump", field.events)
        self.assertEqual(self.game.player.collisions, 0)
        self.game.update(1 / 60, self.controls)
        self.assertGreater(len(self.game.drift.sparks), 0)
        self.assertNotEqual(self.game.drift.rear_offset, 0)

    def test_pause_freezes_visuals_and_restart_clears(self):
        self.game.player.collide(PlayerCar())
        for _ in range(10):
            self.game.update(1 / 60, self.controls)
        ages = [p.age for p in self.game.drift.smoke]
        self.game.set_paused(True)
        self.game.update(0.1, self.controls)
        self.assertEqual([p.age for p in self.game.drift.smoke], ages)
        self.game.start_race()
        self.assertEqual((self.game.drift.smoke, self.game.drift.skids, self.game.drift.sparks), ([], [], []))
        self.assertEqual(self.game.drift.rear_offset, 0)

    def test_v_cycles_intensity_and_zero_disables(self):
        S.DRIVING_FX_INTENSITY = 2
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=0))
        self.game.update(0.05, self.controls)
        self.assertEqual(S.DRIVING_FX_INTENSITY, 0)
        self.assertEqual(self.game.drift.rear_offset, 0)
        self.assertEqual(self.game.drift.smoke, [])

    def test_effects_do_not_change_physics_or_rendering_rng(self):
        player, baseline = PlayerCar(), PlayerCar()
        player.speed = baseline.speed = player.max_speed
        effects = DriftEffects()
        surface = pygame.Surface((800, 600))
        for frame in range(120):
            controls = {"accelerate": frame < 60, "brake": frame >= 60, "steer": 1}
            player.update(1 / 60, self.game.road, **controls)
            baseline.update(1 / 60, self.game.road, **controls)
            effects.update(1 / 60, player, self.game.road, controls)
            player.draw(surface, effects.rear_offset, effects.yaw)
        for field in ("speed", "x", "z", "distance", "score", "collisions", "push"):
            self.assertEqual(getattr(player, field), getattr(baseline, field))
        self.game.shake = S.SHAKE_TIME
        before = random.getstate()
        self.game.render()
        self.assertEqual(random.getstate(), before)
