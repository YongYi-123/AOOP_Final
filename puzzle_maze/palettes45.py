"""Saturated, readable remaster materials, leaving archived themes untouched."""
from puzzle_maze.themes import THEMES,RoomTheme
PALETTES={
 'garden':((46,79,62),(151,134,94),(22,39,38),(107,205,154),(255,193,93),'stone','torch'),
 'castle':((86,65,54),(172,135,94),(40,32,41),(238,183,88),(255,193,95),'stone','banner'),
 'library':((74,40,61),(151,92,103),(33,24,42),(237,181,104),(243,162,94),'wood','books'),
 'crystal':((46,55,96),(106,129,188),(23,28,55),(110,225,238),(140,197,255),'crystal','crystal'),
 'royal':((85,43,63),(161,116,111),(38,25,45),(245,196,89),(255,196,125),'inlay','banner'),
 'workshop':((76,63,48),(157,124,86),(31,35,42),(232,164,84),(251,177,95),'metal','gear'),
 'arcane':((35,49,83),(78,104,147),(18,25,45),(162,124,233),(105,205,239),'star','sigil'),
 'foundry':((40,64,76),(94,131,145),(20,32,45),(237,154,74),(246,181,105),'metal','gear'),
 'pool':((29,72,76),(83,137,142),(16,34,46),(91,224,183),(113,220,225),'crystal','crystal'),
 'sanctuary':((60,44,89),(131,103,174),(28,22,51),(199,156,243),(128,213,244),'inlay','crystal'),
 'debug':((35,42,65),(90,105,145),(14,20,38),(170,180,190),(108,223,217),'star','sigil'),
}
for name,values in PALETTES.items():THEMES['v45_'+name]=RoomTheme(*values)

def assign(rooms):
    sections={1:'garden',2:'castle',3:'castle',4:'crystal',5:'library',6:'royal',7:'workshop',8:'royal',
              9:'garden',10:'pool',11:'foundry',12:'arcane',13:'sanctuary',14:'crystal',15:'foundry',
              16:'royal',17:'sanctuary',18:'pool',19:'royal',20:'workshop',21:'crystal',22:'sanctuary',
              23:'workshop',24:'library',25:'garden',26:'arcane',27:'royal',28:'debug'}
    for id,room in rooms.items():
        room['theme']='v45_'+sections.get(int(id[1:]),'arcane')
        room['seed']=room.get('seed',0)+4500
