"""Token / Ticket accounting for NEON 21 (neon21.py + the profile's NEON 21 hooks).

Run headless from this folder:   python -m unittest test_neon21_economy -v
"""
import json
import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta

from blackjack_testing import stacked_deck
from blackjack import BlackjackRound, Card, Outcome
from game_clock import GameClock
from neon21 import TICKETS, TOKENS, Neon21Table
from player_profile import PlayerProfile, ProfileStore
from settings import NEON21_DAILY_TICKET_CAP, NEON21_DEFAULT_WAGER, NEON21_WAGERS

DAY1 = date(2026, 3, 10)


def stack(*labels):
    return stacked_deck(*labels)



# deal order: player, dealer, player, dealer, then draws
WIN = ("10", "10", "9", "8")                 # stand: 19 vs 18
LOSE = ("10", "10", "7", "9")                # stand: 17 vs 19
PUSH = ("10", "10", "8", "8")
NATURAL = ("A", "9", "K", "7")
DEALER_NATURAL = ("9", "A", "7", "K")
DOUBLE_WIN = ("5", "10", "6", "7", "10")      # 11 + 10 = 21 vs 17
DOUBLE_LOSE = ("5", "10", "6", "10", "2")     # 13 vs 20


def table(profile, labels, **kw):
    return Neon21Table(profile, deck_source=lambda: stack(*labels), **kw)


def play(profile, labels, wager=2, currency=TOKENS, action="stand"):
    t = table(profile, labels)
    t.set_wager(wager)
    t.set_currency(currency)
    assert t.deal()
    if t.phase == t.PLAYING:
        getattr(t, action)()
    return t


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")
        self.clock = GameClock(lambda: DAY1)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def profile(self, tokens=20, tickets=0, **kw):
        return PlayerProfile(tokens=tokens, tickets=tickets, clock=self.clock, **kw)

    def stored(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def stored_profile(self):
        store = ProfileStore(self.path, self.clock)
        p = store.load()
        store.autosave(p)
        return p

    def autosaved(self, tokens=20, tickets=0):
        store = ProfileStore(self.path, self.clock)
        p = self.profile(tokens, tickets)
        store.save(p)
        store.autosave(p)
        return p


class TokenAccountingTests(Base):
    def test_wager_presets_and_default(self):
        self.assertEqual(NEON21_WAGERS, (1, 2, 5, 10))
        self.assertEqual(NEON21_DEFAULT_WAGER, 2)
        t = Neon21Table(self.profile())
        self.assertEqual((t.wager, t.currency), (2, TOKENS))

    def test_deal_charges_the_wager_once(self):
        p = self.profile(20)
        t = table(p, WIN)
        t.set_wager(5)
        self.assertTrue(t.deal())
        self.assertEqual(p.tokens, 15)
        self.assertFalse(t.deal())                      # repeated key: no second charge
        self.assertEqual(p.tokens, 15)

    def test_win_pays_even_money_in_tokens(self):
        p = self.profile(20)
        t = play(p, WIN, 5)
        self.assertEqual((t.result.outcome, p.tokens), (Outcome.WIN, 25))
        self.assertEqual((t.result.stake_returned, t.result.profit_tokens), (5, 5))

    def test_loss_keeps_the_stake(self):
        p = self.profile(20)
        play(p, LOSE, 5)
        self.assertEqual(p.tokens, 15)

    def test_push_returns_stake_and_adds_nothing(self):
        p = self.profile(20)
        t = play(p, PUSH, 5)
        self.assertEqual((p.tokens, t.result.profit, t.result.net_tokens), (20, 0, 0))
        self.assertEqual(p.lifetime_tokens_spent, 0)    # the refund undoes the spend

    def test_natural_pays_three_to_two_rounded_down(self):
        for wager, profit in ((1, 1), (2, 3), (5, 7), (10, 15)):
            p = self.profile(20)
            t = play(p, NATURAL, wager)
            self.assertEqual(t.result.outcome, Outcome.BLACKJACK)
            self.assertEqual(p.tokens, 20 + profit, wager)

    def test_dealer_natural_loses_before_player_acts(self):
        p = self.profile(20)
        t = table(p, DEALER_NATURAL)
        t.deal()
        self.assertEqual((t.phase, t.result.outcome, p.tokens), (t.DONE, Outcome.LOSE, 18))
        self.assertFalse(t.hit())

    def test_insufficient_tokens_blocks_the_deal(self):
        p = self.profile(1)
        t = table(p, WIN)
        t.set_wager(2)
        self.assertFalse(t.can_deal)
        self.assertFalse(t.deal())
        self.assertEqual((p.tokens, t.phase), (1, t.IDLE))
        self.assertEqual(t.affordable_wagers(), [1])

    def test_invalid_wagers_rejected(self):
        t = Neon21Table(self.profile())
        for bad in (0, -2, 3, 100, "5", None):
            self.assertFalse(t.set_wager(bad))
        self.assertEqual(t.wager, 2)

    def test_double_down_wins_and_loses_with_both_stakes(self):
        p = self.profile(20)
        t = table(p, DOUBLE_WIN)
        t.set_wager(5)
        t.deal()
        self.assertTrue(t.double())
        self.assertEqual((t.result.stake, t.result.outcome), (10, Outcome.WIN))
        self.assertEqual(p.tokens, 30)                  # 20 - 10 + 20
        p = self.profile(20)
        t = table(p, DOUBLE_LOSE)
        t.set_wager(5)
        t.deal()
        t.double()
        self.assertEqual(p.tokens, 10)

    def test_double_needs_enough_tokens_and_charges_nothing_when_refused(self):
        p = self.profile(7)
        t = table(p, DOUBLE_WIN)
        t.set_wager(5)
        t.deal()                                        # 2 left, needs 5
        self.assertFalse(t.double())
        self.assertEqual((p.tokens, t.phase, t.round.bet), (2, t.PLAYING, 5))
        t.stand()

    def test_double_only_once_and_only_first_two_cards(self):
        p = self.profile(40)
        t = table(p, ("2", "10", "3", "7", "2", "2", "2"))
        t.deal()
        t.hit()
        self.assertFalse(t.double())
        self.assertEqual(p.tokens, 38)

    def test_double_bust_pays_nothing(self):
        p = self.profile(20)
        t = table(p, ("10", "10", "6", "7", "K"))
        t.deal()
        t.double()
        self.assertEqual((t.result.outcome, p.tokens), (Outcome.BUST, 16))

    def test_no_duplicate_settlement(self):
        p = self.profile(20)
        t = play(p, WIN, 5)
        tokens = p.tokens
        for _ in range(5):
            t.stand()
            t.hit()
            t.finish()
            t._settle()
        self.assertEqual(p.tokens, tokens)
        self.assertIsNone(p.neon21_pending)

    def test_next_round_requires_a_settled_round(self):
        p = self.profile(20)
        t = table(p, WIN)
        self.assertFalse(t.next_round())
        t.deal()
        self.assertFalse(t.next_round())
        t.stand()
        self.assertTrue(t.next_round())
        self.assertEqual(t.phase, t.IDLE)


class TicketRewardTests(Base):
    def test_ticket_mode_pays_profit_in_tickets_and_stake_in_tokens(self):
        p = self.profile(20)
        t = play(p, WIN, 5, TICKETS)
        self.assertEqual((p.tokens, p.tickets), (20, 5))     # stake back, profit as tickets
        self.assertEqual((t.result.tickets_paid, t.result.capped), (5, False))

    def test_ticket_winnings_are_not_earned_tickets(self):
        p = self.profile(20)
        self.assertEqual(p.lifetime_tickets_earned, 0)
        play(p, WIN, 10, TICKETS)
        self.assertEqual(p.tickets, 10)
        self.assertEqual(p.lifetime_tickets_earned, 0)
        self.assertEqual(p.neon21_tickets_today(), 10)

    def test_ticket_winnings_do_not_advance_the_earn_tickets_task(self):
        p = self.profile(20)
        p.reset_daily_tasks()
        before = [(t.id, t.progress) for t in p.daily_tasks]
        play(p, WIN, 10, TICKETS)
        self.assertEqual([(t.id, t.progress) for t in p.daily_tasks], before)

    def test_normal_add_tickets_still_counts_as_earned(self):
        p = self.profile(20)
        p.add_tickets(5)
        self.assertEqual(p.lifetime_tickets_earned, 5)

    def test_push_and_loss_in_ticket_mode(self):
        p = self.profile(20)
        play(p, PUSH, 5, TICKETS)
        self.assertEqual((p.tokens, p.tickets), (20, 0))
        play(p, LOSE, 5, TICKETS)
        self.assertEqual((p.tokens, p.tickets), (15, 0))

    def test_natural_in_ticket_mode(self):
        p = self.profile(20)
        play(p, NATURAL, 5, TICKETS)
        self.assertEqual((p.tokens, p.tickets), (20, 7))

    def test_double_win_in_ticket_mode(self):
        p = self.profile(20)
        t = table(p, DOUBLE_WIN)
        t.set_wager(5)
        t.set_currency(TICKETS)
        t.deal()
        t.double()
        self.assertEqual((p.tokens, p.tickets), (20, 10))

    def test_cap_boundaries(self):
        cap = NEON21_DAILY_TICKET_CAP
        p = self.profile(1000)
        p._neon21_date = DAY1.isoformat()
        p._neon21_tickets = cap - 10                     # exactly enough room for a 10 win
        t = play(p, WIN, 10, TICKETS)
        self.assertEqual((p.neon21_tickets_today(), p.neon21_ticket_room()), (cap, 0))
        self.assertFalse(t.result.capped)
        self.assertEqual(p.tickets, 10)
        t = play(p, WIN, 10, TICKETS)                    # cap reached: all profit in tokens
        self.assertTrue(t.result.capped)
        self.assertEqual((t.result.tickets_paid, t.result.profit_tokens), (0, 10))
        self.assertEqual(p.tickets, 10)
        self.assertEqual(p.neon21_tickets_today(), cap)

    def test_partial_cap_splits_profit_explicitly(self):
        p = self.profile(1000)
        p._neon21_date = DAY1.isoformat()
        p._neon21_tickets = NEON21_DAILY_TICKET_CAP - 4
        before = p.tokens
        t = play(p, WIN, 10, TICKETS)
        r = t.result
        self.assertEqual((r.tickets_paid, r.profit_tokens, r.capped), (4, 6, True))
        self.assertEqual((p.tickets, p.tokens), (4, before + 6))

    def test_one_below_the_cap(self):
        p = self.profile(1000)
        p._neon21_date = DAY1.isoformat()
        p._neon21_tickets = NEON21_DAILY_TICKET_CAP - 1
        t = play(p, WIN, 2, TICKETS)
        self.assertEqual((t.result.tickets_paid, t.result.profit_tokens), (1, 1))

    def test_cap_resets_next_day(self):
        p = self.profile(1000)
        p._neon21_date = DAY1.isoformat()
        p._neon21_tickets = NEON21_DAILY_TICKET_CAP
        self.assertEqual(p.neon21_ticket_room(), 0)
        self.clock = GameClock(lambda: DAY1 + timedelta(days=1))
        p.clock = self.clock
        self.assertEqual(p.neon21_ticket_room(), NEON21_DAILY_TICKET_CAP)

    def test_award_beyond_cap_is_refused(self):
        p = self.profile()
        self.assertFalse(p.award_neon21_tickets(NEON21_DAILY_TICKET_CAP + 1))
        self.assertEqual(p.tickets, 0)
        self.assertTrue(p.award_neon21_tickets(NEON21_DAILY_TICKET_CAP))
        self.assertFalse(p.award_neon21_tickets(1))

    def test_currency_is_locked_once_the_round_starts(self):
        p = self.profile(20)
        t = table(p, WIN)
        t.set_currency(TICKETS)
        t.deal()
        self.assertFalse(t.set_currency(TOKENS))
        self.assertFalse(t.toggle_currency())
        self.assertFalse(t.set_wager(10))
        self.assertEqual(t.currency, TICKETS)
        t.stand()
        self.assertEqual(p.tickets, 2)
        self.assertTrue(t.toggle_currency())            # free again between rounds

    def test_ticket_stake_is_never_charged(self):
        p = self.profile(20, tickets=50)
        play(p, LOSE, 5, TICKETS)
        self.assertEqual(p.tickets, 50)


class ProfileOwnershipTests(Base):
    def test_two_profiles_stay_separate(self):
        a, b = self.profile(20), self.profile(20)
        ta, tb = table(a, WIN), table(b, LOSE)
        ta.set_currency(TICKETS)
        ta.set_wager(5)
        tb.set_wager(10)
        ta.deal()
        tb.deal()
        ta.stand()
        tb.stand()
        self.assertEqual((a.tokens, a.tickets, a.neon21_tickets_today()), (20, 5, 5))
        self.assertEqual((b.tokens, b.tickets, b.neon21_tickets_today()), (10, 0, 0))

    def test_daily_cap_is_per_profile(self):
        a, b = self.profile(100), self.profile(100)
        a._neon21_date = DAY1.isoformat()
        a._neon21_tickets = NEON21_DAILY_TICKET_CAP
        play(a, WIN, 5, TICKETS)
        t = play(b, WIN, 5, TICKETS)
        self.assertEqual((a.tickets, b.tickets), (0, 5))
        self.assertFalse(t.result.capped)


class SaveRestartTests(Base):
    def test_balances_and_cap_survive_a_restart(self):
        p = self.autosaved(20)
        play(p, WIN, 10, TICKETS)
        q = self.stored_profile()
        self.assertEqual((q.tokens, q.tickets, q.neon21_tickets_today()), (20, 10, 10))
        self.assertEqual(q.lifetime_tickets_earned, 0)
        self.assertIsNone(q.neon21_pending)
        play(q, WIN, 10, TICKETS)                       # keeps counting from 10
        self.assertEqual(self.stored_profile().neon21_tickets_today(), 20)

    def test_cap_does_not_reset_by_restarting_the_same_day(self):
        p = self.autosaved(500)
        for _ in range(3):
            play(p, WIN, 10, TICKETS)
        q = self.stored_profile()
        self.assertEqual(q.neon21_ticket_room(), 0)
        t = play(q, WIN, 10, TICKETS)
        self.assertEqual((t.result.tickets_paid, t.result.capped), (0, True))

    def test_old_saves_without_neon21_load_cleanly(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"version": 2, "tokens": 7, "tickets": 3, "transaction_history":
                       [{"date": "2026-03-01", "delta": 5, "reason": "DAILY LOGIN"}]}, f)
        p = self.stored_profile()
        self.assertEqual((p.tokens, p.tickets, p.neon21_tickets_today(), p.neon21_pending),
                         (7, 3, 0, None))
        self.assertEqual(p.history[0]["reason"], "DAILY LOGIN")

    def test_malformed_neon21_block_is_ignored(self):
        for junk in ("x", 5, {"tickets": -3, "date": 4, "pending": "no"}, {"tickets": True}):
            q = PlayerProfile.from_dict({"tokens": 5, "neon21": junk}, clock=self.clock)
            self.assertEqual((q.neon21_tickets_today(), q.neon21_pending, q.tokens), (0, None, 5))

    def test_history_records_stake_and_win(self):
        p = self.profile(20)
        play(p, WIN, 5)
        reasons = [h["reason"] for h in p.history]
        self.assertIn("NEON 21 STAKE", reasons)
        self.assertIn("NEON 21 WIN", reasons)


class MidRoundExitTests(Base):
    def test_finish_stands_and_settles_once(self):
        p = self.profile(20)
        t = table(p, WIN)
        t.set_wager(5)
        t.deal()
        t.finish()
        t.finish()
        self.assertEqual((t.result.outcome, p.tokens), (Outcome.WIN, 25))
        self.assertIsNone(p.neon21_pending)

    def test_finish_never_refunds_a_losing_hand(self):
        p = self.profile(20)
        t = table(p, ("10", "10", "6", "9", "K"))        # 16 vs 19
        t.set_wager(5)
        t.deal()
        t.finish()
        self.assertEqual((t.result.outcome, p.tokens), (Outcome.LOSE, 15))

    def test_finish_before_any_deal_charges_nothing(self):
        p = self.profile(20)
        t = Neon21Table(p)
        self.assertIsNone(t.finish())
        self.assertEqual(p.tokens, 20)

    def test_open_round_is_saved_immediately(self):
        p = self.autosaved(20)
        t = table(p, WIN)
        t.set_wager(5)
        t.deal()
        saved = self.stored()
        self.assertEqual(saved["tokens"], 15)
        self.assertEqual(saved["neon21"]["pending"]["currency"], TOKENS)
        self.assertEqual(saved["neon21"]["pending"]["round"]["bet"], 5)

    def test_force_exit_cannot_reroll_a_committed_wager(self):
        """Kill the game mid-round, reopen: the SAME deck settles the hand."""
        p = self.autosaved(20)
        t = table(p, LOSE)                               # a hand that would lose
        t.set_wager(5)
        t.deal()
        # process dies here - nothing calls finish(). Reopen from disk:
        q = self.stored_profile()
        self.assertEqual(q.tokens, 15)
        self.assertIsNotNone(q.neon21_pending)
        fresh = Neon21Table(q, deck_source=lambda: stack(*WIN))   # a "lucky" new shuffle must not matter
        self.assertEqual(fresh.phase, fresh.DONE)
        self.assertEqual(fresh.result.outcome, Outcome.LOSE)
        self.assertTrue(fresh.result.recovered)
        self.assertEqual(q.tokens, 15)
        self.assertIsNone(q.neon21_pending)
        self.assertEqual(self.stored_profile().tokens, 15)
        self.assertEqual(fresh.notice, "UNFINISHED ROUND SETTLED")

    def test_recovered_win_pays_exactly_once_with_the_chosen_currency(self):
        p = self.autosaved(20)
        t = table(p, WIN)
        t.set_wager(10)
        t.set_currency(TICKETS)
        t.deal()
        q = self.stored_profile()
        a = Neon21Table(q)
        b = Neon21Table(q)                               # opened twice: nothing left to settle
        self.assertEqual((q.tokens, q.tickets), (20, 10))
        self.assertTrue(a.result.recovered)
        self.assertIsNone(b.result)
        self.assertEqual((self.stored_profile().tokens, self.stored_profile().tickets), (20, 10))

    def test_cannot_deal_while_a_round_is_unsettled_on_disk(self):
        p = self.profile(20)
        t = table(p, WIN)
        t.deal()
        other = Neon21Table.__new__(Neon21Table)         # a table that skipped recovery
        other.__dict__.update(t.__dict__)
        other.phase = other.IDLE
        self.assertFalse(other.can_deal)                 # pending round still blocks it

    def test_recovered_double_down_round_keeps_its_doubled_stake(self):
        p = self.autosaved(20)
        t = table(p, DOUBLE_WIN)
        t.set_wager(5)
        t.deal()
        t.double()                                       # settles at once
        self.assertEqual(p.tokens, 30)
        # and a double that is saved mid-way (dealer not played) is impossible:
        self.assertIsNone(self.stored_profile().neon21_pending)

    def test_unreadable_saved_round_returns_the_stake(self):
        p = self.profile(20)
        p.set_neon21_pending({"currency": "tokens", "round": {"bet": 5, "deck": "junk"}})
        t = Neon21Table(p)
        self.assertEqual((p.tokens, p.neon21_pending), (25, None))
        self.assertIn("STAKE RETURNED", t.notice)

    def test_garbage_pending_with_no_bet_is_cleared_without_payment(self):
        p = self.profile(20)
        p.set_neon21_pending({"round": 7})
        Neon21Table(p)
        self.assertEqual((p.tokens, p.neon21_pending), (20, None))

    def test_unknown_saved_currency_falls_back_to_tokens(self):
        p = self.autosaved(20)
        t = table(p, WIN)
        t.set_wager(5)
        t.deal()
        data = p.neon21_pending
        data["currency"] = "gold"
        p.set_neon21_pending(data)
        q = Neon21Table(p)
        self.assertEqual((q.result.currency, p.tokens, p.tickets), (TOKENS, 25, 0))


if __name__ == "__main__":
    unittest.main()
