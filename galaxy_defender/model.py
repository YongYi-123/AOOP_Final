"""Starfall Assault rules: one endless run. No pygame, no drawing, no keyboard; the caller feeds
(move, fire) and reads back the state plus a list of events for sound and effects."""
import math
import random
from dataclasses import dataclass, field

from . import config as cfg
from .settlement import RunResult


def overlap(a, b):
    """Do two (x, y, w, h) boxes, given by centre, touch?"""
    return abs(a[0] - b[0]) * 2 < a[2] + b[2] and abs(a[1] - b[1]) * 2 < a[3] + b[3]


@dataclass
class Bolt:
    x: float
    y: float
    vx: float
    vy: float
    hostile: bool = False
    w: int = 4
    h: int = 9
    pierce: bool = False
    hit: set = field(default_factory=set)      # ids of targets a piercing bolt has already damaged

    @property
    def box(self):
        return (self.x, self.y, self.w, self.h)


@dataclass
class Enemy:
    kind: str
    col: int
    row: int
    hp: int
    max_hp: int
    x: float = 0.0
    y: float = 0.0
    flash: float = 0.0
    carrier: bool = False                  # a Cargo Drone: always drops a power-up when destroyed

    @property
    def spec(self):
        return cfg.ENEMIES[self.kind]

    @property
    def box(self):
        return (self.x, self.y, self.spec["width"], self.spec["height"])


@dataclass
class Boss:
    hp: int
    max_hp: int
    x: float = cfg.FIELD_W / 2
    y: float = cfg.BOSS["y"]
    direction: int = 1
    speed: float = 48.0
    pattern: str = "spread"
    pattern_time: float = 0.0
    fire_timer: float = 1.2
    burst_left: int = 0
    burst_timer: float = 0.0
    volley: int = 0
    flash: float = 0.0

    @property
    def box(self):
        return (self.x, self.y, cfg.BOSS["width"], cfg.BOSS["height"])

    @property
    def enraged(self):
        return self.hp <= self.max_hp * cfg.BOSS["enraged_below"]


@dataclass
class PowerUp:
    kind: str
    x: float
    y: float

    @property
    def box(self):
        return (self.x, self.y, cfg.POWERUP["size"], cfg.POWERUP["size"])


@dataclass
class Event:
    name: str
    x: float = 0.0
    y: float = 0.0
    big: bool = False
    kind: str = ""


class Run:
    """The state of one run from wave 1 until Game Over."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.x = cfg.FIELD_W / 2
        self.hp = cfg.MAX_HP
        self.shield = False
        self.power = {name: 0.0 for name in cfg.POWER_SECONDS}      # seconds left of rapid / spread / pierce
        self.combo = 0
        self.combo_time = 0.0
        self.best_combo = 0
        self.invuln = 0.0
        self.cooldown = 0.0
        self.score = 0
        self.wave = 1                  # the wave being played, or about to start
        self.reached = 1               # the highest wave that has started (the banner counts)
        self.waves_cleared = 0
        self.kills = 0
        self.time = 0.0
        self.over = False
        self.over_reason = None        # "hp" or "breach"
        self.banner = cfg.WAVE_BANNER_SECONDS     # > 0: counting down to the next wave
        self.player_bolts, self.enemy_bolts = [], []
        self.enemies, self.powerups = [], []
        self.boss = None
        self.events = []
        self._formation = dict(x=0.0, y=0.0, dir=1)
        self._total = 1
        self._fire_timer = 1.5
        self._last_drop = -99.0
        self.diff = cfg.difficulty_for(1)

    # ------------------------------------------------------------ queries
    @property
    def banner_active(self):
        return self.banner > 0

    @property
    def firing_gap(self):
        return cfg.PLAYER["rapid_cooldown"] if self.power["rapid"] > 0 else cfg.PLAYER["cooldown"]

    @property
    def multiplier(self):
        c = cfg.COMBO
        return min(c["max_mult"], 1.0 + c["bonus"] * (self.combo // c["step"]))

    @property
    def player_box(self):
        return (self.x, cfg.PLAYER_Y, cfg.PLAYER["width"] - 6, cfg.PLAYER["height"] - 2)

    @property
    def is_boss_wave(self):
        return cfg.is_boss_wave(self.wave)

    def result(self):
        return RunResult.of(self.score, self.reached, self.waves_cleared)

    def take_events(self):
        events, self.events = self.events, []
        return events

    def _emit(self, name, x=0.0, y=0.0, big=False, kind=""):
        self.events.append(Event(name, x, y, big, kind))

    # ------------------------------------------------------------ update
    def update(self, dt, move=0, fire=False):
        if self.over:
            return
        dt = min(dt, 0.05)                      # a long hitch never lets bolts tunnel or enemies teleport
        self.time += dt
        self.cooldown = max(0.0, self.cooldown - dt)
        self.invuln = max(0.0, self.invuln - dt)
        for name in self.power:
            self.power[name] = max(0.0, self.power[name] - dt)
        if self.combo_time > 0:
            self.combo_time -= dt
            if self.combo_time <= 0:
                self.combo = 0
        half = cfg.PLAYER["width"] / 2
        self.x = min(cfg.FIELD_W - half, max(half, self.x + max(-1, min(1, move)) * cfg.PLAYER["speed"] * dt))
        if fire:
            self.shoot()
        if self.banner > 0:
            self.banner -= dt
            if self.banner <= 0:
                self.banner = 0.0
                self._start_wave()
        else:
            self._move_enemies(dt)
        for e in self.enemies:
            e.flash = max(0.0, e.flash - dt)
        if self.boss:
            self.boss.flash = max(0.0, self.boss.flash - dt)
        self._move_bolts(dt)
        self._hit_enemies()
        self._hit_player()
        self._move_powerups(dt)
        if self.over:
            return
        if self.banner <= 0 and not self.enemies and not self.boss:
            self._clear_wave()
        elif any(e.y + e.spec["height"] / 2 >= cfg.DEFENSE_LINE for e in self.enemies):
            self._end("breach")

    def shoot(self):
        """Fire if the cooldown allows it. Returns whether a laser left the ship."""
        spread = self.power["spread"] > 0
        cap = cfg.PLAYER["max_bullets"] + (cfg.PLAYER["spread_bullet_bonus"] if spread else 0)
        if self.over or self.cooldown > 0 or len(self.player_bolts) >= cap:
            return False
        speed, pierce = cfg.PLAYER["bullet_speed"], self.power["pierce"] > 0
        for tilt in ((-1, 0, 1) if spread else (0,)):
            angle = math.radians(cfg.PLAYER["spread_angle"] * tilt)
            self.player_bolts.append(Bolt(self.x, cfg.PLAYER_Y - 10, math.sin(angle) * speed,
                                          -math.cos(angle) * speed, w=3, h=10, pierce=pierce))
        self.cooldown = self.firing_gap
        self._emit("shoot", self.x, cfg.PLAYER_Y - 10, kind="pierce" if pierce else "")
        return True

    # ------------------------------------------------------------ waves
    def _start_wave(self):
        self.diff = cfg.difficulty_for(self.wave)
        self.reached = max(self.reached, self.wave)
        self.enemy_bolts.clear()
        if self.is_boss_wave:
            index = cfg.boss_index(self.wave)
            b = cfg.BOSS
            hp = min(b["max_hp"], b["base_hp"] + b["hp_per_boss"] * index)
            self.boss = Boss(hp, hp, speed=min(b["max_speed"], b["base_speed"] + b["speed_per_boss"] * index))
            self._emit("boss_arrive", self.boss.x, self.boss.y, True)
            return
        d = self.diff
        sx, sy = cfg.FORMATION["spacing_x"], cfg.FORMATION["spacing_y"]
        self.enemies = []
        for row in range(d.rows):
            kind = cfg.enemy_kind(self.wave, row, d.rows)
            hp = cfg.ENEMIES[kind]["hp"]
            for col in range(d.columns):
                self.enemies.append(Enemy(kind, col, row, hp, hp))
        if self.wave >= cfg.CARGO_FROM_WAVE:
            count = min(cfg.CARGO_MAX, 1 + (self.wave - cfg.CARGO_FROM_WAVE) // cfg.CARGO_PER_WAVES)
            for e in self.rng.sample(self.enemies, count):
                e.carrier = True
        width = (d.columns - 1) * sx
        self._formation = dict(x=(cfg.FIELD_W - width) / 2, y=float(cfg.FORMATION["top"]), dir=1)
        self._total = len(self.enemies)
        self._fire_timer = d.fire_gap
        self._place_enemies(0.0)

    def _place_enemies(self, time):
        f, sx, sy = self._formation, cfg.FORMATION["spacing_x"], cfg.FORMATION["spacing_y"]
        for e in self.enemies:
            wobble = math.sin(time * 6 + e.col) * e.spec.get("wobble", 0.0)
            e.x = f["x"] + e.col * sx + wobble
            e.y = f["y"] + e.row * sy

    def _clear_wave(self):
        bonus = min(cfg.SCORES["wave_clear_max"], cfg.SCORES["wave_clear_per_wave"] * self.wave)
        self.score += bonus
        self.waves_cleared += 1
        self.wave += 1
        self.banner = cfg.WAVE_BANNER_SECONDS
        self.enemy_bolts.clear()
        self._emit("wave_clear", cfg.FIELD_W / 2, cfg.FIELD_H / 2, True)

    def _end(self, reason):
        self.over, self.over_reason = True, reason
        self._emit("game_over", self.x, cfg.PLAYER_Y, True)

    # ------------------------------------------------------------ enemies
    def _move_enemies(self, dt):
        if self.boss:
            self._move_boss(dt)
            return
        if not self.enemies:
            return
        f, d, margin = self._formation, self.diff, cfg.FORMATION["margin"]
        sx = cfg.FORMATION["spacing_x"]
        cols = [e.col for e in self.enemies]
        widest = max(e.spec["width"] for e in self.enemies) / 2 + 4      # room for wobble
        left, right = f["x"] + min(cols) * sx - widest, f["x"] + max(cols) * sx + widest
        speed = d.speed * (1 + cfg.FORMATION["speedup"] * (1 - len(self.enemies) / self._total))
        f["x"] += f["dir"] * speed * dt
        shift = 0.0
        if f["dir"] > 0 and right + f["dir"] * speed * dt >= cfg.FIELD_W - margin:
            shift = (cfg.FIELD_W - margin) - (right + f["dir"] * speed * dt)
        elif f["dir"] < 0 and left + f["dir"] * speed * dt <= margin:
            shift = margin - (left + f["dir"] * speed * dt)
        if shift:
            f["x"] += shift
            f["dir"] = -f["dir"]
            f["y"] += d.step_down
            self._emit("formation_turn")
        self._place_enemies(self.time)
        self._fire_timer -= dt
        if self._fire_timer <= 0:
            self._fire_timer = d.fire_gap * self.rng.uniform(0.75, 1.3)
            self._enemy_volley()

    def _enemy_volley(self):
        if len(self.enemy_bolts) >= self.diff.max_bolts:
            return
        shooters = {}
        for e in self.enemies:                       # only the front enemy of each column can fire
            if e.col not in shooters or e.row > shooters[e.col].row:
                shooters[e.col] = e
        pool = list(shooters.values())
        shooter = self.rng.choices(pool, weights=[e.spec["fire"] for e in pool])[0]
        speed = self.diff.bolt_speed * shooter.spec["bolt"]
        vx = max(-cfg.FORMATION["aim_limit"], min(cfg.FORMATION["aim_limit"], (self.x - shooter.x) * 0.4))
        self.enemy_bolts.append(Bolt(shooter.x, shooter.y + 8, vx, speed, hostile=True))
        self._emit("enemy_shoot", shooter.x, shooter.y)

    def _move_boss(self, dt):
        b, spec = self.boss, cfg.BOSS
        half = spec["width"] / 2 + 14
        b.x += b.direction * b.speed * (1.35 if b.enraged else 1.0) * dt
        if b.x > cfg.FIELD_W - half:
            b.x, b.direction = cfg.FIELD_W - half, -1
        elif b.x < half:
            b.x, b.direction = half, 1
        b.pattern_time += dt
        if b.pattern_time >= spec["switch_seconds"]:
            b.pattern_time = 0.0
            b.pattern = "aimed" if b.pattern == "spread" else "spread"
            b.fire_timer = max(b.fire_timer, 0.9)
        b.fire_timer -= dt
        if b.burst_left > 0:
            b.burst_timer -= dt
            if b.burst_timer <= 0:
                b.burst_left -= 1
                b.burst_timer = 0.2
                self._boss_bolt(b.x, b.y + 22, self.x, 150.0)
        elif b.fire_timer <= 0:
            rage = 0.75 if b.enraged else 1.0
            if b.pattern == "spread":
                b.fire_timer = spec["spread_gap"] * rage
                angles = (-24, -8, 8, 24) if b.volley % 2 == 0 else (-32, -16, 0, 16, 32)
                b.volley += 1
                for deg in angles:
                    rad = math.radians(deg)
                    self.enemy_bolts.append(Bolt(b.x, b.y + 22, math.sin(rad) * 120, math.cos(rad) * 120,
                                                 hostile=True, w=5, h=9))
                self._emit("enemy_shoot", b.x, b.y)
            else:
                b.fire_timer = spec["aimed_gap"] * rage
                b.burst_left, b.burst_timer = 3, 0.0

    def _boss_bolt(self, x, y, tx, speed):
        dx, dy = tx - x, cfg.PLAYER_Y - y
        dist = math.hypot(dx, dy) or 1.0
        self.enemy_bolts.append(Bolt(x, y, dx / dist * speed, dy / dist * speed, hostile=True, w=5, h=9))
        self._emit("enemy_shoot", x, y)

    # ------------------------------------------------------------ bolts and collisions
    def _move_bolts(self, dt):
        for bolt in self.player_bolts + self.enemy_bolts:
            bolt.x += bolt.vx * dt
            bolt.y += bolt.vy * dt
        self.player_bolts = [b for b in self.player_bolts if b.y > -12 and -12 < b.x < cfg.FIELD_W + 12]
        self.enemy_bolts = [b for b in self.enemy_bolts if -12 < b.x < cfg.FIELD_W + 12 and b.y < cfg.FIELD_H + 12]

    def _hit_enemies(self):
        for bolt in list(self.player_bolts):
            targets = [t for t in ([self.boss] if self.boss else []) + self.enemies
                       if id(t) not in bolt.hit and overlap(bolt.box, t.box)]
            if not targets:
                continue
            for target in (targets if bolt.pierce else targets[:1]):
                bolt.hit.add(id(target))
                target.hp -= 1
                target.flash = 0.09
                self._emit("enemy_hit", bolt.x, bolt.y, kind="pierce" if bolt.pierce else "")
                if target.hp > 0:
                    continue
                if target is self.boss:
                    self._boss_down()
                else:
                    self._enemy_down(target)
            if not bolt.pierce:
                self.player_bolts.remove(bolt)

    def _award(self, base):
        """Add `base` points times the current chain multiplier and extend the chain."""
        c = cfg.COMBO
        self.combo += 1
        self.combo_time = c["window"]
        self.best_combo = max(self.best_combo, self.combo)
        self.score += int(base * self.multiplier + 0.5)
        if self.combo % c["announce_every"] == 0:
            self._emit("combo", self.x, cfg.PLAYER_Y - 24, kind=str(self.combo))

    def _enemy_down(self, enemy):
        self.enemies.remove(enemy)
        self.kills += 1
        self._award(enemy.spec["score"])
        self._emit("enemy_down", enemy.x, enemy.y, kind=enemy.kind)
        d = cfg.POWERUP
        if enemy.carrier:
            self._drop(enemy.x, enemy.y)
        elif self.time - self._last_drop >= d["min_gap"] and self.rng.random() < d["drop_chance"]:
            self._drop(enemy.x, enemy.y)

    def _boss_down(self):
        boss, spec = self.boss, cfg.BOSS
        self.boss = None
        self.kills += 1
        self.score += spec["score"] + spec["score_per_boss"] * cfg.boss_index(self.wave)
        self.enemy_bolts.clear()
        self._emit("boss_down", boss.x, boss.y, True)
        if cfg.POWERUP["boss_drop"]:
            self._drop(boss.x, boss.y)

    def _drop(self, x, y):
        kinds = [k for k in cfg.POWERUPS
                 if not (k == "repair" and self.hp >= cfg.MAX_HP) and not (k == "shield" and self.shield)]
        if not kinds:
            return
        kind = self.rng.choices(kinds, weights=[cfg.POWERUPS[k]["weight"] for k in kinds])[0]
        self.powerups.append(PowerUp(kind, x, y))
        self._last_drop = self.time

    def _hit_player(self):
        for bolt in list(self.enemy_bolts):
            if overlap(bolt.box, self.player_box):
                if self.invuln > 0:
                    continue                      # flying through a ghosted ship is harmless
                self.enemy_bolts.remove(bolt)
                self.damage()

    def damage(self):
        """One incoming hit. Returns what happened: 'ignored', 'shield' or 'hp'."""
        if self.over or self.invuln > 0:
            return "ignored"
        if self.shield:
            self.shield = False
            self.invuln = cfg.PLAYER["shield_grace"]
            self._emit("shield_break", self.x, cfg.PLAYER_Y)
            return "shield"
        self.hp -= 1
        self.combo, self.combo_time = 0, 0.0
        self.invuln = cfg.PLAYER["invulnerable"]
        self._emit("player_hit", self.x, cfg.PLAYER_Y, True)
        if self.hp <= 0:
            self.hp = 0
            self._end("hp")
        return "hp"

    # ------------------------------------------------------------ power-ups
    def _move_powerups(self, dt):
        kept = []
        for p in self.powerups:
            p.y += cfg.POWERUP["fall_speed"] * dt
            if overlap(p.box, (self.x, cfg.PLAYER_Y, cfg.PLAYER["width"], cfg.PLAYER["height"])):
                self.collect(p.kind)
                self._emit("pickup", p.x, p.y, kind=p.kind)
            elif p.y < cfg.FIELD_H + 10:
                kept.append(p)
        self.powerups = kept

    def collect(self, kind):
        if kind in self.power:
            self.power[kind] = cfg.POWER_SECONDS[kind]     # refreshed, never stacked
        elif kind == "shield":
            self.shield = True
        elif kind == "repair":
            self.hp = min(cfg.MAX_HP, self.hp + 1)
