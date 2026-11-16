"""Kevin authors his papers; the presentation points to the actual object."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from unittest import TestCase
from unittest.mock import patch
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import Game
from puzzle_maze.studio_interactions import object_anchor
from puzzle_maze.studio_notes import pages_for

class KevinJournalTests(TestCase):
    def test_written_pages_are_first_person_and_fit_the_bitmap_budget(self):
        from puzzle_maze.pixel_font import render
        from puzzle_maze.workshop_documents import DOCUMENTS
        for key,doc in DOCUMENTS.items():
            text=' '.join(' '.join(page.paragraphs) for page in doc.pages)
            self.assertTrue(any(word in text for word in ('I ','my ','My ')),key)
            self.assertNotIn('Kevin',text,key)
        from puzzle_maze.developer_diaries import DIARY_PAGES
        for key,pages in DIARY_PAGES.items():
            for page in pages:
                for line in page:self.assertLessEqual(render('  '+line,33,(255,255,255)).get_width(),732)
        self.assertGreater(len(pages_for('dev_001')),1)
        self.assertGreater(len(pages_for('dev_002')),1)

    def test_prompt_stays_beside_each_selected_object_and_tracks_miao(self):
        g=PreviewGame('developer-room',True)
        for key in list(g.session.puzzles.objects):
            g.inspect_key(key)
            from puzzle_maze.tests.studio_flow import close_inspection
            close_inspection(g)
            g.draw(.2)
            anchor=object_anchor(g.session,key);rect=g.renderer.studio_prompt_rect
            self.assertEqual(g.renderer.studio_prompt_target,key)
            self.assertEqual(g.renderer.studio_prompt.anchor,anchor)
            self.assertTrue(pygame.Rect(0,0,320,240).contains(rect))
            dx=max(rect.left-anchor[0],0,anchor[0]-rect.right)
            dy=max(rect.top-anchor[1],0,anchor[1]-rect.bottom)
            self.assertLessEqual(dx+dy,8,(key,anchor,rect))
        c=g.session.studio_companion;c.x,c.y=232.,128.
        miao=g.session.puzzles.objects['miao'];miao.x,miao.y=c.tile
        g.session.player.x,g.session.player.y=14,8;g.visual=[14.,8.];g.draw(.2)
        self.assertEqual(g.renderer.studio_prompt_target,'miao')
        self.assertEqual(g.renderer.studio_prompt.anchor,(232.,110.))

    def test_preview_discovery_has_no_extra_function_key_banner(self):
        g=PreviewGame('grey-pixel',True);g.update(3)
        production=pygame.Surface((960,720));preview=pygame.Surface((960,720))
        Game.draw(g,0,production);g.draw(0,preview)
        self.assertEqual(pygame.image.tobytes(production,'RGB'),pygame.image.tobytes(preview,'RGB'))

    def test_grey_pixel_title_is_centered_at_window_and_letterbox_sizes(self):
        g=PreviewGame('grey-pixel',True);g.update(3)
        for size in ((640,480),(960,720),(1280,720),(500,500)):
            g.draw(0,pygame.Surface(size))
            index=next(i for i,cmd in enumerate(g.renderer.ui.commands) if cmd[0]=='GREY PIXEL')
            self.assertLessEqual(abs(g.renderer.ui.rects[index].centerx-size[0]/2),1,size)

    def test_golden_age_door_is_confined_to_the_side_wall(self):
        from puzzle_maze.workshop_art import WorkshopArt
        baseline=WorkshopArt().floor()
        marker=pygame.Surface((20,54),pygame.SRCALPHA);marker.fill((240,240,240))
        with patch('golden_age_art.door',return_value=marker) as door:
            changed=WorkshopArt().floor()
        door.assert_called_once()
        floor=pygame.Rect(16,48,288,185)
        self.assertEqual(pygame.image.tobytes(changed.subsurface(floor),'RGB'),pygame.image.tobytes(baseline.subsurface(floor),'RGB'))
        self.assertNotEqual(pygame.image.tobytes(changed.subsurface((0,104,16,44)),'RGB'),pygame.image.tobytes(baseline.subsurface((0,104,16,44)),'RGB'))
