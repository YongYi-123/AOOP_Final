import unittest
from types import SimpleNamespace
from car import PlayerCar
from effects import ShieldEffect
from oil_spin import OilSpinEffect
from items import OilSlick


class OilSpinTests(unittest.TestCase):
    def test_rotation_recovers_without_changing_speed_penalty(self):
        effect = OilSpinEffect()
        self.assertEqual(effect.visual_yaw, 0)
        self.assertEqual(effect.multipliers['steering'], 0)
        angles, grips = [], []
        for _ in range(18):
            effect.update(0.1, None)
            angles.append(effect.visual_yaw)
            grips.append(effect.multipliers['steering'])
            self.assertEqual(effect.multipliers['max_speed'], 0.55)
        self.assertEqual(angles, sorted(angles))
        self.assertEqual(grips, sorted(grips))
        self.assertAlmostEqual(angles[-1], 360)
        self.assertAlmostEqual(grips[-1], 0.5)
        self.assertTrue(effect.expired)

    def world(self, car):
        return SimpleNamespace(entities=[car], length=100000,
                               hostile=lambda target, effect: target.receive_hostile(effect))

    def test_staying_on_oil_never_restarts_spin(self):
        car = PlayerCar()
        oil = OilSlick(object(), car.front_z, car.x)
        world = self.world(car)
        oil.update(0.01, world)
        self.assertIsInstance(car.effects[0], OilSpinEffect)
        for _ in range(50):
            car._tick_effects(0.1)
            oil.update(0.1, world)
        self.assertEqual(car.effects, [])
        car.x = 1.0
        oil.update(0.1, world)
        car.x = 0
        oil.update(0.1, world)
        self.assertIsInstance(car.effects[0], OilSpinEffect)

    def test_shield_blocks_oil_and_normal_turn_has_no_spin(self):
        car = PlayerCar()
        self.assertFalse(any(isinstance(e, OilSpinEffect) for e in car.effects))
        car.add_effect(ShieldEffect())
        OilSlick(object(), car.front_z, car.x).update(0.1, self.world(car))
        self.assertFalse(any(isinstance(e, OilSpinEffect) for e in car.effects))

    def test_overlapping_slicks_do_not_reset_active_rotation(self):
        car = PlayerCar()
        first = OilSlick(object(), car.front_z, car.x)
        second = OilSlick(object(), car.front_z, car.x)
        world = self.world(car)
        first.update(0.1, world)
        effect = car.effects[0]
        car._tick_effects(0.5)
        second.update(0.1, world)
        self.assertIs(car.effects[0], effect)
        self.assertEqual(effect.elapsed, 0.5)

    def test_player_render_observes_rotation_and_intensity(self):
        from unittest.mock import patch
        import pygame
        import settings as S
        old = S.DRIVING_FX_INTENSITY
        self.addCleanup(setattr, S, 'DRIVING_FX_INTENSITY', old)
        car = PlayerCar()
        effect = OilSpinEffect()
        car.add_effect(effect)
        effect.update(0.9, car)
        surface = pygame.Surface((800, 600))
        S.DRIVING_FX_INTENSITY = 1
        with patch('car.draw_car_rear') as draw:
            car.draw(surface)
            self.assertAlmostEqual(draw.call_args.kwargs['yaw'], 180)
        S.DRIVING_FX_INTENSITY = 0
        with patch('car.draw_car_rear') as draw:
            car.draw(surface)
            self.assertEqual(draw.call_args.kwargs['yaw'], 0)

    def test_real_game_pause_restart_and_render(self):
        import os
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        import pygame
        pygame.init()
        pygame.display.set_mode((800, 600))
        from game import Game
        game = Game()
        self.addCleanup(game.audio.stop_engine)
        game.start_race()
        game.begin_playing()
        game.player.add_effect(OilSpinEffect())
        controls = {'accelerate': False, 'brake': False, 'steer': 0}
        game.update(0.1, controls)
        effect = game.player.effects[0]
        elapsed = effect.elapsed
        game.render()
        game.set_paused(True)
        game.update(0.1, controls)
        self.assertEqual(effect.elapsed, elapsed)
        game.start_race()
        self.assertEqual(game.player.effects, [])
        game.render()
