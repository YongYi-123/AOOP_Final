"""Visibility and graph presentation derive from room data, never a duplicate atlas."""
from collections import deque

class Exploration:
    def __init__(self):self.tiles={}

    @staticmethod
    def ray(start,end):
        x,y=start;tx,ty=end
        dx=abs(tx-x);dy=-abs(ty-y);sx=1 if x<tx else -1;sy=1 if y<ty else -1;error=dx+dy
        while True:
            yield x,y
            if (x,y)==(tx,ty):break
            twice=2*error
            if twice>=dy:error+=dy;x+=sx
            if twice<=dx:error+=dx;y+=sy

    def reveal(self,room_id,puzzles,player,radius=5):
        known=self.tiles.setdefault(room_id,set());rows=puzzles.tilemap.rows
        start=player.x,player.y
        for y in range(max(0,player.y-radius),min(len(rows),player.y+radius+1)):
            for x in range(max(0,player.x-radius),min(len(rows[0]),player.x+radius+1)):
                if abs(x-player.x)+abs(y-player.y)>radius:continue
                for pos in self.ray(start,(x,y)):
                    known.add(pos)
                    if pos!=start and (rows[pos[1]][pos[0]] in '#O' or puzzles.blocked(*pos)):break

    def capture(self):return {name:[list(p) for p in sorted(points)] for name,points in self.tiles.items()}

    def restore(self,data,rooms):
        if not isinstance(data,dict):raise ValueError('Invalid exploration')
        result={}
        for name,points in data.items():
            if name not in rooms or not isinstance(points,list):raise ValueError('Unknown explored room')
            tiles=set();rows=rooms[name]['tiles']
            for p in points:
                if not isinstance(p,list) or len(p)!=2 or any(type(v) is not int for v in p) or not (0<=p[0]<len(rows[0]) and 0<=p[1]<len(rows)):raise ValueError('Invalid explored tile')
                tiles.add(tuple(p))
            result[name]=tiles
        self.tiles=result

class DungeonAtlas:
    def __init__(self,manager):self.manager=manager

    def visible_rooms(self,visited):
        return {name:room for name,room in self.manager.rooms.items() if not room.get('hidden') or name in visited}

    def layout(self,visited):
        visible=self.visible_rooms(visited)
        if all('atlas' in room for room in visible.values()):return {name:tuple(room['atlas']) for name,room in visible.items()}
        # Existing/custom maps without coordinates still derive their graph automatically.
        root=next(iter(visible));queue=deque([(root,0)]);seen={root};result={}
        while queue:
            name,depth=queue.popleft();result[name]=(len(result)%4,depth)
            for e in visible[name]['exits']:
                if e['target'] in visible and e['target'] not in seen and not e.get('finish'):
                    seen.add(e['target']);queue.append((e['target'],depth+1))
        return result

    def edges(self,visited):
        visible=self.visible_rooms(visited)
        return {tuple(sorted((name,e['target']))) for name,room in visible.items() for e in room['exits'] if not e.get('finish') and e['target'] in visible}

    def discovered_markers(self,session):
        known=session.exploration.tiles.get(session.rooms.current,set())
        room=session.rooms.data
        markers=[('exit',tuple(e['pos'])) for e in room['exits'] if tuple(e['pos']) in known]
        markers += [(o['type'],tuple(o['pos'])) for o in room['objects'] if o['type'] in ('door','secret','chest','receiver') and tuple(o['pos']) in known]
        return markers
