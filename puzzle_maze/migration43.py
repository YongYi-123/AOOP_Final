"""Upgrade optional 4.3 content in memory without rewriting the original save."""
import copy
from collections import deque
from puzzle_maze.puzzles import PuzzleManager

# These conditional 4.2 chests were visible while still locked. Their old
# AVAILABLE phase is not evidence that their puzzle was already completed.
NEWLY_HIDDEN={('r5','compass'),('r8','bonus'),('r11','magnet'),('r12','key'),
              ('r14','reward'),('r22','fragment'),('r22','cache')}

def migrate(data,rooms):
    if data.get('content_revision')=='4.3':return data
    result=copy.deepcopy(data)
    for name,snapshot in list(result['snapshots'].items())+[(result['room'],result['checkpoint']['objects'])]:
        manager=PuzzleManager(rooms[name])
        for id,obj in manager.objects.items():
            if id not in snapshot and obj.data.get('optional'):
                snapshot[id]=dict(pos=list(obj.pos),active=False,remaining=0,unlocked=False,latched=False)
            state=snapshot.get(id,{})
            if (name,id) in NEWLY_HIDDEN and not state.get('active'):
                state.update(chest_phase='hidden',spawn_time=0.,triggered=False)
    name=result['room']
    def landing(pos,snapshot):
        manager=PuzzleManager(rooms[name]);blocked={tuple(v['pos']) for id,v in snapshot.items() if manager.objects[id].blocking and not v['active']}
        queue=deque([tuple(pos)]);seen=set(queue)
        while queue:
            cell=queue.popleft()
            if manager.tilemap.walkable(*cell) and cell not in blocked:return list(cell)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt=cell[0]+dx,cell[1]+dy
                if nxt not in seen and manager.tilemap.walkable(*nxt):seen.add(nxt);queue.append(nxt)
        raise ValueError('No 4.3 save landing')
    result['player']=landing(result['player'],result['snapshots'].get(name,result['checkpoint']['objects']))
    result['checkpoint']['pos']=landing(result['checkpoint']['pos'],result['checkpoint']['objects'])
    orb=result.get('extension',{}).get('orb')
    if orb and orb['carried']:orb['x'],orb['y']=result['player']
    orb=result['checkpoint'].get('orb')
    if orb and orb['carried']:orb['x'],orb['y']=result['checkpoint']['pos']
    result['content_revision']='4.3'
    return result
