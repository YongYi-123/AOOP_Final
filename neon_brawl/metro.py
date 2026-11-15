"""Abandoned transit architecture and bounded background-only motion."""
import math
import pygame
from functools import lru_cache

def paint_metro(s,section):
    from font import get_font
    font=get_font();blue=(75,155,185);green=(90,150,135);warning=(195,155,70)
    def box(c,x,y,w,h):s.fill(c,(x,y,w,h))
    def sign(label,x,y,w,color=blue):
        box((10,19,32),x,y,w,16);pygame.draw.rect(s,color,(x,y,w,16),1)
        image=font.render(label,color);s.blit(image,(x+(w-image.get_width())//2,y+4))
    box((24,33,48),0,45,800,124)
    for x in range(0,800,32):
        for y in range(52,168,16):pygame.draw.rect(s,(42,55,67),(x+1,y+1,30,14),1)
    for x in range(0,800,180):
        box((65,80,95),x+160,45,10,123)
        box((110,135,145),x+15,53,128,4)
        if section==0:
            sign('DISTRICT 09 METRO',x+3,65,153)
            # Ticket gates and a route map with named stations.
            for k in range(3):
                xx=x+9+k*43;box((65,90,105),xx,125,32,41)
                pygame.draw.polygon(s,(105,135,145),[(xx,125),(xx+18,119),(xx+32,125),(xx+13,131)])
                box((155,180,165),xx+5,126,9,4);box((185,85,80),xx+20,139,4,4)
            box((22,43,55),x+8,87,105,28)
            pygame.draw.lines(s,green,False,[(x+13,107),(x+32,99),(x+60,99),(x+83,92),(x+105,92)],2)
            for dx in (13,32,60,83,105):pygame.draw.rect(s,(180,195,165),(x+dx,97 if dx<80 else 90,3,3))
        elif section==1:
            box((6,15,28),x+7,84,146,63)
            for y in (132,138,145):box((55,75,85),x+8,y,145,2)
            sign('LAST TRAIN: CANCELLED',x+5,64,150)
            box((90,85,85),x+13,151,91,5)
            for xx in (x+22,x+91):box((55,65,80),xx,156,4,11)
            # A damaged vending machine with a dead screen and torn poster.
            box((55,75,95),x+119,118,29,49);box((13,25,39),x+123,123,17,24)
            pygame.draw.line(s,(90,145,155),(x+123,124),(x+139,142),1)
            box((125,95,95),x+113,91,16,21)
        elif section==2:
            for y in (73,93):
                box((75,100,110),x+4,y,154,8);box((115,135,130),x+5,y+1,152,2)
            for xx in (x+19,x+114):
                box((65,90,100),xx,61,6,106)
                for y in (75,95):box((135,130,95),xx-3,y-4,12,16)
            box((43,60,78),x+42,114,60,53);box(warning,x+47,118,50,9)
            for k in range(5):box((100,125,130),x+49,136+k*5,46,2)
            sign('DANGER: LIVE CIRCUITS',x+4,46,151,warning)
        else:
            for k in range(2):
                xx=x+10+k*74;box((65,85,105),xx,77,66,55);box((8,25,37),xx+4,81,58,45)
                for j in range(4):
                    pygame.draw.lines(s,blue,False,[(xx+8,88+j*9),(xx+24,93+j*8),(xx+39,86+j*9),(xx+57,91+j*8)],1)
            pygame.draw.polygon(s,(60,77,95),[(x+7,139),(x+148,139),(x+157,164),(x,164)])
            for k in range(10):box(green if k%3 else warning,x+11+k*13,147,7,3)
            sign('CONTROL // SIGNAL LOST',x+2,48,156)
    from .hardware_posters import paint_hardware_displays
    paint_hardware_displays(s,section)
    for x in range(4,800,82):
        pygame.draw.lines(s,(45,65,75),False,[(x,40),(x+36,48),(x+81,40)],2)
    for x in range(0,800,20):
        pygame.draw.polygon(s,(105,100,65),[(x,164),(x+8,164),(x+3,168),(x-5,168)])

@lru_cache(maxsize=3)
def train_glow(frame):
    s=pygame.Surface((100,24),pygame.SRCALPHA)
    for i in range(5):
        pygame.draw.rect(s,(105,155,185,12+i*8),(i*3,i*2,100-i*6,24-i*4))
    for x in (15,42,69):s.fill((200,220,175,90+frame*15),(x,8,16,7))
    return s

def metro_motion(s,section,camera,time):
    for i in range(5):
        x=int((i*107+73-camera*.55)%800)
        y=90+int((time*33+i*13)%72)
        if x<400:s.fill((80,145,170),(x,y,1,3))
    if section==1 and time%18>14:
        x=int((time%18-14)*145)-100
        s.blit(train_glow(int(time*6)%3),(x,109))
    if section==2 and int(time*11)%23<2:
        x=int(83-camera*.55)%400
        for dx,dy in ((0,0),(4,-3),(-3,-5),(2,4)):
            pygame.draw.line(s,(215,205,125),(x,117),(x+dx,117+dy),1)
    if int(time*7)%29==0:s.fill((25,35,48),(0,53,400,3))
