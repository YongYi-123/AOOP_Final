"""Ambient researchers: a deterministic work cycle, never fighters or colliders."""
from dataclasses import dataclass
from functools import lru_cache
import pygame
from .research_art import text
CYCLES={
 'programmer':('typing','typing','error','coffee','sleep','wake'),
 'electronics':('solder','solder','inspect','adjust','startle','inspect'),
 'debugger':('point','scratch','point','frustrated','coffee','scratch'),
 'student':('typing','coffee','sleep','sleep','wake','typing'),
}
MESSAGES={'programmer':'SEGMENTATION FAULT','electronics':'TIMING VIOLATION','debugger':'WHY DOES THIS WORK?','student':'ONE MORE SIMULATION'}
@dataclass
class Engineer:
    role:str
    x:float
    y:float=174.
    state:str='typing'
    timer:float=0.
    variant:int=0

class LabStaff:
    def __init__(self):self.people=[];self.key=None
    def update(self,dt,time,stage,section,player=None,enemies=(),camera=0.):
        key=(stage,section)
        if key!=self.key:
            self.key=key
            roles=tuple(CYCLES) if stage==1 else ('programmer','student')
            self.people=[Engineer(role,70+i*(200 if stage==1 else 400),variant=(i+section)%4) for i,role in enumerate(roles)]
        for i,person in enumerate(self.people):
            person.timer+=max(0,dt)
            person.state=CYCLES[person.role][int((person.timer+i*2.4)/2.4)%6]
    def draw(self,s,camera,time):
        offset=int(camera*.55)%800
        for p in self.people:
            x=int(p.x-offset)%800
            if not -25<x<425:continue
            image=engineer_sprite(p.role,p.state,int(time*6)%4,p.variant)
            s.blit(image,(x-24,int(p.y)-42))
            # Errors live on a dedicated tiny console, never above combat actors.
            if p.state in ('error','frustrated','startle'):
                s.fill((222,143,143),(x-14,140,18,1))
                s.fill((222,143,143),(x-14,143,12,1))

@lru_cache(maxsize=512)
def engineer_sprite(role,state,frame,variant):
    s=pygame.Surface((48,42),pygame.SRCALPHA);r=pygame.draw
    ink=(30,38,55);skin=((222,184,143),(183,144,120),(213,171,146),(166,127,113))[variant%4]
    coat=((117,164,161),(145,139,173),(177,151,118),(111,153,182))[variant%4]
    # Three slightly angled monitor faces, a stool and an attached desk in perspective.
    for i in range(3 if role in ('programmer','student') else 2):
        x=2+i*15;r.rect(s,(51,65,82),(x,1,14,13));r.rect(s,(151,171,161),(x+1,1,12,10))
        r.rect(s,(19,44,55),(x+2,3,10,6));r.line(s,(125,203,168),(x+3,5),(x+9,5))
        r.rect(s,(83,106,119),(x+6,11,3,4))
    r.rect(s,(66,72,89),(14,28,20,12));r.rect(s,(96,111,122),(16,28,16,10))
    r.rect(s,coat,(18,25,13,10));r.line(s,(205,196,164),(23,27),(23,34))
    asleep=state=='sleep';head_y=22 if asleep else 15
    r.rect(s,ink,(18,head_y-1,12,10));r.rect(s,skin,(19,head_y,10,9),border_radius=2)
    r.polygon(s,(67,55,68),[(18,head_y+3),(18,head_y-1),(22,head_y-3),(26,head_y),(29,head_y-2),(30,head_y+4)])
    for x in (21,26):
        if asleep:r.line(s,(86,76,82),(x,head_y+5),(x+1,head_y+5))
        else:r.rect(s,(244,233,210),(x,head_y+4,2,2));r.rect(s,(74,93,107),(x+1,head_y+5,1,1))
    r.polygon(s,(94,96,104),[(0,34),(42,34),(48,39),(3,39)]);r.line(s,(183,167,131),(2,34),(42,34))
    r.rect(s,(190,188,162),(16,34,16,3));r.line(s,(91,105,113),(18,35),(29,35))
    for x in (15,31):
        y=32+(frame%2 if state=='typing' else 0)
        r.line(s,coat,(19 if x==15 else 29,27),(x,y),3);r.rect(s,skin,(x-1,y,3,2))
    if state=='coffee':
        r.line(s,coat,(30,28),(34,22),3);r.rect(s,(222,195,152),(31,20,5,6));r.rect(s,skin,(31,25,3,2))
    if state in ('scratch','frustrated','wake'):
        r.line(s,coat,(30,28),(33,16),3);r.rect(s,skin,(30,15,5,3))
    if state in ('point','inspect','adjust'):
        r.line(s,coat,(17,28),(8,20+frame%2),3);r.rect(s,skin,(6,18+frame%2,4,3))
    if role=='electronics':
        r.rect(s,(47,102,87),(3,30,11,5));r.line(s,(211,176,112),(12,28),(16,34),2)
        if state=='startle':r.lines(s,(246,205,119),False,[(6,28),(9,25),(11,29),(14,26)],1)
    if role=='debugger':r.rect(s,(130,164,159),(2,15,10,12));r.line(s,(209,190,143),(4,18),(9,22))
    if role=='student':
        for y,c in ((27,(161,113,140)),(30,(113,145,173))):r.rect(s,c,(35,y,10,3))
    return s
