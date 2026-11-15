import tempfile
import unittest
from pathlib import Path
from puzzle_maze.remaster import RemasteredSession
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.rooms import validate_rooms

class FloorTests(unittest.TestCase):
    def test_exactly_two_floors_preserve_existing_chambers_and_finale(self):
        s=RemasteredSession(); old=AdvancedDungeonSession()
        self.assertEqual({r['floor'] for r in s.rooms.rooms.values()},{'1F','B1F'})
        self.assertEqual(set(s.rooms.rooms)-set(old.rooms.rooms),{"r28"})
        self.assertEqual(s.rooms.rooms['r27']['floor'],'B1F')
        self.assertTrue(any(e.get('finish') for e in s.rooms.rooms['r27']['exits']))
        validate_rooms(s.rooms.rooms)
    def test_old_save_retains_location_items_and_original_file(self):
        old=AdvancedDungeonSession();old.inventory.abilities.add('map');old.inventory.flags.add('west');old.enter('r10')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.json';old.save(path);before=path.read_bytes()
            new=RemasteredSession.load(path)
            self.assertEqual(new.rooms.current,'r10');self.assertIn('map',new.inventory.abilities)
            self.assertIn('west',new.inventory.flags);self.assertEqual(path.read_bytes(),before)
            self.assertEqual(new.rooms.data['content_revision'],'4.5')

    def test_removed_room_reference_relocates_without_losing_inventory(self):
        import json
        old=AdvancedDungeonSession();old.inventory.abilities.update(('map','gloves'));old.inventory.flags.add('west')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.json';old.save(path);data=json.loads(path.read_text())
            data['room']='B2F';path.write_text(json.dumps(data));before=path.read_bytes()
            new=RemasteredSession.load(path)
            self.assertEqual(new.rooms.current,'r27');self.assertIn('gloves',new.inventory.abilities)
            self.assertIn('west',new.inventory.flags);self.assertEqual(before,path.read_bytes())

    def test_palettes_are_distinct_and_archived_art_is_unchanged(self):
        from puzzle_maze.themes import THEMES
        s=RemasteredSession();old=AdvancedDungeonSession()
        self.assertGreaterEqual(len({r['theme'] for r in s.rooms.rooms.values()}),9)
        self.assertFalse(old.rooms.data['theme'].startswith('v45_'))
        for room in s.rooms.rooms.values():
            theme=THEMES[room['theme']]
            self.assertGreater(sum(theme.wall)-sum(theme.floor),100)

    def test_dash_windows_are_fairer_without_removing_boots_requirement(self):
        s=RemasteredSession();old=AdvancedDungeonSession()
        for id in ('r6','r14'):
            objects={o['id']:o for o in s.rooms.rooms[id]['objects']}
            self.assertEqual(objects['clock']['duration'],.85)
            self.assertTrue(objects['gate']['dash_only'])
            self.assertEqual(next(o for o in old.rooms.rooms[id]['objects'] if o['id']=='clock')['duration'],.35)

    def test_save_migration_creates_immutable_backup_and_hints_progress(self):
        old=AdvancedDungeonSession()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.json';old.save(path);original=path.read_bytes()
            new=RemasteredSession.load(path);new.save(path)
            self.assertEqual(path.with_name('old.json.pre-v45').read_bytes(),original)
            new.save(path);self.assertEqual(path.with_name('old.json.pre-v45').read_bytes(),original)
        clues=[new.next_hint() for _ in range(3)]
        self.assertEqual(len(set(clues)),3)

class GreyPixelTests(unittest.TestCase):
    def discover(self,with_map=True):
        import test_v3_campaign as witness
        s=RemasteredSession();s.inventory.bombs=4
        if with_map:s.inventory.abilities.add('map')
        s.enter('r24');d=witness.DungeonCampaignTests();d.s=s
        d.walk((21,7));s.player.facing=(1,0);self.assertTrue(s.bombs.place())
        d.walk((18,7));s.tick(1.7);s.tick(.7);s.tick(.5)
        return s,d
    def test_real_bomb_reveals_collectible_then_developer_room_has_safe_exit(self):
        s,d=self.discover();self.assertTrue(s.puzzles.objects['debug_seam'].state.active)
        d.use('grey_pixel');s.tick(0);self.assertTrue(s.grey_pixel)
        self.assertIn('grey_pixel',s.inventory.flags);d.travel('r28')
        for key in ('photo','note','miao'):
            d.use(key);s.read_lore(s.puzzles.objects[key].data['content_id'])
        self.assertIn('kevin_photo',s.lore);self.assertIn('miao_memory',s.lore)
        d.travel('r24');self.assertFalse(s.puzzles.objects['grey_pixel'].interact(s.puzzles,s.player))
    def test_map_is_a_real_dependency_and_reset_does_not_duplicate_the_secret(self):
        s,d=self.discover(False)
        self.assertFalse(s.grey_pixel);self.assertFalse(s.puzzles.objects['grey_pixel'].visible)
        s.inventory.abilities.add('map');s.tick(0);s.tick(.5);d.use('grey_pixel');s.tick(0)
        self.assertTrue(s.grey_pixel);s.reset();self.assertTrue(s.grey_pixel)
        self.assertTrue(s.puzzles.objects['grey_pixel'].state.active)
    def test_keyboard_collection_and_reading_work_while_carrying_iron_orb(self):
        import pygame
        from unittest.mock import patch
        from puzzle_maze.game import Game,GameScene
        s,d=self.discover();d.walk((23,8))
        s.orb.carried=True;s.orb.room='r24';s.orb.x,s.orb.y=s.player.x,s.player.y
        g=Game(headless=True,campaign='4.5');g.session=s;g.scene=GameScene.PLAY
        with patch.object(g,'save'):
            g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
            self.assertTrue(s.grey_pixel);self.assertTrue(s.orb.carried);self.assertEqual(g.scene,GameScene.DISCOVERY)
            g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
            self.assertEqual(g.scene,GameScene.PLAY);self.assertTrue(s.grey_pixel)
            g.scene=GameScene.PLAY;d.travel('r28')
            from puzzle_maze.studio_layout import approach
            pos,facing=approach(s.rooms.data,s.puzzles.objects['photo'].pos);d.walk(pos);s.player.facing=facing
            g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
            self.assertIn('kevin_photo',s.lore);self.assertTrue(s.orb.carried)
        pygame.quit()

    def test_secret_lore_and_room_survive_save_load(self):
        s,d=self.discover();d.use('grey_pixel');s.tick(0);d.travel('r28');s.read_lore('kevin_photo')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'secret.json';s.save(path);loaded=RemasteredSession.load(path)
            self.assertEqual(loaded.rooms.current,'r28');self.assertTrue(loaded.grey_pixel)
            self.assertIn('kevin_photo',loaded.lore);self.assertIn('grey_pixel',loaded.inventory.flags)


class WalkthroughTests(unittest.TestCase):
    def test_documented_interactions_and_edges_match_the_production_graph(self):
        import ast,re
        text=(Path(__file__).parents[1]/'PLAYER_ROUTE_V45.md').read_text()
        rooms=RemasteredSession().rooms.rooms;seen=set();count=0
        for line in text.splitlines():
            match=re.match(r'\| (\d+) \| (1F|B1F) (r\d+) .*? \| (.*) \|',line)
            if not match:continue
            _,floor,id,detail=match.groups();self.assertEqual(rooms[id]['floor'],floor);seen.add(id);count+=1
            if detail.startswith('E'):
                name=re.search(r'`([^`]+)`',detail)[1]
                pos=ast.literal_eval(re.search(r'\([^)]*\)',detail)[0])
                obj=next(o for o in rooms[id]['objects'] if o['id']==name)
                self.assertEqual(tuple(obj['pos']),pos)
            else:
                pos=ast.literal_eval(re.search(r'\([^)]*\)',detail)[0])
                target=re.search(r'→ (r\d+)',detail)[1]
                self.assertTrue(any(e['target']==target and tuple(e['pos'])==pos for e in rooms[id]['exits']))
        self.assertEqual(seen,set(rooms));self.assertGreater(count,100)


class EnglishTextTests(unittest.TestCase):
    def test_lore_fits_the_actual_bitmap_line_budget(self):
        from puzzle_maze.secret45 import LORE
        from puzzle_maze.pixel_font import render
        import pygame
        for title,lines in LORE.values():
            self.assertTrue(title.isascii());self.assertLessEqual(len(lines),4)
            for line in lines:
                self.assertTrue(line.isascii())
                # panel adds two spaces; 3x presentation uses 4x bitmap glyphs.
                self.assertLessEqual(render('  '+line,33,(255,255,255)).get_width(),244*3)
