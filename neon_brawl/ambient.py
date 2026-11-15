"""Deterministic non-hostile cats, completely outside fighter/collision lists."""
from dataclasses import dataclass
from functools import lru_cache

@dataclass
class StreetCat:
    x: float
    y: float
    variant: int
    direction: int=1
    age: float=0.
    state: str='walk'
    flee_time: float=0.

class AmbientCats:
    def __init__(self):self.cat=None;self.next_at=5.;self.spawn_count=0
    def update(self,dt,time,stage,section,player_x,enemies):
        if stage!=0:
            self.cat=None;self.next_at=time+6
            return
        if self.cat is None:
            if time<self.next_at:return
            self.cat=StreetCat(section*350+25,164,self.spawn_count%3)
            self.spawn_count+=1
        cat=self.cat;cat.age+=dt
        intense=any(e.alive and e.swing and abs(e.x-cat.x)<105 for e in enemies)
        if intense and cat.state not in ('flee','hide'):
            cat.state='flee';cat.flee_time=0.;cat.direction=-1 if player_x>cat.x else 1
        if cat.state=='flee':
            cat.x+=cat.direction*65*dt;cat.flee_time+=dt
            if cat.flee_time>2:cat.state='hide'
        elif cat.state=='hide' or cat.age>20:
            self.cat=None;self.next_at=time+14
        else:
            cat.state='walk' if cat.age<3 or cat.age>11 else 'sit' if cat.age<5 else 'stretch' if cat.age<6.5 else 'groom' if cat.age<9 else 'observe'
            if cat.state=='walk':cat.x+=cat.direction*19*dt

@lru_cache(maxsize=96)
def cat_sprite(variant,state,frame,direction):
    import pygame
    s=pygame.Surface((22,16),pygame.SRCALPHA)
    fur,shade=(((205,150,85),(135,90,65)),((155,175,190),(90,105,135)),((75,75,95),(155,155,175)))[variant%3]
    r=pygame.draw
    crouch=state in ('sit','groom','observe')
    r.ellipse(s,shade,(3,8,14,6));r.ellipse(s,fur,(4,6 if not crouch else 7,12,6))
    if state=='stretch':r.rect(s,fur,(3,9,15,3))
    r.polygon(s,fur,[(13,8),(13,1),(16,4),(19,1),(20,9)])
    r.rect(s,(150,225,185),(18,6,1,1));r.rect(s,shade,(14,8,3,1))
    stride=(-1,1)[frame%2] if state in ('walk','flee') else 0
    for x,y in ((6,12+stride),(13,12-stride)):r.line(s,shade,(x,10),(x,y),2)
    r.lines(s,fur,False,[(5,9),(2,7),(1,4+frame%2)],2)
    if state=='groom':r.line(s,fur,(13,12),(19,8+frame%2),2)
    r.line(s,shade,(7,7),(7,9));r.line(s,shade,(10,7),(10,9))
    return pygame.transform.flip(s,True,False) if direction<0 else s

def draw_cats(surface,cats,camera,time):
    cat=cats.cat
    if cat is None or cat.state=='hide':return
    surface.blit(cat_sprite(cat.variant,cat.state,int(time*8)%4,cat.direction),(int(cat.x-camera)-11,int(cat.y)-15))
