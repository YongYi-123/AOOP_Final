"""Pixel art of CHAPTER 02's symbols, for the hub's screens (Mochi's maintenance lock and the Quest Log).

The three real symbols are the very patterns the minigames draw (neon_cat_maze/corridor.py, galaxy_defender/
quiet_signal.py, pixel_volleyball/old_ticket.py), so what the player saw in a game is exactly what the lock offers.
The others are decoys: they exist only on the lock's wheels.
"""
import os
import sys

import pygame

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # the minigame packages live in the project root
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from galaxy_defender.quiet_signal import MOON_PIXELS  # noqa: E402
from neon_cat_maze.corridor import STAR_PIXELS  # noqa: E402
from pixel_volleyball.old_ticket import PAW_PIXELS  # noqa: E402

HEART_PIXELS = (".##...##.", "####.####", "#########", "#########", ".#######.", "..#####..", "...###...",
                "....#....", ".........")
FISH_PIXELS = (".........", "...###..#", ".######.#", "##.######", "#########", ".######.#", "...###..#",
               ".........", ".........")
BOLT_PIXELS = ("....###..", "...###...", "..###....", ".#######.", "....###..", "...###...", "..###....",
               ".##......", "#........")
KEY_PIXELS = (".###.....", "#...#....", "#...#....", ".###.....", "..#......", "..###....", "..#......",
              "..##.....", "..#......")
CROWN_PIXELS = (".........", "#...#...#", "##.###.##", "#########", "#########", "#########", ".#######.",
                ".........", ".........")
EYE_PIXELS = (".........", "..#####..", ".#.....#.", "#..###..#", "#..###..#", ".#.....#.", "..#####..",
              ".........", ".........")

SYMBOL_PIXELS = {"STAR": STAR_PIXELS, "MOON": MOON_PIXELS, "PAW": PAW_PIXELS, "HEART": HEART_PIXELS,
                 "FISH": FISH_PIXELS, "BOLT": BOLT_PIXELS, "KEY": KEY_PIXELS, "CROWN": CROWN_PIXELS,
                 "EYE": EYE_PIXELS}
SYMBOL_COLORS = {"STAR": (255, 214, 90), "MOON": (130, 200, 255), "PAW": (245, 150, 205), "HEART": (255, 110, 160),
                 "FISH": (90, 230, 210), "BOLT": (255, 240, 120), "KEY": (200, 200, 220), "CROWN": (255, 170, 60),
                 "EYE": (190, 140, 255)}


def symbol_image(name, scale=2, colour=None, fit=None):
    """The symbol as a transparent surface (its cells at `scale`). None for an unknown name. `fit`: instead of `scale`,
    the largest whole scale that keeps it within `fit` pixels (patterns are not all the same size: PAW is 13 x 13)."""
    rows = SYMBOL_PIXELS.get(name)
    if rows is None:
        return None
    if fit is not None:
        scale = max(1, fit // max(len(rows), len(rows[0])))
    colour = colour or SYMBOL_COLORS.get(name, (255, 255, 255))
    surf = pygame.Surface((len(rows[0]) * scale, len(rows) * scale), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                surf.fill(colour, (x * scale, y * scale, scale, scale))
    return surf
