"""Procedural retro art: palette, pixel font, car sprites, roadside painters and backdrop layers.

Nothing here is loaded from disk; every image is drawn from code, so there are no asset files to ship.
"""
import math
import random
from dataclasses import dataclass, field
import pygame
import settings as S

# ---- limited palette (roughly an 80s arcade set) --------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (240, 240, 240)
YELLOW = (255, 224, 32)
ORANGE = (255, 140, 30)
RED = (230, 32, 32)
CYAN = (64, 224, 255)
GREEN = (48, 200, 64)
DGREEN = (16, 110, 48)
BROWN = (140, 84, 36)
DBROWN = (90, 52, 24)
NAVY = (24, 32, 120)
GREY = (150, 150, 160)


# ---- pixel font -----------------------------------------------------------------------------------
class PixelFont:
    """Non-antialiased bitmap-style text, enlarged with nearest-neighbour scaling for chunky pixels."""

    def __init__(self, base_size, scale=1, bold=False):
        self.font = pygame.font.Font(None, base_size)
        self.font.set_bold(bold)
        self.scale = scale
        self._cache = {}

    def render(self, msg, antialias, color):     # same call shape as pygame.font.Font.render
        key = (msg, color)
        img = self._cache.get(key)
        if img is None:
            if len(self._cache) > 300:
                for old in list(self._cache)[:100]:          # evict the oldest, never a wholesale clear (no hitch)
                    del self._cache[old]
            img = self.font.render(msg, False, color)
            if self.scale > 1:
                img = pygame.transform.scale(img, (img.get_width() * self.scale, img.get_height() * self.scale))
            img = img.convert_alpha()
            self._cache[key] = img
        return img


# ---- car sprites ----------------------------------------------------------------------------------
# Each row is the LEFT half of a rear view (mirrored to make 30 px wide).
#   B body  D dark body  L highlight  S spoiler  G glass  R tail light  W plate  X exhaust  K black
#   T tyre (tread alternates each frame so the wheels look like they turn)   . transparent
SEDAN = [
    "........DBBBBBB",
    ".......DBGGGGGG",
    "......DBGGGGGGG",
    ".....DBBLLBBBBB",
    "..SSSSSSSSSSSSS",
    "...DBBBBBBBBBBB",
    "...DBLBBBBBBBBB",
    "...DBBRRRRBBWWW",
    "TTTTBBRRRRBBWWW",
    "TTTTDBBBBBBBBBB",
    "TTTTDDDDDDDDDXX",
    "TTTTKKKKKKKKKKK",
    "TTTT...........",
]
VAN = [
    "...DDDDDDDDDDDD",
    "..DBBBBBBBBBBBB",
    "..DBBBBBBBBBBBB",
    "..DBGGGGGGGGGGB",
    "..DBGGGGGGGGGGB",
    "..DBBBBBBBBBBBB",
    "..DBBBBBBBBBBBB",
    "..DLLLLLLLLLLLL",
    "..DRRBBBBBBBWWW",
    "..DRRBBBBBBBWWW",
    "TTTTBBBBBBBBBBB",
    "TTTTDDDDDDDDDXX",
    "TTTTKKKKKKKKKKK",
    "TTTT...........",
]


def _palette(body, dark, light, spoiler=None, accent=None, lights=None):
    return {"B": body, "D": dark, "L": light, "S": spoiler or dark, "G": (30, 44, 110), "R": lights or (255, 40, 40),
            "W": (240, 240, 240), "X": (70, 70, 84), "K": (16, 16, 24), "Y": accent or light}


make_palette = _palette      # public name for car_specs.py


# variant -> (grid, palette). "player" is the red sedan; 0-3 are the traffic looks.
CAR_VARIANTS = {
    "player": (SEDAN, _palette((214, 26, 36), (122, 0, 26), (255, 110, 110), (40, 40, 56))),
    0: (SEDAN, _palette((40, 84, 224), (20, 40, 140), (120, 168, 255), (240, 240, 240))),
    1: (SEDAN, _palette((250, 210, 24), (176, 120, 0), (255, 250, 150), (40, 40, 56))),
    2: (SEDAN, _palette((36, 184, 88), (10, 100, 50), (150, 255, 170), (250, 210, 24))),
    3: (VAN, _palette((236, 236, 240), (150, 150, 172), (255, 140, 30))),
}
ENEMY_VARIANTS = 4


@dataclass(frozen=True)
class CarStyle:
    """A car's procedural pixel-art look: `grid` rows are the LEFT half of a rear view (15 chars each,
    mirrored to 30 px wide) and `palette` maps the grid letters to colours. Creating one registers it so
    car_sprite(style.key, ...) can draw it; a new car's look is just one more CarStyle."""
    key: str
    grid: tuple
    palette: dict

    def __post_init__(self):
        assert all(len(row) == 15 for row in self.grid), f"{self.key}: every grid row must be 15 chars"
        CAR_VARIANTS[self.key] = (self.grid, self.palette)


_sprite_base = {}
_sprite_scaled = {}


@dataclass(frozen=True)
class CarLivery:
    """Paint job: colours only, never physics. Overrides the palette letters of a CarStyle
    (B body, D dark body, L highlight, Y accent stripe, W licence plate, S spoiler)."""
    key: str
    primary: tuple
    dark: tuple
    light: tuple
    accent: tuple
    plate: tuple = (240, 240, 240)
    spoiler: tuple = None

    def overrides(self):
        colors = {"B": self.primary, "D": self.dark, "L": self.light, "Y": self.accent, "W": self.plate}
        if self.spoiler is not None:
            colors["S"] = self.spoiler
        return colors


def _base_sprite(variant, frame, livery=None):
    key = (variant, frame, livery)
    if key not in _sprite_base:
        grid, pal = CAR_VARIANTS[variant]
        if livery is not None:
            pal = {**pal, **livery.overrides()}
        h = len(grid)
        surf = pygame.Surface((30, h), pygame.SRCALPHA)
        for y, half in enumerate(grid):
            row = half + half[::-1]
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                color = ((16, 16, 24) if (y + frame) % 2 == 0 else (60, 60, 72)) if ch == "T" else pal[ch]
                surf.set_at((x, y), color)
        _sprite_base[key] = surf
    return _sprite_base[key]


def car_sprite(variant, width, frame=0, livery=None):
    """Rear-view car scaled to `width` px (nearest neighbour, cached). `livery` repaints it."""
    key = (variant, width, frame, livery)
    spr = _sprite_scaled.get(key)
    if spr is None:
        if len(_sprite_scaled) > 600:
            for old in list(_sprite_scaled)[:200]:
                del _sprite_scaled[old]
        base = _base_sprite(variant, frame, livery)
        spr = pygame.transform.scale(base, (width, max(1, round(width * base.get_height() / 30))))
        _sprite_scaled[key] = spr
    return spr


# ---- roadside painters: fn(surf, x, y, s) with (x, y) = ground contact point, s = scale ------------
def _rect(surf, color, x, y, w, h):
    pygame.draw.rect(surf, color, (x, y, max(1, w), max(1, h)))


def pine(surf, x, y, s):
    th, tw = 240 * s, 44 * s
    _rect(surf, BROWN, x - tw / 2, y - th, tw, th)
    _rect(surf, DBROWN, x, y - th, tw / 2, th)
    for i in range(3):
        w = (210 - i * 50) * s
        top = y - th - (i + 1) * 115 * s
        bot = top + 175 * s
        pygame.draw.polygon(surf, DGREEN, ((x, top), (x - w, bot), (x + w, bot)))
        pygame.draw.polygon(surf, GREEN, ((x, top), (x - w, bot), (x, bot)))


PALM_LEAVES = [(-290, 70), (-210, -30), (-100, -110), (100, -110), (210, -30), (290, 70)]


def palm(surf, x, y, s):
    tx, ty = x + 50 * s, y - 520 * s
    pygame.draw.polygon(surf, BROWN, ((x - 20 * s, y), (x + 20 * s, y), (tx + 13 * s, ty), (tx - 13 * s, ty)))
    pygame.draw.polygon(surf, DBROWN, ((x, y), (x + 20 * s, y), (tx + 13 * s, ty), (tx, ty)))
    for dx, dy in PALM_LEAVES:
        mx, my = tx + dx * 0.5 * s, ty + dy * 0.5 * s - 50 * s
        tip = (tx + dx * s, ty + dy * s)
        pygame.draw.polygon(surf, DGREEN, ((tx, ty), (mx, my), tip, (mx, my + 60 * s)))
        pygame.draw.polygon(surf, GREEN, ((tx, ty), (mx, my), tip))
    for cx in (-16, 16):
        pygame.draw.circle(surf, DBROWN, (tx + cx * s, ty + 24 * s), max(1, int(18 * s)))


def bush(surf, x, y, s):
    for cx, cy, r, col in ((-75, 70, 85, DGREEN), (75, 70, 85, DGREEN), (0, 115, 95, DGREEN),
                           (-85, 95, 40, GREEN), (10, 150, 40, GREEN)):
        pygame.draw.circle(surf, col, (x + cx * s, y - cy * s), max(1, int(r * s)))


def _chevron(direction, face=YELLOW, border=BLACK, arrow=BLACK):
    def paint(surf, x, y, s):
        m = direction
        _rect(surf, GREY, x - 8 * s, y - 330 * s, 16 * s, 330 * s)
        _rect(surf, border, x - 116 * s, y - 536 * s, 232 * s, 212 * s)
        _rect(surf, face, x - 104 * s, y - 524 * s, 208 * s, 188 * s)
        pts = [(-70, -410), (10, -410), (10, -370), (75, -430), (10, -490), (10, -450), (-70, -450)]
        pygame.draw.polygon(surf, arrow, [(x + m * px * s, y + py * s - 20 * s) for px, py in pts])
    return paint


SURF_BLUE = (20, 90, 200)
sign_r, sign_l = _chevron(1), _chevron(-1)
surf_r, surf_l = _chevron(1, WHITE, SURF_BLUE, SURF_BLUE), _chevron(-1, WHITE, SURF_BLUE, SURF_BLUE)


def post(surf, x, y, s):
    for i, col in enumerate((RED, WHITE, RED)):
        _rect(surf, col, x - 12 * s, y - 50 * s * (i + 1), 24 * s, 50 * s)
    _rect(surf, YELLOW, x - 6 * s, y - 140 * s, 12 * s, 20 * s)


def billboard(surf, x, y, s):
    for side in (-1, 1):
        _rect(surf, GREY, x + side * 330 * s - 10 * s, y - 360 * s, 20 * s, 360 * s)
    _rect(surf, WHITE, x - 430 * s, y - 640 * s, 860 * s, 290 * s)
    _rect(surf, NAVY, x - 410 * s, y - 620 * s, 820 * s, 250 * s)
    for i, col in enumerate((RED, ORANGE, YELLOW)):
        _rect(surf, col, x - 410 * s, y - 590 * s + i * 40 * s, 820 * s, 26 * s)
    _rect(surf, CYAN, x - 410 * s, y - 470 * s, 820 * s, 30 * s)


# ---- SUBURBS --------------------------------------------------------------------------------------
def _house(wall, shade, roof, roof_shade):
    def paint(surf, x, y, s):
        w, h = 300 * s, 210 * s
        _rect(surf, wall, x - w, y - h, 2 * w, h)
        _rect(surf, shade, x + w * 0.35, y - h, w * 0.65, h)                                   # shaded side
        top = y - h - 175 * s
        pygame.draw.polygon(surf, roof, ((x - w - 30 * s, y - h), (x + w + 30 * s, y - h), (x + w * 0.5, top), (x - w * 0.5, top)))
        pygame.draw.polygon(surf, roof_shade, ((x + w * 0.1, y - h), (x + w + 30 * s, y - h), (x + w * 0.5, top), (x + w * 0.1, top)))
        _rect(surf, (150, 70, 50), x + w * 0.42, top - 40 * s, 60 * s, 80 * s)                # chimney
        _rect(surf, (110, 70, 40), x - 38 * s, y - 130 * s, 76 * s, 130 * s)                   # door
        for wx in (-0.72, 0.5):
            _rect(surf, WHITE, x + wx * w - 4 * s, y - 166 * s, 88 * s, 78 * s)
            _rect(surf, (140, 200, 240), x + wx * w, y - 162 * s, 80 * s, 70 * s)
    return paint


house_a = _house((240, 220, 170), (206, 184, 132), (176, 62, 52), (130, 40, 38))
house_b = _house((160, 188, 214), (120, 148, 176), (92, 104, 116), (66, 76, 88))


def fence(surf, x, y, s):
    for ry in (90, 42):
        _rect(surf, WHITE, x - 150 * s, y - ry * s, 300 * s, 14 * s)
    for k in range(-3, 4):
        px = x + k * 44 * s
        _rect(surf, WHITE, px - 10 * s, y - 108 * s, 20 * s, 108 * s)
        pygame.draw.polygon(surf, WHITE, ((px - 10 * s, y - 108 * s), (px + 10 * s, y - 108 * s), (px, y - 132 * s)))
        _rect(surf, (200, 200, 205), px + 3 * s, y - 108 * s, 7 * s, 108 * s)


# ---- CITY -----------------------------------------------------------------------------------------
def _building(half, height, body, shade, variant):
    def paint(surf, x, y, s):
        w, h = half * s, height * s
        _rect(surf, body, x - w, y - h, 2 * w, h)
        _rect(surf, shade, x + w * 0.45, y - h, w * 0.55, h)                  # shaded side
        _rect(surf, (30, 30, 40), x - w - 12 * s, y - h - 34 * s, 2 * w + 24 * s, 34 * s)   # roof lip
        if variant == 2:
            _rect(surf, GREY, x - 6 * s, y - h - 200 * s, 12 * s, 170 * s)     # antenna
        if s < 0.05:
            return
        rows, cols = int(height / 150), int(half * 2 / 130)
        for r in range(rows):
            for c in range(cols):
                lit = (r * 31 + c * 17 + variant * 5) % 5 < 2
                _rect(surf, (255, 214, 96) if lit else (26, 34, 70),
                      x - w + (30 + c * 130) * s, y - h + (50 + r * 150) * s, 66 * s, 78 * s)
    return paint


building_a = _building(300, 1500, (92, 100, 132), (66, 72, 104), 0)
building_b = _building(360, 1100, (150, 96, 96), (112, 68, 74), 1)
building_c = _building(250, 2000, (70, 120, 130), (48, 88, 100), 2)


def _streetlight(direction):
    def paint(surf, x, y, s):
        top = y - 820 * s
        _rect(surf, GREY, x - 10 * s, top, 20 * s, 820 * s)
        end = x + direction * 300 * s
        _rect(surf, GREY, min(x, end), top - 8 * s, abs(end - x), 16 * s)
        pygame.draw.circle(surf, (255, 246, 170), (end, top + 26 * s), max(1, int(58 * s)))
        _rect(surf, (255, 255, 230), end - 34 * s, top + 4 * s, 68 * s, 22 * s)
    return paint


streetlight_r, streetlight_l = _streetlight(1), _streetlight(-1)


def barrier(surf, x, y, s):
    _rect(surf, (200, 200, 208), x - 150 * s, y - 90 * s, 300 * s, 90 * s)
    _rect(surf, RED, x - 150 * s, y - 90 * s, 300 * s, 28 * s)
    _rect(surf, (140, 140, 150), x - 150 * s, y - 14 * s, 300 * s, 14 * s)


# ---- BEACH ----------------------------------------------------------------------------------------
def umbrella(surf, x, y, s):
    _rect(surf, WHITE, x - 6 * s, y - 320 * s, 12 * s, 320 * s)
    cx, cy, r = x, y - 320 * s, 210 * s
    for k in range(6):
        a0, a1 = math.pi + k * math.pi / 6, math.pi + (k + 1) * math.pi / 6
        pts = [(cx, cy), (cx + r * math.cos(a0), cy + r * 0.55 * math.sin(a0)),
               (cx + r * math.cos(a1), cy + r * 0.55 * math.sin(a1))]
        pygame.draw.polygon(surf, RED if k % 2 else WHITE, pts)


def lifeguard(surf, x, y, s):
    for dx in (-90, 70):
        _rect(surf, BROWN, x + dx * s, y - 170 * s, 20 * s, 170 * s)
    _rect(surf, WHITE, x - 140 * s, y - 380 * s, 280 * s, 210 * s)
    _rect(surf, SURF_BLUE, x - 140 * s, y - 300 * s, 280 * s, 40 * s)
    pygame.draw.polygon(surf, RED, ((x - 175 * s, y - 380 * s), (x + 175 * s, y - 380 * s), (x, y - 470 * s)))
    _rect(surf, GREY, x + 150 * s, y - 520 * s, 8 * s, 150 * s)
    _rect(surf, RED, x + 158 * s, y - 520 * s, 70 * s, 44 * s)


def tuft(surf, x, y, s):
    for dx, h, col in ((-40, 110, GREEN), (-15, 150, (200, 200, 60)), (12, 130, GREEN), (38, 100, (200, 200, 60))):
        pygame.draw.polygon(surf, col, ((x + (dx - 12) * s, y), (x + (dx + 12) * s, y), (x + dx * 1.4 * s, y - h * s)))


def post_blue(surf, x, y, s):
    for i, col in enumerate((SURF_BLUE, WHITE, SURF_BLUE)):
        _rect(surf, col, x - 12 * s, y - 50 * s * (i + 1), 24 * s, 50 * s)


# ---- DESERT ---------------------------------------------------------------------------------------
CACTUS = (40, 130, 60)
CACTUS_DARK = (24, 92, 44)


def cactus(surf, x, y, s):
    _rect(surf, CACTUS, x - 30 * s, y - 380 * s, 60 * s, 380 * s)
    _rect(surf, CACTUS_DARK, x, y - 380 * s, 30 * s, 380 * s)
    pygame.draw.circle(surf, CACTUS, (x, y - 380 * s), max(1, int(30 * s)))
    _rect(surf, CACTUS, x - 120 * s, y - 240 * s, 100 * s, 38 * s)                # left arm
    _rect(surf, CACTUS, x - 120 * s, y - 340 * s, 38 * s, 138 * s)
    _rect(surf, CACTUS, x + 20 * s, y - 190 * s, 100 * s, 38 * s)                 # right arm
    _rect(surf, CACTUS_DARK, x + 82 * s, y - 290 * s, 38 * s, 138 * s)


def rock(surf, x, y, s):
    pts = [(-170, 0), (-130, -100), (-40, -150), (60, -130), (150, -70), (175, 0)]
    pygame.draw.polygon(surf, (120, 84, 62), [(x + px * s, y + py * s) for px, py in pts])
    pygame.draw.polygon(surf, (168, 122, 90), [(x + px * s, y + py * s) for px, py in ((-170, 0), (-130, -100), (-40, -150), (-20, 0))])


def tumble(surf, x, y, s):
    r = max(2, int(70 * s))
    cx, cy = x, y - 70 * s
    w = max(1, int(6 * s))
    pygame.draw.circle(surf, (170, 118, 60), (cx, cy), r, w)
    pygame.draw.line(surf, (170, 118, 60), (cx - r, cy - r * 0.3), (cx + r, cy + r * 0.4), w)
    pygame.draw.line(surf, (170, 118, 60), (cx - r * 0.4, cy - r), (cx + r * 0.5, cy + r), w)


def post_wood(surf, x, y, s):
    _rect(surf, (120, 82, 50), x - 14 * s, y - 170 * s, 28 * s, 170 * s)
    _rect(surf, (80, 54, 34), x, y - 170 * s, 14 * s, 170 * s)
    _rect(surf, (230, 230, 200), x - 8 * s, y - 150 * s, 16 * s, 22 * s)         # reflector


SCENERY = {"tree": pine, "palm": palm, "bush": bush, "sign_l": sign_l, "sign_r": sign_r,
           "sign": sign_r, "post": post, "billboard": billboard,
           "building_a": building_a, "building_b": building_b, "building_c": building_c,
           "streetlight_l": streetlight_l, "streetlight_r": streetlight_r, "barrier": barrier,
           "umbrella": umbrella, "lifeguard": lifeguard, "tuft": tuft, "post_blue": post_blue,
           "surf_l": surf_l, "surf_r": surf_r, "surf": surf_r,
           "cactus": cactus, "rock": rock, "tumble": tumble, "post_wood": post_wood,
           "house_a": house_a, "house_b": house_b, "fence": fence}


# ---- backdrop (built once per theme, blitted with parallax each frame) ---------------------------
from dataclasses import dataclass, field


@dataclass
class SunSpec:
    top: tuple = YELLOW
    bottom: tuple = ORANGE
    striped: bool = True
    radius: int = 64
    x_frac: float = 0.62
    raise_px: int = 0           # lift above the horizon


@dataclass
class LayerSpec:
    kind: str                   # key into LAYER_BUILDERS
    height: int
    color: tuple
    scroll: float               # parallax factor
    lift: int = 0               # distance above the horizon (clouds float in the sky)
    params: dict = field(default_factory=dict)


def make_sky(width, height, bands):
    """Flat colour bands (no smooth gradient) like a 16-colour sunset."""
    surf = pygame.Surface((width, height))
    band_h = math.ceil(height / len(bands))
    for i, col in enumerate(bands):
        surf.fill(col, (0, i * band_h, width, band_h))
    return surf


def make_sun(spec):
    r = spec.radius
    d = r * 2
    surf = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(surf, spec.bottom, (r, r), r)
    surf.fill(spec.top, (0, 0, d, r))                          # top half / bottom half colours
    if spec.striped:
        for i, thick in enumerate((3, 4, 6, 8)):               # gaps cut into the lower half
            surf.fill((0, 0, 0, 0), (0, r + 10 + i * 13, d, thick))
    mask = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return surf


def make_mountains(width, height, color, freqs, phase, step=4):
    """Periodic jagged ridge line; `freqs` are integers so the tile wraps seamlessly."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    weights = (0.5, 0.3, 0.2)
    for x in range(0, width, step):
        t = 2 * math.pi * x / width
        v = sum(w * (1 - abs(math.sin(k * t / 2 + phase * (i + 1)))) for i, (w, k) in enumerate(zip(weights, freqs)))
        hc = max(step, int(v * height) // step * step)
        pygame.draw.rect(surf, color, (x, height - hc, step, hc))
    return surf


def make_skyline(width, height, color, seed=3, lit=0.28):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    x = 0
    while x < width:
        w = rng.randrange(16, 44, 4)
        if width - (x + w) < 16:
            w = width - x          # last building fills the gap so the tile wraps
        h = rng.randrange(16, height + 1, 4)
        pygame.draw.rect(surf, color, (x, height - h, w, h))
        for wy in range(height - h + 6, height - 4, 8):
            for wx in range(x + 4, x + w - 4, 8):
                if rng.random() < lit:
                    surf.fill((255, 210, 80), (wx, wy, 3, 3))
        x += w
    return surf


def make_mesas(width, height, color, seed=5, count=5):
    """Flat-topped desert mesas with a darker strata band; drawn 3x so the tile wraps."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    dark = tuple(int(c * 0.72) for c in color)
    for i in range(count):
        cx = (i + rng.uniform(0.2, 0.8)) * width / count
        w, h = rng.randrange(110, 210), rng.randrange(height // 2, height)
        for off in (-width, 0, width):
            x0 = cx + off
            body = [(x0 - w / 2, height), (x0 - w * 0.36, height - h), (x0 + w * 0.36, height - h), (x0 + w / 2, height)]
            pygame.draw.polygon(surf, color, body)
            pygame.draw.polygon(surf, dark, [(x0 - w / 2, height), (x0 - w * 0.47, height - h * 0.35),
                                             (x0 + w * 0.47, height - h * 0.35), (x0 + w / 2, height)])
    return surf


def make_dunes(width, height, color, freqs=(3, 5), phase=0.6):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    light = tuple(min(255, int(c * 1.08)) for c in color)
    for x in range(0, width, 2):
        t = 2 * math.pi * x / width
        v = 0.55 + 0.25 * math.sin(freqs[0] * t + phase) + 0.2 * math.sin(freqs[1] * t + 2 * phase)
        hc = max(2, int(v * height))
        pygame.draw.rect(surf, color, (x, height - hc, 2, hc))
        surf.fill(light, (x, height - hc, 2, 2))
    return surf


def make_ocean(width, height, base, seed=9):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill(base)
    light = tuple(min(255, c + 40) for c in base)
    for y in range(4, height, 6):
        surf.fill(light, (0, y, width, 2))
    surf.fill((190, 232, 255), (0, 0, width, 2))                # bright horizon line
    rng = random.Random(seed)
    for _ in range(width // 22):                                # sparkles
        x, y, w = rng.randrange(width), rng.randrange(4, height - 2), rng.randrange(6, 14)
        for off in (-width, 0):
            surf.fill((235, 248, 255), (x + off, y, w, 2))
    return surf


def make_clouds(width, height, color, seed=11):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(seed)
    shade = tuple(max(0, c - 34) for c in color)
    for _ in range(5):
        cx, cy, w = rng.uniform(0, width), rng.uniform(height * 0.3, height * 0.7), rng.randrange(70, 150)
        for off in (-width, 0, width):
            for k in range(4):
                bx = cx + off + (k - 1.5) * w * 0.27
                r = int(w * (0.22 + 0.06 * (k % 2)))
                pygame.draw.circle(surf, color, (bx, cy - (k % 2) * 6), r)
            pygame.draw.rect(surf, shade, (cx + off - w * 0.5, cy + w * 0.16, w, 5))
    return surf


LAYER_BUILDERS = {
    "mountains": lambda w, sp: make_mountains(w, sp.height, sp.color, sp.params.get("freqs", (3, 5, 7)), sp.params.get("phase", 0.7)),
    "skyline": lambda w, sp: make_skyline(w, sp.height, sp.color, sp.params.get("seed", 3), sp.params.get("lit", 0.28)),
    "mesas": lambda w, sp: make_mesas(w, sp.height, sp.color, sp.params.get("seed", 5)),
    "dunes": lambda w, sp: make_dunes(w, sp.height, sp.color, sp.params.get("freqs", (3, 5)), sp.params.get("phase", 0.6)),
    "ocean": lambda w, sp: make_ocean(w, sp.height, sp.color),
    "clouds": lambda w, sp: make_clouds(w, sp.height, sp.color),
}


class Backdrop:
    """Sky bands, sun and parallax layers for one TrackTheme."""

    def __init__(self, width, horizon, theme):
        self.width, self.horizon = width, horizon
        self.sky = make_sky(width, horizon + 1, theme.sky_bands)
        self.sun_spec = theme.sun
        self.sun = make_sun(theme.sun) if theme.sun else None
        self.layers = [(LAYER_BUILDERS[sp.kind](width, sp), sp) for sp in theme.layers]

    def draw(self, scr, scroll):
        h = self.horizon
        scr.blit(self.sky, (0, 0))
        if self.sun:
            sp = self.sun_spec
            sun_x = int(self.width * sp.x_frac + scroll * 0.15) % (self.width + 200) - 100
            scr.blit(self.sun, (sun_x - sp.radius, h - 2 * sp.radius - 2 - sp.raise_px))
        for tile, sp in self.layers:
            off = int(scroll * sp.scroll) % self.width
            y = h - sp.height - sp.lift
            scr.blit(tile, (off - self.width, y))
            scr.blit(tile, (off, y))
