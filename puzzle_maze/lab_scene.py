"""Production studio cinematic: warm reveal, legal Miao walk, focus and a quiet memory."""
import pygame
from puzzle_maze.studio_layout import MIAO_ROUTE
from puzzle_maze.miao_adapter import guide_frame
LINES=(
 ('MIAO MEOW',('He wrote down my dinner...','right beside the hard parts.')),
 ('MIAO MEOW',('I remember that fan.','He made it quieter for me.')),
 ('MIAO MEOW',('He never called that work.',)),
 ('MIAO MEOW',('Just... something to fix','before I went to sleep.')),
 ('MIAO MEOW',('Can we leave the blanket','where he put it?')),
)
class LabEntrance:
    walk_start=1.2
    walk_end=5.4
    dialogue_at=9.8
    def __init__(self):
        self.time=0.;self.line=0;self.dwell=0.;self.done=False
        self.veil=pygame.Surface((320,180),pygame.SRCALPHA)
        self.focus=pygame.Surface((160,90));self.zoom=pygame.Surface((320,180));self.fragment=None
    @property
    def ready(self):return self.time>=self.dialogue_at
    @property
    def walking(self):return self.walk_start<=self.time<self.walk_end
    @property
    def reaction(self):return self.walk_end<=self.time<9.2
    @property
    def position(self):
        t=max(0,self.time-self.walk_start)
        for a,b,duration in zip(MIAO_ROUTE,MIAO_ROUTE[1:],(1.3,.5,2.4)):
            if t<duration:
                q=t/duration;return tuple(a[i]+(b[i]-a[i])*q for i in (0,1))
            t-=duration
        return MIAO_ROUTE[-1]
    def update(self,dt):
        before=self.time;self.time+=max(0,dt)
        self.dwell+=max(0,self.time-max(before,self.dialogue_at))
    def advance(self,skip=False):
        if skip:self.done=True
        elif self.ready and self.dwell>=.25:
            self.line+=1;self.dwell=0.
            if self.line>=len(LINES):self.done=True
    def memory(self):
        if self.fragment is not None:return self.fragment
        s=pygame.Surface((132,88));r=pygame.draw;s.fill((237,208,157))
        r.rect(s,(139,96,66),s.get_rect(),3);r.rect(s,(247,227,184),(5,5,122,78),1)
        r.rect(s,(203,163,111),(7,8,118,38));r.rect(s,(170,120,79),(7,46,118,35))
        for y in (55,65,75):r.line(s,(195,145,94),(8,y),(124,y))
        # An everyday fragment: a hand turns down the fan, a cat sleeps nearby.
        r.rect(s,(165,155,125),(79,21,20,34));r.rect(s,(63,87,85),(82,25,14,24))
        r.circle(s,(157,177,152),(89,34),6,1);r.rect(s,(222,198,136),(85,47,7,2))
        r.rect(s,(209,174,132),(29,30,15,14));r.rect(s,(77,64,62),(28,27,16,7))
        for x in (33,39):r.rect(s,(99,78,66),(x,35,1,1))
        r.line(s,(164,112,92),(35,40),(38,40))
        r.polygon(s,(114,153,132),[(29,43),(42,43),(50,65),(22,65)])
        r.line(s,(197,161,126),(42,47),(77,50),5);r.rect(s,(234,195,146),(75,47,9,5))
        r.ellipse(s,(213,157,149),(66,62,44,15));r.ellipse(s,(247,221,177),(70,63,36,9))
        cat=guide_frame(False,4.1);s.blit(cat,(77,52))
        r.rect(s,(159,183,149),(85,67,17,6));r.line(s,(228,230,183),(87,69),(99,69))
        self.fragment=s;return s
    def draw(self,renderer):
        s=renderer.surface;r=pygame.draw;t=self.time;renderer.ui.clear()
        if 6.2<=t<9.2:
            q=min(1,(t-6.2)/1.4);q=q*q*(3-2*q)
            crop=pygame.Rect(round(88+16*q),round(24+8*q),160,90)
            self.focus.blit(s,(0,0),crop);pygame.transform.scale(self.focus,(320,180),self.zoom);s.blit(self.zoom,(0,0))
        if 7.6<=t<9.2:
            self.veil.fill((80,56,40,100));s.blit(self.veil,(0,0));s.blit(self.memory(),(94,40))
            renderer.text('A SMALL MEMORY',24,14,(247,216,158),max_width=272)
        elif t<1.2 or 9.2<=t<9.8:
            progress=t/1.2 if t<1.2 else (t-9.2)/.6
            self.veil.fill((63,45,34,round(235*(1-progress))));s.blit(self.veil,(0,0))
        r.rect(s,(67,51,43),(0,180,320,60));r.line(s,(207,169,112),(0,180),(320,180))
        if self.ready and not self.done:
            name,lines=LINES[self.line];renderer.text(name,12,184,(245,207,143),max_width=296)
            for i,line in enumerate(lines):renderer.text(line,12,198+i*12,(248,229,194),max_width=296)
        elif 7.6<=t<9.2:
            renderer.text('THE QUIET FAN',12,189,(248,215,158),max_width=296)
            renderer.text('He always turned it down.',12,205,(228,204,166),max_width=296)
        else:
            renderer.text("KEVIN'S COZY STUDIO",12,189,(248,215,158),max_width=296)
            renderer.text('Some things were worth keeping.',12,205,(228,204,166),max_width=296)
        renderer.text('ENTER: Next / SPACE: Skip',12,229,(212,184,140),max_width=296)
