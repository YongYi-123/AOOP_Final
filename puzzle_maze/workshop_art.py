"""Original forgotten workshop; the cabinets adapt the Arcade Floor's real sprites."""
import sys
from pathlib import Path
import pygame
from puzzle_maze.studio_layout import SIZE,FURNITURE
from puzzle_maze.pixel_font import render
R=pygame.draw
INK=(28,32,36);WOOD=(66,73,77);TOP=(106,113,115);EDGE=(145,149,145)

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
    k=item.name
    native={'cab_cracked':(36,62),'cab_open':(36,62),'cab_frozen':(36,62),
            'prototype':(44,62),'desk':(120,70),'cart':(44,39),
            'food':(28,25),'cushion':(40,21),'server':(26,46)}
    s=pygame.Surface(native.get(k,item.bounds[2:]),pygame.SRCALPHA)
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
        R.rect(s,(65,74,63),(95,35,9,6));s.fill((189,126,77),(97,37,1,1))
        R.line(s,(174,181,158),(100,33),(105,27));R.line(s,(115,77,52),(98,35),(101,31),2)
    elif k=='cart':
        R.polygon(s,TOP,[(2,6),(37,6),(43,15),(0,15)]);R.rect(s,WOOD,(0,15,44,4))
        for x in (3,37):R.rect(s,(81,75,61),(x,19,3,16));R.circle(s,INK,(x+1,36),3)
        R.rect(s,(106,110,88),(4,26,35,6))
        R.rect(s,(75,116,82),(7,8,12,6));R.rect(s,(33,51,43),(10,9,5,3))
        R.ellipse(s,(81,77,66),(23,7,14,7));R.circle(s,(149,114,85),(27,10),2);R.circle(s,(154,140,88),(33,10),1)
        R.line(s,(156,163,148),(32,3),(21,7),2);R.rect(s,(111,83,63),(32,1,8,3))
    elif k=='server':
        R.rect(s,(40,46,50),(1,1,24,43));R.rect(s,(103,110,110),(1,1,24,43),1)
        for yy in (5,16,27):
            R.rect(s,(63,70,73),(4,yy,18,9))
            for xx in range(7,21,3):R.line(s,(25,30,34),(xx,yy+2),(xx,yy+6))
            s.fill((127,161,133),(5,yy+3,1,1))
        R.line(s,(137,100,75),(2,37),(8,42))
        R.lines(s,(122,113,88),False,[(23,8),(18,12),(23,22),(17,35),(24,39)])
    elif k=='food':
        R.rect(s,WOOD,(0,3,28,20));R.rect(s,INK,(3,6,22,14))
        for x in (5,12,19):R.rect(s,(154,162,123),(x,9,5,9));R.rect(s,(213,190,137),(x,11,5,2))
    elif k=='cushion':
        R.ellipse(s,(80,61,51),(0,6,40,15));R.ellipse(s,(180,137,126),(1,2,38,16));R.ellipse(s,(210,181,147),(5,4,30,10))
        R.rect(s,(127,150,124),(15,3,15,7));R.line(s,(189,199,153),(17,6),(28,6))
        for x in (5,30):R.line(s,(132,95,94),(x,12),(x+3,13))
    # Dusty desaturated materials, with readable screens and worn edges.
    tint=pygame.Surface(s.get_size(),pygame.SRCALPHA);tint.fill((171,186,197,255))
    s.blit(tint,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    if s.get_size()!=item.bounds[2:]:s=pygame.transform.scale(s,item.bounds[2:])
    # Final-resolution damage stays legible after furniture has been reduced.
    if k.startswith('cab_') or k=='prototype':
        w,h=s.get_size()
        for x,y in ((2,7),(w-4,h-8),(4,h-3)):
            R.line(s,(120,125,122),(x,y),(x+2,y))
            s.fill((49,55,58),(x,y+1,1,1))
        if k=='cab_open':
            for dx,color in ((0,(126,104,83)),(3,(82,125,128)),(6,(120,113,132))):
                R.lines(s,color,False,[(6+dx,23),(9+dx,27),(5+dx,32),(10+dx,36)])
        else:
            R.line(s,(62,76,78),(w-4,5),(w-6,13))
    elif k=='desk':
        for x in (8,39,62):
            R.line(s,(154,154,143),(x,29),(x+6,29))
        R.lines(s,(63,91,97),False,[(48,30),(51,35),(45,39),(52,41)])
        R.rect(s,(48,56,60),(64,34,15,6),1)
    elif k=='server':
        R.line(s,(128,100,78),(2,30),(7,33))
        for y in (9,19,28):s.fill((119,165,153),(3,y,1,1))
    edge=pygame.mask.from_surface(s).to_surface(setcolor=(*INK,255),unsetcolor=(0,0,0,0))
    out=pygame.Surface(s.get_size(),pygame.SRCALPHA)
    for off in ((-1,0),(1,0),(0,-1),(0,1)):out.blit(edge,off)
    out.blit(s,(0,0));return out

class WorkshopArt:
    revision='warehouse-workshop-6'
    def __init__(self):self.base=None;self.cached=None;self.parts={};self.masks={}
    def floor(self):
        if self.base is not None:return self.base
        s=pygame.Surface(SIZE);s.fill((55,61,66))
        # Stained concrete and sheet-metal walls; a cold, long-abandoned storeroom.
        R.rect(s,(72,79,84),(12,7,296,39))
        for x in range(16,310,24):
            R.line(s,(49,56,62),(x,8),(x,44))
            for y in (13,39):s.fill((119,123,120),(x+2,y,1,1))
        R.rect(s,(31,37,42),(12,42,296,6))
        # Broad poured concrete, patches and hairline fractures rather than a tile grid.
        R.rect(s,(62,67,70),(16,48,288,185))
        for i in range(520):
            x=17+(i*71)%286;y=49+(i*47)%183
            color=((70,74,76),(52,58,62),(79,81,80),(58,63,66))[i%4]
            s.fill(color,(x,y,1+i%2,1))
        for points in (
            [(16,74),(38,78),(47,72),(62,75)],
            [(173,50),(170,66),(175,74),(169,87)],
            [(20,214),(42,209),(51,214),(65,212),(71,220)],
            [(181,233),(176,220),(182,211),(178,204)],
            [(302,106),(286,110),(280,117),(269,114)]):
            R.lines(s,(39,46,50),False,points,1)
            x,y=points[-1];R.line(s,(88,90,87),(x+1,y),(x+3,y+2))
        for x,y in ((107,197),(217,130),(160,155)):
            R.ellipse(s,(56,62,65),(x,y,22,7),1)
            R.line(s,(72,76,77),(x+4,y+4),(x+14,y+5))
        for x in (11,305):R.rect(s,(35,41,46),(x,42,5,198))
        R.rect(s,(33,39,43),(12,233,296,7))
        R.rect(s,(98,103,102),(7,105,24,37));R.rect(s,(25,31,36),(12,110,17,27))
        R.rect(s,(141,126,93),(9,107,21,33),1)
        # Overhead conduit, dead fluorescent tube and exposed fuse board.
        R.lines(s,(107,111,108),False,[(18,19),(170,19),(170,46)],2)
        R.rect(s,(34,40,45),(186,12,105,25))
        for x in (192,212,232):
            R.rect(s,(84,91,94),(x,17,14,15));R.rect(s,(31,36,41),(x+3,20,8,5))
            R.lines(s,(122,99,78),False,[(x+6,30),(x+9,39),(x+1,45)],1)
        R.rect(s,(32,38,42),(72,11,62,7));R.rect(s,(160,174,169),(76,13,53,2))
        # Loose leads loop around the cabinets and the testing bench.
        for color,points in (
            ((31,36,40),[(53,99),(57,113),(85,116),(100,108),(141,111),(160,123),(182,119),(190,106)]),
            ((110,91,75),[(91,98),(87,106),(72,111),(63,107),(68,101),(101,104),(110,115),(159,116)]),
            ((76,95,99),[(145,96),(152,110),(141,116),(134,110),(139,105),(167,110),(178,120)]),
            ((30,36,40),[(63,186),(82,192),(96,183),(91,172),(80,177),(91,190),(115,189),(123,175)]),
            ((106,101,81),[(228,172),(244,180),(249,169),(239,163),(237,184),(257,189)])):
            R.lines(s,color,False,points,2 if color==(31,36,40) else 1)
            R.rect(s,(144,142,127),(*points[-1],3,2))
        # Only flat debris on the open floor: all equipment has matching furniture bounds.
        for x,y in ((26,204),(193,217),(294,210)):
            R.line(s,(101,100,91),(x,y),(x+3,y+1))
            R.line(s,(37,43,46),(x+5,y+3),(x+7,y+1))
        for f in FURNITURE:
            x,y,w,h=f.footprint;R.ellipse(s,(35,41,45),(x-2,y+h-5,w+5,8))
        for x,c in ((259,(112,116,110)),(279,(92,118,123))):
            R.ellipse(s,(31,38,42),(x,208,14,5));R.ellipse(s,c,(x+1,207,12,4))
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
