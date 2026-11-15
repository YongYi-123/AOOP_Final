"""Five large-scale computing environments; visual phase changes never alter combat."""
import math
from functools import lru_cache
import pygame

LABELS=('SECURITY CHECKPOINT','SERVER RACK CORRIDOR','COOLING AND POWER','CENTRAL COMPUTING','OVERLORD ARENA')

def paint_facility(s,section):
    from font import get_font
    font=get_font();cyan=(70,165,185);violet=(125,85,180);magenta=(165,75,150)
    def box(c,x,y,w,h):s.fill(c,(x,y,w,h))
    def sign(label,x,y,w,color=cyan):
        box((9,16,32),x,y,w,15);pygame.draw.rect(s,color,(x,y,w,15),1)
        img=font.render(label,color);s.blit(img,(x+(w-img.get_width())//2,y+4))
    def rack(x,y,w=57,h=87):
        box((50,60,90),x,y,w,h);box((9,18,35),x+4,y+4,w-8,h-8)
        for yy in range(y+8,y+h-7,10):
            box((45,63,83),x+7,yy,w-14,7)
            for xx in range(x+12,x+w-8,8):box(cyan if (xx+yy)%3 else violet,xx,yy+2,2,2)
    box((15,23,42),0,35,800,134)
    for x in range(0,800,96):
        box((33,46,68),x+2,37,8,130)
        pygame.draw.lines(s,(45,80,110),False,[(x+8,43),(x+30,58),(x+82,58),(x+90,43)],2)
    if section==0:
        for x in range(0,800,200):
            box((65,75,110),x+10,65,161,101);box((11,22,41),x+24,83,129,82)
            for xx in range(x+29,x+151,20):box((40,55,83),xx,84,15,79)
            box(cyan,x+21,68,141,3);box((45,65,90),x+177,111,20,55)
            box((100,190,185),x+181,116,12,14)
            sign('ACCESS // SCAN',x+24,46,129)
    elif section==1:
        # Rows recede behind a second full-height bank: a data center, not a corridor.
        for x in range(-10,800,68):rack(x,63,61,104)
        for x in range(15,800,100):
            pygame.draw.lines(s,(75,55,105),False,[(x,39),(x,51),(x+25,51),(x+25,63)],3)
        sign('COMPUTE CLUSTER 09',270,42,240,violet)
    elif section==2:
        for x in range(0,800,180):
            box((50,75,95),x+8,71,75,95)
            for yy in (80,120):
                pygame.draw.circle(s,(15,28,43),(x+45,yy+11),24)
                pygame.draw.circle(s,(85,125,145),(x+45,yy+11),23,2)
            box((55,65,90),x+96,99,68,67)
            for k in range(4):box((195,125,65),x+103,108+k*12,51,7)
            pygame.draw.lines(s,(65,120,140),False,[(x,56),(x+83,56),(x+83,156),(x+95,156)],6)
            pygame.draw.line(s,(105,175,170),(x,54),(x+83,54),2)
            sign('COOLANT // POWER',x+6,43,157)
    else:
        # Central processor is surrounded by broad server walls and energy buses.
        for x in range(-20,800,95):rack(x,75,70,92)
        for x in (140,400,660):
            box((23,31,53),x-90,42,180,124)
            pygame.draw.polygon(s,(60,55,100),[(x,52),(x+62,107),(x+45,165),(x-45,165),(x-62,107)])
            pygame.draw.polygon(s,(115,75,155),[(x,62),(x+49,110),(x+34,156),(x-34,156),(x-49,110)],2)
            pygame.draw.polygon(s,(50,110,145),[(x,78),(x+32,111),(x,146),(x-32,111)])
            pygame.draw.polygon(s,(105,190,200),[(x,88),(x+22,111),(x,135),(x-22,111)],2)
            box((115,75,135),x-7,105,14,15)
            for dx in (-78,78):
                box((60,65,95),x+dx-12,58,24,103)
                for y in (70,105,140):box(violet,x+dx-9,y,18,3)
            if section==4:
                for dx in (-72,47):
                    box((70,75,100),x+dx,38,26,31);box((15,28,48),x+dx+3,41,20,24)
                    pygame.draw.lines(s,magenta,False,[(x+dx+5,62),(x+dx+11,47),(x+dx+19,57),(x+dx+21,44)],1)
        for y in (151,157,163):
            pygame.draw.line(s,cyan if y==157 else (75,50,115),(0,y),(800,y),2)
        sign('THE LOST SIGNAL // PROCESSING CORE',243,37,300,magenta)
    sign(LABELS[section],12,146,204,cyan)

@lru_cache(maxsize=8)
def fan_frame(frame):
    s=pygame.Surface((40,40),pygame.SRCALPHA)
    for k in range(5):
        a=(k/5+frame/40)*math.tau
        points=[(20,20),(20+int(math.cos(a)*17),20+int(math.sin(a)*17)),
                (20+int(math.cos(a+.6)*13),20+int(math.sin(a+.6)*13))]
        pygame.draw.polygon(s,(75,115,130),points)
    pygame.draw.circle(s,(150,180,180),(20,20),4)
    return s

def facility_motion(s,section,camera,time,phase=1,attack=False):
    for i in range(24):
        x=int((i*39-camera*.55)%800);y=80+i%7*11
        if x<400 and (int(time*3)+i)%5:s.fill((65,135+i%3*15,160),(x,y,2,1))
    if section==2:
        for i in range(5):
            x=int((i*180+45-camera*.55)%800)
            if x<430:
                for y in (91,131):s.blit(fan_frame(int(time*9)%8),(x-20,y-20))
    if section>=3:
        color=((80,185,200),(180,85,185),(215,100,125))[min(2,phase-1)]
        for i in range(3):
            x=int((140+i*260-camera*.55)%800)
            if -50<x<450:
                radius=20+int(math.sin(time*2)*3)
                pygame.draw.polygon(s,color,[(x,111-radius),(x+radius,111),(x,111+radius),(x-radius,111)],2)
                if attack:pygame.draw.line(s,color,(x-30,155),(x+30,155),2)
        for i in range(10):
            x=int((i*53+time*45-camera*.55)%800)
            if x<400:s.fill(color,(x,157,6,1))
    # Raised floor seams and cable trays stay behind the fighters.
    for x in range(-25,425,50):
        xx=x-int(camera)%50
        pygame.draw.lines(s,(43,55,75),False,[(xx,171),(xx,275),(xx+44,275)],1)
        s.fill((70,95,115),(xx+3,176,2,2))
