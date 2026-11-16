"""Original low-resolution sprite construction; cached animation cels."""
import math
from functools import lru_cache
import pygame
from .data import ROSTER, ENEMIES, ATTACKS
from .outfits import outfit_for, BOSS_NAMES
from .characters import fighter_cel
from .effects import attack_effects
from .ambient import draw_cats
from .scenery import paint_section, animate_section, visual_section

INK=(12,10,28)
WHITE=(225,240,245)

@lru_cache(maxsize=2048)
def sprite(name, state='idle', frame=0, facing=1, outfit=0):
    image = fighter_cel(name, state, frame, outfit)
    return pygame.transform.flip(image, True, False) if facing < 0 else image

@lru_cache(maxsize=28)
def background(stage,layer,section=0):
    s=pygame.Surface((800,300),pygame.SRCALPHA)
    accents=((235,60,155),(60,185,220),(155,85,245))
    c=accents[stage]
    if layer==0:
        from .research_art import far_layer
        far_layer(s,stage)
        return s
    paint_section(s,stage,section)
    return s

class Renderer:
    def __init__(self,font):
        self.font=font
        self.background_key=None
        self.background_frame=pygame.Surface((400,166))
        self.previous_background=None
        self.background_changed=0.
    def backdrop(self,s,stage,section,camera,time):
        key=(stage,section)
        if key!=self.background_key:
            self.previous_background=self.background_frame.copy() if self.background_key is not None else None
            self.background_key=key;self.background_changed=time
        for layer,factor in ((0,.18),(1,.55)):
            bg=background(stage,layer,section);offset=int(camera*factor)%800
            self.background_frame.blit(bg,(-offset,0));self.background_frame.blit(bg,(800-offset,0))
        s.blit(self.background_frame,(0,0))
        age=time-self.background_changed
        if self.previous_background is not None and 0<=age<.45:
            self.previous_background.set_alpha(int(255*(1-age/.45)))
            s.blit(self.previous_background,(0,0))
        elif age>=.45:self.previous_background=None
    def text(self,s,text,x,y,color=WHITE,scale=1):
        image=self.font.render(str(text),color,scale=scale)
        s.blit(image,(int(x),int(y)))
    def center(self,s,text,y,color=WHITE,scale=1):
        image=self.font.render(str(text),color,scale=scale)
        s.blit(image,((400-image.get_width())//2,y))
    def world(self,s,campaign,time):
        stage=campaign.stage; cam=campaign.camera
        section=visual_section(campaign)
        self.backdrop(s,stage,section,cam,time)
        s.fill((25,24,43),(0,166,400,134))
        for y in range(170,300,18):
            s.fill((42,39,61),(0,y,400,1))
            for x in range(-40,440,55): s.fill((42,39,61),(x-int(cam)%55+(y%36),y,1,18))
        # Raised access-floor covers and recessed service strips remain decorative.
        for xx in range(-70,470,95):
            x=xx-int(cam*.85)%95
            pygame.draw.polygon(s,(35,44,62),[(x,188),(x+41,188),(x+48,197),(x+5,197)])
            pygame.draw.line(s,(71,91,105),(x+4,189),(x+37,189))
        c=((235,60,155),(60,185,220),(155,85,245))[stage]
        s.fill(c,(0,167,400,2))
        for x in range(0,1500,125):
            xx=int(x-cam)
            if -40<xx<440:
                pygame.draw.ellipse(s,tuple(v//4 for v in c),(xx,244,45,5))
                s.fill(c,(xx+7,245,24,1))
        if stage==1:
            for x in range(0,400,20): pygame.draw.polygon(s,(145,123,55),[(x,270),(x+8,270),(x-5,278),(x-13,278)])
        if stage>0 and campaign.wave<3:
            phase=campaign.hazard_clock%7
            if 3.4<phase<5.15:
                color=(255,80,110) if phase>4.7 else (175,125,55)
                for x in range(0,400,12):
                    pygame.draw.lines(s,color,False,[(x,251),(x+4,247),(x+8,255),(x+12,251)],2)
                self.text(s,'LIVE CIRCUIT! MOVE UP / JUMP',122,272,color)
        animate_section(s,stage,section,cam,time,max((e.phase for e in campaign.enemies if e.boss),default=1),any(e.boss and e.swing for e in campaign.enemies))
        campaign.staff.draw(s,cam,time)
        actors=sorted(campaign.enemies+[campaign.player],key=lambda f:f.y)
        for f in actors:
            x,y=int(f.x-cam),int(f.y)
            if not f.alive and f.defeat_age>1.4: continue
            if f.name not in ROSTER: attack_effects(s,f,cam,time)
            pygame.draw.ellipse(s,(12,12,24),(x-15,y-4,30,7))
            frame=int(time*(13 if f.swing else 8))%4
            if f.swing:
                from .data import ATTACKS
                a=ATTACKS[f.swing.name]
                frame=min(3,int(f.swing.age/(a.windup+a.active+a.recovery)*4))
            if not f.alive: frame=min(3,int(f.defeat_age/.34))
            image=sprite(f.name,'air' if f.jump>0 and not f.swing else f.state,frame,f.facing,getattr(f,"outfit",0))
            if not f.alive:
                image=image.copy()
                image.set_alpha(max(0,int(255*(1-max(0,f.defeat_age-.55)/.9))))
                if f.name=='RELAY':
                    for k in range(6):
                        dx=int(math.sin(k*2.3)*f.defeat_age*24)
                        dy=int(math.cos(k*2.3)*f.defeat_age*20)
                        s.fill((100,220,225),(x+dx,y-28+dy,2,2))
                elif f.name=='NULL':
                    for row in range(int(f.defeat_age*30)):
                        image.fill((0,0,0,0),(0,(row*17)%64,64,2))
            if f.state=='phase':
                radius=25+int(math.sin(time*20)*4)
                pygame.draw.polygon(s,(235,110,225),[(x-radius,y-28),(x,y-70),(x+radius,y-28),(x,y+2)],2)
                s.fill((16,17,35),(90,61,220,13))
                self.center(s,'SIGNAL OVERLOAD',65,(255,140,220))
            if f.flash:
                image=image.copy(); image.fill((130,100,100,0),special_flags=pygame.BLEND_RGBA_ADD)
            if f.name in ('WARDEN','RELAY','NULL'):
                image=pygame.transform.scale(image,(80,80))
                s.blit(image,(x-40,y-74-int(f.jump)))
            else: s.blit(image,(x-32,y-59-int(f.jump)))
            if f.alive and f.name not in ROSTER:
                s.fill((20,12,30),(x-15,y-66,30,3)); s.fill(c,(x-15,y-66,int(30*f.health/f.max_health),2))
        draw_cats(s,campaign.cats,cam,time)
        for x,y,t in campaign.effects:
            xx=int(x-cam); yy=int(y); r=int(5+(1-t/.2)*15)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1)):
                pygame.draw.line(s,(255,235,145),(xx+dx*3,yy+dy*3),(xx+dx*r,yy+dy*r),2)
        gate=int(campaign.bounds[1]-cam)
        if 0<gate<400:
            for yy in range(177,265,12):
                pygame.draw.lines(s,(155,60,105),False,[(gate-3,yy),(gate+2,yy+5),(gate-3,yy+10)],1)
        if campaign.encounter_age<2 and not any(e.boss for e in campaign.enemies):
            from .data import STAGES
            s.fill((13,13,30),(94,59,212,28))
            self.center(s,STAGES[stage][0],64,c)
            self.center(s,f'BLOCK {campaign.wave+1} / 4',77)
        for x,y in campaign.pickups:
            xx=int(x-cam); pygame.draw.polygon(s,(255,210,130),[(xx-6,y-7),(xx+7,y-7),(xx+5,y),(xx-5,y)])
            s.fill((255,95,125),(xx-3,y-5,5,2))
        self.hud(s,campaign)
    def hud(self,s,c):
        p=c.player
        s.fill((12,10,27),(0,0,400,38))
        self.text(s,p.name,9,5,ROSTER[p.name].color)
        self.text(s,f'{c.score:07d}',150,5)
        self.text(s,f'STAGE {c.stage+1}  {int(c.elapsed)//60:02}:{int(c.elapsed)%60:02}',275,5)
        for y,value,maxval,color in ((18,p.health,p.max_health,(245,80,130)),(27,p.energy,100,(75,225,240))):
            s.fill((45,35,60),(9,y,126,6)); s.fill(color,(10,y+1,int(124*value/maxval),4))
        self.text(s,f'HP {p.health}/{p.max_health}',143,19)
        if c.combo>1: self.text(s,f'{c.combo} HITS',300,23,(255,220,90))
        self.text(s,'J COMBO K HEAVY L JUMP U SPECIAL I DODGE',12,288,(150,150,185))
        bosses=[e for e in c.enemies if e.boss and e.alive]
        if bosses:
            s.fill((16,17,35),(0,38,400,23))
            if bosses[0].state in ('intro','guard','teleport','summon') or bosses[0].swing:s.fill((16,17,35),(0,72,400,14))
            b=bosses[0]; self.center(s,f'{BOSS_NAMES[b.name]} / P{b.phase}',42,(255,180,100))
            if b.state=='intro': self.center(s,'INCOMING // WATCH THE WINDUP',76,(245,200,120))
            elif b.swing: self.center(s,b.swing.name.upper()+' // CHANGE LANES OR DODGE',76,(245,200,120))
            elif b.state=='guard': self.center(s,'GUARD // HEAVY ATTACK BREAKS ARMOR',76,(245,200,120))
            elif b.state=='teleport': self.center(s,'SHIFT // WATCH THE LANDING MARK',76,(125,230,245))
            elif b.state=='summon': self.center(s,'DIGITAL REINFORCEMENTS',76,(125,230,245))
            s.fill((45,25,55),(75,53,250,5)); s.fill((230,65,155),(76,54,int(248*b.health/b.max_health),3))
