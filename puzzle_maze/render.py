"""Original pixel artwork built from crisp primitives at 320x240 resolution."""
import math
import random
import pygame
from puzzle_maze.core import Camera
from puzzle_maze.ui import NativeText
from puzzle_maze.combat import EnemyState
from puzzle_maze.exploration import DungeonAtlas
from puzzle_maze.puzzles import PushableBox, PressurePlate, Door, Key, SecretPassage, TimedSwitch, Switch, Chest, LightSource, Receiver, Reflector

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
        for kind in '#.~Ogv':self.tiles[kind]=self.tile(kind)

    def text(self,text,x,y,color=WHITE,font=None,max_width=None):
        self.ui.queue(text,x,y,color,font is self.title,max_width)

    def tile(self,kind):
        s=pygame.Surface((16,16));r=pygame.draw
        if kind=='v':s.fill(INK);return s
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

    def world(self,session,visual,dt,tool="pulse",controls=None):
        from puzzle_maze.onboarding import DEFAULT_CONTROLS
        controls=DEFAULT_CONTROLS if controls is None else controls
        self.ui.clear()
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
        for start,end in session.puzzles.beams:
            r.line(s,(255,227,130),(start[0]*16+8-cx,start[1]*16+8-cy),(end[0]*16+8-cx,end[1]*16+8-cy),2)
        # Hidden passage clue: moss and luminous cracks converge at the wall.
        for o in sorted(session.puzzles.objects.values(), key=lambda obj: 0 if isinstance(obj,PressurePlate) else 1):
            sx,sy=o.x*16-cx,o.y*16-cy
            if isinstance(o,SecretPassage):
                if not o.state.active:
                    s.blit(self.tiles['#'],(sx,sy));r.lines(s,GOLD,False,[(sx+8,sy+2),(sx+5,sy+7),(sx+10,sy+9),(sx+7,sy+14)])
                    r.line(s,TEAL,(sx-8,sy+8),(sx-2,sy+8));r.line(s,TEAL,(sx-5,sy+5),(sx-2,sy+8))
            elif isinstance(o,Chest):
                r.rect(s,(32,40,47),(sx+2,sy+4,12,10));r.rect(s,(153,98,56),(sx+2,sy+3,12,9))
                r.rect(s,TEAL if o.state.active else GOLD,(sx+2,sy+3,12,9),1)
                r.rect(s,GOLD,(sx+7,sy+6,2,3))
                if o.state.active:r.rect(s,INK,(sx+3,sy+4,10,3))
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
        for enemy in session.combat.enemies:
            if enemy.state==EnemyState.DEAD:continue
            sx,sy=enemy.x*16-cx,enemy.y*16-cy
            color=(251,210,139) if enemy.flash>0 else {'slime':(112,190,108),'bat':(152,127,208),'guardian':(176,138,96)}[enemy.kind]
            if enemy.state==EnemyState.DYING:
                radius=max(1,int(enemy.attack_timer*20));r.circle(s,color,(sx+8,sy+8),radius,1);continue
            if enemy.state==EnemyState.WINDUP:r.rect(s,(239,93,91),(sx-1,sy-1,18,18),1)
            r.ellipse(s,(24,34,44),(sx+1,sy+12,14,4))
            if enemy.kind=='slime':r.ellipse(s,color,(sx+2,sy+5,12,9))
            elif enemy.kind=='bat':
                wing=int(math.sin(self.time*18)*3)
                r.polygon(s,color,[(sx,sy+5+wing),(sx+6,sy+8),(sx+8,sy+5),(sx+10,sy+8),(sx+16,sy+5+wing),(sx+12,sy+13),(sx+4,sy+13)])
            else:
                r.rect(s,color,(sx+3,sy+2,10,12));r.rect(s,(88,94,104),(sx+2,sy+7,4,7));r.line(s,GOLD,(sx+13,sy+2),(sx+13,sy+13),2)
            for ex in (5,10):r.rect(s,INK,(sx+ex,sy+8,1,2))
            r.rect(s,(36,41,54),(sx+2,sy-3,12,2));r.rect(s,(234,108,114),(sx+2,sy-3,int(12*enemy.hp/enemy.max_hp),2))
        for drop in session.combat.loot:
            sx,sy=drop['pos'][0]*16-cx,drop['pos'][1]*16-cy
            r.circle(s,(238,104,129),(sx+8,sy+8),3)
        if p.invulnerable<=0 or int(self.time*15)%2==0:self.player(visual,p.facing,p.moving,cx,cy)
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
        near=next((o for o in session.puzzles.objects.values() if abs(o.x-p.x)+abs(o.y-p.y)<=1 and isinstance(o,(Switch,Door,SecretPassage,Chest,Reflector)) and not (isinstance(o,(Door,SecretPassage)) and o.state.active)),None)
        if near:
            self.text(f"[{controls['ability']}] Pulse" if isinstance(near,SecretPassage) else f"[{controls['interact']}] Interact",int(visual[0]*16)-cx-18,int(visual[1]*16)-cy-12,GOLD)
        s.set_clip(None)
        r.rect(s,INK,(4,190,202,17))
        for heart in range(p.max_hp):
            hx=8+heart*13;hy=195
            color=(239,102,119) if heart<p.hp else (75,66,81)
            r.polygon(s,color,[(hx,hy+2),(hx+2,hy),(hx+4,hy+2),(hx+6,hy),(hx+8,hy+2),(hx+8,hy+5),(hx+4,hy+9),(hx,hy+5)])
        self.text(f"{controls['heal']} Potion {session.inventory.potions} / {controls['attack']} Sword",78,193)
        r.rect(s,INK,(208,190,108,17))
        self.text(f"{controls['tool']} {tool} / Dash {session.dash_cooldown:.1f}",211,193)
        r.rect(s,INK,(0,208,320,32));r.line(s,(80,107,112),(0,208),(320,208))
        self.text(f'{session.rooms.current.upper()}  {room["name"]}',7,213,GOLD)
        keys=sum(session.inventory.keys.values())
        self.text(f'Keys {keys}  Sigils {len(session.completed)}/9  Shards {session.inventory.coins}',7,226)
        for i,(ability,label) in enumerate((('gloves','G'),('boots','B'),('mirror','L'),('magnet','M'))):
            self.text(label,228+i*19,213,TEAL if ability in session.inventory.abilities else (75,89,96))
        self.text(f"{controls['map']} map | {controls['pause']}",210,226,(135,161,154))

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
            self.text(('> ' if selected==i else '  ')+line,36,y,TEAL if selected==i else WHITE)
            y+=19

    def atlas_graph(self,session,bounds):
        x,y,w,h=bounds;r=pygame.draw;s=self.surface
        atlas=DungeonAtlas(session.rooms);layout=atlas.layout(session.visited)
        if not layout:return
        max_x=max(p[0] for p in layout.values())+1;max_y=max(p[1] for p in layout.values())+1
        cell_w=w/max_x;cell_h=h/max_y
        centers={name:(int(x+(pos[0]+.5)*cell_w),int(y+(pos[1]+.5)*cell_h)) for name,pos in layout.items()}
        for a,b in atlas.edges(session.visited):
            if a in session.visited or b in session.visited:r.line(s,(65,85,95),centers[a],centers[b])
        for name,center in centers.items():
            color=GOLD if name==session.rooms.current else TEAL if name in session.completed else WHITE if name in session.visited else (61,71,84)
            rw=max(4,int(cell_w*.58));rh=max(4,int(cell_h*.55))
            rect=pygame.Rect(center[0]-rw//2,center[1]-rh//2,rw,rh)
            r.rect(s,INK,rect);r.rect(s,color,rect,1)
            if w>100:self.text(name[1:] if name in session.visited else '?',rect.x+3,rect.y,color)
            elif name==session.rooms.current:r.rect(s,color,(center[0]-1,center[1]-1,2,2))
            if name in session.visited and any(o.get('ability') for o in session.rooms.rooms[name]['objects']):
                r.rect(s,TEAL,(rect.right-3,rect.bottom-3,2,2))

    def minimap(self,session):
        pygame.draw.rect(self.surface,INK,(239,5,77,52))
        pygame.draw.rect(self.surface,(77,108,112),(239,5,77,52),1)
        self.atlas_graph(session,(242,8,71,46))

    def map_panel(self,session):
        self.panel('DUNGEON ATLAS',[])
        self.atlas_graph(session,(30,75,260,68))
        known=session.exploration.tiles.get(session.rooms.current,set())
        rows=session.rooms.data['tiles'];w=len(rows[0]);h=len(rows)
        tile=min(120/w,66/h);x0,y0=32,151
        for x,y in known:
            color=(93,114,107) if rows[y][x] not in '#~O' else (38,64,83) if rows[y][x]=='~' else (62,73,89)
            pygame.draw.rect(self.surface,color,(int(x0+x*tile),int(y0+y*tile),max(1,int(tile)),max(1,int(tile))))
        for kind,(x,y) in DungeonAtlas(session.rooms).discovered_markers(session):
            color=GOLD if kind=='exit' else TEAL if kind in ('chest','receiver') else (198,136,113)
            pygame.draw.rect(self.surface,color,(int(x0+x*tile),int(y0+y*tile),2,2))
        p=session.player
        pygame.draw.rect(self.surface,GOLD,(int(x0+p.x*tile),int(y0+p.y*tile),3,3))
        self.text(session.rooms.data['name'],162,152,GOLD)
        self.text(f'Explored: {len(known)} tiles',162,169)
        self.text('Gold: you / exit',162,184)
        self.text('Teal: item / receiver',162,199)
        self.text('TAB closes / R resets',32,218)
