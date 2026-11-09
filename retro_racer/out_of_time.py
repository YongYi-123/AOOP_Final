"""OUT OF TIME - 88 MPH: a pure-fun easter egg hidden in THE FORGOTTEN HIGHWAY (a nod to a certain time-travel film, in original
pixel art: no borrowed car model, no film frames).

    The rule      the Reverse Gear is already found (the run STARTED with it), and on the long straight before the finish the
                  car reaches 88 on the TEMPORAL gauge while crossing the hidden plate.
    The scene     blue-white current around the car, two lines of fire on the road, a flash, the car is gone ...
    The past      the same highway, whole and warm and busy, with a clear EXIT back to the arcade (reverse_road.SecretRun).

Units. The racer has no real MPH: its dial is km/h of the BASELINE top speed, and cars differ in top speed. So the egg has its own
gauge, shown only on the straight: TEMPORAL MPH = the car's OWN top speed as a percentage (100 = flat out), and 88 is the
threshold. Every car can reach it (the slowest one only has to be 12 percent short of flat out), and nothing in the driving model
reads or changes it.

Nothing here is a reward and nothing counts towards the main story; the host only learns that the egg was discovered.
"""
import math
import random

import pygame

import forgotten_highway as FH
import settings as S
from car import draw_car_rear

TARGET_MPH = 88.0
MPH_AT_TOP = 100.0
EGG_KEY = "out_of_time"

# the cutscene's timeline (seconds)
T_RECEDE = 1.0          # the car starts to pull away
T_FLASH1 = 2.45         # a flash of pixel blocks ...
T_GONE = 2.6            # ... and the car is no longer there
T_FLASH2 = 3.0          # one soft white flash
T_TITLE = 3.1
T_FADE = 5.0
T_END = 5.8
SKIP_AFTER = 1.5

BLUE, WHITE_BLUE, WHITE = (110, 190, 255), (210, 235, 255), (255, 255, 255)
FLAME = ((255, 244, 140), (255, 170, 50), (240, 80, 30))


def mph(player):
    """The egg's own speed reading: percent of this car's top speed, as 'MPH' (88 is the line)."""
    return max(0.0, player.speed_percent * MPH_AT_TOP)


def on_straight(progress):
    a, b = FH.STRAIGHT
    return a * S.SEGMENT_LENGTH <= progress <= b * S.SEGMENT_LENGTH


def crosses_plate(progress, player):
    """True while the car is over the hidden plate, on the road, at 88 or more."""
    return (FH.TRIGGER_Z <= progress <= FH.TRIGGER_Z + FH.TRIGGER_DEPTH and abs(player.x) <= FH.GATE_HALF_WIDTH
            and mph(player) >= TARGET_MPH)


def ramp(t, a, b):
    return max(0.0, min(1.0, (t - a) / (b - a)))


# ------------------------------------------------------------------ drawing helpers
def arcs(surf, center, size, rng, count=8):
    """Jagged blue-white current crackling out of a point."""
    cx, cy = center
    for k in range(count):
        a = rng.uniform(0, math.tau)
        x, y = cx, cy
        pts = [(x, y)]
        for _ in range(rng.choice((3, 4, 5))):
            a += rng.uniform(-0.9, 0.9)
            step = size * rng.uniform(0.12, 0.3)
            x, y = x + step * math.cos(a), y + step * math.sin(a) * 0.7
            pts.append((x, y))
        color = WHITE if k % 3 == 0 else (WHITE_BLUE if k % 3 == 1 else BLUE)
        pygame.draw.lines(surf, color, False, pts, 2 if k % 2 else 3)


def flame_trails(surf, y_from, y_to, wheel_offset, rng, fade=1.0, horizon=S.HEIGHT // 2):
    """Two lines of fire along the road, from the foot of the screen up to the car: they converge on the vanishing point like
    any lane line, burning in chunky flickering pixel blocks."""
    cx, bottom = S.WIDTH // 2, S.HEIGHT
    top = min(y_from, y_to)
    y = bottom
    while y > top:
        scale = (y - horizon) / (bottom - horizon)
        size = max(2, int(14 * scale * fade) // 2 * 2)
        for side in (-1, 1):
            x = cx + side * wheel_offset * scale
            for k in range(2):
                color = FLAME[rng.randrange(3)]
                pygame.draw.rect(surf, color, (x - size / 2 + rng.randint(-size, size) * 0.4, y - size * (1 + k * 0.6) + rng.randint(-2, 2),
                                               size, size))
        y -= max(3, int(11 * scale))


class TimeTravel:
    """The cutscene. Drawn over the highway the run has just rendered (without the car: this draws the car itself so it can
    pull away). It never touches the run's state; `done` says when to go to the past."""

    def __init__(self, run):
        self.run = run
        player = run.player
        self.t = 0.0
        self.spec = player.spec
        self.livery = player.livery
        self.width = 150 * player.spec.width
        self.bottom = S.HEIGHT - 30
        self.sparks = []
        self.said = set()
        self.skipped = False

    @property
    def done(self):
        return self.t >= T_END

    @property
    def car_visible(self):
        return self.t < T_GONE

    @property
    def skippable(self):
        return self.t >= SKIP_AFTER

    def skip(self):
        self.t = T_END

    def car_pose(self):
        """(centre x, bottom y, width) of the car on screen at this moment: still, then pulling away up the road."""
        u = ramp(self.t, T_RECEDE, T_GONE) ** 1.6
        horizon = S.HEIGHT // 2
        y = self.bottom + (horizon + 14 - self.bottom) * u
        scale = (y - horizon) / (self.bottom - horizon)
        return S.WIDTH // 2, y, max(6.0, self.width * scale)

    def _once(self, key, at, sound):
        if key not in self.said and self.t >= at:
            self.said.add(key)
            self.run.game.audio.play(sound)

    def update(self, dt):
        self.t += dt
        self._once("zap", 0.0, "zap")
        self._once("jump", T_RECEDE + 0.3, "timejump")
        if "burst" not in self.said and self.t >= T_GONE:
            self.said.add("burst")
            cx, cy, _ = self.car_pose()
            rng = random.Random(4)
            self.sparks = [[cx, cy - 8, rng.uniform(-260, 260), rng.uniform(-200, 120), rng.choice((WHITE, BLUE, FLAME[0], FLAME[1])),
                            rng.uniform(0.5, 1.1)] for _ in range(46)]
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += 300 * dt
            s[5] -= dt
        self.sparks = [s for s in self.sparks if s[5] > 0]

    def draw(self, screen, hud):
        t, rng = self.t, random.Random(int(self.t * 22))
        cx, y, w = self.car_pose()
        if t >= T_RECEDE:                                      # the fire the car leaves on the road
            fade = 1.0 - 0.7 * ramp(t, T_GONE + 0.3, T_FADE)
            flame_trails(screen, self.bottom if t < T_GONE else y, S.HEIGHT // 2 + 14, self.width * 0.3, rng, fade)
        if self.car_visible:
            draw_car_rear(screen, cx, y, w, self.spec.style.key, livery=self.livery, marker=False)
            arcs(screen, (cx, y - w * 0.22), w * 1.1, rng, 8 + int(4 * ramp(t, 0, T_RECEDE)))
        for px, py, _vx, _vy, color, life in self.sparks:
            pygame.draw.rect(screen, color, (int(px), int(py), 6, 6) if life > 0.25 else (int(px), int(py), 3, 3))
        self._flashes(screen, t, rng)
        if t >= T_TITLE:
            self._title(screen, hud, t)
        fade = ramp(t, T_FADE, T_END)
        if fade > 0:
            self._wash(screen, (255, 226, 170), int(255 * fade))

    def _flashes(self, screen, t, rng):
        """Two flashes only (never a strobe): the first in coarse pixel blocks, the second a soft white that fades away."""
        if T_FLASH1 <= t < T_FLASH1 + 0.12:
            block = 40
            layer = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
            for bx in range(0, S.WIDTH, block):
                for by in range(0, S.HEIGHT, block):
                    if rng.random() < 0.55:
                        layer.fill((255, 255, 255, 210), (bx, by, block, block))
            screen.blit(layer, (0, 0))
        elif T_FLASH2 <= t < T_FLASH2 + 0.5:
            self._wash(screen, (235, 245, 255), int(200 * (1 - (t - T_FLASH2) / 0.5)))

    @staticmethod
    def _wash(screen, color, alpha):
        layer = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        layer.fill((*color, max(0, min(255, alpha))))
        screen.blit(layer, (0, 0))

    def _title(self, screen, hud, t):
        a = int(255 * min(ramp(t, T_TITLE, T_TITLE + 0.3), 1 - ramp(t, T_FADE - 0.4, T_FADE)))
        plate = pygame.Surface((S.WIDTH, 130), pygame.SRCALPHA)
        plate.fill((10, 8, 40, int(160 * a / 255)))
        screen.blit(plate, (0, 210))
        hud.extruded(screen, "OUT OF TIME", (S.WIDTH // 2, 226), WHITE_BLUE, (40, 70, 150), hud.title, 4)
        hud.text(screen, "88 MPH", (S.WIDTH // 2, 300), (255, 190, 90), hud.big, "center", a)


def draw_arrival(screen, t, car_x, car_y, width, rng):
    """The car arriving in the past: a last crackle of current around it, fire fading on the road, a warm flash clearing."""
    if t < 1.4:
        arcs(screen, (car_x, car_y - width * 0.22), width * 1.0, rng, 6)
        flame_trails(screen, car_y, S.HEIGHT // 2 + 14, width * 0.3 * 0.95, rng, 1.0 - t / 1.4)
    if t < 0.9:
        layer = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        layer.fill((255, 226, 170, int(255 * (1 - t / 0.9))))
        screen.blit(layer, (0, 0))
