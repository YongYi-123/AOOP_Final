"""All sprites, drawn from code and cached: the neon cat, the three robots, fish, golden fish and catnip.
Every sprite is 16x16 (one maze tile) unless noted; the cat and robots are drawn around the tile centre."""

import pygame

CYAN, PINK, GOLD, GREEN, WHITE = (90, 240, 255), (255, 120, 205), (255, 214, 90), (130, 255, 160), (255, 255, 255)
FUR, FUR_SHADE, FUR_LIGHT, EAR_INNER, EYE = (255, 176, 96), (214, 120, 60), (255, 222, 170), (255, 140, 190), (40, 240, 255)
OUTLINE = (30, 14, 50)
ROBOT_COLORS = {"patrol": ((255, 150, 60), (190, 90, 30)), "chase": ((255, 70, 110), (160, 30, 70)),
                "ambush": ((170, 110, 255), (100, 60, 190))}
SCARED, SCARED_SHADE = (70, 110, 255), (40, 60, 170)

_CACHE = {}


def _cached(key, build):
    img = _CACHE.get(key)
    if img is None:
        img = _CACHE[key] = build()
    return img


def _surf(size=16):
    return pygame.Surface((size, size), pygame.SRCALPHA)


def _px(s, points, colour):
    for x, y in points:
        if 0 <= x < s.get_width() and 0 <= y < s.get_height():
            s.set_at((x, y), colour)


def _outline(s):
    """A 1px dark outline round every opaque pixel, so sprites stay readable over any floor colour."""
    mask = pygame.mask.from_surface(s)
    w, h = s.get_size()
    ring = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(w):
        for y in range(h):
            if not mask.get_at((x, y)) and any(0 <= x + dx < w and 0 <= y + dy < h and mask.get_at((x + dx, y + dy))
                                               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                ring.set_at((x, y), (*OUTLINE, 255))
    ring.blit(s, (0, 0))
    return ring


# ------------------------------------------------------------------------------------------------------ the cat
def cat_sprite(facing, frame, power=False, blink=False, dead=0.0):
    """facing: (dx, dy); frame 0..3 is the walk cycle (also swings the tail); dead 0..1 spins the cat away."""
    key = ("cat", facing, frame % 4, power, blink, round(dead, 1))
    return _cached(key, lambda: _build_cat(facing, frame % 4, power, blink, dead))


def _build_cat(facing, frame, power, blink, dead):
    s = _surf()
    fur, shade, light = (FUR, FUR_SHADE, FUR_LIGHT) if not power else ((255, 210, 120), (240, 160, 80), (255, 245, 200))
    step = frame % 2
    sway = (0, 1, 0, -1)[frame]
    if facing in ((1, 0), (-1, 0)):
        pygame.draw.ellipse(s, fur, (3, 7, 9, 6))                                 # body
        s.fill(light, (5, 11, 5, 1))
        pygame.draw.circle(s, fur, (11, 6), 4)                                    # head
        _px(s, [(8, 2), (9, 1), (10, 1), (9, 2), (10, 2)], fur)                   # back ear
        _px(s, [(12, 2), (13, 1), (13, 0), (12, 1), (14, 2), (14, 1)], fur)       # front ear
        _px(s, [(13, 1), (13, 2), (12, 2)], EAR_INNER)
        s.fill(shade, (4, 8, 2, 1))
        for i, x in enumerate((4, 6, 9, 11)):                                     # four paws alternate
            lift = 1 if (i + step) % 2 else 0
            s.fill(shade if i % 2 else fur, (x, 12 - lift, 2, 3 + lift))
        tail = [(3, 9), (2, 8 + sway), (1, 7 + sway), (1, 5 + sway), (2, 4 + sway), (3, 4 + sway)]
        _px(s, tail, fur)
        _px(s, [(2, 4 + sway), (3, 4 + sway)], light)
        _px(s, [(13, 7)] if blink else [(13, 6), (13, 7)], EYE)
        _px(s, [(14, 8)], EAR_INNER)                                              # nose
        s.fill(shade, (10, 4, 1, 1))
        if facing == (-1, 0):
            s = pygame.transform.flip(s, True, False)
    elif facing == (0, 1):                                                        # towards the player
        pygame.draw.ellipse(s, fur, (4, 8, 8, 6))
        s.fill(light, (6, 10, 4, 3))
        pygame.draw.circle(s, fur, (8, 6), 5)
        _px(s, [(3, 3), (4, 1), (5, 0), (4, 2), (5, 2), (5, 3)], fur)
        _px(s, [(12, 3), (11, 1), (10, 0), (11, 2), (10, 2), (10, 3)], fur)
        _px(s, [(4, 2), (5, 2), (5, 1)], EAR_INNER)
        _px(s, [(11, 2), (10, 2), (10, 1)], EAR_INNER)
        if blink:
            s.fill(EYE, (5, 6, 2, 1))
            s.fill(EYE, (9, 6, 2, 1))
        else:
            s.fill(EYE, (5, 5, 2, 2))
            s.fill(EYE, (9, 5, 2, 2))
            s.set_at((5, 5), WHITE)
            s.set_at((9, 5), WHITE)
        s.fill(EAR_INNER, (7, 8, 2, 1))
        for x in (5, 10):
            s.fill(shade if step else fur, (x, 13, 2, 2 - step + 1))
        _px(s, [(12 + sway, 10), (13 + sway, 11), (13 + sway, 12)], fur)          # tail peeking out sideways
    else:                                                                         # away from the player
        pygame.draw.ellipse(s, fur, (4, 7, 8, 7))
        pygame.draw.circle(s, fur, (8, 6), 5)
        _px(s, [(3, 3), (4, 1), (5, 0), (4, 2), (5, 2), (5, 3)], fur)
        _px(s, [(12, 3), (11, 1), (10, 0), (11, 2), (10, 2), (10, 3)], fur)
        _px(s, [(4, 2), (5, 2), (5, 1)], shade)
        _px(s, [(11, 2), (10, 2), (10, 1)], shade)
        s.fill(shade, (6, 7, 4, 1))
        for x in (5, 10):
            s.fill(shade if step else fur, (x, 13, 2, 2 - step + 1))
        _px(s, [(8 + sway, 12), (8 + sway, 13), (9 + sway, 14), (10 + sway, 14)], light)
    s = _outline(s)
    if dead:
        s = pygame.transform.rotate(pygame.transform.scale_by(s, max(0.05, 1 - dead * 0.9)), dead * 540)
        out = _surf()
        out.blit(s, s.get_rect(center=(8, 8)))
        s = out
    return s


def cat_glow(power_phase):
    """The catnip aura: a soft cyan-green halo around the cat that breathes (phase 0..3)."""
    def build():
        s = pygame.Surface((36, 36), pygame.SRCALPHA)
        radius = 14 + (0, 1, 2, 1)[power_phase % 4]
        for r in range(radius, 4, -1):
            pygame.draw.circle(s, (*GREEN, int(60 * (1 - r / radius)) + 6), (18, 18), r)
        pygame.draw.circle(s, (*CYAN, 120), (18, 18), radius - 1, 1)
        return s
    return _cached(("glow", power_phase % 4), build)


# --------------------------------------------------------------------------------------------------- robots
def robot_sprite(kind, frame, facing=(0, 1), mode="active", fright=False, flash=False):
    key = ("robot", kind, frame % 2, facing if mode == "eyes" else None, mode, fright, flash)
    return _cached(key, lambda: _build_robot(kind, frame % 2, facing, mode, fright, flash))


def _build_robot(kind, frame, facing, mode, fright, flash):
    s = _surf()
    if mode == "eyes":                              # disabled: only the eyes hurry home
        dx, dy = facing
        for ex in (4, 9):
            s.fill(WHITE, (ex, 6, 3, 4))
            s.fill((40, 60, 200), (ex + 1 + dx, 7 + dy, 1, 2))
        return s
    body, shade = ROBOT_COLORS[kind]
    eye = (255, 240, 120)
    if fright:
        body, shade, eye = (WHITE, (170, 190, 255), (255, 70, 110)) if flash else (SCARED, SCARED_SHADE, WHITE)
    wob = frame
    if kind == "patrol":                            # a friendly dome with one antenna
        pygame.draw.rect(s, body, (3, 5, 10, 8), border_radius=2)
        pygame.draw.circle(s, body, (8, 6), 5)
        s.fill(shade, (3, 11, 10, 2))
        _px(s, [(8, 0), (8, 1), (8, 2)], shade)
        s.fill(PINK if frame and not fright else (255, 230, 120), (7, 0, 2, 2))
        s.fill((20, 12, 50), (4, 6, 8, 3))
        s.fill(eye, (5 + wob, 7, 2, 1))
        s.fill(eye, (9 - wob, 7, 2, 1) if fright else (8 + wob, 7, 2, 1))
    elif kind == "chase":                           # an angular head with horns and a narrow angry visor
        pygame.draw.rect(s, body, (2, 4, 12, 9), border_radius=1)
        _px(s, [(3, 3), (4, 2), (3, 2), (12, 3), (11, 2), (12, 2), (2, 1), (13, 1)], body)
        s.fill(shade, (2, 11, 12, 2))
        s.fill((20, 12, 50), (3, 6, 10, 3))
        _px(s, [(4, 6), (5, 7), (11, 6), (10, 7)], eye)
        s.fill(eye, (6, 7, 1, 1))
        s.fill(eye, (9, 7, 1, 1))
        s.fill((20, 12, 50), (5, 10, 6, 1))
    else:                                           # ambush: a hooded scanner head with a roving eye
        pygame.draw.polygon(s, body, [(8, 1), (13, 6), (13, 13), (3, 13), (3, 6)])
        s.fill(shade, (3, 11, 10, 2))
        s.fill((20, 12, 50), (5, 6, 6, 4))
        scan = 5 + wob * 4
        s.fill(eye, (scan, 7, 2, 2))
        _px(s, [(8, 0)], PINK)
    for x in (3, 9):                                # little treads
        s.fill((30, 20, 60), (x + wob, 13, 4, 2))
        s.fill(shade, (x + wob, 13, 4, 1))
    return _outline(s)


# ------------------------------------------------------------------------------------------------ treats
def fish_sprite(sparkle=False):
    def build():
        s = _surf()
        body = (255, 140, 200)
        s.fill(body, (5, 6, 5, 3))
        _px(s, [(6, 5), (7, 5), (8, 5), (6, 9), (7, 9), (8, 9), (4, 7), (10, 7)], body)
        _px(s, [(11, 5), (12, 4), (11, 6), (12, 7), (11, 8), (12, 10), (11, 9)], (255, 90, 170))
        s.set_at((5, 7), (60, 20, 80))
        if sparkle:
            _px(s, [(7, 3), (7, 4), (6, 4), (8, 4)], WHITE)
        return s
    return _cached(("fish", sparkle), build)


def golden_sprite(frame):
    def build():
        s = _surf()
        gold, deep = GOLD, (220, 150, 30)
        pygame.draw.ellipse(s, gold, (2, 5, 10, 6))
        s.fill(deep, (4, 9, 6, 1))
        _px(s, [(12, 4), (13, 3), (13, 4), (12, 5), (12, 6), (12, 7), (13, 8), (13, 9), (13, 10), (12, 10), (12, 9), (12, 8)], gold)
        _px(s, [(4, 7), (4, 6)], (60, 30, 10))
        _px(s, [(7, 6), (8, 6)], (255, 245, 190))
        if frame % 2:
            _px(s, [(3, 2), (3, 3), (3, 4), (2, 3), (4, 3), (13, 12), (13, 13), (12, 13), (14, 13)], WHITE)
        else:
            _px(s, [(10, 2), (10, 3), (9, 3), (11, 3), (10, 4), (2, 12), (2, 13), (1, 13), (3, 13)], WHITE)
        return s
    return _cached(("golden", frame % 2), build)


def catnip_sprite(frame):
    def build():
        s = _surf()
        leaf, bright = (60, 220, 130), (170, 255, 190)
        _px(s, [(8, 13), (8, 12), (8, 11), (8, 10), (8, 9)], (40, 160, 100))
        for pts in (((7, 8), (6, 7), (5, 6), (6, 6), (7, 7)), ((9, 8), (10, 7), (11, 6), (10, 6), (9, 7)),
                    ((8, 8), (8, 7), (8, 6), (7, 5), (9, 5), (8, 4), (8, 3))):
            _px(s, pts, leaf)
        _px(s, [(8, 5), (8, 6), (6, 6), (10, 6)], bright)
        _px(s, [(5, 6), (11, 6)] if frame % 2 else [(8, 3), (7, 10), (9, 10)], WHITE)
        return s
    return _cached(("catnip", frame % 2), build)


def catnip_halo(phase):
    def build():
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        radius = 8 + (phase % 3)
        for r in range(radius, 2, -1):
            pygame.draw.circle(s, (*GREEN, int(70 * (1 - r / radius)) + 8), (12, 12), r)
        return s
    return _cached(("halo", phase % 3), build)


def heart_icon(filled=True):
    def build():
        s = pygame.Surface((9, 8), pygame.SRCALPHA)
        c = PINK if filled else (70, 40, 100)
        for pts in (((1, 0), (2, 0), (6, 0), (7, 0)), tuple((x, 1) for x in range(0, 9)), tuple((x, 2) for x in range(0, 9)),
                    tuple((x, 3) for x in range(1, 8)), tuple((x, 4) for x in range(2, 7)), ((3, 5), (4, 5), (5, 5)), ((4, 6),)):
            _px(s, pts, c)
        if filled:
            _px(s, [(2, 1), (1, 2)], WHITE)
        return s
    return _cached(("heart", filled), build)


def cat_head_icon():
    def build():
        s = pygame.Surface((11, 9), pygame.SRCALPHA)
        s.fill(FUR, (1, 2, 9, 6))
        _px(s, [(1, 1), (2, 0), (2, 1), (8, 0), (8, 1), (9, 1)], FUR)
        _px(s, [(2, 1)], EAR_INNER)
        _px(s, [(8, 1)], EAR_INNER)
        _px(s, [(3, 4), (7, 4)], EYE)
        _px(s, [(5, 6)], EAR_INNER)
        return s
    return _cached(("head",), build)
