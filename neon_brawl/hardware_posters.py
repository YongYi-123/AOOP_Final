"""Readable original CPU schematics, cached once rather than redrawn as text walls."""
from functools import lru_cache
import pygame
from .research_art import text
DISPLAY_TITLES=('MIPS / FIVE STAGES','CPU / DATAPATH','REGISTER FILE','CACHE HIERARCHY','ALU / CONTROL UNIT','LOGIC GATES')
@lru_cache(maxsize=6)
def schematic(index):
    index%=6;s=pygame.Surface((174,67));s.fill((20,35,54));r=pygame.draw
    cyan=(132,204,210);amber=(222,179,126);r.rect(s,(111,148,171),s.get_rect(),2)
    def node(label,x,y,w=40):
        r.rect(s,(65,105,128),(x,y,w,13),1);text(s,label,x+3,y+3,cyan)
    text(s,DISPLAY_TITLES[index],6,5,(209,226,218))
    if index==0:
        for i,label in enumerate(('IF','ID','EX','MEM','WB')):
            x=8+i*32;node(label,x,25,25)
            if i<4:r.line(s,amber,(x+25,31),(x+32,31),2)
        text(s,'FETCH DECODE EXECUTE',6,47,amber)
        text(s,'MEMORY ACCESS WRITE BACK',6,57,cyan)
    elif index==1:
        node('REGS',8,22,43);node('ALU',75,22,35);node('RAM',131,22,35)
        r.lines(s,amber,False,[(51,28),(75,28)],2);r.line(s,amber,(110,28),(131,28),2)
        r.lines(s,cyan,False,[(149,35),(149,44),(30,44),(30,35)])
        node('PC',8,48,24);node('CONTROL UNIT',79,48,87)
        r.lines(s,cyan,False,[(32,54),(62,54),(62,20),(128,20),(128,28)])
    elif index==2:
        for i in range(3):node('R'+str(i)+' 000'+str(i%2),10,18+i*12,66)
        r.lines(s,amber,False,[(76,24),(97,24),(97,34),(110,34)],2)
        r.lines(s,cyan,False,[(76,48),(94,48),(94,42),(110,42)],2)
        text(s,'READ A',113,27);text(s,'READ B',113,41)
        text(s,'WRITE -> REGISTER',9,57,amber)
    elif index==3:
        for x,label,h in ((9,'L1',8),(65,'L2',14),(122,'RAM',22)):
            node(label,x,21,42);r.rect(s,(70,123,145),(x+4,39,34,h))
        for x in (51,107):r.line(s,amber,(x,27),(x+14,27),2)
        text(s,'CPU -> L1 -> L2 -> RAM',6,58,amber)
    elif index==4:
        r.polygon(s,(81,130,151),[(63,20),(106,20),(99,45),(71,45),(66,35),(71,29)])
        text(s,'ALU',77,29);r.line(s,amber,(17,24),(63,24),2);r.line(s,cyan,(17,41),(68,41),2)
        text(s,'A',9,21);text(s,'B',9,38);r.line(s,amber,(104,31),(144,31),2)
        text(s,'ZERO',133,41);r.line(s,cyan,(122,31),(122,45))
        text(s,'ADD / AND / OR',7,55,amber)
    else:
        r.lines(s,cyan,False,[(27,23),(44,23),(55,29),(58,36),(55,44),(44,49),(27,49),(27,23)],2)
        r.circle(s,amber,(62,36),3,1)
        for y in (29,43):r.line(s,amber,(10,y),(27,y))
        r.line(s,cyan,(65,36),(87,36));text(s,'NAND',27,55,amber)
        r.lines(s,cyan,False,[(111,24),(127,24),(144,36),(128,48),(111,48),(118,36),(111,24)],2)
        r.lines(s,cyan,False,[(105,24),(112,36),(105,48)],1)
        for y in (28,44):r.line(s,amber,(93,y),(113,y))
        r.line(s,amber,(145,36),(164,36));text(s,'XOR',124,55,amber)
    return s

def paint_hardware_displays(surface,section):
    for i,x in enumerate(range(12,800,200)):surface.blit(schematic((section+i)%6),(x,59))
