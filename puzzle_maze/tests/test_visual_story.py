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
