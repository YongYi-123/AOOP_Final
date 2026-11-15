"""The same proximity target drives the visible prompt and the production E action."""
import pygame
import math
LABELS={'kevin_photo':'Examine Photograph','kevin_note':'Read Notebook','miao_memory':'Talk to Miao Meow',
 'lab_gpu':'Inspect Graphics Card','lab_keyboard':'Inspect Keyboard','lab_terminal':'Inspect Computer',
 'lab_coffee':'Examine Coffee','lab_duck':'Inspect Rubber Duck','lab_button':'Press Red Button',
 'studio_todo':'Check To-Do List','studio_food':'Inspect Food Cabinet','studio_cushion':'Inspect Cat Bed','studio_reminder':'Read Reminder'}

def nearby(session):
    p=session.player;facing=p.x+p.facing[0],p.y+p.facing[1]
    candidates=[(o.id,o.pos,o.data.get('content_id','')) for o in session.puzzles.objects.values()
                if abs(o.x-p.x)+abs(o.y-p.y)<=1]
    candidates.sort(key=lambda o:(abs(o[1][0]-p.x)+abs(o[1][1]-p.y),o[1]!=facing))
    if not candidates:return None
    key,pos,content=candidates[0]
    label='Sit' if key=='sofa' else 'Read Developer Log '+content[-3:] if content.startswith('dev_') else LABELS.get(content,'Inspect')
    return key,label

WALL_NOTES={'dev_001':(43,76),'dev_002':(88,78),'dev_003':(131,75),'dev_004':(272,20),'studio_todo':(289,22),'studio_reminder':(256,25),'dev_006':(209,25),'dev_007':(238,24)}

DISPLAY_POINTS={'photo':(200,71),'note':(238,72),'gpu':(255,75),'keyboard':(188,77),'lab_duck':(215,77),'lab_coffee':(177,78),'lab_button':(66,162),'dev_005':(147,153)}

def object_anchor(session,key):
    from puzzle_maze.studio_layout import FURNITURE
    machine={'work_crt':'cab_cracked','work_back':'cab_open','work_frozen':'cab_frozen','work_prototype':'prototype','terminal':'prototype'}
    if key in machine:
        f=next(f for f in FURNITURE if f.name==machine[key]);return (f.bounds[0]+f.bounds[2]//2,f.bounds[1])
    if key in WALL_NOTES:
        x,y=WALL_NOTES[key];return x+5,y
    if key in DISPLAY_POINTS:
        x,y=DISPLAY_POINTS[key];return x+5,y
    obj=session.puzzles.objects[key];return (obj.x*16+8,obj.y*16+4)

PROMPT='[E/ENTER] INSPECT'
def draw_prompt(renderer,session):
    target=nearby(session)
    if not target:return
    from puzzle_maze.studio_layout import FURNITURE,MIAO_TILE
    x,y=object_anchor(session,target[0]);width=112;height=14
    p=session.player
    obstacles=[pygame.Rect(f.bounds) for f in FURNITURE]
    obstacles.extend((pygame.Rect(p.x*16,p.y*16-3,16,20),pygame.Rect(MIAO_TILE[0]*16,MIAO_TILE[1]*16-4,16,20)))
    options=[pygame.Rect(max(2,min(318-width,xx)),max(2,min(224,yy+round(math.sin(renderer.time*3)))),width,height)
             for yy in (y-18,y+18,110,128,206) for xx in (x-width//2,x+12,x-width-12)]
    def score(box):
        overlap=sum(box.clip(o).width*box.clip(o).height for o in obstacles)
        return (overlap,abs(box.centerx-x)+abs(box.centery-y))
    box=min(options,key=score)
    pygame.draw.rect(renderer.surface,(49,43,38),box)
    pygame.draw.rect(renderer.surface,(193,166,118),box,1)
    renderer.text(PROMPT,box.x+4,box.y+3,(236,211,165),max_width=width-8,small=True)

def physical_objects(surface,session):
    """Each readable item has a small real paper, framed photo or hardware prop."""
    r=pygame.draw
    for obj in session.puzzles.objects.values():
        key=obj.data.get('content_id','');x,y=DISPLAY_POINTS.get(obj.id,(obj.x*16+4,obj.y*16+5))
        if obj.id in WALL_NOTES:
            x,y=WALL_NOTES[obj.id];slant=-1 if obj.id=='dev_004' else 1
            r.polygon(surface,(87,68,50),[(x+1,y+2),(x+11,y+1+slant),(x+12,y+12),(x+2,y+13)])
            r.polygon(surface,(186,166,122),[(x,y),(x+10,y+slant),(x+11,y+10),(x+1,y+11)])
            r.line(surface,(212,191,148),(x+2,y+1),(x+8,y+slant+1),2)
            for yy in (4,7):r.line(surface,(118,104,79),(x+3,y+yy),(x+8,y+yy+slant))
            continue
        if key=='miao_memory' or obj.id.startswith('work_'):continue
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
