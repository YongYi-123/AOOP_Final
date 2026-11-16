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
 Furniture('cab_cracked',(34,54,28,48),(35,85,26,20)),
 Furniture('cab_open',(79,54,28,48),(80,87,26,18)),
 Furniture('cab_frozen',(124,54,28,48),(125,85,26,20)),
 Furniture('desk',(184,54,104,52),(186,83,100,22)),
 Furniture('prototype',(36,150,34,48),(38,177,30,22)),
 Furniture('cart',(123,152,36,32),(125,166,32,18)),
 Furniture('server',(211,138,26,46),(213,166,22,18)),
 Furniture('food',(270,142,28,25),(272,154,25,13)),
 Furniture('cushion',(260,179,40,21),(266,186,29,12)),
)
MIAO_FOOTPRINT=(162,122,12,6)
POSITIONS={'photo':(12,5),'note':(14,5),'miao':MIAO_TILE,'gpu':(15,5),'keyboard':(11,5),'terminal':(3,10),
 'dev_001':(3,6),'dev_002':(5,6),'dev_003':(8,6),'dev_004':(16,3),'dev_005':(8,10),'dev_006':(10,3),'dev_007':(12,3),
 'lab_duck':(13,5),'lab_coffee':(10,5),'lab_button':(4,10),
 'studio_todo':(18,3),'studio_food':(17,9),'studio_cushion':(17,11),'studio_reminder':(14,3),
 'work_crt':(3,5),'work_back':(5,5),'work_frozen':(8,5),'work_prototype':(2,10)}

def contact_blocked(px,py,footprints,width=10,height=6):
    left,right=px-width/2,px+width/2;top,bottom=py-height,py
    return any(left<x+w and right>x and top<y+h and bottom>y for x,y,w,h in footprints)

def tile_blocked(x,y,footprints=None):
    return contact_blocked(x*16+8,y*16+16,footprints if footprints is not None else [f.footprint for f in FURNITURE])

def configure(room):
    from puzzle_maze.build_dungeon import obj
    room.update(name="The Forgotten Arcade Workshop",spawn=list(ENTRY),studio_revision=4,decorations=[],
                architecture='studio',hint='The western door leads back. There is no hurry here.',
                tiles=['#'*20]*3+['#'+'.'*18+'#' for _ in range(9)]+['#'*20],
                solid_footprints=[list(f.footprint) for f in FURNITURE])
    for data in room['objects']:data['pos']=list(POSITIONS[data['id']])
    for key in ('studio_todo','studio_food','studio_cushion','studio_reminder','work_crt','work_back','work_frozen','work_prototype'):
        room['objects'].append(obj('mystery_scroll',key,POSITIONS[key],content_id=key,optional=True))


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
    start=(max(1,min(18,pos[0])),max(3,min(11,pos[1])))
    q=deque([start]);seen={start}
    while q:
        x,y=q.popleft()
        if room['tiles'][y][x]!='#' and not tile_blocked(x,y,room['solid_footprints']):return [x,y]
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            p=x+dx,y+dy
            if 1<=p[0]<=18 and 3<=p[1]<=11 and p not in seen:seen.add(p);q.append(p)
    return list(ENTRY)

def migrate_save(data,room):
    extra=data.get('extension',{}).get('remaster',{})
    if extra.get('studio_revision',0)==4:return
    if extra.get('lab_memory_seen',False):
        room=dict(room,solid_footprints=room['solid_footprints']+[list(MIAO_FOOTPRINT)])
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
        data['explored']['r28']=[p for p in points if p[0]<20 and p[1]<13]
    for orb,player in ((data.get('extension',{}).get('orb'),data.get('player')),
                       (data.get('checkpoint',{}).get('orb'),data.get('checkpoint',{}).get('pos'))):
        if orb and orb.get('room')=='r28':
            pos=player if orb.get('carried') and current else safe_position([orb['x'],orb['y']],room)
            orb['x'],orb['y']=pos
