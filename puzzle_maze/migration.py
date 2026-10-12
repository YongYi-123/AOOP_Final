"""Translate v2.0 snapshots into compact maps without resetting earned progress."""
import copy
from bisect import bisect_right
from collections import deque
from puzzle_maze.core import TileMap

class CoordinateTransform:
    def __init__(self,room):self.axes=room.get('legacy_axes')

    def point(self,pos):
        if not isinstance(pos,(list,tuple)) or len(pos)!=2 or any(type(v) is not int for v in pos):raise ValueError("Invalid legacy coordinates")
        if not self.axes:return list(pos)
        if any(not 0<=v<=self.axes[k][-1] for k,v in zip(("columns","rows"),pos)):raise ValueError("Legacy coordinates outside map")
        return [max(0,bisect_right(self.axes[k],v)-1) for k,v in zip(('columns','rows'),pos)]

class LayoutMigration:
    def __init__(self,rooms,legacy):self.rooms=rooms;self.legacy=legacy

    def region(self,name,old_pos):
        room=self.rooms[name];old=self.legacy[name]
        by_id={o['id']:o for o in room['objects']}
        left,right=0,len(room['tiles'][0])-1
        for o in old['objects']:
            if o['id'] not in ('gate','cracked','seal'):continue
            boundary=by_id[o['id']]['pos'][0]
            if old_pos[0]<o['pos'][0]:right=min(right,boundary-1)
            elif old_pos[0]>o['pos'][0]:left=max(left,boundary+1)
        return left,right

    def safe(self,name,old_pos,blocked=(),movable=False):
        room=self.rooms[name];tilemap=TileMap(room['tiles'])
        if not TileMap(self.legacy[name]["tiles"]).walkable(*old_pos):raise ValueError("Blocked old position")
        start=tuple(CoordinateTransform(room).point(old_pos));left,right=self.region(name,old_pos)
        queue=deque([start]);seen={start}
        plates={tuple(o['pos']) for o in room['objects'] if o['type']=='plate'}
        while queue:
            x,y=queue.popleft()
            valid=left<=x<=right and tilemap.walkable(x,y) and (x,y) not in blocked
            if valid and movable and (x,y) not in plates:
                valid=any(tilemap.walkable(x-dx,y-dy) and tilemap.walkable(x+dx,y+dy) and (x-dx,y-dy) not in blocked and (x+dx,y+dy) not in blocked for dx,dy in ((1,0),(0,1)))
            if valid:return [x,y]
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                p=x+dx,y+dy
                if p not in seen and 0<=p[0]<len(room['tiles'][0]) and 0<=p[1]<len(room['tiles']):seen.add(p);queue.append(p)
        raise ValueError('No safe migration position')

    def snapshot(self,name,snapshot):
        room=self.rooms[name];objects={o['id']:o for o in room['objects']}
        if set(snapshot)!={o['id'] for o in self.legacy[name]['objects']}:raise ValueError('Unsupported old object set')
        result=copy.deepcopy(snapshot);blocked=set()
        for key,obj in objects.items():
            if key not in result:
                if not obj.get('optional'):raise ValueError('Missing required object')
                result[key]=dict(pos=list(obj['pos']),active=False,remaining=0,unlocked=False,latched=False)
        for key,values in result.items():
            obj=objects[key]
            if obj['type']!='box':
                old_obj=next((o for o in self.legacy[name]['objects'] if o['id']==key),None)
                if old_obj is not None and values['pos']!=old_obj['pos']:raise ValueError('Moved old static object')
                values['pos']=list(obj['pos'])
            if obj['type']=='timed':values['remaining']=min(values['remaining'],obj['duration'])
            if obj['type'] in ('door','secret') and not values['active']:blocked.add(tuple(values['pos']))
        for key,values in result.items():
            if objects[key]['type']=='box':
                values['pos']=self.safe(name,snapshot[key]['pos'],blocked,True)
                blocked.add(tuple(values['pos']))
        return result,blocked

    def encounter(self,name,encounter,blocked):
        result=copy.deepcopy(encounter);occupied=set(blocked)
        for e in result['enemies'].values():
            e['pos']=self.safe(name,e['pos'],occupied)
            if e['hp']>0:occupied.add(tuple(e['pos']))
        for drop in result['loot']:drop['pos']=self.safe(name,drop['pos'])
        return result

    def apply(self,data):
        result=copy.deepcopy(data);blocked_by_room={}
        for name,snapshot in data['snapshots'].items():
            result['snapshots'][name],blocked_by_room[name]=self.snapshot(name,snapshot)
        for name,snapshot in data.get('encounters',{}).items():
            result['encounters'][name]=self.encounter(name,snapshot,blocked_by_room.get(name,set()))
        name=data['room'];blocked=blocked_by_room.get(name,set())
        result['player']=self.safe(name,data['player'],blocked)
        checkpoint=result['checkpoint'];old_checkpoint=data['checkpoint']
        checkpoint['objects'],checkpoint_blocked=self.snapshot(name,old_checkpoint['objects'])
        checkpoint['pos']=self.safe(name,old_checkpoint['pos'],checkpoint_blocked)
        checkpoint['combat']=self.encounter(name,old_checkpoint['combat'],checkpoint_blocked)
        result['explored']={}
        for name,points in data.get('explored',{}).items():
            axes=self.rooms[name]['legacy_axes'];transform=CoordinateTransform(self.rooms[name])
            result['explored'][name]=[transform.point(p) for p in points if p[0] in axes['columns'] and p[1] in axes['rows']]
        result['map_revision']='2.1'
        return result
