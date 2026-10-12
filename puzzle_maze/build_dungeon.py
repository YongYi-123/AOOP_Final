"""Authoring tool for the original 18-room Clockwork Hollow; emits editable JSON."""
import json
from pathlib import Path


def obj(kind,name,pos,**kw):return dict(type=kind,id=name,pos=list(pos),**kw)

def base(name,theme,atlas,floor='1F',barrier=False):
    tiles=[list('#'*26)]+[list('#'+'.'*24+'#') for _ in range(14)]+[list('#'*26)]
    if barrier:
        for y in range(1,15):tiles[y][18]='#'
        tiles[8][18]='.'
    # Deliberate island columns create navigation decisions without blocking objectives.
    for x,y in ((14,3),(14,4),(14,11),(14,12),(3,11)):tiles[y][x]='#'
    for x,y in ((2,3),(3,3),(2,4)):tiles[y][x]='g'
    return dict(name=name,theme='lower_'+theme if floor=='B1F' else theme,atlas=list(atlas),floor=floor,layout_revision='3.0',spawn=[2,7],tiles=[''.join(row) for row in tiles],objects=[],enemies=[],exits=[],goal=[],hint='E interacts. Follow the inlaid paths.',decorations=[])


def build():
    specs=[('Stone Vestibule','entrance',(2,0),'1F'),('Relay Atrium','mechanism',(2,1),'1F'),('Copper Watch','guard',(1,1),'1F'),('Weight and Light','mechanism',(2,2),'1F'),('Ancient Library','library',(3,1),'1F'),('Returning Runner','observatory',(3,2),'1F'),('Powder Workshop','mechanism',(0,1),'1F'),('Hidden Treasury','vault',(0,2),'1F'),('Boots Trial','guard',(0,0),'1F'),('Lower Landing','observatory',(2,0),'B1F'),('Magnetic Foundry','mechanism',(1,0),'B1F'),('Prism Engine','crystal',(0,0),'B1F'),('Hungry Portal','vault',(2,1),'B1F'),('Threefold Circuit','crystal',(1,1),'B1F'),('Sentinel Gallery','guard',(1,2),'B1F'),('Golem Antechamber','sanctum',(2,2),'B1F'),('Ancient Golem','sanctum',(3,2),'B1F'),('Dawn Reservoir','crystal',(3,3),'B1F')]
    rooms={f'r{i}':base(*spec,barrier=i in (1,3,4,5,6,10,12,13,14,15,16,17,18)) for i,spec in enumerate(specs,1)}
    def objects(i,*values,goal=()):rooms[f'r{i}']['objects']=list(values);rooms[f'r{i}']['goal']=list(goal)
    def enemy(i,kind,pos,name=None):rooms[f'r{i}']['enemies'].append(dict(id=name or kind,type=kind,pos=list(pos)))
    def edge(a,b,pos=(23,8),arrival=(2,7),requires=(),abilities=()):rooms[f'r{a}']['exits'].append(dict(pos=list(pos),target=f'r{b}',arrival=list(arrival),requires=list(requires),abilities=list(abilities),stairs=rooms[f'r{a}']['floor']!=rooms[f'r{b}']['floor']))
    def back(a,b):edge(a,b,(2,8),(4,7))
    gate=lambda *req,**kw:obj('door','gate',(18,8),requires=list(req),**kw)
    seal=lambda:obj('combat','clear',(16,13))
    plate=lambda:obj('plate','plate',(6,8))
    box=lambda **kw:obj('box','box',(6,9),**kw)
    light=lambda:obj('light','lamp',(6,6),direction=[1,0],requires=['plate'])
    reflector=lambda:obj('reflector','prism',(10,6))
    receiver=lambda:obj('receiver','eye',(10,3))
    objects(1,obj('switch','lever',(8,5)),obj('chest','map',(5,4),ability='map'),gate('lever'),goal=['gate'])
    enemy(1,'slime',(10,10));edge(1,2,requires=['gate'])
    objects(2,obj('relay','relays',(15,5),flags=['west','east']),obj('door','lower',(23,8),key='small',cost=2,requires=['relays']),goal=['lower'])
    back(2,1);edge(2,3,(12,2));edge(2,4,(12,13));edge(2,5,(5,3));edge(2,6,(5,13));edge(2,10,requires=['lower'])
    objects(3,seal(),obj('key','combat_key',(8,4),color='small',amount=2,requires=['clear']),gate('clear',key='small'),goal=['gate'])
    enemy(3,'slime',(10,8));enemy(3,'bat',(12,11));back(3,2);edge(3,7,requires=['gate'])
    objects(4,obj('chest','gloves',(4,4),ability='gloves'),box(heavy=True),plate(),light(),reflector(),receiver(),gate('plate','eye'),obj('remote','west',(23,5),flag='west',requires=['gate']),goal=['west'])
    back(4,2)
    objects(5,obj('switch','lever',(9,5)),obj('chest','mirror',(5,4),ability='mirror',requires=['lever']),box(),plate(),gate('lever','plate'),obj('remote','east',(23,5),flag='east'),obj('chest','compass',(23,11),ability='compass',small_keys=1),goal=['east','compass'])
    back(5,2)
    objects(6,obj('timed','clock',(16,8),duration=.35),obj('relay','prism_ready',(4,4),flags=['prism']),gate('clock',dash_only=True),obj('chest','boss_key',(23,6),boss_key=True,requires=['gate','prism_ready']),goal=['boss_key'])
    back(6,2);edge(6,2,(23,12),(4,7))
    objects(7,obj('chest','powder',(6,5),bombs=8,small_keys=1),obj('supply','supply',(4,10)),obj('switch','lever',(12,6)),obj('cracked','crack',(12,13)),goal=['powder','lever'])
    back(7,3);edge(7,9,requires=['lever']);edge(7,8,(12,13),requires=['crack']);rooms['r8']['hidden']=True
    objects(8,obj('chest','reward',(12,6),potions=3,coins=8),obj('blast_switch','blast',(8,8)),obj('chest','bonus',(16,8),bombs=4,requires=['blast']),goal=['reward']);back(8,7)
    objects(9,seal(),box(heavy=True),plate(),obj('chest','boots',(15,8),ability='boots',requires=['clear','plate']),goal=['boots'])
    enemy(9,'guardian',(12,5));enemy(9,'armored_beetle',(12,11));back(9,7)
    objects(10,obj('switch','lever',(8,5)),gate('lever'),obj('chest','rest',(5,11),potions=2),goal=['gate'])
    back(10,2);edge(10,11,(12,2));edge(10,13,requires=['gate'])
    objects(11,seal(),obj('switch','lever',(8,4)),obj('chest','magnet',(13,8),ability='magnet',requires=['lever','clear']),goal=['magnet'])
    enemy(11,'blink_mage',(12,11));back(11,10);edge(11,12,requires=['magnet'])
    def combination(i,timed=False):
        values=[obj('box','box',(9,8),metal=True,heavy=True,magnetic_only=True),obj('plate','plate',(11,8)),obj('light','lamp',(7,4),direction=[1,0],requires=['plate']),obj('reflector','prism',(11,4)),obj('receiver','eye',(11,2))]
        values+=[obj('timed','clock',(16,8),duration=.35)] if timed else []
        values+=[gate('plate','eye',*(['clock'] if timed else []),dash_only=timed)]
        tiles=[list(row) for row in rooms[f'r{i}']['tiles']];tiles[8][8]='~';tiles[7][8]='#';tiles[9][8]='#';rooms[f'r{i}']['tiles']=[''.join(row) for row in tiles]
        return values
    objects(12,*combination(12),obj('remote','prism_signal',(23,5),flag='prism'),obj('chest','key',(23,11),small_keys=1,potions=2),goal=['prism_signal','key'])
    back(12,11)
    objects(13,seal(),obj('supply','supply',(4,4)),obj('chest','portal_key',(8,4),small_keys=1,requires=['clear']),gate('clear'),goal=['portal_key','gate'])
    enemy(13,'bomb_eater',(11,8));back(13,10);edge(13,14,requires=['gate'],abilities=['boots','mirror','magnet']);rooms['r13']['exits'][-1]['portal']=True
    objects(14,*combination(14,True),obj('chest','reward',(23,6),potions=2,requires=['gate']),goal=['gate','reward'])
    back(14,13);edge(14,13,(23,12),(4,7));edge(14,15,requires=['gate'])
    objects(15,seal(),gate('clear',key='small',cost=2),obj('chest','rest',(8,4),potions=2),goal=['gate'])
    enemy(15,'blink_mage',(11,5));enemy(15,'armored_beetle',(11,11));enemy(15,'bat',(15,9));back(15,14);edge(15,16,requires=['gate'])
    objects(16,gate(key='boss'),obj('supply','supply',(4,4)),obj('chest','rest',(8,5),potions=3),goal=['gate'])
    back(16,15);edge(16,17,requires=['gate'],abilities=['boots'])
    objects(17,seal(),obj('dash_switch','anchor',(7,8),duration=6),obj('supply','supply',(4,4)),gate('clear'),goal=['gate'])
    enemy(17,'golem',(13,8));back(17,16);edge(17,18,requires=['gate'])
    objects(18,obj('switch','dawn',(10,5)),obj('chest','treasure',(8,11),coins=20),gate('dawn','treasure'),goal=['gate']);back(18,17)
    rooms['r18']['exits'].append(dict(pos=[23,8],target='r18',arrival=[2,7],requires=['gate'],finish=True))
    hints={1:'J: sword. E: map chest and lever.',2:'Two branch relays power the lower stairs. Two keys unlock them.',3:'Clear the watch, claim two keys, spend one at the lock.',4:'Take gloves. Weight powers light; rotate the mirror from the library.',5:'Move the book crate; the lever reveals a mirror. Relay waits beyond.',6:'Return with boots and the lower prism signal. E then SHIFT east.',7:'B places bombs. Powder jars refill. Cracks mark a hidden stair.',8:'Optional treasury. Bomb the copper receiver for extra supplies.',9:'Flank the beetle. Heavy weight and combat unlock the boots.',10:'1F relays remain powered. Explore both lower branches.',11:'Mages blink along clear lines. Switch and combat unlock magnet.',12:'Face east from (6,8). SPACE with magnet twice; rotate prism with E.',13:'B: place a bomb near the hungry mouth. The cleared gate is a portal.',14:'Magnet, mirror, then E timer and SHIFT from (16,8).',15:'Two branch keys open the lower lock after the sentinel encounter.',16:'Boss Key opens the seal. Refill bombs before entering.',17:'SHIFT onto the anchor. Sword the core. Later: bomb the armor.',18:'Open the treasury and activate dawn to finish.'}
    for i,room in enumerate(rooms.values(),1):
        room['hint']=hints[i]
        if i in (1,3,5,9,10,11,15,16,18):
            rows=[list(row) for row in room['tiles']]
            points=((20,3),(20,4),(20,11),(20,12)) if i in (1,3,5,15,16,18) else ((19,3),(19,4),(20,11),(20,12))
            for x,y in points:rows[y][x]='O'
            room['tiles']=[''.join(row) for row in rows]
        room['decorations']=[dict(kind={'entrance':'torch','mechanism':'gear','library':'books','guard':'rack','crystal':'crystal','vault':'sigil','observatory':'crystal','sanctum':'banner'}[room['theme'].removeprefix('lower_')],pos=[x,0]) for x in (4,10,16,22)]
    # Monotone milestones describe access assumptions for the resource-order solver.
    # Quantities and costs are read from these actual reward / door objects.
    progression={
        (3,'combat_key'):('watch',[]), (5,'mirror'):('mirror',[]),
        (5,'compass'):('library',['mirror']), (4,'gloves'):('gloves',[]),
        (4,'west'):('west',['mirror','gloves']), (5,'east'):('east',['mirror']),
        (3,'gate'):('watch_lock',['watch']), (7,'powder'):('workshop',['watch_lock']),
        (9,'boots'):('boots',['workshop','gloves']), (2,'lower'):('stairs',['west','east']),
        (11,'magnet'):('magnet',['stairs']),
        (12,'key'):('prism',['stairs','mirror','magnet']),
        (13,'portal_key'):('eater',['stairs','workshop']),
        (6,'boss_key'):('boss_key',['boots','prism']),
        (15,'gate'):('sentinels',['prism','eater']),
    }
    for (number,name),(milestone,needs) in progression.items():
        item=next(o for o in rooms[f'r{number}']['objects'] if o['id']==name)
        item['progression']=dict(milestone=milestone,needs=needs)
    return rooms

if __name__=='__main__':
    path=Path(__file__).parent/'maps/dungeon_v3.json';path.write_text(json.dumps(build(),indent=2)+'\n')
