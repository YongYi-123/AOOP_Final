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

class MemoryTimingTests(unittest.TestCase):
    def test_walk_pause_dialogue_and_skip(self):
        from puzzle_maze.lab_scene import LabEntrance,LINES
        scene=LabEntrance();self.assertEqual(scene.position,(24,120));scene.advance();self.assertEqual(scene.line,0)
        scene.update(2);self.assertFalse(scene.ready);self.assertGreater(scene.position[0],24)
        scene.update(3.3);self.assertTrue(scene.ready);self.assertEqual(scene.position,(136,136))
        for _ in LINES:scene.update(.3);scene.advance()
        self.assertTrue(scene.done)
        scene=LabEntrance();scene.advance(skip=True);self.assertTrue(scene.done)

    def test_persisted_memory_and_optional_objects(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from puzzle_maze.remaster import RemasteredSession
        s=RemasteredSession();s.enter('r28');s.lab_memory_seen=True
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'save.json';s.save(p);loaded=RemasteredSession.load(p)
        self.assertTrue(loaded.lab_memory_seen);self.assertIn('gpu',loaded.puzzles.objects)
