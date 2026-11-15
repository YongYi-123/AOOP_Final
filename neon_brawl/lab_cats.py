"""New original compact lab cats: broad expressive heads, short grounded paws, clean outlines.
Lobby cat proportions informed the design; no Lobby sprite or recolored old Brawl frame is used.
"""
from dataclasses import dataclass
from functools import lru_cache
import pygame
SIZE=(26,22)
INK=(47,45,65)
@dataclass(frozen=True)
class CatDesign:
    name:str
    fur:tuple
    shade:tuple
    muzzle:tuple
    iris:tuple
    personality:str
DESIGNS=(
 CatDesign('MARMALADE',(228,165,99),(177,110,73),(250,225,180),(87,139,125),'curious'),
 CatDesign('SOCKS',(91,98,120),(68,75,98),(242,231,204),(113,174,153),'polite'),
 CatDesign('MISO',(169,185,201),(119,141,165),(232,229,211),(104,151,179),'thoughtful'),
 CatDesign('PATCH',(238,214,177),(181,127,90),(252,232,194),(137,155,127),'nosy'),
 CatDesign('CUSTARD',(237,218,170),(199,173,129),(255,239,202),(137,145,176),'sleepy'),
)
@lru_cache(maxsize=640)
def cat_sprite(variant,state='walk',frame=0,direction=1):
    variant%=len(DESIGNS);d=DESIGNS[variant];raw=pygame.Surface(SIZE,pygame.SRCALPHA);r=pygame.draw
    sitting=state in ('sit','observe','groom');sleeping=state in ('sleep','nap')
    hy=9 if sleeping else 7 if state=='stretch' else 4
    stride=((-2,0,2,0) if state in ('run','flee') else (-1,0,1,0))[frame%4] if state in ('walk','run','flee') else 0
    # All paws are at most three pixels long and remain attached to a compact body.
    if sitting:
        r.ellipse(raw,d.fur,(8,10,11,10))
        for x in (12,17):r.rect(raw,d.muzzle,(x,17,3,3))
        tail=[(10,17),(6,18),(4,17),(5,15+frame%2)]
    elif sleeping:
        r.ellipse(raw,d.fur,(4,12,19,8));tail=[(7,18),(4,18),(2,16),(3,14)]
    else:
        by=12 if state=='stretch' else 9 if state=='run' and frame%2 else 10
        r.ellipse(raw,d.fur,(5,by,15,7))
        for x,step in ((7,stride),(11,-stride),(16,-stride),(19,stride)):
            r.rect(raw,d.shade,(x+step,15,2,4));r.rect(raw,d.muzzle,(x+step,18,3,1))
        tail=[(6,13),(3,12),(2,8),(3+frame%2,5)]
    r.lines(raw,d.shade,False,tail,3);r.lines(raw,d.fur,False,tail,2)
    if variant in (0,2):
        for x in (8,12):r.line(raw,d.shade,(x,11 if not sleeping else 13),(x+1,14 if not sleeping else 16),2)
    elif variant==1:
        r.polygon(raw,d.muzzle,[(15,11),(20,12),(19,17),(15,18),(12,15)])
    elif variant==3:
        r.ellipse(raw,(190,122,79),(6,11,7,5));r.ellipse(raw,(86,84,102),(11,12,6,4))
    else:r.ellipse(raw,(246,232,189),(6,11,6,4))
    if variant==2:
        for x,y in ((3,8),(4,11),(5,14)):r.rect(raw,d.shade,(x,y,2,1))
        r.line(raw,d.shade,(10,11),(11,15))
    # Broad round head, small triangular ears and connected cream cheeks.
    r.ellipse(raw,d.fur,(11,hy+2,14,10))
    r.polygon(raw,d.fur,[(12,hy+5),(12,hy-1),(17,hy+3)])
    r.polygon(raw,d.shade if variant==3 else d.fur,[(19,hy+3),(23,hy-1),(24,hy+6)])
    r.rect(raw,(218,158,163),(13,hy+1,1,2));r.rect(raw,(218,158,163),(22,hy+1,1,2))
    if variant==1:r.polygon(raw,d.muzzle,[(18,hy+3),(20,hy+8),(23,hy+9),(20,hy+11),(14,hy+10),(14,hy+7)])
    if variant==3:r.ellipse(raw,(196,127,85),(11,hy+4,5,5))
    r.ellipse(raw,d.muzzle,(15,hy+7,9,4))
    if variant in (0,2):
        r.line(raw,d.shade,(17,hy+3),(17,hy+5));r.line(raw,d.shade,(20,hy+3),(19,hy+5))
    blink=sleeping or frame%8==7
    for x in (14,20):
        if blink:r.lines(raw,(103,96,116),False,[(x,hy+7),(x+1,hy+8),(x+2,hy+7)])
        else:
            r.rect(raw,(254,245,215),(x,hy+5,3,3),border_radius=1)
            dx=0 if state=='observe' and frame%4<2 else 1
            r.rect(raw,d.iris,(x+dx,hy+6,2,2));r.rect(raw,(253,248,225),(x+dx,hy+6,1,1))
    r.rect(raw,(207,136,151),(18,hy+8,2,1));r.lines(raw,(153,122,128),False,[(17,hy+10),(18,hy+11),(20,hy+10)])
    if state=='groom':
        r.line(raw,d.fur,(18,16),(21,hy+8+frame%2),3);r.rect(raw,d.muzzle,(20,hy+8+frame%2,2,2))
    # Outline the completed connected silhouette. Facial features never get detached rims.
    rim=pygame.mask.from_surface(raw).to_surface(setcolor=INK,unsetcolor=(0,0,0,0))
    s=pygame.Surface(SIZE,pygame.SRCALPHA)
    for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):s.blit(rim,(dx,dy))
    s.blit(raw,(0,0))
    return pygame.transform.flip(s,True,False) if direction<0 else s
