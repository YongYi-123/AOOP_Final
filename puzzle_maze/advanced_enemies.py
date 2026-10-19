"""Original mirror, pot and fire weaknesses; Warden reuses the encounter lifecycle."""
from puzzle_maze.combat import Enemy,Guardian,EnemyState,ENEMIES
from puzzle_maze.enemies import ArmoredBeetle

class MirrorMask(ArmoredBeetle):
    max_hp=2
    def mimic(self,manager,dx,dy):
        if self.state!=EnemyState.HUNT:return
        target=self.x-dx,self.y-dy
        if not manager.blocked(target,self) and target!=(manager.player.x,manager.player.y):
            self.x,self.y=target;self.facing=(-dx,-dy)
    def special_update(self,manager,dt):
        p=manager.player;distance=abs(self.x-p.x)+abs(self.y-p.y)
        if self.state==EnemyState.WINDUP:
            self.attack_timer=max(0,self.attack_timer-dt)
            if self.attack_timer==0:
                if distance<=1:manager.damage_player(self)
                self.state=EnemyState.HUNT
        elif distance<=1:self.state=EnemyState.WINDUP;self.attack_timer=.5
        return True

class PotHunter(Guardian):
    max_hp=4
    speed=.5
    def special_update(self,manager,dt):
        carrying=manager.puzzles.inventory.carried is not None
        self.speed=.32 if carrying else .55;self.windup=.55 if carrying else .8
        return False
    def receive_damage(self,manager,amount,kind,source):
        if kind=='sword':manager.events.append('shield');return False
        return super().receive_damage(manager,6 if kind=='pot' else amount,kind,source)

class CrystalGhost(Enemy):
    max_hp=2
    speed=.5
    def visible(self,manager):
        torch=manager.puzzles.objects.get(self.data.get('torch'))
        return torch is not None and torch.state.active
    def receive_damage(self,manager,amount,kind,source):
        if not self.visible(manager):manager.events.append('shield');return False
        return super().receive_damage(manager,amount,kind,source)
    def special_update(self,manager,dt):return not self.visible(manager)

class EliteGuardian(Guardian):
    max_hp=4
    speed=.55
    def special_update(self,manager,dt):
        p=manager.player;distance=abs(self.x-p.x)+abs(self.y-p.y)
        self.move_timer=max(0,self.move_timer-dt)
        if self.state==EnemyState.WINDUP:
            self.attack_timer=max(0,self.attack_timer-dt)
            if not self.attack_timer:
                if distance<=2:manager.damage_player(self)
                if distance>1:manager.fire(self)
                self.state=EnemyState.HUNT;self.move_timer=1.2
            return True
        if self.move_timer<=0 and distance<=8:
            if distance>3:
                pos=manager.next_step(self)
                if pos and pos!=(p.x,p.y):self.x,self.y=pos
            self.state=EnemyState.WINDUP;self.attack_timer=.75
        return True

class CrystalWarden(EliteGuardian):
    max_hp=6
    def __init__(self,data):
        super().__init__(data);self.exposed=2.6
    def special_update(self,manager,dt):
        self.exposed=max(0,self.exposed-dt)
        if self.exposed>0:return True
        before=self.state
        result=super().special_update(manager,dt)
        if before==EnemyState.WINDUP and self.state==EnemyState.HUNT:
            self.exposed=2.6;manager.events.append('boss_break')
        return result
    def capture(self):return dict(super().capture(),exposed=self.exposed)
    def receive_damage(self,manager,amount,kind,source):
        color='blue' if 'crystal_blue' in manager.puzzles.inventory.flags else 'red'
        if color!=self.data.get('weak_color','red') or self.exposed<=0:
            manager.events.append('shield');self.flash=.15;return False
        return Enemy.receive_damage(self,manager,amount,kind,source)

ENEMIES.update(mirror_mask=MirrorMask,pot_hunter=PotHunter,crystal_ghost=CrystalGhost,elite_guardian=EliteGuardian,crystal_warden=CrystalWarden)
