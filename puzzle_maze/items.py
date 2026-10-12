"""Consumable blast simulation uses the same puzzle collision graph as movement."""
from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace

@dataclass
class Bomb:
    x:int
    y:int
    fuse:float=1.6
    swallowed:str|None=None
    @property
    def pos(self):return self.x,self.y

class BombManager:
    cooldown=.35
    def __init__(self,session):self.session=session;self.bombs=[];self.timer=0;self.blasts=[]
    def place(self):
        s=self.session;p=s.player
        if p.hp<=0 or self.timer>0 or s.inventory.bombs<=0:return False
        pos=p.x+p.facing[0],p.y+p.facing[1]
        # Placement against a cracked wall or enemy remains legal, permanent walls reject it.
        if s.puzzles.blocked(*pos):pos=p.x,p.y
        if any(b.pos==pos for b in self.bombs):return False
        s.inventory.bombs-=1;self.bombs.append(Bomb(*pos));self.timer=self.cooldown
        s.combat.events.append('bomb_place');return True
    def footprint(self,pos,radius=2):
        puzzles=self.session.puzzles;seen={pos};queue=deque([(pos,0)]);result=set()
        while queue:
            cell,distance=queue.popleft();result.add(cell)
            if distance>=radius:continue
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt=cell[0]+dx,cell[1]+dy
                if nxt in seen or not puzzles.tilemap.walkable(*nxt):continue
                obj=next((o for o in puzzles.objects.values() if o.pos==nxt and o.blocking and not o.state.active),None)
                if obj and obj.data['type'] not in ('cracked',):continue
                seen.add(nxt);result.add(nxt)
                if not obj:queue.append((nxt,distance+1))
        return result
    def update(self,dt):
        self.timer=max(0,self.timer-dt)
        self.blasts=[(cells,remaining-dt) for cells,remaining in self.blasts if remaining>dt]
        s=self.session
        for bomb in self.bombs[:]:
            eater=next((e for e in s.combat.enemies if e.hp>0 and e.kind=='bomb_eater' and abs(e.x-bomb.x)+abs(e.y-bomb.y)<=1),None)
            if eater and not bomb.swallowed:
                bomb.swallowed=eater.id;bomb.fuse=min(bomb.fuse,.7);eater.flash=.7
            if bomb.swallowed:
                eater=next(e for e in s.combat.enemies if e.id==bomb.swallowed);bomb.x,bomb.y=eater.pos
            bomb.fuse-=dt
            if bomb.fuse>0:continue
            cells=self.footprint(bomb.pos)
            for obj in s.puzzles.objects.values():
                if obj.pos in cells and obj.data['type'] in ('cracked','blast_switch'):obj.state.active=True
            for enemy in s.combat.enemies:
                if enemy.hp>0 and not enemy.dormant and enemy.pos in cells:
                    enemy.receive_damage(s.combat,6 if enemy.id==bomb.swallowed else 2,'bomb',bomb)
            if (s.player.x,s.player.y) in cells:s.combat.damage_player(SimpleNamespace(x=bomb.x,y=bomb.y))
            self.bombs.remove(bomb);self.blasts.append((cells,.45));s.combat.events.append('explosion')
    def capture(self):return dict(timer=self.timer,bombs=[vars(b).copy() for b in self.bombs])
    def restore(self,data):
        import math
        timer=data.get('timer',0)
        if type(timer) not in (float,int) or not math.isfinite(timer) or not 0<=timer<=self.cooldown:raise ValueError('Invalid bomb cooldown')
        self.timer=timer;self.bombs=[]
        for values in data.get('bombs',[]):
            b=Bomb(**values)
            if type(b.x) is not int or type(b.y) is not int or not self.session.puzzles.tilemap.walkable(*b.pos) or type(b.fuse) not in (float,int) or not 0<b.fuse<=1.6:raise ValueError('Invalid bomb')
            if b.swallowed and b.swallowed not in {e.id for e in self.session.combat.enemies if e.hp>0 and e.kind=='bomb_eater'}:raise ValueError('Invalid swallowed bomb')
            self.bombs.append(b)
