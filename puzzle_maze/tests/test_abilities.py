import tempfile
from pathlib import Path
import unittest
from puzzle_maze.session import GameSession
from puzzle_maze.core import Player
from test_playthrough import walk as original_walk,use as original_use

def walk(s,pos):return original_walk(s,s.rooms.legacy_position(pos))
def use(s,pos,pulse=False):return original_use(s,s.rooms.legacy_position(pos),pulse)

class AbilityTests(unittest.TestCase):
    def test_gloves_are_required_and_found_in_chest(self):
        s=GameSession();s.enter('r2');s.player=Player(*s.rooms.legacy_position((31,17)))
        self.assertFalse(s.move(1,0))
        s.enter('r1');use(s,(9,11));self.assertIn('gloves',s.inventory.abilities)
        s.enter('r2');s.player=Player(*s.rooms.legacy_position((31,17)));self.assertTrue(s.move(1,0))

    def test_dash_cooldown_and_wall_collision(self):
        s=GameSession();self.assertEqual(s.dash(),0)
        s.inventory.abilities.add('boots');s.player.facing=(-1,0)
        self.assertEqual(s.dash(),1);self.assertEqual(s.player.x,1)
        s.player.facing=(1,0);self.assertEqual(s.dash(),0)
        s.tick(1.3);self.assertEqual(s.dash(),3)

    def test_mirror_and_magnet_require_tools(self):
        s=GameSession();s.enter('r6');s.player=Player(*s.rooms.legacy_position((30,17)),(1,0))
        self.assertIsNone(s.puzzles.magnet(s.player))
        s.inventory.abilities.add('magnet')
        for _ in range(3):self.assertEqual(s.puzzles.magnet(s.player),'relay_box')
        self.assertTrue(s.puzzles.objects['relay_plate'].state.active)
        self.assertIsNone(s.puzzles.magnet(s.player)) # The end wall blocks a fourth push.
        self.assertEqual(s.puzzles.magnet(s.player,True),'relay_box')
        s.enter('r5');s.player=Player(*s.rooms.legacy_position((34,10)),(1,0))
        self.assertIsNone(s.puzzles.interact(s.player))
        s.inventory.abilities.add('mirror')
        self.assertEqual(s.puzzles.interact(s.player),'prism')

    def test_growth_save_and_reset(self):
        s=GameSession();use(s,(9,11));s.inventory.potions=2
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=GameSession.load(path)
            self.assertEqual(loaded.inventory.abilities,{'gloves'})
            self.assertEqual(loaded.inventory.potions,2)
            loaded.reset();self.assertEqual(loaded.inventory.abilities,set())

    def test_blocked_dash_does_not_grant_free_invulnerability(self):
        s=GameSession();s.inventory.abilities.add('boots');s.player.x=1;s.player.facing=(-1,0)
        self.assertEqual(s.dash(),0);self.assertEqual(s.player.invulnerable,0)

    def test_light_receiver_needs_power_and_correct_orientation(self):
        s=GameSession();s.inventory.abilities.add('mirror');s.enter('r5')
        self.assertFalse(s.puzzles.objects['receiver'].state.active)
        use(s,(6,4));use(s,(6,10))
        self.assertFalse(s.puzzles.objects['receiver'].state.active)
        use(s,(34,10));self.assertTrue(s.puzzles.objects['receiver'].state.active)

    def test_dash_and_combat_timers_survive_save(self):
        s=GameSession();s.inventory.abilities.add('boots');s.player.facing=(1,0)
        self.assertEqual(s.dash(),3);s.attack()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=GameSession.load(path)
            self.assertAlmostEqual(loaded.dash_cooldown,1.2)
            self.assertAlmostEqual(loaded.player.invulnerable,.3)
            self.assertAlmostEqual(loaded.player.attack_cooldown,.25)
