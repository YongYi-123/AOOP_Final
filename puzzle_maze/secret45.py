"""Grey Pixel uses the canonical story ID; it never replaces the Golden Cat."""
SECRET_ID='dungeon_grey_pixel'
DISCOVERY='DEBUG LAYER DISCOVERED. ORIGINAL MAP RESTORED.'
LORE={
 'kevin_photo':('OLD PHOTOGRAPH',('An arcade before opening day.','Kevin stands beside two empty','cabinets. Someone has scratched','a face out of the photograph.')),
 'kevin_note':('KEVIN / HANDWRITTEN NOTE',('If the signal erases a room,','look beyond the map boundary.','I kept the original here.','Please do not forget us. - Kevin')),
 'miao_memory':('MIAO MIAO',('This room... I feel like I have','been here before. But why can','I not remember anything?', 'The photograph feels familiar.')),
 'debug_layer':('GREY PIXEL',('DEBUG LAYER DISCOVERED.','ORIGINAL MAP RESTORED.','The western arch still leads','back to the archive.')),
}

def add_secret(rooms):
    from puzzle_maze.build_dungeon import obj,base
    archive=rooms['r24']
    archive['objects'].extend([
        obj('cracked','debug_seam',(22,7),optional=True,duration=.6),
        obj('chest','grey_pixel',(23,7),optional=True,hidden=True,requires=['debug_seam'],ability_requires=['map'],grey_pixel=True),
    ])
    archive['exits'].append(dict(id='r24:r28',return_id='r28:r24',target='r28',pos=[23,8],arrival=[2,7],
                                entrance='cave',direction='EAST',requires=['debug_seam','grey_pixel'],abilities=['map'],orb_allowed=False))
    dev=base('Developer Room','hidden_sanctuary',(5,1),'1F')
    dev.update(layout_revision='4.0',content_revision='4.5',grid_x=5,grid_y=1,hidden=True,
               hint='The coordinates are broken. The western arch is real.',architecture='fractured',
               objects=[obj('mystery_scroll','photo',(12,5),content_id='kevin_photo'),
                        obj('mystery_scroll','note',(14,5),content_id='kevin_note'),
                        obj('mystery_scroll','miao',(8,8),content_id='miao_memory')],enemies=[],goal=[],
               decorations=[dict(kind='sigil',pos=[6,0])],
               exits=[dict(id='r28:r24',return_id='r24:r28',target='r24',pos=[1,7],arrival=[23,9],
                           entrance='cave',direction='WEST',requires=[],abilities=[],orb_allowed=False)])
    rooms['r28']=dev
