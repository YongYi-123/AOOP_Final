"""Track themes: pure data describing how one road looks, plus a manager that caches the art.

Road geometry and projection never change; a theme only supplies colours, sky/backdrop layers and the
rules for placing roadside objects. Adding a theme means adding one TrackTheme entry to THEMES.
"""
from dataclasses import dataclass, field
import pygame
import assets
from assets import LayerSpec, SunSpec, YELLOW, ORANGE


@dataclass
class Placement:
    """A rule for scattering roadside objects along the track."""
    kinds: tuple = ()               # ((scenery kind, weight), ...) picked at random
    every: int = 6                  # segment interval
    phase: int = 0
    near: float = 1.4               # lateral distance from the road centre, in road half-widths
    far: float = 3.0
    sides: int = 0                  # 0 random side, 1 both sides, 2 alternate sides
    chance: float = 1.0
    by_side: tuple = None           # (kind if left of road, kind if right of road)
    curve_signs: tuple = None       # (left, right, straight) kinds, chosen by the upcoming bend


@dataclass
class TrackTheme:
    key: str
    name: str
    tagline: str
    sky_bands: tuple
    sun: SunSpec
    layers: list
    ground: tuple                   # (light, dark) grass / sand / pavement stripes
    road: tuple                     # (light, dark)
    rumble: tuple                   # (light, dark) kerb colours
    lane: tuple = (240, 240, 240)
    water: tuple = None             # (light, dark, edge offset): sea on the left beyond the sand
    placements: list = field(default_factory=list)
    preview: tuple = ()             # optional ((kind, x, y, scale), ...) for the track-select picture

    @property
    def colors(self):
        """(light band, dark band) colour dicts in the shape Road._draw_segment expects."""
        light = {"road": self.road[0], "grass": self.ground[0], "rumble": self.rumble[0], "lane": self.lane}
        dark = {"road": self.road[1], "grass": self.ground[1], "rumble": self.rumble[1], "lane": None}
        return light, dark


def W(*pairs):
    return tuple(pairs)


# ---- SUBURBS: the original look of the game (sunset sky, striped sun, purple mountains, pines, chevron signs,
#      red-and-white kerbs), now with houses and picket fences -----------------------------------------
SUBURBS = TrackTheme(
    key="suburbs", name="SUBURBS", tagline="SUNSET DRIVE THROUGH TOWN",
    sky_bands=((16, 8, 64), (36, 10, 88), (70, 14, 108), (118, 20, 120), (176, 32, 116),
               (232, 64, 104), (255, 112, 92), (255, 164, 80), (255, 210, 100)),
    sun=SunSpec(YELLOW, ORANGE, striped=True, radius=64, x_frac=0.62),
    layers=[LayerSpec("mountains", 100, (96, 28, 128), 0.25, params={"freqs": (3, 5, 7), "phase": 0.7}),
            LayerSpec("mountains", 56, (58, 20, 100), 0.5, params={"freqs": (2, 6, 9), "phase": 1.9}),
            LayerSpec("skyline", 44, (26, 12, 66), 0.8, params={"seed": 3, "lit": 0.28})],
    ground=((16, 170, 16), (0, 154, 0)),
    road=((107, 107, 107), (99, 99, 99)),
    rumble=((255, 255, 255), (200, 0, 0)),
    lane=(240, 240, 240),
    placements=[
        Placement(W(("tree", 6), ("palm", 1), ("bush", 3)), every=6, near=1.4, far=3.2, sides=0),
        Placement(W(("tree", 1), ("bush", 1), ("palm", 1)), every=6, phase=3, near=1.6, far=3.5, sides=0, chance=0.5),
        Placement(every=45, phase=20, near=1.35, far=1.35, curve_signs=("sign_l", "sign_r", "sign")),
        Placement(W(("post", 1),), every=12, near=1.25, far=1.25, sides=2),
        Placement(W(("billboard", 1),), every=150, phase=60, near=2.1, far=2.1),
        Placement(W(("house_a", 1), ("house_b", 1)), every=16, phase=8, near=2.3, far=3.4, sides=0, chance=0.8),
        Placement(W(("fence", 1),), every=3, near=1.55, far=1.55, sides=1),
    ],
    preview=(("house_a", 640, 350, 0.30), ("tree", 110, 430, 0.5), ("tree", 250, 350, 0.22)))

# ---- CITY: neon dusk, concrete, tall buildings, streetlights and barriers ----------------------------
CITY = TrackTheme(
    key="city", name="CITY", tagline="NEON DUSK DOWNTOWN",
    sky_bands=((8, 6, 40), (20, 8, 64), (44, 10, 90), (80, 14, 110), (130, 20, 120),
               (190, 40, 120), (240, 80, 110), (255, 130, 100), (255, 180, 110)),
    sun=SunSpec((255, 120, 170), (255, 70, 120), striped=True, radius=60, x_frac=0.7),
    layers=[LayerSpec("mountains", 70, (70, 30, 110), 0.2, params={"freqs": (2, 4, 6), "phase": 0.4}),
            LayerSpec("skyline", 84, (48, 24, 96), 0.45, params={"seed": 4, "lit": 0.3}),
            LayerSpec("skyline", 50, (22, 10, 56), 0.8, params={"seed": 8, "lit": 0.4})],
    ground=((112, 114, 128), (102, 104, 118)),
    road=((58, 58, 68), (50, 50, 60)),
    rumble=((240, 200, 40), (36, 36, 46)),
    placements=[
        Placement(W(("building_a", 3), ("building_b", 3), ("building_c", 2)), every=5, near=2.4, far=4.0, sides=1),
        Placement(every=10, near=1.32, far=1.32, sides=1, by_side=("streetlight_l", "streetlight_r")),
        Placement(W(("barrier", 1),), every=2, near=1.22, far=1.22, sides=1),
        Placement(every=45, phase=20, near=1.55, far=1.55, curve_signs=("sign_l", "sign_r", "sign")),
        Placement(W(("billboard", 1),), every=150, phase=60, near=1.95, far=1.95),
    ])

# ---- BEACH: bright day, sand, sea on the left and at the horizon, palms and umbrellas ----------------
BEACH = TrackTheme(
    key="beach", name="BEACH", tagline="SUNNY COASTAL DRIVE",
    sky_bands=((70, 150, 235), (90, 168, 242), (112, 184, 248), (138, 202, 252), (166, 216, 254),
               (194, 230, 255), (222, 242, 255), (246, 251, 255), (255, 255, 240)),
    sun=SunSpec((255, 244, 140), (255, 232, 100), striped=False, radius=44, x_frac=0.76, raise_px=100),
    layers=[LayerSpec("clouds", 70, (255, 255, 255), 0.1, lift=170),
            LayerSpec("mountains", 44, (72, 168, 130), 0.25, params={"freqs": (2, 5, 8), "phase": 1.1}),
            LayerSpec("ocean", 30, (34, 120, 214), 0.05)],
    ground=((240, 218, 152), (228, 204, 134)),
    road=((150, 150, 162), (140, 140, 152)),
    rumble=((250, 250, 250), (40, 120, 220)),
    water=((46, 132, 226), (34, 112, 208), -3.3),
    placements=[
        Placement(W(("palm", 1),), every=6, near=1.5, far=2.9, sides=0),
        Placement(W(("palm", 2), ("umbrella", 1)), every=6, phase=3, near=1.6, far=2.9, chance=0.5),
        Placement(W(("umbrella", 1),), every=13, phase=2, near=1.8, far=3.0, chance=0.7),
        Placement(W(("lifeguard", 1),), every=120, phase=40, near=2.2, far=2.9),
        Placement(W(("tuft", 1),), every=4, near=1.4, far=3.0, chance=0.8),
        Placement(W(("post_blue", 1),), every=12, near=1.25, far=1.25, sides=2),
        Placement(every=45, phase=20, near=1.45, far=1.45, curve_signs=("surf_l", "surf_r", "surf")),
    ])

# ---- DESERT: warm sky, mesas, dunes, cactus and sparse signs -----------------------------------------
DESERT = TrackTheme(
    key="desert", name="DESERT", tagline="DUSTY MESA HIGHWAY",
    sky_bands=((124, 40, 92), (172, 60, 82), (216, 92, 62), (240, 122, 52), (250, 152, 52),
               (255, 182, 72), (255, 208, 104), (255, 228, 144), (255, 242, 184)),
    sun=SunSpec((255, 246, 196), (255, 232, 150), striped=False, radius=56, x_frac=0.3, raise_px=20),
    layers=[LayerSpec("mountains", 80, (150, 74, 84), 0.2, params={"freqs": (2, 3, 5), "phase": 0.5}),
            LayerSpec("mesas", 78, (188, 88, 56), 0.4, params={"seed": 5}),
            LayerSpec("dunes", 30, (214, 150, 82), 0.7)],
    ground=((228, 174, 100), (214, 158, 86)),
    road=((134, 110, 94), (124, 102, 86)),
    rumble=((246, 226, 186), (192, 82, 42)),
    lane=(250, 232, 182),
    placements=[
        Placement(W(("cactus", 3), ("rock", 2), ("tumble", 2)), every=7, near=1.5, far=4.5, sides=0),
        Placement(W(("rock", 1), ("cactus", 1)), every=11, phase=4, near=2.0, far=5.0, sides=0, chance=0.7),
        Placement(W(("post_wood", 1),), every=20, near=1.25, far=1.25, sides=2),
        Placement(every=90, phase=40, near=1.4, far=1.4, curve_signs=("sign_l", "sign_r", "sign")),
    ])

THEMES = [SUBURBS, CITY, BEACH, DESERT]


class TrackThemeManager:
    """Owns the theme list and caches the (relatively costly) backdrop / preview art per theme."""

    def __init__(self, themes=None):
        self.themes = list(themes or THEMES)
        self._backdrops, self._previews = {}, {}

    def __len__(self):
        return len(self.themes)

    def backdrop(self, theme, width, horizon):
        if theme.key not in self._backdrops:
            self._backdrops[theme.key] = assets.Backdrop(width, horizon, theme)
        return self._backdrops[theme.key]

    def preview(self, theme, width=240, height=144):
        """Small pixel-art picture of the theme for the track select screen."""
        key = (theme.key, width, height)
        if key not in self._previews:
            self._previews[key] = self._render_preview(theme, width, height)
        return self._previews[key]

    def _render_preview(self, theme, width, height):
        W_, H_, horizon = 800, 480, 290
        canvas = pygame.Surface((W_, H_))
        canvas.fill(theme.ground[1])
        assets.Backdrop(W_, horizon, theme).draw(canvas, 0)
        light, dark = theme.colors
        canvas.fill(theme.ground[0], (0, horizon, W_, H_ - horizon))
        if theme.water:
            pygame.draw.polygon(canvas, theme.water[0], ((0, horizon), (300, horizon), (-260, H_), (0, H_)))
        cx = W_ // 2
        for shade, top_w, bot_w in ((light["rumble"], 62, 470), (light["road"], 50, 420)):
            pygame.draw.polygon(canvas, shade, ((cx - top_w, horizon), (cx + top_w, horizon), (cx + bot_w, H_), (cx - bot_w, H_)))
        for k in range(5):                                              # centre dashes
            y0, y1 = horizon + 20 + k * 38 + k * k * 5, horizon + 32 + k * 38 + k * k * 8
            w0, w1 = 2 + k * 2, 4 + k * 3
            pygame.draw.polygon(canvas, light["lane"], ((cx - w0, y0), (cx + w0, y0), (cx + w1, y1), (cx - w1, y1)))
        painters = [kind for pl in theme.placements for kind, _ in (pl.kinds or ())][:3] or ["tree"]
        props = theme.preview or ((painters[0], 110, 430, 0.5), (painters[-1], 690, 400, 0.42), (painters[0], 250, 350, 0.22))
        for kind, x, y, s in props:
            assets.SCENERY[kind](canvas, x, y, s)
        return pygame.transform.scale(canvas, (width, height))
