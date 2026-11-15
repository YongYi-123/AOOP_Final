"""Real Grey Pixel entry, collision navigation and production studio frame captures."""
import argparse
from collections import deque,defaultdict
from pathlib import Path
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.studio_layout import approach

def path_to(game,goal):
    s=game.session;exits={tuple(e['pos']) for e in s.rooms.data['exits']}
    start=(s.player.x,s.player.y);q=deque([start]);previous={start:None}
    while q:
        pos=q.popleft()
        if pos==goal:break
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nxt=pos[0]+dx,pos[1]+dy
            if nxt not in previous and (nxt==goal or nxt not in exits) and s.can_enter(*nxt):previous[nxt]=pos;q.append(nxt)
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
    # Compatibility command: capture the current production workshop.
    from puzzle_maze.review_workshop import generate as workshop
    return workshop(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/cozy-studio-review')
    generate(parser.parse_args().output)
