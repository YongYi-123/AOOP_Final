"""Session owns room snapshots, checkpoint reset, and private atomic saves."""
import copy
import json
import math
from pathlib import Path
from puzzle_maze.rooms import RoomManager
from puzzle_maze.puzzles import PuzzleManager, Inventory, Door

SAVE_PATH = Path(__file__).parent / 'save.json'

class GameSession:
    def __init__(self, rooms=None):
        self.rooms = RoomManager(rooms)
        self.inventory = Inventory()
        self.snapshots = {}
        self.completed = set()
        self.visited = {'r1'}
        self.finished = False
        self.enter('r1')

    def capture(self):
        return {name: dict(pos=list(o.pos), active=o.state.active,
                           remaining=o.state.remaining,
                           unlocked=getattr(o,'unlocked',False), latched=getattr(o,'latched',False))
                for name,o in self.puzzles.objects.items()}

    def restore(self, snapshot):
        for name, values in snapshot.items():
            obj=self.puzzles.objects[name]
            obj.x,obj.y=values['pos']
            obj.state.active=values['active']
            obj.state.remaining=values['remaining']
            if isinstance(obj,Door):
                obj.unlocked=values['unlocked']; obj.latched=values['latched']
        self.puzzles.update(0,self.player)

    def enter(self, name, arrival=None):
        self.player=self.rooms.enter(name,arrival)
        self.puzzles=PuzzleManager(self.rooms.data,self.inventory)
        if name in self.snapshots:
            self.restore(self.snapshots[name])
        self.checkpoint = dict(inventory=copy.deepcopy(self.inventory.keys), objects=self.capture(), pos=[self.player.x,self.player.y])
        self.visited.add(name)

    def reset(self):
        self.inventory.keys=copy.deepcopy(self.checkpoint['inventory'])
        self.player.x,self.player.y=self.checkpoint['pos']
        self.player.moving=False
        self.restore(self.checkpoint['objects'])
        # Remove completion only when checkpoint itself was unsolved.
        if not self.puzzles.solved:
            self.completed.discard(self.rooms.current)

    def tick(self, dt):
        self.puzzles.update(dt,self.player)
        if self.puzzles.solved:
            self.completed.add(self.rooms.current)

    def move(self, dx, dy):
        moved=self.puzzles.move(self.player,dx,dy)
        self.tick(0)
        return moved

    def transition(self):
        e=self.rooms.exit_at(self.player)
        if e is None:
            return False
        if e.get('requires') and self.rooms.current not in self.completed and not all(self.puzzles.objects[i].state.active for i in e['requires']):
            return False
        if e.get('finish'):
            if not self.puzzles.solved and self.rooms.current not in self.completed:
                return False
            self.finished=True
            return True
        self.snapshots[self.rooms.current]=self.capture()
        self.enter(e['target'],e['arrival'])
        return True

    def save(self, path=SAVE_PATH):
        self.snapshots[self.rooms.current]=self.capture()
        data=dict(version=1, room=self.rooms.current, player=[self.player.x,self.player.y],
                  inventory=self.inventory.keys, snapshots=self.snapshots,
                  completed=sorted(self.completed), visited=sorted(self.visited),
                  finished=self.finished, checkpoint=self.checkpoint)
        path=Path(path); tmp=path.with_suffix(path.suffix+'.tmp')
        tmp.write_text(json.dumps(data,indent=2)+'\n')
        tmp.replace(path)

    @staticmethod
    def validate_inventory(keys):
        if not isinstance(keys, dict) or any(not isinstance(k, str) or type(v) is not int or v < 0 for k, v in keys.items()):
            raise ValueError('Invalid inventory')

    @staticmethod
    def validate_position(pos, tilemap):
        if not isinstance(pos, list) or len(pos) != 2 or any(type(v) is not int for v in pos) or not tilemap.walkable(*pos):
            raise ValueError('Invalid position')

    @classmethod
    def validate_snapshot(cls, room, snapshot):
        manager = PuzzleManager(room)
        if not isinstance(snapshot, dict) or set(snapshot) != set(manager.objects):
            raise ValueError('Incomplete snapshot')
        occupied = set()
        for name, obj in manager.objects.items():
            values = snapshot[name]
            cls.validate_position(values['pos'], manager.tilemap)
            if obj.data['type'] != 'box' and values['pos'] != obj.data['pos']:
                raise ValueError('Moved static object')
            for flag in ('active', 'unlocked', 'latched'):
                if type(values[flag]) is not bool:
                    raise ValueError('Invalid state')
            timer = values['remaining']
            if not isinstance(timer, (int, float)) or not math.isfinite(timer) or timer < 0 or timer > obj.data.get('duration', 0):
                raise ValueError('Invalid timer')
            if obj.blocking and not values['active']:
                pos = tuple(values['pos'])
                if pos in occupied:
                    raise ValueError('Overlapping obstacles')
                occupied.add(pos)

    @classmethod
    def load(cls,path=SAVE_PATH):
        try:
            data=json.loads(Path(path).read_text())
            candidate=cls()
            if data['version'] != 1 or data['room'] not in candidate.rooms.rooms:
                raise ValueError('Unsupported save')
            candidate.inventory.keys=data['inventory']
            cls.validate_inventory(candidate.inventory.keys)
            candidate.snapshots=data['snapshots']
            candidate.completed=set(data['completed']); candidate.visited=set(data['visited'])
            if not (candidate.completed | candidate.visited) <= candidate.rooms.rooms.keys():
                raise ValueError('Invalid room set')
            # Validate every stored room using the same collision rules as gameplay.
            for room,snapshot in candidate.snapshots.items():
                if room not in candidate.rooms.rooms:
                    raise ValueError('Unknown room')
                cls.validate_snapshot(candidate.rooms.rooms[room], snapshot)
            cls.validate_position(data['player'], PuzzleManager(candidate.rooms.rooms[data['room']]).tilemap)
            candidate.enter(data['room'],data['player'])
            if candidate.puzzles.blocked(*data['player']):
                raise ValueError('Blocked player')
            checkpoint = data['checkpoint']
            cls.validate_inventory(checkpoint['inventory'])
            cls.validate_snapshot(candidate.rooms.data, checkpoint['objects'])
            cls.validate_position(checkpoint['pos'], candidate.puzzles.tilemap)
            check_manager = PuzzleManager(candidate.rooms.data)
            for name, values in checkpoint['objects'].items():
                obj = check_manager.objects[name]
                obj.x, obj.y = values['pos']
                obj.state.active = values['active']
            if check_manager.blocked(*checkpoint['pos']):
                raise ValueError('Blocked checkpoint')
            candidate.checkpoint=checkpoint
            candidate.finished=bool(data['finished'])
            return candidate
        except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError):
            return cls()
