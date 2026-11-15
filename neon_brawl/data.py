"""Central balance and campaign definitions (world units are pixels)."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Stats:
    health: int
    speed: float
    power: float
    defense: float
    recovery: float
    color: tuple
    description: str

ROSTER = {
    'REX': Stats(140, 100, 1, 1, 1, (245, 80, 130), 'Street boxer / balanced combos'),
    'NOVA': Stats(112, 133, .83, .9, .75, (65, 230, 240), 'Signal courier / fast recovery'),
    'BRUNO': Stats(185, 78, 1.4, 1.25, 1.17, (255, 185, 65), 'Station mechanic / crushing force'),
}
@dataclass(frozen=True)
class Attack:
    damage: int
    reach: int
    windup: float
    active: float
    recovery: float
    knockback: float
    knockdown: bool = False
    cost: int = 0

ATTACKS = {
    'light': Attack(12, 39, .07, .10, .14, 45),
    'combo2': Attack(15, 43, .08, .11, .15, 60),
    'combo3': Attack(23, 49, .12, .12, .23, 140, True),
    'heavy': Attack(30, 52, .27, .14, .28, 165, True),
    'air': Attack(19, 46, .06, .22, .17, 95),
    'special': Attack(39, 84, .10, .20, .38, 200, True, 40),
    'enemy': Attack(10, 32, .40, .12, .65, 60),
    'smash': Attack(24, 65, .75, .16, .85, 140, True),
    'shot': Attack(9, 240, .65, .10, 1.1, 50),
    'sweep': Attack(19, 100, .85, .18, .9, 130, True),
}
ENEMIES = {
    'grunt': (42, 47, (155, 90, 220)),
    'runner': (29, 83, (85, 220, 145)),
    'bruiser': (92, 32, (230, 105, 65)),
    'ranged': (35, 44, (90, 160, 235)),
    'WARDEN': (270, 44, (235, 150, 65)),
    'RELAY': (330, 61, (70, 225, 220)),
    'NULL': (620, 58, (235, 65, 180)),
}
STAGES = (
    ('NEON ALLEY', (200, 60, 150), 'WARDEN'),
    ('ABANDONED STATION', (55, 170, 210), 'RELAY'),
    ('SIGNAL CORE', (145, 70, 240), 'NULL'),
)
# Four locked encounters per scrolling stage; the last is a boss arena.
WAVES = (
    (('grunt',)*3, ('grunt','runner','grunt','runner'), ('bruiser','grunt','ranged'), ('WARDEN',)),
    (('runner','grunt','ranged','grunt'), ('bruiser','runner','ranged','runner'), ('bruiser','bruiser','ranged'), ('RELAY','runner')),
    (('bruiser','runner','ranged','grunt'), ('bruiser','ranged','runner','runner'), ('bruiser','bruiser','ranged','ranged'), ('NULL',)),
)
