"""Entrance safety shared by map authoring, validation and live encounters."""
from collections import deque

def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])

def landing_points(name,rooms):
    room=rooms[name]
    return {tuple(room['spawn'])} | {tuple(e['arrival']) for source in rooms.values() for e in source['exits'] if e['target']==name and not e.get('finish')}

def safe_enemy_tile(room,pos,occupied=()):
    from puzzle_maze.core import TileMap
    radius=room.get('entry_safe_radius',3)
    important={tuple(o['pos']) for o in room['objects']} | {tuple(e['pos']) for e in room['exits']}
    return (TileMap(room['tiles']).walkable(*pos) and pos not in important and pos not in occupied
            and all(distance(pos,p)>=radius for p in room.get('safe_landings',[room['spawn']])))

def nearest_safe(room,start,occupied=()):
    from puzzle_maze.core import TileMap
    tiles=TileMap(room['tiles']);queue=deque([tuple(start)]);seen=set(queue)
    while queue:
        pos=queue.popleft()
        if safe_enemy_tile(room,pos,occupied):return pos
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nxt=pos[0]+dx,pos[1]+dy
            if nxt not in seen and tiles.walkable(*nxt):seen.add(nxt);queue.append(nxt)
    raise ValueError('No safe enemy spawn')
