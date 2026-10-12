"""Cached original pixel tiles, mounted decorations and inexpensive light animation."""
import math
import pygame
from puzzle_maze.themes import THEMES

def tint(color,amount):return tuple(max(0,min(255,c+amount)) for c in color)

class EnvironmentPainter:
    def __init__(self):self.cache={};self.glows={};self.base={}

    def tiles(self,name):
        if name not in self.base:self.base[name]={k:self.tile(name,k,0) for k in '#.~Ogv'}
        return self.base[name]

    def tile(self,name,kind,variant=0):
        key=name,kind,variant
        if key in self.cache:return self.cache[key]
        t=THEMES[name];s=pygame.Surface((16,16));r=pygame.draw
        dark=tint(t.floor,-16);bright=tint(t.floor,11)
        if kind=='v':s.fill(tint(t.shadow,-15))
        elif kind=='#':
            s.fill(t.shadow);r.rect(s,t.wall,(0,0,16,12));r.line(s,tint(t.wall,32),(1,1),(14,1))
            r.line(s,tint(t.wall,-35),(0,7),(15,7));r.line(s,tint(t.wall,-35),(8,0),(8,6));r.line(s,tint(t.wall,-35),(3,8),(3,11))
            r.line(s,tint(t.shadow,-10),(0,15),(15,15))
            if t.material=='metal':
                for x,y in ((2,3),(13,3),(7,10)):r.rect(s,t.accent,(x,y,1,1))
                r.line(s,tint(t.wall,-15),(1,5),(14,5))
            elif t.material=='wood':
                r.rect(s,(74,48,42),(1,2,14,8))
                for x,c in ((2,(171,82,75)),(5,(117,143,119)),(8,(89,121,148)),(11,(201,163,109))):
                    r.rect(s,c,(x,3,2,6));r.line(s,t.accent,(x,4),(x+1,4))
            elif t.material in ('crystal','inlay','star'):
                r.polygon(s,tint(t.wall,20),[(3,3),(8,2),(13,4),(9,6),(4,5)],1)
        elif kind=='~':
            s.fill((25,57,83));r.line(s,(67,153,171),(1,4),(7,4));r.line(s,(67,153,171),(8,10),(14,10))
        else:
            s.fill(t.floor)
            if t.material=='wood':
                for y in (0,5,11):r.line(s,dark,(0,y),(15,y));r.line(s,bright,(1,y+1),(14,y+1))
                r.line(s,dark,(5+variant,1),(5+variant,4));r.ellipse(s,dark,(9,7,4,2),1)
            elif t.material=='metal':
                r.rect(s,bright,(1,1,14,14),1)
                for x,y in ((2,2),(13,2),(2,13),(13,13)):r.rect(s,dark,(x,y,1,1))
                if variant==2:r.circle(s,tint(t.accent,-70),(8,8),3,1)
            elif t.material in ('crystal','inlay'):
                r.polygon(s,bright,[(8,1),(15,8),(8,15),(1,8)],1)
                if variant==2:r.polygon(s,tint(t.accent,-65),[(8,5),(11,8),(8,11),(5,8)],1)
            elif t.material=='star':
                r.rect(s,dark,(1,1,14,14),1)
                if variant in (1,3):r.line(s,tint(t.accent,-60),(4,4),(9,10));r.rect(s,t.accent,(4,4,1,1));r.rect(s,t.accent,(9,10,1,1))
            else:
                r.rect(s,bright,(1,1,14,14));r.line(s,dark,(0,15),(15,15))
                if variant==1:r.lines(s,dark,False,[(5,1),(7,5),(4,8),(6,13)])
                elif variant==3:r.line(s,tint(t.floor,-10),(5,8),(9,8))
            if kind=='g':
                for x,y in ((2,5),(9,12),(13,4)):r.lines(s,(72,110,79),False,[(x-1,y-2),(x,y),(x+1,y-3)])
            if kind=='O':
                r.ellipse(s,t.shadow,(1,10,14,6))
                if t.material=='wood':
                    r.rect(s,(113,77,57),(2,2,12,12));r.line(s,t.accent,(2,7),(13,7))
                    for x in (4,7,10):r.rect(s,(161,112,75),(x,3,2,3));r.rect(s,(98,130,123),(x,9,2,3))
                elif t.material=='crystal':
                    r.polygon(s,(100,185,199),[(3,11),(5,2),(9,1),(12,6),(10,13)])
                    r.polygon(s,(173,243,228),[(5,2),(9,1),(8,10)]);r.line(s,(72,116,166),(8,10),(10,13))
                else:
                    r.rect(s,tint(t.wall,-15),(2,11,12,3));r.rect(s,t.wall,(5,3,6,8))
                    r.rect(s,tint(t.wall,25),(4,2,8,3));r.line(s,tint(t.wall,35),(6,5),(6,10))
                    r.rect(s,t.shadow,(9,6,1,4))
        self.cache[key]=s
        return s

    def glow(self,name):
        if name not in self.glows:
            g=pygame.Surface((64,64),pygame.SRCALPHA);color=THEMES[name].light
            for radius in range(28,3,-4):pygame.draw.circle(g,(*color,3+(28-radius)//2),(32,32),radius)
            self.glows[name]=g
        return self.glows[name]

    def decorations(self,target,room,camera,time):
        name=room.get('theme','entrance');t=THEMES[name];r=pygame.draw;cx,cy=camera
        for d in room.get('decorations',[]):
            x,y=d['pos'];sx,sy=x*16-cx,y*16-cy
            if not -32<sx<352 or not -32<sy<240:continue
            phase=time*5+d.get('phase',0);kind=d['kind']
            if kind in ('torch','crystal','sigil'):
                target.blit(self.glow(name),(sx-24,sy-24))
            if kind=='torch':
                r.rect(target,t.shadow,(sx+6,sy+5,5,10));r.rect(target,t.accent,(sx+7,sy+8,3,5))
                flicker=int(math.sin(phase*2)*2)
                r.polygon(target,(253,166,74),[(sx+5,sy+7),(sx+8,sy+2+flicker),(sx+11,sy+7),(sx+9,sy+10),(sx+7,sy+10)])
                r.rect(target,(255,230,137),(sx+7,sy+6,2,3))
            elif kind=='gear':
                r.circle(target,t.shadow,(sx+8,sy+8),7);r.circle(target,t.accent,(sx+8,sy+8),5,1)
                for i in range(4):
                    a=phase*.25+i*math.pi/2
                    r.line(target,t.accent,(sx+8,sy+8),(int(sx+8+math.cos(a)*6),int(sy+8+math.sin(a)*6)),2)
                r.rect(target,t.wall,(sx+7,sy+7,3,3))
            elif kind=='books':
                r.rect(target,(61,41,36),(sx+1,sy+2,14,11))
                for i,c in enumerate(((176,80,73),(99,142,118),(82,124,161),(215,183,116))):
                    r.rect(target,c,(sx+2+i*3,sy+3+(i%2),2,8-i%2));r.line(target,t.accent,(sx+2+i*3,sy+6),(sx+3+i*3,sy+6))
                r.line(target,t.wall,(sx+1,sy+13),(sx+14,sy+13),2)
            elif kind=='rack':
                r.line(target,(87,53,42),(sx+2,sy+5),(sx+14,sy+5),2)
                for ox in (5,11):
                    r.line(target,(195,211,213),(sx+ox,sy+1),(sx+ox,sy+13),2);r.line(target,t.accent,(sx+ox-2,sy+9),(sx+ox+2,sy+9))
            elif kind=='crystal':
                r.polygon(target,t.accent,[(sx+3,sy+10),(sx+6,sy+2),(sx+10,sy+3),(sx+13,sy+11),(sx+8,sy+14)])
                r.line(target,(208,250,245),(sx+6,sy+3),(sx+8,sy+11))
                if int(phase)%3==0:r.rect(target,(243,254,243),(sx+10,sy+4,1,1))
            elif kind=='banner':
                r.line(target,t.accent,(sx+2,sy+2),(sx+14,sy+2),2)
                r.polygon(target,(100,59,127),[(sx+4,sy+3),(sx+12,sy+3),(sx+12,sy+12),(sx+8,sy+15),(sx+4,sy+12)])
                r.polygon(target,t.accent,[(sx+8,sy+5),(sx+10,sy+8),(sx+8,sy+11),(sx+6,sy+8)],1)
            else:
                r.circle(target,t.accent,(sx+8,sy+7),5,1)
                r.lines(target,t.accent,False,[(sx+5,sy+7),(sx+8,sy+4),(sx+11,sy+7),(sx+8,sy+10),(sx+5,sy+7)])
