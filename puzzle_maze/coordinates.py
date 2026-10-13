"""One source of truth for physical room coordinates and reciprocal entrances."""
from dataclasses import dataclass

DELTAS={'NORTH':(0,-1),'SOUTH':(0,1),'EAST':(1,0),'WEST':(-1,0)}
OPPOSITE={'NORTH':'SOUTH','SOUTH':'NORTH','EAST':'WEST','WEST':'EAST','UP':'DOWN','DOWN':'UP'}

@dataclass(frozen=True)
class RoomCoordinate:
    floor:str
    grid_x:int
    grid_y:int
    @classmethod
    def from_room(cls,room):return cls(room['floor'],room['grid_x'],room['grid_y'])
    def direction_to(self,other):
        if self.floor!=other.floor:return 'DOWN' if self.floor=='1F' else 'UP'
        delta=other.grid_x-self.grid_x,other.grid_y-self.grid_y
        return next((direction for direction,value in DELTAS.items() if value==delta),None)

@dataclass(frozen=True)
class DoorConnection:
    id:str
    source_room:str
    target_room:str
    direction:str
    destination_spawn:tuple
    lock_condition:tuple
    return_connection:str|None
    @classmethod
    def from_exit(cls,source,exit):
        return cls(exit['id'],source,exit['target'],exit['direction'],tuple(exit['arrival']),tuple(exit.get('requires',[])),exit.get('return_id'))

class DoorValidator:
    def __init__(self,rooms):self.rooms=rooms
    def validate(self):
        coords={};count=0
        for name,room in self.rooms.items():
            coordinate=RoomCoordinate.from_room(room)
            if any(type(v) is not int or v<0 for v in (coordinate.grid_x,coordinate.grid_y)):raise ValueError('Invalid absolute coordinate')
            if coordinate in coords:raise ValueError('Overlapping rooms')
            coords[coordinate]=name
        for name,room in self.rooms.items():
            source=RoomCoordinate.from_room(room)
            for exit in room['exits']:
                count+=1;connection=DoorConnection.from_exit(name,exit)
                if exit.get('finish'):continue
                target=self.rooms[connection.target_room]
                if not exit.get('portal') and connection.direction!=source.direction_to(RoomCoordinate.from_room(target)):
                    raise ValueError(f'{name}: wrong door direction')
                reverse=next((e for e in target['exits'] if e['id']==connection.return_connection),None)
                if reverse is None or reverse['target']!=name or reverse['return_id']!=connection.id:raise ValueError('Missing reciprocal entrance')
                if not exit.get('portal') and reverse['direction']!=OPPOSITE[connection.direction]:raise ValueError('Wrong return direction')
                dx,dy=DELTAS.get(reverse['direction'],(0,0))
                expected=(reverse['pos'][0]-dx,reverse['pos'][1]-dy) if dx or dy else tuple(reverse.get('landing',reverse['pos']))
                if connection.destination_spawn!=expected:raise ValueError('Arrival does not match return entrance')
                x,y=exit['pos'];w=len(room['tiles'][0]);h=len(room['tiles'])
                if connection.direction in DELTAS and not exit.get('portal'):
                    valid={'NORTH':y==1,'SOUTH':y==h-2,'WEST':x==1,'EAST':x==w-2}[connection.direction]
                    if not valid:raise ValueError('Door is on wrong room edge')
        return count
