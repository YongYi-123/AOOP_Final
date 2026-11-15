"""Grey Pixel uses the canonical story ID; it never replaces the Golden Cat."""
SECRET_ID='dungeon_grey_pixel'
DISCOVERY='DEBUG LAYER DISCOVERED. ORIGINAL MAP RESTORED.'
LORE={
 'kevin_photo':('OLD PHOTOGRAPH',('Kevin grins at a crooked','stack of arcade sketches.','A tiny chair sits beside','his enormous workbench.')),
 'kevin_note':('KEVIN / HANDWRITTEN NOTE',('If a visitor finds this,','please use the good chair.','The other one squeaks in','three different keys.')),
 'miao_memory':('MIAO MEOW',('Twelve keyboards. Two paws.','This may take a while.','I call the quiet one.','If there is a quiet one.')),
 'lab_gpu':('VINTAGE GRAPHICS CARD',('Twin fans. Worn contacts.','Kevin kept this card alive','through countless nights.')),
 'lab_keyboard':('CLICK. CLACK.',('MIAO MEOW: This is louder','than the Arcade machines.','Does it have a quiet key?')),
 'lab_terminal':('BUILD FAILED',('BUILD FAILED: TOO MANY CATS.','Retry with fewer cats?','The terminal votes NO.')),
 'debug_layer':('GREY PIXEL',('DEBUG LAYER DISCOVERED.','ORIGINAL MAP RESTORED.','The western arch still leads','back to the archive.')),
}

from puzzle_maze.developer_diaries import DIARIES
LORE.update(DIARIES)

def add_secret(rooms):
    from puzzle_maze.build_dungeon import obj,base
    archive=rooms['r24']
    archive['objects'].extend([
        obj('cracked','debug_seam',(22,7),optional=True,duration=.6),
        obj('chest','grey_pixel',(23,7),optional=True,hidden=True,requires=['debug_seam'],ability_requires=['map'],grey_pixel=True),
    ])
    archive['exits'].append(dict(id='r24:r28',return_id='r28:r24',target='r28',pos=[23,8],arrival=[2,7],
                                entrance='cave',direction='EAST',requires=['debug_seam','grey_pixel'],abilities=['map'],orb_allowed=True))
    dev=base('Developer Room','hidden_sanctuary',(5,1),'1F')
    dev.update(layout_revision='4.0',content_revision='4.5',grid_x=5,grid_y=1,hidden=True,
               hint='The coordinates are broken. The western arch is real.',architecture='fractured',
               objects=[obj('mystery_scroll','photo',(12,5),content_id='kevin_photo'),
                        obj('mystery_scroll','note',(14,5),content_id='kevin_note'),
                        obj('mystery_scroll','miao',(8,8),content_id='miao_memory')],enemies=[],goal=[],
               decorations=[dict(kind='sigil',pos=[6,0])],
               exits=[dict(id='r28:r24',return_id='r24:r28',target='r24',pos=[1,7],arrival=[23,9],
                           entrance='cave',direction='WEST',requires=[],abilities=[],orb_allowed=True)])
    dev['tiles']=['#'*26]+['#'+'.'*24+'#' for _ in range(14)]+['#'*26]
    dev['objects'].extend([obj('mystery_scroll','gpu',(18,6),optional=True,content_id='lab_gpu'),
                           obj('mystery_scroll','keyboard',(10,6),optional=True,content_id='lab_keyboard'),
                           obj('mystery_scroll','terminal',(21,9),optional=True,content_id='lab_terminal')])
    from puzzle_maze.developer_diaries import add_interactions
    add_interactions(dev)
    rooms['r28']=dev
