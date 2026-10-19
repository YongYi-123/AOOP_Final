"""Original room-scale pixel compositions, cached once per authored chamber."""
import math
import pygame
from puzzle_maze.themes import THEMES
from puzzle_maze.environment import tint

class RoomArt:
    def __init__(self):self.cache={};self.ambient={}
    def layer(self,room):
        key=room['name'],room.get('layout_revision'),room.get('seed',0)
        if key in self.cache:return self.cache[key]
        rows=room['tiles'];w,h=len(rows[0])*16,len(rows)*16
        surface=pygame.Surface((w,h),pygame.SRCALPHA);r=pygame.draw;t=THEMES[room.get('theme','entrance')]
        style=room.get('architecture','arched');seed=room.get('seed',0)
        for y,row in enumerate(rows):
            for x,tile in enumerate(row):
                if tile not in '.g':continue
                sx,sy=x*16,y*16
                if style=='runners' and y in (7,8) and 2<=x<=17:
                    r.rect(surface,(*tint(t.floor,-10),210),(sx,sy,16,16))
                    if y==7:r.line(surface,(*tint(t.accent,-95),180),(sx,sy+1),(sx+15,sy+1))
                    if y==8:r.line(surface,(*tint(t.accent,-95),180),(sx,sy+14),(sx+15,sy+14))
                elif style=='mosaic' and (x+y)%3==0:
                    r.polygon(surface,(*tint(t.accent,-95),70),[(sx+8,sy+3),(sx+13,sy+8),(sx+8,sy+13),(sx+3,sy+8)],1)
                elif style=='fractured' and (x*17+y*13+seed)%11==0:
                    r.lines(surface,(*t.shadow,180),False,[(sx+2,sy+1),(sx+6,sy+5),(sx+4,sy+8),(sx+11,sy+12)])
                elif style=='arched' and x%4==0 and y%4==1:
                    r.rect(surface,(*tint(t.wall,5),65),(sx+2,sy+2,12,12),1)
                if y>0 and rows[y-1][x] in '#O':r.rect(surface,(*t.shadow,100),(sx,sy,16,3))
                if x>0 and row[x-1] in '#O':r.rect(surface,(*t.shadow,65),(sx,sy,3,16))
        for motif in room.get('motifs',[]):
            if motif['kind']!='medallion':continue
            x,y=motif['pos'];center=(x*16+8,y*16+8)
            r.circle(surface,(*tint(t.accent,-35),65),center,22,1)
            for i in range(3 if t.material in ("wood","crystal","ore") else 6):
                a=i*math.pi/4;r.line(surface,(*tint(t.accent,-20),65),(int(center[0]+math.cos(a)*15),int(center[1]+math.sin(a)*15)),(int(center[0]+math.cos(a)*21),int(center[1]+math.sin(a)*21)))
        # Clip every motif to actual floor. It cannot visually paint over walls or water.
        for y,row in enumerate(rows):
            for x,tile in enumerate(row):
                if tile not in '.g':surface.fill((0,0,0,0),(x*16,y*16,16,16))
        self.cache[key]=surface;return surface
    def draw(self,target,room,camera,time):
        if room.get('layout_revision')!='4.0':return
        cx,cy=camera;target.blit(self.layer(room),(-cx,-cy))
        t=THEMES[room.get('theme','entrance')];r=pygame.draw
        # Sparse drifting motes use deterministic paths and avoid allocating particles.
        for i in range(3 if t.material in ("wood","crystal","ore") else 6):
            x=int((i*73+room.get('seed',0)+math.sin(time*.6+i)*9)%416)-cx
            y=int((i*43-time*6)%256)-cy
            if 0<x<320 and 0<y<180:r.rect(target,tint(t.light,-35),(x,y,1,1))
