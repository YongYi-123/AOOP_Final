"""Distinct boss strategies composed with the existing fighter simulation."""
from .data import BOSS_PATTERNS

class BossBrain:
    def think(self, enemy, dt, player, can_attack):
        if not enemy.ready: return
        wanted=3 if enemy.name=='NULL' and enemy.health<=enemy.max_health*.2 else 2 if enemy.health<=enemy.max_health*.5 else 1
        if wanted>enemy.phase:
            enemy.phase=wanted
            enemy.timer=enemy.invulnerable=1.1
            enemy.state='phase'
            enemy.pattern=0
            if wanted==3: enemy.defense=.8
            return
        patterns=BOSS_PATTERNS[enemy.name][min(enemy.phase-1,len(BOSS_PATTERNS[enemy.name])-1)]
        action=patterns[enemy.pattern%len(patterns)]
        dx,dy=player.x-enemy.x,player.y-enemy.y
        enemy.facing=1 if dx>0 else -1
        distance=200 if action in ('orb','laser','strike','teleport','summon') else 110 if action in ('dash','charge') else 56
        if can_attack and abs(dx)<distance and abs(dy)<14:
            enemy.pattern+=1
            if action=='guard':
                enemy.timer=.8; enemy.state='guard'
            elif action=='teleport':
                # Destination is exposed for the whole windup; no damage on arrival.
                bounds=getattr(enemy,'arena_bounds',(18,382))
                enemy.destination=(max(bounds[0]+15,min(bounds[1]-15,player.x+(100 if dx<0 else -100))),max(177,min(260,player.y+25)))
                enemy.timer=.8; enemy.state='teleport'; enemy.teleport_pending=True
            elif action=='summon':
                enemy.timer=1.2; enemy.state='summon'; enemy.summon_request=True
            else: enemy.begin(action,player)
            return
        enemy.position(dt,player,can_attack,distance)
