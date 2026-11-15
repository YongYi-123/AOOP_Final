"""Friendly jelly expressions, kept inside one animated body at native scale."""
from functools import lru_cache
import pygame
@lru_cache(maxsize=48)
def slime_frame(state='idle',frame=0,hurt=False):
    s=pygame.Surface((16,16),pygame.SRCALPHA);r=pygame.draw
    squash=(0,1,0,-1)[frame%4]
    top=5+squash;height=9-squash
    if state=='defeat':top=11;height=4
    body=(238,198,139) if hurt else (124,199,133)
    r.ellipse(s,(60,108,102),(1,top,14,height+1));r.ellipse(s,body,(2,top,12,height))
    r.ellipse(s,(171,224,160),(4,top+1,5,2))
    ey=top+3 if state!='defeat' else 12
    blink=frame%4==3 and state=='idle'
    for x in (4,9):
        if blink:r.line(s,(63,121,121),(x,ey+1),(x+2,ey+1))
        else:
            r.rect(s,(245,249,220),(x,ey,3,3 if state!='defeat' else 2),border_radius=1)
            r.rect(s,(59,115,126),(x+1,ey+1,1,1))
        if state!='defeat':r.rect(s,(230,159,155),(x-1,ey+3,2,1))
    if state!='defeat':
        r.lines(s,(85,112,107),False,[(7,ey+3),(7,ey+4),(8,ey+4),(8,ey+3)])
    return s
