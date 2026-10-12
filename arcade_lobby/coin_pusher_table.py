"""CoinPusherTable: the money and the saved board of NEON COIN PUSHER (no pygame).

It joins one PusherWorld to one PlayerProfile and is the only code that moves currency.

  Opening the machine is free. drop() charges exactly 1 Token - and only when the coin really
  goes in (enough Tokens, room on the stage, not paused / closed, past the short cooldown).
  A coin that crosses the front edge is settled in the very step the world reports it; the world
  removes it first, so a coin can be paid only once. Coins off the sides pay nothing.

Board lifecycle (the anti-farming rule): the board belongs to the PROFILE and is saved with it.
The first visit builds it from a per-profile random seed and saves it at once; after that the
same coins are loaded every time. Closing, crashing and reopening therefore never re-rolls it.
Every event that changes what is owed - a drop (Token spent + coin added), a payout, a side
loss, a restock - is saved together with the board in ONE profile.batch(), so the file on disk
always holds a board that matches the Tokens and Tickets in it. Pure motion is not saved; a
crash loses at most how far the coins had slid since the last event (never a coin, never a
reward). Leaving lands any coin still falling from the chute and saves.

Restock: when fewer than RESTOCK_BELOW coins are in play the machine adds one coin every
RESTOCK_EVERY seconds. Its kind comes from a Random seeded by (profile seed, restock counter),
and the counter is saved with the coin, so the sequence cannot be re-rolled by reopening.
"""
import random

import coin_pusher as cp
from settings import (COIN_PUSHER_CAPPED_TOKENS, COIN_PUSHER_DROP_COST,
                      COIN_PUSHER_GOLDEN_TICKETS, COIN_PUSHER_NORMAL_TOKENS,
                      COIN_PUSHER_SILVER_TOKENS)

REASON = "COIN PUSHER"
DROP_COOLDOWN = 0.30            # seconds between two accepted drops (a held / mashed key cannot machine-gun)
CHUTE_SPEED = 62.0              # board units per second


class Payout:
    """What one collected coin paid (for the LED display and the pop-ups)."""
    __slots__ = ("kind", "tokens", "tickets", "capped", "x")

    def __init__(self, kind, tokens=0, tickets=0, capped=False, x=0.0):
        self.kind, self.tokens, self.tickets, self.capped, self.x = kind, tokens, tickets, capped, x

    @property
    def text(self):
        parts = []
        if self.tokens:
            parts.append(f"+{self.tokens} TOKEN" + ("S" if self.tokens != 1 else ""))
        if self.tickets:
            parts.append(f"+{self.tickets} TICKET" + ("S" if self.tickets != 1 else ""))
        return " ".join(parts) or "NOTHING"


class CoinPusherTable:
    def __init__(self, profile, seed=None):
        self.profile = profile
        self.paused = False
        self.closed = False
        self.chute_x = cp.W / 2
        self.cooldown = 0.0
        self.session_tokens = 0         # won this visit
        self.session_tickets = 0
        self.session_drops = 0
        self.collected = 0              # coins paid / lost since this table was opened (for the books)
        self.lost = 0
        self.restock_timer = 0.0
        self.notice = None
        state = profile.pusher_state
        world = cp.PusherWorld.from_snapshot(state["board"]) if state else None
        valid_seed = state and isinstance(state.get("seed"), int) and not isinstance(state.get("seed"), bool)
        if world is None or not valid_seed:
            self.seed = seed if seed is not None else random.SystemRandom().getrandbits(48)
            self.stock = 0
            self.world = cp.initial_board(self.seed)
            self._save()                # a new board is saved at once: it cannot be re-rolled by reopening
        else:
            self.seed = state["seed"]
            stock = state.get("stock")
            self.stock = stock if isinstance(stock, int) and not isinstance(stock, bool) and stock >= 0 else 0
            self.world = world
            if self.world.drops:        # coins that were still falling when the game stopped land now
                self.world.flush_drops()
        self.drop_log = []              # recent Payouts for the display (newest last)

    # ------------------------------------------------------------ state
    @property
    def tokens(self):
        return self.profile.tokens

    def can_drop(self):
        return (not self.paused and not self.closed and self.cooldown <= 0
                and self.profile.can_afford_tokens(COIN_PUSHER_DROP_COST) and self.world.can_accept())

    def drop_block_reason(self):
        """Why a drop would be refused (None if it would be accepted)."""
        if self.closed or self.paused:
            return "PAUSED"
        if not self.profile.can_afford_tokens(COIN_PUSHER_DROP_COST):
            return "NO TOKENS"
        if not self.world.can_accept():
            return "MACHINE FULL"
        if self.cooldown > 0:
            return "WAIT"
        return None

    def move_chute(self, direction, dt):
        if self.paused or self.closed or not direction:
            return
        self.chute_x = min(cp.W - cp.R, max(cp.R, self.chute_x + direction * CHUTE_SPEED * dt))

    # ------------------------------------------------------------ actions
    def drop(self):
        """Spend 1 Token and release a coin at the chute. False (nothing charged) if refused."""
        if not self.can_drop():
            return False
        with self.profile.batch():
            if not self.profile.spend_tokens(COIN_PUSHER_DROP_COST, f"{REASON} COIN"):
                return False
            self.world.add_drop(self.chute_x)
            self.cooldown = DROP_COOLDOWN
            self.session_drops += 1
            self._save()
        return True

    def update(self, dt):
        """Advance the machine. Returns (events, payouts)."""
        if self.paused or self.closed:
            return [], []
        self.cooldown = max(0.0, self.cooldown - dt)
        events = self.world.advance(dt)
        payouts, changed = [], False
        with self.profile.batch():
            for e in events:
                if e.kind == "tray":
                    payouts.append(self._settle(e.coin))
                    self.collected += 1
                    changed = True
                elif e.kind == "lost":
                    self.lost += 1
                    changed = True
            if self._restock(dt):
                changed = True
            if changed:
                self._save()
        self.drop_log.extend(payouts)
        del self.drop_log[:-6]
        return events, payouts

    def pause(self):
        self.paused = True
        self._save()

    def resume(self):
        self.paused = False

    def close(self):
        """The player leaves (or the program quits). Safe to call more than once."""
        if self.closed:
            return
        self.world.flush_drops()
        self.closed = True
        self._save()

    # ------------------------------------------------------------ internals
    def _settle(self, coin):
        """Pay one collected coin. Called once per coin: the world removed it when it fell."""
        p = self.profile
        tokens = tickets = 0
        capped = False
        if coin.kind == cp.NORMAL:
            tokens = COIN_PUSHER_NORMAL_TOKENS
        elif coin.kind == cp.SILVER:
            tokens = COIN_PUSHER_SILVER_TOKENS
        elif coin.kind == cp.GOLDEN:
            tickets = COIN_PUSHER_GOLDEN_TICKETS
        else:
            currency, amount = coin.prize or cp.MYSTERY_PRIZES[0]
            tokens, tickets = (amount, 0) if currency == "tokens" else (0, amount)
        if tickets and not p.award_pusher_tickets(tickets):
            # over the daily Ticket cap: a smaller Token prize instead (a part of the cap may be left)
            room = p.pusher_ticket_room()
            if room:
                p.award_pusher_tickets(room)
            capped, tokens, tickets = True, tokens + COIN_PUSHER_CAPPED_TOKENS, room
        if tokens:
            p.add_tokens(tokens, f"{REASON} {coin.kind.upper()}")
        self.session_tokens += tokens
        self.session_tickets += tickets
        return Payout(coin.kind, tokens, tickets, capped, coin.x)

    def _restock(self, dt):
        if self.world.count >= cp.RESTOCK_BELOW:
            self.restock_timer = 0.0
            return False
        self.restock_timer += dt
        if self.restock_timer < cp.RESTOCK_EVERY or not self.world.can_accept():
            return False
        self.restock_timer = 0.0
        rng = random.Random(f"coin-pusher-stock:{self.seed}:{self.stock}")
        kind, prize = cp.make_coin_spec(rng)
        self.world.add_drop(rng.uniform(cp.R + 4, cp.W - cp.R - 4), kind, prize, paid=False)
        self.stock += 1
        return True

    def _save(self):
        self.profile.set_pusher_state({"seed": self.seed, "stock": self.stock,
                                            "board": self.world.snapshot()})
