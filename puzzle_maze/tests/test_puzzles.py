import unittest
from puzzle_maze.core import Player
from puzzle_maze.rooms import load_rooms
from puzzle_maze.puzzles import PuzzleManager, Inventory

class PuzzleTests(unittest.TestCase):
    def setUp(self):
        self.rooms = load_rooms()

    def test_box_plate_gate(self):
        m = PuzzleManager(self.rooms['r3'])
        for y in (5,9):
            p = Player(4,y)
            for _ in range(3):self.assertTrue(m.move(p,1,0))
        self.assertTrue(m.solved)

    def test_box_wall(self):
        m = PuzzleManager(self.rooms['r3'])
        b = m.objects['box1']; b.x,b.y = 13,5
        self.assertFalse(m.move(Player(12,5),1,0))
        self.assertEqual(b.pos,(13,5))

    def test_player_plate_latches(self):
        m = PuzzleManager(self.rooms['r2']); p = Player(6,7)
        m.move(p,1,0); self.assertTrue(m.solved)
        m.move(p,1,0); self.assertTrue(m.solved)

    def test_multi_switch(self):
        m = PuzzleManager(self.rooms['r5'])
        m.interact(Player(6,4)); self.assertFalse(m.solved)
        m.interact(Player(6,10)); self.assertTrue(m.solved)

    def test_key_once_and_lock(self):
        inv = Inventory(); m = PuzzleManager(self.rooms['r4'], inv)
        m.update(0,Player(7,5)); m.update(0,Player(7,5))
        self.assertEqual(inv.keys['amber'],1)
        self.assertEqual(m.interact(Player(13,7)), 'gate')
        self.assertEqual(inv.keys['amber'],0)
        self.assertTrue(m.solved)

    def test_wrong_key(self):
        m=PuzzleManager(self.rooms['r4']); m.inventory.add('other')
        self.assertIsNone(m.interact(Player(13,7)))
        self.assertFalse(m.solved)
