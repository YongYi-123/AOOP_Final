import tempfile
import unittest
from pathlib import Path
from puzzle_maze.session import GameSession
from puzzle_maze.core import Player
from puzzle_maze.puzzles import PuzzleManager
from puzzle_maze.rooms import load_rooms

class SessionTests(unittest.TestCase):
    def test_secret_requires_pulse(self):
        m=PuzzleManager(load_rooms()['r6']);p=Player(13,7,(1,0))
        self.assertIsNone(m.interact(p))
        self.assertEqual(m.interact(p,True),'cracked')
        self.assertTrue(m.move(p,1,0))

    def test_timer_and_occupied_gate(self):
        m=PuzzleManager(load_rooms()['r7']);p=Player(7,7)
        m.interact(p);self.assertTrue(m.solved)
        p.x=14;m.update(5,p)
        self.assertTrue(m.can_enter(14,7))
        m.move(p,1,0)
        self.assertFalse(m.can_enter(14,7))
        m.interact(Player(9,7));self.assertTrue(m.solved)

    def test_reset_inventory_and_stones(self):
        s=GameSession();s.enter('r8')
        s.player=Player(4,5);s.move(1,0)
        s.puzzles.update(0,Player(10,3))
        s.reset()
        self.assertEqual(s.puzzles.objects['box1'].pos,(5,5))
        self.assertEqual(s.inventory.keys,{})
        self.assertFalse(s.puzzles.objects['key'].state.active)

    def test_session_transition_preserves_key(self):
        s=GameSession();s.enter('r4');s.puzzles.update(0,Player(7,5))
        s.player=Player(33,7);self.assertTrue(s.transition())
        self.assertEqual(s.rooms.current,'r5')
        self.assertEqual(s.inventory.keys,{'amber':1})

    def test_save_load_and_invalid_save(self):
        s=GameSession();s.enter('r4');s.player=Player(7,5);s.tick(0)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=GameSession.load(path)
            self.assertEqual(loaded.inventory.keys,{'amber':1})
            self.assertEqual(loaded.rooms.current,'r4')
            loaded.reset();self.assertEqual(loaded.inventory.keys,{})
            path.write_text('{broken');self.assertEqual(GameSession.load(path).rooms.current,'r1')

    def test_combined_gate_conditions(self):
        s=GameSession();s.enter('r8');m=s.puzzles
        for y in (5,9):
            p=Player(4,y)
            for _ in range(3):m.move(p,1,0)
        m.update(0,Player(10,3));m.interact(Player(13,7),True)
        m.interact(Player(18,10));m.interact(Player(19,5))
        self.assertFalse(m.solved)
        m.interact(Player(23,7));self.assertTrue(m.solved)

    def test_corrupt_snapshots_and_checkpoint_fall_back(self):
        import json
        s=GameSession()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path)
            original=json.loads(path.read_text())
            for field,value in [('player',[0,0]),('inventory',{'amber':-1}),('checkpoint',{}),('snapshots',{'r1':{}})]:
                data=dict(original);data[field]=value;path.write_text(json.dumps(data))
                loaded=GameSession.load(path)
                self.assertEqual((loaded.player.x,loaded.player.y),(2,7))
                loaded.reset()
