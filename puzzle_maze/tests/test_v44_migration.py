"""Old earned keys, completed runs and source saves survive additive royal content."""
import json
import tempfile
import unittest
from pathlib import Path
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.puzzles import ChestPhase

class RoyalMigrationTests(unittest.TestCase):
    def old_save(self,s,path):
        s.save(path);data=json.loads(path.read_text());data['content_revision']='4.3'
        data['extension'].pop('royal_history',None)
        data['flags']=[f for f in data['flags'] if f!='royal_resonance']
        data['checkpoint']['flags']=[f for f in data['checkpoint']['flags'] if f!='royal_resonance']
        for snapshot in [*data['snapshots'].values(),data['checkpoint']['objects']]:
            snapshot.pop('royal_socket',None);snapshot.pop('royal_signal',None)
        path.write_text(json.dumps(data))
    def test_old_earned_key_and_reward_state_are_preserved_without_rewriting_file(self):
        s=AdvancedDungeonSession();s.enter('r6');s.inventory.boss_key=True
        o=s.puzzles.objects['boss_key'];o.state.active=True;o.phase=ChestPhase.OPENED
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.json';self.old_save(s,path);before=path.read_bytes();loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r6');self.assertTrue(loaded.inventory.boss_key)
            self.assertIn('royal_resonance',loaded.inventory.flags)
            self.assertEqual(loaded.puzzles.objects['boss_key'].phase,ChestPhase.OPENED)
            self.assertFalse(loaded.puzzles.objects['boss_key'].interact(loaded.puzzles,loaded.player))
            self.assertEqual(path.read_bytes(),before)
    def test_old_completed_run_stays_complete_without_spending_royal_first_clear(self):
        s=AdvancedDungeonSession();s.enter('r18');s.finished=True;s.rewards.settle(True,True)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.json';self.old_save(s,path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r18');self.assertTrue(loaded.finished);self.assertTrue(loaded.rewards.claimed)
            self.assertFalse(loaded.history.first_claimed)
            self.assertEqual(loaded.rewards.receipt,s.rewards.receipt)
    def test_gate_animation_roundtrip_preserves_key_and_unlock_progress(self):
        s=AdvancedDungeonSession();s.inventory.flags.add('warden');s.inventory.boss_key=True;s.enter('r16')
        o=s.puzzles.objects['gate'];self.assertTrue(o.interact(s.puzzles,s.player));s.tick(.2)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'opening.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r16');gate=loaded.puzzles.objects['gate']
            self.assertAlmostEqual(gate.opening,.4);self.assertTrue(gate.unlocked)
            self.assertFalse(gate.state.active);loaded.tick(.4);self.assertTrue(gate.state.active)
            self.assertTrue(loaded.inventory.boss_key);self.assertFalse(gate.interact(loaded.puzzles,loaded.player))
