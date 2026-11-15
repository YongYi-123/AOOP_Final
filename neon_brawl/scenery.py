"""Twelve original district compositions, cached by the background renderer."""
import math
import pygame
from .data import SECTIONS

def paint_section(s,stage,section):
    from font import get_font
    font=get_font()
    accents=((225,65,150),(65,175,200),(145,85,220))
    c=accents[stage]
    def box(color,x,y,w,h): s.fill(color,(x,y,w,h))
    def sign(text,x,y,width,color=c):
        box((9,12,25),x,y,width,17)
        pygame.draw.rect(s,color,(x,y,width,17),1)
        img=font.render(text,color)
        s.blit(img,(x+(width-img.get_width())//2,y+5))
    def wall(x,width,color=(27,25,45)):
        box(color,x,64,width,104)
        for yy in range(70,164,12):
            box((39,35,55),x,yy,width,1)
            for xx in range(x+(yy%24),x+width,24):box((39,35,55),xx,yy,1,12)
    if stage==0:
        if section==0:
            for i,x in enumerate((0,160,335,520,685)):
                wall(x,145)
                sign(('LANTERN','NOODLES','PIXEL BAR','NIGHT OWL','REPAIR')[i],x+12,81,120)
                box((12,15,27),x+30,111,75,54)
                for yy in range(113,166,6):box((55,40,62),x+31,yy,73,1)
                for k in range(3):
                    pygame.draw.line(s,(65,55,75),(x+120,62),(x+120,84))
                    pygame.draw.ellipse(s,(215,100,85),(x+115,76,10,14))
                box((65,80,75),x+112,139,15,27);box((105,120,100),x+111,139,17,3)
        elif section==1:
            for i,x in enumerate(range(0,800,125)):
                wall(x,120,(30,25,45))
                color=((150,55,85),(55,100,115),(145,105,45))[i%3]
                pygame.draw.polygon(s,color,[(x,100),(x+113,100),(x+124,119),(x-8,119)])
                for k in range(0,110,17):box((210,175,135),x+k,101,7,17)
                box((85,55,55),x+5,145,106,20)
                for k in range(6):
                    box((180,115+k*12,65),x+10+k*15,139,10,7)
                sign(('FOOD','TAPES','PARTS')[i%3],x+14,75,90)
            for x in range(0,800,35):
                pygame.draw.line(s,(85,70,85),(x,55),(x+35,60))
                box((225,170,95),x+16,58,3,4)
        elif section==2:
            for i,x in enumerate((0,180,370,560,735)):
                wall(x,165,(24,28,47))
                sign(('ARCADE','MIDNIGHT FM','NEON VEND','HOTEL','24 HOUR')[i],x+8,72,148,(80,170,195))
                for k in range(4):
                    box((35,65,85),x+12+k*37,108,28,41)
                    box((85,120,135),x+15+k*37,112,20,2)
                box((50,55,85),x+130,122,22,44);box(c,x+133,126,16,15)
                box((190,180,90),x+140,148,4,7)
        else:
            wall(0,800,(30,24,42))
            for x in range(20,800,150):
                box((10,12,23),x,80,120,85)
                pygame.draw.lines(s,(65,45,70),False,[(x,160),(x+120,85),(x+120,160),(x,85)],2)
                pygame.draw.polygon(s,(145,65,85),[(x+45,78),(x+75,78),(x+80,118),(x+60,130),(x+40,118)])
                pygame.draw.lines(s,(235,165,75),False,[(x+49,91),(x+60,104),(x+71,91)],2)
                box((90,65,60),x+5,145,27,20)
            sign('WARDEN TERRITORY',260,47,250,(225,155,75))
        for x in range(145,800,230):
            box((70,65,90),x,84,3,82);box((185,165,115),x-7,82,18,4)
        for x in (80,460,700):
            box((155,120,130),x,122,16,24);box((60,45,70),x+3,126,10,3)
    elif stage==1:
        if section==0:
            wall(0,800,(25,32,45))
            for x in range(0,800,190):
                pygame.draw.rect(s,(8,15,25),(x+15,82,155,83),border_radius=28)
                box((80,100,115),x+12,157,162,7)
                for k in range(8):box((130,145,145),x+25+k*18,155-k%2*4,14,2)
                sign('DISTRICT TRANSIT',x+12,60,165)
        elif section==1:
            for x in range(0,800,160):
                box((6,13,24),x,65,150,102)
                box((75,85,100),x+140,65,9,103)
                box((100,155,165),x+4,66,124,3)
                box((35,55,65),x+30,109,68,30)
                sign('LAST TRAIN  --:--',x+14,78,116)
                box((100,85,75),x+10,149,95,4)
                box((75,75,80),x+20,153,4,13);box((75,75,80),x+92,153,4,13)
        elif section==2:
            wall(0,800,(20,30,38))
            for x in range(0,800,85):
                box((60,80,88),x,76,7,91);box((105,120,120),x+2,80,2,82)
                box((80,90,90),x,95,80,8);box((115,110,85),x+12,91,5,17)
                box((32,45,55),x+22,121,45,45)
                for k in range(4):box((90,120,130),x+28,126+k*8,32,2)
            sign('HIGH VOLTAGE / SERVICE ONLY',205,52,300,(220,165,70))
        else:
            wall(0,800,(25,32,46))
            for x in range(0,800,135):
                box((65,75,92),x+4,81,119,85)
                box((8,20,30),x+10,88,106,52)
                for k in range(5):
                    pygame.draw.lines(s,c,False,[(x+15,96+k*8),(x+38,99+k*7),(x+55,92+k*9),(x+108,95+k*8)],1)
                box((130,135,125),x+15,150,90,3)
            sign('PHANTOM SECURITY CONTROL',235,51,285)
    else:
        if section==0:
            wall(0,800,(24,27,45))
            for x in range(0,800,190):
                box((55,55,85),x+5,67,166,100)
                box((14,16,35),x+20,85,132,79)
                for k in range(6):box((50,40,75),x+24+k*21,87,17,75)
                box((115,90,170),x+14,69,148,5)
                sign('SCAN // ACCESS 09',x+22,50,143)
        elif section==1:
            wall(0,800,(24,32,50))
            for x in range(0,800,160):
                pygame.draw.rect(s,(45,85,100),(x+18,79,63,82),border_radius=12)
                pygame.draw.rect(s,(75,145,150),(x+23,84,53,72),1,border_radius=10)
                pygame.draw.polygon(s,(35,70,85),[(x+48,92),(x+60,111),(x+54,139),(x+39,139),(x+34,110)])
                box((80,75,115),x+95,106,45,61);box((125,195,190),x+102,112,30,14)
                sign('LAB / SYNTH',x+9,53,134,(85,205,195))
        elif section==2:
            for x in range(0,800,90):
                box((40,35,65),x+2,57,82,110)
                box((10,14,30),x+8,64,70,96)
                for k in range(8):
                    box((60,60,85),x+12,68+k*11,62,8)
                    for j in range(6):box(c if (j+k)%3 else (65,150,155),x+16+j*9,71+k*11,3,2)
            for y in (44,49):pygame.draw.line(s,c,(0,y),(800,y),1)
        else:
            box((13,12,30),0,40,800,128)
            for x in (30,280,530,780):
                pygame.draw.polygon(s,(65,45,90),[(x-20,40),(x+20,40),(x+40,166),(x-40,166)])
                pygame.draw.lines(s,c,False,[(x,45),(x+12,104),(x+18,164)],3)
            for x in (150,400,650):
                pygame.draw.polygon(s,(50,35,80),[(x,60),(x+53,113),(x,166),(x-53,113)])
                pygame.draw.polygon(s,(125,65,145),[(x,74),(x+37,113),(x,152),(x-37,113)],2)
                box((210,95,185),x-7,104,14,18)
            sign('SIGNAL OVERLORD // CENTRAL REACTOR',228,30,340,(205,115,205))
    # Section-specific names stay in the scenery's upper zone, clear of combat HUD.
    sign(SECTIONS[stage][section],12,145,190,tuple(int(v*.8) for v in c))

def animate_section(s,stage,section,camera,time):
    if stage==1 and section==2:
        for i in range(8):
            x=int((i*61-camera*.55)%420); y=160-int((time*17+i*9)%30)
            pygame.draw.line(s,(65,85,95),(x,y),(x+6,y-6),2)
    if stage==1 and int(time*5)%17==0:
        s.fill((22,28,38),(0,66,400,3))
    if stage==2:
        for i in range(12):
            x=int((i*67-camera*.55)%410); y=78+i%5*13
            s.fill((90,130+int(math.sin(time*3+i)*30),155),(x,y,2,2))
        if section==3:
            y=90+int(math.sin(time*1.4)*15)
            pygame.draw.line(s,(75,45,105),(0,y),(400,y),1)
