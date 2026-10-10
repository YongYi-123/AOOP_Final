"""Original circuit landmarks using the same road-object projection contract."""
from dataclasses import dataclass
import pygame


@dataclass(frozen=True)
class CircuitLandmark:
    z: float
    x: float
    kind: str

    def draw(self,surface,sx,sy,sw):
        size=sw*.55
        if size<3: return
        if self.kind=='starlight':
            for i,color in enumerate(((45,45,85),(65,40,95),(35,60,85))):
                x=sx+size*(i*.45-.65)
                height=size*(.7+.2*(i%2))
                pygame.draw.rect(surface,color,(x,sy-height,size*.4,height))
                for level in range(3):
                    pygame.draw.line(surface,(255,110,210) if i%2 else (90,240,255),
                                     (x+size*.06,sy-height+size*(.15+level*.15)),
                                     (x+size*.3,sy-height+size*(.15+level*.15)),max(1,int(size*.025)))
        elif self.kind=='harbor':
            pygame.draw.lines(surface,(110,130,160),False,
                [(sx-size*.5,sy),(sx-size*.5,sy-size),(sx+size*.5,sy-size),(sx+size*.5,sy)],max(1,int(size*.05)))
            pygame.draw.line(surface,(255,220,100),(sx,sy-size),(sx,sy-size*.4),max(1,int(size*.025)))
            for i,color in enumerate(((40,140,160),(130,65,150),(220,130,80))):
                pygame.draw.rect(surface,color,(sx-size*.6+i*size*.35,sy-size*.25,size*.3,size*.25))
        elif self.kind in ('summit','cloudpass'):
            for dx in (-.5,0,.5):
                pygame.draw.rect(surface,(110,80,60),(sx+dx*size-size*.035,sy-size*.25,size*.07,size*.25))
                for top in (.8,.6,.4):
                    pygame.draw.polygon(surface,(45,100+int(top*45),95),
                         [(sx+dx*size,sy-size*top),(sx+dx*size-size*.25,sy-size*(top-.35)),
                          (sx+dx*size+size*.25,sy-size*(top-.35))])
        else:
            pygame.draw.rect(surface,(55,50,95),(sx-size*.7,sy-size*.45,size*1.4,size*.45))
            for row in range(3):
                pygame.draw.line(surface,(100,120,160),(sx-size*.7,sy-size*.15*row),
                                  (sx+size*.7,sy-size*.15*row),max(1,int(size*.025)))
            for i,color in enumerate(((90,240,255),(255,110,210),(255,224,90))):
                x=sx-size*.5+i*size*.5
                pygame.draw.line(surface,(200,200,220),(x,sy-size*.45),(x,sy-size),max(1,int(size*.02)))
                pygame.draw.polygon(surface,color,[(x,sy-size),(x+size*.3,sy-size*.88),(x,sy-size*.76)])


class CircuitLandmarks:
    @staticmethod
    def for_route(route):
        return tuple(CircuitLandmark(route.length*fraction, side*1.6, route.key)
                     for fraction,side in ((.045,-1),(.22,1),(.48,-1),(.7,1),(.88,-1)))
