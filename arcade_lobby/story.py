"""The story layer of the hub: one StoryDirector per RoomHub, shared by all three rooms.

It owns and connects
    QuestManager   (quests.py)       the shared main quest and its save
    MiaoBrain      (miao_meow.py)    where Miao Meow is and what she is doing
    ObjectiveTracker / QuestBanner / QuestLogUI  (quest_ui.py)   the quest screens
    StoryDialogue  (story_dialogue.py)  the RPG dialogue box
    OpeningCutscene (below)          the one-time intro

and the rooms only ask it a few things: update(), draw_world() / draw_hud() / draw_front(), modal, locked,
hides_hud, blockers(), toggle_log(), talk_to_miao(). Nothing in a room knows about a particular quest.

THE OPENING plays once, in HOME, when the players enter the arcade from the startup flow (opening_enabled):

    intro        black, a faint hum -> a beep and a flicker -> the eyes half open -> shut again (the sound muffles) ->
                 wide open (the arcade sounds clearer) -> the neon stutters on -> steady
    monologue    the student wakes up: a deadline, NYCU, no laptop, and an ARCADE
    approach     a coin-bell jingles; Miao Meow runs in from the door
    talk         they meet; control returns; the first NEW MAIN QUEST appears

Everything in the intro hangs on ONE timeline (Timeline): a list of named events at fixed times, advanced by the
accumulated frame time, never by frame counts, each fired exactly once and in order. The picture (screen cover, eyelids)
and the sound (cues, ambience level, music level) are all functions of that same clock, so they cannot drift apart at
any frame rate; `trace` records when each event was scheduled and when it really fired. The cutscene can be skipped
(ESC during the intro / the run-in): the remaining events are marked done silently and the end state is applied at
once; cleanup() always puts the ambience and the music back, so nothing is left muffled, however it ends.

AFTER THE OPENING the ARCADE TOUR (tour.py) plays: one short conversation the first time the players reach HOME, the
ARCADE FLOOR and the PRIZE PLAZA (where Miao Meow and Mochi bicker). Each plays once, is saved as a flag in the shared
story, and its events are what quests THE GRAND TOUR and MEET THE LOCALS wait for (quests.py). Players stay free to roam.

Input is locked (players stand still) for the whole scene; the dialogue is the only thing that answers keys. It is saved
the moment it ends, in every profile of the session, so it never plays twice. A save that predates the story is read as a
veteran's (see quests.py), so nobody is sent back to it.
"""
import pygame

from miao_meow import ARCADE, HOME, SPOTS, THRESHOLD, MiaoBrain
from quest_ui import ObjectiveTracker, QuestBanner, QuestLogUI
from quests import MIAO_CH2_HINT, MIAO_REVERSE_ROAD, SECRET_ITEM_RETRO_RACER, QuestManager
from settings import VIEW_H, VIEW_W
from story_dialogue import LOW_ON_SCREEN as D_LOW, Line, StoryDialogue
import forgotten_games
from tour import ENTER_DELAY, TOURS, Tour, TourGuide
from ui import speech_bubble_image

MIAO, YOU = "MIAO MEOW", "PLAYER"

# The protagonist is a student who fell asleep finishing a deadline at NYCU. First they wake up alone...
OPENING_WAKE = (
    Line(YOU, "...Ugh. Did I fall asleep?"),
    Line(YOU, "Wait... wasn't I just at NYCU trying to finish my deadline?"),
    Line(YOU, "Where's my laptop?"),
    Line(YOU, "...And why am I in an ARCADE?!", "gentle"),
)
# ...then Miao Meow runs in, thrilled to see a human, and not at all sure how anything works.
OPENING_MEET = (
    Line(MIAO, "Meow?! You're awake!", "surprised"),
    Line(MIAO, "Wait! A human?! A real human?!", "surprised"),
    Line(MIAO, "Oh my gosh!! Hi!!!", "happy"),
    Line(YOU, "...A talking cat?"),
    Line(MIAO, "Yep! That's me!", "happy"),
    Line(MIAO, "I'm Miao Meow! Nice to meet you!", "happy"),
    Line(YOU, "Okay... either I'm dreaming, or that deadline finally broke my brain."),
    Line(MIAO, "Hehe! I don't know what a deadline is, but it sounds scary!", "happy"),
    Line(MIAO, "Anyway, welcome to Neon Corner Arcade!", "happy"),
    Line(YOU, "Do you know how I get back?"),
    Line(MIAO, "Um... no. Sorry...", "gentle"),
    Line(MIAO, "But we can figure it out together!", "happy"),
    Line(MIAO, "Come on! I'll show you around!", "happy"),
)
OPENING_LINES = OPENING_WAKE + OPENING_MEET

# What happens on screen as each line starts: (part, index) -> [(action, who-or-arg, arg), ...]. Timed by the dialogue itself.
BEATS = {
    ("wake", 0): [("bubble", "player", "...")],
    ("wake", 1): [("bubble", "player", "?")],
    ("wake", 2): [("look", "player", "left"), ("bubble", "player", "?")],
    ("wake", 3): [("pose", "player", "cheer"), ("bubble", "player", "!")],
    ("meet", 0): [("hop", "miao"), ("bubble", "miao", "!"), ("meow", None)],
    ("meet", 2): [("hop", "miao"), ("jingle", 0.45)],
    ("meet", 3): [("look", "player", "left"), ("bubble", "player", "?")],
    ("meet", 4): [("hop", "miao")],
    ("meet", 6): [("bubble", "player", "...")],
    ("meet", 8): [("hop", "miao"), ("jingle", 0.4)],
    ("meet", 12): [("hop", "miao"), ("jingle", 0.5)],
}

REVERSE_ROAD_CHAT = (            # told once, the next time she is spoken to after the Reverse Gear was found
    Line(MIAO, "YOU FOUND A SECRET ROAD?!", "surprised"),
    Line(YOU, "Yeah... apparently driving backwards was the answer."),
    Line(MIAO, "BACKWARDS?!", "surprised"),
    Line(MIAO, "Hahaha! Humans are so weird!", "happy"),
    Line(MIAO, "Can we try it together next time?", "happy"),
)

GREETINGS = (
    ("Oh! Hi hi! You came to see me!", "happy"),
    ("Yay, company! I could talk to you all day!", "happy"),
    ("I was just thinking about snacks. And also you! Mostly you!", "happy"),
    ("Don't wander off too far, okay? I like having you around.", "gentle"),
)
NO_QUEST_CHAT = (
    ("The arcade feels so much warmer with you here.", "gentle"),
    ("Let's keep looking around. There's always something new!", "happy"),
)


def curve(keys, t):
    """Piecewise-linear value of `keys` [(time, value), ...] at `t` (clamped to the ends)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


class Timeline:
    """Named events at fixed times on one clock. advance(dt) moves the clock by the real time that passed and fires
    every event that is now due, once each, in time order (a long frame fires several; a short one maybe none), so
    the result is the same at any frame rate. `trace` is [(name, scheduled, actual)]."""

    def __init__(self, events):
        self.events = sorted(events)
        self.t = 0.0
        self.next = 0
        self.trace = []

    @property
    def done(self):
        return self.next >= len(self.events)

    def advance(self, dt, fire):
        self.t += dt
        while self.next < len(self.events) and self.events[self.next][0] <= self.t:
            at, name = self.events[self.next]
            self.next += 1
            self.trace.append((name, at, self.t))
            fire(name)

    def finish(self, fire_silently):
        """Skip: the clock jumps to the end; the remaining events are marked done and handed to `fire_silently`
        (so the caller can apply their state without any sound or flash)."""
        while self.next < len(self.events):
            at, name = self.events[self.next]
            self.next += 1
            self.trace.append((name + " (skipped)", at, self.t))
            fire_silently(name)
        self.t = max(self.t, self.events[-1][0] if self.events else 0.0)


# ------------------------------------------------------------------ the opening
class OpeningCutscene:
    """intro -> monologue -> approach -> talk -> hand control back."""
    # the one timeline of the intro: (seconds, event). Pictures and sounds are curves of the same clock, below.
    INTRO = ((0.05, "hum"), (0.90, "beep"), (1.70, "eyes_open_1"), (2.40, "eyes_close"), (3.10, "eyes_open_2"),
             (3.55, "neon_1"), (3.85, "neon_2"), (4.10, "neon_3"), (4.35, "neon_steady"), (4.80, "intro_end"))
    COVER = ((0.0, 255), (0.90, 255), (0.93, 238), (1.05, 238), (1.08, 255), (1.70, 255), (1.90, 225),         # dark; a faint flicker on the beep
             (3.55, 225), (3.58, 150), (3.70, 225), (3.85, 225), (3.88, 110), (3.98, 225),                   # each flicker starts at its sound's time
             (4.10, 225), (4.13, 60), (4.22, 170), (4.35, 170), (4.38, 30), (5.00, 0))                       # ... and the neon holds steady
    LIDS = ((0.0, 0.0), (1.70, 0.0), (2.10, 0.35), (2.40, 0.35), (2.65, 0.0), (3.10, 0.0), (3.90, 1.0), (9.0, 1.0))     # eyes: part open, shut, open
    AMBIENCE = ((0.0, 0.22), (2.40, 0.22), (2.55, 0.08), (3.10, 0.08), (3.90, 0.60), (4.35, 0.80), (5.40, 1.0))        # the hum: quiet, muffled, clear
    DUCK = ((0.0, 0.25), (2.40, 0.25), (2.55, 0.10), (3.10, 0.10), (3.90, 0.50), (5.40, 1.0))                          # the music, the same way
    CUES = {"hum": ("vend_hum", 0.35), "beep": ("vend_select", 0.30), "eyes_open_1": ("emote", 0.28),
            "eyes_open_2": ("vend_hum", 0.30), "neon_1": ("machine", 0.22), "neon_2": ("machine", 0.28),
            "neon_3": ("machine", 0.34), "neon_steady": ("zap", 0.30)}
    PLAYER_AT = (214, 176)              # the scene plays mid-room, above the dialogue box
    RUN_SPEED = 70.0                    # Miao Meow runs in
    JINGLE_EVERY = 0.34                 # seconds between coin-bell jingles while she runs
    APPROACH_TIMEOUT = 8.0

    def __init__(self, director, room):
        self.director = director
        self.room = room
        self.stage = "intro"
        self.clock = 0.0                # the whole scene's clock: curves read it, the intro timeline is driven by it
        self.timeline = Timeline(self.INTRO)
        self.finished = False
        self.bubbles = []               # [{"text", "who", "born"}]
        self._later = []                # [(due clock time, callable)]
        self._flash = 0.0
        self._jingle = 0.0
        self._approach_clock = 0.0
        self._ambience_target = dict(getattr(room, "ambience_mix", {}))
        self.cleaned = False
        brain = director.brain
        brain.place(ARCADE, SPOTS[ARCADE]["centre"], "right")          # Miao Meow is not in this room yet
        brain.scripted = True
        for p in room.players:
            p.x, p.y = float(self.PLAYER_AT[0]), float(self.PLAYER_AT[1])
            p.facing = "up"
            p.stop()
            p.held.clear()
        self._apply_audio()

    @property
    def trace(self):
        return self.timeline.trace

    # ------------------------------------------------------------ the shared clock drives picture AND sound
    def _apply_audio(self):
        """The ambience and the music level are curves of the scene clock: quiet, muffled, then clear."""
        d = self.director
        ambience = getattr(d.hub, "ambience", None)
        level = curve(self.AMBIENCE, self.clock)
        if ambience is not None and self._ambience_target:
            ambience.set_mix({k: v * level for k, v in self._ambience_target.items()})
        d.music_duck = curve(self.DUCK, self.clock)

    def _fire(self, name):
        cue = self.CUES.get(name)
        if cue is not None:
            self.director.play(*cue, event=name)
        if name == "beep":
            self._flash = 0.12
        elif name == "intro_end":
            self._start_monologue()

    def _fire_silently(self, name):
        if name == "intro_end":
            self._start_monologue()

    def update(self, dt, room):
        self.clock += dt
        brain = self.director.brain
        if self.stage == "intro":
            self.timeline.advance(dt, self._fire)
        elif self.stage == "approach":
            self._approach_clock += dt
            self._jingle += dt
            if brain.moving and self._jingle >= self.JINGLE_EVERY:
                self._jingle = 0.0
                p = room.players[0]
                near = max(0.0, 1.0 - ((brain.x - p.x) ** 2 + (brain.y - p.y) ** 2) ** 0.5 / 220.0)
                self.director.play("coin_clink", 0.16 + 0.34 * near, event="bell")
            if brain.arrived or self._approach_clock > self.APPROACH_TIMEOUT:
                self._start_talk(room, teleport=not brain.arrived)
        self._apply_audio()
        self._flash = max(0.0, self._flash - dt)
        for item in list(self._later):
            if self.clock >= item[0]:
                self._later.remove(item)
                item[1]()
        self.bubbles = [b for b in self.bubbles if self.clock - b["born"] < 1.5]

    # ------------------------------------------------------------ stages
    def _start_monologue(self):
        self.stage = "monologue"
        self.timeline.t = max(self.timeline.t, self.INTRO[-1][0])
        room = self.room
        self.director.open_dialogue(room, room.players[0], OPENING_WAKE, on_done=self._start_approach,
                                    on_line=lambda i, line: self._beat("wake", i))

    def _start_approach(self):
        self.stage = "approach"
        self._approach_clock = 0.0
        self._jingle = self.JINGLE_EVERY                               # the first jingle as she appears
        brain, room = self.director.brain, self.room
        p = room.players[0]
        brain.place(HOME, THRESHOLD["left"], "right")
        brain.scripted = True
        brain.watching = p
        brain.script_speed = self.RUN_SPEED
        brain.script_walk((p.x - 30, p.y))

    def _start_talk(self, room, teleport=False):
        brain = self.director.brain
        p = room.players[0]
        if teleport:
            brain.place(HOME, (p.x - 30, p.y), "right")
            brain.scripted = True
        self.stage = "talk"
        for pl in room.players:
            pl.facing = "left"                                         # they turn to face her
            pl.stop()
        brain.side = "right"
        brain.script_speed = None
        brain.watching = p
        brain.state = "script"
        self.director.open_dialogue(room, p, OPENING_MEET, on_done=self.finish,
                                    on_line=lambda i, line: self._beat("meet", i))

    def finish(self):
        d = self.director
        self.cleanup()
        d.brain.release()
        d.manager.finish_opening()
        self.finished = True
        d.cutscene = None
        for p in self.room.players:
            p.held = p.controls.held_now()
        offer = getattr(self.room, "_offer_daily_bonus", None)          # HOME held its daily bonus back for the opening
        if offer is not None:
            offer()

    def cleanup(self):
        """However the scene ends (finished, skipped, game closed): the arcade sounds and the music go back to normal."""
        if self.cleaned:
            return
        self.cleaned = True
        d = self.director
        ambience = getattr(d.hub, "ambience", None)
        if ambience is not None and self._ambience_target:
            ambience.set_mix(self._ambience_target)
        d.music_duck = None
        self.bubbles.clear()
        self._later.clear()

    # ------------------------------------------------------------ skipping
    def handle_event(self, event):
        """ESC while the scene runs by itself (the intro, the run-in) skips ahead to the next conversation."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.skip()

    def skip(self):
        """Jump to the next conversation. Safe at any moment: pending events are marked done without playing anything,
        the end state of the intro is applied at once, and no sound is left running."""
        if self.stage == "intro":
            self.timeline.finish(self._fire_silently)
            self.clock = max(self.clock, self.INTRO[-1][0] + 0.7)
            self._flash = 0.0
            self._apply_audio()
        elif self.stage == "approach":
            self._start_talk(self.room, teleport=True)

    # ------------------------------------------------------------ beats (what happens as each line starts)
    def _beat(self, part, index):
        for action in BEATS.get((part, index), ()):
            self._do(*action)

    def _do(self, action, who=None, arg=None):
        d, room = self.director, self.room
        p, brain = room.players[0], d.brain
        if action == "bubble":
            self.bubbles.append({"text": arg, "who": who, "born": self.clock})
        elif action == "hop":
            brain.notify("greet", p)
            brain.scripted = True
        elif action == "meow":
            brain._meow()
        elif action == "jingle":
            d.play("coin_clink", who if isinstance(who, float) else 0.4, event="bell")
        elif action == "look":
            for pl in room.players:
                pl.facing = arg
                pl.stop()
        elif action == "pose":
            p.play_action(arg, "down")

    # ------------------------------------------------------------ draw
    def draw_world(self, surf):
        """Over the lit world, under every HUD element: the dark screen cover, the eyelids and the little thought bubbles."""
        alpha = int(curve(self.COVER, self.clock)) if self.stage == "intro" or self.clock < self.COVER[-1][0] else 0
        if alpha > 0:
            cover = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            cover.fill((4, 2, 12, alpha))
            surf.blit(cover, (0, 0))
        bar = int((1 - curve(self.LIDS, self.clock)) * VIEW_H / 2)
        if bar > 0 and self.clock < 3.95:
            surf.fill((0, 0, 0), (0, 0, VIEW_W, bar))
            surf.fill((0, 0, 0), (0, VIEW_H - bar, VIEW_W, bar))
            for i in range(1, 4):                                       # a soft edge on the lids
                edge = pygame.Surface((VIEW_W, 1), pygame.SRCALPHA)
                edge.fill((0, 0, 0, 160 - i * 40))
                surf.blit(edge, (0, bar + i - 1))
                surf.blit(edge, (0, VIEW_H - bar - i))
        for b in self.bubbles:
            self._draw_bubble(surf, b)

    def _draw_bubble(self, surf, b):
        age = self.clock - b["born"]
        who = self.room.players[0] if b["who"] == "player" else self.director.brain
        img = speech_bubble_image(b["text"])
        rise = int(min(1.0, age / 0.15) * 3)
        rect = img.get_rect(midbottom=(int(who.x), int(who.y) - 24 - rise))
        img = img.copy()
        img.set_alpha(int(255 * min(1.0, (1.5 - age) / 0.3)))
        surf.blit(img, rect)

    @property
    def flashing(self):
        return self._flash > 0


# ------------------------------------------------------------------ the director
class StoryDirector:
    def __init__(self, hub):
        self.hub = hub
        self.session = hub.session
        self.manager = QuestManager(hub.session)
        self.brain = MiaoBrain(players=lambda: hub.avatars, sound=self.play)
        self.tracker = ObjectiveTracker(self.manager)
        self.banner = QuestBanner()
        self.dialogue = None
        self.log = None
        self.cutscene = None
        self.music_duck = None                  # the music level the story asks for (None: leave it alone)
        self.sound_log = []                     # (cutscene clock or None, effect, volume, event): what the story played, in order
        self.opening_enabled = False            # set by the startup flow: only a real game start plays the intro
        self._chats = 0
        self.guide = TourGuide(self)              # the one-time tour conversations (tour.py)
        self._ch2_wait = 0.0                      # seconds back in the hub with Miao Meow's Chapter 02 talk due

    def close(self):
        if self.cutscene is not None:
            self.cutscene.cleanup()
        self.manager.close()

    # ------------------------------------------------------------ what the rooms ask
    @property
    def modal(self):
        return self.dialogue or self.log

    @property
    def opening_pending(self):
        """A real game start that has not yet seen the opening: rooms hold back popups that would talk over it."""
        return self.opening_enabled and not self.manager.opening_done

    @property
    def locked(self):
        """The opening is playing: players stand still and only the dialogue answers keys."""
        return self.cutscene is not None

    @property
    def hides_hud(self):
        return self.locked or (self.dialogue is not None and self.dialogue.hides_hud)

    def play(self, name, volume=1.0, event=None):
        """Play an effect (at an extra volume 0..1) and remember it, with the opening's clock when it is running."""
        clock = self.cutscene.clock if self.cutscene is not None else None
        self.sound_log.append((None if clock is None else round(clock, 3), name, volume, event))
        del self.sound_log[:-400]
        audio = getattr(self.hub.game, "audio", None)
        if audio is not None:
            audio.play(name, volume) if volume != 1.0 else audio.play(name)

    def blockers(self, room, player):
        """Miao Meow's collision box for `player` (not while she overlaps them, so they can always walk free)."""
        if not self.brain.is_in(room.room_id):
            return []
        box = self.brain.footprint()
        return [] if box.colliderect(player.feet) else [box]

    def avoid_rects(self, room):
        """Screen areas an interaction prompt must not cover: the objective tracker, while it is showing."""
        if self.tracker.appear <= 0 or not self.manager.opening_done or self.manager.active is None:
            return []
        return [self.tracker.rect(room)]                  # the tab, plus whatever of the panel has slid out

    def on_room_enter(self, room):
        self.brain.on_room_enter(room)
        self.guide.on_room_enter(room)
        self._sync_anchor()

    def toggle_tracker(self, room=None):
        """TAB: fold or open the quest drawer. Ignored while the opening plays or a window is open (the room checks too)."""
        if self.locked or (room is not None and room.modal is not None):
            return
        self.tracker.toggle()

    def handle_locked_event(self, event):
        """A key while the opening plays and no dialogue is open (the intro, the run-in): ESC skips ahead."""
        if self.cutscene is not None:
            self.cutscene.handle_event(event)

    # ------------------------------------------------------------ frame
    def _sync_anchor(self):
        q = self.manager.active
        anchored = self.manager.opening_done and q is not None and q.miao_anchor
        self.brain.anchor = tuple(q.miao_anchor) if anchored else None

    def update(self, dt, room):
        m = self.manager
        if self.cutscene is None and self.opening_enabled and not m.opening_done and self._can_start(room):
            self.cutscene = OpeningCutscene(self, room)
        self._sync_anchor()
        self.tracker.update(dt, visible=room.modal is None and not self.locked and not self.hides_hud)
        if room.modal is None:                          # announcements wait for any open window (a popup, the bag ...)
            self.banner.update(dt)
            if not self.locked:
                while m.notifications:
                    self.banner.push(m.notifications.popleft())
        if self.cutscene is not None:
            self.cutscene.update(dt, room)
        self.brain.update(dt, room)
        if self.dialogue is not None:
            self.dialogue.update(dt)
            if self.dialogue.closed:
                self.dialogue = None
        if self.log is not None:
            self.log.update(dt)
            if self.log.closed:
                self.log = None
        self.guide.update(dt, room)
        self._update_ch2_hint(dt, room)

    def _update_ch2_hint(self, dt, room):
        """CHAPTER 02: once all three clues are found, Miao Meow comes to tell the player about Mochi, ONCE, the next
        time they are back in the hub. It waits for anything else on screen (and for a tour of this room); a talk that
        is cut short is told again later, and the flag is only kept when it was told to the end."""
        guide = self.guide
        if not self.manager.miao_ch2_hint_due or guide.playing is not None or guide.leading is not None:
            self._ch2_wait = 0.0
            return
        tour = TOURS.get(room.room_id)
        free = (tour is not None and self.manager.opening_done and self.cutscene is None and self.dialogue is None
                and self.log is None and room.modal is None and not self.banner.busy and not self.manager.notifications
                and room.game.scenes.current is room and not room.game.scenes.transitioning
                and room.arrival_grace <= 0 and room.active_play is None
                and not any(p.activating for p in room.players)
                and not (self.opening_enabled and guide.pending(room.room_id)))
        if not free:
            self._ch2_wait = min(self._ch2_wait, ENTER_DELAY * 0.5)
            return
        self._ch2_wait += dt
        if self._ch2_wait >= ENTER_DELAY:
            self._ch2_wait = 0.0
            guide.start(room, Tour(room.room_id, MIAO_CH2_HINT, forgotten_games.MIAO_HINT_LINES, tour.spot, tour.side))

    def _can_start(self, room):
        scenes = room.game.scenes
        return room.room_id == HOME and scenes.current is room and not scenes.transitioning and room.arrival_grace <= 0

    # ------------------------------------------------------------ conversations
    def open_dialogue(self, room, owner, lines, on_done=None, on_line=None):
        """Open the dialogue box for `owner` (the player's avatar)."""
        context = {"players": list(self.hub.avatars)}
        low = [p.y for p in self.hub.avatars]
        if self.brain.is_in(room.room_id):
            low.append(self.brain.y)
        top = max(low) > D_LOW                                             # the speakers stand where a bottom box would hide them
        self.dialogue = StoryDialogue(lines, context, on_done=on_done, play_sound=self.play, top=top, on_line=on_line)
        room._own_modal(owner)
        room.notice.clear()
        for p in room.players:
            p.held.clear()
        return self.dialogue

    def talk_to_miao(self, room, player=None):
        """The player pressed E on Miao Meow: a short chat with the hint for where the story is. Hints are only ever
        given when asked for (never pushed), and each ask is a little less vague."""
        if self.locked or self.modal is not None:
            return
        if self.guide.press_e_on_miao(room):                  # she is leading the tour: E starts it right here
            return
        player = player or room.player
        m = self.manager
        if (m.opening_done and m.has_secret_item(SECRET_ITEM_RETRO_RACER)
                and not m.state.get("flags", {}).get(MIAO_REVERSE_ROAD)):
            self.brain.notify("talk", player)
            self.open_dialogue(room, player, REVERSE_ROAD_CHAT,
                               on_done=lambda: (m.handle(MIAO_REVERSE_ROAD), self.brain.end_talk()))
            return
        n = self._chats
        self._chats += 1
        text, mood = GREETINGS[n % len(GREETINGS)]
        lines = [Line(MIAO, text, mood)]
        hint = m.take_hint() if m.opening_done else None
        if hint:
            lines.append(Line(MIAO, hint, "normal"))
        else:
            lines.append(Line(MIAO, *NO_QUEST_CHAT[n % len(NO_QUEST_CHAT)]))
        self.brain.notify("talk", player)
        self.open_dialogue(room, player, lines, on_done=self.brain.end_talk)

    def toggle_log(self, room, player=None):
        """Q: open (or close) the Quest Log. Ignored while anything else is open or the opening plays."""
        if self.log is not None:
            self.log.close()
            return
        if self.locked or room.modal is not None or not self.manager.opening_done:
            return
        player = player or room.player
        profile = self.session.player_for_avatar(player).profile
        self.log = QuestLogUI(self.manager, profile)
        room._own_modal(player)
        player.held.clear()

    # ------------------------------------------------------------ drawing
    def draw_world(self, surf, room):
        """Over the lit world but under every HUD element: the opening's dark cover, eyelids and thought bubbles."""
        if self.cutscene is not None:
            self.cutscene.draw_world(surf)

    def draw_hud(self, surf, room):
        self.tracker.draw(surf, room)

    def draw_front(self, surf, room):
        """Topmost: the banner, then the dialogue or the quest log."""
        if room.modal is None:
            self.banner.draw(surf)
        if self.dialogue is not None:
            self.dialogue.draw(surf)
        elif self.log is not None:
            self.log.draw(surf)
