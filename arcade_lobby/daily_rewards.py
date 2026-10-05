"""DailyRewardManager: the once-per-calendar-day login bonus and its streak.

The manager holds the saved state (last login, streak, last claim) and the
rules; it never touches tokens. PlayerProfile.claim_daily_reward() asks it
whether a claim is allowed and pays the result, so the payout stays inside
the profile's token transactions.

Rules (all by calendar date, never by elapsed time):
  * one claim per calendar day;
  * claiming the day after the last claim extends the streak;
  * skipping a day or more follows `on_miss` ("reset" -> day 1, "keep" -> go on);
  * past the last day of `rewards`, `after_last` is "restart" or "hold".
A clock moved back behind the last claim does not allow a second claim.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from game_clock import parse_date
from settings import DAILY_AFTER_LAST, DAILY_ON_MISS, DAILY_REWARDS


@dataclass(frozen=True)
class DailyStatus:
    can_claim: bool
    day: int        # streak day today's claim is (or, if claimed, was) worth
    tokens: int     # that day's reward
    streak: int     # claims in the current streak so far


@dataclass(frozen=True)
class DailyClaim:
    day: int
    tokens: int
    streak: int
    claimed_on: date


class DailyRewardManager:
    def __init__(self, rewards=DAILY_REWARDS, on_miss=DAILY_ON_MISS,
                 after_last=DAILY_AFTER_LAST, last_login_date=None, streak=0,
                 last_claimed=None):
        if not rewards or any(r < 0 for r in rewards):
            raise ValueError("rewards must be a non-empty list of non-negative amounts")
        if on_miss not in ("reset", "keep"):
            raise ValueError(f"on_miss must be 'reset' or 'keep', got {on_miss!r}")
        if after_last not in ("restart", "hold"):
            raise ValueError(f"after_last must be 'restart' or 'hold', got {after_last!r}")
        self.rewards = tuple(rewards)
        self.on_miss = on_miss
        self.after_last = after_last
        self.last_login_date = last_login_date
        self.streak = streak
        self.last_claimed = last_claimed

    # ------------------------------------------------------------ rules
    def reward_for_day(self, day):
        n = len(self.rewards)
        index = (day - 1) % n if self.after_last == "restart" else min(day - 1, n - 1)
        return self.rewards[index]

    def _next_day(self, today):
        if self.last_claimed is None:
            return 1
        if today - self.last_claimed == timedelta(days=1) or self.on_miss == "keep":
            return self.streak + 1
        return 1

    def can_claim(self, today):
        return self.last_claimed is None or today > self.last_claimed

    def status(self, today):
        if self.can_claim(today):
            day = self._next_day(today)
            return DailyStatus(True, day, self.reward_for_day(day), self.streak)
        return DailyStatus(False, self.streak, self.reward_for_day(self.streak), self.streak)

    def record_login(self, today):
        """Note that the game was opened on `today`."""
        if self.last_login_date is None or today > self.last_login_date:
            self.last_login_date = today

    def claim(self, today):
        """Use up today's reward. Returns a DailyClaim, or None if today's
        reward was already claimed. The state changes only on success."""
        if not self.can_claim(today):
            return None
        day = self._next_day(today)
        self.streak = day
        self.last_claimed = today
        self.record_login(today)
        return DailyClaim(day, self.reward_for_day(day), day, today)

    # ------------------------------------------------------------ save data
    def to_dict(self):
        return {
            "last_login_date": self.last_login_date.isoformat() if self.last_login_date else None,
            "daily_streak": self.streak,
            "last_daily_reward_claimed": self.last_claimed.isoformat() if self.last_claimed else None,
        }

    @classmethod
    def from_dict(cls, data, **config):
        """Rebuild from saved data; anything invalid falls back to 'never claimed'."""
        data = data if isinstance(data, dict) else {}
        streak = data.get("daily_streak")
        streak = streak if isinstance(streak, int) and not isinstance(streak, bool) and streak >= 0 else 0
        last_claimed = parse_date(data.get("last_daily_reward_claimed"))
        if last_claimed is None:
            streak = 0
        return cls(last_login_date=parse_date(data.get("last_login_date")), streak=streak,
                   last_claimed=last_claimed, **config)
