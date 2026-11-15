"""Progression, telegraph fairness, clothing and cinematic regression."""
import os
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from neon_brawl.art import sprite
from neon_brawl.outfits import OUTFITS

class OutfitTests(unittest.TestCase):
    def test_each_family_has_structural_clothing_variations(self):
        for name,pool in OUTFITS.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(len(pool),4)
                frames=[sprite(name,'idle',0,1,i) for i in range(len(pool))]
                self.assertEqual(len({pygame.image.tobytes(s,'RGBA') for s in frames}),len(pool))
                self.assertGreaterEqual(len({pygame.mask.from_surface(s).count() for s in frames}),3)
    def test_clothes_follow_facing_and_animation_without_changing_canvas(self):
        for name,pool in OUTFITS.items():
            for index in range(len(pool)):
                for state in ('walk','enemy','hurt','knockdown'):
                    for frame in range(4):
                        right=sprite(name,state,frame,1,index)
                        left=sprite(name,state,frame,-1,index)
                        self.assertEqual(right.get_size(),(64,64))
                        self.assertEqual(pygame.image.tobytes(left,'RGBA'),
                                         pygame.image.tobytes(pygame.transform.flip(right,True,False),'RGBA'))
    def test_bosses_have_original_silhouettes(self):
        images=[sprite(n) for n in ('WARDEN','RELAY','NULL','grunt')]
        self.assertEqual(len({pygame.mask.from_surface(s).count() for s in images}),4)
