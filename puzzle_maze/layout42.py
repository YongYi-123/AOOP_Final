"""Repair room adjacency in place, retaining puzzle IDs and interior solutions."""
COORDS={1:(2,3),2:(2,2),3:(2,1),4:(1,2),5:(3,1),6:(3,3),7:(1,0),8:(0,0),9:(2,0),19:(3,2),20:(1,1),10:(1,2),11:(1,1),12:(2,1),13:(2,2),14:(3,2),15:(3,1),16:(3,0),17:(4,0),18:(5,0),21:(0,2),22:(0,1)}

def repair(rooms):
    from puzzle_maze.coordinates import RoomCoordinate,DELTAS
    def obj(n,id):return next(o for o in rooms[f'r{n}']['objects'] if o['id']==id)
    remove={(2,5),(5,2),(2,6),(6,2),(3,7),(7,3),(5,8),(8,5),(12,21),(21,12),(12,14),(14,12)}
    for name,room in rooms.items():
        n=int(name[1:]);room['grid_x'],room['grid_y']=COORDS[n];room['atlas']=list(COORDS[n]);room['content_revision']='4.2'
        room['exits']=[e for e in room['exits'] if (n,int(e['target'][1:])) not in remove]
        # Duplicated emergency exits concealed the timed-door return bug.
        seen=set();room['exits']=[e for e in room['exits'] if not (e['target'] in seen or seen.add(e['target']))]
        rows=[list(row) for row in room['tiles']]
        if n not in (6,14):
            for y in range(1,len(rows)-1):
                if rows[y][18]=='#':rows[y][18]='.'
        room['tiles']=[''.join(row) for row in rows]
    def add(a,b,**kw):rooms[f'r{a}']['exits'].append(dict(target=f'r{b}',requires=[],abilities=[],**kw))
    add(1,6);add(6,1)
    add(5,3,entrance='walkthrough');add(3,5,entrance='walkthrough')
    # Returning exits stay available without requiring puzzles to be completed.
    forward={1:2,3:9,10:13,13:14,15:16,16:17,17:18,19:5,20:7}
    for n,target in forward.items():
        exit=next(e for e in rooms[f'r{n}']['exits'] if e['target']==f'r{target}')
        exit['requires']=['gate'];exit['entrance']='boss_gate' if n==16 else 'locked' if n in (3,15) else 'stone'
    for n in (4,5,12,21):obj(n,'gate')['type']='gate_control'
    obj(5,'east')['requires']=['gate'];obj(5,'compass')['requires']=['gate'];obj(12,'key')['requires']=['gate']
    for n in (6,14):obj(n,'gate')['reversible']=True
    # An independent exit in the Boots room is not hidden behind its own reward.
    for name,room in rooms.items():
        for e in room['exits']:
            target=rooms[e['target']];n=int(name[1:])
            direction=RoomCoordinate.from_room(room).direction_to(RoomCoordinate.from_room(target))
            if e.get('finish'):direction='EAST'
            if direction is None:raise ValueError(f'Nonadjacent edge {name} -> {e["target"]}')
            e.setdefault('entrance','stone')
            e['direction']=direction;e['id']=f'{name}:{e["target"]}';e['return_id']=f'{e["target"]}:{name}' if not e.get('finish') else None
            e['pos']=list({'NORTH':(12,1),'SOUTH':(12,14),'WEST':(1,8),'EAST':(24,8),'DOWN':(22,11),'UP':(2,8)}[direction])
            if n==14 and direction=='NORTH':e['pos']=[23,1]
            if n==2 and e.get('stairs'):obj(2,'lower')['pos']=list(e['pos'])
            if e.get('stairs'):e['landing']=[e['pos'][0],e['pos'][1]-1]
            rows=[list(row) for row in room['tiles']];x,y=e['pos'];rows[y][x]='.'
            dx,dy=DELTAS.get(direction,(0,0));rows[y-dy][x-dx]='.'
            if n==14 and direction=='NORTH':
                for yy in range(1,8):rows[yy][23]='.'
            room['tiles']=[''.join(row) for row in rows]
            if n in forward and e['target']==f'r{forward[n]}':obj(n,'gate')['pos']=list(e['pos'])
            if n==7 and e['target']=='r8':obj(7,'crack')['pos']=list(e['pos'])
            if n==21 and e['target']=='r22':obj(21,'sanctuary')['pos']=list(e['pos'])
    # Crystal barriers now actually guard the indicated route, not a stale floor tile.
    obj(2,'library_red')['pos']=next(e['pos'][:] for e in rooms['r19']['exits'] if e['target']=='r5')
    barrier=obj(2,'library_red');rooms['r2']['objects'].remove(barrier);rooms['r19']['objects'].append(barrier)
    obj(2,'watch_blue')['pos']=next(e['pos'][:] for e in rooms['r2']['exits'] if e['target']=='r3')
    # Avoid placing two blocking objects on the same door tile.
    obj(19,'gate')['pos']=[18,8];obj(19,'gate')['type']='gate_control'
    obj(18,'gate')['pos']=next(e['pos'][:] for e in rooms['r18']['exits'] if e.get('finish'))
    for name,room in rooms.items():
        for e in room['exits']:
            if e.get('finish'):e['arrival']=list(e['pos']);continue
            reverse=next(x for x in rooms[e['target']]['exits'] if x['id']==e['return_id'])
            dx,dy=DELTAS.get(reverse['direction'],(0,0));e['arrival']=[reverse['pos'][0]-dx,reverse['pos'][1]-dy] if dx or dy else list(reverse['landing'])
    # Optional multi-room/floor growth never removes the original return routes.
    rooms['r20']['objects'].append(dict(id='tower_pillar',type='pillar',pos=[15,10],flag='pillar_storage',optional=True))
    rooms['r11']['objects'].append(dict(id='engine_pillar',type='pillar',pos=[16,10],flag='pillar_foundry',optional=True))
    rooms['r10']['objects'].append(dict(id='west_crystal',type='crystal_barrier',pos=[1,8],color='red',optional=True))
    rooms['r20']['orb_spawn']=[10,11]
    for a,b,direction,pos,landing in ((20,22,'DOWN',[21,13],[21,12]),(22,20,'UP',[5,13],[5,12])):
        rooms[f'r{a}']['exits'].append(dict(id=f'r{a}:r{b}',return_id=f'r{b}:r{a}',target=f'r{b}',direction=direction,pos=pos,landing=landing,arrival=[5,12] if a==20 else [21,12],stairs=True,entrance='stairs_down' if a==20 else 'stairs_up',requires=[],flag_requires=['floor_lowered'],abilities=[],transformed=True,orb_allowed=True))
    rooms['r20']['transformation']={'flags':['pillar_storage','pillar_foundry'],'result':'floor_lowered'}
    rooms['r22']['objects'].extend([
        dict(id='totem_a',type='box',pos=[16,10],heavy=True,mark=1,optional=True),
        dict(id='totem_b',type='box',pos=[20,10],heavy=True,mark=2,optional=True),
        dict(id='arrangement',type='ordered_layout',pos=[22,9],placements=[{'object':'totem_a','pos':[16,9]},{'object':'totem_b','pos':[20,9]}],optional=True),
        dict(id='layout_cache',type='chest',pos=[22,6],hidden=True,requires=['arrangement'],loot=['token_cache'],optional=True),
        dict(id='orb_cache',type='chest',pos=[6,11],hidden=True,flag_requires=['floor_lowered'],loot=['heart_fragment','ticket_bundle'],optional=True)])
    rooms['r12']['objects'].append(dict(id='crystal_cache',type='chest',pos=[15,11],hidden=True,requires=['gate'],crystal_color='blue',loot=['token_cache'],optional=True))
    for room in rooms.values():
        for exit in room['exits']:exit.setdefault('orb_allowed',not exit.get('portal'))
    return rooms
