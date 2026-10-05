"""AI difficulty levels: plain configuration objects the AI drivers read. NORMAL is the baseline (all 1.0 / 0)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Difficulty:
    key: str
    name: str
    skill: tuple = (0.3, 1.0)          # range each racer's skill is drawn from
    aggression: tuple = (0.2, 0.9)     # range for how early racers go for a pass
    speed: float = 1.0                 # x the share of top speed the AI dares to use
    pace: tuple = (0.90, 0.09)         # (base, spread): top-speed share = base + spread * skill
    cornering: tuple = (0.85, 0.18)    # (base, spread): cornering margin = base + spread * skill
    mistakes: float = 1.0              # x wobble / lapses of attention
    corner_margin: float = 0.0         # added to the cornering margin (bigger = takes bends faster)
    catch_up: float = 1.0              # x rubber-band strength when far behind the player
    item_delay: float = 1.0            # x how long an AI waits (and dithers) before using a held item
    item_waste: float = 0.0            # chance-per-check scale of firing an item at a pointless moment


EASY = Difficulty("easy", "EASY", skill=(0.1, 0.6), aggression=(0.1, 0.5), speed=0.90, mistakes=1.6,
                  corner_margin=-0.08, catch_up=0.4, item_delay=1.6, item_waste=0.5)
# NORMAL / HARD were tuned against three simulated players (perfect autopilot, competent human, casual human)
# so that a wider spread of AI skill puts quick racers at the front without punishing ordinary driving.
NORMAL = Difficulty("normal", "NORMAL", pace=(0.84, 0.17), cornering=(0.74, 0.32), item_waste=0.12)
HARD = Difficulty("hard", "HARD", skill=(0.6, 1.0), aggression=(0.5, 1.0), speed=1.02, mistakes=0.4,
                  pace=(0.86, 0.17), cornering=(0.78, 0.30), corner_margin=0.05, catch_up=1.2, item_delay=0.6)

DIFFICULTIES = [EASY, NORMAL, HARD]
DEFAULT_DIFFICULTY = NORMAL
