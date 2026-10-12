import unittest
from puzzle_maze.core import Player
from puzzle_maze.puzzles import PuzzleManager
from puzzle_maze.combat import CombatManager,EnemyState
from puzzle_maze.session import GameSession

ROOM=dict(tiles=['#########','#.......#','#..#....#','#.......#','#########'],objects=[],goal=[],enemies=[dict(id='foe',type='guardian',pos=[6,1])])

class CombatTests(unittest.TestCase):
    def make(self):
        p=Player(2,1);m=PuzzleManager(ROOM);return CombatManager(ROOM,m,p)

    def test_ai_follows_without_crossing_wall(self):
        c=self.make();c.player.x,c.player.y=2,3
        for _ in range(12):
            c.update(.2)
            self.assertTrue(c.puzzles.tilemap.walkable(*c.enemies[0].pos))
        self.assertLess(abs(c.enemies[0].x-2)+abs(c.enemies[0].y-3),6)

    def test_guardian_windup_and_invulnerability(self):
        c=self.make();c.player.x=5;e=c.enemies[0]
        c.update(.01);self.assertEqual(e.state,EnemyState.WINDUP)
        c.update(.3);self.assertEqual(c.player.hp,5)
        c.update(.5);self.assertEqual(c.player.hp,4)
        self.assertFalse(c.damage_player(e));self.assertEqual(c.player.hp,4)
        c.update(1.2);self.assertTrue(c.damage_player(e))

    def test_attack_death_drop_and_no_respawn(self):
        c=self.make();e=c.enemies[0];e.hp=1;c.player.x=5;c.player.facing=(1,0)
        self.assertTrue(c.attack());self.assertEqual(e.state,EnemyState.DYING)
        c.update(.4);self.assertEqual(e.state,EnemyState.DEAD)
        self.assertEqual(len(c.loot),1)
        c.player.x,c.player.y=e.pos;c.update(.1)
        self.assertEqual(c.puzzles.inventory.coins,1)
        c.update(20);self.assertEqual(e.state,EnemyState.DEAD);self.assertFalse(c.loot)

    def test_heal_and_death_disable_actions(self):
        s=GameSession();s.player.hp=2;s.inventory.potions=1
        self.assertTrue(s.heal());self.assertEqual(s.player.hp,5)
        s.player.hp=0;s.inventory.abilities.add('boots')
        self.assertFalse(s.move(1,0));self.assertEqual(s.dash(),0)
        self.assertFalse(s.attack());self.assertFalse(s.heal())

    def test_encounter_persists_across_rooms_and_reset(self):
        s=GameSession();e=s.combat.enemies[0];e.hp=0;e.state=EnemyState.DEAD;e.dropped=True
        s.encounters['r1']=s.combat.capture();s.enter('r2');s.enter('r1')
        self.assertEqual(s.combat.enemies[0].hp,0)
        s.reset();self.assertEqual(s.combat.enemies[0].hp,0)

    def test_health_and_dead_enemy_save_roundtrip(self):
        import tempfile
        from pathlib import Path
        s=GameSession();s.player.hp=3
        e=s.combat.enemies[0];e.hp=0;e.state=EnemyState.DEAD;e.dropped=True
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';s.save(path);loaded=GameSession.load(path)
            self.assertEqual(loaded.player.hp,3)
            self.assertEqual(loaded.combat.enemies[0].state,EnemyState.DEAD)
            loaded.tick(5);self.assertFalse(loaded.combat.loot)

    def test_bat_has_periodic_burst_and_all_archetypes(self):
        from puzzle_maze.combat import ENEMIES
        self.assertEqual(set(ENEMIES),{'slime','bat','guardian','blink_mage','armored_beetle','bomb_eater','golem'})
        bat=ENEMIES['bat'](dict(id='bat',type='bat',pos=[1,1]))
        burst=bat.interval();bat.age=1
        self.assertLess(burst,bat.interval())
