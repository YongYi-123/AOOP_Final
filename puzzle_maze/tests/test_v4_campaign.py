"""Executable fourth-campaign route: branches, five secrets, Warden and final settlement."""
from pathlib import Path
from collections import deque
import tempfile
import unittest
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.validator import DungeonValidator
from puzzle_maze.combat import EnemyState
import test_v3_campaign as legacy_witness

class EmberglassCampaignTests(unittest.TestCase):
    def setUp(self):
        self.s=AdvancedDungeonSession();self.driver=legacy_witness.DungeonCampaignTests();self.driver.s=self.s
    def walk(self,pos):self.driver.walk(pos)
    def use(self,id):self.driver.use(id)
    def travel(self,id):self.driver.travel(id)
    def strike_crystal(self):
        s=self.s;obj=s.puzzles.objects['crystal']
        self.walk((obj.x-1,obj.y));s.player.facing=(1,0);s.tick(.3);self.assertTrue(s.attack());s.tick(.3)
    def fire(self,id):
        s=self.s;o=s.puzzles.objects[id];self.walk((o.x,o.y+1));s.player.facing=(0,-1);self.assertEqual(s.powder(),id)
    def test_twenty_two_rooms_and_all_key_orders(self):
        s=self.s;report=DungeonValidator(s.rooms.rooms).validate()
        self.assertEqual(report['rooms'],22);self.assertEqual(report['resource_states'],report['winning_states'])
        self.assertGreater(len(s.rooms.rooms['r2']['exits']),5)
        self.assertTrue(any(e['target']=='r7' for e in s.rooms.rooms['r20']['exits']))
    def test_complete_non_linear_secret_and_settlement_witness(self):
        s=self.s;d=self.driver
        self.use('map');self.use('lever');self.travel('r2')
        # First take the left ability branch, then the shrine, then the alternate bomb route.
        self.travel('r4');self.use('gloves');self.travel('r2');self.travel('r19');self.use('powder')
        for id in ('dawn','noon','dusk'):self.fire(id)
        d.fight();self.use('flame_signal');self.fire('hidden_fire');self.use('disc');self.travel('r2')
        self.strike_crystal();self.travel('r5');self.use('lever');self.use('mirror');d.weight();self.use('east');self.use('compass');self.travel('r2')
        self.travel('r4');d.weight();self.use('prism');self.use('west');self.travel('r20')
        self.use('charm_pot');self.assertTrue(s.throw_pot());self.assertIn('lucky_charm',s.rewards.collections)
        self.use('jar');hunter=s.combat.enemies[0]
        self.walk((hunter.x-2,hunter.y));s.player.facing=(1,0);self.assertTrue(s.throw_pot());self.assertEqual(hunter.hp,0);s.tick(.4)
        self.use('jar2');self.walk((13,8));self.assertTrue(s.puzzles.objects['load'].state.active);self.assertTrue(s.puzzles.objects['gate'].state.active)
        s.player.facing=(1,0);self.assertTrue(s.drop_pot());self.use('cache');self.travel('r7')
        self.use('powder');self.use('lever');self.travel('r9');d.fight();d.weight();self.use('boots');self.travel('r3')
        d.fight();self.use('combat_key');self.use('fragment');self.use('gate');self.travel('r7')
        self.walk((11,13));s.player.facing=(1,0);self.assertTrue(s.bombs.place());self.walk((8,13));s.tick(1.7)
        self.travel('r8');self.use('reward');self.travel('r7');self.travel('r3');self.travel('r2')
        self.use('lower');self.travel('r10');self.use('rest');self.use('lever');self.travel('r21')
        self.strike_crystal();self.assertNotIn('crystal_blue',s.inventory.flags);d.fight();self.assertIn('warden',s.inventory.flags)
        self.strike_crystal();self.use('warden_cache')
        self.walk((11,13));s.player.facing=(1,0);self.assertTrue(s.bombs.place());self.walk((8,13));s.tick(1.7);self.travel('r22')
        # Ordered mask can be defeated with a correctly aimed bomb while the player holds still.
        for e in s.combat.enemies[:2]:
            while e.hp:
                candidates=[(e.x-1,e.y),(e.x+1,e.y),(e.x,e.y-1),(e.x,e.y+1)]
                pos=next(p for p in candidates if d.path(p) is not None);self.walk(pos)
                s.player.facing=e.x-s.player.x,e.y-s.player.y;s.attack();s.tick(.26)
            s.tick(.4)
        mask=s.combat.enemies[-1]
        initial=((s.player.x,s.player.y),mask.pos);queue=deque([initial]);parents={initial:None};solution=None
        while queue:
            player,foe=state=queue.popleft()
            if abs(player[0]-foe[0])+abs(player[1]-foe[1])<=2:
                solution=[]
                while parents[state] is not None:
                    previous,delta=parents[state];solution.append(delta);state=previous
                solution.reverse();break
            for delta in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt=player[0]+delta[0],player[1]+delta[1]
                if not s.puzzles.can_enter(*nxt) or nxt==foe:continue
                mirrored=foe[0]-delta[0],foe[1]-delta[1]
                if not s.puzzles.can_enter(*mirrored) or mirrored==nxt:mirrored=foe
                new=nxt,mirrored
                if new not in parents:parents[new]=((player,foe),delta);queue.append(new)
        self.assertIsNotNone(solution)
        for delta in solution:
            if abs(mask.x-s.player.x)+abs(mask.y-s.player.y)<=2:break
            self.assertTrue(s.move(*delta))
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            pos=s.player.x+dx,s.player.y+dy
            if s.puzzles.blocked(*pos):pos=s.player.x,s.player.y
            if mask.pos in s.bombs.footprint(pos):s.player.facing=(dx,dy);break
        self.assertTrue(s.bombs.place());s.tick(1.7);s.tick(.4);self.assertEqual(mask.hp,0);self.assertTrue(s.puzzles.objects['sequence'].state.active)
        self.use('skin');self.use('stamp');self.use('fragment');self.use('cache');self.travel('r21');self.travel('r10')
        self.travel('r11');d.fight();self.use('lever');self.use('magnet');self.travel('r12');d.optics();self.use('prism_signal');self.use('key');self.travel('r11');self.travel('r10');self.travel('r2');self.travel('r6')
        d.timer();self.use('boss_key');self.travel('r2');self.travel('r10');self.travel('r13')
        if s.inventory.bombs<8:self.use('supply')
        d.fight();self.use('portal_key');self.travel('r14');d.optics();d.timer();self.use('reward');self.travel('r15')
        d.fight();self.use('gate');self.travel('r16');self.use('gate');self.use('rest');self.travel('r17')
        self.assertIn('crystal_blue',s.inventory.flags);boss=s.combat.enemies[0]
        def strike():
            for _ in range(4):self.walk((boss.x-1,boss.y));s.player.facing=(1,0);self.assertTrue(s.attack());s.tick(.26)
        def dash():self.walk((5,8));s.player.facing=(1,0);self.assertEqual(s.dash(),3)
        def bomb():
            self.walk((boss.x-1,boss.y));s.player.facing=(1,0);self.assertTrue(s.bombs.place());self.walk((8,11));s.tick(1.7)
        dash();strike();bomb();strike();dash();bomb();strike();s.tick(1.3);self.assertEqual(boss.state,EnemyState.DEAD)
        self.travel('r18');self.use('treasure');self.use('dawn');self.walk((23,8));self.assertTrue(s.transition())
        self.assertTrue(s.finished);self.assertTrue(s.rewards.claimed);self.assertEqual(len(s.rewards.collections),5);self.assertEqual(s.visited,set(s.rooms.rooms))
        receipt=s.rewards.settle(True,True);self.assertGreater(receipt['tokens'],0);self.assertGreater(receipt['tickets'],0)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertTrue(loaded.finished);self.assertEqual(loaded.rewards.settle(True,True),receipt)
