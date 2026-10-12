"""Room palettes are presentation data; they never change tile collision."""
from dataclasses import dataclass

@dataclass(frozen=True)
class RoomTheme:
    floor: tuple
    wall: tuple
    shadow: tuple
    accent: tuple
    light: tuple
    material: str
    decor: str

THEMES={
    'entrance':RoomTheme((72,77,73),(119,124,116),(42,52,58),(228,173,90),(250,164,75),'stone','torch'),
    'mechanism':RoomTheme((55,74,80),(101,131,143),(29,44,59),(185,206,117),(108,228,192),'metal','gear'),
    'library':RoomTheme((81,61,54),(137,104,77),(42,34,40),(229,191,125),(241,158,96),'wood','books'),
    'guard':RoomTheme((82,62,60),(123,109,109),(46,42,51),(192,78,76),(255,188,101),'slate','rack'),
    'crystal':RoomTheme((44,59,92),(98,119,165),(27,32,64),(126,242,220),(100,192,255),'crystal','crystal'),
    'vault':RoomTheme((57,47,68),(107,88,124),(27,24,45),(234,189,76),(188,140,239),'inlay','sigil'),
    'observatory':RoomTheme((32,52,69),(84,113,137),(18,27,43),(110,186,237),(144,196,255),'star','crystal'),
    'sanctum':RoomTheme((65,54,88),(143,125,156),(34,27,52),(230,184,117),(255,221,151),'inlay','banner'),
}
DECOR_KINDS={'torch','gear','books','rack','crystal','sigil','banner'}
