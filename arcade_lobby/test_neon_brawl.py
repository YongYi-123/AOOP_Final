"""Headless lobby integration, settlement, presentation and lifecycle regression."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from game import Game
from local_session import LocalSession
from player_profile import PlayerProfile
from room_testing import goto_room
from scenes import MINIGAME_SCENES
from arcade_layout import ArcadeLayout
from neon_brawl_scene import NeonBrawlScene
from neon_brawl.game import BrawlGame
from neon_brawl.model import Campaign
from neon_brawl.tests.pilot import play
from font import get_font

DT=1/60
class PresentationTests(unittest.TestCase):
    def setUp(self):
        pygame.init(); self.b=BrawlGame(get_font()); self.surface=pygame.Surface((400,300))
    def key(self,k):
        self.b.handle_event(pygame.event.Event(pygame.KEYDOWN,key=k))
        self.b.handle_event(pygame.event.Event(pygame.KEYUP,key=k))
    def test_intro_timeout_and_skip(self):
        for _ in range(700): self.b.update(DT)
        self.assertEqual(self.b.screen,'title')
        self.b.change('intro'); self.key(pygame.K_ESCAPE); self.assertEqual(self.b.screen,'title')
    def test_flow_and_selection(self):
        self.key(pygame.K_RETURN); self.key(pygame.K_RETURN); self.key(pygame.K_d)
        self.key(pygame.K_RETURN); self.assertEqual(self.b.campaign.player.name,'NOVA')
        self.assertEqual(self.b.screen,'tutorial'); self.key(pygame.K_j)
        self.assertIn('light',self.b.seen_actions); self.key(pygame.K_RETURN)
        self.assertEqual(self.b.screen,'playing'); self.assertTrue(self.b.started)
    def test_pause_controls_and_focus_loss(self):
        self.b.campaign=Campaign(); self.b.change('playing'); self.b.started=True
        self.key(pygame.K_ESCAPE); elapsed=self.b.campaign.elapsed
        self.b.update(.05); self.assertEqual(self.b.campaign.elapsed,elapsed)
        self.key(pygame.K_s); self.key(pygame.K_RETURN); self.assertEqual(self.b.screen,'controls')
        self.key(pygame.K_RETURN); self.assertEqual(self.b.screen,'paused')
        self.key(pygame.K_ESCAPE); self.assertEqual(self.b.screen,'playing')
        self.b.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST)); self.assertEqual(self.b.screen,'paused')
        self.assertFalse(self.b.held)
    def test_held_confirm_never_skips_multiple_screens(self):
        event=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN)
        self.b.handle_event(event)
        # Real platforms suppress repeated keydowns via repeat flag.
        self.b.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,repeat=True))
        self.assertEqual(self.b.screen,'title')
    def test_all_screens_and_all_sprite_states_render(self):
        from neon_brawl.art import sprite
        from neon_brawl.data import ROSTER, ENEMIES, ATTACKS
        self.b.campaign=Campaign(); self.b.campaign.spawn()
        for screen in ('intro','title','select','tutorial','controls','playing','paused','checkpoint','stage_clear','game_over','ending','results'):
            self.b.screen=screen; self.b.draw(self.surface)
        for name in (*ROSTER,*ENEMIES):
            for state in ('idle','walk','hurt','knockdown','defeated','victory','dodge',*ATTACKS):
                for frame in range(4): self.assertEqual(sprite(name,state,frame).get_size(),(64,64))
    def test_no_audio_device_required(self):
        pygame.mixer.quit(); self.b.audio=None
        self.key(pygame.K_RETURN); self.b.draw(self.surface)
    def test_result_read_has_no_side_effects(self):
        self.assertEqual(self.b.result(),self.b.result())

class LobbyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=PlayerProfile(profile_id='brawl_test',tokens=20,tickets=0)
        self.game=Game(session=LocalSession(self.p),audio_prefs=os.path.join(self.tmp.name,'audio.json'))
        self.addCleanup(self.game.quit)
        self.room=goto_room(self.game,'arcade_floor')
        self.machine=next(m for m in self.room.machines if m.id=='neon_brawl')
    def frames(self,count=40):
        for _ in range(count): self.game.step([],DT)
    def launch(self):
        self.room._start_game(self.machine,player=self.room.players[0]); self.frames()
        self.scene=self.game.scenes.current; self.assertIsInstance(self.scene,NeonBrawlScene)
        return self.scene
    def close(self): self.game.scenes.pop(); self.frames()
    def test_registration_location_prompt_collision(self):
        self.assertIs(MINIGAME_SCENES['neon_brawl'],NeonBrawlScene)
        self.assertEqual(self.machine.rect.topleft,(70,138))
        self.assertTrue(self.machine.zone.collidepoint(self.machine.rect.centerx,self.machine.rect.bottom+8))
        for m in self.room.machines:
            if m is not self.machine: self.assertFalse(m.footprint.colliderect(self.machine.footprint))
        from broken_cabinet import BrokenCatCade
        self.assertTrue(any(isinstance(p,BrokenCatCade) for p in self.room.interactables))
    def test_charge_and_early_quit_policy(self):
        self.launch(); self.assertEqual(self.p.tokens,19)
        self.close(); self.assertIs(self.game.scenes.current,self.room)
        self.assertEqual(self.p.tokens,19); self.assertEqual(self.p.tickets,0)
    def test_pending_launch_refunds(self):
        self.room._start_game(self.machine,player=self.room.players[0])
        self.assertEqual(self.p.tokens,19); self.game.quit(); self.assertEqual(self.p.tokens,20)
    def test_victory_paid_once_and_save_compatible(self):
        scene=self.launch(); c,frames=play('REX'); self.assertEqual(c.state,'victory')
        scene.brawl.campaign=c; scene.brawl.started=True; scene.brawl.change('results')
        result=scene.get_result(); self.assertEqual(result,scene.get_result())
        expected=c.tickets; self.close(); self.assertEqual(self.p.tickets,expected)
        self.room._end_play(True); self.game.quit(); self.assertEqual(self.p.tickets,expected)
        restored=PlayerProfile.from_dict(self.p.to_dict())
        self.assertEqual(restored.tickets,expected); self.assertEqual(restored.high_score('neon_brawl'),c.score)
    def test_defeat_and_repeat_entry_no_stale_state(self):
        scene=self.launch()
        for _ in range(4):
            scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
            scene.handle_event(pygame.event.Event(pygame.KEYUP,key=pygame.K_RETURN))
        for _ in range(60*180):
            self.game.scenes.update(DT)
            if scene.brawl.screen=='game_over': break
        self.assertEqual(scene.brawl.screen,'game_over')
        self.assertEqual(scene.brawl.campaign.player.health,0)
        self.close()
        scene=self.launch(); self.assertIsNone(scene.brawl.campaign); self.assertEqual(scene.brawl.screen,'intro')
        self.assertEqual(self.p.tokens,18)
    def test_music_stage_boss_and_settings(self):
        scene=self.launch(); scene.brawl.campaign=Campaign(); scene.brawl.campaign.stage=1
        self.assertEqual(Game.music_for([scene]),'neon_brawl_1')
        scene.brawl.campaign.wave=3; scene.brawl.campaign.spawn()
        self.assertEqual(Game.music_for([scene]),'neon_brawl_3')
        self.game.audio.set_volumes(bgm=.1,sfx=.2); self.assertAlmostEqual(self.game.audio.bgm_volume,.1)
        scene.brawl.change('paused'); self.assertEqual(Game.duck_for(scene),.45)
    def test_window_close_settles_once(self):
        scene=self.launch(); scene.brawl.campaign=Campaign(); scene.brawl.started=True
        scene.brawl.campaign.score=1800
        self.game.quit(); self.assertEqual(self.p.tickets,10)
        self.game.quit(); self.assertEqual(self.p.tickets,10)
    def test_complete_scene_playthrough_using_only_keyboard_actions(self):
        from neon_brawl.tests.pilot import decide
        scene=self.launch()
        def key(k):
            scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=k,mod=0))
            scene.handle_event(pygame.event.Event(pygame.KEYUP,key=k,mod=0))
        for expected in ('title','select','tutorial','playing'):
            key(pygame.K_RETURN); self.assertEqual(scene.brawl.screen,expected)
        visited=set(); phases=set(); movement=set()
        for frame in range(60*1200):
            b=scene.brawl; c=b.campaign
            visited.add(c.stage)
            phases.update((e.name,e.phase) for e in c.enemies if e.boss)
            if b.screen in ('checkpoint','stage_clear'):
                key(pygame.K_e); key(pygame.K_RETURN); movement.clear()
            elif b.screen=='ending':
                key(pygame.K_RETURN); break
            elif b.screen=='game_over': self.fail('Normal-input scene pilot was defeated')
            elif b.screen=='playing':
                (dx,dy),action=decide(c)
                desired=set()
                if dx: desired.add(pygame.K_d if dx>0 else pygame.K_a)
                if dy: desired.add(pygame.K_s if dy>0 else pygame.K_w)
                for k in movement-desired: scene.handle_event(pygame.event.Event(pygame.KEYUP,key=k,mod=0))
                for k in desired-movement: scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=k,mod=0))
                movement=desired
                if action: key({'light':pygame.K_j,'special':pygame.K_u,'dodge':pygame.K_i,'heavy':pygame.K_k}[action])
            self.game.scenes.update(DT)
            if frame%120==0: self.game.step([],0)
        self.assertEqual(scene.brawl.screen,'results')
        self.assertEqual(visited,{0,1,2}); self.assertIn(('NULL',2),phases)
        self.assertEqual(scene.brawl.campaign.state,'victory')
        expected=scene.brawl.result()['tickets']; key(pygame.K_RETURN); self.frames()
        self.assertIs(self.game.scenes.current,self.room)
        self.assertEqual(self.p.tokens,19); self.assertEqual(self.p.tickets,expected)
        self.room._end_play(True); self.assertEqual(self.p.tickets,expected)

    def test_pause_menu_quit_uses_existing_no_refund_policy(self):
        scene=self.launch()
        for k in (pygame.K_RETURN,)*4+(pygame.K_ESCAPE,pygame.K_s,pygame.K_s,pygame.K_RETURN):
            scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=k))
            scene.handle_event(pygame.event.Event(pygame.KEYUP,key=k))
        self.frames()
        self.assertIs(self.game.scenes.current,self.room)
        self.assertEqual(self.p.tokens,19); self.assertEqual(self.p.tickets,0)

    def test_coupon_refunded_if_launch_never_opens(self):
        from item_registry import FREE_PLAY_COUPON
        self.p.inventory.add_item(FREE_PLAY_COUPON)
        self.room._start_game(self.machine,use_coupon=True,player=self.room.players[0])
        self.assertFalse(self.p.inventory.has_item(FREE_PLAY_COUPON))
        self.game.quit()
        self.assertTrue(self.p.inventory.has_item(FREE_PLAY_COUPON))
        self.assertEqual(self.p.tokens,20)
