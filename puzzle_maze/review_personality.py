"""Diagnostic captures through production preview scenes, never real profiles."""
from pathlib import Path
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import GameScene
from puzzle_maze.slime_art import slime_frame

def generate(output='/tmp/maze-personality'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    g=PreviewGame(headless=True)
    def shot(name):
        g.draw(0);pygame.image.save(g.screen,output/(name+'.png'))
        rects=g.renderer.ui.rects
        assert all(g.screen.get_rect().contains(r) for r in rects),name
        assert all(not a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]),name
    for dt,name in ((.5,'anomaly'),(1.4,'item_form'),(1.,'item_reveal')):g.update(dt);shot(name)
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE));g.update(.01);shot('doorway')
    for _ in range(120):g.update(1/60)
    shot('miao_walk')
    for _ in range(520):g.update(1/60)
    shot('miao_dialogue')
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
    pygame.image.save(pygame.transform.scale(g.renderer.developer_art.layer(),(1248,768)),output/'studio_overview.png')
    from puzzle_maze.secret45 import LORE
    g.visual=[12.,9.]
    for key in LORE:
        g.scene=GameScene.SCROLL;g.reading=key;shot(key)
    sheet=pygame.Surface((320,192));sheet.fill((32,43,53))
    for row,state in enumerate(('idle','attack','defeat')):
        for frame in range(4):sheet.blit(pygame.transform.scale(slime_frame(state,frame,row==1),(64,64)),(frame*80,row*64))
    pygame.image.save(sheet,output/'slime_states.png')
    for room in ('r1','r5','r11','r12','r14'):
        g.session.enter(room);g.scene=GameScene.PLAY;g.visual=[12.,7.];g.toast_time=0;shot(room)
    from puzzle_maze.combat import EnemyState
    g.session.enter('r1');g.scene=GameScene.PLAY
    slime=next(e for e in g.session.combat.enemies if e.kind=='slime')
    g.session.player.x=slime.x+3;g.session.player.y=slime.y
    g.visual=[float(g.session.player.x),float(g.session.player.y)]
    shot('slime_idle_world');slime.state=EnemyState.WINDUP;shot('slime_attack_world')
    from collections import defaultdict
    g.restart_preview('developer-room');g.session.player.x=2;g.session.player.y=7;g.visual=[2.,7.]
    g.update(.14,defaultdict(bool,{pygame.K_LEFT:True}));g.update(.5,defaultdict(bool))
    assert g.session.rooms.current=='r24'
    shot('studio_exit')
    print('Preview and text bounds captures:',output)
if __name__=='__main__':generate()
