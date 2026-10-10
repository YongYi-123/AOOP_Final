import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
import settings as S
from game import Game
from road_hazards import RoadHazards
from oil_spin import OilSpinEffect
from modes import GameMode


class RoadHazardTests(unittest.TestCase):
    def game(self,mode=GameMode.COMPETITIVE):
        game=Game()
        self.addCleanup(game.audio.stop_engine)
        game.mode=mode
        game.start_race(); game.begin_playing()
        return game

    def test_real_game_generates_sparse_visible_oil_in_both_modes(self):
        for mode in GameMode:
            game=self.game(mode)
            self.assertEqual(len(game.hazards.puddles),5)
            self.assertGreater(game.hazards.puddles[0].z,5000)
            self.assertEqual([(h.z,h.x) for h in game.hazards.puddles],
                             [(h.z,h.x) for h in RoadHazards(game.road).puddles])
            original=pygame.Surface((800,600)); oily=pygame.Surface((800,600))
            game.road.draw(original,game.player.z,game.player.x)
            game.road.draw(oily,game.player.z,game.player.x,game.hazards.drawables())
            self.assertNotEqual(pygame.image.tobytes(original,'RGB'),pygame.image.tobytes(oily,'RGB'))
            game.render()

    def test_contact_in_real_loop_emits_smoke_sound_and_recovers(self):
        game=self.game(GameMode.ENDLESS)
        oil=game.hazards.puddles[0]
        game.player.z=oil.z-S.CAMERA_HEIGHT*S.CAMERA_DEPTH
        game.player.x=oil.x
        game.update(1/60,{'accelerate':False,'brake':False,'steer':0})
        self.assertTrue(any(isinstance(e,OilSpinEffect) for e in game.player.effects))
        self.assertTrue(game.audio.last_played.get('skid') is not None)
        game.update(.05,{'accelerate':False,'brake':False,'steer':0})
        self.assertTrue(game.drift.smoke)
        for _ in range(130): game.update(1/60,{'accelerate':False,'brake':False,'steer':0})
        self.assertFalse(any(isinstance(e,OilSpinEffect) for e in game.player.effects))
        game.start_race()
        self.assertTrue(all(not oil.touched for oil in game.hazards.puddles))

    def test_fast_pass_and_ai_use_same_oil_collision_rule(self):
        game=self.game()
        oil=game.hazards.puddles[0]
        player=game.player
        player.z=oil.z-1500-S.CAMERA_HEIGHT*S.CAMERA_DEPTH
        player.x=oil.x
        game.hazards.update(.001,player)
        player.z+=3000
        game.hazards.update(.1,player)
        self.assertTrue(any(isinstance(e,OilSpinEffect) for e in player.effects))
        ai=game.manager.field.racers[0]
        ai.z,ai.x=oil.z,oil.x
        game.hazards.update(.01,player,[ai])
        self.assertTrue(any(isinstance(e,OilSpinEffect) for e in ai.effects))

    def test_shield_and_paint_feedback_for_generated_oil(self):
        from effects import ShieldEffect
        from unittest.mock import patch
        game=self.game()
        oil=game.hazards.puddles[0]
        player=game.player
        player.z=oil.z-S.CAMERA_HEIGHT*S.CAMERA_DEPTH
        player.x=oil.x
        player.add_effect(ShieldEffect())
        game.hazards.update(.01,player)
        self.assertFalse(any(isinstance(e,OilSpinEffect) for e in player.effects))
        self.assertEqual(game.hazards.pop_events(),['shield'])
        ai=game.manager.field.racers[0]
        ai.z,ai.x=oil.z,oil.x
        game.hazards.update(.01,player,[ai])
        ai._tick_effects(.9)
        with patch('racer.draw_car_rear') as draw:
            ai.draw(pygame.Surface((800,600)),400,400,100)
            self.assertAlmostEqual(draw.call_args.kwargs['yaw'],180)
