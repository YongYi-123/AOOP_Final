"""Inspect the real studio, nearby prompts, sofa performance and maze transition."""
import argparse
from pathlib import Path
from collections import defaultdict
import pygame
from puzzle_maze.dev_preview import PreviewGame
from puzzle_maze.game import GameScene
from puzzle_maze.review_cozy_studio import generate,walk
from puzzle_maze.studio_interactions import nearby

def generate_refinement(output='/tmp/studio-refinement'):
    generate(output)
    out=Path(output);g=PreviewGame('developer-room',True)
    def key(k):g.event(pygame.event.Event(pygame.KEYDOWN,key=k))
    def shot(name):
        g.draw(0);pygame.image.save(g.screen,out/(name+'.png'))
        rects=g.renderer.ui.rects
        assert all(g.screen.get_rect().contains(r) for r in rects),name
        assert all(not a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]),name
    walk(g,(4,11));g.session.player.facing=(0,-1)
    assert nearby(g.session)==('sofa','Sit');shot('16_sofa_prompt');key(pygame.K_e)
    g.update(.2);shot('17_sitting_down');g.update(.2);shot('18_seated')
    key(pygame.K_e);g.update(.2);shot('19_standing_up');g.update(.2)
    assert g.studio_seat is None;g.cooldown=0;g.update(.14,defaultdict(bool,{pygame.K_RIGHT:True}))
    assert (g.session.player.x,g.session.player.y)==(5,11)
    for name,content in (('20_notebook_prompt','note'),('21_todo_prompt','studio_todo'),('22_photo_prompt','photo')):
        g.inspect_key(content);key(pygame.K_RETURN);shot(name)
        key(pygame.K_e);shot(name+'_read');key(pygame.K_RETURN)
    g.restart_preview('grey-pixel');g.draw(0);g.finish_discovery();g.update(.01)
    for t,name in ((.25,'23_maze_distortion'),(.85,'24_room_fade'),(1.5,'25_monitors_wake')):
        g.update(t-g.lab_entrance.time);shot(name)
    g.restart_preview('developer-room')
    for i,t in enumerate((0.,.6,4.05,7.1,8.6)):
        g.renderer.time=t;g.draw(0)
        crop=g.renderer.surface.subsurface((140,90,24,25))
        pygame.image.save(pygame.transform.scale(crop,(144,150)),out/('miao_idle_'+str(i)+'.png'))
    print('Studio prompts, sitting / standing, production entry and text layout verified:',out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='/tmp/studio-refinement')
    generate_refinement(p.parse_args().output)
