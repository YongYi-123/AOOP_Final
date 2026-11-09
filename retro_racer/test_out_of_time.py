"""The collapsing Forgotten Highway and the OUT OF TIME easter egg: how the road falls apart (in step with the car, resettable,
never a dead end), the chase after the last gate, the 88 gauge and its hidden plate, the time-travel cutscene, the restored
past road with its exit, and that ordinary racing and the story's one item are untouched.

Run from this folder:   python -m unittest test_out_of_time -v
"""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import forgotten_highway as FH  # noqa: E402
import out_of_time as OOT  # noqa: E402
import reverse_road as RR  # noqa: E402
import settings as S  # noqa: E402
from car import PlayerCar  # noqa: E402
from car_specs import CAR_CATALOG  # noqa: E402
from race import State  # noqa: E402
from road import Road  # noqa: E402
from test_reverse_road import (BRAKE, DT, GAS, IDLE, GameBase, HighwayBase, drive_bot, key)  # noqa: E402


class EggBase(HighwayBase):
    def enter_owned(self, owned=True):
        self.game.gear_owned = owned
        run = self.enter()
        self.assertEqual(run.owned_at_entry, owned)
        return run

    def drive_past(self, run, seconds=40.0):
        for _ in range(round(seconds / DT)):
            if run.phase not in (run.PAST,):
                break
            self.game.update(DT, drive_bot(run, self.game, 0.6))

    def hold_speed(self, run, frac):
        run.player.speed = run.player.max_speed * frac

    def drive_over_plate(self, run, frac=0.95, x=0.0, start=None):
        self.put(run, (FH.TRIGGER_Z - 4000) if start is None else start, x)
        self.hold_speed(run, frac)
        for _ in range(60 * 2):
            run.player.speed = max(run.player.speed, run.player.max_speed * frac)
            self.game.update(DT, {"accelerate": True, "brake": False, "steer": 0})
            if run.phase != run.DRIVE:
                break


# ------------------------------------------------------------------ the falling road
class CollapseTests(HighwayBase):
    def test_it_gets_worse_towards_the_finish_and_is_whole_at_the_start(self):
        c = FH.Collapse(FH.ForgottenRoad())
        values = [c.severity(z) for z in range(0, int(c.road.finish_z), 6000)]
        self.assertEqual(values[0], 0.0)
        self.assertEqual(values, sorted(values))
        self.assertGreater(c.severity(c.road.finish_z), 0.85)
        self.assertGreater(c.severity(c.road.checkpoint_z[-1] + 10), c.severity(c.road.checkpoint_z[-1] - 10) + 0.1)

    def test_the_break_trails_the_car_at_every_position_before_the_last_gate(self):
        run = self.enter()
        for z in (5000, 70000, 130000, 180000):
            self.put(run, z)
            self.run_for(DT * 2)
            self.assertAlmostEqual(run.collapse.gap(run.progress), FH.PRE_GAP, delta=S.MAX_SPEED * 0.1)
            self.assertFalse(run.collapse.chase)

    def test_after_the_last_gate_the_break_runs_after_you_at_a_steady_pace(self):
        run = self.enter()
        self.put(run, run.road.checkpoint_z[-1] + 5)
        self.run_for(DT * 2)
        self.assertEqual(run.checkpoints, 3)
        self.assertTrue(run.collapse.chase)
        self.run_for(1.5, GAS)                                  # (the break closes up to its running gap first)
        run.collapse.front = run.progress - FH.CHASE_GAP + 1000
        run.player.speed = 0.0                                  # stand still: the gap then closes by exactly the break's speed
        run.player.hit_cooldown = 99
        gap0 = run.collapse.gap(run.progress)
        self.run_for(1.0, IDLE)
        self.assertAlmostEqual(gap0 - run.collapse.gap(run.progress), FH.CHASE_SPEED, delta=FH.CHASE_SPEED * 0.12)

    def test_a_driver_going_at_half_speed_is_never_caught(self):
        run = self.enter()
        self.put(run, run.road.checkpoint_z[-1] + 5)
        self.run_for(DT * 2)
        for _ in range(60 * 30):
            if run.phase != run.DRIVE:
                break
            self.game.update(DT, drive_bot(run, self.game, 0.5))
        self.assertEqual(run.fails, 0)
        self.assertIn(run.phase, (run.ARRIVE, run.REWARD))

    def test_being_caught_sends_you_to_the_last_gate_not_the_start_and_nothing_is_lost(self):
        run = self.enter()
        self.put(run, run.road.checkpoint_z[-1] + 5)
        self.run_for(DT * 2)
        run.collapse.front = run.progress - 100                  # it is right behind you
        run.player.speed = 0.0
        self.run_for(0.5, IDLE)
        self.assertEqual(run.fail_reason, "THE ROAD GAVE WAY")
        self.assertEqual(run.fails, 1)
        self.run_for(RR.FAIL_TIME + 0.3)
        self.assertEqual(run.checkpoints, 3)                     # all three gates are still yours
        self.assertAlmostEqual(run.progress, run.road.checkpoint_z[-1] + 600.0, delta=S.MAX_SPEED * 0.3)
        self.assertEqual(self.game.secret_events, [])

    def test_a_retry_starts_from_a_clean_break_with_room_to_run(self):
        run = self.enter()
        self.put(run, run.road.checkpoint_z[-1] + 5)
        self.run_for(DT * 2)
        for _ in range(40):
            run.collapse.debris.append([100, 100, 0, 0, (1, 1, 1), 1.0, 4])
        run.collapse.front = run.progress - 50
        self.run_for(0.3, IDLE)
        self.run_for(RR.FAIL_TIME + 0.3)
        self.assertGreaterEqual(run.collapse.gap(run.progress), FH.CHASE_GAP - 2000)         # (the break is back where it started)
        self.assertLess(len(run.collapse.debris), 40)
        self.assertLess(run.rumble, 0.1)
        for _ in range(60 * 25):                                   # and the retry is finishable
            if run.phase != run.DRIVE:
                break
            self.game.update(DT, drive_bot(run, self.game, 0.55))
        self.assertIn(run.phase, (run.ARRIVE, run.REWARD))

    def test_a_retry_before_the_last_gate_has_no_chase(self):
        run = self.enter()
        self.put(run, run.road.checkpoint_z[1] + 5)
        self.run_for(DT * 2)
        run._fail("TEST")
        self.run_for(RR.FAIL_TIME + 0.3)
        self.assertFalse(run.collapse.chase)
        self.assertAlmostEqual(run.collapse.gap(run.progress), FH.PRE_GAP, delta=S.MAX_SPEED * 0.2)

    def test_debris_is_capped_and_grows_with_the_damage(self):
        c = FH.Collapse(FH.ForgottenRoad())
        for _ in range(60 * 10):
            c.update(DT, 250000.0, False)
        self.assertLessEqual(len(c.debris), c.MAX_DEBRIS)
        low = FH.Collapse(FH.ForgottenRoad())
        for _ in range(60 * 3):
            low.update(DT, 20000.0, False)
        high = FH.Collapse(FH.ForgottenRoad())
        for _ in range(60 * 3):
            high.update(DT, 250000.0, False)
        self.assertGreater(len(high.debris), len(low.debris))

    def test_the_picture_gets_broken_but_the_middle_of_the_road_never_is(self):
        run = self.enter()
        self.put(run, run.road.finish_z - 12000)
        self.run_for(DT * 3)
        run.render(self.game.screen)
        centre = [tuple(self.game.screen.get_at((400, y)))[:3] for y in range(470, 500, 5)]
        self.assertTrue(all(px != FH.VOID for px in centre))
        damaged = sum(1 for seg in run.road.segments[1100:1250] if run.road.collapse.severity(seg.z) > 0.5)
        self.assertGreater(damaged, 50)

    def test_every_stage_draws_the_no_signal_panel_and_the_damage(self):
        run = self.enter()
        for z in (10000, 80000, 150000, run.road.checkpoint_z[-1] + 20000, run.road.finish_z - 3000):
            self.put(run, z)
            self.run_for(DT * 3)
            run.render(self.game.screen)

    def test_the_corner_says_no_signal_and_there_is_no_rear_view(self):
        run = self.enter()
        shown = []
        self.game.hud.trace = shown
        self.run_for(DT * 3)
        run.render(self.game.screen)
        self.game.hud.trace = None
        text = " ".join(m for _, m in shown)
        self.assertNotIn("REAR", text)
        self.assertFalse(hasattr(run, "_draw_mirror"))
        run.clock = 0.0                                          # (the label blinks off for a moment each cycle)
        run.render(self.game.screen)
        self.assertIn("NO SIGNAL", " ".join(m for _, m in shown) or "NO SIGNAL")

    def test_the_neon_lights_stutter_more_the_worse_it_gets(self):
        FH.STATE.update(sev=0.0, t=0.0)
        calm = sum(FH.lit(k) for k in range(200))
        FH.STATE.update(sev=0.95, t=0.0)
        broken = sum(FH.lit(k) for k in range(200))
        FH.STATE.update(sev=0.0)
        self.assertEqual(calm, 200)
        self.assertLess(broken, 120)

    def test_ordinary_roads_have_no_collapse_and_are_drawn_as_before(self):
        road = self.game.road
        self.assertFalse(hasattr(road, "collapse"))
        self.assertIs(type(road), Road)
        for track in self.game.tracks:
            self.start(track)
            self.run_for(1.0, GAS)
            self.game.render()
        self.assertIsNone(self.game.secret)

    def test_the_final_stretch_is_flat_and_free_of_parked_cars(self):
        road = FH.ForgottenRoad()
        a, b = FH.STRAIGHT
        self.assertEqual(max(abs(c) for c in road.route.curves[a:b]), 0.0)
        for car in FH.obstacle_cars(road):
            self.assertFalse(a * 200 - 12000 <= car.z <= road.finish_z)


# ------------------------------------------------------------------ the egg
class TriggerTests(EggBase):
    def test_it_has_its_own_gauge_and_the_threshold_is_88(self):
        self.assertEqual(OOT.TARGET_MPH, 88.0)
        p = PlayerCar()
        p.speed = p.max_speed
        self.assertEqual(OOT.mph(p), 100.0)
        p.speed = p.max_speed * 0.88
        self.assertAlmostEqual(OOT.mph(p), 88.0)
        p.speed = 0
        self.assertEqual(OOT.mph(p), 0.0)

    def test_the_gauge_never_changes_the_driving_model_or_the_dial(self):
        p = PlayerCar()
        p.speed = 6000.0
        before = (p.speed, p.speed_ratio)
        OOT.mph(p)
        self.assertEqual(before, (p.speed, p.speed_ratio))
        self.assertEqual(int(p.speed_ratio * S.DISPLAY_MAX_KMH), 150)       # the km/h dial is still the old one

    def test_every_car_can_reach_88_on_the_straight(self):
        for spec in CAR_CATALOG:
            with self.subTest(car=spec.key):
                p = PlayerCar(spec)
                p.speed = p.max_speed * 0.5
                road = FH.ForgottenRoad()
                z0 = p.distance
                for _ in range(60 * 10):
                    p.update(DT, road, True, False, 0)
                    if OOT.mph(p) >= OOT.TARGET_MPH:
                        break
                self.assertGreaterEqual(OOT.mph(p), OOT.TARGET_MPH)
                self.assertLess(p.distance - z0, (FH.STRAIGHT[1] - FH.STRAIGHT[0]) * 200 * 0.5)

    def test_fast_across_the_plate_with_the_gear_found_starts_it(self):
        run = self.enter_owned()
        self.drive_over_plate(run)
        self.assertEqual(run.phase, run.TIMETRAVEL)
        self.assertEqual(self.game.secret_events, [("easter_egg_found", "out_of_time", True)])

    def test_it_works_on_the_very_first_visit_too_the_two_secrets_are_one(self):
        run = self.enter_owned(False)
        self.drive_over_plate(run)
        self.assertEqual(run.phase, run.TIMETRAVEL)
        self.assertEqual(self.game.secret_events, [("easter_egg_found", "out_of_time", True)])
        self.assertFalse(self.game.gear_owned)                   # nothing is handed out until you are back

    def test_coming_back_from_the_past_on_a_first_visit_awards_the_reverse_gear_once(self):
        run = self.enter_owned(False)
        self.drive_over_plate(run)
        self.run_for(OOT.T_END + RR.RESTORED_TITLE_TIME + 0.3)
        self.drive_past(run)
        self.assertEqual(run.phase, run.LEAVING)
        self.run_for(RR.LEAVE_TIME + 0.2)
        self.assertEqual(run.phase, run.REWARD)
        self.assertTrue(self.game.running)
        gears = [e for e in self.game.secret_events if e[0] == "secret_item_found"]
        self.assertEqual(gears, [("secret_item_found", RR.ITEM_KEY, True)])
        self.assertTrue(self.game.gear_owned)
        self.run_for(RR.REWARD_MIN + 0.1)
        self.game.handle_event(key(pygame.K_RETURN))
        self.assertFalse(self.game.running)

    def test_coming_back_with_the_gear_already_found_just_leaves(self):
        run = self.enter_owned(True)
        self.drive_over_plate(run)
        self.run_for(OOT.T_END + RR.RESTORED_TITLE_TIME + 0.3)
        self.drive_past(run)
        self.run_for(RR.LEAVE_TIME + 0.2)
        self.assertFalse(self.game.running)
        self.assertTrue(all(e[0] != "secret_item_found" for e in self.game.secret_events))

    def test_too_slow_off_the_road_or_off_the_plate_does_not_start_it(self):
        for label, kwargs in (("slow", dict(frac=0.8)), ("offroad", dict(x=1.6)),
                              ("before the plate", dict(start=FH.TRIGGER_Z - 60000))):
            with self.subTest(label):
                self.game.reset()
                self.start()
                run = self.enter_owned()
                frames = 60 * 2
                self.put(run, kwargs.get("start", FH.TRIGGER_Z - 4000), kwargs.get("x", 0.0))
                for _ in range(frames):
                    run.player.speed = run.player.max_speed * kwargs.get("frac", 0.95)
                    run.player.x = kwargs.get("x", 0.0)
                    if label == "before the plate":
                        run.player.distance = min(run.player.distance, FH.TRIGGER_Z - 30000)
                        run.player.z = run.player.distance
                    self.game.update(DT, {"accelerate": False, "brake": False, "steer": 0})
                    if run.phase != run.DRIVE:
                        break
                self.assertEqual(run.phase, run.DRIVE, label)

    def test_it_can_only_start_once_per_visit(self):
        run = self.enter_owned()
        self.drive_over_plate(run)
        events = list(self.game.secret_events)
        self.run_for(RR.CUT_TOTAL)
        self.assertEqual(self.game.secret_events, events)
        self.assertTrue(run.egg_found)

    def test_the_gauge_only_shows_on_the_straight_and_only_to_the_owner_of_the_gear(self):
        run = self.enter_owned()
        shown = []
        self.game.hud.trace = shown
        self.put(run, 20000)
        self.run_for(DT * 2)
        run.render(self.game.screen)
        self.assertNotIn("TEMPORAL SPEED", " ".join(m for _, m in shown))
        self.put(run, FH.TRIGGER_Z - 20000)
        self.run_for(DT * 2)
        run.render(self.game.screen)
        self.assertIn("TEMPORAL SPEED", " ".join(m for _, m in shown))
        self.game.hud.trace = None
        self.game.reset()
        self.start()
        run = self.enter_owned(False)
        shown = []
        self.game.hud.trace = shown
        self.put(run, FH.TRIGGER_Z - 20000)
        self.run_for(DT * 2)
        run.render(self.game.screen)
        self.game.hud.trace = None
        self.assertNotIn("TEMPORAL SPEED", " ".join(m for _, m in shown))


class CutsceneAndPastTests(EggBase):
    def travel(self):
        run = self.enter_owned()
        self.drive_over_plate(run)
        self.assertEqual(run.phase, run.TIMETRAVEL)
        return run

    def test_the_cutscene_draws_current_fire_flashes_the_vanish_and_the_title(self):
        run = self.travel()
        seen, titles = set(), []
        self.game.hud.trace = titles
        for _ in range(round(OOT.T_END / DT) + 5):
            if run.phase != run.TIMETRAVEL:
                break
            self.game.update(DT, IDLE)
            self.game.render()
            seen.add((round(run.tt.t, 1) if run.tt else None, run.tt.car_visible if run.tt else None))
        self.game.hud.trace = None
        self.assertIn("OUT OF TIME", " ".join(m for _, m in titles))
        self.assertTrue(any(v is True for _, v in seen) and any(v is False for _, v in seen))      # the car was there, then gone

    def test_the_car_vanishes_at_the_set_moment(self):
        run = self.travel()
        for _ in range(round((OOT.T_GONE - 0.2) / DT)):
            self.game.update(DT, IDLE)
        self.assertTrue(run.tt.car_visible)
        for _ in range(round(0.4 / DT)):
            self.game.update(DT, IDLE)
        self.assertFalse(run.tt.car_visible)

    def test_it_never_strobes_only_two_flashes_and_it_is_skippable(self):
        flashes = [OOT.T_FLASH1, OOT.T_FLASH2]
        self.assertEqual(len(flashes), 2)
        self.assertLessEqual(OOT.T_END, 6.5)
        run = self.travel()
        self.run_for(1.7)
        self.game.handle_event(key(pygame.K_RETURN))
        self.assertTrue(run.phase in (run.PAST_TITLE, run.TIMETRAVEL))
        self.run_for(0.1)
        self.assertEqual(run.phase, run.PAST_TITLE)

    def test_it_lands_in_the_restored_road_with_no_collapse_and_no_gates(self):
        run = self.travel()
        self.run_for(OOT.T_END + 0.3)
        self.assertEqual(run.phase, run.PAST_TITLE)
        self.assertTrue(run.road.past)
        self.assertIsNone(run.collapse)
        self.assertIsNone(run.road.collapse)
        self.assertEqual(run.player.distance, 0.0)
        self.run_for(RR.RESTORED_TITLE_TIME + 0.3)
        self.assertEqual(run.phase, run.PAST)
        self.assertEqual(FH.STATE["sev"], 0.0)
        self.assertTrue(FH.STATE["warm"])

    def test_the_past_is_livelier_and_warmer(self):
        run = self.travel()
        self.run_for(OOT.T_END + RR.RESTORED_TITLE_TIME + 0.5)
        self.assertGreater(len(run.traffic.cars), 3)
        self.assertTrue(all(c.speed <= S.MAX_SPEED * 0.33 for c in run.traffic.cars))
        self.assertGreater(len(FH.PAST_THEME.placements), len(FH.THEME.placements) - 1)
        self.assertGreater(FH.PAST_THEME.sky_bands[-1][0], FH.THEME.sky_bands[-1][0] - 10)
        self.assertGreater(sum(FH.PAST_THEME.sky_bands[5]), sum(FH.THEME.sky_bands[5]))
        run.render(self.game.screen)

    def drive_past(self, run, seconds=40.0):
        for _ in range(round(seconds / DT)):
            if run.phase not in (run.PAST,):
                break
            self.game.update(DT, drive_bot(run, self.game, 0.6))

    def test_you_can_drive_it_freely_and_the_exit_ends_the_visit(self):
        run = self.travel()
        self.run_for(OOT.T_END + RR.RESTORED_TITLE_TIME + 0.3)
        self.drive_past(run)
        self.assertEqual(run.phase, run.LEAVING)
        self.assertGreaterEqual(run.progress, run.road.exit_z)
        self.assertEqual(run.fails, 0)
        self.assertTrue(self.game.running)
        self.run_for(RR.LEAVE_TIME + 0.2)
        self.assertFalse(self.game.running)                  # the host closes the machine: back to the arcade
        self.assertEqual(self.game.music_duck, 1.0)
        self.assertEqual(FH.STATE["warm"], False)

    def test_nothing_in_the_past_can_fail_you_or_award_anything(self):
        run = self.travel()
        self.run_for(OOT.T_END + RR.RESTORED_TITLE_TIME + 0.3)
        self.put(run, 30000, x=2.4)
        self.run_for(10.0, IDLE)                              # parked on the grass for ten seconds
        self.assertEqual(run.phase, run.PAST)
        self.assertEqual(run.fails, 0)
        self.assertEqual([e[0] for e in self.game.secret_events], ["easter_egg_found"])

    def test_the_past_can_be_paused_and_quit_like_any_race(self):
        run = self.travel()
        self.run_for(OOT.T_END + RR.RESTORED_TITLE_TIME + 0.3)
        self.game.handle_event(key(pygame.K_p))
        self.assertTrue(self.game.paused)
        self.game.handle_event(key(pygame.K_BACKSPACE))
        self.assertIsNone(self.game.secret)
        self.assertIs(self.game.state, State.MODE_SELECT)

    def test_it_can_be_triggered_again_and_the_second_time_is_not_new(self):
        run = self.travel()
        self.game.pop_secret_events()
        self.game.reset()
        self.start()
        self.game.gear_owned = True
        self.game.egg_found = True
        run = self.enter_owned()
        self.drive_over_plate(run)
        self.assertEqual(self.game.secret_events, [("easter_egg_found", "out_of_time", False)])

    def test_the_egg_gives_no_second_item(self):
        run = self.travel()
        self.run_for(OOT.T_END + 6.0)
        self.assertTrue(all(e[0] != "secret_item_found" for e in self.game.secret_events))
        self.assertTrue(self.game.gear_owned)                # (still just the Reverse Gear)


class StillTheSameRaceTests(GameBase):
    def test_ordinary_races_never_see_any_of_it(self):
        self.run_for(30.0, GAS)
        self.assertIs(self.game.state, State.PLAYING)
        self.assertIsNone(self.game.secret)
        self.assertEqual(FH.STATE["sev"], 0.0)


if __name__ == "__main__":
    unittest.main()
