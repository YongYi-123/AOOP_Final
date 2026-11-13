"""CHAPTER 02, THE FORGOTTEN GAMES: how the hub joins up the chapter's pieces. (The saved state is quests.py's.)

    1  HINT CARDS      Once Chapter 02 is open (Trial 01 done), three RETRO HINT CARDS join the ordinary prize pool of
                       both capsule machines (HintCardDraw, given to capsule.CapsuleService as its `bonus`). A card is a
                       single-copy collectible, so only cards still missing can come out (no duplicates), and after
                       CARD_PITY_AFTER pulls in a row without one the next pull is a missing card. They are reread in
                       the bag. Owning them is never required: they only say where to look. Once the Golden Cat is
                       won (Secret Item 02) no more cards come out.
    2  THREE SYMBOLS   NEON CAT MAZE (a hidden corridor behind a cracked corner: I STAR), STARFALL ASSAULT (a quiet,
                       non-hostile ship that returns every calm: II MOON) and CAT VOLLEYBALL (an old spectator ticket
                       after a completed match: III PAW). Each game package owns its own secret and both of its routes:
                       ACE (a real skill milestone: COMPLETE level 3 / CLEAR wave 10 / BEAT Sandra; the game reports
                       "unlocked" and the story keeps a flag) and PERSISTENCE (CH2_TRIES_NEEDED meaningful failed tries,
                       counted here across sessions, never reset). Either way the encounter then stays available, game
                       after game and after a reload, until the player finds it; reaching a route never awards the
                       symbol by itself. Each found symbol is recorded in the story and listed in the Quest Log
                       (RECOVERED SYMBOLS, unknown ones as ???). ClueLink connects a minigame scene to the story.
    3  MIAO MEOW       Once all three are found, she has one thing to say the next time the player is back in the hub
                       (story.StoryDirector, flag MIAO_CH2_HINT). She never names the answer.
    4  MOCHI & LOCK    Mochi gains "Did you find something unusual?" (mochi_chat.py) and shows an old maintenance
                       record (maintenance_note.py, read only) that points to the claw machine's prize lock. The lock
                       itself is on NEON CLAW (claw_lock.py, UP in the claw screen): three wheels that start empty
                       and offer the three symbols among decoys; is_combination() checks STAR, MOON, PAW. A wrong try
                       only gets a gentle line and can be retried at once; Q shows the Quest Log's symbols there.
    5  GOLDEN CAT      Opening the lock puts the Golden Cat Plushie into NEON CLAW (GoldenCatPrize, the claw machine's
                       `special`). It is won with the ordinary claw, and only a plushie that really drops into the chute
                       awards Secret Item 02 (quests.SECRET_ITEM_CLAW), once. Every slipped grab on it makes the next
                       one firmer, and after GOLDEN_SURE_AFTER slips any grab that touches it holds.
Nothing here runs before Chapter 02 opens, and the ordinary capsule and claw machines behave exactly as before.
"""
from capsule import CapsulePrize
from claw_machine import PlushSpec
from local_session import GameEvent
from quests import CH2_CLUES, CH2_SYMBOLS, CLUE_FOUND_EVENT, CLUE_ROUTE_EVENT, CLUE_TRY_EVENT, SECRET_ITEM_CLAW
from story_dialogue import Line

# ------------------------------------------------------------------ 1. the hint cards (item ids: item_registry)
HINT_CARDS = {"maze": "hint_card_maze", "galaxy": "hint_card_galaxy", "volley": "hint_card_volley"}
CARD_WEIGHT = 9                 # per missing card, next to a machine's ~110 of ordinary weight: about 1 pull in 5
CARD_PITY_AFTER = 4             # this many pulls in a row without a card: the next one is a missing card


def story_manager(game):
    story = getattr(getattr(game, "hub", None), "story", None)
    return story.manager if story is not None else None


class HintCardDraw:
    """The capsule machines' Chapter 02 extra: the hint cards the profile is still missing, and the pity counter."""

    def __init__(self, manager):
        self.manager = manager

    def missing(self, profile):
        """The cards still to come out. None before Chapter 02, and none once the Golden Cat (Secret Item 02) is won:
        the secret is over, so the machines are ordinary again (cards already owned are kept)."""
        m = self.manager
        if m is None or not m.chapter_two_open or m.has_secret_item(SECRET_ITEM_CLAW):
            return []
        return [card for card in HINT_CARDS.values() if not profile.inventory.has_item(card)]

    def extra_prizes(self, service, kind):
        return [CapsulePrize(card, CARD_WEIGHT) for card in self.missing(service.profile)]

    def forced(self, service, kind):
        """True: this pull must be a missing card (the pity counter is full)."""
        return bool(self.missing(service.profile)) and self.manager.card_pity >= CARD_PITY_AFTER

    def after_pull(self, service, kind, item_id, offered):
        """Called inside the pull's batch. `offered`: were any cards in the pool for this pull?"""
        if not offered:
            return
        self.manager.set_card_pity(0 if item_id in HINT_CARDS.values() else self.manager.card_pity + 1)


# ------------------------------------------------------------------ 2. the clues in the minigames
class ClueLink:
    """Joins one minigame (its package object) to the story: tells it whether its secret may exist and whether it is
    there from the start, and turns what it reports ("found" / "try") into the story's events, for the player."""

    def __init__(self, scene, clue):
        assert clue in CH2_CLUES
        self.scene, self.clue = scene, clue

    def manager(self):
        return story_manager(self.scene.game)

    def sync(self, target):
        m = self.manager()
        target.secret_enabled = bool(m is not None and m.chapter_two_open)
        target.secret_ready = bool(m is not None and m.clue_due(self.clue))
        if hasattr(target, "secret_found"):
            target.secret_found = bool(m is not None and m.chapter_two_open and m.clue_found(self.clue))
        pop = getattr(target, "pop_secret_events", None)
        for name in (pop() if pop else ()):
            event = {"found": CLUE_FOUND_EVENT, "try": CLUE_TRY_EVENT, "unlocked": CLUE_ROUTE_EVENT}.get(name)
            if event is None or m is None:
                continue
            players = getattr(self.scene, "players", None)
            owner = players[0] if players else self.scene.game.session.primary
            self.scene.game.session.dispatch(GameEvent(event, owner.player_id, key=self.clue))


# ------------------------------------------------------------------ 3. Miao Meow (told once, in the hub)
MIAO, MOCHI = "MIAO MEOW", "MOCHI"
MIAO_HINT_LINES = (
    Line(MIAO, "Hey! Mochi was acting kinda weird earlier!", "surprised"),
    Line(MIAO, "She said she found something interesting at the Prize Counter.", "normal"),
    Line(MIAO, "But when I asked her what it was, she just smiled!", "happy"),
    Line(MIAO, "You should go talk to her!", "happy"),
)

# ------------------------------------------------------------------ 4. Mochi's maintenance record and its lock
UNUSUAL = "Did you find something unusual?"
RECORD_INTRO = (
    Line(MOCHI, "Heh. You noticed?", "happy"),
    Line(MOCHI, "I was tidying under the Prize Counter and found this. An old maintenance record.", "gentle"),
    Line(MOCHI, "It says the claw machine has a little prize lock. Three wheels. Nobody ever got it open.", "normal"),
    Line(MOCHI, "Maybe you've seen those marks somewhere? Go and have a look at the claw machine.", "gentle"),
)
RECORD_TITLE = "MAINTENANCE RECORD  NIGHT SHIFT"
RECORD_LINES = (                # one line each on the paper (at most 56 characters)
    "PRIZE LOCK ON THE CLAW MACHINE JAMMED AGAIN.",
    "THE GOLDEN ONE STAYS INSIDE. NEVER CAME DOWN THE CHUTE.",
    "SPARE LOCK MARKS LEFT IN THREE OLD GAMES.",
    "EACH MARK HAS ITS NUMBER. SET THEM IN ORDER.",
    "THE GOLDEN PRIZE WAITS FOR SOMEONE WHO REMEMBERS.",
)
LOCK_PLATE = ("NEON CLAW  PRIZE LOCK", "TURN EACH WHEEL TO ITS MARK")    # the brass plate above the lock (claw_lock.py)
LOCK_SLOTS = ("I", "II", "III")                              # the wheels, left to right
COMBINATION = tuple(symbol for _, _, symbol, _ in CH2_SYMBOLS)   # STAR, MOON, PAW (the numbered symbols, in order)
# Every wheel offers the same marks: the three real symbols among decoys. Wheels start EMPTY (nothing is ever filled in
# for the player, not even from the Quest Log).
LOCK_CHOICES = ("HEART", "STAR", "FISH", "BOLT", "MOON", "KEY", "CROWN", "PAW", "EYE")
WRONG_LINES = (
    "THE WHEELS CLICK, BUT THE LOCK STAYS SHUT.",
    "MOCHI SMILES.  NOT QUITE.  TRY AGAIN ANY TIME.",
    "HMM. THE LOCK DOES NOT SEEM TO AGREE.",
)
UNSET_LINE = "SET ALL THREE WHEELS FIRST."
RIGHT_LINE = "CLICK! THE PRIZE LOCK OPENS."
SOLVED_LINE = "RESTOCKED"                       # the stamp on the record once the lock is open


def is_combination(marks):
    """Are these the three wheels' marks, left to right, that open the lock?"""
    return tuple(marks) == COMBINATION


# ------------------------------------------------------------------ 5. the Golden Cat in NEON CLAW
GOLDEN_SLOT = 2                 # the middle of the six spots (SLOTS[2])
GOLDEN_SURE_AFTER = 3           # slipped grabs on it: from then on any grab that touches it holds
GOLDEN_MISS_BONUS = 0.12        # each slip before that adds this much grip
GOLDEN_CAT = PlushSpec("claw_golden_cat", "GOLDEN CAT", 16, 15, 0.8, 0,
                       dict(kind="golden", body=(255, 204, 70), dark=(206, 138, 30), accent=(255, 248, 210),
                            eye=(96, 52, 14)), hidden=True)


class GoldenCatPrize:
    """NEON CLAW's `special` while the Golden Cat is waiting (quests.QuestManager.golden_cat_wanted)."""

    def __init__(self, manager, dispatch):
        self.manager = manager
        self.dispatch = dispatch            # callable(GameEvent-type, key): reports the Secret Item to the story
        self.won = False

    @property
    def wanted(self):
        return not self.won and self.manager.golden_cat_wanted

    def in_machine(self, game):
        held = [game.held, game.in_chute] + list(getattr(game, "falling", ()))
        plushies = list(getattr(game, "plushies", ())) + [p for p in held if p is not None]
        return any(p.spec is GOLDEN_CAT for p in plushies)

    # -- the claw machine's hooks
    def stock(self, game, slot):
        if slot != GOLDEN_SLOT or not self.wanted or self.in_machine(game):
            return None
        return GOLDEN_CAT

    def adjust_odds(self, game, spec, odds):
        if spec is not GOLDEN_CAT or odds <= 0:
            return odds
        misses = self.manager.golden_misses
        if misses >= GOLDEN_SURE_AFTER:
            return 1.0
        return min(1.0, odds + GOLDEN_MISS_BONUS * misses)

    def on_lose(self, game, attempt):
        target = attempt.target
        if target is not None and target.spec is GOLDEN_CAT and attempt.odds > 0:
            self.manager.note_golden_miss()

    def on_win(self, game, spec, profile):
        if spec is not GOLDEN_CAT or self.won:
            return
        self.won = True
        if self.manager.can_collect(SECRET_ITEM_CLAW) and not self.manager.has_secret_item(SECRET_ITEM_CLAW):
            self.dispatch("secret_item_found", SECRET_ITEM_CLAW)


def golden_cat_for(scene):
    """The `special` for a ClawScene being opened: a GoldenCatPrize while the Golden Cat waits, else None (ordinary)."""
    manager = story_manager(scene.game)
    if manager is None or not manager.golden_cat_wanted:
        return None
    player = scene.player

    def dispatch(kind, key):
        owner = player or scene.game.session.primary
        scene.game.session.dispatch(GameEvent(kind, owner.player_id, key=key))
    return GoldenCatPrize(manager, dispatch)
