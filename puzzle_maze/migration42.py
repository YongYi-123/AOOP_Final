"""Validate and migrate the prior layout without changing earned progress."""
import copy
from puzzle_maze.rooms import load_rooms,MAP_PATH
from puzzle_maze.puzzles import PuzzleManager


def migrate(data,rooms,validate_snapshot):
    if data.get('content_revision')=='4.2':return data
    legacy=load_rooms(MAP_PATH.with_name('dungeon_v41.json'))
    result=copy.deepcopy(data)
    def snapshot(name,old):
        # Validate old static coordinates before replacing them with authored new ones.
        validate_snapshot(legacy[name],old)
        defaults=PuzzleManager(rooms[name])
        transformed={}
        for id,obj in defaults.objects.items():
            state=copy.deepcopy(old.get(id,dict(pos=list(obj.pos),active=obj.state.active,remaining=0,unlocked=getattr(obj,'unlocked',False),latched=False)))
            if obj.data['type'] not in ('box','pot'):state['pos']=list(obj.pos)
            transformed[id]=state
        return transformed
    result['snapshots']={name:snapshot(name,old) for name,old in data['snapshots'].items()}
    name=data['room'];result['checkpoint']['objects']=snapshot(name,data['checkpoint']['objects'])
    # All old walking tiles remain walking tiles. New blocking gates can require
    # an adjacent landing, but the saved inventory/combat/rewards are retained.
    from collections import deque
    def safe(pos,snapshot):
        manager=PuzzleManager(rooms[name]);blocked={tuple(v['pos']) for id,v in snapshot.items() if manager.objects[id].blocking and not v['active']}
        queue=deque([tuple(pos)]);seen=set(queue)
        while queue:
            p=queue.popleft()
            if manager.tilemap.walkable(*p) and p not in blocked:return list(p)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt=p[0]+dx,p[1]+dy
                if nxt not in seen and manager.tilemap.walkable(*nxt):seen.add(nxt);queue.append(nxt)
        raise ValueError('No migrated landing')
    result['player']=safe(data['player'],result['snapshots'].get(name,result['checkpoint']['objects']))
    result['checkpoint']['pos']=safe(data['checkpoint']['pos'],result['checkpoint']['objects'])
    result['content_revision']='4.2'
    return result
