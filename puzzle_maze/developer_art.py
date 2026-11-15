"""Production-only cozy studio art: shared by the actual room and all preview targets."""
import pygame
from puzzle_maze.pixel_font import render
from puzzle_maze.studio_layout import SIZE,FURNITURE
from puzzle_maze.studio_furniture import furniture_sprite,picture

class DeveloperRoomArt:
    revision='quiet-studio-3'
    def __init__(self):self.cached=None;self.base=None;self.parts={};self.translucent={};self.masks={};self.actor_mask=pygame.mask.Mask((16,18),fill=True)
    def floor(self):
        if self.base is not None:return self.base
        s=pygame.Surface(SIZE);r=pygame.draw;s.fill((225,205,166))
        r.rect(s,(242,225,190),(9,7,302,38));r.rect(s,(213,183,139),(9,38,302,9))
        r.line(s,(254,239,204),(10,38),(309,38),2)
        for y in range(48,201,12):
            for x in range(-24 if y%24 else 0,320,48):
                r.rect(s,(184+(x//48)%2*4,139+(y//12)%2*4,91),(x+1,y,47,11))
                r.line(s,(204,160,107),(x+4,y+2),(x+42,y+2));r.line(s,(166,121,80),(x+12,y+8),(x+26,y+8))
        r.rect(s,(235,214,175),(0,42,13,163));r.rect(s,(201,168,122),(12,45,4,159))
        r.rect(s,(224,200,155),(304,43,16,162));r.line(s,(248,225,184),(304,44),(304,202))
        r.rect(s,(155,107,71),(12,200,296,8));r.line(s,(221,179,118),(13,200),(307,200),2)
        # Two restful textiles with a broad unoccupied central aisle.
        r.rect(s,(151,160,124),(24,134,121,61),border_radius=4);r.rect(s,(221,209,164),(27,137,115,55),2)
        r.rect(s,(225,186,165),(223,138,80,56),border_radius=4);r.rect(s,(246,220,183),(226,141,74,50),1)
        for xx in range(32,136,13):r.line(s,(173,180,143),(xx,141),(xx,188))
        # Contact shadows share the exact footprints used by movement.
        for item in FURNITURE:
            x,y,w,h=item.footprint
            r.ellipse(s,(149,112,78),(x-3,y+h-7,w+7,10))
        # A proper wooden doorway, not a dungeon arch.
        r.rect(s,(164,111,73),(7,105,24,37));r.rect(s,(104,78,62),(12,110,17,27))
        r.rect(s,(241,208,152),(9,107,21,33),2);r.rect(s,(213,169,107),(12,135,18,5))
        # Wall memories, a short to-do card and a warm floor lamp.
        r.rect(s,(160,113,71),(253,8,51,32));r.rect(s,(209,166,106),(255,10,47,28))
        for x,y,w,h in ((259,13,16,19),(279,14,20,12),(281,29,15,7)):
            r.rect(s,(248,230,187),(x,y,w,h));r.rect(s,(192,129,105),(x+2,y+2,2,2))
            for yy in range(y+7,y+h-2,4):r.line(s,(174,148,112),(x+3,yy),(x+w-3,yy))
        picture(s,235,127,True)
        for x,c in ((224,(219,180,131)),(245,(168,197,187))):
            r.ellipse(s,(135,107,83),(x,185,15,7));r.ellipse(s,c,(x+1,184,13,5))
            r.ellipse(s,(107,163,170) if x==245 else (153,110,78),(x+3,185,9,2))
        r.circle(s,(200,139,151),(272,190),3);r.line(s,(224,201,145),(268,192),(264,193))
        r.line(s,(121,107,75),(101,163),(101,137),2);r.ellipse(s,(132,109,76),(95,161,13,5))
        r.polygon(s,(249,216,153),[(95,133),(107,133),(112,144),(90,144)]);r.line(s,(255,236,188),(92,144),(110,144))
        # Fade pigments, then light just the work areas, not the entire room.
        tint=pygame.Surface(SIZE);tint.fill((172,164,153));s.blit(tint,(0,0),special_flags=pygame.BLEND_RGB_MULT)
        for cx,cy,radius in ((166,81,45),(101,145,34)):
            glow=pygame.Surface(SIZE,pygame.SRCALPHA)
            for rad in range(radius,0,-4):
                pygame.draw.circle(glow,(94,57,25,round(12*(1-rad/radius))),(cx,cy),rad)
            s.blit(glow,(0,0))
        self.base=s;return s
    def ensure(self,item):
        if item.name not in self.parts:
            self.parts[item.name]=furniture_sprite(item)
            tint=pygame.Surface(item.bounds[2:],pygame.SRCALPHA);tint.fill((202,188,166,255))
            self.parts[item.name].blit(tint,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
            self.masks[item.name]=pygame.mask.from_surface(self.parts[item.name])
    def occludes(self,item,actor):
        if not pygame.Rect(item.bounds).colliderect(actor):return False
        self.ensure(item)
        return self.masks[item.name].overlap(self.actor_mask,(actor.x-item.bounds[0],actor.y-item.bounds[1])) is not None
    def sprite(self,item,ghost=False):
        self.ensure(item)
        if not ghost:return self.parts[item.name]
        if item.name not in self.translucent:
            s=self.parts[item.name].copy();s.set_alpha(180);self.translucent[item.name]=s
        return self.translucent[item.name]
    def layer(self):
        if self.cached is None:
            self.cached=self.floor().copy()
            for item in sorted(FURNITURE,key=lambda f:f.footprint[1]+f.footprint[3]):self.cached.blit(self.sprite(item),item.bounds[:2])
        return self.cached
    def draw(self,target,camera,time,effect=None):
        target.blit(self.layer(),(-camera[0],-camera[1]))
    def effects(self,s,time,effect):
        # Local screen activity, with no room-wide glitch or cold lighting.
        if int(time*2)%3:s.fill((121,163,139),(279,77,5,1))
        # Sparse dust in warm pools; deterministic and independent of collisions.
        for i in range(9):
            x=95+int((i*19+time*1.5)%120);y=56+int((i*13+time*.7)%78)
            if int(time+i)%4==0:s.fill((155,128,91),(x,y,1,1))
        if effect and time-effect[1]<3:
            if effect[0]=='lab_terminal':
                pygame.draw.polygon(s,(223,184,133),[(271,65),(271,59),(275,62),(279,59),(279,66)])
                for x in (273,277):s.fill((76,96,95),(x,63,1,1))
            elif effect[0]=='lab_button':pygame.draw.rect(s,(224,153,151),(232,66,10,6),1)
