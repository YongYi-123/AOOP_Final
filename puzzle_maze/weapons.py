"""Equipment owns reach, damage and timing; combat consumes one swing once."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Weapon:
    id: str
    name: str
    damage: int = 1
    reach: int = 1
    cooldown: float = .25
    swing_duration: float = .18

    def contains(self,origin,target,facing):
        dx,dy=target[0]-origin[0],target[1]-origin[1]
        forward=dx*facing[0]+dy*facing[1]
        sideways=abs(dx*facing[1]-dy*facing[0])
        return 0<forward<=self.reach and sideways==0

class BasicSword(Weapon):
    def __init__(self):super().__init__('basic_sword','Basic Sword')

WEAPONS={'basic_sword':BasicSword}
