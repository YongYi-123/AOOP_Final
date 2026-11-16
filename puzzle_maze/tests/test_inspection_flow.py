"""Object description precedes paper content; pages and modal input remain explicit."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from unittest import TestCase
from unittest.mock import Mock
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import GameScene
from puzzle_maze.studio_layout import approach
from puzzle_maze.studio_notes import DESCRIPTIONS,inspection_dialogue
from puzzle_maze.tests.studio_flow import open_paper

class InspectionFlowTests(TestCase):
    def start_inspection(self,key):
        g=PreviewGame('developer-room',True);s=g.session
        pos,facing=approach(s.rooms.data,s.puzzles.objects[key].pos)
        s.player.x,s.player.y=pos;s.player.facing=facing;g.visual=list(map(float,pos))
        g.audio=Mock()
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
        return g

    def test_description_types_before_page_and_confirm_does_not_close_both(self):
        g=self.start_inspection('work_crt');intro=g.inspection_intro
        self.assertEqual(g.scene,GameScene.SCROLL);self.assertEqual(intro.line.speaker,'PLAYER')
        self.assertIn('sticky note',intro.line.text)
        self.assertEqual(intro.shown,0)
        g.update(.1);self.assertGreater(intro.shown,0)
        g.audio.play.assert_called_with('vend_select')
        g.draw(0);self.assertEqual(g.renderer.ui.commands,[])
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,repeat=True))
        self.assertFalse(intro.done_typing)
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        self.assertTrue(intro.done_typing);self.assertIs(g.inspection_intro,intro)
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        self.assertIsNone(g.inspection_intro);self.assertEqual(g.scene,GameScene.SCROLL)
        g.draw(0)
        self.assertEqual(g.renderer.ui.commands[0][0],'THE CRACKED CRT')
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        self.assertEqual(g.scene,GameScene.PLAY)

    def test_page_counter_is_separate_at_bottom_right_and_arrows_wait_for_page(self):
        g=self.start_inspection('studio_todo')
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT))
        self.assertEqual(g.reading_page,0)
        open_paper(g);g.draw(0)
        counter=next(cmd for cmd in g.renderer.ui.commands if cmd[0]=='1/4')
        self.assertGreaterEqual(counter[1],270)
        for _ in range(3):g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT))
        self.assertEqual(g.reading_page,3);g.draw(0)
        self.assertIn('4/4',[cmd[0] for cmd in g.renderer.ui.commands])
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT,repeat=True))
        self.assertEqual(g.reading_page,3)

    def test_all_descriptions_fit_without_truncation_and_board_has_two_pages(self):
        for key in DESCRIPTIONS:
            d=inspection_dialogue(key)
            self.assertEqual(' '.join(d._rows()),d.line.text,key)
        g=self.start_inspection('store_aoop')
        self.assertIn('cat doodle',g.inspection_intro.line.text)
        open_paper(g);g.draw(0)
        self.assertIn('1/2',[cmd[0] for cmd in g.renderer.ui.commands])
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT));g.draw(0)
        self.assertIn('2/2',[cmd[0] for cmd in g.renderer.ui.commands])
