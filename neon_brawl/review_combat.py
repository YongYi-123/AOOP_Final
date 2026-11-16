"""Combat contact sheets and an optional save-free, normal-input play window.

PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_combat
PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_combat --play
The sheets use staged encounters, not a claimed human playthrough.
"""
import argparse
from pathlib import Path
import time
import pygame
from .art import sprite
from .data import ATTACKS
from .game import BrawlGame
from .model import Campaign, EnemyFighter


def generate(output):
    from font import get_font
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    pygame.init();font=get_font()
    sheet=pygame.Surface((640,480));sheet.fill((23,24,43))
    names=('NOVA','REX','BRUNO','grunt','runner','bruiser','ranged','duelist',
           'shield','cyber','assassin','sniper','WARDEN','RELAY','NULL','echo')
    for i,name in enumerate(names):
        x,y=i%8*80,i//8*240
        sheet.blit(sprite(name),(x+8,y+10))
        sheet.blit(sprite(name,'hurt',1),(x+8,y+85))
        sheet.blit(sprite(name,'light',3,-1),(x+8,y+160))
        sheet.blit(font.render(name,(220,238,239)),(x+3,y+223))
    pygame.image.save(pygame.transform.scale(sheet,(1280,960)),output/'characters.png')

    phases=pygame.Surface((640,540));phases.fill((23,24,43))
    for row,action in enumerate(('light','heavy','special','airborne','dodge','defeated')):
        for frame in range(8):
            x,y=frame*80,row*90
            phases.blit(sprite('NOVA',action,frame),(x+8,y+4))
            phases.blit(font.render(f'{action.upper()} {frame+1}',(209,231,238)),(x+2,y+72))
    pygame.image.save(pygame.transform.scale(phases,(1280,1080)),output/'nova_poses.png')

    game=BrawlGame(font);surface=pygame.Surface((400,300));reviews=[]
    for action,key in (('punch',pygame.K_j),('heavy',pygame.K_k),('special',pygame.K_u),
                       ('dodge',pygame.K_i),('jump',pygame.K_l)):
        c=Campaign('NOVA');c.spawned=True;c.encounter_age=3
        c.player.x=145;c.enemies=[EnemyFighter('bruiser',183,220)]
        game.campaign=c;game.change('playing');game.started=True
        game.handle_event(pygame.event.Event(pygame.KEYDOWN,key=key))
        game.handle_event(pygame.event.Event(pygame.KEYUP,key=key))
        sheet=pygame.Surface((800,600))
        for index,frame_limit in enumerate((3,9,18,36)):
            begin=(0,3,9,18)[index]
            for _ in range(frame_limit-begin):game.update(1/60)
            game.draw(surface)
            sheet.blit(surface,((index%2)*400,(index//2)*300))
        pygame.image.save(sheet,output/f'{action}.png')
        reviews.append(c)
    for stage,(name,action) in enumerate((('WARDEN','slam'),('RELAY','pulse'),('NULL','strike'))):
        c=Campaign('NOVA');c.stage=stage;c.wave=3;c.player.x=1130;c.camera=1050
        c.spawn();boss=next(e for e in c.enemies if e.boss)
        boss.x,boss.y=1190,220;boss.timer=0;boss.invulnerable=0;boss.facing=-1
        boss.begin(action,c.player);game.campaign=c;game.change('playing')
        sheet=pygame.Surface((800,600))
        a=ATTACKS[action]
        for i,age in enumerate((a.windup*.2,a.windup*.8,a.windup+a.active*.5,a.windup+a.active+a.recovery*.5)):
            boss.swing.age=age;game.time+=.6;game.draw(surface)
            sheet.blit(surface,((i%2)*400,(i//2)*300))
        pygame.image.save(sheet,output/f'{name.lower()}.png')
        reviews.append(c)
    start=time.perf_counter()
    for frame in range(240):
        game.campaign=reviews[frame%len(reviews)];game.time+=1/60;game.draw(surface)
    mean=(time.perf_counter()-start)*1000/240
    print(f'Staged render review: {output}; mean {mean:.2f} ms/frame (240 native frames).')


def play():
    from font import get_font
    pygame.init()
    window=pygame.display.set_mode((1200,900),pygame.RESIZABLE)
    pygame.display.set_caption('NEON BRAWL / combat preview / no save or rewards')
    game=BrawlGame(get_font());game.selection=1;game.change('select')
    clock=pygame.time.Clock()
    running=True
    while running and not game.wants_exit:
        dt=min(.05,clock.tick(60)/1000)
        for event in pygame.event.get():
            if event.type==pygame.QUIT:running=False
            else:game.handle_event(event)
        game.update(dt);game.draw(window);pygame.display.flip()
    pygame.quit()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='/tmp/brawl-combat-review')
    parser.add_argument('--play',action='store_true')
    args=parser.parse_args()
    if args.play:play()
    else:generate(args.output)
