"""The NEON 21 deck: one genuine, shuffled, 52-card deck per round, dealt without
replacement. These tests are about distribution and drawing rules, not looks.

Run headless from this folder:   python -m unittest test_blackjack_deck -v
"""
import collections
import json
import os
import random
import unittest

from blackjack import (DECK_SIZE, STANDARD_CARDS, SUITS, BlackjackError,
                       BlackjackRound, Card, Phase, hand_value, is_standard_deal,
                       new_deck, standard_deck)
from blackjack_testing import stacked_deck
from neon21 import Neon21Table
from player_profile import PlayerProfile

HERE = os.path.dirname(os.path.abspath(__file__))


def everything(r):
    """Every card the round knows about: undealt deck + both hands."""
    return r.deck + r.player + r.dealer


class StandardDeckTests(unittest.TestCase):
    def test_exactly_52_unique_cards_no_jokers(self):
        deck = standard_deck()
        self.assertEqual((len(deck), len(set(deck)), DECK_SIZE), (52, 52, 52))
        self.assertEqual(set(deck), STANDARD_CARDS)
        self.assertTrue(all(1 <= c.rank <= 13 and c.suit in SUITS for c in deck))

    def test_every_rank_appears_exactly_four_times(self):
        counts = collections.Counter(c.rank for c in new_deck(random.Random(1)))
        self.assertEqual(sorted(counts), list(range(1, 14)))
        self.assertEqual(set(counts.values()), {4})
        labels = collections.Counter(c.label for c in standard_deck())
        self.assertEqual(labels, {l: 4 for l in "A 2 3 4 5 6 7 8 9 10 J Q K".split()})

    def test_every_suit_has_exactly_thirteen_cards_one_of_each_rank(self):
        deck = new_deck(random.Random(2))
        self.assertEqual(set(SUITS), {"S", "H", "D", "C"})
        for suit in SUITS:
            ranks = sorted(c.rank for c in deck if c.suit == suit)
            self.assertEqual(ranks, list(range(1, 14)), suit)

    def test_a_shuffled_deck_is_the_same_52_cards_in_a_different_order(self):
        a, b = new_deck(random.Random(1)), new_deck(random.Random(2))
        self.assertEqual(set(a), set(b))
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, standard_deck())
        self.assertEqual(len({tuple(new_deck()) for _ in range(20)}), 20)       # the real RNG shuffles

    def test_hand_value_rules_are_unchanged(self):
        self.assertEqual(hand_value([Card(1, "S"), Card(13, "H")]), (21, True))     # A = 11
        self.assertEqual(hand_value([Card(1, "S"), Card(1, "H"), Card(9, "C")]), (21, True))
        self.assertEqual(hand_value([Card(1, "S"), Card(13, "H"), Card(12, "D")]), (21, False))   # A = 1
        self.assertEqual([Card(r, "S").points for r in (11, 12, 13)], [10, 10, 10])


class RoundDeckTests(unittest.TestCase):
    def test_a_new_round_starts_from_one_full_deck_minus_the_four_dealt_cards(self):
        r = BlackjackRound(5, rng=random.Random(3))
        self.assertEqual((len(r.player), len(r.dealer), len(r.deck)), (2, 2, 48))
        self.assertTrue(is_standard_deal(r.deck, r.player, r.dealer))

    def test_player_and_dealer_draw_from_one_shared_deck(self):
        r = BlackjackRound(5, deck=stacked_deck("2", "3", "4", "5", "6", "7", "8", "9"))
        deck_obj = r.deck
        r.hit()
        self.assertIs(r.deck, deck_obj)                                          # one list, mutated in place
        r.stand()                                                                # the dealer draws from the same list
        self.assertIs(r.deck, deck_obj)
        self.assertEqual(len(r.deck) + len(r.player) + len(r.dealer), 52)
        self.assertFalse(set(r.player) & set(r.dealer))                           # no card in both hands
        self.assertEqual([c.label for c in r.player], ["2", "4", "6"])            # P D P D then draws in order
        self.assertEqual([c.label for c in r.dealer][:2], ["3", "5"])

    def test_the_deck_shrinks_by_exactly_the_cards_dealt(self):
        r = BlackjackRound(5, deck=stacked_deck("2", "3", "4", "3", "2", "2", "2"))
        before = len(r.deck)
        r.hit()
        self.assertEqual(len(r.deck), before - 1)
        r.hit()
        self.assertEqual(len(r.deck), before - 2)

    def test_drawing_never_duplicates_a_card_across_thousands_of_rounds(self):
        rng = random.Random(7)
        for i in range(3000):
            r = BlackjackRound(5, rng=rng)
            self.assertTrue(is_standard_deal(everything(r)))
            while not r.settled:
                (r.hit if r.player_value < 17 and rng.random() < 0.8 else r.stand)()
                self.assertTrue(is_standard_deal(everything(r)), f"round {i}")     # 52 unique after EVERY draw
            self.assertEqual(len(set(r.player + r.dealer)), len(r.player) + len(r.dealer))

    def test_no_rank_ever_appears_more_than_four_times_in_a_round(self):
        rng = random.Random(8)
        worst = collections.Counter()
        for _ in range(3000):
            r = BlackjackRound(5, rng=rng)
            while not r.settled:
                r.hit() if r.player_value < 21 and rng.random() < 0.9 else r.stand()
            counts = collections.Counter(c.rank for c in r.player + r.dealer)
            for rank, n in counts.items():
                worst[rank] = max(worst[rank], n)
        self.assertTrue(all(n <= 4 for n in worst.values()), worst)

    def test_the_fifth_ace_cannot_appear(self):
        # all four Aces dealt first (two each), then a long run of other cards
        r = BlackjackRound(5, deck=stacked_deck("A", "A", "A", "A", "2", "2", "2", "2", "3", "3", "3", "3"))
        self.assertEqual(sum(c.rank == 1 for c in r.player + r.dealer), 4)
        self.assertEqual(sum(c.rank == 1 for c in r.deck), 0)                    # none left to draw
        while r.can_hit and r.player_value < 21:
            r.hit()
            self.assertEqual(sum(c.rank == 1 for c in r.player + r.dealer + r.deck), 4)
        # and over the whole deck exactly four Aces are ever drawn, in any order
        r = BlackjackRound(5, rng=random.Random(11))
        drawn = r.player + r.dealer
        while r.deck:
            drawn.append(r._draw())
        self.assertEqual(len(drawn), 52)
        self.assertEqual(sum(c.rank == 1 for c in drawn), 4)

    def test_cards_cannot_be_drawn_after_the_deck_is_exhausted(self):
        r = BlackjackRound(5, rng=random.Random(12))
        for _ in range(48):
            r._draw()
        self.assertEqual(len(r.deck), 0)
        with self.assertRaises(BlackjackError):
            r._draw()
        with self.assertRaises(BlackjackError):
            r.hit()
        self.assertEqual((len(r.player), r.phase), (2, Phase.PLAYER))            # nothing was invented
        self.assertEqual(len(r.deck), 0)                                         # and no reshuffle

    def test_no_reshuffle_mid_round(self):
        r = BlackjackRound(5, deck=stacked_deck("2", "3", "4", "5", "6", "7", "8", "9", "10"))
        expected_next = [c for c in reversed(r.deck)]                            # the draw order, fixed at the deal
        drawn = []
        while r.can_hit and r.player_value < 21:
            drawn.append(r.hit())
        self.assertEqual(drawn, expected_next[:len(drawn)])

    def test_each_round_gets_its_own_new_full_shuffled_deck(self):
        profile = PlayerProfile(tokens=100)
        decks = []
        for _ in range(4):
            t = Neon21Table(profile, rng=random.Random(len(decks)))
            t.set_wager(1)
            t.deal()
            r = t.round
            self.assertTrue(is_standard_deal(everything(r)))
            decks.append(tuple(r.deck))
            if t.phase == t.PLAYING:
                t.stand()
        self.assertEqual(len(set(decks)), 4)                                     # four different shuffles
        self.assertTrue(all(len(d) <= 48 for d in decks))

    def test_a_rigged_or_hand_built_deck_must_still_be_one_standard_deck(self):
        good = new_deck(random.Random(1))
        for bad in (good[:-1], good + [Card(2, "S")], [Card(2, "S")] * 52, good[:51] + [good[0]],
                    good[:51] + [Card(14, "S")], good[:51] + [Card(2, "X")], []):
            with self.assertRaises(ValueError):
                BlackjackRound(5, deck=bad)

    def test_no_card_is_generated_independently_anywhere_in_the_game_code(self):
        for name in ("blackjack.py", "neon21.py", "neon21_scene.py", "neon21_art.py"):
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                source = f.read()
            self.assertNotIn("randint(1, 13)", source, name)
            if name != "blackjack.py":
                self.assertNotIn("Card(", source.replace("CardView(", "").replace("is_standard", ""), name)
        with open(os.path.join(HERE, "blackjack.py"), encoding="utf-8") as f:
            self.assertNotIn("randint", f.read())


class SaveLoadDeckTests(unittest.TestCase):
    def test_save_and_load_keep_the_exact_remaining_deck_in_order(self):
        r = next(r for r in (BlackjackRound(5, rng=random.Random(s)) for s in range(100)) if not r.settled)
        r.hit()
        data = json.loads(json.dumps(r.to_dict()))                               # through real JSON
        back = BlackjackRound.from_dict(data)
        self.assertEqual(back.deck, r.deck)                                      # same cards, same order
        self.assertEqual((back.player, back.dealer, back.bet), (r.player, r.dealer, r.bet))
        self.assertEqual(len(back.deck), 52 - len(r.player) - len(r.dealer))
        self.assertTrue(is_standard_deal(everything(back)))

    def test_a_restored_round_draws_the_same_cards_in_the_same_order(self):
        for seed in range(30):
            original = BlackjackRound(5, rng=random.Random(seed))
            if original.settled:
                continue
            restored = BlackjackRound.from_dict(json.loads(json.dumps(original.to_dict())))
            original.stand()
            restored.stand()
            self.assertEqual(restored.dealer, original.dealer, seed)
            self.assertEqual((restored.outcome, restored.payout), (original.outcome, original.payout))
            self.assertEqual(restored.deck, original.deck)

    def test_a_restored_round_cannot_be_rebuilt_from_a_different_deck(self):
        r = BlackjackRound(5, rng=random.Random(5))
        data = r.to_dict()
        for key in ("player", "dealer", "deck"):
            tampered = json.loads(json.dumps(data))
            tampered[key] = tampered[key][::-1] if key == "deck" else tampered[key]
            back = BlackjackRound.from_dict(tampered)                            # reversing is still one real deck...
            self.assertEqual(sorted(map(tuple, tampered["deck"])), sorted(map(tuple, data["deck"])))
        swapped = json.loads(json.dumps(data))
        swapped["deck"][0] = swapped["player"][0]                                # ...but a duplicate is refused
        with self.assertRaises(ValueError):
            BlackjackRound.from_dict(swapped)
        short = json.loads(json.dumps(data))
        short["deck"].pop()
        with self.assertRaises(ValueError):
            BlackjackRound.from_dict(short)

    def test_a_recovered_round_cannot_reroll_its_cards(self):
        """Kill the game mid-hand: whatever shuffle or RNG the next run has, the saved
        hand finishes with the SAME dealer cards as if it had never been interrupted."""
        for seed in range(25):
            control_profile = PlayerProfile(tokens=100)
            control = Neon21Table(control_profile, rng=random.Random(seed))
            control.set_wager(5)
            control.deal()
            if control.phase != control.PLAYING:
                continue
            saved = control_profile.neon21_pending                              # what the file holds
            deck_at_save = list(control.round.deck)
            control.stand()
            crashed = PlayerProfile(tokens=95)
            crashed.set_neon21_pending(saved)
            recovered = Neon21Table(crashed, rng=random.Random(seed + 1000),
                                    deck_source=lambda: stacked_deck("10", "10", "10", "9"))
            self.assertTrue(recovered.result.recovered)
            self.assertEqual(recovered.round.dealer, control.round.dealer, seed)
            self.assertEqual(recovered.round.deck, control.round.deck, seed)
            self.assertEqual(recovered.result.outcome, control.result.outcome)
            self.assertEqual(crashed.tokens, control_profile.tokens, seed)
            self.assertLessEqual(len(deck_at_save), 48)

    def test_saved_deck_is_updated_after_every_hit(self):
        profile = PlayerProfile(tokens=100)
        t = Neon21Table(profile, deck_source=lambda: stacked_deck("2", "10", "3", "9", "2", "2"))
        t.set_wager(5)
        t.deal()
        before = profile.neon21_pending["round"]["deck"]
        t.hit()
        after = profile.neon21_pending["round"]["deck"]
        self.assertEqual(after, before[:-1])                                     # exactly the drawn card left it
        self.assertEqual(len(profile.neon21_pending["round"]["player"]), 3)

    def test_unsaved_extra_cards_or_shuffled_in_aces_are_rejected(self):
        r = BlackjackRound(5, rng=random.Random(9))
        data = r.to_dict()
        data["deck"].append([1, "S"])                                            # a spare Ace of Spades
        with self.assertRaises(ValueError):
            BlackjackRound.from_dict(data)


if __name__ == "__main__":
    unittest.main()
