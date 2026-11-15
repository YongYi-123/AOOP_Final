"""Cached debug-room set dressing and body-sized story props."""
import pygame
from puzzle_maze.pixel_font import render

class DeveloperRoomArt:
    def __init__(self):self.cached=None
    def layer(self):
        if self.cached is not None:return self.cached
        s=pygame.Surface((416,256),pygame.SRCALPHA)
        for x in range(32,400,32):pygame.draw.line(s,(65,85,115,85),(x,20),(x,236))
        for y in range(32,240,32):pygame.draw.line(s,(65,85,115,85),(20,y),(396,y))
        for x,y,label in ((40,28,'X=??'),(280,28,'Y=--'),(45,195,'BUILD 00'),(260,203,'LOST SIGNAL')):
            s.blit(render(label,8,(105,160,175)),(x,y))
        pygame.draw.rect(s,(37,27,43),(173,68,78,33))
        pygame.draw.rect(s,(130,86,72),(175,67,74,24))
        pygame.draw.line(s,(205,149,111),(176,68),(247,68),2)
        for x in (178,240):pygame.draw.rect(s,(80,55,58),(x,91,6,11))
        pygame.draw.rect(s,(30,39,53),(200,52,20,14));pygame.draw.rect(s,(100,175,170),(203,55,14,8),1)
        self.cached=s;return s
    def draw(self,target,camera,time):
        target.blit(self.layer(),(-camera[0],-camera[1]))
        for i in range(4):
            x=40+i*85;y=40+int(time*3+i*37)%160
            target.fill((90,120,135),(x-camera[0],y-camera[1],6,1))

    @staticmethod
    def prop(target,key,x,y):
        r=pygame.draw
        if key=='kevin_photo':
            r.rect(target,(195,165,110),(x+1,y,14,14));r.rect(target,(50,65,80),(x+3,y+2,10,10))
            r.rect(target,(210,165,125),(x+5,y+4,3,3));r.rect(target,(100,160,150),(x+4,y+7,5,4))
            r.line(target,(195,190,180),(x+9,y+3),(x+11,y+11),2)
        elif key=='kevin_note':
            r.rect(target,(220,209,167),(x+2,y+1,12,12))
            for yy in (4,7,10):r.line(target,(95,80,85),(x+4,y+yy),(x+11,y+yy))
        elif key=='miao_memory':
            r.ellipse(target,(125,135,155),(x+2,y+4,12,10))
            r.polygon(target,(165,175,195),[(x+2,y+6),(x+2,y),(x+6,y+3),(x+10,y+3),(x+14,y),(x+14,y+6)])
            for xx in (5,10):r.rect(target,(110,235,215),(x+xx,y+6,2,2))
            r.lines(target,(125,135,155),False,[(x+12,y+12),(x+16,y+10),(x+16,y+6)],2)
