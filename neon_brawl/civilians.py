"""Small deterministic ambient actors. No fighter, damage, collision or wave APIs."""
from dataclasses import dataclass
from functools import lru_cache
import math
import pygame

@dataclass
class Civilian:
    role:str
    x:float
    y:float
    variant:int
    home:float
    state:str='browse'
    fear:float=0.
    timer:float=0.
    direction:int=1

class StreetLife:
    def __init__(self):self.people=[];self.section=None;self.age=0.
    def populate(self,section):
        self.section=section;self.people=[]
        for i,role in enumerate(('vendor','shopper','tourist','spectator','customer','walker')):
            x=section*350+30+i*61
            self.people.append(Civilian(role,x,165+i%3*3,i%4,x,direction=1 if i%2 else -1))
    def update(self,dt,time,stage,section,player,enemies,camera):
        if stage!=0:self.people=[];self.section=None;return
        if section!=self.section:self.populate(section)
        self.age+=dt
        if (section in (1,3) or time%40>25) and not any(p.role=='police' for p in self.people):
            x=camera+365;self.people.append(Civilian('police',x,169,0,x))
        for p in self.people:
            p.timer+=dt
            nearby=[e for e in enemies if e.alive and abs(e.x-p.x)<150]
            danger=bool(abs(player.x-p.x)<180 and player.swing or any(e.swing for e in nearby) or len(nearby)>=3)
            intense=sum(bool(e.swing) for e in nearby)>=2 or any(e.boss and e.swing for e in nearby)
            p.fear=max(0,p.fear+(dt if danger else -dt*.6))
            if p.state=='panic':
                p.x+=p.direction*55*dt
                if p.timer>2.2:p.state='hide';p.timer=0.
                continue
            if p.state=='hide':
                if p.timer>4 and not danger:p.x=p.home;p.state='browse';p.timer=0.
                continue
            if p.role=='police':p.state='direct' if danger else 'observe'
            elif p.role=='vendor':p.state='cook'
            elif danger:
                if p.role in ('shopper','walker') and (intense or p.fear>.7):
                    p.state='panic';p.timer=0.;p.direction=-1 if p.x<player.x else 1
                elif p.role=='tourist':p.state='photo'
                elif p.role=='customer':p.state='peek'
                else:p.state='watch';p.x+=(p.home-7-p.x)*min(1,dt*3)
            elif p.role=='walker':
                p.state='walk';p.x+=p.direction*9*dt
                if abs(p.x-p.home)>20:p.direction*=-1
            else:p.state='browse'
    def draw(self,s,camera,time):
        for p in self.people:
            if p.state=='hide':continue
            x=int(p.x-camera);y=int(p.y)
            if not -24<x<424:continue
            pygame.draw.ellipse(s,(22,26,40),(x-8,y-2,17,4))
            image=civilian_sprite(p.role,p.state,int(time*(10 if p.state=='panic' else 5))%4,p.variant,p.direction)
            s.blit(image,(x-9,y-30))
            if p.role=='police':
                # A compact patrol scooter at a safe background curb; never a collider.
                xx=int(p.home-camera)+8
                for dx in (0,19):pygame.draw.circle(s,(22,25,40),(xx+dx,170),4)
                pygame.draw.lines(s,(89,123,157),False,[(xx,168),(xx+7,160),(xx+19,168),(xx+22,152)],3)
                s.fill((171,112,132) if int(time)%2 else (109,155,187),(xx+17,151,4,2))

@lru_cache(maxsize=640)
def civilian_sprite(role,state,frame,variant,direction):
    s=pygame.Surface((18,31),pygame.SRCALPHA);r=pygame.draw
    ink=(35,34,48);skin=((206,162,128),(160,119,103),(223,185,143),(182,138,115))[variant%4]
    coat=((156,103,127),(108,154,146),(179,143,90),(113,125,173))[variant%4]
    if role=='police':coat=(92,119,157)
    bob=1 if state in ('walk','panic') and frame%2 else 0
    r.rect(s,ink,(5,3+bob,8,9));r.rect(s,skin,(6,5+bob,6,7))
    r.rect(s,(71,57,65),(5,2+bob,8,4));r.rect(s,(71,57,65),(5,4+bob,2,4))
    for x in (7,10):r.rect(s,(238,230,208),(x,7+bob,1,1))
    r.rect(s,(128,84,87),(8,10+bob,2,1));r.rect(s,skin,(8,12,2,2))
    r.polygon(s,ink,[(5,13),(12,13),(15,23),(3,23)])
    r.rect(s,coat,(5,14,8,9));r.line(s,(199,179,150),(9,15),(9,22))
    stride=(-2,0,2,0)[frame%4] if state in ('walk','panic') else 0
    for x,step in ((5,stride),(10,-stride)):
        r.rect(s,(65,70,94),(x,23,3,5+step));r.rect(s,(41,43,58),(x-1,27+step,5,2))
    raised=state in ('watch','direct','photo')
    r.line(s,coat,(5,15),(2,17 if raised else 22),3)
    r.line(s,coat,(12,15),(15,11 if raised and frame%2 else 19),3)
    r.rect(s,skin,(1,16 if raised else 22,3,3));r.rect(s,skin,(14,10 if raised and frame%2 else 19,3,3))
    if role=='vendor':
        r.rect(s,(216,201,164),(6,17,6,8));r.rect(s,(216,201,164),(5,2,9,3))
        r.line(s,(188,188,175),(14,20),(16,13+frame%2))
    if role=='shopper' and state!='panic':
        r.rect(s,(180,151,105),(1,23,5,6));r.arc(s,(190,170,121),(1,20,5,7),0,3.14,1)
    if state=='photo':
        r.rect(s,(52,60,76),(3,9,10,5));r.rect(s,(152,189,192),(6,10,3,2))
    if state=='peek':r.rect(s,(107,89,86),(1,22,16,8))
    if role=='police':
        r.rect(s,(79,106,146),(4,2,10,3));r.rect(s,(217,189,116),(8,2,2,2))
        r.rect(s,(217,189,116),(6,16,2,2));r.rect(s,(41,49,68),(5,22,8,2))
    return pygame.transform.flip(s,True,False) if direction<0 else s
