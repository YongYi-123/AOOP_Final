"""The player's arcade wallet and stats (PlayerProfile) and its JSON save file
(ProfileStore).

Two currencies, never merged: TOKENS are spent to play (and won or lost in the
Lucky Corner), TICKETS are earned from minigames. All changes go through
PlayerProfile's methods - nothing else writes its fields. Every change is
announced to subscribers as a ProfileChange, which is how the HUD animates and
how ProfileStore autosaves.

The profile also owns the daily login state (DailyRewardManager) and today's
daily tasks (DailyTaskManager), so one save file holds everything.
"""
import json
import os
import random
from collections import deque, namedtuple

from daily_rewards import DailyRewardManager
from daily_tasks import DailyTaskManager
from game_clock import GameClock
from settings import (STARTING_TICKETS, STARTING_TOKENS,
                      TRANSACTION_HISTORY_SIZE)

# field: "tokens", "tickets", "games_played", "high_score", "daily", "tasks",
#        "chance_games" or "cats_petted"
# delta: signed change (for "high_score": the new score); value: new total
ProfileChange = namedtuple("ProfileChange", "field delta value")

SAVE_VERSION = 2


def _check_amount(amount):
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise ValueError(f"amount must be a non-negative int, got {amount!r}")


def _count(value, default):
    """A saved counter if it is a sane non-negative int, else the default."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return value


class PlayerProfile:
    TOKEN, TICKET = "tokens", "tickets"

    def __init__(self, tokens=STARTING_TOKENS, tickets=STARTING_TICKETS, high_scores=None,
                 total_games_played=0, lifetime_tickets_earned=0, lifetime_tokens_earned=0,
                 lifetime_tokens_spent=0, chance_games_played=0, cats_petted=0,
                 daily=None, daily_tasks=None, history=(), clock=None):
        self._tokens = tokens
        self._tickets = tickets
        self._high_scores = dict(high_scores or {})
        self._total_games_played = total_games_played
        self._lifetime_tickets_earned = lifetime_tickets_earned
        self._lifetime_tokens_earned = lifetime_tokens_earned
        self._lifetime_tokens_spent = lifetime_tokens_spent
        self._chance_games_played = chance_games_played
        self._cats_petted = cats_petted
        self.clock = clock or GameClock()
        self._daily = daily or DailyRewardManager()
        self._tasks = daily_tasks or DailyTaskManager()
        self._history = deque(history, maxlen=TRANSACTION_HISTORY_SIZE)
        self._listeners = []
        self._tasks.ensure_current(self.clock.today())

    # ------------------------------------------------------------ read-only
    @property
    def tokens(self):
        return self._tokens

    @property
    def tickets(self):
        return self._tickets

    @property
    def total_games_played(self):
        return self._total_games_played

    @property
    def lifetime_tickets_earned(self):
        return self._lifetime_tickets_earned

    @property
    def lifetime_tokens_earned(self):
        return self._lifetime_tokens_earned

    @property
    def lifetime_tokens_spent(self):
        return self._lifetime_tokens_spent

    @property
    def chance_games_played(self):
        return self._chance_games_played

    @property
    def cats_petted(self):
        return self._cats_petted

    @property
    def high_scores(self):
        return dict(self._high_scores)  # a copy: edit through record_score()

    def high_score(self, game_id):
        return self._high_scores.get(game_id, 0)

    @property
    def last_login_date(self):
        return self._daily.last_login_date

    @property
    def daily_streak(self):
        return self._daily.streak

    @property
    def last_daily_reward_claimed(self):
        return self._daily.last_claimed

    @property
    def daily_tasks(self):
        """Today's DailyTask objects (read them; change them through the
        profile's record_* and claim_task())."""
        return list(self._tasks.tasks)

    @property
    def claimable_tasks(self):
        """Today's tasks that are finished but not yet claimed."""
        return self._tasks.claimable

    @property
    def daily_tasks_date(self):
        return self._tasks.date

    @property
    def history(self):
        """Recent token changes, oldest first: dicts with date/delta/reason."""
        return [dict(entry) for entry in self._history]

    def history_lines(self):
        """The history as readable lines, e.g. '+7 TOKEN  DAILY LOGIN'."""
        return [f"{e['delta']:+d} TOKEN  {e['reason']}" for e in self._history]

    # ------------------------------------------------------------ tokens
    def can_afford_tokens(self, amount):
        _check_amount(amount)
        return self._tokens >= amount

    def add_tokens(self, amount, reason=None):
        _check_amount(amount)
        if amount:
            self._tokens += amount
            self._lifetime_tokens_earned += amount
            self._log(amount, reason)
            self._notify(self.TOKEN, amount, self._tokens)

    def spend_tokens(self, amount, reason=None):
        """Take `amount` tokens. Returns False (and changes nothing) if the
        player cannot afford it."""
        if not self.can_afford_tokens(amount):
            return False
        if amount:
            self._tokens -= amount
            self._lifetime_tokens_spent += amount
            self._log(-amount, reason)
            self._notify(self.TOKEN, -amount, self._tokens)
        return True

    def refund_tokens(self, amount, reason=None):
        """Return tokens that were spent on something that never happened.
        Undoes the spend in the lifetime totals instead of counting as earned."""
        _check_amount(amount)
        if amount:
            self._tokens += amount
            self._lifetime_tokens_spent = max(0, self._lifetime_tokens_spent - amount)
            self._log(amount, f"{reason} REFUND" if reason else "REFUND")
            self._notify(self.TOKEN, amount, self._tokens)

    def _log(self, delta, reason):
        self._history.append({"date": self.clock.today().isoformat(), "delta": delta,
                              "reason": (reason or "OTHER").upper()})

    # ------------------------------------------------------------ tickets
    def add_tickets(self, amount):
        _check_amount(amount)
        if amount:
            self._tickets += amount
            self._lifetime_tickets_earned += amount
            self._notify(self.TICKET, amount, self._tickets)
            self._task_event("tickets_earned", amount)

    # ------------------------------------------------------------ daily login
    def daily_status(self, today=None):
        """DailyStatus for `today` (default: the clock's date)."""
        return self._daily.status(today or self.clock.today())

    def record_login(self):
        """Note that the arcade was opened today."""
        before = self._daily.last_login_date
        self._daily.record_login(self.clock.today())
        if self._daily.last_login_date != before:
            self._notify("daily", 0, self._daily.streak)

    def claim_daily_reward(self):
        """Claim today's login bonus. Returns the DailyClaim, or None if it
        was already claimed today. The tokens are paid exactly once."""
        claim = self._daily.claim(self.clock.today())
        if claim is None:
            return None
        self.add_tokens(claim.tokens, "DAILY LOGIN")
        self._notify("daily", claim.tokens, claim.streak)   # saves even for a 0 reward
        return claim

    # ------------------------------------------------------------ daily tasks
    def sync_daily_tasks(self):
        """Roll new tasks if the calendar date changed. Returns True if it did."""
        changed = self._tasks.ensure_current(self.clock.today())
        if changed:
            self._notify("tasks", 0, 0)
        return changed

    def reset_daily_tasks(self):
        """Debug: replace today's tasks with a fresh random set."""
        self._tasks.reset(self.clock.today(), random.Random())
        self._notify("tasks", 0, 0)

    def claim_task(self, task_id):
        """Claim a finished task. Returns the tokens paid (0 if the task is
        unknown, unfinished or already claimed)."""
        self.sync_daily_tasks()
        reward = self._tasks.claim(task_id)
        if reward:
            self.add_tokens(reward, "DAILY TASK")
            self._notify("tasks", reward, len(self._tasks.claimable))
        return reward

    def _task_event(self, event, amount=1, key=None, game_id=None):
        self.sync_daily_tasks()
        if self._tasks.on_event(event, amount, key, game_id):
            self._notify("tasks", amount, len(self._tasks.claimable))

    # ------------------------------------------------------------ stats
    def record_game_played(self, game_id=None):
        self._total_games_played += 1
        self._notify("games_played", 1, self._total_games_played)
        self._task_event("game_played", game_id=game_id)

    def record_chance_game_played(self):
        self._chance_games_played += 1
        self._notify("chance_games", 1, self._chance_games_played)

    def record_cat_petted(self):
        self._cats_petted += 1
        self._notify("cats_petted", 1, self._cats_petted)
        self._task_event("cat_petted")

    def record_machine_visit(self, machine_id):
        self._task_event("machine_visited", key=machine_id)

    def record_score(self, game_id, score):
        """Keep `score` if it beats the stored best. Returns True if it did."""
        _check_amount(score)
        best = self._high_scores.get(game_id)
        if best is not None and score <= best:
            return False
        self._high_scores[game_id] = score
        self._notify("high_score", score, score)
        if score > 0:
            self._task_event("high_score", game_id=game_id)
        return True

    # ------------------------------------------------------------ observers
    def subscribe(self, callback):
        """callback(ProfileChange) is called after every change."""
        self._listeners.append(callback)

    def unsubscribe(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self, field, delta, value):
        change = ProfileChange(field, delta, value)
        for callback in list(self._listeners):
            callback(change)

    # ------------------------------------------------------------ (de)serialise
    def to_dict(self):
        return {
            "version": SAVE_VERSION,
            "tokens": self._tokens,
            "tickets": self._tickets,
            "total_games_played": self._total_games_played,
            "lifetime_tickets_earned": self._lifetime_tickets_earned,
            "lifetime_tokens_earned": self._lifetime_tokens_earned,
            "lifetime_tokens_spent": self._lifetime_tokens_spent,
            "chance_games_played": self._chance_games_played,
            "cats_petted": self._cats_petted,
            "high_scores": dict(self._high_scores),
            **self._daily.to_dict(),
            "daily_tasks": self._tasks.to_dict(),
            "transaction_history": list(self._history),
        }

    @classmethod
    def from_dict(cls, data, clock=None):
        """Build a profile from saved data; any missing or invalid field falls
        back to its default instead of failing. A version-1 save kept its
        tokens under "coins": they are carried over as tokens."""
        if not isinstance(data, dict):
            data = {}
        scores = data.get("high_scores")
        scores = {k: v for k, v in scores.items()
                  if isinstance(k, str) and _count(v, None) is not None} if isinstance(scores, dict) else {}
        tokens = _count(data.get("tokens"), None)
        if tokens is None:
            tokens = _count(data.get("coins"), STARTING_TOKENS)
        tickets = _count(data.get("tickets"), STARTING_TICKETS)
        history = data.get("transaction_history")
        history = [{"date": str(e.get("date", "")), "delta": e["delta"], "reason": str(e.get("reason", "OTHER"))}
                   for e in history if isinstance(e, dict) and isinstance(e.get("delta"), int)
                   and not isinstance(e["delta"], bool)] if isinstance(history, list) else []
        return cls(
            tokens=tokens,
            tickets=tickets,
            high_scores=scores,
            total_games_played=_count(data.get("total_games_played"), 0),
            lifetime_tickets_earned=max(tickets, _count(data.get("lifetime_tickets_earned"), tickets)),
            lifetime_tokens_earned=_count(data.get("lifetime_tokens_earned"), 0),
            lifetime_tokens_spent=_count(data.get("lifetime_tokens_spent"), 0),
            chance_games_played=_count(data.get("chance_games_played"), 0),
            cats_petted=_count(data.get("cats_petted"), 0),
            daily=DailyRewardManager.from_dict(data),
            daily_tasks=DailyTaskManager.from_dict(data.get("daily_tasks")),
            history=history,
            clock=clock,
        )


class ProfileStore:
    """Loads/saves a PlayerProfile as JSON. Never raises on bad files: a
    missing file starts a new profile, a corrupted one is moved aside to
    `<file>.corrupt` and replaced by a new profile."""

    def __init__(self, path, clock=None):
        self.path = path
        self.clock = clock

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("save data is not a JSON object")
        except FileNotFoundError:
            profile = PlayerProfile(clock=self.clock)
            self.save(profile)          # create the file right away
            return profile
        except (OSError, ValueError) as e:  # JSONDecodeError/UnicodeDecodeError are ValueErrors
            print(f"[save] could not read {self.path} ({e}); starting a new profile")
            self._move_aside()
            profile = PlayerProfile(clock=self.clock)
            self.save(profile)
            return profile
        profile = PlayerProfile.from_dict(data, clock=self.clock)
        if data.get("version") != SAVE_VERSION or "coins" in data:
            self.save(profile)          # an older save: rewrite it in the new schema
        return profile

    def save(self, profile):
        """Write atomically (temp file + rename) so a crash mid-write cannot
        leave a half-written save. Returns False if the write failed."""
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, indent=4)
            os.replace(tmp, self.path)
        except OSError as e:
            print(f"[save] could not write {self.path}: {e}")
            return False
        return True

    def autosave(self, profile):
        """Save `profile` after every change from now on."""
        profile.subscribe(lambda _change: self.save(profile))

    def _move_aside(self):
        try:
            os.replace(self.path, self.path + ".corrupt")
        except OSError:
            pass
