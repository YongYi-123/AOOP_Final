"""Native pixel photograph: a repair at night, preserved on yellowing paper."""
import pygame
from puzzle_maze.miao_adapter import guide_frame

def repair_photograph():
    s=pygame.Surface((160,108));r=pygame.draw
    paper=(210,185,133);ink=(86,70,56)
    s.fill((108,83,57));r.rect(s,paper,(2,2,156,104))
    r.rect(s,(163,137,94),(8,7,144,87));r.rect(s,(100,91,73),(10,9,140,83))
    # Shelves, obsolete parts and a warm pool of light behind the repair desk.
    r.rect(s,(132,114,81),(10,10,140,40))
    for x in (15,89):
        r.rect(s,(78,74,63),(x,17,30,3))
        for dx in (2,12,22):r.rect(s,(104+dx,100,75),(x+dx,10,6,7))
    r.polygon(s,(164,137,88),[(76,19),(103,19),(126,68),(51,68)])
    r.line(s,(75,73,62),(89,13),(89,20),2)
    r.polygon(s,(66,68,60),[(81,14),(97,14),(102,22),(76,22)])
    r.line(s,(214,189,127),(80,22),(99,22))
    for y in (58,71,84):r.line(s,(115,100,76),(10,y),(150,y))
    r.polygon(s,(128,103,74),[(33,59),(117,59),(128,70),(25,70)])
    r.rect(s,(75,70,60),(28,70,96,4))
    for x in (32,116):r.rect(s,(64,62,53),(x,74,4,16))
    # Three-quarter portrait: tousled hair, glasses, face planes, sleeve seams and hands.
    r.rect(s,(61,61,56),(46,34,17,19));r.rect(s,(171,136,98),(48,33,14,17))
    r.rect(s,(190,155,113),(50,36,11,12));r.rect(s,(151,114,85),(48,40,3,8))
    r.rect(s,(180,143,103),(53,47,5,6));r.line(s,(219,181,131),(60,39),(62,43))
    r.rect(s,(57,60,55),(46,30,17,7));r.rect(s,(70,70,60),(44,33,6,11))
    r.polygon(s,(68,69,58),[(44,33),(49,28),(54,30),(60,28),(65,34),(60,37),(53,34),(48,38)])
    r.line(s,(121,111,85),(49,31),(55,31));r.line(s,(112,103,79),(59,32),(62,34))
    for x in (52,58):
        r.rect(s,(77,76,64),(x,39,5,4),1);s.fill((42,48,46),(x+2,40,1,1))
    r.line(s,(77,76,64),(56,40),(58,40));r.line(s,(126,95,74),(57,47),(60,47))
    r.polygon(s,(83,102,89),[(46,51),(55,53),(61,50),(69,58),(65,72),(37,72),(39,57)])
    r.line(s,(133,143,112),(46,53),(43,68));r.line(s,(57,79,73),(54,56),(56,70))
    r.polygon(s,(112,126,100),[(62,52),(68,55),(75,63),(70,66),(61,60)])
    r.polygon(s,(183,145,103),[(72,61),(80,58),(88,60),(86,64),(75,66)])
    r.line(s,(219,181,130),(79,60),(86,61));r.line(s,(130,103,78),(81,63),(86,63))
    r.polygon(s,(83,83,71),[(40,72),(64,72),(69,90),(37,90)])
    r.line(s,(52,62,58),(53,75),(55,90))
    # Open arcade prototype and loose repair cable.
    from puzzle_maze.workshop_art import cabinet
    machine=pygame.transform.scale(cabinet('cab_open'),(27,47))
    tint=pygame.Surface(machine.get_size(),pygame.SRCALPHA);tint.fill((235,205,153,255))
    machine.blit(tint,(0,0),special_flags=pygame.BLEND_RGBA_MULT);s.blit(machine,(116,33))
    r.lines(s,(178,146,93),False,[(88,62),(102,65),(105,56),(120,58)],1)
    r.rect(s,(66,82,70),(83,60,18,8));r.rect(s,(144,148,104),(87,62,5,4),1)
    cat=guide_frame(False,4.1);cat=cat.copy()
    tint=pygame.Surface(cat.get_size(),pygame.SRCALPHA);tint.fill((215,194,157,255))
    cat.blit(tint,(0,0),special_flags=pygame.BLEND_RGBA_MULT);s.blit(cat,(88,77))
    # Vignetting, silvering, dust, scratches and a bent corner live in the paper itself.
    for x in range(10,150):
        if x%3:r.line(s,(111,96,72),(x,9),(x,10))
        if x%5==0:s.fill((112,96,73),(x,91,1,1))
    for i in range(85):
        x=11+(i*47)%138;y=10+(i*29)%81
        if i%5==0:s.fill((186,161,113),(x,y,1,1))
    r.line(s,(181,157,110),(22,12),(23,34));r.line(s,(171,147,104),(135,63),(133,88))
    r.lines(s,(184,157,110),False,[(3,83),(6,78),(8,83),(11,81)],1)
    r.polygon(s,(157,132,93),[(145,2),(157,2),(157,15)])
    r.line(s,(228,204,153),(145,2),(157,15))
    for x in (18,23,28,33,38,43):r.line(s,ink,(x,99),(x+3,98))
    r.line(s,(138,114,80),(116,99),(142,99))
    return s
