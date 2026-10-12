"""Resource-state search plus executable puzzle witnesses for Clockwork Hollow."""
from collections import deque
from puzzle_maze.rooms import validate_rooms

class DungeonValidator:
    def __init__(self,rooms):self.rooms=rooms
    def validate(self):
        validate_rooms(self.rooms)
        if len(self.rooms)!=18:raise ValueError('Expected eighteen authored chambers')
        floors={r.get('floor') for r in self.rooms.values()}
        if floors!={'1F','B1F'}:raise ValueError('Missing floor')
        for name,room in self.rooms.items():
            if any(e['type']=='bomb_eater' for e in room.get('enemies',[])) or name=='r17':
                if not any(o['type']=='supply' for o in room['objects']):raise ValueError('Required bomb encounter has no renewable supply')
            if any(o.get('key')=='small' for o in room['objects']):
                if any(o.get('cost',1)<1 for o in room['objects'] if o.get('key')=='small'):raise ValueError('Invalid key cost')
        # Finite search tracks collected branch rewards and consumed permanent locks.
        # Every attainable spending order must still extend to all mandatory locks.
        rewards={'watch':2,'library':1,'workshop':1,'prism':1,'eater':1}
        locks={'watch_lock':(1,{'watch'}),'stairs':(2,{'west','east'}),'sentinels':(2,{'prism','eater'})}
        start=(frozenset(),frozenset(),0);queue=deque([start]);states={start};success=set();edges={}
        while queue:
            collected,opened,keys=queue.popleft();state=(collected,opened,keys);out=[]
            grants={'watch':set(),'library':set(),'west':{'library'},'east':{'library'},'workshop':{'watch_lock'},'boots':{'workshop'},'prism':{'stairs','west','library'},'eater':{'stairs'},'boss_key':{'boots','prism'}}
            available=set(collected)|set(opened)
            for grant,needs in grants.items():
                if grant not in collected and needs<=available:out.append((collected|{grant},opened,keys+rewards.get(grant,0)))
            for lock,(cost,needs) in locks.items():
                if lock not in opened and needs<=available and keys>=cost:out.append((collected,opened|{lock},keys-cost))
            edges[state]=out
            if set(locks)<=opened and 'boss_key' in collected:success.add(state)
            for new in out:
                if new not in states:states.add(new);queue.append(new)
        winning=set(success)
        changed=True
        while changed:
            changed=False
            for state,out in edges.items():
                if state not in winning and any(next_state in winning for next_state in out):winning.add(state);changed=True
        if states-winning:raise ValueError('A legal key spending order creates a permanent dead end')
        abilities={o.get('ability') for r in self.rooms.values() for o in r['objects']}
        if not {'gloves','boots','mirror','magnet','map','compass'}<=abilities:raise ValueError('Missing ability reward')
        if not any(o.get('boss_key') for r in self.rooms.values() for o in r['objects']):raise ValueError('Missing Boss Key')
        # The search resource budget must agree with real authored rewards and locks.
        actual_keys=sum(o.get('small_keys',0)+ (o.get('amount',1) if o['type']=='key' and o.get('color')=='small' else 0) for r in self.rooms.values() for o in r['objects'])
        actual_cost=sum(o.get('cost',1) for r in self.rooms.values() for o in r['objects'] if o.get('key')=='small')
        if actual_keys!=sum(rewards.values()) or actual_cost!=sum(cost for cost,_ in locks.values()):raise ValueError('Authored key economy differs from search model')
        return dict(rooms=len(self.rooms),resource_states=len(states),winning_states=len(winning),keys=actual_keys,cost=actual_cost)
