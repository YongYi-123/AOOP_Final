"""Use the Lobby's exact Miao Meow pixels and walk timing, without editing her assets."""
import sys
from pathlib import Path

def guide_frame(walking=False,time=0.,side='right',reaction=False):
    host=str(Path(__file__).resolve().parents[1]/'arcade_lobby')
    if host not in sys.path:sys.path.append(host)
    from miao_meow import miao_frame,facing_frame,WALK_LEGS,WALK_STEP
    frame=int(time/WALK_STEP)%4
    eyes='surprised' if reaction else 'closed' if not walking and int(time*10)%43 in (40,41) else 'open'
    image=miao_frame('stand' if walking else 'sit',eyes,
                     gaze=(0,-1) if reaction else (0,1),tail=(0,1,2,1)[int(time*2)%4],ear=(1 if int(time*8)%71==68 else 2 if int(time*8)%71==69 else 0) if not walking else 0,tilt=not walking and int(time)%11 in (7,8),legs=WALK_LEGS[frame] if walking else 0,level=3)
    return facing_frame(image,side)
