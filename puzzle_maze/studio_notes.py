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

_PAPER=None

def aged_paper():
    """Cached yellowed stock with soft stains, a fold and chipped edges."""
    global _PAPER
    if _PAPER is not None:return _PAPER
    paper=pygame.Surface((284,98),pygame.SRCALPHA);r=pygame.draw
    for y in range(98):
        edge=min(y,97-y,10)
        color=(214+edge*2,185+edge*2,130+edge*3)
        r.line(paper,color,(0,y),(283,y))
    for i in range(85):
        x=(i*73)%284;y=(i*29)%98
        if x<9 or x>275 or y<4 or y>94:
            paper.fill((176,145,98),(x,y,1,1))
    r.rect(paper,(183,150,99),(0,0,284,98),1)
    r.line(paper,(214,185,133),(140,3),(139,93))
    r.line(paper,(240,215,166),(141,3),(140,93))
    r.circle(paper,(207,177,123),(272,11),8,1)
    r.circle(paper,(214,184,130),(272,11),7,1)
    r.polygon(paper,(181,149,100),[(272,0),(283,0),(283,11)])
    r.line(paper,(246,222,175),(272,0),(283,11))
    for x,y in ((0,0),(281,95),(0,94)):
        paper.fill((0,0,0,0),(x,y,3,3))
    r.line(paper,(183,148,94),(5,17),(277,17))
    for y in (34,46,58,70):r.line(paper,(224,197,146),(7,y),(276,y))
    _PAPER=paper;return paper

def draw_note(renderer,key,page,room,preview=False):
    from puzzle_maze.secret45 import LORE
    pages=pages_for(key);page=max(0,min(page,len(pages)-1));title=LORE[key][0]
    obj=next((o for o in room['objects'] if o.get('content_id')==key),None)
    y=42 if obj and obj['pos'][1]>=8 else 136
    s=renderer.surface;r=pygame.draw;renderer.ui.clear()
    r.rect(s,(42,37,32),(17,y+4,286,99))
    s.blit(aged_paper(),(18,y))
    r.rect(s,(170,136,85),(22,y+4,2,2))
    renderer.text(title,28,y+5,(102,72,47),max_width=264)
    for i,line in enumerate(pages[page]):renderer.text(line,28,y+24+i*12,(94,76,52),max_width=264)
    footer=f'ARROWS: {page+1}/{len(pages)} / ENTER: Close' if len(pages)>1 else 'ENTER: Close / ESC: Exit' if preview else 'ENTER / ESC: Close'
    renderer.text(footer,28,y+84,(128,98,60),max_width=264)
