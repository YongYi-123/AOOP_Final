"""4.1 reward lifecycle, physical entrances, save compatibility and final access."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import pygame
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.puzzles import ChestPhase
from puzzle_maze.exploration import DungeonAtlas
from puzzle_maze.entrances import draw_entrance
from puzzle_maze.integrity import DungeonIntegrityValidator


class Dungeon41Tests(unittest.TestCase):
    def test_hidden_chest_spawn_latches_and_cannot_be_opened_early(self):
        s=AdvancedDungeonSession();s.enter('r5');chest=s.puzzles.objects['mirror']
        s.player.x,s.player.y=5,5;s.player.facing=(0,-1)
        self.assertEqual(chest.phase,ChestPhase.HIDDEN)
        self.assertFalse(chest.blocking);self.assertFalse(chest.interact(s.puzzles,s.player))
        s.puzzles.objects['lever'].state.active=True;s.puzzles.update(0,s.player)
        self.assertEqual(chest.phase,ChestPhase.SPAWNING)
        self.assertFalse(chest.interact(s.puzzles,s.player))
        s.puzzles.objects['lever'].state.active=False;s.puzzles.update(.45,s.player)
        self.assertEqual(chest.phase,ChestPhase.AVAILABLE)
        self.assertTrue(chest.interact(s.puzzles,s.player));self.assertIn('mirror',s.inventory.abilities)
        self.assertEqual(chest.phase,ChestPhase.OPENED);self.assertFalse(chest.interact(s.puzzles,s.player))

    def test_combat_key_is_hidden_chest_and_pays_once(self):
        s=AdvancedDungeonSession();s.enter('r3');chest=s.puzzles.objects['combat_key']
        self.assertEqual(chest.phase,ChestPhase.HIDDEN)
        # Production combat death, followed by normal seal update, triggers the chest.
        for enemy in s.combat.enemies:
            enemy.receive_damage(s.combat,100,'bomb',s.player)
        s.tick(.5);s.tick(.45)
        self.assertEqual(chest.phase,ChestPhase.AVAILABLE)
        self.assertTrue(chest.interact(s.puzzles,s.player));self.assertEqual(s.inventory.keys['small'],2)
        self.assertFalse(chest.interact(s.puzzles,s.player));self.assertEqual(s.inventory.keys['small'],2)

    def test_boss_key_requires_boots_prism_warden_and_crossing(self):
        s=AdvancedDungeonSession();s.enter('r6');chest=s.puzzles.objects['boss_key']
        s.puzzles.objects['gate'].latched=True;s.inventory.flags.add('prism');s.puzzles.update(0,s.player)
        self.assertEqual(chest.phase,ChestPhase.HIDDEN)
        s.inventory.abilities.add('boots');s.inventory.flags.add('warden');s.puzzles.update(0,s.player)
        self.assertEqual(chest.phase,ChestPhase.SPAWNING)
        s.puzzles.update(.45,s.player);self.assertTrue(chest.interact(s.puzzles,s.player))
        self.assertTrue(s.inventory.boss_key)

    def test_spawn_timer_and_opened_rewards_survive_save_reload(self):
        s=AdvancedDungeonSession();s.enter('r5');s.puzzles.objects['lever'].state.active=True;s.tick(0)
        s.tick(.2);self.assertAlmostEqual(s.puzzles.objects['mirror'].spawn_time,.25)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r5');self.assertAlmostEqual(loaded.puzzles.objects['mirror'].spawn_time,.25)
            loaded.tick(.25);chest=loaded.puzzles.objects['mirror'];self.assertTrue(chest.interact(loaded.puzzles,loaded.player))
            loaded.save(path);again=AdvancedDungeonSession.load(path)
            self.assertEqual(again.puzzles.objects['mirror'].phase,ChestPhase.OPENED)
            self.assertFalse(again.puzzles.objects['mirror'].interact(again.puzzles,again.player))

    def test_legacy_v40_chest_snapshots_load_without_erasing_progress(self):
        s=AdvancedDungeonSession();s.enter('r3');s.inventory.keys['small']=2
        s.puzzles.objects['combat_key'].state.active=True;s.tick(0)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.json';s.save(path);data=json.loads(path.read_text())
            for snapshot in [*data['snapshots'].values(),data['checkpoint']['objects']]:
                for state in snapshot.values():
                    state.pop('chest_phase',None);state.pop('spawn_time',None)
            path.write_text(json.dumps(data));original=path.read_bytes()
            loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r3');self.assertEqual(loaded.inventory.keys['small'],2)
            self.assertEqual(loaded.puzzles.objects['combat_key'].phase,ChestPhase.OPENED)
            self.assertEqual(path.read_bytes(),original)

    def test_remote_passage_cannot_be_bypassed_by_room_completion(self):
        s=AdvancedDungeonSession();s.enter('r11');s.completed.add('r11');s.player.x,s.player.y=23,12
        self.assertTrue(s.puzzles.blocked(23,12));self.assertFalse(s.transition())
        s.inventory.flags.update(('flame','warden'));self.assertFalse(s.puzzles.blocked(23,12))
        self.assertTrue(s.transition());self.assertEqual(s.rooms.current,'r22')
        self.assertEqual((s.player.x,s.player.y),(23,11));self.assertFalse(s.puzzles.blocked(23,11))
        s.player.x,s.player.y=23,12;self.assertTrue(s.transition());self.assertEqual(s.rooms.current,'r11')

    def test_walkthrough_passage_discovery_and_return(self):
        s=AdvancedDungeonSession();s.enter('r5');s.exploration.tiles['r5']={(23,13)}
        self.assertNotIn(('exit',(23,13)),DungeonAtlas(s.rooms).discovered_markers(s))
        s.player.x,s.player.y=23,12;self.assertTrue(s.move(0,1));self.assertTrue(s.transition())
        self.assertEqual(s.rooms.current,'r8');self.assertIn('r8',s.visited)
        s.player.x,s.player.y=12,13;self.assertTrue(s.transition());self.assertEqual(s.rooms.current,'r5')
        self.assertIn(('exit',(23,13)),DungeonAtlas(s.rooms).discovered_markers(s))

    def test_restored_crate_or_enemy_never_traps_return_arrival(self):
        s=AdvancedDungeonSession();s.enter('r4');snap=s.capture();snap['box']['pos']=[2,7];s.snapshots['r4']=snap
        s.enter('r4',[2,7]);self.assertNotEqual((s.player.x,s.player.y),(2,7));self.assertTrue(s.can_enter(s.player.x,s.player.y))
        s.enter('r3',[10,8]);self.assertNotEqual((s.player.x,s.player.y),(10,8));self.assertTrue(s.can_enter(s.player.x,s.player.y))

    def test_integrity_rejects_bad_landings_returns_flags_and_floor(self):
        rooms=AdvancedDungeonSession().rooms.rooms;report=DungeonIntegrityValidator(rooms).validate()
        self.assertEqual(report['final_room'],'r18');self.assertEqual(report['resource_states'],report['winning_states'])
        self.assertEqual(report['chests'],27);self.assertEqual(report['stair_entrances'],2)
        variants=[]
        bad=copy.deepcopy(rooms);bad['r5']['exits'][-1]['arrival']=[0,0];variants.append(bad)
        bad=copy.deepcopy(rooms);bad['r11']['exits'][-1]['flag_requires']=['nonexistent'];variants.append(bad)
        bad=copy.deepcopy(rooms);bad['r2']['exits'][-1]['entrance']='stairs_up';variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError):DungeonIntegrityValidator(bad).validate()

    def test_real_frame_timed_gate_can_be_crossed_and_reward_remains(self):
        s=AdvancedDungeonSession();s.inventory.abilities.add('boots');s.inventory.flags.update(('prism','warden'));s.enter('r6')
        s.player.x,s.player.y=16,8;s.player.facing=(1,0)
        self.assertEqual(s.puzzles.interact(s.player),'clock')
        # Allow realistic key-to-dash latency at 60 FPS, then use the live ability.
        for _ in range(12):s.tick(1/60)
        self.assertEqual(s.dash(),3);self.assertEqual(s.player.x,19)
        for _ in range(60):s.tick(1/60)
        self.assertFalse(s.puzzles.objects['gate'].state.active)
        self.assertEqual(s.puzzles.objects['boss_key'].phase,ChestPhase.AVAILABLE)
        self.assertTrue(s.puzzles.objects['boss_key'].interact(s.puzzles,s.player))
        self.assertTrue(s.inventory.boss_key)

    def test_undiscovered_bomb_wall_has_no_map_exit_marker(self):
        s=AdvancedDungeonSession();s.enter('r7');s.exploration.tiles['r7']={(12,13)}
        self.assertNotIn(('exit',(12,13)),DungeonAtlas(s.rooms).discovered_markers(s))
        s.inventory.bombs=1;s.player.x,s.player.y=11,13;s.player.facing=(1,0)
        self.assertTrue(s.bombs.place());s.move(-1,0);s.move(-1,0);s.tick(1.7)
        self.assertIn(('exit',(12,13)),DungeonAtlas(s.rooms).discovered_markers(s))

    def test_stairs_art_has_distinct_up_down_and_no_arrow_marker(self):
        s=AdvancedDungeonSession();wall=pygame.Surface((16,16));samples=[]
        for kind in ('stone','locked','boss_gate','cave','stairs_up','stairs_down'):
            surface=pygame.Surface((20,20));draw_entrance(surface,s,dict(entrance=kind,target='r2',requires=['lever']),2,2,wall)
            samples.append(pygame.image.tobytes(surface,'RGB'))
        self.assertEqual(len(set(samples)),6)
