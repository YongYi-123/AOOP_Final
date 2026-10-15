"""Free trial cabinet uses the lobby window and returns without a payout."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
from unittest.mock import patch
import pygame
from game import Game
from local_session import LocalSession
from player_profile import PlayerProfile
from room_testing import goto_room
from scenes import minigame_definition
from puzzle_maze.lobby_scene import PuzzleMazeScene
from puzzle_maze.game import GameScene

class PuzzleMazeLobbyTests(unittest.TestCase):
    def start(self,two=False,starter=0):
        saves=patch('puzzle_maze.game.Game.save');saves.start();self.addCleanup(saves.stop)
        self.profiles=[PlayerProfile(profile_id='maze_a',tokens=0)]
        if two:self.profiles.append(PlayerProfile(profile_id='maze_b',tokens=0))
        self.game=Game(session=LocalSession(self.profiles));self.addCleanup(self.game.quit)
        self.room=goto_room(self.game,'arcade_floor')
        self.machine=next(m for m in self.room.machines if m.id=='puzzle_maze')
        window=pygame.display.get_surface()
        with patch('pygame.display.set_mode',wraps=pygame.display.set_mode) as display, patch('pygame.mixer.init',wraps=pygame.mixer.init) as mixer:
            self.room._start_game(self.machine,player=self.room.players[starter])
            self.frames(30)
            display.assert_not_called();mixer.assert_not_called()
        self.scene=self.game.scenes.current
        self.assertIsInstance(self.scene,PuzzleMazeScene)
        self.assertIs(window,pygame.display.get_surface())

    def begin(self):
        # title menu -> intro -> controls card -> play (the 4.x onboarding adds the middle two screens)
        for _ in range(3):self.frames(1,pygame.K_RETURN)
        self.assertEqual(self.scene.maze.scene,GameScene.PLAY)

    def frames(self,count,key=None,up=False):
        events=[] if key is None else [pygame.event.Event(pygame.KEYUP if up else pygame.KEYDOWN,key=key,mod=0)]
        for i in range(count):self.game.step(events if i==0 else [],1/60)

    def test_free_launch_controls_and_return(self):
        self.start()
        self.assertEqual(self.machine.play_cost,0)
        self.assertFalse(minigame_definition('puzzle_maze').supports(2))
        self.begin()
        self.frames(25,pygame.K_d);self.frames(1,pygame.K_d,True)
        self.assertGreater(self.scene.maze.session.player.x,2)
        self.frames(1,pygame.K_r)
        self.assertEqual(self.scene.maze.session.player.x,2)
        self.frames(1,pygame.K_TAB)
        self.assertEqual(self.scene.maze.scene,GameScene.MAP)
        self.frames(1,pygame.K_TAB);self.frames(1,pygame.K_ESCAPE)
        self.assertEqual(self.scene.maze.scene,GameScene.PAUSE)
        self.scene.maze.selection=len(self.scene.maze.options())-1
        self.frames(1,pygame.K_RETURN);self.frames(40)
        self.assertIs(self.game.scenes.current,self.room)
        self.assertEqual(self.profiles[0].tokens,0)
        self.assertEqual(self.profiles[0].tickets,PlayerProfile().tickets)
        self.assertNotIn('puzzle_maze',self.profiles[0].high_scores)

    def test_title_escape_returns(self):
        self.start();self.frames(1,pygame.K_ESCAPE);self.frames(40)
        self.assertIs(self.game.scenes.current,self.room)

    def test_second_player_owns_controls(self):
        self.start(two=True,starter=1);self.begin()
        self.frames(30,pygame.K_d);self.frames(1,pygame.K_d,True)
        self.assertEqual(self.scene.maze.session.player.x,2)
        self.frames(25,pygame.K_RIGHT);self.frames(1,pygame.K_RIGHT,True)
        self.assertGreater(self.scene.maze.session.player.x,2)
        self.assertEqual(self.scene.participants,[self.profiles[1]])
