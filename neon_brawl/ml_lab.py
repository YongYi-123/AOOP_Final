"""Machine learning department: distinct data, training, networks and failed models."""
import math
from functools import lru_cache
import pygame
from .research_art import shell,desk,crt,keyboard,server,sign,text
LABELS=('DATA COLLECTION','MODEL TRAINING','NEURAL NETWORK RESEARCH','FAILED EXPERIMENTS')
PANEL_TITLES=('TRAINING DATA','LOSS FUNCTION','NEURAL NETWORK','CLASSIFICATION')
FOOTERS=(('VALIDATION SET','FEATURE EXTRACTION'),('EPOCH 9999 / 10000','GRADIENT DESCENT'),
         ('REGRESSION','ACCURACY: 99.9%'),('ANOMALY DETECTED','OVERFITTING. AGAIN.'))
@lru_cache(maxsize=8)
def ml_screen(kind,variant=0):
    s=pygame.Surface((174,67));s.fill((18,39,48));r=pygame.draw;r.rect(s,(129,179,170),s.get_rect(),2)
    text(s,PANEL_TITLES[kind],6,5,(197,224,195))
    if kind==0:
        r.line(s,(100,136,146),(12,48),(158,48));r.line(s,(100,136,146),(12,19),(12,48))
        for i in range(26):
            x=20+(i*19)%132;y=23+(i*11)%22
            r.rect(s,(217,164,112) if x<86 else (120,207,199),(x,y,2,2))
        r.line(s,(182,139,190),(86,20),(86,47),1)
    elif kind==1:
        r.lines(s,(108,148,157),False,[(12,20),(12,48),(160,48)])
        r.lines(s,(112,219,170),False,[(17,24),(36,33),(54,39),(78,43),(104,44),(155,45)],2)
        r.lines(s,(232,172,126),False,[(17,26),(39,35),(65,36),(89,32),(120,27),(155,21)],1)
    elif kind==2:
        nodes=[[(24,22+i*10) for i in range(3)],[(77,18+i*10) for i in range(4)],[(143,27+i*13) for i in range(2)]]
        for a,b in zip(nodes,nodes[1:]):
            for x,y in a:
                for xx,yy in b:r.line(s,(56,98,114),(x,y),(xx,yy))
        for group in nodes:
            for x,y in group:r.circle(s,(123,211,186),(x,y),3);r.rect(s,(218,233,186),(x,y,1,1))
    else:
        for row in range(3):
            for col in range(3):
                c=(98,177,167) if row==col else (49,83,99)
                r.rect(s,c,(12+col*17,19+row*10,15,8))
        text(s,'CAT  DOG',75,22);text(s,'CAT  CAT',75,33,(232,188,125));text(s,'CAT  CAT',75,44,(232,188,125))
    text(s,FOOTERS[kind][variant%2],6,56,(220,181,131))
    return s

def paint_ml(s,section):
    shell(s,0,section);r=pygame.draw
    for i,x in enumerate(range(0,800,200)):
        kind=(section+i%2)%4
        s.blit(ml_screen(kind,i%2),(x+12,59))
        desk(s,x+13,135,171);crt(s,x+137,114,mini=True);keyboard(s,x+85,136)
        # Data tapes, papers, battered towers, specimen camera and a plush mascot.
        if section==0:
            for k in range(4):
                r.rect(s,(143,150-k*8,139),(x+20+k*18,128,14,8));r.rect(s,(48,72,85),(x+23+k*18,130,7,3))
            r.line(s,(68,83,101),(x+70,134),(x+70,117),2);r.rect(s,(152,171,162),(x+62,114,17,10));r.circle(s,(46,87,100),(x+70,119),3)
        elif section==1:
            server(s,x+20,115,34,47,i%2==0)
            r.ellipse(s,(192,159,116),(x+64,130,11,7));r.rect(s,(231,206,159),(x+65,126,8,7))
        elif section==2:
            r.rect(s,(147,162,138),(x+18,128,42,8));r.rect(s,(52,111,91),(x+22,130,33,4))
            for xx in range(x+24,x+53,6):r.rect(s,(205,179,103),(xx,131,3,2))
        else:
            server(s,x+18,123,35,39,True)
            r.lines(s,(169,125,144),False,[(x+55,138),(x+63,153),(x+75,148)],2)
        # Tiny lab-cat plush: round head and short paws, not a hostile experiment.
        r.ellipse(s,(175,145,170),(x+114,129,13,8));r.polygon(s,(175,145,170),[(x+113,130),(x+113,124),(x+118,127),(x+124,124),(x+125,132)])
        for dx in (116,121):r.rect(s,(234,220,188),(x+dx,129,1,1))
    # Every zone has an explicit, mounted research identity.
    sign(s,LABELS[section],(215,41,235,15),(182,216,174))
    if section==3:
        sign(s,'REAL-WORLD ACCURACY: 12%', (420,140,175,16),(231,176,141))

@lru_cache(maxsize=8)
def steam(frame):
    s=pygame.Surface((18,24),pygame.SRCALPHA)
    for k in range(3):
        pygame.draw.lines(s,(155,188,179,60),False,[(3+k*5,23),(2+k*5+frame%3,14),(4+k*5,4)],1)
    return s

def lab_motion(s,stage,section,camera,time):
    # Decoration only: all effects stay above the fighter lanes.
    offset=int(camera*.55)%800
    for world_x in (74,340,622):
        x=(world_x-offset)%800
        if x<410:
            y=47+int((time*23+world_x)%110)
            s.fill((132,187,194),(x,y,1,3))
            if section%2:s.blit(steam(int(time*4)%8),(x+25,128))
    if int(time*8)%37==0:
        x=(175-offset)%800
        if x<400:
            for dx,dy in ((0,0),(3,-3),(-3,2)):pygame.draw.line(s,(239,205,130),(x,128),(x+dx,128+dy))
    if int(time*5)%29==0:s.fill((47,79,89),(int((112-offset)%400),68,48,2))
