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

# The hub is three rooms side by side (ARCADE FLOOR <-> HOME <-> PRIZE PLAZA).
# Doorways are gaps in the side walls; walking into one changes room.
ROOM_IDS = ("arcade_floor", "home", "prize_plaza")
START_ROOM = "home"
SIDE_DOOR_Y, SIDE_DOOR_H = 198, 52      # the doorway gap in a side wall
EXIT_DEPTH = 12                         # feet this close to the screen edge trigger the exit
ENTRY_INSET = 34                        # where a player arriving through a door stands
ARRIVAL_GRACE = 0.4                     # seconds after arriving before exits work again
PLAYER_START = (200, 250)               # first spawn, in HOME
ROOM_TITLE_TIME = 2.0                   # seconds the room name stays on screen

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
INVENTORY_KEY = pygame.K_i
CONFIRM_KEYS = (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
PREV_KEYS = (pygame.K_UP, pygame.K_w)
NEXT_KEYS = (pygame.K_DOWN, pygame.K_s)
BACK_KEYS = (pygame.K_ESCAPE,)

# Debug build only (python main.py --debug)
DEBUG = False
DEBUG_TOKEN_KEY = pygame.K_F5        # +DEBUG_TOKENS tokens
DEBUG_NEXT_DAY_KEY = pygame.K_F6     # pretend it is the next calendar day
DEBUG_RESET_TASKS_KEY = pygame.K_F7  # roll a fresh set of daily tasks
DEBUG_TOKENS = 10
DEBUG_STICKER_KEY = pygame.K_F8      # add a CAT STICKER
DEBUG_COUPON_KEY = pygame.K_F9       # add a FREE PLAY COUPON

# ------------------------------------------------------------ economy
# Every number that shapes the token economy lives here. TOKENS are spent to
# play machines and chance games; TICKETS are a separate reward currency.
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save_data.json")   # the old single-profile save
SAVES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")   # profiles.json + profiles/<id>.json
MAX_LOCAL_PLAYERS = 2           # a running session; the number of SAVED profiles is unlimited
PROFILE_NAME_MAX = 12           # characters in a display name (the pixel font is wide)
RECENT_PROFILES = 8             # how many recently used profiles are remembered
STARTING_TOKENS = 10
STARTING_TICKETS = 0
DEFAULT_PLAY_COST = 1           # tokens per play, unless a machine sets play_cost
# Temporary: tickets paid out by minigames that have no real scoring yet.
PLACEHOLDER_REWARD_TICKETS = 5
TRANSACTION_HISTORY_SIZE = 30   # how many recent token changes are saved

# Daily login: the reward for streak day 1, 2, 3, ... Each entry is a token
# amount, or a dict such as {"tokens": 15, "items": {"free_play_coupon": 1}}.
DAILY_REWARDS = (5, 6, 7, 8, 10, 12, 15)
# After the last day of DAILY_REWARDS: "restart" begins again at day 1,
# "hold" keeps paying the last day's reward.
DAILY_AFTER_LAST = "restart"
# Skipping a calendar day or more: "reset" drops back to day 1, "keep" carries on.
DAILY_ON_MISS = "reset"

# Daily tasks. One is picked at random for each of DAILY_TASK_COUNT slots.
# "event" is what the profile reports (see PlayerProfile.record_*); "game_id"
# narrows it to one machine; "distinct" counts different keys (machines) once.
# "available": False keeps a task out of rotation until the game can report it.
# "reward" is tokens; "reward_tickets" and "reward_items" ({item_id: quantity})
# are optional extras. "requires_item" offers the task only to owners of that item.
# Every payout is a RewardBundle delivered by RewardService.
DAILY_TASK_COUNT = 3
DAILY_TASK_POOL = (
    {"id": "play_games", "description": "PLAY 3 ARCADE GAMES", "event": "game_played",
     "target": 3, "reward": 5},
    {"id": "earn_tickets", "description": "EARN 50 TICKETS", "event": "tickets_earned",
     "target": 50, "reward": 8},
    {"id": "play_racer", "description": "PLAY RETRO RACER", "event": "game_played",
     "game_id": "retro_racer", "target": 1, "reward": 4},
    {"id": "pet_cats", "description": "PET 3 CATS", "event": "cat_petted",
     "target": 3, "reward": 3},
    {"id": "visit_machines", "description": "VISIT 3 DIFFERENT MACHINES",
     "event": "machine_visited", "distinct": True, "target": 3, "reward": 5},
    # Only offered while the player owns a coupon to use.
    {"id": "use_coupon", "description": "USE A FREE PLAY COUPON", "event": "coupon_used",
     "target": 1, "reward": 4, "requires_item": "free_play_coupon"},
    # Retro Racer reports real scores through MiniGameResult.
    {"id": "beat_high_score", "description": "BEAT ONE HIGH SCORE", "event": "high_score",
     "target": 1, "reward": 10},
)

# Lucky Wheel: entry cost and the reward table. The chance of a reward is
# weight / sum(weights); nothing about the player changes it. This table pays
# back 0.95 tokens per token spent on average.
LUCKY_WHEEL_COST = 1
LUCKY_WHEEL_REWARDS = (
    {"tokens": 0, "weight": 50, "rarity": "COMMON"},
    {"tokens": 1, "weight": 28, "rarity": "COMMON"},
    {"tokens": 2, "weight": 12, "rarity": "COMMON"},
    {"tokens": 3, "weight": 6, "rarity": "UNCOMMON"},
    {"tokens": 5, "weight": 3, "rarity": "RARE"},
    {"tokens": 10, "weight": 1, "rarity": "VERY RARE"},
)
# The slices painted on the wheel, in order. Purely cosmetic: the result is
# drawn from LUCKY_WHEEL_REWARDS first and the wheel then stops on a slice
# showing that reward. Every reward above must appear at least once.
LUCKY_WHEEL_SLICES = (0, 1, 0, 2, 0, 1, 3, 0, 5, 1, 2, 10)

# High-Low: entry cost, and the tokens held after 1, 2, 3 ... correct guesses.
# The streak ends (and pays out) after len(HIGH_LOW_PAYOUTS) wins. A tie loses.
# The player sees the card before choosing, so a perfect player wins ~71% of
# guesses; these numbers are set so even perfect play returns only ~0.87
# tokens per token spent. (Entry 1 with payouts 2/4/8 would let a careful
# player earn ~2.65 per token and farm tokens.)
HIGH_LOW_COST = 2
HIGH_LOW_PAYOUTS = (2, 3, 5)
HIGH_LOW_RANKS = 13             # cards run from 1 (ace) to 13 (king)

# NEON 21 (Blackjack). Wagers are always TOKENS. Before the deal the player picks
# how WINNINGS are paid: TOKENS (default) or TICKETS. The stake itself is always
# returned in Tokens. Net profit converts at NEON21_TICKETS_PER_TOKEN tickets per
# profit token, but at most NEON21_DAILY_TICKET_CAP tickets per profile per
# calendar day; profit beyond the cap is paid in Tokens (and the player is told).
# These tickets are gambling winnings: they do not count as "earned" tickets
# (lifetime stat, EARN 50 TICKETS task). Natural blackjack pays 3:2, rounded down.
NEON21_WAGERS = (1, 2, 5, 10)
NEON21_DEFAULT_WAGER = 2
NEON21_TICKETS_PER_TOKEN = 1
NEON21_DAILY_TICKET_CAP = 30


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


# The arcade machines on the ARCADE FLOOR (see arcade_layout.py, which turns
# each entry into an ArcadeMachineDefinition). The id is what the minigame
# scene registry (scenes.MINIGAME_SCENES) and the save file's high scores key
# off. A new teammate game is just one more entry here.
#   "x" / "y"    where the cabinet stands; or "slot": a name from
#                arcade_layout.ARCADE_SLOTS instead of x / y
#   "game_id"    optional: the minigame (and high-score) id, defaults to "id"
#   "play_cost"  optional, defaults to DEFAULT_PLAY_COST
MACHINES = [
    {
        "id": "retro_racer",
        "name": "Retro Racer",
        "marquee": "RETRO RACER",
        "description": "Zoom down neon highways and race the sunrise home. "
                       "Three laps, one tiny car, zero brakes.",
        "x": 36,
        "neon": (255, 64, 80),
        "accent": (70, 150, 255),
        "screen": "racer",
        "play_cost": 1,
    },
    {
        "id": "space_blaster",
        "name": "Space Blaster",
        "marquee": "SPACE",
        "description": "Wobbly critters are drifting past the moon! "
                       "Defend the city skies with your trusty pew-pew ship.",
        "x": 92,
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
        "x": 148,
        "neon": (170, 80, 255),
        "accent": (255, 110, 210),
        "screen": "puzzle",
        "play_cost": 1,
    },
    {
        "id": "pixel_volleyball", "name": "Cat Volleyball", "marquee": "CAT VOLLEYBALL",
        "description": "Jump, receive and spike a yarn ball with pixel cats. "
                       "First to five points wins. Play solo or challenge a friend!",
        "slot": "wall_3", "neon": (50, 140, 255), "accent": (255, 150, 40),
        "screen": "volley", "play_cost": 1,
    },
    {
        "id": "cat_minesweeper", "name": "Cat Territory", "marquee": "CATS",
        "description": "One cat per color, row and column. Cats cannot touch. "
                       "Click to mark X, double click to place a cat. Three hearts!",
        "slot": "wall_4", "neon": (176, 96, 255), "accent": (90, 240, 255),
        "screen": "cat", "play_cost": 1,
    },
]


# The arcade cats. Each entry is pure data for one cats.CatNPC: its look
# (cat_sprites.CatLook fields), personality (friendly / shy / lazy / curious,
# see cat.PERSONALITIES) and meow pitch. Where each cat lives is up to the
# room: each room's cat_spots maps the id to its spots (the first is home).
# "room" is the one room the cat lives in (default "home"); a cat is never in
# two rooms.
CATS = [
    {
        "id": "miso", "name": "Miso", "personality": "friendly", "pitch": 1.0,
        # orange tabby
        "look": {"fur": (246, 164, 86), "shade": (208, 118, 60), "stripes": (208, 118, 60)},
    },
    {
        "id": "pixel", "name": "Pixel", "personality": "curious", "pitch": 1.12,
        "room": "arcade_floor",
        # black cat with a white bib and socks, glowing green eyes
        "look": {"fur": (62, 56, 84), "shade": (42, 38, 60), "belly": (232, 228, 248),
                 "eye": (170, 255, 120), "lid": (140, 130, 176), "nose": (230, 130, 170)},
    },
    {
        "id": "mochi", "name": "Mochi", "personality": "lazy", "pitch": 0.8,
        # round cream cat with grey patches and a grey tail
        "look": {"fur": (246, 240, 232), "shade": (196, 188, 192), "belly": (255, 252, 246),
                 "patch": (150, 146, 164), "cap": (150, 146, 164), "tail": (150, 146, 164),
                 "chonk": 1},
    },
    {
        "id": "luna", "name": "Luna", "personality": "shy", "pitch": 1.22,
        # blue-grey tabby with golden eyes
        "look": {"fur": (150, 160, 198), "shade": (102, 110, 150), "stripes": (108, 116, 158),
                 "belly": (222, 226, 244), "eye": (250, 210, 90), "lid": (70, 70, 104)},
    },
    {
        "id": "bean", "name": "Bean", "personality": "friendly", "pitch": 1.38,
        # tiny calico: white with orange and black patches
        "look": {"fur": (250, 244, 234), "shade": (206, 196, 190), "patch": (240, 150, 70),
                 "cap": (64, 54, 66), "tail": (240, 150, 70)},
    },
]
