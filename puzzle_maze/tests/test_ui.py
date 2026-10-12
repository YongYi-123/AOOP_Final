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
            for scene in (GameScene.MENU,GameScene.PLAY,GameScene.HELP,GameScene.MAP):
                game.scene=scene;game.draw(.016,target)
                self.assertTrue(game.renderer.ui.rects)
                self.assertTrue(all(target.get_rect().contains(rect) for rect in game.renderer.ui.rects))
        self.assertIn(30,game.renderer.ui.fonts)

    def test_bundled_traditional_chinese_glyphs(self):
        pygame.font.init()
        self.assertTrue(FONT_PATH.exists())
        font=pygame.font.Font(str(FONT_PATH),24)
        self.assertTrue(all(metric is not None for metric in font.metrics('迷宮生命光之鏡探索')))
