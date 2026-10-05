"""Tests for the token economy: the coins -> tokens migration, daily login,
daily tasks, the Lucky Corner games and how they plug into the arcade.

Run headless from this folder:   python -m unittest test_economy -v
"""
import json
import os
import random
import shutil
import tempfile
import unittest
from datetime import date, timedelta

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from chance_game import ChanceGame  # noqa: E402
from chance_scene import ChanceGameScene  # noqa: E402
from daily_rewards import DailyRewardManager  # noqa: E402
from daily_tasks import DailyTaskManager, TaskSpec  # noqa: E402
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from high_low import HIGHER, LOWER, HighLowGame  # noqa: E402
from lucky_wheel import SPIN_TIME, LuckyWheelGame  # noqa: E402
from machine import ArcadeMachine  # noqa: E402
from player_profile import SAVE_VERSION, PlayerProfile, ProfileStore  # noqa: E402
from settings import (DAILY_REWARDS, DAILY_TASK_COUNT, DAILY_TASK_POOL,  # noqa: E402
                      HIGH_LOW_COST, HIGH_LOW_PAYOUTS, HIGH_LOW_RANKS,
                      LUCKY_WHEEL_REWARDS, MACHINES)
from stations import ChanceStation, DailyBoard  # noqa: E402

DT = 1 / 60
DAY1 = date(2026, 3, 10)
COST, PAY = HIGH_LOW_COST, HIGH_LOW_PAYOUTS


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def clock_at(day=DAY1):
    return GameClock(lambda: day)


class SeqRng(random.Random):
    """A rigged RNG for tests: randint() returns the queued values in order."""

    def __init__(self, *values):
        super().__init__(0)
        self.values = list(values)

    def randint(self, a, b):
        value = self.values.pop(0)
        assert a <= value <= b
        return value


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save_data.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def write_save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)


# ---------------------------------------------------------------- coins -> tokens
class TokenMigrationTests(TempDirTest):
    OLD = {"version": 1, "coins": 8, "tickets": 40, "total_games_played": 6,
           "lifetime_tickets_earned": 90, "high_scores": {"retro_racer": 5200}}

    def test_old_save_coins_become_tokens(self):
        self.write_save(self.OLD)
        p = ProfileStore(self.path, clock_at()).load()
        self.assertEqual(p.tokens, 8)
        self.assertEqual((p.tickets, p.total_games_played, p.lifetime_tickets_earned), (40, 6, 90))
        self.assertEqual(p.high_scores, {"retro_racer": 5200})
        self.assertFalse(hasattr(p, "coins"))

    def test_migrated_save_is_rewritten_in_the_new_schema(self):
        self.write_save(self.OLD)
        ProfileStore(self.path, clock_at()).load()
        data = self.saved()
        self.assertNotIn("coins", data)
        self.assertEqual((data["version"], data["tokens"], data["tickets"]), (SAVE_VERSION, 8, 40))
        self.assertEqual(data["high_scores"], {"retro_racer": 5200})
        for field in ("last_login_date", "daily_streak", "last_daily_reward_claimed",
                      "daily_tasks", "lifetime_tokens_earned", "lifetime_tokens_spent",
                      "chance_games_played", "transaction_history"):
            self.assertIn(field, data)

    def test_tokens_win_when_both_fields_exist(self):
        self.write_save({"coins": 3, "tokens": 12})
        self.assertEqual(ProfileStore(self.path, clock_at()).load().tokens, 12)

    def test_zero_coins_migrate_as_zero_not_default(self):
        self.write_save({"coins": 0})
        self.assertEqual(ProfileStore(self.path, clock_at()).load().tokens, 0)

    def test_machine_costs_are_tokens(self):
        m = ArcadeMachine(dict(MACHINES[0], play_cost=1))
        self.assertEqual(m.cost_label, "1 TOKEN")
        p = PlayerProfile(tokens=1, tickets=7, clock=clock_at())
        self.assertIsNotNone(m.start_play(p))
        self.assertEqual((p.tokens, p.tickets), (0, 7))     # tickets untouched
        self.assertEqual(p.history_lines()[-1], "-1 TOKEN  RETRO RACER")

    def test_no_coin_wording_left_in_the_profile_api(self):
        p = PlayerProfile(clock=clock_at())
        self.assertFalse([n for n in dir(p) if "coin" in n.lower()])


# ---------------------------------------------------------------- profile ledger
class TokenLedgerTests(unittest.TestCase):
    def test_lifetime_totals_and_history(self):
        p = PlayerProfile(tokens=10, clock=clock_at())
        p.add_tokens(7, "daily login")
        p.spend_tokens(1, "Retro Racer")
        p.add_tokens(5, "daily task")
        self.assertEqual((p.lifetime_tokens_earned, p.lifetime_tokens_spent), (12, 1))
        self.assertEqual(p.history_lines(), ["+7 TOKEN  DAILY LOGIN", "-1 TOKEN  RETRO RACER",
                                             "+5 TOKEN  DAILY TASK"])

    def test_refused_spend_is_not_logged(self):
        p = PlayerProfile(tokens=0, clock=clock_at())
        self.assertFalse(p.spend_tokens(1, "x"))
        self.assertEqual((p.history, p.lifetime_tokens_spent), ([], 0))

    def test_refund_undoes_the_spend(self):
        p = PlayerProfile(tokens=5, clock=clock_at())
        p.spend_tokens(2, "x")
        p.refund_tokens(2, "x")
        self.assertEqual((p.tokens, p.lifetime_tokens_spent, p.lifetime_tokens_earned), (5, 0, 0))

    def test_history_is_bounded_and_saved(self):
        p = PlayerProfile(tokens=1000, clock=clock_at())
        for _ in range(100):
            p.spend_tokens(1, "x")
        self.assertEqual(len(p.history), 30)
        q = PlayerProfile.from_dict(p.to_dict(), clock_at())
        self.assertEqual(q.history, p.history)

    def test_tokens_and_tickets_stay_separate(self):
        p = PlayerProfile(tokens=3, tickets=9, clock=clock_at())
        p.add_tickets(10)
        p.spend_tokens(1, "x")
        self.assertEqual((p.tokens, p.tickets), (2, 19))


# ---------------------------------------------------------------- daily login
class DailyRewardTests(TempDirTest):
    def profile(self, day=DAY1):
        return PlayerProfile(clock=clock_at(day))

    def test_first_login_awards_day_one(self):
        p = self.profile()
        status = p.daily_status()
        self.assertEqual((status.can_claim, status.day, status.tokens), (True, 1, 5))
        claim = p.claim_daily_reward()
        self.assertEqual((claim.day, claim.tokens), (1, 5))
        self.assertEqual(p.tokens, 15)
        self.assertEqual((p.daily_streak, p.last_daily_reward_claimed), (1, DAY1))
        self.assertEqual(p.history_lines()[-1], "+5 TOKEN  DAILY LOGIN")

    def test_same_day_cannot_claim_twice(self):
        p = self.profile()
        p.claim_daily_reward()
        self.assertIsNone(p.claim_daily_reward())
        self.assertFalse(p.daily_status().can_claim)
        self.assertEqual(p.tokens, 15)

    def test_reopening_the_game_the_same_day_gives_nothing(self):
        store = ProfileStore(self.path, clock_at())
        p = store.load()
        store.autosave(p)
        p.claim_daily_reward()
        again = ProfileStore(self.path, clock_at()).load()      # "closed and reopened"
        self.assertFalse(again.daily_status().can_claim)
        self.assertIsNone(again.claim_daily_reward())
        self.assertEqual((again.tokens, again.daily_streak), (15, 1))

    def test_claim_is_saved_immediately(self):
        store = ProfileStore(self.path, clock_at())
        p = store.load()
        store.autosave(p)
        p.claim_daily_reward()
        data = self.saved()
        self.assertEqual((data["tokens"], data["daily_streak"], data["last_daily_reward_claimed"]),
                         (15, 1, DAY1.isoformat()))

    def test_streak_runs_through_the_week_then_restarts(self):
        p = self.profile()
        got = []
        for i in range(9):
            p.clock = clock_at(DAY1 + timedelta(days=i))
            got.append(p.claim_daily_reward().tokens)
        self.assertEqual(got, list(DAILY_REWARDS) + [5, 6])
        self.assertEqual(got[:7], [5, 6, 7, 8, 10, 12, 15])

    def test_hold_keeps_paying_the_last_day(self):
        m = DailyRewardManager(after_last="hold")
        got = [m.claim(DAY1 + timedelta(days=i)).tokens for i in range(9)]
        self.assertEqual(got, [5, 6, 7, 8, 10, 12, 15, 15, 15])

    def test_missing_a_day_resets_the_streak(self):
        p = self.profile()
        p.claim_daily_reward()
        p.clock = clock_at(DAY1 + timedelta(days=1))
        p.claim_daily_reward()
        p.clock = clock_at(DAY1 + timedelta(days=4))             # skipped two days
        claim = p.claim_daily_reward()
        self.assertEqual((claim.day, claim.tokens, p.daily_streak), (1, 5, 1))

    def test_keep_mode_continues_after_a_miss(self):
        m = DailyRewardManager(on_miss="keep")
        m.claim(DAY1)
        claim = m.claim(DAY1 + timedelta(days=5))
        self.assertEqual((claim.day, claim.tokens), (2, 6))

    def test_next_calendar_day_after_late_night_play(self):
        """Dates, not hours: 23:59 -> 00:01 is a new day."""
        m = DailyRewardManager()
        m.claim(DAY1)
        self.assertFalse(m.can_claim(DAY1))
        self.assertTrue(m.can_claim(DAY1 + timedelta(days=1)))

    def test_clock_set_backwards_gives_no_second_reward(self):
        p = self.profile(DAY1 + timedelta(days=3))
        p.claim_daily_reward()
        p.clock = clock_at(DAY1)
        self.assertIsNone(p.claim_daily_reward())

    def test_login_date_recorded_and_persisted(self):
        p = self.profile()
        p.record_login()
        q = PlayerProfile.from_dict(p.to_dict(), clock_at())
        self.assertEqual(q.last_login_date, DAY1)

    def test_bad_saved_dates_fall_back_to_fresh(self):
        q = PlayerProfile.from_dict({"daily_streak": 4, "last_daily_reward_claimed": "yesterday",
                                     "last_login_date": 5}, clock_at())
        self.assertEqual((q.daily_streak, q.last_daily_reward_claimed, q.last_login_date), (0, None, None))
        self.assertTrue(q.daily_status().can_claim)

    def test_config_is_validated(self):
        for bad in ({"rewards": ()}, {"on_miss": "sometimes"}, {"after_last": "loop"}):
            with self.assertRaises(ValueError):
                DailyRewardManager(**bad)


# ---------------------------------------------------------------- daily tasks
class DailyTaskTests(TempDirTest):
    def profile(self, day=DAY1):
        return PlayerProfile(clock=clock_at(day))

    def only(self, *specs, count=None):
        """A profile whose tasks are exactly `specs` (dicts)."""
        mgr = DailyTaskManager(pool=specs, count=count or len(specs))
        return PlayerProfile(daily_tasks=mgr, clock=clock_at())

    def test_three_tasks_generate_from_the_pool(self):
        p = self.profile()
        ids = [t.id for t in p.daily_tasks]
        self.assertEqual(len(ids), DAILY_TASK_COUNT)
        self.assertEqual(len(set(ids)), DAILY_TASK_COUNT)
        usable = {s["id"] for s in DAILY_TASK_POOL if s.get("available", True)}
        self.assertLessEqual(set(ids), usable)
        self.assertEqual(p.daily_tasks_date, DAY1)
        for t in p.daily_tasks:
            self.assertEqual((t.progress, t.completed, t.claimed), (0, False, False))

    def test_task_rewards_are_modest(self):
        for spec in DAILY_TASK_POOL:
            self.assertTrue(3 <= spec["reward"] <= 10, spec["id"])

    def test_game_progress_completion_and_claim_once(self):
        p = self.only({"id": "g", "description": "PLAY 3", "event": "game_played",
                       "target": 3, "reward": 5})
        before = p.tokens
        for _ in range(2):
            p.record_game_played("space_blaster")
        task = p.daily_tasks[0]
        self.assertEqual((task.progress, task.completed), (2, False))
        self.assertEqual(p.claim_task("g"), 0)                  # not finished: nothing
        p.record_game_played("puzzle_drop")
        p.record_game_played("puzzle_drop")                     # past the target: capped
        self.assertEqual((task.progress, task.completed, task.claimed), (3, True, False))
        self.assertEqual(p.claim_task("g"), 5)
        self.assertEqual(p.claim_task("g"), 0)                  # claimed once only
        self.assertEqual(p.tokens, before + 5)
        self.assertTrue(task.claimed)
        self.assertEqual(p.history_lines()[-1], "+5 TOKEN  DAILY TASK")

    def test_ticket_task_counts_tickets_not_tokens(self):
        p = self.only({"id": "t", "description": "EARN 50", "event": "tickets_earned",
                       "target": 50, "reward": 8})
        p.add_tickets(20)
        p.add_tokens(100, "x")
        p.add_tickets(40)
        self.assertEqual((p.daily_tasks[0].progress, p.daily_tasks[0].completed), (50, True))

    def test_machine_specific_task(self):
        p = self.only({"id": "r", "description": "PLAY RACER", "event": "game_played",
                       "game_id": "retro_racer", "target": 1, "reward": 4})
        p.record_game_played("space_blaster")
        self.assertEqual(p.daily_tasks[0].progress, 0)
        p.record_game_played("retro_racer")
        self.assertTrue(p.daily_tasks[0].completed)

    def test_distinct_machine_visits(self):
        p = self.only({"id": "v", "description": "VISIT 3", "event": "machine_visited",
                       "distinct": True, "target": 3, "reward": 5})
        for m in ("retro_racer", "retro_racer", "space_blaster", "retro_racer"):
            p.record_machine_visit(m)
        self.assertEqual(p.daily_tasks[0].progress, 2)
        p.record_machine_visit("puzzle_drop")
        self.assertTrue(p.daily_tasks[0].completed)

    def test_pet_and_high_score_tasks(self):
        p = self.only({"id": "c", "description": "PET 3", "event": "cat_petted", "target": 3, "reward": 3},
                      {"id": "h", "description": "BEAT", "event": "high_score", "target": 1, "reward": 10})
        for _ in range(3):
            p.record_cat_petted()
        p.record_score("retro_racer", 500)
        self.assertEqual([t.completed for t in p.daily_tasks], [True, True])
        self.assertEqual(p.cats_petted, 3)

    def test_lower_score_does_not_count_as_beating(self):
        p = PlayerProfile(high_scores={"retro_racer": 900}, daily_tasks=DailyTaskManager(
            pool=[{"id": "h", "description": "B", "event": "high_score", "target": 1, "reward": 10}], count=1),
            clock=clock_at())
        p.record_score("retro_racer", 400)
        self.assertFalse(p.daily_tasks[0].completed)
        p.record_score("retro_racer", 901)
        self.assertTrue(p.daily_tasks[0].completed)

    def finish_everything(self, p):
        """Complete every task the pool can offer."""
        p.add_tickets(60)
        for _ in range(3):
            p.record_cat_petted()
            p.record_game_played("retro_racer")
        for m in ("retro_racer", "space_blaster", "puzzle_drop"):
            p.record_machine_visit(m)

    def test_reopen_preserves_progress_and_claims(self):
        store = ProfileStore(self.path, clock_at())
        p = store.load()
        store.autosave(p)
        ids = [t.id for t in p.daily_tasks]
        p.record_cat_petted()                                    # part way on some tasks
        p.record_game_played("space_blaster")
        q = ProfileStore(self.path, clock_at()).load()
        self.assertEqual([t.id for t in q.daily_tasks], ids)
        self.assertEqual([t.progress for t in q.daily_tasks], [t.progress for t in p.daily_tasks])

        self.finish_everything(p)
        first = p.daily_tasks[0]
        self.assertEqual(p.claim_task(first.id), first.reward_tokens)
        data = self.saved()
        self.assertEqual(data["daily_tasks"]["task_ids"], ids)
        self.assertEqual(data["daily_tasks"]["date"], DAY1.isoformat())
        q = ProfileStore(self.path, clock_at()).load()
        self.assertEqual([(t.progress, t.completed, t.claimed) for t in q.daily_tasks],
                         [(t.progress, t.completed, t.claimed) for t in p.daily_tasks])
        self.assertEqual(q.claim_task(first.id), 0)              # no second claim after reload
        self.assertEqual(q.claim_task(p.daily_tasks[1].id), p.daily_tasks[1].reward_tokens)

    def test_distinct_progress_survives_reload(self):
        spec = {"id": "v", "description": "VISIT 3", "event": "machine_visited",
                "distinct": True, "target": 3, "reward": 5}
        p = self.only(spec)
        p.record_machine_visit("a")
        q = PlayerProfile.from_dict(p.to_dict(), clock_at())
        q._tasks = DailyTaskManager.from_dict(p.to_dict()["daily_tasks"], pool=[spec], count=1)
        q.record_machine_visit("a")
        q.record_machine_visit("b")
        self.assertEqual(q._tasks.tasks[0].progress, 2)

    def test_same_day_keeps_tasks_next_day_makes_new_ones(self):
        p = self.profile()
        p.record_cat_petted()
        same = [t.id for t in p.daily_tasks]
        self.assertFalse(p.sync_daily_tasks())
        self.assertEqual([t.id for t in p.daily_tasks], same)

        p.clock = clock_at(DAY1 + timedelta(days=1))
        self.assertTrue(p.sync_daily_tasks())
        self.assertEqual(p.daily_tasks_date, DAY1 + timedelta(days=1))
        self.assertEqual(len(p.daily_tasks), DAILY_TASK_COUNT)
        self.assertTrue(all(t.progress == 0 and not t.claimed for t in p.daily_tasks))

    def test_reload_on_a_later_day_generates_new_tasks(self):
        store = ProfileStore(self.path, clock_at())
        p = store.load()
        store.autosave(p)
        p.record_cat_petted()
        p.add_tokens(1, "x")                                     # make sure it is saved
        q = ProfileStore(self.path, clock_at(DAY1 + timedelta(days=2))).load()
        self.assertEqual(q.daily_tasks_date, DAY1 + timedelta(days=2))
        self.assertTrue(all(t.progress == 0 for t in q.daily_tasks))

    def test_event_after_midnight_goes_to_the_new_days_tasks(self):
        p = self.only({"id": "c", "description": "PET", "event": "cat_petted", "target": 3, "reward": 3})
        p.record_cat_petted()
        p.clock = clock_at(DAY1 + timedelta(days=1))
        p.record_cat_petted()
        self.assertEqual(p.daily_tasks[0].progress, 1)

    def test_unknown_or_broken_saved_tasks_are_dropped(self):
        data = PlayerProfile(clock=clock_at()).to_dict()
        data["daily_tasks"]["tasks"] += [{"id": "gone"}, "junk", {"id": "pet_cats", "progress": "x"}]
        q = PlayerProfile.from_dict(data, clock_at())
        ids = [t.id for t in q.daily_tasks]
        self.assertNotIn("gone", ids)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(t.progress >= 0 for t in q.daily_tasks))

    def test_save_with_no_usable_tasks_regenerates(self):
        q = PlayerProfile.from_dict({"daily_tasks": {"date": DAY1.isoformat(),
                                                     "tasks": [{"id": "gone"}]}}, clock_at())
        self.assertEqual(len(q.daily_tasks), DAILY_TASK_COUNT)

    def test_reset_gives_a_fresh_unclaimed_set(self):
        p = self.profile()
        p.record_cat_petted()
        p.reset_daily_tasks()
        self.assertEqual(len(p.daily_tasks), DAILY_TASK_COUNT)
        self.assertTrue(all(t.progress == 0 for t in p.daily_tasks))

    def test_tasks_are_repeatable_per_date(self):
        a = DailyTaskManager()
        b = DailyTaskManager()
        a.ensure_current(DAY1)
        b.ensure_current(DAY1)
        self.assertEqual([t.id for t in a.tasks], [t.id for t in b.tasks])

    def test_spec_matching_helper(self):
        spec = TaskSpec("x", "X", "game_played", 2, 3)
        self.assertEqual((spec.game_id, spec.distinct, spec.available), (None, False, True))


# ---------------------------------------------------------------- chance games
class LuckyWheelTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(tokens=10, clock=clock_at())

    def test_odds_total_one_and_do_not_favour_the_player(self):
        wheel = LuckyWheelGame()
        self.assertAlmostEqual(sum(wheel.probabilities().values()), 1.0)
        self.assertLessEqual(wheel.expected_payout(), wheel.cost)
        self.assertEqual(sorted(wheel.probabilities()), [0, 1, 2, 3, 5, 10])
        self.assertEqual(wheel.cost, 1)

    def test_charges_once_even_if_started_repeatedly(self):
        wheel = LuckyWheelGame(rng=random.Random(1))
        self.assertTrue(wheel.start(self.p))
        for _ in range(5):
            self.assertFalse(wheel.start(self.p))
        self.assertEqual(self.p.tokens, 9)
        self.assertEqual(self.p.chance_games_played, 1)
        self.assertEqual(self.p.lifetime_tokens_spent, 1)

    def test_pays_out_exactly_once(self):
        for seed in range(30):
            p = PlayerProfile(tokens=10, clock=clock_at())
            wheel = LuckyWheelGame(rng=random.Random(seed))
            wheel.start(p)
            prize = wheel.prize
            for _ in range(int((SPIN_TIME + 3) / DT)):
                wheel.update(DT)
            self.assertEqual(wheel.phase, wheel.DONE)
            wheel.finish()
            wheel.finish()
            for _ in range(60):
                wheel.update(DT)
            self.assertEqual(p.tokens, 9 + prize, seed)
            self.assertEqual(wheel.get_result().payout, prize)
            self.assertEqual(wheel.get_result().net, prize - 1)

    def test_wheel_stops_on_a_slice_showing_the_prize(self):
        for seed in range(40):
            wheel = LuckyWheelGame(rng=random.Random(seed))
            wheel.start(PlayerProfile(tokens=1, clock=clock_at()))
            for _ in range(int((SPIN_TIME + 0.5) / DT)):
                wheel.update(DT)
            self.assertEqual(wheel.slices[wheel.slice_under_pointer()], wheel.prize, seed)

    def test_leaving_mid_spin_pays_the_same_prize_once(self):
        wheel = LuckyWheelGame(rng=random.Random(4))
        wheel.start(self.p)
        prize = wheel.prize
        wheel.update(0.5)
        result = wheel.finish()
        self.assertEqual(wheel.finish(), result)
        self.assertEqual(self.p.tokens, 9 + prize)

    def test_cannot_play_without_tokens(self):
        broke = PlayerProfile(tokens=0, clock=clock_at())
        wheel = LuckyWheelGame()
        self.assertFalse(wheel.can_play(broke))
        self.assertFalse(wheel.start(broke))
        self.assertEqual((broke.tokens, wheel.phase, broke.chance_games_played), (0, wheel.IDLE, 0))
        self.assertIsNone(wheel.finish())

    def test_finish_before_start_does_nothing(self):
        wheel = LuckyWheelGame()
        self.assertIsNone(wheel.finish())
        self.assertEqual(self.p.tokens, 10)

    def test_probabilities_match_the_table_over_many_rounds(self):
        rng = random.Random(123)
        wheel = LuckyWheelGame(rng=rng)
        counts = {}
        n = 20000
        for _ in range(n):
            prize = wheel._draw_prize()
            counts[prize] = counts.get(prize, 0) + 1
        for tokens, p in wheel.probabilities().items():
            self.assertAlmostEqual(counts.get(tokens, 0) / n, p, delta=0.015)

    def test_bad_config_rejected(self):
        with self.assertRaises(ValueError):
            LuckyWheelGame(rewards=[{"tokens": 1, "weight": 0}], slices=(1,))
        with self.assertRaises(ValueError):
            LuckyWheelGame(slices=(0, 1, 2))          # slices must show every reward

    def test_rewards_are_modest(self):
        self.assertLessEqual(max(r["tokens"] for r in LUCKY_WHEEL_REWARDS), 10)


class HighLowTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(tokens=10, clock=clock_at())

    def game(self, *cards):
        g = HighLowGame(rng=SeqRng(*cards))
        self.assertTrue(g.start(self.p))
        return g

    def flip(self, g):
        for _ in range(60):
            g.update(DT)

    def test_charges_once(self):
        g = self.game(7)
        for _ in range(4):
            self.assertFalse(g.start(self.p))
        self.assertEqual((self.p.tokens, self.p.chance_games_played), (10 - COST, 1))

    def test_win_then_cash_out_pays_once(self):
        g = self.game(5, 9)                         # 5 -> HIGHER -> 9
        self.assertTrue(g.guess(HIGHER))
        self.flip(g)
        self.assertEqual((g.streak, g.prize, g.phase), (1, PAY[0], g.PLAYING))
        self.assertEqual(self.p.tokens, 10 - COST)  # nothing paid until cash out
        self.assertTrue(g.cash_out())
        for _ in range(5):
            self.assertFalse(g.cash_out())
            g.finish()
        self.assertEqual(self.p.tokens, 10 - COST + PAY[0])
        self.assertEqual(g.get_result().payout, PAY[0])

    def test_loss_pays_nothing(self):
        g = self.game(5, 2)
        g.guess(HIGHER)
        self.flip(g)
        self.assertEqual((g.phase, g.get_result().payout, self.p.tokens), (g.DONE, 0, 10 - COST))
        g.finish()
        self.assertEqual(self.p.tokens, 10 - COST)

    def test_tie_loses(self):
        g = self.game(6, 6)
        g.guess(LOWER)
        self.flip(g)
        self.assertEqual((g.get_result().payout, self.p.tokens), (0, 10 - COST))

    def test_double_or_continue_ladder_and_max_streak(self):
        g = self.game(5, 9, 3, 12)                  # H win, L win, H win -> max
        for direction in (HIGHER, LOWER, HIGHER):
            self.assertTrue(g.guess(direction))
            self.flip(g)
        self.assertEqual(g.phase, g.DONE)           # auto cash-out at the top
        self.assertEqual(self.p.tokens, 10 - COST + PAY[-1])
        self.assertEqual(g.get_result().payout, PAY[-1])
        self.assertFalse(g.guess(HIGHER))           # nothing more can happen
        g.finish()
        self.assertEqual(self.p.tokens, 10 - COST + PAY[-1])
        self.assertEqual(g.max_streak, len(HIGH_LOW_PAYOUTS))

    def test_win_then_lose_forfeits_the_held_prize(self):
        g = self.game(5, 9, 11)
        g.guess(HIGHER)
        self.flip(g)
        g.guess(HIGHER)                             # 9 -> 11 would win; make it lose:
        g.pending = (2, False)
        self.flip(g)
        self.assertEqual((g.get_result().payout, self.p.tokens), (0, 10 - COST))

    def test_guess_spam_during_flip_cannot_double_guess(self):
        g = self.game(5, 9, 1)
        self.assertTrue(g.guess(HIGHER))
        for _ in range(10):
            self.assertFalse(g.guess(LOWER))
            self.assertFalse(g.cash_out())
        self.flip(g)
        self.assertEqual(g.streak, 1)
        self.assertEqual(g.rng.values, [1])         # only one extra card was drawn

    def test_cannot_cash_out_before_winning(self):
        g = self.game(5)
        self.assertFalse(g.cash_out())
        self.assertEqual(self.p.tokens, 10 - COST)

    def test_leaving_mid_the_decided_guess(self):
        g = self.game(5, 9)
        g.guess(HIGHER)
        g.finish()
        g.finish()
        self.assertEqual(self.p.tokens, 10 - COST + PAY[0])

    def test_leaving_mid_flip_on_a_losing_guess_pays_nothing(self):
        g = self.game(5, 2)
        g.guess(HIGHER)
        g.finish()
        self.assertEqual(self.p.tokens, 10 - COST)

    def test_leaving_with_a_streak_cashes_it_out_once(self):
        g = self.game(5, 9, 11)
        g.guess(HIGHER)
        self.flip(g)
        g.finish()
        g.finish()
        self.assertEqual(self.p.tokens, 10 - COST + PAY[0])

    def test_leaving_before_any_guess_refunds_the_entry(self):
        g = self.game(5)
        g.finish()
        g.finish()
        self.assertEqual((self.p.tokens, self.p.lifetime_tokens_spent, self.p.lifetime_tokens_earned),
                         (10, 0, 0))

    def test_insufficient_tokens_blocks_play(self):
        broke = PlayerProfile(tokens=0, clock=clock_at())
        g = HighLowGame()
        self.assertFalse(g.can_play(broke))
        self.assertFalse(g.start(broke))
        self.assertEqual(g.phase, g.IDLE)

    def test_payouts_are_capped_and_modest(self):
        self.assertLessEqual(max(HIGH_LOW_PAYOUTS), 8)
        self.assertLessEqual(self.optimal_return(), 1.0)

    def optimal_return(self):
        """Tokens back per token spent for a player who always picks the
        likelier direction and cashes out at the best moment (exact)."""
        n, pay = HIGH_LOW_RANKS, HIGH_LOW_PAYOUTS

        def value(card, wins):               # best expected prize with `wins` held
            hold = pay[wins - 1] if wins else 0
            best = 0
            for higher in (True, False):
                total = sum(pay[wins] if wins + 1 >= len(pay) else value(c, wins + 1)
                            for c in range(1, n + 1) if (c > card if higher else c < card))
                best = max(best, total / n)
            return max(hold, best)

        return sum(value(c, 0) for c in range(1, n + 1)) / n / HIGH_LOW_COST

    def test_bad_config_rejected(self):
        with self.assertRaises(ValueError):
            HighLowGame(payouts=())
        with self.assertRaises(ValueError):
            HighLowGame(ranks=1)


class ChanceGameInterfaceTests(unittest.TestCase):
    def test_both_games_share_the_interface(self):
        for cls in (LuckyWheelGame, HighLowGame):
            g = cls()
            self.assertIsInstance(g, ChanceGame)
            for name in ("can_play", "start", "update", "draw", "get_result", "finish"):
                self.assertTrue(callable(getattr(g, name)), (cls, name))
            self.assertIsNone(g.get_result())

    def test_a_result_cannot_be_resolved_twice(self):
        p = PlayerProfile(tokens=10, clock=clock_at())
        g = LuckyWheelGame(rng=random.Random(2))
        g.start(p)
        first = g._resolve(5, "x")
        again = g._resolve(10, "y")
        self.assertIs(first, again)
        self.assertEqual(p.tokens, 9 + 5)

    def test_game_rounds_are_logged(self):
        p = PlayerProfile(tokens=10, clock=clock_at())
        g = HighLowGame(rng=SeqRng(5, 9))
        g.start(p)
        g.guess(HIGHER)
        for _ in range(60):
            g.update(DT)
        g.cash_out()
        self.assertEqual(p.history_lines(), [f"-{COST} TOKEN  HIGH-LOW", f"+{PAY[0]} TOKEN  HIGH-LOW WIN"])


# ---------------------------------------------------------------- in the arcade
class ArcadeEconomyFlowTests(TempDirTest):
    def make_game(self, day=DAY1, popup=False, **kw):
        self.clock = clock_at(day)
        g = Game(save_path=self.path, clock=self.clock, **kw)
        room = g.scenes.current
        if not popup and room.popup:
            self.run_frames(g, 3, [key(pygame.K_ESCAPE)])
        return g, room

    def run_frames(self, g, n, events=()):
        g.step(list(events), DT)
        for _ in range(n - 1):
            g.step([], DT)

    def stand_at(self, g, room, target, frames=5):
        room.player.x, room.player.y = target.zone.centerx, target.zone.bottom - 2
        self.run_frames(g, frames)

    def claim_bonus(self, g, room):
        self.run_frames(g, 5, [key(pygame.K_RETURN)])
        self.run_frames(g, 60)
        self.assertIsNone(room.popup)

    # ---- daily bonus popup
    def test_popup_appears_on_first_entry_and_claims_once(self):
        g, room = self.make_game(popup=True)
        self.assertIsNotNone(room.popup)
        self.assertEqual((room.popup.day, room.popup.reward_lines), (1, ["+5 TOKENS"]))
        self.run_frames(g, 5, [key(pygame.K_RETURN)] * 6 + [key(pygame.K_e)] * 6)   # mash
        self.run_frames(g, 60)
        self.assertEqual(g.profile.tokens, 15)
        self.assertIsNone(room.popup)
        self.assertEqual(len(room.hud.floaters), 1)              # the floating +5 TOKENS
        self.assertEqual(self.saved()["tokens"], 15)             # saved straight away
        self.assertEqual(self.saved()["daily_streak"], 1)

    def test_no_second_popup_the_same_day_even_after_restart(self):
        g, room = self.make_game(popup=True)
        self.claim_bonus(g, room)
        self.run_frames(g, 150)                                  # still none while it stays open
        self.assertIsNone(room.popup)
        g2, room2 = self.make_game(popup=True)
        self.assertIsNone(room2.popup)
        self.assertEqual(g2.profile.tokens, 15)

    def test_next_day_offers_the_next_streak_day(self):
        g, room = self.make_game(popup=True)
        self.claim_bonus(g, room)
        g2, room2 = self.make_game(DAY1 + timedelta(days=1), popup=True)
        self.assertEqual((room2.popup.day, room2.popup.reward_lines), (2, ["+6 TOKENS"]))
        self.claim_bonus(g2, room2)
        self.assertEqual(g2.profile.tokens, 21)

    def test_esc_puts_the_bonus_off_without_nagging(self):
        g, room = self.make_game(popup=True)
        self.run_frames(g, 3, [key(pygame.K_ESCAPE)])
        self.assertIsNone(room.popup)
        self.run_frames(g, 200)
        self.assertIsNone(room.popup)                            # not re-shown this session
        self.assertEqual(g.profile.tokens, 10)
        g2, room2 = self.make_game(popup=True)                   # but it is back next time
        self.assertIsNotNone(room2.popup)

    def test_popup_blocks_walking_and_interaction(self):
        g, room = self.make_game(popup=True)
        x = room.player.x
        self.run_frames(g, 30, [key(pygame.K_a)])
        self.assertEqual(room.player.x, x)

    def test_midnight_rollover_while_open_offers_the_new_bonus(self):
        g, room = self.make_game(popup=True)
        self.claim_bonus(g, room)
        self.clock.advance_days(1)
        self.run_frames(g, 80)                                   # the day check runs each second
        self.assertIsNotNone(room.popup)
        self.assertEqual(room.popup.day, 2)

    # ---- debug keys
    def test_debug_keys_do_nothing_in_normal_play(self):
        g, room = self.make_game()
        before = (g.profile.tokens, [t.id for t in g.profile.daily_tasks])
        self.run_frames(g, 3, [key(pygame.K_F5), key(pygame.K_F6), key(pygame.K_F7)])
        self.assertEqual((g.profile.tokens, [t.id for t in g.profile.daily_tasks]), before)
        self.assertEqual(self.clock.today(), DAY1)

    def test_debug_keys_in_debug_mode(self):
        g, room = self.make_game(debug=True)
        self.run_frames(g, 2, [key(pygame.K_F5)])
        self.assertEqual(g.profile.tokens, 20)
        self.assertEqual(g.profile.history_lines()[-1], "+10 TOKEN  DEBUG")
        g.profile.record_cat_petted()
        self.run_frames(g, 2, [key(pygame.K_F7)])
        self.assertTrue(all(t.progress == 0 for t in g.profile.daily_tasks))
        self.run_frames(g, 2, [key(pygame.K_F6)])
        self.assertEqual(self.clock.today(), DAY1 + timedelta(days=1))
        self.assertIsNotNone(room.popup)                         # a new day: bonus is back
        self.assertEqual(g.profile.daily_tasks_date, DAY1 + timedelta(days=1))

    # ---- board
    def test_board_opens_shows_tasks_and_claims(self):
        g, room = self.make_game()
        board = next(s for s in room.stations if isinstance(s, DailyBoard))
        self.stand_at(g, room, board)
        self.assertIs(room.nearby, board)
        self.assertEqual(room.prompt.label, "DAILY CHALLENGES")
        self.run_frames(g, 30, [key(pygame.K_e)])
        self.assertIsNotNone(room.panel)
        g.profile.add_tickets(500)                               # finish every kind of task
        for _ in range(5):
            g.profile.record_game_played("retro_racer")
            g.profile.record_cat_petted()
            for m in ("retro_racer", "space_blaster", "puzzle_drop"):
                g.profile.record_machine_visit(m)
        self.assertTrue(all(t.completed for t in g.profile.daily_tasks))
        before = g.profile.tokens
        total = sum(t.reward_tokens for t in g.profile.daily_tasks)
        for i in range(len(g.profile.daily_tasks)):
            self.run_frames(g, 2, [key(pygame.K_e)] * 4)         # mash E on this row
            self.run_frames(g, 2, [key(pygame.K_DOWN)])
        self.run_frames(g, 3)
        self.assertEqual(g.profile.tokens, before + total)
        self.assertTrue(all(t.claimed for t in g.profile.daily_tasks))
        self.run_frames(g, 3, [key(pygame.K_ESCAPE)])
        self.run_frames(g, 3)
        self.assertIsNone(room.panel)
        self.assertEqual(self.saved()["tokens"], before + total)

    def test_board_blocks_walking_while_open(self):
        g, room = self.make_game()
        room.open_task_panel()
        x = room.player.x
        self.run_frames(g, 20, [key(pygame.K_a)])
        self.assertEqual(room.player.x, x)

    def test_complete_task_shows_a_hint(self):
        g, room = self.make_game()
        g.profile.reset_daily_tasks()
        for _ in range(5):
            g.profile.record_game_played("retro_racer")
            g.profile.record_cat_petted()
            g.profile.add_tickets(60)
            for m in ("retro_racer", "space_blaster", "puzzle_drop"):
                g.profile.record_machine_visit(m)
        self.run_frames(g, 3)
        self.assertTrue(room.notice.visible)

    # ---- progress from the arcade
    def test_petting_a_cat_counts_once_per_pet(self):
        g, room = self.make_game()
        cat = room.cats.cats[0]
        from cat import CatState
        for c in room.cats:
            c.set_state(CatState.SLEEP, 999)
        cat.set_state(CatState.SIT, 999)
        room.player.x, room.player.y = cat.x - 14, cat.y
        self.run_frames(g, 3)
        self.run_frames(g, 1, [key(pygame.K_e)] * 5)             # mashing: only one pet reacts
        self.assertEqual(g.profile.cats_petted, 1)

    def test_visiting_machines_counts_distinct_ones(self):
        g, room = self.make_game()
        mgr = DailyTaskManager(pool=[{"id": "v", "description": "VISIT 3", "event": "machine_visited",
                                      "distinct": True, "target": 3, "reward": 5}], count=1)
        g.profile._tasks = mgr
        mgr.ensure_current(self.clock.today())
        machine = room.machines[0]
        for _ in range(2):                                       # the same machine twice
            self.stand_at(g, room, machine)
            self.run_frames(g, 30, [key(pygame.K_e)])
            self.assertIsNotNone(room.dialogue)
            self.run_frames(g, 3, [key(pygame.K_ESCAPE)])
        self.assertEqual(mgr.tasks[0].progress, 1)
        other = room.machines[1]
        self.stand_at(g, room, other)
        self.run_frames(g, 30, [key(pygame.K_e)])
        self.assertEqual(mgr.tasks[0].progress, 2)

    def test_playing_a_machine_progresses_play_tasks(self):
        g, room = self.make_game()
        mgr = DailyTaskManager(pool=[{"id": "p", "description": "PLAY 1", "event": "game_played",
                                      "target": 1, "reward": 5}], count=1)
        g.profile._tasks = mgr
        mgr.ensure_current(self.clock.today())
        machine = next(m for m in room.machines if m.id == "space_blaster")
        self.stand_at(g, room, machine)
        self.run_frames(g, 30, [key(pygame.K_e)])
        self.run_frames(g, 40, [key(pygame.K_RETURN)])
        self.run_frames(g, 40, [key(pygame.K_ESCAPE)])
        self.run_frames(g, 40)
        self.assertTrue(g.profile.daily_tasks[0].completed)

    # ---- lucky corner
    def lucky(self, room, cls_name):
        return next(s for s in room.stations if isinstance(s, ChanceStation)
                    and s.game_cls.__name__ == cls_name)

    def test_lucky_corner_stations_exist_and_are_interactable(self):
        g, room = self.make_game()
        for cls in ("LuckyWheelGame", "HighLowGame"):
            st = self.lucky(room, cls)
            self.assertIn(st, room.interactables)
            self.assertIn(st.footprint, room.room.solids)
        sign = next(p for p in room.room.props if p.__class__.__name__ == "LuckySign")
        self.assertNotIn(sign.footprint, room.room.solids)

    def test_playing_the_wheel_through_the_scene_charges_and_pays_once(self):
        g, room = self.make_game()
        st = self.lucky(room, "LuckyWheelGame")
        self.stand_at(g, room, st)
        self.assertIs(room.nearby, st)
        self.run_frames(g, 30, [key(pygame.K_e)])
        self.run_frames(g, 40)
        scene = g.scenes.current
        self.assertIsInstance(scene, ChanceGameScene)
        self.assertEqual(g.profile.tokens, 10)                   # entering is free
        self.run_frames(g, 1, [key(pygame.K_e)] * 8)             # mash E
        self.assertEqual(g.profile.tokens, 9)
        prize = scene.round.prize
        self.run_frames(g, int((SPIN_TIME + 3) / DT), [key(pygame.K_e)])
        self.assertEqual(g.profile.tokens, 9 + prize)
        self.assertEqual(g.profile.chance_games_played, 1)
        self.run_frames(g, 1, [key(pygame.K_ESCAPE)])
        self.run_frames(g, 60)
        self.assertIs(g.scenes.current, room)
        self.assertEqual(g.profile.tokens, 9 + prize)
        self.assertEqual(self.saved()["tokens"], 9 + prize)

    def test_mashing_after_a_result_does_not_buy_a_new_round(self):
        g, room = self.make_game()
        scene = ChanceGameScene(g, LuckyWheelGame)
        g.scenes.push(scene, fade=False)
        self.run_frames(g, 1, [key(pygame.K_e)])
        self.run_frames(g, int((SPIN_TIME + 1.2) / DT))
        self.assertEqual(scene.round.phase, scene.round.DONE)
        spent = g.profile.lifetime_tokens_spent
        self.run_frames(g, 1, [key(pygame.K_e)] * 5)             # instantly after the result
        self.assertEqual(g.profile.lifetime_tokens_spent, spent)
        self.run_frames(g, 60)
        self.run_frames(g, 1, [key(pygame.K_e)] * 5)             # a deliberate next round
        self.assertEqual(g.profile.lifetime_tokens_spent, spent + 1)

    def test_scene_blocks_play_without_tokens(self):
        self.write_save({"tokens": 0, "tickets": 3})
        g, room = self.make_game()
        scene = ChanceGameScene(g, HighLowGame)
        g.scenes.push(scene, fade=False)
        self.run_frames(g, 1, [key(pygame.K_e)] * 5)
        self.assertEqual((g.profile.tokens, scene.round.phase), (0, scene.round.IDLE))
        self.assertEqual(g.profile.tickets, 3)

    def test_closing_the_window_mid_spin_pays_once(self):
        g, room = self.make_game()
        scene = ChanceGameScene(g, LuckyWheelGame)
        g.scenes.push(scene, fade=False)
        self.run_frames(g, 1, [key(pygame.K_e)])
        self.run_frames(g, 20)
        prize = scene.round.prize
        g.step([pygame.event.Event(pygame.QUIT)], DT)
        g.quit()
        self.assertEqual(self.saved()["tokens"], 9 + prize)

    def test_leaving_high_low_before_guessing_refunds(self):
        g, room = self.make_game()
        scene = ChanceGameScene(g, HighLowGame)
        g.scenes.push(scene, fade=False)
        self.run_frames(g, 1, [key(pygame.K_e)])
        self.assertEqual(g.profile.tokens, 10 - COST)
        g.scenes.pop(fade=False)
        self.assertEqual(g.profile.tokens, 10)

    def test_tickets_are_never_touched_by_chance_games(self):
        g, room = self.make_game()
        g.profile.add_tickets(25)
        scene = ChanceGameScene(g, LuckyWheelGame)
        g.scenes.push(scene, fade=False)
        self.run_frames(g, 1, [key(pygame.K_e)])
        self.run_frames(g, int((SPIN_TIME + 3) / DT))
        self.assertEqual(g.profile.tickets, 25)

    def test_scenes_draw_in_every_phase(self):
        g, room = self.make_game()
        for cls in (LuckyWheelGame, HighLowGame):
            scene = ChanceGameScene(g, cls)
            g.scenes.push(scene, fade=False)
            self.run_frames(g, 5)
            self.run_frames(g, 1, [key(pygame.K_e)])
            self.run_frames(g, 30, [key(pygame.K_UP)])
            self.run_frames(g, 300)
            g.scenes.pop(fade=False)
        room.open_task_panel()
        self.run_frames(g, 5)


class HudTextTests(TempDirTest):
    def test_hud_says_tokens_and_tickets(self):
        g = Game(save_path=self.path, clock=clock_at())
        hud = g.scenes.current.hud
        hud.draw(g.canvas)
        self.assertEqual(hud._key[:2], (10, 0))
        self.assertTrue(hasattr(hud, "token_icon"))
        self.assertFalse(hasattr(hud, "coin_icon"))
        g.profile.add_tokens(2, "x")
        self.assertEqual(hud.floaters[-1].image.get_width() > 0, True)


if __name__ == "__main__":
    unittest.main()
