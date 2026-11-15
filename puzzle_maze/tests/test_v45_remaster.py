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
    def test_secret_lore_and_room_survive_save_load(self):
        s,d=self.discover();d.use('grey_pixel');s.tick(0);d.travel('r28');s.read_lore('kevin_photo')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'secret.json';s.save(path);loaded=RemasteredSession.load(path)
            self.assertEqual(loaded.rooms.current,'r28');self.assertTrue(loaded.grey_pixel)
            self.assertIn('kevin_photo',loaded.lore);self.assertIn('grey_pixel',loaded.inventory.flags)
