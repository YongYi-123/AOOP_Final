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
        self.data=data;self.dormant=bool(data.get('summon_at'));self.id=data['id'];self.kind=data['type'];self.x,self.y=data['pos']
        self.hp=self.max_hp;self.state=EnemyState.HUNT
        self.move_timer=self.speed;self.attack_timer=0;self.flash=0;self.age=0;self.dropped=False

    @property
    def pos(self):return self.x,self.y

    def receive_damage(self,manager,amount,kind,source):
        if self.hp<=0:return False
        self.hp=max(0,self.hp-amount);self.flash=.18
        if self.hp==0:
            self.state=EnemyState.DYING;self.attack_timer=.6 if self.kind=='golem' else .35
            manager.record_defeat(self)
        else:manager.knockback(self,source)
        return True

    def special_update(self,manager,dt):return False

    def interval(self):return self.speed

    def capture(self):
        return dict(pos=list(self.pos),hp=self.hp,state=self.state.value,move_timer=self.move_timer,attack_timer=self.attack_timer,flash=self.flash,age=self.age,dropped=self.dropped,dormant=self.dormant)

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
        from puzzle_maze import advanced_enemies
        from puzzle_maze import enemies  # Register strategies without import cycles.
        self.puzzles=puzzles;self.player=player
        self.kill_order=room.get('kill_order',[]);self.order_index=0
        self.projectiles=[]
        self.enemies=[ENEMIES[d['type']](d) for d in room.get('enemies',[])]
        self.loot=[]
        self.events=[]

    def record_defeat(self,enemy):
        if not self.kill_order:return
        if enemy.id==self.kill_order[self.order_index]:
            self.order_index+=1;self.events.append('order_step')
        else:
            self.enemies=[ENEMIES[e.data['type']](e.data) for e in self.enemies]
            self.order_index=0;self.loot=[];self.projectiles=[];self.events.append('order_wrong')
            self.puzzles.inventory.notifications.append(('pulse','WRONG ORDER / RESET'))

    def fire(self,enemy,spread=False):
        from puzzle_maze.enemies import fire
        fire(self,enemy,spread)

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
        p.attack_cooldown=p.weapon.cooldown;p.attack_flash=p.weapon.swing_duration
        p.attack_facing=p.facing
        hit=False
        for e in self.enemies:
            if not e.dormant and e.hp>0 and p.weapon.contains((p.x,p.y),e.pos,p.attack_facing):
                hit=e.receive_damage(self,p.weapon.damage,"sword",p) or hit
        self.events.append('hit' if hit else 'attack')
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
        from puzzle_maze.enemies import update_projectiles
        update_projectiles(self,dt)
        for e in self.enemies:
            e.age+=dt;e.flash=max(0,e.flash-dt)
            if e.dormant:
                summoner=next((foe for foe in self.enemies if foe.kind=="crystal_warden"),None)
                if summoner and summoner.hp<=e.data["summon_at"]:e.dormant=False;self.events.append("teleport")
                else:continue
            if e.state==EnemyState.DEAD:continue
            if e.state==EnemyState.DYING:
                e.attack_timer=max(0,e.attack_timer-dt)
                if e.attack_timer<=0:
                    e.state=EnemyState.DEAD
                    if not e.dropped:
                        if not self.kill_order:self.loot.append(dict(pos=list(e.pos),heal=1,coins=1,bombs=2 if e.kind in ("blink_mage","armored_beetle","bomb_eater") else 0))
                        e.dropped=True
                        self.events.append('defeat')
                continue
            if e.special_update(self,dt):continue
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
                self.puzzles.inventory.supply_bombs(drop.get('bombs',0))
                self.loot.remove(drop);self.events.append('heal')

    @property
    def cleared(self):
        if any(e.kind=="golem" for e in self.enemies):return all(e.state==EnemyState.DEAD for e in self.enemies)
        return all(e.hp==0 for e in self.enemies)

    def capture(self):return dict(order_index=self.order_index,enemies={e.id:e.capture() for e in self.enemies},loot=self.loot.copy(),projectiles=[vars(b).copy() for b in self.projectiles])

    def restore(self,snapshot):
        from puzzle_maze.enemies import Projectile
        self.projectiles=[]
        for values in snapshot.get('projectiles',[]):
            bolt=Projectile(**values)
            if not self.puzzles.tilemap.walkable(bolt.x,bolt.y) or (bolt.dx,bolt.dy) not in DIRECTIONS or not 0<bolt.steps<=8 or not 0<=bolt.timer<=.16:raise ValueError('Invalid projectile')
            self.projectiles.append(bolt)
        self.order_index=snapshot.get('order_index',0)
        if type(self.order_index) is not int or not 0<=self.order_index<=len(self.kill_order):raise ValueError('Invalid kill order')
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
            if type(values.get('dormant',False)) is not bool:raise ValueError('Invalid summon state')
            e.dormant=values.get('dormant',False)
            if e.kind in ('armored_beetle','mirror_mask'):
                facing=tuple(values.get('facing',(0,1)))
                if facing not in DIRECTIONS or type(values.get('armor',True)) is not bool:raise ValueError('Invalid armor state')
                e.facing=facing;e.armor=values.get('armor',True)
            if e.kind=='golem':
                for attr in ('exposed','primed'):
                    value=values.get(attr,0)
                    if type(value) not in (int,float) or not 0<=value<=6:raise ValueError('Invalid boss state')
                    setattr(e,attr,value)
        self.loot=[]
        for drop in snapshot['loot']:
            pos=drop['pos']
            if not isinstance(pos,list) or len(pos)!=2 or any(type(v) is not int for v in pos) or not self.puzzles.tilemap.walkable(*pos):raise ValueError('Invalid loot position')
            if any(type(drop[k]) is not int or not 0<=drop[k]<=5 for k in ('heal','coins')):raise ValueError('Invalid loot')
            bombs=drop.get('bombs',0)
            if type(bombs) is not int or not 0<=bombs<=20:raise ValueError('Invalid bomb drop')
            self.loot.append(dict(drop))
