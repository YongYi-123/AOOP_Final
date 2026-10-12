"""Session owns room snapshots, checkpoint reset, and private atomic saves."""
import copy
import json
from pathlib import Path
from puzzle_maze.rooms import RoomManager
from puzzle_maze.puzzles import PuzzleManager, Inventory, Door

SAVE_PATH = Path(__file__).parent / 'save.json'

class GameSession:
    def __init__(self):
        self.rooms = RoomManager()
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

    @classmethod
    def load(cls,path=SAVE_PATH):
        try:
            data=json.loads(Path(path).read_text())
            candidate=cls()
            if data['version'] != 1 or data['room'] not in candidate.rooms.rooms:
                raise ValueError('Unsupported save')
            candidate.inventory.keys=data['inventory']
            if any(not isinstance(v,int) or v<0 for v in candidate.inventory.keys.values()):
                raise ValueError('Invalid inventory')
            candidate.snapshots=data['snapshots']
            candidate.completed=set(data['completed']); candidate.visited=set(data['visited'])
            if not (candidate.completed | candidate.visited) <= candidate.rooms.rooms.keys():
                raise ValueError('Invalid room set')
            # Validate every stored room using the same collision rules as gameplay.
            for room,snapshot in candidate.snapshots.items():
                if room not in candidate.rooms.rooms:
                    raise ValueError('Unknown room')
                candidate.enter(room)
                for obj in candidate.puzzles.objects.values():
                    if not candidate.puzzles.tilemap.walkable(*obj.pos):
                        raise ValueError('Invalid object position')
            candidate.enter(data['room'],data['player'])
            if candidate.puzzles.blocked(*data['player']):
                raise ValueError('Blocked player')
            candidate.checkpoint=data['checkpoint']
            candidate.finished=bool(data['finished'])
            return candidate
        except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError):
            return cls()
