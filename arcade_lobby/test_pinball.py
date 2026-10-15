"""LUCKY CAT PINBALL: the physics and rules (pinball.py), the money and saved run (pinball_table.py)
and the profile's pinball data. No window and no hub needed.
Run headless from this folder:   python -m unittest test_pinball
"""
import math
import os
import random
import unittest
from datetime import date, timedelta

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pinball as pb  # noqa: E402
from game_clock import GameClock  # noqa: E402
from pinball_table import GAME_ID, PinballTable, reward_for  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from settings import (PINBALL_DAILY_TICKET_CAP, PINBALL_DAILY_TOKEN_CAP, PINBALL_MAX_TICKETS,  # noqa: E402
                      PINBALL_POINTS_PER_TICKET, PINBALL_TOKEN_REWARD, PINBALL_TOKEN_SCORE)

DT = 1 / 60
DAY1 = date(2026, 3, 10)


def kinds(events):
    return [e.kind for e in events]


def run(world, seconds, dt=DT):
    out = []
    for _ in range(round(seconds / dt)):
        out += world.advance(dt)
    return out


def playing(x, y, vx=0.0, vy=0.0, balls=1):
    """A world with the ball in play at (x, y)."""
    w = pb.PinballWorld()
    w.start_run()
    w.ball_no = balls
    w.phase = "play"
    w.bx, w.by, w.vx, w.vy = x, y, vx, vy
    return w


def shoot(world, pull):
    world.hold_plunger(True)
    run(world, pull * pb.PULL_TIME)
    return world.hold_plunger(False)


def table(tokens=10, clock=None):
    p = PlayerProfile(tokens=tokens, clock=clock or GameClock(lambda: DAY1))
    saves = []
    p.subscribe_save(lambda: saves.append(p.to_dict()))
    p.saves = saves
    return p, PinballTable(p)


def drain_ball(t):
    """Put the live ball just over the drain line and let the table notice."""
    w = t.world
    w.phase, w.bx, w.by, w.vx, w.vy = "play", 60.0, pb.DRAIN_Y + 1, 0.0, 50.0
    return t.update(DT)


def update_for(t, seconds):
    out = []
    for _ in range(round(seconds / DT)):
        out += t.update(DT)
    return out


def finish_bonus(t):
    return update_for(t, pb.BONUS_TIME + 0.1)


class PhysicsTests(unittest.TestCase):
    def test_gravity_pulls_the_ball_down_and_damping_slows_it(self):
        w = playing(45, 125)
        run(w, 0.5)
        self.assertGreater(w.vy, 100)
        self.assertLess(w.vy, pb.GRAVITY * 0.5)               # damping: a bit less than free fall
        fast = playing(60, 80, vx=300, vy=0)                  # flying sideways in open air
        run(fast, 0.05)
        self.assertLess(fast.vx, 300)

    def test_the_speed_never_exceeds_the_cap_and_the_ball_never_tunnels(self):
        w = playing(60, 120, vx=5000, vy=-5000)
        for _ in range(600):
            w.advance(DT)
            self.assertLessEqual(math.hypot(w.vx, w.vy), pb.MAX_SPEED * 1.02 + 1)
            if w.phase != "play":
                break
        self.assertLess(pb.MAX_SPEED * pb.STEP, pb.R)          # one step is always under the ball's radius

    def test_the_walls_keep_the_ball_inside(self):
        w = playing(60, 100, vx=-400, vy=0)
        run(w, 0.4)
        self.assertGreaterEqual(w.bx, pb.R)                    # bounced off the left wall
        self.assertGreater(w.vx, -50)
        w = playing(60, 100, vx=0, vy=-500)                    # straight up into the top arc
        for _ in range(240):
            w.advance(DT)
            self.assertGreater(w.by, -2)

    def test_a_long_random_game_keeps_the_ball_in_bounds_and_makes_progress(self):
        rng = random.Random(5)
        w = pb.PinballWorld()
        w.start_run()
        for _ in range(3):
            shoot(w, rng.uniform(0.5, 1.0))
            for i in range(60 * 60):
                if i % 7 == 0:
                    w.set_flippers(rng.random() < 0.5, rng.random() < 0.5)
                w.advance(DT)
                if w.phase == "play":
                    self.assertTrue(-5 <= w.bx <= pb.W + 5 and -5 <= w.by <= pb.H + 30, (w.bx, w.by))
                if w.phase == "bonus":
                    break
            run(w, pb.BONUS_TIME + 0.2)
            if w.phase == "over":
                break
        self.assertGreater(w.score, 0)

    def test_the_simulation_is_deterministic(self):
        def play():
            w = pb.PinballWorld()
            w.start_run()
            shoot(w, 0.8)
            seq = random.Random(11)
            ev = []
            for i in range(60 * 20):
                if i % 9 == 0:
                    ev += w.set_flippers(seq.random() < 0.5, seq.random() < 0.5)
                ev += w.advance(DT)
            return (w.bx, w.by, w.vx, w.vy, w.score, w.phase), kinds(ev)
        self.assertEqual(play(), play())

    def test_the_frame_rate_does_not_change_the_result(self):
        def play(dt):
            w = pb.PinballWorld()
            w.start_run()
            w.hold_plunger(True)
            run(w, 0.5, dt)
            w.hold_plunger(False)
            run(w, 6.0, dt)
            return round(w.bx, 6), round(w.by, 6), w.score
        self.assertEqual(play(1 / 60), play(1 / 120))
        self.assertEqual(play(1 / 60), play(1 / 240))

    def test_a_long_hitch_is_dropped_not_replayed(self):
        w = playing(60, 20)
        w.advance(5.0)                                         # a 5 s stall
        self.assertLess(w.time, pb.STEP * pb.MAX_STEPS_PER_UPDATE + 1e-6)


class LaunchTests(unittest.TestCase):
    def test_a_new_run_waits_with_the_ball_in_the_plunger_lane(self):
        w = pb.PinballWorld()
        self.assertEqual(w.phase, "idle")
        w.start_run()
        self.assertEqual((w.phase, w.ball_no, w.score), ("ready", 1, 0))
        self.assertGreater(w.bx, pb.LANE_X)
        run(w, 1.0)
        self.assertEqual(w.phase, "ready")                     # it rests on the plunger
        self.assertGreater(w.by, pb.H - 24)

    def test_holding_the_plunger_charges_it_and_releasing_launches_the_ball(self):
        w = pb.PinballWorld()
        w.start_run()
        self.assertEqual(w.hold_plunger(True), [])
        run(w, 0.4)
        self.assertGreater(w.pull, 0.3)
        events = w.hold_plunger(False)
        self.assertEqual(kinds(events), ["launch"])
        self.assertEqual(w.phase, "play")
        self.assertLess(w.vy, -pb.LAUNCH_MIN)
        self.assertEqual(w.pull, 0.0)

    def test_a_longer_pull_launches_harder(self):
        speeds = []
        for pull in (0.2, 0.6, 1.0):
            w = pb.PinballWorld()
            w.start_run()
            shoot(w, pull)
            speeds.append(-w.vy)
        self.assertLess(speeds[0], speeds[1])
        self.assertLess(speeds[1], speeds[2])
        self.assertLessEqual(speeds[2], pb.LAUNCH_MAX + 1)

    def test_a_tap_is_a_weak_shot_that_falls_back_to_the_plunger(self):
        w = pb.PinballWorld()
        w.start_run()
        w.hold_plunger(True)
        events = w.hold_plunger(False)                         # pressed and released at once
        self.assertEqual(kinds(events), ["launch"])
        run(w, 4.0)
        self.assertEqual(w.phase, "play")
        self.assertGreater(w.bx, pb.LANE_X)                    # back in the lane, not drained
        self.assertTrue(w.can_launch())
        self.assertEqual(kinds(shoot(w, 0.8)), ["launch"])     # and it can be shot again

    def test_a_full_shot_travels_round_the_top_arc_into_the_playfield(self):
        w = pb.PinballWorld()
        w.start_run()
        shoot(w, 0.9)
        seen = False
        for _ in range(60 * 6):
            w.advance(DT)
            if w.bx < pb.LANE_X - 10 and w.by < 120:
                seen = True
                break
        self.assertTrue(seen)

    def test_the_gate_lets_a_ball_up_but_not_back_into_the_lane(self):
        w = playing(132, 100, vx=0, vy=-300)                   # rising through the gate
        run(w, 0.15)
        self.assertLess(w.by, 90)
        w = playing(131, 60, vx=0, vy=40)                      # falling onto it from above
        run(w, 1.5)
        self.assertLess(w.bx, pb.LANE_X + 1)                   # it slid off into the playfield

    def test_launching_is_refused_unless_the_ball_rests_in_the_lane(self):
        w = playing(60, 100)
        self.assertFalse(w.can_launch())
        self.assertEqual(w.hold_plunger(True), [])
        self.assertFalse(w.pulling)
        self.assertEqual(w.launch(), [])
        idle = pb.PinballWorld()
        self.assertEqual(idle.hold_plunger(True), [])
        self.assertEqual(idle.launch(), [])


class FlipperTests(unittest.TestCase):
    def test_pressing_raises_the_flipper_and_releasing_lowers_it(self):
        w = pb.PinballWorld()
        w.start_run()
        f = w.flippers[-1]
        self.assertAlmostEqual(f.angle, pb.FLIPPER_REST)
        events = w.set_flippers(True, False)
        self.assertEqual(kinds(events), ["flipper"])
        run(w, 0.12)
        self.assertAlmostEqual(f.angle, pb.FLIPPER_UP)
        self.assertAlmostEqual(w.flippers[1].angle, pb.FLIPPER_REST)    # only the left one moved
        w.set_flippers(False, False)
        run(w, 0.2)
        self.assertAlmostEqual(f.angle, pb.FLIPPER_REST)

    def test_a_quick_tap_still_swings_the_flipper_up(self):
        w = pb.PinballWorld()
        w.start_run()
        w.set_flippers(False, True)
        w.set_flippers(False, False)                           # released before a single step ran
        run(w, 0.04)
        self.assertLess(w.flippers[1].angle, pb.FLIPPER_REST - 0.3)

    def test_the_flipper_swings_fast_enough_to_feel_snappy(self):
        w = pb.PinballWorld()
        w.start_run()
        w.set_flippers(True, True)
        run(w, 0.06)
        self.assertGreater(w.flippers[-1].raised, 0.9)

    def test_a_raised_flipper_hits_the_ball_up_and_away(self):
        w = playing(40, 190)                                   # resting on the left flipper
        run(w, 0.05)
        w.set_flippers(True, False)
        vy_before = w.vy
        events = run(w, 0.2)
        self.assertLess(w.vy, vy_before - 50)                  # kicked upward
        self.assertIn("flip_hit", kinds(events))

    def test_an_idle_flipper_just_lets_the_ball_roll_down_it(self):
        w = playing(34, 190)
        run(w, 0.4)
        self.assertGreater(w.bx, 40)                           # rolling towards the middle gap
        self.assertGreater(w.vx, 0)

    def test_a_ball_down_the_middle_drains(self):
        w = playing(61, 150)
        events = run(w, 2.0)
        self.assertIn("drain", kinds(events))

    def test_a_ball_down_an_outlane_drains_too(self):
        w = playing(5, 120)
        events = run(w, 2.0)
        self.assertIn("drain", kinds(events))

    def test_a_flipper_press_changes_the_lit_lane(self):
        w = playing(60, 120)
        w.lanes = [True, False]
        w.set_flippers(True, False)
        self.assertEqual(w.lanes, [False, True])
        w.set_flippers(True, False)                            # still held: no second change
        self.assertEqual(w.lanes, [False, True])


class ScoringTests(unittest.TestCase):
    def test_a_bumper_kicks_the_ball_away_and_scores(self):
        bx, by = pb.BUMPERS[1]
        w = playing(bx - pb.BUMPER_R - pb.R + 0.5, by, vx=60, vy=0)
        events = run(w, 0.05)
        hit = [e for e in events if e.kind == "bumper"]
        self.assertEqual(len(hit), 1)
        self.assertEqual((hit[0].points, w.score), (pb.BUMPER_POINTS, pb.BUMPER_POINTS))
        self.assertLess(w.vx, -pb.BUMPER_KICK * 0.7)           # the kick: much faster than it came in
        self.assertGreater(w.bumper_flash[1], 0)

    def test_a_bumper_scores_once_per_touch_not_every_step(self):
        bx, by = pb.BUMPERS[0]
        w = playing(bx, by - pb.BUMPER_R - 2, vx=0, vy=100)
        run(w, 0.08)
        self.assertEqual(w.stats["bumpers"], 1)

    def test_the_kick_is_stronger_than_a_wall_bounce(self):
        bx, by = pb.BUMPERS[2]
        a = playing(bx + 14, by, vx=-120, vy=0)
        run(a, 0.03)
        wall = playing(5.5, 100, vx=-120, vy=0)
        run(wall, 0.03)
        self.assertGreater(math.hypot(a.vx, a.vy), 2 * math.hypot(wall.vx, wall.vy))

    def test_lucky_cat_mode_makes_bumpers_pay_more(self):
        bx, by = pb.BUMPERS[1]
        w = playing(bx - pb.BUMPER_R - pb.R + 0.5, by, vx=60)
        w.lucky_left = 5
        run(w, 0.05)
        self.assertEqual(w.score, pb.LUCKY_BUMPER_POINTS)
        self.assertGreater(pb.LUCKY_BUMPER_POINTS, pb.BUMPER_POINTS)

    def test_a_lane_scores_once_and_both_lanes_raise_the_multiplier_and_light_the_scoop(self):
        x, y, wd, h = pb.LANES[0]
        w = playing(x + wd / 2, y + h / 2)
        w.scoop_lit = False
        events = run(w, 0.02)
        self.assertEqual([e.points for e in events if e.kind == "lane"], [pb.LANE_POINTS])
        self.assertEqual(w.lanes, [True, False])
        run(w, 0.0)
        x2, y2, w2, h2 = pb.LANES[1]
        w.bx, w.by, w.vx, w.vy = x2 + w2 / 2, y2 + h2 / 2, 0, 0
        events = run(w, 0.02)
        self.assertIn("lanes_done", kinds(events))
        self.assertEqual(w.score, 2 * pb.LANE_POINTS + pb.LANES_DONE_POINTS)
        self.assertEqual((w.mult, w.lanes, w.scoop_lit), (2, [False, False], True))

    def test_the_multiplier_stops_at_its_maximum(self):
        w = playing(60, 100)
        for _ in range(8):
            w.lanes = [True, False]
            x2, y2, w2, h2 = pb.LANES[1]
            w.bx, w.by, w.vx, w.vy = x2 + w2 / 2, y2 + h2 / 2, 0, 0
            w.in_lane = [False, False]
            run(w, 0.02)
        self.assertEqual(w.mult, pb.MAX_MULT)

    def hit_target(self, w, i):
        (x0, y0), (x1, y1) = pb.TARGETS[i]
        w.cat_flash = 0
        w.bx, w.by, w.vx, w.vy = x0 - pb.R - 1.0, (y0 + y1) / 2, 80.0, 0.0
        return run(w, 0.05)

    def test_a_target_lights_and_scores_and_a_repeat_pays_little(self):
        w = playing(60, 120)
        events = self.hit_target(w, 0)
        self.assertEqual([e.points for e in events if e.kind == "target"], [pb.TARGET_POINTS])
        self.assertEqual(w.targets, [True, False, False])
        events = self.hit_target(w, 0)
        self.assertEqual([e.points for e in events if e.kind == "target"], [pb.TARGET_REPEAT_POINTS])

    def test_c_a_t_completes_the_cat_pays_and_starts_lucky_cat_mode(self):
        w = playing(60, 120)
        self.assertEqual(w.lucky_left, 0)
        for i in (0, 1):
            self.hit_target(w, i)
        score = w.score
        events = self.hit_target(w, 2)
        self.assertIn("cat", kinds(events))
        self.assertIn("lucky_start", kinds(events))
        self.assertEqual(w.score - score, pb.TARGET_POINTS + pb.CAT_POINTS)
        self.assertEqual((w.cats, w.stats["cats"], w.stats["lucky"]), (1, 1, 1))
        self.assertAlmostEqual(w.lucky_left, pb.LUCKY_TIME, delta=0.1)
        self.assertGreater(w.cat_flash, 0)
        self.assertTrue(w.scoop_lit)

    def test_the_cat_letters_flash_then_reset(self):
        w = playing(60, 60)
        w.targets = [True, True, True]
        w.cat_flash = pb.CAT_FLASH
        run(w, pb.CAT_FLASH + 0.1)
        self.assertEqual(w.targets, [False, False, False])

    def test_each_cat_pays_more_up_to_a_limit(self):
        w = playing(60, 60)
        pays = []
        for _ in range(6):
            w.targets = [True, True, False]
            before = w.score
            self.hit_target(w, 2)
            pays.append(w.score - before - pb.TARGET_POINTS)
            w.cat_flash = 0
            w.targets = [False] * 3
        self.assertEqual(pays[:3], [3000, 4000, 5000])
        self.assertEqual(pays[-1], pb.CAT_MAX)

    def test_lucky_cat_mode_lasts_twelve_seconds_of_play(self):
        w = playing(60, 120)
        w.lucky_left = pb.LUCKY_TIME
        w.bx, w.by = 131.0, pb.H - 12                          # parked on the plunger: no scoring, ball stays
        w.phase = "play"
        run(w, 5.0)
        self.assertAlmostEqual(w.lucky_left, pb.LUCKY_TIME - 5.0, delta=0.05)
        events = run(w, 7.5)
        self.assertEqual(w.lucky_left, 0)
        self.assertEqual(kinds(events).count("lucky_end"), 1)

    def test_a_second_cat_during_lucky_mode_refreshes_the_timer_without_a_second_start(self):
        w = playing(60, 120)
        w.lucky_left = 4.0
        w.targets = [True, True, False]
        events = self.hit_target(w, 2)
        self.assertNotIn("lucky_start", kinds(events))
        self.assertAlmostEqual(w.lucky_left, pb.LUCKY_TIME, delta=0.1)

    def test_lucky_mode_does_not_run_down_between_balls(self):
        w = playing(60, 120)
        w.lucky_left = 8.0
        drain_ball_world = w
        drain_ball_world.by = pb.DRAIN_Y + 1
        run(w, 0.05)
        self.assertEqual(w.phase, "bonus")
        left = w.lucky_left
        run(w, 1.0)
        self.assertEqual(w.lucky_left, left)

    def test_the_scoop_holds_the_ball_pays_once_then_darkens_and_ejects(self):
        sx, sy = pb.SCOOP
        w = playing(sx + 2, sy)
        events = run(w, 0.02)
        self.assertEqual([e.points for e in events if e.kind == "scoop"], [pb.SCOOP_POINTS])
        self.assertGreater(w.captured, 0)
        self.assertFalse(w.scoop_lit)
        pos = (w.bx, w.by)
        events = run(w, pb.SCOOP_HOLD / 2)
        self.assertEqual((w.bx, w.by), pos)                    # held still
        events = run(w, pb.SCOOP_HOLD / 2 + 0.03)
        self.assertIn("eject", kinds(events))
        self.assertLess(w.vy, 0)                               # spat upwards
        w.bx, w.by, w.vx, w.vy = sx + 1, sy, 0, 0              # the same ball comes back
        w.scoop_cool = 0
        events = run(w, 0.02)
        self.assertEqual([e.points for e in events if e.kind == "scoop"], [pb.SCOOP_UNLIT])

    def test_the_scoop_pays_double_in_lucky_mode_when_lit(self):
        sx, sy = pb.SCOOP
        w = playing(sx, sy)
        w.lucky_left = 5
        run(w, 0.02)
        self.assertEqual(w.score, pb.LUCKY_SCOOP_POINTS)

    def test_the_scoop_cannot_be_farmed_by_looping_the_ball_through_it(self):
        sx, sy = pb.SCOOP
        w = playing(sx, sy)
        paid = 0
        for _ in range(12):
            w.bx, w.by, w.vx, w.vy, w.scoop_cool, w.captured = sx, sy, 0, 0, 0, 0
            events = run(w, 0.02) + run(w, pb.SCOOP_HOLD + 0.1)
            paid += sum(e.points for e in events if e.kind == "scoop")
        self.assertEqual(paid, pb.SCOOP_POINTS + 11 * pb.SCOOP_UNLIT)

    def test_the_ball_is_ejected_a_different_way_each_time(self):
        w = playing(60, 120)
        directions = []
        for _ in range(3):
            w.bx, w.by, w.vx, w.vy, w.scoop_cool, w.captured = pb.SCOOP[0], pb.SCOOP[1], 0, 0, 0, 0
            run(w, 0.02)
            run(w, pb.SCOOP_HOLD + 0.01)
            directions.append((round(w.vx), round(w.vy)))
        self.assertEqual(len(set(directions)), 3)


class BallLifecycleTests(unittest.TestCase):
    def test_a_drain_loses_the_ball_pays_the_bonus_and_loads_the_next_ball(self):
        w = playing(60, 100)
        w.ball_bumpers, w.ball_targets, w.mult = 10, 2, 2
        score = w.score
        events = run(w, 0.0)
        w.by = pb.DRAIN_Y + 1
        events = run(w, 0.02)
        self.assertEqual(w.phase, "bonus")
        self.assertEqual(kinds(events), ["drain"])
        expected = (10 * pb.BONUS_PER_BUMPER + 2 * pb.BONUS_PER_TARGET) * 2
        self.assertEqual(events[0].points, expected)
        self.assertEqual(w.score, score + expected)
        self.assertEqual(w.last_bonus, (10, 2, 2, expected))
        events = run(w, pb.BONUS_TIME + 0.1)
        self.assertEqual(kinds(events), ["ball_start"])
        self.assertEqual((w.phase, w.ball_no, w.mult, w.ball_bumpers), ("ready", 2, 1, 0))
        self.assertGreater(w.bx, pb.LANE_X)

    def test_the_bumper_part_of_the_bonus_is_capped(self):
        w = playing(60, 100)
        w.ball_bumpers = 500
        w.by = pb.DRAIN_Y + 1
        run(w, 0.02)
        self.assertEqual(w.last_bonus[3], pb.BONUS_BUMPER_CAP * pb.BONUS_PER_BUMPER)

    def test_three_balls_then_the_run_is_over_exactly_once(self):
        w = pb.PinballWorld()
        w.start_run()
        overs = 0
        for n in range(1, 4):
            self.assertEqual(w.ball_no, n)
            w.phase, w.bx, w.by, w.vx, w.vy = "play", 60.0, pb.DRAIN_Y + 1, 0.0, 0.0
            run(w, 0.02)
            overs += kinds(run(w, pb.BONUS_TIME + 0.1)).count("run_over")
        self.assertEqual((w.phase, overs, w.ball_no), ("over", 1, 3))
        self.assertEqual(run(w, 3.0), [])                      # nothing more happens

    def test_controls_do_nothing_between_balls_or_after_the_run(self):
        w = playing(60, 100)
        w.by = pb.DRAIN_Y + 1
        run(w, 0.02)
        self.assertEqual(w.phase, "bonus")
        self.assertEqual(w.hold_plunger(True), [])
        self.assertEqual(w.launch(), [])

    def test_a_ball_that_hardly_moves_gets_nudged(self):
        w = playing(61, 80)
        w.bx, w.by = pb.BUMPERS[3][0], pb.BUMPERS[3][1] - pb.BUMPER_R - pb.R    # balanced on the lower bumper
        w.vx = w.vy = 0
        w.advance(DT)
        w.vx = w.vy = 0
        w.slow = pb.STUCK_AFTER - 0.001
        run(w, 0.1)
        self.assertGreaterEqual(w.nudges, 1)

    def test_the_cat_centrepiece_and_art_geometry_match_the_physics(self):
        import pinball_art as art
        self.assertEqual(art.P(0, 0), art.TABLE_POS)
        for x, y in pb.BUMPERS:
            self.assertTrue(pb.BUMPER_R < x < pb.LANE_X - pb.BUMPER_R)
        for i, (a, b) in enumerate(pb.TARGETS):
            self.assertLess(a[0], pb.LANE_X)
        self.assertEqual(len(pb.TARGETS), len(pb.TARGET_LETTERS))
        self.assertGreaterEqual(len(pb.BUMPERS), 3)
        self.assertLessEqual(len(pb.BUMPERS), 5)
        self.assertEqual(len(pb.LANES), 2)


class RewardTests(unittest.TestCase):
    def test_tickets_follow_the_score_with_a_per_run_cap(self):
        self.assertEqual(reward_for(0), (0, 0))
        self.assertEqual(reward_for(PINBALL_POINTS_PER_TICKET - 1), (0, 0))
        self.assertEqual(reward_for(PINBALL_POINTS_PER_TICKET), (1, 0))
        self.assertEqual(reward_for(3 * PINBALL_POINTS_PER_TICKET + 10)[0], 3)
        self.assertEqual(reward_for(10 ** 9)[0], PINBALL_MAX_TICKETS)
        self.assertEqual(reward_for(-5), (0, 0))

    def test_a_token_comes_back_only_for_a_rare_big_score(self):
        self.assertEqual(reward_for(PINBALL_TOKEN_SCORE - 1)[1], 0)
        self.assertEqual(reward_for(PINBALL_TOKEN_SCORE)[1], PINBALL_TOKEN_REWARD)
        self.assertLessEqual(PINBALL_TOKEN_REWARD, 1)

    def test_the_most_a_run_can_pay_is_modest_next_to_the_other_lucky_corner_games(self):
        tickets, tokens = reward_for(10 ** 9)
        self.assertLessEqual(tickets, 12)
        self.assertLessEqual(tokens, 1)
        self.assertLessEqual(PINBALL_DAILY_TICKET_CAP, 30)      # the same daily ceiling NEON 21 and COIN PUSHER use
        self.assertLessEqual(PINBALL_DAILY_TOKEN_CAP, 2)


class TableStartTests(unittest.TestCase):
    def test_start_charges_exactly_one_token_and_records_the_run(self):
        p, t = table(5)
        self.assertEqual(t.state, "idle")
        self.assertTrue(t.start())
        self.assertEqual(p.tokens, 4)
        self.assertEqual(p.pinball_run, {"score": 0, "ball": 1})
        self.assertEqual((t.state, t.world.phase, t.world.ball_no), ("play", "ready", 1))
        self.assertEqual(p.to_dict()["lifetime_tokens_spent"], 1)

    def test_a_second_start_while_a_run_is_live_charges_nothing(self):
        p, t = table(5)
        t.start()
        for _ in range(5):
            self.assertFalse(t.start())
        self.assertEqual(p.tokens, 4)
        self.assertEqual(t.start_block_reason(), "IN PLAY")

    def test_no_tokens_means_no_run_and_no_charge(self):
        p, t = table(0)
        self.assertFalse(t.start())
        self.assertEqual((p.tokens, p.pinball_run, t.state), (0, None, "idle"))
        self.assertEqual(t.start_block_reason(), "NO TOKENS")
        self.assertEqual(p.saves, [])                          # not even a save was asked for

    def test_paused_or_closed_tables_refuse_to_start(self):
        p, t = table(5)
        t.pause()
        self.assertFalse(t.start())
        self.assertEqual(t.start_block_reason(), "PAUSED")
        t.resume()
        t.close()
        self.assertFalse(t.start())
        self.assertEqual(p.tokens, 5)

    def test_the_token_is_never_taken_without_a_run_on_record(self):
        p, t = table(5)
        t.start()
        for snap in p.saves:                                    # every save that has the token spent has the run too
            if snap["tokens"] == 4:
                self.assertEqual(snap["pinball"]["run"], {"score": 0, "ball": 1})

    def test_inputs_are_ignored_unless_a_run_is_live(self):
        p, t = table(5)
        self.assertEqual(t.set_flippers(True, True), [])
        self.assertEqual(t.hold_plunger(True), [])
        self.assertEqual(update_for(t, 1.0), [])
        t.start()
        t.pause()
        self.assertEqual(t.set_flippers(True, True), [])
        self.assertEqual(t.update(1.0), [])
        self.assertEqual(t.world.time, 0.0)


class TableSettlementTests(unittest.TestCase):
    def play_out(self, t, score):
        """Three drains with `score` on the board (the third pays the run)."""
        t.world.score = score
        for _ in range(3):
            drain_ball(t)
            finish_bonus(t)

    def test_a_finished_run_pays_tickets_for_its_score_exactly_once(self):
        p, t = table(5)
        t.start()
        t.world.score = 14000                                   # 2 tickets' worth (the end-of-ball bonuses add a little)
        self.play_out(t, 14000)
        r = t.result
        self.assertEqual((r.score, r.tickets, r.tokens), (14000, 2, 0))
        self.assertEqual(p.tickets, 2)
        self.assertEqual(t.state, "result")
        self.assertIsNone(p.pinball_run)
        update_for(t, 8.0)
        t.close()
        t.close()
        self.assertEqual((p.tickets, t.settled), (2, 1))

    def test_the_run_is_settled_only_when_the_third_ball_drains(self):
        p, t = table(5)
        t.start()
        t.world.score = 50000
        drain_ball(t)
        finish_bonus(t)
        drain_ball(t)
        finish_bonus(t)
        self.assertEqual((p.tickets, t.result), (0, None))
        self.assertEqual(p.pinball_run["ball"], 3)
        drain_ball(t)
        self.assertEqual(p.tickets, 0)                          # the bonus is still on show
        finish_bonus(t)
        self.assertGreater(p.tickets, 0)

    def test_a_big_score_pays_the_capped_tickets_and_one_token(self):
        p, t = table(5)
        t.start()
        self.play_out(t, 400000)
        self.assertEqual((t.result.tickets, t.result.tokens), (PINBALL_MAX_TICKETS, 1))
        self.assertEqual((p.tickets, p.tokens), (PINBALL_MAX_TICKETS, 4 + 1))

    def test_a_zero_score_run_pays_nothing_and_is_still_settled(self):
        p, t = table(5)
        t.start()
        self.play_out(t, 0)
        self.assertEqual((t.result.tickets, t.result.tokens, p.tickets), (0, 0, 0))
        self.assertIsNone(p.pinball_run)
        self.assertTrue(t.can_start())

    def test_the_high_score_is_recorded_and_only_improves(self):
        p, t = table(5)
        t.start()
        self.play_out(t, 8000)
        self.assertTrue(t.result.new_best)
        best = p.high_score(GAME_ID)
        self.assertGreaterEqual(best, 8000)
        t.start()
        self.play_out(t, 100)
        self.assertFalse(t.result.new_best)
        self.assertEqual(p.high_score(GAME_ID), best)

    def test_pinball_tickets_are_winnings_not_earned_tickets(self):
        p, t = table(5)
        earned = p.to_dict()["lifetime_tickets_earned"]
        t.start()
        self.play_out(t, 30000)
        self.assertGreater(p.tickets, 0)
        self.assertEqual(p.to_dict()["lifetime_tickets_earned"], earned)

    def test_the_daily_ticket_cap_clips_the_payout_and_says_so(self):
        p, t = table(50)
        paid = 0
        for _ in range(5):
            t.start()
            self.play_out(t, 100000)
            paid += t.result.tickets
        self.assertEqual(paid, PINBALL_DAILY_TICKET_CAP)
        self.assertTrue(t.result.capped)
        self.assertEqual(t.result.tickets, 0)
        self.assertEqual(p.pinball_ticket_room(), 0)
        self.assertEqual(p.tickets, PINBALL_DAILY_TICKET_CAP)

    def test_the_daily_token_cap_limits_the_token_bonus(self):
        p, t = table(50)
        for _ in range(PINBALL_DAILY_TOKEN_CAP + 2):
            t.start()
            self.play_out(t, 60000)
        self.assertEqual(p.pinball_tokens_today(), PINBALL_DAILY_TOKEN_CAP)
        self.assertEqual(p.pinball_token_room(), 0)

    def test_the_caps_reset_on_the_next_calendar_day(self):
        day = {"d": DAY1}
        p, t = table(50, clock=GameClock(lambda: day["d"]))
        for _ in range(4):
            t.start()
            self.play_out(t, 100000)
        self.assertEqual(p.pinball_ticket_room(), 0)
        day["d"] = DAY1 + timedelta(days=1)
        self.assertEqual((p.pinball_ticket_room(), p.pinball_token_room()), (PINBALL_DAILY_TICKET_CAP, PINBALL_DAILY_TOKEN_CAP))

    def test_settling_twice_pays_once(self):
        p, t = table(5)
        t.start()
        t.world.score = 25000
        first = t._settle(25000)
        again = t._settle(25000)
        self.assertEqual(p.tickets, 5)
        self.assertIs(again, t.result)
        self.assertEqual(first.tickets, 5)

    def test_the_payout_reaches_the_save_in_the_same_write_that_clears_the_run(self):
        p, t = table(5)
        t.start()
        self.play_out(t, 20000)
        after_start = [snap for snap in p.saves if snap["lifetime_tokens_spent"] == 1]
        cleared = [snap for snap in after_start if "run" not in snap.get("pinball", {})]
        self.assertTrue(cleared)
        for snap in cleared:                                    # the run is never cleared before its reward is in the same file
            self.assertEqual(snap["tickets"], p.tickets)
            self.assertGreaterEqual(snap["high_scores"][GAME_ID], 20000)
        self.assertTrue(all("run" in s["pinball"] for s in after_start if s["tickets"] == 0 and s["lifetime_tokens_spent"] == 1
                            and "pinball" in s and s["high_scores"].get(GAME_ID, 0) == 0))


class TableExitTests(unittest.TestCase):
    def test_leaving_mid_run_pays_the_score_so_far_once_and_forfeits_the_rest(self):
        p, t = table(5)
        t.start()
        t.world.score = 12000
        t.close()
        self.assertEqual((t.result.score, t.result.tickets, t.result.forfeited), (12000, 2, True))
        self.assertEqual(p.tickets, 2)
        self.assertIsNone(p.pinball_run)
        t.close()
        self.assertEqual((p.tickets, t.settled), (2, 1))
        self.assertFalse(t.live)

    def test_leaving_an_idle_machine_changes_nothing(self):
        p, t = table(5)
        t.close()
        self.assertEqual((p.tokens, p.tickets, t.result), (5, 0, None))
        self.assertEqual(p.saves, [])

    def test_leaving_after_the_result_does_not_pay_again(self):
        p, t = table(5)
        t.start()
        t.world.score = 10000
        for _ in range(3):
            drain_ball(t)
            finish_bonus(t)
        tickets = p.tickets
        t.close()
        self.assertEqual(p.tickets, tickets)

    def test_pausing_saves_the_run_and_freezes_the_machine(self):
        p, t = table(5)
        t.start()
        t.world.score = 777
        t.pause()
        self.assertEqual(p.pinball_run, {"score": 777, "ball": 1})
        self.assertEqual(p.saves[-1]["pinball"]["run"]["score"], 777)
        time = t.world.time
        t.update(2.0)
        self.assertEqual(t.world.time, time)
        t.resume()
        t.update(0.1)
        self.assertGreater(t.world.time, time)

    def test_pausing_drops_a_half_pulled_plunger(self):
        p, t = table(5)
        t.start()
        t.hold_plunger(True)
        update_for(t, 0.3)
        self.assertGreater(t.world.pull, 0)
        t.pause()
        self.assertEqual((t.world.pull, t.world.pulling), (0.0, False))

    def test_a_drain_saves_the_score_and_the_next_ball(self):
        p, t = table(5)
        t.start()
        t.world.score = 4321
        drain_ball(t)
        self.assertEqual(p.pinball_run["ball"], 2)
        self.assertGreaterEqual(p.pinball_run["score"], 4321)


class TableCrashTests(unittest.TestCase):
    def test_a_crash_right_after_start_keeps_the_token_spent_and_pays_the_empty_run_on_return(self):
        p, t = table(5)
        t.start()
        crashed = PlayerProfile.from_dict(p.saves[-1], clock=p.clock)           # the file as it was when the app died
        self.assertEqual(crashed.tokens, 4)
        self.assertEqual(crashed.pinball_run, {"score": 0, "ball": 1})
        t2 = PinballTable(crashed)
        self.assertEqual((t2.result.score, t2.result.recovered, t2.state), (0, True, "result"))
        self.assertEqual((crashed.tokens, crashed.tickets), (4, 0))
        self.assertIsNone(crashed.pinball_run)

    def test_a_crash_mid_run_pays_the_last_saved_score_once(self):
        p, t = table(5)
        t.start()
        t.world.score = 16000
        drain_ball(t)                                           # the ball end saved the score
        crashed = PlayerProfile.from_dict(p.saves[-1], clock=p.clock)
        t2 = PinballTable(crashed)
        self.assertTrue(t2.result.recovered)
        self.assertEqual((t2.result.score, crashed.tickets), (p.pinball_run["score"], 3))
        t3 = PinballTable(PlayerProfile.from_dict(crashed.saves[-1] if hasattr(crashed, "saves") else crashed.to_dict(), clock=p.clock))
        self.assertIsNone(t3.result)                            # a third visit finds nothing owed
        self.assertEqual(crashed.tickets, 3)

    def test_reopening_after_a_settled_run_never_pays_it_again(self):
        p, t = table(5)
        t.start()
        t.world.score = 30000
        for _ in range(3):
            drain_ball(t)
            finish_bonus(t)
        tickets = p.tickets
        for _ in range(3):
            again = PinballTable(PlayerProfile.from_dict(p.to_dict(), clock=p.clock))
            self.assertIsNone(again.result)
        self.assertEqual(PlayerProfile.from_dict(p.to_dict()).tickets, tickets)

    def test_every_save_is_consistent_over_a_whole_simulated_run(self):
        """Replay a full run and check the books at every single save the profile asked for."""
        p, t = table(5)
        problems = []

        def check():
            s = p.to_dict()
            run_open = "run" in s.get("pinball", {})
            spent = s["lifetime_tokens_spent"]
            if run_open and spent != 1:
                problems.append(("run without its token", spent))
            if not run_open and spent == 1 and s["tickets"] == 0 and s["high_scores"].get(GAME_ID, 0) > 0:
                problems.append(("score recorded but tickets missing", s["tickets"]))
        p.subscribe_save(check)
        rng = random.Random(3)
        t.start()
        for _ in range(3):
            t.hold_plunger(True)
            update_for(t, rng.uniform(0.3, 0.9))
            t.hold_plunger(False)
            for i in range(60 * 90):
                if i % 11 == 0:
                    t.set_flippers(rng.random() < 0.5, rng.random() < 0.5)
                t.update(DT)
                if t.world.phase == "bonus":
                    break
            update_for(t, pb.BONUS_TIME + 0.2)
        self.assertEqual(t.state, "result")
        self.assertEqual(problems, [])


class ProfileDataTests(unittest.TestCase):
    def test_a_profile_without_pinball_data_is_unchanged_on_disk(self):
        p = PlayerProfile(tokens=5)
        self.assertNotIn("pinball", p.to_dict())
        q = PlayerProfile.from_dict(p.to_dict())
        self.assertIsNone(q.pinball_run)
        self.assertEqual((q.pinball_tickets_today(), q.pinball_tokens_today()), (0, 0))

    def test_an_old_save_with_other_games_loads_and_gains_the_data_only_when_used(self):
        old = {"tokens": 9, "tickets": 3, "coin_pusher": {"date": "2026-01-01", "tickets": 4}, "neon21": {"date": "x", "tickets": 2}}
        p = PlayerProfile.from_dict(old)
        self.assertEqual((p.tokens, p.tickets), (9, 3))
        self.assertNotIn("pinball", p.to_dict())
        self.assertIn("coin_pusher", p.to_dict())

    def test_the_run_and_the_daily_counters_round_trip(self):
        p = PlayerProfile(tokens=5, clock=GameClock(lambda: DAY1))
        p.set_pinball_run({"score": 900, "ball": 2})
        p.award_pinball(3, 1)
        q = PlayerProfile.from_dict(p.to_dict(), clock=p.clock)
        self.assertEqual(q.pinball_run, {"score": 900, "ball": 2})
        self.assertEqual((q.pinball_tickets_today(), q.pinball_tokens_today()), (3, 1))
        self.assertEqual((q.tickets, q.tokens), (p.tickets, p.tokens))

    def test_corrupt_pinball_data_is_ignored_without_crashing(self):
        for junk in ("x", [1], {"run": "x"}, {"run": {"score": "a", "ball": -3}}, {"tickets": -4, "tokens": True, "date": 5}, None):
            p = PlayerProfile.from_dict({"tokens": 7, "pinball": junk})
            self.assertEqual(p.tokens, 7)
            run = p.pinball_run
            self.assertTrue(run is None or (run["score"] >= 0 and run["ball"] >= 1))
            self.assertGreaterEqual(p.pinball_ticket_room(), 0)
            PinballTable(PlayerProfile.from_dict({"tokens": 7, "pinball": junk}))     # and the machine opens

    def test_a_saved_run_is_not_shared_by_copying_the_returned_object(self):
        p = PlayerProfile()
        p.set_pinball_run({"score": 5, "ball": 1})
        p.pinball_run["score"] = 99999
        self.assertEqual(p.pinball_run["score"], 5)

    def test_players_have_separate_wallets_runs_and_caps(self):
        a, ta = table(5)
        b, tb = table(5)
        ta.start()
        ta.world.score = 25000
        ta.close()
        self.assertEqual((a.tickets, a.tokens), (5, 4))
        self.assertEqual((b.tickets, b.tokens, b.pinball_run), (0, 5, None))
        self.assertEqual(b.pinball_ticket_room(), PINBALL_DAILY_TICKET_CAP)

    def test_award_pinball_never_pays_over_the_caps_or_negative_amounts(self):
        p = PlayerProfile(clock=GameClock(lambda: DAY1))
        self.assertEqual(p.award_pinball(10 ** 6, 10 ** 6), (PINBALL_DAILY_TICKET_CAP, PINBALL_DAILY_TOKEN_CAP))
        self.assertEqual(p.award_pinball(5, 5), (0, 0))
        with self.assertRaises(ValueError):
            p.award_pinball(-1, 0)


if __name__ == "__main__":
    unittest.main()
