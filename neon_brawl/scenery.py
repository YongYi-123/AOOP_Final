"""Cached architecture and low-cost animation, separate from combat geometry."""
from .ml_lab import paint_ml,lab_motion
from .architecture_lab import paint_architecture,architecture_motion
from .oop_core import paint_oop,oop_motion

def visual_section(campaign):
    if campaign.stage==2 and campaign.wave==3 and any(e.boss and e.phase>=2 for e in campaign.enemies):return 4
    return campaign.wave

def paint_section(surface,stage,section):
    (paint_ml,paint_architecture,paint_oop)[stage](surface,section)

def animate_section(surface,stage,section,camera,time,phase=1,attack=False):
    if stage==0:lab_motion(surface,stage,section,camera,time)
    elif stage==1:architecture_motion(surface,section,camera,time)
    else:oop_motion(surface,section,camera,time,phase,attack)
