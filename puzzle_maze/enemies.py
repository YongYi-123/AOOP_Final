"""Original enemy strategies layered onto the existing finite encounter manager."""
from dataclasses import dataclass
from puzzle_maze.combat import Enemy,Guardian,EnemyState,ENEMIES
from puzzle_maze.exploration import Exploration

@dataclass
class Projectile:
    x:int
    y:int
    dx:int
    dy:int
    timer:float=.16
    steps:int=8

class BlinkMage(Enemy):
    max_hp=3
    speed=.75
    def special_update(self,manager,dt):
        p=manager.player
        self.move_timer=max(0,self.move_timer-dt)
        if self.state==EnemyState.WINDUP:
            self.attack_timer=max(0,self.attack_timer-dt)
            if not self.attack_timer:
                manager.fire(self);self.state=EnemyState.HUNT;self.move_timer=1.8
            return True
        if self.move_timer>0:return True
        distance=abs(self.x-p.x)+abs(self.y-p.y)
        if distance<=3:
            # Blink requires line of sight for every intervening tile.
            candidates=[]
            for dx,dy in ((3,0),(-3,0),(0,3),(0,-3)):
                dest=self.x+dx,self.y+dy
                if dest==(p.x,p.y):continue
                if all(not manager.blocked(cell,self) and cell!=(p.x,p.y) for cell in list(Exploration.ray(self.pos,dest))[1:]):candidates.append(dest)
            if candidates:
                self.x,self.y=max(candidates,key=lambda cell:abs(cell[0]-p.x)+abs(cell[1]-p.y));manager.events.append('teleport')
        if distance<=9:self.state=EnemyState.WINDUP;self.attack_timer=.65
        else:self.move_timer=.5
        return True

class ArmoredBeetle(Guardian):
    max_hp=3
    speed=.7
    def __init__(self,data):super().__init__(data);self.facing=(0,1);self.armor=True
    def receive_damage(self,manager,amount,kind,source):
        if kind=='bomb':self.armor=False
        vector=source.x-self.x,source.y-self.y
        if kind=='sword' and self.armor and vector[0]*self.facing[0]+vector[1]*self.facing[1]>=0:
            self.flash=.12;manager.events.append('shield');return False
        return super().receive_damage(manager,amount,kind,source)
    def special_update(self,manager,dt):
        # Armor orientation commits during windup, allowing a flank.
        if self.state!=EnemyState.WINDUP and self.move_timer<=dt:
            step=manager.next_step(self)
            if step:self.facing=step[0]-self.x,step[1]-self.y
        return False
    def capture(self):return dict(super().capture(),facing=list(self.facing),armor=self.armor)

class BombEater(Enemy):
    max_hp=6
    speed=.55
    def receive_damage(self,manager,amount,kind,source):
        if kind!='bomb':manager.events.append('shield');return False
        return super().receive_damage(manager,amount,kind,source)
    def special_update(self,manager,dt):
        bombs=getattr(manager,'bombs',None)
        if not bombs or not bombs.bombs:return False
        bomb=min(bombs.bombs,key=lambda b:abs(b.x-self.x)+abs(b.y-self.y))
        if abs(bomb.x-self.x)+abs(bomb.y-self.y)<=1:return True
        self.move_timer=max(0,self.move_timer-dt)
        if self.move_timer==0:
            candidates=[(self.x+dx,self.y+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))]
            candidates=[pos for pos in candidates if not manager.blocked(pos,self) and pos!=(manager.player.x,manager.player.y)]
            if candidates:self.x,self.y=min(candidates,key=lambda pos:abs(pos[0]-bomb.x)+abs(pos[1]-bomb.y))
            self.move_timer=self.speed
        return True

class AncientGolem(Guardian):
    max_hp=12
    speed=.65
    windup=.85
    def __init__(self,data):super().__init__(data);self.exposed=0;self.primed=0
    @property
    def phase(self):return 1 if self.hp>8 else 2 if self.hp>4 else 3
    def dash_trigger(self):
        self.primed=6
        if self.phase==1:self.exposed=6
    def receive_damage(self,manager,amount,kind,source):
        if self.hp<=0:return False
        if self.phase==3 and self.data.get('crystal_color'):
            color='blue' if 'crystal_blue' in manager.puzzles.inventory.flags else 'red'
            if color!=self.data['crystal_color']:manager.events.append('shield');return False
        if kind=='bomb':
            if self.phase==2 or self.phase==3 and self.primed>0:
                self.exposed=5;self.flash=.4;self.state=EnemyState.HUNT;self.move_timer=1.4
                manager.events.append('boss_break');return True
            manager.events.append('shield');return False
        if kind not in ('sword','pot') or self.exposed<=0:
            manager.events.append('shield');return False
        phase=self.phase
        # Arena anchor is immune to knockback; exposure requires abilities again after each phase.
        self.hp=max(0,self.hp-amount);self.flash=.18;self.stagger=.22
        if self.hp<=0:self.state=EnemyState.DYING;self.attack_timer=1.2
        elif self.phase!=phase:self.exposed=0;self.primed=0;self.state=EnemyState.HUNT;self.move_timer=1
        return True
    def special_update(self,manager,dt):
        self.exposed=max(0,self.exposed-dt);self.primed=max(0,self.primed-dt)
        if self.exposed>0:
            self.state=EnemyState.HUNT;self.move_timer=max(self.move_timer,1.0);return True
        self.move_timer=max(0,self.move_timer-dt)
        p=manager.player
        if self.state==EnemyState.WINDUP:
            self.attack_timer=max(0,self.attack_timer-dt)
            if not self.attack_timer:
                if abs(self.x-p.x)+abs(self.y-p.y)<=2:manager.damage_player(self)
                if self.phase>=2:manager.fire(self,spread=self.phase==3)
                self.state=EnemyState.HUNT;self.move_timer=1.4 if self.phase<3 else .85
            return True
        if self.move_timer<=0:
            if self.phase>=2 and abs(self.x-p.x)+abs(self.y-p.y)>2:
                dest=manager.next_step(self)
                if dest and dest!=(p.x,p.y):self.x,self.y=dest
            self.state=EnemyState.WINDUP;self.attack_timer=.85 if self.phase<3 else .55
        return True
    def capture(self):return dict(super().capture(),exposed=self.exposed,primed=self.primed)

ENEMIES.update(blink_mage=BlinkMage,armored_beetle=ArmoredBeetle,bomb_eater=BombEater,golem=AncientGolem)

def fire(manager,enemy,spread=False):
    p=manager.player;dx=p.x-enemy.x;dy=p.y-enemy.y
    direction=(1 if dx>0 else -1,0) if abs(dx)>=abs(dy) else (0,1 if dy>0 else -1)
    directions=((1,0),(-1,0),(0,1),(0,-1)) if spread else (direction,)
    for dx,dy in directions:manager.projectiles.append(Projectile(enemy.x,enemy.y,dx,dy))
    manager.events.append('projectile')

def update_projectiles(manager,dt):
    for bolt in manager.projectiles[:]:
        bolt.timer-=dt
        while bolt.timer<=0 and bolt in manager.projectiles:
            bolt.timer+=.16;bolt.x+=bolt.dx;bolt.y+=bolt.dy;bolt.steps-=1
            if not manager.puzzles.can_enter(bolt.x,bolt.y) or bolt.steps<=0:
                manager.projectiles.remove(bolt);break
            if (bolt.x,bolt.y)==(manager.player.x,manager.player.y):
                from types import SimpleNamespace
                manager.damage_player(SimpleNamespace(x=bolt.x-bolt.dx,y=bolt.y-bolt.dy));manager.projectiles.remove(bolt);break
