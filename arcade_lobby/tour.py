"""THE ARCADE TOUR: short, one-time conversations the first time the players reach each part of the arcade.

    HOME            Miao Meow shows off the central lounge (right after the opening and its quest banner)
    ARCADE FLOOR    the machines and the Tickets they pay out                          -> event "tour_arcade"  (quest 1)
    PRIZE PLAZA     the Prize Counter, and Miao Meow and Mochi bickering fondly         -> event "met_mochi"    (quest 2)

Nothing here forces anybody to follow anyone: a conversation starts when the players have walked into the room, stood
a moment and nothing else is on screen (a popup, a window, the quest banner, a transition), and it is a plain dialogue
box that ends after a handful of lines. Each one plays ONCE: its flag is saved in the shared story the moment it ends
(quests.TOUR_EVENTS), in the playing profile, so loading a save or re-entering a room
never replays it. A room the player reaches early is toured early: the quests that wait on the flags complete the moment
they become active, so nothing is done twice.

Miao Meow LEADS the way in the Arcade Floor and the Prize Plaza: she runs in through the door the players came
through (or sets off from where she stands), walks to a spot in the room and waits for them there, looking back. The
players stay completely free: the conversation starts when somebody walks up to her (or presses E on her, or after a
generous wait), never by taking the controls away. Nobody has to follow: if they leave the room the tour is simply
unfinished and she goes back to her own life; it starts again on the next visit. HOME has no walk (she is already there).
She is held still for the conversation only; release() gives her back her own life on every way it ends.
Mochi is the real shopkeeper object of the Prize Plaza; she only turns to the players (her own greetings are untouched).
Tours only play in a real game start (the director's `opening_enabled`), like the opening itself.
"""
from dataclasses import dataclass

import math

from miao_meow import ARCADE, DOORS, HOME, PLAZA, SPOTS
from story_dialogue import Line

MIAO, MOCHI, YOU = "MIAO MEOW", "MOCHI", "PLAYER"

# ------------------------------------------------------------------ the conversations
HOME_TOUR = (
    Line(MIAO, "First stop: HOME! This is the central lounge.", "happy"),
    Line(MIAO, "It's my favorite place. Cozy couches, rain on the window, fairy lights... I could nap here all day!",
         "happy"),
    Line(MIAO, "The Arcade Floor is through the left door, and the Prize Plaza is through the right one.", "normal"),
    Line(MIAO, "Oh, and the bed in the corner is MINE. Just so you know.", "gentle"),
)

ARCADE_TOUR = (
    Line(MIAO, "Ta-da! This is the Arcade Floor!", "happy"),
    Line(MIAO, "Every machine here is a different little game. Walk up, press E, and play!", "happy"),
    Line(MIAO, "Finish a round and the machine pays out Tickets. Everybody loves Tickets!", "happy"),
    Line(YOU, "And what do the Tickets do?"),
    Line(MIAO, "Ooh, that's the best part! The Prize Plaza is next. Through HOME, then the right door!", "surprised"),
    Line(MIAO, "But take your time. Poke at things. Nothing here bites. Mostly.", "gentle"),
)

PLAZA_TOUR = (
    Line(MIAO, "And this is the Prize Plaza!", "happy"),
    Line(MIAO, "Where all your hard-earned Tickets become wonderful prizes!", "happy"),
    Line(MOCHI, "And where certain cats keep asking for free snacks.", "gentle"),
    Line(MIAO, "That was ONE time!", "surprised"),
    Line(MOCHI, "It was this morning.", "gentle"),
    Line(MIAO, "...Okay, but I said please!", "gentle"),
    Line(YOU, "Are you two always like this?"),
    Line(MOCHI, "Unfortunately.", "gentle"),
    Line(MIAO, "HEY!", "surprised"),
    Line(MOCHI, "...I'm kidding. She's the best greeter this place has ever had. Don't tell her I said so.", "happy"),
    Line(MOCHI, "Welcome, by the way. I'm Mochi, and I run the Prize Counter.", "normal"),
    Line(MOCHI, "Play the machines on the Arcade Floor to earn Tickets, then bring them here. Prizes, decorations, "
                "collectibles: it's all on the shelves.", "normal"),
    Line(MIAO, "And that's the Lucky Corner! Try your luck there and you can win more Tokens!", "happy"),
    Line(MOCHI, "Tokens are what you play with. The Capsule Corner next door takes Tickets, for surprise prizes.",
         "normal"),
    Line(MOCHI, "Take your time. And Miao? There's a snack under the counter for you.", "happy"),
    Line(MIAO, "SNACK?!", "happy"),
)


@dataclass(frozen=True)
class Tour:
    room_id: str
    event: str                  # the story event fired when it ends (and the flag that stops it replaying)
    lines: tuple
    spot: tuple                 # where Miao Meow appears when she is not already in the room
    side: str                   # which way she faces there
    stage: tuple = None         # where she leads the players to (None: no walk, she talks where she is)
    door: str = None            # the door side she runs in from when she was not in the room


TOURS = {
    HOME: Tour(HOME, "tour_home", HOME_TOUR, SPOTS[HOME]["hub"], "right"),
    ARCADE: Tour(ARCADE, "tour_arcade", ARCADE_TOUR, SPOTS[ARCADE]["right"], "left",
                 stage=SPOTS[ARCADE]["centre"], door="right"),
    PLAZA: Tour(PLAZA, "met_mochi", PLAZA_TOUR, SPOTS[PLAZA]["left"], "right",
                stage=SPOTS[PLAZA]["left"], door="left"),
}
ENTER_DELAY = 0.9               # seconds the players have been in a room before the tour begins
LEAD_SPEED = 62.0               # how fast she runs ahead (the players walk at 72)
LEAD_NEAR = 118                 # a player this close to her (px) starts the conversation
LEAD_WAIT = 12.0                # she waits this long at the stage, then simply starts
LEAD_TIMEOUT = 24.0             # the walk itself may take this long (a blocked path): then she is just there


class TourGuide:
    """Decides when a tour conversation starts and runs it. One per StoryDirector; the director calls update() every
    frame (with the room on screen) and on_room_enter() when the players arrive."""

    def __init__(self, director):
        self.director = director
        self.waited = 0.0               # seconds spent in the current room
        self.room_id = None
        self.playing = None             # the Tour being told right now
        self.leading = None             # the Tour she is leading the players into (walking, or waiting at the stage)
        self.lead_time = 0.0
        self.wait_time = 0.0
        self.played = []                # the events told this session, in order (tests and debugging)

    # ------------------------------------------------------------ questions
    def seen(self, tour):
        return bool(self.director.manager.state.get("flags", {}).get(tour.event))

    def pending(self, room_id):
        tour = TOURS.get(room_id)
        return tour if tour is not None and not self.seen(tour) else None

    def can_start(self, room):
        d = self.director
        scenes = room.game.scenes
        return (d.opening_enabled and d.manager.opening_done and d.cutscene is None
                and d.dialogue is None and d.log is None and room.modal is None
                and not d.banner.busy and not d.manager.notifications
                and scenes.current is room and not scenes.transitioning and room.arrival_grace <= 0
                and room.active_play is None and not any(p.activating for p in room.players))

    # ------------------------------------------------------------ frame
    def on_room_enter(self, room):
        self.room_id, self.waited = room.room_id, 0.0

    def update(self, dt, room):
        d = self.director
        if self.playing is not None:
            if d.dialogue is None:                                      # it ended some other way: never leave her held
                self._end(room, self.playing, complete=False)
            return
        if room.room_id != self.room_id:
            self.on_room_enter(room)
        if self.leading is not None:
            self._lead(dt, room)
            return
        tour = self.pending(room.room_id)
        if tour is None:
            return
        if not self.can_start(room):
            self.waited = min(self.waited, ENTER_DELAY * 0.5)           # (a popup or a banner: the clock restarts gently)
            return
        self.waited += dt
        if self.waited >= ENTER_DELAY:
            if tour.stage is None:
                self.start(room, tour)
            else:
                self.begin_lead(room, tour)

    # ------------------------------------------------------------ leading the way
    def begin_lead(self, room, tour):
        """She sets off for the stage (from the door if she was elsewhere); the players stay free."""
        brain = self.director.brain
        if not brain.is_in(room.room_id):
            door = DOORS[room.room_id][tour.door]
            brain.place(room.room_id, door, "left" if tour.door == "right" else "right")
        brain.scripted = True
        brain.script_speed = LEAD_SPEED
        brain.watching = None
        brain.script_walk(tour.stage)
        self.leading, self.lead_time, self.wait_time = tour, 0.0, 0.0

    def _near(self, room):
        brain = self.director.brain
        return any(math.hypot(p.x - brain.x, p.y - brain.y) <= LEAD_NEAR for p in room.players)

    def _lead(self, dt, room):
        d, brain, tour = self.director, self.director.brain, self.leading
        if room.room_id != tour.room_id:                                # they went elsewhere: the tour waits for next time
            return self.cancel_lead()
        self.lead_time += dt
        arrived = brain.arrived
        if arrived:
            self.wait_time += dt
            brain.watching = min(room.players, key=lambda p: math.hypot(p.x - brain.x, p.y - brain.y))
        ready = (arrived and (self._near(room) or self.wait_time >= LEAD_WAIT)) or self.lead_time >= LEAD_TIMEOUT
        if ready and self.can_start(room):
            if not arrived:                                             # (a blocked walk: she is simply there)
                brain.place(room.room_id, tour.stage, tour.side)
            self.leading = None
            self.start(room, tour)

    def cancel_lead(self):
        self.leading = None
        self.waited = 0.0
        self.director.brain.release()

    def press_e_on_miao(self, room):
        """E on her while she is leading: the tour starts at once. True if it did."""
        if self.leading is None or not self.can_start(room):
            return False
        tour, brain = self.leading, self.director.brain
        if not brain.is_in(room.room_id):
            return False
        self.leading = None
        self.start(room, tour)
        return True

    # ------------------------------------------------------------ the conversation
    def start(self, room, tour):
        d = self.director
        brain = d.brain
        owner = room.players[0]
        if not brain.is_in(room.room_id):                               # she is elsewhere: she is simply here, by the door
            brain.place(room.room_id, tour.spot, tour.side)
        brain.scripted = True                                           # she stays put for the talk only
        brain.script_speed = None
        brain.path, brain.moving, brain.state = [], False, "script"
        brain.watching = owner
        brain.side = "left" if owner.x < brain.x else "right"
        self.playing = tour
        d.open_dialogue(room, owner, tour.lines, on_done=lambda: self._end(room, tour, complete=True),
                        on_line=lambda i, line: self._beat(room, tour, i, line))

    def _beat(self, room, tour, index, line):
        """Little reactions as lines start: Mochi turns to the players when she speaks (it never counts as one of her
        welcomes, so her own greetings are untouched) and Miao Meow hops when she shouts."""
        brain = self.director.brain
        mochi = getattr(room, "mochi", None)
        if line.speaker == MOCHI and mochi is not None:
            mochi.watching = room.players[0]
        elif line.speaker == MIAO and line.mood == "surprised" and brain.is_in(room.room_id):
            brain.notify("greet", room.players[0])
            brain.scripted = True

    def _end(self, room, tour, complete):
        d = self.director
        self.playing = None
        self.waited = 0.0                                               # (a talk that was cut short is told again after the usual wait)
        d.brain.release()
        if complete:
            self.played.append(tour.event)
            d.manager.handle(tour.event)
