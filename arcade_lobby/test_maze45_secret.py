"""Grey Pixel connects through the real, owner-scoped chapter event bus."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
import unittest
from unittest.mock import patch
from game import Game
from local_session import LocalSession
from player_profile import PlayerProfile
from room_testing import goto_room
from quests import SECRET_ITEM_DUNGEON,SECRET_ITEM_CLAW,SECRET_ITEM_RETRO_RACER

class GreyPixelLobbyTests(unittest.TestCase):
    def test_pending_discovery_records_once_when_chapter_three_opens(self):
        with tempfile.TemporaryDirectory() as folder,patch('puzzle_maze.game.Game.save'):
            p=PlayerProfile(profile_id='maze45_secret',tokens=0)
            g=Game(session=LocalSession(p),audio_prefs=folder+'/audio.json')
            try:
                room=goto_room(g,'arcade_floor');machine=next(m for m in room.machines if m.id=='puzzle_maze')
                room._start_game(machine,player=room.players[0])
                for _ in range(35):g.step([],1/60)
                scene=g.scenes.current;manager=g.hub.story.manager
                scene.maze.session.grey_pixel=True;scene.maze.session.lore.add('kevin_photo')
                scene.sync_story();self.assertFalse(manager.has_secret_item(SECRET_ITEM_DUNGEON))
                manager.handle('vending_secret');manager.handle('secret_item_found',SECRET_ITEM_RETRO_RACER)
                manager.handle('secret_trial_done','trial_01');manager.handle('secret_item_found',SECRET_ITEM_CLAW)
                p.add_tokens(100,'TEST');p.add_tickets(1000);manager.handle('secret_trial_done','trial_02')
                self.assertTrue(manager.chapter_unlocked(3))
                events=[];g.session.add_listener(lambda owner,event:events.append(event))
                scene.sync_story();self.assertTrue(manager.has_secret_item(SECRET_ITEM_DUNGEON))
                balance=(p.tokens,p.tickets);scene.sync_story();scene.sync_story()
                self.assertEqual(sum(e.type=='secret_item_found' and e.key==SECRET_ITEM_DUNGEON for e in events),1)
                self.assertEqual((p.tokens,p.tickets),balance);self.assertTrue(manager.has_secret_item(SECRET_ITEM_CLAW))
                self.assertTrue(manager.state['flags']['egg_kevin_developer_room'])
                restored=PlayerProfile.from_dict(p.to_dict());self.assertEqual(restored.story,p.story)
                g.scenes.pop()
                for _ in range(40):g.step([],1/60)
                self.assertIs(g.scenes.current,room)
            finally:g.quit()
