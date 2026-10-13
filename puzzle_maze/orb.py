"""A single recoverable Iron Orb persists independently of room-local pots."""
from dataclasses import dataclass,asdict

@dataclass
class IronOrb:
    room:str='r20'
    x:int=10
    y:int=11
    carried:bool=False

    @property
    def pos(self):return self.x,self.y
    def capture(self):return asdict(self)
    @classmethod
    def restore(cls,data,rooms):
        from puzzle_maze.core import TileMap
        if not isinstance(data,dict) or set(data)!={'room','x','y','carried'}:raise ValueError('Invalid orb record')
        if data['room'] not in rooms or type(data['carried']) is not bool or any(type(data[k]) is not int for k in ('x','y')):raise ValueError('Invalid orb location')
        if not TileMap(rooms[data['room']]['tiles']).walkable(data['x'],data['y']):raise ValueError('Orb inside wall')
        return cls(**data)
    def recall(self):
        self.room,self.x,self.y,self.carried='r20',10,11,False
    def interact(self,session):
        p=session.player
        if p.hp<=0 or session.inventory.carried is not None:return False
        if self.carried:
            dest=p.x+p.facing[0],p.y+p.facing[1]
            if not session.can_enter(*dest):return False
            self.room=session.rooms.current;self.x,self.y=dest;self.carried=False
            session.combat.events.append('pot_lift');return True
        if self.room!=session.rooms.current or abs(self.x-p.x)+abs(self.y-p.y)>1 or 'gloves' not in session.inventory.abilities:return False
        self.carried=True;self.room=session.rooms.current;self.x,self.y=p.x,p.y
        session.combat.events.append('pot_lift');return True
    def throw(self,session):
        if not self.carried or session.player.hp<=0:return False
        from puzzle_maze.advanced_puzzles import DestructiblePillar
        p=session.player;dx,dy=p.facing;impact=p.x,p.y
        for distance in range(1,5):
            dest=p.x+dx*distance,p.y+dy*distance
            pillar=next((o for o in session.puzzles.objects.values() if isinstance(o,DestructiblePillar) and not o.state.active and o.pos==dest),None)
            if pillar:
                pillar.state.active=True;session.inventory.flags.add(pillar.data['flag'])
                session.effects.append(('shards',dest,.7));session.combat.events.append('pot_break');break
            if session.puzzles.blocked(*dest):break
            enemy=next((e for e in session.combat.enemies if e.hp>0 and not e.dormant and e.pos==dest),None)
            if enemy:enemy.receive_damage(session.combat,2,'pot',p);break
            impact=dest
        self.room=session.rooms.current;self.x,self.y=impact;self.carried=False
        session.pot_flights.append(dict(start=(p.x,p.y),end=impact,time=.3,kind='orb'))
        session.tick(0);return True
