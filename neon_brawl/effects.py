"""Readable ground warnings use the same attack data as collision resolution."""
import math
import pygame
from .data import ATTACKS
from .animation import attack_phase

WARNING=(235,165,75)
DANGER=(250,105,155)
ENERGY=(125,235,250)


def star(surface, color, x, y, radius=3):
    x, y, radius = int(x), int(y), max(1, int(radius))
    pygame.draw.polygon(surface, color, [(x,y-radius),(x+1,y-1),(x+radius,y),
                                       (x+1,y+1),(x,y+radius),(x-1,y+1),
                                       (x-radius,y),(x-1,y-1)])


def draw_impact(surface, effect, camera):
    progress = effect.age/effect.duration
    special = effect.kind == 'special'
    strong = ATTACKS[effect.kind].knockdown
    color = ENERGY if special else (255, 207, 136) if strong else (255, 192, 207)
    # A small candy-coloured cluster; never a full-screen flash.
    color = tuple(int(c*(1-progress*.55)) for c in color)
    x, y = int(effect.x-camera), int(effect.y)
    count = 7 if special else 5 if strong else 4
    for i in range(count):
        angle = i*math.tau/count+.35
        radius = 4+progress*(23 if strong else 15)
        dx = math.cos(angle)*radius+effect.direction*progress*5
        dy = math.sin(angle)*radius*.72-progress*6
        star(surface, color if i%2 else (min(255,color[0]+30),min(255,color[1]+30),min(255,color[2]+30)),
             x+dx, y+dy, max(1, (4 if strong else 3)*(1-progress)))
    if progress < .35:
        star(surface, (245, 250, 235), x, y, 5 if strong else 3)


def fighter_effects(surface, fighter, camera, behind=False):
    """Small ground dust / ghosts behind bodies; short energy ribbons in front."""
    x, foot = round(fighter.x-camera), round(fighter.y)
    y = foot-round(fighter.jump)-26
    cyan = fighter.name == 'NOVA'
    color = ENERGY if cyan or fighter.name == 'RELAY' else (248, 150, 216) if fighter.name == 'NULL' else (255, 205, 133)
    if behind:
        if fighter.state == 'dodge':
            from .art import sprite
            from .animation import animation_sample
            state, frame = animation_sample(fighter)
            image = sprite(fighter.name, state, frame, fighter.facing, getattr(fighter, 'outfit', 0)).copy()
            image.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
            for offset, alpha in ((18, 35), (10, 65)):
                image.set_alpha(alpha)
                surface.blit(image, (x-32-fighter.facing*offset, foot-59))
        jumping = 0 < fighter.jump_age < .14 or fighter.jump_age > .55
        moving = fighter.state in ('walk', 'approach', 'positioning', 'dodge')
        if jumping or moving and int(fighter.age*12)%4 == 0:
            for i in range(3 if jumping else 2):
                offset = (i-1)*7 if jumping else -fighter.facing*(8+i*5)
                pygame.draw.ellipse(surface, (97, 109, 138), (x+offset-3, foot-3-i%2, 6, 3))
                pygame.draw.line(surface, (153, 166, 186), (x+offset-1,foot-3-i%2), (x+offset+1,foot-3-i%2))
        return
    swing = fighter.swing
    if not swing:return
    attack = ATTACKS[swing.name]
    phase, progress = attack_phase(swing.name, swing.age, getattr(fighter, 'attack_recovery', 1))
    if swing.name == 'special':
        if phase == 'anticipation':
            # Gather a few beads toward the hand; no damage-looking burst yet.
            for i in range(4):
                angle = i*math.tau/4+progress
                radius = 13-progress*8
                star(surface, color, x+fighter.facing*12+math.cos(angle)*radius, y+math.sin(angle)*radius, 2)
        elif phase == 'attack':
            radius = round(18+(attack.reach-18)*math.sin(progress*math.pi/2))
            pygame.draw.ellipse(surface, color, (x-radius,y-12,radius*2,25), 2)
            pygame.draw.arc(surface, (220,255,250), (x-radius+4,y-8,max(2,radius*2-8),18), .15, 2.8, 1)
            for i in range(5):
                angle = i*math.tau/5+progress*1.3
                star(surface, color, x+math.cos(angle)*radius, y+math.sin(angle)*12, 3)
        elif progress < .4:
            for i in range(3): star(surface,color,x+(i-1)*19,y-8-progress*18,2)
    elif phase == 'attack' and swing.name not in ('shot', 'snipe', 'orb', 'laser', 'strike', 'wave', 'pulse'):
        direction = swing.direction
        reach = min(attack.reach, 40)
        center = x+direction*(14+progress*8)
        # Open crescent and tiny stars mark travel without covering faces.
        rect = pygame.Rect(center-13, y-11, 26, 25)
        start, end = (-1.1, 1.0) if direction > 0 else (2.1, 4.2)
        pygame.draw.arc(surface, color, rect, start, end, 2)
        if progress > .3: star(surface, (235,248,248), x+direction*reach, y, 2)
        if attack.knockdown:
            radius = round(10+progress*24)
            pygame.draw.arc(surface, color, (x-radius,foot-7,radius*2,12), 0, math.pi, 2)

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
