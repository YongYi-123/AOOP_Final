"""Production studio cinematic: CRT arrival, legal Miao walk and an aged repair memory."""
import pygame
from puzzle_maze.studio_layout import MIAO_ROUTE
LINES=(
 ('MIAO MEOW',('He tested every machine.','Then checked my water.')),
 ('MIAO MEOW',('That little grey light...','It always found its way back.')),
 ('MIAO MEOW',('He left the repair lead in.',)),
 ('MIAO MEOW',('Perhaps he thought someone','might finish this one.')),
 ('MIAO MEOW',('Can we leave it running?','Just a little longer.')),
)
class LabEntrance:
    walk_start=1.2
    walk_end=5.4
    dialogue_at=9.8
    def __init__(self,maze_frame=None,play_sound=None):
        self.maze_frame=maze_frame.copy() if maze_frame is not None else None
        self.time=0.;self.line=0;self.dwell=0.;self.done=False
        from puzzle_maze.studio_dialogue import make_dialogue
        self.dialogue=make_dialogue([(name,' '.join(rows),'gentle') for name,rows in LINES],play_sound)
        self.veil=pygame.Surface((320,240),pygame.SRCALPHA)
        self.fragment=None
    @property
    def ready(self):return self.time>=self.dialogue_at
    @property
    def walking(self):return self.walk_start<=self.time<self.walk_end
    @property
    def reaction(self):return self.walk_end<=self.time<9.2
    @property
    def position(self):
        t=max(0,self.time-self.walk_start)
        for a,b,duration in zip(MIAO_ROUTE,MIAO_ROUTE[1:],(1.4,1.4,1.4)):
            if t<duration:
                q=t/duration;return tuple(a[i]+(b[i]-a[i])*q for i in (0,1))
            t-=duration
        return MIAO_ROUTE[-1]
    def update(self,dt):
        before=self.time;self.time+=max(0,dt)
        elapsed=max(0,self.time-max(before,self.dialogue_at))
        self.dwell+=elapsed
        if elapsed and not self.done:self.dialogue.update(elapsed)
    def advance(self,skip=False):
        if skip:self.done=True
        elif self.ready and self.dwell>=.25:
            self.dialogue.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
            self.line=self.dialogue.index;self.done=self.dialogue.closed;self.dwell=0.
    def memory(self):
        if self.fragment is not None:return self.fragment
        from puzzle_maze.memory_photo import repair_photograph
        self.fragment=repair_photograph();return self.fragment

    def television(self,s):
        """Full-frame temporal interference with a CRT ignition, never a cropped view."""
        import math
        import random
        t=self.time;r=pygame.draw;room=s.copy();rng=random.Random(int(t*32))
        source=self.maze_frame if t<.2 and self.maze_frame is not None else room
        s.blit(source,(0,0))
        # All parts of the scene break into horizontal signal bands.
        strength=max(0,1-t/1.2)
        for y in range(0,240,6):
            shift=round(math.sin(y*.37+t*53)*12*strength)
            s.blit(source,(shift,y),(0,y,320,6))
            if shift>0:s.blit(source,(shift-320,y),(0,y,320,6))
            elif shift<0:s.blit(source,(320+shift,y),(0,y,320,6))
        overlay=pygame.Surface((320,240),pygame.SRCALPHA)
        darkness=int((150+55*math.sin(t*39))*strength)
        overlay.fill((7,15,23,max(0,min(230,darkness))))
        for y in range(0,240,3):
            r.line(overlay,(25,48,57,int(130*strength)),(0,y),(319,y))
        for i in range(180):
            x=rng.randrange(320);y=rng.randrange(240)
            color=(98,169,166,int(155*strength)) if i%3 else (116,96,158,int(155*strength))
            r.line(overlay,color,(x,y),(min(319,x+rng.randrange(1,9)),y))
        # Whole-screen rolling sync bars and receding coordinate frames.
        for i in range(3):
            y=int((t*170+i*80)%240)
            r.rect(overlay,(72,137,145,int(80*strength)),(0,y,320,3))
        for i in range(5):
            scale=((t*1.5+i/5)%1)**1.3
            w=max(4,int(320*scale));h=max(3,int(240*scale))
            r.rect(overlay,(75,139,144,int(120*strength)),(160-w//2,120-h//2,w,h),1)
        s.blit(overlay,(0,0))
        # A tube's horizontal ignition is an accent across the entire width.
        if .2<=t<.55:
            for width,color in ((5,(23,57,66)),(3,(61,111,119)),(1,(184,218,207))):
                r.line(s,color,(0,120),(319,120),width)

    def draw(self,renderer):
        s=renderer.surface;r=pygame.draw;t=self.time;renderer.ui.clear()
        if t<1.2:self.television(s)
        elif t<2.2:
            # Brief scanline lock and spatial echoes settle into the room.
            overlay=pygame.Surface((320,240),pygame.SRCALPHA)
            strength=(2.2-t)
            for y in range(0,240,3):pygame.draw.line(overlay,(10,20,28,int(65*strength)),(0,y),(319,y))
            s.blit(overlay,(0,0))
        if 7.6<=t<9.2:
            self.veil.fill((80,56,40,100));s.blit(self.veil,(0,0));s.blit(self.memory(),(80,37))
            renderer.text('A SMALL MEMORY',24,14,(247,216,158),max_width=272)
        elif 9.2<=t<9.8:
            self.veil.fill((20,29,36,round(170*(1-(t-9.2)/.6))));s.blit(self.veil,(0,0))
        if self.ready and not self.done:
            self.dialogue.draw(s)
        elif 1.2<=t<6.2:
            renderer.text('THE FORGOTTEN WORKSHOP',12,213,(170,180,181),max_width=296,small=True)
        renderer.text('ENTER: Next / SPACE: Skip',12,228,(153,166,170),max_width=296,small=True)
