"""Bomb, walk, solve, open, return, save: real rules for every new branch."""
import json
import tempfile
import unittest
from pathlib import Path
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.layout43 import SECRET_BRANCHES
from puzzle_maze.entrances import entrance_visible
from puzzle_maze.puzzles import EntrancePhase,ChestPhase
from puzzle_maze.exploration import DungeonAtlas
import test_v3_campaign as witness

class Secret43Tests(unittest.TestCase):
    def test_each_branch_explodes_reveals_solves_and_returns(self):
        for index,(host,name,*_) in enumerate(SECRET_BRANCHES):
            with self.subTest(room=name):
                s=AdvancedDungeonSession();s.inventory.abilities.update(('gloves','powder','map','compass'))
                s.inventory.powder=8;s.inventory.bombs=8
                exit=next(e for e in s.rooms.rooms[host]['exits'] if e['target']==name)
                wallpos=exit['pos'];direction=exit['direction']
                dx,dy={'NORTH':(0,-1),'SOUTH':(0,1),'EAST':(1,0)}[direction]
                s.enter(host,[wallpos[0]-dx,wallpos[1]-dy]);s.player.facing=(dx,dy)
                wall=s.puzzles.objects['secret43'];atlas=DungeonAtlas(s.rooms)
                self.assertEqual(wall.phase,EntrancePhase.SEALED)
                self.assertNotIn(name,atlas.visible_rooms(s.visited));self.assertFalse(entrance_visible(s,exit))
                self.assertNotIn(('cracked',wall.pos),atlas.discovered_markers(s))
                self.assertFalse(s.puzzles.can_enter(*wall.pos));self.assertTrue(s.bombs.place())
                for _ in range(3):self.assertTrue(s.move(-dx,-dy))
                s.tick(1.6);self.assertEqual(wall.phase,EntrancePhase.REVEALING)
                self.assertFalse(s.puzzles.can_enter(*wall.pos));s.tick(.6)
                self.assertEqual(wall.phase,EntrancePhase.OPEN);self.assertTrue(entrance_visible(s,exit))
                d=witness.DungeonCampaignTests();d.s=s;d.travel(name)
                self.assertIn(name,atlas.visible_rooms(s.visited))
                if index==0:d.fight();d.use('vein')
                elif index==1:
                    d.walk((9,8));s.player.facing=(0,-1);self.assertEqual(s.powder(),'candle')
                elif index==2:d.walk((9,10));self.assertTrue(s.move(0,-1))
                else:
                    d.walk((8,7));s.player.facing=(1,0);self.assertTrue(s.attack())
                s.tick(.45);chest=s.puzzles.objects['cache'];self.assertEqual(chest.phase,ChestPhase.AVAILABLE)
                d.use('cache');sources=set(s.rewards.sources);self.assertFalse(chest.interact(s.puzzles,s.player))
                self.assertEqual(sources,s.rewards.sources);d.travel(host)
                self.assertEqual(s.puzzles.objects['secret43'].phase,EntrancePhase.OPEN)
                with tempfile.TemporaryDirectory() as folder:
                    path=Path(folder)/'save.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
                    self.assertEqual(loaded.rooms.current,host)
                    self.assertEqual(loaded.puzzles.objects['secret43'].phase,EntrancePhase.OPEN)
                    self.assertEqual(loaded.rewards.sources,sources)
                    self.assertIn(name,loaded.visited)

    def test_revealing_wall_roundtrip_and_no_blast_through_it(self):
        s=AdvancedDungeonSession();s.enter('r8');o=s.puzzles.objects['secret43']
        s.player.x,s.player.y=o.x,o.y-4
        o.blast();s.tick(.2)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r8');wall=loaded.puzzles.objects['secret43']
            self.assertEqual(wall.phase,EntrancePhase.REVEALING);loaded.tick(.4)
            self.assertEqual(wall.phase,EntrancePhase.OPEN)
        # A cracked internal wall absorbs a blast instead of propagating through it.
        o.state.active=False;o.state.remaining=0;o.x,o.y=10,8
        self.assertNotIn((11,8),s.bombs.footprint((9,8)))

    def test_v42_save_migration_preserves_open_rewards_and_adds_sealed_walls(self):
        s=AdvancedDungeonSession();s.enter('r5');s.inventory.coins=17
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';s.save(path);data=json.loads(path.read_text())
            data['content_revision']='4.2'
            for snap in [*data['snapshots'].values(),data['checkpoint']['objects']]:snap.pop('secret43',None)
            path.write_text(json.dumps(data));before=path.read_bytes();loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r5');self.assertEqual(loaded.inventory.coins,17)
            self.assertEqual(loaded.puzzles.objects['secret43'].phase,EntrancePhase.SEALED)
            self.assertEqual(path.read_bytes(),before)

    def test_v42_player_on_new_wall_moves_safely_without_losing_carried_orb(self):
        s=AdvancedDungeonSession();s.enter('r5');s.inventory.abilities.add('gloves')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';s.save(path);data=json.loads(path.read_text())
            data['content_revision']='4.2';data['player']=[24,8]
            data['extension']['orb'].update(room='r5',x=24,y=8,carried=True)
            for snap in [*data['snapshots'].values(),data['checkpoint']['objects']]:snap.pop('secret43',None)
            path.write_text(json.dumps(data));loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r5');self.assertTrue(loaded.orb.carried)
            self.assertEqual(loaded.orb.pos,(loaded.player.x,loaded.player.y))
            self.assertNotEqual(loaded.orb.pos,(24,8));self.assertIn('gloves',loaded.inventory.abilities)

    def test_v42_visible_locked_chest_does_not_become_a_free_reward(self):
        s=AdvancedDungeonSession();s.enter('r5')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';s.save(path);data=json.loads(path.read_text());data['content_revision']='4.2'
            for snap in [*data['snapshots'].values(),data['checkpoint']['objects']]:
                snap.pop('secret43',None);snap['compass'].update(chest_phase='available',spawn_time=0.)
            path.write_text(json.dumps(data));loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r5');o=loaded.puzzles.objects['compass']
            self.assertEqual(o.phase,ChestPhase.HIDDEN);self.assertFalse(o.interact(loaded.puzzles,loaded.player))
