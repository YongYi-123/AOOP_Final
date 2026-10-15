import unittest
from types import SimpleNamespace
from puzzle_maze.session import GameSession
from puzzle_maze.items import BombManager
from puzzle_maze.combat import EnemyState


def arena(objects=None,enemies=None):
    return dict(tiles=['#'*23]+['#'+'.'*21+'#' for _ in range(15)]+['#'*23],spawn=[2,7],objects=objects or [],enemies=enemies or [],goal=[],exits=[])

def setup(enemies=None,objects=None):
    s=GameSession({'r1':arena(objects,enemies)});s.bombs=BombManager(s);s.combat.bombs=s.bombs
    return s

class DungeonSystemsTests(unittest.TestCase):
    def test_bomb_consumption_repeat_and_cap(self):
        s=setup();s.inventory.supply_bombs(99);self.assertEqual(s.inventory.bombs,20)
        self.assertTrue(s.bombs.place());self.assertFalse(s.bombs.place());self.assertEqual(s.inventory.bombs,19)
        s.bombs.update(1.6);self.assertEqual(s.player.hp,4);self.assertFalse(s.bombs.bombs)

    def test_blast_wall_occlusion_and_crack(self):
        s=setup(objects=[dict(id='crack',type='cracked',pos=[4,7])]);s.player.x=2;s.inventory.bombs=3;s.player.facing=(1,0)
        s.puzzles.tilemap.rows[6]='#'+'#'*21+'#';s.puzzles.tilemap.rows[8]='#'+'#'*21+'#'
        self.assertNotIn((5,7),s.bombs.footprint((3,7)))
        s.bombs.place();s.bombs.update(2);self.assertTrue(s.puzzles.objects['crack'].state.active)
        self.assertIn((5,7),s.bombs.footprint((3,7)))

    def test_multikey_cost_is_atomic_and_boss_key_persists(self):
        s=setup(objects=[dict(id='lock',type='door',pos=[3,7],key='small',cost=2),dict(id='boss',type='door',pos=[4,7],key='boss')])
        s.inventory.keys['small']=1;lock=s.puzzles.objects['lock']
        self.assertFalse(lock.interact(s.puzzles,s.player));self.assertEqual(s.inventory.keys['small'],1)
        s.inventory.keys['small']=2;self.assertTrue(lock.interact(s.puzzles,s.player));self.assertFalse(lock.interact(s.puzzles,s.player));self.assertEqual(s.inventory.keys['small'],0)
        s.inventory.boss_key=True;self.assertTrue(s.puzzles.objects['boss'].interact(s.puzzles,s.player));self.assertTrue(s.inventory.boss_key)

    def test_supplies_cannot_exhaust_mandatory_bomb_puzzles(self):
        s=setup(objects=[dict(id='supply',type='supply',pos=[3,7])]);s.inventory.bombs=0
        for _ in range(4):
            self.assertTrue(s.puzzles.objects['supply'].interact(s.puzzles,s.player));self.assertEqual(s.inventory.bombs,8);s.inventory.bombs=0

    def test_armored_front_back_and_bomb(self):
        s=setup([dict(id='beetle',type='armored_beetle',pos=[10,7])]);e=s.combat.enemies[0]
        self.assertFalse(e.receive_damage(s.combat,1,'sword',SimpleNamespace(x=10,y=8)))
        self.assertTrue(e.receive_damage(s.combat,1,'sword',SimpleNamespace(x=10,y=6)))
        self.assertTrue(e.receive_damage(s.combat,2,'bomb',SimpleNamespace(x=10,y=8)));self.assertEqual(e.hp,0)

    def test_bomb_eater_swallow_special_damage(self):
        s=setup([dict(id='eater',type='bomb_eater',pos=[4,7])]);s.inventory.bombs=2;s.player.facing=(1,0)
        self.assertFalse(s.combat.enemies[0].receive_damage(s.combat,1,'sword',s.player))
        s.bombs.place();s.bombs.update(.1);self.assertEqual(s.bombs.bombs[0].swallowed,'eater')
        s.bombs.update(.7);self.assertEqual(s.combat.enemies[0].hp,0)

    def test_blink_and_projectiles_obey_walls(self):
        s=setup([dict(id='mage',type='blink_mage',pos=[5,7])]);e=s.combat.enemies[0];e.move_timer=0
        s.combat.update(.01);self.assertTrue(s.puzzles.tilemap.walkable(*e.pos));self.assertNotEqual(e.pos,(s.player.x,s.player.y))
        e.x,e.y=5,7;s.player.x,s.player.y=10,7;s.puzzles.tilemap.rows[7]=s.puzzles.tilemap.rows[7][:7]+'#'+s.puzzles.tilemap.rows[7][8:]
        s.combat.fire(e);s.combat.update(.6);self.assertEqual(s.player.hp,5);self.assertFalse(s.combat.projectiles)

    def test_all_boss_phases_require_abilities(self):
        s=setup([dict(id='golem',type='golem',pos=[10,7])]);e=s.combat.enemies[0]
        self.assertFalse(e.receive_damage(s.combat,1,'sword',s.player));e.dash_trigger()
        for _ in range(4):self.assertTrue(e.receive_damage(s.combat,1,'sword',s.player))
        self.assertEqual(e.phase,2);self.assertFalse(e.receive_damage(s.combat,1,'sword',s.player))
        e.receive_damage(s.combat,2,'bomb',s.player)
        for _ in range(4):e.receive_damage(s.combat,1,'sword',s.player)
        self.assertEqual(e.phase,3);self.assertFalse(e.receive_damage(s.combat,2,'bomb',s.player))
        e.dash_trigger();e.receive_damage(s.combat,2,'bomb',s.player)
        for _ in range(4):e.receive_damage(s.combat,1,'sword',s.player)
        self.assertEqual(e.hp,0);self.assertEqual(e.state,EnemyState.DYING)
        s.combat.update(1.3);self.assertEqual(e.state,EnemyState.DEAD)
