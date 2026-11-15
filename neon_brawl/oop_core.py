"""Playful software department: UML-inspired diagrams, arcade machinery and live objects."""
import math
from functools import lru_cache
import pygame
from .research_art import shell,server,sign,text,desk,keyboard
from .ml_lab import lab_motion
LABELS=('CLASS GALLERY','INHERITANCE TREE','COMPONENT WORKSHOP','ARCADE RUNTIME','CENTRAL SOFTWARE CONTROL')
TITLES=('CLASS / OBJECT','INHERITANCE','COMPOSITION','INTERFACE / METHOD','ARCADE SYSTEM / AOOP')
@lru_cache(maxsize=5)
def class_diagram(kind):
    s=pygame.Surface((174,67));s.fill((29,31,59));r=pygame.draw;cyan=(135,214,203);purple=(190,160,220)
    r.rect(s,(133,117,174),s.get_rect(),2);text(s,TITLES[kind],6,5,(227,209,231))
    def node(label,x,y,w):
        r.rect(s,(90,85,135),(x,y,w,12),1);text(s,label,x+3,y+3,cyan)
    if kind==0:
        node('CLASS',9,19,63);node('OBJECT',100,19,65)
        text(s,'HP / MOVE()',12,36,purple);text(s,'REX / 140',103,36,purple)
        r.line(s,cyan,(74,25),(97,25));r.lines(s,cyan,False,[(93,22),(97,25),(93,28)])
        text(s,'CONSTRUCTOR -> INSTANCE',6,56,(221,181,136))
    elif kind==1:
        node('ENTITY',62,18,52);node('PLAYER',10,42,61);node('ENEMY',103,42,61)
        r.lines(s,cyan,False,[(40,42),(40,37),(88,37),(133,37),(133,42)])
        r.polygon(s,cyan,[(88,30),(83,36),(93,36)],1)
        text(s,'POLYMORPHISM: UPDATE',6,57,(221,181,136))
    elif kind==2:
        node('SCENE',64,18,49)
        r.polygon(s,cyan,[(89,30),(93,34),(89,38),(85,34)])
        r.lines(s,cyan,False,[(32,44),(32,39),(89,39),(142,39),(142,44)]);r.line(s,cyan,(89,38),(89,44))
        for x,label in ((8,'DRAW'),(65,'MOVE'),(122,'INPUT')):node(label,x,44,44)
        text(s,'ENCAPSULATION / PRIVATE',6,58,(221,181,136))
    elif kind==3:
        node('ACTOR',64,18,49)
        for x,label in ((9,'ROBOT'),(103,'CAT')):
            node(label,x,41,61)
            start=x+30
            for step in range(0,8,2):
                a=(round(start+(88-start)*step/8),round(41-8*step/8))
                b=(round(start+(88-start)*(step+1)/8),round(41-8*(step+1)/8))
                r.line(s,cyan,a,b)
        r.polygon(s,cyan,[(88,30),(84,35),(92,35)],1)
        text(s,'ABSTRACTION / ATTRIBUTE',6,57,(221,181,136))
    else:
        node('GAME',65,18,49);node('SCENE',9,41,61);node('OBJECT',103,41,61)
        r.lines(s,cyan,False,[(39,41),(39,35),(89,35),(89,30)]);r.lines(s,cyan,False,[(134,41),(134,35),(89,35)])
        text(s,'NULL IS NOT A GAME PLAN',6,57,(221,181,136))
    return s

def arcade(s,x,y,color=(125,174,182),mascot=0):
    r=pygame.draw
    r.polygon(s,(26,31,49),[(x+5,y),(x+35,y),(x+39,y+9),(x+32,y+35),(x+40,y+42),(x+38,y+70),(x,y+70),(x+1,y+44),(x+7,y+35)])
    r.polygon(s,color,[(x+7,y+2),(x+33,y+2),(x+35,y+9),(x+30,y+37),(x+37,y+43),(x+34,y+67),(x+3,y+67),(x+3,y+46),(x+9,y+37)])
    r.rect(s,(26,40,57),(x+7,y+12,24,25));r.rect(s,(135,206,183),(x+9,y+14,20,20),1)
    if mascot%2:
        r.rect(s,(226,181,137),(x+14,y+21,10,8));r.rect(s,(226,181,137),(x+14,y+18,2,4));r.rect(s,(226,181,137),(x+22,y+18,2,4))
        for dx in (16,21):r.rect(s,(39,70,84),(x+dx,y+23,1,1))
    else:
        r.rect(s,(195,152,208),(x+14,y+20,11,10));r.rect(s,(125,213,213),(x+16,y+22,7,3))
        for dx in (15,23):r.rect(s,(95,132,175),(x+dx,y+30,2,3))
    r.line(s,(42,50,69),(x+13,y+44),(x+13,y+39),2);r.circle(s,(218,136,161),(x+13,y+39),2)
    for dx,c in ((24,(231,189,129)),(29,(133,214,182))):r.rect(s,c,(x+dx,y+41,3,2))
    r.rect(s,(49,48,68),(x+14,y+53,13,8));r.rect(s,(211,176,113),(x+18,y+55,5,1))

def paint_oop(s,section):
    shell(s,2,section);r=pygame.draw
    if section<3:
        for i,x in enumerate(range(0,800,200)):
            s.blit(class_diagram((section+i%2)%4),(x+12,59))
            desk(s,x+15,138,168);keyboard(s,x+92,139)
            server(s,x+20,127,29,38,i%2==0)
            # Component trays and tiny inactive robots have physical supports.
            r.rect(s,(113,99,144),(x+59,134,26,9));r.rect(s,(180,186,164),(x+62,130,17,10))
            r.rect(s,(97,191,184),(x+65,132,11,3));r.rect(s,(54,60,85),(x+66,141,3,3));r.rect(s,(54,60,85),(x+75,141,3,3))
    elif section==3:
        for i,x in enumerate(range(0,800,100)):
            arcade(s,x+9,96,(113+i%3*15,132,172),i);server(s,x+56,74,33,91,i%3==0)
            if i%2==0:
                r.rect(s,(33,31,57),(x+6,59,83,29));text(s,'BUILD FAILED',x+12,64,(223,157,169));text(s,'TRY SNACKS',x+12,77,(189,208,180))
    else:
        for x in range(0,800,55):server(s,x,64,42,101)
        # The boss camera rests near world x=1050. Wrap the large landmark across
        # the 800px parallax tile so its monitor is centered in the actual arena view.
        for center in (-23,777):
            r.rect(s,(88,83,127),(center-126,58,252,99));r.rect(s,(20,31,56),(center-121,63,242,89))
            s.blit(class_diagram(4),(center-87,69))
            for xx in range(center-112,center+114,12):r.rect(s,(109,184,185),(xx,143,6,2))
            arcade(s,center-176,95,(164,125,169),1);arcade(s,center+139,95,(105,168,168),0)
            sign(s,'RUNTIME // THE LOST SIGNAL',(center-112,39,224,16),(180,211,194))
    if section<4:sign(s,LABELS[section],(215,41,245,15),(206,183,216))
    if section==0:sign(s,'ADVANCED OBJECT-ORIENTED PROGRAMMING',(405,146,270,17),(184,204,215))

@lru_cache(maxsize=32)
def pixel_object(kind,frame):
    s=pygame.Surface((15,15),pygame.SRCALPHA);r=pygame.draw
    c=((153,202,187),(201,162,207),(217,186,133))[kind%3]
    r.polygon(s,(41,42,65),[(7,0),(14,4),(14,11),(7,15),(0,11),(0,4)])
    r.polygon(s,c,[(7,1),(13,4),(7,7),(1,4)]);r.polygon(s,tuple(v*3//4 for v in c),[(1,5),(7,8),(7,14),(1,11)])
    r.polygon(s,tuple(v*2//3 for v in c),[(8,8),(13,5),(13,11),(8,14)])
    for x in (4,8):r.rect(s,(40,81,94),(x,4+frame%2,1,1))
    return s

def oop_motion(s,section,camera,time,phase=1,attack=False):
    lab_motion(s,2,section,camera,time)
    offset=int(camera*.55)%800
    for i in range(6):
        x=int((i*137+54-offset)%800);y=84+int(math.sin(time*.8+i)*6)
        if x<410 and section in (1,2,4):s.blit(pixel_object(i%3,int(time*2)%4),(x,y))
    if section==4:
        color=(115,191,194) if phase==1 else (186,128,203) if phase==2 else (224,155,140)
        for i in range(8):
            x=int((time*33+i*57-camera*.55)%400)
            s.fill(color,(x,154+i%2*4,6,1))
        # Phase light is confined to the computing wall, never a fullscreen flash.
        if attack:s.fill((168,116,155),(12,61,32,2))
    if section==3 and int(time)%4<2:
        text(s,'NULL',int((123-offset)%800),91,(206,183,216))
