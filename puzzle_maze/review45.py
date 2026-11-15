"""Reproducible palette and English lore rendering, without touching saves."""
import argparse
from pathlib import Path
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.secret45 import LORE

def generate(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    g=Game(headless=True,campaign='4.5');sheet=pygame.Surface((960,480))
    for i,room in enumerate(('r1','r5','r11','r12','r27','r28')):
        g.session.enter(room,(12,8));g.visual=[g.session.player.x,g.session.player.y]
        g.scene=GameScene.PLAY;g.fade=0;g.toast_time=0;g.draw(.016)
        pygame.image.save(g.screen,output/f'{room}.png')
        sheet.blit(pygame.transform.scale(g.screen,(320,240)),((i%3)*320,(i//3)*240))
    pygame.image.save(sheet,output/'palettes.png')
    for key in LORE:
        g.scene=GameScene.SCROLL;g.reading=key;g.draw(.016)
        pygame.image.save(g.screen,output/f'{key}.png')
        rects=g.renderer.ui.rects
        for i,rect in enumerate(rects):
            assert g.screen.get_rect().contains(rect),(key,rect)
            assert all(not rect.colliderect(other) for other in rects[i+1:]),key
    print(f'Maze palette and English text review: {output}')
    pygame.quit()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/maze45-review')
    generate(parser.parse_args().output)
