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
            self.cat=StreetCat(camera+(50 if direction>0 else 350),247,self.spawn_count%5,direction)
            self.spawn_count+=1;self.next_at=time+22
        cat=self.cat;cat.age+=max(0,dt)
        # Ambient actors remain visible during combat and never enter fighter lists.
        if cat.age>16:
            self.cat=None;return
        cat.state='walk' if cat.age<5 or cat.age>11 else 'sit' if cat.age<7 else 'groom' if cat.age<9.5 else 'observe'
        if 11<cat.age<12.5:cat.state='run'
        if cat.state in ('walk','run'):cat.x+=cat.direction*(34 if cat.state=='run' else 21)*dt
        cat.x=max(camera+20,min(camera+380,cat.x))

CAT_COLORS=(
 ((216,158,91),(150,99,66)),((74,80,98),(226,224,203)),
 ((154,172,189),(91,114,143)),((233,213,179),(155,106,75)),
 ((234,218,174),(184,151,111)),
)

@lru_cache(maxsize=640)
def cat_sprite(variant,state,frame,direction):
    import pygame
    s=pygame.Surface((22,16),pygame.SRCALPHA);r=pygame.draw
    fur,shade=CAT_COLORS[variant%len(CAT_COLORS)];ink=(40,42,57);cream=(249,239,210)
    crouch=state in ('sit','groom','observe')
    by=7 if crouch else 6
    r.ellipse(s,ink,(3,by,14,8));r.ellipse(s,fur,(4,by,12,6))
    if variant%5==1:r.ellipse(s,cream,(11,8,6,6))
    if variant%5==3:
        r.ellipse(s,(189,120,72),(5,by,5,4));r.ellipse(s,(71,74,87),(9,by+1,5,4))
    if variant%5 in (0,2):
        for x in (6,10):r.line(s,shade,(x,by),(x+1,by+3))
    # Two clear forward-facing eyes, tiny pupils, inner ears, nose and muzzle.
    r.polygon(s,ink,[(12,9),(12,1),(16,3),(20,0),(22,7),(20,12),(14,12)])
    r.polygon(s,fur,[(13,8),(13,2),(16,5),(20,2),(21,8),(19,11),(15,11)])
    r.rect(s,(214,155,157),(14,3,1,2));r.rect(s,(214,155,157),(19,3,1,2))
    r.ellipse(s,cream,(15,8,6,3))
    for x in (14,18):
        if frame%8==7:r.line(s,shade,(x,7),(x+1,7))
        else:
            r.rect(s,(246,245,216),(x,6,2,2));r.rect(s,(67,104,116),(x+1,7,1,1))
    r.rect(s,(206,132,143),(17,8,1,1));r.line(s,(122,100,109),(16,10),(18,10))
    stride=(-1,1)[frame%2] if state in ('walk','run','flee') else 0
    for x,y in ((6,13+stride),(13,13-stride)):
        r.line(s,shade,(x,10),(x,y),2);r.line(s,cream if variant%5==1 else fur,(x,y),(x+2,y))
    tip=(1,3+frame%3) if not crouch else (2,9-frame%2)
    r.lines(s,ink,False,[(5,10),(2,8),tip],3);r.lines(s,fur,False,[(5,10),(2,8),tip],2)
    if state=='groom':r.line(s,fur,(13,12),(18,8+frame%2),2)
    return pygame.transform.flip(s,True,False) if direction<0 else s

def draw_cats(surface,cats,camera,time):
    cat=cats.cat
    if cat is None or cat.state=='hide':return
    import pygame
    image=visible_cat_sprite(cat.variant,cat.state,int(time*6)%8,cat.direction)
    x=int(cat.x-camera);y=int(cat.y)
    pygame.draw.ellipse(surface,(15,18,30),(x-14,y-3,29,6))
    surface.blit(image,(x-16,y-24))

@lru_cache(maxsize=640)
def visible_cat_sprite(variant,state,frame,direction):
    import pygame
    return pygame.transform.scale(cat_sprite(variant,state,frame,direction),(33,24))
