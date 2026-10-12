"""All tunable numbers for NEON CAT MAZE (package name: neon_cat_maze) in one place (pure data, no pygame)."""
from dataclasses import dataclass

FIELD_W, FIELD_H = 400, 300          # the logical canvas; the lobby canvas is the same size
TILE = 16                            # pixels per maze tile
MAZE_ORIGIN = (32, 30)               # top-left pixel of the maze: 21x15 tiles = 336x240, HUD above, hint strip below
STEP = 1 / 120                       # fixed simulation step (seconds): movement is identical at any frame rate
MAX_FRAME = 0.25                     # a longer frame (window drag, stall) is simulated as this much only

START_LIVES = 3
MAX_LIVES = 5

# --- scoring (all tunable here) -------------------------------------------------------------------------------
SCORES = dict(fish=10, golden=200, catnip=50, level_clear=500, level_clear_per_level=100,
              disable=(200, 400, 800, 1600))     # disable: 1st, 2nd, 3rd, 4th robot of ONE catnip
EXTRA_LIFE_AT = 5000                 # one bonus life the first time a run's score reaches this

# --- timings -----------------------------------------------------------------------------------------------------
READY_SECONDS = 1.6                  # "READY!" before the cat may move (also after losing a life)
DYING_SECONDS = 1.3
CLEAR_SECONDS = 3.2                  # the level-clear panel; confirm skips it after CLEAR_SKIP_AFTER
CLEAR_SKIP_AFTER = 1.0
OVER_SECONDS = 2.4                   # the GAME OVER banner before the results screen
RESPAWN_GRACE = 1.8                  # the cat cannot be caught this long after READY ends (it blinks)
TURN_BUFFER = 0.45                   # a turn pressed this long before an intersection is still taken

# --- movement (tiles per second) ---------------------------------------------------------------------------------
CAT_SPEED = 5.6
ROBOT_SPEED = dict(patrol=0.70, chase=0.80, ambush=0.76)   # fraction of the cat's speed on level 1
ROBOT_SPEED_PER_LEVEL = 0.02
ROBOT_SPEED_MAX = 0.96               # a robot is never as fast as the cat: pursuit can always be escaped
FRIGHT_SPEED = 0.50
EYES_SPEED = 1.8                     # a disabled robot hurries back to the den
CATCH_DISTANCE = 0.62                # tiles between centres that count as contact

# --- robots ---------------------------------------------------------------------------------------------------------
ROBOTS = ("patrol", "chase", "ambush")
ROBOT_NAMES = dict(patrol="PATROL BOT", chase="CHASE BOT", ambush="AMBUSH BOT")
RELEASE_FIRST = 2.2                  # seconds after READY before the first robot leaves the den ...
RELEASE_GAP = 3.0                    # ... and between the following ones (both shrink with the level)
RELEASE_MIN_GAP = 1.2
PATROL_TURN_CHANCE = (0.12, 0.02, 0.35)          # level-1 chance of a random turn at an intersection, +/level, cap
CHASE_NOISE = (0.22, -0.02, 0.04)                # chance a Chase Bot picks a random way instead of the best one
AMBUSH_LOOKAHEAD = 4                 # tiles ahead of the cat
AMBUSH_GIVE_UP = 3                   # closer than this many tiles the Ambush Bot stops lunging and circles away
# Scatter/chase: robots take turns being aggressive. (scatter seconds, chase seconds) on level 1, then per level.
SCATTER = (7.0, -0.5, 3.0)
CHASE = (12.0, 1.0, 26.0)

# --- catnip -----------------------------------------------------------------------------------------------------------
CATNIP_SECONDS = (7.0, -0.35, 3.5)   # level-1 duration, change per level, floor. Picking up a second one RESETS the
CATNIP_WARN = 2.0                    # timer to the full length (never longer) - effects do not stack. The last seconds flash.
DISABLED_SECONDS = 1.4               # a disabled robot sits in the den this long before it is released again

# --- golden fish ----------------------------------------------------------------------------------------------------
GOLDEN_AT = (0.35, 0.7)              # fractions of the level's fish eaten at which a golden fish appears
GOLDEN_SECONDS = 11.0

TICKETS = dict(per_level_cleared=3, per_score=450, cap=40)


def _ramp(spec, level):
    start, per_level, limit = spec
    value = start + per_level * (max(1, level) - 1)
    return max(value, limit) if per_level < 0 else min(value, limit)


@dataclass(frozen=True)
class Difficulty:
    """Everything that depends on the level number. Every value is capped, so a high level stays hard but fair."""
    speed: dict               # robot kind -> tiles/s
    release_first: float
    release_gap: float
    patrol_turn: float
    chase_noise: float
    scatter: float
    chase: float
    catnip: float


def difficulty_for(level):
    level = max(1, int(level))
    speed = {k: min(ROBOT_SPEED_MAX, base + ROBOT_SPEED_PER_LEVEL * (level - 1)) * CAT_SPEED
             for k, base in ROBOT_SPEED.items()}
    return Difficulty(speed=speed,
                      release_first=max(0.8, RELEASE_FIRST - 0.15 * (level - 1)),
                      release_gap=max(RELEASE_MIN_GAP, RELEASE_GAP - 0.25 * (level - 1)),
                      patrol_turn=_ramp(PATROL_TURN_CHANCE, level), chase_noise=_ramp(CHASE_NOISE, level),
                      scatter=_ramp(SCATTER, level), chase=_ramp(CHASE, level), catnip=_ramp(CATNIP_SECONDS, level))
