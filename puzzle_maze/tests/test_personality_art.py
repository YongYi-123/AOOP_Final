"""Readable optional content and safe native-scale jelly animation."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from puzzle_maze.slime_art import slime_frame
from puzzle_maze.developer_diaries import DIARIES
from puzzle_maze.lab_scene import LINES

class PersonalityTests(unittest.TestCase):
    def test_diaries_are_optional_and_not_required_for_room_exit(self):
        from puzzle_maze.remaster import RemasteredSession
        s=RemasteredSession();s.enter('r28')
        self.assertGreaterEqual(len(DIARIES),7)
        for key in DIARIES:self.assertTrue(s.puzzles.objects[key].data['optional'])
        self.assertEqual(s.rooms.data['exits'][0]['requires'],[])
        self.assertFalse(any('memory' in line.lower() or 'lost signal' in line.lower() for _,lines in LINES for line in lines))
    def test_slime_eyes_and_all_states_are_contained_and_connected(self):
        for state in ('idle','attack','defeat'):
            for frame in range(4):
                for hurt in (False,True):
                    s=slime_frame(state,frame,hurt);mask=pygame.mask.from_surface(s)
                    self.assertEqual(s.get_size(),(16,16));self.assertGreater(mask.count(),40)
                    self.assertEqual(len(mask.connected_components()),1)
                    if state!='defeat' and not (state=='idle' and frame==3):
                        ey=5+(0,1,0,-1)[frame]+3
                        for x in (5,10):self.assertEqual(tuple(s.get_at((x,ey+1)))[:3],(59,115,126))
    def test_every_diary_fits_the_production_reading_strip_at_three_sizes(self):
        from puzzle_maze.dev_preview import PreviewGame
        g=PreviewGame('developer-diaries',True)
        for size in ((640,480),(960,720),(1280,720)):
            g.screen=pygame.display.set_mode(size)
            for _ in DIARIES:
                g.next_note();g.draw(0);rects=g.renderer.ui.rects
                self.assertTrue(all(g.screen.get_rect().contains(r) for r in rects))
                self.assertTrue(all(not a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]))
