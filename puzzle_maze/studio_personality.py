"""Original cozy clutter, with clear doorway and inspection paths."""
import pygame
from puzzle_maze.pixel_font import render

def shadows(s):
    r=pygame.draw
    for x,y,w,h in ((139,89,172,27),(31,83,98,25),(318,149,65,19),(38,198,45,12),(332,198,45,12)):
        r.polygon(s,(69,46,43),[(x,y),(x+w,y),(x+w+9,y+h),(x+7,y+h)])
    r.line(s,(227,191,132),(17,58),(398,58),2)

def paint(s):
    r=pygame.draw
    # A low bed behind a foreground quilt, visibly raised above the floor.
    r.rect(s,(61,40,43),(165,185,130,48));r.rect(s,(153,100,66),(166,183,128,8))
    r.rect(s,(207,191,150),(170,191,120,32));r.rect(s,(91,123,131),(173,200,114,26))
    for x in range(174,285,12):r.line(s,(115,151,151),(x,201),(x+4,223))
    r.rect(s,(232,215,171),(177,192,35,9),border_radius=3)
    r.polygon(s,(125,155,152),[(227,198),(286,202),(282,222),(251,219)])
    # Mini refrigerator, game cartridges, books and a tiny sleepy plush.
    r.rect(s,(57,52,57),(303,184,24,40));r.rect(s,(167,181,158),(305,185,20,37))
    r.line(s,(71,93,91),(306,201),(324,201));r.rect(s,(67,73,78),(321,206,2,7))
    for i,c in enumerate(((143,84,110),(107,153,147),(212,165,93))):
        r.rect(s,(43,36,46),(112+i*12,183-i*3,11,15));r.rect(s,c,(114+i*12,186-i*3,7,8))
    r.ellipse(s,(184,166,186),(256,187,20,15));r.polygon(s,(184,166,186),[(257,190),(257,183),(264,188),(273,183),(274,192)])
    for x in (261,269):r.line(s,(82,69,92),(x,191),(x+2,191))
    r.rect(s,(224,161,151),(264,195,3,2))
    # Desk snacks and notes avoid the photograph and existing input devices.
    r.ellipse(s,(71,45,42),(287,79,13,5));r.rect(s,(216,189,145),(289,71,9,10))
    r.arc(s,(216,189,145),(295,72,7,6),-1.5,1.5,2)
    r.polygon(s,(201,139,91),[(130,87),(141,87),(139,101),(132,101)])
    r.line(s,(244,218,155),(132,85),(145,79));r.line(s,(244,218,155),(134,85),(147,81))
    r.rect(s,(187,84,106),(305,105,13,7));r.lines(s,(236,193,119),False,[(306,106),(311,108),(316,106)])
    for x,y,c in ((185,43,(233,199,111)),(240,47,(170,196,160)),(317,56,(223,157,152))):
        r.rect(s,c,(x,y,7,8));r.line(s,(96,82,76),(x+2,y+3),(x+5,y+3))
    # A keyboard rack: recognizable individual keys, not anonymous boxes.
    for i in range(3):
        y=65+i*7;r.rect(s,(50,43,52),(356,y,33,6))
        for x in range(359,386,4):r.rect(s,(177-i*15,166,139),(x,y+1,2,2))
        r.rect(s,(205,178,129),(365,y+4,14,1))
    r.rect(s,(58,48,66),(90,20,42,25));r.rect(s,(157,115,148),(92,22,38,21),1)
    s.blit(render('SHIP IT',8,(237,198,117)),(92,25))
    r.polygon(s,(97,173,162),[(102,40),(109,31),(116,40)])
    # A debugging duck and an irresistibly harmless red button.
    r.ellipse(s,(237,193,79),(211,103,11,6));r.circle(s,(246,206,101),(219,101),4)
    r.rect(s,(70,69,65),(219,100,1,1));r.rect(s,(226,129,74),(222,102,3,2))
    r.rect(s,(63,58,65),(298,125,15,9));r.ellipse(s,(210,80,98),(300,123,11,6))
