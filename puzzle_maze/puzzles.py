"""Composable puzzle entities. Doors observe named puzzle conditions."""
from dataclasses import dataclass, field
from puzzle_maze.core import CollisionManager, TileMap

@dataclass
class Inventory:
    keys: dict = field(default_factory=dict)

    def add(self, color):
        self.keys[color] = self.keys.get(color, 0) + 1

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
        if manager.inventory.consume(self.data['key']):
            self.unlocked = True
            return True
        return False

class Key(PuzzleObject):
    pass

FACTORY = {'box': PushableBox, 'plate': PressurePlate, 'switch': Switch, 'door': Door, 'key': Key}

class PuzzleManager(CollisionManager):
    def __init__(self, room, inventory=None):
        super().__init__(TileMap(room['tiles']))
        self.room = room
        self.inventory = inventory if inventory is not None else Inventory()
        self.objects = {d['id']: FACTORY[d['type']](d) for d in room['objects']}
        self.update(0, None)

    def blocked(self, x, y, ignore=None):
        return not self.tilemap.walkable(x, y) or any(o.id != ignore and o.pos == (x, y) and o.blocking and not o.state.active for o in self.objects.values())

    def can_enter(self, x, y):
        return not self.blocked(x, y)

    def move(self, player, dx, dy):
        if abs(dx) + abs(dy) != 1:
            return False
        player.facing = dx, dy
        dest = player.x + dx, player.y + dy
        box = next((o for o in self.objects.values() if isinstance(o, PushableBox) and o.pos == dest), None)
        if box:
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
        for obj in self.objects.values():
            if isinstance(obj, Key) and player and obj.pos == (player.x, player.y) and not obj.state.active:
                self.inventory.add(obj.data['color'])
                obj.state.active = True
            if isinstance(obj, PressurePlate):
                obj.state.active = (player is not None and obj.pos == (player.x, player.y)) or any(isinstance(b, PushableBox) and b.pos == obj.pos for b in self.objects.values())
        self.update_special(dt)
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
                obj.state.active = powered or (obj.latched and not timed) or bool(occupied)

    def update_special(self, dt):
        for obj in self.objects.values():
            if isinstance(obj, TimedSwitch):
                obj.state.remaining = max(0, obj.state.remaining - dt)
                obj.state.active = obj.state.remaining > 0

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
