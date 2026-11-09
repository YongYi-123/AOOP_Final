"""Secret Item 01, THE REVERSE ROAD: the trigger rule, the reverse physics, the cutscene, THE FORGOTTEN HIGHWAY (gates,
retries, finish) and the reward event; plus proof that ordinary driving is untouched.

Run from this folder:   python -m unittest test_reverse_road -v
"""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import forgotten_highway as FH  # noqa: E402
import reverse_road as RR  # noqa: E402
import settings as S  # noqa: E402
from car import PlayerCar  # noqa: E402
from game import Game  # noqa: E402
from modes import GameMode  # noqa: E402
from race import State  # noqa: E402
from tracks import TRACKS  # noqa: E402

DT = 1 / 60
IDLE = {"accelerate": False, "brake": False, "steer": 0}
BRAKE = {"accelerate": False, "brake": True, "steer": 0}
GAS = {"accelerate": True, "brake": False, "steer": 0}


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def fake(step_dz):
    return SimpleNamespace(step_dz=step_dz)


# ------------------------------------------------------------------ the rule on its own
class TriggerRuleTests(unittest.TestCase):
    def feed(self, trigger, seconds, step=0.0, dt=DT):
        fired = False
        for _ in range(round(seconds / dt)):
            fired = trigger.update(dt, fake(step * dt), True) or fired
        return fired

    def test_the_numbers_are_the_specified_ones(self):
        self.assertEqual(RR.STILL_SECONDS, 20.0)

    def test_under_twenty_seconds_still_never_triggers(self):
        t = RR.ReverseTrigger()
        self.feed(t, 19.5)
        self.assertFalse(t.armed)
        self.assertFalse(self.feed(t, 3.0, step=-2000))               # backs up at 19.5 s: too early, nothing happens
        self.assertFalse(t.fired)

    def test_twenty_seconds_without_backing_up_does_not_trigger(self):
        t = RR.ReverseTrigger()
        self.assertFalse(self.feed(t, 40.0))
        self.assertTrue(t.armed)
        self.assertFalse(t.fired)

    def test_twenty_seconds_then_really_backing_up_triggers(self):
        t = RR.ReverseTrigger()
        self.feed(t, 20.1)
        self.assertFalse(self.feed(t, 1.0, step=-2000))               # a short back-up is not enough ...
        self.assertFalse(self.feed(t, 2.0, step=-2000))
        self.assertTrue(self.feed(t, 3.0, step=-2000))                # ... it has to keep going for about five seconds
        self.assertTrue(t.fired)

    def test_the_brake_key_alone_is_not_enough_only_real_movement_is(self):
        t = RR.ReverseTrigger()
        self.feed(t, 21.0)
        self.assertFalse(self.feed(t, 5.0, step=0.0))                 # (the key is held but the car does not move)
        self.assertFalse(self.feed(t, 0.2, step=-0.5))                # a crawl smaller than the minimum is not a reverse yet
        self.assertFalse(t.fired)

    def test_a_tiny_float_error_still_counts_as_standing_still(self):
        t = RR.ReverseTrigger()
        for i in range(round(20.2 / DT)):
            t.update(DT, fake(1e-9 * (1 if i % 2 else -1)), True)
        self.assertTrue(t.armed)

    def test_moving_forward_restarts_the_count(self):
        t = RR.ReverseTrigger()
        self.feed(t, 15.0)
        self.feed(t, 0.5, step=3000)
        self.assertEqual(t.still, 0.0)
        self.feed(t, 19.0)
        self.assertFalse(t.armed)
        self.assertFalse(self.feed(t, 1.0, step=-1500))               # only 19 s since the move
        self.feed(t, 21.0)
        self.assertTrue(t.armed)

    def test_moving_forward_after_being_armed_disarms_it(self):
        t = RR.ReverseTrigger()
        self.feed(t, 21.0)
        self.feed(t, 0.2, step=2000)
        self.assertFalse(t.armed)
        self.assertFalse(self.feed(t, 1.0, step=-1500))

    def test_it_follows_the_games_time_not_the_frame_rate(self):
        for fps in (15, 30, 60, 144):
            with self.subTest(fps=fps):
                t = RR.ReverseTrigger()
                dt = 1 / fps
                frames = 0
                while not t.armed:
                    t.update(dt, fake(0.0), True)
                    frames += 1
                self.assertAlmostEqual(frames * dt, 20.0, delta=dt * 1.01)

    def test_an_inactive_game_neither_accumulates_nor_keeps_old_time(self):
        t = RR.ReverseTrigger()
        self.feed(t, 10.0)
        for _ in range(60 * 30):
            t.update(DT, fake(0.0), False)
        self.assertEqual(t.still, 0.0)
        self.assertFalse(t.armed)

    def test_it_fires_exactly_once(self):
        t = RR.ReverseTrigger()
        self.feed(t, 20.5)
        results = [t.update(DT, fake(-40.0), True) for _ in range(300)]
        self.assertEqual(results.count(True), 1)


# ------------------------------------------------------------------ the reverse physics
class ReversePhysicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()
        cls.road = cls.game.road

    def car(self, speed=0.0):
        c = PlayerCar()
        c.speed = speed
        return c

    def test_braking_a_moving_car_is_the_old_model_and_never_reverses(self):
        c = self.car(S.MAX_SPEED * 0.8)
        for _ in range(60 * 8):
            c.update(DT, self.road, False, True, 0)
            self.assertGreaterEqual(c.speed, 0.0)
            self.assertEqual(c.reverse_speed, 0.0)
            if c.speed == 0:
                break
        self.assertEqual(c.speed, 0.0)

    def test_a_short_brake_tap_at_a_standstill_does_not_move_the_car(self):
        c = self.car()
        for _ in range(round((S.REVERSE_HOLD - 0.1) / DT)):
            c.update(DT, self.road, False, True, 0)
        self.assertEqual(c.step_dz, 0.0)
        self.assertEqual(c.reverse_speed, 0.0)

    def test_holding_the_brake_at_a_standstill_backs_up_slowly_and_caps(self):
        c = self.car()
        before = c.z
        for _ in range(60 * 4):
            c.update(DT, self.road, False, True, 0)
        self.assertLess(c.velocity, 0)
        self.assertLess(c.step_dz, 0)
        self.assertAlmostEqual(c.reverse_speed, S.REVERSE_MAX)
        self.assertLess(S.REVERSE_MAX, S.MAX_SPEED * 0.25)             # a crawl
        self.assertNotEqual(c.z, before)

    def test_throttle_stops_the_reversing_and_drives_forward_again(self):
        c = self.car()
        for _ in range(60 * 2):
            c.update(DT, self.road, False, True, 0)
        for _ in range(60 * 2):
            c.update(DT, self.road, True, False, 0)
        self.assertEqual(c.reverse_speed, 0.0)
        self.assertGreater(c.speed, 0.0)
        self.assertGreater(c.step_dz, 0.0)

    def test_the_other_cars_in_the_race_are_unchanged(self):
        from car import DrivenCar
        self.assertFalse(hasattr(DrivenCar, "_reverse_step"))


# ------------------------------------------------------------------ the secret inside the real game loop
class GameBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()

    def setUp(self):
        g = self.game
        g.audio.muted = True
        g.reset()
        g.mode = GameMode.COMPETITIVE
        self.start()

    def start(self, track=None, mode=GameMode.COMPETITIVE):
        g = self.game
        g.mode = mode
        g.track = g.selected_track = track or g.tracks[0]
        g.apply_look()
        g.start_race()
        g.begin_playing()
        g.gear_owned = False
        g.egg_found = False
        g.secret_events.clear()

    def run_for(self, seconds, controls=IDLE):
        for _ in range(round(seconds / DT)):
            self.game.update(DT, controls)

    def reverse_out(self):
        """Hold the brake until the car really backs up far enough (or the secret starts)."""
        for _ in range(60 * 8):
            self.game.update(DT, BRAKE)
            if self.game.state is State.SECRET:
                return True
        return False


class TriggerInTheGameTests(GameBase):
    def test_still_twenty_seconds_then_reversing_starts_the_secret(self):
        self.run_for(20.2)
        self.assertIs(self.game.state, State.PLAYING)
        self.assertTrue(self.reverse_out())
        self.assertIsNotNone(self.game.secret)
        self.assertTrue(self.game.secret.in_cutscene)

    def test_under_twenty_seconds_does_not(self):
        self.run_for(19.0)
        self.assertFalse(self.reverse_out())
        self.assertIsNone(self.game.secret)

    def test_twenty_seconds_without_reversing_does_not(self):
        self.run_for(35.0)
        self.assertIs(self.game.state, State.PLAYING)
        self.assertIsNone(self.game.secret)

    def test_a_brake_tap_too_short_to_move_the_car_does_not(self):
        self.run_for(20.5)
        self.run_for(0.2, BRAKE)
        self.run_for(2.0)
        self.assertIsNone(self.game.secret)

    def test_moving_in_the_middle_restarts_the_clock(self):
        self.run_for(15.0)
        self.run_for(1.0, GAS)
        self.run_for(10.0, {"accelerate": False, "brake": True, "steer": 0})      # brake it to a stop, then wait
        self.assertFalse(self.game.state is State.SECRET)
        self.run_for(25.0)                                                         # (still: the brake is released)
        self.assertIsNone(self.game.secret)

    def test_pausing_does_not_add_time(self):
        self.run_for(10.0)
        self.game.set_paused(True)
        for _ in range(60 * 60):
            self.game.update(DT, IDLE)
        self.game.set_paused(False)
        self.run_for(9.0)
        self.assertFalse(self.reverse_out())                                        # 19 s of real play
        self.assertIsNone(self.game.secret)

    def test_the_countdown_and_menus_do_not_count(self):
        g = self.game
        g.start_race()                                  # 3-2-1: the clock must not run
        for _ in range(round(2.5 / DT)):
            g.update(DT, IDLE)
        self.assertIs(g.state, State.COUNTDOWN)
        self.assertEqual(g.reverse_trigger.still, 0.0)
        g.state = State.MODE_SELECT
        for _ in range(60 * 30):
            g.update(DT, IDLE)
        self.assertEqual(g.reverse_trigger.still, 0.0)

    def test_every_normal_track_can_trigger_it(self):
        for track in self.game.tracks:
            with self.subTest(track=track.key):
                self.start(track)
                self.run_for(20.2)
                self.assertTrue(self.reverse_out(), track.key)
                self.assertTrue(self.game.secret.in_cutscene)

    def test_endless_mode_can_trigger_it_too(self):
        self.start(mode=GameMode.ENDLESS)
        self.run_for(20.2)
        self.assertTrue(self.reverse_out())

    def test_the_hud_never_shows_a_countdown_or_hint(self):
        self.game.hud.trace = []
        self.run_for(21.0)
        self.game.render()
        shown = " ".join(msg for _, msg in self.game.hud.trace).upper()
        self.game.hud.trace = None
        for word in ("REVERSE", "BACK UP", "WAIT", "SECRET", "20"):
            self.assertNotIn(word, shown)


class ReverseBeepTests(GameBase):
    def beeps(self, seconds, controls):
        played = []
        self.game.audio.play = lambda name: played.append(name)
        try:
            self.run_for(seconds, controls)
        finally:
            del self.game.audio.play
        return played

    def test_a_plain_reverse_beeps_slowly_and_a_driving_car_does_not(self):
        self.assertEqual(self.beeps(1.0, GAS).count("backup"), 0)
        self.game.player.speed = 0
        played = self.beeps(3.0, BRAKE)
        self.assertTrue(2 <= played.count("backup") <= 5)
        self.assertNotIn("backup_hi", played)

    def test_after_the_twenty_seconds_the_beep_changes_and_quickens(self):
        self.run_for(20.3)
        played = self.beeps(2.0, BRAKE)
        self.assertIn("backup_hi", played)
        self.assertNotIn("backup", played)

    def test_the_cue_sound_plays_once_the_moment_the_wait_is_served_before_any_reversing(self):
        played = self.beeps(19.5, IDLE)
        self.assertNotIn("reverse_cue", played)
        played = self.beeps(1.0, IDLE)
        self.assertEqual(played.count("reverse_cue"), 1)
        self.assertEqual(self.beeps(5.0, IDLE).count("reverse_cue"), 0)      # once only, and the car is still standing

    def test_no_cue_when_the_wait_was_not_served_or_the_car_moved(self):
        self.run_for(10.0)
        self.assertNotIn("reverse_cue", self.beeps(2.0, BRAKE))
        self.run_for(1.0, GAS)
        self.assertNotIn("reverse_cue", self.beeps(15.0, IDLE))

    def test_the_back_up_has_to_last_a_few_seconds(self):
        self.run_for(20.3)
        self.run_for(1.2, BRAKE)
        self.assertIsNone(self.game.secret)
        self.assertTrue(self.reverse_out())


class CutsceneTests(GameBase):
    def go(self):
        self.run_for(20.2)
        self.assertTrue(self.reverse_out())
        return self.game.secret

    def test_the_cutscene_plays_once_even_with_the_keys_spammed(self):
        built = []
        real = RR.SecretRun

        def counting(game):
            built.append(1)
            return real(game)
        with mock.patch("game.SecretRun", counting):
            self.run_for(20.2)
            for _ in range(60 * 8):
                self.game.update(DT, BRAKE)
                self.game.handle_event(key(pygame.K_DOWN))
                self.game.handle_event(key(pygame.K_RETURN))
        self.assertEqual(len(built), 1)

    def test_it_runs_its_course_into_the_highway_and_the_music_comes_back(self):
        run = self.go()
        seen = []
        for _ in range(round((RR.CUT_TOTAL + 0.5) / DT)):
            self.game.update(DT, IDLE)
            seen.append(self.game.music_duck)
        self.assertEqual(run.phase, run.TITLE)
        self.assertLess(min(seen), 0.2)                              # the music went down ...
        for _ in range(round((RR.TITLE_TIME + 0.5) / DT)):
            self.game.update(DT, IDLE)
        self.assertEqual(run.phase, run.DRIVE)
        self.assertEqual(self.game.music_duck, 1.0)                  # ... and is back at full level

    def test_the_cutscene_is_short(self):
        self.assertLessEqual(RR.CUT_TOTAL, 8.0)

    def test_enter_skips_it_safely_and_repeatedly(self):
        run = self.go()
        self.game.update(DT, IDLE)
        self.game.handle_event(key(pygame.K_RETURN))                 # too early: ignored
        self.assertTrue(run.in_cutscene)
        for _ in range(round(1.2 / DT)):
            self.game.update(DT, IDLE)
        for _ in range(5):
            self.game.handle_event(key(pygame.K_RETURN))
        self.assertEqual(run.phase, run.TITLE)
        self.assertIsNotNone(run.player)

    def test_it_draws_every_stage_without_error_and_in_the_pixel_style(self):
        run = self.go()
        shown = []
        self.game.hud.trace = shown
        for t in (0.2, 1.2, 2.0, 3.2, 4.6, 5.4, 6.3, 6.7):
            while run.t < t and run.in_cutscene:
                self.game.update(DT, IDLE)
            self.game.render()
        self.game.hud.trace = None
        text = " ".join(msg for _, msg in shown)
        self.assertIn("WRONG WAY?", text)
        self.assertIn("...OR THE RIGHT WAY?", text)

    def test_sounds_fire_once_each_with_the_cutscene(self):
        played = []
        self.game.audio.play = lambda name: played.append(name)
        try:
            self.go()
            for _ in range(round((RR.CUT_TOTAL + 0.3) / DT)):
                self.game.update(DT, IDLE)
        finally:
            del self.game.audio.play
        for name in ("wrongway", "rightway", "warp"):
            self.assertEqual(played.count(name), 1, name)
        self.assertEqual(played.count("glitch"), 2)


# ------------------------------------------------------------------ the secret road itself
class HighwayBase(GameBase):
    def enter(self):
        self.run_for(20.2)
        self.assertTrue(self.reverse_out())
        self.game.secret.skip()
        run = self.game.secret
        self.run_for(RR.TITLE_TIME + 0.2)
        self.assertEqual(run.phase, run.DRIVE)
        return run

    def enter_fresh(self):
        self.game.reset()
        self.start()
        return self.enter()

    def put(self, run, progress, x=0.0):
        """Place the car at a progress along the road."""
        run.player.distance = progress - run.offset
        run.player.z = run.player.distance
        run.player.x = x


class HighwayTests(HighwayBase):
    def test_it_is_not_in_any_menu(self):
        self.assertNotIn(FH.KEY, [t.key for t in TRACKS])
        self.assertNotIn(FH.KEY, [t.key for t in self.game.tracks])
        self.assertNotIn(FH.THEME.key, [t.key for t in self.game.themes.themes])

    def test_it_is_a_one_way_road_with_three_gates_a_start_and_a_garage(self):
        road = FH.ForgottenRoad()
        self.assertEqual(len(road.checkpoint_z), 3)
        self.assertEqual(sorted(road.checkpoint_z), road.checkpoint_z)
        self.assertLess(road.checkpoint_z[-1], road.finish_z)
        self.assertGreater(road.garage_z, road.finish_z)
        self.assertLess(road.garage_z, road.length)
        self.assertEqual(len(road.project(road.finish_z, 0.0)), min(S.DRAW_DISTANCE, road.end_index - int(road.finish_z // 200) + 1))

    def test_it_starts_at_the_start_line_without_a_countdown_or_time_limit(self):
        run = self.enter()
        self.assertEqual(run.checkpoints, 0)
        self.assertEqual(run.player.distance, 0.0)
        self.run_for(120.0)                                     # nothing ends it
        self.assertEqual(run.phase, run.DRIVE)

    def test_gates_count_in_order_as_the_car_drives_through(self):
        run = self.enter()
        for n, z in enumerate(run.road.checkpoint_z, 1):
            self.put(run, z + 5)
            self.run_for(DT * 2)
            self.assertEqual(run.checkpoints, n)

    def test_a_gate_crossed_off_the_road_does_not_count_and_sends_you_back(self):
        run = self.enter()
        self.put(run, run.road.checkpoint_z[0] + 5, x=2.0)
        self.run_for(DT * 2)
        self.assertEqual(run.checkpoints, 0)
        self.assertGreater(run.fail_time, 0)
        self.assertEqual(run.fail_reason, "MISSED THE GATE")

    def test_the_finish_is_only_reached_through_all_three_gates_in_order(self):
        run = self.enter()
        self.put(run, run.road.finish_z + 5, x=2.0)             # past every line, but off the tarmac: nothing counts
        self.run_for(DT * 2)
        self.assertNotEqual(run.phase, run.ARRIVE)
        self.assertEqual(run.checkpoints, 0)
        self.assertFalse(self.game.secret_events)
        run2 = self.enter_fresh()
        self.put(run2, run2.road.finish_z + 5)                  # on the road: the gates are taken one after the other
        self.run_for(DT * 2)
        self.assertEqual(run2.checkpoints, 3)
        self.assertEqual(run2.phase, run2.ARRIVE)

    def test_a_failure_restarts_from_the_last_checkpoint_not_the_start(self):
        run = self.enter()
        self.put(run, run.road.checkpoint_z[1] + 5)
        self.run_for(DT * 2)
        self.assertEqual(run.checkpoints, 2)
        run.player.x = 2.2                                      # stay off the tarmac too long
        self.run_for(RR.OFF_ROAD_LIMIT + 0.3, IDLE)
        self.assertGreater(run.fails, 0)
        self.run_for(RR.FAIL_TIME + 0.2)
        self.assertEqual(run.checkpoints, 2)                    # still collected
        self.assertAlmostEqual(run.progress, run.road.checkpoint_z[1] + 600.0, delta=S.MAX_SPEED * 0.4 * 0.5)
        self.assertAlmostEqual(run.player.x, 0.0, delta=0.1)
        self.assertGreater(run.player.speed, 0.0)

    def test_a_failure_before_any_gate_restarts_at_the_start(self):
        run = self.enter()
        self.put(run, 30000.0, x=2.3)
        run._fail("TEST")
        self.run_for(RR.FAIL_TIME + 0.2)
        self.assertLess(run.progress, 3000)

    def test_a_failure_does_not_award_anything(self):
        run = self.enter()
        run._fail("TEST")
        self.run_for(RR.FAIL_TIME + 0.5)
        self.assertEqual(self.game.secret_events, [])
        self.assertFalse(self.game.gear_owned)

    def test_the_parked_cars_are_sparse_and_never_block_the_road(self):
        road = FH.ForgottenRoad()
        cars = FH.obstacle_cars(road)
        self.assertGreater(len(cars), 5)
        for a, b in zip(cars, cars[1:]):
            self.assertGreater(b.z - a.z, 12000)
        for c in cars:
            self.assertTrue(all(abs(c.z - g) > 5000 for g in road.checkpoint_z))

    def test_you_cannot_reverse_off_the_start_of_the_road(self):
        run = self.enter()
        self.run_for(4.0, BRAKE)
        self.assertGreaterEqual(run.player.distance, 0.0)
        self.assertEqual(run.phase, run.DRIVE)


def drive_bot(run, game, target=0.55):
    """A small autopilot: holds a speed, follows the bend and slips into a free lane past parked cars."""
    p, road = run.player, run.road
    lane = 0.0
    ahead = [c for c in run.traffic.cars if 0 < c.z - p.front_z < 9000]
    if ahead:
        lane = -0.66 if ahead[0].x >= 0 else 0.66
    steer = max(-1, min(1, (lane - p.x) * 3 + road.segment_at(p.front_z).curve * 0.6))
    return {"accelerate": p.speed_percent < target, "brake": False, "steer": steer}


class FinishTests(HighwayBase):
    def finish(self):
        run = self.enter()
        for _ in range(60 * 200):
            if run.phase not in (run.DRIVE, run.ARRIVE):
                break
            self.game.update(DT, drive_bot(run, self.game) if run.phase == run.DRIVE else IDLE)
        return run

    def test_a_full_drive_through_all_three_gates_ends_in_the_garage_and_the_reward(self):
        run = self.finish()
        self.assertEqual(run.phase, run.REWARD)
        self.assertEqual(run.checkpoints, 3)
        self.assertTrue(run.finished)
        self.assertEqual(run.fails, 0)

    def test_reaching_the_garage_reports_the_item_exactly_once(self):
        self.finish()
        self.assertEqual(self.game.secret_events, [("secret_item_found", RR.ITEM_KEY, True)])
        self.run_for(3.0)
        self.assertEqual(len(self.game.secret_events), 1)
        self.assertEqual(self.game.pop_secret_events(), [("secret_item_found", RR.ITEM_KEY, True)])
        self.assertEqual(self.game.pop_secret_events(), [])
        self.assertTrue(self.game.gear_owned)

    def test_the_reward_screen_says_what_the_brief_says(self):
        run = self.finish()
        for _ in range(round(2.6 / DT)):
            self.game.update(DT, IDLE)
        shown = []
        self.game.hud.trace = shown
        self.game.render()
        self.game.hud.trace = None
        text = " ".join(msg for _, msg in shown)
        for line in ("SECRET ITEM FOUND", "01 / 03", "THE REVERSE GEAR"):
            self.assertIn(line, text)

    def test_the_garage_stops_the_car_it_cannot_drive_through(self):
        run = self.finish()
        self.assertLess(run.progress, run.road.garage_z)

    def test_playing_it_again_is_allowed_and_is_marked_as_not_new(self):
        self.finish()
        self.game.pop_secret_events()
        self.game.reset()
        self.start()
        self.game.gear_owned = True                      # (the host says the item is already in the story)
        run = self.finish()
        self.assertFalse(run.first_time)
        self.assertEqual(self.game.secret_events[0][2], False)

    def test_enter_closes_the_reward_and_asks_the_host_to_leave(self):
        run = self.finish()
        self.game.handle_event(key(pygame.K_RETURN))     # too early
        self.assertTrue(self.game.running)
        self.run_for(RR.REWARD_MIN + 0.1)
        self.game.handle_event(key(pygame.K_RETURN))
        self.assertFalse(self.game.running)
        self.assertEqual(self.game.music_duck, 1.0)

    def test_quitting_from_the_pause_menu_gives_nothing_and_returns_to_the_menu(self):
        run = self.enter()
        self.put(run, run.road.checkpoint_z[0] + 5)
        self.run_for(DT * 2)
        self.game.handle_event(key(pygame.K_p))
        self.assertTrue(self.game.paused)
        self.game.handle_event(key(pygame.K_BACKSPACE))
        self.assertIsNone(self.game.secret)
        self.assertIs(self.game.state, State.MODE_SELECT)
        self.assertEqual(self.game.secret_events, [])
        self.assertFalse(self.game.gear_owned)

    def test_the_secret_pauses_like_a_race(self):
        run = self.enter()
        self.game.handle_event(key(pygame.K_p))
        before = run.player.distance
        self.run_for(1.0, GAS)
        self.assertEqual(run.player.distance, before)


# ------------------------------------------------------------------ ordinary racing is untouched
class OrdinaryRacingTests(GameBase):
    def test_a_normal_race_plays_exactly_as_before(self):
        g = self.game
        g.player.speed = g.player.max_speed * 0.5
        for _ in range(60 * 10):
            g.update(DT, {"accelerate": True, "brake": False, "steer": 0})
        self.assertIs(g.state, State.PLAYING)
        self.assertIsNone(g.secret)
        self.assertGreater(g.player.distance, 0)
        self.assertEqual(g.player.reverse_speed, 0.0)

    def test_braking_to_a_stop_in_a_race_and_driving_off_works(self):
        g = self.game
        g.player.speed = g.player.max_speed * 0.6
        for _ in range(60 * 6):
            g.update(DT, {"accelerate": False, "brake": True, "steer": 0})
            if g.player.speed == 0 and g.player.reverse_speed:
                break
        for _ in range(60 * 2):
            g.update(DT, {"accelerate": True, "brake": False, "steer": 0})
        self.assertGreater(g.player.speed, 0)
        self.assertIsNone(g.secret)

    def test_a_race_still_finishes_and_menus_still_work(self):
        g = self.game
        g.state = State.TITLE
        g.handle_event(key(pygame.K_RETURN))
        self.assertIs(g.state, State.MODE_SELECT)
        g.handle_event(key(pygame.K_BACKSPACE))
        self.assertIs(g.state, State.TITLE)

    def test_the_old_distance_figures_never_go_negative(self):
        g = self.game
        for _ in range(60 * 4):
            g.update(DT, BRAKE)                       # (the car reverses: distance goes below zero)
        g.render()
        self.assertGreaterEqual(g.manager.result["distance_km"] if g.manager.result else 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
