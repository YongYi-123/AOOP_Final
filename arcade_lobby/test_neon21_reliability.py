"""NEON 21 reliability: day boundaries, daily caps per profile, crashes around
settlement, repeated recovery, corrupted saved rounds, no duplicated money,
and the lifetime-earned / daily-task statistics.

The persistence model these tests pin down: every money movement and the saved
open round go to ONE profile file in ONE atomic write (profile.batch() ->
ProfileStore.save: temp file + os.replace). So the file on disk is always
either "before" (round still open, old balances) or "after" (round cleared,
balances paid); recovery settles "before" once. See the final report for the
risks that remain (no fsync, two processes on one save, a failed write).

Run headless from this folder:   python -m unittest test_neon21_reliability -v
"""
import json
import os
import random
import shutil
import tempfile
import unittest
from datetime import date, timedelta

from blackjack_testing import stacked_deck
from blackjack import BlackjackRound, Card, Outcome, new_deck
from game_clock import GameClock
from neon21 import MAX_STAKE, TICKETS, TOKENS, Neon21Table
from player_profile import PlayerProfile, ProfileStore
from profile_manager import ProfileManager
from rewards import RewardBundle, RewardService
from settings import NEON21_DAILY_TICKET_CAP as CAP

DAY1 = date(2026, 3, 10)
DAY2 = DAY1 + timedelta(days=1)


def stack(*labels):
    return stacked_deck(*labels)



WIN = ("10", "10", "9", "8")
LOSE = ("10", "10", "7", "9")
NATURAL = ("A", "9", "K", "7")


class Crash(Exception):
    """Stands in for the process dying at that exact moment."""


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")
        self.day = DAY1
        self.clock = GameClock(lambda: self.day)
        self._orig_save = ProfileStore.save

    def tearDown(self):
        ProfileStore.save = self._orig_save
        shutil.rmtree(self.dir, ignore_errors=True)

    # one profile in one file: "starting the game" = loading it again
    def start(self, tokens=None):
        store = ProfileStore(self.path, self.clock)
        p = store.load()
        store.autosave(p)
        if tokens is not None:
            p._tokens = tokens
            store.save(p)
        return p

    def crash_on_save(self, nth=1):
        """Make the nth ProfileStore.save from now raise Crash (before writing)."""
        calls = {"n": 0}
        original = self._orig_save

        def save(store, profile):
            calls["n"] += 1
            if calls["n"] == nth:
                raise Crash()
            return original(store, profile)
        ProfileStore.save = save

    def heal(self):
        ProfileStore.save = self._orig_save

    def table(self, p, labels, wager=5, currency=TOKENS):
        t = Neon21Table(p, deck_source=lambda: stack(*labels))
        t.set_wager(wager)
        t.set_currency(currency)
        return t

    def disk(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)


class MidnightTests(Base):
    def test_a_hand_dealt_before_midnight_settles_under_the_settlement_date(self):
        p = self.start(100)
        self.table(p, WIN, 10, TICKETS).deal()                    # day 1, then the game is closed
        self.day = DAY2                                           # it is past midnight now
        q = self.start()
        t = Neon21Table(q)                                        # recovery on day 2
        self.assertEqual((t.result.outcome, t.result.tickets_paid, t.result.recovered),
                         (Outcome.WIN, 10, True))
        self.assertEqual(q.neon21_tickets_today(), 10)
        self.assertEqual(self.disk()["neon21"]["date"], DAY2.isoformat())

    def test_yesterdays_cap_does_not_limit_a_hand_settled_today(self):
        p = self.start(100)
        p._neon21_date, p._neon21_tickets = DAY1.isoformat(), CAP        # day 1: cap used up
        self.table(p, WIN, 10, TICKETS).deal()
        self.day = DAY2
        q = self.start()
        t = Neon21Table(q)
        self.assertEqual((t.result.tickets_paid, t.result.capped), (10, False))
        self.assertEqual(q.neon21_tickets_today(), 10)                  # today's count, not 40

    def test_a_hand_dealt_on_a_capped_day_two_does_not_borrow_day_one_room(self):
        p = self.start(100)
        self.day = DAY2
        p._neon21_date, p._neon21_tickets = DAY2.isoformat(), CAP        # today's cap used up
        self.table(p, WIN, 10, TICKETS).deal()
        q = self.start()
        t = Neon21Table(q)
        self.assertEqual((t.result.tickets_paid, t.result.profit_tokens, t.result.capped), (0, 10, True))

    def test_cap_resets_on_the_next_calendar_day_and_survives_restarts_within_a_day(self):
        p = self.start(500)
        for _ in range(3):
            t = self.table(p, WIN, 10, TICKETS)
            t.deal()
            t.stand()
        self.assertEqual((p.neon21_tickets_today(), p.neon21_ticket_room()), (CAP, 0))
        q = self.start()                                                # same day, new run
        self.assertEqual(q.neon21_ticket_room(), 0)
        self.day = DAY2
        r = self.start()
        self.assertEqual(r.neon21_ticket_room(), CAP)
        t = self.table(r, WIN, 10, TICKETS)
        t.deal()
        t.stand()
        self.assertEqual((r.neon21_tickets_today(), t.result.capped), (10, False))
        self.assertEqual(r.tickets, 40)                                 # nothing was taken back


class MultiProfileTests(Base):
    def make(self):
        self.manager = ProfileManager(os.path.join(self.dir, "saves"), clock=self.clock)
        a, b = self.manager.create_profile("Alice"), self.manager.create_profile("Bob")
        for p in (a, b):
            p.add_tokens(200, "SETUP")
        return a, b

    def reopen(self, *profiles):
        manager = ProfileManager(os.path.join(self.dir, "saves"), clock=self.clock)
        return [manager.load_profile(p.profile_id) for p in profiles]

    def test_daily_caps_are_independent_and_persist_per_profile(self):
        a, b = self.make()
        for _ in range(3):
            t = self.table(a, WIN, 10, TICKETS)
            t.deal()
            t.stand()
        t = self.table(b, WIN, 10, TICKETS)
        t.deal()
        t.stand()
        a2, b2 = self.reopen(a, b)
        self.assertEqual((a2.neon21_tickets_today(), b2.neon21_tickets_today()), (CAP, 10))
        self.assertEqual((a2.tickets, b2.tickets), (CAP, 10))
        t = self.table(b2, WIN, 10, TICKETS)
        t.deal()
        t.stand()
        self.assertEqual((t.result.tickets_paid, t.result.capped), (10, False))   # Bob is not capped
        t = self.table(a2, WIN, 10, TICKETS)
        t.deal()
        t.stand()
        self.assertEqual((t.result.tickets_paid, t.result.capped), (0, True))     # Alice is

    def test_open_rounds_belong_to_their_profiles_across_a_restart(self):
        a, b = self.make()
        ta, tb = self.table(a, WIN, 10, TICKETS), self.table(b, LOSE, 2, TOKENS)
        ta.deal()
        tb.deal()
        a2, b2 = self.reopen(a, b)
        ra, rb = Neon21Table(a2), Neon21Table(b2)
        self.assertEqual((ra.result.outcome, rb.result.outcome), (Outcome.WIN, Outcome.LOSE))
        self.assertEqual((a2.tokens, a2.tickets, b2.tokens, b2.tickets), (210, 10, 208, 0))


class CrashTests(Base):
    def control(self, labels, wager, currency):
        """What an uninterrupted round pays: the oracle for the crash cases."""
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")
        p = self.start(100)
        t = self.table(p, labels, wager, currency)
        t.deal()
        t.stand()
        out = (p.tokens, p.tickets, p.neon21_tickets_today())
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")
        return out

    def test_crash_while_writing_the_settlement_pays_once_on_recovery(self):
        expected = self.control(WIN, 10, TICKETS)
        p = self.start(100)
        t = self.table(p, WIN, 10, TICKETS)
        t.deal()
        self.crash_on_save(1)                                     # the one write that settles
        with self.assertRaises(Crash):
            t.stand()
        self.heal()
        q = self.start()                                          # new process: disk is "before"
        self.assertEqual((q.tokens, q.tickets), (90, 0))
        self.assertIsNotNone(q.neon21_pending)
        t2 = Neon21Table(q)
        self.assertEqual((q.tokens, q.tickets, q.neon21_tickets_today()), expected)
        self.assertEqual(self.disk()["tokens"], expected[0])
        self.assertIsNone(q.neon21_pending)

    def test_crash_right_after_settlement_does_not_pay_again(self):
        p = self.start(100)
        t = self.table(p, WIN, 10, TICKETS)
        t.deal()
        t.stand()
        paid = (p.tokens, p.tickets)
        q = self.start()                                          # killed before the scene closed
        t2 = Neon21Table(q)
        self.assertIsNone(t2.result)
        self.assertEqual((q.tokens, q.tickets), paid)
        self.assertEqual(self.disk()["neon21"].get("pending"), None)

    def test_crash_while_dealing_loses_no_stake(self):
        p = self.start(100)
        t = self.table(p, WIN, 10)
        self.crash_on_save(1)
        with self.assertRaises(Crash):
            t.deal()
        self.heal()
        q = self.start()
        self.assertEqual((q.tokens, q.neon21_pending), (100, None))     # nothing taken, nothing open

    def test_crash_after_the_deal_is_saved_settles_the_open_hand_once(self):
        p = self.start(100)
        self.table(p, LOSE, 10).deal()                            # saved: 90 and an open hand
        q = self.start()
        self.assertEqual(q.tokens, 90)
        t = Neon21Table(q)
        self.assertEqual((t.result.outcome, q.tokens), (Outcome.LOSE, 90))

    def test_crash_while_recovering_then_recovering_again_pays_once(self):
        expected = self.control(WIN, 10, TICKETS)
        p = self.start(100)
        self.table(p, WIN, 10, TICKETS).deal()
        q = self.start()
        self.crash_on_save(1)
        with self.assertRaises(Crash):
            Neon21Table(q)                                        # dies while settling the saved hand
        self.heal()
        r = self.start()
        Neon21Table(r)
        self.assertEqual((r.tokens, r.tickets, r.neon21_tickets_today()), expected)
        self.assertEqual(self.start().tokens, expected[0])

    def test_natural_crash_between_the_deal_save_and_the_settlement_save(self):
        p = self.start(100)
        t = self.table(p, NATURAL, 10)
        original = self._orig_save
        calls = {"n": 0}

        def save(store, profile):
            calls["n"] += 1
            if calls["n"] == 2:                                   # deal save ok, settlement save dies
                raise Crash()
            return original(store, profile)
        ProfileStore.save = save
        with self.assertRaises(Crash):
            t.deal()
        self.heal()
        q = self.start()
        self.assertEqual(q.tokens, 90)
        self.assertIsNotNone(q.neon21_pending)
        t2 = Neon21Table(q)
        self.assertEqual((t2.result.outcome, q.tokens), (Outcome.BLACKJACK, 90 + 10 + 15))

    def test_a_failed_disk_write_cannot_duplicate_money_after_a_restart(self):
        """The write fails quietly (disk full): memory is ahead of the file, and the
        next run settles from the file - once. Nothing is paid twice."""
        p = self.start(100)
        t = self.table(p, WIN, 10)
        t.deal()
        ProfileStore.save = lambda store, profile: False         # ProfileStore reports failure, raises nothing
        t.stand()
        self.assertEqual(p.tokens, 110)                           # what the player saw
        self.heal()
        q = self.start()                                          # restart: only the file counts
        Neon21Table(q)
        self.assertEqual(q.tokens, 110)

    def test_repeated_recovery_attempts_pay_once(self):
        p = self.start(100)
        self.table(p, WIN, 10, TICKETS).deal()
        results = []
        for _ in range(5):
            q = self.start()
            results.append(Neon21Table(q).result)
        self.assertIsNotNone(results[0])
        self.assertEqual(results[1:], [None] * 4)
        q = self.start()
        self.assertEqual((q.tokens, q.tickets, q.neon21_tickets_today()), (100, 10, 10))
        t = Neon21Table(q)                                        # also twice on one live profile
        u = Neon21Table(q)
        self.assertEqual((t.result, u.result), (None, None))
        self.assertEqual((q.tokens, q.tickets), (100, 10))


class CorruptedPendingTests(Base):
    def run_junk(self, pending):
        p = PlayerProfile(tokens=50, clock=self.clock)
        p.set_neon21_pending(pending)
        t = Neon21Table(p)                                        # must never raise
        self.assertIsNone(p.neon21_pending, pending)
        self.assertEqual(p.tickets, 0)
        self.assertEqual(p.lifetime_tickets_earned, 0)
        return p, t

    def test_unreadable_rounds_are_cleared_and_a_sane_stake_is_returned(self):
        good = BlackjackRound(5, deck=stack(*WIN)).to_dict()          # a legal, complete saved round
        for pending, refund in (
                ({"currency": "tokens", "round": {"bet": 5, "deck": "junk"}}, 5),
                ({"currency": "tokens", "round": {"bet": 5}}, 5),
                ({"currency": "tickets", "round": {**good, "bet": 5, "outcome": "jackpot"}}, 5),
                ({"currency": "tokens", "round": {**good, "player": [[99, "S"], [2, "S"]]}}, 5),
                ({"currency": "tokens", "round": {**good, "dealer": [[2, "X"], [3, "S"]]}}, 5),
                ({"currency": "tokens", "round": {**good, "player": [[2, "S"]]}}, 5),
                ({"currency": "tokens", "round": {**good, "deck": [[1]]}}, 5),
                ({"currency": "tokens", "round": {**good, "deck": good["deck"] + [[2, "H"]]}}, 5),      # a 53rd / duplicate card
                ({"currency": "tokens", "round": {**good, "deck": good["deck"][1:]}}, 5),               # a card missing
                ({"currency": "tokens", "round": {**good, "deck": good["deck"][:-1] + [good["player"][0]]}}, 5),
                ({"currency": "tokens", "round": {**good, "deck": []}}, 5),
                ({"currency": "tokens", "round": {**good, "bet": MAX_STAKE}, "extra": 1}, None),
        ):
            p, t = self.run_junk(pending)
            if refund is not None:
                self.assertEqual(p.tokens, 55, pending)
                self.assertIn("STAKE RETURNED", t.notice)

    def test_nonsense_bets_are_never_refunded(self):
        for bet in (0, -5, True, 2.5, "5", None, 10 ** 9, MAX_STAKE + 1):
            p, t = self.run_junk({"currency": "tokens", "round": {**BlackjackRound(5, deck=stack(*WIN)).to_dict(), "bet": bet}})
            self.assertEqual(p.tokens, 50, bet)

    def test_non_dict_rounds_and_pending_values(self):
        for pending in ({"round": 7}, {"round": None}, {"round": []}, {"round": "x"}, {}):
            p = PlayerProfile(tokens=50, clock=self.clock)
            p._neon21_pending = pending                           # as if loaded from a hand-edited file
            Neon21Table(p)
            self.assertEqual(p.tokens, 50)
            self.assertIsNone(p.neon21_pending)

    def test_a_non_dict_pending_in_the_file_is_dropped_on_load(self):
        for junk in ("open", 5, ["round"], None):
            q = PlayerProfile.from_dict({"tokens": 7, "neon21": {"pending": junk}}, clock=self.clock)
            self.assertEqual((q.tokens, q.neon21_pending), (7, None))

    def test_a_tampered_settled_round_pays_at_most_its_own_stake_bounds(self):
        round_ = BlackjackRound(5, deck=stack(*NATURAL)).to_dict()          # settled: outcome "blackjack"
        self.assertEqual(round_["outcome"], "blackjack")
        p = PlayerProfile(tokens=50, clock=self.clock)
        p.set_neon21_pending({"currency": "tickets", "round": round_})
        t = Neon21Table(p)
        self.assertEqual((t.result.outcome, p.tokens, p.tickets), (Outcome.BLACKJACK, 50 + 5, 7))
        self.assertEqual(p.lifetime_tickets_earned, 0)

    def test_corrupt_data_in_the_file_recovers_through_a_real_restart(self):
        p = self.start(100)
        self.table(p, WIN, 5).deal()
        data = self.disk()
        data["neon21"]["pending"]["round"]["deck"] = "garbage"
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        q = self.start()
        t = Neon21Table(q)
        self.assertEqual((q.tokens, q.neon21_pending), (100, None))
        self.assertEqual(self.start().tokens, 100)


class NoDuplicateMoneyTests(Base):
    def test_random_play_with_random_crashes_conserves_every_token_and_ticket(self):
        rng = random.Random(2026)
        p = self.start(300)
        tokens0, expected_tokens, expected_tickets = 300, 300, 0
        settled = 0
        for i in range(160):
            t = Neon21Table(p, deck_source=lambda: new_deck(rng))      # a real shuffled deck every round
            if t.result is not None:                              # a recovered round from a past crash
                expected_tokens += t.result.net_tokens
                expected_tickets += t.result.tickets_paid
                settled += 1
            if not p.can_afford_tokens(10):
                p._tokens += 100
                expected_tokens += 100
            t.set_wager(rng.choice((1, 2, 5, 10)))
            t.set_currency(rng.choice((TOKENS, TICKETS)))
            if not t.deal():
                continue
            crash = rng.random() < 0.3
            while t.phase == t.PLAYING:
                r = rng.random()
                if crash and r < 0.4:
                    break
                if r < 0.15 and t.can_double:
                    t.double()
                elif r < 0.6:
                    t.hit()
                else:
                    t.stand()
            if t.phase == t.DONE:
                expected_tokens += t.result.net_tokens
                expected_tickets += t.result.tickets_paid
                settled += 1
                if rng.random() < 0.3:                            # a restart after settling: no change
                    p = self.start()
            elif crash:
                p = self.start()                                  # killed mid-hand; recovery next loop
            if p.neon21_tickets_today() > CAP:
                self.fail("daily cap exceeded")
            if p.neon21_pending is None:                              # nothing in flight: books must balance
                self.assertEqual((p.tokens, p.tickets), (expected_tokens, expected_tickets), f"round {i}")
        p = self.start()
        t = Neon21Table(p)
        if t.result is not None:
            expected_tokens += t.result.net_tokens
            expected_tickets += t.result.tickets_paid
        self.assertEqual((p.tokens, p.tickets), (expected_tokens, expected_tickets))
        self.assertEqual(p.lifetime_tickets_earned, 0)
        self.assertGreater(settled, 40)

    def test_stake_refund_and_payout_each_happen_once(self):
        p = self.start(100)
        t = self.table(p, WIN, 10)
        t.deal()
        t.stand()
        t.finish()
        t._settle()
        t.next_round()
        reasons = [h["reason"] for h in p.history]
        self.assertEqual(reasons.count("NEON 21 STAKE"), 1)
        self.assertEqual(reasons.count("NEON 21 STAKE REFUND"), 1)
        self.assertEqual(reasons.count("NEON 21 WIN"), 1)
        self.assertEqual(p.tokens, 110)


class StatisticsTests(Base):
    def test_neon21_tickets_never_touch_lifetime_earned_or_tasks(self):
        p = self.start(300)
        p.reset_daily_tasks()
        tasks = [(t.id, t.progress) for t in p.daily_tasks]
        for _ in range(3):
            t = self.table(p, WIN, 10, TICKETS)
            t.deal()
            t.stand()
        self.assertEqual((p.tickets, p.lifetime_tickets_earned), (30, 0))
        self.assertEqual([(t.id, t.progress) for t in p.daily_tasks], tasks)
        q = self.start()
        self.assertEqual((q.tickets, q.lifetime_tickets_earned), (30, 0))

    def test_real_ticket_rewards_still_count_and_stack_with_neon21_tickets(self):
        p = self.start(100)
        t = self.table(p, WIN, 10, TICKETS)
        t.deal()
        t.stand()
        p.add_tickets(5)
        RewardService.grant(p, RewardBundle(tickets=7, reason="TEST"))
        self.assertEqual((p.tickets, p.lifetime_tickets_earned), (22, 12))
        q = self.start()
        self.assertEqual((q.tickets, q.lifetime_tickets_earned), (22, 12))

    def test_earn_tickets_task_still_advances_from_real_rewards(self):
        p = self.start(100)
        spec = {"id": "earn_tickets", "description": "EARN 50 TICKETS", "event": "tickets_earned",
                "target": 50, "reward": 8}
        from daily_tasks import DailyTaskManager
        p._tasks = DailyTaskManager(pool=(spec,), count=1)
        p._tasks.ensure_current(DAY1, random.Random(1))
        t = self.table(p, WIN, 10, TICKETS)
        t.deal()
        t.stand()
        self.assertEqual(p.daily_tasks[0].progress, 0)
        p.add_tickets(20)
        self.assertEqual(p.daily_tasks[0].progress, 20)

    def test_a_normal_reload_changes_no_statistics_and_rewrites_nothing(self):
        p = self.start(100)
        p.add_tickets(12)
        t = self.table(p, WIN, 10, TICKETS)
        t.deal()
        t.stand()
        with open(self.path, "rb") as f:
            before = f.read()
        stats = (p.tokens, p.tickets, p.lifetime_tickets_earned, p.lifetime_tokens_earned,
                 p.lifetime_tokens_spent, p.chance_games_played, p.total_games_played)
        for _ in range(3):
            q = ProfileStore(self.path, self.clock).load()
            self.assertEqual((q.tokens, q.tickets, q.lifetime_tickets_earned, q.lifetime_tokens_earned,
                              q.lifetime_tokens_spent, q.chance_games_played, q.total_games_played), stats)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)                          # load() did not rewrite the file
        self.assertEqual(PlayerProfile.from_dict(p.to_dict(), clock=self.clock).to_dict(), p.to_dict())

    def test_old_saves_remain_compatible(self):
        # a save from before NEON 21: no neon21 block; lifetime recorded
        old = {"version": 2, "tokens": 9, "tickets": 40, "lifetime_tickets_earned": 90,
               "transaction_history": [{"date": "2026-03-01", "delta": 5, "reason": "DAILY LOGIN"}]}
        p = PlayerProfile.from_dict(old, clock=self.clock)
        self.assertEqual((p.tokens, p.tickets, p.lifetime_tickets_earned, p.neon21_pending,
                          p.neon21_tickets_today()), (9, 40, 90, None, 0))
        self.assertEqual(p.history[0]["reason"], "DAILY LOGIN")
        # an old save with no lifetime field at all: assume the balance was earned (as before)
        p = PlayerProfile.from_dict({"tokens": 1, "tickets": 33}, clock=self.clock)
        self.assertEqual(p.lifetime_tickets_earned, 33)
        # a version-1 save keeps its coins -> tokens migration
        p = PlayerProfile.from_dict({"version": 1, "coins": 8, "tickets": 40}, clock=self.clock)
        self.assertEqual((p.tokens, p.lifetime_tickets_earned), (8, 40))

    def test_a_stored_lifetime_total_below_the_balance_is_kept_not_inflated(self):
        """The case the old max() clamp used to rewrite: tickets won at NEON 21
        are in the balance but were never 'earned'. The stored total wins."""
        p = PlayerProfile.from_dict({"tokens": 1, "tickets": 30, "lifetime_tickets_earned": 0,
                                     "neon21": {"date": DAY1.isoformat(), "tickets": 30}}, clock=self.clock)
        self.assertEqual(p.lifetime_tickets_earned, 0)

    def test_invalid_stored_lifetime_values_fall_back_safely(self):
        for junk in (-4, "7", None, True, 2.5):
            p = PlayerProfile.from_dict({"tickets": 12, "lifetime_tickets_earned": junk}, clock=self.clock)
            self.assertEqual(p.lifetime_tickets_earned, 12, junk)


if __name__ == "__main__":
    unittest.main()
