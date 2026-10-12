import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.rewards import DungeonRewardBag
from puzzle_maze.combat import EnemyState

class AdvancedMechanicsTests(unittest.TestCase):
    def setUp(self):self.s=AdvancedDungeonSession()
    def face(self,x,y,dx,dy):self.s.player.x=x;self.s.player.y=y;self.s.player.facing=(dx,dy)
    def test_powder_ownership_limit_order_reset_and_refill(self):
        s=self.s;s.enter('r19');self.face(7,6,0,-1);self.assertIsNone(s.powder())
        s.inventory.abilities.add('powder');s.inventory.supply_powder(99);self.assertEqual(s.inventory.powder,30)
        self.face(10,6,0,-1);self.assertEqual(s.powder(),'wrong');self.assertFalse(s.puzzles.objects['flames'].state.active)
        for x in (7,10,13):self.face(x,6,0,-1);self.assertIsNotNone(s.powder())
        self.assertTrue(s.puzzles.objects['flames'].state.active);before=s.inventory.powder;self.assertIsNone(s.powder());self.assertEqual(s.inventory.powder,before)
        s.inventory.powder=0;self.assertTrue(s.puzzles.objects['dust'].interact(s.puzzles,s.player));self.assertEqual(s.inventory.powder,12)
    def test_lift_drop_weights_and_collision(self):
        s=self.s;s.enter('r20');self.face(5,6,1,0);self.assertIsNone(s.puzzles.interact(s.player))
        s.inventory.abilities.add('gloves');self.assertEqual(s.puzzles.interact(s.player),'jar');self.assertEqual(s.inventory.carried,'jar')
        self.face(13,8,1,0);s.puzzles.update(0,s.player);self.assertTrue(s.puzzles.objects['load'].state.active)
        self.assertEqual(s.drop_pot(),'jar');s.puzzles.update(0,s.player);self.assertFalse(s.puzzles.objects['load'].state.active)
        self.assertFalse(s.move(1,0));self.assertTrue(s.puzzles.objects['jar'].blocking)
    def test_pot_hunter_and_renewable_pots(self):
        s=self.s;s.inventory.abilities.add('gloves');s.enter('r20');self.face(5,6,1,0);s.puzzles.interact(s.player)
        self.face(12,10,1,0);enemy=s.combat.enemies[0]
        self.assertFalse(enemy.receive_damage(s.combat,1,'sword',s.player));self.assertTrue(s.throw_pot());self.assertEqual(enemy.hp,0)
        self.assertTrue(s.puzzles.objects['pot_rack'].interact(s.puzzles,s.player));self.assertFalse(s.puzzles.objects['jar'].state.active)
    def test_explosive_and_collectible_pots(self):
        s=self.s;s.inventory.abilities.add('gloves');s.enter('r20');self.face(11,4,1,0);s.puzzles.interact(s.player);self.assertTrue(s.throw_pot())
        self.assertIn('lucky_charm',s.rewards.collections)
        self.face(5,11,1,0);self.assertEqual(s.puzzles.interact(s.player),'bomb_pot');self.assertTrue(s.throw_pot());self.assertEqual(len(s.bombs.bombs),1)
    def test_global_crystal_save_and_occupied_barrier(self):
        s=self.s;s.enter('r21');barrier=s.puzzles.objects['red'];s.puzzles.toggle_crystal(s.player);self.assertTrue(barrier.state.active)
        self.face(*barrier.pos,0,1);s.puzzles.toggle_crystal(s.player);self.assertTrue(barrier.state.active)
        self.face(16,8,0,1);s.tick(0);self.assertFalse(barrier.state.active)
        s.puzzles.toggle_crystal(s.player);s.enter('r2');self.assertTrue(s.puzzles.objects['crystal'].state.active)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r2');self.assertIn('crystal_blue',loaded.inventory.flags)
    def test_ordered_enemy_wrong_order_resets_and_correct_unlocks(self):
        s=self.s;s.enter('r22');s.combat.enemies[1].receive_damage(s.combat,99,'bomb',s.player)
        self.assertEqual(s.combat.order_index,0);self.assertTrue(all(e.hp==e.max_hp for e in s.combat.enemies));self.assertFalse(s.combat.loot)
        for enemy in s.combat.enemies:enemy.receive_damage(s.combat,99,'bomb',s.player)
        s.tick(0);self.assertEqual(s.combat.order_index,3);self.assertTrue(s.puzzles.objects['sequence'].state.active)
    def test_ghost_mask_and_warden_weaknesses(self):
        s=self.s;s.enter('r19');ghost=s.combat.enemies[0]
        self.assertFalse(ghost.receive_damage(s.combat,1,'bomb',s.player));s.puzzles.objects['dawn'].state.active=True
        self.assertTrue(ghost.receive_damage(s.combat,1,'sword',s.player))
        s.enter('r22');mask=s.combat.enemies[-1];old=mask.pos;self.assertTrue(s.move(1,0));self.assertEqual(mask.pos,(old[0]-1,old[1]))
        self.assertTrue(s.puzzles.can_enter(*mask.pos));s.enter('r21');warden=s.combat.enemies[0]
        s.inventory.flags.add('crystal_blue');self.assertFalse(warden.receive_damage(s.combat,1,'sword',s.player))
        s.inventory.flags.remove('crystal_blue');self.assertTrue(warden.receive_damage(s.combat,3,'pot',s.player));s.tick(.1)
        self.assertFalse(any(e.dormant for e in s.combat.enemies));self.assertEqual(len(s.combat.enemies),3)
    def test_golem_final_phase_needs_blue_and_existing_abilities(self):
        s=self.s;s.enter('r17');golem=s.combat.enemies[0];golem.hp=4;golem.dash_trigger()
        self.assertFalse(golem.receive_damage(s.combat,2,'bomb',s.player));s.inventory.flags.add('crystal_blue')
        self.assertTrue(golem.receive_damage(s.combat,2,'bomb',s.player));self.assertTrue(golem.receive_damage(s.combat,1,'sword',s.player))
    def test_pending_rewards_settlement_once_death_and_restore(self):
        bag=DungeonRewardBag();self.assertTrue(bag.collect('cache','token_cache'));self.assertFalse(bag.collect('cache','token_cache'))
        bag.collect('tickets','ticket_bundle');bag.collect('statue','golden_cat')
        self.assertIsNone(bag.settle(False,True));self.assertIsNone(bag.settle(True,False));self.assertFalse(bag.claimed)
        first=bag.settle(True,True);second=bag.settle(True,True);self.assertEqual(first,second);self.assertEqual(first['tokens'],10)
        restored=DungeonRewardBag.restore(bag.capture());self.assertEqual(restored.settle(True,True),first)
    def test_carry_and_pending_reward_save_reset(self):
        s=self.s;s.inventory.abilities.add('gloves');s.enter('r20');self.face(5,6,1,0);s.puzzles.interact(s.player)
        s.grant_treasure('fixture','token_cache')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r20');self.assertEqual(loaded.inventory.carried,'jar');self.assertEqual(loaded.rewards.tokens,10)
            self.assertFalse(loaded.rewards.claimed);loaded.reset();self.assertIsNone(loaded.inventory.carried);self.assertEqual(loaded.rewards.tokens,0)
    def test_heart_fragments_are_unique_and_persist_capacity(self):
        s=self.s
        for i in range(4):self.assertTrue(s.grant_treasure(str(i),'heart_fragment'))
        self.assertFalse(s.grant_treasure('0','heart_fragment'));self.assertEqual(s.player.max_hp,6);self.assertEqual(s.player.hp,6)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=AdvancedDungeonSession.load(path);self.assertEqual(loaded.player.max_hp,6);self.assertEqual(loaded.player.hp,6)

    def test_pot_hunter_changes_hunt_and_windup_for_carried_pots(self):
        s=self.s;s.enter('r20');hunter=s.combat.enemies[0];hunter.special_update(s.combat,.01)
        normal=hunter.speed,hunter.windup;s.inventory.carried='jar';hunter.special_update(s.combat,.01)
        self.assertLess(hunter.speed,normal[0]);self.assertLess(hunter.windup,normal[1])
