"""The calendar date the arcade runs on. Daily rewards and tasks ask a
GameClock for "today" so tests (and the debug next-day key) can move it."""
from datetime import date, timedelta


class GameClock:
    def __init__(self, today_fn=date.today):
        self._today_fn = today_fn
        self._offset = 0

    def today(self):
        return self._today_fn() + timedelta(days=self._offset)

    def advance_days(self, days=1):
        """Debug: pretend `days` more calendar days have passed."""
        self._offset += days


def parse_date(value):
    """A saved ISO date ('2026-10-05') as a date, or None if it is not one."""
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None
