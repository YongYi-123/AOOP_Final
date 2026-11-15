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
        self.assertEqual(set(old.rooms.rooms),set(s.rooms.rooms))
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
