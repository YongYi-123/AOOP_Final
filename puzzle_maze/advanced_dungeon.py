"""Fourth campaign extension: shared puzzles, pots, escrow, crystals and secrets."""
from pathlib import Path
import copy
from types import SimpleNamespace
from puzzle_maze.dungeon import DungeonSession
from puzzle_maze.rooms import MAP_PATH,load_rooms
from puzzle_maze.advanced_puzzles import AdvancedPuzzleManager,LiftablePot,CrystalSwitch,OrderedSeal
from puzzle_maze.rewards import DungeonRewardBag,TREASURES
from puzzle_maze.items import Bomb
from puzzle_maze.puzzles import Chest,ChestPhase
from puzzle_maze.orb import IronOrb

V4_SAVE=Path(__file__).parent/'save_v4.json'

class AdvancedDungeonSession(DungeonSession):
    def __init__(self,rooms=None):
        self.orb=IronOrb()
        self.rewards=DungeonRewardBag();self.effects=[];self.pot_flights=[]
        super().__init__(rooms or load_rooms(MAP_PATH.with_name('dungeon_v4.json')))
    def prepare_loaded_save(self,data):
        if data.get('content_revision')!='4.2':
            from puzzle_maze.migration42 import migrate
            data=migrate(data,self.rooms.rooms,self.validate_snapshot)
            self.migration_notice='Previous progress retained in the repaired 4.2 layout.'
        return data
    def make_puzzles(self,room):
        manager=AdvancedPuzzleManager(room,self.inventory);manager.grant_treasure=self.grant_treasure;manager.has_external_load=lambda:self.orb.carried;return manager
    def enter(self,name,arrival=None):
        super().enter(name,arrival)
        if self.orb.carried:self.orb.room=name;self.orb.x,self.orb.y=self.player.x,self.player.y
        self.checkpoint['orb']=self.orb.capture()
        self.checkpoint['reward_bag']=self.rewards.capture();self.effects=[];self.pot_flights=[]
    def tick(self,dt):
        pending={o.id for o in self.puzzles.objects.values() if isinstance(o,Chest) and o.phase==ChestPhase.HIDDEN}
        super().tick(dt)
        if self.player.hp<=0:return
        self.pot_flights=[dict(flight,time=flight['time']-dt) for flight in self.pot_flights if flight['time']>dt]
        self.effects=[(kind,pos,time-dt) for kind,pos,time in self.effects if time>dt]
        for obj in self.puzzles.objects.values():
            if isinstance(obj,OrderedSeal):obj.state.active=self.combat.order_index==len(self.combat.kill_order) and bool(self.combat.kill_order)
        flag=self.rooms.data.get('on_clear_flag')
        if flag and self.combat.cleared:self.inventory.flags.add(flag)
        if self.orb.carried:self.orb.room=self.rooms.current;self.orb.x,self.orb.y=self.player.x,self.player.y
        for room in self.rooms.rooms.values():
            rule=room.get('transformation')
            if rule and set(rule['flags'])<=self.inventory.flags and rule['result'] not in self.inventory.flags:
                self.inventory.flags.add(rule['result']);self.inventory.notifications.append(('map','PILLARS BROKEN / NEW STAIRS'))
        self.puzzles.update(0,self.player)
        for name in pending:
            chest=self.puzzles.objects[name]
            if chest.phase==ChestPhase.SPAWNING:
                self.combat.events.append('solve');self.effects.append(('chest',chest.pos,.45))
    def move(self,dx,dy):
        moved=super().move(dx,dy)
        if moved:
            for enemy in self.combat.enemies:
                if enemy.kind=='mirror_mask' and enemy.hp>0:enemy.mimic(self.combat,dx,dy)
            self.puzzles.update(0,self.player)
        return moved
    def attack(self):
        p=self.player
        if p.hp<=0 or p.attack_cooldown>0:return False
        target=p.x+p.facing[0],p.y+p.facing[1]
        crystal=next((o for o in self.puzzles.objects.values() if isinstance(o,CrystalSwitch) and o.pos==target),None)
        hit=super().attack()
        if crystal:
            self.puzzles.toggle_crystal(p);self.combat.events.append('crystal');self.effects.append(('crystal',crystal.pos,.6));return True
        return hit
    def powder(self):
        if self.player.hp<=0:return None
        result=self.puzzles.ignite(self.player)
        if result:
            self.combat.events.append('order_wrong' if result=='wrong' else 'ignite')
            self.effects.append(('fire',(self.player.x,self.player.y),.5));self.tick(0)
        return result
    def interact_orb(self):return self.orb.interact(self)
    def recall_orb(self):
        if self.player.hp<=0:return False
        self.orb.recall();self.inventory.notifications.append(('magnet','IRON ORB RECALLED / POT STORAGE'));return True
    def drop_pot(self):
        id=self.inventory.carried
        if id is None:return None
        obj=self.puzzles.objects[id];p=self.player;pos=p.x+p.facing[0],p.y+p.facing[1]
        if not self.can_enter(*pos):return None
        obj.x,obj.y=pos;obj.state.active=False;self.inventory.carried=None
        self.puzzles.update(0,p);self.combat.events.append('pot_lift');return id
    def throw_pot(self):
        if self.orb.carried:return self.orb.throw(self)
        id=self.inventory.carried;p=self.player
        if id is None or p.hp<=0:return False
        pot=self.puzzles.objects[id];dx,dy=p.facing;impact=p.x,p.y
        for distance in range(1,5):
            pos=p.x+dx*distance,p.y+dy*distance
            if self.puzzles.blocked(*pos):break
            impact=pos
            enemy=next((e for e in self.combat.enemies if e.hp>0 and e.pos==pos),None)
            if enemy:
                enemy.receive_damage(self.combat,3,'pot',p);break
        self.pot_flights.append(dict(start=(p.x,p.y),end=impact,time=.3))
        self.inventory.carried=None;pot.x,pot.y=impact;pot.state.active=True
        for treasure in pot.data.get('loot',[]):self.grant_treasure(pot.id,treasure)
        if pot.data.get('explosive'):self.bombs.bombs.append(Bomb(*impact,fuse=.7))
        self.effects.append(('shards',impact,.7));self.combat.events.append('pot_break');self.tick(0);return True
    def grant_treasure(self,source,treasure):
        if treasure not in TREASURES:return False
        origin=f'{self.rooms.current}:{source}:{treasure}'
        if not self.rewards.collect(origin,treasure):return False
        name,kind,amount=TREASURES[treasure];inv=self.inventory
        if kind=='powder':inv.supply_powder(amount);inv.abilities.add('powder')
        elif kind=='bomb':inv.supply_bombs(amount)
        elif kind=='heal':self.player.hp=min(self.player.max_hp,self.player.hp+amount)
        elif kind=='fragment':
            inv.heart_fragments+=amount;self.player.max_hp=5+min(3,inv.heart_fragments//4)
            if inv.heart_fragments%4==0:self.player.hp=self.player.max_hp
        elif kind=='key':inv.add('small')
        elif kind=='boss':inv.boss_key=True
        elif kind=='ability':inv.abilities.add(treasure)
        inv.notifications.append((treasure,name));return True
    def transition(self):
        exit=self.rooms.exit_at(self.player)
        if exit and not set(exit.get('flag_requires',[])) <= self.inventory.flags:return False
        if exit and not all(self.puzzles.condition(i) for i in exit.get('requires',[])):return False
        if exit and exit.get('crystal') and exit['crystal']!=('blue' if 'crystal_blue' in self.inventory.flags else 'red'):return False
        if self.inventory.carried is not None:return False
        if exit and self.orb.carried and not exit.get('orb_allowed',True):
            self.inventory.notifications.append(('magnet','PORTAL: DROP ORB / E OR RECALL / T'));return False
        moved=super().transition()
        if moved and self.finished:self.rewards.settle(True,self.player.hp>0)
        return moved
    def reset(self):
        if self.rewards.claimed:return False
        super().reset();self.orb=IronOrb.restore(self.checkpoint.get('orb',IronOrb().capture()),self.rooms.rooms);self.rewards=DungeonRewardBag.restore(self.checkpoint['reward_bag']);self.effects=[];self.pot_flights=[]
    def save_extension(self):return dict(rewards=self.rewards.capture(),orb=self.orb.capture())
    def load_extension(self,data):
        self.orb=IronOrb.restore(data.get('orb',IronOrb().capture()),self.rooms.rooms)
        if self.orb.carried and (self.orb.room!=self.rooms.current or self.orb.pos!=(self.player.x,self.player.y)):raise ValueError('Carried orb out of sync')
        self.rewards=DungeonRewardBag.restore(data['rewards'])
        checkpoint_orb=IronOrb.restore(self.checkpoint.get('orb',IronOrb().capture()),self.rooms.rooms)
        if self.orb.carried and self.inventory.carried is not None:raise ValueError('Two carried weights')
        if checkpoint_orb.carried and (checkpoint_orb.room!=self.rooms.current or checkpoint_orb.pos!=tuple(self.checkpoint['pos']) or self.checkpoint.get('carried') is not None):raise ValueError('Invalid checkpoint orb')
        checkpoint=DungeonRewardBag.restore(self.checkpoint['reward_bag'])
        if checkpoint.run_id!=self.rewards.run_id or self.rewards.claimed!=self.finished:raise ValueError('Invalid reward lifecycle')
        id=self.inventory.carried
        if id is not None and (id not in self.puzzles.objects or not isinstance(self.puzzles.objects[id],LiftablePot) or not self.puzzles.objects[id].state.active):raise ValueError('Invalid carried pot')
        if self.checkpoint.get('carried') is not None:raise ValueError('Cannot enter with a carried pot')
    def save(self,path=V4_SAVE):super().save(path)
    @classmethod
    def load(cls,path=V4_SAVE):return super().load(path)
