"""The player's arcade wallet and stats (PlayerProfile) and its JSON save file
(ProfileStore).

All currency changes go through PlayerProfile's methods - nothing else writes
to its fields. Every change is announced to subscribers as a ProfileChange,
which is how the HUD animates and how ProfileStore autosaves.
"""
import json
import os
from collections import namedtuple

from settings import STARTING_COINS, STARTING_TICKETS

# field: "coins", "tickets", "games_played" or "high_score"
# delta: signed change (for "high_score": the new score); value: new total
ProfileChange = namedtuple("ProfileChange", "field delta value")

SAVE_VERSION = 1


def _check_amount(amount):
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise ValueError(f"amount must be a non-negative int, got {amount!r}")


def _count(value, default):
    """A saved counter if it is a sane non-negative int, else the default."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return value


class PlayerProfile:
    COIN, TICKET = "coins", "tickets"

    def __init__(self, coins=STARTING_COINS, tickets=STARTING_TICKETS, high_scores=None,
                 total_games_played=0, lifetime_tickets_earned=0):
        self._coins = coins
        self._tickets = tickets
        self._high_scores = dict(high_scores or {})
        self._total_games_played = total_games_played
        self._lifetime_tickets_earned = lifetime_tickets_earned
        self._listeners = []

    # ------------------------------------------------------------ read-only
    @property
    def coins(self):
        return self._coins

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
    def high_scores(self):
        return dict(self._high_scores)  # a copy: edit through record_score()

    def high_score(self, game_id):
        return self._high_scores.get(game_id, 0)

    # ------------------------------------------------------------ coins
    def can_afford_coins(self, amount):
        _check_amount(amount)
        return self._coins >= amount

    def add_coins(self, amount):
        _check_amount(amount)
        if amount:
            self._coins += amount
            self._notify(self.COIN, amount, self._coins)

    def spend_coins(self, amount):
        """Take `amount` coins. Returns False (and changes nothing) if the
        player cannot afford it."""
        if not self.can_afford_coins(amount):
            return False
        if amount:
            self._coins -= amount
            self._notify(self.COIN, -amount, self._coins)
        return True

    # ------------------------------------------------------------ tickets
    def add_tickets(self, amount):
        _check_amount(amount)
        if amount:
            self._tickets += amount
            self._lifetime_tickets_earned += amount
            self._notify(self.TICKET, amount, self._tickets)

    # ------------------------------------------------------------ stats
    def record_game_played(self):
        self._total_games_played += 1
        self._notify("games_played", 1, self._total_games_played)

    def record_score(self, game_id, score):
        """Keep `score` if it beats the stored best. Returns True if it did."""
        _check_amount(score)
        best = self._high_scores.get(game_id)
        if best is not None and score <= best:
            return False
        self._high_scores[game_id] = score
        self._notify("high_score", score, score)
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
            "coins": self._coins,
            "tickets": self._tickets,
            "total_games_played": self._total_games_played,
            "lifetime_tickets_earned": self._lifetime_tickets_earned,
            "high_scores": dict(self._high_scores),
        }

    @classmethod
    def from_dict(cls, data):
        """Build a profile from saved data; any missing or invalid field falls
        back to its default instead of failing."""
        if not isinstance(data, dict):
            data = {}
        scores = data.get("high_scores")
        scores = {k: v for k, v in scores.items()
                  if isinstance(k, str) and _count(v, None) is not None} if isinstance(scores, dict) else {}
        tickets = _count(data.get("tickets"), STARTING_TICKETS)
        return cls(
            coins=_count(data.get("coins"), STARTING_COINS),
            tickets=tickets,
            high_scores=scores,
            total_games_played=_count(data.get("total_games_played"), 0),
            lifetime_tickets_earned=max(tickets, _count(data.get("lifetime_tickets_earned"), tickets)),
        )


class ProfileStore:
    """Loads/saves a PlayerProfile as JSON. Never raises on bad files: a
    missing file starts a new profile, a corrupted one is moved aside to
    `<file>.corrupt` and replaced by a new profile."""

    def __init__(self, path):
        self.path = path

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("save data is not a JSON object")
        except FileNotFoundError:
            profile = PlayerProfile()
            self.save(profile)          # create the file right away
            return profile
        except (OSError, ValueError) as e:  # JSONDecodeError/UnicodeDecodeError are ValueErrors
            print(f"[save] could not read {self.path} ({e}); starting a new profile")
            self._move_aside()
            profile = PlayerProfile()
            self.save(profile)
            return profile
        return PlayerProfile.from_dict(data)

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
