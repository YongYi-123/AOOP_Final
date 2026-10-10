"""Clear race-only roof badge and spoiler; no collision or driving changes."""
import pygame


class RivalBadge:
    @staticmethod
    def draw(surface,sx,sy,width,number):
        if width < 14:return
        roof = sy-width*.48
        pygame.draw.line(surface,(255,224,90),(sx-width*.4,roof),(sx+width*.4,roof),max(2,int(width*.035)))
        size=max(5,min(16,int(width*.2)))
        rect=pygame.Rect(round(sx-size*.5),round(roof-size-3),size,size)
        pygame.draw.rect(surface,(20,10,35),rect)
        pygame.draw.rect(surface,(255,224,90),rect,1)
        # A compact race-number pip badge stays legible even far ahead.
        for i in range(number):
            x=rect.x+2+(i%3)*max(1,(size-4)//3)
            y=rect.y+2+(i//3)*max(1,(size-4)//2)
            pygame.draw.rect(surface,(90,240,255),(x,y,2,2))
