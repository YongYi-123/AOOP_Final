"""Original code-drawn pixel cats and rotating yarn; presentation only."""
from enum import Enum
import math
import pygame
from .model import FLOOR, MatchState


class CatAnimation(Enum):
    IDLE = 'idle'
    MOVE = 'move'
    JUMP = 'jump'
    HIT = 'hit'
    SMASH = 'smash'
    VICTORY = 'victory'


class CatAthleteRenderer:
    @staticmethod
    def state(player, match):
        if match.state is MatchState.FINISHED and match.outcome.winner == player.side:
            return CatAnimation.VICTORY
        if player.attack.animating:
            return CatAnimation.SMASH
        if player.hit_flash > 0:
            return CatAnimation.HIT
        if player.y < FLOOR-player.radius-.5:
            return CatAnimation.JUMP
        if player.moving:
            return CatAnimation.MOVE
        return CatAnimation.IDLE

    def draw(self, surface, player, match):
        state = self.state(player, match)
        fur = (235, 235, 242) if player.side == 0 else (38, 38, 48)
        scarf = (90, 240, 255) if player.side == 0 else (255, 110, 210)
        x, y = round(player.x), round(player.y)
        wave = math.sin(match.elapsed * (18 if state is CatAnimation.MOVE else 5))
        bounce = int(abs(wave)*3) if state is CatAnimation.VICTORY else 0
        y -= bounce
        pygame.draw.ellipse(surface, (12, 8, 25), (x-14, FLOOR-3, 28, 5))
        tail = 1 if player.side == 0 else -1
        pygame.draw.lines(surface, fur, False,
                          [(x+tail*10,y+7),(x+tail*18,y+3),(x+tail*18,y-2+int(wave*3))], 3)
        pygame.draw.rect(surface, (30, 20, 40), (x-12,y-12,24,23))
        pygame.draw.rect(surface, fur, (x-10,y-11,20,21))
        patch = (38,38,48) if player.side == 0 else (235,235,242)
        pygame.draw.rect(surface,patch,(x-10,y-11,9,8))
        pygame.draw.rect(surface,(245,245,250),(x-2,y-4,5,13))
        for dx in (-10, 5):
            pygame.draw.polygon(surface, fur, [(x+dx,y-9),(x+dx,y-19),(x+dx+6,y-10)])
            pygame.draw.line(surface, (255, 135, 170), (x+dx+2,y-15),(x+dx+3,y-11),2)
        pygame.draw.rect(surface, (235, 235, 242), (x-6,y+1,12,8))
        blink = int(match.elapsed*2)%11 == 10 and state is CatAnimation.IDLE
        for dx in (-5, 4):
            pygame.draw.rect(surface, (25, 20, 45), (x+dx,y-6,2,1 if blink else 3))
        for direction in (-1,1):
            pygame.draw.line(surface,(190,190,210),(x+direction*5,y-1),(x+direction*13,y-3),1)
            pygame.draw.line(surface,(190,190,210),(x+direction*5,y+1),(x+direction*13,y+2),1)
        pygame.draw.rect(surface, (230, 100, 140), (x-1,y-1,3,2))
        pygame.draw.line(surface, scarf, (x-10,y+1),(x+10,y+1),3)
        for direction in (-1, 1):
            arm_y = y-9 if state in (CatAnimation.HIT,CatAnimation.VICTORY) else y+5
            if state is CatAnimation.SMASH:
                # Lift the striking paw, then sweep forward through follow-through.
                facing = 1 if player.side == 0 else -1
                progress = min(1, player.attack.age / .19)
                arm_y = y - 18 + round(progress * 20) if direction == facing else y-6
                if direction == facing:
                    start = (x + direction*10, y-8)
                    end = (x + direction*(16+round(progress*5)), arm_y+2)
                    pygame.draw.line(surface, scarf, start, end, 2)
                    pygame.draw.rect(surface, fur, (end[0]-2,end[1]-2,5,5))
                    if player.attack.active:
                        # Neon swoosh arc behind the striking paw plus a lit paw outline.
                        pygame.draw.rect(surface, (255,224,90), (end[0]-3,end[1]-3,7,7), 1)
                        for lag, color in ((5,(255,224,90)),(9,scarf)):
                            pygame.draw.line(surface, color,
                                             (end[0]-facing*lag, end[1]-lag),
                                             (end[0]-facing*(lag+5), end[1]-lag-4), 2)
            pygame.draw.rect(surface, fur, (x+direction*12-2,arm_y,4,5))
            foot_y = y+11 + (int(wave*2)*direction if state is CatAnimation.MOVE else 0)
            pygame.draw.rect(surface, fur, (x+direction*6-2,foot_y,5,3))


class YarnRenderer:
    def __init__(self):
        self.sprite = pygame.Surface((16,16), pygame.SRCALPHA)
        pygame.draw.circle(self.sprite,(50,20,60),(8,8),7)
        pygame.draw.circle(self.sprite,(255,155,205),(8,8),6)
        for offset in (-3,0,3):
            pygame.draw.arc(self.sprite,(155,70,135),(3+offset,2,8,12),-.9,1.8,1)
        pygame.draw.line(self.sprite,(255,220,240),(4,4),(10,12),1)

    def draw(self, surface, ball):
        sprite = pygame.transform.rotate(self.sprite, ball.rotation % 360)
        surface.blit(sprite,sprite.get_rect(center=(round(ball.x),round(ball.y))))
