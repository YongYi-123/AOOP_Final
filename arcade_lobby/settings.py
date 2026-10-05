"""Global settings, colour palette and content data for the arcade prototype.

Everything is drawn onto a small low-resolution canvas (VIEW_W x VIEW_H) which
is then scaled up by PIXEL_SCALE, giving crisp chunky pixels.
"""
import os

import pygame

TITLE = "Neon Corner Arcade"
SCREEN_W, SCREEN_H = 800, 600
PIXEL_SCALE = 2
VIEW_W, VIEW_H = SCREEN_W // PIXEL_SCALE, SCREEN_H // PIXEL_SCALE
FPS = 60

# Room layout, in canvas pixels
FLOOR_TOP = 64          # back wall occupies y < FLOOR_TOP
WALL_SIDE = 20          # thickness of the left/right walls
FLOOR_BOTTOM = 282      # bottom wall starts here
DOOR_X, DOOR_W = 180, 40
PLAYER_START = (200, 262)
CAT_HOME = (318, 226)

# Room look: "lofi" (chill late-night arcade) or "neon" (the original bright
# style). Override at launch with:  python main.py --style neon
BACKGROUND_STYLES = ("lofi", "neon")
BACKGROUND_STYLE = "lofi"

PLAYER_SPEED = 72       # canvas pixels per second
TRANSITION_TIME = 0.18  # seconds for each half of the scanline wipe
INTERACT_FLASH = 0.22   # machine flash before the dialogue opens

# Controls
MOVE_KEYS = {
    pygame.K_w: (0, -1), pygame.K_UP: (0, -1),
    pygame.K_s: (0, 1), pygame.K_DOWN: (0, 1),
    pygame.K_a: (-1, 0), pygame.K_LEFT: (-1, 0),
    pygame.K_d: (1, 0), pygame.K_RIGHT: (1, 0),
}
INTERACT_KEYS = (pygame.K_e,)
CONFIRM_KEYS = (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
PREV_KEYS = (pygame.K_UP, pygame.K_w)
NEXT_KEYS = (pygame.K_DOWN, pygame.K_s)
BACK_KEYS = (pygame.K_ESCAPE,)

# Player profile / arcade economy
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save_data.json")
STARTING_COINS = 10
STARTING_TICKETS = 0
DEFAULT_PLAY_COST = 1           # coins per play, unless a machine sets play_cost
# Temporary: tickets paid out by minigames that have no real scoring yet.
PLACEHOLDER_REWARD_TICKETS = 5

# Debug helpers (enable with:  python main.py --debug)
DEBUG = False
DEBUG_REFILL_KEY = pygame.K_F5
DEBUG_REFILL_COINS = 10


class Col:
    """Neon arcade palette: dark navy/purple base with bright accents."""
    OUTLINE = (12, 8, 22)
    SHADOW = (0, 0, 0)
    TEXT = (236, 232, 255)
    TEXT_MUTED = (150, 140, 204)

    CYAN = (80, 240, 255)
    MAGENTA = (255, 70, 200)
    PURPLE = (150, 90, 255)
    BLUE = (70, 120, 255)
    YELLOW = (255, 214, 90)
    GREEN = (90, 255, 150)

    PANEL = (14, 10, 34)
    FLOOR = (22, 18, 44)
    FLOOR_ALT = (27, 21, 54)
    WALL = (36, 26, 66)
    WALL_PANEL = (46, 34, 84)
    WALL_CAP = (24, 18, 46)
    CABINET = (26, 18, 46)
    CABINET_SIDE = (40, 30, 68)

    FADE = (6, 4, 14)


class Lofi:
    """Softer late-night palette for the lofi room: navy/purple base, muted
    neon, and a few warm lamp accents."""
    NIGHT = (12, 12, 30)
    CEILING = (16, 14, 36)
    WALL = (32, 27, 62)
    WALL_STRIPE = (36, 30, 69)
    WALL_DOT = (44, 37, 82)
    RAIL = (56, 44, 92)
    RAIL_HI = (74, 60, 116)
    WAINSCOT = (25, 21, 49)
    WAINSCOT_LINE = (20, 17, 40)
    WAINSCOT_HI = (31, 27, 60)
    BASEBOARD = (17, 15, 35)
    SIDE_WALL = (18, 16, 38)
    SIDE_WALL_HI = (24, 21, 48)

    TILE_A = (21, 21, 45)
    TILE_B = (24, 24, 51)
    GROUT = (17, 17, 37)
    TILE_SHINE = (31, 31, 63)

    PURPLE = (150, 112, 230)
    MAGENTA = (225, 105, 190)
    PINK = (255, 170, 215)
    CYAN = (110, 215, 235)
    BLUE = (100, 140, 235)
    WARM = (255, 196, 120)
    AMBER = (255, 150, 80)
    CREAM = (240, 222, 190)

    WOOD = (86, 60, 72)
    WOOD_HI = (116, 84, 92)
    WOOD_DARK = (56, 38, 50)
    TERRACOTTA = (172, 96, 80)
    TERRACOTTA_HI = (204, 124, 98)
    LEAF = (74, 152, 122)
    LEAF_DARK = (50, 116, 102)
    LEAF_LIGHT = (116, 196, 150)


# The three arcade machines. The id is what the minigame scene registry
# (scenes.MINIGAME_SCENES) and the save file's high scores key off.
# "play_cost" is optional and defaults to DEFAULT_PLAY_COST.
MACHINES = [
    {
        "id": "retro_racer",
        "name": "Retro Racer",
        "marquee": "RACE",
        "description": "Zoom down neon highways and race the sunrise home. "
                       "Three laps, one tiny car, zero brakes.",
        "x": 70,
        "neon": (255, 72, 72),
        "accent": (255, 168, 60),
        "screen": "racer",
        "play_cost": 1,
    },
    {
        "id": "space_blaster",
        "name": "Space Blaster",
        "marquee": "SPACE",
        "description": "Wobbly critters are drifting past the moon! "
                       "Defend the city skies with your trusty pew-pew ship.",
        "x": 130,
        "neon": (60, 130, 255),
        "accent": (90, 240, 255),
        "screen": "space",
        "play_cost": 1,
    },
    {
        "id": "puzzle_drop",
        "name": "Puzzle Drop",
        "marquee": "DROP",
        "description": "Stack the falling candies and clear full rows "
                       "before the sweet jar overflows.",
        "x": 190,
        "neon": (170, 80, 255),
        "accent": (255, 110, 210),
        "screen": "puzzle",
        "play_cost": 1,
    },
]
