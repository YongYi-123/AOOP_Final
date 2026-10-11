"""Blackjack rules for NEON 21: pure logic, no pygame, no wallet.

A BlackjackRound is one hand against the dealer. It works in whole units of
whatever stake the caller chose and never touches a profile: the caller
charges the stake before dealing, and pays `payout` (stake included) once the
round is SETTLED. That keeps the rules testable on their own.

Rules: one fresh shuffled 52-card deck per round; dealer stands on every 17
(soft 17 included); a natural (Ace + 10-value card on the first two cards)
pays 3:2, rounded DOWN to a whole unit; a 21 made with 3+ cards is an ordinary
21; dealer naturals are checked before the player may act; a double down is
allowed on the first two cards only and draws exactly one card.

Leaving mid-round: finish() makes the player STAND on the current hand and
plays the dealer out, so the stake is neither refunded (a free peek at the
cards) nor silently lost.
"""
import random
from dataclasses import dataclass
from enum import Enum

SUITS = ("S", "H", "D", "C")             # spades, hearts, diamonds, clubs
RANK_LABELS = {1: "A", 11: "J", 12: "Q", 13: "K"}
DEALER_STANDS_ON = 17


@dataclass(frozen=True)
class Card:
    rank: int       # 1 (ace) .. 13 (king)
    suit: str

    @property
    def label(self):
        return RANK_LABELS.get(self.rank, str(self.rank))

    @property
    def points(self):
        """Face value with the ace as 1 (hand_value upgrades one to 11)."""
        return min(self.rank, 10)


def new_deck(rng=None):
    """A fresh, fairly shuffled 52-card deck (Fisher-Yates via Random.shuffle)."""
    deck = [Card(rank, suit) for suit in SUITS for rank in range(1, 14)]
    (rng or random.SystemRandom()).shuffle(deck)
    return deck


def hand_value(cards):
    """(best total, is_soft). An ace counts 11 when that does not bust the
    hand - at most one ace can, since two 11s already make 22."""
    total = sum(c.points for c in cards)
    if any(c.rank == 1 for c in cards) and total + 10 <= 21:
        return total + 10, True
    return total, False


def is_natural(cards):
    return len(cards) == 2 and hand_value(cards)[0] == 21


def natural_payout(bet):
    """Total returned for a winning natural: the stake plus 3:2, with the odd
    half unit dropped (5 -> +7, 10 -> +15). Always in the house's favour, so a
    fractional win can never be farmed by repeating small bets."""
    return bet + (bet * 3) // 2


class Phase(Enum):
    PLAYER = "player"       # the player may hit / stand / double
    SETTLED = "settled"     # over; payout is final


class Outcome(Enum):
    BLACKJACK = "blackjack"
    WIN = "win"
    DEALER_BUST = "dealer_bust"
    PUSH = "push"
    LOSE = "lose"
    BUST = "bust"


WINNING = (Outcome.BLACKJACK, Outcome.WIN, Outcome.DEALER_BUST)


class BlackjackError(Exception):
    """An action that is not legal in the current state."""


class BlackjackRound:
    def __init__(self, bet, rng=None, deck=None):
        if isinstance(bet, bool) or not isinstance(bet, int) or bet <= 0:
            raise ValueError(f"bet must be a positive int, got {bet!r}")
        self.bet = bet
        self.deck = list(deck) if deck is not None else new_deck(rng)
        self.player = []
        self.dealer = []
        self.phase = Phase.PLAYER
        self.outcome = None
        self.doubled = False
        self.hole_hidden = True
        for hand in (self.player, self.dealer, self.player, self.dealer):   # real deal order
            hand.append(self._draw())
        self._check_naturals()

    # ------------------------------------------------------------ queries
    @property
    def settled(self):
        return self.phase is Phase.SETTLED

    @property
    def player_value(self):
        return hand_value(self.player)[0]

    @property
    def dealer_value(self):
        return hand_value(self.dealer)[0]

    @property
    def dealer_visible_value(self):
        """What the player may know: just the up-card while the hole is hidden."""
        return hand_value(self.dealer[:1])[0] if self.hole_hidden else self.dealer_value

    @property
    def can_hit(self):
        return self.phase is Phase.PLAYER

    can_stand = can_hit

    @property
    def can_double(self):
        return self.phase is Phase.PLAYER and len(self.player) == 2 and not self.doubled

    @property
    def payout(self):
        """Total units handed back (stake included); 0 until SETTLED."""
        if not self.settled:
            return 0
        return {Outcome.BLACKJACK: natural_payout(self.bet),
                Outcome.WIN: 2 * self.bet, Outcome.DEALER_BUST: 2 * self.bet,
                Outcome.PUSH: self.bet}.get(self.outcome, 0)

    @property
    def net(self):
        return self.payout - self.bet

    def potential_payout(self):
        """The total a plain win would return right now (a natural pays more)."""
        return 2 * self.bet

    # ------------------------------------------------------------ actions
    def hit(self):
        self._require(self.can_hit, "hit")
        self.player.append(self._draw())
        if self.player_value > 21:
            self._settle(Outcome.BUST)
        elif self.player_value == 21:
            self._dealer_plays()            # 21 cannot improve: stand for the player
        return self.player[-1]

    def stand(self):
        self._require(self.can_stand, "stand")
        self._dealer_plays()

    def double(self):
        """Double the bet, draw exactly one card, then stand. The CALLER must
        have collected the extra stake first (check can_double, charge, then
        call this); the bet grows by the original amount."""
        self._require(self.can_double, "double down")
        self.bet *= 2
        self.doubled = True
        self.player.append(self._draw())
        if self.player_value > 21:
            self._settle(Outcome.BUST)
        else:
            self._dealer_plays()

    def finish(self):
        """The player is leaving: stand on the current hand. Idempotent."""
        if self.phase is Phase.PLAYER:
            self._dealer_plays()

    # ------------------------------------------------------------ saving
    def to_dict(self):
        """The whole round (including the undealt deck, so a saved round can
        never be re-drawn differently) as plain JSON data."""
        cards = lambda hand: [[c.rank, c.suit] for c in hand]
        return {"bet": self.bet, "doubled": self.doubled, "deck": cards(self.deck),
                "player": cards(self.player), "dealer": cards(self.dealer),
                "outcome": self.outcome.value if self.outcome else None}

    @classmethod
    def from_dict(cls, data):
        """Rebuild a saved round. Raises ValueError for anything malformed."""
        try:
            def cards(raw):
                out = [Card(int(r), str(s)) for r, s in raw]
                if any(not 1 <= c.rank <= 13 or c.suit not in SUITS for c in out):
                    raise ValueError("bad card")
                return out
            self = cls.__new__(cls)
            bet = data["bet"]
            if isinstance(bet, bool) or not isinstance(bet, int) or bet <= 0:
                raise ValueError("bad bet")
            self.bet, self.doubled = bet, bool(data.get("doubled"))
            self.deck, self.player, self.dealer = (cards(data[k]) for k in ("deck", "player", "dealer"))
            if len(self.player) < 2 or len(self.dealer) < 2:
                raise ValueError("incomplete hands")
            outcome = data.get("outcome")
            self.outcome = Outcome(outcome) if outcome else None
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"unreadable saved round: {exc}") from exc
        self.phase = Phase.SETTLED if self.outcome else Phase.PLAYER
        self.hole_hidden = not self.outcome
        return self

    # ------------------------------------------------------------ internals
    def _require(self, ok, action):
        if not ok:
            raise BlackjackError(f"cannot {action} now")

    def _draw(self):
        return self.deck.pop()

    def _check_naturals(self):
        player_bj, dealer_bj = is_natural(self.player), is_natural(self.dealer)
        if player_bj and dealer_bj:
            self._settle(Outcome.PUSH)
        elif dealer_bj:
            self._settle(Outcome.LOSE)
        elif player_bj:
            self._settle(Outcome.BLACKJACK)

    def _dealer_plays(self):
        self.hole_hidden = False
        while self.dealer_value < DEALER_STANDS_ON:     # stands on soft 17
            self.dealer.append(self._draw())
        p, d = self.player_value, self.dealer_value
        if d > 21:
            self._settle(Outcome.DEALER_BUST)
        elif p > d:
            self._settle(Outcome.WIN)
        elif p == d:
            self._settle(Outcome.PUSH)
        else:
            self._settle(Outcome.LOSE)

    def _settle(self, outcome):
        if self.phase is Phase.SETTLED:
            return
        self.outcome = outcome
        self.phase = Phase.SETTLED
        self.hole_hidden = False
