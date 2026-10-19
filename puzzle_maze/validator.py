"""Monotone resource-state search, paired with production-action puzzle witnesses.

Access assumptions are authored on actual JSON objects. The search enumerates
all key spending orders in that abstraction; campaign tests separately replay
collision, optics, magnetic weights, timed dashes and the three-stage boss.
"""
from collections import deque,defaultdict
from puzzle_maze.rooms import validate_rooms
from puzzle_maze.solver import solve_boxes

class DungeonValidator:
    def __init__(self,rooms):self.rooms=rooms
    def validate(self):
        validate_rooms(self.rooms)
        if not 16<=len(self.rooms)<=32:raise ValueError('Expected sixteen to thirty-two chambers')
        if {r.get('floor') for r in self.rooms.values()}!={'1F','B1F'}:raise ValueError('Missing floor')
        grants={};locks={};keys_total=0;cost_total=0
        for room in self.rooms.values():
            for enemy in room.get('enemies',[]):
                if enemy['type'] in ('bomb_eater','golem') and not any(o['type']=='supply' for o in room['objects']):
                    raise ValueError('Required bomb encounter has no renewable supply')
            if any(o['type']=='box' and not o.get('metal') for o in room['objects']) and solve_boxes(room) is None:
                raise ValueError('Unsolvable push puzzle')
            for obj in room['objects']:
                keys=obj.get('small_keys',0)+(obj.get('amount',1) if obj['type']=='key' and obj.get('color')=='small' else 0)
                cost=obj.get('cost',1) if obj.get('key')=='small' else 0
                if type(keys) is not int or keys<0 or type(cost) is not int or cost<0:raise ValueError('Invalid key economy')
                keys_total+=keys;cost_total+=cost
                rule=obj.get('progression')
                if (keys or cost) and not rule:raise ValueError('Missing resource access rule')
                if not rule:continue
                name=rule['milestone'];needs=[set(choice) for choice in rule.get('alternatives',[rule['needs']])]
                if name in grants or name in locks:raise ValueError('Duplicate milestone')
                if cost:locks[name]=(cost,needs)
                else:grants[name]=(keys,needs)
        names=set(grants)|set(locks)
        if 'boss_key' not in names:raise ValueError('Missing boss access milestone')
        if any(not all(choice<=names for choice in needs) for _,needs in list(grants.values())+list(locks.values())):raise ValueError('Unknown milestone dependency')
        if not any(o.get('boss_key') for r in self.rooms.values() for o in r['objects']):raise ValueError('Missing Boss Key')
        abilities={o.get('ability') for r in self.rooms.values() for o in r['objects']}
        if not {'gloves','boots','mirror','magnet','map','compass'}<=abilities:raise ValueError('Missing ability reward')
        # Monotone free pickups cannot hurt a run. Paid locks are the branching resource decisions.
        initial=(frozenset(),frozenset(),0);queue=deque([initial]);states={initial};success=set();reverse=defaultdict(set)
        while queue:
            state=queue.popleft();collected,opened,keys=state;available=collected|opened
            if set(locks)<=opened and 'boss_key' in collected:success.add(state)
            out=[]
            for name,(reward,needs) in grants.items():
                if name not in collected and any(choice<=available for choice in needs):out.append((collected|{name},opened,keys+reward))
            for name,(cost,needs) in locks.items():
                if name not in opened and any(choice<=available for choice in needs) and keys>=cost:out.append((collected,opened|{name},keys-cost))
            for new in out:
                reverse[new].add(state)
                if new not in states:states.add(new);queue.append(new)
        winning=set(success);queue=deque(success)
        while queue:
            for previous in reverse[queue.popleft()]:
                if previous not in winning:winning.add(previous);queue.append(previous)
        if states-winning:raise ValueError('A legal spending order creates a permanent dead end')
        return dict(rooms=len(self.rooms),resource_states=len(states),winning_states=len(winning),keys=keys_total,cost=cost_total)
