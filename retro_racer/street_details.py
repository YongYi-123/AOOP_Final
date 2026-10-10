"""Theme-specific street districts sharing the road-object projection interface."""
from dataclasses import dataclass
import pygame


@dataclass(frozen=True)
class StreetDetail:
    z: float
    x: float
    theme: str
    variant: int

    def draw(self,surface,sx,sy,sw):
        size = sw*.6
        if size < 5:return
        v = self.variant
        if self.theme == 'city':
            height=size*(1+.18*(v%3))
            pygame.draw.rect(surface,(25+v%3*12,25,70),(sx-size*.35,sy-height,size*.7,height))
            for row in range(5):
                for col in range(3):
                    pygame.draw.rect(surface,(255,90,190) if v%2 else (90,240,255),
                        (sx-size*.25+col*size*.2,sy-height+size*.12+row*size*.18,size*.09,size*.08))
        elif self.theme in ('beach','sunset_coast'):
            color=(255,160,100) if self.theme=='sunset_coast' else (90,230,220)
            pygame.draw.line(surface,(160,120,75),(sx,sy),(sx,sy-size*.85),max(1,int(size*.04)))
            pygame.draw.polygon(surface,color,[(sx-size*.5,sy-size*.55),(sx,sy-size),(sx+size*.5,sy-size*.55)])
            pygame.draw.rect(surface,(210,180,125),(sx-size*.55,sy-size*.18,size*1.1,size*.12))
            if v%2:pygame.draw.rect(surface,(100,150,190),(sx-size*.35,sy-size*.5,size*.7,size*.26))
        elif self.theme=='forest':
            pygame.draw.rect(surface,(100,65,45),(sx-size*.4,sy-size*.4,size*.8,size*.4))
            pygame.draw.polygon(surface,(55,90,60),[(sx-size*.55,sy-size*.4),(sx,sy-size),(sx+size*.55,sy-size*.4)])
            pygame.draw.rect(surface,(240,200,120),(sx-size*.1,sy-size*.3,size*.2,size*.2))
            if v%2:pygame.draw.line(surface,(180,140,100),(sx+size*.5,sy),(sx+size*.5,sy-size*.6),max(1,int(size*.06)))
        elif self.theme=='desert':
            pygame.draw.polygon(surface,(150+v%3*20,80,65),[(sx-size*.6,sy),(sx-size*.3,sy-size*.7),
                              (sx+size*.2,sy-size*.85),(sx+size*.5,sy)])
            pygame.draw.rect(surface,(60,130,90),(sx-size*.05,sy-size*.55,size*.1,size*.55))
        else:
            pygame.draw.rect(surface,(110+v%3*30,115,150),(sx-size*.4,sy-size*.55,size*.8,size*.55))
            pygame.draw.polygon(surface,(100,50,80),[(sx-size*.5,sy-size*.55),(sx,sy-size),(sx+size*.5,sy-size*.55)])
            for offset in (-.2,.15):pygame.draw.rect(surface,(255,225,120),(sx+size*offset,sy-size*.4,size*.12,size*.15))
            pygame.draw.rect(surface,(230,160,190),(sx-size*.45,sy-size*.16,size*.9,size*.12))


class StreetDistricts:
    @staticmethod
    def for_road(route,theme):
        return tuple(StreetDetail(i*route.segment_length,(-1 if (i//45)%2 else 1)*2.1,theme.key,i//45)
                     for i in range(12,len(route.curves),45))
