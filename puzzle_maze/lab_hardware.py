"""Cached original pixel engineering equipment, built at the room's native scale."""
from functools import lru_cache
import math
import pygame

@lru_cache(maxsize=32)
def equipment(kind):
    s=pygame.Surface((42,38),pygame.SRCALPHA);r=pygame.draw
    ink=(36,32,36);cream=(195,184,148);green=(47,100,75);gold=(217,173,87);metal=(114,126,130)
    def box(c,x,y,w,h):s.fill(c,(x,y,w,h))
    if kind in ('crt','scope','display'):
        thin=kind=='display'
        r.polygon(s,ink,[(3,3),(34,3),(39,8),(37,28),(4,28),(1,23)])
        r.rect(s,metal if thin else cream,(3,4,33,23 if not thin else 20),border_radius=2)
        box((22,45,43),6,7,26,16 if not thin else 14)
        if kind=='scope':
            pygame.draw.lines(s,(105,235,160),False,[(7,18),(12,18),(14,11),(17,21),(21,12),(25,18),(30,18)])
            for x in (11,19,27):r.circle(s,metal,(x,25),2)
        else:
            for y,w in ((10,17),(14,11),(18,19)):box((100,170,145),9,y,w,1)
            if kind=='crt':box(gold,28,25,2,1)
        box(ink,17,28,7,6);r.polygon(s,metal if thin else cream,[(12,33),(28,33),(32,36),(8,36)])
    elif kind=='keyboard':
        r.polygon(s,ink,[(3,9),(35,9),(40,25),(1,25)])
        r.polygon(s,cream,[(4,10),(34,10),(38,23),(2,23)])
        for y in (12,16,20):
            for x in range(5,34,5):box((76,78,77),x,y,3,2)
        box((139,139,120),12,20,13,2)
    elif kind in ('gpu','motherboard','ram','cpu'):
        if kind=='ram':
            box(ink,1,10,39,14);box(green,2,11,37,11)
            for x in range(4,37,7):box((35,42,44),x,13,5,6)
            for x in range(3,37,3):box(gold,x,22,2,3)
            box((0,0,0,0),20,22,3,3)
        elif kind=='cpu':
            for x in range(7,33,4):
                box(gold,x,3,2,4);box(gold,x,31,2,4);box(gold,4,x,3,2);box(gold,33,x,3,2)
            box(ink,7,7,26,26);box(metal,9,9,22,22);box((185,194,185),12,12,16,15)
            box((90,110,115),15,17,9,2)
        elif kind=='gpu':
            box(ink,1,8,39,23);box(green,3,10,34,19);box(metal,1,8,3,25)
            for cx in (14,28):
                r.circle(s,ink,(cx,19),8);r.circle(s,metal,(cx,19),6,1)
                for k in range(5):
                    a=k*math.tau/5;r.line(s,(80,93,98),(cx,19),(int(cx+math.cos(a)*5),int(19+math.sin(a)*5)),2)
                r.circle(s,gold,(cx,19),2)
            for x in range(10,32,3):box(gold,x,30,2,3)
        else:
            box(ink,1,1,40,36);box(green,2,2,38,34)
            box(cream,10,8,15,15);box(metal,13,11,9,9)
            for x in (29,33,37):box((25,41,46),x,6,2,21)
            for y in (27,31):box(cream,7,y,21,2)
            for cx,cy in ((5,5),(6,18),(25,5),(34,30)):r.circle(s,metal,(cx,cy),2)
            pygame.draw.lines(s,(95,155,106),False,[(4,27),(4,24),(9,24),(9,5),(21,5)],1)
    elif kind=='case':
        box(ink,6,0,28,38);box(metal,7,1,26,36);box((37,50,50),10,4,20,30)
        box(green,11,5,15,23);box(cream,14,9,8,9)
        r.circle(s,ink,(21,10),5);r.circle(s,metal,(21,10),4,1)
        box((42,46,49),12,22,18,6);box(gold,14,24,13,1)
        box((70,77,76),10,31,20,4)
        pygame.draw.lines(s,(190,109,77),False,[(27,5),(29,14),(25,19),(29,29)],1)
    elif kind=='solder':
        box(ink,3,23,32,10);box((67,98,106),5,24,28,7)
        for x in range(11,29,3):r.line(s,metal,(x,21),(x-3,10))
        r.line(s,gold,(23,7),(31,19),3);r.line(s,metal,(21,4),(25,10),2)
        pygame.draw.lines(s,ink,False,[(30,20),(37,20),(39,34),(27,35)],1)
    elif kind=='meter':
        r.rect(s,(133,57,50),(10,4,22,32),border_radius=3)
        box((135,170,137),13,8,16,7);box((45,71,58),17,10,8,2)
        r.circle(s,ink,(21,24),6);r.line(s,cream,(21,24),(24,21),2)
        pygame.draw.lines(s,(195,81,65),False,[(15,34),(7,35),(5,18)],1)
        pygame.draw.lines(s,ink,False,[(27,34),(37,35),(38,16)],1)
    elif kind=='drive':
        box(ink,5,4,32,29);box(metal,6,5,30,27)
        r.circle(s,(189,194,183),(20,18),11);r.circle(s,ink,(20,18),3)
        r.lines(s,gold,False,[(32,27),(29,20),(17,16)],2)
        for x,y in ((8,7),(33,7),(8,30),(33,30)):box(ink,x,y,2,2)
        for x in range(10,30,3):box(gold,x,33,2,2)
    elif kind=='psu':
        r.polygon(s,ink,[(3,8),(31,8),(39,14),(39,33),(3,33)])
        box(metal,4,9,27,23);r.polygon(s,(73,84,89),[(31,10),(37,14),(37,31),(31,31)])
        r.circle(s,ink,(17,20),10)
        for radius in (4,7,9):r.circle(s,(146,154,150),(17,20),radius,1)
        r.line(s,metal,(7,20),(27,20));r.line(s,metal,(17,10),(17,30))
        for offset,c in ((0,gold),(2,(184,80,71)),(4,(57,55,62))):
            r.lines(s,c,False,[(35,24),(40,25+offset),(40,35)],1)
    elif kind=='disk':
        box(ink,9,4,25,28);box((73,88,103),10,5,23,26)
        box(metal,15,5,14,9);box((221,209,165),13,18,17,10);box(ink,24,6,3,6)
    return s
