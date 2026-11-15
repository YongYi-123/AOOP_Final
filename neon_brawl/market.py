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
    # Varied open businesses: luminous interiors, visible counters and real displays.
    x=0
    for i,w in enumerate((104,126,92,118,108,128,124)):
        kind=(i+section*2)%9
        name=('JADE NOODLES','BUBBLE TEA','LUCKY MART','PIXEL ARCADE','CIRCUIT REPAIR','GOLDEN BAKERY','FRESH FRUIT','DIM SUM','HOT SKEWERS')[kind]
        color=(red,gold,cyan,(220,100,170))[i%4]
        box((28,20,33),x,105,w-3,63)
        # Open doorway and warm interior floor establish depth instead of shutter stripes.
        box((108,73,58),x+5,110,w-14,55)
        box((229,179,99),x+8,112,w-20,4)
        box((38,30,39),x+w-29,118,19,45)
        box((159,105,64),x+w-27,156,15,7)
        for xx in range(x+12,x+w-35,22):
            box((246,208,134),xx,120,14,13)
            box((106,73,57),xx+2,123,10,1)
            box((106,73,57),xx+2,127,8,1)
        box((84,50,42),x+7,150,w-42,16)
        box((219,158,92),x+6,148,w-40,4)
        if kind in (0,7,8):
            # Cooking pots, hanging menu and bowls at the street counter.
            for k in range(max(1,(w-45)//22)):
                xx=x+13+k*22
                pygame.draw.ellipse(s,(212,199,165),(xx,141,15,7))
                box((230,168,87),xx+2,141,11,2)
                pygame.draw.arc(s,(65,54,51),(xx+3,133,9,11),0,3.14,2)
            box((180,64,62),x+8,127,12,12)
        elif kind==1:
            for k in range(4):
                xx=x+12+k*13;box((203,166,126),xx,135,8,12)
                box((235,208,170),xx-1,134,10,2);box((80,49,53),xx+3,129,1,7)
                for dx in (2,5):box((57,35,43),xx+dx,143,2,2)
        elif kind in (2,5,6):
            for row in range(2):
                for k in range(5):
                    xx=x+10+k*12;yy=135+row*7
                    pygame.draw.ellipse(s,((231,153,64),(132,177,83),(220,105,91))[(k+kind)%3],(xx,yy,9,6))
            box((202,182,144),x+7,133,3,15)
        else:
            for k in range(2):
                xx=x+12+k*27
                box((39,42,61),xx,129,20,18);box((71,178,193),xx+3,131,14,9)
                box((204,119,169),xx+4,143,12,2)
                if kind==3:
                    box((97,64,102),xx,144,21,18);box(gold,xx+4,147,3,2)
        sign(name,x+2,89,w-6,color)
        # Projecting awnings, lamps, small stools and open entrances remain below signs.
        if i%2:
            pygame.draw.polygon(s,(161,53,69),[(x+1,106),(x+w-4,106),(x+w+1,115),(x-4,115)])
            for dx in range(5,w-4,13):box((229,184,118),x+dx,107,4,8)
        for xx in (x+5,x+w-13):
            pygame.draw.ellipse(s,(195,62,69),(xx,72,7,11));box(gold,xx+2,75,2,5)
        if kind in (0,1,7,8):
            box((173,107,68),x+w-18,158,12,3)
            box((91,59,52),x+w-16,161,2,6);box((91,59,52),x+w-9,161,2,6)
        x+=w
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
