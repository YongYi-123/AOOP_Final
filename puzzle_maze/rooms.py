"""JSON room loading and structural validation."""
import json
from pathlib import Path
from puzzle_maze.core import TileMap, Player
from puzzle_maze.themes import THEMES,DECOR_KINDS

MAP_PATH = Path(__file__).parent / 'maps' / 'dungeon.json'

def load_rooms(path=MAP_PATH):
    rooms = json.loads(Path(path).read_text())
    validate_rooms(rooms)
    return rooms

def validate_rooms(rooms):
    from puzzle_maze import advanced_puzzles
    if len(rooms) < 8:
        raise ValueError('At least eight rooms required')
    for name, room in rooms.items():
        rows = room['tiles']
        if not rows or len(set(map(len, rows))) != 1:
            raise ValueError(f'{name}: non-rectangular map')
        tilemap = TileMap(rows)
        if any(c not in '#.~Ogv' for row in rows for c in row):
            raise ValueError(f'{name}: unknown terrain')
        if any(c != '#' for c in rows[0] + rows[-1]) or any(row[0] != '#' or row[-1] != '#' for row in rows):
            raise ValueError(f'{name}: unsealed border')
        if not tilemap.walkable(*room['spawn']):
            raise ValueError(f'{name}: blocked spawn')
        ids = [obj['id'] for obj in room['objects']]
        if len(ids) != len(set(ids)):
            raise ValueError(f'{name}: duplicate object ids')
        occupied = set()
        for obj in room['objects']:
            if obj['type'] not in ('box', 'plate', 'switch', 'door', 'key', 'secret', 'timed', 'chest', 'light', 'receiver', 'reflector', 'combat','cracked','blast_switch','supply','dash_switch','relay','remote','brazier','torch_order','weight','crystal_switch','crystal_barrier','pot','powder_supply','pot_supply','ordered'):
                raise ValueError(f'{name}: unknown object')
            pos = tuple(obj['pos'])
            if not tilemap.walkable(*pos) or pos in occupied or pos == tuple(room['spawn']):
                raise ValueError(f'{name}: invalid object position')
            occupied.add(pos)
            if any(req not in ids for req in obj.get('requires', [])):
                raise ValueError(f'{name}: missing condition')
            if obj['type']=='chest' and obj.get('ability') not in (None,'gloves','boots','mirror','magnet','map','compass','powder'):
                raise ValueError(f'{name}: unknown ability')
            if obj['type']=='light' and obj.get('direction') not in ([1,0],[-1,0],[0,1],[0,-1]):
                raise ValueError(f'{name}: invalid light direction')
            if obj['type'] == 'timed' and obj.get('duration', 0) <= 0:
                raise ValueError(f'{name}: invalid timer')
            if obj['type']=='torch_order' and (not obj.get('order') or len(obj['order'])!=len(set(obj['order'])) or any(i not in ids for i in obj['order'])):raise ValueError(f'{name}: invalid torch sequence')
            if obj['type']=='crystal_barrier' and obj.get('color') not in ('red','blue'):raise ValueError(f'{name}: invalid crystal barrier')
            if obj['type'] in ('weight','pot') and (type(obj.get('weight',2)) is not int or not 1<=obj.get('weight',2)<=6):raise ValueError(f'{name}: invalid weight')
            if obj.get('loot'):
                from puzzle_maze.rewards import TREASURES
                if any(t not in TREASURES for t in obj['loot']):raise ValueError(f'{name}: unknown treasure')

        enemy_ids=set()
        for enemy in room.get('enemies',[]):
            if enemy['id'] in enemy_ids or enemy['type'] not in ('slime','bat','guardian','blink_mage','armored_beetle','bomb_eater','golem','mirror_mask','pot_hunter','crystal_ghost','elite_guardian','crystal_warden'):
                raise ValueError(f'{name}: invalid enemy')
            enemy_ids.add(enemy['id'])
            x,y=enemy['pos'];sx,sy=room['spawn']
            if not tilemap.walkable(x,y) or (x,y) in occupied or abs(x-sx)+abs(y-sy)<5:
                raise ValueError(f'{name}: unsafe enemy spawn')
            occupied.add((x,y))
        if room.get('kill_order') and (len(room['kill_order'])!=len(enemy_ids) or set(room['kill_order'])!=enemy_ids):raise ValueError(f'{name}: invalid kill order')
        if room.get('theme','entrance') not in THEMES:raise ValueError(f'{name}: unknown room theme')
        for decoration in room.get('decorations',[]):
            x,y=decoration['pos']
            if decoration['kind'] not in DECOR_KINDS or not (0<=y<len(rows) and 0<=x<len(rows[0])) or rows[y][x]!='#':
                raise ValueError(f'{name}: decoration must be mounted on an existing wall')
            if any(abs(x-o['pos'][0])+abs(y-o['pos'][1])<2 for o in room['objects']):raise ValueError(f'{name}: decoration hides mechanism')
        atlas=room.get('atlas')
        if atlas is not None and (not isinstance(atlas,list) or len(atlas)!=2 or any(type(v) is not int or v<0 for v in atlas)):
            raise ValueError(f'{name}: invalid atlas coordinates')
        dependencies={o['id']:o.get('requires',[]) for o in room['objects']}
        def visit(node,stack,seen):
            if node in stack:raise ValueError(f'{name}: cyclic puzzle conditions')
            if node in seen:return
            for dep in dependencies[node]:visit(dep,stack|{node},seen)
            seen.add(node)
        checked=set()
        for node in dependencies:visit(node,set(),checked)
        if not room['exits']:
            raise ValueError(f'{name}: missing exits')
        for e in room['exits']:
            if any(req not in ids for req in e.get('requires', [])):
                raise ValueError(f'{name}: missing exit condition')
            if not tilemap.walkable(*e['pos']) or e['target'] not in rooms:
                raise ValueError(f'{name}: invalid exit')
            if not TileMap(rooms[e['target']]['tiles']).walkable(*e['arrival']):
                raise ValueError(f'{name}: invalid arrival')
        if any(i not in ids for i in room['goal']):
            raise ValueError(f'{name}: invalid goal')
    reachable = {next(iter(rooms))}
    frontier = list(reachable)
    while frontier:
        for e in rooms[frontier.pop()]['exits']:
            if e['target'] not in reachable:
                reachable.add(e['target'])
                frontier.append(e['target'])
    if reachable != set(rooms):
        raise ValueError('Disconnected room graph')

class RoomManager:
    def __init__(self, rooms=None):
        self.rooms = rooms or load_rooms()
        self.current = next(iter(self.rooms))
        self.revision=self.data.get("layout_revision","2.0")

    @property
    def data(self):
        return self.rooms[self.current]

    def enter(self, name, arrival=None):
        self.current = name
        return Player(*(arrival or self.data['spawn']))

    def legacy_position(self,pos):
        from puzzle_maze.migration import CoordinateTransform
        return CoordinateTransform(self.data).point(pos)

    def exit_at(self, player):
        return next((e for e in self.data['exits'] if tuple(e['pos']) == (player.x, player.y)), None)
