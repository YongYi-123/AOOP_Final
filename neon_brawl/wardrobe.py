"""Body-anchored pixel clothing and bespoke boss silhouettes, before facing/rotation."""
import pygame
from .outfits import outfit_for

INK=(12,10,28)

def dress(surface,name,index,bob,reach,attack):
    o=outfit_for(name,index)
    c,t=o.color,o.trim
    def box(color,x,y,w,h): surface.fill(color,(x,y+bob,w,h))
    def poly(color,points): pygame.draw.polygon(surface,color,[(x,y+bob) for x,y in points])
    if o.style in ('leather','denim'):
        poly(t,[(25,25),(30,30),(28,35),(24,29)])
        poly(t,[(38,25),(33,30),(35,35),(40,29)])
        box(t,26,35,4,3); box(t,35,35,4,3)
        if o.style=='leather': box((230,220,200),24,25,3,2)
        else:
            box((165,195,220),25,27,2,12); box((165,195,220),38,27,2,12)
    elif o.style=='hood':
        poly(c,[(23,22),(22,10),(26,6),(37,6),(42,12),(41,25),(37,22),(38,12),(28,12),(27,23)])
        box(t,29,27,1,8); box(t,35,27,1,8); box(INK,29,35,7,3)
    elif o.style in ('vest','military'):
        box((210,150,110),21,26,5,7)
        box(INK,29,26,5,13)
        box(t,25,30,4,6); box(t,36,30,4,6)
        if o.style=='military':
            for x in (25,36): box((35,50,38),x,33,4,1)
            box(c,24,9,17,4)
        else: box(INK,27,17,12,5)
    elif o.style=='track':
        box(t,24,25,3,15); box(t,37,25,3,15); box(t,24,47,2,7)
    elif o.style=='courier':
        poly(t,[(25,24),(29,24),(41,40),(37,41)])
        box(INK,18,25,6,14); box(c,19,26,4,11)
        box(t,26,10,14,5); box(INK,28,15,11,3)
    elif o.style=='armor':
        poly(INK,[(20,23),(29,22),(32,27),(37,22),(44,24),(45,31),(38,32),(38,40),(25,40),(24,32),(19,31)])
        box(c,21,24,8,6); box(c,37,24,7,6); box((115,135,150),26,29,12,10)
        box(t,29,31,7,2); box(INK,27,36,10,2); box(c,24,8,18,9); box(t,27,15,13,2)
    elif o.style=='worker':
        box((40,50,65),25,29,15,11); box(t,27,25,2,14); box(t,36,25,2,14)
        box(c,24,7,18,5); box(t,22,12,22,2); box(t,28,33,8,3)
    elif o.style=='coat':
        poly(c,[(23,26),(28,39),(26,52),(18,50)])
        poly(c,[(39,26),(44,50),(35,52),(35,39)])
        box(t,26,26,2,15); box(t,38,26,2,15)
    elif o.style=='tech':
        box(INK,25,27,15,12)
        for x in (27,37): box(t,x,29,1,8)
        box(t,28,32,9,1); box(c,24,9,18,7); box(t,27,15,14,2)
    elif o.style=='mask':
        box(INK,26,17,14,7); box(t,29,19,10,2)
        box(c,24,9,17,6); box(t,25,28,3,9)
    # Equipment identifies advanced archetypes even across different clothing families.
    if name=='duelist':
        pygame.draw.line(surface,(200,235,240),(reach,28+bob),(reach+5,13+bob),2)
    elif name=='shield':
        poly(INK,[(16,29),(26,26),(29,43),(22,49),(15,42)])
        poly((100,140,160),[(17,30),(24,28),(27,42),(22,46),(17,41)])
        box(t,19,32,5,2)
    elif name=='elite':
        box(t,24,24,6,3); box(t,35,24,7,3); box(INK,25,17,14,5)
    elif name in ('cyber','assassin','echo'):
        box(INK,25,9,17,15); box(t,27,15,14,2)
        if name=='cyber': box((150,175,190),36,26,5,13); box(t,37,29,3,2)
        elif name=='assassin':
            poly(c,[(23,11),(17,29),(26,24)]); box(t,18,25,8,2)
            pygame.draw.line(surface,t,(reach,28+bob),(reach+5,15+bob),1)
        else: box(t,29,29,7,7)
    elif name=='security':
        box(INK,21,23,24,8); box((115,130,145),23,25,20,5)
        box(t,28,29,9,6); box(INK,24,7,19,13); box(t,27,15,14,2)
    elif name=='sniper':
        pygame.draw.line(surface,INK,(38,30+bob),(61,21+bob),5)
        pygame.draw.line(surface,(100,140,155),(38,30+bob),(61,21+bob),3)
        box(t,47,21,4,2); box(t,59,20,3,2)
    # Hands/gloves use the same attack endpoint as the articulated arm.
    if o.style in ('leather','armor','military'):
        surface.fill(t,(reach-2,(22 if attack else 34)+bob,5,4))


def boss_sprite(name,state,frame):
    s=pygame.Surface((64,64),pygame.SRCALPHA)
    bob=frame%2 if state in ('idle','walk','intro','phase') else 0
    stride=(-2,0,2,0)[frame%4] if state=='walk' else 0
    active=state in ('charge','slam','barrage','dash','pulse','orb','laser','strike','wave')
    reach=57 if active and frame in (1,2) else 47
    def box(c,x,y,w,h): s.fill(c,(x,y+bob,w,h))
    def poly(c,points): pygame.draw.polygon(s,c,[(x,y+bob) for x,y in points])
    def limb(points,c,width=6):
        pygame.draw.lines(s,INK,False,[(x,y+bob) for x,y in points],width+2)
        pygame.draw.lines(s,c,False,[(x,y+bob) for x,y in points],width)
    colors={'WARDEN':((65,45,65),(245,165,70)), 'RELAY':((60,90,115),(90,245,235)), 'NULL':((65,55,105),(245,85,190))}
    c,t=colors[name]
    limb([(26,40),(25+stride,49),(22+stride,57)],(45,45,65),7)
    limb([(38,40),(39-stride,49),(43-stride,57)],(65,65,90),7)
    box(INK,16+stride,55,12,5); box(INK,37-stride,55,13,5)
    box(t,18+stride,56,8,2); box(t,39-stride,56,9,2)
    if name=='WARDEN':
        poly(INK,[(22,22),(40,22),(48,51),(36,54),(32,43),(26,53),(13,50)])
        poly(c,[(23,23),(39,23),(47,54),(37,55),(33,39),(28,54),(14,53)])
        box((150,60,75),26,26,12,16)
        poly(t,[(23,23),(29,29),(26,34)]); poly(t,[(39,23),(34,29),(38,34)])
        box((220,155,115),26,10,12,14)
        poly((225,220,190),[(24,13),(24,7),(29,3),(34,7),(39,5),(40,12)])
        box(INK,28,18,10,2); box(t,23,35,4,5)
        limb([(23,26),(17,32),(18,39)],c,7)
        limb([(40,26),(46,28),(reach,25 if active else 38)],c,7)
        box(t,reach-3,22 if active else 35,7,7)
    elif name=='RELAY':
        poly(INK,[(19,23),(43,23),(47,34),(40,43),(23,43),(16,33)])
        poly(c,[(20,25),(42,25),(44,33),(38,40),(25,40),(19,32)])
        box((130,155,165),26,27,12,12); box(t,29,30,6,2)
        box(c,23,7,19,17); box(INK,25,12,17,8); box(t,26,15,14,3)
        box((130,155,165),20,22,7,7); box((130,155,165),39,22,7,7)
        limb([(22,29),(17,35),(21,40)],c,7)
        limb([(41,29),(48,31),(reach,24 if active else 39)],c,7)
        box((130,155,165),reach-4,21 if active else 35,9,9)
        box(t,reach-2,23 if active else 37,5,3)
    else:
        # Wide mechanical shoulders, reactor core, horned head and segmented limbs.
        poly(INK,[(8,21),(23,18),(32,23),(41,18),(56,21),(58,33),(45,37),(40,46),(23,46),(18,37),(6,32)])
        poly(c,[(10,23),(23,20),(32,26),(41,20),(54,23),(55,31),(44,34),(38,43),(25,43),(20,34),(9,31)])
        box((125,115,160),11,24,12,6); box((125,115,160),41,24,12,6)
        poly(t,[(32,27),(39,33),(32,40),(25,33)])
        box((220,245,255),30,31,4,4)
        poly(c,[(24,21),(23,9),(18,3),(27,5),(32,10),(38,5),(46,3),(41,12),(40,22)])
        box(INK,26,12,15,10); box(t,27,15,13,3)
        limb([(16,32),(12,38),(17,44)],(125,115,160),7)
        limb([(48,32),(52,35),(reach,25 if active else 44)],(125,115,160),7)
        box(t,reach-3,23 if active else 41,7,5)
        for x in (20,43): box(t,x,24,2,9)
    if state=='phase':
        box((230,245,255),29,30,6,4)
    if state in ('hurt','knockdown','defeated'):
        if state=='hurt': s.scroll(-2,2)
        else:
            s=pygame.transform.rotate(s,90)
            fallen=pygame.Surface((64,64),pygame.SRCALPHA); fallen.blit(s,(0,18)); s=fallen
    return s
