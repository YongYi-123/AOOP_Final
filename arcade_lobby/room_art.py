"""Shared art for the three hub rooms: the colour themes that give each room
its own feel, a backdrop that paints floor, walls and doorways from a theme,
and a few small animated effects. The rooms add their own decor on top, so
all three are the same neon-lofi world with different lighting.

Everything static is painted once into cached layers (backdrop.py); the
effects here only pick a pre-rendered level per frame."""
import math
from dataclasses import dataclass

import pygame

from backdrop import ArcadeBackdrop
from font import get_font
from gfx import glow_line, neon_rect_glow, radial_glow, scale_color, shade
from settings import (FLOOR_BOTTOM, FLOOR_TOP, SIDE_DOOR_H, SIDE_DOOR_Y, VIEW_H,
                      VIEW_W, WALL_SIDE)

WALL_STRIP_Y = 46


@dataclass(frozen=True)
class RoomTheme:
    name: str
    floor_style: str            # "planks", "grid" or "checker"
    night: tuple
    floor_a: tuple
    floor_b: tuple
    grout: tuple
    shine: tuple
    wall: tuple
    wall_stripe: tuple
    wall_dot: tuple
    rail: tuple
    rail_hi: tuple
    wainscot: tuple
    wainscot_line: tuple
    baseboard: tuple
    side: tuple
    side_hi: tuple
    trim: tuple                 # neon edge colour of the walls
    light_edge: tuple           # vignette: darkest colour at the corners ...
    light_center: tuple         # ... and the colour in the middle
    title: tuple                # room-name colours
    title_glow: tuple
    accent_a: tuple = (255, 255, 255)   # the room's two neon accent colours
    accent_b: tuple = (255, 255, 255)


HOME_THEME = RoomTheme(
    "HOME", "planks",
    night=(12, 12, 30), floor_a=(58, 40, 70), floor_b=(64, 44, 76), grout=(38, 26, 50),
    shine=(78, 56, 92), wall=(32, 27, 62), wall_stripe=(36, 30, 69), wall_dot=(44, 37, 82),
    rail=(56, 44, 92), rail_hi=(74, 60, 116), wainscot=(25, 21, 49), wainscot_line=(20, 17, 40),
    baseboard=(17, 15, 35), side=(18, 16, 38), side_hi=(24, 21, 48), trim=(150, 112, 230),
    light_edge=(74, 62, 118), light_center=(224, 210, 244),
    title=(255, 206, 232), title_glow=(176, 96, 170),
    accent_a=(150, 112, 230), accent_b=(225, 105, 190))

ARCADE_THEME = RoomTheme(
    "ARCADE FLOOR", "grid",
    night=(8, 8, 24), floor_a=(15, 14, 40), floor_b=(19, 17, 48), grout=(10, 10, 30),
    shine=(40, 36, 86), wall=(26, 20, 60), wall_stripe=(31, 24, 70), wall_dot=(50, 36, 104),
    rail=(70, 40, 120), rail_hi=(90, 170, 214), wainscot=(18, 14, 42), wainscot_line=(14, 11, 32),
    baseboard=(10, 8, 26), side=(12, 10, 32), side_hi=(20, 16, 48), trim=(80, 240, 255),
    light_edge=(54, 46, 112), light_center=(206, 214, 255),
    title=(190, 252, 255), title_glow=(255, 70, 200),
    accent_a=(80, 240, 255), accent_b=(255, 70, 200))

PLAZA_THEME = RoomTheme(
    "PRIZE PLAZA", "checker",
    night=(18, 10, 30), floor_a=(46, 28, 66), floor_b=(60, 36, 80), grout=(112, 84, 52),
    shine=(120, 80, 120), wall=(54, 26, 74), wall_stripe=(62, 30, 84), wall_dot=(150, 104, 70),
    rail=(170, 130, 70), rail_hi=(236, 196, 116), wainscot=(38, 18, 56), wainscot_line=(30, 14, 46),
    baseboard=(22, 10, 36), side=(30, 16, 46), side_hi=(42, 22, 62), trim=(255, 214, 90),
    light_edge=(92, 62, 118), light_center=(255, 232, 246),
    title=(255, 232, 150), title_glow=(255, 90, 190),
    accent_a=(255, 214, 90), accent_b=(255, 110, 190))

ROOM_THEMES = {"home": HOME_THEME, "arcade_floor": ARCADE_THEME, "prize_plaza": PLAZA_THEME}


def door_rect(side):
    """The doorway gap in a side wall, in canvas pixels."""
    x = 0 if side == "left" else VIEW_W - WALL_SIDE
    return pygame.Rect(x, SIDE_DOOR_Y, WALL_SIDE, SIDE_DOOR_H)


# ------------------------------------------------------------ static layers
class HubBackdrop(ArcadeBackdrop):
    """Paints a room's static look from a RoomTheme: floor, papered back wall
    with a chair rail and wainscot, side walls with the doorways cut out, and
    a glowing vertical sign above each doorway. Subclasses add posters, shelves
    and other decor in paint_room()."""

    def __init__(self, size, theme, doors, style):
        """`doors` maps "left" / "right" to (label, colour) of the room it leads to;
        `style` is the shared ArcadeStyle (glow and seam strengths)."""
        super().__init__(size)
        self.theme = theme
        self.doors = doors
        self.style = style

    # -------------------------------------------------------------- floor
    def paint_floor(self, surf):
        t = self.theme
        surf.fill(t.night)
        tile = 16
        for y in range(FLOOR_TOP, FLOOR_BOTTOM, tile):
            for x in range(0, VIEW_W, tile):
                i, j = x // tile, (y - FLOOR_TOP) // tile
                if t.floor_style == "planks":
                    self._plank(surf, x, y, tile, i, j)
                else:
                    surf.fill(t.floor_b if (i + j) % 2 else t.floor_a, (x, y, tile, tile))
                    surf.fill(t.grout, (x, y, tile, 1))
                    surf.fill(t.grout, (x, y, 1, tile))
                    if (i * 3 + j) % 5 == 0:
                        surf.fill(t.shine, (x + 2, y + 2, 3, 1))
        if t.floor_style == "grid":                      # glowing neon seams
            for x in range(WALL_SIDE + 16 * 4, VIEW_W - WALL_SIDE, 16 * 6):
                surf.fill(self.style.seam(t.trim, 0.22), (x, FLOOR_TOP, 1, FLOOR_BOTTOM - FLOOR_TOP))
            for y in range(FLOOR_TOP + 16 * 3, FLOOR_BOTTOM, 16 * 5):
                surf.fill(self.style.seam(t.trim, 0.22), (WALL_SIDE, y, VIEW_W - 2 * WALL_SIDE, 1))
        shadow = pygame.Surface((VIEW_W, 8), pygame.SRCALPHA)   # under the back wall
        for i, a in enumerate((110, 80, 55, 35, 20, 10)):
            shadow.fill((0, 0, 0, a), (0, i, VIEW_W, 1))
        surf.blit(shadow, (0, FLOOR_TOP))

    def _plank(self, surf, x, y, tile, i, j):
        t = self.theme
        surf.fill(t.floor_b if (i + j // 2) % 2 else t.floor_a, (x, y, tile, tile))
        surf.fill(t.grout, (x, y, tile, 1))
        if (i * 5 + j * 3) % 4 == 0:                           # board ends
            surf.fill(t.grout, (x, y, 1, tile))
        if (i + j) % 3 == 0:
            surf.fill(t.shine, (x + 3, y + 5, 4, 1))

    # -------------------------------------------------------------- walls
    def paint_walls(self, surf):
        t = self.theme
        surf.fill(t.wall, (0, 0, VIEW_W, FLOOR_TOP))
        for x in range(0, VIEW_W, 12):
            surf.fill(t.wall_stripe, (x, 4, 2, WALL_STRIP_Y - 4))
        for y in range(8, WALL_STRIP_Y - 2, 8):
            for x in range(6 + (y // 8 % 2) * 6, VIEW_W, 12):
                surf.fill(t.wall_dot, (x, y, 1, 1))
        surf.fill(t.night, (0, 0, VIEW_W, 3))
        k = self.style.palette.neon
        surf.fill(scale_color(t.trim, 0.35 + 0.35 * k), (0, 3, VIEW_W, 1))      # ceiling neon
        surf.fill(t.rail, (0, WALL_STRIP_Y - 1, VIEW_W, 3))
        surf.fill(t.rail_hi, (0, WALL_STRIP_Y - 1, VIEW_W, 1))
        surf.fill(t.wainscot, (0, WALL_STRIP_Y + 2, VIEW_W, FLOOR_TOP - WALL_STRIP_Y - 6))
        for x in range(0, VIEW_W, 20):
            surf.fill(t.wainscot_line, (x, WALL_STRIP_Y + 4, 1, 10))
        surf.fill(t.baseboard, (0, FLOOR_TOP - 4, VIEW_W, 4))
        surf.fill(t.rail, (0, FLOOR_TOP - 4, VIEW_W, 1))

        for side, x in (("left", 0), ("right", VIEW_W - WALL_SIDE)):
            gap = door_rect(side) if side in self.doors else None
            spans = [(0, VIEW_H)] if gap is None else [(0, gap.top), (gap.bottom, VIEW_H)]
            for y0, y1 in spans:
                surf.fill(t.side, (x, y0, WALL_SIDE, y1 - y0))
                surf.fill(t.side_hi, (x + 3, y0, WALL_SIDE - 6, y1 - y0))
            edge = WALL_SIDE - 1 if side == "left" else VIEW_W - WALL_SIDE
            surf.fill(scale_color(t.trim, 0.45 + 0.4 * k), (edge, FLOOR_TOP, 1, FLOOR_BOTTOM - FLOOR_TOP))
            if gap is not None:
                self._paint_doorway(surf, side, gap)

        surf.fill(t.side, (0, FLOOR_BOTTOM, VIEW_W, VIEW_H - FLOOR_BOTTOM))
        surf.fill(t.side_hi, (0, FLOOR_BOTTOM + 3, VIEW_W, VIEW_H - FLOOR_BOTTOM - 6))
        surf.fill(scale_color(t.trim, 0.45 + 0.4 * k), (0, FLOOR_BOTTOM, VIEW_W, 1))

    def _paint_doorway(self, surf, side, gap):
        """Frame, dimming floor and a vertical neon label for one doorway."""
        label, color = self.doors[side]
        t = self.theme
        # the floor continues out through the gap, getting darker toward the edge
        shade_layer = pygame.Surface(gap.size, pygame.SRCALPHA)
        for i in range(WALL_SIDE):
            k = i / WALL_SIDE if side == "left" else 1 - i / WALL_SIDE
            shade_layer.fill((4, 2, 12, int(235 * (1 - k) ** 1.5)), (i, 0, 1, gap.h))
        surf.blit(shade_layer, gap.topleft)
        for y in (gap.top - 2, gap.bottom):                       # door frame
            surf.fill(t.baseboard, (gap.x, y, WALL_SIDE, 2))
            surf.fill(color, (gap.x, y if y < gap.top else y + 1, WALL_SIDE, 1))
        # vertical neon sign on the wall above the door, reading toward the room it leads to
        text = get_font().render(label, shade(color, 0.3))
        text = pygame.transform.rotate(text, 90 if side == "left" else -90)
        y = gap.top - 6 - text.get_height()
        x = gap.centerx - text.get_width() // 2
        surf.fill((10, 6, 22), (x - 2, y - 2, text.get_width() + 4, text.get_height() + 4))
        pygame.draw.rect(surf, scale_color(color, 0.7),
                         (x - 2, y - 2, text.get_width() + 4, text.get_height() + 4), 1)
        surf.blit(text, (x, y))
        # light spilling out of the doorway and from its sign
        glow_x = gap.x - 14 if side == "left" else gap.x - 8
        self.add_light(neon_rect_glow(WALL_SIDE, gap.h, color, 8, self.style.strength(0.18)), (glow_x - 4, gap.y - 8))
        self.add_light(radial_glow(18, self.style.light(scale_color(color, 0.28)), bands=4, squash=1.6),
                       (x - 9, y + text.get_height() // 2 - 28))

    # -------------------------------------------------------------- decor
    def paint_decor(self, surf):
        self.add_light(glow_line(VIEW_W, self.theme.trim, spread=3, strength=self.style.strength(0.18)), (-3, 1))
        rail = glow_line(VIEW_W - 2 * WALL_SIDE, self.theme.rail_hi, spread=3,
                         strength=self.style.strength(0.06 + 0.12 * self.style.palette.neon))
        self.add_light(rail, (WALL_SIDE - 3, WALL_STRIP_Y - 3))                  # chair-rail glow
        self.paint_room(surf)

    def paint_room(self, surf):
        """Hook: this room's own posters, shelves and signs."""


# ------------------------------------------------------------------ effects
class FloorStrips:
    """Neon strips set into the floor that pulse, with a spark chasing along
    each. `strips` is a list of (rect, colour)."""

    def __init__(self, strips, gain=1.0):
        self.strips = strips
        self.gain = gain            # the style's glow
        self.t = 0.0

    def update(self, t):
        self.t = t

    def draw(self, surf):
        pulse = 0.55 + 0.35 * math.sin(self.t * 1.6)
        for i, (rect, color) in enumerate(self.strips):
            surf.fill(scale_color(color, min(1.0, pulse * self.gain)), rect)
            length = max(rect.w, rect.h)
            pos = int((self.t * 60 + i * 37) % (length + 20)) - 10
            if rect.w > rect.h:
                spark = pygame.Rect(rect.x + pos, rect.y, 6, 1).clip(rect)
            else:
                spark = pygame.Rect(rect.x, rect.y + pos, 1, 6).clip(rect)
            if spark.w and spark.h:
                surf.fill(shade(color, 0.7), spark)


class Twinkles:
    """Little sparkles that wink on and off at fixed spots (prize shelves)."""

    def __init__(self, spots, colors=((255, 244, 190), (255, 190, 230), (190, 240, 255))):
        self.spots = spots            # (x, y, phase)
        self.colors = colors
        self.t = 0.0

    def update(self, t):
        self.t = t

    def draw(self, surf):
        for i, (x, y, phase) in enumerate(self.spots):
            v = math.sin(self.t * 2.2 + phase)
            if v > 0.55:
                c = self.colors[i % len(self.colors)]
                surf.fill(c, (x, y, 1, 1))
                if v > 0.85:
                    surf.fill(scale_color(c, 0.6), (x - 1, y, 3, 1))
                    surf.fill(scale_color(c, 0.6), (x, y - 1, 1, 3))
