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
