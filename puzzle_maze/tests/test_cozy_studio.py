"""Verify the actual studio renderer, production collision and old-save recovery."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json
import unittest
from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import pygame
from puzzle_maze.remaster import RemasteredSession
from puzzle_maze.studio_layout import ENTRY,FURNITURE,MIAO_ROUTE,approach,contact_blocked

class CozyStudioTests(unittest.TestCase):
    def test_all_interactions_and_door_have_connected_legal_walking_paths(self):
        s=RemasteredSession();s.enter('r28');q=deque([tuple(ENTRY)]);seen=set(q)
        while q:
            x,y=q.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                pos=x+dx,y+dy
                if pos not in seen and s.can_enter(*pos):seen.add(pos);q.append(pos)
        self.assertGreater(len(seen),100);self.assertIn((1,7),seen)
        for obj in s.puzzles.objects.values():self.assertIn(approach(s.rooms.data,obj.pos)[0],seen,obj.id)
    def test_solid_furniture_blocks_move_and_dash_but_not_tall_art(self):
        s=RemasteredSession();s.enter('r28');s.inventory.abilities.add('boots')
        for item in FURNITURE:
            x,y,w,h=item.footprint
            tiles=[(tx,ty) for tx in range(1,19) for ty in range(3,12) if x<tx*16+8<x+w and y<ty*16+15<y+h]
            self.assertTrue(tiles,item.name)
            self.assertTrue(all(not s.can_enter(*pos) for pos in tiles),item.name)
        s.player.x,s.player.y=8,6;s.player.facing=(0,-1)
        self.assertFalse(s.move(0,-1));self.assertEqual(s.dash(),0)
        # The head of the bookcase is tall decoration; its floor contact is lower.
        self.assertTrue(s.can_enter(3,3))
    def test_miao_scripted_route_clears_every_furniture_contact(self):
        boxes=[f.footprint for f in FURNITURE]
        for a,b in zip(MIAO_ROUTE,MIAO_ROUTE[1:]):
            for step in range(101):
                x=a[0]+(b[0]-a[0])*step/100;y=a[1]+(b[1]-a[1])*step/100
                self.assertFalse(contact_blocked(x,y,boxes),((x,y),boxes))
    def test_real_entry_and_preview_use_identical_production_room_pixels(self):
        from puzzle_maze.game import Game,GameScene
        from puzzle_maze.dev_preview import PreviewGame
        g=Game(headless=True,persistent=False);s=g.session;s.inventory.abilities.add('map');s.enter('r24',(21,7))
        s.puzzles.objects['debug_seam'].blast()
        for _ in range(90):s.tick(1/60)
        s.player.x,s.player.y=23,8;g.scene=GameScene.PLAY;g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
        self.assertTrue(s.grey_pixel);self.assertTrue(s.transition());self.assertEqual(s.rooms.current,'r28')
        preview=PreviewGame('developer-room',True)
        for app in (g,preview):
            app.session.player.x,app.session.player.y=ENTRY;app.session.lab_memory_seen=True
            app.visual=list(map(float,ENTRY));app.renderer.studio_scene=None
            with patch.object(app.renderer.environment,'tiles',side_effect=AssertionError('dungeon tiles in studio')),patch.object(app.renderer.hud,'draw',side_effect=AssertionError('dungeon HUD in studio')):
                app.renderer.world(app.session,app.visual,0)
        self.assertEqual(pygame.image.tobytes(g.renderer.surface,'RGB'),pygame.image.tobytes(preview.renderer.surface,'RGB'))
        self.assertEqual(g.renderer.developer_art.layer().get_size(),(320,240))
    def test_legacy_studio_snapshot_relocates_safely_and_keeps_an_immutable_backup(self):
        s=RemasteredSession();s.enter('r28');s.grey_pixel=True;s.lore={'kevin_photo','dev_001'};s.inventory.coins=17
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'save.json';s.save(path);data=json.loads(path.read_text())
            data['extension']['remaster'].pop('studio_revision');data['player']=[23,13]
            data['extension']['orb'].update(room='r28',x=23,y=13,carried=True)
            data['checkpoint']['pos']=[2,7]
            data['explored']['r28']=[[25,15],[2,7]]
            old={'photo':[12,5],'note':[14,5],'miao':[8,8],'terminal':[21,9]}
            for snapshot in [data['snapshots']['r28'],data['checkpoint']['objects']]:
                for key,pos in old.items():snapshot[key]['pos']=pos
                for key in ('studio_todo','studio_food','studio_cushion','studio_reminder'):snapshot.pop(key)
            path.write_text(json.dumps(data));before=path.read_bytes();loaded=RemasteredSession.load(path)
            self.assertEqual(path.read_bytes(),before);self.assertEqual(loaded.rooms.current,'r28')
            self.assertEqual(loaded.inventory.coins,17);self.assertEqual(loaded.lore,s.lore);self.assertTrue(loaded.grey_pixel)
            self.assertTrue(loaded.can_enter(loaded.player.x,loaded.player.y));self.assertTrue(loaded.orb.carried)
            self.assertEqual(loaded.orb.pos,(loaded.player.x,loaded.player.y))
            loaded.save(path);backup=path.with_name(path.name+'.pre-studio-v2')
            self.assertEqual(backup.read_bytes(),before);loaded.save(path);self.assertEqual(backup.read_bytes(),before)

    def test_depth_sort_preserves_front_and_back_without_fading(self):
        from puzzle_maze.render import Renderer
        s=RemasteredSession();s.enter('r28');r=Renderer()
        for position,behind in (((8,3),True),((8,6),False)):
            sequence=[]
            player=r.player;sprite=r.developer_art.sprite
            def record_player(*args):sequence.append('player');return player(*args)
            def record_sprite(item,ghost=False):
                sequence.append(item.name)
                if item.name=='desk':self.assertFalse(ghost)
                return sprite(item,ghost)
            with patch.object(r,'player',record_player),patch.object(r.developer_art,'sprite',record_sprite):
                r.world(s,list(position),0)
            self.assertEqual(sequence.index('player')<sequence.index('desk'),behind)

    def test_todo_pages_are_real_optional_interactions_and_hold_keys_do_not_skip(self):
        from puzzle_maze.dev_preview import PreviewGame
        from puzzle_maze.game import GameScene
        g=PreviewGame('kevin-notes',True)
        self.assertEqual(g.scene,GameScene.SCROLL);self.assertEqual(g.reading,'studio_todo')
        self.assertIn('studio_todo',g.session.lore)
        for page in range(1,4):
            g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT));self.assertEqual(g.reading_page,page)
            g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT,repeat=True));self.assertEqual(g.reading_page,page)
            g.draw(0)
            rects=g.renderer.ui.rects
            self.assertTrue(all(g.screen.get_rect().contains(r) for r in rects))
            self.assertTrue(all(not a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]))
        self.assertFalse(g.persistent)

    def test_cinematic_has_a_collision_free_continuous_walk_before_dialogue(self):
        from puzzle_maze.lab_scene import LabEntrance
        scene=LabEntrance();previous=scene.position;boxes=[f.footprint for f in FURNITURE]
        for _ in range(580):
            scene.update(1/60);x,y=scene.position
            self.assertLessEqual(abs(x-previous[0])+abs(y-previous[1]),.65)
            self.assertFalse(contact_blocked(x,y,boxes));self.assertFalse(scene.ready)
            scene.advance();self.assertEqual(scene.line,0);previous=(x,y)
        scene.update(.5);self.assertTrue(scene.ready);scene.advance();self.assertEqual(scene.line,1)
        self.assertEqual(scene.position,MIAO_ROUTE[-1]);self.assertIs(scene.memory(),scene.memory())


    def test_cabinet_sprites_are_cached_without_any_proximity_fade(self):
        from puzzle_maze.developer_art import DeveloperRoomArt
        art=DeveloperRoomArt()
        for item in FURNITURE:
            image=art.sprite(item)
            self.assertIs(image,art.sprite(item,True))
            self.assertIn(image.get_alpha(),(None,255))
