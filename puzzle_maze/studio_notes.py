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
PAGES['store_aoop']=(
 ('Game owns Room.','Room owns Cat.','Cat owns the keyboard.','Kevin owns the bugs.'),
 ('PUBLIC: Miao may enter.','PRIVATE: Kevin may not eat','the emergency cat food.','Miao wrote the access rules.'),
)
NAMES={'kevin_photo':'Photo','kevin_note':'Notebook','miao_memory':'Miao Meow','lab_gpu':'GPU','lab_keyboard':'Keyboard',
 'lab_terminal':'Terminal','lab_coffee':'Coffee','lab_duck':'Duck','lab_button':'Red button',
 'studio_todo':'To-do list','studio_food':'Food cans','studio_cushion':'Cushion','studio_reminder':'Reminder'}

DESCRIPTIONS={
 'kevin_photo':"An old photograph is tucked beside the workbench.",
 'kevin_note':"Someone left a notebook on the engineer's desk.",
 'miao_memory':"Miao looks like she has something to tell me.",
 'lab_gpu':"There is a dusty graphics card on an anti-static mat.",
 'lab_keyboard':"A handwritten label is stuck to this old keyboard.",
 'lab_terminal':"The prototype's monitor still has a message on it.",
 'lab_coffee':"An old coffee mug. There is a note underneath it.",
 'lab_duck':"A rubber duck is guarding the test equipment.",
 'lab_button':"Someone labelled this very tempting red button.",
 'studio_todo':"A folded to-do list is pinned beside the tools.",
 'studio_food':"These food cans all have little handwritten labels.",
 'studio_cushion':"The cat cushion has been carefully patched up.",
 'studio_reminder':"A small reminder is taped above the workbench.",
 'work_crt':"A sticky note is taped to this abandoned arcade machine.",
 'work_back':"There are handwritten labels inside the open service panel.",
 'work_frozen':"This broken machine is still showing a message.",
 'work_prototype':"There is a service log beside Prototype 07.",
 'store_tools':"A scrap of paper is caught in the toolbox drawer.",
 'store_parts':"These parts boxes have a handwritten sorting guide.",
 'store_timebox':"Someone put a very serious warning on this parcel.",
 'store_server':"A maintenance note hangs from the backup server.",
 'store_aoop':"A cute cat doodle covers this old classroom board.",
 'store_breadboard':"There is a lab report inside this electronics case.",
 'store_cables':"A little tag is tied around the cable reel.",
}

def inspection_dialogue(key,play_sound=None):
    from types import SimpleNamespace
    from puzzle_maze.studio_dialogue import make_dialogue
    import sys
    from pathlib import Path
    host=str(Path(__file__).resolve().parents[1]/'arcade_lobby')
    if host not in sys.path:sys.path.append(host)
    from player import PlayerLook
    text=DESCRIPTIONS.get(key,"A repair diary is taped beside this old equipment.")
    look=PlayerLook('expedition',shirt=(67,158,163),shirt_dark=(49,112,127),
                    beanie=(85,89,103),beanie_dark=(57,65,79),pom=(94,98,111))
    return make_dialogue([('PLAYER',text,'normal')],play_sound,
                         context={'players':[SimpleNamespace(look=look)]})

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
    footer='LEFT/RIGHT: Page / ENTER: Close' if len(pages)>1 else 'ENTER / ESC: Close'
    renderer.text(footer,28,y+85,(128,98,60),max_width=224,small=True)
    if len(pages)>1:
        renderer.text(f'{page+1}/{len(pages)}',274,y+85,(115,86,52),max_width=24,small=True)
