"""Original royal resonance circuit: two pillars, a lower socket, an upper key."""
from puzzle_maze.safety import landing_points,nearest_safe

def upgrade(rooms):
    for room in rooms.values():room['content_revision']='4.4'
    rooms['r22']['objects'].append(dict(id='royal_socket',type='orb_socket',pos=[9,12],flag='royal_resonance',flag_requires=['floor_lowered'],optional=True,progression={'milestone':'royal_resonance','needs':['magnet','gloves','prism']}))
    rooms['r6']['objects'].append(dict(id='royal_signal',type='relay',pos=[21,11],flags=['royal_resonance'],optional=True))
    chest=next(o for o in rooms['r6']['objects'] if o['id']=='boss_key')
    chest['flag_requires'].append('royal_resonance');chest['progression']['needs'].append('royal_resonance')
    rooms['r6']['hint']='The crowned chest listens to a matching socket below. Two shattered pillars reveal the way.'
    rooms['r22']['hint']='The crown socket wakes beneath the lowered floor. Place the Iron Orb on its round inlay.'
    next(o for o in rooms['r16']['objects'] if o['id']=='gate')['opening_duration']=.6
    from puzzle_maze.vault import add_vault
    add_vault(rooms)
    for name,room in rooms.items():
        room['safe_landings']=[list(p) for p in sorted(landing_points(name,rooms))]
        occupied=set()
        for enemy in room.get('enemies',[]):
            enemy['pos']=list(nearest_safe(room,enemy['pos'],occupied));occupied.add(tuple(enemy['pos']))
    return rooms
