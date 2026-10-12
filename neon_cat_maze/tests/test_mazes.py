"""The handcrafted mazes: well formed, fully traversable, every collectible reachable, fair at the start."""
import unittest
from dataclasses import replace

from neon_cat_maze import config as cfg
from neon_cat_maze.mazes import COLS, MAZES, ROWS, distances, maze_for_level, reach, validate


class MazeTests(unittest.TestCase):
    def test_there_are_three_distinct_handcrafted_layouts(self):
        self.assertEqual(len(MAZES), 3)
        self.assertEqual(len({m.rows for m in MAZES}), 3)
        self.assertEqual(len({m.name for m in MAZES}), 3)
        self.assertEqual(len({m.edge_color for m in MAZES}), 3)      # each one has its own neon colour

    def test_every_maze_passes_the_automatic_validation(self):
        for maze in MAZES:
            self.assertEqual(validate(maze), [], maze.name)

    def test_size_and_mirror_symmetry(self):
        for maze in MAZES:
            self.assertEqual((len(maze.rows), {len(r) for r in maze.rows}), (ROWS, {COLS}))
            for row in maze.rows:
                self.assertEqual(row, row[::-1], maze.name)
            self.assertTrue(all(row[0] == row[-1] == "#" for row in maze.rows))      # sealed on the left and right
            self.assertEqual(set(maze.rows[0] + maze.rows[-1]), {"#"})               # ... and top and bottom

    def test_the_whole_floor_is_connected_from_the_cat_start(self):
        for maze in MAZES:
            self.assertEqual(reach(maze, maze.start), set(maze.floor()), maze.name)

    def test_every_fish_and_catnip_is_reachable_without_crossing_the_den(self):
        for maze in MAZES:
            outside = reach(maze, maze.start, avoid=set(maze.den))
            self.assertTrue(maze.fish <= outside, maze.name)
            self.assertTrue(maze.catnip <= outside, maze.name)
            self.assertGreaterEqual(len(maze.catnip), 2)
            self.assertGreater(len(maze.fish), 100)

    def test_the_cat_start_is_a_fair_open_junction_far_from_the_den(self):
        for maze in MAZES:
            self.assertGreaterEqual(len(maze.neighbours(maze.start)), 2, maze.name)
            dist = distances(maze, maze.start)
            self.assertGreaterEqual(dist[maze.door], 10, maze.name)
            for tile in maze.floor():
                if tile not in maze.den and len(maze.neighbours(tile)) == 1:
                    self.assertGreater(dist[tile], 6, f"{maze.name} dead end {tile} near the start")

    def test_there_are_loops_to_run_round(self):
        for maze in MAZES:
            tiles = set(maze.floor()) - set(maze.den)
            edges = sum(len(maze.neighbours(t)) for t in tiles) // 2
            self.assertGreaterEqual(edges - len(tiles) + 1, 8, maze.name)

    def test_the_den_has_one_door_and_the_gate_is_restricted(self):
        for maze in MAZES:
            self.assertEqual(len(maze.den), 3)
            self.assertEqual(maze.neighbours(maze.gate).__len__(), 2)               # corridor above, den below
            self.assertIn(maze.gate, maze.restricted)
            self.assertNotIn(maze.door, maze.restricted)

    def test_level_one_to_three_use_each_layout_then_they_repeat(self):
        names = [maze_for_level(n).name for n in range(1, 8)]
        self.assertEqual(names[:3], [m.name for m in MAZES])
        self.assertEqual(names[3:6], names[:3])
        self.assertEqual(maze_for_level(0).name, MAZES[0].name)

    def test_the_validator_catches_a_broken_maze(self):
        maze = MAZES[0]
        stranded = replace(maze, fish=maze.fish | {(0, 0)})                       # a fish inside a wall
        self.assertTrue(any("fish not reachable" in p for p in validate(stranded)))
        boxed_in = replace(maze, walls=maze.walls | {(9, 13), (11, 13), (10, 12)})  # the cat cannot get out
        self.assertTrue(any("unreachable" in p for p in validate(boxed_in)))
        dead_end = replace(maze, walls=maze.walls | {(9, 13), (10, 12)})           # the start is a dead end
        self.assertTrue(validate(dead_end))
        self.assertEqual(validate(maze), [])

    def test_difficulty_ramps_but_stays_capped(self):
        d1, d5, d99 = cfg.difficulty_for(1), cfg.difficulty_for(5), cfg.difficulty_for(99)
        for kind in cfg.ROBOTS:
            self.assertLess(d1.speed[kind], d5.speed[kind])
            self.assertLessEqual(d99.speed[kind], cfg.ROBOT_SPEED_MAX * cfg.CAT_SPEED + 1e-9)
            self.assertLess(d99.speed[kind], cfg.CAT_SPEED)               # a robot is never faster than the cat
        self.assertLess(d5.catnip, d1.catnip)
        self.assertGreaterEqual(d99.catnip, 3.5)
        self.assertLess(d5.release_gap, d1.release_gap)
        self.assertGreaterEqual(d99.release_gap, cfg.RELEASE_MIN_GAP)
        self.assertGreater(d5.chase, d1.chase)


if __name__ == "__main__":
    unittest.main()
