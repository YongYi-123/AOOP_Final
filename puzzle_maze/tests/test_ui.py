import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.ui import FONT_PATH

class NativeUITests(unittest.TestCase):
    def tearDown(self):pygame.quit()

    def test_native_layout_at_different_sizes(self):
        game=Game(headless=True)
        for size in ((320,240),(640,480),(960,720),(1000,700),(240,180)):
            target=pygame.Surface(size)
            for scene in (GameScene.MENU,GameScene.PLAY,GameScene.HELP,GameScene.MAP,GameScene.INTRO,GameScene.TUTORIAL,GameScene.GAMEOVER):
                game.scene=scene;game.draw(.016,target)
                self.assertTrue(game.renderer.ui.rects)
                self.assertTrue(all(target.get_rect().contains(rect) for rect in game.renderer.ui.rects))
        self.assertIn((33,False),game.renderer.ui.fonts)

    def test_bundled_english_glyphs(self):
        pygame.font.init()
        self.assertTrue(FONT_PATH.exists())
        font=pygame.font.Font(str(FONT_PATH),24)
        self.assertTrue(all(metric is not None for metric in font.metrics('Basic Sword J E SPACE 0123456789')))

    def test_modal_text_does_not_leak_world_hud(self):
        game=Game(headless=True)
        for scene in (GameScene.HELP,GameScene.MAP,GameScene.GAMEOVER):
            game.scene=scene;game.draw(.016)
            self.assertFalse(any('H Potion' in command[0] or 'Dash 0.0' in command[0] for command in game.renderer.ui.commands))

    def test_all_displayed_strings_are_english(self):
        game=Game(headless=True)
        for scene in GameScene:
            game.scene=scene;game.draw(.016)
            self.assertTrue(all(command[0].isascii() for command in game.renderer.ui.commands))
