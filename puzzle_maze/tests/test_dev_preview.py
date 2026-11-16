"""Exercise the real production preview while forbidding profile/save writes."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from puzzle_maze.tests.studio_flow import open_paper
import pygame
from puzzle_maze.dev_preview import PreviewGame,TARGETS
from puzzle_maze.game import GameScene

class PreviewTests(unittest.TestCase):
    def key(self,g,key,repeat=False):g.event(pygame.event.Event(pygame.KEYDOWN,key=key,repeat=repeat))
    def test_all_targets_use_the_actual_campaign_and_render(self):
        for target in TARGETS:
            g=PreviewGame(target,True);g.update(.01);g.draw(0)
            self.assertFalse(g.persistent);self.assertIsNone(g.profile_store)
            self.assertTrue(g.session.grey_pixel)
            self.assertEqual(g.scene,GameScene.DISCOVERY if target=='grey-pixel' else GameScene.MEMORY if target=='miao-entrance' else GameScene.SCROLL if target=='kevin-notes' else GameScene.PLAY)
    def test_skip_walk_dialogue_replay_and_exit(self):
        g=PreviewGame(headless=True);self.key(g,pygame.K_SPACE);g.update(.01)
        self.assertEqual(g.session.rooms.current,'r28');self.assertEqual(g.scene,GameScene.MEMORY)
        g.update(5.6);self.key(g,pygame.K_RETURN);self.assertEqual(g.lab_entrance.line,0)
        g.update(4.5);self.key(g,pygame.K_RETURN);self.assertEqual(g.lab_entrance.line,0)
        self.assertTrue(g.lab_entrance.dialogue.done_typing)
        g.update(.3);self.key(g,pygame.K_RETURN);self.assertEqual(g.lab_entrance.line,1)
        self.key(g,pygame.K_SPACE);self.assertTrue(g.session.lab_memory_seen)
        self.key(g,pygame.K_F7);g.update(.01);self.assertEqual(g.lab_entrance.time,0)
        self.key(g,pygame.K_F5);self.assertEqual(g.scene,GameScene.DISCOVERY)
        self.key(g,pygame.K_r);self.assertEqual(g.grey_reveal.time,0)
        self.key(g,pygame.K_ESCAPE);self.assertFalse(g.running)
    def test_diary_and_real_room_exit(self):
        g=PreviewGame('developer-diaries',True);self.key(g,pygame.K_e)
        self.assertEqual(g.scene,GameScene.SCROLL);self.assertEqual(g.reading,'dev_001')
        open_paper(g)
        self.key(g,pygame.K_RETURN);self.assertEqual(g.scene,GameScene.PLAY)
        g.session.player.x=1;g.session.player.y=7
        self.assertTrue(g.session.transition());self.assertEqual(g.session.rooms.current,'r24')
    def test_no_real_save_or_profile_access_even_on_restart_and_close(self):
        from puzzle_maze.remaster import RemasteredSession
        with TemporaryDirectory() as folder:
            sentinel=Path(folder)/'real-profile.json';sentinel.write_bytes(b'player progress untouched')
            before=sentinel.read_bytes()
            with patch.object(RemasteredSession,'save',side_effect=AssertionError('preview wrote a save')),patch.object(RemasteredSession,'load',side_effect=AssertionError('preview read a save')):
                g=PreviewGame(headless=True);g.bind_profile('real',root=folder);g.save()
                self.key(g,pygame.K_SPACE);g.update(.01);self.key(g,pygame.K_SPACE)
                g.start(continuing=True,onboarding=False);g.save();g.event(pygame.event.Event(pygame.QUIT))
            self.assertEqual(sentinel.read_bytes(),before);self.assertEqual(list(Path(folder).iterdir()),[sentinel])

    def test_all_ten_notes_use_real_interactions_and_repeat_keys_do_not_skip(self):
        from puzzle_maze.developer_diaries import DIARIES
        g=PreviewGame('developer-diaries',True)
        for key in DIARIES:
            self.key(g,pygame.K_F8);self.assertEqual(g.reading,key);self.assertEqual(g.scene,GameScene.SCROLL)
            self.assertIn(key,g.session.lore)
            before=g.note_index;self.key(g,pygame.K_F8,repeat=True);self.assertEqual(g.note_index,before)
        self.assertTrue(DIARIES.keys()<=g.session.lore)

    def test_windowed_constructor_never_binds_a_real_profile(self):
        from puzzle_maze.game import Game
        with patch.object(Game,'bind_profile',side_effect=AssertionError('real profile binding')):
            g=PreviewGame('developer-room',False)
            self.assertFalse(g.persistent);self.key(g,pygame.K_ESCAPE)

    def test_documented_module_entrypoint_accepts_every_target(self):
        import subprocess,sys
        for target in TARGETS:
            result=subprocess.run([sys.executable,'-m','puzzle_maze','--dev-preview',target,'--headless','--frames','1'],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_exit_uses_the_actual_game_movement_and_transition(self):
        from collections import defaultdict
        g=PreviewGame('developer-room',True);g.session.player.x=2;g.session.player.y=7;g.visual=[2.,7.]
        g.update(.14,defaultdict(bool,{pygame.K_LEFT:True}))
        self.assertEqual(g.session.rooms.current,'r24');self.assertTrue(g.session.grey_pixel)
        self.assertFalse(g.persistent);g.draw(.016)
