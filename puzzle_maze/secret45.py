"""Grey Pixel uses the canonical story ID; it never replaces the Golden Cat."""
SECRET_ID='dungeon_grey_pixel'
DISCOVERY='DEBUG LAYER DISCOVERED. ORIGINAL MAP RESTORED.'
LORE={
 'kevin_photo':('OLD PHOTOGRAPH',('Kevin and a much smaller','Miao, beside the workbench.','His hand steadies her paw.','The corners are worn soft.')),
 'kevin_note':('KEVIN / HANDWRITTEN NOTE',('Prototype 07 failed again.','Miao stayed until sunrise.','She seems to think I am','doing something important.')),
 'miao_memory':('MIAO MEOW',('I know that blanket.','He always folded it twice.','I never asked him to.','He just noticed.')),
 'lab_gpu':('VINTAGE GRAPHICS CARD',('Twin fans. Worn contacts.','Kevin kept this card alive','through countless nights.')),
 'lab_keyboard':('CLICK. CLACK.',('A handwritten label:','DO NOT LET MIAO WALK','ON THIS KEYBOARD.','The label has paw prints.')),
 'lab_terminal':('BUILD FAILED',('ERROR: CAT DETECTED','ON KEYBOARD.','The error looks pleased','with itself.')),
 'debug_layer':('GREY PIXEL',('DEBUG LAYER DISCOVERED.','ORIGINAL MAP RESTORED.','The western arch still leads','back to the archive.')),
}

from puzzle_maze.developer_diaries import DIARIES
LORE.update(DIARIES)
from puzzle_maze.studio_notes import NOTES
LORE.update(NOTES)
LORE.update({
 'work_crt':('THE CRACKED CRT',('A tiny screen fracture.','Kevin marked the fault:','DO NOT FIX WITH A HAMMER.','The hammer is missing.')),
 'work_back':('OPEN SERVICE PANEL',('Each wire has a label.','One says: DOOR CHIME.','Another: NOT DOOR CHIME.','Both lead to the same bell.')),
 'work_frozen':('PAUSED FOREVER',('The score is still zero.','The machine reports:','PLAYER TWO IS A CAT.','WAITING FOR THUMBS.')),
 'work_prototype':('PROTOTYPE / RETURN PATH',('A grey test pixel travels','through an unfinished game.','An old service recording:','Leave a way back. Always.')),
})

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
    from puzzle_maze.studio_layout import configure,ENTRY
    configure(dev)
    archive['exits'][-1]['arrival']=list(ENTRY)
    rooms['r28']=dev
