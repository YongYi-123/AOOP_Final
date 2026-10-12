import copy
import unittest
from puzzle_maze.rooms import load_rooms, validate_rooms, RoomManager

class RoomTests(unittest.TestCase):
    def test_all_maps_and_exits(self):
        rooms = load_rooms()
        self.assertEqual(len(rooms), 8)
        for room in rooms.values():
            self.assertTrue(room['objects'])
            self.assertTrue(room['goal'])

    def test_invalid_map(self):
        rooms = copy.deepcopy(load_rooms())
        rooms['r1']['spawn'] = [0, 0]
        with self.assertRaises(ValueError):
            validate_rooms(rooms)

    def test_transition(self):
        manager = RoomManager()
        p = manager.enter('r1', [33, 7])
        e = manager.exit_at(p)
        p = manager.enter(e['target'], e['arrival'])
        self.assertEqual(manager.current, 'r2')
        self.assertEqual((p.x, p.y), (2, 7))
