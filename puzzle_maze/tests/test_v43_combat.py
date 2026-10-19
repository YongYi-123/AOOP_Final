"""Real combat clocks for entry protection, telegraphs and safe weakness windows."""
import copy
import unittest
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.safety import landing_points,distance
from puzzle_maze.combat import EnemyState

class Combat43Tests(unittest.TestCase):
    def make(self):
        rooms=copy.deepcopy(AdvancedDungeonSession().rooms.rooms)
        for name,room in rooms.items():room['safe_landings']=[list(p) for p in sorted(landing_points(name,rooms))]
        return AdvancedDungeonSession(rooms)
    def test_live_entry_relocates_foes_and_reserves_all_return_landings(self):
        s=self.make()
        for name,room in s.rooms.rooms.items():
            s.enter(name)
            for e in s.combat.enemies:
                self.assertTrue(all(distance(e.pos,p)>=3 for p in room['safe_landings']))
                self.assertTrue(s.puzzles.tilemap.walkable(*e.pos))
                self.assertNotIn(e.pos,{tuple(o['pos']) for o in room['objects']})
            self.assertEqual(s.combat.entry_protection,1)
    def test_protection_allows_movement_but_attack_cancels_it(self):
        s=self.make();s.enter('r3');e=s.combat.enemies[0];hp=s.player.hp
        self.assertFalse(s.combat.damage_player(e));self.assertEqual(s.player.hp,hp)
        self.assertTrue(s.move(1,0));s.attack();self.assertEqual(s.combat.entry_protection,0)
        self.assertTrue(s.combat.damage_player(e));self.assertFalse(s.combat.damage_player(e))
        self.assertEqual(s.player.hp,hp-1)
    def test_protection_expires_and_bombs_cannot_exploit_it(self):
        s=self.make();s.enter('r3');s.tick(1.01)
        self.assertEqual(s.combat.entry_protection,0)
        s.enter('r3');s.inventory.bombs=2;self.assertTrue(s.bombs.place())
        self.assertEqual(s.combat.entry_protection,0)
    def test_golem_exposure_suppresses_attacks_and_preserves_challenge_afterwards(self):
        s=AdvancedDungeonSession();s.enter('r17');e=s.combat.enemies[0]
        s.player.x,s.player.y=e.x-1,e.y;s.player.facing=(1,0);e.dash_trigger()
        hp=s.player.hp
        self.assertTrue(s.attack());s.tick(.26);self.assertEqual(s.player.hp,hp)
        self.assertFalse(s.combat.damage_player(e,kind='contact'))
        s.tick(6);self.assertEqual(e.exposed,0)
        e.move_timer=0;s.tick(.01);self.assertEqual(e.state,EnemyState.WINDUP)
        hp=s.player.hp;s.tick(.3);self.assertEqual(s.player.hp,hp)
        s.tick(.6);self.assertLess(s.player.hp,hp)
    def test_warden_color_window_stagger_and_roundtrip(self):
        s=AdvancedDungeonSession();s.enter('r21');e=s.combat.enemies[0]
        s.inventory.flags.discard('crystal_blue')
        s.player.x,s.player.y=e.x-1,e.y;s.player.facing=(1,0)
        self.assertTrue(s.attack());self.assertGreater(e.stagger,0)
        snap=s.combat.capture();s.combat.restore(snap);self.assertEqual(e.exposed,2.6)
        s.inventory.flags.add('crystal_blue');e.stagger=0
        self.assertFalse(e.receive_damage(s.combat,1,'sword',s.player))
        s.tick(3);e.move_timer=0;s.tick(.01);self.assertEqual(e.state,EnemyState.WINDUP)
        s.tick(.8);self.assertGreater(e.exposed,2)
