"""A neon garage terminal fitting the existing interactable furniture contract."""
import pygame
from stations import Station
from font import get_font
from settings import Col


class GarageStation(Station):
    prompt_label = 'GARAGE'

    def __init__(self,pos):
        sprite = pygame.Surface((44,48),pygame.SRCALPHA)
        sprite.fill((30,20,60))
        pygame.draw.rect(sprite,Col.CYAN,(1,1,42,46),1)
        sprite.blit(get_font().render('GARAGE',Col.YELLOW),(4,5))
        pygame.draw.rect(sprite,(10,7,25),(4,17,36,21))
        pygame.draw.rect(sprite,(255,80,185),(10,26,24,9))
        pygame.draw.rect(sprite,Col.CYAN,(15,21,14,7))
        for x in (11,28):pygame.draw.rect(sprite,(10,7,20),(x,33,5,4))
        x,y = pos
        super().__init__(sprite,pos,(x+1,y+37,42,11),Col.CYAN,Col.MAGENTA)

    def interact(self,scene):
        scene.open_garage()
