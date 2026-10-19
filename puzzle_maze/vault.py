"""Original Royal Treasure Vault layout, native pixel scenery and a future scroll."""
import math
import pygame
from puzzle_maze.icons import IconAtlas

def add_vault(rooms):
    source=rooms['r18'];exit=next(e for e in source['exits'] if e.get('finish'))
    exit.update(target='r27',arrival=[2,7],return_id='r27:r18',id='r18:r27');exit.pop('finish')
    w,h=22,14;tiles=['#'*w]+['#'+'.'*(w-2)+'#' for _ in range(h-2)]+['#'*w]
    rows=[list(r) for r in tiles]
    for x,y in ((4,2),(17,2),(4,11),(17,11)):rows[y][x]='O'
    rooms['r27']=dict(name='Royal Treasure Vault',floor='B1F',grid_x=6,grid_y=0,atlas=[6,0],layout_revision='4.0',content_revision='4.4',theme='royal_vault',architecture='mosaic',hint='The three sealed royal chests fund the expedition receipt. Read the floating scroll; the eastern arch ends your journey.',spawn=[2,7],tiles=[''.join(row) for row in rows],enemies=[],objects=[
        dict(id='royal_tokens',type='chest',pos=[6,4],loot=['royal_tokens'],royal=True),
        dict(id='royal_tickets',type='chest',pos=[15,4],loot=['royal_tickets'],royal=True),
        dict(id='royal_collection',type='chest',pos=[15,10],loot=['royal_crown'],royal=True),
        dict(id='scroll',type='mystery_scroll',pos=[11,7],content_id='coming_soon'),
        dict(id='gate',type='door',pos=[20,7],requires=['royal_tokens','royal_tickets','royal_collection'])],
        goal=['royal_tokens','royal_tickets','royal_collection'],decorations=[dict(kind='torch',pos=[x,0],phase=x) for x in (3,8,13,18)],
        exits=[dict(id='r27:r18',return_id='r18:r27',target='r18',pos=[1,7],arrival=[23,8],direction='WEST',entrance='stone',requires=[],abilities=[],orb_allowed=True),
               dict(id='r27:finish',return_id=None,target='r27',pos=[20,7],arrival=[20,7],direction='EAST',entrance='stone',requires=['gate'],abilities=[],finish=True,orb_allowed=True)])
    return rooms

class RoyalVaultArt:
    def __init__(self):self.base=None;self.atlas=IconAtlas()
    def layer(self):
        if self.base is not None:return self.base
        s=pygame.Surface((352,224),pygame.SRCALPHA);r=pygame.draw
        # Broad clear central aisle. Treasure and empty display chests stay at its sides.
        for x in (32,288):
            for y in (50,86,126,160):
                for i in range(10):
                    ox=(i*7)%25;oy=(i*11)%16
                    c=(231,180,65) if y%4 else (194,211,216)
                    r.ellipse(s,(62,49,51),(x+ox,y+oy+2,8,4));r.ellipse(s,c,(x+ox,y+oy,8,3));r.line(s,(255,233,163),(x+ox+2,y+oy),(x+ox+5,y+oy))
        for x,y,c in ((70,80,(230,92,123)),(266,80,(88,178,240)),(70,150,(94,215,155)),(265,150,(186,122,233))):
            r.polygon(s,(42,37,60),[(x,y-6),(x+8,y),(x,y+8),(x-8,y)])
            r.polygon(s,c,[(x,y-6),(x+6,y),(x,y+6),(x-6,y)]);r.line(s,(255,241,215),(x,y-4),(x-3,y))
        for x,y in ((64,32),(272,32),(64,176),(272,176)):
            r.rect(s,(87,62,52),(x-5,y-8,12,23));r.rect(s,(220,173,78),(x-4,y-9,10,22));r.line(s,(255,229,146),(x-2,y-8),(x-2,y+9),2)
            r.rect(s,(242,201,108),(x-7,y-11,16,4));r.rect(s,(177,124,58),(x-7,y+12,16,4))
        for x in (64,100):
            # Open, visibly empty display chests: no locks and no false interaction hint.
            r.rect(s,(122,79,47),(x,158,20,13));r.rect(s,(28,29,43),(x+2,157,16,8));r.rect(s,(174,122,65),(x,149,20,5));r.line(s,(233,184,91),(x,149),(x+19,149))
        for x in range(96,265,24):
            for y in (30,194):r.lines(s,(165,133,81),False,[(x,y),(x+4,y-3),(x+8,y),(x+4,y+3),(x,y)])
        for x in range(16,337,32):
            r.rect(s,(202,170,103),(x,2,18,9),1);r.line(s,(240,205,128),(x+3,5),(x+14,5))
        self.base=s;return s
    def draw(self,target,camera,time):
        cx,cy=camera;target.blit(self.layer(),(-cx,-cy));r=pygame.draw
        for i in range(12):
            x=int((i*29+math.sin(time*.5+i)*5)%330)+8;y=int((i*41-time*8)%190)+12
            if int(time*4+i)%4:r.rect(target,(229,190,105),(x-cx,y-cy,1,1))
        for x,y in ((70,80),(266,80),(70,150),(265,150)):
            if int(time*5+x)%4==0:
                r.line(target,(255,243,187),(x-cx-2,y-cy),(x-cx+2,y-cy));r.line(target,(255,243,187),(x-cx,y-cy-2),(x-cx,y-cy+2))
    def scroll(self,target,x,y,time,glow):
        bob=int(math.sin(time*2)*3)
        target.blit(glow,(x-24,y-27));pygame.draw.ellipse(target,(60,48,60),(x+2,y+12,13,4))
        target.blit(pygame.transform.scale(self.atlas.get('mystery_scroll'),(20,20)),(x-2,y-9+bob))
        for i in range(4):
            a=time+i*math.pi/2;px=int(x+8+math.cos(a)*15);py=int(y+3+math.sin(a)*7)
            pygame.draw.rect(target,(249,224,148),(px,py,1,2))
