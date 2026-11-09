"""TRIAL 01 - THE GOLDEN AGE ("The Room Where It Began"): the rules of the escape room, with no drawing in it.

Everything here is plain data and small state machines, so the whole puzzle chain can be tested without a window:

    Circuit         the 4x4 fuse board behind the power box (rotate tiles until the current reaches the output)
    morse_pulses    the telephone's message as timed tones, and MorsePlayback which walks through them frame by frame
    Desktop         the old computer's menu (PLAY GAME / HIGH SCORES / LOCKED FILES / EXIT); the game itself is happy_breakout.py
    TrialRun        what has happened in the room so far (power, drawer, cabinet, journal, boot disk, computer), the
                    Trial Inventory, the clue list and the current objective

The scene (golden_age_scene.py) draws and plays; the story only hears about the end (event "secret_trial_done" with
key "trial_01", see QuestManager.handle), so leaving halfway records nothing.

Nothing here (or anywhere in this trial) reveals who PLAYER_000 is: the mystery is kept.
"""
from dataclasses import dataclass, field

import golden_age_content as C
from golden_age_content import (ADMIN_CARD, COMPUTER_AFTER, COMPUTER_DEAD, COMPUTER_STANDBY, DISK_FOUND, HINTS,  # noqa: F401 (re-exported)
                                JOURNAL_PAGES, JOURNAL_REACTION, OPENING, PHONE_DEAD, POWER_RESTORED, CABINET_DEAD)

TRIAL_ID = "trial_01"
MEMORY_FRAGMENT_FLAG = "memory_fragment_01"        # in the story's flags: set once, by the first completion
INTRO_FLAG = "trial01_intro"                         # in the story's flags: the opening cutscene has played
BREAKOUT_FLAG = "trial01_breakout"                   # in the story's flags: HAPPY BREAKOUT.EXE has been cleared (kept for good)
ANSWER = "SHELF"

# ------------------------------------------------------------------ Morse code
MORSE_UNIT = 0.15                       # seconds in one unit (audio_synth.MORSE_UNIT says the same: a test compares them)
MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....", "I": "..",
    "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
}
DOT, DASH = ".", "-"
GAP_ELEMENT, GAP_LETTER = 1, 3          # silent units between tones of one letter / between two letters (the standard timing)
LEAD_IN = 0.45                          # a beat of silence before the first tone, so the lamp is seen to wake up first


def encode(word):
    """'SHELF' -> '... / .... / . / .-.. / ..-.'  (letters separated by ' / ')."""
    return " / ".join(MORSE[ch] for ch in word.upper())


@dataclass(frozen=True)
class Pulse:
    start: float                        # seconds from the start of the message
    length: float                       # how long the tone (and the lamp) lasts
    symbol: str                         # "." or "-"
    letter: int                         # which letter of the word it belongs to

    @property
    def end(self):
        return self.start + self.length

    @property
    def sound(self):
        return "morse_dot" if self.symbol == DOT else "morse_dash"


def morse_pulses(word=ANSWER, unit=MORSE_UNIT, lead_in=LEAD_IN):
    """The word as timed tones. A dot lasts 1 unit, a dash 3; 1 silent unit between the tones of a letter and 3 between
    letters."""
    out, t = [], lead_in
    for i, ch in enumerate(word.upper()):
        for j, symbol in enumerate(MORSE[ch]):
            units = 1 if symbol == DOT else 3
            out.append(Pulse(round(t, 6), round(units * unit, 6), symbol, i))
            t += (units + (GAP_ELEMENT if j < len(MORSE[ch]) - 1 else GAP_LETTER)) * unit
    return tuple(out)


def morse_duration(word=ANSWER, unit=MORSE_UNIT, lead_in=LEAD_IN):
    pulses = morse_pulses(word, unit, lead_in)
    return pulses[-1].end if pulses else 0.0


class MorsePlayback:
    """One telephone transmission. `advance(dt)` moves its clock and returns the pulses that STARTED during that step
    (once each, in order, whatever the frame rate), so the tone and the lamp can never drift apart: the scene plays the
    tone for exactly the pulses this returns, and `lit` is true exactly while a pulse is sounding."""

    def __init__(self, word=ANSWER, unit=MORSE_UNIT, lead_in=LEAD_IN):
        self.pulses = morse_pulses(word, unit, lead_in)
        self.duration = morse_duration(word, unit, lead_in)
        self.t = 0.0
        self._next = 0
        self.playing = True

    @property
    def lit(self):
        return self.playing and any(p.start <= self.t < p.end for p in self.pulses)

    @property
    def current(self):
        return next((p for p in self.pulses if p.start <= self.t < p.end), None)

    @property
    def finished(self):
        return not self.playing

    def advance(self, dt):
        if not self.playing:
            return []
        self.t += dt
        started = []
        while self._next < len(self.pulses) and self.pulses[self._next].start <= self.t:
            started.append(self.pulses[self._next])
            self._next += 1
        if self.t >= self.duration:
            self.playing = False
        return started


# ------------------------------------------------------------------ the fuse board
N, E, S, W = 0, 1, 2, 3
DIRS = (N, E, S, W)
STEP = {N: (-1, 0), E: (0, 1), S: (1, 0), W: (0, -1)}      # (row, column) offsets
BASE = {"straight": (N, S), "corner": (N, E)}               # openings at rotation 0; one rotation turns them 90 degrees clockwise


def opposite(d):
    return (d + 2) % 4


def openings(kind, rot):
    return frozenset((d + rot) % 4 for d in BASE[kind])


# The current comes in from the west edge of (0, 0) and must leave through the east edge of (3, 3).
SIZE = 4
SOURCE, OUTPUT = (0, 0), (3, 3)
# the one intended route and the shape each of its tiles has to be: (row, col) -> (comes in from, goes out to)
ROUTE = {(0, 0): (W, E), (0, 1): (W, E), (0, 2): (W, S), (1, 2): (N, S), (2, 2): (N, W),
         (2, 1): (E, S), (3, 1): (N, E), (3, 2): (W, E), (3, 3): (W, E)}
# the other seven tiles are loose decoys (any turn of them is fine)
DECOYS = {(0, 3): "corner", (1, 0): "straight", (1, 1): "corner", (1, 3): "straight",
          (2, 0): "corner", (2, 3): "corner", (3, 0): "straight"}
START_ROTS = {(0, 0): 1, (0, 1): 1, (0, 2): 0, (1, 2): 1, (2, 2): 2, (2, 1): 3, (3, 1): 1, (3, 2): 1, (3, 3): 1,
              (0, 3): 2, (1, 0): 0, (1, 1): 3, (1, 3): 1, (2, 0): 1, (2, 3): 0, (3, 0): 1}


def _kind_for(pair):
    a, b = pair
    return "straight" if opposite(a) == b else "corner"


def _solution_rot(kind, pair):
    return next(r for r in range(4) if openings(kind, r) == frozenset(pair))


class Circuit:
    """A 4x4 board of tiles that can be turned. `rotate(row, col)` turns one tile a quarter clockwise; `powered()` follows
    the current from the source; `solved` is true once it reaches the output. There is always a way to solve it
    (`solution()` is that way), it is not solved at the start, and one turn is never enough."""

    def __init__(self, rots=None):
        self.kinds = {cell: _kind_for(pair) for cell, pair in ROUTE.items()}
        self.kinds.update(DECOYS)
        self.rots = dict(START_ROTS if rots is None else rots)
        self.turns = 0                  # how many times the player turned a tile

    def rotate(self, row, col, times=1):
        self.rots[(row, col)] = (self.rots[(row, col)] + times) % 4
        self.turns += times

    def openings_of(self, cell):
        return openings(self.kinds[cell], self.rots[cell])

    def solution(self):
        """{cell: rotation} of one working board (the route's tiles; decoys keep their rotation)."""
        out = dict(self.rots)
        for cell, pair in ROUTE.items():
            out[cell] = _solution_rot(self.kinds[cell], pair)
        return out

    def powered(self):
        """The set of cells the current reaches (it enters the source tile through its west edge)."""
        if W not in self.openings_of(SOURCE):
            return set()
        lit, todo = {SOURCE}, [SOURCE]
        while todo:
            r, c = todo.pop()
            for d in self.openings_of((r, c)):
                dr, dc = STEP[d]
                nxt = (r + dr, c + dc)
                if nxt in lit or not (0 <= nxt[0] < SIZE and 0 <= nxt[1] < SIZE):
                    continue
                if opposite(d) in self.openings_of(nxt):
                    lit.add(nxt)
                    todo.append(nxt)
        return lit

    @property
    def solved(self):
        return OUTPUT in self.powered() and E in self.openings_of(OUTPUT)

    def turns_needed(self):
        """The fewest quarter turns that solve it from the present board (each route tile on its own; a straight piece
        looks the same after a half turn, so it needs at most one)."""
        total = 0
        for cell, pair in ROUTE.items():
            off = (_solution_rot(self.kinds[cell], pair) - self.rots[cell]) % 4
            total += off % 2 if self.kinds[cell] == "straight" else off
        return total


# ------------------------------------------------------------------ the old computer
BOOT_LINES = ("BOOTING...", "CHECKING DISK...", "LOADING ARCHIVE...")


class Desktop:
    """The computer's menu once the disk has booted: [1] PLAY GAME  [2] HIGH SCORES  [3] LOCKED FILES  [4] EXIT.
    `choose(cleared)` says what the choice does: "play", "scores", "locked" (not yet: the game has not been cleared),
    "files" (open the locked files) or "exit"."""

    def __init__(self):
        self.cursor = 0
        self.message = ""

    @property
    def items(self):
        return C.DESKTOP_MENU

    def move(self, delta):
        self.cursor = (self.cursor + delta) % len(self.items)

    def pick(self, number):
        """The number keys 1-4."""
        if 1 <= number <= len(self.items):
            self.cursor = number - 1
            return True
        return False

    def choose(self, cleared):
        self.message = ""
        label = self.items[self.cursor]
        if label == "PLAY GAME":
            return "play"
        if label == "HIGH SCORES":
            return "scores"
        if label == "EXIT":
            return "exit"
        if not cleared:
            self.message = " ".join(C.LOCKED_DENIED)
            return "locked"
        return "files"


# ------------------------------------------------------------------ the run
OBJECTIVE_ORDER = ("power", "phone", "cabinet", "bookshelf", "computer", "done")      # (internal: the player is never told)

# What a stage says when asked too early
COMPUTER_STANDBY_NODISK = C.COMPUTER_STANDBY

DRAWER_PAPER = ("A folded paper lies in the desk drawer, along with a worn chart.",
                'It reads: "When words fail, patterns speak."')
CABINET_NOTE = ("The best ideas were never locked in drawers.",
                "Look where stories sleep.")


@dataclass
class Clue:
    key: str
    title: str
    lines: tuple


CLUES = {
    "paper": Clue("paper", "PAPER FROM THE DRAWER", ('"When words fail, patterns speak."',)),
    "chart": Clue("chart", "MORSE CODE CHART", ()),             # drawn as a chart, not text
    "note": Clue("note", "NOTE FROM THE CABINET", CABINET_NOTE),
    "journal": Clue("journal", "THE UNTITLED NOTEBOOK", ()),
}


@dataclass
class TrialRun:
    """Everything that has happened in the room. It lives with the hub while the game runs (so leaving and coming back
    carries on where you were) and is thrown away when the trial is completed (so a replay starts from the dark room).
    Looking at the room's ordinary things (the window, the noodles, the books ...) never changes any of the progress here."""
    power: bool = False
    circuit: Circuit = field(default_factory=Circuit)
    phone_plays: int = 0
    drawer_opened: bool = False
    cabinet_open: bool = False
    wrong_codes: int = 0
    journal_found: bool = False
    journal_read: bool = False
    inventory: list = field(default_factory=list)       # the Trial Inventory (not the shop's bag; never touches the wallet)
    clues: list = field(default_factory=list)            # keys of CLUES, in the order they were found
    computer_done: bool = False
    breakout_cleared: bool = False
    plushie_seen: bool = False
    inspected: dict = field(default_factory=dict)        # object key -> how many times it was looked at (flavour only)
    books_read: list = field(default_factory=list)       # shelf book keys that were opened
    hints: dict = field(default_factory=dict)            # objective -> how many hints were asked for
    intro_played: bool = False

    BOOT_DISK = "OLD BOOT DISK"

    # ------------------------------------------------------------ progress (never shown to the player as a goal)
    @property
    def objective(self):
        if self.computer_done:
            return "done"
        if not self.power:
            return "power"
        if self.cabinet_open:
            return "computer" if self.has_boot_disk else "bookshelf"
        return "cabinet" if self.phone_plays else "phone"

    @property
    def has_boot_disk(self):
        return self.BOOT_DISK in self.inventory

    def add_clue(self, key):
        if key not in self.clues:
            self.clues.append(key)
            return True
        return False

    # ------------------------------------------------------------ steps
    def restore_power(self):
        """The fuse board is solved: the lights, telephone and cabinet come alive. Only a solved board does it."""
        if self.power:
            return False
        if not self.circuit.solved:
            return False
        self.power = True
        return True

    def play_phone(self):
        """The telephone was used. False (and nothing happens) while there is no power."""
        if not self.power:
            return False
        self.phone_plays += 1
        return True

    def open_drawer(self):
        """The desk drawer: the paper and the chart. Always there to look at; True the first time."""
        first = not self.drawer_opened
        self.drawer_opened = True
        self.add_clue("paper")
        self.add_clue("chart")
        return first

    def try_cabinet(self, code):
        """Type a password into the cabinet. Returns "locked" (no power), "open", "again" (already open) or "wrong"."""
        if not self.power:
            return "locked"
        if self.cabinet_open:
            return "again"
        if code.strip().upper() == ANSWER:
            self.cabinet_open = True
            self.add_clue("note")
            return "open"
        self.wrong_codes += 1
        return "wrong"

    # ---- the bookshelf: a browser of books; one of them (the plain notebook) only turns up once the cabinet's note is read
    def shelf(self):
        """The keys of the books on the shelf now, in order. The notebook is the last one, and only after the cabinet opened."""
        keys = list(C.BOOK_ORDER)
        if self.cabinet_open:
            keys.append(C.NOTEBOOK_KEY)
        return keys

    def book_pages(self, key):
        if key == C.NOTEBOOK_KEY:
            return C.JOURNAL_PAGES
        return C.BOOKS[key][2]

    def open_book(self, key):
        """A book was taken off the shelf. Returns its pages. Opening the notebook finds it (a clue); ordinary books just
        get remembered as read."""
        if key not in self.shelf():
            raise KeyError(key)
        if key == C.NOTEBOOK_KEY:
            self.journal_found = True
            self.add_clue("journal")
        elif key not in self.books_read:
            self.books_read.append(key)
        return self.book_pages(key)

    def finish_journal(self):
        """The last page of the notebook has been read: the disk taped inside its back cover is in the player's hands.
        True the first time."""
        self.journal_read = True
        if self.has_boot_disk:
            return False
        self.inventory.append(self.BOOT_DISK)
        return True

    # ---- the computer
    def computer_state(self):
        """What the computer does when used: "dark", "standby" (power but no disk), "ready" or "done"."""
        if self.computer_done:
            return "done"
        if not self.power:
            return "dark"
        if self.cabinet_open and self.has_boot_disk:
            return "ready"
        return "standby"

    def clear_breakout(self):
        """HAPPY BREAKOUT.EXE was cleared. It stays cleared (losing a later game takes nothing away)."""
        first = not self.breakout_cleared
        self.breakout_cleared = True
        return first

    def finish_computer(self):
        """The locked files were opened and read. Needs the whole chain, and the game cleared."""
        if self.computer_state() != "ready" or not self.breakout_cleared:
            return False
        self.computer_done = True
        return True

    def see_plushie(self):
        self.plushie_seen = True

    # ---- the room's ordinary things
    def inspect(self, key):
        """Look at an ordinary object. Returns the lines to say (a different variant each time round). Changes nothing
        that matters: only a counter of how often it was looked at."""
        variants = C.LIFE[key]["lines"]
        n = self.inspected.get(key, 0)
        self.inspected[key] = n + 1
        return variants[n % len(variants)]

    # ------------------------------------------------------------ hints (asked for, never pushed)
    def hint(self):
        """The next hint for the current stage, a bit more each time it is asked (the last one repeats)."""
        key = self.objective
        tiers = HINTS[key]
        n = self.hints.get(key, 0)
        self.hints[key] = min(n + 1, len(tiers) - 1)
        return tiers[min(n, len(tiers) - 1)]
