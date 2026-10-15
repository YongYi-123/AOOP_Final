"""The three robot brains: they obey the walls, stay deterministic, never make the game unfair, and each behaves differently."""
import random
import unittest
from dataclasses import replace

from neon_cat_maze import ai, config as cfg
from neon_cat_maze.mazes import MAZES
from neon_cat_maze.model import Run
from neon_cat_maze.pathing import distance_field, path_distance, shortest_path
from neon_cat_maze.tests.autopilot import steer_for
from neon_cat_maze.tests.helpers import DT, advance, play, running

RIGHT = (1, 0)


def trail_of(run, robot, seconds):
    """The tiles `robot` stood on, in order, as it walked for `seconds`."""
    trail = [robot.tile]
    for _ in advance(run, seconds):
        if robot.tile != trail[-1]:
            trail.append(robot.tile)
    return trail


def free_robot(run, index, tile, mode="active"):
    robot = run.robots[index]
    robot.mode, robot.fright, robot.release_in = mode, False, 10 ** 6
    robot.place(tile)
    return robot


class PathingTests(unittest.TestCase):
    def test_distance_fields_never_cross_walls(self):
        for maze in MAZES:
            field = distance_field(maze, maze.start)
            self.assertEqual(set(field), set(maze.floor()))
            for tile, d in field.items():
                for _, nxt in maze.neighbours(tile):
                    self.assertLessEqual(abs(field[nxt] - d), 1)

    def test_shortest_path_is_a_walk_over_open_tiles(self):
        maze = MAZES[1]
        path = shortest_path(maze, (1, 1), (19, 13))
        self.assertEqual((path[0], path[-1]), ((1, 1), (19, 13)))
        self.assertEqual(len(path) - 1, path_distance(maze, (1, 1), (19, 13)))
        for a, b in zip(path, path[1:]):
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)
            self.assertTrue(maze.is_open(b))
        self.assertEqual(shortest_path(maze, (1, 1), (0, 0)), [])             # a wall tile is unreachable


class RobotRulesTests(unittest.TestCase):
    def test_robots_obey_the_walls_and_stay_out_of_the_den_for_a_long_run(self):
        for level in (1, 2, 3):
            run = Run(random.Random(level), level)
            run.phase = "run"
            for i in range(60 * 90):
                if i % 40 == 0:
                    d = steer_for(run)
                    if d:
                        run.steer(d)
                run.update(DT)
                if run.phase != "run":
                    run._reset_positions()
                    run.phase = "run"
                for robot in run.robots:
                    self.assertTrue(run.maze.is_open(robot.nearest_tile()), (level, robot.kind, robot.pos))
                    if robot.mode == "active":
                        self.assertNotIn(robot.nearest_tile(), run.maze.restricted - {run.maze.gate} or set())

    def test_active_robots_never_turn_back_unless_they_must(self):
        run = running()
        robot = free_robot(run, 1, (5, 5))
        robot.dir = (1, 0)
        options = ai.options_for(run.maze, robot)
        self.assertNotIn((-1, 0), [d for d, _ in options])
        self.assertTrue(options)

    def test_a_dead_end_forces_a_turn_round(self):
        run = running()
        maze = run.maze
        dead = [t for t in maze.floor() if len(maze.neighbours(t)) == 1 and t not in maze.restricted]
        if dead:
            robot = free_robot(run, 1, dead[0])
            only = maze.neighbours(dead[0])[0][0]
            robot.dir = (-only[0], -only[1])
            self.assertEqual([d for d, _ in ai.options_for(maze, robot)], [only])

    def test_every_run_is_reproducible_from_its_seed(self):
        def trace(seed):
            run = Run(random.Random(seed), 2)
            run.phase = "run"
            run.steer(RIGHT)
            return [(run.update(DT), tuple(r.pos for r in run.robots))[1] for _ in range(60 * 25)]
        self.assertEqual(trace(5), trace(5))
        self.assertNotEqual(trace(5), trace(6))


class PatrolTests(unittest.TestCase):
    def patrol_run(self, chance, seed=2, cat=(10, 13)):
        run = running(seed=seed)
        run.diff = replace(run.diff, patrol_turn=chance)
        run.cat.place(cat)
        run.invulnerable = 10 ** 6
        return run, free_robot(run, 0, run.maze.door)

    def test_it_walks_its_route_in_order_when_it_never_turns_off(self):
        run, robot = self.patrol_run(0.0)
        route = robot.route
        trail = trail_of(run, robot, 120.0)
        visited = [t for i, t in enumerate(trail) if t in route and (i == 0 or trail[i - 1] != t)]
        self.assertGreaterEqual(len(visited), 6)
        order = [route.index(t) for t in visited]
        for a, b in zip(order, order[1:]):
            self.assertEqual(b, (a + 1) % len(route))                          # strictly the next waypoint each time

    def test_the_route_is_a_repeating_loop(self):
        run, robot = self.patrol_run(0.0)
        trail = trail_of(run, robot, 200.0)
        visits = [i for i, t in enumerate(trail) if t == robot.route[0] and (i == 0 or trail[i - 1] != t)]
        self.assertGreaterEqual(len(visits), 4)
        first, second = trail[visits[1]:visits[2]], trail[visits[2]:visits[3]]
        self.assertEqual(first, second)                                       # every lap is exactly the same walk
        self.assertGreater(len(first), 30)

    def test_it_sometimes_leaves_the_route_at_an_intersection(self):
        steady, _ = self.patrol_run(0.0)
        wild, _ = self.patrol_run(0.9)
        a = trail_of(steady, steady.robots[0], 60.0)
        b = trail_of(wild, wild.robots[0], 60.0)
        self.assertNotEqual(a, b)
        lap_a = [t for t in a if t in steady.robots[0].route]
        lap_b = [t for t in b if t in wild.robots[0].route]
        self.assertNotEqual(lap_a[:12], lap_b[:12])

    def test_a_low_chance_means_mostly_predictable(self):
        self.assertLess(cfg.PATROL_TURN_CHANCE[0], 0.2)

    def test_it_ignores_the_cat_and_the_scatter_clock(self):
        run, robot = self.patrol_run(0.0, cat=(10, 13))
        run.scattering, run.phase_clock = True, 10 ** 6
        a = trail_of(run, robot, 30.0)
        run2, robot2 = self.patrol_run(0.0, cat=(3, 13))
        run2.scattering, run2.phase_clock = False, 10 ** 6
        b = trail_of(run2, robot2, 30.0)
        self.assertEqual(a, b)


class ChaseTests(unittest.TestCase):
    def test_it_follows_the_maze_to_the_cat_never_through_walls(self):
        run = running()
        run.diff = replace(run.diff, chase_noise=0.0)
        run.scattering, run.phase_clock = False, 10 ** 6
        cat_tile = (3, 13)
        run.cat.place(cat_tile)
        robot = free_robot(run, 1, (19, 1))
        steps = path_distance(run.maze, robot.tile, cat_tile)
        run.invulnerable = 10 ** 6                                             # watch, do not get caught
        seen = []
        for _ in advance(run, steps / run.diff.speed["chase"] + 1.0):
            seen.append(robot.nearest_tile())
            self.assertTrue(run.maze.is_open(robot.nearest_tile()))
        self.assertIn(cat_tile, seen)                                          # it reached the cat ...
        self.assertLessEqual(seen.index(cat_tile) * run.diff.speed["chase"] * DT, steps + 2)   # ... by (about) the shortest way

    def test_the_distance_to_a_standing_cat_never_grows_while_chasing(self):
        run = running()
        run.diff = replace(run.diff, chase_noise=0.0)
        run.scattering, run.phase_clock = False, 10 ** 6
        run.cat.place((10, 13))
        run.invulnerable = 10 ** 6
        robot = free_robot(run, 1, (1, 1))
        best = path_distance(run.maze, robot.tile, (10, 13))
        arrived = False
        for _ in advance(run, 12.0):
            d = path_distance(run.maze, robot.tile, (10, 13))
            if d == 0:
                arrived = True
                break
            self.assertLessEqual(d, best)                                      # every tile it enters is closer
            best = d
        self.assertTrue(arrived)

    def test_it_retreats_to_its_corner_while_scattering(self):
        run = running()
        run.diff = replace(run.diff, chase_noise=0.0)
        run.scattering, run.phase_clock = True, 10 ** 6
        run.cat.place((10, 13))
        run.invulnerable = 10 ** 6
        robot = free_robot(run, 1, (10, 5))
        corner = ai.scatter_corner(run.maze, "chase")
        play(run, 12.0)
        self.assertLessEqual(path_distance(run.maze, robot.nearest_tile(), corner), 4)

    def test_pursuit_is_not_perfect_noise_makes_it_wander_a_little(self):
        def walked(noise):
            run = running(seed=3)
            run.diff = replace(run.diff, chase_noise=noise)
            run.scattering, run.phase_clock = False, 10 ** 6
            run.cat.place((10, 13))
            run.invulnerable = 10 ** 6
            robot = free_robot(run, 1, (1, 1))
            return len(set(trail_of(run, robot, 6.0)))
        self.assertGreater(cfg.CHASE_NOISE[0], 0)
        self.assertGreaterEqual(walked(0.6), walked(0.0))


class AmbushTests(unittest.TestCase):
    def test_it_aims_ahead_of_the_cats_direction(self):
        run = running()
        run.cat.place((5, 13), (1, 0))
        run.cat.dir, run.cat.t = (1, 0), 0.0
        self.assertEqual(ai.ambush_target(run.maze, run.cat), (9, 13))
        run.cat.place((15, 13), (-1, 0))
        run.cat.dir = (-1, 0)
        self.assertEqual(ai.ambush_target(run.maze, run.cat), (11, 13))

    def test_the_aim_point_stops_at_a_wall(self):
        run = running()
        run.cat.place((18, 13), (1, 0))
        run.cat.dir = (1, 0)
        self.assertEqual(ai.ambush_target(run.maze, run.cat), (19, 13))        # only one tile left before the wall
        run.cat.dir = (0, 0)
        run.cat.facing = (0, 1)
        self.assertEqual(ai.ambush_target(run.maze, run.cat), (18, 13))        # nothing below

    def test_the_aim_point_is_always_a_real_corridor_tile(self):
        run = running()
        for tile in run.maze.floor():
            if tile in run.maze.restricted:
                continue
            for d in ((0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)):
                run.cat.place(tile, (1, 0))
                run.cat.dir = d
                target = ai.ambush_target(run.maze, run.cat)
                self.assertTrue(run.maze.is_open(target))
                self.assertNotIn(target, run.maze.restricted)

    def test_it_heads_for_the_aim_point_not_the_cat(self):
        run = running()
        run.diff = replace(run.diff, chase_noise=0.0)
        run.scattering, run.phase_clock = False, 10 ** 6
        run.cat.place((2, 13), (1, 0))
        run.cat.dir, run.cat.t = (1, 0), 0.0
        robot = free_robot(run, 2, (9, 9))
        robot.dir = (0, 1)
        robot.place((9, 9))
        choice = ai.choose(run.maze, robot, run.cat, False, run.diff, run.rng)
        aim = ai.ambush_target(run.maze, run.cat)
        field_aim, field_cat = distance_field(run.maze, aim), distance_field(run.maze, run.cat.tile)
        nxt = (robot.tile[0] + choice[0], robot.tile[1] + choice[1])
        self.assertLess(field_aim[nxt], field_aim[robot.tile])
        self.assertNotEqual(aim, run.cat.tile)
        del field_cat

    def test_it_stops_lunging_when_it_is_right_behind_the_cat(self):
        run = running()
        run.diff = replace(run.diff, chase_noise=0.0)
        run.cat.place((10, 13), (1, 0))
        run.cat.dir = (1, 0)
        robot = free_robot(run, 2, (8, 13))
        self.assertLess(path_distance(run.maze, robot.tile, run.cat.tile), cfg.AMBUSH_GIVE_UP)
        choice = ai.choose(run.maze, robot, run.cat, False, run.diff, run.rng)
        corner = ai.scatter_corner(run.maze, "ambush")
        field = distance_field(run.maze, corner)
        nxt = (robot.tile[0] + choice[0], robot.tile[1] + choice[1])
        self.assertLess(field[nxt], field[robot.tile])


class BehavioursDifferTests(unittest.TestCase):
    def test_the_three_robots_take_different_ways_from_the_same_start(self):
        paths = {}
        for index, kind in ((0, "patrol"), (1, "chase"), (2, "ambush")):
            run = running(seed=9)
            run.scattering, run.phase_clock = False, 10 ** 6
            run.cat.place((3, 13), (1, 0))
            run.cat.dir = (1, 0)
            run.invulnerable = 10 ** 6
            robot = free_robot(run, index, (10, 5))
            paths[kind] = tuple(trail_of(run, robot, 8.0))
        self.assertEqual(len(set(paths.values())), 3)

    def test_each_robot_type_has_its_own_speed_and_colour(self):
        self.assertEqual(len(set(cfg.ROBOT_SPEED.values())), 3)
        self.assertEqual(set(cfg.ROBOT_NAMES), set(cfg.ROBOTS))


class FairnessTests(unittest.TestCase):
    def test_no_robot_leaves_the_den_before_the_cat_has_had_time_to_move(self):
        for level in (1, 4, 20):
            run = Run(random.Random(1), level)
            self.assertGreaterEqual(min(r.release_in for r in run.robots), 0.8)
            self.assertTrue(all(r.mode == "den" for r in run.robots))
            self.assertEqual(sorted(r.release_in for r in run.robots), [r.release_in for r in run.robots])
            gaps = [b.release_in - a.release_in for a, b in zip(run.robots, run.robots[1:])]
            self.assertTrue(all(g >= cfg.RELEASE_MIN_GAP - 1e-9 for g in gaps))

    def test_robots_are_far_from_the_cat_when_a_try_begins(self):
        for maze in MAZES:
            for tile in maze.den:
                self.assertGreaterEqual(path_distance(maze, tile, maze.start), 12)

    def test_the_robots_are_always_slower_than_the_cat_so_pursuit_can_be_escaped(self):
        for level in (1, 5, 10, 50):
            for speed in cfg.difficulty_for(level).speed.values():
                self.assertLess(speed, cfg.CAT_SPEED)
        self.assertLess(cfg.FRIGHT_SPEED, cfg.ROBOT_SPEED["patrol"])

    def test_a_simple_pilot_can_clear_the_first_level_on_every_seed(self):
        for seed in range(1, 6):
            run = Run(random.Random(seed))
            t = 0.0
            while t < 240 and run.level == 1 and not run.over:
                d = steer_for(run)
                if d:
                    run.steer(d)
                run.update(DT)
                t += DT
            self.assertEqual(run.level, 2, f"seed {seed}: cleared level 1")
            self.assertGreaterEqual(run.lives, 1)

    def test_and_level_difficulty_eventually_ends_a_run(self):
        run = Run(random.Random(2))
        t = 0.0
        while t < 1200 and not run.over:
            d = steer_for(run)
            if d:
                run.steer(d)
            run.update(DT)
            t += DT
        self.assertTrue(run.over)
        self.assertGreaterEqual(run.level, 2)


if __name__ == "__main__":
    unittest.main()
