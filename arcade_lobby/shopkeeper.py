"""MOCHI, the cat shopkeeper of the PRIZE COUNTER.

One Shopkeeper object serves both places she appears: sitting on the counter in
PRIZE PLAZA and as the little portrait in the ShopScene (the room is paused while
the shop is open, so whichever scene is on top updates her). She is painted with
the shared cat drawing code (cat_sprites.draw_cat) plus her own overlays: big
expressive eyes, a purple bowtie and ear / paw variants. Frames are painted once and cached.

Behaviour is a small state machine driven by time and by real events:

    notify("open" | "purchase" | "insufficient" | "leave" | "approach", player)

The shop calls these when the thing really happens (a BUY? that went through, a
purchase refused for lack of Tickets, the shop closing, ...); nothing is faked on
a timer. Idle life (blink, ear twitch, tail swish, paw licking, dozing off) uses
timers drawn from a seeded random generator, so it is deterministic in tests.
"""
import math
import random

import pygame

from cat_sprites import CatLook, draw_cat
from font import get_font
from gfx import outlined
from ui import SpeechBubble, wrap_text

NAME = "MOCHI"
LOOK = CatLook(fur=(246, 164, 86), shade=(200, 112, 56), belly=(255, 236, 208), stripes=(205, 118, 56))
BOW, BOW_DARK, BOW_KNOT = (150, 84, 224), (100, 52, 176), (206, 160, 255)
IRIS, PUPIL, SHINE, LID = (255, 214, 90), (34, 24, 50), (255, 255, 255), (60, 36, 40)
TONGUE = (255, 130, 160)

APPROACH_RANGE = 72         # a player this close (feet to Mochi) gets a welcome
LEAVE_RANGE = 92            # ... and must go this far away to be welcomed again
WELCOME_COOLDOWN = 8.0
SLEEPY_AFTER = 16.0         # seconds of nobody around: heavy-lidded
SLEEP_AFTER = 22.0          # ... then she dozes off
REACTION_TIME = {"wake": 0.55, "greet": 0.8, "celebrate": 1.2, "tilt": 1.2, "wave": 1.3, "lick": 1.8}
SAYS = {"approach": "WELCOME!", "open": "HELLO, FRIEND!", "purchase": "PURRFECT CHOICE!",
        "insufficient": "NEED MORE TICKETS?", "leave": "COME BACK SOON!"}
CLUE_EVERY = 6              # every sixth welcome is a mumble about something else entirely...
CLUE_SAY = "5151... AND 06?"
MEOW_GAP = 2.5              # seconds between meows: rare and quiet


# ------------------------------------------------------------------ sprites
_FRAMES = {}


def _px(s, color, x, y, w=1, h=1):
    s.fill(color, (x, y, w, h))


def _eyes(s, hy, mode, gaze):
    """Big 2x3 eyes. mode: open / sleepy / (closed and happy come from draw_cat).
    gaze: (col, down): which pixel column the pupil sits in and whether she looks down."""
    col, down = gaze
    top = hy + 2
    for x in (1, 5):
        if mode == "sleepy":
            _px(s, LID, x, top, 2, 1)                        # a heavy lid over the upper eye
            _px(s, IRIS, x, top + 1, 2, 2)
            _px(s, PUPIL, x + col, top + 1 + down, 1, 1 + (not down))
            continue
        _px(s, IRIS, x, top, 2, 3)
        _px(s, PUPIL, x + col, top + down, 1, 2)
        _px(s, SHINE, x + 1 - col, top + down)             # the glint sits opposite the pupil


def _bowtie(s, pose):
    y = 9 if pose == "sit" else 11
    _px(s, BOW, 1, y, 2, 2)
    _px(s, BOW, 4, y, 2, 2)
    _px(s, BOW_DARK, 1, y + 1, 2, 1)
    _px(s, BOW_DARK, 4, y + 1, 2, 1)
    _px(s, BOW_KNOT, 3, y, 1, 2)


def mochi_frame(pose="sit", eyes="open", gaze=(0, 1), tail=0, ear=0, paw=None, tilt=False):
    """One left-facing, outlined 20x17 frame. pose: sit / nap. eyes: open, sleepy, closed, happy.
    ear: 0 still, 1 right ear flicked, 2 left ear flicked. paw: None, 'lick0/1' or 'wave0/1'."""
    key = (pose, eyes, gaze, tail, ear, paw, tilt)
    frame = _FRAMES.get(key)
    if frame is not None:
        return frame
    base = "happy" if eyes == "happy" else "closed"
    s = draw_cat(LOOK, pose, tail, base)
    hy = 2 if pose == "sit" else 5
    if eyes in ("open", "sleepy") and pose == "sit":
        _eyes(s, hy, eyes, gaze)
    if ear == 1:                                            # flick the right ear outward
        s.fill((0, 0, 0, 0), (7, hy - 1, 1, 1))
        _px(s, LOOK.fur, 8, hy, 1, 1)
    elif ear == 2:
        s.fill((0, 0, 0, 0), (1, hy - 1, 1, 1))
        _px(s, LOOK.fur, 0, hy, 1, 1)
    if ear == 0 and pose == "sit":
        _px(s, (255, 150, 180), 2, hy, 1, 1)                # inner ear
    _bowtie(s, pose)
    if paw and paw.startswith("lick"):                      # a paw up to the mouth
        step = int(paw[-1])
        _px(s, LOOK.belly, 2 + step, 8 - step, 2, 2)
        _px(s, TONGUE, 1, 8, 1, 1)
    elif paw and paw.startswith("wave"):                    # a paw held up, waving
        step = int(paw[-1])
        _px(s, LOOK.fur, 3 + step, 6, 1, 3)
        _px(s, LOOK.belly, 3 + step, 5, 1, 1)
    if tilt:                                                # the head leans: shift it down and across
        head = s.subsurface(pygame.Rect(0, 0, 9, 10)).copy()
        s.fill((0, 0, 0, 0), (0, 0, 9, 10))
        s.blit(head, (1, 1))
    frame = _FRAMES[key] = outlined(s)
    return frame


_FLIPPED = {}


def facing_frame(frame, side):
    """Frames face left; 'right' is the mirror image (cached per frame)."""
    if side == "left":
        return frame
    flipped = _FLIPPED.get(id(frame))
    if flipped is None:
        flipped = _FLIPPED[id(frame)] = pygame.transform.flip(frame, True, False)
    return flipped


_PLATE = []


def nameplate_image():
    """A tiny cat-shaped nameplate: two ears over a plaque that reads MOCHI."""
    if not _PLATE:
        font = get_font()
        label = font.render(NAME, (255, 236, 160))
        w, h = label.get_width() + 8, 14
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in (1, w - 6):                               # ears
            pygame.draw.polygon(s, (255, 190, 70), [(x, 5), (x + 2, 0), (x + 4, 5)])
            pygame.draw.polygon(s, (255, 150, 180), [(x + 1, 4), (x + 2, 2), (x + 3, 4)])
        plate = pygame.Rect(0, 4, w, h - 4)
        s.fill((255, 190, 70), plate)
        s.fill((70, 26, 96), plate.inflate(-2, -2))
        s.blit(label, (4, 6))
        _PLATE.append(outlined(s))
    return _PLATE[0]


class KeeperBubble(SpeechBubble):
    """Mochi's bubble stays up a little longer than a cat's meow."""
    HOLD = 1.7


# ------------------------------------------------------------------ the shopkeeper
class Shopkeeper:
    SIZE = (20, 17)

    def __init__(self, pos=(0, 0), rng=None, sound=None, sort_y=None):
        """pos: (x, y) of the middle of her feet. sound(name) plays a sound effect (may be None).
        sort_y: her depth for drawing (the counter's, so she is painted on top of it)."""
        self.pos = pos
        self._sort_y = sort_y
        self.rng = rng or random.Random(7)
        self.sound = sound
        self.time = 0.0
        self.state = "idle"             # idle / sleep / wake / greet / celebrate / tilt / wave / lick
        self.state_time = 0.0
        self.idle_for = 0.0             # seconds with nobody around and nothing happening
        self.customer = None            # the avatar being served (shop open) - she watches them
        self.watching = None            # whoever she looks at right now (customer or nearest player)
        self.near = {}                  # id(avatar) -> avatar: players inside her range
        self.welcomed = {}              # id(avatar) -> time of the last welcome
        self.bubble = KeeperBubble()
        self.last_meow = -99.0
        self.blink_until = 0.0
        self.next_blink = self.rng.uniform(1.5, 3.0)
        self.next_ear = self.rng.uniform(3.0, 6.0)
        self.ear_until, self.ear_side = 0.0, 1
        self.next_lick = self.rng.uniform(9.0, 14.0)
        self.approaches = 0             # welcomes so far (every CLUE_EVERY-th one is the mumble)
        self.events = []                # (event, time): a log of what reached her (tests, debugging)

    # ------------------------------------------------------------ geometry
    @property
    def sort_y(self):
        return self._sort_y if self._sort_y is not None else self.pos[1] + 0.5

    @property
    def sleeping(self):
        return self.state == "sleep"

    @property
    def sleepy(self):
        return self.state == "idle" and self.idle_for >= SLEEPY_AFTER

    @property
    def side(self):
        """Which way she faces: towards whoever she watches (default: into the room)."""
        who = self.watching
        if who is None:
            return "right"
        return "left" if who.x < self.pos[0] else "right"

    # ------------------------------------------------------------ events
    def say(self, text):
        self.bubble.show(text)

    def _meow(self):
        if self.sound is not None and self.time - self.last_meow >= MEOW_GAP:
            self.last_meow = self.time
            self.sound("meow")

    def _set(self, state):
        self.state, self.state_time = state, 0.0

    def notify(self, event, player=None):
        """Something really happened at the counter. `player`: the avatar it happened to."""
        if event not in SAYS:
            raise ValueError(f"unknown shop event {event!r}")
        self.events.append((event, round(self.time, 3)))
        self.idle_for = 0.0
        if player is not None:
            self.watching = player
            if event != "leave":
                self.customer = player
        if event == "leave":
            self.customer = None
        woke = self.sleeping
        if woke:
            self._set("wake")                                  # she wakes up first, then reacts below
        if event == "approach":
            if not woke:
                self._set("greet")
        elif event == "open":
            self._set("wake" if woke else "greet")
            self._meow()
        elif event == "purchase":
            self._set("celebrate")
            self._meow()
        elif event == "insufficient":
            self._set("tilt")
        elif event == "leave":
            self._set("wave")
        text = SAYS[event]
        if event == "approach":
            self.approaches += 1
            if self.approaches % CLUE_EVERY == 0:
                text = CLUE_SAY
        self.say(text)

    # ------------------------------------------------------------ per frame
    def update(self, dt, players=()):
        """Advance time. `players`: the avatars in the room (for approaching / watching)."""
        self.time += dt
        self.state_time += dt
        self.bubble.update(dt)
        self._notice_players(players)
        if self.state in REACTION_TIME and self.state_time >= REACTION_TIME[self.state]:
            self._set("idle")
        if self.state in ("idle", "lick", "sleep"):
            self.idle_for += dt
        if self.state == "idle":
            if self.idle_for >= SLEEP_AFTER:
                self._set("sleep")
            self._idle_life()

    def _notice_players(self, players):
        nearest, best = None, 1e9
        for p in players:
            d = math.hypot(p.x - self.pos[0], p.y - self.pos[1])
            if d < best:
                nearest, best = p, d
            key = id(p)
            if d <= APPROACH_RANGE and key not in self.near:
                self.near[key] = p
                if self.time - self.welcomed.get(key, -99.0) >= WELCOME_COOLDOWN:
                    self.welcomed[key] = self.time
                    self.notify("approach", p)
            elif d > LEAVE_RANGE:
                self.near.pop(key, None)
        if self.customer is not None:
            self.watching = self.customer
        elif nearest is not None and best <= APPROACH_RANGE * 1.6:
            self.watching = nearest
            self.idle_for = min(self.idle_for, SLEEPY_AFTER - 1) if self.state == "idle" else self.idle_for
        else:
            self.watching = None
        if self.near and self.state == "idle":
            self.idle_for = min(self.idle_for, 2.0)           # company keeps her awake

    def _idle_life(self):
        t = self.time
        if t >= self.next_blink:
            self.blink_until = t + 0.14
            self.next_blink = t + self.rng.uniform(2.6, 4.6)
        if t >= self.next_ear:
            self.ear_until, self.ear_side = t + 0.3, self.rng.choice((1, 2))
            self.next_ear = t + self.rng.uniform(4.5, 8.0)
        if t >= self.next_lick and not self.sleepy:
            self._set("lick")
            self.next_lick = t + self.rng.uniform(12.0, 20.0)

    # ------------------------------------------------------------ drawing
    def _gaze(self):
        who = self.watching
        if who is None:
            return (0, 1)
        dx, dy = who.x - self.pos[0], who.y - self.pos[1]
        return (0 if abs(dx) > 22 else 1, 1 if dy > -4 else 0)

    def _tail(self):
        if self.state in ("celebrate", "greet"):
            return (0, 1, 2, 1)[int(self.time * 10) % 4]
        if self.state == "sleep":
            return 0
        phase = self.time % 3.2                                # a lazy swish once per cycle
        return (0, 1, 2, 1)[int((phase - 2.2) / 0.25) % 4] if phase >= 2.2 else 0

    def frame(self):
        """The current (left-facing) frame for her state."""
        t, state = self.time, self.state
        if state == "sleep":
            return mochi_frame("nap", "closed", tail=0 if int(t / 3) % 2 else 1)
        gaze, tail = self._gaze(), self._tail()
        if state in ("greet", "celebrate"):
            return mochi_frame(eyes="happy", tail=tail, ear=0)
        if state == "tilt":
            return mochi_frame(eyes="open", gaze=gaze, tail=0, tilt=True, ear=1 if int(t * 6) % 2 else 0)
        if state == "wave":
            return mochi_frame(eyes="happy", tail=tail, paw=f"wave{int(t * 5) % 2}")
        if state == "wake":
            return mochi_frame(eyes="open", gaze=gaze, ear=1 if int(t * 8) % 2 else 2)
        if state == "lick":
            return mochi_frame(eyes="closed", tail=tail, paw=f"lick{int(t * 4) % 2}")
        if t < self.blink_until:
            return mochi_frame(eyes="closed", tail=tail)
        eyes = "sleepy" if self.sleepy else "open"
        ear = self.ear_side if t < self.ear_until else 0
        return mochi_frame(eyes=eyes, gaze=gaze, tail=tail, ear=ear)

    def hop(self):
        """Vertical offset in pixels (negative = up) during a happy hop."""
        if self.state == "greet":
            return -int(abs(math.sin(self.state_time * math.pi / 0.4)) * 3)
        if self.state == "celebrate":
            return -int(abs(math.sin(self.state_time * math.pi / 0.4)) * 4)
        return 0

    def image(self):
        return facing_frame(self.frame(), self.side)

    def draw_under(self, surf):
        pass

    def draw(self, surf):
        """In the room: the nameplate beside her and Mochi herself on the counter."""
        plate = nameplate_image()
        surf.blit(plate, (self.pos[0] - 52, self.pos[1] - plate.get_height() + 1))
        image = self.image()
        x, y = int(self.pos[0]), int(self.pos[1]) + self.hop()
        surf.blit(image, (x - image.get_width() // 2, y - image.get_height() + 1))
        if self.sleeping:
            self._draw_zzz(surf, x, y)

    def _draw_zzz(self, surf, x, y):
        k = (self.time % 2.4) / 2.4
        if k < 0.85:
            z = get_font().render("Z", (190, 176, 255))
            surf.blit(z, (x + (-6 if self.side == "left" else 4) + int(k * 4), y - 16 - int(k * 8)))

    def draw_bubble(self, surf):
        self.bubble.draw(surf, (int(self.pos[0]), int(self.pos[1]) - 19))

    def speech_lines(self, width):
        """The bubble text wrapped for a box `width` px wide (None when she is quiet)."""
        if not self.bubble.visible:
            return None
        return wrap_text(self.bubble.text, width)

    def portrait(self):
        """A 2x scaled frame for the ShopScene header."""
        image = self.image()
        hop = self.hop()
        scaled = pygame.transform.scale(image, (image.get_width() * 2, image.get_height() * 2))
        return scaled, hop * 2
