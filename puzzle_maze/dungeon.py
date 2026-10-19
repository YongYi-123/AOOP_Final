"""The v3 campaign composes existing rooms, puzzles and combat with global relays and bombs."""
import copy
from pathlib import Path
from puzzle_maze.session import GameSession
from puzzle_maze.rooms import load_rooms,MAP_PATH
from puzzle_maze.items import BombManager

V3_SAVE=Path(__file__).parent/'save_v3.json'

class DungeonSession(GameSession):
    def __init__(self,rooms=None):
        self.pickup=None;self.trails=[];self.map_floor=None
        super().__init__(rooms or load_rooms(MAP_PATH.with_name('dungeon_v3.json')))
    def enter(self,name,arrival=None):
        super().enter(name,arrival)
        self.bombs=BombManager(self);self.combat.bombs=self.bombs
        self.map_floor=self.rooms.data.get('floor','1F');self.trails=[]
    def tick(self,dt):
        if self.player.hp<=0:return
        if self.pickup:
            kind,label,remaining=self.pickup
            self.pickup=(kind,label,remaining-dt) if remaining>dt else None
        self.trails=[(pos,time-dt) for pos,time in self.trails if time>dt]
        self.bombs.update(dt)
        super().tick(dt)
        if self.inventory.notifications:
            kind,label=self.inventory.notifications.pop(0)
            self.pickup=kind,label,2.4 if kind=='boss_key' else 1.2;self.combat.events.append('boss_key' if kind=='boss_key' else 'key')
        for o in self.puzzles.objects.values():
            if o.data['type']=='combat' and any(e.kind=='golem' for e in self.combat.enemies):
                from puzzle_maze.combat import EnemyState
                o.state.active=all(e.state==EnemyState.DEAD for e in self.combat.enemies)
                self.puzzles.update(0,self.player)
            if o.data['type']=='dash_switch':
                o.state.remaining=max(0,o.state.remaining-dt);o.state.active=o.state.remaining>0
    def move(self,dx,dy):
        target=self.player.x+dx,self.player.y+dy
        if any(o.pos==target and o.data.get("dash_only") and not (o.data.get("reversible") and o.latched) for o in self.puzzles.objects.values()):
            self.player.facing=(dx,dy);self.player.moving=False;return False
        return super().move(dx,dy)
    def dash(self):
        before=self.player.x,self.player.y
        moved=super().dash()
        if moved:
            dx,dy=self.player.facing
            for distance in range(moved+1):
                pos=before[0]+dx*distance,before[1]+dy*distance
                self.trails.append((pos,.35))
                for o in self.puzzles.objects.values():
                    if o.pos==pos and o.data['type']=='dash_switch':
                        o.state.active=True;o.state.remaining=6
                        for enemy in self.combat.enemies:
                            if enemy.kind=='golem' and enemy.hp>0:
                                enemy.dash_trigger()
                                if enemy.exposed>0:self.combat.events.append('boss_break')
            for enemy in self.combat.enemies:
                if enemy.hp>0 and enemy.kind=='armored_beetle' and abs(enemy.x-self.player.x)+abs(enemy.y-self.player.y)==1:
                    enemy.armor=False;enemy.flash=.3
        return moved
    def reset(self):
        super().reset();self.bombs=BombManager(self);self.combat.bombs=self.bombs;self.pickup=None;self.trails=[]
    def transition(self):
        exit=self.rooms.exit_at(self.player)
        if not exit:return False
        if any(a not in self.inventory.abilities for a in exit.get('abilities',[])):return False
        # Re-entering cannot silently discard a lit bomb.
        if self.bombs.bombs:return False
        return super().transition()
    def save(self,path=V3_SAVE):
        if self.player.hp<=0:return  # Preserve the last living expedition for retries.
        super().save(path)
    @classmethod
    def load(cls,path=V3_SAVE):return super().load(path)
