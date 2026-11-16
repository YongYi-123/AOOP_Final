"""The same proximity target drives the visible prompt and the production E action."""
import pygame
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

# Exactly three paper props: one fault tag, one notebook, and one clipboard.
WALL_NOTES={}
PAPER_NOTES={'work_crt':(54,85),'note':(238,77),'studio_todo':(283,77)}

DISPLAY_POINTS={'photo':(200,74),'note':(238,77),'gpu':(258,81),'keyboard':(215,79),'lab_duck':(251,66),'lab_coffee':(282,76),'lab_button':(59,163),'dev_005':(85,158)}

def object_anchor(session,key):
    from puzzle_maze.studio_layout import FURNITURE
    machine={'work_crt':'cab_cracked','work_back':'cab_open','work_frozen':'cab_frozen','work_space':'cab_space','work_prototype':'prototype','store_tools':'toolbox','store_parts':'crates','store_timebox':'shelf','store_server':'server','store_breadboard':'electronics','store_cables':'wire_spool'}
    if key=='store_aoop':return 112,12
    if key=='power_cabinet':return 280,18
    if key=='terminal':return 220,60
    if key=='project_file':return 270,63
    if key=='repair_log':return 88,159
    if key=='studio_todo':return 286,77
    if key=='miao':return session.studio_companion.x,session.studio_companion.y-18
    if key in machine:
        f=next(f for f in FURNITURE if f.name==machine[key]);return (f.bounds[0]+f.bounds[2]//2,f.bounds[1])
    if key in WALL_NOTES:
        x,y=WALL_NOTES[key];return x+5,y
    if key in DISPLAY_POINTS:
        x,y=DISPLAY_POINTS[key];return x+5,y
    obj=session.puzzles.objects[key];return (obj.x*16+8,obj.y*16+4)

PROMPT='[E/ENTER] INSPECT'
def draw_prompt(renderer,session):
    """The exact Golden Age PromptBubble, bounded to Maze's native canvas."""
    from ui import PromptBubble
    from puzzle_maze.studio_layout import FURNITURE
    if not hasattr(renderer,'studio_prompt'):
        class ObjectPrompt(PromptBubble):
            def place(self,avoid=(),below_first=False):
                # Keep every candidate beside the inspected object. The shared
                # avatar placement can drift across a crowded workshop.
                ax,ay=self.anchor;w,h=self.frames[0].get_size()
                options=[]
                for below in (False,True):
                    for shift in (0,-12,12):
                        rect=pygame.Rect(round(ax-w/2+shift),round(ay+6 if below else ay-h-6),w,h).clamp(self.SAFE)
                        overlap=sum(rect.clip(obstacle).width*rect.clip(obstacle).height for obstacle in avoid)
                        options.append((overlap,abs(rect.centerx-ax)+abs(rect.centery-ay),below,rect))
                _,_,below,rect=min(options,key=lambda option:option[:3])
                self._rect=rect;self._tail_up=below
                return rect,below
        renderer.studio_prompt=ObjectPrompt('INSPECT',key='E/ENTER')
        renderer.studio_prompt.SAFE=pygame.Rect(2,2,316,232)
    prompt=renderer.studio_prompt;target=nearby(session);p=session.player
    anchor=object_anchor(session,target[0]) if target else None
    renderer.studio_prompt_target=target[0] if target else None
    prompt.update(getattr(renderer,'frame_dt',0),anchor,'INSPECT' if target else None)
    obstacles=[pygame.Rect(f.bounds) for f in FURNITURE]
    obstacles.append(pygame.Rect(p.x*16,p.y*16-4,16,20))
    c=session.studio_companion
    obstacles.append(pygame.Rect(round(c.x)-10,round(c.y)-20,20,20))
    renderer.studio_prompt_rect=prompt.draw(renderer.surface,renderer.time,obstacles,below_first=True)

def physical_objects(surface,session):
    """Each readable item has a small real paper, framed photo or hardware prop."""
    r=pygame.draw
    for key,(x,y) in PAPER_NOTES.items():
        if key=='note':
            r.rect(surface,(77,76,61),(x-1,y,12,9));r.rect(surface,(158,150,110),(x+1,y+1,9,6))
            r.line(surface,(81,89,76),(x+2,y+1),(x+2,y+6))
        elif key=='studio_todo':
            r.rect(surface,(73,82,77),(x-1,y-1,9,12));r.rect(surface,(181,174,129),(x,y,7,9))
            r.line(surface,(103,105,83),(x+1,y+3),(x+5,y+3));r.rect(surface,(112,127,113),(x+2,y-1,3,2))
        else:
            r.rect(surface,(174,166,121),(x,y,3,5));surface.fill((112,88,63),(x+1,y+1,1,1))
    for obj in session.puzzles.objects.values():
        key=obj.data.get('content_id','');x,y=DISPLAY_POINTS.get(obj.id,(obj.x*16+4,obj.y*16+5))
        if obj.id in WALL_NOTES:
            x,y=WALL_NOTES[obj.id];slant=-1 if obj.id=='dev_004' else 1
            r.polygon(surface,(87,68,50),[(x+1,y+2),(x+8,y+1+slant),(x+9,y+9),(x+2,y+10)])
            r.polygon(surface,(186,166,122),[(x,y),(x+7,y+slant),(x+8,y+8),(x+1,y+9)])
            r.line(surface,(212,191,148),(x+2,y+1),(x+6,y+slant+1),1)
            for yy in (4,6):r.line(surface,(118,104,79),(x+3,y+yy),(x+6,y+yy+slant))
            continue
        if key=='miao_memory' or obj.id.startswith(('work_','store_')):continue
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
