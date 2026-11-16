"""Moving Miao and every patch of exposed concrete remain usable in production."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import math
from collections import deque
from unittest import TestCase
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.studio_layout import ENTRY,contact_blocked
from puzzle_maze.studio_interactions import nearby,object_anchor

class CompanionTests(TestCase):
    def test_roaming_following_naps_and_waking_use_legal_floor_and_live_interactions(self):
        g=PreviewGame('developer-room',True);s=g.session;c=s.studio_companion
        s.player.x,s.player.y=10,12
        states=set();positions=set()
        for _ in range(70*30):
            s.tick(1/30);states.add(c.state);positions.add((round(c.x),round(c.y)))
            self.assertFalse(contact_blocked(c.x,c.y,s.rooms.data['solid_footprints']))
            self.assertTrue(16<=c.x<=304 and 48<=c.y<=224)
            self.assertEqual(s.puzzles.objects['miao'].pos,c.tile)
        self.assertGreater(len(positions),60)
        self.assertTrue({'wander','follow','sleep','idle'}<=states,states)
        c.time=35;c.x,c.y=168.,128.;s.player.x,s.player.y=10,12;s.tick(.03)
        self.assertEqual(c.state,'sleep')
        s.player.x,s.player.y=10,8;s.tick(.03)
        self.assertNotEqual(c.state,'sleep')
        s.player.x,s.player.y=c.tile;s.tick(0)
        self.assertEqual(nearby(s)[0],'miao')
        self.assertEqual(object_anchor(s,'miao'),(c.x,c.y-18))
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
        self.assertEqual(g.reading,'miao_memory')

    def test_open_floor_is_walkable_connected_and_no_static_cat_block_remains(self):
        s=PreviewGame('developer-room',True).session;room=s.rooms.data
        for y in range(3,14):
            for x in range(1,19):
                if not contact_blocked(x*16+8,y*16+16,room['solid_footprints']):
                    self.assertTrue(s.can_enter(x,y),(x,y))
        q=deque([ENTRY]);seen={ENTRY}
        while q:
            x,y=q.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                tile=(x+dx,y+dy)
                if tile not in seen and s.can_enter(*tile):seen.add(tile);q.append(tile)
        self.assertGreater(len(seen),155)
        self.assertTrue({(1,7),(3,13),(10,12),(16,13),(10,7)}<=seen)

    def test_miao_can_yield_if_player_steps_into_her_position(self):
        s=PreviewGame('developer-room',True).session;c=s.studio_companion
        s.player.x,s.player.y=c.tile;start=c.position
        for _ in range(120):s.tick(1/30)
        self.assertGreater(math.dist(start,c.position),17)
        self.assertTrue(s.can_enter(10,7))

    def test_saving_after_miao_moves_keeps_room_progress_loadable(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        s=PreviewGame('developer-room',True).session
        s.player.x,s.player.y=10,12
        for _ in range(180):s.tick(1/30)
        self.assertNotEqual(s.studio_companion.tile,(10,7))
        s.read_lore('kevin_photo')
        with TemporaryDirectory() as directory:
            path=Path(directory)/'moving-miao.json';s.save(path)
            restored=type(s).load(path)
            self.assertEqual(restored.rooms.current,'r28')
            self.assertEqual(restored.lore,s.lore);self.assertTrue(restored.grey_pixel)
            self.assertEqual((restored.player.x,restored.player.y),(10,12))
            restored.tick(.03)
            self.assertEqual(restored.puzzles.objects['miao'].pos,restored.studio_companion.tile)
            s.enter('r24',(22,8));s.save(path)
            restored=type(s).load(path)
            self.assertEqual(restored.rooms.current,'r24');self.assertEqual(restored.lore,s.lore)
            restored.enter('r28',(6,8));restored.tick(.03)
            self.assertEqual(restored.puzzles.objects['miao'].pos,restored.studio_companion.tile)

    def test_sleep_and_walk_frames_are_visibly_distinct(self):
        from puzzle_maze.miao_adapter import guide_frame
        frames=[guide_frame(False,35,sleeping=True),guide_frame(True,.2),guide_frame(False,0)]
        self.assertEqual(len({pygame.image.tobytes(frame,'RGBA') for frame in frames}),3)
