"""Test helper: rig the order of a REAL 52-card deck.

stacked_deck("10", "A", "9H") puts those cards on top, dealt in that order
(player, dealer, player, dealer, then draws), and keeps every other card of the
standard deck underneath in a fixed order - so a rigged round still has exactly
one legal 52-card deck (a fifth Ace or a repeated card is impossible).

A label is a rank ("A", "2".."10", "J", "Q", "K"), optionally followed by a
suit letter (S, H, D, C): "10H". Without a suit the first unused suit is taken.
"""
from blackjack import RANK_LABELS, SUITS, Card, standard_deck

_RANKS = {v: k for k, v in RANK_LABELS.items()}


def _parse(label):
    suit = None
    if len(label) > 1 and label[-1] in SUITS:
        label, suit = label[:-1], label[-1]
    return (_RANKS[label] if label in _RANKS else int(label)), suit


def stacked_deck(*labels):
    remaining = standard_deck()
    top = []
    for label in labels:
        rank, suit = _parse(label)
        card = next((c for c in remaining if c.rank == rank and (suit is None or c.suit == suit)), None)
        if card is None:
            raise ValueError(f"no {label} left in a standard deck (a rank has only four cards)")
        remaining.remove(card)
        top.append(card)
    return remaining + top[::-1]            # the next card is the END of the list
