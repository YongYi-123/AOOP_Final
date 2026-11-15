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
