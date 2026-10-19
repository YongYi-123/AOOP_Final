"""Derive switch consumers from real room/object/flag data, not hand-written text."""
from collections import deque
from puzzle_maze.puzzles import FACTORY

class PuzzleDependencyValidator:
    ACTUATORS={'switch','timed','remote','crystal_switch','plate','weight','reflector','brazier','torch_order','blast_switch','dash_switch','ordered','ordered_layout','pillar','orb_socket'}
    def __init__(self,rooms):self.rooms=rooms
    def targets(self,name,obj):
        room=self.rooms[name];targets=[]
        for other in room['objects']:
            if obj['id'] in other.get('requires',[]) or obj['id'] in other.get('order',[]):targets.append(f'{name}:{other["id"]}')
        for exit in room['exits']:
            if obj['id'] in exit.get('requires',[]):targets.append(exit['id'])
        if obj['type'] in ('plate','weight'):
            targets += [f'{name}:{o["id"]}' for o in room['objects'] if o['type']=='light' and obj['id'] in o.get('requires',[])]
        if obj['type']=='reflector':targets += [f'{name}:{o["id"]}' for o in room['objects'] if o['type']=='receiver']
        if obj['type']=='dash_switch':targets += [f'{name}:{e["id"]}' for e in room.get('enemies',[]) if e['type']=='golem']
        if obj['type']=='crystal_switch':
            targets += [f'{rn}:{o["id"]}' for rn,r in self.rooms.items() for o in r['objects'] if o['type']=='crystal_barrier' or o.get('crystal_color')]
            targets += [f'{rn}:{e["id"]}' for rn,r in self.rooms.items() for e in r.get('enemies',[]) if e.get('weak_color') or e.get('crystal_color')]
        if obj.get('flag'):
            flag=obj['flag']
            for rn,r in self.rooms.items():
                targets += [f'{rn}:{o["id"]}' for o in r['objects'] if flag in o.get('flags',[]) or flag in o.get('flag_requires',[])]
                targets += [e['id'] for e in r['exits'] if flag in e.get('flag_requires',[])]
                if flag in r.get('transformation',{}).get('flags',[]):targets.append(f'{rn}:floor_transform')
        return sorted(set(targets))
    def validate(self):
        result={}
        for name,room in self.rooms.items():
            for obj in room['objects']:
                if obj['type'] in self.ACTUATORS:
                    targets=self.targets(name,obj)
                    if not targets:raise ValueError(f'{name}:{obj["id"]}: ineffective mechanism')
                    result[f'{name}:{obj["id"]}']=targets
        return result

class ChestValidator:
    """Check every chest has an interaction route once its conditions are solved.

    This local collision check supplements the campaign action witness and
    dependency/resource searches; it does not substitute for solving triggers.
    """
    def __init__(self,rooms):self.rooms=rooms
    def validate(self):
        from puzzle_maze.advanced_puzzles import AdvancedPuzzleManager
        from puzzle_maze.puzzles import Inventory,Door
        total=0
        for name,room in self.rooms.items():
            manager=AdvancedPuzzleManager(room,Inventory(abilities={'gloves','boots','mirror','magnet'}))
            for obj in manager.objects.values():
                if obj.blocking and obj.data['type'] not in ('box','pot'):obj.state.active=True
            start=tuple(room['spawn']);queue=deque([start]);seen={start}
            while queue:
                x,y=queue.popleft()
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    dest=x+dx,y+dy
                    if dest not in seen and manager.can_enter(*dest):seen.add(dest);queue.append(dest)
            for obj in manager.objects.values():
                if obj.data['type']=='chest':
                    if not any((obj.x+dx,obj.y+dy) in seen for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))):raise ValueError(f'{name}:{obj.id}: unreachable chest')
                    total+=1
        return total
