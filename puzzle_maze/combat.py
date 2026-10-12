"""Finite, collision-aware enemy encounters and player combat."""
from collections import deque
from enum import Enum

class EnemyState(str,Enum):
    HUNT='hunt'
    WINDUP='windup'
    DYING='dying'
    DEAD='dead'

class Enemy:
    max_hp=2
    speed=.65
    windup=.3
    def __init__(self,data):
        self.id=data['id'];self.kind=data['type'];self.x,self.y=data['pos']
        self.hp=self.max_hp;self.state=EnemyState.HUNT
        self.move_timer=self.speed;self.attack_timer=0;self.flash=0;self.age=0;self.dropped=False

    @property
    def pos(self):return self.x,self.y

    def interval(self):return self.speed

    def capture(self):
        return dict(pos=list(self.pos),hp=self.hp,state=self.state.value,move_timer=self.move_timer,attack_timer=self.attack_timer,flash=self.flash,age=self.age,dropped=self.dropped)

class Slime(Enemy):
    pass

class Bat(Enemy):
    max_hp=1
    speed=.28
    windup=.18
    def interval(self):return .11 if self.age%2.8<.55 else self.speed

class Guardian(Enemy):
    max_hp=4
    speed=.8
    windup=.7

ENEMIES={'slime':Slime,'bat':Bat,'guardian':Guardian}
DIRECTIONS=((1,0),(-1,0),(0,1),(0,-1))

class CombatManager:
    def __init__(self,room,puzzles,player):
        self.puzzles=puzzles;self.player=player
        self.enemies=[ENEMIES[d['type']](d) for d in room.get('enemies',[])]
        self.loot=[]
        self.events=[]

    def blocked(self,pos,ignore=None):
        return not self.puzzles.can_enter(*pos) or any(e is not ignore and e.pos==pos and e.hp>0 for e in self.enemies)

    def knockback(self,target,source):
        dx=target.x-source.x;dy=target.y-source.y
        step=(1 if dx>0 else -1,0) if abs(dx)>=abs(dy) and dx else (0,1 if dy>0 else -1)
        pos=target.x+step[0],target.y+step[1]
        if not self.blocked(pos, target) and (target is self.player or pos!=(self.player.x,self.player.y)):
            target.x,target.y=pos

    def damage_player(self,source,amount=1):
        p=self.player
        if p.hp<=0 or p.invulnerable>0:return False
        p.hp=max(0,p.hp-amount);p.invulnerable=1.1
        self.knockback(p,source);self.events.append('hurt')
        return True

    def attack(self):
        p=self.player
        if p.hp<=0 or p.attack_cooldown>0:return False
        p.attack_cooldown=.25;p.attack_flash=.16
        dx,dy=p.facing;hit=False
        for e in self.enemies:
            ex,ey=e.x-p.x,e.y-p.y
            if e.hp>0 and abs(ex)+abs(ey)<=1 and ex*dx+ey*dy>=0:
                e.hp=max(0,e.hp-1);e.flash=.18;hit=True
                if e.hp==0:e.state=EnemyState.DYING;e.attack_timer=.35
                else:self.knockback(e,p)
        self.events.append('attack')
        return hit

    def heal(self):
        if self.player.hp<=0 or self.player.hp>=self.player.max_hp or self.puzzles.inventory.potions<=0:return False
        self.puzzles.inventory.potions-=1
        self.player.hp=min(self.player.max_hp,self.player.hp+3)
        self.events.append('heal');return True

    def next_step(self,enemy):
        start=enemy.pos;target=(self.player.x,self.player.y)
        queue=deque([(start,None)]);seen={start}
        while queue:
            pos,first=queue.popleft()
            if pos==target:return first
            for dx,dy in DIRECTIONS:
                nxt=pos[0]+dx,pos[1]+dy
                if nxt not in seen and (nxt==target or not self.blocked(nxt,enemy)) and self.puzzles.can_enter(*nxt):
                    seen.add(nxt);queue.append((nxt,first or nxt))
        return None

    def update(self,dt):
        p=self.player
        p.invulnerable=max(0,p.invulnerable-dt)
        p.attack_cooldown=max(0,p.attack_cooldown-dt)
        p.attack_flash=max(0,p.attack_flash-dt)
        if p.hp<=0:return
        for e in self.enemies:
            e.age+=dt;e.flash=max(0,e.flash-dt)
            if e.state==EnemyState.DEAD:continue
            if e.state==EnemyState.DYING:
                e.attack_timer=max(0,e.attack_timer-dt)
                if e.attack_timer<=0:
                    e.state=EnemyState.DEAD
                    if not e.dropped:
                        self.loot.append(dict(pos=list(e.pos),heal=1,coins=1));e.dropped=True
                        self.events.append('defeat')
                continue
            distance=abs(e.x-p.x)+abs(e.y-p.y)
            if e.state==EnemyState.WINDUP:
                e.attack_timer=max(0,e.attack_timer-dt)
                if e.attack_timer<=0:
                    if distance<=1:self.damage_player(e)
                    e.state=EnemyState.HUNT;e.move_timer=e.speed
                continue
            if distance<=1:
                e.state=EnemyState.WINDUP;e.attack_timer=e.windup;continue
            if distance>7:continue
            e.move_timer=max(0,e.move_timer-dt)
            if e.move_timer<=0:
                pos=self.next_step(e)
                if pos and pos!=(p.x,p.y):e.x,e.y=pos
                e.move_timer=e.interval()
        for drop in self.loot[:]:
            if tuple(drop['pos'])==(p.x,p.y):
                p.hp=min(p.max_hp,p.hp+drop['heal']);self.puzzles.inventory.coins+=drop['coins']
                self.loot.remove(drop);self.events.append('heal')

    @property
    def cleared(self):return all(e.hp==0 for e in self.enemies)

    def capture(self):return dict(enemies={e.id:e.capture() for e in self.enemies},loot=self.loot.copy())

    def restore(self,snapshot):
        enemies=snapshot['enemies']
        if set(enemies)!={e.id for e in self.enemies}:raise ValueError('Enemy snapshot mismatch')
        for e in self.enemies:
            values=enemies[e.id];pos=values['pos']
            if not isinstance(pos,list) or len(pos)!=2 or any(type(v) is not int for v in pos) or not self.puzzles.tilemap.walkable(*pos):raise ValueError('Invalid enemy position')
            if type(values['hp']) is not int or not 0<=values['hp']<=e.max_hp:raise ValueError('Invalid enemy HP')
            e.x,e.y=pos;e.hp=values['hp'];e.state=EnemyState(values['state'])
            if (e.hp==0)!=(e.state in (EnemyState.DEAD,EnemyState.DYING)):raise ValueError('Invalid enemy life state')
            for attr in ('move_timer','attack_timer','flash','age'):
                v=values[attr]
                if not isinstance(v,(int,float)) or not 0<=v<1e8:raise ValueError('Invalid enemy timer')
                setattr(e,attr,v)
            if type(values['dropped']) is not bool:raise ValueError('Invalid drop flag')
            e.dropped=values['dropped']
        self.loot=[]
        for drop in snapshot['loot']:
            pos=drop['pos']
            if not isinstance(pos,list) or len(pos)!=2 or any(type(v) is not int for v in pos) or not self.puzzles.tilemap.walkable(*pos):raise ValueError('Invalid loot position')
            if any(type(drop[k]) is not int or not 0<=drop[k]<=5 for k in ('heal','coins')):raise ValueError('Invalid loot')
            self.loot.append(dict(drop))
