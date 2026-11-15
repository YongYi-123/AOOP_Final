"""Original forgotten workshop; the cabinets adapt the Arcade Floor's real sprites."""
import sys
from pathlib import Path
import pygame
from puzzle_maze.studio_layout import SIZE,FURNITURE
from puzzle_maze.pixel_font import render
R=pygame.draw
INK=(54,43,39);WOOD=(116,84,58);TOP=(169,135,91);EDGE=(202,170,120)

def cabinet(kind):
    host=str(Path(__file__).resolve().parents[1]/'arcade_lobby')
    if host not in sys.path:sys.path.append(host)
    from machine import _build_cabinet
    style={'cab_cracked':'racer','cab_open':'galaxy','cab_frozen':'maze','prototype':'brawl'}[kind]
    s=_build_cabinet(style,'',0,(140,129,105),(118,154,147))
    tint=pygame.Surface(s.get_size(),pygame.SRCALPHA);tint.fill((184,176,159,255));s.blit(tint,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    R.rect(s,(22,33,38),(6,15,24,16))
    if kind=='cab_cracked':
        for a,b in (((12,16),(19,22)),((19,22),(16,28)),((19,22),(27,20)),((19,22),(25,29))):R.line(s,(169,190,172),a,b)
        R.rect(s,(83,102,90),(8,18,4,3));R.line(s,(196,141,85),(5,45),(12,54))
    elif kind=='cab_open':
        R.rect(s,(35,40,38),(4,13,28,42));R.rect(s,(72,101,78),(7,17,21,19))
        for x in (9,17,23):
            R.rect(s,(43,54,51),(x,20,4,7));R.line(s,(166,149,94),(x+1,28),(x+1,33))
        for i,c in enumerate(((157,101,77),(104,135,143),(184,152,91))):R.lines(s,c,False,[(8+i*7,34),(13+i*3,41),(8+i*6,50)],1)
        R.rect(s,(110,108,86),(5,52,24,3))
    elif kind=='cab_frozen':
        s.blit(render('ERR',8,(150,177,147)),(9,18));R.line(s,(92,119,115),(7,28),(28,28))
        for x,y in ((3,4),(26,9),(4,55),(28,46)):s.fill((141,124,94),(x,y,3,1))
    else:
        R.rect(s,(82,107,97),(7,17,22,12));R.rect(s,(178,183,149),(15,20,4,4))
        R.rect(s,(38,42,40),(5,44,26,12));R.rect(s,(101,124,88),(9,46,19,8))
        for x in (11,18,24):R.circle(s,(61,65,56),(x,50),2)
        R.line(s,(187,151,86),(2,8),(31,8));s.blit(render('07',8,(188,163,117)),(12,0))
    for x in (3,12,24,30):s.fill((142,126,99),(x,10,2,1))
    return s

def monitor(s,x,y):
    R.polygon(s,(93,104,96),[(x+2,y),(x+25,y),(x+30,y+4),(x+29,y+22),(x+1,y+22)])
    R.rect(s,(172,164,133),(x,y,25,21));R.rect(s,(28,49,48),(x+3,y+3,19,13))
    for yy in (6,9,12):R.line(s,(113,157,126),(x+5,y+yy),(x+18-yy//3,y+yy))
    R.rect(s,(96,96,78),(x+10,y+21,5,4));R.rect(s,(155,143,111),(x+5,y+25,16,2))

def sprite(item):
    s=pygame.Surface(item.bounds[2:],pygame.SRCALPHA);k=item.name
    if k.startswith('cab_') or k=='prototype':
        s.blit(cabinet(k),(0,0))
        if k=='prototype':
            R.rect(s,(105,108,87),(36,23,7,31));R.line(s,(183,137,81),(39,25),(39,51))
            for yy in (28,37,46):R.rect(s,(65,87,72),(37,yy,5,5))
    elif k=='desk':
        R.polygon(s,INK,[(2,29),(114,29),(119,38),(117,52),(1,52)])
        R.polygon(s,TOP,[(4,26),(113,26),(119,43),(0,43)])
        R.line(s,EDGE,(4,27),(112,27));R.rect(s,WOOD,(0,43,120,5))
        for x in (3,81):
            R.rect(s,(85,62,46),(x,48,5 if x==3 else 35,21))
            if x==81:
                for yy in (50,58):R.rect(s,(139,106,70),(84,yy,29,7));R.rect(s,(196,160,106),(96,yy+2,6,2))
        monitor(s,8,1);monitor(s,55,3)
        R.polygon(s,(166,158,125),[(12,33),(45,33),(48,40),(10,40)])
        for xx in range(15,44,4):R.line(s,(77,75,64),(xx,35),(xx,38))
        R.ellipse(s,(181,172,133),(51,35,5,7));R.rect(s,(68,110,78),(65,32,20,9))
        for xx in (70,79):R.circle(s,(34,48,42),(xx,36),3);R.circle(s,(144,153,111),(xx,36),2,1)
        R.line(s,(80,78,61),(106,31),(106,14),2);R.polygon(s,(216,176,111),[(100,13),(112,13),(116,21),(96,21)])
        for i in range(3):R.line(s,(176,147,101),(89+i*4,38),(92+i*4,31));R.rect(s,(110,74,51),(88+i*4,38,2,4))
    elif k=='cart':
        R.polygon(s,TOP,[(2,6),(37,6),(43,15),(0,15)]);R.rect(s,WOOD,(0,15,44,4))
        for x in (3,37):R.rect(s,(81,75,61),(x,19,3,16));R.circle(s,INK,(x+1,36),3)
        R.rect(s,(106,110,88),(4,26,35,6))
        R.rect(s,(75,116,82),(7,8,12,6));R.rect(s,(33,51,43),(10,9,5,3))
        R.ellipse(s,(81,77,66),(23,7,14,7));R.circle(s,(149,114,85),(27,10),2);R.circle(s,(154,140,88),(33,10),1)
        R.line(s,(156,163,148),(32,3),(21,7),2);R.rect(s,(111,83,63),(32,1,8,3))
    elif k=='food':
        R.rect(s,WOOD,(0,3,28,20));R.rect(s,INK,(3,6,22,14))
        for x in (5,12,19):R.rect(s,(154,162,123),(x,9,5,9));R.rect(s,(213,190,137),(x,11,5,2))
    elif k=='cushion':
        R.ellipse(s,(80,61,51),(0,6,40,15));R.ellipse(s,(180,137,126),(1,2,38,16));R.ellipse(s,(210,181,147),(5,4,30,10))
        R.rect(s,(127,150,124),(15,3,15,7));R.line(s,(189,199,153),(17,6),(28,6))
        for x in (5,30):R.line(s,(132,95,94),(x,12),(x+3,13))
    edge=pygame.mask.from_surface(s).to_surface(setcolor=(*INK,255),unsetcolor=(0,0,0,0))
    out=pygame.Surface(s.get_size(),pygame.SRCALPHA)
    for off in ((-1,0),(1,0),(0,-1),(0,1)):out.blit(edge,off)
    out.blit(s,(0,0));return out

class WorkshopArt:
    revision='forgotten-workshop-4'
    def __init__(self):self.base=None;self.cached=None;self.parts={};self.masks={}
    def floor(self):
        if self.base is not None:return self.base
        s=pygame.Surface(SIZE);s.fill((124,113,92));R.rect(s,(150,137,110),(12,7,296,36))
        for x in range(16,310,23):R.line(s,(135,123,101),(x,8),(x,43))
        R.rect(s,(81,72,61),(12,42,296,6))
        for y in range(48,235,12):
            for x in range(-20 if y%24 else 0,320,40):
                R.rect(s,(114+(x//40)%2*4,91,65),(x+1,y,39,11));R.line(s,(130,105,75),(x+4,y+2),(x+33,y+2))
        for x in (11,305):R.rect(s,(90,76,59),(x,42,5,198))
        R.rect(s,(74,64,52),(12,233,296,7))
        # A service door, wiring channels and a tool pegboard; no domestic furniture.
        R.rect(s,(135,102,68),(7,105,24,37));R.rect(s,(65,57,49),(12,110,17,27));R.rect(s,(179,142,94),(9,107,21,33),1)
        R.lines(s,(57,64,59),False,[(18,31),(168,31),(168,132),(51,132),(51,140)],2)
        R.rect(s,(85,74,57),(184,12,108,23))
        for x in range(188,290,6):
            for y in (16,22,28):s.fill((54,52,44),(x,y,1,1))
        for x in (190,202,214):R.line(s,(167,164,138),(x,17),(x+3,28),2);R.rect(s,(122,85,57),(x+1,25,4,6))
        R.circle(s,(159,151,120),(230,22),5,2);R.rect(s,(93,118,99),(244,16,14,13))
        for xx in range(246,257,3):R.line(s,(176,155,105),(xx,18),(xx,26))
        R.rect(s,(178,164,123),(275,16,10,14));R.line(s,(129,103,74),(278,20),(282,20))
        for f in FURNITURE:
            x,y,w,h=f.footprint;R.ellipse(s,(77,65,50),(x-2,y+h-5,w+5,8))
        # The prototype's marked service bay and a narrow cable route establish depth.
        for x,y in ((28,132),(77,132),(28,205),(77,205)):
            R.line(s,(177,143,80),(x,y),(x+6,y));R.line(s,(177,143,80),(x,y),(x,y+4))
        R.lines(s,(67,67,55),False,[(70,168),(93,168),(93,121),(184,121),(184,105)],2)
        # Small affectionate corner, not a bedroom.
        for x,c in ((259,(159,124,87)),(279,(109,146,142))):R.ellipse(s,(70,62,50),(x,208,14,5));R.ellipse(s,c,(x+1,207,12,4))
        R.circle(s,(165,120,117),(306,196),2)
        self.base=s;return s
    def sprite(self,item,ghost=False):
        if item.name not in self.parts:self.parts[item.name]=sprite(item)
        return self.parts[item.name]
    def layer(self):
        if self.cached is None:
            self.cached=self.floor().copy()
            for f in sorted(FURNITURE,key=lambda f:f.footprint[1]+f.footprint[3]):self.cached.blit(self.sprite(f),f.bounds[:2])
        return self.cached
    def occludes(self,item,actor):
        if not pygame.Rect(item.bounds).colliderect(actor):return False
        mask=pygame.mask.from_surface(self.sprite(item));return mask.overlap(pygame.mask.Mask(actor.size,fill=True),(actor.x-item.bounds[0],actor.y-item.bounds[1])) is not None
    def effects(self,s,time,effect):
        # A slow grey return-pixel travels between the prototype and Kevin's bench.
        x=94+int(time*9)%90;s.fill((168,181,157),(x,120,2,2))
        if int(time*3)%4:s.fill((124,161,128),(18+32,160,3,1))
        for i in range(6):
            if int(time+i)%3==0:s.fill((157,140,106),(182+i*17,52+int((i*13+time)%42),1,1))
    def draw(self,target,camera,time,effect=None):target.blit(self.layer(),(-camera[0],-camera[1]))
