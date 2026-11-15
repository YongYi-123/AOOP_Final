"""Original transit engineering displays; plain names, no external logos."""
from functools import lru_cache
import pygame

DISPLAY_TITLES=('CPU / DECODE','GPU / PARALLEL COMPUTE','CLOCK / PIPELINE','MEMORY / DATA BUS')
@lru_cache(maxsize=4)
def schematic(index):
    from font import get_font
    index%=4;f=get_font();s=pygame.Surface((148,56));s.fill((13,28,39));r=pygame.draw
    cyan=(112,202,201);amber=(215,181,103)
    r.rect(s,(71,115,128),s.get_rect(),1)
    def text(label,x,y,color=cyan):s.blit(f.render(label,color),(x,y))
    def node(label,x,y,w=42):
        r.rect(s,(41,74,85),(x,y,w,12),1);text(label,x+3,y+3)
    text(DISPLAY_TITLES[index],5,4)
    if index==0:
        node('REGISTER',5,19,57);node('ALU',89,19,48);node('CACHE',44,36,53)
        r.lines(s,amber,False,[(62,25),(76,25),(76,42),(97,42)],1)
        r.line(s,cyan,(76,25),(89,25));r.line(s,cyan,(30,31),(44,42))
        text('INSTRUCTION DECODER',5,48,amber)
    elif index==1:
        text('NVIDIA / AMD',5,44,amber)
        for k in range(8):
            x=8+(k%4)*32;y=18+(k//4)*12
            r.rect(s,(72,137,130),(x,y,20,8),1)
            r.line(s,cyan,(x+4,y+3),(x+16,y+3))
    elif index==2:
        for i,label in enumerate(('IF','ID','EX','MEM','WB')):
            x=5+i*28;node(label,x,22,24)
            if i<4:r.line(s,amber,(x+24,28),(x+28,28))
        text('INTEL / TIMING LAB',5,43,amber)
    else:
        node('RAM',6,20,42);node('CACHE',94,20,47)
        r.lines(s,amber,False,[(27,32),(27,40),(115,40),(115,32)],2)
        text('CONTROL UNIT',5,46,amber)
    return s

def paint_hardware_displays(surface,section):
    # Fixed wall-mounted information panels above the walkable platform.
    for i,x in enumerate((10,370,550)):
        index=(section+i)%4
        surface.blit(schematic(index),(x,83 if section!=3 else 77))
        pygame.draw.rect(surface,(76,90,101),(x-2,81 if section!=3 else 75,152,60),1)
