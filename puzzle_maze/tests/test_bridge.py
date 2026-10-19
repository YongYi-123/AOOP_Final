"""Optional bridge regression without editing or saving any host module."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
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

    def test_second_player_bindings_match_tutorial_and_attack(self):
        from controls import P2_CONTROLS
        from input_router import PlayerInput
        class Participant:
            profile=SimpleNamespace(profile_id='test_p2')
        scene=self.scene()
        scene.game.session=SimpleNamespace(input=SimpleNamespace(input_for=lambda p:PlayerInput(P2_CONTROLS)))
        scene.attach_players([Participant()])
        c=scene.maze.tutorial.controls
        self.assertEqual((c['attack'],c['ability'],c['dash']),('K','KP0','RSHIFT'))
        scene.maze.scene=GameScene.PLAY;e=scene.maze.session.combat.enemies[0];p=scene.maze.session.player
        p.x,p.y=e.x-1,e.y;p.facing=(1,0)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_j))
        self.assertEqual(e.hp,2)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_k))
        self.assertEqual(e.hp,1)

    def test_original_cabinet_loads_v4_and_routes_powder_pots_and_bombs(self):
        from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
        scene=self.scene();self.assertIsInstance(scene.maze.session,AdvancedDungeonSession)
        self.assertEqual(len(scene.maze.session.rooms.rooms),26)
        scene.maze.start(onboarding=False);s=scene.maze.session
        s.inventory.abilities.update(('powder','gloves'));s.inventory.powder=5;s.enter('r19')
        s.player.x,s.player.y=7,6;s.player.facing=(0,-1)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p));self.assertEqual(s.inventory.powder,4)
        s.enter('r20');s.player.x,s.player.y=5,6;s.player.facing=(1,0)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e));self.assertEqual(s.inventory.carried,'jar')
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_g));self.assertIsNone(s.inventory.carried)
        s.inventory.bombs=3;scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_b));self.assertEqual(s.inventory.bombs,2)
        scene.maze.scene=GameScene.MENU;scene.draw(pygame.Surface((960,720)))
        self.assertTrue(any('4.3' in command[0] for command in scene.maze.renderer.ui.commands))
        self.assertEqual(scene.get_result().player_results,())

    def test_real_original_cabinet_v4_onboarding_p2_and_safe_return(self):
        from game import Game as HostGame
        from local_session import LocalSession
        from player_profile import PlayerProfile
        from room_testing import goto_room
        from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
        profiles=[PlayerProfile(profile_id='maze_bridge_a',tokens=0),PlayerProfile(profile_id='maze_bridge_b',tokens=0)]
        balances=[(p.tokens,p.tickets) for p in profiles]
        with patch('puzzle_maze.game.Game.save'):
            host=HostGame(session=LocalSession(profiles))
            try:
                room=goto_room(host,'arcade_floor');machine=next(m for m in room.machines if m.id=='puzzle_maze')
                room._start_game(machine,player=room.players[1])
                for _ in range(35):host.step([],1/60)
                scene=host.scenes.current;self.assertIsInstance(scene,PuzzleMazeScene)
                self.assertIsInstance(scene.maze.session,AdvancedDungeonSession)
                for expected in (GameScene.INTRO,GameScene.TUTORIAL,GameScene.PLAY):
                    host.step([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,mod=0)],1/60)
                    self.assertEqual(scene.maze.scene,expected)
                s=scene.maze.session;s.inventory.abilities.add('powder');s.inventory.powder=5;s.enter('r19')
                s.player.x,s.player.y=7,6;s.player.facing=(0,-1)
                host.step([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p,mod=0)],1/60)
                self.assertEqual(s.inventory.powder,4)
                self.assertTrue(any('K Crystal' in line for line in scene.maze.tutorial.lines()))
                scene.maze.choose('Return to arcade');scene.leave()
                for _ in range(35):host.step([],1/60)
                self.assertIs(host.scenes.current,room)
                self.assertEqual([(p.tokens,p.tickets) for p in profiles],balances)
                self.assertTrue(all('puzzle_maze' not in p.high_scores for p in profiles))
            finally:host.quit()
