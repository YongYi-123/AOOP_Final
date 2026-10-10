"""Tunable constants for the retro racer."""
import math

# Window
WIDTH, HEIGHT = 800, 600
FPS = 60
TITLE = "RETRO GRAND PRIX"

# Road geometry (world units)
SEGMENT_LENGTH = 200
ROAD_WIDTH = 2000          # half-width of the road in world units
RUMBLE_SEGMENTS = 3        # segments per colour band
LANES = 3
DRAW_DISTANCE = 220        # segments drawn ahead of the camera
CAMERA_HEIGHT = 1000
FIELD_OF_VIEW = 100
CAMERA_DEPTH = 1 / math.tan(math.radians(FIELD_OF_VIEW / 2))

# Player physics
MAX_SPEED = SEGMENT_LENGTH * FPS        # world units per second
ACCEL = MAX_SPEED / 5
BRAKING = MAX_SPEED * 0.9
DECEL = MAX_SPEED / 8                   # coasting
OFFROAD_DECEL = MAX_SPEED / 2
OFFROAD_LIMIT = MAX_SPEED / 4
STEER_RATE = 2.0
CENTRIFUGAL = 0.35
COLLISION_SPEED_PENALTY = 0.6            # fraction of speed lost in a crash (baseline car)
COLLISION_FOLLOW_FACTOR = 0.9            # after a crash you can't keep more than this x the other car's speed
DISPLAY_MAX_KMH = 300

# Colours
SKY_TOP = (16, 8, 64)
SKY_BOTTOM = (255, 110, 150)
SUN = (255, 220, 90)
MOUNTAIN = (70, 30, 110)
WHITE = (240, 240, 240)
HUD_YELLOW = (255, 230, 60)
HUD_RED = (255, 60, 60)

LIGHT = {"road": (107, 107, 107), "grass": (16, 170, 16), "rumble": (255, 255, 255), "lane": (240, 240, 240)}
DARK = {"road": (99, 99, 99), "grass": (0, 154, 0), "rumble": (200, 0, 0), "lane": None}

# Traffic
TRAFFIC_COUNT = 8
TRAFFIC_MIN_SPEED = 0.2 * MAX_SPEED
TRAFFIC_MAX_SPEED = 0.6 * MAX_SPEED
TRAFFIC_SPAWN_MIN = 8000          # world units ahead of the player
TRAFFIC_SPAWN_MAX = 40000
TRAFFIC_MIN_GAP = 3000            # min z distance between cars in the same lane at spawn
TRAFFIC_DESPAWN_BEHIND = 3000     # recycle cars this far behind the player
TRAFFIC_DESPAWN_AHEAD = 44000     # ...or this far ahead (beyond draw distance)
TRAFFIC_LANES = (-0.66, 0.0, 0.66)
COLLISION_DEPTH = 350             # z overlap that counts as touching
SHAKE_TIME = 0.4

# Race rules
RACE_LAPS = 3
START_TIME = 45.0                     # seconds on the clock at the start
CHECKPOINT_BONUS = 12                 # seconds added per checkpoint
CHECKPOINT_FRACTIONS = (0.33, 0.66)   # checkpoint positions as a fraction of one lap
BANNER_TIME = 1.2                     # seconds a checkpoint/lap message stays up
TIME_BONUS_SCORE = 50                 # score per second left on the clock when finishing
CHECKPOINT_COLOR = (255, 190, 0)

# Presentation
DRIVING_FX_INTENSITY = 1.0    # 0 disables driving visuals; V cycles 0..2
VOLUME = 0.6                 # global volume, 0.0 - 1.0 (M mutes, [ and ] change it in-game)
COUNTDOWN_SECONDS = 3        # 3-2-1 before the race; the clock and car are frozen during it
GO_TIME = 0.9                # how long "GO!" stays on screen

# Audio balance (multipliers on top of VOLUME)
ENGINE_VOLUME = 0.6          # engine loudness; SFX_VOLUME is independent so the mix can be rebalanced
SFX_VOLUME = 1.2             # all one-shot effects together ...
UI_VOLUME = 0.9              # ... and per category on top of that:
COLLISION_VOLUME = 1.0       #   crashes
ITEM_VOLUME = 1.0            #   pickups, item use, hits, shield pops
RACE_VOLUME = 1.0            #   countdown, GO, checkpoints, finish / game over
REMOTE_ITEM_VOLUME = 0.35    # AI racers' item sounds (heard only when close) relative to your own
SFX_MAX_GAIN = 0.7           # hard ceiling for any single effect: headroom so engine + effects never clip
ENGINE_DUCK = 0.55           # engine level while a big event sound plays

# Endless mode
ENDLESS_MAX_CRASHES = 5      # run ends on this many collisions
ENDLESS_RAMP_SECONDS = 150   # time for difficulty to climb from 0 to its maximum
ENDLESS_LEVELS = 6           # difficulty is shown as LEVEL 1..N
ENDLESS_MAX_CARS = 14        # traffic grows from TRAFFIC_COUNT to this
ENDLESS_MIN_SPEED_SCALE = 0.75   # traffic speed multiplier at maximum difficulty (slower = harder to get past)

# Competitive racing (AI opponents + items)
RACE_OPPONENTS = 5           # computer racers (player + 5 = 6 on the grid)
RACE_TRAFFIC_COUNT = 4       # civilian traffic is thin during a real race (Endless keeps TRAFFIC_COUNT)
TRAFFIC_CLEAR_OF_RACERS = 4000   # never spawn civilians this close (in track units) to a racer
TRAFFIC_MAX_ABREAST = 2      # never spawn a third car within TRAFFIC_ABREAST_ZONE of two others (no walls)
TRAFFIC_ABREAST_ZONE = 2500
GRID_CLEAR_ZONE = 3000       # no item boxes this close to any grid slot
PLAYER_START_PROGRESS = CAMERA_HEIGHT * CAMERA_DEPTH   # the player's car starts this far past the start line
GRID_ROW_GAP = 800           # world units between grid rows
ITEM_ROWS_PER_LAP = 6        # rows of pickup boxes around the lap (3 boxes per row)
ITEM_RESPAWN = 8.0           # seconds before a collected box comes back
ITEM_RUBBER_BAND = 0.6       # 0 = pure random item choice, 1 = strong catch-up bias
