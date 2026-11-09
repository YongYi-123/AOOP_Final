"""THE FORGOTTEN HIGHWAY: the secret route of Secret Item 01 (the Reverse Gear).

It is built from the racer's own parts: a TrackDefinition (the same spline -> segments pipeline as every circuit),
a Road subclass, a TrackTheme and the shared Backdrop / PlayerCar / EnemyCar / TrafficManager. It is NOT listed in
tracks.TRACKS, so no menu ever offers it; only reverse_road.SecretRun builds it.

Unlike the circuits it is a one-way road: a start line, three checkpoint gates, and a finish garage at the end. The
spline underneath is a closed loop (every route is), but the road is cut off behind the garage so only the part from
the start to the garage is ever drawn or driven.
"""
import dataclasses
import math
import random

import pygame

import assets
import settings as S
from assets import LayerSpec, SunSpec
from car import EnemyCar
from road import Road
from theme import Placement, TrackTheme, W
from tracks import TrackDefinition
from traffic import TrafficManager

KEY = "forgotten_highway"
NAME = "THE FORGOTTEN HIGHWAY"
SEGMENTS = 1500
CHECKPOINT_FRACTIONS = (0.2, 0.42, 0.64)      # where the three gates stand (fraction of the spline)
FINISH_FRACTION = 0.86
GARAGE_DEPTH = 9000                          # world units from the finish line to the garage door
GATE_HALF_WIDTH = 1.15                       # a gate only counts when you cross it on the road (road half-widths)

NEON_CYAN, NEON_PINK, NEON_VIOLET = (90, 240, 255), (255, 110, 210), (170, 120, 255)
DEEP, DEEPER = (34, 16, 66), (24, 10, 48)
GOLD, GOLD_DARK = (255, 214, 64), (176, 116, 24)
VOID = (8, 3, 22)                            # what a collapsed stretch of road shows: nothing

# The collapsing road's tuning (world units; speeds in units / s)
STRAIGHT = (1000, 1260)                      # segments of the long straight before the finish (its bends are ironed out)
STRAIGHT_RAMP = 24                           # ... eased in and out over this many segments
TRIGGER_Z = 240000.0                         # the hidden OUT OF TIME plate (OUT OF TIME, out_of_time.py) lies here ...
TRIGGER_DEPTH = 3200.0                       # ... this deep
PRE_GAP = 30000.0                            # how far behind the car the road is already falling, before the last gate
CHASE_GAP = 26000.0                          # ... and after it, when the collapse starts running after you
CHASE_SPEED = S.MAX_SPEED * 0.40             # a steady pace most drivers beat easily: only stopping lets it catch up
EXIT_Z = 120000.0                            # the past version: the way back to the arcade stands here
EXIT_DEPTH = 8000.0

# What the roadside painters need to know this frame (set by reverse_road.SecretRun; painters only draw).
STATE = {"sev": 0.0, "t": 0.0, "warm": False}


def hash32(n):
    """A small stable integer hash (the same road always breaks in the same places)."""
    n = (int(n) * 2654435761) & 0xFFFFFFFF
    n ^= n >> 15
    return (n * 2246822519) & 0xFFFFFFFF


def palette():
    """(accent A, accent B, accent C): the highway's neon at night, or the warm lights of the past."""
    if STATE["warm"]:
        return (255, 206, 120), (255, 130, 150), (255, 170, 90)
    return NEON_CYAN, NEON_PINK, NEON_VIOLET


def lit(key):
    """Is the neon thing at `key` shining right now? Fully, while the road is whole; stuttering more as it falls apart."""
    sev = STATE["sev"]
    if sev < 0.12:
        return True
    return (hash32(int(STATE["t"] * 7) * 131 + key) & 0xFFFF) / 65535 > sev * 0.75

# A long, forgiving ribbon: wide sweepers, one gentle S, no hairpin. (Plan view, y down, positive turns right.)
CONTROLS = ((0, -320), (240, -320), (420, -300), (520, -210), (500, -90), (400, -10), (300, 60), (290, 160),
            (380, 240), (450, 340), (380, 420), (230, 440), (90, 400), (-30, 330), (-150, 330), (-260, 380),
            (-380, 340), (-450, 230), (-430, 90), (-480, -40), (-420, -180), (-300, -270), (-150, -310))
DEFINITION = TrackDefinition(KEY, NAME, "A ROAD THAT WAS NEVER ON THE MAP", CONTROLS, SEGMENTS)


# ------------------------------------------------------------------ roadside art (registered with the racer's painters)
def _rect(surf, color, x, y, w, h):
    pygame.draw.rect(surf, color, (x, y, max(1, w), max(1, h)))


def neon_pylon(surf, x, y, s):
    """A tall dark pylon topped with two tubes: they stutter and die as the road falls apart."""
    a, b, _ = palette()
    _rect(surf, (52, 36, 96), x - 14 * s, y - 760 * s, 28 * s, 760 * s)
    _rect(surf, (80, 58, 140), x, y - 760 * s, 14 * s, 760 * s)
    key = int(s * 60)
    _rect(surf, a if lit(key) else (46, 40, 70), x - 120 * s, y - 800 * s, 240 * s, 26 * s)
    _rect(surf, b if lit(key + 7) else (60, 36, 70), x - 120 * s, y - 760 * s, 240 * s, 16 * s)
    if STATE["sev"] > 0.4 and not lit(key) and int(STATE["t"] * 9 + key) % 4 == 0:
        _rect(surf, (255, 255, 255), x + 90 * s, y - 770 * s, 36 * s, 36 * s)        # a spark where the tube shorted


def glitch_sign(surf, x, y, s):
    """A broken old arcade sign: a lit panel with a dead row and a stuck pixel block."""
    for side in (-1, 1):
        _rect(surf, (70, 52, 120), x + side * 300 * s - 9 * s, y - 380 * s, 18 * s, 380 * s)
    a, b, c = palette()
    warm = STATE["warm"]
    _rect(surf, (20, 10, 44) if not warm else (70, 34, 52), x - 400 * s, y - 640 * s, 800 * s, 280 * s)
    _rect(surf, b, x - 400 * s, y - 640 * s, 800 * s, 14 * s)
    _rect(surf, a, x - 400 * s, y - 374 * s, 800 * s, 14 * s)
    for i in range(5):
        _rect(surf, a if i % 2 else c, x - 340 * s + i * 140 * s, y - 560 * s, 90 * s, 120 * s)
    if not warm:
        _rect(surf, (20, 10, 44), x + 80 * s, y - 560 * s, 90 * s, 120 * s)               # one dead letter
        _rect(surf, b, x - 340 * s, y - 420 * s, 130 * s, 22 * s)                          # a stuck block of pixels


def ghost_cabinet(surf, x, y, s):
    """An abandoned arcade cabinet standing by the road."""
    _rect(surf, (58, 40, 108), x - 160 * s, y - 520 * s, 320 * s, 520 * s)
    _rect(surf, (36, 22, 76), x + 40 * s, y - 520 * s, 120 * s, 520 * s)
    a, b, _ = palette()
    _rect(surf, (10, 6, 28) if not STATE["warm"] else (60, 30, 40), x - 120 * s, y - 440 * s, 240 * s, 190 * s)
    _rect(surf, a, x - 100 * s, y - 400 * s, 80 * s, 14 * s)
    _rect(surf, b, x - 100 * s, y - 360 * s, 140 * s, 14 * s)
    _rect(surf, b, x - 120 * s, y - 540 * s, 240 * s, 22 * s)
    for k in range(3):
        _rect(surf, (255, 224, 90) if k == 1 else a, x - 90 * s + k * 70 * s, y - 210 * s, 36 * s, 36 * s)


def pixel_tree(surf, x, y, s):
    """A bare, glowing violet tree: a trunk and two stacked pixel blocks."""
    _rect(surf, (60, 38, 96), x - 20 * s, y - 280 * s, 40 * s, 280 * s)
    _rect(surf, (120, 70, 200), x - 150 * s, y - 520 * s, 300 * s, 260 * s)
    _rect(surf, (170, 110, 250), x - 150 * s, y - 520 * s, 150 * s, 130 * s)
    _rect(surf, NEON_PINK, x + 40 * s, y - 440 * s, 40 * s, 40 * s)


def lane_glow(surf, x, y, s):
    """A low neon kerb marker."""
    _rect(surf, (50, 34, 90), x - 26 * s, y - 110 * s, 52 * s, 110 * s)
    _rect(surf, palette()[0] if lit(int(s * 60) + 3) else (50, 44, 72), x - 26 * s, y - 120 * s, 52 * s, 22 * s)


def fair_stall(surf, x, y, s):
    """A little stall with a striped awning (the past is lively)."""
    _rect(surf, (120, 70, 60), x - 190 * s, y - 300 * s, 380 * s, 300 * s)
    for k in range(6):
        _rect(surf, (255, 236, 200) if k % 2 else (255, 110, 120), x - 210 * s + k * 70 * s, y - 380 * s, 70 * s, 90 * s)
    _rect(surf, (255, 210, 120), x - 150 * s, y - 230 * s, 300 * s, 70 * s)
    _rect(surf, (255, 150, 90), x - 110 * s, y - 200 * s, 60 * s, 40 * s)


def balloons(surf, x, y, s):
    """A bunch of balloons on a post."""
    _rect(surf, (210, 190, 170), x - 8 * s, y - 360 * s, 16 * s, 360 * s)
    for k, color in enumerate(((255, 110, 130), (255, 210, 110), (120, 220, 255))):
        cx, cy = x + (k - 1) * 90 * s, y - 470 * s - (k % 2) * 60 * s
        pygame.draw.circle(surf, color, (cx, cy), max(1, int(70 * s)))
        pygame.draw.line(surf, (230, 220, 210), (cx, cy + 70 * s), (x, y - 360 * s), max(1, int(4 * s)))


def warm_lamp(surf, x, y, s):
    """A steady street lamp with a soft amber head."""
    _rect(surf, (90, 62, 80), x - 12 * s, y - 640 * s, 24 * s, 640 * s)
    _rect(surf, (255, 214, 130), x - 90 * s, y - 700 * s, 180 * s, 70 * s)
    _rect(surf, (255, 244, 200), x - 60 * s, y - 690 * s, 120 * s, 28 * s)


assets.SCENERY.update({"neon_pylon": neon_pylon, "glitch_sign": glitch_sign, "ghost_cabinet": ghost_cabinet,
                       "pixel_tree": pixel_tree, "lane_glow": lane_glow, "fair_stall": fair_stall,
                       "balloons": balloons, "warm_lamp": warm_lamp})

THEME = TrackTheme(
    key=KEY, name="FORGOTTEN", tagline="A ROAD THAT WAS NEVER ON THE MAP",
    sky_bands=((10, 4, 36), (20, 8, 56), (34, 12, 78), (54, 16, 100), (84, 20, 120),
               (122, 28, 134), (166, 40, 140), (206, 62, 140), (240, 100, 150)),
    sun=SunSpec(NEON_CYAN, NEON_PINK, striped=True, radius=58, x_frac=0.3, raise_px=8),
    layers=[LayerSpec("mountains", 90, (60, 28, 110), 0.2, params={"freqs": (2, 4, 7), "phase": 1.3}),
            LayerSpec("skyline", 60, (34, 14, 76), 0.5, params={"seed": 12, "lit": 0.22}),
            LayerSpec("skyline", 36, (20, 8, 48), 0.8, params={"seed": 5, "lit": 0.35})],
    ground=(DEEP, DEEPER),
    road=((46, 38, 86), (40, 32, 78)),
    rumble=(NEON_CYAN, NEON_PINK),
    lane=(196, 168, 255),
    placements=[
        Placement(W(("neon_pylon", 1),), every=14, near=1.35, far=1.35, sides=2),
        Placement(W(("lane_glow", 1),), every=4, near=1.22, far=1.22, sides=1),
        Placement(W(("pixel_tree", 4), ("ghost_cabinet", 1)), every=9, phase=3, near=1.8, far=3.6, sides=0, chance=0.8),
        Placement(W(("glitch_sign", 1),), every=110, phase=40, near=1.95, far=1.95),
        Placement(every=45, phase=20, near=1.35, far=1.35, curve_signs=("sign_l", "sign_r", "sign")),
    ])

# The same road, long before it fell: warm sunset, lit signs, busy verges.
PAST_THEME = TrackTheme(
    key=KEY + "_past", name="FORGOTTEN (THEN)", tagline="THE ROAD, WHEN IT WAS NEW",
    sky_bands=((70, 38, 120), (112, 52, 140), (160, 70, 150), (206, 92, 150), (240, 120, 140),
               (255, 150, 120), (255, 184, 110), (255, 214, 130), (255, 236, 170)),
    sun=SunSpec((255, 246, 190), (255, 170, 90), striped=False, radius=70, x_frac=0.55, raise_px=4),
    layers=[LayerSpec("mountains", 90, (150, 78, 140), 0.2, params={"freqs": (2, 4, 7), "phase": 1.3}),
            LayerSpec("skyline", 60, (110, 50, 120), 0.5, params={"seed": 12, "lit": 0.6}),
            LayerSpec("skyline", 36, (80, 34, 96), 0.8, params={"seed": 5, "lit": 0.7})],
    ground=((92, 150, 96), (82, 138, 88)),
    road=((84, 72, 96), (76, 64, 88)),
    rumble=((255, 236, 200), (255, 110, 120)),
    lane=(255, 236, 190),
    placements=[
        Placement(W(("warm_lamp", 1),), every=10, near=1.35, far=1.35, sides=2),
        Placement(W(("lane_glow", 1),), every=4, near=1.22, far=1.22, sides=1),
        Placement(W(("fair_stall", 2), ("balloons", 2), ("ghost_cabinet", 1)), every=7, phase=2, near=1.7, far=3.2, sides=0),
        Placement(W(("tree", 3), ("bush", 2), ("palm", 1)), every=5, phase=1, near=1.9, far=4.0, sides=0, chance=0.9),
        Placement(W(("glitch_sign", 1), ("billboard", 1)), every=70, phase=30, near=2.0, far=2.0),
        Placement(every=45, phase=20, near=1.35, far=1.35, curve_signs=("sign_l", "sign_r", "sign")),
    ])


# ------------------------------------------------------------------ the garage and the gates' companions

class Garage:
    """The secret garage at the end of the road: a wide neon shed with a gold gear above its door. A road object."""
    x = 0.0

    def __init__(self, z):
        self.z = z

    def draw(self, surf, sx, sy, sw):
        w = sw * 1.25                                           # a little wider than the road
        h = sw * 1.15
        if w < 6:
            return
        pygame.draw.rect(surf, (36, 22, 78), (sx - w, sy - h, 2 * w, h))
        pygame.draw.rect(surf, (60, 40, 112), (sx - w, sy - h, 2 * w, h * 0.12))
        pygame.draw.rect(surf, NEON_PINK, (sx - w, sy - h, 2 * w, max(2, h * 0.04)))
        door = pygame.Rect(sx - w * 0.62, sy - h * 0.66, w * 1.24, h * 0.66)
        pygame.draw.rect(surf, (10, 6, 28), door)
        for k in range(1, 6):                                      # roller-door slats, half rolled up
            pygame.draw.line(surf, (44, 30, 92), (door.x, door.y + door.h * k / 6), (door.right, door.y + door.h * k / 6),
                             max(1, int(h * 0.012)))
        pygame.draw.rect(surf, NEON_CYAN, door, max(1, int(h * 0.02)))
        draw_gear(surf, (sx, sy - h * 0.84), h * 0.13, GOLD, GOLD_DARK)


def draw_gear(surf, center, radius, color=GOLD, dark=GOLD_DARK, angle=0.0):
    """A pixel-style gold gear: a toothed disc with a hub hole."""
    cx, cy = center
    teeth = 10
    pts = []
    for i in range(teeth * 4):
        a = angle + i * math.tau / (teeth * 4)
        r = radius * (1.0 if (i // 2) % 2 == 0 else 0.76)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pygame.draw.polygon(surf, dark, [(x + radius * 0.06, y + radius * 0.06) for x, y in pts])
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.circle(surf, dark, (cx, cy), max(1, int(radius * 0.58)))
    pygame.draw.circle(surf, color, (cx, cy), max(1, int(radius * 0.5)))
    pygame.draw.circle(surf, (24, 12, 40), (cx, cy), max(1, int(radius * 0.24)))
    pygame.draw.line(surf, (255, 246, 190), (cx - radius * 0.7, cy - radius * 0.3), (cx - radius * 0.3, cy - radius * 0.7),
                     max(1, int(radius * 0.1)))


# ------------------------------------------------------------------ the road
def _route():
    """The spline's route with its long straight (STRAIGHT) ironed flat, eased in and out: the bends are only the picture,
    nothing else reads them, so the road stays one real Road with one ordinary projection."""
    route = DEFINITION.build(S.SEGMENT_LENGTH)
    curves = list(route.curves)
    a, b = STRAIGHT
    for i in range(a - STRAIGHT_RAMP, b + STRAIGHT_RAMP + 1):
        w = min(1.0, (i - (a - STRAIGHT_RAMP)) / STRAIGHT_RAMP, ((b + STRAIGHT_RAMP) - i) / STRAIGHT_RAMP)
        curves[i] *= 1.0 - w * w * (3 - 2 * w)
    return dataclasses.replace(route, curves=tuple(curves))


class Collapse:
    """The state of the falling road: where the break is (`front`, a track position behind the car), how bad it is at any point
    (`severity`, 0..1, worse towards the finish) and the pieces falling right now. Pure state + particles; the road and the
    run only read it. It follows the car's position every frame, so it is always in step with where the car is, and reset()
    puts it back exactly as it is at a given point of the road (a retry starts from a clean break)."""

    MAX_DEBRIS = 140

    def __init__(self, road):
        self.road = road
        self.rng = random.Random(9)
        self.reset(0.0, False)

    def reset(self, progress=0.0, chase=False):
        self.chase = chase
        self.front = progress - (CHASE_GAP + 4000 if chase else PRE_GAP)
        self.debris = []
        self.clock = 0.0
        self.owed = 0.0                              # fractional debris still to spawn

    def severity(self, z):
        """How broken the road is at track position z: nothing at the start, falling apart by the finish."""
        base = max(0.0, min(1.0, (z - 8000.0) / (self.road.finish_z - 8000.0))) ** 1.15
        after_last_gate = 0.18 if z >= self.road.checkpoint_z[-1] else 0.0
        return min(1.0, base * 0.82 + after_last_gate)

    def gap(self, progress):
        return progress - self.front

    def update(self, dt, progress, chase):
        """Advance by `dt`. Before the last gate the break just trails the car; after it the break runs after you at a steady
        pace (and is closed up fast to CHASE_GAP the moment the last gate is taken)."""
        self.clock += dt
        if chase:
            self.chase = True
            gap = self.gap(progress)
            self.front += CHASE_SPEED * dt
            if gap > CHASE_GAP:
                self.front += min(gap - CHASE_GAP, 14000.0 * dt)
        else:
            self.chase = False
            self.front = progress - PRE_GAP
        sev = self.severity(progress)
        self._spawn(dt, sev)
        for d in self.debris:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            d[3] += 700 * dt
            d[5] -= dt
        self.debris = [d for d in self.debris if d[5] > 0 and d[1] < S.HEIGHT + 20]

    def _spawn(self, dt, sev):
        """Chunks and pixels coming off the road ahead and at its edges: more of them the worse it is."""
        self.owed += dt * (4 + 70 * sev)
        while self.owed >= 1 and len(self.debris) < self.MAX_DEBRIS:
            self.owed -= 1
            r = self.rng
            side = r.choice((-1, 1))
            x = S.WIDTH / 2 + side * r.uniform(60, 330) if r.random() < 0.7 else r.uniform(0, S.WIDTH)
            y = r.uniform(S.HEIGHT / 2 - 10, S.HEIGHT / 2 + 150)
            color = r.choice(((60, 50, 100), (90, 76, 140), NEON_PINK, NEON_CYAN, (40, 30, 70)))
            size = r.choice((3, 4, 5, 6)) if r.random() < 0.8 else r.choice((9, 12, 14))
            self.debris.append([x, y, r.uniform(-60, 60), r.uniform(-80, 40), color, r.uniform(0.7, 1.6), size])

    def draw_debris(self, surf):
        for x, y, _vx, _vy, color, _life, size in self.debris:
            pygame.draw.rect(surf, color, (int(x), int(y), size, size))


class ForgottenRoad(Road):
    """A Road with this route's own markers: three gates, a start line, a finish line and a garage; nothing past it. It can carry
    a Collapse (cracks, holes at the edges, vanishing far road), or be the PAST version: whole, warm, with an exit instead of a
    finish."""

    def __init__(self, theme=None, markers=True, past=False):
        self.past = past
        self.collapse = None
        self.far_void = False
        self.plate = False                  # draw the faint hidden-plate glow (only for those who already have the Reverse Gear)
        super().__init__(theme or (PAST_THEME if past else THEME), markers, _route())
        self.landmarks = (ExitArch(self.exit_z) if past else Garage(self.garage_z),)   # the circuits' stock landmarks do not belong here
        self.districts = ()

    def _find_markers(self):
        n = len(self.segments)
        self._start_segments = (0, 1)
        self._checkpoint_segments = [] if self.past else [int(f * n) for f in CHECKPOINT_FRACTIONS]
        self.checkpoint_z = [i * S.SEGMENT_LENGTH for i in self._checkpoint_segments] if not self.past else \
            [int(f * n) * S.SEGMENT_LENGTH for f in CHECKPOINT_FRACTIONS]
        self.finish_segment = int(FINISH_FRACTION * n)
        self.finish_z = self.finish_segment * S.SEGMENT_LENGTH
        self.garage_z = self.finish_z + GARAGE_DEPTH
        self.exit_z = EXIT_Z
        self.end_index = int((self.exit_z + EXIT_DEPTH) // S.SEGMENT_LENGTH) if self.past else int(self.garage_z // S.SEGMENT_LENGTH)

    def apply(self, theme, markers=True):
        super().apply(theme, markers)
        self.districts = ()
        if markers and not self.past:
            for seg in self.segments[self.finish_segment:self.finish_segment + 2]:
                seg.start_line = True
            self.segments[self.finish_segment].sprites.append(("finish", 0.0))

    def project(self, cam_z, player_x):
        """The normal projection, cut off behind the end of the road (the rest of the loop does not exist); while the road is
        falling apart, bands of the far road are marked as gone."""
        base = int(cam_z // S.SEGMENT_LENGTH)
        visible = super().project(cam_z, player_x)[:max(0, self.end_index - base + 1)]
        sev = self.collapse.severity(cam_z) if self.collapse is not None else 0.0
        for i, seg in enumerate(visible):
            seg.void = bool(sev > 0.2 and i > 70 and (hash32(seg.index // 9) & 0xFF) / 255 < (sev - 0.15) * 0.5)
        return visible

    # ---- rendering the damage
    def _plate(self, surf, seg):
        """The hidden plate: two thin pulsing blue-white lines across the road. Faint on purpose."""
        if not (self.plate and TRIGGER_Z <= seg.z < TRIGGER_Z + TRIGGER_DEPTH):
            return
        if (seg.index % 5) // 4:
            return
        pulse = 0.5 + 0.5 * math.sin(STATE["t"] * 4)
        color = (int(70 + 90 * pulse), int(110 + 100 * pulse), 255)
        pygame.draw.line(surf, color, (seg.sx1 - seg.sw1 * 0.9, seg.sy1), (seg.sx1 + seg.sw1 * 0.9, seg.sy1), max(1, int(seg.sw1 / 160)))

    def _draw_segment(self, surf, seg):
        collapse = self.collapse
        if collapse is None:
            super()._draw_segment(surf, seg)
            return self._plate(surf, seg)
        if getattr(seg, "void", False):                         # a stretch of far road that has simply gone
            top = int(seg.sy2)
            pygame.draw.rect(surf, VOID, (0, top, S.WIDTH, max(1, int(seg.sy1) - top + 1)))
            pygame.draw.line(surf, NEON_PINK, (0, top), (S.WIDTH, top), 1)
            return
        super()._draw_segment(surf, seg)
        sev = collapse.severity(seg.z)
        if sev > 0.08:
            self._damage(surf, seg, sev)
        self._plate(surf, seg)

    def _damage(self, surf, seg, sev):
        """Cracks across the tarmac and bites out of its edges. Only the picture: the middle of the road is never touched, so
        there is always a clear way through."""
        y1, y2 = seg.sy1, seg.sy2
        h = hash32(seg.index)
        group = hash32(seg.index // 5)
        if group % 100 < sev * 60:                             # a bite out of one edge (outer fifth of the road)
            side = -1 if group & 0x100 else 1
            f0, f1 = 0.78 * side, 1.0 * side
            pts = [(seg.sx1 + seg.sw1 * f0, y1), (seg.sx1 + seg.sw1 * f1, y1), (seg.sx2 + seg.sw2 * f1, y2),
                   (seg.sx2 + seg.sw2 * f0, y2)]
            pygame.draw.polygon(surf, VOID, pts)
            pygame.draw.line(surf, NEON_PINK, pts[0], pts[3], max(1, int(seg.sw1 / 140)))
        if (h >> 3) % 100 < sev * 70:                          # a crack, jagged from one segment to the next
            f = ((h >> 8) % 130 - 65) / 100
            jitter = ((h >> 16) % 30 - 15) / 100
            a, b = (seg.sx1 + seg.sw1 * f, y1), (seg.sx2 + seg.sw2 * (f + jitter), y2)
            width = max(1, int(seg.sw1 / 70))
            if sev > 0.45:
                pygame.draw.line(surf, NEON_PINK, (a[0] + width, a[1]), (b[0] + width, b[1]), width)
            pygame.draw.line(surf, (10, 4, 26), a, b, width)


def draw_background_decay(surf, sev, scroll, t):
    """Pieces of the far skyline and mountains blinking out of the picture (blocks of the sky showing through), more as the
    road falls apart. Positions are fixed and slide with the background, so it is a stable, deliberate effect."""
    if sev < 0.12:
        return
    horizon = S.HEIGHT // 2
    count = int(4 + 22 * sev)
    for i in range(count):
        h = hash32(i * 7 + 3)
        x = (h % S.WIDTH + int(scroll * 0.4)) % S.WIDTH
        w = 24 + (h >> 8) % 70
        top = horizon - 8 - (h >> 16) % 70
        flick = (hash32(int(t * 5) + i) & 7) == 0
        sky = surf.get_at((min(S.WIDTH - 1, x), max(0, top - 6)))[:3]
        pygame.draw.rect(surf, sky, (x, top, w, horizon - top - 2))
        edge = NEON_PINK if (h >> 20) & 1 else NEON_CYAN
        if not flick:
            pygame.draw.rect(surf, edge, (x, top, w, 2))
            for k in range(0, w, 8):                           # ragged, pixel-stepped bottom edge
                pygame.draw.rect(surf, edge, (x + k, top + 2 + (hash32(i + k) % 3) * 3, 4, 3))


class ExitArch:
    """The way back in the restored road: a wide arch with a glowing portal and the word EXIT. A road object."""
    x = 0.0
    _word = None

    def __init__(self, z):
        self.z = z

    def draw(self, surf, sx, sy, sw):
        w, h = sw * 1.15, sw * 1.0
        if w < 8:
            return
        pygame.draw.rect(surf, (255, 236, 190), (sx - w * 0.78, sy - h * 0.78, w * 1.56, h * 0.78))
        pygame.draw.rect(surf, (255, 250, 225), (sx - w * 0.5, sy - h * 0.62, w, h * 0.62))
        for side in (-1, 1):
            pygame.draw.rect(surf, (140, 84, 110), (sx + side * w - w * 0.12, sy - h, w * 0.12 + 0, h))
        pygame.draw.rect(surf, (140, 84, 110), (sx - w, sy - h, 2 * w, h * 0.16))
        pygame.draw.rect(surf, (255, 130, 150), (sx - w, sy - h, 2 * w, max(2, h * 0.04)))
        if ExitArch._word is None:
            font = pygame.font.Font(None, 40)
            ExitArch._word = font.render("EXIT", False, (255, 244, 210))
        word = ExitArch._word
        ww = max(8, int(w * 0.9))
        img = pygame.transform.scale(word, (ww, max(4, int(ww * word.get_height() / word.get_width()))))
        surf.blit(img, img.get_rect(center=(sx, sy - h * 0.92)))


def obstacle_cars(road, seed=11):
    """Broken-down cars parked on the road. Sparse, never two abreast, always leaving a clear lane: a gentle road. None on
    the long straight before the finish: that stretch is for flat-out driving."""
    rng = random.Random(seed)
    cars, lane_cycle = [], [0.66, -0.66, 0.0, -0.66, 0.66, 0.0]
    z, i = 26000.0, 0
    clear = (STRAIGHT[0] * S.SEGMENT_LENGTH - 12000, road.finish_z)
    while z < road.finish_z - 12000:
        if all(abs(z - g) > 9000 for g in road.checkpoint_z) and not clear[0] <= z <= clear[1]:
            cars.append(EnemyCar(lane_cycle[i % len(lane_cycle)] + rng.uniform(-0.06, 0.06), z, 0.0, i))
            i += 1
        z += rng.uniform(14000, 22000)
    return cars


def obstacle_traffic(road):
    """A TrafficManager that only holds the parked cars (it is never updated, so they never move or recycle)."""
    traffic = TrafficManager(road, seed=1)
    traffic.cars = obstacle_cars(road)
    return traffic


def past_traffic(road, player, count=7):
    """The restored road is busier: a few ordinary slow cars going the same way (the racer's own traffic model)."""
    traffic = TrafficManager(road, seed=3)
    traffic.reset(player, count)
    for car in traffic.cars:
        car.speed = min(car.speed, S.MAX_SPEED * 0.32)
    return traffic
