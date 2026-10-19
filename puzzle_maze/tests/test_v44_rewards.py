"""Royal first/replay policy, persistent idempotence and profile isolation."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import pygame
from puzzle_maze.royal_rewards import RoyalClearHistory,CampaignProfile
from puzzle_maze.rewards import DungeonRewardBag
from puzzle_maze.game import Game,GameScene
import test_v3_campaign as witness

class RoyalRewardTests(unittest.TestCase):
    def tearDown(self):pygame.quit()
    def bag(self):
        b=DungeonRewardBag()
        for id,treasure in (('royal_tokens','royal_tokens'),('royal_tickets','royal_tickets'),('royal_collection','royal_crown')):
            b.collect(f'r27:{id}:{treasure}',treasure)
        return b
    def test_first_clear_once_and_replay_smaller_without_changing_exploration_rewards(self):
        history=RoyalClearHistory();b=self.bag()
        self.assertIsNone(history.finalize(b,False,True,True));b.settle(True,True)
        first=history.finalize(b,True,True,True);self.assertEqual((first['tokens'],first['tickets']),(1000,300))
        self.assertEqual(first,history.finalize(b,True,True,True))
        first['tokens']=0;self.assertEqual(history.get(b.run_id)['tokens'],1000)
        replay=self.bag();replay.collect('exploration','token_cache');replay.collect('side','ticket_bundle');replay.settle(True,True)
        result=history.finalize(replay,True,True,True)
        self.assertEqual((result['tokens'],result['tickets']),(110,45));self.assertEqual(result['tier'],'replay')
        restored=RoyalClearHistory.restore(history.capture());self.assertEqual(restored.get(replay.run_id),result)
    def test_dead_exit_or_incomplete_vault_never_records_a_clear(self):
        history=RoyalClearHistory();b=self.bag()
        self.assertIsNone(history.finalize(b,False,True,False));self.assertIsNone(b.settle(True,False))
        self.assertIsNone(history.finalize(b,True,False,True));b.settle(True,True)
        self.assertIsNone(history.finalize(b,True,True,False));self.assertFalse(history.receipts)
        missing=DungeonRewardBag();missing.collect('fake','royal_tokens');missing.settle(True,True)
        self.assertIsNone(history.finalize(missing,True,True,True))
    def test_authoritative_history_persists_and_profiles_never_share_files(self):
        with tempfile.TemporaryDirectory() as folder:
            a=CampaignProfile('alice',folder);b=CampaignProfile('bob',folder)
            self.assertNotEqual(a.save_path,b.save_path)
            bag=self.bag();bag.settle(True,True);h=a.load_history();h.finalize(bag,True,True,True);a.save_history(h)
            reloaded=a.load_history();self.assertTrue(reloaded.first_claimed);self.assertFalse(b.load_history().first_claimed)
            self.assertEqual(reloaded.finalize(bag,True,True,True)['tokens'],1000)
            replay=self.bag();replay.settle(True,True);self.assertEqual(reloaded.finalize(replay,True,True,True)['tokens'],100)
            a.save_history(reloaded);self.assertEqual(len(a.load_history().receipts),2)
    def test_malformed_or_wrong_owner_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            store=CampaignProfile('../alice',folder);self.assertEqual(store.directory.parent,Path(folder))
            store.directory.mkdir();store.history_path.write_text('{bad')
            g=Game(headless=True);g.bind_profile('../alice',folder)
            self.assertTrue(g.session.history.blocked);g.start(onboarding=False)
            self.assertTrue(g.session.history.blocked);self.assertFalse(store.save_history(g.session.history))
            self.assertEqual(store.history_path.read_text(),'{bad')
            store.history_path.write_text(json.dumps({'owner':'wrong','history':RoyalClearHistory().capture()}))
            with self.assertRaises(ValueError):store.load_history()
    def finish_vault(self,g):
        s=g.session;s.enter('r27');d=witness.DungeonCampaignTests();d.s=s
        for id in ('royal_tokens','royal_tickets','royal_collection'):d.use(id)
        d.walk(next(e['pos'] for e in s.rooms.data['exits'] if e.get('finish')))
        self.assertTrue(s.transition());g.scene=GameScene.VICTORY;g.save()
        return s.history.get(s.rewards.run_id)
    def test_game_continue_new_game_and_player_switch_keep_independent_history(self):
        with tempfile.TemporaryDirectory() as folder:
            g=Game(headless=True);g.bind_profile('alice',folder);g.start(onboarding=False)
            first=self.finish_vault(g);self.assertEqual(first['tier'],'first')
            loaded=Game(headless=True);loaded.bind_profile('alice',folder);loaded.start(continuing=True)
            self.assertTrue(loaded.session.finished);self.assertEqual(loaded.session.history.get(first['run_id']),first)
            loaded.start(onboarding=False);replay=self.finish_vault(loaded)
            self.assertEqual((replay['tokens'],replay['tickets']),(100,30))
            bob=Game(headless=True);bob.bind_profile('bob',folder);bob.start(continuing=True)
            self.assertFalse(bob.session.finished);self.assertFalse(bob.session.history.first_claimed)
            self.assertEqual(self.finish_vault(bob)['tier'],'first')
    def test_death_in_vault_retry_rolls_back_pending_chest_rewards(self):
        g=Game(headless=True);g.start(onboarding=False);s=g.session;s.enter('r27');d=witness.DungeonCampaignTests();d.s=s
        d.use('royal_tokens');s.combat.entry_protection=0
        while s.player.hp:
            s.player.invulnerable=0;s.combat.damage_player(SimpleNamespace(x=1,y=1))
        self.assertFalse(s.history.receipts);self.assertFalse(s.rewards.claimed);s.reset()
        self.assertEqual(s.rewards.tokens,0);self.assertFalse(s.puzzles.objects['royal_tokens'].state.active)
