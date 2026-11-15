"""Original low-resolution sprite construction; cached animation cels."""
import math
from functools import lru_cache
import pygame
from .data import ROSTER, ENEMIES

INK=(12,10,28)
WHITE=(225,240,245)

@lru_cache(maxsize=512)
def sprite(name, state='idle', frame=0, facing=1):
    s=pygame.Surface((64,64),pygame.SRCALPHA)
    color=ROSTER[name].color if name in ROSTER else ENEMIES[name][2]
    heavy=name in ('BRUNO','bruiser','WARDEN','NULL')
    w=9 if heavy else 7
    skin=(220,155,115) if name not in ('NULL','RELAY','ranged') else (150,175,195)
    dark=tuple(c//2 for c in color)
    bob=(frame%2) if state in ('idle','walk','victory') else 0
    attack=state in ('light','combo2','combo3','heavy','air','special','enemy','smash','sweep','shot')
    stride=(-3,0,3,0)[frame%4] if state=='walk' else 0
    def rect(c,r): pygame.draw.rect(s,c,r)
    def limb(points,c,width=5):
        pygame.draw.lines(s,INK,False,points,width+2)
        pygame.draw.lines(s,c,False,points,width)
    # Boots, articulated trousers, jacket, collar, individual face pixels.
    limb([(29,40),(27+stride,49),(25+stride,56)],(46,48,82),6)
    limb([(36,40),(37-stride,49),(39-stride,56)],(65,64,105),6)
    rect(INK,(20+stride,54,10,5)); rect(dark,(20+stride,55,9,2))
    rect(INK,(35-stride,54,11,5)); rect(color,(36-stride,55,9,2))
    pygame.draw.polygon(s,INK,[(32-w-2,24+bob),(32+w+2,24+bob),(32+w,43),(32-w,43)])
    pygame.draw.polygon(s,color,[(32-w,25+bob),(32+w,25+bob),(32+w-2,41),(32-w+1,41)])
    rect(dark,(25,30+bob,5,10)); rect(WHITE,(32,25+bob,2,15))
    rect(INK,(24,40,17,3)); rect((255,215,100),(31,40,4,2))
    limb([(32-w,27+bob),(20,34),(22,39)],dark)
    if state=='hurt': bob=3
    reach=55 if attack and frame%4 in (1,2) else 43
    limb([(32+w,27+bob),(43,29+bob),(reach,24 if attack else 36)],color)
    rect(INK,(reach-3,(21 if attack else 33),7,7)); rect(skin,(reach-2,(22 if attack else 34),5,4))
    rect(INK,(25,9+bob,15,17)); rect(skin,(27,11+bob,11,13))
    rect((135,85,85),(27,20+bob,3,3)); rect(WHITE,(34,16+bob,3,2)); rect(INK,(36,16+bob,1,2))
    if name=='NOVA':
        rect(color,(24,7+bob,15,7)); pygame.draw.polygon(s,color,[(25,10),(18,19),(23,25),(28,12)])
        rect(INK,(27,14+bob,11,3)); rect(WHITE,(33,14+bob,4,1))
    elif name=='BRUNO' or name=='WARDEN':
        rect(color,(24,8+bob,17,5)); rect(dark,(22,12+bob,21,2)); rect(INK,(29,21+bob,9,4))
    elif name=='NULL':
        rect(INK,(23,7,18,8)); rect(color,(24,10,17,3)); rect(WHITE,(29,16,10,2))
        pygame.draw.polygon(s,dark,[(22,25),(13,49),(26,44)])
    elif name in ('ranged','RELAY'):
        rect(dark,(23,8+bob,19,9)); rect(color,(25,15+bob,16,3)); rect(WHITE,(30,16+bob,9,1))
        if attack: rect(dark,(46,22,15,6)); rect(WHITE,(58,23,3,3))
    else:
        pygame.draw.polygon(s,INK,[(24,15+bob),(24,8+bob),(29,5+bob),(32,8+bob),(38,7+bob),(40,14+bob)])
        rect(color,(24,13+bob,15,2))
        if name=='runner': rect(color,(16,22,10,3))
    if state=='special':
        for i in range(6):
            a=i*math.tau/6+frame
            x,y=32+int(math.cos(a)*27),31+int(math.sin(a)*24)
            pygame.draw.line(s,WHITE,(x,y),(x+3,y-4),2)
    if state=='victory':
        limb([(38,27),(43,17),(42,7)],color)
    if state in ('knockdown','defeated'):
        s=pygame.transform.rotate(s,90)
        shifted=pygame.Surface((64,64),pygame.SRCALPHA)
        shifted.blit(s,(0,22)); s=shifted
    if state=='dodge': s.set_alpha(150)
    return pygame.transform.flip(s,True,False) if facing<0 else s

@lru_cache(maxsize=6)
def background(stage,layer):
    s=pygame.Surface((800,300),pygame.SRCALPHA)
    accents=((235,60,155),(60,185,220),(155,85,245))
    c=accents[stage]
    if layer==0:
        s.fill((10+stage*3,9,27+stage*6))
        for i in range(22):
            x=i*39; height=45+(i*47)%100
            pygame.draw.rect(s,(21,21+stage*4,47),(x,160-height,35,height))
            for y in range(165-height,155,9):
                for xx in range(x+4,x+30,7):
                    if (xx+y)%4: s.fill((45,50,84),(xx,y,2,3))
        return s
    for i in range(8):
        x=i*102
        pygame.draw.rect(s,(28,25,48),(x,65,95,103))
        pygame.draw.rect(s,(45,40,65),(x+3,68,89,95),1)
        if stage==0:
            pygame.draw.rect(s,(14,15,30),(x+12,112,60,49))
            for y in range(115,160,5): s.fill((55,45,74),(x+13,y,58,1))
            pygame.draw.rect(s,c,(x+18,77,55,23),2)
            for j in range(5):
                s.fill(c,(x+23+j*9,82,5,12)); s.fill((20,15,35),(x+25+j*9,86,3,2))
            s.fill((145,95,110),(x+76,120,13,21)); s.fill(c,(x+78,123,8,1))
        elif stage==1:
            pygame.draw.rect(s,(8,12,25),(x+10,83,73,64),border_radius=20)
            pygame.draw.rect(s,(75,75,95),(x+8,66,78,5))
            s.fill(c,(x+16,68,62,2)); s.fill((110,105,115),(x+86,70,7,96))
            s.fill((35,50,65),(x+26,99,38,21)); s.fill(c,(x+30,104,26,2))
        else:
            s.fill((13,17,35),(x+8,76,78,78))
            for j in range(6):
                s.fill((40,50,75),(x+12,80+j*12,69,8))
                for k in range(9): s.fill(c if (k+j)%3 else (80,235,200),(x+16+k*7,82+j*12,2,2))
            pygame.draw.lines(s,c,False,[(x+2,60),(x+2,40),(x+80,40),(x+80,62)],2)
    return s

class Renderer:
    def __init__(self,font): self.font=font
    def text(self,s,text,x,y,color=WHITE,scale=1):
        image=self.font.render(str(text),color,scale=scale)
        s.blit(image,(int(x),int(y)))
    def center(self,s,text,y,color=WHITE,scale=1):
        image=self.font.render(str(text),color,scale=scale)
        s.blit(image,((400-image.get_width())//2,y))
    def world(self,s,campaign,time):
        stage=campaign.stage; cam=campaign.camera
        for layer,factor in ((0,.18),(1,.55)):
            bg=background(stage,layer); offset=int(cam*factor)%800
            s.blit(bg,(-offset,0)); s.blit(bg,(800-offset,0))
        s.fill((25,24,43),(0,166,400,134))
        for y in range(170,300,18):
            s.fill((42,39,61),(0,y,400,1))
            for x in range(-40,440,55): s.fill((42,39,61),(x-int(cam)%55+(y%36),y,1,18))
        c=((235,60,155),(60,185,220),(155,85,245))[stage]
        s.fill(c,(0,167,400,2))
        for x in range(0,1500,125):
            xx=int(x-cam)
            if -40<xx<440:
                pygame.draw.ellipse(s,tuple(v//4 for v in c),(xx,244,45,5))
                s.fill(c,(xx+7,245,24,1))
        if stage==1:
            for x in range(0,400,20): pygame.draw.polygon(s,(145,123,55),[(x,270),(x+8,270),(x-5,278),(x-13,278)])
        if stage==0:
            for i in range(45):
                x=int((i*71-time*48)%420); y=int((i*43+time*190)%300)
                pygame.draw.line(s,(75,85,130),(x,y),(x-2,y+6))
        if stage>0:
            phase=campaign.hazard_clock%7
            if 3.4<phase<5.15:
                color=(255,80,110) if phase>4.7 else (175,125,55)
                for x in range(0,400,12):
                    pygame.draw.lines(s,color,False,[(x,251),(x+4,247),(x+8,255),(x+12,251)],2)
                self.text(s,'LIVE RAIL! MOVE UP / JUMP',122,272,color)
        actors=sorted(campaign.enemies+[campaign.player],key=lambda f:f.y)
        for f in actors:
            x,y=int(f.x-cam),int(f.y)
            if not f.alive and f.age%1<.2: continue
            pygame.draw.ellipse(s,(12,12,24),(x-15,y-4,30,7))
            frame=int(time*(13 if f.swing else 8))%4
            if f.swing:
                from .data import ATTACKS
                a=ATTACKS[f.swing.name]
                frame=min(3,int(f.swing.age/(a.windup+a.active+a.recovery)*4))
                if f.swing.age<a.windup and f.name not in ROSTER:
                    width=a.reach if f.swing.name!='shot' else 170
                    pygame.draw.line(s,(240,105,90),(x,y),(x+f.facing*width,y),2)
                    self.text(s,'!',x-2,y-64,(255,210,85))
            if f.swing and f.swing.name=='shot':
                from .data import ATTACKS
                a=ATTACKS['shot']
                if a.windup<=f.swing.age<=a.windup+a.active:
                    pygame.draw.line(s,(155,245,255),(x+f.facing*18,y-24),(x+f.facing*240,y-24),3)
                    pygame.draw.line(s,WHITE,(x+f.facing*18,y-24),(x+f.facing*240,y-24),1)
            image=sprite(f.name,'air' if f.jump>0 and not f.swing else f.state,frame,f.facing)
            if f.flash:
                image=image.copy(); image.fill((130,100,100,0),special_flags=pygame.BLEND_RGBA_ADD)
            s.blit(image,(x-32,y-59-int(f.jump)))
            if f.alive and f.name not in ROSTER:
                s.fill((20,12,30),(x-15,y-66,30,3)); s.fill(c,(x-15,y-66,int(30*f.health/f.max_health),2))
        for x,y,t in campaign.effects:
            xx=int(x-cam); yy=int(y); r=int(5+(1-t/.2)*15)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1)):
                pygame.draw.line(s,(255,235,145),(xx+dx*3,yy+dy*3),(xx+dx*r,yy+dy*r),2)
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
            b=bosses[0]; self.center(s,f'{b.name} / PHASE {b.phase}',42,(255,180,100))
            s.fill((45,25,55),(75,53,250,5)); s.fill((230,65,155),(76,54,int(248*b.health/b.max_health),3))
