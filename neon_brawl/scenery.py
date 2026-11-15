"""Cached architecture and low-cost animation, separate from combat geometry."""
from .ml_lab import paint_ml,lab_motion
from .metro import paint_metro,metro_motion
from .facility import paint_facility,facility_motion

def visual_section(campaign):
    if campaign.stage==2 and campaign.wave==3 and any(e.boss and e.phase>=2 for e in campaign.enemies):return 4
    return campaign.wave

def paint_section(surface,stage,section):
    (paint_ml,paint_metro,paint_facility)[stage](surface,section)

def animate_section(surface,stage,section,camera,time,phase=1,attack=False):
    if stage==0:lab_motion(surface,stage,section,camera,time)
    elif stage==1:metro_motion(surface,section,camera,time)
    else:facility_motion(surface,section,camera,time,phase,attack)
