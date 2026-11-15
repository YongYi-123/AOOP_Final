"""Original rain-soaked night-market architecture; every sign is English."""
import math
import pygame
from functools import lru_cache

def paint_market(s,section):
    from font import get_font
    font=get_font();red=(235,65,85);gold=(225,165,75);cyan=(75,185,205)
    def box(c,x,y,w,h):s.fill(c,(x,y,w,h))
    def sign(text,x,y,w,color=red):
        box((16,13,30),x,y,w,18);pygame.draw.rect(s,color,(x,y,w,18),1)
        img=font.render(text,color);s.blit(img,(x+(w-img.get_width())//2,y+5))
    def vertical(text,x,y,color):
        box((14,14,29),x,y,14,len(text)*8+5)
        pygame.draw.rect(s,color,(x,y,14,len(text)*8+5),1)
        for k,char in enumerate(text):s.blit(font.render(char,color),(x+4,y+3+k*8))
    # Apartment stacks, vents, laundry rails and layered suspended shop signs.
    for i,x in enumerate(range(-30,820,105)):
        color=((39,35,53),(35,43,60),(46,36,51))[i%3]
        box(color,x,24+i%3*5,99,145)
        for yy in (35,55,75):
            for xx in (x+8,x+38,x+68):
                box((12,20,35),xx,yy,21,15)
                box((115,100,78) if (i+xx+yy)%3 else (65,105,120),xx+2,yy+2,7,9)
                box((95,100,110),xx+13,yy+12,11,7)
                for dy in (14,16):box((40,50,65),xx+14,yy+dy,8,1)
        pygame.draw.lines(s,(65,60,78),False,[(x,45),(x+35,54),(x+108,42)],1)
        vertical(('TEA','ROOMS','DIMSUM','NOODLE')[i%4],x+84,35,red if i%2 else gold)
    for i,x in enumerate(range(0,800,120)):
        box((22,22,39),x,104,116,64)
        name=(('GOLDEN TEA','NIGHT RECORDS','JADE NOODLES','MOON HOTEL')[i%4] if section==0 else
              ('DIM SUM','FISH BALLS','HOT SKEWERS','TEA HOUSE')[i%4] if section in (1,2) else
              ('CLOSED','WARDEN CREW','NO ENTRY','KEEP OUT')[i%4])
        sign(name,x+3,88,111,red if i%3 else cyan)
        if section==0:
            for k in range(3):
                box((35,65,75),x+8+k*34,112,27,42);box((125,100,95),x+11+k*34,116,21,2)
            box((55,50,70),x+8,157,99,6)
        elif section==1:
            pygame.draw.polygon(s,(145,45,65) if i%2 else (45,90,105),[(x,111),(x+110,111),(x+120,128),(x-8,128)])
            for xx in range(x+4,x+110,14):box((205,175,120),xx,112,5,15)
            box((100,60,55),x+5,145,106,21)
            for k in range(6):
                pygame.draw.ellipse(s,(220,165-k*8,85),(x+11+k*15,141,10,5))
                box((125,85,75),x+12+k*15,148,8,2)
        elif section==2:
            box((35,53,65),x+8,112,47,41);box((155,95,65),x+60,111,47,46)
            for yy in (120,130,140):box((220,165,105),x+66,yy,35,2)
            box((65,65,80),x+13,139,34,24);box((225,155,95),x+17,143,26,6)
            for k in range(3):pygame.draw.ellipse(s,(160,145,135),(x+15+k*9,136,7,3))
        else:
            for yy in range(112,167,5):box((60,45,66),x+6,yy,104,2)
            pygame.draw.polygon(s,(130,45,75),[(x+44,105),(x+76,105),(x+76,145),(x+60,157),(x+44,145)])
            pygame.draw.lines(s,gold,False,[(x+50,119),(x+60,130),(x+70,119)],2)
        # Paper posters, refuse bins, steam vents and projecting lamps.
        box((155,130,120),x+111,118,9,24);box((55,50,75),x+113,121,5,3)
        if i%2:
            box((50,75,75),x+98,147,15,20);box((95,110,105),x+97,146,17,3)
        else:
            box((35,35,50),x+3,161,24,6)
            for xx in range(x+5,x+25,4):box((95,90,110),xx,162,1,4)
    for x in range(20,800,170):
        pygame.draw.lines(s,(95,70,90),False,[(x,61),(x+85,72),(x+168,59)],1)
        for dx in (30,75,120):
            pygame.draw.ellipse(s,(175,65,65),(x+dx,65,7,10))
            box(gold,x+dx+2,67,2,5)

@lru_cache(maxsize=8)
def steam(frame):
    s=pygame.Surface((22,26),pygame.SRCALPHA)
    for k in range(3):
        offset=int(math.sin(frame*1.2+k)*2)
        pygame.draw.lines(s,(125,145,155,65),False,[(6+k*5,25),(5+k*5+offset,17),(8+k*5-offset,8),(7+k*5+offset,2)],2)
    return s

def market_motion(s,section,camera,time):
    for i in range(4):
        x=int((i*123+27-camera*.55)%800)
        if x<410 and section in (1,2):s.blit(steam(int(time*5+i)%8),(x,135))
    if int(time*7)%31==0:
        s.fill((100,30,55),(18,88,43,2))
    for i in range(9):
        x=int((i*97-camera)%420)-10;y=235+i%3*10
        width=18+int(math.sin(time*3+i)*4)
        s.fill((80,35,65) if i%2 else (35,70,90),(x,y,width,1))
