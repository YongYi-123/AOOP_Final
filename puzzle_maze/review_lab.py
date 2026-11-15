"""Capture actual presentation states without touching player saves."""
import argparse
from pathlib import Path
from collections import defaultdict
import pygame
from puzzle_maze.game import Game,GameScene

def generate(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    g=Game(headless=True);g.save=lambda:None;g.fade=0
    def capture(name):
        g.draw(0);pygame.image.save(g.screen,output/(name+'.png'))
        for i,rect in enumerate(g.renderer.ui.rects):
            assert g.screen.get_rect().contains(rect),(name,rect)
            assert not any(rect.colliderect(other) for other in g.renderer.ui.rects[i+1:]),name
    for room in ('r1','r12','r24'):
        g.session.enter(room);g.scene=GameScene.PLAY
        g.visual=[22.,7.] if room=='r24' else [12.,7.];g.toast_time=0
        if room=='r24':g.session.player.x=20;g.session.player.y=9;g.visual=[20.,9.]
        capture(room)
    g.session.enter('r28',(2,7));g.visual=[2.,7.];g.scene=GameScene.PLAY
    g.update(.01,defaultdict(bool));capture('lab_doorway')
    for i in range(120):g.update(1/60)
    capture('lab_walk')
    for i in range(210):g.update(1/60)
    capture('lab_dialogue')
    for line in range(1,5):
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN));g.update(.3)
        capture('memory_'+str(line))
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
    g.session.enter('r27',(2,7));g.visual=[11.,7.];g.scene=GameScene.PLAY
    g.update(.01,defaultdict(bool));g.update(.7);capture('treasury_reveal')
    g.update(2);capture('treasury_before')
    for key in ('royal_tokens','royal_tickets','royal_collection'):
        o=g.session.puzzles.objects[key];g.session.player.x=o.x-1;g.session.player.y=o.y
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
        for i in range(45):g.session.tick(1/60)
    g.visual=[11.,7.];capture('treasury_after')
    print('Presentation frames and subtitle bounds verified:',output)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/kevin-lab-review')
    generate(parser.parse_args().output)
