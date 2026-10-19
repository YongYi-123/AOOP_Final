"""Production movement from dead Boss to a walkable, interactive royal room."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from puzzle_maze.game import Game,GameScene
from puzzle_maze.advanced_dungeon import AdvancedDungeonSession
from puzzle_maze.combat import EnemyState
import test_v3_campaign as witness

class VaultTests(unittest.TestCase):
    def tearDown(self):pygame.quit()
    def test_boss_death_waits_for_animation_then_vault_exploration_precedes_settlement(self):
        s=AdvancedDungeonSession();s.enter('r17');boss=s.combat.enemies[0]
        # Boss damage/phase mechanics are also exercised by the full campaign.
        boss.hp=1;boss.exposed=5;s.inventory.flags.add('crystal_blue');boss.receive_damage(s.combat,1,'sword',s.player)
        self.assertEqual(boss.state,EnemyState.DYING);s.tick(.6)
        self.assertFalse(s.puzzles.objects['gate'].state.active);self.assertFalse(s.rewards.claimed)
        s.tick(.6);self.assertEqual(boss.state,EnemyState.DEAD);self.assertTrue(s.puzzles.objects['gate'].state.active)
        d=witness.DungeonCampaignTests();d.s=s;d.travel('r18');d.use('treasure');d.use('dawn');d.travel('r27')
        self.assertEqual(s.rooms.data['name'],'Royal Treasure Vault');self.assertTrue(s.can_enter(s.player.x,s.player.y))
        self.assertFalse(s.finished);self.assertFalse(s.rewards.claimed)
        for name in ('royal_tokens','royal_tickets','royal_collection'):d.use(name)
        self.assertEqual((s.rewards.tokens,s.rewards.tickets),(1010,315));self.assertIn('royal_crown',s.rewards.collections)
        d.travel('r18');d.travel('r27')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';s.save(path);loaded=AdvancedDungeonSession.load(path)
            self.assertEqual(loaded.rooms.current,'r27')
            for name in ('royal_tokens','royal_tickets','royal_collection'):
                o=loaded.puzzles.objects[name];self.assertTrue(o.state.active);self.assertFalse(o.interact(loaded.puzzles,loaded.player))
        d.walk(next(e['pos'] for e in s.rooms.data['exits'] if e.get('finish')));self.assertTrue(s.transition());self.assertTrue(s.rewards.claimed)
    def test_scroll_e_prompt_modal_and_clocks_freeze_without_adding_a_story(self):
        g=Game(headless=True);g.start(onboarding=False);s=g.session;s.enter('r27');s.player.x,s.player.y=11,8;s.player.facing=(0,-1);g.visual=[11,8];g.fade=0
        g.draw(.016);self.assertTrue(any('[E] Read' in c[0] for c in g.renderer.ui.commands))
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e));self.assertEqual(g.scene,GameScene.SCROLL)
        before=s.capture();g.update(2);self.assertEqual(before,s.capture())
        g.draw(.016);self.assertIn('COMING SOON',[c[0] for c in g.renderer.ui.commands])
        self.assertNotIn('The story will continue...',[c[0] for c in g.renderer.ui.commands])
        g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE));self.assertEqual(g.scene,GameScene.PLAY)
        self.assertFalse(s.finished);self.assertFalse(s.rewards.claimed)
    def test_vault_art_is_cached_and_does_not_cover_hud_or_change_collision(self):
        g=Game(headless=True);g.scene=GameScene.PLAY;g.session.enter('r27');g.visual=[11,7];g.fade=0
        before=g.session.capture();layer=g.renderer.vault_art.layer()
        self.assertIs(layer,g.renderer.vault_art.layer())
        with patch('pygame.transform.smoothscale',side_effect=AssertionError('no blurred scaling')):g.draw(.016)
        self.assertEqual(before,g.session.capture());self.assertEqual(g.renderer.surface.get_clip(),g.renderer.surface.get_rect())
