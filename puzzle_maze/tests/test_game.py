import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from collections import defaultdict
import pygame
from puzzle_maze.game import Game, GameScene
from puzzle_maze.audio import AudioManager

class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.game=Game(headless=True)
        self.save_patch=patch.object(self.game,'save');self.save_patch.start()

    def tearDown(self):
        self.save_patch.stop();pygame.quit()

    def key(self,key):
        self.game.event(pygame.event.Event(pygame.KEYDOWN,key=key))

    def test_menus_maps_and_all_rooms_render(self):
        for scene in GameScene:
            self.game.scene=scene;self.game.draw(.016)
        for name in self.game.session.rooms.rooms:
            self.game.session.enter(name)
            self.game.visual=[2.,7.];self.game.scene=GameScene.PLAY
            self.game.draw(.016)
        self.assertEqual(self.game.renderer.surface.get_size(),(320,240))

    def test_input_movement_pause_reset(self):
        self.key(pygame.K_RETURN)
        self.assertEqual(self.game.scene,GameScene.PLAY)
        self.game.cooldown=0
        keys=defaultdict(bool);keys[pygame.K_d]=True
        self.game.update(.05,keys)
        self.assertEqual(self.game.session.player.x,3)
        self.key(pygame.K_r);self.assertEqual(self.game.session.player.x,2)
        self.key(pygame.K_TAB);self.assertEqual(self.game.scene,GameScene.MAP)
        self.key(pygame.K_TAB);self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.scene,GameScene.PAUSE)
        self.key(pygame.K_ESCAPE);self.assertEqual(self.game.scene,GameScene.PLAY)

    def test_pause_freezes_clock(self):
        self.game.start();self.game.session.enter('r7')
        clock=self.game.session.puzzles.objects['clock']
        clock.state.remaining=3;clock.state.active=True
        self.game.scene=GameScene.PAUSE
        self.game.update(1)
        self.assertEqual(clock.state.remaining,3)

    def test_audio_device_failure_is_optional(self):
        with patch('pygame.mixer.init',side_effect=pygame.error('no device')):
            audio=AudioManager();audio.play('solve');audio.toggle()
            self.assertFalse(audio.enabled)
