"""Car catalogue: every selectable car is one CarSpec (driving character) plus one CarStyle (pixel-art look).

All physics numbers are MULTIPLIERS on the baselines in settings.py (1.0 = the original car). That keeps the
driving model recognisable, keeps F1 tuning working, and means a new car needs no code changes:

    CAR_CATALOG gets one more CarSpec(...)  +  one CarStyle(...)
"""
from dataclasses import dataclass
import random
from assets import CarStyle, CarLivery, SEDAN, make_palette

# ---- visual definitions (left half of a 30 px wide rear view; see assets.CarStyle) ---------------------
#   B body  D dark body  L highlight  S spoiler  G glass  R tail light  W plate  X exhaust  K black
#   Y accent stripe  T tyre  . transparent
VIPER_GRID = (      # low, wide wedge with a big rear wing and twin tail lights
    "..SSSSSSSSSSSSS",
    "....S..........",
    "..........DBBBB",
    ".........DBGGGG",
    "......DDBBBYYYY",
    "...DBBBBBBYYYYY",
    "..DBBRRBBBBYWWW",
    "TTTTBRRBBBBBWWW",
    "TTTTDBBBBBBBBBB",
    "TTTTDDDDDDDDXXX",
    "TTTTKKKKKKKKKKK",
    "TTTT...........",
)
COMET_GRID = (      # narrow compact hatch with a racing stripe and a small lip spoiler
    ".........DBBBBB",
    "........DBGGGGG",
    "........DBGGGGG",
    ".......SSSSSSSS",
    "......DBBBBBBBB",
    "......DBYYYYYYY",
    "......DBRRRBBWW",
    "....TTTBRRRBBWW",
    "....TTTDBBBBBBB",
    "....TTTDDDDDDXX",
    "....TTTKKKKKKKK",
    "....TTT........",
)
TITAN_GRID = (      # tall boxy off-roader: roof rack, big rear window, spare wheel
    "...KKKKKKKKKKKK",
    "....YYYYYYYYYYY",
    "...DBBBBBBBBBBB",
    "...DBGGGGGGGGGB",
    "...DBGGGGGGGGGB",
    "...DBBBBBBBBBBB",
    "...DBBBBBBBBBBB",
    "...DBBBBBBBXXXX",
    "...DRRBBBBBXKKK",
    "TTTTRRBBBBBXKKK",
    "TTTTDBBBBBBBBBB",
    "TTTTDDDDDDDDDXX",
    "TTTTKKKKKKKKKKK",
    "TTTT...........",
)

FALCON_STYLE = CarStyle("falcon", SEDAN, make_palette((214, 26, 36), (122, 0, 26), (255, 110, 110), (40, 40, 56)))
VIPER_STYLE = CarStyle("viper", VIPER_GRID, make_palette((150, 48, 210), (80, 20, 132), (222, 150, 255), (28, 28, 40),
                                                          accent=(245, 245, 245), lights=(255, 150, 30)))
COMET_STYLE = CarStyle("comet", COMET_GRID, make_palette((255, 132, 24), (172, 72, 0), (255, 212, 120), (255, 214, 40),
                                                          accent=(255, 240, 90)))
TITAN_STYLE = CarStyle("titan", TITAN_GRID, make_palette((116, 128, 144), (62, 70, 84), (176, 188, 204), (40, 44, 54),
                                                          accent=(255, 130, 30)))

# ---- how the UI turns multipliers into 1..10 bars (fixed ranges, so a new car never re-scales the others) ----
BAR_SEGMENTS = 10
STAT_RANGES = {"max_speed": (0.80, 1.20), "acceleration": (0.60, 1.50), "handling": (0.75, 1.30),
               "braking": (0.80, 1.20), "durability": (0.70, 1.50)}


@dataclass(frozen=True)
class CarSpec:
    """One car's driving character. Every number is a multiplier on the matching settings.py baseline."""
    key: str
    name: str
    tagline: str
    style: CarStyle
    max_speed: float = 1.0              # x MAX_SPEED
    acceleration: float = 1.0           # x ACCEL
    braking: float = 1.0                # x BRAKING
    steering: float = 1.0               # x STEER_RATE (how fast the car turns in)
    centrifugal_resistance: float = 1.0  # >1 = pushed less toward the outside of a bend
    offroad_penalty: float = 1.0        # x OFFROAD_DECEL (>1 loses more speed on grass)
    collision_retention: float = 1.0    # x the speed kept after a crash (>1 = more durable)
    collision_push: float = 1.0         # x the sideways shove after a crash (>1 = lighter, knocked further)
    width: float = 1.0                  # x body width, for both the sprite and the hit box
    engine_pitch: float = 0.0           # engine pitch shift, in pre-rendered pitch steps (+ = higher)
    engine_volume: float = 1.0          # x engine loudness

    @property
    def handling(self):
        """Overall handling = geometric mean of turn-in and stability (used for the UI bar)."""
        return (self.steering * self.centrifugal_resistance) ** 0.5

    def stats(self):
        """The five displayed stats as multipliers (before normalising)."""
        return {"max_speed": self.max_speed, "acceleration": self.acceleration, "handling": self.handling,
                "braking": self.braking, "durability": self.collision_retention}

    def bars(self):
        """[(label, blocks 1..10)] in display order."""
        labels = {"max_speed": "TOP SPEED", "acceleration": "ACCELERATION", "handling": "HANDLING",
                  "braking": "BRAKING", "durability": "DURABILITY"}
        out = []
        for stat, value in self.stats().items():
            lo, hi = STAT_RANGES[stat]
            norm = max(0.0, min(1.0, (value - lo) / (hi - lo)))
            out.append((labels[stat], 1 + int(norm * (BAR_SEGMENTS - 1) + 0.5)))
        return out


class CarCatalog:
    """Ordered registry of the selectable cars."""

    def __init__(self, specs):
        self._specs = {spec.key: spec for spec in specs}
        self.order = list(self._specs)

    def __getitem__(self, key):
        return self._specs[key]

    def __iter__(self):
        return (self._specs[k] for k in self.order)

    def __len__(self):
        return len(self.order)

    def at(self, index):
        return self._specs[self.order[index % len(self.order)]]

    def index(self, spec):
        return self.order.index(spec.key)

    @property
    def default(self):
        return self.at(0)


# ---- liveries (paint only) ------------------------------------------------------------------------------
PLAYER_ACCENT = (60, 230, 255)       # cyan stripe on the player's car ...
PLAYER_PLATE = (120, 255, 90)        # ... a lime licence plate, and a small marker above the roof (see car.py)
_player_liveries = {}


def player_livery(spec):
    """The player keeps the car's own colours, plus the player-only cyan accent and lime plate."""
    if spec.key not in _player_liveries:
        pal = spec.style.palette
        _player_liveries[spec.key] = CarLivery(f"player-{spec.key}", pal["B"], pal["D"], pal["L"], PLAYER_ACCENT, PLAYER_PLATE)
    return _player_liveries[spec.key]


LIVERY_POOL = [        # ten clearly different paint jobs for the CPU racers
    CarLivery("sky", (40, 120, 230), (20, 60, 150), (140, 190, 255), (255, 255, 255)),
    CarLivery("lime", (110, 200, 40), (60, 110, 10), (200, 255, 120), (30, 30, 30)),
    CarLivery("orange", (255, 140, 20), (170, 80, 0), (255, 200, 110), (255, 240, 80)),
    CarLivery("magenta", (225, 60, 170), (130, 10, 90), (255, 150, 225), (255, 255, 255)),
    CarLivery("teal", (20, 170, 150), (0, 95, 90), (120, 235, 220), (250, 250, 90)),
    CarLivery("yellow", (245, 215, 30), (170, 130, 0), (255, 250, 150), (30, 30, 30)),
    CarLivery("white", (236, 236, 242), (150, 150, 170), (255, 255, 255), (220, 30, 30)),
    CarLivery("charcoal", (58, 58, 68), (20, 20, 28), (120, 120, 140), (255, 120, 0)),
    CarLivery("violet", (140, 70, 215), (75, 30, 130), (205, 150, 255), (255, 230, 90)),
    CarLivery("crimson", (222, 40, 40), (130, 10, 20), (255, 130, 130), (255, 255, 255)),
]
MIN_COLOR_GAP = 95


def color_distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def pick_liveries(count, avoid, rng=None):
    """`count` CPU liveries whose body colours differ from each other and from `avoid` (the player's)."""
    rng = rng or random.Random()
    pool = LIVERY_POOL[:]
    rng.shuffle(pool)
    chosen = []
    for livery in pool:
        if color_distance(livery.primary, avoid) >= MIN_COLOR_GAP and \
                all(color_distance(livery.primary, c.primary) >= MIN_COLOR_GAP for c in chosen):
            chosen.append(livery)
        if len(chosen) == count:
            return chosen
    return (chosen + [l for l in pool if l not in chosen])[:count]      # pool exhausted: still return enough


CAR_CATALOG = CarCatalog([
    CarSpec("falcon", "FALCON", "BALANCED ALL-ROUNDER", FALCON_STYLE),      # the original car: every multiplier 1.0
    CarSpec("viper", "VIPER", "FASTEST TOP END, TWITCHY", VIPER_STYLE,
            max_speed=1.15, acceleration=0.88, braking=1.00, steering=0.95, centrifugal_resistance=0.95,
            offroad_penalty=1.05, collision_retention=0.95, collision_push=1.10, width=1.06,
            engine_pitch=1.0, engine_volume=1.0),
    CarSpec("comet", "COMET", "QUICK AND AGILE", COMET_STYLE,
            max_speed=0.88, acceleration=1.30, braking=1.10, steering=1.15, centrifugal_resistance=1.20,
            offroad_penalty=1.20, collision_retention=0.85, collision_push=1.25, width=0.92,
            engine_pitch=1.5, engine_volume=0.95),
    CarSpec("titan", "TITAN", "HEAVY AND TOUGH", TITAN_STYLE,
            max_speed=0.96, acceleration=0.80, braking=0.90, steering=0.85, centrifugal_resistance=1.05,
            offroad_penalty=0.70, collision_retention=1.40, collision_push=0.60, width=1.10,
            engine_pitch=-1.0, engine_volume=1.10),
])
