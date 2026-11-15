"""Real rendered research-complex scenes, diagram sheets and new cat animation frames."""
from pathlib import Path
import time
import pygame
from .model import Campaign
from .art import Renderer
from .lab_cats import cat_sprite,SIZE
from .lab_staff import engineer_sprite,CYCLES
from .ml_lab import ml_screen
from .hardware_posters import schematic,DISPLAY_TITLES
from .oop_core import class_diagram

def generate(output='/tmp/brawl-research-review'):
    from font import get_font
    output=Path(output);output.mkdir(parents=True,exist_ok=True);pygame.init()
    r=Renderer(get_font());s=pygame.Surface((400,300));sheet=pygame.Surface((1600,900));frames=[]
    for stage in range(3):
        for section in range(4):
            c=Campaign('NOVA');c.stage=stage;c.wave=section;c.player.x=section*350+80;c.camera=section*350
            c.spawn();c.encounter_age=3
            c.staff.update(6,6,stage,section,c.player,c.enemies,c.camera)
            c.cats.update(.05,6,stage,section,c.player.x,c.enemies,c.camera)
            r.world(s,c,6);r.world(s,c,6.6)
            pygame.image.save(pygame.transform.scale(s,(1200,900)),output/f'stage{stage+1}_{section+1}.png')
            sheet.blit(s,(section*400,stage*300));frames.append(c)
    pygame.image.save(sheet,output/'departments.png')
    c=frames[-1]
    for e in c.enemies:
        if e.boss:e.phase=3;e.state='phase'
    r.world(s,c,8);r.world(s,c,8.6);pygame.image.save(pygame.transform.scale(s,(1200,900)),output/'final_runtime.png')
    cats=pygame.Surface((650,672));cats.fill((36,40,58))
    for row,state in enumerate(('walk','sit','groom','sleep','stretch','run','observe')):
        for variant in range(5):cats.blit(pygame.transform.scale(cat_sprite(variant,state,0,1),(104,88)),(variant*130+8,row*96+4))
    pygame.image.save(cats,output/'cat_designs.png')
    anim=pygame.Surface((832,440));anim.fill((36,40,58))
    for variant in range(5):
        for f in range(8):anim.blit(pygame.transform.scale(cat_sprite(variant,'walk',f,1),(104,88)),(f*104,variant*88))
    pygame.image.save(anim,output/'cat_walk_blink.png')
    engineers=pygame.Surface((864,504));engineers.fill((36,40,58))
    for row,role in enumerate(CYCLES):
        for col,state in enumerate(CYCLES[role]):engineers.blit(pygame.transform.scale(engineer_sprite(role,state,1,row),(144,126)),(col*144,row*126))
    pygame.image.save(engineers,output/'engineer_cycles.png')
    diagrams=[ml_screen(i) for i in range(4)]+[schematic(i) for i in range(len(DISPLAY_TITLES))]+[class_diagram(i) for i in range(5)]
    boards=pygame.Surface((1044,670));boards.fill((30,34,52))
    for i,image in enumerate(diagrams):boards.blit(pygame.transform.scale(image,(348,134)),((i%3)*348,(i//3)*134))
    pygame.image.save(boards,output/'technical_diagrams.png')
    before=(c.player.health,c.score,[(e.x,e.y,e.health) for e in c.enemies]);start=time.perf_counter()
    for i in range(240):r.world(s,c,9+i/60)
    assert before==(c.player.health,c.score,[(e.x,e.y,e.health) for e in c.enemies])
    print(f'Research review: {output}; 240 native render frames mean {(time.perf_counter()-start)*1000/240:.2f} ms (not full-game FPS)')
if __name__=='__main__':generate()
