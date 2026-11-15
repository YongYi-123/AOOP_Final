"""Real Grey Pixel entry, collision navigation and production studio frame captures."""
import argparse
from collections import deque,defaultdict
from pathlib import Path
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.studio_layout import approach

def path_to(game,goal):
    s=game.session;start=(s.player.x,s.player.y);q=deque([start]);previous={start:None}
    while q:
        pos=q.popleft()
        if pos==goal:break
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nxt=pos[0]+dx,pos[1]+dy
            if nxt not in previous and s.can_enter(*nxt):previous[nxt]=pos;q.append(nxt)
    if goal not in previous:raise AssertionError('Unreachable capture location: '+str(goal))
    result=[];pos=goal
    while previous[pos] is not None:result.append(pos);pos=previous[pos]
    return list(reversed(result))

def walk(game,goal):
    for x,y in path_to(game,goal):
        dx,dy=x-game.session.player.x,y-game.session.player.y
        key={(1,0):pygame.K_RIGHT,(-1,0):pygame.K_LEFT,(0,1):pygame.K_DOWN,(0,-1):pygame.K_UP}[(dx,dy)]
        old_room=game.session.rooms.current
        game.cooldown=0;game.update(.14,defaultdict(bool,{key:True}))
        if game.session.rooms.current!=old_room:return
        assert (game.session.player.x,game.session.player.y)==(x,y)

def generate(output='/tmp/cozy-studio-review'):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    g=Game(headless=True,persistent=False);g.scene=GameScene.PLAY;s=g.session
    # Only initial supplies/location are staged. The bomb, item, door and all later
    # movement use the same production event/update path as the Arcade cabinet.
    s.inventory.abilities.add('map');s.inventory.bombs=2;s.enter('r24',(21,7));g.visual=[21.,7.]
    def key(value):g.event(pygame.event.Event(pygame.KEYDOWN,key=value))
    def shot(name):
        g.draw(0);pygame.image.save(g.screen,out/(name+'.png'))
        rects=g.renderer.ui.rects
        assert all(g.screen.get_rect().contains(r) for r in rects),name
        assert all(not a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:]),name
    key(pygame.K_b);walk(g,(18,7));s.tick(1.7);s.tick(.7);s.tick(.5)
    walk(g,(23,8));key(pygame.K_e);assert g.scene==GameScene.DISCOVERY
    g.update(3);shot('00_grey_pixel');g.update(3)
    walk(g,(23,9));walk(g,(23,8));assert s.rooms.current=='r28'
    g.update(.01)
    for moment,name in ((.6,'01_warm_reveal'),(3.,'02_miao_walk'),(5.8,'03_miao_reaction'),(6.9,'04_photo_focus'),(8.3,'05_memory_fragment'),(10.2,'06_story_dialogue')):
        while g.lab_entrance.time<moment:g.update(min(1/60,moment-g.lab_entrance.time))
        shot(name)
    for i in range(1,5):key(pygame.K_RETURN);g.update(.3);shot('dialogue_'+str(i))
    key(pygame.K_RETURN);assert g.scene==GameScene.PLAY;g.fade=0;g.toast_time=0;shot('07_studio_overview')
    for name,rect in (('08_engineering_desk',(75,25,179,85)),('09_living_corner',(18,125,124,78)),('10_miao_corner',(220,120,88,78))):
        pygame.image.save(pygame.transform.scale(g.renderer.surface.subsurface(rect),(rect[2]*4,rect[3]*4)),out/(name+'.png'))
    todo=s.puzzles.objects['studio_todo'];pos,facing=approach(s.rooms.data,todo.pos)
    walk(g,pos);s.player.facing=facing;key(pygame.K_e);assert g.reading=='studio_todo'
    for i in range(4):
        if i:key(pygame.K_RIGHT)
        shot('todo_'+str(i+1))
    key(pygame.K_RETURN)
    # Real walking around and behind the furniture, not pose teleportation.
    for name,pos in (('11_desk_front',(8,6)),('12_desk_behind',(8,3)),('13_sofa_front',(3,11)),('14_cat_corner',(16,9))):
        walk(g,pos);shot(name)
    walk(g,(8,6));before=s.player.x,s.player.y;key(pygame.K_UP)
    g.cooldown=0;g.update(.14,defaultdict(bool,{pygame.K_UP:True}));assert before==(s.player.x,s.player.y)
    walk(g,(2,7));g.cooldown=0;g.update(.14,defaultdict(bool,{pygame.K_LEFT:True}));assert s.rooms.current=='r24'
    g.update(.5,defaultdict(bool));shot('15_safe_exit')
    print('Actual production entry, furniture paths, cinematic and paper pages verified:',out)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/cozy-studio-review')
    generate(parser.parse_args().output)
