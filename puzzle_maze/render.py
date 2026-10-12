"""Original pixel artwork built from crisp primitives at 320x240 resolution."""
import math
import random
import pygame
from puzzle_maze.core import Camera
from puzzle_maze.puzzles import PushableBox, PressurePlate, Door, Key, SecretPassage, TimedSwitch, Switch

INK=(18,26,39); GOLD=(245,198,96); WHITE=(230,237,219); TEAL=(81,195,165)

class Renderer:
    def __init__(self):
        self.surface=pygame.Surface((320,240))
        self.font=pygame.font.Font(None,14)
        self.title=pygame.font.Font(None,32)
        self.camera=Camera()
        self.tiles={}
        self.particles=[]
        self.time=0
        for kind in '#.~Og':self.tiles[kind]=self.tile(kind)

    def text(self,text,x,y,color=WHITE,font=None):
        self.surface.blit((font or self.font).render(text,False,color),(x,y))

    def tile(self,kind):
        s=pygame.Surface((16,16));r=pygame.draw
        if kind=='#':
            s.fill((37,48,61));r.rect(s,(79,96,100),(0,0,16,11));r.line(s,(111,127,122),(1,1),(14,1));r.line(s,(45,63,71),(0,7),(15,7));r.line(s,(45,63,71),(8,0),(8,6));r.line(s,(45,63,71),(3,8),(3,11));r.line(s,(23,34,48),(0,15),(15,15))
        elif kind=='~':
            s.fill((30,74,107));r.line(s,(60,127,148),(1,4),(7,4));r.line(s,(81,160,169),(8,10),(14,10))
        else:
            s.fill((53,66,67));r.rect(s,(62,75,73),(1,1,14,14));r.line(s,(71,83,77),(2,2),(13,2));r.line(s,(42,55,58),(0,15),(15,15));r.rect(s,(80,88,77),(4,9,2,1))
            if kind=='g':
                s.fill((39,76,64))
                for x,y in [(2,6),(7,12),(12,4),(13,13)]:r.lines(s,(79,126,83),False,[(x-1,y-2),(x,y),(x+1,y-3)])
            if kind=='O':
                r.ellipse(s,(23,34,42),(1,8,14,7));r.polygon(s,(126,135,124),[(2,10),(4,3),(11,2),(14,8),(10,13),(4,13)]);r.line(s,(171,172,145),(5,4),(10,3));r.line(s,(84,100,98),(11,5),(12,10))
        return s

    def burst(self,x,y,color=GOLD,count=18):
        for _ in range(count):
            angle=random.random()*math.tau;speed=random.uniform(10,40)
            self.particles.append([x*16+8,y*16+8,math.cos(angle)*speed,math.sin(angle)*speed,random.uniform(.3,.8),color])

    def world(self,session,visual,dt):
        self.time+=dt;s=self.surface;r=pygame.draw;s.fill(INK)
        room=session.rooms.data;p=session.player
        proxy=type('Position',(),dict(x=visual[0],y=visual[1]))()
        self.camera.follow(proxy,len(room['tiles'][0]),len(room['tiles']))
        cx,cy=int(self.camera.x),int(self.camera.y)
        s.set_clip((0,0,320,208))
        for y,row in enumerate(room['tiles']):
            for x,kind in enumerate(row):
                sx,sy=x*16-cx,y*16-cy
                if -16<sx<320 and -16<sy<208:
                    s.blit(self.tiles[kind],(sx,sy))
                    if kind == '~':
                        offset=int(self.time*3+x+y)%8
                        r.line(s,(83,159,174),(sx+offset,sy+6),(sx+min(15,offset+5),sy+6))
                    elif kind == '.' and (x*17+y*31)%23==0:
                        r.rect(s,(99,111,94),(sx+5,sy+4,2,1))
                    elif kind == '#' and (x+3*y)%11==0:
                        r.line(s,(60,112,82),(sx+2,sy+3),(sx+2,sy+8))
                        r.rect(s,(78,131,88),(sx+3,sy+4,2,2))
        # Lantern sconces give each room landmarks and a warm flickering glow.
        for tx,ty in ((3,2),(11,2),(3,15),(11,15)):
            sx,sy=tx*16-cx,ty*16-cy
            r.rect(s,(30,39,47),(sx+5,sy+5,7,9))
            r.rect(s,(188,128,69),(sx+6,sy+6,5,6),1)
            flicker=int(math.sin(self.time*9+tx)*1.5)
            r.rect(s,GOLD,(sx+7,sy+7+flicker,3,3))
            r.rect(s,(255,226,142),(sx+8,sy+8+flicker,1,2))
        # Inlaid entrance compass; authored art remains entirely local.
        sx,sy=2*16-cx,7*16-cy
        r.circle(s,(98,134,123),(sx+8,sy+8),7,1)
        r.lines(s,(142,170,140),False,[(sx+8,sy+2),(sx+8,sy+14)])
        for e in room['exits']:
            x,y=e['pos'];sx,sy=x*16-cx,y*16-cy
            r.rect(s,TEAL,(sx+3,sy+2,10,12),1);r.polygon(s,GOLD,[(sx+5,sy+5),(sx+11,sy+8),(sx+5,sy+11)])
        # Hidden passage clue: moss and luminous cracks converge at the wall.
        for o in sorted(session.puzzles.objects.values(), key=lambda obj: 0 if isinstance(obj,PressurePlate) else 1):
            sx,sy=o.x*16-cx,o.y*16-cy
            if isinstance(o,SecretPassage):
                if not o.state.active:
                    s.blit(self.tiles['#'],(sx,sy));r.lines(s,GOLD,False,[(sx+8,sy+2),(sx+5,sy+7),(sx+10,sy+9),(sx+7,sy+14)])
                    r.line(s,TEAL,(sx-8,sy+8),(sx-2,sy+8));r.line(s,TEAL,(sx-5,sy+5),(sx-2,sy+8))
            elif isinstance(o,PushableBox):
                r.rect(s,(28,36,44),(sx+1,sy+3,14,13));r.rect(s,(145,98,59),(sx+2,sy+1,12,12));r.rect(s,(211,162,92),(sx+3,sy+2,10,10),1);r.line(s,(211,162,92),(sx+4,sy+3),(sx+11,sy+10));r.line(s,(211,162,92),(sx+11,sy+3),(sx+4,sy+10))
            elif isinstance(o,PressurePlate):
                c=TEAL if o.state.active else (153,137,108)
                r.polygon(s,(28,40,49),[(sx+8,sy+1),(sx+15,sy+8),(sx+8,sy+15),(sx+1,sy+8)])
                r.polygon(s,c,[(sx+8,sy+3),(sx+13,sy+8),(sx+8,sy+13),(sx+3,sy+8)],2)
            elif isinstance(o,Door):
                if o.state.active:
                    r.rect(s,TEAL,(sx,sy,2,16));r.rect(s,TEAL,(sx+14,sy,2,16))
                else:
                    r.rect(s,(23,31,44),(sx,sy,16,16));r.rect(s,(141,128,94),(sx+1,sy+1,14,14),1)
                    for i in (4,8,12):r.line(s,GOLD,(sx+i,sy+2),(sx+i,sy+13))
                    if not o.unlocked:r.rect(s,(232,157,77),(sx+6,sy+6,5,5))
            elif isinstance(o,Key):
                if not o.state.active:
                    yy=sy+int(math.sin(self.time*4)*2)
                    r.circle(s,GOLD,(sx+6,yy+5),3,1);r.line(s,GOLD,(sx+8,yy+7),(sx+12,yy+11),2);r.line(s,GOLD,(sx+11,yy+9),(sx+13,yy+7))
            elif isinstance(o,Switch):
                r.rect(s,(26,38,49),(sx+3,sy+8,10,6));r.rect(s,(142,155,137),(sx+4,sy+9,8,3));r.line(s,GOLD,(sx+8,sy+9),(sx+10 if o.state.active else sx+5,sy+3),2)
                r.circle(s,TEAL if o.state.active else (180,91,74),(sx+8,sy+3),2)
                if isinstance(o,TimedSwitch) and o.state.remaining:
                    self.text(f'{o.state.remaining:.1f}',sx-1,sy-9,GOLD)
        self.player(visual,p.facing,p.moving,cx,cy)
        for particle in self.particles[:]:
            particle[0]+=particle[2]*dt;particle[1]+=particle[3]*dt;particle[4]-=dt
            if particle[4]<=0:self.particles.remove(particle)
            else:r.rect(s,particle[5],(int(particle[0])-cx,int(particle[1])-cy,2,2))
        near=next((o for o in session.puzzles.objects.values() if abs(o.x-p.x)+abs(o.y-p.y)<=1 and isinstance(o,(Switch,Door,SecretPassage)) and not (isinstance(o,(Door,SecretPassage)) and o.state.active)),None)
        if near:
            self.text('[SPACE] Pulse' if isinstance(near,SecretPassage) else '[E] Interact',int(visual[0]*16)-cx-18,int(visual[1]*16)-cy-12,GOLD)
        s.set_clip(None)
        r.rect(s,INK,(0,208,320,32));r.line(s,(80,107,112),(0,208),(320,208))
        self.text(f'{session.rooms.current.upper()}  {room["name"]}',7,213,GOLD)
        keys=sum(session.inventory.keys.values())
        self.text(f'Keys {keys}   Sigils {len(session.completed)}/9',7,226)
        self.text('TAB Map  ESC Menu',210,226,(135,161,154))

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
        r.rect(s,GOLD,(x+11 if facing[0]>=0 else x+1,y+9+bob,3,3))

    def panel(self,title,lines,selected=None):
        overlay=pygame.Surface((320,240),pygame.SRCALPHA);overlay.fill((9,18,29,220));self.surface.blit(overlay,(0,0))
        pygame.draw.rect(self.surface,(70,107,114),(22,22,276,194),1)
        self.text(title,35,36,GOLD,self.title)
        y=78
        for i,line in enumerate(lines):
            self.text(('> ' if selected==i else '  ')+line,36,y,TEAL if selected==i else WHITE)
            y+=19

    def map_panel(self,session):
        self.panel('DUNGEON ATLAS',['Eight chambers + a hidden archive', '', '', '', '', '', 'TAB closes / R resets current room'])
        positions = {
            'r1': (30,94), 'r2': (94,94), 'r3': (158,94), 'r4': (222,94),
            'r5': (222,131), 'r6': (158,131), 'r7': (94,131), 'r8': (30,131),
            'r9': (158,168),
        }
        for name,room in session.rooms.rooms.items():
            x,y=positions[name]
            for exit_data in room['exits']:
                target=exit_data['target']
                if exit_data.get('finish') or name not in session.visited or target not in session.visited:
                    continue
                tx,ty=positions[target]
                pygame.draw.line(self.surface,(97,112,109),(x+22,y+13),(tx+22,ty+13))
        for i,(name,room) in enumerate(session.rooms.rooms.items()):
            x,y=positions[name]
            pygame.draw.rect(self.surface,INK,(x,y,44,26))
            pygame.draw.rect(self.surface,TEAL if name in session.completed else (97,112,109) if name in session.visited else (44,55,68),(x,y,44,26),1)
            if name==session.rooms.current:pygame.draw.rect(self.surface,GOLD,(x-2,y-2,48,30),1)
            self.text(str(i+1) if name in session.visited else '?',x+18,y+8,GOLD)
