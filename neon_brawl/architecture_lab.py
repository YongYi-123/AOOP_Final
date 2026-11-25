"""The hardware department, sharing the facility shell with distinct copper-blue benches."""
import pygame
from .research_art import shell,desk,crt,keyboard,server,sign
from .hardware_posters import paint_hardware_displays
from .ml_lab import lab_motion
LABELS=('INSTRUCTION FETCH / DECODE','DATAPATH WORKSHOP','CACHE AND MEMORY','PIPELINE CONTROL')
def paint_architecture(s,section):
    shell(s,1,section);r=pygame.draw
    paint_hardware_displays(s,section)
    for i,x in enumerate(range(0,800,200)):
        desk(s,x+14,139,170)
        if i in (0,3):
            from .lab_staff import MESSAGES
            sign(s,tuple(MESSAGES.values())[(i+section)%4],(x+12,41,174,15),(220,182,139))
        # Socket, traces, expansion slots and socketed RAM on a real-looking board.
        r.rect(s,(31,72,76),(x+23,129,46,12));r.rect(s,(172,180,157),(x+31,131,11,8))
        for xx in (x+49,x+56,x+63):r.rect(s,(185,158,94),(xx,131,3,8))
        for yy in (131,137):r.line(s,(90,145,126),(x+25,yy),(x+29,yy))
        keyboard(s,x+88,139);crt(s,x+139,117,mini=True)
        if section in (0,3):
            r.rect(s,(72,96,117),(x+75,129,12,9));r.rect(s,(215,155,94),(x+78,132,6,3))
        else:
            server(s,x+147,144,27,23,section==2 and i%2==0)
        # Old oscilloscope and soldering iron identify the bench as hardware research.
        r.rect(s,(152,164,150),(x+104,126,24,13));r.rect(s,(23,52,63),(x+107,128,14,7))
        r.lines(s,(123,214,169),False,[(x+108,133),(x+112,130),(x+116,134),(x+120,129)])
        r.line(s,(219,173,103),(x+16,135),(x+24,128),2)
    sign(s,LABELS[section],(212,41,250,15),(188,203,211))

def architecture_motion(s,section,camera,time):
    lab_motion(s,1,section,camera,time)
    # A clock pulse follows the actual pipeline direction on a dedicated upper bus.
    x=int((time*29-camera*.55)%800)
    if x<400:s.fill((218,173,106),(x,56,5,1))
