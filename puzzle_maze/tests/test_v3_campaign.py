"""Action witnesses use legal collision-aware moves, real item interactions and transitions."""
from collections import deque
from pathlib import Path
import tempfile
import unittest
from puzzle_maze.dungeon import DungeonSession
from puzzle_maze.validator import DungeonValidator
from puzzle_maze.combat import EnemyState

class DungeonCampaignTests(unittest.TestCase):
    def setUp(self):self.s=DungeonSession()
    def path(self,target):
        s=self.s;start=s.player.x,s.player.y;queue=deque([start]);parents={start:None}
        while queue:
            pos=queue.popleft()
            if pos==target:
                result=[]
                while parents[pos] is not None:
                    old=parents[pos];result.append((pos[0]-old[0],pos[1]-old[1]));pos=old
                return result[::-1]
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt=pos[0]+dx,pos[1]+dy
                if nxt not in parents and s.can_enter(*nxt) and not any(o.pos==nxt and o.data.get("dash_only") for o in s.puzzles.objects.values()):parents[nxt]=pos;queue.append(nxt)
        return None
    def walk(self,pos):
        path=self.path(tuple(pos));self.assertIsNotNone(path,f'{self.s.rooms.current}: unreachable {pos}')
        for direction in path:self.assertTrue(self.s.move(*direction))
    def use(self,name):
        s=self.s;o=s.puzzles.objects[name]
        if o.pos!=(s.player.x,s.player.y):
            candidates=[(o.x+dx,o.y+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))]
            reachable=[(len(path),pos) for pos in candidates if (path:=self.path(pos)) is not None]
            self.assertTrue(reachable,f'{s.rooms.current} cannot interact with {name}');self.walk(min(reachable)[1])
        if getattr(o,'spawn_time',0):s.tick(o.spawn_time)
        s.player.facing=o.x-s.player.x,o.y-s.player.y
        if s.player.facing==(0,0):s.player.facing=(1,0)
        result=s.puzzles.interact(s.player);self.assertEqual(result,name);s.tick(0)
    def travel(self,target):
        s=self.s;e=next(e for e in s.rooms.data['exits'] if e['target']==target and not e.get('finish') and self.path(tuple(e['pos'])) is not None)
        self.walk(e['pos']);self.assertTrue(s.transition(),f'{s.rooms.current} -> {target} blocked')
    def fight(self):
        s=self.s
        for enemy in s.combat.enemies:
            for _ in range(20):
                if enemy.hp==0:break
                if enemy.kind=='bomb_eater':
                    self.walk((enemy.x-2,enemy.y));s.player.facing=(1,0)
                    self.assertTrue(s.bombs.place());self.walk((enemy.x-4,enemy.y));s.tick(.8);s.tick(.4);continue
                spots=[(enemy.x+dx,enemy.y+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))]
                if enemy.kind=='armored_beetle' and enemy.armor:
                    spots=[pos for pos in spots if (pos[0]-enemy.x)*enemy.facing[0]+(pos[1]-enemy.y)*enemy.facing[1]<0]
                options=[(len(path),pos) for pos in spots if (path:=self.path(pos)) is not None]
                self.assertTrue(options);self.walk(min(options)[1]);s.player.facing=enemy.x-s.player.x,enemy.y-s.player.y
                s.attack();s.tick(.26)
            self.assertEqual(enemy.hp,0,f'Could not defeat {enemy.kind}')
            s.tick(.4)
            if s.combat.loot:self.walk(s.combat.loot[0]['pos']);s.tick(0)
        self.assertGreater(s.player.hp,0)
    def weight(self):
        self.walk((6,10));self.assertTrue(self.s.move(0,-1));self.assertTrue(self.s.puzzles.objects['plate'].state.active)
    def optics(self):
        self.walk((6,8));self.s.player.facing=(1,0)
        self.assertEqual(self.s.puzzles.magnet(self.s.player),'box');self.assertEqual(self.s.puzzles.magnet(self.s.player),'box')
        self.use('prism');self.assertTrue(self.s.puzzles.objects['eye'].state.active)
    def timer(self):
        self.walk((16,8));self.use('clock');self.s.player.facing=(1,0);self.assertEqual(self.s.dash(),3)
    def test_resource_search_every_order_can_finish(self):
        report=DungeonValidator(self.s.rooms.rooms).validate()
        self.assertEqual(report['resource_states'],report['winning_states']);self.assertEqual(report['keys'],6)
    def test_campaign_branch_backtracking_ability_witness(self):
        s=self.s
        self.use('map');self.use('lever');self.travel('r2')
        self.travel('r5');self.use('lever');self.use('mirror')
        self.weight()
        self.use('east');self.use('compass');self.travel('r2')
        self.travel('r4');self.use('gloves');self.weight();self.use('prism');self.use('west');self.travel('r2')
        self.travel('r3');self.fight();self.walk(s.puzzles.objects['combat_key'].pos);self.use('gate');self.travel('r7')
        self.use('powder');self.use('lever');self.use('supply') if s.inventory.bombs<8 else None
        # Optional secret: a real bomb opens the authored cracked exit.
        self.walk((11,13));s.player.facing=(1,0);self.assertTrue(s.bombs.place());self.walk((8,13));s.tick(1.7)
        self.assertTrue(s.puzzles.objects['crack'].state.active);self.travel('r8');self.use('reward');self.travel('r7')
        self.travel('r9');self.fight();self.weight();self.use('boots');self.travel('r7');self.travel('r3');self.travel('r2')
        self.use('lower');self.travel('r10');self.use('lever');self.travel('r11');self.fight();self.use('lever');self.use('magnet');self.travel('r12')
        self.optics();self.use('prism_signal');self.use('key');self.travel('r11');self.travel('r10');self.travel('r2');self.travel('r6')
        self.timer();self.use('boss_key');self.assertTrue(s.inventory.boss_key);self.travel('r2');self.travel('r10');self.travel('r13')
        self.use('supply') if s.inventory.bombs<8 else None;self.fight();self.use('portal_key');self.travel('r14');self.optics();self.timer();self.use('reward');self.travel('r15')
        self.fight();self.use('gate');self.travel('r16');self.use('gate');self.use('rest');self.use('supply') if s.inventory.bombs<8 else None;self.travel('r17')
        self.assertEqual(s.rooms.data['floor'],'B1F');self.assertEqual(s.inventory.keys['small'],1)
        self.assertTrue({'gloves','mirror','boots','magnet','map','compass'}<=s.inventory.abilities)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'save.json';s.save(path);loaded=DungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r17');self.assertEqual(loaded.inventory.flags,s.inventory.flags);self.assertEqual(loaded.inventory.bombs,s.inventory.bombs)
        boss=s.combat.enemies[0]
        def strike_core():
            for _ in range(4):
                self.walk((boss.x-1,boss.y));s.player.facing=(1,0);self.assertTrue(s.attack());s.tick(.26)
        def dash_anchor():
            self.walk((5,8));s.player.facing=(1,0);self.assertEqual(s.dash(),3)
        def bomb_armor():
            self.walk((boss.x-1,boss.y));s.player.facing=(1,0);self.assertTrue(s.bombs.place())
            self.walk((8,11));s.tick(1.7)
        dash_anchor();strike_core();self.assertEqual(boss.phase,2)
        bomb_armor();strike_core();self.assertEqual(boss.phase,3)
        dash_anchor();bomb_armor();strike_core();self.assertEqual(boss.hp,0)
        self.assertFalse(s.puzzles.objects['gate'].state.active)
        s.tick(1.3);self.assertTrue(s.puzzles.objects['gate'].state.active)
        self.travel('r18');self.use('treasure');self.use('dawn');self.walk((23,8));self.assertTrue(s.transition());self.assertTrue(s.finished);self.assertEqual(s.visited,set(s.rooms.rooms))

    def test_floor_and_active_bomb_save_reset(self):
        s=self.s;s.inventory.bombs=5;s.inventory.abilities.update(('boots','map','compass'));s.enter('r13');s.player.facing=(1,0)
        self.assertTrue(s.bombs.place())
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'save.json';s.save(path);loaded=DungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r13');self.assertEqual(len(loaded.bombs.bombs),1);self.assertEqual(loaded.inventory.bombs,4)
            loaded.reset();self.assertEqual(loaded.inventory.bombs,5);self.assertFalse(loaded.bombs.bombs)
            original=path.read_bytes();loaded.player.hp=0;loaded.save(path);self.assertEqual(path.read_bytes(),original)
    def test_timed_gate_requires_boots_and_renewable_reset(self):
        s=self.s;s.enter('r6');self.walk((16,8));self.use('clock');self.assertEqual(s.dash(),0);s.tick(.4)
        self.assertFalse(s.puzzles.objects['gate'].state.active);s.inventory.abilities.add('boots');self.timer()
        self.assertTrue(s.puzzles.objects['gate'].latched);s.tick(1);self.assertFalse(s.puzzles.blocked(s.player.x,s.player.y));s.reset()
        self.assertEqual((s.player.x,s.player.y),(2,7))

    def test_boss_exposure_and_phase_save_load(self):
        s=self.s;s.inventory.abilities.add('boots');s.inventory.bombs=8;s.enter('r17')
        self.walk((5,8));s.player.facing=(1,0);self.assertEqual(s.dash(),3)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'boss.json';s.save(path);loaded=DungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r17');self.assertGreater(loaded.combat.enemies[0].exposed,0)
            self.assertEqual(loaded.puzzles.objects['anchor'].state.remaining,6)
            self.assertEqual(loaded.dash_cooldown,1.2)
            loaded.reset();self.assertEqual(loaded.combat.enemies[0].exposed,0)
    def test_magnetic_only_weights_cannot_be_manually_bypassed(self):
        s=self.s;s.inventory.abilities.add('gloves');s.enter('r12')
        box=s.puzzles.objects['box'];box.x,box.y=6,8
        self.walk((5,8));self.assertFalse(s.move(1,0));self.assertEqual(box.pos,(6,8))
        s.inventory.abilities.add('magnet');s.player.facing=(1,0)
        self.assertEqual(s.puzzles.magnet(s.player),'box');self.assertEqual(box.pos,(7,8))
    def test_combat_key_is_inert_before_clear_then_picked_once(self):
        s=self.s;s.enter('r3');self.walk((8,4));self.assertEqual(s.inventory.keys.get('small',0),0)
        self.fight();self.walk((8,4));self.assertEqual(s.inventory.keys['small'],2)
        self.walk((8,5));self.walk((8,4));self.assertEqual(s.inventory.keys['small'],2)
