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
        # A clear work surface: computer left, testing instrument right, parts below.
        R.polygon(s,INK,[(2,32),(115,32),(119,47),(117,53),(1,53)])
        R.polygon(s,TOP,[(4,30),(113,30),(119,47),(0,47)])
        R.line(s,EDGE,(4,31),(112,31));R.rect(s,WOOD,(0,47,120,5))
        for x in (4,111):R.rect(s,(67,74,77),(x,52,5,17))
        R.line(s,(112,119,117),(8,64),(112,64),2)
        R.rect(s,(60,68,72),(77,52,30,13));R.rect(s,(99,106,106),(79,54,26,9))
        R.rect(s,(151,143,112),(89,57,7,2))
        monitor(s,18,2)
        R.rect(s,(111,119,109),(79,11,25,18));R.rect(s,(20,42,44),(82,14,16,10))
        R.lines(s,(113,165,136),False,[(83,20),(86,20),(88,16),(91,22),(94,18),(96,18)])
        for yy in (16,22):R.circle(s,(56,66,63),(101,yy),1)
        R.rect(s,(66,81,75),(44,33,28,10));R.rect(s,(126,137,116),(46,35,24,6),1)
        R.line(s,(89,98,95),(114,35),(114,13),2)
        R.polygon(s,(148,141,110),[(107,12),(117,12),(119,19),(103,19)])
        R.line(s,(207,189,135),(106,19),(117,19))
        R.lines(s,(48,66,69),False,[(30,29),(33,34),(28,40),(35,44)])
        for x in (8,75):R.line(s,(153,151,136),(x,45),(x+10,45))
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
    elif k=='toolbox':
        R.rect(s,(70,78,80),(1,4,28,23));R.rect(s,(108,115,112),(2,5,26,5))
        R.rect(s,(126,139,134),(10,1,11,4),1)
        for yy in (12,18,24):
            R.rect(s,(44,53,58),(3,yy-1,24,1));R.line(s,(155,158,143),(11,yy+1),(20,yy+1))
        R.rect(s,(142,119,77),(22,7,3,3));R.line(s,(145,128,98),(3,21),(7,19))
        for x in (4,25):R.circle(s,(29,36,40),(x,27),2)
        R.line(s,(76,107,113),(5,6),(8,6))
    elif k=='crates':
        for x,y,w,h in ((1,10,19,14),(14,11,17,13),(7,0,19,13)):
            R.rect(s,(132,119,91),(x,y,w,h));R.rect(s,(71,74,65),(x,y,w,h),1)
            R.line(s,(174,154,108),(x+w//2,y+1),(x+w//2,y+h-2),2)
            R.rect(s,(196,182,140),(x+3,y+4,8,4));R.line(s,(99,99,81),(x+4,y+6),(x+8,y+6))
        R.line(s,(69,82,79),(11,1),(17,2));R.line(s,(69,82,79),(9,3),(12,4))
    elif k=='spare_crt':
        R.polygon(s,(83,95,96),[(3,2),(21,2),(24,7),(22,21),(1,21)])
        R.rect(s,(142,146,125),(1,5,20,16));R.rect(s,(26,43,46),(4,7,14,10))
        R.line(s,(91,121,118),(5,8),(16,8));R.line(s,(134,142,124),(3,22),(22,22))
        R.rect(s,(76,85,80),(10,21,5,3));R.line(s,(157,151,120),(8,12),(12,15))
        R.lines(s,(54,65,67),False,[(22,16),(24,18),(20,24)])
    elif k=='shelf':
        for x in (1,27):R.rect(s,(104,114,114),(x,0,2,29))
        for yy in (9,25):R.rect(s,(73,85,90),(0,yy,30,3))
        R.rect(s,(130,115,88),(4,12,21,12));R.line(s,(184,163,110),(14,12),(14,23),2)
        R.rect(s,(185,173,133),(6,16,7,4));R.line(s,(95,100,86),(7,18),(11,18))
        R.rect(s,(61,82,80),(5,1,9,7));R.circle(s,(142,155,128),(9,5),2,1)
        R.rect(s,(117,111,100),(17,2,8,6));R.line(s,(161,148,112),(19,2),(19,7))
    elif k=='electronics':
        # Open project case: breadboard, meter, probes, solder spool and a sandwich.
        R.rect(s,(50,64,69),(1,9,33,14));R.rect(s,(102,117,112),(2,10,31,12),1)
        R.rect(s,(151,156,134),(3,1,29,10));R.rect(s,(74,94,88),(5,3,25,6))
        R.rect(s,(208,206,171),(4,12,15,8))
        for y in (14,17):
            for x in range(6,18,3):s.fill((88,108,104),(x,y,1,1))
        R.lines(s,(141,119,91),False,[(7,14),(9,11),(13,11),(14,17)])
        R.rect(s,(155,139,85),(22,11,9,10));R.rect(s,(39,64,65),(24,13,5,3))
        R.circle(s,(53,72,72),(26,18),2)
        R.lines(s,(94,133,131),False,[(25,21),(26,23),(20,23),(19,19)])
        R.polygon(s,(185,166,117),[(6,4),(10,1),(15,5)]);R.line(s,(104,129,92),(8,4),(13,4))
        for x in (5,29):R.circle(s,(34,44,49),(x,23),1)
    elif k=='wire_spool':
        R.rect(s,(71,86,88),(1,15,26,5));R.ellipse(s,(115,126,116),(0,10,28,10))
        R.ellipse(s,(75,105,103),(2,2,24,14));R.ellipse(s,(132,140,119),(2,0,24,10))
        R.ellipse(s,(33,57,63),(8,2,12,5));R.line(s,(162,157,118),(7,13),(22,13))
        for y in (8,10,12):R.line(s,(46,76,79),(3,y),(24,y))
        R.lines(s,(137,120,88),False,[(23,8),(27,14),(23,20),(16,19)])
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
    revision='warehouse-workshop-8'
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
        # The shutter is set into the west wall, sharing its steel and concrete.
        R.rect(s,(35,41,46),(5,44,12,189))
        R.rect(s,(24,33,39),(8,100,24,47))
        R.rect(s,(49,61,66),(7,100,25,4));R.line(s,(76,87,89),(8,100),(31,100))
        for x in (8,29):R.rect(s,(60,74,79),(x,104,2,39))
        R.rect(s,(12,22,29),(11,108,18,33))
        for y in range(105,120,3):
            R.line(s,(78,94,98),(11,y),(28,y));R.line(s,(39,54,62),(11,y+1),(28,y+1))
        R.rect(s,(48,61,65),(10,141,21,3))
        for x in range(12,29,6):R.line(s,(106,110,94),(x,141),(x+2,143))
        R.line(s,(75,90,94),(27,123),(27,132));s.fill((128,130,105),(26,129,1,1))
        R.line(s,(49,62,66),(32,99),(32,147))
        R.rect(s,(36,54,59),(8,94,20,5));R.line(s,(99,151,137),(12,96),(23,96))
        # Overhead conduit, dead fluorescent tube and exposed fuse board.
        R.lines(s,(107,111,108),False,[(18,19),(170,19),(170,46)],2)
        R.rect(s,(34,40,45),(186,12,105,25))
        for x in (192,212,232):
            R.rect(s,(84,91,94),(x,17,14,15));R.rect(s,(31,36,41),(x+3,20,8,5))
            R.lines(s,(122,99,78),False,[(x+6,30),(x+9,39),(x+1,45)],1)
        # A chalky AOOP ownership diagram, pinned over old screw holes.
        R.rect(s,(84,97,94),(55,7,123,36));R.rect(s,(27,48,47),(57,9,119,32))
        R.line(s,(136,146,124),(56,8),(176,8))
        s.blit(render('AOOP',8,(167,185,156)),(61,12))
        s.blit(render('CAT > UML',8,(136,157,140)),(117,12))
        for x,label,w in ((61,'GAME',27),(103,'ROOM',27),(148,'CAT',22)):
            R.rect(s,(119,150,134),(x,24,w,12),1)
            s.blit(render(label,8,(181,194,158)),(x+2,27))
        for x in (89,132):
            R.line(s,(155,174,147),(x,29),(x+11,29))
            R.lines(s,(155,174,147),False,[(x+8,27),(x+11,29),(x+8,31)])
        for x in (75,94,144):R.line(s,(59,82,73),(x,39),(x+7,39))
        R.rect(s,(64,79,77),(63,43,109,3));R.rect(s,(180,184,147),(154,43,7,2))
        R.rect(s,(36,44,48),(84,1,61,5));R.line(s,(155,169,159),(88,2),(141,2))
        # Loose leads loop around the cabinets and the testing bench.
        for color,points in (
            ((31,36,40),[(53,99),(57,113),(85,116),(100,108),(141,111),(160,123),(182,119),(190,106)]),
            ((110,91,75),[(91,98),(87,106),(72,111),(63,107),(68,101),(101,104),(110,115),(159,116)]),
            ((76,95,99),[(145,96),(152,110),(141,116),(134,110),(139,105),(167,110),(178,120)]),
            ((30,36,40),[(63,180),(68,191),(105,191),(109,182),(98,178),(91,176)]),
            ((106,101,81),[(284,138),(267,143),(259,132),(267,125),(271,149),(294,154)])):
            R.lines(s,color,False,points,2 if color==(31,36,40) else 1)
            R.rect(s,(144,142,127),(*points[-1],3,2))
        # A patched coat, a clock that lost its hands, and a very carefully parked broom.
        R.rect(s,(112,118,105),(37,16,3,3));R.polygon(s,(81,97,94),[(36,21),(43,21),(48,30),(44,32),(43,41),(35,41),(34,30),(30,31)])
        R.line(s,(128,139,119),(38,24),(38,39));R.rect(s,(137,123,94),(39,34,3,3))
        R.circle(s,(103,114,111),(18,24),7);R.circle(s,(37,49,55),(18,24),5)
        for x,y in ((18,20),(18,28),(14,24),(22,24)):s.fill((155,155,129),(x,y,1,1))
        R.line(s,(125,111,82),(300,158),(293,191),2);R.polygon(s,(116,123,104),[(290,188),(298,190),(299,197),(286,195)])
        for x in (289,292,295):R.line(s,(62,76,77),(x,191),(x-1,194))
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
