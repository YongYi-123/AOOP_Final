"""Deterministic normal-input pilot. No health, damage, or campaign shortcuts."""
from neon_brawl.model import Campaign

def decide(c):
    p=c.player
    targets=[e for e in c.enemies if e.alive]
    if not targets: return (0,0),None
    e=min(targets,key=lambda e:abs(e.x-p.x)+abs(e.y-p.y)*2)
    dx=1 if e.x-p.x>27 else -1 if e.x-p.x< -27 else 0
    dy=1 if e.y-p.y>6 else -1 if e.y-p.y< -6 else 0
    facing=1 if e.x>p.x else -1
    if p.facing!=facing:
        return (facing,dy),None
    action=None
    if p.ready:
        danger=any(en.swing and abs(en.x-p.x)<105 and abs(en.y-p.y)<18 for en in targets)
        if danger and p.dodge_cooldown<=0: action='dodge'
        elif abs(e.x-p.x)<80 and p.energy>=40: action='special'
        elif abs(e.x-p.x)<42 and abs(e.y-p.y)<15: action='light'
    return (dx,dy),action

def play(name):
    c=Campaign(name)
    for frame in range(60*1200):
        if c.state in ('checkpoint','stage_clear'): c.advance()
        if c.state in ('victory','defeat'): return c,frame
        direction,action=decide(c)
        if action: c.player.act(action)
        c.update(1/60,direction)
    return c,frame

if __name__=='__main__':
    for name in ('REX','NOVA','BRUNO'):
        c,f=play(name)
        print(name,c.state,'kills',c.kills,'HP',c.player.health,'damage',c.damage_received,'seconds',round(c.elapsed,1))
