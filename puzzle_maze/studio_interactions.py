"""The same proximity target drives the visible prompt and the production E action."""
import pygame
SOFA_TILE=(4,10)
LABELS={'kevin_photo':'Examine Photograph','kevin_note':'Read Notebook','miao_memory':'Talk to Miao Meow',
 'lab_gpu':'Inspect Graphics Card','lab_keyboard':'Inspect Keyboard','lab_terminal':'Inspect Computer',
 'lab_coffee':'Examine Coffee','lab_duck':'Inspect Rubber Duck','lab_button':'Press Red Button',
 'studio_todo':'Check To-Do List','studio_food':'Inspect Food Cabinet','studio_cushion':'Inspect Cat Bed','studio_reminder':'Read Reminder'}

def nearby(session):
    p=session.player;facing=p.x+p.facing[0],p.y+p.facing[1]
    candidates=[(o.id,o.pos,o.data.get('content_id','')) for o in session.puzzles.objects.values()
                if abs(o.x-p.x)+abs(o.y-p.y)<=1]
    if abs(p.x-SOFA_TILE[0])+abs(p.y-SOFA_TILE[1])<=1:candidates.append(('sofa',SOFA_TILE,''))
    candidates.sort(key=lambda o:(o[1]!=facing,abs(o[1][0]-p.x)+abs(o[1][1]-p.y)))
    if not candidates:return None
    key,pos,content=candidates[0]
    label='Sit' if key=='sofa' else 'Read Developer Log '+content[-3:] if content.startswith('dev_') else LABELS.get(content,'Inspect')
    return key,label

class SofaSeat:
    """A local, disposable pose; logical feet stay at the legal approach tile."""
    def __init__(self,visual):self.start=(visual[0]*16+8,visual[1]*16+16);self.time=0.;self.leaving=False
    def update(self,dt):
        self.time=max(0,self.time-dt) if self.leaving else min(.4,self.time+dt)
        return self.leaving and self.time<=0
    @property
    def position(self):
        q=self.time/.4;q=q*q*(3-2*q)
        return tuple(a+(b-a)*q for a,b in zip(self.start,(64,170)))

def physical_objects(surface,session):
    """Each readable item has a small real paper, framed photo or hardware prop."""
    r=pygame.draw
    for obj in session.puzzles.objects.values():
        key=obj.data.get('content_id','');x,y=obj.x*16+4,obj.y*16+5
        if key=='miao_memory':continue
        if key=='kevin_photo':
            r.rect(surface,(101,69,49),(x,y,10,11));r.rect(surface,(196,173,130),(x+1,y+1,8,9))
            r.rect(surface,(106,136,119),(x+3,y+3,3,5));r.rect(surface,(80,80,105),(x+6,y+5,2,3))
        elif key in ('lab_terminal','lab_keyboard','lab_gpu','lab_button','lab_duck','lab_coffee','studio_food','studio_cushion'): 
            if key=='lab_gpu':
                r.rect(surface,(68,103,77),(x,y+2,11,6));r.circle(surface,(41,55,50),(x+4,y+5),2);r.line(surface,(179,145,82),(x+1,y+8),(x+9,y+8))
            elif key=='lab_keyboard':
                r.polygon(surface,(172,155,122),[(x,y+4),(x+9,y+4),(x+11,y+9),(x-1,y+9)])
                for xx in range(x+1,x+9,2):r.line(surface,(82,78,65),(xx,y+5),(xx,y+7))
            elif key=='lab_button':r.circle(surface,(99,80,60),(x+5,y+7),4);r.circle(surface,(174,81,67),(x+5,y+6),2)
            elif key=='lab_duck':r.ellipse(surface,(199,157,75),(x,y+5,9,4));r.circle(surface,(221,177,88),(x+7,y+3),3);surface.fill((50,47,40),(x+8,y+2,1,1))
            elif key=='lab_coffee':r.rect(surface,(173,150,114),(x+2,y+3,6,7));r.rect(surface,(75,57,44),(x+3,y+3,4,2))
        else:
            # Small bound notebook / pinned card with an actual spine and ruled paper.
            r.rect(surface,(71,53,42),(x,y+2,10,10));r.rect(surface,(183,162,122),(x+1,y+1,9,9))
            r.line(surface,(133,91,66),(x+1,y+1),(x+1,y+9))
            for yy in (4,6,8):r.line(surface,(114,101,80),(x+3,y+yy),(x+7,y+yy))
