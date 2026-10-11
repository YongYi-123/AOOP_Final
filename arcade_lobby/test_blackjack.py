"""Tests for the NEON 21 rules engine (blackjack.py).

Run headless from this folder:   python -m unittest test_blackjack -v
"""
import random
import unittest

from blackjack_testing import stacked_deck
from blackjack import (BlackjackError, BlackjackRound, Card, Outcome, Phase,
                       hand_value, is_natural, natural_payout, new_deck)


def stack(*labels):
    """A real 52-card deck that deals `labels` first, in order ('A', 'K', '7' ...)."""
    return stacked_deck(*labels)


def rnd(bet, *labels):
    """Deal order is player, dealer, player, dealer, then draws."""
    return BlackjackRound(bet, deck=stack(*labels))


def hand(*labels):
    ranks = {"A": 1, "J": 11, "Q": 12, "K": 13}
    return [Card(ranks.get(s) or int(s), "S") for s in labels]


class CardValueTests(unittest.TestCase):
    def test_number_and_face_values(self):
        self.assertEqual(hand_value(hand("2", "9")), (11, False))
        self.assertEqual(hand_value(hand("K", "Q")), (20, False))
        self.assertEqual(hand_value(hand("J", "10")), (20, False))

    def test_ace_counts_eleven_or_one(self):
        self.assertEqual(hand_value(hand("A", "6")), (17, True))
        self.assertEqual(hand_value(hand("A", "6", "10")), (17, False))
        self.assertEqual(hand_value(hand("A", "K")), (21, True))

    def test_multiple_aces(self):
        self.assertEqual(hand_value(hand("A", "A")), (12, True))
        self.assertEqual(hand_value(hand("A", "A", "9")), (21, True))
        self.assertEqual(hand_value(hand("A", "A", "A", "A")), (14, True))
        self.assertEqual(hand_value(hand("A", "A", "K")), (12, False))
        self.assertEqual(hand_value(hand("A", "A", "K", "K")), (22, False))

    def test_natural_detection(self):
        self.assertTrue(is_natural(hand("A", "K")))
        self.assertTrue(is_natural(hand("10", "A")))
        self.assertFalse(is_natural(hand("7", "7", "7")))     # 21 with three cards
        self.assertFalse(is_natural(hand("A", "9")))
        self.assertFalse(is_natural(hand("A", "A")))

    def test_deck_is_a_full_shuffled_52(self):
        deck = new_deck(random.Random(5))
        self.assertEqual(len(deck), 52)
        self.assertEqual(len(set(deck)), 52)
        self.assertNotEqual(deck, new_deck(random.Random(6)))
        self.assertEqual(sum(c.rank == 1 for c in deck), 4)


class RoundFlowTests(unittest.TestCase):
    def test_initial_deal(self):
        r = rnd(10, "9", "5", "7", "6")
        self.assertEqual([c.label for c in r.player], ["9", "7"])
        self.assertEqual([c.label for c in r.dealer], ["5", "6"])
        self.assertTrue(r.hole_hidden)
        self.assertEqual(r.dealer_visible_value, 5)
        self.assertEqual(r.phase, Phase.PLAYER)

    def test_bust_ends_round_immediately(self):
        r = rnd(10, "10", "5", "6", "6", "K")
        r.hit()
        self.assertEqual((r.outcome, r.phase, r.payout), (Outcome.BUST, Phase.SETTLED, 0))
        self.assertFalse(r.hole_hidden)

    def test_repeated_hits_until_stand(self):
        r = rnd(10, "2", "10", "3", "7", "2", "2")
        r.hit()
        r.hit()
        self.assertEqual(r.player_value, 9)
        r.stand()
        self.assertEqual(r.outcome, Outcome.LOSE)          # 9 vs 17

    def test_regular_win_pays_even_money(self):
        r = rnd(10, "10", "10", "9", "8")
        r.stand()
        self.assertEqual((r.outcome, r.payout, r.net), (Outcome.WIN, 20, 10))

    def test_push_returns_stake(self):
        r = rnd(10, "10", "10", "8", "8")
        r.stand()
        self.assertEqual((r.outcome, r.payout, r.net), (Outcome.PUSH, 10, 0))

    def test_loss_pays_nothing(self):
        r = rnd(10, "10", "10", "7", "9")
        r.stand()
        self.assertEqual((r.outcome, r.payout, r.net), (Outcome.LOSE, 0, -10))

    def test_dealer_bust(self):
        r = rnd(10, "10", "10", "8", "6", "K")
        r.stand()
        self.assertEqual((r.outcome, r.payout), (Outcome.DEALER_BUST, 20))

    def test_dealer_draws_to_17_and_stops(self):
        r = rnd(10, "10", "5", "8", "4", "3", "5", "K")    # dealer 9 -> 12 -> 17
        r.stand()
        self.assertEqual([c.label for c in r.dealer], ["5", "4", "3", "5"])
        self.assertEqual(r.dealer_value, 17)

    def test_dealer_stands_on_soft_17(self):
        r = rnd(10, "10", "A", "9", "6", "K")              # dealer A+6 = soft 17
        r.stand()
        self.assertEqual(len(r.dealer), 2)
        self.assertEqual(r.dealer_value, 17)
        self.assertEqual(r.outcome, Outcome.WIN)

    def test_dealer_hits_soft_16_and_hard_16(self):
        r = rnd(10, "10", "A", "9", "5", "2")              # soft 16 -> 18 soft
        r.stand()
        self.assertEqual(r.dealer_value, 18)
        r = rnd(10, "10", "10", "9", "6", "4")             # hard 16 -> 20
        r.stand()
        self.assertEqual(r.dealer_value, 20)

    def test_three_card_21_is_not_a_natural(self):
        r = rnd(10, "7", "9", "7", "8", "7")
        r.hit()
        self.assertEqual(r.player_value, 21)
        self.assertNotEqual(r.outcome, Outcome.BLACKJACK)
        self.assertEqual(r.outcome, Outcome.WIN)           # 21 beats dealer's 17
        self.assertEqual(r.payout, 20)                     # even money, not 3:2

    def test_hitting_to_21_stands_automatically(self):
        r = rnd(10, "10", "10", "5", "7", "6")
        r.hit()
        self.assertTrue(r.settled)


class NaturalTests(unittest.TestCase):
    def test_player_natural_pays_three_to_two(self):
        r = rnd(10, "A", "9", "K", "7")
        self.assertEqual((r.outcome, r.phase), (Outcome.BLACKJACK, Phase.SETTLED))
        self.assertEqual((r.payout, r.net), (25, 15))

    def test_dealer_natural_checked_before_player_acts(self):
        r = rnd(10, "9", "A", "7", "K")
        self.assertEqual((r.outcome, r.payout), (Outcome.LOSE, 0))
        self.assertFalse(r.hole_hidden)
        with self.assertRaises(BlackjackError):
            r.hit()

    def test_both_naturals_push(self):
        r = rnd(10, "A", "A", "K", "K")
        self.assertEqual((r.outcome, r.payout), (Outcome.PUSH, 10))

    def test_fractional_natural_rounds_down(self):
        self.assertEqual(natural_payout(5), 12)            # 5 + 7 (7.5 -> 7)
        self.assertEqual(natural_payout(10), 25)
        self.assertEqual(natural_payout(25), 62)           # 25 + 37
        self.assertEqual(natural_payout(1), 2)
        self.assertEqual(natural_payout(50), 125)

    def test_natural_never_exceeds_exact_three_to_two(self):
        for bet in range(1, 200):
            self.assertLessEqual(natural_payout(bet) - bet, bet * 1.5)
            self.assertGreater(natural_payout(bet) - bet, bet * 1.5 - 1)


class DoubleDownTests(unittest.TestCase):
    def test_double_doubles_bet_and_draws_one_card(self):
        r = rnd(10, "5", "10", "6", "7", "10", "K")
        self.assertTrue(r.can_double)
        r.double()
        self.assertEqual((r.bet, len(r.player), r.player_value), (20, 3, 21))
        self.assertTrue(r.settled)
        self.assertEqual((r.outcome, r.payout), (Outcome.WIN, 40))

    def test_double_loss_costs_both_stakes(self):
        r = rnd(10, "5", "10", "6", "10", "2")
        r.double()                                         # 13 vs 20
        self.assertEqual((r.bet, r.payout, r.net), (20, 0, -20))

    def test_double_bust(self):
        r = rnd(10, "10", "10", "6", "7", "K")
        r.double()
        self.assertEqual((r.outcome, r.bet), (Outcome.BUST, 20))

    def test_double_only_on_first_two_cards(self):
        r = rnd(10, "2", "10", "3", "7", "2", "2")
        r.hit()
        self.assertFalse(r.can_double)
        with self.assertRaises(BlackjackError):
            r.double()
        self.assertEqual(r.bet, 10)

    def test_cannot_double_twice(self):
        r = rnd(10, "5", "10", "6", "7", "2")
        r.double()
        with self.assertRaises(BlackjackError):
            r.double()
        self.assertEqual(r.bet, 20)


class InvalidActionTests(unittest.TestCase):
    def test_no_actions_after_settlement(self):
        r = rnd(10, "10", "10", "9", "8")
        r.stand()
        for action in (r.hit, r.stand, r.double):
            with self.assertRaises(BlackjackError):
                action()
        self.assertEqual(r.payout, 20)

    def test_bad_bets_rejected(self):
        for bad in (0, -5, 2.5, "10", True, None):
            with self.assertRaises(ValueError):
                BlackjackRound(bad)

    def test_payout_zero_until_settled(self):
        r = rnd(10, "10", "10", "9", "8")
        self.assertEqual(r.payout, 0)

    def test_finish_stands_once(self):
        r = rnd(10, "10", "10", "9", "8", "K")
        r.finish()
        first = (r.outcome, r.payout, list(r.dealer))
        r.finish()
        self.assertEqual((r.outcome, r.payout, list(r.dealer)), first)
        self.assertEqual(r.outcome, Outcome.WIN)

    def test_random_rounds_always_terminate_consistently(self):
        rng = random.Random(11)
        for _ in range(500):
            r = BlackjackRound(10, rng=rng)
            while not r.settled:
                r.hit() if r.player_value < 15 and rng.random() < 0.8 else r.stand()
            self.assertIn(r.payout, (0, 10, 20, 25))
            self.assertGreaterEqual(r.player_value if r.outcome is not Outcome.BUST else 22, 1)


if __name__ == "__main__":
    unittest.main()
