"""Non-blocking presentation flow and keyboard-driven campaign controller."""
import math
import pygame
from .model import Campaign
from .data import ROSTER, STAGES
from .art import Renderer, sprite, background

MOVEMENT={pygame.K_a:(-1,0),pygame.K_d:(1,0),pygame.K_w:(0,-1),pygame.K_s:(0,1),
          pygame.K_LEFT:(-1,0),pygame.K_RIGHT:(1,0),pygame.K_UP:(0,-1),pygame.K_DOWN:(0,1)}
ACTIONS={pygame.K_j:'light',pygame.K_k:'heavy',pygame.K_l:'jump',pygame.K_u:'special',pygame.K_i:'dodge',pygame.K_e:'pickup'}
CONFIRM=(pygame.K_RETURN,pygame.K_KP_ENTER,pygame.K_SPACE)

class BrawlGame:
    def __init__(self,font,audio=None):
        self.renderer=Renderer(font)
        self.audio=audio
        self.screen='intro'
        self.time=self.screen_time=0.
        self.selection=0
        self.campaign=None
        self.held=set()
        self.pause_selection=0
        self.controls_return='playing'
        self.wants_exit=False
        self.started=False
        self.pending_attack=None
        self.buffer_time=0.
        self.tutorial_player=Campaign().player
        self.seen_actions=set()

    @property
    def paused(self): return self.screen in ('paused','controls')
    def sound(self,name):
        if self.audio:
            mapped={'hit':'brawl_light','boom':'brawl_heavy','laser':'brawl_special','skid':'brawl_dodge',
                    'win':'brawl_win','loss':'brawl_loss','bounce':'brawl_hurt','impact':'brawl_impact',
                    'defeat':'brawl_defeat','jump':'brawl_jump'}.get(name,name)
            self.audio.play(mapped)
    def change(self,screen):
        self.pending_attack=None
        self.screen=screen; self.screen_time=0; self.held.clear()
    def pause(self):
        self.held.clear()
        if self.screen=='playing': self.change('paused')
    def handle_event(self,event):
        if event.type==pygame.WINDOWFOCUSLOST: self.pause(); return
        if event.type==pygame.KEYUP: self.held.discard(event.key); return
        if event.type!=pygame.KEYDOWN or getattr(event,'repeat',False): return
        key=event.key
        if key in self.held: return
        self.held.add(key)
        confirm=key in CONFIRM
        if self.screen=='intro' and (confirm or key==pygame.K_ESCAPE):
            self.change('title'); self.sound('confirm')
        elif self.screen=='title':
            if confirm: self.change('select'); self.sound('confirm')
            elif key==pygame.K_ESCAPE: self.wants_exit=True
        elif self.screen=='select':
            if key in (pygame.K_a,pygame.K_LEFT,pygame.K_d,pygame.K_RIGHT):
                self.selection=(self.selection+(-1 if key in (pygame.K_a,pygame.K_LEFT) else 1))%3
                self.sound('machine')
            elif confirm:
                self.campaign=Campaign(tuple(ROSTER)[self.selection]); self.tutorial_player=Campaign(tuple(ROSTER)[self.selection]).player
                self.change('tutorial'); self.sound('confirm')
            elif key==pygame.K_ESCAPE: self.change('title')
        elif self.screen in ('tutorial','controls'):
            if confirm or key==pygame.K_ESCAPE:
                self.change(self.controls_return if self.screen=='controls' else 'playing')
                self.started=True
            elif key in ACTIONS:
                action=ACTIONS[key]
                self.tutorial_player.act(action)
                self.seen_actions.add(action)
                self.sound('hit' if action in ('light','heavy') else 'powerup')
        elif self.screen=='playing':
            if key==pygame.K_ESCAPE: self.pause()
            elif key in ACTIONS:
                action=ACTIONS[key]
                if action=='pickup': self.campaign.pickup()
                elif self.campaign.player.act(action): self.sound({'heavy':'boom','special':'laser','dodge':'skid','jump':'jump'}.get(action,'hit'))
                elif action in ('light','heavy','special'):
                    self.pending_attack=action; self.buffer_time=.18
        elif self.screen=='paused':
            if key==pygame.K_ESCAPE: self.change('playing')
            elif key in (pygame.K_w,pygame.K_UP,pygame.K_s,pygame.K_DOWN):
                self.pause_selection=(self.pause_selection+(-1 if key in (pygame.K_w,pygame.K_UP) else 1))%3
                self.sound('machine')
            elif confirm:
                if self.pause_selection==0: self.change('playing')
                elif self.pause_selection==1: self.controls_return='paused'; self.change('controls')
                else: self.wants_exit=True
        elif self.screen in ('checkpoint','stage_clear'):
            if key==pygame.K_e: self.campaign.pickup()
            if confirm:
                self.campaign.advance()
                self.change('ending' if self.campaign.state=='victory' else 'playing')
                self.sound('win' if self.screen=='ending' else 'confirm')
        elif self.screen=='ending':
            if confirm or key==pygame.K_ESCAPE: self.change('results')
        elif self.screen=='game_over':
            if confirm or key==pygame.K_ESCAPE: self.change('results')
        elif self.screen=='results':
            if confirm or key==pygame.K_ESCAPE: self.wants_exit=True

    def update(self,dt):
        dt=max(0,min(dt,.05)); self.time+=dt; self.screen_time+=dt
        if self.screen=='intro':
            if int((self.screen_time-dt)*2)!=int(self.screen_time*2) and self.screen_time<2: self.sound('machine')
            if self.screen_time-dt<3<=self.screen_time: self.sound('glitch')
            if self.screen_time-dt<8<=self.screen_time: self.sound('win')
            if self.screen_time>=11: self.change('title')
        elif self.screen in ('tutorial','controls'):
            self.tutorial_player.tick(dt)
            if self.screen=='tutorial' and self.screen_time>=9: self.started=True; self.change('playing')
        elif self.screen=='playing':
            if self.pending_attack:
                self.buffer_time-=dt
                if self.buffer_time<=0: self.pending_attack=None
                elif self.campaign.player.act(self.pending_attack):
                    self.sound('hit'); self.pending_attack=None
            dx=sum(MOVEMENT[k][0] for k in self.held if k in MOVEMENT)
            dy=sum(MOVEMENT[k][1] for k in self.held if k in MOVEMENT)
            self.campaign.update(dt,(max(-1,min(1,dx)),max(-1,min(1,dy))))
            for event in self.campaign.events:
                self.sound({'hit':'impact','hurt':'bounce','defeat':'defeat','clear':'win','lose':'loss','pickup':'powerup'}.get(event,'machine'))
            if self.campaign.state in ('checkpoint','stage_clear'): self.change(self.campaign.state)
            elif self.campaign.state=='defeat': self.change('game_over')
        elif self.screen=='ending' and self.screen_time>=10: self.change('results')

    def result(self):
        c=self.campaign
        return {'score':c.score if c else 0,'tickets':c.tickets if c and self.started else 0,
                'kills':c.kills if c else 0,'combo':c.best_combo if c else 0,
                'damage':c.damage_received if c else 0,'stage':c.stage+1 if c else 0,
                'time':int(c.elapsed) if c else 0,'victory':bool(c and c.state=='victory')}

    def panel(self,s,title,lines):
        overlay=pygame.Surface((400,300),pygame.SRCALPHA); overlay.fill((5,4,18,215)); s.blit(overlay,(0,0))
        pygame.draw.rect(s,(60,210,235),(30,50,340,205),1)
        self.renderer.center(s,title,65,(255,105,180),2)
        for i,line in enumerate(lines): self.renderer.center(s,line,108+i*18)

    def draw(self,s):
        r=self.renderer
        if self.campaign and self.screen not in ('title','intro','select','tutorial','controls'):
            r.world(s,self.campaign,self.time)
            if self.campaign.hitstop>0:
                shifted=s.copy(); s.fill((8,7,20)); s.blit(shifted,(2 if int(self.time*60)%2 else -2,1))
        else:
            s.blit(background(0,0),(0,0)); s.blit(background(0,1),(-int(self.time*12)%400-200,0))
            s.fill((18,17,34),(0,168,400,132))
        screen=self.screen
        if screen=='intro':
            t=self.screen_time
            if t<1:
                s.fill((0,0,0)); pygame.draw.line(s,(175,255,255),(int(200-t*190),150),(int(200+t*190),150),max(1,int(t*5)))
            else:
                for i in range(65):
                    x=int((i*73-t*45)%400); y=int((i*47+t*145)%300)
                    pygame.draw.line(s,(75,95,140),(x,y),(x-2,y+5))
                if t>3:
                    r.center(s,'TRANSMISSION // DISTRICT 09',35,(80,230,240))
                    r.center(s,'THE SIGNAL HAS TAKEN THE CITY.',55)
                if t>5:
                    for i,name in enumerate(('grunt','runner','bruiser','ranged')):
                        image=sprite(name,'walk',int(t*7)%4)
                        dark=image.copy(); dark.fill((35,35,55,255),special_flags=pygame.BLEND_RGBA_MULT)
                        s.blit(dark,(65+i*70,130))
                if t>6: s.blit(sprite('REX','walk',int(t*8)%4),(min(165,int((t-6)*70)),191))
                if t>8:
                    settle=max(0,1-(t-8)*2)
                    r.center(s,'NEON BRAWL',int(91-110*settle*settle),(255,95,175),3)
                if t<2.2:
                    veil=pygame.Surface((400,300)); veil.fill((0,0,0))
                    veil.set_alpha(int(255*max(0,1-(t-1)/1.2))); s.blit(veil,(0,0))
            r.center(s,'ENTER / SPACE / ESC : SKIP',282,(160,170,200))
        elif screen=='title':
            r.center(s,'NEON',45,(75,235,245),4); r.center(s,'BRAWL',88,(255,85,170),4)
            for i,name in enumerate(ROSTER):
                image=pygame.transform.scale(sprite(name,'idle',int(self.time*5)%4),(96,96)); s.blit(image,(54+i*100,153))
            r.center(s,'RECLAIM THE CITY. BREAK THE SIGNAL.',140)
            r.center(s,'ENTER : START    ESC : LEAVE',273,(255,215,100))
        elif screen=='select':
            r.center(s,'CHOOSE YOUR FIGHTER',15,(85,235,245),2)
            for i,(name,stats) in enumerate(ROSTER.items()):
                x=15+i*130; selected=i==self.selection
                pygame.draw.rect(s,stats.color if selected else (60,50,80),(x,47,120,190),2 if selected else 1)
                image=pygame.transform.scale(sprite(name,'idle',int(self.time*6)%4),(96,96)); s.blit(image,(x+12,53))
                r.text(s,name,x+12,153,stats.color,2)
                for j,(label,value) in enumerate((('SPD',stats.speed/27),('PWR',stats.power*3),('DEF',stats.defense*3))):
                    r.text(s,label,x+8,181+j*15)
                    for k in range(5): s.fill(stats.color if k<round(value) else (50,40,65),(x+42+k*12,182+j*15,9,5))
            r.center(s,ROSTER[tuple(ROSTER)[self.selection]].description,249)
            r.center(s,'A/D : SELECT   ENTER : CONFIRM',277,(255,215,100))
        elif screen in ('tutorial','controls'):
            r.center(s,'STREET SURVIVAL',15,(85,235,245),2)
            lines=('WASD / ARROWS   MOVE IN TWO LANES','J   LIGHT / THREE-HIT COMBO','K   HEAVY / BREAK THEIR GUARD','L   JUMP   + J : AIR ATTACK','U   SPECIAL / 40 ENERGY','I   DODGE / BRIEF INVULNERABILITY','E   PICK UP FOOD AT CHECKPOINTS','ESC PAUSE / ENTER BEGIN')
            for i,line in enumerate(lines): r.text(s,line,15,54+i*21,(235,225,190))
            demo=self.tutorial_player
            state=demo.state if demo.swing or demo.timer else ('walk','heavy','air','special')[int(self.time)%4]
            s.blit(sprite(demo.name,state,int(self.time*8)%4),(300,222))
            r.center(s,'TRY THE ACTION KEYS NOW',275,(75,230,225))
        elif screen=='paused':
            self.panel(s,'PAUSED',[('> ' if self.pause_selection==i else '  ')+v for i,v in enumerate(('RESUME','CONTROLS','END RUN / RETURN'))]+['W/S SELECT / ENTER CONFIRM'])
        elif screen=='checkpoint':
            self.panel(s,'AREA SECURED',['CHECKPOINT / +35 HEALTH / +20 ENERGY','E : FOOD +30 HP / NEXT BLOCK OPEN','ENTER : CONTINUE'])
        elif screen=='stage_clear':
            self.panel(s,'STAGE CLEAR',[STAGES[self.campaign.stage][0],'THE SIGNAL LEADS DEEPER...','ENTER : CONTINUE'])
        elif screen=='game_over': self.panel(s,'SIGNAL LOST',['YOU FOUGHT FOR THE CITY.','ENTER : VIEW RESULTS'])
        elif screen=='ending':
            self.campaign.player.state='victory'
            self.panel(s,'SIGNAL BROKEN',['NULL IS SILENT. THE CITY WAKES.','THE STREETS BELONG TO EVERYONE.','THANK YOU FOR PLAYING NEON BRAWL','ENTER : RESULTS'])
        elif screen=='results':
            data=self.result()
            self.panel(s,'CITY LIBERATED' if data['victory'] else 'RUN COMPLETE',[
                f"SCORE {data['score']:07d} / KILLS {data['kills']}",f"BEST COMBO {data['combo']} / DAMAGE {data['damage']}",
                f"STAGE {data['stage']} / TIME {data['time']//60:02}:{data['time']%60:02}",f"TICKETS EARNED {data['tickets']}",'ENTER : RETURN TO ARCADE'])
