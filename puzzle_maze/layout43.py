"""Optional 4.3 exploration branches; original puzzle IDs and routes stay intact."""
from puzzle_maze.safety import landing_points,nearest_safe

SECRET_BRANCHES=(
 ('r8','r23','SOUTH',(0,1),'Amber Mine','mine'),
 ('r5','r24','EAST',(4,1),'Whisper Archive','underground_library'),
 ('r6','r25','EAST',(4,3),'Moonlit Mint','vault'),
 ('r22','r26','NORTH',(0,0),'Starling Shrine','hidden_sanctuary'),
)

def upgrade(rooms):
    for room in rooms.values():
        room['content_revision']='4.3'
        for obj in room['objects']:
            if obj['type']=='cracked':obj['duration']=.6
            if obj['type']=='chest' and any(obj.get(key) for key in ('requires','flag_requires','ability_requires','crystal_color','enemy_requires')):obj['hidden']=True
    positions={'NORTH':[12,1],'SOUTH':[12,14],'WEST':[1,8],'EAST':[24,8]}
    opposite={'NORTH':'SOUTH','SOUTH':'NORTH','EAST':'WEST','WEST':'EAST'}
    delta={'NORTH':(0,-1),'SOUTH':(0,1),'WEST':(-1,0),'EAST':(1,0)}
    def object(id,type,pos,**kw):return dict(id=id,type=type,pos=pos,**kw)
    puzzles=[
        [object('vein','switch',[9,7]),object('cache','chest',[15,7],hidden=True,requires=['vein'],enemy_requires=['ore_bat'],loot=['heart_fragment','ticket_bundle','bomb_bundle'])],
        [object('candle','brazier',[9,7]),object('powder','powder_supply',[7,10]),object('cache','chest',[15,7],hidden=True,requires=['candle'],loot=['music_disc','token_cache'])],
        [object('box','box',[9,9],heavy=True),object('plate','plate',[9,8]),object('cache','chest',[15,7],hidden=True,requires=['plate'],loot=['crystal_skin','ticket_bundle'])],
        [object('crystal','crystal_switch',[9,7]),object('cache','chest',[15,7],hidden=True,crystal_color='blue',ability_requires=['gloves'],loot=['golden_cat','token_cache','heart_fragment'])],
    ]
    for index,(source,name,direction,coord,title,theme) in enumerate(SECRET_BRANCHES):
        parent=rooms[source];back=opposite[direction];pos=positions[direction][:];backpos=positions[back][:]
        dx,dy=delta[direction];bdx,bdy=delta[back]
        parent['objects'].append(object('secret43','cracked',pos[:],optional=True,duration=.6))
        parent['exits'].append(dict(id=f'{source}:{name}',return_id=f'{name}:{source}',target=name,pos=pos[:],arrival=[backpos[0]-bdx,backpos[1]-bdy],direction=direction,entrance='cave',requires=['secret43'],abilities=[],orb_allowed=True))
        rows=['#'*26]+['#'+'.'*24+'#' for _ in range(14)]+['#'*26]
        # Authored mineral pillars / bookshelves stay off the small puzzle's approaches.
        rows=[list(row) for row in rows]
        for x,y in ((5,4),(19,4),(5,11),(19,11)):rows[y][x]='O'
        room=dict(name=title,hint=('Listen to the stone, then study what remains.' if index==0 else 'A quiet flame remembers old songs.' if index==1 else 'Weight leaves a mark on the mint floor.' if index==2 else 'Blue light and strong hands reveal the offering.'),tiles=[''.join(row) for row in rows],spawn=[2,7],floor=parent['floor'],grid_x=coord[0],grid_y=coord[1],atlas=list(coord),layout_revision=parent['layout_revision'],content_revision='4.3',hidden=True,theme=theme,objects=puzzles[index],enemies=[],goal=['cache'],decorations=[dict(kind='torch' if theme=='mine' else 'books' if 'library' in theme else 'sigil',pos=[6,0],phase=index)],exits=[dict(id=f'{name}:{source}',return_id=f'{source}:{name}',target=source,pos=backpos,arrival=[pos[0]-dx,pos[1]-dy],direction=back,entrance='cave',requires=[],abilities=[],orb_allowed=True)])
        if index==0:room['enemies']=[dict(id='ore_bat',type='bat',pos=[17,10])]
        rooms[name]=room
        # Carve only the entry and its inward approach in the existing room.
        rows=[list(row) for row in parent['tiles']];x,y=pos;rows[y][x]='.';rows[y-dy][x-dx]='.';parent['tiles']=[''.join(row) for row in rows]
    for name,room in rooms.items():
        room['safe_landings']=[list(p) for p in sorted(landing_points(name,rooms))]
        occupied=set()
        for enemy in room.get('enemies',[]):
            enemy['pos']=list(nearest_safe(room,enemy['pos'],occupied));occupied.add(tuple(enemy['pos']))
    return rooms
