"""Powder fires, liftable weights and a global crystal circuit extend PuzzleManager."""
from puzzle_maze.puzzles import PuzzleManager,PuzzleObject,PressurePlate,PushableBox,FACTORY

class Brazier(PuzzleObject):pass
class TorchSequence(PuzzleObject):pass
class WeightPlate(PressurePlate):pass
class CrystalSwitch(PuzzleObject):pass
class CrystalBarrier(PuzzleObject):blocking=True
class OrderedSeal(PuzzleObject):pass

class DestructiblePillar(PuzzleObject):blocking=True
class OrderedLayoutSeal(PuzzleObject):pass

class LiftablePot(PuzzleObject):
    blocking=True
    def interact(self,manager,player,pulse=False):
        inv=manager.inventory
        if pulse or self.state.active or 'gloves' not in inv.abilities or inv.carried is not None:return False
        inv.carried=self.id;self.state.active=True;return True

class PowderSupply(PuzzleObject):
    def interact(self,manager,player,pulse=False):
        if pulse or manager.inventory.powder>=12:return False
        manager.inventory.supply_powder(12-manager.inventory.powder);return True

class PotSupply(PuzzleObject):
    def interact(self,manager,player,pulse=False):
        if pulse:return False
        for pot in manager.objects.values():
            if isinstance(pot,LiftablePot) and pot.data.get('renewable') and pot.state.active and manager.inventory.carried!=pot.id:
                pos=tuple(pot.data['pos'])
                if not manager.blocked(*pos) and pos!=(player.x,player.y) and pos not in manager.occupants:
                    pot.x,pot.y=pos;pot.state.active=False;return True
        return False

FACTORY.update(brazier=Brazier,torch_order=TorchSequence,weight=WeightPlate,crystal_switch=CrystalSwitch,crystal_barrier=CrystalBarrier,pot=LiftablePot,powder_supply=PowderSupply,pot_supply=PotSupply,ordered=OrderedSeal,pillar=DestructiblePillar,ordered_layout=OrderedLayoutSeal)

class AdvancedPuzzleManager(PuzzleManager):
    def update(self,dt,player):
        super().update(dt,player)
        for obj in self.objects.values():
            if isinstance(obj,DestructiblePillar):obj.state.active=obj.data['flag'] in self.inventory.flags
            elif isinstance(obj,OrderedLayoutSeal):obj.state.active=all(self.objects[pair['object']].pos==tuple(pair['pos']) for pair in obj.data['placements'])
            elif isinstance(obj,WeightPlate):
                weight=(1+(self.objects[self.inventory.carried].data.get('weight',2) if self.inventory.carried in self.objects else 0)) if player and obj.pos==(player.x,player.y) else 0
                weight+=sum(o.data.get('weight',3 if o.data.get('heavy') else 2)
                            for o in self.objects.values()
                            if isinstance(o,(PushableBox,LiftablePot)) and o.pos==obj.pos
                            and (not isinstance(o,LiftablePot) or not o.state.active))
                obj.state.active=weight>=obj.data.get('weight',2)
            elif isinstance(obj,CrystalSwitch):obj.state.active='crystal_blue' in self.inventory.flags
            elif isinstance(obj,CrystalBarrier):
                color='blue' if 'crystal_blue' in self.inventory.flags else 'red'
                occupied=player and obj.pos==(player.x,player.y) or obj.pos in self.occupants or any(o.pos==obj.pos and o.blocking and not o.state.active and o is not obj for o in self.objects.values())
                obj.state.active=obj.data['color']!=color or bool(occupied)
        # Re-evaluate doors after derived weights, without advancing timers twice.
        for obj in self.objects.values():
            from puzzle_maze.puzzles import Door
            if isinstance(obj,Door) and obj.data.get('requires') and any(isinstance(self.objects[i],WeightPlate) for i in obj.data['requires']):
                if obj.unlocked and all(self.condition(i) for i in obj.data['requires']):obj.state.active=True;obj.latched=True
        from puzzle_maze.puzzles import Chest
        for obj in self.objects.values():
            if isinstance(obj,Chest):obj.advance(self,0)
    def ignite(self,player):
        if 'powder' not in self.inventory.abilities or self.inventory.powder<=0:return None
        front=player.x+player.facing[0],player.y+player.facing[1]
        fires=[o for o in self.objects.values() if isinstance(o,Brazier) and not o.state.active and abs(o.x-player.x)+abs(o.y-player.y)<=1 and all(self.condition(i) for i in o.data.get('requires',[]))]
        fires.sort(key=lambda o:o.pos!=front)
        if not fires:return None
        fire=fires[0];self.inventory.powder-=1
        group=next((o for o in self.objects.values() if isinstance(o,TorchSequence) and fire.id in o.data['order']),None)
        if group:
            index=sum(self.objects[name].state.active for name in group.data['order'])
            if group.data['order'][index]!=fire.id:
                for name in group.data['order']:self.objects[name].state.active=False
                group.state.active=False;self.inventory.notifications.append(('powder','WRONG ORDER / RETRY'));return 'wrong'
            fire.state.active=True;group.state.active=all(self.objects[name].state.active for name in group.data['order'])
        else:fire.state.active=True
        self.update(0,player);return fire.id
    def toggle_crystal(self,player=None):
        if 'crystal_blue' in self.inventory.flags:self.inventory.flags.remove('crystal_blue')
        else:self.inventory.flags.add('crystal_blue')
        self.update(0,player)
