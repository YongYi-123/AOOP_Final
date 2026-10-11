"""Starfall Assault rules: movement, firing, collisions, formations, waves, bosses, health, power-ups."""
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from galaxy_defender import config as cfg
from galaxy_defender.model import Bolt, Enemy, Run, overlap
from galaxy_defender.settlement import RunResult, tickets_for

DT = 1 / 60


def started(wave=1, seed=1):
    """A run whose wave `wave` has just spawned."""
    run = Run(random.Random(seed))
    run.wave = wave
    run.banner = 0.001
    run.update(0.01)
    return run


def advance(run, seconds, move=0, fire=False):
    for _ in range(int(seconds / DT)):
        run.update(DT, move, fire)


def calm(run):
    """Stop the enemies from shooting so a test about something else is not disturbed."""
    run._fire_timer = 1e9
    if run.boss:
        run.boss.fire_timer = 1e9


class MovementTests(unittest.TestCase):
    def test_ship_moves_both_ways_and_stays_inside_the_screen(self):
        run = started()
        calm(run)
        start = run.x
        advance(run, 0.2, move=1)
        self.assertGreater(run.x, start)
        advance(run, 0.4, move=-1)
        self.assertLess(run.x, start)
        advance(run, 5, move=1)
        self.assertEqual(run.x, cfg.FIELD_W - cfg.PLAYER["width"] / 2)
        advance(run, 5, move=-1)
        self.assertEqual(run.x, cfg.PLAYER["width"] / 2)

    def test_movement_input_is_clamped(self):
        run = started()
        before = run.x
        run.update(DT, move=50)
        self.assertAlmostEqual(run.x - before, cfg.PLAYER["speed"] * DT)


class ShootingTests(unittest.TestCase):
    def test_cooldown_limits_fire_rate(self):
        run = started()
        calm(run)
        self.assertTrue(run.shoot())
        self.assertFalse(run.shoot())
        advance(run, cfg.PLAYER["cooldown"] + 0.02)
        self.assertTrue(run.shoot())

    def test_holding_fire_repeats_at_the_cooldown(self):
        run = started()
        calm(run)
        run.player_bolts.clear()
        shots = []
        for _ in range(int(1.0 / DT)):
            run.update(DT, 0, True)
            shots += [e for e in run.take_events() if e.name == "shoot"]
        self.assertAlmostEqual(len(shots), 1.0 / cfg.PLAYER["cooldown"], delta=1.1)

    def test_rapid_fire_fires_faster(self):
        run = started()
        run.collect("rapid")
        self.assertEqual(run.firing_gap, cfg.PLAYER["rapid_cooldown"])
        self.assertLess(cfg.PLAYER["rapid_cooldown"], cfg.PLAYER["cooldown"])

    def test_bolts_in_flight_are_capped(self):
        run = started()
        calm(run)
        for _ in range(40):
            run.cooldown = 0
            run.shoot()
        self.assertLessEqual(len(run.player_bolts), cfg.PLAYER["max_bullets"])


class CollisionTests(unittest.TestCase):
    def test_overlap_helper(self):
        self.assertTrue(overlap((10, 10, 4, 4), (12, 10, 4, 4)))
        self.assertFalse(overlap((10, 10, 4, 4), (20, 10, 4, 4)))

    def test_player_bolt_destroys_scout_and_scores(self):
        run = started()
        calm(run)
        target = run.enemies[0]
        run.player_bolts.append(Bolt(target.x, target.y, 0, 0))
        before = len(run.enemies)
        run.update(DT)
        self.assertEqual(len(run.enemies), before - 1)
        self.assertEqual(run.score, cfg.ENEMIES["scout"]["score"])
        self.assertEqual(run.player_bolts, [])

    def test_tank_needs_several_hits(self):
        run = started(wave=cfg.TANK_FROM_WAVE)
        calm(run)
        tank = next(e for e in run.enemies if e.kind == "tank")
        for hits in range(1, cfg.ENEMIES["tank"]["hp"]):
            run.player_bolts.append(Bolt(tank.x, tank.y, 0, 0))
            run.update(DT)
            self.assertIn(tank, run.enemies)
            self.assertEqual(tank.hp, cfg.ENEMIES["tank"]["hp"] - hits)
        run.player_bolts.append(Bolt(tank.x, tank.y, 0, 0))
        run.update(DT)
        self.assertNotIn(tank, run.enemies)
        self.assertEqual(run.score, cfg.ENEMIES["tank"]["score"])

    def test_enemy_bolt_hurts_the_player(self):
        run = started()
        calm(run)
        run.enemy_bolts.append(Bolt(run.x, cfg.PLAYER_Y, 0, 0, hostile=True))
        run.update(DT)
        self.assertEqual(run.hp, cfg.MAX_HP - 1)
        self.assertEqual(run.enemy_bolts, [])

    def test_missing_bolt_does_not_hurt(self):
        run = started()
        calm(run)
        run.enemy_bolts.append(Bolt(run.x + 80, cfg.PLAYER_Y, 0, 0, hostile=True))
        run.update(DT)
        self.assertEqual(run.hp, cfg.MAX_HP)

    def test_bolts_that_leave_the_screen_are_removed(self):
        run = started()
        calm(run)
        run.player_bolts.append(Bolt(5, 3, 0, -300))
        run.enemy_bolts.append(Bolt(5, cfg.FIELD_H + 5, 0, 300, hostile=True))
        advance(run, 0.2)
        self.assertEqual((run.player_bolts, run.enemy_bolts), ([], []))


class FormationTests(unittest.TestCase):
    def test_wave_one_is_an_organised_grid(self):
        run = started()
        d = cfg.difficulty_for(1)
        self.assertEqual(len(run.enemies), d.columns * d.rows)
        xs = sorted({round(e.x) for e in run.enemies})
        ys = sorted({round(e.y) for e in run.enemies})
        self.assertEqual(len(xs), d.columns)
        self.assertEqual(len(ys), d.rows)
        self.assertEqual({b - a for a, b in zip(xs, xs[1:])}, {cfg.FORMATION["spacing_x"]})

    def test_formation_moves_sideways_as_a_group(self):
        run = started()
        calm(run)
        before = [(e.x, e.y) for e in run.enemies]
        advance(run, 0.3)
        after = [(e.x, e.y) for e in run.enemies]
        shifts = {round(a[0] - b[0], 3) for a, b in zip(after, before)}
        self.assertEqual(len(shifts), 1)
        self.assertGreater(shifts.pop(), 0)

    def test_formation_reverses_and_descends_at_the_edges(self):
        run = started()
        calm(run)
        top = min(e.y for e in run.enemies)
        turns, directions = 0, [run._formation["dir"]]
        for _ in range(int(14 / DT)):
            calm(run)
            run.update(DT)
            if run._formation["dir"] != directions[-1]:
                directions.append(run._formation["dir"])
            if run.over:
                break
            right = max(e.x for e in run.enemies) + 8
            left = min(e.x for e in run.enemies) - 8
            self.assertLessEqual(right, cfg.FIELD_W)
            self.assertGreaterEqual(left, 0)
        self.assertGreaterEqual(len(directions), 3)            # right, left, right again
        self.assertGreater(min(e.y for e in run.enemies), top)
        steps = round((min(e.y for e in run.enemies) - top) / run.diff.step_down)
        self.assertEqual(steps, len(directions) - 1)

    def test_formation_speeds_up_as_it_thins(self):
        run = started()
        calm(run)
        full = run.diff.speed
        x0 = run.enemies[0].x
        run.update(DT)
        step_full = abs(run.enemies[0].x - x0)
        for e in run.enemies[: len(run.enemies) // 2]:
            run.enemies.remove(e)
        calm(run)
        x1 = run.enemies[0].x
        run.update(DT)
        self.assertGreater(abs(run.enemies[0].x - x1), step_full * 1.01)
        self.assertGreater(full, 0)

    def test_enemies_shoot_from_the_front_of_a_column_towards_the_player(self):
        run = started()
        run._fire_timer = 0
        run.x = 40
        run.update(DT)
        self.assertEqual(len(run.enemy_bolts), 1)
        bolt = run.enemy_bolts[0]
        front = max(e.row for e in run.enemies if abs(e.x - bolt.x) < 1)
        self.assertEqual(front, max(e.row for e in run.enemies))
        self.assertLessEqual(abs(bolt.vx), cfg.FORMATION["aim_limit"])
        self.assertGreater(bolt.vy, 0)

    def test_new_enemy_types_unlock_with_the_wave(self):
        kinds = lambda w: {e.kind for e in started(w).enemies}
        self.assertEqual(kinds(1), {"scout"})
        self.assertIn("dash", kinds(cfg.DASH_FROM_WAVE))
        self.assertIn("tank", kinds(cfg.TANK_FROM_WAVE))
        self.assertTrue({"scout", "dash", "tank"} <= kinds(9))


class WaveTests(unittest.TestCase):
    def test_clearing_a_wave_awards_a_bonus_and_starts_the_next_after_a_pause(self):
        run = started()
        calm(run)
        run.enemies.clear()
        run.update(DT)
        self.assertEqual(run.waves_cleared, 1)
        self.assertEqual(run.wave, 2)
        self.assertEqual(run.score, cfg.SCORES["wave_clear_per_wave"])
        self.assertTrue(run.banner_active)
        self.assertEqual(run.enemies, [])
        advance(run, cfg.WAVE_BANNER_SECONDS + 0.1)
        self.assertGreater(len(run.enemies), 0)
        self.assertEqual(run.reached, 2)

    def test_the_run_goes_on_far_past_the_first_waves(self):
        run = Run(random.Random(5))
        run.hp = 10 ** 6                        # immortal: this is about the waves, not the player
        for expected in range(1, 61):
            run.banner = 0.001
            run.update(0.01)
            self.assertEqual(run.wave, expected)
            self.assertTrue(run.enemies or run.boss)
            run.enemies.clear()
            run.boss = None
            run.update(DT)
        self.assertEqual(run.waves_cleared, 60)
        self.assertFalse(run.over)

    def test_difficulty_grows_then_stops_at_its_caps(self):
        d1, d5, d40, d400 = (cfg.difficulty_for(w) for w in (1, 5, 40, 400))
        self.assertGreater(d5.speed, d1.speed)
        self.assertLess(d5.fire_gap, d1.fire_gap)
        self.assertGreaterEqual(d5.bolt_speed, d1.bolt_speed)
        self.assertEqual(d40, d400)
        self.assertLessEqual(d400.speed, cfg.DIFFICULTY["speed"][2])
        self.assertGreaterEqual(d400.fire_gap, cfg.DIFFICULTY["fire_gap"][2])
        self.assertLessEqual(d400.columns * cfg.FORMATION["spacing_x"], cfg.FIELD_W - 2 * cfg.FORMATION["margin"])
        self.assertEqual(cfg.difficulty_for(0), d1)

    def test_enemy_bolts_are_capped_on_screen(self):
        run = started(30)
        for _ in range(60):
            run._fire_timer = 0
            run.update(0.0001)
        self.assertLessEqual(len(run.enemy_bolts), run.diff.max_bolts)

    def test_wave_clear_removes_leftover_enemy_bolts(self):
        run = started()
        calm(run)
        run.enemy_bolts.append(Bolt(5, 100, 0, 50, hostile=True))
        run.enemies.clear()
        run.update(DT)
        self.assertEqual(run.enemy_bolts, [])


class BossTests(unittest.TestCase):
    def test_a_boss_every_fifth_wave_and_only_then(self):
        for wave in range(1, 31):
            run = started(wave)
            if wave % 5 == 0:
                self.assertIsNotNone(run.boss, wave)
                self.assertEqual(run.enemies, [])
            else:
                self.assertIsNone(run.boss, wave)
                self.assertTrue(run.enemies)

    def test_boss_scales_but_stays_beatable(self):
        hps = [started(w).boss.hp for w in (5, 10, 15, 20, 500)]
        self.assertEqual(hps, sorted(hps))
        self.assertEqual(hps[-1], cfg.BOSS["max_hp"])
        self.assertLessEqual(started(500).boss.speed, cfg.BOSS["max_speed"])

    def test_boss_uses_two_different_attacks(self):
        run = started(5)
        run.hp = 10 ** 6
        seen = {}
        for _ in range(int(14 / DT)):
            run.boss.pattern_time = run.boss.pattern_time
            before = len(run.enemy_bolts)
            pattern = run.boss.pattern
            run.update(DT)
            seen.setdefault(pattern, 0)
            seen[pattern] += max(0, len(run.enemy_bolts) - before)
            run.enemy_bolts = [b for b in run.enemy_bolts if b.y < 200]
        self.assertGreater(seen["spread"], 0)
        self.assertGreater(seen["aimed"], 0)
        self.assertEqual(set(seen), {"spread", "aimed"})

    def test_defeating_the_boss_scores_drops_a_power_up_and_continues_to_the_next_wave(self):
        run = started(5)
        calm(run)
        run.hp = 2
        run.boss.hp = 1
        run.player_bolts.append(Bolt(run.boss.x, run.boss.y, 0, 0))
        run.update(DT)
        self.assertIsNone(run.boss)
        self.assertEqual(run.score, cfg.BOSS["score"] + cfg.SCORES["wave_clear_per_wave"] * 5)
        self.assertEqual(len(run.powerups), 1)
        self.assertEqual((run.wave, run.waves_cleared), (6, 1))
        advance(run, cfg.WAVE_BANNER_SECONDS + 0.1)
        self.assertTrue(run.enemies)

    def test_boss_hp_can_be_depleted_by_real_fire(self):
        run = started(5)
        run.hp = 10 ** 6
        run.boss.x = run.x = 200
        run.boss.speed = 0
        calm(run)
        for _ in range(int(60 / DT)):
            calm(run)
            run.update(DT, 0, True)
            if run.boss is None:
                break
        self.assertIsNone(run.boss)


class HealthTests(unittest.TestCase):
    def test_hit_costs_hp_and_grants_invulnerability(self):
        run = started()
        self.assertEqual(run.hp, 3)
        self.assertEqual(run.damage(), "hp")
        self.assertEqual(run.hp, 2)
        self.assertGreater(run.invuln, 0)
        self.assertEqual(run.damage(), "ignored")
        self.assertEqual(run.hp, 2)

    def test_invulnerability_expires(self):
        run = started()
        calm(run)
        run.damage()
        advance(run, cfg.PLAYER["invulnerable"] + 0.05)
        self.assertEqual(run.invuln, 0)
        self.assertEqual(run.damage(), "hp")
        self.assertEqual(run.hp, 1)

    def test_bolts_pass_through_an_invulnerable_ship(self):
        run = started()
        calm(run)
        run.damage()
        run.enemy_bolts.append(Bolt(run.x, cfg.PLAYER_Y, 0, 0, hostile=True))
        run.update(DT)
        self.assertEqual(run.hp, 2)

    def test_shield_blocks_exactly_one_hit(self):
        run = started()
        run.collect("shield")
        self.assertEqual(run.damage(), "shield")
        self.assertEqual((run.hp, run.shield), (3, False))
        run.invuln = 0
        self.assertEqual(run.damage(), "hp")
        self.assertEqual(run.hp, 2)

    def test_repair_heals_but_never_above_the_maximum(self):
        run = started()
        run.collect("repair")
        self.assertEqual(run.hp, cfg.MAX_HP)
        run.hp = 1
        run.collect("repair")
        run.collect("repair")
        run.collect("repair")
        self.assertEqual(run.hp, cfg.MAX_HP)

    def test_zero_hp_is_game_over(self):
        run = started()
        for _ in range(3):
            run.invuln = 0
            run.damage()
        self.assertTrue(run.over)
        self.assertEqual((run.hp, run.over_reason), (0, "hp"))

    def test_breaching_the_defense_line_is_game_over(self):
        run = started()
        calm(run)
        run._formation["y"] = cfg.DEFENSE_LINE - 5
        run.update(DT)
        self.assertTrue(run.over)
        self.assertEqual(run.over_reason, "breach")

    def test_a_finished_run_ignores_everything(self):
        run = started()
        run.invuln = 0
        run.hp = 1
        run.damage()
        score, x = run.score, run.x
        run.update(1, move=1, fire=True)
        self.assertFalse(run.shoot())
        self.assertEqual((run.score, run.x), (score, x))

    def test_formation_can_always_be_stopped_before_breaching(self):
        """Even the deepest formation has room above the defense line for several descents."""
        for wave in (1, 8, 19, 99):
            d = cfg.difficulty_for(wave)
            bottom = cfg.FORMATION["top"] + (d.rows - 1) * cfg.FORMATION["spacing_y"] + 7
            self.assertGreater((cfg.DEFENSE_LINE - bottom) / d.step_down, 8)


class PowerUpTests(unittest.TestCase):
    def test_timed_powers_expire_on_schedule(self):
        for kind, seconds in cfg.POWER_SECONDS.items():
            run = started()
            calm(run)
            run.collect(kind)
            self.assertEqual(run.power[kind], seconds)
            advance(run, seconds - 0.5)
            self.assertGreater(run.power[kind], 0)
            advance(run, 0.6)
            self.assertEqual(run.power[kind], 0, kind)

    def test_rapid_fire_gap_returns_to_normal_after_expiry(self):
        run = started()
        calm(run)
        run.collect("rapid")
        self.assertEqual(run.firing_gap, cfg.PLAYER["rapid_cooldown"])
        advance(run, cfg.POWER_SECONDS["rapid"] + 0.1)
        self.assertEqual(run.firing_gap, cfg.PLAYER["cooldown"])

    def test_powers_refresh_instead_of_stacking_and_combine_with_each_other(self):
        run = started()
        run.collect("rapid")
        run.power["rapid"] = 3
        run.collect("rapid")
        self.assertEqual(run.power["rapid"], cfg.POWER_SECONDS["rapid"])
        run.collect("spread")
        run.collect("pierce")
        self.assertTrue(all(left > 0 for left in run.power.values()))

    def test_spread_fires_three_diverging_bolts_and_expires(self):
        run = started()
        calm(run)
        run.collect("spread")
        run.shoot()
        self.assertEqual(len(run.player_bolts), 3)
        self.assertEqual(sorted(round(b.vx) for b in run.player_bolts)[1], 0)
        self.assertLess(min(b.vx for b in run.player_bolts), 0)
        self.assertGreater(max(b.vx for b in run.player_bolts), 0)
        self.assertTrue(all(b.vy < 0 for b in run.player_bolts))
        advance(run, cfg.POWER_SECONDS["spread"] + 0.1)
        run.player_bolts.clear()
        run.cooldown = 0
        run.shoot()
        self.assertEqual(len(run.player_bolts), 1)

    def test_pierce_goes_through_every_target_in_line_but_hits_each_once(self):
        run = started()
        calm(run)
        run.enemies.clear()
        run._move_enemies = lambda dt: None            # hold the hand-placed targets still
        run.enemies += [Enemy("tank", 0, 0, 3, 3, 200, 120), Enemy("scout", 0, 1, 1, 1, 200, 90)]
        bolt = Bolt(200, 150, 0, -100, w=3, h=10, pierce=True)
        run.player_bolts.append(bolt)
        advance(run, 1.2)
        self.assertEqual([e.kind for e in run.enemies], ["tank"])          # the scout died, the tank was hit once
        self.assertEqual(run.enemies[0].hp, 2)
        self.assertEqual(run.score, cfg.ENEMIES["scout"]["score"])

    def test_normal_bolt_stops_at_the_first_target(self):
        run = started()
        calm(run)
        run.enemies.clear()
        run._move_enemies = lambda dt: None
        run.enemies += [Enemy("scout", 0, 0, 1, 1, 200, 120), Enemy("scout", 0, 1, 1, 1, 200, 90)]
        run.player_bolts.append(Bolt(200, 150, 0, -100, w=3, h=10))
        advance(run, 1.2)
        self.assertEqual(len(run.enemies), 1)

    def test_pierce_hits_the_boss_once_per_bolt(self):
        run = started(5)
        calm(run)
        run.boss.x = run.x = 200
        run.boss.speed = 0
        start = run.boss.hp
        run.player_bolts.append(Bolt(200, run.boss.y + 30, 0, -60, w=3, h=10, pierce=True))
        advance(run, 1.5)
        self.assertEqual(run.boss.hp, start - 1)

    def test_falling_power_up_is_collected_on_contact(self):
        run = started()
        calm(run)
        run.hp = 1
        run.powerups.append(__import__("galaxy_defender.model", fromlist=["PowerUp"]).PowerUp("repair", run.x, cfg.PLAYER_Y - 4))
        run.update(DT)
        self.assertEqual((run.hp, run.powerups), (2, []))

    def test_missed_power_up_falls_away(self):
        from galaxy_defender.model import PowerUp
        run = started()
        calm(run)
        run.x = 30
        run.powerups.append(PowerUp("rapid", 350, 100))
        advance(run, 6)
        self.assertEqual(run.powerups, [])

    def test_drops_are_uncommon_and_spaced(self):
        run = started()
        calm(run)
        drops = 0
        for _ in range(400):
            run.enemies.append(Enemy("scout", 0, 0, 1, 1, 100, 100))
            before = len(run.powerups)
            run._enemy_down(run.enemies[-1])
            drops += len(run.powerups) - before
            run.time += 1.0
        self.assertLess(drops, 400 * cfg.POWERUP["drop_chance"] * 2)
        self.assertGreater(drops, 0)

    def test_useless_drops_are_not_offered(self):
        run = started()
        run.shield = True
        for _ in range(60):
            run._drop(10, 10)
        self.assertTrue(all(p.kind != "shield" for p in run.powerups))
        self.assertTrue(all(p.kind != "repair" for p in run.powerups))     # at full HP


class ComboAndCargoTests(unittest.TestCase):
    def kill(self, run, n=1, kind="scout"):
        for _ in range(n):
            e = Enemy(kind, 0, 0, 1, 1, 100, 100)
            run.enemies.append(e)
            run._enemy_down(e)

    def test_chained_kills_raise_the_multiplier_in_steps_up_to_a_cap(self):
        run = started()
        calm(run)
        run.enemies.clear()
        self.assertEqual(run.multiplier, 1.0)
        self.kill(run, cfg.COMBO["step"])
        self.assertEqual(run.multiplier, 1.0 + cfg.COMBO["bonus"])
        self.kill(run, 100)
        self.assertEqual(run.multiplier, cfg.COMBO["max_mult"])
        self.assertEqual(run.best_combo, 100 + cfg.COMBO["step"])

    def test_first_kills_score_face_value_and_later_ones_more(self):
        run = started()
        run.enemies.clear()
        self.kill(run, 2)
        self.assertEqual(run.score, 20)
        self.kill(run)                       # the chain reaches 3: x1.25 applies from this kill on
        self.assertEqual(run.score, 20 + 13)
        self.kill(run)
        self.assertEqual(run.score, 20 + 13 + 13)

    def test_combo_expires_without_a_kill(self):
        run = started()
        calm(run)
        self.kill(run, 5)
        self.assertGreater(run.combo, 0)
        advance(run, cfg.COMBO["window"] + 0.1)
        self.assertEqual((run.combo, run.multiplier), (0, 1.0))

    def test_taking_damage_breaks_the_combo(self):
        run = started()
        self.kill(run, 6)
        run.damage()
        self.assertEqual(run.combo, 0)

    def test_combo_milestones_are_announced(self):
        run = started()
        run.take_events()
        self.kill(run, cfg.COMBO["announce_every"])
        self.assertIn("combo", [e.name for e in run.take_events()])

    def test_cargo_drones_appear_from_wave_two_and_always_drop_a_core(self):
        self.assertFalse(any(e.carrier for e in started(1).enemies))
        for wave in (2, 3, 7, 9):
            run = started(wave)
            carriers = [e for e in run.enemies if e.carrier]
            self.assertGreaterEqual(len(carriers), 1, wave)
            self.assertLessEqual(len(carriers), cfg.CARGO_MAX)
        run = started(2)
        calm(run)
        run.hp = 1
        carrier = next(e for e in run.enemies if e.carrier)
        run._last_drop = run.time                      # even straight after another drop
        run._enemy_down(carrier)
        self.assertEqual(len(run.powerups), 1)

    def test_drop_mix_contains_every_power_up(self):
        run = started()
        run.hp = 1
        for _ in range(400):
            run.shield = False
            run._drop(10, 10)
        self.assertEqual({p.kind for p in run.powerups}, set(cfg.POWERUPS))


class TicketTests(unittest.TestCase):
    def test_tickets_are_never_negative_and_zero_without_score(self):
        self.assertEqual(tickets_for(0, 9), 0)
        self.assertEqual(tickets_for(-50, -3), 0)

    def test_tickets_grow_with_play_and_are_capped(self):
        self.assertLess(tickets_for(300, 0), tickets_for(1500, 3))
        self.assertEqual(tickets_for(10 ** 7, 500), cfg.TICKETS["cap"])
        self.assertLessEqual(tickets_for(2000, 4), 20)       # a decent run pays about what a volleyball win does

    def test_run_result_ranking(self):
        low, high = RunResult.of(100, 1, 0), RunResult.of(3000, 6, 5)
        self.assertTrue(high.better_than(low))
        self.assertFalse(low.better_than(high))
        self.assertFalse(low.better_than(low))


if __name__ == "__main__":
    unittest.main()


class FairnessTests(unittest.TestCase):
    def test_a_simple_pilot_survives_the_first_waves_including_the_first_boss(self):
        from galaxy_defender.tests.autopilot import move_for
        for seed in (0, 1, 2):
            run = Run(random.Random(seed))
            for _ in range(int(240 / DT)):
                run.update(DT, move_for(run), True)
                if run.wave > 6 or run.over:
                    break
            self.assertFalse(run.over, f"seed {seed} died on wave {run.wave} ({run.over_reason})")
            self.assertGreater(run.wave, 5, f"seed {seed} never got past the boss")
            self.assertEqual(run.waves_cleared, run.wave - 1)
