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
    shape: str = "forward"
    lane: int = 17
    mobility: float = 0

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
# Difficulty changes damage and tactics; original HP and player controls are preserved.
ENEMY_DAMAGE = (1.0, 1.25, 1.5)
BOSS_DAMAGE = (1.0, 1.4, 1.7)
BOSS_PATTERNS = {
    'WARDEN': (('charge','slam','barrage'), ('slam','charge','wave','barrage')),
    'RELAY': (('dash','pulse','guard','orb'), ('dash','strike','guard','summon','pulse')),
    'NULL': (('orb','barrage','wave','teleport'),
             ('laser','strike','teleport','summon','barrage'),
             ('strike','laser','wave','teleport','orb')),
}
ENEMIES.update({
    'duelist': (37, 82, (190,90,100)),
    'shield': (88, 35, (85,135,155)),
    'elite': (58, 63, (135,85,165)),
    'cyber': (50, 79, (95,190,205)),
    'security': (100, 31, (115,145,175)),
    'sniper': (40, 48, (165,100,175)),
    'assassin': (34, 108, (100,90,160)),
    'echo': (16, 70, (145,145,245)),
})
ATTACKS.update({
    'double': Attack(12, 40, .46, .22, .70, 65),
    'bash': Attack(15, 44, .65, .15, .95, 100, True),
    'lunge': Attack(12, 43, .65, .20, .85, 85, mobility=175),
    'snipe': Attack(13, 280, .95, .10, 1.15, 70),
    'charge': Attack(17, 45, .85, .24, 1.15, 115, True, mobility=190),
    'slam': Attack(18, 65, .95, .16, 1.15, 110, True, shape='radial', lane=25),
    'barrage': Attack(15, 56, .60, .32, .95, 75),
    'wave': Attack(14, 210, .90, .16, 1.10, 90, shape='radial', lane=12),
    'dash': Attack(13, 43, .75, .22, 1.0, 95, mobility=220),
    'pulse': Attack(14, 77, .90, .18, 1.0, 85, shape='radial', lane=28),
    'orb': Attack(12, 245, .85, .12, 1.0, 70),
    'laser': Attack(14, 290, 1.0, .20, 1.05, 80, lane=13),
    'strike': Attack(15, 38, 1.10, .18, 1.0, 100, True, shape='target', lane=23),
})
STAGE_POOLS = (
    frozenset(('grunt','runner','bruiser','WARDEN')),
    frozenset(('grunt','runner','duelist','shield','ranged','elite','RELAY')),
    frozenset(('elite','cyber','security','sniper','assassin','NULL')),
)
# 70 opponents across twelve encounters. New mechanics appear before mixed squads.
WAVES = (
    (('grunt',)*6,
     ('grunt','runner','grunt','runner','runner','grunt','runner','grunt'),
     ('bruiser','grunt','runner','bruiser','grunt','runner'), ('WARDEN',)),
    (('duelist','grunt','runner','duelist','grunt','ranged','runner','ranged'),
     ('shield','duelist','ranged','elite','grunt','shield','duelist','ranged'),
     ('elite','shield','ranged','duelist','elite','ranged'), ('RELAY','duelist')),
    (('cyber','elite','assassin','cyber','elite','sniper','assassin','elite'),
     ('security','sniper','cyber','assassin','elite','security','sniper','cyber'),
     ('security','assassin','sniper','elite','cyber','security','assassin','sniper'), ('NULL',)),
)
SECTIONS = (
    ('LANTERN ALLEY','NIGHT MARKET','RAIN DISTRICT','KINGS CROSSING'),
    ('STATION ENTRANCE','EMPTY PLATFORM','SERVICE TUNNEL','CONTROL ROOM'),
    ('SECURITY GATE','UNDERGROUND LAB','DATA CONDUIT','OVERLORD CHAMBER'),
)
