"""Combat simulation: no display, input devices, audio, or save dependencies."""
import math
from dataclasses import dataclass, field
from .data import ROSTER, ENEMIES, ATTACKS, WAVES

def approach(value, target, amount):
    return min(value + amount, target) if value < target else max(value - amount, target)

@dataclass
class Swing:
    name: str
    age: float = 0
    victims: set = field(default_factory=set)

class Fighter:
    def __init__(self, name, x, y, health, speed, power=1, defense=1):
        self.name, self.x, self.y = name, float(x), float(y)
        self.max_health = self.health = health
        self.speed, self.power, self.defense = speed, power, defense
        self.vx = self.vy = self.push = 0.
        self.facing = 1
        self.state = 'idle'
        self.timer = self.invulnerable = self.jump = self.jump_age = 0.
        self.swing = None
        self.energy = 100.
        self.flash = 0.
        self.age = 0.

    @property
    def alive(self): return self.health > 0
    @property
    def ready(self): return self.alive and self.timer <= 0 and self.swing is None

    def attack(self, name):
        attack = ATTACKS[name]
        if not self.ready or self.energy < attack.cost: return False
        self.energy -= attack.cost
        self.swing = Swing(name)
        self.state = name
        return True

    def damage(self, amount, force, knockdown=False):
        if not self.alive or self.invulnerable > 0 or self.jump > 17: return 0
        dealt = max(1, round(amount / self.defense))
        self.health = max(0, self.health - dealt)
        self.swing = None
        self.push = force
        self.timer = .8 if knockdown else .26
        self.invulnerable = self.timer + .32
        self.state = 'defeated' if not self.alive else 'knockdown' if knockdown else 'hurt'
        self.flash = .14
        return dealt

    def tick(self, dt):
        self.age += dt
        for attr in ('timer', 'invulnerable', 'flash'):
            setattr(self, attr, max(0, getattr(self, attr)-dt))
        self.x += self.push * dt
        self.push = approach(self.push, 0, dt * 340)
        if self.jump_age:
            self.jump_age += dt
            self.jump = max(0, 115*self.jump_age - 180*self.jump_age**2)
            if self.jump_age > .65: self.jump_age = self.jump = 0
        if self.swing:
            self.swing.age += dt
            a = ATTACKS[self.swing.name]
            recovery = ROSTER[self.name].recovery if self.name in ROSTER else 1
            if self.swing.age >= a.windup + a.active + a.recovery * recovery:
                self.swing = None
        if self.ready: self.state = 'walk' if abs(self.vx)+abs(self.vy)>5 else 'idle'

class PlayerFighter(Fighter):
    def __init__(self, name='REX'):
        s = ROSTER[name]
        super().__init__(name, 80, 220, s.health, s.speed, s.power, s.defense)
        self.combo_step = 0
        self.combo_window = 0.
        self.dodge_cooldown = 0.

    def act(self, action):
        if action == 'light':
            if self.jump: return self.attack('air')
            step = (self.combo_step % 3) + 1 if self.combo_window > 0 else 1
            if self.attack(('light','combo2','combo3')[step-1]):
                self.combo_step, self.combo_window = step, .85
                return True
            return False
        if action in ('heavy','special'): return self.attack(action)
        if not self.ready: return False
        if action == 'jump' and not self.jump_age:
            self.jump_age = .001
            return True
        if action == 'dodge' and self.dodge_cooldown <= 0:
            self.timer, self.invulnerable, self.dodge_cooldown = .28, .30, .85
            self.push, self.state = self.facing*230, 'dodge'
            return True
        return False

    def move(self, dt, direction, bounds):
        dx, dy = direction
        length = max(1, math.hypot(dx,dy))
        factor = .28 if self.swing else 0 if self.timer else 1
        self.vx = approach(self.vx, dx/length*self.speed*factor, dt*800)
        self.vy = approach(self.vy, dy/length*self.speed*.66*factor, dt*800)
        if dx and not self.swing and not self.timer: self.facing = 1 if dx>0 else -1
        self.x = max(bounds[0], min(bounds[1], self.x+self.vx*dt))
        self.y = max(173, min(265, self.y+self.vy*dt))
        self.combo_window = max(0, self.combo_window-dt)
        self.dodge_cooldown = max(0, self.dodge_cooldown-dt)
        self.energy = min(100, self.energy+dt*3)

class EnemyFighter(Fighter):
    def __init__(self, name, x, y, index=0):
        health, speed, _ = ENEMIES[name]
        super().__init__(name,x,y,health,speed)
        self.index, self.phase = index, 1
        self.timer = .9 + index*.15
        self.state = 'idle'
        self.pattern = 0

    @property
    def boss(self): return self.name in ('WARDEN','RELAY','NULL')

    def think(self, dt, player, can_attack):
        if not self.ready: return
        if self.boss and self.health <= self.max_health*.5 and self.phase == 1:
            self.phase = 2
            self.invulnerable = self.timer = 1.1
            self.state = 'phase'
            return
        dx, dy = player.x-self.x, player.y-self.y
        self.facing = 1 if dx>0 else -1
        distance = 175 if self.name == 'ranged' else 36 if not self.boss else 49
        if abs(dy) < 13 and abs(dx) <= distance and can_attack:
            name = 'shot' if self.name == 'ranged' else 'smash' if self.name == 'bruiser' or self.boss else 'enemy'
            if self.boss:
                self.pattern += 1
                if self.phase == 2 and self.pattern % 2: name = 'sweep'
                elif self.name in ('RELAY','NULL') and self.pattern % 3 == 0: name = 'shot'
            self.attack(name)
            return
        # Alternate flanks and lane offsets distribute waiting attackers.
        flank = 1 if self.index % 2 else -1
        target_x = player.x + flank*(distance*.8 if can_attack else 80)
        target_y = player.y + (0 if can_attack else (self.index%3-1)*24)
        self.x += max(-1,min(1,(target_x-self.x)/12))*self.speed*dt
        self.y += max(-1,min(1,(target_y-self.y)/12))*self.speed*.65*dt
        self.y = max(175,min(263,self.y))
        self.state = 'approach' if can_attack else 'positioning'

class CombatSystem:
    @staticmethod
    def resolve(attacker, targets):
        swing = attacker.swing
        if not swing: return []
        a = ATTACKS[swing.name]
        if not a.windup <= swing.age <= a.windup+a.active: return []
        hits = []
        for target in targets:
            if target in swing.victims or not target.alive: continue
            dx = target.x-attacker.x
            radial = swing.name in ('special','sweep')
            if abs(target.y-attacker.y)>17 or abs(dx)>a.reach+10: continue
            if not radial and dx*attacker.facing < -8: continue
            swing.victims.add(target)
            dealt = target.damage(a.damage*attacker.power, (1 if dx>=0 else -1)*a.knockback*attacker.power, a.knockdown)
            if dealt: hits.append((target,dealt))
        return hits

class Campaign:
    def __init__(self, character='REX'):
        self.player = PlayerFighter(character)
        self.stage = self.wave = 0
        self.enemies = []
        self.spawned = False
        self.score = self.kills = self.damage_received = self.combo = self.best_combo = 0
        self.combo_time = self.elapsed = self.hitstop = 0.
        self.state = 'playing'
        self.effects = []
        self.pickups = []
        self.events = []
        self.camera = 0.

    @property
    def bounds(self): return (self.wave*350+18, self.wave*350+382)
    @property
    def tickets(self): return min(150, self.score//180 + self.stage*8 + (40 if self.state=='victory' else 0))

    def spawn(self):
        self.enemies = [EnemyFighter(name,self.wave*350+240+(i%3)*36,185+(i%4)*22,i)
                        for i,name in enumerate(WAVES[self.stage][self.wave])]
        self.spawned = True
        self.events.append('wave')

    def update(self, dt, direction=(0,0)):
        if self.state != 'playing': return
        dt = max(0,min(dt,.05))
        self.elapsed += dt
        self.events.clear()
        self.effects = [(x,y,t-dt) for x,y,t in self.effects if t>dt]
        if self.hitstop>0:
            self.hitstop -= dt
            return
        if not self.spawned: self.spawn()
        p = self.player
        p.tick(dt)
        p.move(dt,direction,self.bounds)
        self.combo_time = max(0,self.combo_time-dt)
        if not self.combo_time: self.combo = 0
        active = sum(e.swing is not None for e in self.enemies)
        candidates = sorted((e for e in self.enemies if e.alive),key=lambda e:abs(e.x-p.x)+abs(e.y-p.y)*2)
        permitted = set(candidates[:2])
        for e in self.enemies:
            e.tick(dt)
            e.think(dt,p,e in permitted and active<2)
            if e.swing: active += 1
            e.x = max(self.bounds[0],min(self.bounds[1],e.x))
        # Soft separation leaves escape routes rather than trapping the player.
        for i,e in enumerate(candidates):
            for other in candidates[i+1:]:
                if abs(e.x-other.x)<19 and abs(e.y-other.y)<12:
                    e.x -= 12*dt
                    other.x += 12*dt
        for target, damage in CombatSystem.resolve(p,self.enemies):
            self.score += damage*5
            self.combo += 1
            self.best_combo = max(self.best_combo,self.combo)
            self.combo_time = 2
            p.energy = min(100,p.energy+4)
            self.impact(target)
            if not target.alive:
                self.kills += 1
                self.score += 150 if not target.boss else 1200
                self.events.append('defeat')
        for e in self.enemies:
            for target, damage in CombatSystem.resolve(e,[p]):
                self.damage_received += damage
                self.impact(target)
                self.events.append('hurt')
        if not p.alive:
            self.state = 'defeat'
            self.events.append('lose')
        elif self.spawned and all(not e.alive for e in self.enemies):
            self.pickups = [(self.wave*350+300,220)]
            self.state = 'checkpoint' if self.wave<3 else 'stage_clear'
            self.score += 300
            self.events.append('clear')
        target = max(0,min(1050,p.x-150))
        self.camera += (target-self.camera)*min(1,dt*6)

    def impact(self, target):
        self.effects.append((target.x,target.y-23,.20))
        self.hitstop = .045
        self.events.append('hit')

    def pickup(self):
        for item in self.pickups[:]:
            if abs(self.player.x-item[0])<35 and abs(self.player.y-item[1])<25:
                self.player.health = min(self.player.max_health,self.player.health+30)
                self.pickups.remove(item)
                self.events.append('pickup')

    def advance(self):
        if self.state not in ('checkpoint','stage_clear'): return
        # Checkpoint aid is guaranteed, even if the player skips the food pickup.
        self.player.health = min(self.player.max_health,self.player.health+22)
        self.player.energy = min(100,self.player.energy+20)
        if self.wave == 3:
            if self.stage == 2:
                self.state = 'victory'
                return
            self.stage += 1
            self.wave = 0
            self.player.x, self.camera = 80,0
        else:
            self.wave += 1
            self.player.x = self.wave*350+45
        self.player.y = 220
        self.player.swing = None
        self.player.timer = 0
        self.player.invulnerable = 1
        self.pickups.clear()
        self.spawned = False
        self.state = 'playing'
