"""PinballTable: the money and the saved run of LUCKY CAT PINBALL (no pygame).

It joins one PinballWorld to one PlayerProfile and is the only code that moves currency.

  Opening the machine is free. start() charges exactly 1 Token - and only when the run really
  starts (enough Tokens, no run live, not paused / closed). The same batch writes the "paid but
  not settled" run into the profile, so a Token is never taken without a run on record.

  A run is settled exactly once. The settlement happens inside one profile.batch() that (1) tests
  that the saved run is still there, (2) removes it and (3) pays the Tickets / Token and records
  the high score; a second call finds no run and pays nothing. A run ends when the third ball
  drains, when the player leaves mid-run (the score so far pays, the unplayed balls are
  forfeited) or - after a crash or power cut - the next time the machine is opened (the score
  saved at the last ball end / pause pays). A crash can therefore cost the points of the ball that
  was in the air, never a Token and never a second payout.
"""
import pinball as pb
from settings import (PINBALL_MAX_TICKETS, PINBALL_POINTS_PER_TICKET, PINBALL_RUN_COST,
                      PINBALL_TOKEN_REWARD, PINBALL_TOKEN_SCORE)

REASON = "LUCKY CAT PINBALL"
GAME_ID = "lucky_cat_pinball"


def reward_for(score):
    """(Tickets, Tokens) a final score earns before the daily caps."""
    tickets = min(PINBALL_MAX_TICKETS, max(0, score) // PINBALL_POINTS_PER_TICKET)
    return tickets, (PINBALL_TOKEN_REWARD if score >= PINBALL_TOKEN_SCORE else 0)


class RunResult:
    __slots__ = ("score", "tickets", "tokens", "capped", "new_best", "best", "recovered", "forfeited")

    def __init__(self, score, tickets, tokens, capped, new_best, best, recovered=False, forfeited=False):
        self.score, self.tickets, self.tokens, self.capped = score, tickets, tokens, capped
        self.new_best, self.best, self.recovered, self.forfeited = new_best, best, recovered, forfeited


class PinballTable:
    def __init__(self, profile):
        self.profile = profile
        self.world = pb.PinballWorld()
        self.paused = False
        self.closed = False
        self.result = None
        self.runs = 0                   # runs started on this table
        self.settled = 0                # runs settled on this table (for the books)
        self.session_tickets = 0
        self.session_tokens = 0
        if profile.pinball_run:         # a paid run the last visit never settled (a crash): it pays now
            self.result = self._settle(profile.pinball_run["score"], recovered=True)

    # ------------------------------------------------------------ state
    @property
    def live(self):
        return self.world.phase in ("ready", "play", "bonus")

    @property
    def state(self):
        return "play" if self.live else "result" if self.result else "idle"

    def start_block_reason(self):
        """Why a start would be refused (None if it would be accepted)."""
        if self.closed or self.paused:
            return "PAUSED"
        if self.live:
            return "IN PLAY"
        if not self.profile.can_afford_tokens(PINBALL_RUN_COST):
            return "NO TOKENS"
        return None

    def can_start(self):
        return self.start_block_reason() is None

    # ------------------------------------------------------------ actions
    def start(self):
        """Spend 1 Token and begin a 3-ball run. False (nothing charged) if refused."""
        if not self.can_start():
            return False
        with self.profile.batch():
            if not self.profile.spend_tokens(PINBALL_RUN_COST, f"{REASON} RUN"):
                return False
            self.profile.set_pinball_run({"score": 0, "ball": 1})
        self.result = None
        self.runs += 1
        self.world.start_run()
        return True

    def set_flippers(self, left, right):
        if self.paused or self.closed or not self.live:
            return []
        return self.world.set_flippers(left, right)

    def hold_plunger(self, held):
        if self.paused or self.closed or not self.live:
            return []
        return self.world.hold_plunger(held)

    def update(self, dt):
        """Advance the machine. Returns the world's events."""
        if self.paused or self.closed or not self.live:
            return []
        events = self.world.advance(dt)
        for e in events:
            if e.kind == "drain":
                self._save_progress(next_ball=True)
            elif e.kind == "run_over":
                self.result = self._settle(self.world.score)
        return events

    def pause(self):
        if self.closed:
            return
        self.paused = True
        self.world.pulling = False
        self.world.pull = 0.0
        if self.live:
            self._save_progress()

    def resume(self):
        self.paused = False

    def close(self):
        """The player leaves (or the program quits). A live run is cashed out first. Safe to call twice."""
        if self.closed:
            return
        self.closed = True
        if self.live:
            self.world.end_run()
            self.result = self._settle(self.world.score, forfeited=True)

    # ------------------------------------------------------------ internals
    def _save_progress(self, next_ball=False):
        if self.profile.pinball_run is None:
            return
        ball = min(pb.BALLS, self.world.ball_no + (1 if next_ball else 0))
        self.profile.set_pinball_run({"score": self.world.score, "ball": ball})

    def _settle(self, score, recovered=False, forfeited=False):
        """Pay the run on record. Called once per run: the saved run is the 'not yet paid' flag."""
        p = self.profile
        if p.pinball_run is None:
            return self.result
        want_tickets, want_tokens = reward_for(score)
        with p.batch():
            p.set_pinball_run(None)
            tickets, tokens = p.award_pinball(want_tickets, want_tokens)
            new_best = p.record_score(GAME_ID, score)
        self.settled += 1
        self.session_tickets += tickets
        self.session_tokens += tokens
        return RunResult(score, tickets, tokens, (tickets, tokens) != (want_tickets, want_tokens),
                         new_best, p.high_score(GAME_ID), recovered, forfeited)
