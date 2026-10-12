import tempfile
from pathlib import Path
import unittest
from puzzle_maze.session import GameSession
from puzzle_maze.core import Player
from puzzle_maze.puzzles import PuzzleManager
from puzzle_maze.combat import CombatManager,EnemyState
from puzzle_maze.weapons import BasicSword

class SwordTests(unittest.TestCase):
    def test_start_equipped_without_tool_unlock(self):
        s=GameSession()
        self.assertIsInstance(s.player.weapon,BasicSword)
        self.assertEqual(s.inventory.abilities,set())
        self.assertEqual(s.player.weapon.name,'Basic Sword')
        s.enter('r2');self.assertIsInstance(s.player.weapon,BasicSword)

    def test_only_front_hit_single_damage_and_cooldown(self):
        room=dict(tiles=['#######']+['#.....#']*5+['#######'],objects=[],goal=[],enemies=[dict(id=n,type='slime',pos=p) for n,p in [('front',[4,3]),('side',[3,4]),('back',[2,3])]])
        player=Player(3,3,(1,0));combat=CombatManager(room,PuzzleManager(room),player)
        self.assertTrue(combat.attack())
        self.assertEqual([e.hp for e in combat.enemies],[1,2,2])
        self.assertFalse(combat.attack())
        combat.update(.1);combat.update(.1)
        self.assertEqual(combat.enemies[0].hp,1)
        self.assertIn('hit',combat.events)
        self.assertGreater(combat.enemies[0].x,4)

    def test_first_two_room_foes_die_to_starter_sword(self):
        for name in ('r1','r2'):
            s=GameSession();s.enter(name);e=s.combat.enemies[0]
            for _ in range(e.max_hp):
                s.player.x,s.player.y=e.x-1,e.y;s.player.facing=(1,0)
                self.assertTrue(s.attack());s.tick(.26)
            self.assertEqual(e.hp,0)
            s.tick(.4);self.assertEqual(e.state,EnemyState.DEAD)

    def test_legacy_v2_save_defaults_to_sword(self):
        import json
        s=GameSession()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path)
            data=json.loads(path.read_text());data.pop('weapon');path.write_text(json.dumps(data))
            loaded=GameSession.load(path)
            self.assertEqual(loaded.player.weapon.id,'basic_sword')

    def test_swing_direction_survives_save_and_room_entry(self):
        s=GameSession();s.player.facing=(1,0);s.attack();s.player.facing=(0,-1)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=GameSession.load(path)
            self.assertEqual(loaded.player.facing,(0,-1))
            self.assertEqual(loaded.player.attack_facing,(1,0))
            self.assertIsInstance(loaded.player.weapon,BasicSword)
            loaded.enter('r2');self.assertIsInstance(loaded.player.weapon,BasicSword)

    def test_walking_toward_enemy_turns_without_overlapping_and_enables_attack(self):
        s=GameSession();e=s.combat.enemies[0]
        s.player.x,s.player.y=e.x-1,e.y;s.player.facing=(0,-1)
        original=s.player.x,s.player.y
        self.assertFalse(s.move(1,0))
        self.assertEqual((s.player.x,s.player.y),original)
        self.assertEqual(s.player.facing,(1,0))
        self.assertTrue(s.attack())
        self.assertEqual(e.hp,1)
