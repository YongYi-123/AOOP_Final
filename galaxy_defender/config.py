"""All tunable numbers for Starfall Assault (package name: galaxy_defender) in one place (pure data, no pygame)."""
from dataclasses import dataclass

FIELD_W, FIELD_H = 400, 300          # the logical playfield; the lobby canvas is the same size
HUD_H = 24                           # the top strip reserved for the HUD
DEFENSE_LINE = 252                   # an enemy reaching this height breaches the defense
PLAYER_Y = 272                       # centre line of the player ship
MAX_HP = 3

PLAYER = dict(width=22, height=14, speed=170.0, cooldown=0.30, rapid_cooldown=0.13,
              bullet_speed=330.0, invulnerable=1.6, shield_grace=0.6, max_bullets=8,
              spread_angle=13.0, spread_bullet_bonus=8)
# Timed weapon upgrades: seconds of effect. They stack with each other, never with themselves
# (picking one up again just refreshes it).
POWER_SECONDS = dict(rapid=8.0, spread=10.0, pierce=8.0)

# Enemy kinds. `wobble` is the sideways weave of a Dash drone.
ENEMIES = {
    "scout": dict(name="SCOUT DRONE", hp=1, score=10, width=16, height=12, fire=1.0, bolt=1.0),
    "dash": dict(name="DART DRONE", hp=1, score=25, width=14, height=12, fire=1.3, bolt=1.45, wobble=7.0),
    "tank": dict(name="ARMOR BOT", hp=3, score=40, width=20, height=14, fire=0.7, bolt=0.85),
}
DASH_FROM_WAVE = 3
TANK_FROM_WAVE = 4

BOSS_EVERY = 5
BOSS = dict(name="MOTHERSHIP", width=60, height=24, y=42, base_hp=28, hp_per_boss=12, max_hp=120,
            base_speed=48.0, speed_per_boss=5.0, max_speed=90.0, score=500, score_per_boss=250,
            switch_seconds=5.0, spread_gap=1.9, aimed_gap=1.5, enraged_below=0.5)

SCORES = dict(wave_clear_per_wave=50, wave_clear_max=500)
# Chain kills: every `step` kills in a row adds `bonus` to the score multiplier, up to `max_mult`.
COMBO = dict(window=1.6, step=3, bonus=0.25, max_mult=2.0, announce_every=5)
CARGO_FROM_WAVE = 2          # waves with a Cargo Drone: one marked drone that always drops a power-up
CARGO_PER_WAVES = 12         # one extra Cargo Drone per this many waves, up to CARGO_MAX
CARGO_MAX = 3
WAVE_BANNER_SECONDS = 2.0


@dataclass(frozen=True)
class Difficulty:
    """Everything that depends on the wave number. Each value is capped so a very high wave
    stays hard but fair."""
    columns: int
    rows: int
    speed: float             # formation px/s
    step_down: float         # px dropped at every edge
    fire_gap: float          # seconds between formation volleys
    bolt_speed: float
    max_bolts: int


DIFFICULTY = dict(columns=(6, 1 / 2, 8), rows=(3, 1 / 4, 4), speed=(26.0, 3.0, 62.0),
                  step_down=(8.0, 0.3, 11.0), fire_gap=(1.7, -0.07, 0.65),
                  bolt_speed=(105.0, 4.0, 165.0), max_bolts=(4, 0.5, 9))
FORMATION = dict(spacing_x=30, spacing_y=24, top=38, margin=12, speedup=0.7, aim_limit=38.0)


def _ramp(spec, wave):
    start, per_wave, limit = spec
    value = start + per_wave * (wave - 1)
    return max(value, limit) if per_wave < 0 else min(value, limit)


def difficulty_for(wave):
    """The (capped) Difficulty of a wave; waves beyond the first few just sit on the caps."""
    wave = max(1, int(wave))
    d = {k: _ramp(v, wave) for k, v in DIFFICULTY.items()}
    return Difficulty(int(d["columns"]), int(d["rows"]), d["speed"], d["step_down"], d["fire_gap"],
                      d["bolt_speed"], int(d["max_bolts"]))


def is_boss_wave(wave):
    return wave > 0 and wave % BOSS_EVERY == 0


def boss_index(wave):
    return max(0, wave // BOSS_EVERY - 1)


def enemy_kind(wave, row, rows):
    """Which enemy fills `row` (0 = top) of a formation: tanks lead, dashers sit behind them."""
    if wave >= TANK_FROM_WAVE and row == 0:
        return "tank"
    dash_rows = {1 if wave >= TANK_FROM_WAVE else 0}
    if wave >= DASH_FROM_WAVE + 6:
        dash_rows.add(max(dash_rows) + 1)
    return "dash" if wave >= DASH_FROM_WAVE and row in dash_rows and row < rows else "scout"


POWERUPS = dict(
    rapid=dict(weight=26, label="RAPID FIRE"),
    spread=dict(weight=22, label="SPREAD SHOT"),
    pierce=dict(weight=14, label="PIERCE"),
    shield=dict(weight=22, label="SHIELD"),
    repair=dict(weight=16, label="REPAIR"),
)
POWERUP = dict(drop_chance=0.07, min_gap=9.0, fall_speed=58.0, size=10, boss_drop=True)

# Tickets: modest next to the other machines (Cat Volleyball pays at most 20).
TICKETS = dict(per_wave_cleared=2, per_score=600, cap=40)
