"""The main story's quests: data (QUESTS), the progress state, and the QuestManager that moves it along.

DATA-DRIVEN. A quest is one QuestDef row; to add one, add a row (and, if it needs a new kind of trigger, one
branch in QuestManager._met). Nothing else in the game names a quest.

    trigger kinds
      ("played", N)        N different arcade machines have been played (a running story-wide count)
      ("event", name)      the event `name` happens while this quest is the active one
      ("sticky", name)     the event `name` has happened, even before the quest started (a found secret stays found)
      ("counters", {...})  every named counter has reached its target
      ("item", key)        the Secret Item `key` is owned (kept, so an item found in an older save still counts)
      ("trial", trial_id)  the Secret Trial is complete (its earnings milestone is the terminal's business, not the quest's)

OWNERSHIP. The story belongs to the PROFILE being played: one profile, one main quest, saved in that profile
(PlayerProfile.story). Other profiles have their own and are never read or written. (Saves made by the old two-player
game hold a copy of the then-shared story in each of the two profiles; both copies are kept exactly as they are.)
A profile saved before the story existed has no story: it is read as 'veteran' (opening skipped, finished steps
ticked) so nobody is sent back to the tutorial or left waiting for something they already did.

THE TOUR. Quests one and two (THE GRAND TOUR, MEET THE LOCALS) are "sticky": the tour conversations (tour.py) fire the
events "tour_arcade" / "met_mochi" the first time the players reach those rooms, and a found flag stays found, so a
player who wanders to the Prize Plaza first is not sent back, and a conversation that has played never plays again.
Saves from before the tour are migrated (migrate_story): whoever was already past "Get Your Bearings" skips the tour.

THE CHAPTERS. After the vending secret the story runs in three chapters, strictly in order (CHAPTERS):
    CHAPTER 01  THE GOLDEN AGE        Secret Item "retro_racer_reverse_gear" (Retro Racer)  +  Secret Trial 01
    CHAPTER 02  THE FORGOTTEN GAMES   Secret Item "claw_secret_reward" (Claw Machine)      +  Secret Trial 02
    CHAPTER 03  THE FINAL CHALLENGE   Secret Item "dungeon_grey_pixel" (Dungeon Maze)      +  Secret Trial 03
    FINAL CHAPTER  REOPEN THE ARCADE  needs all six
Chapter 01 opens with the vending secret; each later chapter opens when the one before it has BOTH its item and its trial.
Items are recorded by their stable key (never by slot number), and only while their chapter is open; what an older save
already holds is kept and counted wherever it is. Nothing about a chapter is stored: it is worked out from what is
owned every time, so an old profile needs no migration. Ordinary games never look at any of this.
A trial also asks for LIFETIME EARNINGS (settings.SECRET_TRIAL_EARNINGS): every Token and Ticket the player has ever
legitimately received, not the wallet. Spending never lowers them, so once reached a milestone never closes the trial
again; nothing is ever charged, and a completed trial stays completed.

The vending-machine step is only completed by the REAL hidden screen (vending_ui.py fires a "vending_secret"
event the moment its listener recognises the secret sequence); opening the ordinary shop never counts.
"""
import copy
from collections import deque
from dataclasses import dataclass, field

from player_profile import clean_story

VENDING_SECRET_FLAG = "vending_konami_discovered"      # the profile secret vending_ui.py already records
SECRET_ITEM_RETRO_RACER = "retro_racer_reverse_gear"    # Secret Item 01: the key its "secret_item_found" event carries (saved as is)
SECRET_ITEM_CLAW = "claw_secret_reward"                 # Secret Item 02: the Claw Machine's secret reward
SECRET_ITEM_DUNGEON = "dungeon_grey_pixel"              # Secret Item 03: the Dungeon Maze's grey pixel
ITEM_ALIASES = {"reverse_gear": SECRET_ITEM_RETRO_RACER}     # the racer's own name for its item (retro_racer/reverse_road.ITEM_KEY)
MOCHI_ARCADE_STORY = "mochi_arcade_story"               # story flag: Mochi's first Retro Racer story has been told
MIAO_REVERSE_ROAD = "miao_reverse_road"                 # story flag: Miao Meow's talk about the secret road has been told

# ---- CHAPTER 02, THE FORGOTTEN GAMES (the game-facing rules live in forgotten_games.py). All of it is saved in the
# playing profile's story and is only ever written while Chapter 02 is open (Trial 01 complete).
CH2_CLUES = ("maze", "galaxy", "volley")                # NEON CAT MAZE, STARFALL ASSAULT, CAT VOLLEYBALL
CH2_CLUE_FLAGS = {"maze": "ch2_clue_corridor",          # the forgotten corridor behind the maze
                  "galaxy": "ch2_clue_signal",          # the quiet, non-hostile ship and its signal
                  "volley": "ch2_clue_ticket"}          # the old spectator ticket
# The symbol each clue shows, in the lock's fixed order (I, II, III), with the game it is found in. The record of a
# found symbol (CH2_SYMBOLS_FOUND) is written next to its clue flag; the Quest Log reads both and never shows a symbol
# that is not found (it stays "???").
CH2_SYMBOLS = (("maze", "I", "STAR", "NEON CAT MAZE"),
               ("galaxy", "II", "MOON", "STARFALL ASSAULT"),
               ("volley", "III", "PAW", "CAT VOLLEYBALL"))
CH2_SYMBOLS_FOUND = "ch2_symbols"                       # stats: {numeral: {"symbol": ..., "game": ...}} once found
CH2_TRIES_NEEDED = {"maze": 12, "galaxy": 12, "volley": 12}   # PERSISTENCE route: meaningful failed tries per game
#   (cumulative over any number of sessions, never reset by a win; what counts as meaningful is each game's own rule:
#    neon_cat_maze/corridor.TRY_MIN_SCORE, galaxy_defender/quiet_signal.TRY_MIN_SCORE, pixel_volleyball/old_ticket.py)
CH2_ROUTE_FLAGS = {"maze": "ch2_route_maze",            # flag: the ACE route was earned in that game (kept for good,
                   "galaxy": "ch2_route_galaxy",        #   so the encounter stays available after leaving or reloading)
                   "volley": "ch2_route_volley"}
CH2_TRIES = "ch2_tries"                                 # stats: {clue: meaningful failed tries counted so far}
CH2_CARD_PITY = "ch2_card_pity"                         # stats: capsule pulls in a row without a hint card
CH2_GOLDEN_MISSES = "ch2_golden_misses"                 # stats: grabs on the Golden Cat that slipped
CH2_RIDDLE_SOLVED = "ch2_riddle_solved"                 # flag: Mochi's maintenance lock was opened (STAR MOON PAW)
MIAO_CH2_HINT = "miao_ch2_hint"                         # flag: Miao Meow's "Mochi was acting weird" talk is told
CLUE_FOUND_EVENT = "forgotten_clue_found"               # session event (key: a CH2_CLUES entry)
CLUE_TRY_EVENT = "forgotten_clue_try"                   # session event: a meaningful failed try (key: a clue)
CLUE_ROUTE_EVENT = "forgotten_clue_route"               # session event: a game's ACE milestone was reached (key: a clue)


@dataclass(frozen=True)
class QuestDef:
    id: str
    title: str                  # "Get Your Bearings"
    objective: str              # the full sentence
    hud: str                    # the short line for the corner tracker
    trigger: tuple
    hints: tuple                # Miao Meow's hint, vaguest first; asking again moves to the next
    miao_anchor: tuple = None   # (room_id, spot): Miao Meow waits there while this quest is active
    reward_tokens: int = 0      # optional: tokens paid once, to every profile of the session, when it is completed
    intro: str = ""             # the line shown under the NEW MAIN QUEST banner
    chapter: int = 0            # 1..3 for a chapter's steps, 4 for the final chapter, 0 before the chapters begin


# ------------------------------------------------------------------ Secret Items and chapters
@dataclass(frozen=True)
class SecretItemDef:
    key: str                    # the STABLE id saved in the story (never the slot number)
    slot: int                   # the number shown: SECRET ITEM 01, 02, 03
    name: str                   # shown once it is found
    source: str                 # the game it hides in (said only once its chapter is open)
    chapter: int


SECRET_ITEMS = (
    SecretItemDef(SECRET_ITEM_RETRO_RACER, 1, "REVERSE GEAR", "RETRO RACER", 1),
    SecretItemDef(SECRET_ITEM_CLAW, 2, "CLAW MACHINE PRIZE", "CLAW MACHINE", 2),
    SecretItemDef(SECRET_ITEM_DUNGEON, 3, "GREY PIXEL", "DUNGEON MAZE", 3),
)
ITEMS_BY_KEY = {i.key: i for i in SECRET_ITEMS}


@dataclass(frozen=True)
class ChapterDef:
    number: int
    title: str
    item: str                   # the Secret Item key this chapter hands out
    trial: str                  # the Secret Trial id this chapter ends with

    @property
    def label(self):
        return f"CHAPTER {self.number:02d}"


CHAPTERS = (
    ChapterDef(1, "THE GOLDEN AGE", SECRET_ITEM_RETRO_RACER, "trial_01"),
    ChapterDef(2, "THE FORGOTTEN GAMES", SECRET_ITEM_CLAW, "trial_02"),
    ChapterDef(3, "THE FINAL CHALLENGE", SECRET_ITEM_DUNGEON, "trial_03"),
)
FINAL_CHAPTER_TITLE = "REOPEN THE ARCADE"
FINALE_EVENT = "arcade_reopened"            # the (not yet built) finale fires this when the arcade reopens
SECRET_ITEMS_NEEDED = len(SECRET_ITEMS)
SECRET_TRIALS_NEEDED = len(CHAPTERS)


def canonical_item(key):
    """The stable key for an item event's key (an alias is mapped), or None if it is not a Secret Item at all."""
    key = ITEM_ALIASES.get(key, key) if isinstance(key, str) else None
    return key if key in ITEMS_BY_KEY else None


MEMORY_FRAGMENTS = {"trial_01": "memory_fragment_01"}      # a trial's first completion unseals its Memory Fragment (a story flag, kept once)
TRIAL_NOTES = ("trial01_intro", "trial01_breakout")                           # quiet flags a trial scene keeps for itself (its opening has played)
TOUR_EVENTS = ("tour_home", "tour_arcade", "met_mochi")     # the tour conversations that have played (flags in the story)
LEGACY_QUESTS = {"get_your_bearings"}                        # a quest the tour replaced: reading it in a save means 'tour done'

QUESTS = (
    QuestDef("grand_tour", "The Grand Tour", "Follow Miao Meow and see the Arcade Floor.", "SEE THE ARCADE FLOOR",
             ("sticky", "tour_arcade"),
             ("Let's see the Arcade Floor! It's through the left door in HOME.",
              "Left door, then straight on. That's where all the machines live!"),
             miao_anchor=("home", "hub")),
    QuestDef("meet_the_locals", "Meet the Locals", "Go to the Prize Plaza and meet Mochi.",
             "MEET MOCHI AT THE PRIZE PLAZA", ("sticky", "met_mochi"),
             ("Next, the Prize Plaza! Take the right door in HOME.",
              "Somebody there runs the Prize Counter. She's very calm. I'm... not always."),
             miao_anchor=("home", "hub")),
    QuestDef("arcade_explorer", "Give It a Try", "Try 3 different machines on the Arcade Floor.",
             "TRY 3 MACHINES ON THE ARCADE FLOOR", ("played", 3),
             ("Every machine on the Arcade Floor is different! Let's try a few.",
              "Some are fast, some are puzzly. Try one you haven't played yet!")),
    QuestDef("earn_some_rewards", "Earn Your Rewards", "Win Tickets from an Arcade Floor game, then see what they can buy.",
             "WIN TICKETS ON THE ARCADE FLOOR",
             ("event", "tickets_earned"),
             ("Arcade Floor games pay out Tickets when you finish! Check the corner of your screen.",
              "Play a round all the way through. Your Ticket count will tick up. Then the Prize Plaza awaits!")),
    QuestDef("check_the_vending_machine", "Check the Vending Machine", "Find out what's up with the vending machine.",
             "CHECK THE VENDING MACHINE", ("sticky", "vending_secret"),
             ("That vending machine on the Arcade Floor has been acting really weird lately...",
              "Why not take a closer look at it? Arcade machines always have a few tricks up their sleeves.",
              "I can't tell you what it wants. Keep exploring the Arcade and trust your curiosity!")),
    # ---- CHAPTER 01: THE GOLDEN AGE
    QuestDef("ch1_secret_item", "Chapter 01: The Golden Age", "Find Secret Item 01. Mochi at the Prize Plaza remembers an old Retro Racer story.",
             "CH 01: FIND SECRET ITEM 01", ("item", SECRET_ITEM_RETRO_RACER),
             ("The vending machine woke something up! Mochi has run the Prize Plaza forever. Ask her?",
              "Old racing games had their own little secrets. Ask Mochi about the Retro Racer!",
              "If a road only goes one way... is that really the only way? I'm just a cat, I don't know cars!"),
             chapter=1),
    QuestDef("ch1_secret_trial", "Chapter 01: The Golden Age", "Open the Legacy Terminal in the vending machine and complete Secret Trial 01.",
             "CH 01: COMPLETE SECRET TRIAL 01", ("trial", "trial_01"),
             ("Secret Trial 01 is waiting inside the vending machine. Use the same secret to open it again!",
              "Take your time in there. Every little thing in a room can tell you something."),
             chapter=1),
    # ---- CHAPTER 02: THE FORGOTTEN GAMES
    QuestDef("ch2_secret_item", "Chapter 02: The Forgotten Games", "Find Secret Item 02. Clues are hidden across the arcade's games.",
             "CH 02: FIND SECRET ITEM 02", ("item", SECRET_ITEM_CLAW),
             ("The old games are whispering again! Keep playing them and watch for anything odd.",
              "The capsule machines in the Prize Plaza have some funny old cards in them now. Maybe they help?",
              "A clue in one game can point to another. Write things down, I always forget!"),
             chapter=2),
    QuestDef("ch2_secret_trial", "Chapter 02: The Forgotten Games", "Earn {tokens} Tokens and {tickets} Tickets in total, then complete Secret Trial 02 at the Legacy Terminal.",
             "CH 02: COMPLETE SECRET TRIAL 02", ("trial", "trial_02"),
             ("Trial 02 opens for players who have earned enough Tokens and Tickets. Spending is fine!",
              "Everything you ever win counts. Keep playing, then visit the vending machine again."),
             chapter=2),
    # ---- CHAPTER 03: THE FINAL CHALLENGE
    QuestDef("ch3_secret_item", "Chapter 03: The Final Challenge", "Find Secret Item 03. Something very small is hidden deep in the Dungeon Maze.",
             "CH 03: FIND SECRET ITEM 03", ("item", SECRET_ITEM_DUNGEON),
             ("The Dungeon Maze is the hardest game here. The last secret would hide somewhere like that!",
              "The smallest things are the easiest to miss. Look everywhere, even where nothing seems to be."),
             chapter=3),
    QuestDef("ch3_secret_trial", "Chapter 03: The Final Challenge", "Earn {tokens} Tokens and {tickets} Tickets in total, then complete Secret Trial 03 at the Legacy Terminal.",
             "CH 03: COMPLETE SECRET TRIAL 03", ("trial", "trial_03"),
             ("The last trial wants a lot of Tokens and Tickets earned. It counts everything you ever won!",
              "Spend whatever you like. What you have earned stays earned."),
             chapter=3),
    # ---- FINAL CHAPTER: REOPEN THE ARCADE
    QuestDef("reopen_the_arcade", "Final Chapter: Reopen the Arcade", "All three Secret Items and Secret Trials are done. Return to the Legacy Terminal.",
             "REOPEN THE ARCADE", ("event", FINALE_EVENT),
             ("We did it! Everything is ready. The Legacy Terminal is waiting for us.",),
             chapter=4),
)
_ORDER = {q.id: i for i, q in enumerate(QUESTS)}

# ------------------------------------------------------------------ the three Secret Trials
@dataclass(frozen=True)
class TrialDef:
    """One Secret Trial (an escape room), the end of chapter `chapter`. `needs_items` are Secret Items the player must
    already own to be let in. The lifetime Tokens / Tickets it asks the player to have EARNED are
    settings.SECRET_TRIAL_EARNINGS[id] (read at use, so they stay configurable in one place)."""
    id: str
    number: int
    title: str
    chapter: int
    needs_items: tuple = ()             # ((secret item key, short name), ...)


TRIALS = (
    TrialDef("trial_01", 1, "THE GOLDEN AGE", 1, needs_items=((SECRET_ITEM_RETRO_RACER, "REVERSE GEAR (SECRET ITEM 01)"),)),
    TrialDef("trial_02", 2, "THE FORGOTTEN GAMES", 2),
    TrialDef("trial_03", 3, "THE FINAL CHALLENGE", 3),
)
TRIALS_BY_ID = {t.id: t for t in TRIALS}

# Why a trial is locked (TrialStatus.lock):
LOCK_CHAPTER = "chapter"        # an earlier chapter is not finished (its Secret Item and Secret Trial)
LOCK_ITEM = "item"              # this chapter's own way in (Trial 01 needs the Reverse Gear) is not found yet
LOCK_EARNINGS = "earnings"      # the chapter is open but the player has not yet EARNED enough Tokens and Tickets in total


@dataclass(frozen=True)
class TrialStatus:
    code: str                           # "done", "available" or "locked"
    reasons: tuple = ()                 # why it is locked, one short line each
    tokens_needed: int = 0              # lifetime earnings the trial asks for ...
    tickets_needed: int = 0
    tokens_earned: int = 0              # ... and what the player has earned so far (never the wallet)
    tickets_earned: int = 0
    lock: str = None                    # LOCK_CHAPTER / LOCK_ITEM / LOCK_EARNINGS when locked

    @property
    def needs_earnings(self):
        return bool(self.tickets_needed or self.tokens_needed)

    @property
    def earnings_ok(self):
        return self.tickets_earned >= self.tickets_needed and self.tokens_earned >= self.tokens_needed

    @property
    def short(self):
        if self.code == "locked" and self.lock == LOCK_EARNINGS:
            return "NEED EARNINGS"
        return {"done": "COMPLETE", "available": "AVAILABLE", "locked": "LOCKED"}[self.code]


def trial_earnings(trial):
    """(tokens, tickets) the player must have EARNED in total to go into `trial`, read from settings every time."""
    import settings
    need = settings.SECRET_TRIAL_EARNINGS.get(trial.id if hasattr(trial, "id") else trial, {})
    return int(need.get("tokens", 0)), int(need.get("tickets", 0))


def lifetime_earnings(profile):
    """(tokens, tickets) this profile has ever legitimately received (PlayerProfile's lifetime totals, never the wallet)."""
    return profile.lifetime_tokens_earned, profile.lifetime_tickets_received


def trial_status(manager, profile, trial):
    """Whether `trial` can be entered by the player holding `profile`: done, available, or locked (and exactly why).
    Reading this never changes anything, and never charges anything. The milestone is LIFETIME earnings, so spending
    never closes a trial again; a done trial stays done (and replayable)."""
    tokens, tickets = trial_earnings(trial)
    have_k, have_t = lifetime_earnings(profile)
    base = dict(tokens_needed=tokens, tickets_needed=tickets, tokens_earned=have_k, tickets_earned=have_t)
    if manager.trial_done(trial.id):
        return TrialStatus("done", **base)
    if not manager.chapter_unlocked(trial.chapter):
        before = trial.chapter - 1
        return TrialStatus("locked", (f"COMPLETE CHAPTER {before:02d} FIRST" if before else "THE LEGACY SYSTEM IS SEALED",),
                           lock=LOCK_CHAPTER, **base)
    missing = [f"NEED THE {name}" for key, name in trial.needs_items if not manager.has_secret_item(key)]
    if missing:
        return TrialStatus("locked", tuple(missing), lock=LOCK_ITEM, **base)
    reasons = []
    if have_k < tokens:
        reasons.append(f"EARN {tokens} TOKENS IN TOTAL (EARNED {have_k})")
    if have_t < tickets:
        reasons.append(f"EARN {tickets} TICKETS IN TOTAL (EARNED {have_t})")
    if reasons:
        return TrialStatus("locked", tuple(reasons), lock=LOCK_EARNINGS, **base)
    return TrialStatus("available", **base)


def exit_status(manager):
    """The final reopening: needs every Secret Item AND every Secret Trial. Returns (unlocked, reasons)."""
    reasons = []
    if manager.secret_items < SECRET_ITEMS_NEEDED:
        reasons.append(f"NEED {SECRET_ITEMS_NEEDED} SECRET ITEMS (HAVE {manager.secret_items})")
    if manager.secret_trials < SECRET_TRIALS_NEEDED:
        reasons.append(f"NEED {SECRET_TRIALS_NEEDED} SECRET TRIALS (HAVE {manager.secret_trials})")
    return not reasons, tuple(reasons)


def objective_text(quest):
    """The quest's full sentence, with the earnings a trial step asks for filled in from settings."""
    if quest.trigger[0] == "trial":
        tokens, tickets = trial_earnings(quest.trigger[1])
        return quest.objective.format(tokens=tokens, tickets=tickets)
    return quest.objective


# What the legacy-protocol screen says once the vending secret is found (shown by the quest UI)
PROTOCOL_LINES = ("LEGACY PROTOCOL ACTIVE", "3 SECRET ITEMS REQUIRED", "3 SECRET TRIALS REQUIRED")


@dataclass
class Notification:
    """Something the quest UI should announce, in order. kind: 'quest' (NEW MAIN QUEST) or 'protocol'."""
    kind: str
    quest: QuestDef = None
    lines: tuple = field(default=())


# ------------------------------------------------------------------ state helpers
def has_history(profile):
    """Has this (old) profile played before? Used to read a save that predates the story as a veteran."""
    return bool(profile.total_games_played or profile.lifetime_tickets_earned or profile.lifetime_tokens_spent
                or profile.cats_petted or profile.secrets)


def veteran_state(profile, quests=QUESTS):
    """The story implied by what an old profile has already done: opening skipped, finished steps ticked."""
    played = list(profile.high_scores)
    state = {"opening_done": True, "completed": [], "stats": {"played": played[:SECRET_ITEMS_NEEDED * 4]},
             "flags": {name: True for name in TOUR_EVENTS}}            # (somebody who has played has seen the place)
    checks = {
        "grand_tour": True,
        "meet_the_locals": True,
        "arcade_explorer": profile.total_games_played >= 3 or len(played) >= 3,
        "earn_some_rewards": profile.lifetime_tickets_earned > 0,
        "check_the_vending_machine": profile.has_secret(VENDING_SECRET_FLAG),
    }
    for q in quests:
        if checks.get(q.id):
            state["completed"].append(q.id)
        else:
            break
    if profile.has_secret(VENDING_SECRET_FLAG):
        state["flags"]["vending_secret"] = True
    return clean_story(state)


def migrate_story(story, quests=QUESTS):
    """A saved story from before the tour, read with today's quests: whoever had already got past the first step (or has
    any later quest done) has seen the arcade, so THE GRAND TOUR and MEET THE LOCALS are ticked, the tour
    conversations count as played and nothing is replayed. A story that was still at its first step starts the tour.
    The story is returned as-is when it needs nothing."""
    story = copy.deepcopy(story)
    done = list(story.get("completed", ()))
    ids = {q.id for q in quests}
    if "grand_tour" not in ids:                                  # (a custom quest list that has no tour)
        return story
    later = [c for c in done if c in ids and c not in ("grand_tour", "meet_the_locals")]
    if not (LEGACY_QUESTS & set(done)) and not later:
        return story
    done = [c for c in done if c not in LEGACY_QUESTS]
    for tour_id in ("meet_the_locals", "grand_tour"):
        if tour_id not in done:
            done.insert(0, tour_id)
    story["completed"] = done
    flags = dict(story.get("flags", {}))
    flags.update({name: True for name in TOUR_EVENTS})
    story["flags"] = flags
    return clean_story(story)


# ------------------------------------------------------------------ the manager
class QuestManager:
    """Owns the playing profile's story. Listens to the profile (games played, tickets earned) and the session
    (story events), advances quests, queues announcements for the UI and saves into the profile."""

    def __init__(self, session, quests=QUESTS):
        self.session = session
        self.quests = tuple(quests)
        self.by_id = {q.id: q for q in self.quests}
        self.profiles = list(session.profiles)
        self.notifications = deque()
        self._lifetime = {}
        self._change_hooks = []
        # The story is the playing profile's own: nothing is merged with any other profile's copy
        # (a two-player session used to write one shared story into both profiles; each keeps what it has).
        profile = self.profiles[0]
        story = profile.story
        if not story and has_history(profile):
            story = veteran_state(profile, self.quests)
        self.state = clean_story(migrate_story(story, self.quests)) if story else {}
        self._settle(silent=True)
        for p in self.profiles:
            self._lifetime[id(p)] = p.lifetime_tickets_earned
            p.subscribe_events(self._on_profile_event)
            p.subscribe(self._on_profile_change)
        session.add_listener(self._on_session_event)
        self.save()

    def close(self):
        for p in self.profiles:
            p.unsubscribe_events(self._on_profile_event)
            p.unsubscribe(self._on_profile_change)
        self.session.remove_listener(self._on_session_event)

    def on_change(self, callback):
        """callback(kind) after any visible change ('progress', 'quest', 'complete', 'opening')."""
        self._change_hooks.append(callback)

    # ------------------------------------------------------------ reading
    @property
    def opening_done(self):
        return bool(self.state.get("opening_done"))

    @property
    def completed_ids(self):
        return list(self.state.get("completed", ()))

    @property
    def completed(self):
        return [self.by_id[c] for c in self.completed_ids if c in self.by_id]

    @property
    def active(self):
        """The quest being worked on now (None when every quest is done)."""
        done = set(self.completed_ids)
        return next((q for q in self.quests if q.id not in done), None)

    @property
    def way_out_active(self):
        """Is the story in its chapters (the vending secret's quest is behind it)?"""
        q = self.active
        return q is not None and q.chapter > 0

    @property
    def protocol_active(self):
        """Has the legacy protocol been unlocked (the vending secret found and its quest completed)?"""
        return "check_the_vending_machine" in self.completed_ids or self.way_out_active or \
            (self.active is None and bool(self.completed_ids))

    # ------------------------------------------------------------ chapters (worked out from what is owned, never stored)
    def chapter(self, number):
        return CHAPTERS[number - 1]

    def chapter_complete(self, number):
        """Chapter `number` (1..3) is done: its Secret Item is owned AND its Secret Trial is complete."""
        ch = self.chapter(number)
        return self.has_secret_item(ch.item) and self.trial_done(ch.trial)

    def chapter_unlocked(self, number):
        """Chapter 01 opens with the vending machine's Secret Interface; each later one when the one before is complete.
        Number 4 is the final chapter: every chapter complete."""
        if number <= 1:
            return self.secret_interface_unlocked
        return self.chapter_unlocked(number - 1) and self.chapter_complete(number - 1)

    @property
    def current_chapter(self):
        """0 before the Secret Interface, 1..3 for the chapter being played, 4 once the final chapter is open."""
        if not self.chapter_unlocked(1):
            return 0
        return next((n for n in range(1, len(CHAPTERS) + 1) if not self.chapter_complete(n)), len(CHAPTERS) + 1)

    @property
    def finale_unlocked(self):
        """The final chapter (and with it the last message) opens only with all three items AND all three trials."""
        return self.chapter_unlocked(len(CHAPTERS) + 1)

    def can_collect(self, key):
        """May the Secret Item `key` be picked up now? Only while its chapter is open (or if it is already owned)."""
        key = canonical_item(key)
        if key is None:
            return False
        return self.has_secret_item(key) or self.chapter_unlocked(ITEMS_BY_KEY[key].chapter)

    def can_finish_trial(self, trial_id):
        """May a completion of `trial_id` be recorded? Only once its chapter is open (a player inside the room is never
        sent out, nor robbed of the result, whatever happens to the wallet)."""
        trial = TRIALS_BY_ID.get(trial_id)
        return trial is not None and (self.trial_done(trial_id) or self.chapter_unlocked(trial.chapter))

    def objective_text(self, quest=None):
        q = quest or self.active
        return objective_text(q) if q is not None else ""

    def earnings_check(self, quest=None):
        """For a trial step with an earnings milestone: (tokens_earned, tokens_need, tickets_earned, tickets_need), else None.
        Lifetime earnings of the playing profile, never its wallet."""
        q = quest or self.active
        if q is None or q.trigger[0] != "trial":
            return None
        tokens, tickets = trial_earnings(q.trigger[1])
        if not (tokens or tickets):
            return None
        have_k, have_t = lifetime_earnings(self.profiles[0])
        return have_k, tokens, have_t, tickets

    # ------------------------------------------------------------ CHAPTER 02 (the clues, the record, the Golden Cat)
    @property
    def chapter_two_open(self):
        """Chapter 02 opens with Trial 01 (and the Reverse Gear): only then do its cards, clues and prize exist."""
        return self.chapter_unlocked(2)

    def clue_found(self, clue):
        return clue in CH2_CLUE_FLAGS and bool(self.state.get("flags", {}).get(CH2_CLUE_FLAGS[clue]))

    @property
    def clues_found(self):
        return sum(1 for clue in CH2_CLUES if self.clue_found(clue))

    def recovered_symbols(self):
        """[(numeral, symbol or None, game or None)] in the lock's fixed order I, II, III, whatever order they were found
        in. A symbol not found yet is (numeral, None, None): nothing about it is shown anywhere."""
        rows = []
        for clue, numeral, symbol, game in CH2_SYMBOLS:
            if not self.clue_found(clue):
                rows.append((numeral, None, None))
                continue
            rows.append((numeral, symbol, game))
        return rows

    @property
    def all_clues_found(self):
        return self.clues_found == len(CH2_CLUES)

    def _stat_int(self, value):
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0

    def clue_tries(self, clue):
        """Meaningful failed tries counted towards `clue`'s PERSISTENCE route (only while Chapter 02 was open)."""
        tries = self.state.get("stats", {}).get(CH2_TRIES)
        return self._stat_int(tries.get(clue)) if isinstance(tries, dict) else 0

    def clue_route_open(self, clue):
        """Has either route made `clue`'s secret available for good: the ACE milestone (a saved flag) or the PERSISTENCE
        count? It stays so after leaving the game or reloading the profile. (Finding it is still up to the player.)"""
        if not self.chapter_two_open or clue not in CH2_ROUTE_FLAGS:
            return False
        ace = bool(self.state.get("flags", {}).get(CH2_ROUTE_FLAGS[clue]))
        return ace or self.clue_tries(clue) >= CH2_TRIES_NEEDED[clue]

    def clue_due(self, clue):
        """Is `clue`'s encounter waiting in its game right now: a route is open and it has not been found yet?"""
        return self.clue_route_open(clue) and not self.clue_found(clue)

    def clue_route(self, clue):
        """How the route was opened, for tools and tests: "ace", "persistence", or None."""
        if not self.chapter_two_open:
            return None
        if self.state.get("flags", {}).get(CH2_ROUTE_FLAGS.get(clue, "")):
            return "ace"
        return "persistence" if self.clue_tries(clue) >= CH2_TRIES_NEEDED.get(clue, 1 << 30) else None

    @property
    def riddle_solved(self):
        return bool(self.state.get("flags", {}).get(CH2_RIDDLE_SOLVED))

    @property
    def golden_cat_wanted(self):
        """The Golden Cat sits in the claw machine: the record was solved and Secret Item 02 is not owned yet."""
        return self.chapter_two_open and self.riddle_solved and not self.has_secret_item(SECRET_ITEM_CLAW)

    @property
    def miao_ch2_hint_due(self):
        return self.chapter_two_open and self.all_clues_found and not self.state.get("flags", {}).get(MIAO_CH2_HINT)

    @property
    def card_pity(self):
        return self._stat_int(self.state.get("stats", {}).get(CH2_CARD_PITY))

    def set_card_pity(self, value):
        stats = self.state.setdefault("stats", {})
        value = max(0, int(value))
        if stats.get(CH2_CARD_PITY, 0) != value:
            stats[CH2_CARD_PITY] = value
            self.save()

    @property
    def golden_misses(self):
        return self._stat_int(self.state.get("stats", {}).get(CH2_GOLDEN_MISSES))

    def note_golden_miss(self):
        if self.golden_cat_wanted:
            self.state.setdefault("stats", {})[CH2_GOLDEN_MISSES] = self.golden_misses + 1
            self.save()

    def counter(self, name):
        found = self.state.get("stats", {}).get(name, [])
        return len(found) if isinstance(found, list) else 0

    def trial_done(self, trial_id):
        """Has this Secret Trial been completed (by anyone in the session: the story is shared)?"""
        found = self.state.get("stats", {}).get("secret_trials")
        return isinstance(found, (list, tuple)) and trial_id in found      # (a damaged save with a bare string must not count by accident)

    @property
    def secret_interface_unlocked(self):
        """True once the vending machine's REAL secret screen has opened (the "vending_secret" flag): ordinary use of
        the machine, or standing next to it, never sets it."""
        return bool(self.state.get("flags", {}).get("vending_secret"))

    def egg_found(self, key):
        """Has this pure-fun easter egg (e.g. "out_of_time") been discovered by anyone in the session?"""
        return bool(self.state.get("flags", {}).get(f"egg_{key}"))

    @property
    def memory_fragments(self):
        """How many Memory Fragments have been unsealed (one per Secret Trial that was completed)."""
        flags = self.state.get("flags", {})
        return sum(1 for flag in MEMORY_FRAGMENTS.values() if flags.get(flag))

    def has_memory_fragment(self, trial_id):
        return bool(self.state.get("flags", {}).get(MEMORY_FRAGMENTS.get(trial_id, "")))

    def has_secret_item(self, key):
        found = self.state.get("stats", {}).get("secret_items")
        key = ITEM_ALIASES.get(key, key) if isinstance(key, str) else key
        return isinstance(found, (list, tuple)) and key in found

    @property
    def mochi_story_stage(self):
        """Where Mochi's Retro Racer talk stands: None (locked: she says nothing about it), "new" (unlocked, the first
        story not heard), "heard" (heard; the hint is offered) or "found" (Secret Item 01 is in hand)."""
        if not self.secret_interface_unlocked:
            return None
        if self.has_secret_item(SECRET_ITEM_RETRO_RACER):
            return "found"
        return "heard" if self.state.get("flags", {}).get(MOCHI_ARCADE_STORY) else "new"

    @property
    def secret_items(self):
        """How many of the three Secret Items are owned (by stable key; other keys an old save may hold are kept, not counted)."""
        return sum(1 for item in SECRET_ITEMS if self.has_secret_item(item.key))

    @property
    def secret_trials(self):
        return sum(1 for trial in TRIALS if self.trial_done(trial.id))

    def progress(self, quest=None):
        """(done, total) for the quest's counter, or None for a quest that is a single step."""
        q = quest or self.active
        if q is None:
            return None
        kind = q.trigger[0]
        if kind == "played":
            return min(len(self.state.get("stats", {}).get("played", ())), q.trigger[1]), q.trigger[1]
        if kind == "counters":
            return self.secret_items + self.secret_trials, SECRET_ITEMS_NEEDED + SECRET_TRIALS_NEEDED
        return None

    def hud_text(self):
        q = self.active
        if q is None:
            return None
        p = self.progress(q)
        if q.trigger[0] == "played" and p and p[1] > 1:
            return f"{q.hud} {p[0]}/{p[1]}"
        return q.hud

    # ------------------------------------------------------------ hints (asked for, never pushed)
    def hint_tier(self, quest=None):
        q = quest or self.active
        return self.state.get("hints", {}).get(q.id, 0) if q else 0

    def current_hint(self, quest=None):
        """The hint for the active quest at the tier already reached (does not advance it)."""
        q = quest or self.active
        if q is None or not q.hints:
            return None
        return q.hints[min(self.hint_tier(q), len(q.hints) - 1)]

    def take_hint(self):
        """Miao Meow gives a hint because the player asked: the vaguest first, a little more each time they ask again."""
        q = self.active
        if q is None or not q.hints:
            return None
        tier = self.hint_tier(q)
        text = q.hints[min(tier, len(q.hints) - 1)]
        if tier < len(q.hints) - 1:
            self.state.setdefault("hints", {})[q.id] = tier + 1
            self.save()
        return text

    # ------------------------------------------------------------ events
    def _on_profile_event(self, event, key, game_id):
        if event == "game_played":
            self.handle("game_played", game_id or key)

    def _on_profile_change(self, change):
        if change.field != "tickets" or change.delta <= 0:
            return
        for p in self.profiles:                                  # earned (lifetime counter rose), not merely refunded
            now = p.lifetime_tickets_earned
            if now > self._lifetime.get(id(p), 0):
                self._lifetime[id(p)] = now
                self.handle("tickets_earned")

    def _on_session_event(self, owner, event):
        if event.type in ("vending_secret", "secret_item_found", "secret_trial_done", "easter_egg_found", FINALE_EVENT,
                          CLUE_FOUND_EVENT, CLUE_TRY_EVENT, CLUE_ROUTE_EVENT):
            self.handle(event.type, event.key)

    def handle(self, name, key=None):
        """One thing happened in the game. Updates the story's counters, then lets quests complete."""
        state = self.state
        changed = False
        if name == "game_played" and isinstance(key, str):
            played = state.setdefault("stats", {}).setdefault("played", [])
            if key not in played:
                played.append(key)
                changed = True
        elif name in ("secret_item_found", "secret_trial_done"):
            # Only the real items and trials, by their stable ids, and only once their chapter is open: a secret found
            # too early is simply not recorded (the game that hides it is asked to keep it closed: can_collect).
            if name == "secret_item_found":
                counter, ident = "secret_items", canonical_item(key)
                allowed = ident is not None and self.can_collect(ident)
            else:
                counter, ident = "secret_trials", key
                allowed = self.can_finish_trial(key)
            if not allowed:
                return
            found = state.setdefault("stats", {}).setdefault(counter, [])
            if not isinstance(found, list):
                found = state["stats"][counter] = []
            if ident not in found:
                found.append(ident)
                changed = True
                fragment = MEMORY_FRAGMENTS.get(ident) if name == "secret_trial_done" else None
                if fragment:                                  # kept with the first completion, never handed out twice
                    state.setdefault("flags", {})[fragment] = True
        elif name in TRIAL_NOTES:                             # quiet: no pop-up, no counter, no reward
            if not state.setdefault("flags", {}).get(name):
                state["flags"][name] = True
                self.save()
            return
        elif name == "easter_egg_found":                      # a pure-fun discovery: a note in the story, never a counter or a reward
            flag = f"egg_{key}" if isinstance(key, str) and key else None
            if flag and not state.setdefault("flags", {}).get(flag):
                state["flags"][flag] = True
                self.save()                                   # (kept quietly: no progress pop-up, no counters, no reward)
            return
        elif name == CLUE_ROUTE_EVENT:
            # the ACE milestone: kept in the profile so the encounter stays available until it is found
            if key not in CH2_ROUTE_FLAGS or not self.chapter_two_open or self.clue_found(key):
                return
            flags = state.setdefault("flags", {})
            if not flags.get(CH2_ROUTE_FLAGS[key]):
                flags[CH2_ROUTE_FLAGS[key]] = True
                self.save()
            return
        elif name in (CLUE_FOUND_EVENT, CLUE_TRY_EVENT):
            # Quiet (no pop-up, no counter on screen) and only while Chapter 02 is open: a clue found earlier, or by
            # an unknown game, is simply not recorded. A try only counts towards a clue that is not found yet.
            if key not in CH2_CLUE_FLAGS or not self.chapter_two_open or self.clue_found(key):
                return
            if name == CLUE_FOUND_EVENT:
                state.setdefault("flags", {})[CH2_CLUE_FLAGS[key]] = True
                numeral, symbol, game = next((n, sym, g) for c, n, sym, g in CH2_SYMBOLS if c == key)
                found = state.setdefault("stats", {}).get(CH2_SYMBOLS_FOUND)
                found = dict(found) if isinstance(found, dict) else {}
                found[numeral] = {"symbol": symbol, "game": game}
                state["stats"][CH2_SYMBOLS_FOUND] = found
                self.save()
                self._fire("progress")                       # the corner tracker's SYMBOLS count moves (no pop-up)
                return
            else:
                tries = state.setdefault("stats", {}).get(CH2_TRIES)
                tries = dict(tries) if isinstance(tries, dict) else {}
                tries[key] = self.clue_tries(key) + 1
                state["stats"][CH2_TRIES] = tries
            self.save()
            return
        elif name in (MIAO_CH2_HINT, CH2_RIDDLE_SOLVED):
            # once, and only after all three clues (the record's question does not exist before that)
            if not (self.chapter_two_open and self.all_clues_found) or state.get("flags", {}).get(name):
                return
            state.setdefault("flags", {})[name] = True
            self.save()
            return
        elif name in (MOCHI_ARCADE_STORY, MIAO_REVERSE_ROAD):
            flags = state.setdefault("flags", {})
            ready = self.secret_interface_unlocked if name == MOCHI_ARCADE_STORY else self.has_secret_item(SECRET_ITEM_RETRO_RACER)
            if ready and not flags.get(name):         # once, and only when what it talks about has really happened
                flags[name] = True
                changed = True
        elif name == "vending_secret" or name in TOUR_EVENTS:
            if not state.setdefault("flags", {}).get(name):
                state["flags"][name] = True
                changed = True
        elif name == FINALE_EVENT:                            # the reopening itself: only once all six are done
            q = self.active
            if q is not None and q.trigger == ("event", FINALE_EVENT) and self.finale_unlocked:
                state.setdefault("progress", {}).setdefault(q.id, {})["done"] = True
                changed = True
        elif name == "tickets_earned":
            q = self.active
            if q is not None and q.trigger == ("event", "tickets_earned"):
                state.setdefault("progress", {}).setdefault(q.id, {})["done"] = True
                changed = True
        if changed and self.opening_done:
            self._fire("progress")
        if self._settle() or changed:
            self.save()

    def finish_opening(self):
        """The opening cutscene is over: the first quest is announced. Idempotent."""
        if self.opening_done:
            return False
        self.state["opening_done"] = True
        first = self.active
        self._settle(silent=True)
        if first is not None and self.active is first:
            self.notifications.append(Notification("quest", first))
        self.save()
        self._fire("opening")
        return True

    # ------------------------------------------------------------ completing
    def _met(self, quest):
        kind = quest.trigger[0]
        stats, flags = self.state.get("stats", {}), self.state.get("flags", {})
        if kind == "played":
            return len(stats.get("played", ())) >= quest.trigger[1]
        if kind == "event":
            return bool(self.state.get("progress", {}).get(quest.id, {}).get("done"))
        if kind == "sticky":
            return bool(flags.get(quest.trigger[1]))
        if kind == "counters":
            return all(len(stats.get(k, ())) >= n for k, n in quest.trigger[1].items())
        if kind == "item":
            return self.has_secret_item(quest.trigger[1])
        if kind == "trial":
            return self.trial_done(quest.trigger[1])
        return False

    def _settle(self, silent=False):
        """Complete every quest whose condition is met, in order (so a veteran or an early secret never gets stuck).
        Only the last step of a run is announced. Returns True if anything completed. Quests wait for the opening."""
        if not self.opening_done:
            return False
        moved = False
        while True:
            q = self.active
            if q is None or not self._met(q):
                break
            self._complete(q, silent)
            moved = True
        if moved and not silent:
            nxt = self.active
            if nxt is not None:
                self.notifications.append(Notification("quest", nxt))
        return moved

    def _complete(self, quest, silent):
        done = self.state.setdefault("completed", [])
        if quest.id in done:                                    # never twice: no second reward
            return
        done.append(quest.id)
        if quest.reward_tokens and not silent:
            for p in self.profiles:
                p.add_tokens(quest.reward_tokens, "QUEST")
        if not silent:
            if quest.id == "check_the_vending_machine":
                self.notifications.append(Notification("protocol", lines=PROTOCOL_LINES))
            self._fire("complete")

    def _fire(self, kind):
        for cb in list(self._change_hooks):
            cb(kind)

    # ------------------------------------------------------------ saving
    def save(self):
        for p in self.profiles:
            p.set_story(self.state)
