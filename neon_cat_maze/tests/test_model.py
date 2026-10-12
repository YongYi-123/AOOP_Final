"""The cat's movement, collisions, eating, scoring, lives, levels and Catnip - the whole simulation without a window."""
import math
import random
import unittest

from neon_cat_maze import config as cfg
from neon_cat_maze.model import Run, STOP
from neon_cat_maze.settlement import RunResult, tickets_for
from neon_cat_maze.tests.helpers import DT, advance, clear_level, names, play, running

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


def on_lanes(pos, eps=1e-6):
    """A mover is always on a tile centre line: x or y is a whole number (that is what makes corner clipping impossible)."""
    return abs(pos[0] - round(pos[0])) < eps or abs(pos[1] - round(pos[1])) < eps


class MovementTests(unittest.TestCase):
    def test_the_cat_starts_still_and_ready(self):
        run = Run(random.Random(1))
        self.assertEqual((run.phase, run.cat.dir, run.cat.tile), ("ready", STOP, run.maze.start))
        play(run, 0.5)
        self.assertEqual(run.cat.pos, tuple(map(float, run.maze.start)))      # nothing moves during READY

    def test_it_moves_at_the_configured_speed_in_four_directions(self):
        run = running()
        run.steer(RIGHT)
        play(run, 0.5)
        self.assertAlmostEqual(run.cat.pos[0] - run.maze.start[0], cfg.CAT_SPEED * 0.5, places=1)
        self.assertEqual(run.cat.pos[1], run.maze.start[1])
        run.steer(UP)                     # the junction above (x = 12..13?) is found by simply holding up
        for _ in advance(run, 3.0):
            run.steer(UP)
            if run.cat.facing == UP and run.cat.dir == UP:
                break
        self.assertEqual(run.cat.facing, UP)

    def test_it_stops_exactly_at_a_wall_and_never_enters_it(self):
        run = running()
        run.steer(RIGHT)
        play(run, 3.0)
        self.assertEqual(run.cat.pos, (19.0, 13.0))                           # the end of the bottom corridor
        self.assertEqual(run.cat.dir, STOP)
        run.steer(RIGHT)
        play(run, 0.5)
        self.assertEqual(run.cat.pos, (19.0, 13.0))
        run.steer(DOWN)                                                       # a wall below: nothing happens
        play(run, 0.3)
        self.assertEqual(run.cat.pos, (19.0, 13.0))

    def test_the_cat_can_never_leave_the_corridors(self):
        run = running()
        rng = random.Random(5)
        for _ in advance(run, 40.0):
            if rng.random() < 0.06:
                run.steer(rng.choice((UP, DOWN, LEFT, RIGHT)))
            self.assertTrue(run.maze.is_open(run.cat.nearest_tile()))
            self.assertNotIn(run.cat.nearest_tile(), run.maze.restricted)
            self.assertTrue(on_lanes(run.cat.pos))

    def test_a_buffered_turn_is_taken_at_the_next_intersection(self):
        run = running()
        run.steer(RIGHT)
        play(run, 0.05)
        self.assertLess(run.cat.pos[0], 11.0)                                 # the crossing at x=11 is still ahead
        run.steer(UP)                                                         # pressed early
        self.assertEqual(run.cat.dir, RIGHT)                                  # still going right: no mid-tile turn
        for _ in advance(run, 0.5):
            if run.cat.dir == UP:
                break
        self.assertEqual(run.cat.dir, UP)
        self.assertEqual(run.cat.pos[0], 11.0)                                # turned exactly in the centre of the crossing
        self.assertTrue(run.maze.is_open((11, 12)))
        play(run, 0.3)
        self.assertEqual(run.cat.pos[0], 11.0)                                # and went straight up the new corridor

    def test_a_turn_too_early_for_the_buffer_waits_for_a_second_press(self):
        run = running()
        run.steer(RIGHT)
        play(run, 0.2)                                                        # x = 11.1: the next crossing is 0.7 s away
        run.steer(UP)
        play(run, cfg.TURN_BUFFER + 0.1)
        self.assertEqual(run.cat.dir, RIGHT)                                  # the buffer ran out: not a surprise turn
        run.steer(UP)                                                         # pressing (or holding) again re-arms it
        for _ in advance(run, 0.5):
            if run.cat.dir == UP:
                break
        self.assertEqual((run.cat.dir, run.cat.pos[0]), (UP, 15.0))

    def test_a_turn_buffer_expires(self):
        run = running()
        run.steer(RIGHT)
        play(run, 0.05)
        run.steer(UP)
        run.cat.buffer_ttl = 0.0                                              # long ago
        play(run, 3.0)
        self.assertEqual(run.cat.pos[1], run.maze.start[1])                   # it just kept going right to the wall

    def test_reversing_is_instant_and_keeps_the_position(self):
        run = running()
        run.steer(RIGHT)
        play(run, 0.2)
        before = run.cat.pos
        run.steer(LEFT)
        self.assertEqual(run.cat.dir, LEFT)
        after = run.cat.pos
        self.assertAlmostEqual(before[0], after[0], places=6)
        play(run, 0.2)
        self.assertLess(run.cat.pos[0], before[0])
        self.assertTrue(on_lanes(run.cat.pos))

    def test_a_blocked_turn_does_not_stop_the_cat(self):
        run = running()
        run.steer(RIGHT)
        play(run, 0.1)
        run.steer(DOWN)                                                       # a wall is below the bottom corridor
        play(run, 0.5)
        self.assertEqual(run.cat.dir, RIGHT)
        self.assertGreater(run.cat.pos[0], run.maze.start[0] + 1)

    def test_a_held_direction_waits_for_its_turn_when_the_cat_is_stopped(self):
        run = running()
        run.cat.place((19, 13))
        run.steer(LEFT)
        play(run, 0.3)
        self.assertEqual(run.cat.dir, LEFT)

    def test_simulation_is_independent_of_the_frame_rate(self):
        results = []
        for dt in (1 / 30, 1 / 60, 1 / 120, 1 / 240):
            run = running(seed=3)
            run.steer(RIGHT)
            play(run, 0.5, dt)
            run.steer(UP)
            play(run, 1.5, dt)
            results.append(run.cat.pos)
        for pos in results[1:]:
            self.assertAlmostEqual(pos[0], results[0][0], places=4)
            self.assertAlmostEqual(pos[1], results[0][1], places=4)

    def test_a_long_frame_is_capped_instead_of_teleporting_the_cat(self):
        run = running()
        run.steer(RIGHT)
        run.update(10.0)                                                      # a window drag: 10 s in one frame
        self.assertLessEqual(run.cat.pos[0] - run.maze.start[0], cfg.CAT_SPEED * cfg.MAX_FRAME + 1e-6)


class ScoringTests(unittest.TestCase):
    def test_eating_a_fish_scores_and_removes_it(self):
        run = running()
        total = run.fish_left
        run.steer(RIGHT)
        play(run, 0.5)
        self.assertEqual(run.fish_left, total - run.fish_eaten)
        self.assertEqual(run.score, run.fish_eaten * cfg.SCORES["fish"])
        self.assertGreaterEqual(run.fish_eaten, 2)

    def test_a_fish_is_scored_once(self):
        run = running()
        run.steer(RIGHT)
        play(run, 3.0)
        score = run.score
        run.steer(LEFT)
        play(run, 1.0)
        self.assertEqual(run.score, score)                                    # the corridor behind is already eaten

    def test_catnip_scores_and_is_not_a_regular_fish(self):
        run = running()
        run.fish.discard((18, 13))
        run.cat.place((18, 13))
        run.steer(RIGHT)
        play(run, 0.5)
        self.assertEqual(run.score, cfg.SCORES["catnip"])
        self.assertEqual(run.fish_eaten, 1)
        self.assertTrue(run.catnip_active)

    def test_golden_fish_appears_twice_per_level_and_is_worth_a_lot(self):
        run = running(seed=4)
        seen = 0
        for tile in sorted(run.fish)[:int(run.fish_total * 0.4)]:
            run.fish.discard(tile)
        play(run, 0.1)
        self.assertIsNotNone(run.golden)
        tile, left = run.golden
        self.assertIn(tile, set(run.maze.floor()))
        self.assertNotIn(tile, run.maze.restricted)
        self.assertAlmostEqual(left, cfg.GOLDEN_SECONDS, delta=0.2)
        run.cat.place(tile)
        play(run, 0.05)
        self.assertEqual(run.goldens, 1)
        self.assertEqual(run.score, cfg.SCORES["golden"])
        self.assertIsNone(run.golden)
        self.assertIn("golden", names(run))
        for t in sorted(run.fish)[:int(run.fish_total * 0.4)]:
            run.fish.discard(t)
        play(run, 0.1)
        seen = 1 if run.golden else 0
        self.assertEqual(seen, 1)                                             # the second one

    def test_a_golden_fish_expires(self):
        run = running(seed=4)
        for tile in sorted(run.fish)[:int(run.fish_total * 0.4)]:
            run.fish.discard(tile)
        play(run, 0.1)
        self.assertIsNotNone(run.golden)
        play(run, cfg.GOLDEN_SECONDS + 0.5)
        self.assertIsNone(run.golden)
        self.assertEqual(run.goldens, 0)

    def test_a_golden_fish_is_not_needed_to_clear_the_level(self):
        run = running(seed=4)
        for tile in list(run.fish)[:-1]:
            run.fish.discard(tile)
        self.assertEqual(run.fish_left, 1)
        last = next(iter(run.fish))
        run.golden = ((1, 5), 5.0)
        run.cat.place(last)
        play(run, 0.1)
        self.assertEqual(run.phase, "clear")

    def test_level_clear_bonus_grows_with_the_level(self):
        for level in (1, 2, 3):
            run = running(level=level)
            run.fish.clear()
            play(run, 0.05)
            self.assertEqual(run.phase, "clear")
            self.assertEqual(run.score, cfg.SCORES["level_clear"] + cfg.SCORES["level_clear_per_level"] * (level - 1))
            self.assertEqual(run.levels_cleared, 1)

    def test_an_extra_life_at_the_threshold_only_once(self):
        run = running()
        run._add_score(cfg.EXTRA_LIFE_AT - 1)
        self.assertEqual(run.lives, cfg.START_LIVES)
        run._add_score(1)
        self.assertEqual(run.lives, cfg.START_LIVES + 1)
        run._add_score(cfg.EXTRA_LIFE_AT)
        self.assertEqual(run.lives, cfg.START_LIVES + 1)
        self.assertIn("extra_life", names(run))

    def test_scoring_constants_are_balanced(self):
        s = cfg.SCORES
        self.assertLess(s["fish"], s["catnip"])
        self.assertLess(s["catnip"], s["golden"])
        self.assertEqual(list(s["disable"]), sorted(s["disable"]))            # each robot in a chain is worth more
        self.assertGreater(s["level_clear"], s["golden"])


class LifeAndLevelTests(unittest.TestCase):
    def catch(self, run):
        """Put an active Chase Bot on the cat."""
        robot = run.robots[1]
        robot.mode, robot.fright = "active", False
        robot.place(run.cat.nearest_tile())
        run.invulnerable = 0.0
        play(run, 0.02)

    def test_three_starting_lives(self):
        self.assertEqual(Run(random.Random(1)).lives, 3)

    def test_a_robot_touch_costs_one_life_and_starts_the_death_animation(self):
        run = running()
        self.catch(run)
        self.assertEqual((run.lives, run.phase), (2, "dying"))
        self.assertIn("life_lost", names(run))

    def test_after_the_animation_everyone_goes_back_to_start_and_eaten_fish_stay_eaten(self):
        run = running()
        run.steer(RIGHT)
        play(run, 1.0)
        eaten = run.fish_eaten
        left = run.fish_left
        self.catch(run)
        play(run, cfg.DYING_SECONDS + 0.1)
        self.assertEqual(run.phase, "ready")
        self.assertEqual(run.cat.tile, run.maze.start)
        self.assertTrue(all(r.mode == "den" for r in run.robots))
        self.assertEqual(run.fish_left, left)
        self.assertEqual(run.fish_eaten, eaten)

    def test_the_cat_is_protected_for_a_moment_after_each_restart(self):
        run = running()
        self.catch(run)
        play(run, cfg.DYING_SECONDS + cfg.READY_SECONDS + 0.1)
        self.assertEqual(run.phase, "run")
        self.assertGreater(run.invulnerable, 0)
        robot = run.robots[0]
        robot.mode, robot.fright = "active", False
        robot.place(run.cat.nearest_tile())
        play(run, 0.1)
        self.assertEqual(run.lives, 2)                                        # not caught during the grace period
        play(run, cfg.RESPAWN_GRACE)
        robot.place(run.cat.nearest_tile())
        play(run, 0.05)
        self.assertEqual(run.lives, 1)

    def test_the_last_life_ends_the_run(self):
        run = running()
        run.lives = 1
        self.catch(run)
        self.assertEqual(run.lives, 0)
        play(run, cfg.DYING_SECONDS + 0.1)
        self.assertEqual(run.phase, "over")
        self.assertTrue(run.over)
        self.assertIn("game_over", names(run))
        score = run.score
        run.steer(RIGHT)
        play(run, 1.0)
        self.assertEqual((run.score, run.cat.pos), (score, tuple(map(float, run.maze.start))))

    def test_clearing_a_level_goes_to_the_next_layout_with_lives_and_score_kept(self):
        run = running()
        run.lives = 2
        run.score = 1234
        run.fish.clear()
        play(run, 0.05)
        self.assertEqual(run.phase, "clear")
        self.assertIn("level_clear", names(run))
        play(run, cfg.CLEAR_SECONDS + 0.1)
        self.assertEqual((run.level, run.phase, run.lives), (2, "ready", 2))
        self.assertEqual(run.maze.name, "CIRCUIT GARDEN")
        self.assertGreater(run.score, 1234)
        self.assertEqual(run.fish_left, run.fish_total)
        self.assertEqual(run.cat.tile, run.maze.start)

    def test_the_clear_screen_can_be_skipped_but_not_instantly(self):
        run = running()
        run.fish.clear()
        play(run, 0.05)
        run.skip_clear()
        self.assertEqual(run.phase, "clear")
        play(run, cfg.CLEAR_SKIP_AFTER)
        run.skip_clear()
        self.assertEqual((run.phase, run.level), ("ready", 2))

    def test_levels_repeat_the_layouts_with_rising_difficulty(self):
        run = running()
        for _ in range(3):
            clear_level(run)
        self.assertEqual(run.level, 4)
        self.assertEqual(run.maze.name, "NEON ALLEY")
        self.assertGreater(run.diff.speed["chase"], cfg.difficulty_for(1).speed["chase"])
        self.assertLess(run.diff.catnip, cfg.difficulty_for(1).catnip)

    def test_nothing_moves_in_the_ready_and_dying_phases(self):
        run = Run(random.Random(1))
        run.steer(RIGHT)
        play(run, 1.0)
        self.assertEqual(run.cat.tile, run.maze.start)
        run.phase = "run"
        self.catch(run)
        pos = [r.pos for r in run.robots]
        play(run, 0.5)
        self.assertEqual([r.pos for r in run.robots], pos)


class CatnipTests(unittest.TestCase):
    def grab(self, run):
        run.fish.discard((19, 13))
        run.cat.place((19, 13))
        run._start_catnip()

    def test_catnip_makes_the_robots_frightened_and_turns_them_round(self):
        run = running()
        robot = run.robots[0]
        robot.mode = "active"
        robot.place((5, 1))
        robot.dir, robot.t = RIGHT, 0.5
        self.grab(run)
        self.assertTrue(all(r.fright for r in run.robots))
        self.assertEqual(robot.dir, LEFT)                                     # reversed on the spot
        self.assertTrue(run.catnip_active)

    def test_the_effect_lasts_the_configured_time_then_robots_recover(self):
        run = running()
        run.robots[0].mode = "active"
        run.robots[0].place((5, 1))
        self.grab(run)
        duration = run.diff.catnip
        play(run, duration - 0.3)
        self.assertTrue(run.catnip_active and run.robots[0].fright)
        play(run, 0.5)
        self.assertFalse(run.catnip_active)
        self.assertFalse(any(r.fright for r in run.robots))
        self.assertIn("catnip_end", names(run))

    def test_a_second_catnip_refreshes_but_never_stacks(self):
        run = running()
        self.grab(run)
        play(run, 3.0)
        self.assertLess(run.catnip_left, run.diff.catnip - 2.9)
        run._start_catnip()
        self.assertAlmostEqual(run.catnip_left, run.diff.catnip, places=6)
        run._start_catnip()
        self.assertLessEqual(run.catnip_left, run.diff.catnip)
        self.assertLessEqual(run.diff.catnip, 7.0)

    def test_frightened_robots_are_slower_and_flee(self):
        run = running()
        robot = run.robots[1]
        robot.mode = "active"
        robot.place((3, 5))
        self.grab(run)
        start = run.cat.nearest_tile()
        from neon_cat_maze.pathing import path_distance
        before = path_distance(run.maze, robot.tile, start)
        play(run, 1.5)
        after = path_distance(run.maze, robot.nearest_tile(), start)
        self.assertGreaterEqual(after, before - 1)                            # it did not charge at the cat
        self.assertLess(cfg.FRIGHT_SPEED, 1.0)

    def test_touching_a_frightened_robot_disables_it_for_bonus_points(self):
        run = running()
        robot = run.robots[0]
        robot.mode = "active"
        self.grab(run)
        score = run.score
        robot.place(run.cat.nearest_tile())
        play(run, 0.02)
        self.assertEqual(robot.mode, "eyes")
        self.assertEqual(run.score, score + cfg.SCORES["disable"][0])
        self.assertEqual(run.lives, cfg.START_LIVES)                          # and the cat was not hurt
        self.assertIn("disable", names(run))

    def test_a_chain_of_disabled_robots_pays_more_each_time_and_resets_with_the_next_catnip(self):
        run = running()
        self.grab(run)
        paid = []
        for robot in run.robots:
            robot.mode, robot.fright = "active", True
            robot.place(run.cat.nearest_tile())
            before = run.score
            play(run, 0.02)
            paid.append(run.score - before)
        self.assertEqual(paid, list(cfg.SCORES["disable"][:3]))
        run.catnip_left = 0.0001
        play(run, 0.05)
        self.grab(run)
        self.assertEqual(run.chain, 0)

    def test_a_disabled_robot_walks_home_rests_and_comes_back_hostile(self):
        run = running()
        robot = run.robots[0]
        robot.mode, robot.fright = "active", True
        robot.place((1, 1))
        self.grab(run)
        run.catnip_left = 100
        robot.place(run.cat.nearest_tile())
        run._disable(robot)
        run.cat.place((10, 13))
        self.assertEqual(robot.mode, "eyes")
        play(run, 12.0)
        self.assertIn(robot.mode, ("den", "exit", "active"))
        self.assertNotEqual(robot.mode, "eyes")
        run.catnip_left = 0
        run._tick_catnip(0.001)
        self.assertFalse(robot.fright)

    def test_a_non_frightened_robot_touch_is_dangerous_but_eyes_are_harmless(self):
        run = running()
        robot = run.robots[0]
        robot.mode = "eyes"
        robot.place(run.cat.nearest_tile())
        play(run, 0.05)
        self.assertEqual(run.lives, cfg.START_LIVES)


class SettlementTests(unittest.TestCase):
    def test_no_score_no_tickets(self):
        self.assertEqual(tickets_for(0, 5), 0)
        self.assertEqual(tickets_for(-100, -3), 0)

    def test_tickets_grow_with_score_and_levels_and_are_capped(self):
        self.assertEqual(tickets_for(450, 0), 1)
        self.assertEqual(tickets_for(900, 1), cfg.TICKETS["per_level_cleared"] + 2)
        self.assertEqual(tickets_for(10 ** 9, 100), cfg.TICKETS["cap"])
        self.assertLessEqual(tickets_for(2000, 0), tickets_for(2000, 2))

    def test_better_than_ranks_by_tickets_then_score_then_level(self):
        a, b = RunResult.of(2000, 2, 1), RunResult.of(1000, 5, 0)
        self.assertTrue(a.better_than(b))
        self.assertFalse(b.better_than(a))
        self.assertFalse(a.better_than(a))
        self.assertTrue(RunResult.of(10, 1, 0).better_than(RunResult()))


class DeterminismTests(unittest.TestCase):
    def trace(self, seed):
        run = Run(random.Random(seed))
        run.steer(RIGHT)
        out = []
        for i in range(60 * 30):
            if i % 45 == 0:
                run.steer((UP, LEFT, DOWN, RIGHT)[(i // 45) % 4])
            run.update(DT)
            if i % 30 == 0:
                out.append((run.cat.pos, tuple(r.pos for r in run.robots), run.score, run.lives))
        return out

    def test_the_same_seed_replays_exactly(self):
        self.assertEqual(self.trace(11), self.trace(11))

    def test_different_seeds_diverge(self):
        self.assertNotEqual(self.trace(11), self.trace(12))


if __name__ == "__main__":
    unittest.main()
