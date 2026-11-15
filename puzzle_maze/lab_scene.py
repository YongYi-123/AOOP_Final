"""Non-blocking doorway entrance and paced, skippable memory sequence."""
import math
import pygame
from puzzle_maze.miao_adapter import guide_frame

LINES=(
 ('MIAO MEOW',('All these computers...','Why does this place feel','so familiar?')),
 ('MIAO MEOW',('Someone used to work here','every night.')),
 ('MIAO MEOW',('Kevin...','Was this your room?')),
 ('SYSTEM',('ARCHIVED DEVELOPMENT','RECORD DETECTED.')),
 ('MIAO MEOW',("I think... there's something","we're supposed to remember.")),
)
class LabEntrance:
    def __init__(self):self.time=0.;self.line=0;self.dwell=0.;self.done=False
    @property
    def ready(self):return self.time>=5.2
    @property
    def position(self):
        t=self.time
        points=((24,120),(24,152),(104,152),(136,136))
        lengths=(.9,2.2,1.1)
        for a,b,duration in zip(points,points[1:],lengths):
            if t<duration:
                q=max(0,t/duration);return tuple(a[i]+(b[i]-a[i])*q for i in (0,1))
            t-=duration
        return points[-1]
    def update(self,dt):
        self.time+=max(0,dt)
        if self.ready:self.dwell+=max(0,dt)
    def advance(self,skip=False):
        if skip:self.done=True
        elif self.ready and self.dwell>=.25:
            self.line+=1;self.dwell=0.
            if self.line>=len(LINES):self.done=True
    def draw(self,renderer):
        x,y=self.position;cx,cy=renderer.camera.x,renderer.camera.y
        image=guide_frame(self.time<4.2,self.time,reaction=4.2<=self.time<5.2)
        renderer.surface.blit(image,image.get_rect(midbottom=(round(x-cx),round(y-cy))))
        # Dedicated lower strip: never lay subtitles over the workbench or walking cat.
        renderer.ui.clear()
        pygame.draw.rect(renderer.surface,(27,25,31),(0,180,320,60))
        if self.ready and not self.done:
            name,lines=LINES[self.line]
            renderer.text(name,12,183,(239,197,126),max_width=296)
            for i,line in enumerate(lines):renderer.text(line,12,196+i*11,(234,226,202),max_width=296)
        else:renderer.text("KEVIN'S HIDDEN ENGINEERING LAB",12,189,(239,197,126),max_width=296)
        renderer.text('ENTER: Next / SPACE: Skip',12,229,(154,191,174),max_width=296)
