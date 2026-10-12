import unittest
from puzzle_maze.core import Player, TileMap, CollisionManager, Camera

class MovementTests(unittest.TestCase):
    def test_movement_and_collision(self):
        p = Player(1, 1)
        c = CollisionManager(TileMap(['####', '#..#', '####']))
        self.assertTrue(c.move(p, 1, 0))
        self.assertFalse(c.move(p, 1, 0))
        self.assertEqual((p.x, p.y), (2, 1))

    def test_camera_clamps(self):
        c = Camera()
        c.follow(Player(99, 99), 40, 30)
        self.assertEqual((c.x, c.y), (320, 272))
