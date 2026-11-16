"""Production studio cinematic: warm reveal, legal Miao walk, focus and a quiet memory."""
import pygame
from puzzle_maze.studio_layout import MIAO_ROUTE
from puzzle_maze.miao_adapter import guide_frame
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
        # The same portrait, typewriter cadence and panel used by Golden Age.
        import sys
        from pathlib import Path
        host=str(Path(__file__).resolve().parents[1]/'arcade_lobby')
        if host not in sys.path:sys.path.append(host)
        from story_dialogue import StoryDialogue,Line
        from ui import wrap_text,draw_text
        class WorkshopDialogue(StoryDialogue):
            # Native pixels, restrained neon and a compact speech panel.
            def _rows(self):
                return wrap_text(self.line.text,222)[:3]
            def draw(self,surf):
                box=self.box;r=pygame.draw
                r.rect(surf,(16,24,31),box,border_radius=3)
                r.rect(surf,(42,77,83),box.inflate(2,2),1,border_radius=3)
                r.line(surf,(104,182,177),box.topleft,(box.right-1,box.top))
                r.line(surf,(113,99,153),(box.left,box.bottom-1),(box.right-1,box.bottom-1))
                r.polygon(surf,(16,24,31),[(box.left+18,box.bottom-1),(box.left+25,box.bottom+5),(box.left+31,box.bottom-1)])
                r.lines(surf,(79,126,134),False,[(box.left+18,box.bottom),(box.left+25,box.bottom+5),(box.left+31,box.bottom)])
                face=self.speaker.face(self.line.mood,self.context)
                if face is not None:surf.blit(pygame.transform.scale(face,(24,24)),(box.x+5,box.y+17))
                draw_text(surf,self.speaker.name,(box.x+35,box.y+5),(132,193,188))
                remaining=int(self.shown)
                for i,row in enumerate(self._rows()):
                    part=row[:max(0,remaining)];remaining-=len(row)+1
                    if part:draw_text(surf,part,(box.x+35,box.y+18+i*9),(194,207,210))
                if self.done_typing:
                    r.polygon(surf,(123,178,178),[(box.right-9,box.bottom-7),(box.right-4,box.bottom-7),(box.right-7,box.bottom-4)])
        self.dialogue=WorkshopDialogue([Line(name,' '.join(rows),'gentle') for name,rows in LINES],
                                    top=True,play_sound=play_sound)
        self.dialogue.box=pygame.Rect(24,8,272,50)
        self.veil=pygame.Surface((320,240),pygame.SRCALPHA)
        self.focus=pygame.Surface((160,120));self.zoom=pygame.Surface((320,240));self.fragment=None
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
        """A dead tube finds a signal: dot, horizontal beam, vertical sweep, locked image."""
        import math
        t=self.time;r=pygame.draw;room=s.copy()
        if t<.2:
            if self.maze_frame is not None:s.blit(self.maze_frame,(0,0))
            for i in range(7):
                y=20+i*29
                r.line(s,(72,115,122),(20+(i*19)%50,y),(170+i*12,y))
            shade=pygame.Surface((320,240),pygame.SRCALPHA)
            shade.fill((10,17,24,int(255*t/.2)));s.blit(shade,(0,0));return
        s.fill((6,11,17));q=min(1,max(0,(t-.2)/1.0))
        if q<.3:
            half=2+int(145*(q/.3)**1.7)
            for width,color in ((5,(18,45,53)),(3,(63,112,119)),(1,(190,227,214))):
                r.line(s,color,(160-half,120),(160+half,120),width)
            r.circle(s,(224,239,216),(160,120),2)
        else:
            openness=min(1,(q-.3)/.7);height=max(2,int(240*openness**.7))
            image=pygame.transform.scale(room,(320,height));s.blit(image,(0,120-height//2))
            r.line(s,(102,186,184),(4,120-height//2),(315,120-height//2))
            r.line(s,(118,98,157),(4,119+height//2),(315,119+height//2))
            if openness<.9:
                for i in range(5):
                    y=max(0,min(239,120-height//2+i*max(1,height//5)))
                    s.blit(room,(int(math.sin(t*38+i)*5*(1-openness)),y),(0,y,320,2))
        for y in range(0,240,3):r.line(s,(8,18,25),(0,y),(319,y))
        for i in range(24):
            x=(i*73+int(t*93))%318;y=(i*41+int(t*57))%238
            if abs(y-120)<max(3,int(120*q)):s.fill((58,90,94),(x,y,2,1))

    def draw(self,renderer):
        s=renderer.surface;r=pygame.draw;t=self.time;renderer.ui.clear()
        if t<1.2:self.television(s)
        elif t<2.2:
            # Brief scanline lock and spatial echoes settle into the room.
            overlay=pygame.Surface((320,240),pygame.SRCALPHA)
            strength=(2.2-t)
            for y in range(0,240,3):pygame.draw.line(overlay,(10,20,28,int(65*strength)),(0,y),(319,y))
            s.blit(overlay,(0,0))
        if 6.2<=t<9.2:
            q=min(1,(t-6.2)/1.4);q=q*q*(3-2*q)
            crop=pygame.Rect(round(16+4*q),round(92+4*q),160,120)
            self.focus.blit(s,(0,0),crop);pygame.transform.scale(self.focus,(320,240),self.zoom);s.blit(self.zoom,(0,0))
        if 7.6<=t<9.2:
            self.veil.fill((80,56,40,100));s.blit(self.veil,(0,0));s.blit(self.memory(),(80,37))
            renderer.text('A SMALL MEMORY',24,14,(247,216,158),max_width=272)
        elif 9.2<=t<9.8:
            self.veil.fill((20,29,36,round(170*(1-(t-9.2)/.6))));s.blit(self.veil,(0,0))
        if self.ready and not self.done:
            self.dialogue.draw(s)
        elif t<6.2:
            renderer.text('THE FORGOTTEN WORKSHOP',12,213,(170,180,181),max_width=296,small=True)
        renderer.text('ENTER: Next / SPACE: Skip',12,228,(153,166,170),max_width=296,small=True)
