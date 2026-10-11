"""Neon21Table: the money side of NEON 21 (no pygame). It joins one
BlackjackRound to one PlayerProfile and is the only code that moves currency.

    deal()      spends the wager (TOKENS) and saves the open round
    double()    spends the extra wager
    hit/stand   change the round; a finished round settles itself
    finish()    the player is leaving: STAND on the hand and settle
    settle      pays once, then clears the saved round

Payout, settled exactly once (`_paid`) and in one profile.batch() so the
balance, the daily-cap counter and the cleared round reach the save together:
  * the stake that comes back (win, natural or push) is returned in Tokens;
  * net profit is paid in Tokens, or - if the player chose TICKETS before the
    deal - converted at settings.NEON21_TICKETS_PER_TOKEN, limited by the
    profile's daily NEON 21 ticket cap. Profit beyond the cap is paid in
    Tokens and the Settlement says so (capped=True). Currency is locked at deal.

The open round is stored in the profile (set_neon21_pending) after every step,
so closing or killing the game cannot reroll a committed wager: the next
Neon21Table for that profile settles the saved round (standing on its hand,
with the saved deck) before anything new can be dealt.
"""
import random
from dataclasses import dataclass

from blackjack import (WINNING, BlackjackError, BlackjackRound, Outcome,
                       natural_payout)
from settings import (NEON21_DEFAULT_WAGER, NEON21_TICKETS_PER_TOKEN,
                      NEON21_WAGERS)

TOKENS, TICKETS = "tokens", "tickets"
REASON = "NEON 21"


@dataclass(frozen=True)
class Settlement:
    outcome: Outcome
    stake: int              # total tokens wagered (doubled included)
    currency: str           # what the player chose for winnings
    stake_returned: int     # tokens handed back (stake on a win / push)
    profit: int             # net profit in tokens-equivalent (0 on push / loss)
    tickets_paid: int
    profit_tokens: int      # profit that was paid in tokens
    capped: bool            # the daily ticket cap turned some or all ticket profit into tokens
    recovered: bool = False  # settled from a saved round after a restart

    @property
    def net_tokens(self):
        return self.stake_returned + self.profit_tokens - self.stake


class Neon21Table:
    IDLE, PLAYING, DONE = "idle", "playing", "done"

    def __init__(self, profile, rng=None, deck_source=None):
        self.profile = profile
        self.deck_source = deck_source      # tests: a callable returning a stacked deck
        self.rng = rng or random.SystemRandom()
        self.wager = NEON21_DEFAULT_WAGER
        self.currency = TOKENS
        self.round = None
        self.result = None
        self.phase = self.IDLE
        self._paid = False
        self.notice = None          # one-off message, e.g. about a recovered round
        self._recover()

    # ------------------------------------------------------------ betting
    def affordable_wagers(self):
        return [w for w in NEON21_WAGERS if self.profile.can_afford_tokens(w)]

    def set_wager(self, wager):
        if self.phase == self.PLAYING or wager not in NEON21_WAGERS:
            return False
        self.wager = wager
        return True

    def step_wager(self, step):
        """Move the wager one preset up (+1) or down (-1)."""
        i = NEON21_WAGERS.index(self.wager) + step
        return 0 <= i < len(NEON21_WAGERS) and self.set_wager(NEON21_WAGERS[i])

    def set_currency(self, currency):
        """TOKENS or TICKETS for winnings. Refused once a round is under way."""
        if self.phase == self.PLAYING or currency not in (TOKENS, TICKETS):
            return False
        self.currency = currency
        return True

    def toggle_currency(self):
        return self.set_currency(TICKETS if self.currency == TOKENS else TOKENS)

    @property
    def can_deal(self):
        return (self.phase in (self.IDLE, self.DONE) and self.profile.neon21_pending is None
                and self.profile.can_afford_tokens(self.wager))

    @property
    def stake(self):
        return self.round.bet if self.round else self.wager

    def preview(self, bet=None):
        """(win profit, natural profit) in tokens for a wager - what the screen
        shows before the deal."""
        bet = self.wager if bet is None else bet
        return bet, natural_payout(bet) - bet

    def ticket_room(self):
        return self.profile.neon21_ticket_room()

    # ------------------------------------------------------------ actions
    def deal(self):
        """Spend the wager and deal. False (nothing charged) if not allowed."""
        if not self.can_deal:
            return False
        round_ = BlackjackRound(self.wager, deck=self.deck_source() if self.deck_source else None,
                                rng=self.rng)
        with self.profile.batch():
            if not self.profile.spend_tokens(self.wager, f"{REASON} STAKE"):
                return False
            self.profile.record_chance_game_played()
            self.round, self.result, self._paid = round_, None, False
            self.phase = self.PLAYING
            self._save_open_round()
        if round_.settled:                       # a natural on either side ends it at once
            self._settle()
        return True

    def hit(self):
        return self._act(lambda: self.round.hit())

    def stand(self):
        return self._act(lambda: self.round.stand())

    @property
    def can_double(self):
        return (self.phase == self.PLAYING and self.round.can_double
                and self.profile.can_afford_tokens(self.round.bet))

    def double(self):
        if not self.can_double:
            return False
        extra = self.round.bet
        with self.profile.batch():
            if not self.profile.spend_tokens(extra, f"{REASON} DOUBLE"):
                return False
            self.round.double()
            self._save_open_round()
        if self.round.settled:
            self._settle()
        return True

    def finish(self):
        """The player is leaving. An open hand stands and settles (once)."""
        if self.phase == self.PLAYING:
            self.round.finish()
            self._settle()
        return self.result

    def next_round(self):
        """Back to betting after a result."""
        if self.phase == self.DONE:
            self.round, self.result, self.phase = None, None, self.IDLE
            return True
        return False

    # ------------------------------------------------------------ internals
    def _act(self, action):
        if self.phase != self.PLAYING or self.round.settled:
            return False
        try:
            action()
        except BlackjackError:
            return False
        if self.round.settled:
            self._settle()
        else:
            self._save_open_round()
        return True

    def _save_open_round(self):
        self.profile.set_neon21_pending({"currency": self.currency, "round": self.round.to_dict()})

    def _settle(self, recovered=False):
        if self._paid or self.round is None or not self.round.settled:
            return self.result
        self._paid = True
        r = self.round
        stake, payout = r.bet, r.payout
        returned, profit = min(payout, stake), max(0, payout - stake)
        profile, tickets, profit_tokens, capped = self.profile, 0, profit, False
        with profile.batch():
            if returned:
                profile.refund_tokens(returned, f"{REASON} STAKE")
            if profit and self.currency == TICKETS:
                per = NEON21_TICKETS_PER_TOKEN
                convertible = min(profit, profile.neon21_ticket_room() // per)
                tickets = convertible * per
                if tickets:
                    profile.award_neon21_tickets(tickets)
                profit_tokens = profit - convertible
                capped = convertible < profit
            if profit_tokens:
                profile.add_tokens(profit_tokens, f"{REASON} WIN")
            profile.set_neon21_pending(None)
        self.result = Settlement(r.outcome, stake, self.currency, returned, profit, tickets,
                                 profit_tokens, capped, recovered)
        self.phase = self.DONE
        return self.result

    def _recover(self):
        """Settle a round left open by a crash or a forced close."""
        saved = self.profile.neon21_pending
        if saved is None:
            return
        currency = saved.get("currency")
        self.currency = currency if currency in (TOKENS, TICKETS) else TOKENS
        try:
            self.round = BlackjackRound.from_dict(saved.get("round"))
        except ValueError:
            self.round = None
            raw = saved.get("round") if isinstance(saved.get("round"), dict) else {}
            bet = raw.get("bet")
            with self.profile.batch():          # unreadable: give the stake back, never keep it
                if isinstance(bet, int) and not isinstance(bet, bool) and bet > 0:
                    self.profile.refund_tokens(bet, f"{REASON} STAKE")
                self.profile.set_neon21_pending(None)
            self.notice = "UNFINISHED ROUND WAS UNREADABLE - STAKE RETURNED"
            return
        self.phase = self.PLAYING
        if not self.round.settled:
            self.round.finish()                 # stand on the saved hand with the saved deck
        self._settle(recovered=True)
        self.notice = "UNFINISHED ROUND SETTLED"

    @staticmethod
    def is_win(outcome):
        return outcome in WINNING
