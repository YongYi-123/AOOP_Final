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
    def update(self,dt,time,stage,section,player_x,enemies,camera=0.):
        if stage!=0:
            self.cat=None;self.next_at=time+6
            return
        if self.cat is None:
            if time<self.next_at:return
            direction=1 if self.spawn_count%2==0 else -1
            self.cat=StreetCat(camera+(50 if direction>0 else 350),247,self.spawn_count%3,direction)
            self.spawn_count+=1;self.next_at=time+22
        cat=self.cat;cat.age+=max(0,dt)
        # Ambient actors remain visible during combat and never enter fighter lists.
        if cat.age>16:
            self.cat=None;return
        cat.state='walk' if cat.age<5 or cat.age>11 else 'sit' if cat.age<7 else 'groom' if cat.age<9.5 else 'observe'
        if cat.state=='walk':cat.x+=cat.direction*21*dt
        cat.x=max(camera+20,min(camera+380,cat.x))

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
    import pygame
    image=visible_cat_sprite(cat.variant,cat.state,int(time*8)%4,cat.direction)
    x=int(cat.x-camera);y=int(cat.y)
    pygame.draw.ellipse(surface,(15,18,30),(x-14,y-3,29,6))
    surface.blit(image,(x-16,y-24))

@lru_cache(maxsize=96)
def visible_cat_sprite(variant,state,frame,direction):
    import pygame
    return pygame.transform.scale(cat_sprite(variant,state,frame,direction),(33,24))
