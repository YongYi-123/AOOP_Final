"""Push-state breadth-first search: canonical player regions avoid tile blowup."""
from collections import deque
from puzzle_maze.core import TileMap

def solve_boxes(room, box_ids=None, plate_ids=None, start=None, open_ids=()):
    tilemap=TileMap(room['tiles'])
    boxes=frozenset(tuple(o['pos']) for o in room['objects'] if o['type']=='box' and (box_ids is None or o['id'] in box_ids))
    goals=frozenset(tuple(o['pos']) for o in room['objects'] if o['type']=='plate' and (plate_ids is None or o['id'] in plate_ids))
    barriers={tuple(o['pos']) for o in room['objects'] if o['type'] in ('door','secret') and o['id'] not in open_ids}
    directions=((1,0),(-1,0),(0,1),(0,-1))

    def region(start,stones):
        reachable={start};stack=[start]
        while stack:
            x,y=stack.pop()
            for dx,dy in directions:
                p=x+dx,y+dy
                if p not in reachable and p not in stones and p not in barriers and tilemap.walkable(*p):
                    reachable.add(p);stack.append(p)
        return reachable

    initial=tuple(start or room['spawn'])
    queue=deque([(initial,boxes,[])])
    seen={(min(region(initial,boxes)),boxes)}
    while queue:
        player,stones,path=queue.popleft()
        if goals<=stones:return path
        reachable=region(player,stones)
        for x,y in sorted(stones):
            for dx,dy in directions:
                behind=(x-dx,y-dy);ahead=(x+dx,y+dy)
                if behind not in reachable or ahead in stones or ahead in barriers or not tilemap.walkable(*ahead):continue
                # A stone away from a plate in a static corner is unrecoverable.
                if ahead not in goals:
                    ax,ay=ahead
                    if any((not tilemap.walkable(ax+hx,ay) or (ax+hx,ay) in barriers) and (not tilemap.walkable(ax,ay+vy) or (ax,ay+vy) in barriers) for hx in (-1,1) for vy in (-1,1)):continue
                next_stones=(stones-{(x,y)})|{ahead}
                state=(min(region((x,y),next_stones)),next_stones)
                if state in seen:continue
                seen.add(state);queue.append(((x,y),next_stones,path+[(behind,(dx,dy))]))
    return None
