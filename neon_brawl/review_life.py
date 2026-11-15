"""Staged real campaign frames for civilian reactions and street-cat expressions."""
from pathlib import Path
import pygame
from .model import Campaign,EnemyFighter
from .art import Renderer
from .ambient import cat_sprite

def generate(output='/tmp/brawl-street-life'):
    from font import get_font
    output=Path(output);output.mkdir(parents=True,exist_ok=True);pygame.init()
    renderer=Renderer(get_font());surface=pygame.Surface((400,300));c=Campaign('NOVA');c.player.x=180;c.encounter_age=3
    def shot(name,time):
        renderer.world(surface,c,time);renderer.world(surface,c,time+.6)
        pygame.image.save(pygame.transform.scale(surface,(1200,900)),output/(name+'.png'))
    c.street_life.update(.01,26,0,0,c.player,[],0);shot('normal',10)
    c.enemies=[EnemyFighter('grunt',130+i*75,225,i) for i in range(3)]
    c.street_life.update(.1,27,0,0,c.player,c.enemies,0);shot('spectators',11)
    for _ in range(20):c.street_life.update(.05,28,0,0,c.player,c.enemies,0)
    officer=next(p for p in c.street_life.people if p.role=='police');officer.x=officer.home=275
    c.street_life.update(.1,28,0,0,c.player,c.enemies,0)
    c.cats.update(.1,6,0,0,c.player.x,c.enemies,0);shot('panic_police_cats',12)
    sheet=pygame.Surface((550,240));sheet.fill((34,37,52))
    for row,state in enumerate(('walk','sit','groom')):
        for variant in range(5):
            sheet.blit(pygame.transform.scale(cat_sprite(variant,state,0,1),(88,64)),(variant*110+10,row*80+8))
    pygame.image.save(sheet,output/'cat_faces.png')
    print('Street-life production frames:',output)
if __name__=='__main__':generate()
