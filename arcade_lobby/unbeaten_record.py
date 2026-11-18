"""TRIAL 02 - THE UNBEATEN RECORD: the rules (no drawing, no pygame).

The trial is a memory of NEON CORNER ARCADE on its best night: a championship. The player has to fix a lost tournament
entry (THE MISSING ENTRY), then win three fights on the arcade's own NEON BRAWL cabinet, and the night ends with a
celebration in which the arcade's systems quietly misbehave.

    the way in      legacy_terminal.TRIAL_SCENES["trial_02"] (chapter and lifetime-earnings rules: quests.trial_status)
    the room        unbeaten_scene.TournamentHallScene
    the fights      unbeaten_bout (NEON BRAWL's own fighters, AI and renderer, one opponent at a time)
    the words       unbeaten_content

What is saved (QuestManager.save_trial_progress, in the playing profile's story): the registration, the rounds won,
whose stories about the arcade's founder the player has heard, and whether Miao Meow's realisation has played. A lost
fight saves nothing and costs nothing: the same round is simply offered again. Completion is only ever the story event
GameEvent("secret_trial_done", key="trial_02"); the Memory Fragment comes with the first one (quests.MEMORY_FRAGMENTS).
"""
from dataclasses import dataclass

TRIAL_ID = "trial_02"
INTRO_FLAG = "trial02_intro"            # story flag: the opening has played once (later visits skip it)
REALIZED_FLAG = "trial02_founder"       # story flag: Miao Meow's realisation about the founder has played
FRAGMENT_NAME = "MEMORY FRAGMENT 02"
KEY_NAME = "CHAMPIONSHIP STAGE KEY"     # a trial-only item too: found in the trophy cabinet, used in the final cabinet
ANOMALY = "DISPLAY DATA UPDATED"        # the only system message before the ending (as the key goes in)
BADGE_NAME = "TOURNAMENT BADGE"         # a trial-only keepsake: shown in the hall, never put in the bag, never a Secret Item

# ------------------------------------------------------------------ THE MISSING ENTRY
# The registration terminal wants an ENTRY CODE: division letter + the two-digit ledger number. The three documents:
#   poster  the fee each division pays (and how a code is written)
#   ticket  what the player paid (2 TOKENS) and a check-in stamp torn after "6:4"
#   ledger  every entry in order: number, name (a spilled soda hid some), what was PAID, check-in time, and refunds
#           crossed out. It does not say the division: that has to be worked out from the fee.
# Fee 2 -> STUDENT -> B. Paid 2 and checked in 6:40 to 6:49: entries 07, 09 and 10. Entry 09 has a readable name (KAI T.
# is here, it is not the lost record), entry 07 is crossed out (refunded, the person went home): so it is 10. Answer: B10.
# Each clue is needed: candidates() with any one left out finds more than one entry.
DIVISIONS = (("A", "JUNIOR", "UNDER 12", 1),
             ("B", "STUDENT", "SCHOOL OR UNIVERSITY", 2),
             ("C", "OPEN", "EVERYBODY ELSE", 3),
             ("D", "VETERAN", "10 YEARS A REGULAR", 0))
TICKET_FEE = 2
TICKET_TIME = "6:4"                     # the rest of the time is torn off
SMUDGED = None                          # a ledger name nobody can read any more
REFUNDED = "REFUNDED"
# (number, name, tokens paid, check-in time, note)
LEDGER = (
    (1, "DANNY K.", 3, "6:02", None),
    (2, "MEI L.", 2, "6:09", None),
    (3, SMUDGED, 1, "6:15", None),
    (4, "ROCKO", 0, "6:21", None),
    (5, SMUDGED, 3, "6:33", None),
    (6, "JUNE P.", 2, "6:38", None),
    (7, SMUDGED, 2, "6:41", REFUNDED),
    (8, SMUDGED, 0, "6:44", None),
    (9, "KAI T.", 2, "6:45", None),
    (10, SMUDGED, 2, "6:47", None),
    (11, "TOMMY", 1, "6:48", None),
    (12, SMUDGED, 2, "6:53", None),
    (13, "SAM R.", 3, "6:59", None),
    (14, SMUDGED, 2, "7:12", None),
)
WAITING_LIST_FROM = "7:00"              # registration closed at seven: later names wait (the poster says so)
LETTERS = tuple(d[0] for d in DIVISIONS)
TENS = (0, 1)
UNITS = tuple(range(10))
DOCUMENTS = ("poster", "ticket", "ledger")               # THE MISSING ENTRY's three
# Everything that can be read again from the evidence file ([TAB] in the hall), once found. Saved in the run's "seen".
EVIDENCE = ("poster", "ticket", "ledger", "bracket", "slips", "photos", "champ_note")


def code_of(letter, number):
    return f"{letter}{number:02d}"


def division_for_fee(fee):
    return next(d[0] for d in DIVISIONS if d[3] == fee)


def division_of(row):
    return division_for_fee(row[2])


def _minutes(clock):
    h, m = clock.split(":")
    return int(h) * 60 + int(m)


def candidates(fee=True, time=True, smudge=True, refunds=True):
    """Every ledger entry the clues allow (the puzzle is fair only if, with every clue, this is exactly one). The
    switches leave a clue out, which shows that each one is needed."""
    letter = division_for_fee(TICKET_FEE)
    return [row for row in LEDGER
            if (not smudge or row[1] is SMUDGED) and (not fee or division_of(row) == letter)
            and (not time or row[3].startswith(TICKET_TIME)) and (not refunds or row[4] != REFUNDED)
            and _minutes(row[3]) < _minutes(WAITING_LIST_FROM)]


def solution():
    (row,) = candidates()
    return code_of(division_of(row), row[0])


ANSWER = solution()


def check_code(code):
    """What the terminal says about an entered code: ("ok", ...) for the player's own entry, else why not.
    Never says which entry IS the player's, and never which division an entry is in."""
    code = (code or "").upper()
    if code == ANSWER:
        return "ok", "ENTRY RECORD RESTORED."
    row = next((r for r in LEDGER if code_of(division_of(r), r[0]) == code), None)
    if row is None:
        return "none", "NO ENTRY MATCHES THAT CODE."
    if _minutes(row[3]) >= _minutes(WAITING_LIST_FROM):
        return "waiting", f"ENTRY {row[0]:02d} IS ON THE WAITING LIST."
    if row[4] == REFUNDED:
        return "refunded", f"ENTRY {row[0]:02d} WAS REFUNDED. IT IS CLOSED."
    if row[1] is not SMUDGED:
        return "taken", f"ENTRY {row[0]:02d} IS {row[1]} AND THEY ARE ALREADY HERE."
    return "other", f"ENTRY {row[0]:02d} DOES NOT MATCH YOUR TICKET."


class CodeWheels:
    """The terminal's three wheels: LETTER, TENS, UNITS. They start empty-ish (A00) and are never filled in for you."""

    def __init__(self):
        self.values = [0, 0, 0]
        self.cursor = 0

    @property
    def choices(self):
        return (LETTERS, TENS, UNITS)

    def move(self, step):
        self.cursor = (self.cursor + step) % 3

    def turn(self, step):
        options = self.choices[self.cursor]
        self.values[self.cursor] = (self.values[self.cursor] + step) % len(options)

    def symbol(self, i):
        return str(self.choices[i][self.values[i]])

    @property
    def code(self):
        return LETTERS[self.values[0]] + str(TENS[self.values[1]]) + str(UNITS[self.values[2]])

    def set_code(self, code):
        """(tests and tools) put the wheels on `code`."""
        self.values = [LETTERS.index(code[0]), TENS.index(int(code[1])), UNITS.index(int(code[2]))]


# ------------------------------------------------------------------ the tournament
# ------------------------------------------------------------------ PUZZLE 02: THE BROKEN BRACKET
# After the qualifier the bracket board scrambles itself: the player has to put tonight's eight back in their slots
# and mark who won each first-round match, so the host knows who plays the semifinal. The evidence:
#   the board's own rules (BRACKET_RULES), the referee's slips (SLIPS: winner slot, time, notes, names smudged by the
#   printer), the ledger from Puzzle 01 (ledger numbers, and TOMMY paid 1 token = JUNIOR), and what people saw (the
#   testimonies in unbeaten_content, each one a fact in TESTIMONY_FACTS below).
# Slots 1 and 2 are YOU and THE ROOKIE (that match was just played). The answer is unique (a test enumerates every
# placement): 3 MEI L., 4 THE CHALLENGER, 5 DANNY K., 6 JUNE P., 7 ROCKO, 8 THE CHAMPION; winners 1, 4, 5, 8.
BRACKET_FIXED = {1: "YOU", 2: "THE ROOKIE"}
BRACKET_SLOTS = (3, 4, 5, 6, 7, 8)
MATCHES = ((1, 2), (3, 4), (5, 6), (7, 8))
BRACKET_POOL = ("DANNY K.", "JUNE P.", "MEI L.", "ROCKO", "THE CHALLENGER", "THE CHAMPION", "TOMMY")   # A to Z
INVITED = ("THE CHALLENGER", "THE CHAMPION")            # last season's finalists: not in the ledger
# (match number, winner's slot, time, note)
SLIPS = ((1, 1, "0:52", "QUALIFIER. THE NEW FACE WON."),
         (2, 4, "1:44", "14 BLOCKS. A NEW RECORD FOR THE NIGHT."),
         (3, 5, "3:10", "WENT TO A THIRD ROUND. LONGEST MATCH OF THE NIGHT."),
         (4, 8, "0:38", "FASTEST MATCH OF THE NIGHT."))
BRACKET_RULES = ("1. JUNIORS PLAY THEIR OWN BRACKET ON SATURDAY.",
                 "2. INVITED PLAYERS TAKE THE EVEN SLOT OF THEIR MATCH.",
                 "3. OTHERWISE THE LOWER LEDGER NUMBER TAKES THE ODD SLOT.",
                 "4. EACH WINNER MOVES ON TO THE RIGHT.")


def ledger_number(name):
    return next((r[0] for r in LEDGER if r[1] == name), None)


def is_junior(name):
    row = next((r for r in LEDGER if r[1] == name), None)
    return row is not None and division_of(row) == "A"


def _match_of(slot):
    return next(i for i, pair in enumerate(MATCHES) if slot in pair)


def _slip(match_index):
    return SLIPS[match_index]


# What people in the hall saw (unbeaten_content gives each one a voice). Each is a test on a full bracket.
def _same_match(b, a, c):
    sa = next((s for s, n in b.items() if n == a), None)
    sc = next((s for s, n in b.items() if n == c), None)
    return sa is not None and sc is not None and _match_of(sa) == _match_of(sc)


def _winner_of(b, w, name):
    slot = next((s for s, n in b.items() if n == name), None)
    return slot is not None and slot in w


def _match_note(b, name, words):
    slot = next((s for s, n in b.items() if n == name), None)
    return slot is not None and words in _slip(_match_of(slot))[3]


TESTIMONY_FACTS = {
    "fan": lambda b, w: _same_match(b, "THE CHAMPION", "ROCKO") and _winner_of(b, w, "THE CHAMPION")
    and _match_note(b, "THE CHAMPION", "FASTEST"),
    "student": lambda b, w: _same_match(b, "DANNY K.", "JUNE P.") and _winner_of(b, w, "DANNY K."),
    "nycu": lambda b, w: _match_note(b, "DANNY K.", "LONGEST"),
    "challenger": lambda b, w: _winner_of(b, w, "THE CHALLENGER") and _match_note(b, "THE CHALLENGER", "14 BLOCKS"),
}
# More people back those up after the qualifier. What they say is true of the answer (tested) but adds nothing the
# evidence above does not already settle, so the puzzle still needs the board's rules, the slips and the eyewitnesses.
SUPPORTING_FACTS = {
    "old_regular": lambda b, w: _winner_of(b, w, "THE CHALLENGER") and _match_note(b, "THE CHALLENGER", "14 BLOCKS"),
    "visitor": lambda b, w: not _same_match(b, "MEI L.", "JUNE P."),
    "waiting": lambda b, w: "TOMMY" not in b.values(),
}


def _rules_ok(b):
    for name in b.values():
        if name in BRACKET_POOL and is_junior(name):
            return False
    for a, c in MATCHES[1:]:
        na, nc = b.get(a), b.get(c)
        if na in INVITED and nc in INVITED:
            return False
        if na in INVITED:                                  # (invited: the even slot)
            return False
        if na not in INVITED and nc not in INVITED and not ledger_number(na) < ledger_number(nc):
            return False
    return True


def _slips_ok(w):
    return set(w) == {slip[1] for slip in SLIPS}


def bracket_ok(bracket, winners, skip=()):
    """Is this bracket ({slot: name} for slots 3..8, winners = set of winning slots) consistent with every piece of
    evidence? `skip` leaves out pieces ("rules", "slips" or a testimony key), to show each one matters."""
    b = dict(BRACKET_FIXED)
    b.update(bracket)
    w = set(winners)
    if sorted(bracket) != list(BRACKET_SLOTS) or len(set(bracket.values())) != len(BRACKET_SLOTS):
        return False
    if any(n not in BRACKET_POOL for n in bracket.values()):
        return False
    if len(w) != len(MATCHES) or any(len(set(pair) & w) != 1 for pair in MATCHES):
        return False
    if "rules" not in skip and not _rules_ok(b):
        return False
    if "slips" not in skip and not _slips_ok(w):
        return False
    return all(fact(b, w) for key, fact in TESTIMONY_FACTS.items() if key not in skip)


def bracket_solutions(skip=()):
    """Every bracket the evidence allows (with nothing skipped: exactly one)."""
    from itertools import combinations, permutations, product
    out = []
    for names in permutations(BRACKET_POOL, len(BRACKET_SLOTS)):
        b = dict(zip(BRACKET_SLOTS, names))
        for picks in product(*MATCHES):
            if bracket_ok(b, set(picks), skip):
                out.append((b, frozenset(picks)))
    return out


BRACKET_ANSWER, BRACKET_WINNERS = bracket_solutions()[0]


def semifinal_opponent(bracket, winners):
    winner = next(s for s in MATCHES[1] if s in winners)
    return bracket.get(winner)


class BracketDraft:
    """The board while the player works on it: names put in slots 3..8 and winner marks. Never filled in for you."""

    def __init__(self):
        self.slots = {s: None for s in BRACKET_SLOTS}
        self.winners = {1}                                  # (the qualifier was just won)

    def cycle(self, slot, step):
        """The next name for `slot` (names already used elsewhere are skipped; an empty slot is one of the choices)."""
        used = {n for s, n in self.slots.items() if n and s != slot}
        options = [None] + [n for n in BRACKET_POOL if n not in used]
        cur = self.slots[slot]
        i = options.index(cur) if cur in options else 0
        self.slots[slot] = options[(i + step) % len(options)]

    def mark_winner(self, slot):
        pair = MATCHES[_match_of(slot)]
        if slot in pair and pair != MATCHES[0]:
            self.winners -= set(pair)
            self.winners.add(slot)

    def clear_slot(self, slot):
        """Empty one slot (its winner mark goes with it)."""
        self.slots[slot] = None
        self.winners.discard(slot)

    def clear(self):
        """Wipe the board: every name and every winner mark the player made (the qualifier stays won)."""
        self.slots = {s: None for s in BRACKET_SLOTS}
        self.winners = {1}

    def place(self, slot, name):
        """(tests and tools)"""
        self.slots[slot] = name

    def check(self):
        if any(n is None for n in self.slots.values()):
            return "incomplete"
        return "ok" if bracket_ok(self.slots, self.winners) else "wrong"


# ------------------------------------------------------------------ PUZZLE 03: THE CHAMPION'S TROPHY
# After the semifinal the championship stage will not power up: its old brass key is missing. It is hidden in the
# trophy cabinet, which opens only when its three trophies stand the way the old champion kept them:
#   photo wall  three photos: each trophy design, held up on its own championship night, with the year on the banner
#               (all three prints carry the same PRINTED stamp: a harmless red herring)
#   the note    "the newest one always goes closest to the door ... a trophy with its back to the crowd is sulking"
#   the hall    the door is on the LEFT wall, so the left slot is the one nearest the door
# Answer: JOYSTICK (1990), ROCKET (1989), CUP (1988), left to right, each turned so its engraved mark faces out.
TROPHY_YEARS = {"cup": 1988, "rocket": 1989, "joystick": 1990}
TROPHY_MARKS = {"cup": "heart", "rocket": "bolt", "joystick": "coin"}
TROPHY_START = (("cup", 2), ("joystick", 1), ("rocket", 3))         # (kind, facing): how the cabinet is found
FACINGS = 4                                                       # 0 = the engraved mark faces out
DOOR_SIDE = "left"                                                # where the door is, seen from the cabinet
TROPHY_ANSWER = tuple(sorted(TROPHY_YEARS, key=lambda k: -TROPHY_YEARS[k]))   # newest nearest the door (left)


class TrophyCase:
    """The cabinet: three trophies in three slots. Pick one up and put it down on another slot to swap them; turn the
    one under the cursor; pull the lever to try. A wrong try just clunks: nothing is lost."""

    def __init__(self):
        self.slots = [list(t) for t in TROPHY_START]
        self.cursor = 0                 # 0..2 a slot, 3 the lever
        self.held = None                # index of the slot whose trophy is lifted
        self.tries = 0
        self.open = False

    @property
    def order(self):
        return tuple(k for k, _ in self.slots)

    @property
    def facings(self):
        return tuple(f for _, f in self.slots)

    def move(self, step):
        self.cursor = (self.cursor + step) % 4

    def lift(self):
        """E on a slot: lift its trophy, or put the lifted one here (the two swap places)."""
        if self.cursor > 2 or self.open:
            return False
        if self.held is None:
            self.held = self.cursor
        else:
            a, b = self.held, self.cursor
            self.slots[a], self.slots[b] = self.slots[b], self.slots[a]
            self.held = None
        return True

    def turn(self, step):
        if self.cursor > 2 or self.held is not None or self.open:
            return False
        self.slots[self.cursor][1] = (self.slots[self.cursor][1] + step) % FACINGS
        return True

    @property
    def correct(self):
        return self.order == TROPHY_ANSWER and all(f == 0 for f in self.facings)

    def pull(self):
        """The lever. Returns True when the hidden compartment opens."""
        if self.open:
            return True
        self.tries += 1
        self.held = None
        if self.correct:
            self.open = True
        return self.open

    def arrange(self, order, facings=(0, 0, 0)):
        """(tests and tools)"""
        self.slots = [[k, f] for k, f in zip(order, facings)]


@dataclass(frozen=True)
class RoundDef:
    number: int
    stage: str              # QUALIFIER / SEMIFINAL / GRAND FINAL
    opponent: str           # key of unbeaten_bout.OPPONENTS (and of the competitor in the hall)
    title: str              # THE ROOKIE ...
    difficulty: str         # what the host's board says


ROUNDS = (
    RoundDef(1, "QUALIFIER", "rookie", "THE ROOKIE", "EASY"),
    RoundDef(2, "SEMIFINAL", "challenger", "THE CHALLENGER", "NORMAL"),
    RoundDef(3, "GRAND FINAL", "champion", "THE CHAMPION", "NORMAL+"),
)

KEVIN_NEEDED = 3            # different people who talked about the founder before Miao Meow wonders about the name


class TournamentRun:
    """Where this player's tournament night stands. Saved in the profile (to_dict / from_dict) whenever it changes."""

    def __init__(self):
        self.registered = False
        self.rounds_won = 0
        self.kevin = []             # ids of the people whose stories about the founder were heard to the end
        self.seen = []              # documents looked at (poster / ticket / ledger), for Miao's hints only
        self.wrong_codes = 0
        self.losses = 0             # fights lost this visit (not saved: losing never matters)
        self.bracket = False        # PUZZLE 02 solved (the semifinal can be called)
        self.trophies = False       # PUZZLE 03 solved: the cabinet opened and the stage key was taken
        self.key_used = False       # the key is in the championship cabinet (the final can be played)
        self.bracket_tries = 0
        self.chats = []             # phases in which Miao Meow has already had her say (then: hints)
        self.heard = []             # "person:phase" for every clue heard from someone (the evidence file keeps them)

    @property
    def phase(self):
        """Which part of the night it is, for what people say: the rounds won, as saved (0 .. 3)."""
        return self.rounds_won

    # ---- saving
    def to_dict(self):
        data = {"registered": self.registered, "rounds": self.rounds_won, "kevin": list(self.kevin), "seen": list(self.seen),
                "bracket": self.bracket, "trophies": self.trophies, "key": self.key_used, "miao": list(self.chats),
                "heard": list(self.heard)}
        return {k: v for k, v in data.items() if v}

    @classmethod
    def from_dict(cls, data):
        run = cls()
        data = data if isinstance(data, dict) else {}
        run.registered = data.get("registered") is True
        rounds = data.get("rounds")
        run.rounds_won = max(0, min(len(ROUNDS), rounds)) if isinstance(rounds, int) and not isinstance(rounds, bool) else 0
        run.bracket = data.get("bracket") is True and run.rounds_won >= 1
        run.trophies = data.get("trophies") is True and run.rounds_won >= 2
        run.key_used = data.get("key") is True and run.trophies
        if not run.registered:
            run.rounds_won = 0                      # (no fight without an entry: a damaged save cannot skip the desk)
        if not run.bracket:                         # (nor skip a puzzle: a round needs the puzzle before it)
            run.rounds_won = min(run.rounds_won, 1)
        if not run.key_used:
            run.rounds_won = min(run.rounds_won, 2)
        run.kevin = [k for k in data.get("kevin", []) if isinstance(k, str)][:16] if isinstance(data.get("kevin"), list) else []
        run.seen = [k for k in data.get("seen", []) if k in EVIDENCE] if isinstance(data.get("seen"), list) else []
        heard = data.get("heard") if isinstance(data.get("heard"), list) else []
        run.heard = [h for h in heard if isinstance(h, str) and h.count(":") == 1 and len(h) < 40][:32]
        run.chats = [p for p in data.get("miao", []) if p in (0, 1, 2, 3) and not isinstance(p, bool)][:4] \
            if isinstance(data.get("miao"), list) else []
        return run

    # ---- the desk
    def look_at(self, document):
        if document in EVIDENCE and document not in self.seen:
            self.seen.append(document)
            return True
        return False

    def try_code(self, code):
        """Enter a code at the terminal. Returns (result, message); registers on the right one."""
        result, message = check_code(code)
        if result == "ok":
            self.registered = True
        else:
            self.wrong_codes += 1
        return result, message

    @property
    def has_badge(self):
        return self.registered

    # ---- the fights
    @property
    def finished(self):
        return self.rounds_won >= len(ROUNDS)

    @property
    def next_round(self):
        """The round the host offers now (None before registration or after the final)."""
        if not self.registered or self.finished:
            return None
        return ROUNDS[self.rounds_won]

    @property
    def round_ready(self):
        """Is the puzzle before the round on offer solved? (1: the entry, 2: the bracket, 3: the stage key put in)"""
        nxt = self.next_round
        if nxt is None:
            return False
        return {1: self.registered, 2: self.bracket, 3: self.key_used}[nxt.number]

    @property
    def stage(self):
        """Where the night stands: entry / fight / bracket / trophies / key / done."""
        if not self.registered:
            return "entry"
        if self.finished:
            return "done"
        if self.rounds_won == 1 and not self.bracket:
            return "bracket"
        if self.rounds_won == 2 and not self.trophies:
            return "trophies"
        if self.rounds_won == 2 and not self.key_used:
            return "key"
        return "fight"

    def solve_bracket(self, draft):
        """Submit the board. Returns "ok", "wrong" or "incomplete"."""
        if self.rounds_won != 1:
            return "closed"
        result = draft.check()
        if result == "ok":
            self.bracket = True
        elif result == "wrong":
            self.bracket_tries += 1
        return result

    def take_key(self, case):
        if self.rounds_won != 2 or not case.open or self.trophies:
            return False
        self.trophies = True
        return True

    def use_key(self):
        if not self.trophies or self.key_used:
            return False
        self.key_used = True
        return True

    def win(self, number):
        """The round `number` was won. Only the round on offer counts (a replayed old one changes nothing), and only
        once its puzzle is solved."""
        nxt = self.next_round
        if nxt is None or nxt.number != number or not self.round_ready:
            return False
        self.rounds_won += 1
        return True

    def lose(self, number):
        """A lost fight: nothing is taken away, the same round stays on offer."""
        self.losses += 1
        return self.next_round

    def hear_clue(self, tag):
        if tag not in self.heard:
            self.heard.append(tag)
            return True
        return False

    # ---- the founder's name
    def hear_kevin(self, who):
        if who not in self.kevin:
            self.kevin.append(who)
            return True
        return False

    @property
    def realization_ready(self):
        return len(self.kevin) >= KEVIN_NEEDED


# Before the board: the referee's slips first (the host has them). Said until they have been read, then the tiers below.
SLIPS_FIRST = "Wait, before we touch that board! Let's ask the host first. They've got the referee's slips from every match."
HINTS = {
    "bracket": ("The board scrambled itself! The host has the referee's slips, and everybody here watched the matches.",
                "Read the rules at the bottom of the board. Does everyone in that list even belong in tonight's eight?",
                "Pair people up first, using what they saw and the slips. Then the rules say who sits where.",
                "Invited players have no ledger number. Everyone else? The ledger at the desk knows theirs."),
    "trophies": ("No key, no final! The old champions kept their treasures with their trophies, didn't they?",
                 "Those photos on the board show each trophy on its own night. The years are on the banners.",
                 "Somebody left a note about the trophies. The schedule board, maybe? Where IS the door from there?",
                 "Newest nearest the door, oldest farthest away. And no sulking trophies: marks facing out!"),
    "key": ("You've got the key! The championship cabinet is on the stage, left side. Go on, go on!",),
}


def hint(run, asked=0):
    """Miao Meow's hint for where the night stands (asked for, never pushed): a little more each time she is asked
    about the same puzzle. Never the answer itself."""
    if not run.registered:
        seen = set(run.seen)
        if "poster" not in seen:
            return "The desk can't find your entry. That big poster by the desk explains how entry codes work!"
        if "ticket" not in seen:
            return "Didn't you have a ticket? People drop stuff all the time. Is there a lost and found here?"
        if "ledger" not in seen:
            return "Your ticket says what you paid. The poster says what that means. Now, where do they write the names?"
        if run.wrong_codes >= 3:
            return "Read every line of that book, even the messy ones. Not every entry is still an entry."
        if run.wrong_codes >= 1:
            return "The book doesn't say divisions, only what people paid. The poster can turn one into the other!"
        return "What you paid, when you came in, and a name nobody can read. Only one line fits ALL of it."
    stage = run.stage
    if stage == "bracket" and "slips" not in run.seen:
        return SLIPS_FIRST
    if stage in HINTS:
        tiers = HINTS[stage]
        return tiers[min(asked, len(tiers) - 1)]
    if not run.finished:
        rnd = run.next_round
        lines = {1: "The host is on the stage! Tell them you're ready and show that Rookie what you've got!",
                 2: "The Challenger blocks a lot. Heavy attacks break a guard, remember!",
                 3: "The Champion hits hard, but every big move has a windup. Watch, dodge, then strike!"}
        return lines[rnd.number]
    return "The host is waiting on the stage for the trophy ceremony. Whenever you're ready!"
