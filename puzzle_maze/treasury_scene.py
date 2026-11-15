"""Brief presentation-only vault opening; never grants or changes rewards."""
import pygame
class TreasuryReveal:
    duration=1.8
    def __init__(self):self.time=0.
    def update(self,dt):self.time=min(self.duration,self.time+max(0,dt));return self.time>=self.duration
    def draw(self,renderer):
        s=renderer.surface;r=pygame.draw;renderer.ui.clear()
        progress=min(1,self.time/1.4);width=int(160*(1-progress))
        for x in (0,320-width):
            r.rect(s,(90,58,44),(x,0,width,184))
            if width>3:
                r.rect(s,(222,173,82),(x,0,width,184),2)
                for y in range(20,180,24):r.line(s,(159,116,65),(x+3,y),(x+width-3,y),2)
        r.rect(s,(25,21,32),(0,184,320,56))
        renderer.text('THE ROYAL TREASURY',18,190,(249,211,130),max_width=284)
        renderer.text('Your journey has earned this.',18,207,(230,220,197),max_width=284)
        renderer.text('ENTER / SPACE: Continue',18,225,(149,194,177),max_width=284)
