"""Small original pixel expressions; silhouettes and danger colors remain readable."""
import math
import pygame
from puzzle_maze.combat import EnemyState

class EnemyPortraits:
    def __init__(self):self.encounter=None;self.positions={}
    def position(self,combat,enemy,dt):
        if self.encounter is not combat:
            self.encounter=combat;self.positions={}
        x,y=self.positions.get(enemy.id,enemy.pos)
        if abs(x-enemy.x)+abs(y-enemy.y)>3:x,y=enemy.pos
        blend=min(1,max(0,dt)*18)
        x+=(enemy.x-x)*blend;y+=(enemy.y-y)*blend
        self.positions[enemy.id]=x,y
        return round(x*16),round(y*16)
    def face(self,surface,enemy,x,y,time):
        r=pygame.draw;hurt=enemy.flash>0
        # White catchlights, tiny cheeks and a mouth are visible at native scale.
        if enemy.kind=='crystal_ghost':return  # Its translucent body must remain translucent.
        ey=7 if enemy.kind in ('golem','crystal_warden') else 8
        if hurt:
            for ox in (5,10):r.lines(surface,(34,39,56),False,[(x+ox-1,y+ey),(x+ox+1,y+ey+1),(x+ox-1,y+ey+2)])
            r.rect(surface,(93,47,66),(x+7,y+ey+3,2,2))
        else:
            blink=int(time*3+sum(map(ord,enemy.id)))%19==0
            for ox in (5,10):
                r.rect(surface,(239,245,226),(x+ox-1,y+ey-1,3,1 if blink else 3))
                if not blink:r.rect(surface,(30,39,57),(x+ox,y+ey,1,2))
            r.line(surface,(74,61,75),(x+7,y+ey+4),(x+8,y+ey+4))
            for ox in (3,12):r.rect(surface,(223,143,145),(x+ox,y+ey+3,1,1))
        if enemy.state==EnemyState.WINDUP:
            r.rect(surface,(255,222,126),(x+7,y-8,2,4));r.rect(surface,(255,222,126),(x+7,y-3,2,1))
        elif enemy.kind not in ('bat','blink_mage','crystal_warden','golem'):
            step=int(math.sin(enemy.age*11)*1.5)
            r.rect(surface,(49,59,71),(x+3,y+14+step,3,2));r.rect(surface,(49,59,71),(x+10,y+14-step,3,2))
    def death(self,surface,enemy,x,y):
        progress=max(0,min(1,enemy.attack_timer/.35))
        for i in range(6):
            a=i*math.tau/6;d=(1-progress)*14
            px,py=int(x+8+math.cos(a)*d),int(y+8+math.sin(a)*d)
            pygame.draw.rect(surface,(206,226,208),(px,py,2,2))
        if progress>.4:
            for ox in (5,10):
                pygame.draw.line(surface,(228,206,221),(x+ox-1,y+7),(x+ox+1,y+9))
                pygame.draw.line(surface,(228,206,221),(x+ox+1,y+7),(x+ox-1,y+9))
