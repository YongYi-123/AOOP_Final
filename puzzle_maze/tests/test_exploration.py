import tempfile
from pathlib import Path
import unittest
from puzzle_maze.session import GameSession
from puzzle_maze.exploration import DungeonAtlas

class ExplorationTests(unittest.TestCase):
    def test_hidden_room_absent_until_discovery(self):
        s=GameSession();atlas=DungeonAtlas(s.rooms)
        self.assertNotIn('r9',atlas.layout(s.visited))
        self.assertNotIn(('r6','r9'),atlas.edges(s.visited))
        s.enter('r9')
        self.assertIn('r9',atlas.layout(s.visited))
        self.assertIn(('r6','r9'),atlas.edges(s.visited))

    def test_fog_reveals_nearby_not_through_walls(self):
        s=GameSession();known=s.exploration.tiles['r1']
        self.assertIn((2,7),known);self.assertNotIn((33,13),known)
        s.player.x,s.player.y=13,7;s.tick(0)
        self.assertIn((14,7),s.exploration.tiles['r1'])
        self.assertNotIn((15,7),s.exploration.tiles['r1'])
        self.assertTrue(any(kind=='door' for kind,pos in DungeonAtlas(s.rooms).discovered_markers(s)))

    def test_exploration_save_and_reset(self):
        s=GameSession();s.move(1,0);s.move(1,0)
        before=s.exploration.capture();s.reset()
        self.assertEqual(s.exploration.capture(),before)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=GameSession.load(path)
            self.assertEqual(loaded.exploration.capture(),before)

    def test_graph_reads_new_map_edges(self):
        s=GameSession();s.rooms.rooms['r1']['exits'].append(dict(target='r8',pos=[3,7],arrival=[2,7]))
        self.assertIn(('r1','r8'),DungeonAtlas(s.rooms).edges(s.visited))
