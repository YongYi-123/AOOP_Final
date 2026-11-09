"""The main story's quests: data (QUESTS), the progress state, and the QuestManager that moves it along.

DATA-DRIVEN. A quest is one QuestDef row; to add one, add a row (and, if it needs a new kind of trigger, one
branch in QuestManager._met). Nothing else in the game names a quest.

    trigger kinds
      ("played", N)        N different arcade machines have been played (a running story-wide count)
      ("event", name)      the event `name` happens while this quest is the active one
      ("sticky", name)     the event `name` has happened, even before the quest started (a found secret stays found)
      ("counters", {...})  every named counter has reached its target (secret items / trials)

SHARING. The story belongs to the SESSION, not to one person: a one- or two-player session shares one main quest,
and either player's actions move it. It is saved in EVERY profile of the session (PlayerProfile.story), so each
save keeps the story and the next session starts from the most advanced copy. A profile saved before the story
existed has no story: it is read as 'veteran' (opening skipped, finished steps ticked) so nobody is sent back to
the tutorial or left waiting for something they already did.

THE TOUR. Quests one and two (THE GRAND TOUR, MEET THE LOCALS) are "sticky": the tour conversations (tour.py) fire the
events "tour_arcade" / "met_mochi" the first time the players reach those rooms, and a found flag stays found, so a
player who wanders to the Prize Plaza first is not sent back, and a conversation that has played never plays again.
Saves from before the tour are migrated (migrate_story): whoever was already past "Get Your Bearings" skips the tour.

The vending-machine step is only completed by the REAL hidden screen (vending_ui.py fires a "vending_secret"
event the moment its listener recognises the secret sequence); opening the ordinary shop never counts.
"""
import copy
from collections import deque
from dataclasses import dataclass, field

from player_profile import clean_story

VENDING_SECRET_FLAG = "vending_konami_discovered"      # the profile secret vending_ui.py already records
SECRET_ITEMS_NEEDED = 3
SECRET_TRIALS_NEEDED = 3


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
    QuestDef("the_way_out", "The Way Out", "Collect 3 Secret Items and complete 3 Secret Trials.",
             "COLLECT SECRETS, FINISH TRIALS",
             ("counters", {"secret_items": SECRET_ITEMS_NEEDED, "secret_trials": SECRET_TRIALS_NEEDED}),
             ("We need 3 secret items and 3 secret trials. I don't know where they are... yet!",
              "Keep exploring every room. Secrets love to hide where we've stopped looking.")),
)
_ORDER = {q.id: i for i, q in enumerate(QUESTS)}

# ------------------------------------------------------------------ the three Secret Trials
@dataclass(frozen=True)
class TrialDef:
    """One Secret Trial (an escape room). `requires` are trials that must be done first; `cost_names` name the
    settings constants holding the Tickets / Tokens the player must HOLD (read at use, so they stay configurable)."""
    id: str
    number: int
    title: str
    requires: tuple = ()
    cost_names: tuple = None            # ("SETTING_FOR_TICKETS", "SETTING_FOR_TOKENS")


TRIALS = (
    TrialDef("trial_01", 1, "THE GOLDEN AGE"),
    TrialDef("trial_02", 2, "THE UNBEATEN RECORD"),
    TrialDef("trial_03", 3, "THE FINAL LOCK", requires=("trial_01", "trial_02"),
             cost_names=("TRIAL_FINAL_TICKETS", "TRIAL_FINAL_TOKENS")),
)
TRIALS_BY_ID = {t.id: t for t in TRIALS}


@dataclass(frozen=True)
class TrialStatus:
    code: str                           # "done", "available" or "locked"
    reasons: tuple = ()                 # why it is locked, one short line each
    tickets_needed: int = 0
    tokens_needed: int = 0
    tickets_have: int = 0
    tokens_have: int = 0

    @property
    def needs_currency(self):
        return bool(self.tickets_needed or self.tokens_needed)

    @property
    def short(self):
        return {"done": "COMPLETE", "available": "AVAILABLE", "locked": "LOCKED"}[self.code]


def trial_cost(trial):
    """(tickets, tokens) the player must hold for `trial`, read from settings every time."""
    if not trial.cost_names:
        return 0, 0
    import settings
    return getattr(settings, trial.cost_names[0]), getattr(settings, trial.cost_names[1])


def trial_status(manager, profile, trial):
    """Whether `trial` can be entered by the player holding `profile`: done, available, or locked (and exactly why).
    Reading this never changes anything, and never charges anything."""
    tickets, tokens = trial_cost(trial)
    have_t, have_k = profile.tickets, profile.tokens
    base = dict(tickets_needed=tickets, tokens_needed=tokens, tickets_have=have_t, tokens_have=have_k)
    if manager.trial_done(trial.id):
        return TrialStatus("done", **base)
    reasons = []
    missing = [TRIALS_BY_ID[r] for r in trial.requires if not manager.trial_done(r)]
    if missing:
        nums = " AND ".join(f"{t.number:02d}" for t in missing)
        reasons.append(f"COMPLETE TRIAL{'S' if len(missing) > 1 else ''} {nums} FIRST")
    if tickets and have_t < tickets:
        reasons.append(f"NEED {tickets} TICKETS (YOU HAVE {have_t})")
    if tokens and have_k < tokens:
        reasons.append(f"NEED {tokens} TOKENS (YOU HAVE {have_k})")
    return TrialStatus("locked" if reasons else "available", tuple(reasons), **base)


def exit_status(manager):
    """The final reopening: needs every Secret Item AND every Secret Trial. Returns (unlocked, reasons)."""
    reasons = []
    if manager.secret_items < SECRET_ITEMS_NEEDED:
        reasons.append(f"NEED {SECRET_ITEMS_NEEDED} SECRET ITEMS (HAVE {manager.secret_items})")
    if manager.secret_trials < SECRET_TRIALS_NEEDED:
        reasons.append(f"NEED {SECRET_TRIALS_NEEDED} SECRET TRIALS (HAVE {manager.secret_trials})")
    return not reasons, tuple(reasons)


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


def _progress_rank(story):
    return (len(story.get("completed", ())), len(story.get("flags", ())), bool(story.get("opening_done")),
            sum(story.get("hints", {}).values()))


def merge_stories(stories, quests=QUESTS):
    """The one shared story of a session: the most advanced copy, plus everything any copy knows.
    Completed quests are the union (kept in quest order); counters and played machines take the larger / the union."""
    stories = [clean_story(s) for s in stories]
    stories = [s for s in stories if s]
    if not stories:
        return {}
    best = copy.deepcopy(max(stories, key=_progress_rank))
    order = {q.id: i for i, q in enumerate(quests)}
    done = {c for s in stories for c in s.get("completed", ())}
    best["completed"] = sorted(done, key=lambda c: order.get(c, len(order)))
    if any(s.get("opening_done") for s in stories):
        best["opening_done"] = True
    flags = {}
    for s in stories:
        flags.update(s.get("flags", {}))
    if flags:
        best["flags"] = flags
    played = []
    for s in stories:
        for g in s.get("stats", {}).get("played", ()):
            if g not in played and isinstance(g, str):
                played.append(g)
    if played:
        best.setdefault("stats", {})["played"] = played
    for s in stories:
        for key in ("secret_items", "secret_trials"):
            mine, theirs = best.get("stats", {}).get(key), s.get("stats", {}).get(key)
            if isinstance(theirs, list):
                merged = list(dict.fromkeys((mine if isinstance(mine, list) else []) + theirs))
                best.setdefault("stats", {})[key] = merged
    for s in stories:
        for k, n in s.get("hints", {}).items():
            best.setdefault("hints", {})[k] = max(best.get("hints", {}).get(k, 0), n)
    return clean_story(best)


# ------------------------------------------------------------------ the manager
class QuestManager:
    """Owns the session's shared story. Listens to the profiles (games played, tickets earned) and the session
    (story events), advances quests, queues announcements for the UI and saves into every profile."""

    def __init__(self, session, quests=QUESTS):
        self.session = session
        self.quests = tuple(quests)
        self.by_id = {q.id: q for q in self.quests}
        self.profiles = list(session.profiles)
        self.notifications = deque()
        self._lifetime = {}
        self._change_hooks = []
        stories = []
        for p in self.profiles:
            story = p.story
            if not story and has_history(p):
                story = veteran_state(p, self.quests)
            stories.append(migrate_story(story, self.quests) if story else story)
        self.state = merge_stories(stories, self.quests)
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
        q = self.active
        return q is not None and q.trigger[0] == "counters"

    @property
    def protocol_active(self):
        """Has the legacy protocol been unlocked (the vending secret found and its quest completed)?"""
        return "check_the_vending_machine" in self.completed_ids or self.way_out_active or \
            (self.active is None and bool(self.completed_ids))

    def counter(self, name):
        found = self.state.get("stats", {}).get(name, [])
        return len(found) if isinstance(found, list) else 0

    def trial_done(self, trial_id):
        """Has this Secret Trial been completed (by anyone in the session: the story is shared)?"""
        return trial_id in self.state.get("stats", {}).get("secret_trials", ())

    @property
    def secret_items(self):
        return min(self.counter("secret_items"), SECRET_ITEMS_NEEDED)

    @property
    def secret_trials(self):
        return min(self.counter("secret_trials"), SECRET_TRIALS_NEEDED)

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
        if event.type in ("vending_secret", "secret_item_found", "secret_trial_done"):
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
            counter = "secret_items" if name == "secret_item_found" else "secret_trials"
            found = state.setdefault("stats", {}).setdefault(counter, [])
            ident = key if isinstance(key, str) and key else f"{counter}_{len(found) + 1}"
            if ident not in found:
                found.append(ident)
                changed = True
        elif name == "vending_secret" or name in TOUR_EVENTS:
            if not state.setdefault("flags", {}).get(name):
                state["flags"][name] = True
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
