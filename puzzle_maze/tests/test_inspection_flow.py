"""The player observes first; Kevin's own document opens without losing input state."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from unittest import TestCase
from unittest.mock import Mock
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import GameScene
from puzzle_maze.studio_layout import approach
from puzzle_maze.tests.studio_flow import open_paper,close_inspection

class InspectionFlowTests(TestCase):
    def start_inspection(self,key):
        g=PreviewGame('developer-room',True);s=g.session
        pos,facing=approach(s.rooms.data,s.puzzles.objects[key].pos)
        s.player.x,s.player.y=pos;s.player.facing=facing;g.visual=list(map(float,pos));g.audio=Mock()
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
        return g

    def test_description_types_before_note_and_confirm_does_not_close_both(self):
        g=self.start_inspection('note');intro=g.inspection_intro
        self.assertEqual(g.scene,GameScene.SCROLL);self.assertEqual(intro.line.speaker,'PLAYER')
        self.assertEqual(intro.line.text,'This looks like an abandoned experiment log.')
        g.update(.1);g.audio.play.assert_called_with('vend_select')
        shown=intro.shown
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,repeat=True))
        self.assertEqual(intro.shown,shown)
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN));self.assertTrue(intro.done_typing)
        open_paper(g);self.assertEqual(g.scene,GameScene.SCROLL);self.assertIsNone(g.inspection_intro)
        g.draw(0)
        self.assertEqual(g.renderer.ui.commands[0][0],"KEVIN'S EXPERIMENT LOG")
        self.assertIn('1/7',[cmd[0] for cmd in g.renderer.ui.commands])
        close_inspection(g);self.assertEqual(g.scene,GameScene.PLAY)

    def test_page_counter_is_bottom_right_and_arrows_wait_for_note(self):
        g=self.start_inspection('studio_todo')
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT));self.assertEqual(g.reading_page,0)
        open_paper(g);g.draw(0)
        counter=next(cmd for cmd in g.renderer.ui.commands if cmd[0]=='1/3');self.assertGreaterEqual(counter[1],274)
        for _ in range(5):g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT))
        self.assertEqual(g.reading_page,2);g.draw(0)
        self.assertIn('3/3',[cmd[0] for cmd in g.renderer.ui.commands])
        for _ in range(5):g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_LEFT))
        self.assertEqual(g.reading_page,0)

    def test_board_uses_authored_responses_and_first_hand_documents_keep_their_voice(self):
        g=self.start_inspection('store_aoop')
        self.assertEqual(g.workshop_inspection.response.title,"KEVIN'S DESIGN BOARD")
        self.assertEqual(g.inspection_intro.line.speaker,'PLAYER')
        close_inspection(g);g.inspect_key('store_aoop')
        self.assertEqual(g.workshop_inspection.response.title,'PROJECT: GRAND THEFT ARCADE')
        from puzzle_maze.workshop_documents import DOCUMENTS
        for document in DOCUMENTS.values():
            for observation in document.observations:
                self.assertTrue(all(isinstance(text,str) and text for text in observation))
