"""Optional bridge regression without editing or saving any host module."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import pygame

HOST=Path(__file__).resolve().parents[2]/'arcade_lobby'
if str(HOST) not in sys.path:sys.path.append(str(HOST))
from puzzle_maze.lobby_scene import PuzzleMazeScene
from puzzle_maze.game import GameScene

class BridgeTests(unittest.TestCase):
    def tearDown(self):pygame.quit()

    def scene(self):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960,720))
        host=SimpleNamespace(audio=SimpleNamespace(play=Mock()),scenes=SimpleNamespace(pop=Mock()))
        return PuzzleMazeScene(host,SimpleNamespace(id='puzzle_maze',name='Puzzle Maze'))

    def test_attack_key_reaches_existing_bridge(self):
        scene=self.scene();scene.maze.scene=GameScene.PLAY
        e=scene.maze.session.combat.enemies[0];p=scene.maze.session.player
        p.x,p.y=e.x-1,e.y;p.facing=(1,0)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_j))
        self.assertEqual(e.hp,1)
        self.assertGreater(p.attack_flash,0)

    def test_full_resolution_text_is_not_upscaled_by_host(self):
        scene=self.scene();target=pygame.Surface((960,720))
        scene.draw(target)
        self.assertTrue(scene.full_resolution)
        self.assertIn((33,False),scene.maze.renderer.ui.fonts)

    def test_existing_bridge_routes_tools_and_dash(self):
        scene=self.scene();scene.maze.scene=GameScene.PLAY
        scene.maze.session.inventory.abilities.update({'boots','magnet'})
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_q))
        self.assertEqual(scene.maze.tool,'magnet')
        scene.maze.session.player.facing=(1,0)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_LSHIFT))
        self.assertEqual(scene.maze.session.player.x,5)
