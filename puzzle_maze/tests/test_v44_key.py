"""One original royal key silhouette, real acquisition and persistent gate opening."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
import unittest
from pathlib import Path
import pygame
from puzzle_maze.icons import IconAtlas,BossKeyIcon
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.puzzles import ChestPhase
from puzzle_maze.game import Game,GameScene

class RoyalKeyTests(unittest.TestCase):
    def tearDown(self):pygame.quit()
    def test_key_is_larger_gemmed_and_distinct_from_silver_small_key(self):
        atlas=IconAtlas();small=atlas.get('small_key');boss=atlas.get('boss_key')
        self.assertGreater(boss.get_width(),small.get_width());self.assertIs(boss,BossKeyIcon.surface())
        self.assertTrue(any(boss.get_at((x,y))[:3]==(203,96,207) for x in range(16) for y in range(16)))
        self.assertNotEqual(pygame.image.tobytes(boss,'RGBA'),pygame.image.tobytes(atlas.get('boss_key',False),'RGBA'))
    def test_special_chest_acquisition_updates_hud_cue_and_save(self):
        g=Game(headless=True);g.scene=GameScene.PLAY;s=g.session;s.enter('r6');o=s.puzzles.objects['boss_key']
        self.assertEqual(o.phase,ChestPhase.HIDDEN)
        # Produce the prerequisites; the complete campaign separately witnesses each puzzle.
        s.puzzles.objects['gate'].latched=True;s.inventory.flags.update(('prism','warden','royal_resonance'));s.inventory.abilities.add('boots')
        s.tick(0);s.tick(.45);self.assertTrue(o.interact(s.puzzles,s.player));s.tick(0)
        # Drain earlier notifications through the production pickup queue.
        for _ in range(8):
            if s.pickup and s.pickup[0]=='boss_key':break
            s.tick(0)
        self.assertTrue(s.inventory.boss_key);self.assertIn('boss_key',s.combat.events)
        s.tick(1.0);self.assertEqual(s.pickup[0],'boss_key')
        self.assertGreater(s.pickup[2],1.)
        g.visual=[s.player.x,s.player.y];g.draw(.016)
        self.assertTrue(any('BOSS KEY ACQUIRED'==c[0] for c in g.renderer.ui.commands))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r6');self.assertTrue(loaded.inventory.boss_key)
            self.assertFalse(loaded.puzzles.objects['boss_key'].interact(loaded.puzzles,loaded.player))
    def test_gate_needs_key_opens_once_and_persists_animation(self):
        s=AdvancedDungeonSession();s.inventory.flags.add('warden');s.enter('r16');o=s.puzzles.objects['gate'];o.data['opening_duration']=.6
        self.assertFalse(o.interact(s.puzzles,s.player));s.inventory.boss_key=True
        self.assertTrue(o.interact(s.puzzles,s.player));s.puzzles.update(.2,s.player)
        self.assertAlmostEqual(o.opening,.4);self.assertFalse(o.state.active)
        self.assertFalse(o.interact(s.puzzles,s.player));self.assertTrue(s.inventory.boss_key)
        snap=s.capture();s.restore(snap);self.assertAlmostEqual(o.opening,.4)
        s.puzzles.update(.4,s.player);self.assertTrue(o.state.active)
