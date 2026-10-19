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

# Cold underground masonry has distinct palettes while retaining each material's behavior.
from dataclasses import replace
for _name in ('observatory','mechanism','crystal','vault','guard','sanctum'):
    _theme=THEMES[_name]
    THEMES['lower_'+_name]=replace(_theme,
        floor=tuple(max(0,c-13)+(8 if i==2 else 0) for i,c in enumerate(_theme.floor)),
        wall=tuple(max(0,c-18)+(12 if i==2 else 0) for i,c in enumerate(_theme.wall)),
        light=(105,166,229))

THEMES.update({
 'stone_garden':RoomTheme((54,70,66),(104,125,114),(22,38,39),(167,183,119),(242,187,105),'stone','torch'),
 'torch_shrine':RoomTheme((74,47,43),(143,91,69),(36,25,33),(245,180,93),(255,160,78),'inlay','torch'),
 'pot_storage':RoomTheme((83,63,45),(155,116,80),(39,31,30),(220,169,115),(233,180,118),'clay','gear'),
 'crystal_hall':RoomTheme((39,48,80),(93,129,170),(20,25,50),(93,225,211),(118,204,248),'crystal','crystal'),
 'underground_library':RoomTheme((52,51,57),(103,83,88),(27,26,38),(193,160,131),(162,174,236),'wood','books'),
 'forgotten_vault':RoomTheme((39,43,55),(83,91,112),(17,22,32),(211,185,109),(137,201,186),'inlay','sigil'),
 'ancient_workshop':RoomTheme((56,59,65),(121,122,112),(27,34,41),(213,155,92),(227,157,96),'metal','gear'),
 'hidden_sanctuary':RoomTheme((42,58,67),(97,118,120),(22,29,46),(197,205,143),(156,209,238),'star','crystal'),
 'boss_chamber':RoomTheme((54,44,69),(112,100,126),(23,20,40),(236,168,113),(177,147,244),'slate','banner'),
})

THEMES['mine']=RoomTheme((68,61,52),(119,103,81),(34,33,37),(205,161,92),(244,187,101),'ore','torch')
