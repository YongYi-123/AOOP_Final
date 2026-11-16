"""Grey Pixel uses the canonical story ID; it never replaces the Golden Cat."""
SECRET_ID='dungeon_grey_pixel'
DISCOVERY='DEBUG LAYER DISCOVERED. ORIGINAL MAP RESTORED.'
LORE={
 'kevin_photo':('OLD PHOTOGRAPH', ('I asked Miao to pose.', 'She inspected my soldering.', 'I kept the blurry photo.', 'Best review I got all week.')),
 'kevin_note':('KEVIN / HANDWRITTEN NOTE', ('I missed dinner again.', 'Prototype 07 still fails.', 'Miao stayed until sunrise.', 'I should build her a bed.')),
 'miao_memory':('MIAO MEOW',('I know that blanket.','He always folded it twice.','I never asked him to.','He just noticed.')),
 'lab_gpu':('VINTAGE GRAPHICS CARD', ('I replaced both tiny fans.', 'The card survived the night.', 'My patience did not.', 'I saved the card anyway.')),
 'lab_keyboard':('CLICK. CLACK.', ('I wrote: NO CATS ON KEYS.', 'Miao added paw prints.', 'I revised the house rules:', 'ASK THE CAT FOR ACCESS.')),
 'lab_terminal':('BUILD FAILED', ('I fixed a missing bracket.', 'My agent added twelve more.', 'Now the build has eyebrows.', 'I have asked it to stop.')),
 'debug_layer':('GREY PIXEL',('DEBUG LAYER DISCOVERED.','ORIGINAL MAP RESTORED.','The western arch still leads','back to the archive.')),
}

from puzzle_maze.developer_diaries import DIARIES
LORE.update(DIARIES)
from puzzle_maze.studio_notes import NOTES
LORE.update(NOTES)
LORE.update({
 'repair_log':('ARCADE REPAIR LOG',('I kept the maintenance log.','The totals are worrying.')),
 'project_file':('ABANDONED GAME PROJECT FILE',('I kept my cancelled project.','Three roads. One new idea.')),
 'work_space':('STARFALL ASSAULT / TEST UNIT',('A scorched test cabinet.','Its diagnostics still run.')),
 'power_cabinet':('MAIN POWER DISTRIBUTION',('A damaged power cabinet.','The warning light flickers.')),
 'store_tools':('THE MISSING 10 MM SOCKET', ('I bought five 10 mm sockets.', 'All five disappeared.', 'I bought a sixth.', 'Miao is sitting on it.')),
 'store_parts':('PARTS SORTING SYSTEM', ('[A] I tested these parts.', '[B] I broke these parts.', '[C] They work when I look.', 'I do not trust box C.')),
 'store_timebox':('THE BUG BOX', ('I labelled this box: BUGS.', 'I meant software bugs.', 'The box just sneezed.', 'I am moving my desk.')),
 'store_server':('THE BACKUP SERVER', ('I built a cooling system.', 'Fan 1 only cools Fan 2.', 'Fan 2 only cools Fan 1.', 'I forgot to plug it in.')),
 'store_aoop':('AOOP / OWNERSHIP DIAGRAM', ('I wrote: Game owns Room.', 'Then I added: Room owns Cat.', 'Miao crossed that out.', 'She says Cat owns Game.')),
 'store_breadboard':('THE BREADBOARD EXPERIMENT', ('I tested a breadboard.', 'I added a sandwich.', 'The circuit still failed.', 'My lunch passed inspection.')),
 'store_cables':('CABLE MANAGEMENT', ('I tried to untangle a lead.', 'Three hours. One round knot.', 'I called it cable storage.', 'Miao called it her pillow.')),
 'work_crt':('THE CRACKED CRT', ('I found a crack in the CRT.', 'I wrote: NO HAMMERS.', 'Someone borrowed my hammer.', 'I will try to trust them.')),
 'work_back':('OPEN SERVICE PANEL', ('I labelled every wire.', 'Both labels say THIS END.', 'I traced them to the bell.', 'I am now afraid to knock.')),
 'work_frozen':('PAUSED FOREVER', ('I added a second player.', 'Miao took that seat at once.', 'I am still waiting for her', 'to grow opposable thumbs.')),
 'work_prototype':('PROTOTYPE / RETURN PATH', ('I left one grey test pixel.', 'My map forgot this workshop.', 'The pixel did not forget.', 'Leave a way back. Always.')),
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
