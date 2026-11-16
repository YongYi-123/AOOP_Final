"""A room-local Miao: legal floor paths, following, wandering and quiet naps."""
from collections import deque
import math
import random
from puzzle_maze.studio_layout import MIAO_TILE,contact_blocked

class StudioCompanion:
    def __init__(self):
        self.x,self.y=MIAO_TILE[0]*16+8.,MIAO_TILE[1]*16+16.
        self.time=0.;self.state='wander';self.walking=False;self.side='right'
        self.path=[];self.think=0.;self.rng=random.Random(71)

    @property
    def position(self):return self.x,self.y

    @property
    def tile(self):return round((self.x-8)/16),round((self.y-16)/16)

    def route(self,session,target):
        start=self.tile;q=deque([start]);previous={start:None}
        while q:
            p=q.popleft()
            if p==target:
                path=[]
                while previous[p] is not None:path.append(p);p=previous[p]
                return list(reversed(path))
            for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
                nxt=p[0]+dx,p[1]+dy
                if nxt not in previous and session.can_enter(*nxt):previous[nxt]=p;q.append(nxt)
        return []

    def update(self,dt,session):
        dt=max(0,dt);self.time+=dt;self.think-=dt;self.walking=False
        p=session.player;player=(p.x*16+8,p.y*16+16)
        distance=math.dist(self.position,player)
        phase=self.time%54
        if 34<=phase<47 and distance>=22:
            self.state='sleep';self.path=[];return
        if 17<=distance<32 and self.time%8<2.5:
            self.state='idle';self.path=[];return
        self.state='follow' if distance>75 else 'wander'
        if self.think<=0 or (distance<20 and not self.path):
            self.think=self.rng.uniform(2.2,4.5)
            candidates=[(x,y) for y,row in enumerate(session.rooms.data['tiles']) for x,_ in enumerate(row)
                        if session.can_enter(x,y) and math.dist((x*16+8,y*16+16),player)>=24
                        and (x,y)!=(1,7)]
            if self.state=='follow':
                candidates.sort(key=lambda tile:abs(tile[0]-p.x)+abs(tile[1]-p.y))
                candidates=candidates[:6]
            elif distance<20:
                candidates=[tile for tile in candidates if math.dist((tile[0]*16+8,tile[1]*16+16),self.position)<60]
            else:
                candidates=[tile for tile in candidates if math.dist((tile[0]*16+8,tile[1]*16+16),self.position)<75]
            self.rng.shuffle(candidates)
            for target in candidates:
                path=self.route(session,target)
                if path:self.path=path;break
        budget=min(dt,.1)*(29 if self.state=='follow' else 19)
        while self.path and budget>0:
            tx,ty=self.path[0];goal=(tx*16+8,ty*16+16)
            length=math.dist(self.position,goal)
            if length<.01:self.path.pop(0);continue
            step=min(length,budget)
            nx=self.x+(goal[0]-self.x)/length*step;ny=self.y+(goal[1]-self.y)/length*step
            # Feet, walls and furniture use the same physical checks as the player.
            if ((math.dist((nx,ny),player)<17 and math.dist((nx,ny),player)<=math.dist(self.position,player)) or
                contact_blocked(nx,ny,session.rooms.data['solid_footprints'],width=10,height=6)):
                self.path=[];self.think=0.;break
            if abs(nx-self.x)>.01:self.side='right' if nx>self.x else 'left'
            self.x,self.y=nx,ny;budget-=step;self.walking=True
