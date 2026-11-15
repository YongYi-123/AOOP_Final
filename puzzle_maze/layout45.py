"""Two-floor remaster policy; stable chamber IDs preserve the authored campaign."""
import copy
FLOORS=('1F','B1F')
FLOOR_ALIASES={'F1':'1F','GROUND':'1F','B2F':'B1F','2F':'B1F','VAULT':'B1F'}

def upgrade(source):
    rooms=copy.deepcopy(source)
    for name,room in rooms.items():
        room['floor']=FLOOR_ALIASES.get(room['floor'],room['floor'])
        if room['floor'] not in FLOORS: raise ValueError(f'Unsupported remaster floor: {name}')
        room['content_revision']='4.5'
    from puzzle_maze.secret45 import add_secret
    add_secret(rooms)
    from puzzle_maze.palettes45 import assign
    assign(rooms)
    return rooms
