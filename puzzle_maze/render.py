"""Original pixel artwork built from crisp primitives at 320x240 resolution."""
import math
import random
import pygame
from puzzle_maze.core import Camera
from puzzle_maze.entrances import draw_entrance
from puzzle_maze.ui import NativeText
from puzzle_maze.icons import IconHUD
from puzzle_maze.room_art import RoomArt
from puzzle_maze.advanced_puzzles import Brazier,TorchSequence,WeightPlate,LiftablePot,CrystalSwitch,CrystalBarrier,PowderSupply,PotSupply,OrderedSeal,DestructiblePillar,OrderedLayoutSeal
from puzzle_maze.combat import EnemyState
from puzzle_maze.exploration import DungeonAtlas
from puzzle_maze.environment import EnvironmentPainter
from puzzle_maze.themes import THEMES
from puzzle_maze.puzzles import PushableBox, PressurePlate, Door, Key, SecretPassage, TimedSwitch, Switch, Chest, LightSource, Receiver, Reflector,CrackedWall,BombSupply,DashSwitch,BlastSwitch,RemoteRelay,ChestPhase,GateControl

INK=(18,26,39); GOLD=(245,198,96); WHITE=(230,237,219); TEAL=(81,195,165)

class Renderer:
    def __init__(self):
        self.surface=pygame.Surface((320,240))
        self.title=object()  # NativeText uses this marker for its heading style.
        self.camera=Camera()
        self.tiles={}
        self.particles=[]
        self.time=0
        self.ui=NativeText()
        self.environment=EnvironmentPainter()
        self.hud=IconHUD()
        self.room_art=RoomArt();self.object_seen={};self.opening={}
        self.tiles=self.environment.tiles('entrance')

    def text(self,text,x,y,color=WHITE,font=None,max_width=None):
        self.ui.queue(text,x,y,color,font is self.title,max_width)

    def burst(self,x,y,color=GOLD,count=18):
        if len(self.particles)>120:self.particles=self.particles[-120:]
        for _ in range(count):
            angle=random.random()*math.tau;speed=random.uniform(10,40)
            self.particles.append([x*16+8,y*16+8,math.cos(angle)*speed,math.sin(angle)*speed,random.uniform(.3,.8),color])

    def world(self,session,visual,dt,tool="pulse",controls=None):
        from puzzle_maze.onboarding import DEFAULT_CONTROLS
        controls=DEFAULT_CONTROLS if controls is None else controls
        self.ui.clear();self.boss_panel_rect=None
        self.time+=dt;s=self.surface;r=pygame.draw;s.fill(INK)
        room=session.rooms.data;p=session.player
        theme_name=room.get("theme","entrance");theme=THEMES[theme_name]
        self.tiles=self.environment.tiles(theme_name)
        proxy=type('Position',(),dict(x=visual[0],y=visual[1]))()
        self.camera.follow(proxy,len(room['tiles'][0]),len(room['tiles']),viewport=(320,184))
        cx,cy=int(self.camera.x),int(self.camera.y)
        s.set_clip((0,0,320,184))
        for y,row in enumerate(room['tiles']):
            for x,kind in enumerate(row):
                sx,sy=x*16-cx,y*16-cy
                if -16<sx<320 and -16<sy<208:
                    s.blit(self.environment.tile(theme_name,kind,(x*37+y*17)%13),(sx,sy))
                    if kind == '~':
                        offset=int(self.time*3+x+y)%8
                        r.line(s,(83,159,174),(sx+offset,sy+6),(sx+min(15,offset+5),sy+6))
                    elif kind == '.' and (x*17+y*31)%23==0:
                        r.rect(s,(99,111,94),(sx+5,sy+4,2,1))
                    elif kind == '#' and (x+3*y)%11==0:
                        r.line(s,(60,112,82),(sx+2,sy+3),(sx+2,sy+8))
                        r.rect(s,(78,131,88),(sx+3,sy+4,2,2))
        self.room_art.draw(s,room,(cx,cy),self.time)
        self.environment.decorations(s,room,(cx,cy),self.time)
        # Inlaid entrance compass; authored art remains entirely local.
        sx,sy=2*16-cx,7*16-cy
        r.circle(s,(98,134,123),(sx+8,sy+8),7,1)
        r.lines(s,(142,170,140),False,[(sx+8,sy+2),(sx+8,sy+14)])
        for e in room['exits']:
            x,y=e['pos'];sx,sy=x*16-cx,y*16-cy
            draw_entrance(s,session,e,sx,sy,self.tiles['#'])
        for start,end in session.puzzles.beams:
            r.line(s,(255,227,130),(start[0]*16+8-cx,start[1]*16+8-cy),(end[0]*16+8-cx,end[1]*16+8-cy),2)
        # Hidden passage clue: moss and luminous cracks converge at the wall.
        for o in sorted(session.puzzles.objects.values(), key=lambda obj: 0 if isinstance(obj,PressurePlate) else 1):
            sx,sy=o.x*16-cx,o.y*16-cy
            if not (-16<sx<320 and -16<sy<208):continue
            if isinstance(o,Brazier):
                r.ellipse(s,(23,26,38),(sx+1,sy+11,14,5));r.rect(s,(99,102,103),(sx+3,sy+8,10,5));r.line(s,(193,177,142),(sx+2,sy+8),(sx+13,sy+8),2)
                if o.state.active:
                    s.blit(self.environment.glow(theme_name),(sx-24,sy-29))
                    wave=int(math.sin(self.time*13+o.x)*2)
                    r.polygon(s,(239,111,62),[(sx+3,sy+8),(sx+5,sy+2+wave),(sx+8,sy+5),(sx+10,sy+1-wave),(sx+13,sy+8)])
                    r.polygon(s,GOLD,[(sx+5,sy+8),(sx+8,sy+3),(sx+11,sy+8)]);r.rect(s,WHITE,(sx+7,sy+6,2,3))
                if o.data.get('mark'):self.text(str(o.data['mark']),sx+5,sy-9,GOLD,max_width=13)
            elif isinstance(o,DestructiblePillar):
                if o.state.active:
                    for ox,oy in ((2,11),(7,8),(11,12)):r.rect(s,(115,125,139),(sx+ox,sy+oy,4,3))
                else:
                    r.ellipse(s,(24,30,44),(sx,sy+12,16,4));r.rect(s,(116,126,147),(sx+3,sy+1,10,13));r.rect(s,(190,181,144),(sx+1,sy+1,14,3))
                    r.lines(s,(61,73,88),False,[(sx+7,sy+5),(sx+9,sy+8),(sx+6,sy+11)]);r.circle(s,GOLD,(sx+8,sy+6),2,1)
            elif isinstance(o,OrderedLayoutSeal):
                for pair in o.data['placements']:
                    px,py=pair['pos'];r.rect(s,TEAL if o.state.active else GOLD,(px*16-cx+1,py*16-cy+1,14,14),1)
                    mark=session.puzzles.objects[pair['object']].data['mark'];self.text(str(mark),px*16-cx+5,py*16-cy+4,GOLD,max_width=12)
            elif isinstance(o,CrystalSwitch):
                color=(110,200,249) if o.state.active else (239,112,130)
                s.blit(self.environment.glow(theme_name),(sx-24,sy-24))
                r.ellipse(s,(25,34,49),(sx+1,sy+12,14,4));r.polygon(s,color,[(sx+8,sy),(sx+14,sy+7),(sx+8,sy+14),(sx+2,sy+7)])
                r.line(s,WHITE,(sx+8,sy+2),(sx+4,sy+7));r.line(s,(83,89,155),(sx+8,sy+3),(sx+8,sy+12))
            elif isinstance(o,CrystalBarrier):
                color=(111,180,234) if o.data['color']=='blue' else (215,108,118)
                r.rect(s,(31,37,55),(sx+1,sy+11,14,4));r.line(s,color,(sx+1,sy+14),(sx+14,sy+14))
                if not o.state.active:
                    for ox in (3,8,13):r.polygon(s,color,[(sx+ox,sy+1),(sx+ox+2,sy+6),(sx+ox+2,sy+13),(sx+ox-2,sy+13),(sx+ox-2,sy+6)])
            elif isinstance(o,LiftablePot):
                if not o.state.active:
                    r.ellipse(s,(21,26,34),(sx+2,sy+11,12,5));s.blit(pygame.transform.scale(self.hud.atlas.get('pot'),(16,16)),(sx,sy-1))
                    if o.data.get('inscribed'):r.rect(s,GOLD,(sx+7,sy+7,3,3))
                    if o.data.get('explosive'):r.line(s,(234,105,89),(sx+4,sy+5),(sx+11,sy+10))
            elif isinstance(o,(PotSupply,PowderSupply)):
                r.rect(s,(81,63,59),(sx+1,sy+4,14,10));r.rect(s,(177,132,88),(sx+2,sy+5,12,8),1)
                s.blit(self.hud.atlas.get('pot' if isinstance(o,PotSupply) else 'powder'),(sx+2,sy+1))
            elif isinstance(o,(TorchSequence,OrderedSeal)):
                r.rect(s,(48,52,66),(sx+1,sy+3,14,10));r.rect(s,TEAL if o.state.active else GOLD,(sx+2,sy+4,12,8),1)
                for index in range(3):r.rect(s,TEAL if o.state.active else (126,111,103),(sx+3+index*4,sy+7,2,2))
            elif isinstance(o,CrackedWall):
                if not o.state.active:
                    s.blit(self.tiles["#"],(sx,sy));r.lines(s,(102,108,104),False,[(sx+3,sy+1),(sx+9,sy+5),(sx+5,sy+10),(sx+12,sy+15)]);r.rect(s,(104,58,44),(sx+10,sy+4,2,2))
            elif isinstance(o,BombSupply):
                r.rect(s,(110,91,65),(sx+2,sy+4,12,10));s.blit(self.hud.atlas.get("bomb"),(sx+2,sy+2))
            elif isinstance(o,DashSwitch):
                r.rect(s,TEAL if o.state.active else GOLD,(sx+1,sy+2,14,12),2);r.polygon(s,WHITE,[(sx+3,sy+5),(sx+11,sy+8),(sx+3,sy+11)])
            elif isinstance(o,(BlastSwitch,RemoteRelay)):
                r.circle(s,TEAL if o.state.active else (112,76,104),(sx+8,sy+8),5,2)
            elif isinstance(o,SecretPassage):
                if not o.state.active:
                    s.blit(self.tiles['#'],(sx,sy));r.lines(s,(102,108,104),False,[(sx+8,sy+2),(sx+5,sy+7),(sx+10,sy+9),(sx+7,sy+14)])
            elif isinstance(o,Chest):
                if not o.visible:continue
                if o.phase == ChestPhase.SPAWNING:
                    sy += int(o.spawn_time / o.spawn_duration * 10)
                    r.line(s,GOLD,(sx+2,sy-2),(sx+13,sy-2))
                key=session.rooms.current,o.id
                if o.state.active and not self.object_seen.get(key,False):
                    self.opening[key]=.45;self.burst(o.x,o.y,GOLD,8)
                self.object_seen[key]=o.state.active
                self.opening[key]=max(0,self.opening.get(key,0)-dt)
                r.rect(s,(32,40,47),(sx+2,sy+4,12,10));r.rect(s,(153,98,56),(sx+2,sy+3,12,9))
                r.rect(s,TEAL if o.state.active else GOLD,(sx+2,sy+3,12,9),1)
                r.rect(s,GOLD,(sx+7,sy+6,2,3))
                if o.state.active:
                    r.rect(s,INK,(sx+3,sy+4,10,3));r.rect(s,(182,126,68),(sx+2,sy-1-int(self.opening[key]*7),12,3));r.line(s,GOLD,(sx+2,sy-1),(sx+13,sy-1))
            elif isinstance(o,Reflector):
                r.rect(s,(91,139,174),(sx+2,sy+2,12,12),1)
                r.line(s,WHITE,(sx+3,sy+12 if o.state.active else sy+3),(sx+12,sy+3 if o.state.active else sy+12),2)
            elif isinstance(o,Receiver):
                r.circle(s,TEAL if o.state.active else (99,94,141),(sx+8,sy+8),6,2)
                r.circle(s,GOLD if o.state.active else INK,(sx+8,sy+8),2)
            elif isinstance(o,LightSource):
                r.rect(s,(133,112,158),(sx+3,sy+3,10,10));r.circle(s,GOLD,(sx+8,sy+8),3)
            elif isinstance(o,PushableBox):
                r.rect(s,(28,36,44),(sx+1,sy+3,14,13));r.rect(s,(117,147,166) if o.data.get('metal') else (145,98,59),(sx+2,sy+1,12,12));r.rect(s,(211,162,92),(sx+3,sy+2,10,10),1);r.line(s,(211,162,92),(sx+4,sy+3),(sx+11,sy+10));r.line(s,(211,162,92),(sx+11,sy+3),(sx+4,sy+10))
                if o.data.get("metal"):
                    for ox,oy in ((3,2),(11,2),(3,10),(11,10)):r.rect(s,WHITE,(sx+ox,sy+oy,1,1))
            elif isinstance(o,PressurePlate):
                c=TEAL if o.state.active else (153,137,108)
                r.polygon(s,(28,40,49),[(sx+8,sy+1),(sx+15,sy+8),(sx+8,sy+15),(sx+1,sy+8)])
                r.polygon(s,c,[(sx+8,sy+3),(sx+13,sy+8),(sx+8,sy+13),(sx+3,sy+8)],2)
                if isinstance(o,WeightPlate):
                    for dot in range(o.data.get("weight",2)):r.rect(s,GOLD,(sx+3+dot*3,sy+7,2,2))
            elif isinstance(o,GateControl):
                r.circle(s,TEAL if o.state.active else (113,120,137),(sx+8,sy+8),6,2)
                r.rect(s,GOLD if o.state.active else INK,(sx+6,sy+6,4,4))
            elif isinstance(o,Door):
                if o.state.active:
                    r.rect(s,TEAL,(sx,sy,2,16));r.rect(s,TEAL,(sx+14,sy,2,16))
                else:
                    r.rect(s,(23,31,44),(sx,sy,16,16));r.rect(s,theme.wall,(sx,sy,3,16));r.rect(s,theme.wall,(sx+13,sy,3,16));r.line(s,theme.accent,(sx+1,sy),(sx+14,sy),2)
                    for i in (4,8,12):r.line(s,GOLD,(sx+i,sy+2),(sx+i,sy+13))
                    if not o.unlocked:r.rect(s,(232,157,77),(sx+6,sy+6,5,5))
            elif isinstance(o,Key):
                if not o.state.active and all(session.puzzles.condition(i) for i in o.data.get("requires",[])):
                    yy=sy+int(math.sin(self.time*4)*2)
                    r.circle(s,GOLD,(sx+6,yy+5),3,1);r.line(s,GOLD,(sx+8,yy+7),(sx+12,yy+11),2);r.line(s,GOLD,(sx+11,yy+9),(sx+13,yy+7))
            elif isinstance(o,Switch):
                r.rect(s,(26,38,49),(sx+3,sy+8,10,6));r.rect(s,(142,155,137),(sx+4,sy+9,8,3));r.line(s,GOLD,(sx+8,sy+9),(sx+10 if o.state.active else sx+5,sy+3),2)
                r.circle(s,TEAL if o.state.active else (180,91,74),(sx+8,sy+3),2)
                if isinstance(o,TimedSwitch) and o.state.remaining:
                    self.text(f'{o.state.remaining:.1f}',sx-1,sy-9,GOLD)
        for enemy in session.combat.enemies:
            if enemy.state==EnemyState.DEAD or enemy.dormant:continue
            sx,sy=enemy.x*16-cx,enemy.y*16-cy
            color=(251,210,139) if enemy.flash>0 else {'slime':(112,190,108),'bat':(152,127,208),'guardian':(176,138,96),'blink_mage':(144,106,215),'armored_beetle':(104,168,175),'bomb_eater':(215,133,76),'golem':(154,164,179),'mirror_mask':(184,210,211),'pot_hunter':(194,116,103),'crystal_ghost':(141,211,228),'elite_guardian':(164,153,204),'crystal_warden':(100,202,221)}[enemy.kind]
            if enemy.state==EnemyState.DYING:
                radius=max(1,int(enemy.attack_timer*20));r.circle(s,color,(sx+8,sy+8),radius,1);continue
            if enemy.state==EnemyState.WINDUP:r.rect(s,(239,93,91),(sx-1,sy-1,18,18),1)
            r.ellipse(s,(24,34,44),(sx+1,sy+12,14,4))
            if enemy.kind=='slime':r.ellipse(s,color,(sx+2,sy+5,12,9))
            elif enemy.kind=='bat':
                wing=int(math.sin(self.time*18)*3)
                r.polygon(s,color,[(sx,sy+5+wing),(sx+6,sy+8),(sx+8,sy+5),(sx+10,sy+8),(sx+16,sy+5+wing),(sx+12,sy+13),(sx+4,sy+13)])
            elif enemy.kind=='crystal_ghost':
                ghost=pygame.Surface((16,16),pygame.SRCALPHA)
                pygame.draw.polygon(ghost,color,[(8,1),(13,5),(14,13),(11,11),(8,14),(5,11),(2,13),(3,5)])
                if not enemy.visible(session.combat):ghost.set_alpha(70)
                s.blit(ghost,(sx,sy))
            elif enemy.kind=='mirror_mask':
                r.polygon(s,(49,76,97),[(sx+8,sy),(sx+15,sy+13),(sx+1,sy+13)]);r.rect(s,color,(sx+4,sy+3,8,7));r.line(s,TEAL,(sx+5,sy+4),(sx+10,sy+4));r.rect(s,INK,(sx+6,sy+7,4,2))
            elif enemy.kind=='pot_hunter':
                r.ellipse(s,color,(sx+2,sy+3,12,11));r.line(s,GOLD,(sx+3,sy+1),(sx+3,sy+6),2);r.line(s,GOLD,(sx+12,sy+1),(sx+12,sy+6),2);r.rect(s,(87,62,69),(sx+4,sy+8,8,5))
            elif enemy.kind=='crystal_warden':
                r.rect(s,(31,58,78),(sx-4,sy-5,24,22));r.polygon(s,color,[(sx+8,sy-10),(sx+20,sy+4),(sx+8,sy+18),(sx-4,sy+4)]);r.polygon(s,(68,100,141),[(sx+8,sy-5),(sx+15,sy+4),(sx+8,sy+12),(sx+1,sy+4)]);r.circle(s,GOLD if 'crystal_blue' in session.inventory.flags else WHITE,(sx+8,sy+4),3)
            elif enemy.kind=='elite_guardian':
                r.rect(s,color,(sx+2,sy+1,12,14));r.polygon(s,(97,47,88),[(sx+1,sy+4),(sx+8,sy+1),(sx+15,sy+4),(sx+13,sy+15),(sx+3,sy+15)]);r.rect(s,color,(sx+4,sy+2,8,5));r.line(s,WHITE,(sx+13,sy),(sx+13,sy+15),2)
            elif enemy.kind=='blink_mage':
                r.polygon(s,color,[(sx+8,sy),(sx+1,sy+14),(sx+15,sy+14)]);r.rect(s,GOLD,(sx+4,sy+8,8,1));r.circle(s,TEAL,(sx+13,sy+3),2)
            elif enemy.kind=='armored_beetle':
                r.ellipse(s,color,(sx+2,sy+2,12,12));r.line(s,INK,(sx+8,sy+3),(sx+8,sy+12));dx,dy=enemy.facing;r.line(s,GOLD if enemy.armor else (89,88,91),(sx+8-dy*5+dx*5,sy+8+dx*5+dy*5),(sx+8+dy*5+dx*5,sy+8-dx*5+dy*5),3)
            elif enemy.kind=='bomb_eater':
                r.ellipse(s,color,(sx+1,sy+3,14,12));r.rect(s,INK,(sx+3,sy+8,10,5));r.line(s,WHITE,(sx+4,sy+9),(sx+11,sy+9));r.rect(s,GOLD,(sx+5,sy+2,6,3))
            elif enemy.kind=='golem':
                r.rect(s,(34,41,58),(sx-7,sy-9,30,28));r.rect(s,color,(sx-5,sy-11,26,28));r.rect(s,(70,87,107),(sx-3,sy-8,22,22),2);r.circle(s,TEAL if enemy.exposed>0 else GOLD,(sx+8,sy+4),5,2);r.rect(s,(225,95,91),(sx+4,sy-5,8,2))
                if enemy.exposed<=0:r.circle(s,(121,201,227),(sx+8,sy+6),19,1)
            else:
                r.rect(s,color,(sx+3,sy+2,10,12));r.rect(s,(88,94,104),(sx+2,sy+7,4,7));r.line(s,GOLD,(sx+13,sy+2),(sx+13,sy+13),2)
            for ex in (5,10):r.rect(s,INK,(sx+ex,sy+8,1,2))
            r.rect(s,(36,41,54),(sx+2,sy-3,12,2));r.rect(s,(234,108,114),(sx+2,sy-3,int(12*enemy.hp/enemy.max_hp),2))
        for drop in session.combat.loot:
            sx,sy=drop['pos'][0]*16-cx,drop['pos'][1]*16-cy
            r.circle(s,(238,104,129),(sx+8,sy+8),3)
            if drop.get("bombs",0):s.blit(self.hud.atlas.get("bomb"),(sx+1,sy+1))
        for bolt in session.combat.projectiles:
            bx,by=bolt.x*16+8-cx,bolt.y*16+8-cy
            r.circle(s,(236,113,170),(bx,by),3);r.line(s,GOLD,(bx-bolt.dx*5,by-bolt.dy*5),(bx,by))
        for pos,remaining in getattr(session,'trails',[]):
            r.rect(s,(68,135,161),(pos[0]*16+3-cx,pos[1]*16+3-cy,10,10),1)
        if hasattr(session,'bombs'):
            for bomb in session.bombs.bombs:
                bx,by=bomb.x*16-cx,bomb.y*16-cy
                s.blit(self.hud.atlas.get('bomb'),(bx+2,by+2));r.rect(s,GOLD if int(bomb.fuse*12)%2 else WHITE,(bx+8,by+1,2,2))
            for cells,remaining in session.bombs.blasts:
                for bx,by in cells:
                    radius=max(2,int(remaining*20));r.circle(s,GOLD if int(remaining*25)%2 else (240,123,72),(bx*16+8-cx,by*16+8-cy),radius,2)
        if (p.invulnerable<=0 and session.combat.entry_protection<=0) or int(self.time*15)%2==0:self.player(visual,p.facing,p.moving,cx,cy)
        if getattr(session.inventory,'carried',None):
            s.blit(pygame.transform.scale(self.hud.atlas.get('pot'),(16,16)),(int(visual[0]*16)-cx,int(visual[1]*16)-cy-12))
        for kind,pos,remaining in getattr(session,'effects',[]):
            ex,ey=pos[0]*16+8-cx,pos[1]*16+8-cy
            if kind=='chest':
                light=pygame.Surface((320,184),pygame.SRCALPHA);light.fill((255,221,143,int(remaining/.45*28)));s.blit(light,(0,0))
                s.blit(self.environment.glow(theme_name),(ex-32,ey-32))
                for i in range(10):
                    a=i*math.tau/10;distance=(.45-remaining)*38
                    r.rect(s,GOLD,(int(ex+math.cos(a)*distance),int(ey+math.sin(a)*distance-10),2,2))
            elif kind=='shards':
                for i in range(8):
                    a=i*math.pi/4;distance=(.7-remaining)*28;r.rect(s,(209,153,104),(int(ex+math.cos(a)*distance),int(ey+math.sin(a)*distance+distance*.2),2,2))
            else:r.circle(s,TEAL if kind=='crystal' else GOLD,(ex,ey),max(1,int((.6-remaining)*28)),1)
        for flight in getattr(session,'pot_flights',[]):
            progress=1-flight['time']/.3;start,end=flight['start'],flight['end']
            x=(start[0]+(end[0]-start[0])*progress)*16-cx;y=(start[1]+(end[1]-start[1])*progress)*16-cy-math.sin(progress*math.pi)*14
            sprite=pygame.transform.scale(self.hud.atlas.get('pot'),(16,16))
            if flight.get('kind')=='orb':
                r.circle(s,(138,166,185),(int(x)+8,int(y)+8),6);r.circle(s,WHITE,(int(x)+6,int(y)+6),2)
            else:s.blit(pygame.transform.rotate(sprite,90 if progress>.5 else 0),(int(x),int(y)))
        if p.attack_flash>0:
            sx,sy=int(visual[0]*16+8)-cx,int(visual[1]*16+8)-cy
            dx,dy=p.attack_facing
            progress=1-p.attack_flash/p.weapon.swing_duration
            angle=math.atan2(dy,dx)-.8+progress*1.6
            for offset,color in ((-.3,(70,111,134)),(-.15,TEAL),(0,WHITE)):
                a=angle+offset;end=(int(sx+math.cos(a)*20),int(sy+math.sin(a)*20))
                r.line(s,color,(sx,sy),end,2 if offset else 3)
            hilt=(int(sx+math.cos(angle)*5),int(sy+math.sin(angle)*5))
            r.circle(s,GOLD,hilt,2)
        for particle in self.particles[:]:
            particle[0]+=particle[2]*dt;particle[1]+=particle[3]*dt;particle[4]-=dt
            if particle[4]<=0:self.particles.remove(particle)
            else:r.rect(s,particle[5],(int(particle[0])-cx,int(particle[1])-cy,2,2))
        orb_prompt=False
        if hasattr(session,'orb') and session.orb.room==session.rooms.current:
            orb=session.orb
            ox,oy=(p.x*16+8-cx,p.y*16-3-cy) if orb.carried else (orb.x*16+8-cx,orb.y*16+8-cy)
            r.ellipse(s,(20,27,36),(ox-6,oy+4,13,4));r.circle(s,(107,134,153),(ox,oy),6);r.circle(s,(184,201,209),(ox-2,oy-2),2);r.circle(s,(53,77,95),(ox,oy),6,1)
            if (orb.carried or abs(orb.x-p.x)+abs(orb.y-p.y)<=1) and session.inventory.carried is None:
                orb_prompt=True
                label=f"{controls['interact']} Drop / G Orb / T Recall" if orb.carried else f"{controls['interact']} Lift Orb / T Recall"
                r.rect(s,INK,(6,145,288,22));self.text(label,10,150,GOLD,max_width=276)
        near=next((o for o in session.puzzles.objects.values() if abs(o.x-p.x)+abs(o.y-p.y)<=1 and isinstance(o,(Switch,Door,SecretPassage,Chest,Reflector,CrackedWall,BombSupply,LiftablePot,Brazier,CrystalSwitch,PotSupply,PowderSupply)) and not isinstance(o,GateControl) and not (isinstance(o,Chest) and o.phase!=ChestPhase.AVAILABLE) and not (isinstance(o,(Door,SecretPassage)) and o.state.active)),None)
        if not orb_prompt and (near or getattr(session.inventory,'carried',None)):
            carrying=getattr(session.inventory,'carried',None)
            label=f"{controls['interact']} Drop / G Throw" if carrying else '[P] Light' if isinstance(near,Brazier) else f"[{controls['attack']}] Crystal" if isinstance(near,CrystalSwitch) else f"[{controls['interact']}] Lift" if isinstance(near,LiftablePot) else '[B] Bomb' if isinstance(near,CrackedWall) else f"[{controls['ability']}] Pulse" if isinstance(near,SecretPassage) else f"[{controls['interact']}] Interact"
            px=int(visual[0]*16)-cx;py=int(visual[1]*16)-cy
            hint_y=max(2,min(168,py+18 if carrying or py<18 else py-15))
            hint_x=max(2,min(146,px-30))
            r.rect(s,INK,(hint_x,hint_y,172,15));self.text(label,hint_x+3,hint_y+1,GOLD,max_width=166)
        s.set_clip(None)
        self.hud.draw(self,session,tool,controls)
        boss=next((e for e in session.combat.enemies if e.kind in ('golem','crystal_warden') and e.state!=EnemyState.DEAD),None)
        if boss:
            labels={1:'I: DASH ANCHOR > SWORD',2:'II: BOMB > SWORD',3:'III: DASH + BOMB > SWORD'}
            actors=[pygame.Rect(int(visual[0]*16)-cx,int(visual[1]*16)-cy,16,16)]
            actors += [pygame.Rect(e.x*16-cx-6,e.y*16-cy-11,28,30) for e in session.combat.enemies if e.hp>0 and not e.dormant]
            top=next((y for y in (5,148,112,38) if not any(pygame.Rect(5,y,222,27).colliderect(actor) for actor in actors)),5)
            self.boss_panel_rect=pygame.Rect(5,top,222,27)
            r.rect(s,INK,(5,top,222,27));r.rect(s,(83,110,130),(5,top,222,27),1)
            self.text('RED REVEALS THE WARDEN' if boss.kind=='crystal_warden' else 'CORE OPEN' if boss.exposed>0 else 'BLUE / DASH + BOMB > SWORD' if boss.phase==3 and boss.data.get('crystal_color') else labels[boss.phase],10,top+3,TEAL if getattr(boss,'exposed',0)>0 else GOLD,max_width=211)
            r.rect(s,(51,54,73),(10,top+18,210,3));r.rect(s,(227,107,113),(10,top+18,int(210*boss.hp/boss.max_hp),3))


    def player(self,pos,facing,moving,cx,cy):
        r=pygame.draw;s=self.surface
        x,y=int(pos[0]*16)-cx,int(pos[1]*16)-cy
        bob=int(math.sin(self.time*7)) if not moving else int(math.sin(self.time*20))
        stride=int(math.sin(self.time*20)*2) if moving else 0
        r.ellipse(s,(25,37,45),(x+2,y+12,12,4))
        r.rect(s,(37,58,76),(x+4+stride,y+12,3,3));r.rect(s,(37,58,76),(x+9-stride,y+12,3,3))
        r.rect(s,(57,145,149),(x+3,y+7+bob,10,6));r.rect(s,(114,203,180),(x+4,y+7+bob,8,2))
        r.rect(s,(229,186,139),(x+4,y+3+bob,8,5));r.rect(s,(49,53,67),(x+3,y+1+bob,10,3));r.rect(s,(83,87,95),(x+4,y+bob,7,2))
        if facing[1]>=0:
            for ex in ((5,10) if facing[0]==0 else ((10,) if facing[0]>0 else (5,))):r.rect(s,INK,(x+ex,y+5+bob,1,2))
        if facing[1]<0:r.rect(s,(49,53,67),(x+4,y+3+bob,8,4))
        # Equipped sword remains visible at the belt outside its swing.
        sword_x=x+12 if facing[0]>=0 else x+2
        r.line(s,(158,195,203),(sword_x,y+7+bob),(sword_x,y+14+bob),2)
        r.line(s,GOLD,(sword_x-2,y+9+bob),(sword_x+2,y+9+bob))

    def panel(self,title,lines,selected=None):
        self.ui.clear()  # Modal text replaces the deferred world HUD.
        overlay=pygame.Surface((320,240),pygame.SRCALPHA);overlay.fill((9,18,29,220));self.surface.blit(overlay,(0,0))
        pygame.draw.rect(self.surface,(70,107,114),(22,22,276,194),1)
        self.text(title,35,36,GOLD,self.title,max_width=248)
        y=78
        for i,line in enumerate(lines):
            self.text(('> ' if selected==i else '  ')+line,36,y,TEAL if selected==i else WHITE,max_width=244)
            y+=19

    def atlas_graph(self,session,bounds):
        x,y,w,h=bounds;r=pygame.draw;s=self.surface
        atlas=DungeonAtlas(session.rooms);layout=atlas.displayed_layout(session,minimap=w<=100)
        floor=getattr(session,"map_floor",None) if w>100 else session.rooms.data.get("floor")
        if floor:layout={name:pos for name,pos in layout.items() if session.rooms.rooms[name].get("floor","1F")==floor}
        if not layout:return
        max_x=max(p[0] for p in layout.values())+1;max_y=max(p[1] for p in layout.values())+1
        cell_w=w/max_x;cell_h=h/max_y
        centers={name:(int(x+(pos[0]+.5)*cell_w),int(y+(pos[1]+.5)*cell_h)) for name,pos in layout.items()}
        for a,b in atlas.edges(session.visited,session.inventory.flags):
            if a in centers and b in centers and (a in session.visited or b in session.visited):r.line(s,(65,85,95),centers[a],centers[b])
        for name,center in centers.items():
            color=GOLD if name==session.rooms.current else TEAL if name in session.completed else WHITE if name in session.visited else (61,71,84)
            rw=max(4,int(cell_w*.58));rh=max(4,int(cell_h*.55))
            rect=pygame.Rect(center[0]-rw//2,center[1]-rh//2,rw,rh)
            r.rect(s,INK,rect);r.rect(s,color,rect,1)
            if w>100:self.text(name[1:] if name in session.visited else '?',rect.x+3,rect.y,color)
            elif name==session.rooms.current:r.rect(s,color,(center[0]-1,center[1]-1,2,2))
            if name in session.visited and any(e.get('stairs') for e in session.rooms.rooms[name]['exits']):
                for step in range(3):r.line(s,WHITE,(rect.x,rect.bottom-1-step),(rect.x+step+1,rect.bottom-1-step))
            if name in session.visited and 'compass' in session.inventory.abilities and any(o.get('ability') or o.get('boss_key') for o in session.rooms.rooms[name]['objects']):
                r.rect(s,TEAL,(rect.right-3,rect.bottom-3,2,2))
            if "compass" in session.inventory.abilities and any(e["type"] in ("golem","crystal_warden") for e in session.rooms.rooms[name].get("enemies",[])) and (name in session.visited or any(name in pair and (set(pair)-{name})<=session.visited for pair in atlas.edges(session.visited,session.inventory.flags))):
                r.rect(s,(236,98,116),(center[0]-2,center[1]-2,4,4))

    def minimap(self,session):
        pygame.draw.rect(self.surface,INK,(239,5,77,52))
        pygame.draw.rect(self.surface,(77,108,112),(239,5,77,52),1)
        self.text(session.rooms.data.get("floor","1F"),243,7,TEAL,max_width=30)
        self.atlas_graph(session,(242,23,71,29))

    def map_panel(self,session):
        self.panel('DUNGEON ATLAS',[])
        if hasattr(session,"map_floor"):self.text(f"{session.map_floor} / LEFT, RIGHT: floor",32,60,TEAL)
        self.atlas_graph(session,(30,75,260,68))
        known=session.exploration.tiles.get(session.rooms.current,set())
        rows=session.rooms.data['tiles'];w=len(rows[0]);h=len(rows)
        tile=min(120/w,66/h);x0,y0=32,151
        for x,y in known:
            color=(93,114,107) if rows[y][x] not in '#~Ov' else (38,64,83) if rows[y][x]=='~' else (62,73,89)
            pygame.draw.rect(self.surface,color,(int(x0+x*tile),int(y0+y*tile),max(1,int(tile)),max(1,int(tile))))
        for kind,(x,y) in DungeonAtlas(session.rooms).discovered_markers(session):
            color=GOLD if kind=='exit' else TEAL if kind in ('chest','receiver') else (198,136,113)
            pygame.draw.rect(self.surface,color,(int(x0+x*tile),int(y0+y*tile),2,2))
        p=session.player
        pygame.draw.rect(self.surface,GOLD,(int(x0+p.x*tile),int(y0+p.y*tile),3,3))
        self.text(session.rooms.data['name'],162,152,GOLD)
        self.text(f'Explored: {len(known)} tiles',162,169)
        self.text('Gold: you / exit',162,184)
        if hasattr(session,'rewards'):
            self.surface.blit(self.hud.atlas.get('token_cache'),(162,199));self.text(str(session.rewards.tokens),176,198,GOLD,max_width=38)
            self.surface.blit(self.hud.atlas.get('ticket_bundle'),(219,199));self.text(str(session.rewards.tickets),234,198,TEAL,max_width=38)
            self.surface.blit(self.hud.atlas.get('golden_cat'),(277,199));self.text(str(len(session.rewards.collections)),292,198,max_width=20)
        else:self.text('Teal: item / receiver',162,199)
        self.text('TAB closes / LEFT, RIGHT floor',32,218)
