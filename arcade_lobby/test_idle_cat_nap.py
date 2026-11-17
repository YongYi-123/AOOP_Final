"""Standing still summons a room-local nap pile without blocking normal play."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import math
import tempfile
import unittest
import pygame
from game import Game
from room_testing import goto_room
from cat import CatState


class IdleCatNapTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.game=Game(save_path=self.folder.name+'/save.json')
        self.game.step([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE)],.02)
        self.room=goto_room(self.game,'arcade_floor');self.colony=self.room.cats
        self.player=self.room.player;self.player.x,self.player.y=200.,145.;self.player.stop()
        self.colony.update(0,[self.player])

    def tick(self,seconds,busy=False):
        for _ in range(round(seconds*20)):
            self.colony.update(.05,[self.player],busy)

    def gather(self):
        self.tick(65)
        self.assertTrue(self.colony.idle_nap.active)
        self.assertEqual(len(self.colony.idle_nap.plans),len(self.colony.cats))

    def test_requires_continuous_thirty_seconds_then_walks_without_teleporting(self):
        self.tick(29.9);nap=self.colony.idle_nap
        self.assertFalse(nap.active)
        before={cat:cat.position for cat in self.colony}
        self.tick(.2);self.assertTrue(nap.active)
        for cat in self.colony:self.assertLessEqual(math.dist(before[cat],cat.position),6)
        self.tick(35)
        for cat in self.colony:
            self.assertEqual(cat.state,CatState.SLEEP)
            self.assertTrue(cat.anim.name.startswith('nap_'))
            self.assertLessEqual(math.dist(cat.position,(self.player.x,self.player.y)),42)
            self.assertFalse(cat.feet.colliderect(self.player.feet))
            self.assertTrue(self.colony.is_free(cat.position))
        feet=[cat.feet for cat in self.colony]
        self.assertFalse(any(a.colliderect(b) for i,a in enumerate(feet) for b in feet[i+1:]))

    def test_route_can_leave_a_narrow_gap_using_resident_cat_footprint(self):
        from types import SimpleNamespace
        cat = SimpleNamespace(position=(20, 20))
        colony = SimpleNamespace(room_solids=[pygame.Rect(0, 15, 50, 1)], players=[], cats=[])
        path = self.colony.idle_nap._route(colony, cat, (20, 40))
        self.assertEqual(path, [(20, 40)])

    def test_movement_even_when_blocked_resets_wait_and_busy_windows_do_not_count(self):
        self.tick(29)
        self.player.held=[pygame.K_a];self.tick(2)
        self.assertEqual(self.colony.idle_nap.idle_time,0)
        self.player.held=[];self.tick(29);self.assertFalse(self.colony.idle_nap.active)
        self.tick(40,busy=True);self.assertFalse(self.colony.idle_nap.active)
        self.assertEqual(self.colony.idle_nap.idle_time,0)
        self.tick(29);self.assertFalse(self.colony.idle_nap.active)

    def test_walking_away_wakes_the_group_and_leaves_an_escape_path(self):
        self.gather();nap=self.colony.idle_nap;cats=list(nap.plans)
        self.assertFalse(self.colony.blockers(self.player))
        y=self.player.y
        self.game.step([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_s)],1/60)
        for _ in range(39):self.game.step([],1/60)
        self.game.step([pygame.event.Event(pygame.KEYUP,key=pygame.K_s)],1/60)
        self.assertGreater(self.player.y,y+15)
        self.assertFalse(nap.active);self.assertFalse(nap.plans)
        self.assertTrue(all(cat.state!=CatState.SLEEP for cat in cats))

    def test_story_editor_and_player_actions_do_not_count_as_idle(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        for attribute, value in (('hub', SimpleNamespace(story=SimpleNamespace(locked=True))),
                                 ('edit_mode', True)):
            with patch.object(self.room, attribute, value, create=True):
                self.tick(40)
                self.assertEqual(self.colony.idle_nap.idle_time, 0)
                self.assertFalse(self.colony.idle_nap.active)
        self.player.action = 'sit'
        self.tick(40)
        self.assertFalse(self.colony.idle_nap.active)
        self.player.action = None
        self.tick(29)
        self.assertFalse(self.colony.idle_nap.active)

    def test_pause_resume_room_changes_and_dance_reset_the_wait(self):
        self.gather();self.colony.pause()
        snapshot=[(cat.position,cat.time) for cat in self.colony]
        self.tick(5)
        self.assertEqual(snapshot,[(cat.position,cat.time) for cat in self.colony])
        self.assertFalse(self.colony.idle_nap.active)
        self.colony.resume();self.tick(29);self.assertFalse(self.colony.idle_nap.active)
        self.tick(2);self.assertTrue(self.colony.idle_nap.active)
        self.assertTrue(self.colony.start_dance());self.assertFalse(self.colony.idle_nap.active)
        self.assertTrue(self.colony.dancing)
        self.tick(5);self.assertFalse(self.colony.idle_nap.active)
        goto_room(self.game,'home');self.assertTrue(self.colony.paused)
        goto_room(self.game,'arcade_floor');self.assertEqual(self.colony.idle_nap.idle_time,0)

    def test_petting_sleepers_uses_the_existing_reaction_and_cancels_the_gather(self):
        self.gather();cat=self.colony.cats[0]
        plays=cat.voice.plays
        self.assertTrue(self.colony.interact(cat,self.player))
        self.assertEqual(cat.state,CatState.PET)
        self.assertGreater(cat.voice.plays,plays)
        self.assertFalse(self.colony.idle_nap.active)
        self.assertIsNone(self.colony.follower)

    def test_each_hub_room_uses_its_own_cats_and_no_profile_rewards_are_changed(self):
        before=(self.game.profile.tokens,self.game.profile.tickets,self.game.profile.inventory.to_dict())
        for room_id,position in (('home',(200,250)),('arcade_floor',(200,145)),('prize_plaza',(200,230))):
            room=goto_room(self.game,room_id);p=room.player;p.x,p.y=position;p.stop()
            cats=room.cats;cats.update(0,[p])
            for _ in range(65*20):cats.update(.05,[p])
            self.assertTrue(cats.idle_nap.active,room_id)
            self.assertEqual(len(cats.idle_nap.plans),len(cats.cats),room_id)
            self.assertTrue(all(cat.state==CatState.SLEEP for cat in cats),room_id)
            self.assertTrue(all(cat in cats.cats for cat in cats.idle_nap.plans))
        self.assertEqual(before,(self.game.profile.tokens,self.game.profile.tickets,self.game.profile.inventory.to_dict()))


if __name__=='__main__':unittest.main()
