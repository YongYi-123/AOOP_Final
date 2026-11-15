"""One source for the production studio's placement, contact footprints and story route."""
from dataclasses import dataclass
SIZE=(320,208)
ENTRY=(3,8)
MIAO_TILE=(9,6)
MIAO_ROUTE=((24.,128.),(72.,128.),(72.,112.),(152.,112.))
@dataclass(frozen=True)
class Furniture:
    name:str
    bounds:tuple
    footprint:tuple
SOURCE_FURNITURE=(
 Furniture('desk',(80,33,144,75),(88,76,128,27)),
 Furniture('tower',(225,52,25,51),(226,83,23,20)),
 Furniture('bookshelf',(32,43,34,55),(32,78,34,20)),
 Furniture('sofa',(30,142,67,46),(32,164,63,20)),
 Furniture('table',(108,149,28,33),(109,166,27,16)),
 Furniture('archive',(258,47,45,73),(260,90,43,29)),
 Furniture('food',(272,122,31,32),(272,137,31,17)),
 Furniture('cushion',(234,151,50,33),(237,165,47,18)),
 Furniture('post',(286,127,18,41),(286,156,18,12)),
 Furniture('plant',(20,164,18,31),(23,184,14,9)),
)
# Thin, human-scaled furniture: keep each floor contact anchored while reducing volume.
def refined(item):
    x,y,w,h=item.bounds
    scale=1 if item.name=='plant' else .67 if item.name in ('desk','tower','archive','bookshelf') else .8
    nw,nh=round(w*scale),round(h*scale)
    nx,ny=x+(w-nw)//2,y+h-nh
    fx,fy,fw,fh=item.footprint
    return Furniture(item.name,(nx,ny,nw,nh),
        (nx+round((fx-x)*scale),ny+round((fy-y)*scale),max(8,round(fw*scale)),max(6,round(fh*scale))))
FURNITURE=tuple(refined(item) for item in SOURCE_FURNITURE)

POSITIONS={'photo':(11,5),'note':(13,5),'miao':MIAO_TILE,'gpu':(14,5),'keyboard':(8,5),'terminal':(17,6),
 'dev_001':(3,4),'dev_002':(3,5),'dev_003':(7,4),'dev_004':(15,3),'dev_005':(7,10),'dev_006':(17,4),'dev_007':(3,10),
 'lab_duck':(12,5),'lab_coffee':(6,10),'lab_button':(15,6),
 'studio_todo':(17,3),'studio_food':(17,8),'studio_cushion':(16,10),'studio_reminder':(6,4)}

def contact_blocked(px,py,footprints,width=10,height=6):
    left,right=px-width/2,px+width/2;top,bottom=py-height,py
    return any(left<x+w and right>x and top<y+h and bottom>y for x,y,w,h in footprints)

def tile_blocked(x,y,footprints=None):
    return contact_blocked(x*16+8,y*16+16,footprints if footprints is not None else [f.footprint for f in FURNITURE])

def configure(room):
    from puzzle_maze.build_dungeon import obj
    room.update(name="Kevin's Cozy Studio",spawn=list(ENTRY),studio_revision=2,decorations=[],
                architecture='studio',hint='The western door leads back. There is no hurry here.',
                tiles=['#'*20]*3+['#'+'.'*18+'#' for _ in range(9)]+['#'*20],
                solid_footprints=[list(f.footprint) for f in FURNITURE])
    for data in room['objects']:data['pos']=list(POSITIONS[data['id']])
    for key in ('studio_todo','studio_food','studio_cushion','studio_reminder'):
        room['objects'].append(obj('mystery_scroll',key,POSITIONS[key],content_id=key,optional=True))


def approach(room,position):
    """Return a reachable inspection neighbor and facing using the production footprints."""
    x,y=position
    for dx,dy in ((0,1),(-1,0),(1,0),(0,-1)):
        px,py=x+dx,y+dy
        rows=room['tiles']
        if 0<=py<len(rows) and 0<=px<len(rows[0]) and rows[py][px]!='#' and not tile_blocked(px,py,room['solid_footprints']):
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
    if extra.get('studio_revision',0)==2:return
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
