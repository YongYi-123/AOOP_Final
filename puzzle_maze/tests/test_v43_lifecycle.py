"""Reward checkpoints, settled receipts and the existing free Arcade trial policy."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pygame
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
import test_v3_campaign as witness

HOST=Path(__file__).resolve().parents[2]/'arcade_lobby'
if str(HOST) not in sys.path:sys.path.append(str(HOST))

class Lifecycle43Tests(unittest.TestCase):
    def tearDown(self):pygame.quit()
    def test_death_retry_rolls_back_real_chest_rewards(self):
        s=AdvancedDungeonSession();s.enter('r18');d=witness.DungeonCampaignTests();d.s=s
        d.use('treasure');self.assertEqual((s.rewards.tokens,s.rewards.tickets),(10,15))
        s.combat.entry_protection=0
        while s.player.hp:
            s.player.invulnerable=0;self.assertTrue(s.combat.damage_player(SimpleNamespace(x=1,y=1)))
        self.assertIsNone(s.rewards.settle(False,False));s.reset()
        self.assertGreater(s.player.hp,0);self.assertEqual((s.rewards.tokens,s.rewards.tickets),(0,0))
        self.assertFalse(s.puzzles.objects['treasure'].state.active)
        d.use('treasure');self.assertEqual((s.rewards.tokens,s.rewards.tickets),(10,15))

    def test_victory_return_keeps_private_receipt_and_does_not_duplicate_lobby_rewards(self):
        from game import Game as HostGame
        from local_session import LocalSession
        from player_profile import PlayerProfile
        from room_testing import goto_room
        from puzzle_maze.lobby_scene import PuzzleMazeScene
        from puzzle_maze.game import GameScene
        profile=PlayerProfile(profile_id='maze43',tokens=0);before=profile.tokens,profile.tickets
        with patch('puzzle_maze.game.Game.save'):
            host=HostGame(session=LocalSession([profile]))
            try:
                room=goto_room(host,'arcade_floor');machine=next(m for m in room.machines if m.id=='puzzle_maze')
                room._start_game(machine,player=room.players[0])
                for _ in range(35):host.step([],1/60)
                scene=host.scenes.current;self.assertIsInstance(scene,PuzzleMazeScene)
                s=scene.maze.session;s.enter('r18');d=witness.DungeonCampaignTests();d.s=s
                d.use('treasure');d.use('dawn');d.travel('r27');d.use('royal_tokens');d.use('royal_tickets');d.use('royal_collection');d.walk(next(e['pos'] for e in s.rooms.data['exits'] if e.get('finish')))
                self.assertTrue(s.transition());receipt=s.rewards.settle(True,True)
                self.assertEqual((receipt['tokens'],receipt['tickets']),(1010,315))
                with tempfile.TemporaryDirectory() as folder:
                    path=Path(folder)/'run.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
                    self.assertTrue(loaded.finished);self.assertEqual(loaded.rewards.settle(True,True),receipt)
                scene.maze.scene=GameScene.VICTORY;scene.leave()
                for _ in range(40):host.step([],1/60)
                self.assertIs(host.scenes.current,room);room._end_play(True)
                self.assertEqual((profile.tokens,profile.tickets),before)
                self.assertEqual(scene.get_result().player_results,())
                self.assertEqual(s.rewards.settle(True,True),receipt)
            finally:host.quit()
