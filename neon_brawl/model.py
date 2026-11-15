"""Combat simulation: no display, input devices, audio, or save dependencies."""
import math
from dataclasses import dataclass, field
from .data import ROSTER, ENEMIES, ATTACKS, WAVES, ENEMY_DAMAGE, BOSS_DAMAGE
from .ai import BossBrain
from .ambient import AmbientCats

def approach(value, target, amount):
    return min(value + amount, target) if value < target else max(value - amount, target)

@dataclass
class Swing:
    name: str
    age: float = 0
    victims: set = field(default_factory=set)
    origin: tuple = (0, 0)
    target: tuple = (0, 0)
    direction: int = 1

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
        self.defeat_age = 0.
        self.attack_recovery = 1.

    @property
    def alive(self): return self.health > 0
    @property
    def ready(self): return self.alive and self.timer <= 0 and self.swing is None

    def attack(self, name):
        attack = ATTACKS[name]
        if not self.ready or self.energy < attack.cost: return False
        self.energy -= attack.cost
        self.swing = Swing(name, origin=(self.x,self.y), target=(self.x,self.y), direction=self.facing)
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
        if not self.alive: self.defeat_age += dt
        for attr in ('timer', 'invulnerable', 'flash'):
            setattr(self, attr, max(0, getattr(self, attr)-dt))
        self.x += self.push * dt
        self.push = approach(self.push, 0, dt * 340)
        if self.jump_age:
            self.jump_age += dt
            self.jump = max(0, 115*self.jump_age - 180*self.jump_age**2)
            if self.jump_age > .65: self.jump_age = self.jump = 0
        if self.swing:
            previous_age=self.swing.age
            self.swing.age += dt
            a = ATTACKS[self.swing.name]
            recovery = ROSTER[self.name].recovery if self.name in ROSTER else self.attack_recovery
            motion_time=max(0.,min(self.swing.age,a.windup+a.active)-max(previous_age,a.windup))
            if a.mobility:
                self.x += self.swing.direction*a.mobility*motion_time
            if self.swing.age > a.windup+a.active: self.state = 'recovery'
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
    def __init__(self, name, x, y, index=0, stage=0):
        health, speed, _ = ENEMIES[name]
        health = round(health * (1.5 if name.islower() else 1.35))
        power=(BOSS_DAMAGE if name in ('WARDEN','RELAY','NULL') else ENEMY_DAMAGE)[stage]
        super().__init__(name,x,y,health,speed,power)
        self.index, self.phase, self.outfit, self.stage = index, 1, index+stage, stage
        self.timer = 1.3 if self.boss else .9+index*.12
        self.state = 'intro' if self.boss else 'idle'
        if self.boss: self.invulnerable=self.timer
        self.pattern = 0
        self.brain=BossBrain() if self.boss else None
        self.destination=None
        self.teleport_pending=False
        self.summon_request=False
        self.support_count=0
        self.guard_clock=0.

    @property
    def boss(self): return self.name in ('WARDEN','RELAY','NULL')

    def tick(self,dt):
        super().tick(dt)
        self.guard_clock=max(0,self.guard_clock-dt)
        if self.teleport_pending and self.timer<=0:
            if self.alive:
                self.x,self.y=self.destination
                self.timer=.55
                self.state='recovery'
            self.teleport_pending=False

    def damage(self,amount,force,knockdown=False):
        # Heavy blows break a shield; guard otherwise reduces, never nullifies damage.
        if self.state=='guard' and not knockdown: amount*=.35
        return super().damage(amount,force,knockdown)

    def begin(self,name,player):
        if self.attack(name):
            self.swing.target=(player.x,player.y)
            if self.name=='NULL' and self.phase>=2: self.attack_recovery=.85
            return True
        return False

    def think(self, dt, player, can_attack):
        if not self.ready: return
        if self.brain:
            self.brain.think(self,dt,player,can_attack)
            return
        dx,dy=player.x-self.x,player.y-self.y
        self.facing=1 if dx>0 else -1
        distance=205 if self.name=='sniper' else 175 if self.name in ('ranged','echo') else 75 if self.name=='assassin' else 36
        if abs(dy)<13 and abs(dx)<=distance and can_attack:
            self.pattern+=1
            if self.name in ('shield','security') and self.guard_clock<=0:
                self.state='guard'; self.timer=.65; self.guard_clock=3.5
                return
            attack={'ranged':'shot','echo':'shot','sniper':'snipe','bruiser':'smash',
                    'shield':'bash','security':'bash','duelist':'double','cyber':'pulse',
                    'assassin':'lunge','elite':'double'}.get(self.name,'enemy')
            self.begin(attack,player)
            return
        self.position(dt,player,can_attack,distance)

    def position(self,dt,player,can_attack,distance):
        self.facing=1 if player.x>self.x else -1
        flank=1 if self.index%2 else -1
        target_x=player.x+flank*(distance*.8 if can_attack else 80)
        target_y=player.y+(0 if can_attack else (self.index%3-1)*24)
        self.x+=max(-1,min(1,(target_x-self.x)/12))*self.speed*dt
        self.y+=max(-1,min(1,(target_y-self.y)/12))*self.speed*.65*dt
        self.y=max(175,min(263,self.y))
        self.state='approach' if can_attack else 'positioning'

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
            radial = a.shape=='radial' or swing.name in ('special','sweep')
            cx,cy=swing.target if a.shape=='target' else (attacker.x,attacker.y)
            dx=target.x-cx
            if abs(target.y-cy)>a.lane or abs(dx)>a.reach+10: continue
            if not radial and a.shape!='target' and dx*swing.direction < -8: continue
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
        self.hazard_clock = 0.
        self.encounter_age = 0.
        self.cats = AmbientCats()

    @property
    def bounds(self): return (self.wave*350+18, self.wave*350+382)
    @property
    def tickets(self): return min(150, self.score//180 + self.stage*8 + (40 if self.state=='victory' else 0))

    def spawn_position(self,index,occupied=()):
        left,right=self.bounds
        cells=[(left+30+col*55,183+row*26) for col in range(6) for row in range(4)]
        cells.sort(key=lambda pos: abs(pos[0]-self.player.x)+abs(pos[1]-self.player.y),reverse=True)
        safe=[pos for pos in cells if math.hypot(pos[0]-self.player.x,pos[1]-self.player.y)>=95
              and all(math.hypot(pos[0]-e.x,pos[1]-e.y)>=25 for e in occupied)]
        return safe[index%len(safe)] if safe else (right-20,183 if self.player.y>220 else 255)

    def spawn(self):
        self.enemies=[]
        for i,name in enumerate(WAVES[self.stage][self.wave]):
            x,y=self.spawn_position(i,self.enemies)
            enemy=EnemyFighter(name,x,y,i,self.stage)
            enemy.arena_bounds=self.bounds
            self.enemies.append(enemy)
        self.encounter_age=0.
        self.spawned=True
        self.events.append('wave')

    def update(self, dt, direction=(0,0)):
        if self.state != 'playing': return
        dt = max(0,min(dt,.05))
        self.elapsed += dt
        self.events.clear()
        self.cats.update(dt,self.elapsed,self.stage,self.wave,self.player.x,self.enemies)
        self.effects = [(x,y,t-dt) for x,y,t in self.effects if t>dt]
        if self.hitstop>0:
            self.hitstop -= dt
            return
        if not self.spawned: self.spawn()
        self.encounter_age += dt
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
            e.think(dt,p,e in permitted and active<2 and self.camera+12 < e.x < self.camera+388)
            if e.swing: active += 1
            e.x = max(self.bounds[0],min(self.bounds[1],e.x))
        for boss in tuple(self.enemies):
            if boss.summon_request:
                boss.summon_request=False
                limit=2 if boss.name=='NULL' else 1
                if boss.alive and boss.support_count<limit and len(candidates)<4:
                    name='echo' if boss.name=='NULL' else 'duelist'
                    x,y=self.spawn_position(0,candidates)
                    support=EnemyFighter(name,x,y,8+boss.support_count,self.stage)
                    support.arena_bounds=self.bounds
                    self.enemies.append(support)
                    boss.support_count+=1
                    self.events.append('summon')
            if boss.state in ('intro','phase','guard','teleport') and boss.boss and boss.timer>.95:
                if not getattr(boss,'cue_played',False):
                    self.events.append('boss_'+boss.name.lower()); boss.cue_played=True
        # Grounded bodies block each other; jumps and dodges cross the crowd.
        if p.jump<5 and p.state!='dodge':
            for e in candidates:
                dx=p.x-e.x
                if abs(dx)<15 and abs(p.y-e.y)<10 and e.state!='knockdown':
                    p.x=e.x+(15 if dx>=0 else -15)
            p.x=max(self.bounds[0],min(self.bounds[1],p.x))
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
        self.hazard_clock += dt
        if self.stage > 0 and self.wave < 3 and 4.7 < self.hazard_clock % 7 < 5.15 and abs(p.y-251)<9:
            damage = p.damage(12, -p.facing*65)
            if damage:
                self.damage_received += damage
                self.impact(p)
                self.events.append('hurt')
        if not p.alive:
            self.state = 'defeat'
            self.events.append('lose')
        elif self.spawned and all(not e.alive for e in self.enemies) and all(not e.boss or e.defeat_age>=1.35 for e in self.enemies):
            self.pickups = [(self.player.x,self.player.y)]
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
        self.player.health = min(self.player.max_health,self.player.health+35)
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
