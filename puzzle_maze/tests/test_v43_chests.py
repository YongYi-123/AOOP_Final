"""Hidden rewards use production collision, events, persistence and escrow."""
import tempfile
import unittest
from pathlib import Path
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.puzzles import ChestPhase
from puzzle_maze.exploration import DungeonAtlas

class HiddenChest43Tests(unittest.TestCase):
    def test_hidden_has_no_marker_collision_or_interaction(self):
        s=AdvancedDungeonSession();s.enter('r5');o=s.puzzles.objects['mirror']
        s.inventory.abilities.add('compass');s.exploration.tiles['r5']={o.pos}
        self.assertFalse(o.visible);self.assertTrue(s.puzzles.can_enter(*o.pos))
        self.assertFalse(o.interact(s.puzzles,s.player))
        self.assertNotIn(('chest',o.pos),DungeonAtlas(s.rooms).discovered_markers(s))

    def test_spawn_waits_for_player_and_moving_obstacle(self):
        s=AdvancedDungeonSession();s.enter('r5');o=s.puzzles.objects['mirror']
        s.player.x,s.player.y=o.pos;s.puzzles.objects['lever'].state.active=True;s.tick(0)
        self.assertEqual(o.phase,ChestPhase.HIDDEN)
        s.player.y+=1
        box=s.puzzles.objects['box'];old=box.pos;box.x,box.y=o.pos;s.tick(0)
        self.assertEqual(o.phase,ChestPhase.HIDDEN)
        box.x,box.y=old;s.tick(0)
        self.assertEqual(o.phase,ChestPhase.SPAWNING)
        self.assertIn('chest_spawn',s.combat.events)
        self.assertTrue(any(kind=='chest' for kind,_,_ in s.effects))
        self.assertFalse(o.interact(s.puzzles,s.player));s.tick(.45)
        self.assertEqual(o.phase,ChestPhase.AVAILABLE)

    def test_spawn_event_survives_interaction_update_and_return(self):
        s=AdvancedDungeonSession();s.enter('r5');s.puzzles.objects['lever'].state.active=True
        s.puzzles.update(0,s.player);s.tick(0)
        self.assertEqual(s.combat.events.count('chest_spawn'),1)
        s.tick(.2)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r5')
            self.assertAlmostEqual(loaded.puzzles.objects['mirror'].spawn_time,.25)
            loaded.tick(.25);loaded.snapshots['r5']=loaded.capture();loaded.enter('r2');loaded.enter('r5')
            o=loaded.puzzles.objects['mirror'];self.assertEqual(o.phase,ChestPhase.AVAILABLE)
            self.assertTrue(o.interact(loaded.puzzles,loaded.player));self.assertFalse(o.interact(loaded.puzzles,loaded.player))
            loaded.save(path);again=AdvancedDungeonSession.load(path)
            self.assertEqual(again.puzzles.objects['mirror'].phase,ChestPhase.OPENED)

    def test_trigger_latches_while_occupied_and_survives_save(self):
        s=AdvancedDungeonSession();s.enter('r5');o=s.puzzles.objects['mirror']
        s.player.x,s.player.y=o.pos;s.puzzles.objects['lever'].state.active=True;s.tick(0)
        self.assertEqual(o.phase,ChestPhase.HIDDEN);self.assertTrue(o.triggered)
        s.puzzles.objects['lever'].state.active=False
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r5')
            chest=loaded.puzzles.objects['mirror'];self.assertTrue(chest.triggered)
            self.assertEqual(chest.phase,ChestPhase.HIDDEN)
            self.assertTrue(loaded.move(0,1));loaded.tick(.45)
            self.assertEqual(chest.phase,ChestPhase.AVAILABLE)

    def test_iron_orb_delays_chest_without_losing_trigger(self):
        s=AdvancedDungeonSession();s.enter('r5');o=s.puzzles.objects['mirror']
        s.orb.room='r5';s.orb.x,s.orb.y=o.pos;s.puzzles.objects['lever'].state.active=True;s.tick(0)
        self.assertEqual(o.phase,ChestPhase.HIDDEN);self.assertTrue(o.triggered)
        s.recall_orb();s.tick(0);self.assertEqual(o.phase,ChestPhase.SPAWNING)
