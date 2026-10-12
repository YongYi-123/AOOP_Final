import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
from unittest.mock import patch
import pygame
from puzzle_maze.game import Game,GameScene

class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.game=Game(headless=True)
        self.writer=patch('puzzle_maze.session.GameSession.save');self.saved=self.writer.start()

    def tearDown(self):self.writer.stop();pygame.quit()

    def key(self,key):self.game.event(pygame.event.Event(pygame.KEYDOWN,key=key))

    def test_six_second_intro_then_confirmation(self):
        self.game.choose('New expedition')
        self.assertEqual(self.game.scene,GameScene.INTRO)
        enemies=self.game.session.combat.capture()
        self.game.update(5.9);self.assertEqual(self.game.scene,GameScene.INTRO)
        self.game.update(.1);self.assertEqual(self.game.scene,GameScene.TUTORIAL)
        self.key(pygame.K_j);self.assertEqual(self.game.session.player.attack_flash,0)
        self.game.update(20);self.assertEqual(self.game.session.combat.capture(),enemies)
        self.key(pygame.K_RETURN);self.assertEqual(self.game.scene,GameScene.PLAY)
        self.game.update(.01);self.assertEqual(self.game.scene,GameScene.PLAY)

    def test_skip_animation_quick_start_and_cancel(self):
        self.game.start();self.key(pygame.K_RETURN)
        self.assertEqual(self.game.scene,GameScene.TUTORIAL)
        self.game.save();self.saved.assert_not_called()
        self.key(pygame.K_ESCAPE);self.assertEqual(self.game.scene,GameScene.MENU)
        self.game.choose('Quick start (skip tutorial)')
        self.assertEqual(self.game.scene,GameScene.PLAY)

    def test_continue_does_not_repeat_onboarding(self):
        with patch('puzzle_maze.game.GameSession.load',return_value=self.game.session):
            self.game.start(continuing=True)
        self.assertEqual(self.game.scene,GameScene.PLAY)
