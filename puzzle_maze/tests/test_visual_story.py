"""Pixel identity, scene timing and non-destructive presentation regression."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from puzzle_maze.lab_hardware import equipment

class HardwareArtTests(unittest.TestCase):
    def test_equipment_is_distinct_cached_and_within_native_canvas(self):
        kinds=('crt','display','keyboard','gpu','cpu','ram','motherboard','case','scope','solder','meter','disk')
        images=[equipment(k) for k in kinds]
        self.assertEqual(len({pygame.image.tobytes(s,'RGBA') for s in images}),len(kinds))
        for kind,s in zip(kinds,images):
            self.assertEqual(s.get_size(),(42,38));self.assertIs(s,equipment(kind))
            self.assertGreater(pygame.mask.from_surface(s).count(),90)

    def test_lobby_character_pixels_are_reused(self):
        from puzzle_maze.miao_adapter import guide_frame
        guide_frame()
        from miao_meow import miao_frame,facing_frame
        self.assertIs(guide_frame(),facing_frame(miao_frame('sit','open',tail=0,legs=0,level=3),'right'))

    def test_studio_is_cached_and_opaque(self):
        from puzzle_maze.developer_art import DeveloperRoomArt
        art=DeveloperRoomArt();s=art.layer()
        self.assertEqual(s.get_size(),(416,256));self.assertIs(s,art.layer())
        self.assertEqual(s.get_at((200,120)).a,255)
