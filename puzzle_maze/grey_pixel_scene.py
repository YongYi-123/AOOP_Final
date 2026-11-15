"""Production secret-item presentation, shared by normal play and developer preview."""
import math
import pygame
class GreyPixelReveal:
    duration=5.8
    def __init__(self):self.time=0.
    def update(self,dt):self.time=min(self.duration,self.time+max(0,dt));return self.time>=self.duration
    def draw(self,renderer):
        s=renderer.surface;r=pygame.draw;renderer.ui.clear();t=self.time
        shade=pygame.Surface((320,240),pygame.SRCALPHA);shade.fill((15,23,36,232));s.blit(shade,(0,0))
        # Exposed coordinate grid folds inward before the tiny anomalous pixel resolves.
        for i in range(13):
            x=16+i*24+int(math.sin(t*1.8+i)*min(4,t*2))
            r.line(s,(36,58,69),(x,15),(x,166))
        for y in range(15,167,16):r.line(s,(36,58,69),(16,y),(304,y))
        if t<.9:
            for i in range(5):
                x=int((i*61+t*57)%280)+20;y=47+i*19
                r.line(s,(117,165,163),(x,y),(min(304,x+25),y),1)
        else:
            progress=min(1,(t-.9)/1.3);size=4+int(progress*20)
            rect=pygame.Rect(160-size//2,94-size//2,size,size)
            r.rect(s,(53,69,79),rect.inflate(10,10));r.rect(s,(173,180,187),rect)
            r.line(s,(227,230,223),rect.topleft,rect.topright,2)
            for i in range(12):
                a=i*math.tau/12+t*.35;d=27+progress*19
                x=int(160+math.cos(a)*d);y=int(94+math.sin(a)*d)
                r.rect(s,(122,212,186),(x,y,2,2))
        renderer.text('MAP BOUNDARY ANOMALY' if t<2.2 else 'SECRET ITEM 03 / 03',53,24,(132,218,196),max_width=260)
        if t>=2.2:
            renderer.text('GREY PIXEL',82,145,(246,207,134),max_width=230)
            renderer.text('DEBUG LAYER DISCOVERED.',28,177,(231,230,217),max_width=280)
            renderer.text('ORIGINAL MAP RESTORED.',28,192,(231,230,217),max_width=280)
        else:renderer.text('Something does not belong.',34,183,(215,223,219),max_width=270)
        renderer.text('ENTER / SPACE: Continue',37,221,(154,188,185),max_width=270)
