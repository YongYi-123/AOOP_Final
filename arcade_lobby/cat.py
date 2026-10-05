"""Arcade cats: one reusable CatNPC class driven by data.

A cat's differences live in small configuration objects - a CatLook (fur
and markings, cat_sprites.py), a Personality (how it behaves) and a
CatProfile (name, voice pitch, look, personality) - never in subclasses.
Cats get everything about the room (player, collision, the shared follow
slot) through the CatColony that owns them (cat_colony.py)."""
import math
import random
from dataclasses import dataclass
from enum import Enum

import pygame

from animation import Animation, AnimatedSprite
from cat_sprites import FRAME_TIMES, CatLook, cat_sheet, heart_sprite
from cat_voice import CatVoice
from font import get_font
from gfx import soft_shadow
from ui import SpeechBubble


class CatState(Enum):
    IDLE = "idle"
    WALK = "walk"
    SIT = "sit"
    SLEEP = "sleep"
    FOLLOW = "follow"
    PET = "pet"         # short reaction after the player presses E


# state -> animation in the sprite sheet
STATE_ANIM = {CatState.IDLE: "idle", CatState.WALK: "walk", CatState.SIT: "sit",
              CatState.SLEEP: "nap", CatState.FOLLOW: "walk", CatState.PET: "pet"}


@dataclass(frozen=True)
class Personality:
    """Behaviour tuning shared by every cat of a type. `choices` weights what
    an idle cat does next: sit, wander, visit (another of its spots), idle,
    sleep or approach (walk up to a nearby player)."""
    name: str
    prompt: str = "PET"                         # label after [E]
    choices: tuple = (("sit", 4), ("wander", 3), ("visit", 2), ("idle", 1))
    sit_time: tuple = (3.0, 6.0)
    sleep_time: tuple = (7.0, 12.0)
    idle_time: tuple = (1.8, 3.5)
    sleep_after_sit: float = 0.4                # chance a sitting cat dozes off
    speed: float = 28
    approach_range: float = 0                   # FRIENDLY: walks up to the player
    flee_range: float = 0                       # SHY: steps away from a moving player
    flee_chance: float = 0.0
    auto_follow: bool = False                   # CURIOUS: trots after a passing player
    follow_after_pet: float = 0.0               # chance of following after a pet
    chatter: float = 0                          # seconds between unprompted meows (0 = never)
    phrases: tuple = (("meow!", "meow"),)       # (bubble text, sound kind)
    sleepy_phrases: tuple = (("prrr...", "prrr"),)


FRIENDLY = Personality(
    "friendly", choices=(("sit", 3), ("wander", 3), ("visit", 2), ("idle", 1), ("approach", 3)),
    approach_range=90, follow_after_pet=0.6, chatter=11,
    phrases=(("meow!", "meow"), ("mrrp!", "mrrp"), ("nya~", "nya"), ("mew!", "mew")))
SHY = Personality(
    "shy", prompt="SAY HI", choices=(("sit", 4), ("wander", 2), ("visit", 1), ("idle", 2)),
    flee_range=34, flee_chance=0.6, follow_after_pet=0.1,
    phrases=(("mew?", "mew"), ("...mrrp", "mrrp"), ("nya~", "nya")))
LAZY = Personality(
    "lazy", choices=(("sit", 3), ("wander", 1), ("idle", 1), ("sleep", 5)),
    sit_time=(5.0, 9.0), sleep_time=(12.0, 20.0), idle_time=(1.5, 2.5),
    sleep_after_sit=0.8, speed=18,
    phrases=(("prrr...", "prrr"), ("mrrrow...", "meow"), ("meow.", "meow")))
CURIOUS = Personality(
    "curious", choices=(("sit", 2), ("wander", 4), ("visit", 4), ("idle", 2)),
    sit_time=(2.0, 4.0), sleep_after_sit=0.2, speed=34, auto_follow=True,
    follow_after_pet=0.4, chatter=20,
    phrases=(("mrrp?", "mrrp"), ("nya~?", "nya"), ("meow!", "meow"), ("mew?", "mew")))

PERSONALITIES = {p.name: p for p in (FRIENDLY, SHY, LAZY, CURIOUS)}


@dataclass(frozen=True)
class CatProfile:
    """Who a cat is: built from an entry of settings.CATS."""
    id: str
    name: str
    look: CatLook
    personality: Personality
    pitch: float = 1.0

    @classmethod
    def from_data(cls, data):
        return cls(data["id"], data["name"], CatLook(**data["look"]),
                   PERSONALITIES[data["personality"]], data.get("pitch", 1.0))


_ZZZ = None


def _zzz():
    global _ZZZ
    if _ZZZ is None:
        _ZZZ = get_font().render("Z", (190, 176, 255))
    return _ZZZ


class CatNPC(AnimatedSprite):
    FOLLOW_SPEED = 46
    FLEE_SPEED = 52
    FOLLOW_RANGE = 56       # curious cats notice a passing player this close
    FOLLOW_TIME = 2.5       # auto-follow
    PET_FOLLOW_TIME = 4.0   # follow after being petted
    FOLLOW_COOLDOWN = 8.0
    FLEE_COOLDOWN = 5.0
    REACH = 16              # stops this far from the player when walking up
    PET_TIME = 1.1          # length of the petting reaction
    PET_COOLDOWN = 0.4      # after the reaction, before it can be petted again
    WANDER = (40, 26)       # max wander offset from the current spot
    FEET_W, FEET_H = 10, 4

    def __init__(self, profile, spots, rng=None):
        self.profile = profile
        self.name = profile.name
        self.personality = profile.personality
        self.rng = rng or random.Random()
        animations = {f"{name}_{side}": Animation(frames, FRAME_TIMES[name])
                      for (name, side), frames in cat_sheet(profile.look).items()}
        super().__init__(animations, "sit_left")
        self.animation_controller = self.anim
        self.spots = list(spots)
        self.home = self.anchor = self.spots[0]
        self.x, self.y = float(self.home[0]), float(self.home[1])
        self.side = self.rng.choice(("left", "right"))
        self.state = CatState.SIT
        self.timer = self.rng.uniform(1.0, 4.0)
        self.target = None
        self.speed = self.personality.speed
        self.follow_cooldown = self.rng.uniform(3.0, 6.0)
        self.flee_cooldown = 0.0
        self.pet_cooldown = 0.0
        self.chat_timer = self._next_chat()
        self.heart_time = 0.0
        self.time = 0.0
        self.voice = CatVoice(profile.pitch)
        self.bubble = SpeechBubble()
        self.shadow = soft_shadow(14, 4)
        # Desync the cats so their tails don't all swish together.
        self.anim.current.time = self.rng.uniform(0, self.anim.current.frame_duration)
        self.anim.current.current_frame = self.rng.randrange(len(self.anim.current.frames))

    # ------------------------------------------------------------ geometry
    @property
    def position(self):
        return (self.x, self.y)

    @property
    def sort_y(self):
        return self.y

    @property
    def feet(self):
        return self.feet_at(self.x, self.y)

    @classmethod
    def feet_at(cls, x, y):
        return pygame.Rect(int(x) - cls.FEET_W // 2, int(y) - cls.FEET_H, cls.FEET_W, cls.FEET_H)

    def distance_to(self, thing):
        return math.hypot(thing.x - self.x, thing.y - self.y)

    def face(self, thing):
        if abs(thing.x - self.x) > 0.5:
            self.side = "left" if thing.x < self.x else "right"

    # -------------------------------------------------------------- states
    @property
    def following(self):
        return self.state == CatState.FOLLOW

    @property
    def can_pet(self):
        return self.state != CatState.PET and self.pet_cooldown <= 0

    def set_state(self, state, duration=None):
        p = self.personality
        self.state = state
        if duration is None:
            duration = {
                CatState.IDLE: self.rng.uniform(*p.idle_time),
                CatState.SIT: self.rng.uniform(*p.sit_time),
                CatState.SLEEP: self.rng.uniform(*p.sleep_time),
                CatState.WALK: 6.0,         # walk_to() sets a distance-based one
                CatState.FOLLOW: self.FOLLOW_TIME,
                CatState.PET: self.PET_TIME,
            }[state]
        self.timer = duration
        if state not in (CatState.WALK, CatState.FOLLOW):
            self.target = None

    def walk_to(self, point, speed=None):
        self.target = point
        self.speed = speed or self.personality.speed
        dist = math.hypot(point[0] - self.x, point[1] - self.y)
        self.set_state(CatState.WALK, dist / self.speed + 2.0)

    def start_follow(self, duration=None):
        self.set_state(CatState.FOLLOW, duration or self.FOLLOW_TIME)
        self.follow_cooldown = self.FOLLOW_COOLDOWN
        self.heart_time = max(self.heart_time, 0.8)

    def settle(self):
        """Stop whatever it is doing and sit (used when the hub pauses)."""
        if self.state in (CatState.FOLLOW, CatState.PET, CatState.WALK):
            if self.state != CatState.WALK:
                self.anchor = (self.x, self.y)
            self.set_state(CatState.SIT)
        self.heart_time = 0.0
        self.bubble.clear()
        self.voice.stop()

    def _choose_next(self, world):
        p = self.personality
        if self.state == CatState.SLEEP:
            self.set_state(CatState.SIT)
            return
        if not world.is_free(self.position):
            # ended up in front of a machine or in the doorway: go home-ish
            self.anchor = min(self.spots, key=lambda s: math.dist(s, self.position))
            self.walk_to(self.anchor)
            return
        if self.state == CatState.SIT:
            self.set_state(CatState.SLEEP if self.rng.random() < p.sleep_after_sit else CatState.IDLE)
            return
        options = [(name, w) for name, w in p.choices
                   if name != "visit" or len(self.spots) > 1]
        player = world.player
        near_player = player is not None and self.distance_to(player) < p.approach_range
        if not near_player:
            options = [(name, w) for name, w in options if name != "approach"]
        names, weights = zip(*options)
        choice = self.rng.choices(names, weights)[0]
        if choice == "wander":
            point = self._pick_point(world, self.anchor, self.WANDER)
            if point:
                self.walk_to(point)
                return
        elif choice == "visit":
            self.anchor = self.rng.choice([s for s in self.spots if s != self.anchor])
            self.walk_to(self.anchor)
            return
        elif choice == "approach":
            # stop a little short of the player, on this cat's side
            d = max(1.0, self.distance_to(player))
            point = (player.x + (self.x - player.x) / d * self.REACH,
                     player.y + (self.y - player.y) / d * self.REACH * 0.5)
            if world.is_free(point):
                self.walk_to(point)
                return
        elif choice == "sleep":
            self.set_state(CatState.SLEEP)
            return
        elif choice == "idle":
            self.set_state(CatState.IDLE)
            return
        self.set_state(CatState.SIT)

    def _pick_point(self, world, center, spread, tries=5):
        wx, wy = spread
        for _ in range(tries):
            point = (center[0] + self.rng.randint(-wx // 2, wx // 2),
                     center[1] + self.rng.randint(-wy // 2, wy // 2))
            if world.is_free(point):
                return point
        return None

    # ---------------------------------------------------------- interaction
    def pet(self, world):
        """The player pressed E next to this cat. Returns False (and does
        nothing) while it is still reacting to the last pet."""
        if not self.can_pet:
            return False
        sleepy = self.state == CatState.SLEEP
        self.face(world.player)
        self.set_state(CatState.PET)
        self.heart_time = 1.0
        phrases = self.personality.sleepy_phrases if sleepy else self.personality.phrases
        self.say(*self.rng.choice(phrases))
        return True

    def say(self, text, kind, loudness=1.0):
        self.bubble.show(text)
        self.voice.play(kind, self.time, loudness)

    def make_way(self, world, player):
        """Step aside when the player keeps bumping into this cat."""
        if self.state in (CatState.PET, CatState.FOLLOW):
            return False
        horizontal = player.facing in ("left", "right")
        sign = 1 if (self.y >= player.y if horizontal else self.x >= player.x) else -1
        for s in (sign, -sign):
            dx, dy = (0, 18 * s) if horizontal else (18 * s, 0)
            point = (self.x + dx, self.y + dy)
            if world.is_free(point, avoid=False):
                self.anchor = point
                self.walk_to(point, self.FLEE_SPEED)
                return True
        return False

    def _react_to_player(self, world, dist):
        """Personality reactions while sitting or idling. True if one fired."""
        p, player = self.personality, world.player
        if not player.moving:
            return False
        if p.flee_range and dist < p.flee_range and self.flee_cooldown <= 0:
            self.flee_cooldown = self.FLEE_COOLDOWN
            if self.rng.random() < p.flee_chance:
                d = max(1.0, dist)
                away = (self.x + (self.x - player.x) / d * 40, self.y + (self.y - player.y) / d * 30)
                point = away if world.is_free(away) else self._pick_point(world, away, (30, 24))
                if point:
                    self.anchor = point
                    self.walk_to(point, self.FLEE_SPEED)
                    return True
        if (p.auto_follow and dist < self.FOLLOW_RANGE and self.follow_cooldown <= 0
                and world.request_follow(self)):
            self.start_follow()
            return True
        return False

    def _next_chat(self):
        c = self.personality.chatter
        return self.rng.uniform(c * 0.7, c * 1.3) if c else math.inf

    # -------------------------------------------------------------- update
    def update(self, dt, world):
        self.time += dt
        self.timer -= dt
        self.follow_cooldown -= dt
        self.flee_cooldown -= dt
        self.pet_cooldown -= dt
        self.chat_timer -= dt
        self.heart_time = max(0.0, self.heart_time - dt)
        self.bubble.update(dt)
        player = world.player
        dist = self.distance_to(player)

        if self.state == CatState.PET:
            if self.timer <= 0:
                self.pet_cooldown = self.PET_COOLDOWN
                if (self.rng.random() < self.personality.follow_after_pet
                        and world.request_follow(self)):
                    self.start_follow(self.PET_FOLLOW_TIME)
                else:
                    self.anchor = (self.x, self.y)
                    self.set_state(CatState.SIT)
        elif self.state == CatState.FOLLOW:
            self.target = (player.x, player.y)
            self.speed = self.FOLLOW_SPEED
            if dist > self.REACH:
                self._walk(dt, world.cat_solids())
            else:
                self.face(player)
            if self.timer <= 0:
                self.anchor = (self.x, self.y)
                self.set_state(CatState.SIT)
        elif self.state == CatState.WALK:
            arrived = self._walk(dt, world.cat_solids())
            if arrived or self.timer <= 0:
                self._choose_next(world)
        elif self.state == CatState.SLEEP:
            if self.timer <= 0:
                self._choose_next(world)
        elif not self._react_to_player(world, dist) and self.timer <= 0:
            self._choose_next(world)

        if (self.chat_timer <= 0 and self.state in (CatState.SIT, CatState.IDLE, CatState.WALK)
                and dist < 110):
            if world.claim_ambient_meow():
                self.say(*self.rng.choice(self.personality.phrases), loudness=0.5)
            self.chat_timer = self._next_chat()

        anim = STATE_ANIM[self.state]
        same = self.anim.name.startswith(anim + "_")
        self.anim.play(f"{anim}_{self.side}", sync=same)
        self.anim.update(dt)

    def _walk(self, dt, solids):
        """Step toward the target. Returns True when arrived or blocked."""
        tx, ty = self.target
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 2:
            return True
        step = min(dist, self.speed * dt)
        if abs(dx) > 0.5:
            self.side = "left" if dx < 0 else "right"
        before = (self.x, self.y)
        self._move_axis(dx / dist * step, 0, solids)
        self._move_axis(0, dy / dist * step, solids)
        moved = math.hypot(self.x - before[0], self.y - before[1])
        return moved < step * 0.3  # mostly blocked: give up

    def _move_axis(self, dx, dy, solids):
        # Only new overlaps block, so a cat that ends up touching something
        # (e.g. the player stepped onto it) can still walk free.
        old = self.feet
        self.x += dx
        self.y += dy
        new = self.feet
        for rect in solids:
            if new.colliderect(rect) and not old.colliderect(rect):
                self.x -= dx
                self.y -= dy
                return

    # ---------------------------------------------------------------- draw
    def draw_under(self, surf):
        surf.blit(self.shadow, (int(self.x) - 7, int(self.y) - 3))

    def draw(self, surf):
        frame = self.image
        surf.blit(frame, (int(self.x) - frame.get_width() // 2,
                          int(self.y) - frame.get_height() + 1))
        if self.heart_time > 0:
            # beside the head (the speech bubble sits right above it)
            rise = int((1.0 - self.heart_time) * 8)
            hx = 5 if self.side == "left" else -12
            surf.blit(heart_sprite(), (int(self.x) + hx, int(self.y) - 16 - rise))
        if self.state == CatState.SLEEP:
            # a little Z drifting up every couple of seconds
            k = (self.time % 2.4) / 2.4
            if k < 0.85:
                dx = -5 if self.side == "left" else 3
                surf.blit(_zzz(), (int(self.x) + dx + int(k * 4), int(self.y) - 16 - int(k * 8)))

    def draw_bubble(self, surf):
        """Speech bubble, drawn after the room lighting so it stays crisp."""
        self.bubble.draw(surf, (int(self.x), int(self.y) - 17))
