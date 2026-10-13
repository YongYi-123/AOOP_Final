"""Original looped dungeon authoring: preserve the v3 mechanics and vary the architecture."""
import json
from pathlib import Path
from puzzle_maze.build_dungeon import build as build_v3,base,obj

def build():
    rooms=build_v3()
    def add(number,*values):rooms[f'r{number}']['objects'].extend(values)
    def item(number,name):return next(o for o in rooms[f'r{number}']['objects'] if o['id']==name)
    def edge(a,b,pos,requires=(),abilities=(),**kw):rooms[f'r{a}']['exits'].append(dict(pos=list(pos),target=f'r{b}',arrival=[2,7],requires=list(requires),abilities=list(abilities),**kw))
    def tile(number,x,y,kind):
        room=rooms[f'r{number}'];rows=[list(row) for row in room['tiles']];rows[y][x]=kind;room['tiles']=[''.join(row) for row in rows]
    for number,room in enumerate(rooms.values(),1):
        room['layout_revision']='4.0';room['architecture']=('arched','mosaic','runners','fractured')[number%4]
        # Use alcoves and staggered pillars; clear all old purely repeated columns.
        for x,y in ((14,3),(14,4),(14,11),(14,12)):tile(number,x,y,'.')
        if number in (1,3,5,9,10,11,15,16,18):
            for x,y in ((14,2),(15,2),(15,3),(15,12),(14,13)):tile(number,x,y,'#')
        if number in (2,7,11):
            for x in range(18,24):tile(number,x,3,'#')
            for y in (4,5):tile(number,23,y,'#')
        # Presentation motifs share the tile collision geometry, never fake walls.
        room['motifs']=[dict(kind='medallion',pos=[12,7]),dict(kind='runner',pos=[2,7])]
    for number,name,theme,atlas,floor in ((19,'Torch Shrine','torch_shrine',(4,0),'1F'),(20,'Pot Storage','pot_storage',(1,2),'1F'),(21,'Crystal Warden','crystal_hall',(2,3),'B1F'),(22,'Hidden Sanctuary','hidden_sanctuary',(1,3),'B1F')):
        rooms[f'r{number}']=base(name,theme,atlas,'1F',barrier=number!=22)
        rooms[f'r{number}'].update(floor=floor,layout_revision='4.0',architecture='mosaic',motifs=[dict(kind='medallion',pos=[12,7])])
    rooms['r19']['objects']=[obj('chest','powder',(5,4),ability='powder',powder=12),obj('powder_supply','dust',(4,10)),obj('brazier','dawn',(7,5),mark=1),obj('brazier','noon',(10,5),mark=2),obj('brazier','dusk',(13,5),mark=3),obj('torch_order','flames',(16,4),order=['dawn','noon','dusk']),obj('combat','clear',(16,13)),obj('door','gate',(18,8),requires=['flames','clear']),obj('remote','flame_signal',(23,5),flag='flame',requires=['gate']),obj('brazier','hidden_fire',(22,11),requires=['flames']),obj('chest','disc',(23,11),loot=['music_disc'],requires=['hidden_fire'],hidden=True)]
    for x in (7,10,13):tile(19,x,4,'#')
    rooms['r19']['enemies']=[dict(id='ghost',type='crystal_ghost',pos=[11,10],torch='dawn')];rooms['r19']['goal']=['flame_signal']
    rooms['r19']['hint']='P lights marked bowls: dawn, noon, dusk. E refills powder.'
    rooms['r20']['objects']=[obj('pot','jar',(6,6),weight=2,renewable=True),obj('pot','jar2',(9,9),weight=2,renewable=True),obj('pot','charm_pot',(12,4),weight=2,loot=['lucky_charm'],inscribed=True),obj('pot','bomb_pot',(6,11),weight=2,explosive=True),obj('pot_supply','pot_rack',(4,4)),obj('weight','load',(13,8),weight=3),obj('combat','clear',(16,13)),obj('relay','flame_ready',(16,5),flags=['flame']),obj('door','gate',(18,8),requires=['load','clear','flame_ready']),obj('chest','cache',(23,5),loot=['bomb_bundle','token_cache'],requires=['gate'])]
    rooms['r20']['objects'].extend(obj('pot',f'stored_{x}',(x,12),weight=2,renewable=True) for x in (5,7,9))
    rooms['r20']['enemies']=[dict(id='hunter',type='pot_hunter',pos=[14,10])];rooms['r20']['goal']=['cache']
    rooms['r20']['hint']='E lifts a pot. G throws. Carry weight onto the three-dot plate.'
    rooms['r21']['objects']=[obj('crystal_switch','crystal',(5,8)),obj('crystal_barrier','red',(17,8),color='red'),obj('combat','clear',(16,13)),obj('door','gate',(18,8),requires=['clear']),obj('chest','warden_cache',(23,5),loot=['ticket_bundle','heart_recovery'],requires=['gate']),obj('supply','bombs',(4,4)),obj('cracked','sanctuary',(12,13))]
    rooms['r21']['enemies']=[dict(id='warden',type='crystal_warden',pos=[12,8],weak_color='red'),dict(id='spark_slime',type='slime',pos=[15,5],summon_at=3),dict(id='spark_bat',type='bat',pos=[15,11],summon_at=3)]
    for x,y in ((2,1),(3,1),(4,1),(2,2),(3,2),(23,1),(22,1),(21,1),(23,2),(22,2),(2,13),(3,13),(23,13),(22,13),(23,12)):tile(21,x,y,'#')
    rooms['r21']['on_clear_flag']='warden';rooms['r21']['goal']=['clear','warden_cache'];rooms['r21']['hint']='J strikes crystal. Red reveals the Warden; blue lowers the exit.'
    rooms['r22']['hidden']=True
    rooms['r22']['objects']=[obj('ordered','sequence',(16,13)),obj('chest','skin',(20,5),loot=['crystal_skin'],requires=['sequence'],hidden=True),obj('relay','sanctuary_ready',(8,4),flags=['flame','warden']),obj('chest','stamp',(8,5),loot=['ancient_stamp'],requires=['sanctuary_ready'],hidden=True),obj('chest','fragment',(19,11),loot=['heart_fragment'],requires=['sequence']),obj('chest','cache',(21,11),loot=['token_cache','ticket_bundle'],requires=['sequence'])]
    rooms['r22']['enemies']=[dict(id='slime',type='slime',pos=[7,5]),dict(id='bat',type='bat',pos=[11,11]),dict(id='mask',type='mirror_mask',pos=[15,8])]
    rooms['r22']['kill_order']=['slime','bat','mask'];rooms['r22']['goal']=['skin'];rooms['r22']['hint']='Carved order: slime, bat, mask. Wrong order awakens them again.'
    edge(2,19,(8,2));edge(19,2,(2,8));edge(19,5,(23,8),['gate']);edge(5,19,(12,2))
    edge(4,20,(8,13),abilities=['gloves']);edge(20,4,(2,8));edge(20,7,(23,8),['gate']);edge(7,20,(12,2),abilities=['gloves'])
    edge(10,21,(12,13),crystal='blue');edge(21,10,(2,8));edge(21,12,(23,8),['gate']);edge(12,21,(12,13),crystal='blue')
    edge(21,22,(12,13),['sanctuary','clear']);edge(22,21,(2,8))
    add(2,obj('crystal_switch','crystal',(7,10)),obj('crystal_barrier','library_red',(5,3),color='red'),obj('crystal_barrier','watch_blue',(12,2),color='blue'))
    rooms['r2']['hint']='Blue opens the library; red opens the watch. Three relays power B1F.'
    item(2,'relays')['flags'].append('flame')
    item(2,'lower')['progression']['needs'].append('flame')
    add(10,obj('crystal_switch','crystal',(8,9)))
    add(12,obj('crystal_barrier','blue',(15,8),color='blue'))
    add(16,obj('relay','warden_signal',(12,11),flags=['warden']))
    item(16,'gate')['requires']=['warden_signal']
    add(17,obj('crystal_switch','crystal',(5,11)),obj('pot','arena_pot',(9,4),renewable=True,explosive=True),obj('pot_supply','arena_rack',(4,11)))
    rooms['r17']['enemies'][0]['crystal_color']='blue'
    rooms['r17']['hint']='Dash anchor, bomb armor, sword core. Final phase needs BLUE crystal.'
    add(15,obj('pot','guard_pot',(6,11),renewable=True),obj('pot_supply','rack',(4,10)))
    rooms['r15']['enemies'].append(dict(id='elite',type='elite_guardian',pos=[15,5]))
    # Add loops unlocked by existing relay objectives; neither requires another small key.
    edge(12,14,(23,12),['gate'],abilities=['boots','mirror','magnet']);edge(14,12,(12,13),['gate'])
    edge(9,3,(12,2),['boots']);edge(3,9,(12,13),abilities=['boots'])
    # Shared-key economy remains six keys for five mandatory costs. Rewards are private escrow.
    loot={(1,'map'):['token_cache'],(3,'combat_key'):[],(4,'gloves'):['heart_fragment'],(6,'boss_key'):['ticket_bundle'],(7,'powder'):['magic_powder'],(8,'reward'):['golden_cat','heart_fragment','ticket_bundle'],(9,'boots'):['heart_recovery'],(10,'rest'):['heart_fragment'],(18,'treasure'):['token_cache','ticket_bundle']}
    for (number,name),values in loot.items():item(number,name)['loot']=values
    add(3,obj('chest','fragment',(5,11),loot=['heart_fragment']))
    item(19,'flame_signal')['progression']=dict(milestone='flame',needs=[])
    rooms['r21']['objects'][2]['progression']=dict(milestone='warden',needs=['stairs'])
    item(6,'boss_key')['progression']['needs'].append('warden')
    item(7,'powder')['progression']['alternatives']=[['watch_lock'],['flame','gloves']]
    # Distinct room materials and décor; mounted placements never alter collision.
    special={1:'stone_garden',5:'underground_library',7:'ancient_workshop',8:'forgotten_vault',12:'crystal_hall',14:'crystal_hall',16:'boss_chamber',17:'boss_chamber',18:'hidden_sanctuary'}
    for i,theme in special.items():rooms[f'r{i}']['theme']=theme
    for i,room in enumerate(rooms.values(),1):
        room['decorations']=[dict(kind='torch' if i in (1,19) else 'books' if i==5 else 'gear' if i in (7,20) else 'crystal' if i in (12,14,21) else 'banner',pos=[x,0]) for x in (4,10,16,22)]
        # Texture patterns and inlaid paths are room-specific authored presentation.
        room['seed']=i*79
    # 4.1 is an additive content update: existing coordinates/save schema remain valid.
    item(3,'combat_key').update(type='chest',small_keys=2,hidden=True)
    item(3,'combat_key').pop('color',None);item(3,'combat_key').pop('amount',None)
    for number,name in ((5,'mirror'),(9,'boots'),(13,'portal_key'),(19,'disc'),(20,'cache'),(21,'warden_cache'),(22,'skin'),(22,'stamp')):
        item(number,name)['hidden']=True
    item(6,'boss_key').update(hidden=True,ability_requires=['boots'],flag_requires=['prism','warden'])
    # A subtle book-wall passage and a remotely opened foundry passage add optional loops.
    edge(5,8,(23,13));edge(8,5,(12,13))
    rooms['r5']['exits'][-1].update(entrance='walkthrough',arrival=[12,12])
    rooms['r8']['exits'][-1].update(entrance='cave',arrival=[23,12])
    edge(11,22,(23,12));edge(22,11,(23,12))
    rooms['r11']['exits'][-1].update(entrance='remote',flag_requires=['flame','warden'],arrival=[23,11])
    rooms['r22']['exits'][-1].update(entrance='stone',arrival=[23,11])
    for room in rooms.values():
        room['content_revision']='4.1'
        for exit in room['exits']:
            if 'entrance' in exit:continue
            if exit.get('stairs'):
                exit['entrance']='stairs_down' if room['floor']=='1F' else 'stairs_up'
            else:
                objects={o['id']:o for o in room['objects']}
                gates=[objects[i] for i in exit.get('requires',[]) if i in objects]
                exit['entrance']='boss_gate' if any(o.get('key')=='boss' for o in gates) else 'locked' if any(o.get('key')=='small' for o in gates) else 'cave' if any(o['type']=='cracked' for o in gates) else 'stone'
    from puzzle_maze.layout42 import repair
    return repair(rooms)

if __name__=='__main__':
    (Path(__file__).parent/'maps/dungeon_v4.json').write_text(json.dumps(build(),indent=2)+'\n')
