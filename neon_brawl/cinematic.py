"""Eleven-second cinematic with separate picture, logo, subtitle and prompt zones."""
import math
import pygame
from .art import background, sprite

class Cinematic:
    duration=11.
    def __init__(self,font):
        self.font=font
        self.last_layout=[]

    @staticmethod
    def zones(size):
        w,h=size
        return {'header':pygame.Rect(w*.04,h*.05,w*.92,h*.09),
                'visual':pygame.Rect(w*.03,h*.17,w*.94,h*.52),
                'logo':pygame.Rect(w*.08,h*.20,w*.84,h*.19),
                'subtitle':pygame.Rect(w*.04,h*.73,w*.92,h*.14),
                'prompt':pygame.Rect(w*.04,h*.93,w*.92,h*.04)}

    def draw(self,s,time):
        w,h=s.get_size(); zones=self.zones(s.get_size()); visual=zones['visual']
        self.last_layout=[]
        s.fill((7,8,21))
        def text(label,zone,y=None,color=(215,230,240),scale=1):
            image=self.font.render(label,color,scale=scale)
            rect=image.get_rect(center=(zone.centerx,zone.centery if y is None else y))
            s.blit(image,rect); self.last_layout.append(('text',label,rect.copy()))
        def actor(name,x,feet,state='walk',dark=False):
            image=sprite(name,state,int(time*8)%4,1 if name=='REX' else -1)
            if dark:
                image=image.copy(); image.fill((30,35,60,255),special_flags=pygame.BLEND_RGBA_MULT)
            rect=image.get_rect(midbottom=(int(x),int(feet)))
            s.blit(image,rect); self.last_layout.append(('actor',name,rect.copy()))
        if time<.9:
            extent=math.sin(min(1,time/.9)*math.pi/2)*w*.43
            pygame.draw.line(s,(180,250,250),(int(w/2-extent),h//2),(int(w/2+extent),h//2),1+int(time*3))
            text('LINKING TO RESEARCH COMPLEX',zones['subtitle'])
        else:
            old=s.get_clip(); s.set_clip(visual)
            pan=int(time*13)%400
            s.blit(background(0,0),(-pan,0))
            s.blit(background(0,1),(int(-time*9)%200-200,0))
            s.fill((21,23,40),(visual.x,visual.bottom-30,visual.w,30))
            pygame.draw.line(s,(90,55,105),(visual.left,visual.bottom-29),(visual.right,visual.bottom-29))
            for i in range(8):
                x=int((i*71-time*40)%w); y=int((i*43+time*120)%max(1,visual.h))+visual.top
                pygame.draw.line(s,(65,80,115),(x,y),(x,y+3))
            if 2.8<=time<6.5:
                for i,name in enumerate(('grunt','runner','bruiser')):
                    actor(name,w*(.57+i*.13),visual.bottom-4-i%2*8,dark=True)
            if 4.4<=time<7.3:
                fraction=min(1,(time-4.4)/1.3)
                actor('REX',w*(.12+.16*fraction),visual.bottom-2)
            elif time>=7.3:
                actor('REX',w*.5,visual.bottom-2,'victory' if time>8.8 else 'idle')
            if 6.3<=time<7.3:
                # Short, spatially constrained interference leaves subtitles untouched.
                for i in range(5):
                    y=visual.top+int((i*29+time*70)%visual.h)
                    s.fill((85,55,105),(visual.left,y,visual.w,1))
            if time<2.1:
                veil=pygame.Surface(visual.size); veil.fill((5,7,18)); veil.set_alpha(int(max(0,1-(time-.9)/1.2)*255))
                s.blit(veil,visual)
            s.set_clip(old)
            if time<2.8:
                header='RESEARCH COMPLEX // OFFLINE'; lines=('THREE DEPARTMENTS. ONE BROKEN SYSTEM.','ONE SIGNAL HAS TAKEN CONTROL.')
            elif time<4.4:
                header='LABORATORIES UNDER LOCKDOWN'; lines=('THE WARDEN HAS LOCKED THE ML LAB.','THE PHANTOM GUARDS THE HARDWARE WING.')
            elif time<6.3:
                header='ONE LAST TRANSMISSION'; lines=('REX: TIME TO REBOOT THIS PLACE.','NOVA AND BRUNO ARE ALREADY ON THE WAY.')
            elif time<7.3:
                header='SIGNAL // INTERCEPTED'; lines=('UNKNOWN: YOU CANNOT SILENCE THE CORE.','REX: WATCH US.')
            else:
                header='BREAK THE SIGNAL'; lines=('THREE FIGHTERS. THREE DEPARTMENTS.','THE COMPLEX IS WAITING FOR YOU.')
                # Logo stays inside its own box; no incoming text flies over dialogue.
                progress=min(1,(time-7.3)/.6)
                color=(int(100+155*progress),int(65+35*progress),int(130+55*progress))
                plate=zones['logo'].inflate(0,4)
                s.fill((10,10,27),plate)
                pygame.draw.rect(s,(70,65,100),plate,1)
                text('NEON BRAWL',zones['logo'],color=color,scale=3)
                pygame.draw.line(s,(80,220,235),(zones['logo'].centerx-int(110*progress),zones['logo'].bottom-4),
                                 (zones['logo'].centerx+int(110*progress),zones['logo'].bottom-4),1)
            text(header,zones['header'],color=(90,225,235))
            s.fill((11,12,28),zones['subtitle'].inflate(0,6))
            text(lines[0],zones['subtitle'],zones['subtitle'].centery-8)
            text(lines[1],zones['subtitle'],zones['subtitle'].centery+8,color=(180,190,215))
        text('ENTER / SPACE / ESC : SKIP',zones['prompt'],color=(145,160,185))
