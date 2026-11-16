"""Native pixel photograph: a repair at night, preserved on yellowing paper."""
import pygame
from puzzle_maze.miao_adapter import guide_frame

def kevin_engineer_frame():
    """Lobby's real small character sheet, dressed for a late repair shift."""
    import sys
    from pathlib import Path
    host=str(Path(__file__).resolve().parents[1]/'arcade_lobby')
    if host not in sys.path:sys.path.append(host)
    from player import PlayerLook,player_sheet
    look=PlayerLook('Kevin / engineering',shirt=(139,164,156),shirt_dark=(87,116,116),
                    beanie=(67,78,77),beanie_dark=(44,59,62),pom=(67,78,77),
                    skin=(231,193,147),blush=(196,148,118),eye=(41,49,49),hair=(55,64,61),
                    outline=(39,48,49),accent=(127,171,162))
    frame=player_sheet(look)['right']['press'][1].copy()
    # An ID badge and a clipped pen sit on the existing work-shirt pixels.
    pygame.draw.rect(frame,(208,205,166),(6,12,2,3))
    frame.fill((72,116,128),(9,11,1,3))
    return frame

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
    r.polygon(s,(128,103,74),[(37,73),(117,73),(128,81),(31,81)])
    r.rect(s,(75,70,60),(32,81,92,3))
    for x in (36,116):r.rect(s,(64,62,53),(x,84,3,7))
    # The same tiny body, head and action pose as the Lobby; no portrait-sized face.
    r.rect(s,(175,159,115),(48,29,29,22))
    for x in range(51,75,4):r.line(s,(158,149,112),(x,32),(x,48))
    for y in range(32,49,4):r.line(s,(158,149,112),(51,y),(74,y))
    r.lines(s,(80,110,102),False,[(53,44),(57,36),(63,36),(65,42),(72,42)],1)
    r.circle(s,(96,115,102),(62,43),2,1)
    person=kevin_engineer_frame()
    tint=pygame.Surface(person.get_size(),pygame.SRCALPHA);tint.fill((235,211,167,255))
    person.blit(tint,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(person,person.get_rect(midbottom=(58,90)))
    # Soldering iron, mat, tiny project board and a spool of test lead.
    r.rect(s,(70,92,80),(72,74,27,7));r.rect(s,(128,144,105),(78,75,10,5))
    r.rect(s,(64,78,69),(81,76,4,3));r.line(s,(190,164,105),(79,79),(87,79))
    r.line(s,(145,137,105),(65,79),(75,76));r.line(s,(84,91,77),(65,79),(68,78),2)
    r.circle(s,(147,139,104),(105,77),3,1)
    # Open arcade prototype and loose repair cable.
    from puzzle_maze.workshop_art import cabinet
    machine=pygame.transform.scale(cabinet('cab_open'),(27,47))
    tint=pygame.Surface(machine.get_size(),pygame.SRCALPHA);tint.fill((235,205,153,255))
    machine.blit(tint,(0,0),special_flags=pygame.BLEND_RGBA_MULT);s.blit(machine,(116,42))
    r.lines(s,(178,146,93),False,[(88,77),(101,80),(108,69),(120,67)],1)
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
