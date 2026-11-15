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
    def __init__(self):self.cat=None;self.next_at=5.;self.spawn_count=0;self.stage=None
    def update(self,dt,time,stage,section,player_x,enemies,camera=0.):
        if self.stage is not None and self.stage!=stage:
            self.cat=None;self.next_at=time+4
        self.stage=stage
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
        if 5<cat.age<7:cat.state=('observe','sit','stretch','groom','sleep')[cat.variant]
        if 7<cat.age<11:cat.state='sleep' if cat.variant in (1,4) else 'groom' if cat.variant==3 else 'observe'
        if stage==1 and 6<cat.age<7.5:cat.state='stretch'
        if 11<cat.age<12.5:cat.state='run'
        if cat.state in ('walk','run'):cat.x+=cat.direction*(34 if cat.state=='run' else 21)*dt
        cat.x=max(camera+20,min(camera+380,cat.x))

from .lab_cats import cat_sprite,DESIGNS,SIZE
CAT_COLORS=tuple((d.fur,d.shade) for d in DESIGNS)

def draw_cats(surface,cats,camera,time):
    cat=cats.cat
    if cat is None or cat.state=='hide':return
    import pygame
    image=visible_cat_sprite(cat.variant,cat.state,int(time*(10 if cat.state=='run' else 6))%8,cat.direction)
    x=int(cat.x-camera);y=int(cat.y)
    pygame.draw.ellipse(surface,(15,18,30),(x-14,y-3,29,6))
    surface.blit(image,(x-SIZE[0]//2,y-SIZE[1]))

@lru_cache(maxsize=640)
def visible_cat_sprite(variant,state,frame,direction):
    import pygame
    return cat_sprite(variant,state,frame,direction)
