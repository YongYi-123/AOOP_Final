"""Warm personal notes, with an actual paged paper list instead of a quest log."""
import pygame
NOTES={
 'studio_todo':("KEVIN'S TO-DO LIST",('[X] Repair Arcade audio.','[X] Replace the GPU fan.','','A quieter fan was worth it.')),
 'studio_food':('MIAO / FOOD CUPBOARD',('Neatly arranged food cans.','Each has a tiny label:','For Miao. Her favorite.','Even the spare has a label.')),
 'studio_cushion':('THE SLEEPING CUSHION',('The seams are repaired','with different pink thread.','The little blanket is','folded with unusual care.')),
 'studio_reminder':('A SMALL REMINDER',('Turn the computer off','before Miao goes to sleep.','The fan keeps her awake.','She never complains.')),
}
PAGES={'studio_todo':(
 NOTES['studio_todo'][1],
 ("[ ] Buy Miao's favorite",'    canned food.','[ ] Wash her cushion.','    Gentle soap this time.'),
 ('[ ] Eat a proper dinner.','[ ] Finish the prototype.','','Noodles are not a meal.'),
 ('[ ] Take Miao outside','    when the rain stops.','','Pack her little blanket.'),
)}
NAMES={'kevin_photo':'Photo','kevin_note':'Notebook','miao_memory':'Miao Meow','lab_gpu':'GPU','lab_keyboard':'Keyboard',
 'lab_terminal':'Terminal','lab_coffee':'Coffee','lab_duck':'Duck','lab_button':'Red button',
 'studio_todo':'To-do list','studio_food':'Food cans','studio_cushion':'Cushion','studio_reminder':'Reminder'}

def pages_for(key):
    from puzzle_maze.secret45 import LORE
    return PAGES.get(key,(LORE[key][1],))

def draw_note(renderer,key,page,room,preview=False):
    from puzzle_maze.secret45 import LORE
    pages=pages_for(key);page=max(0,min(page,len(pages)-1));title=LORE[key][0]
    obj=next((o for o in room['objects'] if o.get('content_id')==key),None)
    y=42 if obj and obj['pos'][1]>=8 else 136
    s=renderer.surface;r=pygame.draw;renderer.ui.clear()
    r.rect(s,(103,77,59),(17,y+3,286,101));r.rect(s,(250,232,192),(18,y,284,98))
    r.line(s,(218,181,126),(21,y+17),(298,y+17));r.rect(s,(225,186,137),(21,y+3,3,3))
    renderer.text(title,28,y+5,(113,76,57),max_width=264)
    for i,line in enumerate(pages[page]):renderer.text(line,28,y+24+i*12,(109,86,65),max_width=264)
    footer=f'ARROWS: {page+1}/{len(pages)} / ENTER: Close' if len(pages)>1 else 'ENTER: Close / ESC: Exit' if preview else 'ENTER / ESC: Close'
    renderer.text(footer,28,y+84,(151,103,69),max_width=264)
