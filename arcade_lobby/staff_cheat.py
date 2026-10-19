"""The rules behind the BROKEN CAT-CADE's MOCHI'S STAFF PANEL (the screens are in staff_ui.py).

Deliberately small and separate from everything story-related: it knows nothing about the NEON VEND-O-MATIC's
hidden code sequence, its terminal or the story flags. A staff grant changes one thing - the
acting player's Token or Ticket balance - through PlayerProfile.grant_staff_currency, which leaves every game
statistic, daily cap and payout alone and writes the save once.
"""
import pygame

from player_profile import STAFF_BALANCE_CAP, PlayerProfile

PASSWORD = "515106"
MAX_INPUT = 16                      # a few more letters than the password, so a typo can be seen and fixed
GRANT_AMOUNTS = (10, 100, 1000)
CURRENCIES = (PlayerProfile.TOKEN, PlayerProfile.TICKET)
BALANCE_CAP = STAFF_BALANCE_CAP

# Friendly, silly answers to a wrong password. They cycle in order; none gives the password away.
WRONG_LINES = ("ACCESS DENIED. PLEASE TRY PURRING.", "NOPE. THE CAT-CADE SNIFFED THAT.",
               "WRONG PASSWORD. THE OPERATOR IS NAPPING.", "HISS. THAT IS NOT THE WORD.",
               "ERROR 404: PASSWORD NOT FOUND.", "A CAT WALKED ON THE KEYBOARD. TRY AGAIN.")
HINT_AFTER = 3                      # wrong attempts before the machine mutters a clue
HINT_LINE = "OPERATOR NOTE: 5151 + 06"


class PasswordEntry:
    """The text box of the maintenance screen: letters and digits only, upper-cased, length-limited.
    Pure logic (no drawing, no scene), so it is easy to test."""

    def __init__(self, password=PASSWORD, limit=MAX_INPUT):
        self.password = password
        self.limit = limit
        self.text = ""
        self.attempts = 0

    @staticmethod
    def char_for(event):
        """The character a KEYDOWN types, or None. The keyboard layout's own character wins (so an AZERTY 'a' is an
        'a'); without one, the key's name. Only A-Z and 0-9 count: no other key can ever type anything."""
        ch = (getattr(event, "unicode", "") or "").upper()
        if len(ch) == 1 and ch.isascii() and ch.isalnum():
            return ch
        key = event.key
        if pygame.K_a <= key <= pygame.K_z:
            return chr(ord("A") + key - pygame.K_a)
        if pygame.K_0 <= key <= pygame.K_9:
            return chr(ord("0") + key - pygame.K_0)
        return None

    def type(self, ch):
        """Add one character. Returns False (and changes nothing) when the box is full or `ch` is not allowed."""
        if not ch or len(ch) != 1 or not ch.isascii() or not ch.isalnum() or len(self.text) >= self.limit:
            return False
        self.text += ch.upper()
        return True

    def backspace(self):
        had = bool(self.text)
        self.text = self.text[:-1]
        return had

    def clear(self):
        had = bool(self.text)
        self.text = ""
        return had

    def submit(self):
        """Check the text (case-insensitively). A right answer returns True and keeps the box; a wrong one counts as
        an attempt and empties the box."""
        if self.text.strip().upper() == self.password:
            return True
        self.attempts += 1
        self.text = ""
        return False

    def wrong_line(self):
        """The friendly answer to the latest wrong attempt."""
        return WRONG_LINES[(max(1, self.attempts) - 1) % len(WRONG_LINES)]

    @property
    def wants_hint(self):
        return self.attempts >= HINT_AFTER


class StaffResult:
    __slots__ = ("code", "currency", "requested", "added")

    def __init__(self, code, currency, requested, added):
        self.code, self.currency, self.requested, self.added = code, currency, requested, added

    @property
    def ok(self):
        return self.code in ("ok", "partial")


class StaffService:
    """Pays the staff panel's rewards to ONE profile: the player who opened the screen."""

    def __init__(self, profile):
        self.profile = profile

    def balance(self, currency):
        return self.profile.tokens if currency == PlayerProfile.TOKEN else self.profile.tickets

    def grant(self, currency, amount):
        """Add `amount` (one of GRANT_AMOUNTS) of `currency`. Codes: "ok" (all of it), "partial" (the wallet's cap
        cut it short), "full" (already at the cap, nothing added), "invalid" (not a staff amount / currency)."""
        if currency not in CURRENCIES or isinstance(amount, bool) or amount not in GRANT_AMOUNTS:
            return StaffResult("invalid", currency, amount, 0)
        added = self.profile.grant_staff_currency(currency, amount)
        code = "full" if added == 0 else "ok" if added == amount else "partial"
        return StaffResult(code, currency, amount, added)
