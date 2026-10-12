"""NEON COIN PUSHER: the physics (coin_pusher.py) and the money + saved board
(coin_pusher_table.py), without any screen. Run from this folder:
    python -m unittest test_coin_pusher
"""
import math
import os
import random
import unittest
from datetime import date, timedelta

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import coin_pusher as cp  # noqa: E402
from coin_pusher_table import DROP_COOLDOWN, CoinPusherTable  # noqa: E402
from game_clock import GameClock  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from settings import (COIN_PUSHER_DAILY_TICKET_CAP, COIN_PUSHER_GOLDEN_TICKETS,  # noqa: E402
                      COIN_PUSHER_SILVER_TOKENS)

DT = 1 / 60


def run(world, seconds, dt=DT, on_step=None):
    """Advance `world`; returns every event."""
    events = []
    for _ in range(int(round(seconds / dt))):
        events += world.advance(dt)
        if on_step:
            on_step(world)
    return events


def overlaps(world):
    worst = 0.0
    cs = world.coins
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            worst = max(worst, 2 * cp.R - math.hypot(a.x - b.x, a.y - b.y))
    return worst


def far_beyond_front(world, kind=cp.NORMAL, prize=None, x=65.0):
    """A settled coin one nudge from falling over the front edge."""
    coin = world.place(x, cp.D - 2, kind, prize)
    coin.y = cp.D - 0.5
    return coin


class PusherMotionTests(unittest.TestCase):
    def test_pusher_starts_back_reaches_the_front_and_repeats(self):
        self.assertAlmostEqual(cp.pusher_face(0), cp.FACE_MIN)
        self.assertAlmostEqual(cp.pusher_face(cp.PUSH_PERIOD / 2), cp.FACE_MAX)
        self.assertAlmostEqual(cp.pusher_face(cp.PUSH_PERIOD), cp.FACE_MIN)
        self.assertAlmostEqual(cp.pusher_face(3.3), cp.pusher_face(3.3 + 5 * cp.PUSH_PERIOD))

    def test_pusher_never_leaves_its_stroke_and_never_jumps(self):
        previous = cp.pusher_face(0)
        for i in range(1, 2000):
            face = cp.pusher_face(i * cp.STEP)
            self.assertTrue(cp.FACE_MIN - 1e-9 <= face <= cp.FACE_MAX + 1e-9)
            self.assertLess(abs(face - previous), 0.4)           # far below a coin radius (5.5): nothing can tunnel
            previous = face

    def test_pusher_speed_matches_its_position(self):
        h = 1e-5
        for t in (0.3, 1.1, 2.9):
            numeric = (cp.pusher_face(t + h) - cp.pusher_face(t - h)) / (2 * h)
            self.assertAlmostEqual(cp.pusher_speed(t), numeric, places=3)

    def test_the_pusher_advances_and_displaces_a_coin_in_front_of_it(self):
        w = cp.PusherWorld()
        coin = w.place(65, cp.FACE_MIN + cp.R + 4)
        start = coin.y
        run(w, cp.PUSH_PERIOD / 2)
        self.assertGreater(coin.y, start + 15)                    # shoved a long way forward
        self.assertGreaterEqual(coin.y, w.face + cp.R - 1e-6)

    def test_the_pusher_cannot_be_passed_by_a_coin(self):
        w = cp.PusherWorld()
        coin = w.place(65, 60)
        coin.vy = -40                                             # flung straight back at the pusher
        worst = [0.0]

        def check(world):
            worst[0] = min([worst[0]] + [c.y - cp.R - world.face for c in world.coins])
        run(w, 8, on_step=check)
        self.assertGreaterEqual(worst[0], -1e-6)


class DropTests(unittest.TestCase):
    def test_a_drop_lands_where_the_chute_was_after_the_fall_time(self):
        w = cp.PusherWorld()
        w.add_drop(40.0)
        self.assertEqual((len(w.coins), len(w.drops)), (0, 1))
        events = run(w, cp.DROP_TIME + 0.05)
        self.assertEqual([e.kind for e in events if e.kind == "land"], ["land"])
        coin = w.coins[0]
        self.assertAlmostEqual(coin.x, 40.0, delta=0.5)
        self.assertGreaterEqual(coin.y, cp.DROP_Y - 0.1)

    def test_drop_x_is_clamped_inside_the_walls(self):
        w = cp.PusherWorld()
        w.add_drop(-50)
        w.add_drop(500)
        self.assertEqual([d.x for d in w.drops], [cp.R, cp.W - cp.R])

    def test_a_drop_never_lands_inside_the_pusher(self):
        for offset in (0.0, 0.5, 1.0, 1.5):
            w = cp.PusherWorld()
            w.motor = offset * cp.PUSH_PERIOD / 2
            w.add_drop(30)
            run(w, cp.DROP_TIME + 0.02)
            self.assertGreaterEqual(w.coins[0].y - cp.R, w.face - 1e-6)

    def test_where_and_when_a_coin_is_dropped_changes_the_outcome(self):
        def outcome(x, motor):
            w = cp.initial_board(4)
            w.motor = motor
            w.add_drop(x)
            events = run(w, 6)
            return round(sum(c.x * 3 + c.y for c in w.coins), 1), sum(e.kind == "tray" for e in events)
        a, b = outcome(20, 0.0), outcome(110, 0.0)
        c = outcome(20, cp.PUSH_PERIOD / 2)
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)

    def test_pending_drops_and_stage_are_limited(self):
        w = cp.PusherWorld()
        for _ in range(cp.MAX_PENDING):
            self.assertTrue(w.can_accept())
            w.add_drop(60)
        self.assertFalse(w.can_accept())
        w = cp.PusherWorld()
        for i in range(cp.MAX_COINS):
            w.coins.append(cp.Coin(10, 60, uid=i))
        self.assertFalse(w.can_accept())


class ContactTests(unittest.TestCase):
    def test_overlapping_coins_are_pushed_apart(self):
        w = cp.PusherWorld()
        a, b = w.place(60, 70), w.place(63, 70)
        run(w, 1)
        self.assertGreaterEqual(math.hypot(a.x - b.x, a.y - b.y), 2 * cp.R - 0.4)

    def test_a_moving_coin_hits_a_resting_one_and_cannot_pass_through_it(self):
        w = cp.PusherWorld()
        mover, target = w.place(57, 70), w.place(70, 70)
        mover.vx = 40
        run(w, 1.2)
        self.assertLess(mover.x, target.x)                        # never swapped places
        self.assertGreater(target.x, 70.5)                        # it was shoved

    def test_walls_hold_coins_in_the_back_half(self):
        w = cp.PusherWorld()
        coin = w.place(20, 56)
        coin.vx = -45
        run(w, 1)
        self.assertGreaterEqual(coin.x, cp.R - 1e-6)
        self.assertEqual(len(w.coins), 1)

    def test_coin_type_does_not_change_the_motion(self):
        def final(kind):
            w = cp.initial_board(2)
            for c in w.coins:
                c.kind = kind
            w.add_drop(50)
            run(w, 5)
            return sorted((round(c.x, 3), round(c.y, 3)) for c in w.coins)
        self.assertEqual(final(cp.NORMAL), final(cp.GOLDEN))


class EdgeTests(unittest.TestCase):
    def test_front_edge_pays_exactly_once(self):
        w = cp.PusherWorld()
        far_beyond_front(w).vy = 25
        events = run(w, 0.3)
        trays = [e for e in events if e.kind == "tray"]
        self.assertEqual(len(trays), 1)
        self.assertEqual(w.coins, [])
        self.assertEqual(len(w.falling), 1)                       # still dropping into the tray (picture only)
        self.assertEqual([e for e in run(w, 2) if e.kind in ("tray", "lost")], [])

    def test_side_loss_in_the_open_part_pays_nothing(self):
        w = cp.PusherWorld()
        coin = w.place(cp.R, cp.SIDE_Y + 6)
        coin.x = 2.0
        coin.vx = -30
        events = run(w, 1)
        lost = [e for e in events if e.kind == "lost"]
        self.assertEqual((len(lost), lost[0].side), (1, -1))
        self.assertFalse([e for e in events if e.kind == "tray"])
        self.assertEqual(w.coins, [])

    def test_right_side_loss(self):
        w = cp.PusherWorld()
        coin = w.place(cp.W - cp.R, cp.SIDE_Y + 6)
        coin.x = cp.W - 2.0
        coin.vx = 30
        self.assertEqual([e.side for e in run(w, 1) if e.kind == "lost"], [1])

    def test_a_long_run_never_reports_a_coin_twice_and_conserves_coins(self):
        w = cp.initial_board(7)
        start = len(w.coins)
        rng = random.Random(3)
        added, seen, falls = 0, set(), 0
        for i in range(60 * 70):
            if i % 70 == 0 and w.can_accept():
                w.add_drop(rng.uniform(8, 122))
                added += 1
            for e in w.advance(DT):
                if e.kind in ("tray", "lost"):
                    falls += 1
                    self.assertNotIn(e.coin.uid, seen)
                    seen.add(e.coin.uid)
        self.assertEqual(start + added, len(w.coins) + len(w.drops) + falls)


class StabilityTests(unittest.TestCase):
    def test_a_busy_board_stays_inside_the_stage_without_blowing_up(self):
        w = cp.initial_board(11)
        rng = random.Random(5)
        peak = [0.0]
        worst_overlap = [0.0]

        def watch(world):
            for c in world.coins:
                self.assertTrue(math.isfinite(c.x) and math.isfinite(c.y))
                self.assertGreaterEqual(c.y - cp.R, world.face - 1e-6)
                self.assertLessEqual(c.speed, cp.MAX_SPEED * 1.001)
                peak[0] = max(peak[0], c.speed)
            if int(world.motor * 60) % 30 == 0:
                worst_overlap[0] = max(worst_overlap[0], overlaps(world))
        for i in range(24):
            if w.can_accept():
                w.add_drop(rng.uniform(8, 122))
            run(w, 1.4, on_step=watch)
        self.assertLess(peak[0], cp.MAX_SPEED + 0.1)
        self.assertLess(worst_overlap[0], 0.4 * 2 * cp.R)         # piles squeeze a little, never merge

    def test_a_calm_coin_comes_to_rest(self):
        w = cp.PusherWorld()
        coin = w.place(65, 70)
        coin.vx, coin.vy = 18, 12
        run(w, 4)
        self.assertEqual(coin.speed, 0.0)

    def test_resting_coins_do_not_jitter(self):
        w = cp.initial_board(3)
        run(w, 1)
        before = {c.uid: (c.x, c.y) for c in w.coins if c.y > 75}
        run(w, 0.5)                                               # the pusher is far from the front rows
        moved = max(math.hypot(c.x - before[c.uid][0], c.y - before[c.uid][1])
                    for c in w.coins if c.uid in before)
        self.assertLess(moved, 0.05)

    def test_initial_board_is_deterministic_per_seed(self):
        a, b, c = cp.initial_board(5), cp.initial_board(5), cp.initial_board(6)
        self.assertEqual(a.snapshot(), b.snapshot())
        self.assertNotEqual(a.snapshot(), c.snapshot())
        self.assertTrue(40 <= len(a.coins) <= 60)
        for coin in a.coins:
            self.assertTrue(cp.R - 0.5 <= coin.x <= cp.W - cp.R + 0.5 and coin.y > cp.FACE_MAX)
        self.assertLess(overlaps(a), 1.0)
        kinds = {c.kind for s in range(1, 8) for c in cp.initial_board(s).coins}
        self.assertEqual(kinds, set(cp.KINDS))

    def test_frame_rate_does_not_change_the_result(self):
        def final(dts):
            w = cp.initial_board(9)
            w.add_drop(40)
            w.add_drop(90)
            for dt in dts:
                w.advance(dt)
            return w.snapshot()
        total = 8.0
        at60 = final([1 / 60] * int(total * 60))
        self.assertEqual(at60, final([1 / 30] * int(total * 30)))
        self.assertEqual(at60, final([1 / 120] * int(total * 120)))
        self.assertEqual(at60, final([1 / 20] * int(total * 20)))

    def test_a_huge_frame_is_dropped_not_replayed(self):
        w = cp.PusherWorld()
        w.advance(30.0)
        self.assertLessEqual(w.motor, (cp.MAX_STEPS_PER_UPDATE + 1) * cp.STEP)

    def test_a_busy_board_steps_fast_enough(self):
        import time
        w = cp.initial_board(1)
        for i in range(12):
            w.add_drop(10 + i * 9)
        t0 = time.perf_counter()
        run(w, 4)
        per_step = (time.perf_counter() - t0) / (4 * 60)
        self.assertLess(per_step, 0.006)                          # well under a 16 ms frame, even on a slow box


class SnapshotTests(unittest.TestCase):
    def test_round_trip(self):
        w = cp.initial_board(8)
        w.add_drop(50, cp.MYSTERY, ("tickets", 3), paid=False)
        run(w, 0.1)
        snap = w.snapshot()
        back = cp.PusherWorld.from_snapshot(snap)
        self.assertEqual(len(back.coins), len(w.coins))
        self.assertEqual(len(back.drops), len(w.drops))
        self.assertEqual(sorted(c.kind for c in back.coins), sorted(c.kind for c in w.coins))
        for a, b in zip(sorted(back.coins, key=lambda c: (c.x, c.y)), sorted(w.coins, key=lambda c: (c.x, c.y))):
            self.assertLess(math.hypot(a.x - b.x, a.y - b.y), 0.6)
        self.assertFalse(back.drops[0].paid)
        self.assertEqual(back.drops[0].prize, ("tickets", 3))

    def test_bad_data_is_survived(self):
        self.assertIsNone(cp.PusherWorld.from_snapshot(None))
        self.assertIsNone(cp.PusherWorld.from_snapshot({"coins": "x"}))
        junk = {"coins": [[1, 2], "x", [float("nan"), 3, "n"], [50, 60, "q"], [50, 60, "m", ["tokens", 99]],
                          [999, -50, "g"], [60, 80, "s"]],
                "drops": [["a"], [10, "z", None]]}
        world = cp.PusherWorld.from_snapshot(junk)
        self.assertEqual(sorted(c.kind for c in world.coins), ["golden", "mystery", "silver"])
        for c in world.coins:
            self.assertTrue(0 <= c.x <= cp.W and c.y >= world.face + cp.R - 1e-6)
        mystery = next(c for c in world.coins if c.kind == "mystery")
        self.assertIn(mystery.prize, cp.MYSTERY_PRIZES)
        self.assertEqual(world.drops, [])


def profile(tokens=30, today=date(2026, 3, 10)):
    clock = GameClock(lambda: today)
    p = PlayerProfile(tokens=tokens, clock=clock)
    p.saves = []
    p.subscribe_save(lambda: p.saves.append(p.to_dict()))
    return p


def table(tokens=30, seed=1, **kw):
    p = profile(tokens, **kw)
    return p, CoinPusherTable(p, seed=seed)


class DropMoneyTests(unittest.TestCase):
    def test_opening_is_free_and_saves_the_new_board_at_once(self):
        p, t = table(30)
        self.assertEqual(p.tokens, 30)
        self.assertIsNotNone(p.pusher_state)
        self.assertTrue(p.saves)

    def test_a_drop_charges_exactly_one_token_and_adds_one_coin(self):
        p, t = table(30)
        before = t.world.count
        self.assertTrue(t.drop())
        self.assertEqual((p.tokens, t.world.count), (29, before + 1))
        self.assertEqual(p.to_dict()["lifetime_tokens_spent"], 1)

    def test_mashing_charges_once_until_the_cooldown_passes(self):
        p, t = table(30)
        self.assertEqual([t.drop() for _ in range(10)].count(True), 1)
        self.assertEqual(p.tokens, 29)
        t.update(DROP_COOLDOWN + 0.01)
        self.assertTrue(t.drop())
        self.assertEqual(p.tokens, 28)

    def test_no_charge_without_tokens(self):
        p, t = table(0)
        before = t.world.count
        self.assertFalse(t.drop())
        self.assertEqual((p.tokens, t.world.count, t.session_drops), (0, before, 0))
        self.assertEqual(t.drop_block_reason(), "NO TOKENS")

    def test_no_charge_when_the_machine_cannot_accept_a_coin(self):
        p, t = table(30)
        while t.world.count < cp.MAX_COINS:
            t.world.coins.append(cp.Coin(10, 80, uid=1000 + t.world.count))
        self.assertFalse(t.drop())
        self.assertEqual(p.tokens, 30)
        self.assertEqual(t.drop_block_reason(), "MACHINE FULL")
        t.world.coins.clear()
        t.world.drops = [cp.Drop(50, "normal", None, 99, 0)] * cp.MAX_PENDING
        self.assertFalse(t.drop())
        self.assertEqual(p.tokens, 30)

    def test_no_charge_while_paused_or_closed(self):
        p, t = table(30)
        t.pause()
        self.assertFalse(t.drop())
        t.resume()
        self.assertTrue(t.drop())
        t.close()
        t.cooldown = 0
        self.assertFalse(t.drop())
        self.assertEqual(p.tokens, 29)

    def test_pause_freezes_the_machine(self):
        p, t = table(30)
        t.drop()
        t.pause()
        motor, now = t.world.motor, t.world.time
        self.assertEqual(t.update(5.0), ([], []))
        self.assertEqual((t.world.motor, t.world.time), (motor, now))
        t.move_chute(1, 1.0)
        self.assertEqual(t.chute_x, cp.W / 2)
        t.resume()
        t.update(1.0)
        self.assertGreater(t.world.motor, motor)

    def test_chute_moves_and_stays_inside_the_walls(self):
        p, t = table()
        x0 = t.chute_x
        t.move_chute(1, 0.1)
        self.assertGreater(t.chute_x, x0)
        t.move_chute(-1, 100)
        self.assertEqual(t.chute_x, cp.R)
        t.move_chute(1, 100)
        self.assertEqual(t.chute_x, cp.W - cp.R)
        t.chute_x = 50
        t.drop()
        self.assertEqual(t.world.drops[-1].x, 50)

    def test_a_dropped_coin_is_a_normal_coin(self):
        p, t = table(30)
        t.drop()
        self.assertEqual((t.world.drops[-1].kind, t.world.drops[-1].paid), (cp.NORMAL, True))


class PayoutTests(unittest.TestCase):
    def collect(self, kind, prize=None, tokens=30, today=date(2026, 3, 10), t=None, p=None):
        if t is None:
            p, t = table(tokens, today=today)
        t.world.coins = []
        far_beyond_front(t.world, kind, prize).vy = 30
        _, payouts = t.update(0.5)
        return p, t, payouts

    def test_normal_coin_pays_one_token(self):
        p, t, payouts = self.collect(cp.NORMAL)
        self.assertEqual((p.tokens, p.tickets), (31, 0))
        self.assertEqual([x.kind for x in payouts], [cp.NORMAL])

    def test_silver_coin_pays_three_tokens(self):
        p, t, _ = self.collect(cp.SILVER)
        self.assertEqual(p.tokens, 30 + COIN_PUSHER_SILVER_TOKENS)

    def test_golden_cat_coin_pays_five_tickets(self):
        p, t, payouts = self.collect(cp.GOLDEN)
        self.assertEqual((p.tickets, p.tokens), (COIN_PUSHER_GOLDEN_TICKETS, 30))
        self.assertEqual(t.session_tickets, 5)
        self.assertFalse(payouts[0].capped)

    def test_golden_tickets_are_gambling_winnings_not_earned(self):
        p, t, _ = self.collect(cp.GOLDEN)
        self.assertEqual(p.to_dict()["lifetime_tickets_earned"], 0)

    def test_mystery_coin_pays_its_own_prize(self):
        for prize in cp.MYSTERY_PRIZES:
            p, t, payouts = self.collect(cp.MYSTERY, prize)
            self.assertEqual((30 + (prize[1] if prize[0] == "tokens" else 0),
                              prize[1] if prize[0] == "tickets" else 0), (p.tokens, p.tickets), prize)

    def test_mystery_prizes_are_modest(self):
        for currency, amount in cp.MYSTERY_PRIZES:
            self.assertLessEqual(amount, 4 if currency == "tokens" else 3)

    def test_side_loss_pays_nothing_and_is_saved(self):
        p, t = table(30)
        t.world.coins = []
        coin = t.world.place(cp.R, cp.SIDE_Y + 6)
        coin.x = 2.0
        coin.vx = -30
        t.update(1.0)
        self.assertEqual((p.tokens, p.tickets, t.lost), (30, 0, 1))
        self.assertEqual(p.pusher_state["board"]["coins"], [])

    def test_a_coin_is_paid_once_however_long_the_machine_runs(self):
        p, t, _ = self.collect(cp.SILVER)
        for _ in range(20):
            t.update(1.0)
        self.assertEqual(p.tokens, 33 + 0 * t.collected)
        self.assertEqual(t.collected, 1)

    def test_many_coins_in_one_frame_are_each_paid_once(self):
        p, t = table(30)
        t.world.coins = []
        for i in range(6):
            far_beyond_front(t.world, cp.NORMAL, x=10 + 20 * i).vy = 30
        t.update(0.5)
        self.assertEqual((p.tokens, t.collected), (36, 6))

    def test_daily_ticket_cap_turns_the_rest_into_a_token(self):
        p, t, _ = self.collect(cp.GOLDEN)
        for _ in range(COIN_PUSHER_DAILY_TICKET_CAP // COIN_PUSHER_GOLDEN_TICKETS - 1):
            self.collect(cp.GOLDEN, t=t, p=p)
        self.assertEqual((p.tickets, p.pusher_ticket_room()), (COIN_PUSHER_DAILY_TICKET_CAP, 0))
        tokens = p.tokens
        _, _, payouts = self.collect(cp.GOLDEN, t=t, p=p)
        self.assertEqual(p.tickets, COIN_PUSHER_DAILY_TICKET_CAP)               # nothing more
        self.assertEqual(p.tokens, tokens + 1)
        self.assertTrue(payouts[0].capped)

    def test_a_partly_used_cap_pays_what_is_left(self):
        p = profile(30)
        p.award_pusher_tickets(COIN_PUSHER_DAILY_TICKET_CAP - 3)
        t = CoinPusherTable(p, seed=2)
        _, _, payouts = self.collect(cp.GOLDEN, t=t, p=p)
        self.assertEqual(p.pusher_tickets_today(), COIN_PUSHER_DAILY_TICKET_CAP)
        self.assertEqual((payouts[0].tickets, payouts[0].tokens), (3, 1))

    def test_the_cap_resets_the_next_day_and_survives_a_restart(self):
        day = [date(2026, 3, 10)]
        p = PlayerProfile(tokens=30, clock=GameClock(lambda: day[0]))
        p.award_pusher_tickets(COIN_PUSHER_DAILY_TICKET_CAP)
        saved = p.to_dict()
        again = PlayerProfile.from_dict(saved, clock=GameClock(lambda: day[0]))
        self.assertEqual(again.pusher_ticket_room(), 0)
        day[0] += timedelta(days=1)
        self.assertEqual(again.pusher_ticket_room(), COIN_PUSHER_DAILY_TICKET_CAP)

    def test_the_cap_is_separate_from_neon_21(self):
        p = profile(30)
        p.award_pusher_tickets(COIN_PUSHER_DAILY_TICKET_CAP)
        self.assertGreater(p.neon21_ticket_room(), 0)


class BoardLifecycleTests(unittest.TestCase):
    def reopen(self, p):
        """What a restart does: the profile is rebuilt from its save data."""
        return PlayerProfile.from_dict(p.to_dict(), clock=p.clock)

    def test_reopening_never_resets_the_board(self):
        p, t = table(30, seed=12)
        first = p.pusher_state
        for _ in range(6):
            t.close()
            t = CoinPusherTable(p)
            t.update(0.0)
        self.assertEqual(p.pusher_state["seed"], first["seed"])
        self.assertEqual(p.pusher_state["board"], first["board"])
        self.assertEqual(p.tokens, 30)

    def test_closing_and_reopening_after_a_restart_keeps_every_coin(self):
        p, t = table(30, seed=3)
        t.drop()
        run(t.world, 5)
        t.close()
        kinds = sorted(c.kind for c in t.world.coins)
        q = self.reopen(p)
        t2 = CoinPusherTable(q)
        self.assertEqual(sorted(c.kind for c in t2.world.coins), kinds)
        self.assertEqual(q.tokens, 29)

    def test_restart_is_not_a_free_reroll_of_the_first_board(self):
        p, _ = table(30, seed=4)
        q = self.reopen(p)
        self.assertEqual(CoinPusherTable(q).world.snapshot()["coins"].__len__(),
                         len(CoinPusherTable(self.reopen(p)).world.coins))
        self.assertEqual(q.pusher_state["seed"], 4)

    def test_leaving_with_a_coin_in_the_air_keeps_it(self):
        p, t = table(30)
        n = len(t.world.coins)
        t.drop()
        t.close()
        self.assertEqual((len(t.world.coins), t.world.drops), (n + 1, []))
        self.assertEqual(len(p.pusher_state["board"]["coins"]), n + 1)
        self.assertEqual(p.pusher_state["board"]["drops"], [])

    def test_a_crash_right_after_a_drop_keeps_the_token_spent_and_the_coin_on_the_board(self):
        p, t = table(30)
        n = len(t.world.coins)
        t.drop()
        crashed = PlayerProfile.from_dict(p.saves[-1], clock=p.clock)        # the file as it was when the app died
        self.assertEqual(crashed.tokens, 29)
        t2 = CoinPusherTable(crashed)
        self.assertEqual(len(t2.world.coins), n + 1)

    def test_a_crash_right_after_a_payout_keeps_the_reward_and_removes_the_coin(self):
        p, t = table(30)
        t.world.coins = []
        far_beyond_front(t.world, cp.SILVER).vy = 30
        t.update(0.5)
        crashed = PlayerProfile.from_dict(p.saves[-1], clock=p.clock)
        self.assertEqual(crashed.tokens, 33)
        self.assertEqual(CoinPusherTable(crashed).world.coins, [])

    def test_every_save_is_consistent_so_nothing_is_lost_or_duplicated(self):
        """Replay a long game and check the books at every single save the profile asked for."""
        p, t = table(60, seed=21)
        start = len(t.world.coins)
        rng = random.Random(8)
        problems = []

        def check():
            s = p.to_dict()
            state = s["coin_pusher"]
            on_board = len(state["board"]["coins"]) + len(state["board"]["drops"])
            spent = s["lifetime_tokens_spent"]
            expected = start + state["stock"] + spent - t.collected - t.lost
            if on_board != expected:
                problems.append((on_board, expected))
        p.subscribe_save(check)
        for i in range(60 * 90):
            if i % 55 == 0:
                t.chute_x = rng.uniform(8, 122)
                t.drop()
            t.update(DT)
        t.close()
        self.assertEqual(problems, [])
        self.assertGreater(t.collected + t.lost, 5)

    def test_players_have_separate_boards_and_wallets(self):
        a, ta = table(30, seed=1)
        b, tb = table(30, seed=2)
        self.assertNotEqual(a.pusher_state["board"], b.pusher_state["board"])
        ta.drop()
        self.assertEqual((a.tokens, b.tokens), (29, 30))
        before = b.pusher_state["board"]
        run(ta.world, 6)
        ta.update(1.0)
        self.assertEqual(b.pusher_state["board"], before)
        ta.world.coins = []
        far_beyond_front(ta.world, cp.GOLDEN).vy = 30
        ta.update(0.5)
        self.assertEqual((a.tickets, b.tickets), (5, 0))
        self.assertEqual(b.pusher_ticket_room(), COIN_PUSHER_DAILY_TICKET_CAP)

    def test_a_profile_without_a_board_is_unchanged_on_disk(self):
        p = PlayerProfile(tokens=5)
        self.assertNotIn("coin_pusher", p.to_dict())
        self.assertIsNone(PlayerProfile.from_dict(p.to_dict()).pusher_state)

    def test_corrupt_saved_data_starts_a_fresh_board_without_crashing(self):
        for junk in ({"board": "x"}, {"board": {"coins": 4}}, {"seed": "s", "board": {"coins": []}}, [1], "x"):
            p = PlayerProfile.from_dict({"tokens": 7, "coin_pusher": junk})
            t = CoinPusherTable(p)
            self.assertGreater(len(t.world.coins), 20)
            self.assertEqual(p.tokens, 7)

    def test_a_saved_board_is_not_shared_by_copying_the_state_object(self):
        p, t = table()
        state = p.pusher_state
        state["board"]["coins"].clear()
        self.assertTrue(p.pusher_state["board"]["coins"])


class RestockTests(unittest.TestCase):
    def drain(self, t):
        t.world.coins = t.world.coins[:cp.RESTOCK_BELOW - 4]

    def test_the_machine_restocks_a_thin_board_one_coin_at_a_time(self):
        p, t = table(30)
        self.drain(t)
        before = t.world.count
        t.update(cp.RESTOCK_EVERY + 0.1)
        self.assertEqual((t.world.count, t.stock), (before + 1, 1))
        self.assertFalse(t.world.drops[0].paid)

    def test_it_stops_when_the_board_is_healthy(self):
        p, t = table(30)
        t.update(10)
        self.assertEqual(t.stock, 0)

    def test_restock_does_not_charge_the_player(self):
        p, t = table(30)
        self.drain(t)
        t.update(5)
        self.assertEqual(p.to_dict()["lifetime_tokens_spent"], 0)

    def test_the_restock_sequence_cannot_be_rerolled_by_reopening(self):
        from unittest.mock import patch

        def specs(reopen):
            made = []
            real = cp.make_coin_spec

            def record(rng, *args):
                spec = real(rng, *args)
                made.append(spec)
                return spec
            with patch.object(cp, "make_coin_spec", record):
                p, t = table(30, seed=5)
                self.drain(t)
                for _ in range(8):
                    self.drain(t)
                    for _ in range(int((cp.RESTOCK_EVERY + 0.05) / DT)):
                        t.update(DT)
                    if reopen:
                        t.close()
                        p = PlayerProfile.from_dict(p.to_dict(), clock=p.clock)
                        t = CoinPusherTable(p)
            return made[-8:], t.stock
        straight, stock_a = specs(False)
        reopened, stock_b = specs(True)
        self.assertEqual(stock_a, stock_b)
        self.assertEqual(straight, reopened)


class EconomyTests(unittest.TestCase):
    """Simulated play: the machine must pay back less than it takes, yet pay often enough to be fun."""

    VALUE = {cp.NORMAL: 1, cp.SILVER: 3, cp.GOLDEN: 1.5, cp.MYSTERY: 2}      # a Ticket is worth ~0.3 Token

    def play(self, seed, interval, drops, picker):
        p, t = table(drops + 10, seed=seed)
        p.tokens_start = p.tokens
        rng = random.Random(seed)
        cycle_wins = {}
        value, last_drop = 0.0, -99.0
        now = 0.0
        while t.session_drops < drops:
            if now - last_drop >= interval:
                t.chute_x = picker(rng)
                if t.drop():
                    last_drop = now
            _, payouts = t.update(DT)
            for pay in payouts:
                value += self.VALUE[pay.kind]
                cycle_wins[int(now // cp.PUSH_PERIOD)] = cycle_wins.get(int(now // cp.PUSH_PERIOD), 0) + 1
            now += DT
        return value / drops, cycle_wins, now, p, t

    def test_random_play_returns_less_than_it_costs_and_wins_come_often_enough(self):
        rtp, wins, total, p, t = self.play(1, 1.2, 70, lambda r: r.uniform(8, 122))
        self.assertTrue(0.45 < rtp < 0.97, rtp)
        cycles = int(total // cp.PUSH_PERIOD)
        paying = sum(1 for c in range(3, cycles) if wins.get(c))
        self.assertGreater(paying / (cycles - 3), 0.5)            # a payout in most pusher strokes ...
        self.assertLess(paying / (cycles - 3), 1.0)               # ... but not in every single one
        self.assertLess(p.tokens, p.tokens_start + 5)             # the player does not get rich from random play

    def test_aiming_at_the_middle_does_not_break_the_economy_either(self):
        rtp, *_ = self.play(2, 1.2, 60, lambda r: 65 + r.uniform(-6, 6))
        self.assertTrue(0.45 < rtp < 1.05, rtp)

    def test_the_first_payout_arrives_in_a_few_drops(self):
        p, t = table(40, seed=3)
        rng = random.Random(1)
        for i in range(30):
            t.chute_x = rng.uniform(8, 122)
            t.drop()
            for _ in range(60):
                t.update(DT)
            if t.collected:
                break
        self.assertTrue(t.collected, "nothing paid in 30 drops")
        self.assertLessEqual(i, 14)


if __name__ == "__main__":
    unittest.main()
