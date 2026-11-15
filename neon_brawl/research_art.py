"""Shared native-pixel research equipment, perspective and material language."""
import pygame
from functools import lru_cache
INK=(22,29,44)
PALETTES=(((64,91,91),(119,156,144),(218,197,146)),
          ((49,69,96),(108,145,172),(208,151,102)),
          ((64,58,99),(134,120,182),(115,209,195)))
def text(s,label,x,y,color=(207,226,212)):
    from font import get_font
    s.blit(get_font().render(label,color),(x,y))
def sign(s,label,rect,color=(147,217,200)):
    x,y,w,h=rect;r=pygame.draw;r.rect(s,INK,rect);r.rect(s,color,rect,1)
    from font import get_font
    image=get_font().render(label,color);s.blit(image,(x+(w-image.get_width())//2,y+(h-image.get_height())//2))
def shell(s,stage,section):
    r=pygame.draw;wall,trim,accent=PALETTES[stage]
    s.fill((18,29,42));r.rect(s,wall,(0,37,800,130))
    for x in range(0,800,50):
        r.line(s,tuple(max(0,v-9) for v in wall),(x,42),(x,166))
        r.line(s,tuple(max(0,v-9) for v in wall),(x+1,96),(x+48,96))
    r.rect(s,trim,(0,39,800,5));r.line(s,accent,(0,44),(800,44))
    for x in range(8,800,200):
        r.rect(s,(37,51,63),(x,47,184,7));r.rect(s,(174,198,177),(x+8,49,163,2))
        r.lines(s,(43,47,58),False,[(x,55),(x+18,61),(x+70,57),(x+98,62)],2)
    r.lines(s,(99,126,131),False,[(0,58),(74,58),(74,65),(340,65),(340,58),(622,58),(622,64),(800,64)],4)
    r.line(s,(163,177,163),(2,57),(71,57))
    for x,y in ((74,62),(340,62),(622,61)):r.rect(s,(177,152,112),(x-3,y-3,7,5),1)
    r.rect(s,(41,53,65),(0,158,800,9));r.line(s,trim,(0,160),(800,160),2)
    # A cool wall plane meets a warmer raised floor, with thick support columns.
    for x in range(188,800,200):
        r.polygon(s,(40,48,67),[(x,45),(x+10,45),(x+15,165),(x,165)])
        r.line(s,trim,(x+2,47),(x+6,160),2)

def desk(s,x,y,w=174):
    r=pygame.draw
    r.polygon(s,(29,33,45),[(x,y+5),(x+w,y+5),(x+w+6,y+31),(x+4,y+31)])
    r.polygon(s,(165,147,113),[(x,y),(x+w-8,y),(x+w,y+7),(x-4,y+7)])
    r.rect(s,(84,95,101),(x,y+7,w,7));r.line(s,(215,192,144),(x,y+1),(x+w-8,y+1))
    for xx in (x+5,x+w-15):r.rect(s,(53,67,80),(xx,y+14,7,17))

def crt(s,x,y,color=(129,215,188),mini=False):
    r=pygame.draw;w,h=(26,22) if mini else (40,30)
    r.polygon(s,(34,39,48),[(x,y),(x+w-5,y),(x+w,y+5),(x+w,y+h-4),(x+2,y+h-4)])
    r.rect(s,(174,177,153),(x,y,w-4,h-5));r.rect(s,(21,44,52),(x+3,y+3,w-10,h-12))
    for k in range(3):r.line(s,color,(x+5,y+5+k*3),(x+w-14+k%2*3,y+5+k*3))
    r.rect(s,(90,107,110),(x+w//2-5,y+h-5,7,5));r.rect(s,(174,177,153),(x+8,y+h-1,w-16,2))

def keyboard(s,x,y,w=30):
    r=pygame.draw;r.polygon(s,(48,46,58),[(x,y),(x+w-3,y),(x+w,y+7),(x-2,y+7)])
    r.polygon(s,(180,174,147),[(x+1,y+1),(x+w-4,y+1),(x+w-1,y+6),(x,y+6)])
    for xx in range(x+3,x+w-4,4):
        for yy in (y+2,y+4):r.rect(s,(89,96,100),(xx,yy,2,1))

def server(s,x,y,w=32,h=66,damaged=False):
    r=pygame.draw;r.rect(s,(35,45,63),(x,y,w,h));r.rect(s,(117,134,149),(x,y,w,h),2)
    for yy in range(y+6,y+h-6,10):
        r.rect(s,(60,79,91),(x+4,yy,w-8,7));r.rect(s,(141,206,160),(x+6,yy+2,2,2))
        r.line(s,(27,43,57),(x+12,yy+3),(x+w-6,yy+3))
    if damaged:
        r.polygon(s,(17,29,42),[(x+3,y+13),(x+w-4,y+20),(x+10,y+39),(x+2,y+28)])
        r.lines(s,(208,134,111),False,[(x+6,y+19),(x+15,y+25),(x+9,y+34)],1)

def far_layer(s,stage):
    r=pygame.draw;s.fill((19+stage*3,26,44+stage*5))
    for x in range(-20,800,95):
        r.rect(s,(34,45,64),(x,45,73,114));r.rect(s,(17,30,48),(x+5,56,63,95))
        for yy in range(64,149,15):r.line(s,(53,74,89),(x+10,yy),(x+61,yy),2)
        r.line(s,(62,79,91),(x+20,45),(x+44,20),2)
