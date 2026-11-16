"""One source for the production studio's placement, contact footprints and story route."""
from dataclasses import dataclass
SIZE=(320,240)
ENTRY=(6,8)
MIAO_TILE=(10,7)
MIAO_ROUTE=((24.,128.),(72.,128.),(120.,128.),(168.,128.))
@dataclass(frozen=True)
class Furniture:
    name:str
    bounds:tuple
    footprint:tuple
FURNITURE=(
 Furniture('cab_cracked',(36,55,24,40),(38,82,20,14)),
 Furniture('cab_open',(82,55,24,40),(84,82,20,14)),
 Furniture('cab_frozen',(128,55,24,40),(130,82,20,14)),
 Furniture('cab_space',(163,55,24,40),(165,82,20,14)),
 Furniture('desk',(194,52,100,48),(196,78,96,22)),
 Furniture('prototype',(36,145,28,43),(38,174,24,13)),
 Furniture('cart',(73,157,28,26),(75,172,24,12)),
 Furniture('server',(276,101,22,39),(278,126,18,14)),
 Furniture('food',(275,151,22,19),(276,157,20,13)),
 Furniture('toolbox',(20,188,30,29),(22,206,26,12)),
 Furniture('crates',(55,192,32,25),(57,206,28,12)),
 Furniture('spare_crt',(89,193,25,25),(91,206,21,12)),
 Furniture('electronics',(171,205,35,25),(173,218,31,12)),
 Furniture('wire_spool',(213,207,28,22),(215,218,24,12)),
 Furniture('shelf',(270,203,30,29),(272,218,26,14)),
 Furniture('cushion',(269,181,28,15),(272,189,22,7)),
)
POSITIONS={'photo':(12,5),'note':(14,5),'miao':MIAO_TILE,'gpu':(15,5),'keyboard':(13,5),'terminal':(12,4),
 'lab_duck':(15,4),'lab_coffee':(18,4),
 'studio_todo':(18,5),'studio_food':(17,9),'studio_cushion':(17,11),
 'store_aoop':(6,3),'store_breadboard':(11,13),'store_cables':(14,13),
 'store_tools':(2,12),'store_parts':(4,12),'store_timebox':(17,13),'store_server':(17,7),
 'repair_log':(5,11),'project_file':(16,5),
 'power_cabinet':(17,3),'work_crt':(3,5),'work_back':(5,5),'work_frozen':(8,5),
 'work_space':(10,5),'work_prototype':(2,10)}
CONTENT_IDS={**{key:key for key in POSITIONS},'photo':'kevin_photo','note':'kevin_note','miao':'miao_memory',
             'gpu':'lab_gpu','keyboard':'lab_keyboard','terminal':'lab_terminal'}

def contact_blocked(px,py,footprints,width=10,height=6):
    left,right=px-width/2,px+width/2;top,bottom=py-height,py
    return any(left<x+w and right>x and top<y+h and bottom>y for x,y,w,h in footprints)

def tile_blocked(x,y,footprints=None):
    return contact_blocked(x*16+8,y*16+16,footprints if footprints is not None else [f.footprint for f in FURNITURE])

def configure(room):
    from puzzle_maze.build_dungeon import obj
    room.update(name="The Forgotten Arcade Workshop",spawn=list(ENTRY),studio_revision=9,decorations=[],
                architecture='studio',hint='The western door leads back. There is no hurry here.',
                tiles=['#'*20]*3+['#'+'.'*18+'#' for _ in range(11)]+['#'*20],
                solid_footprints=[list(f.footprint) for f in FURNITURE])
    room['objects']=[obj('mystery_scroll',key,position,content_id=CONTENT_IDS[key],optional=key not in ('photo','note','miao'))
                     for key,position in POSITIONS.items()]


def approach(room,position):
    """Return a reachable inspection neighbor and facing using the production footprints."""
    x,y=position
    occupied={tuple(o['pos']) for o in room['objects']}
    for dx,dy in ((0,1),(-1,0),(1,0),(0,-1)):
        px,py=x+dx,y+dy
        rows=room['tiles']
        if 0<=py<len(rows) and 0<=px<len(rows[0]) and rows[py][px]!='#' and (px,py) not in occupied and not tile_blocked(px,py,room['solid_footprints']):
            return (px,py),(-dx,-dy)
    raise ValueError('No studio inspection approach: '+str(position))

def safe_position(pos,room):
    """Relocate a valid old studio position only; malformed saves still fail validation."""
    from collections import deque
    if not isinstance(pos,list) or len(pos)!=2 or any(type(v) is not int for v in pos) or not (0<pos[0]<25 and 0<pos[1]<15):return pos
    start=(max(1,min(18,pos[0])),max(3,min(13,pos[1])))
    q=deque([start]);seen={start}
    while q:
        x,y=q.popleft()
        if room['tiles'][y][x]!='#' and not tile_blocked(x,y,room['solid_footprints']):return [x,y]
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            p=x+dx,y+dy
            if 1<=p[0]<=18 and 3<=p[1]<=13 and p not in seen:seen.add(p);q.append(p)
    return list(ENTRY)

def migrate_save(data,room):
    extra=data.get('extension',{}).get('remaster',{})
    if extra.get('studio_revision',0)==9:return
    snapshots=[]
    if 'r28' in data.get('snapshots',{}):snapshots.append(data['snapshots']['r28'])
    current=data.get('room')=='r28'
    if current:snapshots.append(data['checkpoint']['objects'])
    for snapshot in snapshots:
        for key,value in snapshot.items():
            if key in POSITIONS:value['pos']=list(POSITIONS[key])
    if current:
        data['player']=safe_position(data['player'],room)
        data['checkpoint']['pos']=safe_position(data['checkpoint']['pos'],room)
        if not extra.get('lab_memory_seen',False):
            data['player']=list(ENTRY);data['checkpoint']['pos']=list(ENTRY)
    points=data.get('explored',{}).get('r28')
    if points is not None:
        if not isinstance(points,list) or any(not isinstance(p,list) or len(p)!=2 or any(type(v) is not int for v in p) or not (0<=p[0]<26 and 0<=p[1]<16) for p in points):raise ValueError('Invalid old studio exploration')
        data['explored']['r28']=[p for p in points if p[0]<20 and p[1]<15]
    for orb,player in ((data.get('extension',{}).get('orb'),data.get('player')),
                       (data.get('checkpoint',{}).get('orb'),data.get('checkpoint',{}).get('pos'))):
        if orb and orb.get('room')=='r28':
            pos=player if orb.get('carried') and current else safe_position([orb['x'],orb['y']],room)
            orb['x'],orb['y']=pos
