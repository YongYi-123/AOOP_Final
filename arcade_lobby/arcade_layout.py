"""Data-driven machine layout for the ARCADE FLOOR.

A machine is described by an ArcadeMachineDefinition (which game, where it
stands, what it costs, how it looks). The room builds its cabinets from the
list of definitions, so a teammate adds a minigame machine by adding one entry
to settings.MACHINES - no room code changes. Slots that no definition claims
are filled with dark SOON cabinets, so the floor always looks complete and it
is obvious where the next machine goes.
"""
from dataclasses import dataclass

from machine import ArcadeMachine, IdleCabinet
from settings import DEFAULT_PLAY_COST, MACHINES

WALL_Y = ArcadeMachine.TOP_Y          # cabinets standing against the back wall
ISLAND_Y = 138                         # the free-standing middle row
WALL_PITCH = 56
ISLAND_PITCH = 84

# slot name -> top-left of the cabinet standing there
ARCADE_SLOTS = {
    **{f"wall_{i}": (36 + i * WALL_PITCH, WALL_Y) for i in range(5)},
    **{f"island_{i}": (70 + i * ISLAND_PITCH, ISLAND_Y) for i in range(3)},
}


@dataclass(frozen=True)
class MachineTheme:
    """How a cabinet looks: neon/accent colours, the attract-mode screen
    style (see machine.STYLES) and the marquee text."""
    neon: tuple
    accent: tuple
    screen: str
    marquee: str


@dataclass(frozen=True)
class ArcadeMachineDefinition:
    machine_id: str
    game_id: str
    name: str
    description: str
    position: tuple              # (x, y) of the cabinet's top-left
    cost: int
    visual_theme: MachineTheme

    @classmethod
    def from_data(cls, data):
        """Build a definition from a settings.MACHINES entry."""
        if "slot" in data:
            position = ARCADE_SLOTS[data["slot"]]
        else:
            position = (data["x"], data.get("y", WALL_Y))
        return cls(
            machine_id=data["id"],
            game_id=data.get("game_id", data["id"]),
            name=data["name"],
            description=data["description"],
            position=tuple(position),
            cost=data.get("play_cost", DEFAULT_PLAY_COST),
            visual_theme=MachineTheme(data["neon"], data["accent"], data["screen"], data["marquee"]),
        )

    def to_data(self):
        """The dict form ArcadeMachine is built from."""
        theme = self.visual_theme
        return {"id": self.machine_id, "game_id": self.game_id, "name": self.name,
                "marquee": theme.marquee, "description": self.description,
                "x": self.position[0], "y": self.position[1], "neon": theme.neon,
                "accent": theme.accent, "screen": theme.screen, "play_cost": self.cost}

    def build(self):
        return ArcadeMachine(self.to_data())


class ArcadeLayout:
    """Everything standing in the arcade's machine rows."""

    def __init__(self, definitions, slots=None):
        self.definitions = list(definitions)
        self.slots = dict(ARCADE_SLOTS if slots is None else slots)
        ids = [d.machine_id for d in self.definitions]
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate machine ids in the arcade layout: {ids}")
        taken = [d.position for d in self.definitions]
        if len(set(taken)) != len(taken):
            raise ValueError("two machines share a position in the arcade layout")

    @classmethod
    def from_settings(cls, machines=None):
        machines = MACHINES if machines is None else machines
        return cls(ArcadeMachineDefinition.from_data(d) for d in machines)

    def build_machines(self):
        return [d.build() for d in self.definitions]

    def free_slots(self):
        taken = {d.position for d in self.definitions}
        return {name: pos for name, pos in self.slots.items() if pos not in taken}

    def build_idle_cabinets(self):
        return [IdleCabinet(pos) for pos in self.free_slots().values()]
