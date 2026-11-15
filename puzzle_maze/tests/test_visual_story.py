"""Pixel identity, scene timing and non-destructive presentation regression."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from puzzle_maze.lab_hardware import equipment

class HardwareArtTests(unittest.TestCase):
    def test_equipment_is_distinct_cached_and_within_native_canvas(self):
        kinds=('crt','display','keyboard','gpu','cpu','ram','motherboard','case','scope','solder','meter','disk','drive','psu')
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
        self.assertEqual(s.get_size(),(320,240));self.assertIs(s,art.layer())
        self.assertEqual(s.get_at((200,120)).a,255)

class MemoryTimingTests(unittest.TestCase):
    def test_walk_pause_dialogue_and_skip(self):
        from puzzle_maze.lab_scene import LabEntrance,LINES
        scene=LabEntrance();self.assertEqual(scene.position,(24,128));scene.advance();self.assertEqual(scene.line,0)
        scene.update(2);self.assertFalse(scene.ready);self.assertGreater(scene.position[0],24)
        scene.update(8.1);self.assertTrue(scene.ready);self.assertEqual(scene.position,(152,112))
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


    def test_lab_has_no_invisible_dungeon_columns(self):
        from puzzle_maze.remaster import RemasteredSession
        tiles=RemasteredSession().rooms.rooms['r28']['tiles']
        self.assertTrue(all(set(row[1:-1])=={'.'} for row in tiles[3:-1]))
        self.assertEqual(len(tiles[0]),20)
        self.assertTrue(RemasteredSession().rooms.rooms['r28']['solid_footprints'])

    def test_game_sequence_freezes_world_and_records_story_once(self):
        from puzzle_maze.game import Game,GameScene
        g=Game(headless=True);g.save=lambda:None
        g.session.enter('r28');g.scene=GameScene.PLAY;g.update(.01)
        self.assertEqual(g.scene,GameScene.MEMORY)
        before=(g.session.player.x,g.session.player.y,g.session.room_elapsed)
        g.update(3);self.assertEqual(before,(g.session.player.x,g.session.player.y,g.session.room_elapsed))
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,repeat=True))
        self.assertEqual(g.lab_entrance.line,0)
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
        self.assertTrue(g.session.lab_memory_seen);self.assertIn('kevin_photo',g.session.lore)
        g.update(.01);self.assertEqual(g.scene,GameScene.PLAY)


    def test_vault_reveal_never_grants_rewards_or_replays_during_visit(self):
        from puzzle_maze.game import Game,GameScene
        g=Game(headless=True);g.save=lambda:None;g.session.enter('r27');g.scene=GameScene.PLAY
        before=(g.session.rewards.tokens,g.session.rewards.tickets)
        g.update(.01);self.assertEqual(g.scene,GameScene.TREASURY)
        g.update(2);self.assertEqual(g.scene,GameScene.PLAY)
        g.update(.01);self.assertEqual(g.scene,GameScene.PLAY)
        self.assertEqual(before,(g.session.rewards.tokens,g.session.rewards.tickets))

    def test_previous_v45_snapshot_gains_only_optional_lab_interactions(self):
        import json
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from puzzle_maze.remaster import RemasteredSession
        s=RemasteredSession();s.enter('r28');s.grey_pixel=True;s.lore={'kevin_photo'}
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'save.json';s.save(p);data=json.loads(p.read_text())
            for snapshot in [*data['snapshots'].values(),data['checkpoint']['objects']]:
                for key in ('gpu','keyboard','terminal'):snapshot.pop(key,None)
            data['extension']['remaster'].pop('lab_memory_seen',None)
            p.write_text(json.dumps(data));loaded=RemasteredSession.load(p)
        self.assertEqual(loaded.rooms.current,'r28');self.assertTrue(loaded.grey_pixel)
        self.assertIn('kevin_photo',loaded.lore);self.assertFalse(loaded.lab_memory_seen)
        self.assertTrue({'gpu','keyboard','terminal'}<=loaded.puzzles.objects.keys())
