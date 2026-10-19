"""Original multi-floor Orb circuit and item-gated cartography."""
import tempfile
import unittest
from pathlib import Path
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.exploration import DungeonAtlas
from puzzle_maze.puzzles import ChestPhase

class RoyalCircuitTests(unittest.TestCase):
    def test_socket_needs_lowered_floor_and_real_dropped_orb_then_syncs_upper_chest(self):
        s=AdvancedDungeonSession();s.inventory.abilities.update(('gloves','boots'));s.enter('r22')
        s.orb.room='r22';s.orb.x,s.orb.y=9,12;s.tick(0)
        self.assertNotIn('royal_resonance',s.inventory.flags)
        s.inventory.flags.update(('pillar_storage','pillar_foundry'));s.tick(0)
        self.assertIn('floor_lowered',s.inventory.flags);s.tick(0)
        self.assertIn('royal_resonance',s.inventory.flags)
        self.assertTrue(s.puzzles.objects['royal_socket'].state.active)
        self.assertTrue(s.recall_orb());s.enter('r6');s.inventory.flags.update(('prism','warden'))
        s.puzzles.objects['gate'].latched=True;s.tick(0)
        self.assertEqual(s.puzzles.objects['boss_key'].phase,ChestPhase.SPAWNING)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'circuit.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r6');self.assertIn('royal_resonance',loaded.inventory.flags)
            self.assertEqual(loaded.orb.room,'r20');loaded.tick(.45)
            self.assertTrue(loaded.puzzles.objects['boss_key'].interact(loaded.puzzles,loaded.player))
    def test_key_remains_hidden_until_lower_circuit_and_map_respects_items(self):
        s=AdvancedDungeonSession();s.visited.update(('r2','r4'));atlas=DungeonAtlas(s.rooms)
        self.assertEqual(set(atlas.displayed_layout(s)),{'r1'})
        o=s.puzzles.objects['map'];self.assertTrue(o.interact(s.puzzles,s.player))
        self.assertIn('r2',atlas.displayed_layout(s));self.assertNotIn('r8',atlas.displayed_layout(s))
        s.enter('r5');s.puzzles.objects['lever'].state.active=True;s.puzzles.objects['gate'].latched=True;s.tick(0);s.tick(.45)
        self.assertTrue(s.puzzles.objects['compass'].interact(s.puzzles,s.player));self.assertIn('compass',s.inventory.abilities)
        s.enter('r6');s.inventory.abilities.add('boots');s.inventory.flags.update(('prism','warden'));s.puzzles.objects['gate'].latched=True;s.tick(0)
        self.assertEqual(s.puzzles.objects['boss_key'].phase,ChestPhase.HIDDEN)
