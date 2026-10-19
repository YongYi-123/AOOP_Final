"""Session owns room snapshots, checkpoint reset, and private atomic saves."""
import copy
import json
import math
from pathlib import Path
from puzzle_maze.rooms import RoomManager
from puzzle_maze.combat import CombatManager
from puzzle_maze.exploration import Exploration
from puzzle_maze.weapons import WEAPONS
from puzzle_maze.migration import LayoutMigration
from puzzle_maze.puzzles import PuzzleManager, Inventory, Door, Chest, ChestPhase

SAVE_PATH = Path(__file__).parent / 'save_v2.json'

class GameSession:
    def __init__(self, rooms=None):
        self.rooms = RoomManager(rooms)
        self.inventory = Inventory()
        self.snapshots = {}
        self.completed = set()
        self.visited = {'r1'}
        self.finished = False
        self.migration_notice=""
        self.dash_cooldown = 0
        self.encounters = {}
        self.exploration=Exploration()
        self.enter('r1')

    def make_puzzles(self,room):
        return PuzzleManager(room,self.inventory)

    def prepare_loaded_save(self,data):return data

    def save_extension(self):return {}
    def load_extension(self,data):pass

    def capture(self):
        return {name: dict(pos=list(o.pos), active=o.state.active,
                           remaining=o.state.remaining,
                           unlocked=getattr(o,'unlocked',False), latched=getattr(o,'latched',False),
                           **({'chest_phase':o.phase.value,'spawn_time':o.spawn_time} if isinstance(o,Chest) else {}))
                for name,o in self.puzzles.objects.items()}

    def restore(self, snapshot):
        for name, values in snapshot.items():
            obj=self.puzzles.objects[name]
            obj.x,obj.y=values['pos']
            obj.state.active=values['active']
            obj.state.remaining=values['remaining']
            if isinstance(obj,Chest):
                obj.phase=ChestPhase(values.get('chest_phase','opened' if obj.state.active else 'hidden' if obj.data.get('hidden') else 'available'))
                obj.spawn_time=values.get('spawn_time',0.)
            if isinstance(obj,Door):
                obj.unlocked=values['unlocked']; obj.latched=values['latched']
        self.puzzles.update(0,self.player)

    def enter(self, name, arrival=None):
        weapon=self.player.weapon if hasattr(self,"player") else WEAPONS["basic_sword"]()
        health=self.player.hp if hasattr(self,"player") else 5
        self.player=self.rooms.enter(name,arrival)
        self.player.max_hp=5+min(3,self.inventory.heart_fragments//4)
        self.player.hp=min(health,self.player.max_hp)
        self.player.weapon=weapon
        self.puzzles=self.make_puzzles(self.rooms.data)
        if name in self.snapshots:
            self.restore(self.snapshots[name])
        self.combat=CombatManager(self.rooms.data,self.puzzles,self.player)
        if name in self.encounters:self.combat.restore(self.encounters[name])
        # Restored crates/enemies may have moved onto a return entrance.
        from collections import deque
        occupied={e.pos for e in self.combat.enemies if e.hp>0 and not e.dormant}
        start=(self.player.x,self.player.y);queue=deque([start]);seen={start}
        while queue:
            pos=queue.popleft()
            if self.puzzles.can_enter(*pos) and pos not in occupied:
                self.player.x,self.player.y=pos
                break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt=pos[0]+dx,pos[1]+dy
                if nxt not in seen and self.puzzles.tilemap.walkable(*nxt):
                    seen.add(nxt);queue.append(nxt)
        else:
            raise ValueError('No safe room landing')
        self.checkpoint = dict(hp=self.player.hp, combat=copy.deepcopy(self.combat.capture()),inventory=copy.deepcopy(self.inventory.keys), abilities=sorted(self.inventory.abilities), potions=self.inventory.potions, coins=self.inventory.coins, powder=self.inventory.powder,heart_fragments=self.inventory.heart_fragments,carried=self.inventory.carried,bombs=self.inventory.bombs,boss_key=self.inventory.boss_key,flags=sorted(self.inventory.flags),objects=self.capture(), pos=[self.player.x,self.player.y])
        self.visited.add(name)
        self.exploration.reveal(name,self.puzzles,self.player)

    def reset(self):
        self.inventory.keys=copy.deepcopy(self.checkpoint['inventory'])
        self.inventory.abilities=set(self.checkpoint['abilities'])
        self.inventory.potions=self.checkpoint['potions']
        self.inventory.coins=self.checkpoint['coins']
        self.inventory.powder=self.checkpoint.get('powder',0)
        self.inventory.heart_fragments=self.checkpoint.get('heart_fragments',0)
        self.inventory.carried=self.checkpoint.get('carried')
        self.player.max_hp=5+min(3,self.inventory.heart_fragments//4)
        self.inventory.bombs=self.checkpoint.get('bombs',0)
        self.inventory.boss_key=self.checkpoint.get('boss_key',False)
        self.inventory.flags=set(self.checkpoint.get('flags',[]))
        self.inventory.notifications.clear()
        self.dash_cooldown=0
        self.player.hp=self.checkpoint['hp']
        self.player.invulnerable=0
        self.player.attack_cooldown=0
        self.player.x,self.player.y=self.checkpoint['pos']
        self.player.moving=False
        self.restore(self.checkpoint['objects'])
        self.combat.restore(copy.deepcopy(self.checkpoint['combat']))
        # Remove completion only when checkpoint itself was unsolved.
        if not self.puzzles.solved:
            self.completed.discard(self.rooms.current)

    def tick(self, dt):
        self.dash_cooldown=max(0,self.dash_cooldown-dt)
        self.combat.player=self.player
        self.combat.update(dt)
        self.puzzles.defeated={e.id for e in self.combat.enemies if e.hp<=0}
        self.puzzles.occupants={e.pos for e in self.combat.enemies if e.hp>0 and not e.dormant}
        for obj in self.puzzles.objects.values():
            if obj.data['type']=='combat':obj.state.active=self.combat.cleared
        self.puzzles.update(dt,self.player)
        self.exploration.reveal(self.rooms.current,self.puzzles,self.player)
        if self.puzzles.solved:
            self.completed.add(self.rooms.current)

    def can_enter(self,x,y):
        return self.puzzles.can_enter(x,y) and not any(e.hp>0 and not e.dormant and e.pos==(x,y) for e in self.combat.enemies)

    def move(self, dx, dy):
        if self.player.hp<=0 or abs(dx)+abs(dy)!=1:return False
        self.player.facing=(dx,dy)
        target=self.player.x+dx,self.player.y+dy
        occupied={e.pos for e in self.combat.enemies if e.hp>0 and not e.dormant}
        box=next((o for o in self.puzzles.objects.values() if o.data['type']=='box' and o.pos==target),None)
        if target in occupied or box is not None and (box.x+dx,box.y+dy) in occupied:
            self.player.moving=False
            return False
        moved=self.puzzles.move(self.player,dx,dy)
        self.tick(0)
        return moved

    def dash(self):
        if self.player.hp<=0:return 0
        if 'boots' not in self.inventory.abilities or self.dash_cooldown>0:return 0
        dx,dy=self.player.facing
        moved=0
        for _ in range(3):
            if not self.can_enter(self.player.x+dx,self.player.y+dy):break
            self.player.x+=dx;self.player.y+=dy;moved+=1
            self.puzzles.update(0,self.player)
        if moved:
            self.dash_cooldown=1.2
            self.player.invulnerable=max(self.player.invulnerable,.3)
        self.tick(0)
        return moved

    def attack(self):
        return self.combat.attack()

    def heal(self):
        return self.combat.heal()

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
        self.encounters[self.rooms.current]=copy.deepcopy(self.combat.capture())
        self.enter(e['target'],e['arrival'])
        return True

    def save(self, path=SAVE_PATH):
        self.encounters[self.rooms.current]=copy.deepcopy(self.combat.capture())
        self.snapshots[self.rooms.current]=self.capture()
        data=dict(content_revision=self.rooms.data.get('content_revision',self.rooms.revision),extension=self.save_extension(),powder=self.inventory.powder,heart_fragments=self.inventory.heart_fragments,carried=self.inventory.carried,bombs=self.inventory.bombs,boss_key=self.inventory.boss_key,flags=sorted(self.inventory.flags),bomb_state=self.bombs.capture() if hasattr(self,"bombs") else {},version=2, facing=list(self.player.facing), attack_facing=list(self.player.attack_facing), map_revision=self.rooms.revision, weapon=self.player.weapon.id, dash_cooldown=self.dash_cooldown, player_status={k:getattr(self.player,k) for k in ('invulnerable','attack_cooldown','attack_flash')}, explored=self.exploration.capture(), hp=self.player.hp, encounters=self.encounters, abilities=sorted(self.inventory.abilities), potions=self.inventory.potions, coins=self.inventory.coins, room=self.rooms.current, player=[self.player.x,self.player.y],
                  inventory=self.inventory.keys, snapshots=self.snapshots,
                  completed=sorted(self.completed), visited=sorted(self.visited),
                  finished=self.finished, checkpoint=self.checkpoint)
        path=Path(path)
        if path.exists() and self.rooms.revision=='2.1':
            try:old=json.loads(path.read_text())
            except (ValueError,OSError):old={}
            if old.get('version')==2 and old.get('map_revision','2.0')=='2.0':
                backup=path.with_name(path.name+'.v20.bak')
                if not backup.exists():backup.write_bytes(path.read_bytes())
        tmp=path.with_suffix(path.suffix+'.tmp')
        tmp.write_text(json.dumps(data,indent=2)+'\n')
        tmp.replace(path)

    @staticmethod
    def validate_growth(data):
        abilities=data['abilities']
        if not isinstance(abilities,list) or not all(isinstance(a,str) and a in ('gloves','boots','mirror','magnet','map','compass','powder') for a in abilities):
            raise ValueError('Unknown ability')
        if any(type(data[k]) is not int or data[k]<0 for k in ('potions','coins')):
            raise ValueError('Invalid supplies')
        bombs=data.get('bombs',0);boss_key=data.get('boss_key',False);flags=data.get('flags',[])
        if type(data.get('powder',0)) is not int or not 0<=data.get('powder',0)<=30 or type(data.get('heart_fragments',0)) is not int or not 0<=data.get('heart_fragments',0)<=100 or data.get('carried') is not None and not isinstance(data['carried'],str):raise ValueError('Invalid advanced inventory')
        if type(bombs) is not int or not 0<=bombs<=20 or type(boss_key) is not bool or not isinstance(flags,list) or any(not isinstance(f,str) for f in flags):
            raise ValueError('Invalid dungeon checkpoint supplies')

    @staticmethod
    def validate_inventory(keys):
        if not isinstance(keys, dict) or any(not isinstance(k, str) or type(v) is not int or v < 0 for k, v in keys.items()):
            raise ValueError('Invalid inventory')

    @staticmethod
    def validate_position(pos, tilemap):
        if not isinstance(pos, list) or len(pos) != 2 or any(type(v) is not int for v in pos) or not tilemap.walkable(*pos):
            raise ValueError('Invalid position')

    @staticmethod
    def add_optional_objects(room,snapshot):
        if not isinstance(snapshot,dict):return
        for obj in room['objects']:
            if obj['id'] not in snapshot and obj.get('optional') and obj['type']=='chest':
                snapshot[obj['id']]=dict(pos=list(obj['pos']),active=False,remaining=0,unlocked=False,latched=False)

    @classmethod
    def validate_snapshot(cls, room, snapshot):
        manager = PuzzleManager(room)
        if not isinstance(snapshot, dict) or set(snapshot) != set(manager.objects):
            raise ValueError('Incomplete snapshot')
        occupied = set()
        for name, obj in manager.objects.items():
            values = snapshot[name]
            cls.validate_position(values['pos'], manager.tilemap)
            if obj.data['type'] not in ('box','pot') and values['pos'] != obj.data['pos']:
                raise ValueError('Moved static object')
            for flag in ('active', 'unlocked', 'latched'):
                if type(values[flag]) is not bool:
                    raise ValueError('Invalid state')
            if isinstance(obj,Chest) and 'chest_phase' in values:
                phase=ChestPhase(values['chest_phase'])
                elapsed=values.get('spawn_time',0.)
                if not isinstance(elapsed,(int,float)) or not math.isfinite(elapsed) or not 0<=elapsed<=obj.spawn_duration:
                    raise ValueError('Invalid chest spawn timer')
                if values['active'] != (phase == ChestPhase.OPENED):
                    raise ValueError('Inconsistent chest state')
                if phase != ChestPhase.SPAWNING and elapsed != 0:
                    raise ValueError('Unexpected chest timer')
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
            revision=data.get('map_revision','2.0')
            if revision!=candidate.rooms.revision:
                if revision!='2.0' or candidate.rooms.revision!='2.1':raise ValueError('Unsupported map revision')
                from puzzle_maze.rooms import load_rooms, MAP_PATH
                legacy=load_rooms(MAP_PATH.with_name('dungeon_v20.json'))
                data=LayoutMigration(candidate.rooms.rooms,legacy).apply(data)
                candidate.migration_notice='Loaded 2.0 progress into compact 2.1 chambers.'
            if data['version'] != 2 or data['room'] not in candidate.rooms.rooms:
                raise ValueError('Unsupported save')
            data=candidate.prepare_loaded_save(data)
            candidate.exploration.restore(data.get('explored',{}),candidate.rooms.rooms)
            candidate.inventory.powder=data.get('powder',0);candidate.inventory.heart_fragments=data.get('heart_fragments',0);candidate.inventory.carried=data.get('carried')
            candidate.inventory.keys=data['inventory']
            bombs=data.get('bombs',0);boss_key=data.get('boss_key',False);flags=data.get('flags',[])
            if type(data.get('powder',0)) is not int or not 0<=data.get('powder',0)<=30 or type(data.get('heart_fragments',0)) is not int or not 0<=data.get('heart_fragments',0)<=100 or data.get('carried') is not None and not isinstance(data['carried'],str):raise ValueError('Invalid advanced inventory')
            if type(bombs) is not int or not 0<=bombs<=20 or type(boss_key) is not bool or not isinstance(flags,list) or any(not isinstance(f,str) for f in flags):raise ValueError('Invalid dungeon supplies')
            candidate.inventory.bombs=bombs;candidate.inventory.boss_key=boss_key;candidate.inventory.flags=set(flags)
            candidate.inventory.abilities=set(data['abilities'])
            candidate.inventory.potions=data['potions'];candidate.inventory.coins=data['coins']
            cls.validate_growth(data)
            cls.validate_inventory(candidate.inventory.keys)
            candidate.snapshots=data['snapshots']
            candidate.encounters=data.get('encounters',{})
            hp=data.get('hp',5)
            if type(hp) is not int or not 0<=hp<=5+min(3,candidate.inventory.heart_fragments//4):raise ValueError('Invalid HP')
            for room,snapshot in candidate.encounters.items():
                if room not in candidate.rooms.rooms:raise ValueError('Invalid encounter room')
                CombatManager(candidate.rooms.rooms[room],PuzzleManager(candidate.rooms.rooms[room]),candidate.player).restore(snapshot)
            candidate.completed=set(data['completed']); candidate.visited=set(data['visited'])
            if not (candidate.completed | candidate.visited) <= candidate.rooms.rooms.keys():
                raise ValueError('Invalid room set')
            # Validate every stored room using the same collision rules as gameplay.
            for room,snapshot in candidate.snapshots.items():
                if room not in candidate.rooms.rooms:
                    raise ValueError('Unknown room')
                cls.add_optional_objects(candidate.rooms.rooms[room],snapshot)
                cls.validate_snapshot(candidate.rooms.rooms[room], snapshot)
            cls.validate_position(data['player'], PuzzleManager(candidate.rooms.rooms[data['room']]).tilemap)
            candidate.enter(data['room'],data['player'])
            candidate.player.hp=hp
            weapon=data.get("weapon","basic_sword")
            if weapon not in WEAPONS:raise ValueError("Unknown weapon")
            candidate.player.weapon=WEAPONS[weapon]()
            for name in ('facing','attack_facing'):
                direction=data.get(name,[0,1])
                if direction not in ([1,0],[-1,0],[0,1],[0,-1]):raise ValueError('Invalid facing')
                setattr(candidate.player,name,tuple(direction))
            status=data.get('player_status',{})
            if not isinstance(status,dict):raise ValueError('Invalid player timers')
            for name in ('invulnerable','attack_cooldown','attack_flash','dash_cooldown'):
                value=data.get(name,0) if name=='dash_cooldown' else status.get(name,0)
                if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<={"invulnerable":1.1,"attack_cooldown":candidate.player.weapon.cooldown,"attack_flash":candidate.player.weapon.swing_duration,"dash_cooldown":1.2}[name]:raise ValueError('Invalid player timer')
                setattr(candidate if name=='dash_cooldown' else candidate.player,name,value)
            if candidate.puzzles.blocked(*data['player']):
                raise ValueError('Blocked player')
            checkpoint = data['checkpoint']
            cls.validate_inventory(checkpoint['inventory'])
            cls.validate_growth(checkpoint)
            cls.add_optional_objects(candidate.rooms.data,checkpoint['objects'])
            cls.validate_snapshot(candidate.rooms.data, checkpoint['objects'])
            cls.validate_position(checkpoint['pos'], candidate.puzzles.tilemap)
            check_manager = PuzzleManager(candidate.rooms.data)
            for name, values in checkpoint['objects'].items():
                obj = check_manager.objects[name]
                obj.x, obj.y = values['pos']
                obj.state.active = values['active']
            if check_manager.blocked(*checkpoint['pos']):
                raise ValueError('Blocked checkpoint')
            if type(checkpoint['hp']) is not int or not 0<=checkpoint['hp']<=5+min(3,checkpoint.get('heart_fragments',0)//4):raise ValueError('Invalid checkpoint HP')
            CombatManager(candidate.rooms.data, candidate.puzzles, candidate.player).restore(checkpoint['combat'])
            candidate.checkpoint=checkpoint
            candidate.finished=bool(data['finished'])
            candidate.load_extension(data.get('extension',{}))
            if hasattr(candidate,'bombs'):candidate.bombs.restore(data.get('bomb_state',{}))
            return candidate
        except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError):
            return cls()
