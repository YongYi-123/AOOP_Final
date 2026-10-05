"""Visual style of the arcade, as data.

A StylePalette is a handful of numbers (how neon, how glowy, how saturated).
An ArcadeStyle applies one palette to every room: it turns each room's base
RoomTheme (its own colours and accents) into a styled theme and scales the
lighting. Rooms ask the style - they never branch on a style name - so a new
look is one more entry in STYLES.

  neon_lofi  the default: late-night neon arcade with a cozy lofi atmosphere
  lofi       the calm, muted look (soft machine glow, gentle neon)
  neon       the original bright look: saturated colours and strong glow

Select one with `python main.py --style NAME` (or Game(style=NAME)).
"""
import sys
from dataclasses import dataclass, replace

from gfx import lerp_color, scale_color
from room_art import ROOM_THEMES, RoomTheme

DEFAULT_STYLE = "neon_lofi"


@dataclass(frozen=True)
class StylePalette:
    name: str
    neon: float             # 0..1: how far wall / rail / floor colours lean toward the room's neon accents
    saturation: float       # colour saturation multiplier for the room colours
    glow: float             # multiplier on light pools and neon halos
    seams: float            # brightness of the neon seams in the floor
    scanlines: float        # multiplier on the CRT scanline overlay
    soft_machines: bool     # cabinets use the gentler halo set


STYLE_PALETTES = {
    "neon_lofi": StylePalette("neon_lofi", neon=0.6, saturation=1.25, glow=1.2, seams=1.15,
                              scanlines=1.0, soft_machines=False),
    "lofi": StylePalette("lofi", neon=0.0, saturation=1.0, glow=0.8, seams=0.5,
                         scanlines=0.6, soft_machines=True),
    "neon": StylePalette("neon", neon=1.0, saturation=1.5, glow=1.55, seams=1.8,
                         scanlines=1.3, soft_machines=False),
}
STYLE_NAMES = tuple(STYLE_PALETTES)


def saturate(color, amount):
    grey = sum(color[:3]) / 3
    return tuple(max(0, min(255, int(grey + (c - grey) * amount))) for c in color[:3])


# colour fields that get saturated; night / light_center stay as the room set them
_TINTED = ("floor_a", "floor_b", "grout", "shine", "wall", "wall_stripe", "wall_dot", "rail",
           "rail_hi", "wainscot", "side_hi", "trim", "title", "title_glow")


class ArcadeStyle:
    """One palette applied to all rooms. Immutable after creation, so the
    three rooms and the hub share a single instance."""

    def __init__(self, palette):
        self.palette = palette
        self.name = palette.name
        self._themes = {room_id: self._style_theme(theme) for room_id, theme in ROOM_THEMES.items()}

    def _style_theme(self, theme):
        p = self.palette
        kw = {f: saturate(getattr(theme, f), p.saturation) for f in _TINTED}
        # lean the walls toward the room's own neon accents
        kw["wall_dot"] = lerp_color(kw["wall_dot"], theme.accent_a, 0.35 * p.neon)
        kw["wall_stripe"] = lerp_color(kw["wall_stripe"], scale_color(theme.accent_b, 0.35), 0.25 * p.neon)
        kw["rail_hi"] = lerp_color(kw["rail_hi"], theme.accent_a, 0.5 * p.neon)
        kw["light_edge"] = lerp_color(saturate(theme.light_edge, p.saturation),
                                      scale_color(theme.accent_a, 0.6), 0.3 * p.neon)
        kw["shine"] = lerp_color(kw["shine"], scale_color(theme.accent_b, 0.5), 0.35 * p.neon)
        return replace(theme, **kw)

    def theme_for(self, room_id):
        """The room's colours under this style (each room keeps its own accents)."""
        return self._themes[room_id]

    # ---- lighting helpers the rooms use instead of hard-coded numbers
    @property
    def soft_machines(self):
        return self.palette.soft_machines

    def light(self, color):
        """A light-pool colour, scaled by the style's glow."""
        return scale_color(color, self.palette.glow)

    def strength(self, value):
        """A neon halo strength, scaled by the style's glow."""
        return min(1.0, value * self.palette.glow)

    def seam(self, color, base):
        """A floor-seam colour at `base` brightness, scaled by the style."""
        return scale_color(color, min(1.0, base * self.palette.seams))

    def scanline_alpha(self, base):
        return max(0, min(255, int(base * self.palette.scanlines)))


class StyleManager:
    """Looks styles up by name. An unknown name falls back to the default
    (with a message) instead of failing, so a typo never stops the game."""

    def __init__(self, palettes=None, default=DEFAULT_STYLE):
        self.palettes = dict(STYLE_PALETTES if palettes is None else palettes)
        self.default = default
        self._cache = {}

    @property
    def names(self):
        return tuple(self.palettes)

    def get(self, name=None):
        name = name or self.default
        if name not in self.palettes:
            print(f"[style] unknown style {name!r}; using {self.default!r} "
                  f"(choose from: {', '.join(self.palettes)})", file=sys.stderr)
            name = self.default
        if name not in self._cache:
            self._cache[name] = ArcadeStyle(self.palettes[name])
        return self._cache[name]


STYLES = StyleManager()
