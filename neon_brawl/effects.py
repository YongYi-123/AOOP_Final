"""Readable ground warnings use the same attack data as collision resolution."""
import pygame
from .data import ATTACKS

WARNING=(235,165,75)
DANGER=(250,105,155)
ENERGY=(125,235,250)

def attack_effects(surface,fighter,camera,time):
    old=surface.get_clip()
    surface.set_clip(pygame.Rect(0,160,400,120))
    swing=fighter.swing
    if swing:
        a=ATTACKS[swing.name]
        cx,cy=swing.target if a.shape=='target' else (fighter.x,fighter.y)
        x,y=int(cx-camera),int(cy)
        direction=swing.direction
        if swing.age<a.windup:
            length=a.reach+10+int(a.mobility*a.active)
            radial=a.shape in ('target','radial') or swing.name=='sweep'
            box=pygame.Rect(x-length if radial or direction<0 else x-8,y-a.lane,
                            length*2 if radial else length+8,a.lane*2)
            pygame.draw.rect(surface,WARNING,box,1)
            for xx in range(box.left+3,box.right,14):
                pygame.draw.line(surface,(95,70,70),(xx,box.centery-2),(xx+5,box.centery+2))
            if a.shape=='target':
                pygame.draw.line(surface,DANGER,(x-9,y),(x+9,y),1)
                pygame.draw.line(surface,DANGER,(x,y-9),(x,y+9),1)
            else:
                edge=x+direction*min(length,75)
                pygame.draw.lines(surface,WARNING,False,[(edge-direction*5,y-4),(edge,y),(edge-direction*5,y+4)],2)
        elif swing.age<=a.windup+a.active:
            if swing.name in ('shot','snipe','orb','laser'):
                pygame.draw.line(surface,ENERGY,(x+direction*14,y-25),(x+direction*a.reach,y-25),3 if swing.name!='laser' else 5)
                pygame.draw.line(surface,(245,245,255),(x+direction*14,y-25),(x+direction*a.reach,y-25),1)
            elif a.shape=='target':
                pygame.draw.line(surface,ENERGY,(x,160),(x,y),5)
                pygame.draw.rect(surface,DANGER,(x-a.reach,y-a.lane,a.reach*2,a.lane*2),2)
            elif a.shape=='radial':
                radius=int(a.reach*(.5+.5*(swing.age-a.windup)/a.active))
                pygame.draw.ellipse(surface,ENERGY,(x-radius,y-a.lane,radius*2,a.lane*2),2)
            elif a.mobility:
                for k in range(3): pygame.draw.line(surface,DANGER,(x-direction*(18+k*8),y-20+k*7),(x-direction*(32+k*8),y-20+k*7),2)
    if fighter.state=='teleport' and fighter.destination:
        x,y=int(fighter.destination[0]-camera),int(fighter.destination[1])
        pygame.draw.polygon(surface,ENERGY,[(x-16,y),(x,y-12),(x+16,y),(x,y+8)],2)
        for offset in (-8,0,8): pygame.draw.line(surface,(110,100,190),(x+offset,y-42),(x+offset,y-12))
    if fighter.state=='guard':
        x,y=int(fighter.x-camera),int(fighter.y)
        pygame.draw.lines(surface,WARNING,False,[(x-22,y-44),(x-26,y-17),(x,y),(x+26,y-17),(x+22,y-44)],2)
    if fighter.state=='summon':
        x,y=int(fighter.x-camera),int(fighter.y)
        pygame.draw.ellipse(surface,ENERGY,(x-29,y-8,58,15),2)
    surface.set_clip(old)
