from neon_brawl.model import Campaign

def play(name):
 c=Campaign(name)
 for frame in range(60*1200):
  if c.state in ('checkpoint','stage_clear'): c.advance()
  if c.state in ('victory','defeat'): return c,frame
  p=c.player
  targets=[e for e in c.enemies if e.alive]
  dx=dy=0
  if targets:
   e=min(targets,key=lambda e:abs(e.x-p.x)+abs(e.y-p.y)*2)
   dx=1 if e.x-p.x>27 else -1 if e.x-p.x< -27 else 0
   dy=1 if e.y-p.y>6 else -1 if e.y-p.y< -6 else 0
   if p.ready:
    p.facing=1 if e.x>p.x else -1
    danger=any(en.swing and abs(en.x-p.x)<105 and abs(en.y-p.y)<18 for en in targets)
    if danger and p.dodge_cooldown<=0: p.act('dodge')
    elif abs(e.x-p.x)<80 and p.energy>=40: p.act('special')
    elif abs(e.x-p.x)<42 and abs(e.y-p.y)<15: p.act('light')
  c.update(1/60,(dx,dy))
 return c,frame
if __name__=='__main__':
 for name in ('REX','NOVA','BRUNO'):
  c,f=play(name); print(name,c.state,c.stage,c.wave,c.kills,c.player.health,c.damage_received,round(c.elapsed,1),f)
