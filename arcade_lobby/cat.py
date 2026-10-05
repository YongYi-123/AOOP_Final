"""The arcade cat: a tiny NPC that idles, sits, naps, wanders between a few
cozy spots and sometimes trots after the player for a moment."""
import math
import random
from enum import Enum

import pygame

from animation import Animation, AnimatedSprite
from font import get_font
from gfx import outlined, soft_shadow

CAT = (246, 164, 86)
CAT_DARK = (208, 118, 60)
CREAM = (255, 230, 190)
PINK = (255, 150, 180)
EYE = (34, 24, 50)

# Tail pixel paths (relative to the left-facing sprite), per pose and wag frame
_STAND_TAILS = (
    ((14, 6), (15, 5), (16, 4), (16, 3), (16, 2)),
    ((14, 6), (15, 5), (16, 5), (17, 4), (17, 3)),
    ((14, 6), (15, 5), (15, 4), (15, 3), (14, 2)),
)
_SIT_TAILS = (
    ((11, 13), (12, 13), (13, 13), (14, 12), (15, 11)),
    ((11, 13), (12, 13), (13, 13), (14, 13), (15, 13)),
    ((11, 13), (12, 13), (13, 12), (14, 11), (14, 10)),
)
_NAP_TAILS = (
    ((16, 12), (16, 13), (15, 14), (14, 14), (13, 14), (12, 14), (11, 14), (10, 14)),
    ((16, 12), (16, 13), (15, 14), (14, 14), (13, 14), (12, 14), (11, 13), (10, 12)),  # flick
)
_LEGS = ((5, 7, 11, 13), (4, 7, 10, 13), (6, 8, 11, 12))


def _draw_cat(pose, tail=0, blink=False, legs=0, breathe=0):
    """Paint an 18x15 left-facing cat frame. pose: stand, sit or nap."""
    s = pygame.Surface((18, 15), pygame.SRCALPHA)

    def px(color, x, y, w=1, h=1):
        s.fill(color, (x, y, w, h))

    if pose == "stand":
        path = _STAND_TAILS[tail]
        for x in _LEGS[legs]:
            px(CAT_DARK, x, 10, 1, 3)
            px(CREAM, x, 12)
        pygame.draw.ellipse(s, CAT, (4, 5, 11, 6))
        px(CREAM, 6, 9, 6, 1)
        px(CAT_DARK, 9, 5, 1, 2)
        px(CAT_DARK, 12, 5, 1, 2)
        hy = 1
    elif pose == "nap":
        # curled-up loaf, head tucked low, gently breathing
        path = _NAP_TAILS[tail]
        pygame.draw.ellipse(s, CAT, (3, 7 - breathe, 14, 7 + breathe))
        px(CAT_DARK, 9, 7 - breathe, 1, 2)
        px(CAT_DARK, 12, 7 - breathe, 1, 2)
        px(CREAM, 4, 12, 6, 1)
        hy = 5
        blink = True
    else:
        path = _SIT_TAILS[tail]
        pygame.draw.ellipse(s, CAT, (4, 5, 9, 9))
        px(CAT_DARK, 9, 7, 1, 2)
        px(CAT_DARK, 11, 8, 1, 2)
        px(CREAM, 4, 8, 3, 4)
        px(CAT, 4, 11, 1, 3)
        px(CAT, 6, 11, 1, 3)
        px(CREAM, 4, 13)
        px(CREAM, 6, 13)
        hy = 2
    for x, y in path:
        px(CAT, x, y)
    px(CAT_DARK, *path[-1])

    # head
    pygame.draw.ellipse(s, CAT, (0, hy + 1, 8, 6))
    pygame.draw.polygon(s, CAT, [(1, hy + 2), (1, hy - 1), (4, hy + 1)])
    pygame.draw.polygon(s, CAT, [(4, hy + 1), (7, hy - 1), (7, hy + 2)])
    px(PINK, 2, hy + 1)
    px(PINK, 6, hy + 1)
    px(CAT_DARK, 3, hy + 1, 2, 1)
    px(CREAM, 0, hy + 5, 3, 1)
    px(PINK, 0, hy + 4)
    if blink:
        px(EYE, 1, hy + 3, 2, 1)
        px(EYE, 5, hy + 3, 2, 1)
    else:
        px(EYE, 2, hy + 2, 1, 2)
        px(EYE, 5, hy + 2, 1, 2)
    return s


_SHEET = None


def cat_sheet():
    """{(anim, side): [frames]} built once. side is 'left' or 'right'."""
    global _SHEET
    if _SHEET is None:
        idle_tails = (0, 0, 0, 0, 1, 2, 1, 0, 0, 0, 0, 0)
        sit_tails = (0, 0, 1, 2, 1, 0, 0, 0, 0, 0, 1, 2, 1, 0, 0, 0)
        # slow breaths, with one lazy tail flick per cycle
        nap = ((0, 0), (0, 0), (0, 1), (0, 1), (0, 0), (0, 0), (0, 1), (0, 1),
               (0, 0), (1, 0), (0, 0), (0, 1), (0, 1), (0, 0), (0, 0), (0, 1))
        raw = {
            "idle": [_draw_cat("stand", t, blink=(i == 9)) for i, t in enumerate(idle_tails)],
            "sit": [_draw_cat("sit", t, blink=(i in (7, 8))) for i, t in enumerate(sit_tails)],
            "walk": [_draw_cat("stand", i % 2, legs=l) for i, l in enumerate((1, 0, 2, 0))],
            "nap": [_draw_cat("nap", t, breathe=b) for t, b in nap],
        }
        _SHEET = {}
        for name, frames in raw.items():
            left = [outlined(f) for f in frames]
            _SHEET[(name, "left")] = left
            _SHEET[(name, "right")] = [pygame.transform.flip(f, True, False) for f in left]
    return _SHEET


def _heart():
    s = pygame.Surface((5, 4), pygame.SRCALPHA)
    for y, row in enumerate(("01010", "11111", "01110", "00100")):
        for x, c in enumerate(row):
            if c == "1":
                s.set_at((x, y), (255, 110, 170))
    return outlined(s)


def _zzz():
    return get_font().render("Z", (190, 176, 255))


class CatState(Enum):
    IDLE = "idle"
    WALK = "walk"
    SIT = "sit"
    NAP = "nap"


class CatNPC(AnimatedSprite):
    SPEED = 28
    FOLLOW_SPEED = 46
    FOLLOW_RANGE = 56
    FOLLOW_TIME = 2.5
    FOLLOW_COOLDOWN = 8.0
    WANDER = (40, 26)       # max wander offset from home
    DURATIONS = {"idle": 0.18, "sit": 0.2, "walk": 0.12, "nap": 0.32}

    def __init__(self, home, rng=None, spots=()):
        sheet = cat_sheet()
        animations = {f"{name}_{side}": Animation(frames, self.DURATIONS[name])
                      for (name, side), frames in sheet.items()}
        super().__init__(animations, "sit_left")
        self.rng = rng or random.Random()
        self.home = home
        self.spots = list(spots) or [home]   # cozy places to stroll to and nap at
        self.anchor = home                   # the spot it is hanging around now
        self.x, self.y = float(home[0]), float(home[1])
        self.side = "left"
        self.state = CatState.SIT
        self.timer = self.rng.uniform(2, 4)
        self.target = None
        self.following = False
        self.follow_cooldown = 3.0
        self.heart_time = 0.0
        self.shadow = soft_shadow(14, 4)
        self.heart = _heart()
        self.zzz = _zzz()
        self.time = 0.0

    @property
    def sort_y(self):
        return self.y

    @property
    def feet(self):
        return pygame.Rect(int(self.x) - 4, int(self.y) - 3, 8, 3)

    # ---------------------------------------------------------------- states
    def set_state(self, state, duration=None):
        self.state = state
        self.timer = duration if duration is not None else {
            CatState.IDLE: self.rng.uniform(1.8, 3.5),
            CatState.SIT: self.rng.uniform(3.0, 6.0),
            CatState.NAP: self.rng.uniform(7.0, 12.0),
            CatState.WALK: 6.0,
        }[state]
        self.following = False
        if state != CatState.WALK:
            self.target = None

    def _choose_next(self):
        if self.state == CatState.NAP:
            self.set_state(CatState.SIT)
            return
        if self.state == CatState.SIT:
            self.set_state(CatState.NAP if self.rng.random() < 0.4 else CatState.IDLE)
            return
        roll = self.rng.random()
        if roll < 0.4:
            self.set_state(CatState.SIT)
        elif roll < 0.7:
            wx, wy = self.WANDER
            ax, ay = self.anchor
            self.target = (ax + self.rng.randint(-wx // 2, wx // 2),
                           ay + self.rng.randint(-wy // 2, wy // 2))
            self.set_state(CatState.WALK)
        elif roll < 0.95 and len(self.spots) > 1:
            # stroll over to another cozy spot
            self.anchor = self.rng.choice([p for p in self.spots if p != self.anchor])
            self.target = self.anchor
            self.set_state(CatState.WALK)
        else:
            self.set_state(CatState.IDLE)

    def start_follow(self):
        self.set_state(CatState.WALK, self.FOLLOW_TIME)
        self.following = True
        self.follow_cooldown = self.FOLLOW_COOLDOWN
        self.heart_time = 1.0

    # ---------------------------------------------------------------- update
    def update(self, dt, player, solids):
        self.time += dt
        self.timer -= dt
        self.follow_cooldown -= dt
        self.heart_time = max(0.0, self.heart_time - dt)
        dist = math.hypot(player.x - self.x, player.y - self.y)

        if (self.state not in (CatState.WALK, CatState.NAP) and player.moving and self.follow_cooldown <= 0
                and dist < self.FOLLOW_RANGE):
            self.start_follow()

        if self.state == CatState.WALK:
            if self.following:
                self.target = (player.x, player.y)
            arrived = self._walk(dt, solids)
            if self.following and dist < 18:
                self.anchor = (self.x, self.y)
                self.side = "left" if player.x < self.x else "right"
                self.set_state(CatState.SIT, self.rng.uniform(2.5, 4.0))
            elif arrived or self.timer <= 0:
                self._choose_next()
        elif self.timer <= 0:
            self._choose_next()

        same_state = self.anim.name.startswith(self.state.value)
        self.anim.play(f"{self.state.value}_{self.side}", sync=same_state)
        self.anim.update(dt)

    def _walk(self, dt, solids):
        """Step toward the target. Returns True when arrived or blocked."""
        tx, ty = self.target
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 2:
            return True
        speed = self.FOLLOW_SPEED if self.following else self.SPEED
        step = min(dist, speed * dt)
        if abs(dx) > 0.5:
            self.side = "left" if dx < 0 else "right"
        before = (self.x, self.y)
        self._move_axis(dx / dist * step, 0, solids)
        self._move_axis(0, dy / dist * step, solids)
        moved = math.hypot(self.x - before[0], self.y - before[1])
        return moved < step * 0.3  # mostly blocked: give up

    def _move_axis(self, dx, dy, solids):
        self.x += dx
        self.y += dy
        if self.feet.collidelist(solids) != -1:
            self.x -= dx
            self.y -= dy

    # ---------------------------------------------------------------- draw
    def draw_under(self, surf):
        surf.blit(self.shadow, (int(self.x) - 7, int(self.y) - 3))

    def draw(self, surf):
        frame = self.image
        surf.blit(frame, (int(self.x) - frame.get_width() // 2,
                          int(self.y) - frame.get_height() + 1))
        if self.heart_time > 0:
            rise = int((1.0 - self.heart_time) * 8)
            surf.blit(self.heart, (int(self.x) - 3, int(self.y) - 22 - rise))
        if self.state == CatState.NAP:
            # a little Z drifting up every couple of seconds
            k = (self.time % 2.4) / 2.4
            if k < 0.85:
                dx = -5 if self.side == "left" else 3
                surf.blit(self.zzz, (int(self.x) + dx + int(k * 4), int(self.y) - 16 - int(k * 8)))
