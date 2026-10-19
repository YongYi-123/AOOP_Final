"""Composable puzzle entities. Doors observe named puzzle conditions."""
from dataclasses import dataclass, field
from enum import Enum
from puzzle_maze.core import CollisionManager, TileMap

@dataclass
class Inventory:
    keys: dict = field(default_factory=dict)
    abilities: set = field(default_factory=set)
    potions: int = 0
    coins: int = 0
    bombs: int = 0
    powder: int = 0
    heart_fragments: int = 0
    carried: str | None = None
    boss_key: bool = False
    flags: set = field(default_factory=set)
    notifications: list = field(default_factory=list)

    def supply_powder(self,amount):
        before=self.powder;self.powder=min(30,self.powder+amount)
        if self.powder>before:self.notifications.append(("powder",f"POWDER +{self.powder-before} / P"))

    def supply_bombs(self,amount):
        before=self.bombs;self.bombs=min(20,self.bombs+amount)
        if self.bombs>before:self.notifications.append(("bomb",f"BOMB +{self.bombs-before} / B"))

    def add(self, color):
        self.keys[color] = self.keys.get(color, 0) + 1
        self.notifications.append(("small_key","KEY +1"))

    def consume(self, color):
        if self.keys.get(color, 0) <= 0:
            return False
        self.keys[color] -= 1
        return True

@dataclass
class PuzzleState:
    active: bool = False
    remaining: float = 0

class PuzzleObject:
    blocking = False

    def __init__(self, data):
        self.data = data
        self.id = data['id']
        self.x, self.y = data['pos']
        self.state = PuzzleState()

    @property
    def pos(self):
        return self.x, self.y

    def interact(self, manager, player, pulse=False):
        return False

class PushableBox(PuzzleObject):
    blocking = True

class PressurePlate(PuzzleObject):
    pass

class Switch(PuzzleObject):
    def interact(self, manager, player, pulse=False):
        if pulse:
            return False
        self.state.active = not self.state.active
        return True

class Door(PuzzleObject):
    blocking = True

    def __init__(self, data):
        super().__init__(data)
        self.unlocked = 'key' not in data
        self.latched = False

    def interact(self, manager, player, pulse=False):
        if pulse or self.unlocked:
            return False
        cost=self.data.get('cost',1)
        key=self.data['key']
        if key=='boss':
            if not manager.inventory.boss_key:return False
            self.unlocked=True;return True
        if manager.inventory.keys.get(key,0)>=cost:
            manager.inventory.keys[key]-=cost
            self.unlocked = True
            return True
        return False

class GateControl(Door):
    blocking = False

class Key(PuzzleObject):
    pass

FACTORY = {'box': PushableBox, 'plate': PressurePlate, 'switch': Switch, 'door': Door, 'gate_control': GateControl, 'key': Key}

class PuzzleManager(CollisionManager):
    def __init__(self, room, inventory=None):
        super().__init__(TileMap(room['tiles']))
        self.room = room
        self.inventory = inventory if inventory is not None else Inventory()
        self.objects = {d['id']: FACTORY[d['type']](d) for d in room['objects']}
        self.beams=[]
        self.occupants=set()
        self.player_position=None
        self.defeated=set()
        self.chest_events=[]
        self.update(0, None)

    def blocked(self, x, y, ignore=None):
        remote_closed=any(tuple(e['pos'])==(x,y) and e.get('entrance')=='remote' and not set(e.get('flag_requires',[])) <= self.inventory.flags for e in self.room.get('exits',[]))
        return remote_closed or not self.tilemap.walkable(x, y) or any(o.id != ignore and o.pos == (x, y) and o.blocking and not o.state.active for o in self.objects.values())

    def can_enter(self, x, y):
        return not self.blocked(x, y)

    def move(self, player, dx, dy):
        if abs(dx) + abs(dy) != 1:
            return False
        player.facing = dx, dy
        dest = player.x + dx, player.y + dy
        box = next((o for o in self.objects.values() if isinstance(o, PushableBox) and o.pos == dest), None)
        if box:
            if box.data.get('magnetic_only'):
                player.moving=False;return False
            if box.data.get('heavy') and 'gloves' not in self.inventory.abilities:
                player.moving=False
                return False
            if self.blocked(box.x + dx, box.y + dy):
                player.moving = False
                return False
            box.x += dx
            box.y += dy
        moved = super().move(player, dx, dy)
        self.update(0, player)
        return moved

    def interact(self, player, pulse=False):
        target = player.x + player.facing[0], player.y + player.facing[1]
        candidates = [o for o in self.objects.values() if o.pos == target]
        candidates += [o for o in self.objects.values() if abs(o.x-player.x)+abs(o.y-player.y) <= 1 and o not in candidates]
        for obj in candidates:
            if obj.interact(self, player, pulse):
                self.update(0, player)
                return obj.id
        return None

    def update(self, dt, player):
        self.player_position=(player.x,player.y) if player is not None else None
        for obj in self.objects.values():
            if isinstance(obj, Key) and player and obj.pos == (player.x, player.y) and not obj.state.active and all(self.condition(i) for i in obj.data.get("requires",[])):
                for _ in range(obj.data.get("amount",1)):self.inventory.add(obj.data['color'])
                obj.state.active = True
            if isinstance(obj, PressurePlate):
                obj.state.active = (player is not None and obj.pos == (player.x, player.y)) or any(isinstance(b, PushableBox) and b.pos == obj.pos for b in self.objects.values())
        self.update_special(dt)
        self.trace_light()
        for obj in self.objects.values():
            if isinstance(obj, Door):
                powered = all(self.objects[i].state.active or (isinstance(self.objects[i], Door) and self.objects[i].latched) for i in obj.data.get('requires', [])) and obj.unlocked
                # Non-timed doors latch: the introductory player plate remains fair.
                timed = any(self.objects[i].data['type'] == 'timed' for i in obj.data.get('requires', []))
                if powered and not timed:
                    obj.latched = True
                if timed and player is not None and player.x > obj.x:
                    obj.latched = True  # Crossing memory powers later stages, without holding this gate open.
                occupied = player is not None and obj.pos == (player.x, player.y) or any(isinstance(b, PushableBox) and b.pos == obj.pos for b in self.objects.values())
                obj.state.active = powered or (obj.latched and (not timed or obj.data.get('reversible',False))) or bool(occupied) or obj.pos in self.occupants

        for obj in self.objects.values():
            if isinstance(obj, Chest):
                obj.advance(self, dt)

    def update_special(self, dt):
        for obj in self.objects.values():
            if isinstance(obj, CrackedWall) and obj.state.remaining>0:
                obj.state.remaining=max(0.,obj.state.remaining-dt)
                if obj.state.remaining<1e-9:obj.state.remaining=0.;obj.state.active=True
            if isinstance(obj, RemoteRelay):obj.state.active=all(i in self.inventory.flags for i in obj.data.get("flags",[]))
            if isinstance(obj, TimedSwitch):
                obj.state.remaining = max(0, obj.state.remaining - dt)
                obj.state.active = obj.state.remaining > 0

    def condition(self, name):
        obj=self.objects[name]
        return obj.state.active or isinstance(obj,Door) and obj.latched

    def trace_light(self):
        self.beams=[]
        for obj in self.objects.values():
            if isinstance(obj,Receiver):obj.state.active=False
        for source in self.objects.values():
            if not isinstance(source,LightSource) or not all(self.condition(i) for i in source.data.get('requires',[])):continue
            x,y=source.pos;dx,dy=source.data['direction'];seen=set()
            for _ in range(120):
                start=(x,y);x+=dx;y+=dy
                if (x,y,dx,dy) in seen or not self.tilemap.walkable(x,y):break
                seen.add((x,y,dx,dy));self.beams.append((start,(x,y)))
                obj=next((o for o in self.objects.values() if o.pos==(x,y)),None)
                if isinstance(obj,Receiver):obj.state.active=True;break
                if isinstance(obj,Reflector):
                    dx,dy=(-dy,-dx) if obj.state.active else (dy,dx)
                elif obj and obj.blocking and not obj.state.active:break

    def magnet(self, player, attract=False):
        if 'magnet' not in self.inventory.abilities:return None
        dx,dy=player.facing
        for distance in range(1,7):
            x,y=player.x+dx*distance,player.y+dy*distance
            if not (0<=y<len(self.tilemap.rows) and 0<=x<len(self.tilemap.rows[0])) or self.tilemap.rows[y][x] in '#O':return None
            box=next((o for o in self.objects.values() if isinstance(o,PushableBox) and o.data.get('metal') and o.pos==(x,y)),None)
            if box:
                step=-1 if attract else 1
                dest=box.x+dx*step,box.y+dy*step
                if dest==(player.x,player.y) or self.blocked(*dest):return None
                box.x,box.y=dest;self.update(0,player)
                return box.id
        return None

    @property
    def solved(self):
        return all(self.objects[i].state.active for i in self.room['goal'])

class SecretPassage(PuzzleObject):
    blocking = True

    def interact(self, manager, player, pulse=False):
        if pulse and not self.state.active:
            self.state.active = True
            return True
        return False

class TimedSwitch(Switch):
    def interact(self, manager, player, pulse=False):
        if pulse:
            return False
        self.state.remaining = self.data['duration']
        self.state.active = True
        return True

FACTORY.update(secret=SecretPassage, timed=TimedSwitch)

class ChestPhase(str, Enum):
    HIDDEN = 'hidden'
    SPAWNING = 'spawning'
    AVAILABLE = 'available'
    OPENED = 'opened'

class Chest(PuzzleObject):
    spawn_duration = .45

    def __init__(self, data):
        super().__init__(data)
        self.phase = ChestPhase.HIDDEN if data.get('hidden') else ChestPhase.AVAILABLE
        self.spawn_time = 0.

    @property
    def visible(self):
        return self.phase != ChestPhase.HIDDEN

    def advance(self, manager, dt):
        if self.state.active:
            self.phase = ChestPhase.OPENED
            self.spawn_time = 0.
        elif self.phase == ChestPhase.HIDDEN:
            clear_spawn=(self.pos!=manager.player_position and self.pos not in manager.occupants
                         and manager.tilemap.walkable(*self.pos)
                         and not any(o is not self and o.pos==self.pos and o.blocking and not o.state.active for o in manager.objects.values()))
            if (clear_spawn and set(self.data.get('enemy_requires',[])) <= manager.defeated
                    and all(manager.condition(i) for i in self.data.get('requires', []))
                    and set(self.data.get('ability_requires', [])) <= manager.inventory.abilities
                    and set(self.data.get('flag_requires', [])) <= manager.inventory.flags
                    and self.data.get('crystal_color', 'blue' if 'crystal_blue' in manager.inventory.flags else 'red') == ('blue' if 'crystal_blue' in manager.inventory.flags else 'red')):
                self.phase = ChestPhase.SPAWNING
                self.spawn_time = self.spawn_duration
                manager.chest_events.append(self.id)
        elif self.phase == ChestPhase.SPAWNING:
            self.spawn_time = max(0., self.spawn_time - dt)
            if self.spawn_time == 0:
                self.phase = ChestPhase.AVAILABLE

    def interact(self, manager, player, pulse=False):
        if pulse or self.state.active or self.phase not in (ChestPhase.AVAILABLE, ChestPhase.OPENED) or (not self.data.get("hidden") and not all(manager.condition(i) for i in self.data.get("requires",[]))):
            return False
        ability=self.data.get('ability')
        if ability:
            manager.inventory.abilities.add(ability)
            manager.inventory.notifications.append((ability,{"boots":"DASH BOOTS / SHIFT","gloves":"GLOVES / PUSH","mirror":"MIRROR / E","magnet":"MAGNET / F, SPACE","map":"DUNGEON MAP / TAB","compass":"COMPASS / TAB","powder":"MAGIC POWDER / P"}[ability]))
        manager.inventory.supply_bombs(self.data.get("bombs",0))
        for _ in range(self.data.get("small_keys",0)):manager.inventory.add("small")
        if self.data.get("boss_key"):
            manager.inventory.boss_key=True;manager.inventory.notifications.append(("boss_key","BOSS KEY"))
        manager.inventory.supply_powder(self.data.get('powder',0))
        for treasure in self.data.get('loot',[]):
            if hasattr(manager,'grant_treasure'):manager.grant_treasure(self.id,treasure)
        manager.inventory.potions+=self.data.get('potions',0)
        manager.inventory.coins+=self.data.get('coins',0)
        self.state.active=True
        self.phase=ChestPhase.OPENED
        return True

class LightSource(PuzzleObject):
    pass

class Receiver(PuzzleObject):
    pass

class Reflector(PuzzleObject):
    def interact(self,manager,player,pulse=False):
        if 'mirror' not in manager.inventory.abilities:return False
        self.state.active=not self.state.active
        return True

FACTORY.update(chest=Chest, light=LightSource, receiver=Receiver, reflector=Reflector)

class CombatSeal(PuzzleObject):
    pass

FACTORY['combat']=CombatSeal


class EntrancePhase(str,Enum):
    SEALED='sealed'
    REVEALING='revealing'
    OPEN='open'

class CrackedWall(PuzzleObject):
    blocking=True
    @property
    def phase(self):
        return EntrancePhase.OPEN if self.state.active else EntrancePhase.REVEALING if self.state.remaining>0 else EntrancePhase.SEALED
    def blast(self,dt=0):
        if self.phase!=EntrancePhase.SEALED:return False
        duration=self.data.get('duration',0)
        if duration:self.state.remaining=duration+dt
        else:self.state.active=True
        return True

class BlastSwitch(PuzzleObject):
    pass

class BombSupply(PuzzleObject):
    def interact(self,manager,player,pulse=False):
        if pulse or manager.inventory.bombs>=8:return False
        manager.inventory.supply_bombs(8-manager.inventory.bombs);return True

class DashSwitch(PuzzleObject):
    def interact(self,manager,player,pulse=False):return False

class RemoteRelay(PuzzleObject):
    pass

class RemoteSwitch(Switch):
    def interact(self,manager,player,pulse=False):
        if pulse or self.state.active or not all(manager.condition(i) for i in self.data.get("requires",[])):return False
        self.state.active=True;manager.inventory.flags.add(self.data['flag']);return True

FACTORY.update(cracked=CrackedWall,blast_switch=BlastSwitch,supply=BombSupply,dash_switch=DashSwitch,relay=RemoteRelay,remote=RemoteSwitch)
