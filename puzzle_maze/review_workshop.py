"""Capture the real Grey Pixel route, workshop cinematic, inspection and legal paths."""
import argparse
from pathlib import Path
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.review_cozy_studio import walk
from puzzle_maze.studio_layout import approach

def generate(output='/tmp/forgotten-workshop'):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    g=Game(headless=True,persistent=False);g.scene=GameScene.PLAY;s=g.session
    s.inventory.abilities.add('map');s.inventory.bombs=2;s.enter('r24',(21,7));g.visual=[21.,7.]
    def key(k):g.event(pygame.event.Event(pygame.KEYDOWN,key=k))
    def shot(name):
        g.draw(0);pygame.image.save(g.screen,out/(name+'.png'))
        rects=g.renderer.ui.rects
        assert all(g.screen.get_rect().contains(r) for r in rects),name
        assert all(not a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]),name
    key(pygame.K_b);walk(g,(18,7));s.tick(1.7);s.tick(.7);s.tick(.5)
    walk(g,(23,8));key(pygame.K_e);assert g.scene==GameScene.DISCOVERY
    g.update(3);shot('00_grey_pixel');g.update(3)
    walk(g,(23,9));walk(g,(23,8));assert s.rooms.current=='r28';g.update(.01)
    for t,name in ((.1,'00a_signal_lost'),(.3,'00b_crt_beam'),(.7,'00c_crt_sweep'),(1.,'01_maze_transition'),(1.5,'02_workshop_reveal'),(3.,'03_miao_entrance'),(6.8,'04_prototype_focus'),(8.3,'05_archived_repair'),(10.2,'06_story_dialogue')):
        while g.lab_entrance.time<t:g.update(min(1/60,t-g.lab_entrance.time))
        shot(name)
    for i in range(5):
        key(pygame.K_RETURN);g.update(.3)  # Complete the typewriter line.
        shot('dialogue_'+str(i)+'_complete')
        key(pygame.K_RETURN);g.update(.3)
    assert g.scene==GameScene.PLAY;shot('07_workshop_overview')
    for i,obj in enumerate(list(s.puzzles.objects.values())):
        pos,facing=approach(s.rooms.data,obj.pos);walk(g,pos);s.player.facing=facing
        shot('inspect_'+obj.id+'_prompt')
        key(pygame.K_RETURN if i%2 else pygame.K_e)
        assert g.scene==GameScene.SCROLL and g.reading==obj.data['content_id'],obj.id
        shot('inspect_'+obj.id+'_open');key(pygame.K_RETURN)
    # Explicit obstruction checks through the same move method used by the game.
    for start,direction in (((3,6),(0,-1)),((12,6),(0,-1)),((8,9),(0,1))):
        walk(g,start);assert not s.move(*direction),(start,direction)
    # Capture natural movement and sleep through normal gameplay updates.
    walk(g,(6,12))
    for _ in range(180):g.update(1/60)
    shot('miao_roaming')
    for _ in range(54*60):
        g.update(1/60)
        if s.studio_companion.state=='sleep':break
    assert s.studio_companion.state=='sleep'
    shot('miao_sleeping')
    walk(g,(1,7));assert s.rooms.current=='r24';shot('08_safe_exit')
    print('Real bomb / Grey Pixel / workshop entrance / all inspections / collisions / exit verified:',out)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/forgotten-workshop')
    generate(parser.parse_args().output)
