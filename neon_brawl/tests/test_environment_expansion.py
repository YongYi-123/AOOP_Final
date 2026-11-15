import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
from neon_brawl.ambient import AmbientCats,cat_sprite
from neon_brawl.model import Campaign

class StreetCatTests(unittest.TestCase):
    def test_cats_are_occasional_bounded_and_have_multiple_appearances(self):
        cats=AmbientCats();cats.update(.05,4,0,0,80,[]);self.assertIsNone(cats.cat)
        cats.update(.05,5,0,0,80,[]);self.assertIsNotNone(cats.cat)
        self.assertFalse(hasattr(cats.cat,'health'));self.assertFalse(hasattr(cats.cat,'damage'))
        import pygame
        self.assertEqual(len({pygame.image.tobytes(cat_sprite(i,'walk',0,1),'RGBA') for i in range(3)}),3)
    def test_combat_scares_cats_without_hurting_them(self):
        from neon_brawl.model import EnemyFighter
        cats=AmbientCats();e=EnemyFighter('grunt',80,220);e.tick(2);e.attack('enemy')
        cats.update(.05,6,0,0,100,[e]);self.assertEqual(cats.cat.state,'flee')
        for i in range(45):cats.update(.05,6+i*.05,0,0,100,[e])
        self.assertIsNone(cats.cat)
    def test_no_cats_in_metro_or_core_and_never_in_combat_targets(self):
        c=Campaign();c.cats.update(.05,6,0,0,80,[]);c.spawn()
        self.assertNotIn(c.cats.cat,c.enemies)
        for stage in (1,2):
            c.cats.update(.05,10,stage,0,80,c.enemies);self.assertIsNone(c.cats.cat)
    def test_pause_freezes_ambient_behavior(self):
        from neon_brawl.game import BrawlGame
        from font import get_font
        b=BrawlGame(get_font());b.campaign=Campaign();b.change('playing')
        b.campaign.elapsed=6;b.update(.05);cat=b.campaign.cats.cat
        before=(cat.x,cat.age,cat.state);b.pause();b.update(.05)
        self.assertEqual((cat.x,cat.age,cat.state),before)

class ExpandedEnvironmentTests(unittest.TestCase):
    def test_thirteen_distinct_sets_and_bounded_caches(self):
        import pygame
        from neon_brawl.art import background
        images=[pygame.image.tobytes(background(stage,1,section),'RGB')
                for stage in range(3) for section in range(5 if stage==2 else 4)]
        self.assertEqual(len(set(images)),13)
        self.assertLessEqual(background.cache_info().currsize,28)
    def test_render_animation_and_phase_changes_never_mutate_combat(self):
        import pygame
        from font import get_font
        from neon_brawl.art import Renderer
        from neon_brawl.scenery import visual_section
        r=Renderer(get_font());s=pygame.Surface((400,300));c=Campaign()
        c.stage=2;c.wave=3;c.player.x=1130;c.camera=1050;c.spawn()
        boss=c.enemies[0]
        before=(c.player.health,c.score,c.elapsed,[(e.x,e.y,e.health,e.power) for e in c.enemies])
        self.assertEqual(visual_section(c),3);r.world(s,c,0)
        boss.phase=2;self.assertEqual(visual_section(c),4);r.world(s,c,1)
        self.assertIsNotNone(r.previous_background)
        for i in range(70):r.world(s,c,1+i/60)
        self.assertIsNone(r.previous_background)
        self.assertEqual(before,(c.player.health,c.score,c.elapsed,[(e.x,e.y,e.health,e.power) for e in c.enemies]))
        self.assertEqual(s.get_clip(),s.get_rect())
    def test_background_blending_reuses_frames_between_transitions(self):
        import pygame
        from font import get_font
        from neon_brawl.art import Renderer
        r=Renderer(get_font());s=pygame.Surface((400,300));c=Campaign();c.spawn()
        frame=r.background_frame;r.world(s,c,0);r.world(s,c,.1)
        self.assertIs(frame,r.background_frame);self.assertIsNone(r.previous_background)
        c.wave=1;r.world(s,c,1);old=r.previous_background;r.world(s,c,1.1)
        self.assertIs(old,r.previous_background)
