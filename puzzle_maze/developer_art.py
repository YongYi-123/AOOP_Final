"""Kevin's warm engineering studio: a dedicated interior, not a dungeon overlay."""
import math
import pygame
from puzzle_maze.pixel_font import render
from puzzle_maze.lab_hardware import equipment

class DeveloperRoomArt:
    def __init__(self):self.cached=None
    def layer(self):
        if self.cached is not None:return self.cached
        s=pygame.Surface((416,256));r=pygame.draw
        # Warm wallpaper and wood planks replace all ordinary dungeon masonry.
        s.fill((67,45,44));r.rect(s,(184,152,108),(16,16,384,38))
        for x in range(20,397,12):r.line(s,(169,136,99),(x,17),(x,51))
        r.rect(s,(95,61,43),(16,51,384,8));r.line(s,(219,172,103),(16,52),(399,52),2)
        for y in range(60,241,12):
            for x in range(16,400,48):
                offset=24 if y%24 else 0
                r.rect(s,(112+(x//48)%3*5,77+(y//12)%2*4,51),(x-offset,y,47,11))
                r.line(s,(135,95,61),(x-offset+2,y+2),(x-offset+42,y+2))
        r.rect(s,(94,56,69),(83,115,217,101));r.rect(s,(186,134,93),(86,118,211,95),2)
        for x in range(95,290,13):r.line(s,(120,76,81),(x,124),(x,207))
        from puzzle_maze.studio_personality import shadows
        shadows(s)
        # Large central workbench: two CRTs, a flat display and several input devices.
        self.desk(s,(139,70,170,37))
        for x,kind in ((146,'crt'),(196,'crt'),(251,'display')):s.blit(equipment(kind),(x,37))
        for x in (148,250):s.blit(equipment('keyboard'),(x,82))
        r.ellipse(s,(205,190,151),(293,91,7,10));r.line(s,(47,40,40),(296,82),(296,91))
        # Left hardware repair bench; each tool has a distinct native pixel silhouette.
        self.desk(s,(31,67,97,37))
        s.blit(equipment('case'),(30,28));s.blit(equipment('scope'),(78,35))
        s.blit(pygame.transform.scale(equipment('motherboard'),(30,27)),(43,72))
        s.blit(pygame.transform.scale(equipment('meter'),(22,25)),(78,75))
        s.blit(pygame.transform.scale(equipment('solder'),(26,26)),(100,75))
        self.desk(s,(292,94,98,25))
        s.blit(pygame.transform.scale(equipment('ram'),(29,26)),(351,80))
        s.blit(pygame.transform.scale(equipment('cpu'),(23,22)),(326,78))
        # Personal memory corner and a quiet network terminal.
        for x in (38,332):self.bookshelf(s,x,159)
        self.plant(s,65,218);self.plant(s,374,151)
        self.chair(s,103,174);self.chair(s,264,145)
        self.desk(s,(318,138,64,24));s.blit(equipment('crt'),(329,106))
        s.blit(pygame.transform.scale(equipment('disk'),(16,16)),(355,145))
        s.blit(pygame.transform.scale(equipment('drive'),(24,22)),(323,143))
        self.desk(s,(35,114,42,21))
        s.blit(pygame.transform.scale(equipment('psu'),(28,25)),(39,96))
        # Coiled connectors and a folded circuit drawing on the repair trolley.
        r.lines(s,(205,163,92),False,[(65,117),(71,118),(71,126),(63,127),(63,121)],1)
        r.rect(s,(222,208,167),(79,109,22,14))
        r.lines(s,(71,115,100),False,[(82,112),(88,112),(88,119),(97,119),(97,113)],1)
        r.rect(s,(84,96,88),(86,114,5,4),1)
        for x in (199,219):
            r.rect(s,(86,55,42),(x,23,16,18));r.rect(s,(207,173,110),(x+1,24,14,16),1)
            r.polygon(s,(112,141,123),[(x+3,37),(x+7,29),(x+12,37)])
        # Amber lamps illuminate the work surfaces without washing out equipment.
        for x,y in ((129,72),(310,143)):
            r.line(s,(66,58,49),(x,y),(x,y-27),2)
            r.polygon(s,(235,191,108),[(x-8,y-28),(x+6,y-28),(x+11,y-18),(x-12,y-18)])
            r.line(s,(255,222,148),(x-9,y-18),(x+8,y-18),2)
        s.blit(render('KEVIN / ENGINEERING',8,(98,70,56)),(244,24))
        # The actual western portal is visibly framed as the studio doorway.
        r.rect(s,(48,34,35),(11,103,18,35));r.rect(s,(204,161,99),(12,103,17,35),2)
        r.line(s,(231,190,118),(30,104),(30,137),2)
        from puzzle_maze.studio_personality import paint
        paint(s)
        self.cached=s;return s

    @staticmethod
    def desk(s,rect):
        x,y,w,h=rect;r=pygame.draw
        r.rect(s,(55,36,34),(x-2,y-2,w+4,h+5));r.rect(s,(157,104,65),(x,y,w,h))
        r.line(s,(218,165,103),(x+1,y+1),(x+w-2,y+1),2)
        r.rect(s,(91,55,40),(x,y+h-6,w,8))
        for xx in (x+4,x+w-10):r.rect(s,(85,54,40),(xx,y+h,6,13))
    @staticmethod
    def bookshelf(s,x,y):
        r=pygame.draw;r.rect(s,(62,39,33),(x,y,42,49));r.rect(s,(139,93,58),(x+2,y+2,38,45))
        for yy in (y+5,y+25):
            for i,c in enumerate(((114,65,76),(83,115,90),(76,100,125),(174,135,78),(106,79,117))):
                r.rect(s,c,(x+5+i*6,yy,5,15));r.line(s,(212,184,130),(x+5+i*6,yy+4),(x+8+i*6,yy+4))
            r.line(s,(72,45,34),(x+2,yy+17),(x+39,yy+17),2)
    @staticmethod
    def chair(s,x,y):
        r=pygame.draw;r.rect(s,(59,43,41),(x-2,y-2,29,32));r.rect(s,(104,133,101),(x,y,25,26),border_radius=4)
        r.rect(s,(130,150,112),(x+4,y+3,17,13));r.rect(s,(73,95,76),(x-3,y+22,31,8))
        for xx in (x,x+20):r.line(s,(60,47,41),(xx,y+30),(xx,y+35),3)
    @staticmethod
    def plant(s,x,y):
        r=pygame.draw;r.polygon(s,(167,95,62),[(x-8,y),(x+8,y),(x+5,y+13),(x-5,y+13)])
        for dx,dy in ((-8,-15),(7,-19),(0,-25),(-10,-5),(10,-8)):
            r.line(s,(71,113,69),(x,y),(x+dx,y+dy),2);r.ellipse(s,(111,153,85),(x+dx-4,y+dy-3,8,6))
    def draw(self,target,camera,time):
        target.blit(self.layer(),(-camera[0],-camera[1]))
        # Small cyan activity on the hidden network terminal, rather than a room-wide glitch.
        if int(time*2)%3:target.fill((117,206,173),(342-camera[0],119-camera[1],9,1))

    @staticmethod
    def prop(target,key,x,y):
        r=pygame.draw
        if key=='kevin_photo':
            r.rect(target,(198,157,95),(x+1,y,14,14));r.rect(target,(53,73,75),(x+3,y+2,10,10))
            r.rect(target,(215,170,123),(x+5,y+4,3,3));r.rect(target,(115,150,119),(x+4,y+7,5,4))
            r.line(target,(185,181,164),(x+9,y+3),(x+11,y+11),2)
        elif key=='kevin_note':
            r.rect(target,(226,211,168),(x+2,y+1,12,12))
            for yy in (4,7,10):r.line(target,(95,80,72),(x+4,y+yy),(x+11,y+yy))
        elif key=='miao_memory':
            from puzzle_maze.miao_adapter import guide_frame
            image=guide_frame();target.blit(image,image.get_rect(midbottom=(x+8,y+16)))
        elif key=='lab_gpu':target.blit(pygame.transform.scale(equipment('gpu'),(32,29)),(x-7,y-12))
        elif key=='lab_keyboard':target.blit(pygame.transform.scale(equipment('keyboard'),(30,27)),(x-7,y-12))
        elif key=='lab_terminal':pass # The terminal belongs to the cached furniture layer.
