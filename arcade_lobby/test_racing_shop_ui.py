import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from game import Game
from local_session import LocalSession
from player_profile import PlayerProfile
from room_testing import goto_room
from racing_progression.ui import PrizeCounterScene,GarageScene
from racing_progression.service import PrizeService
from racing_progression.station import GarageStation


class ShopSceneTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id='shop_a',tickets=500),PlayerProfile(profile_id='shop_b',tickets=500)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game,'prize_plaza')

    def frames(self,count=30):
        for _ in range(count):self.game.step([],1/60)

    def key(self,key):
        self.game.step([pygame.event.Event(pygame.KEYDOWN,key=key,mod=0)],1/60)

    def test_counter_owns_input_and_repeated_confirm_equips_without_charge(self):
        self.room.acting_player = self.room.players[1]
        self.room.open_prize_counter()
        self.frames()
        scene = self.game.scenes.current
        self.assertIsInstance(scene,PrizeCounterScene)
        self.key(pygame.K_DOWN)
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[1].tickets,500)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.profiles[1].tickets,420)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.profiles[1].tickets,420)
        self.assertEqual(self.profiles[1].racing_selection['car'],'comet')
        self.assertEqual(self.profiles[0].tickets,500)
        self.key(pygame.K_ESCAPE)
        self.frames()
        self.assertIs(self.game.scenes.current,self.room)

    def test_garage_shows_owned_cars_and_actual_performance(self):
        PrizeService(self.profiles[0]).buy('car','viper')
        self.room.open_garage()
        self.frames()
        scene = self.game.scenes.current
        self.assertIsInstance(scene,GarageScene)
        self.assertEqual([p.key for p in scene.rows],['falcon','viper'])
        self.key(pygame.K_s)
        self.key(pygame.K_e)
        self.assertEqual(scene.shop.garage.selected('car'),'viper')
        self.assertGreater(scene.preview.spec('viper').max_speed,scene.preview.spec('falcon').max_speed)
        self.assertTrue(any(isinstance(p,GarageStation) for p in self.room.props))
        scene.draw(pygame.Surface((400,300)))
        self.key(pygame.K_ESCAPE)
        self.frames()
        self.assertIs(self.game.scenes.current,self.room)

    def test_shop_to_garage_and_back_preserves_owner(self):
        self.room.open_prize_counter()
        self.frames()
        shop = self.game.scenes.current
        self.key(pygame.K_i)
        self.frames()
        self.assertIsInstance(self.game.scenes.current,GarageScene)
        self.assertIs(self.game.scenes.current.owner,shop.owner)
        self.key(pygame.K_i)
        self.frames()
        self.assertIs(self.game.scenes.current,shop)

    def test_e_on_garage_terminal_launches_and_returns_to_plaza(self):
        terminal = next(p for p in self.room.props if isinstance(p,GarageStation))
        avatar = self.room.players[0]
        avatar.x,avatar.y = terminal.zone.centerx,terminal.zone.bottom-2
        self.frames(5)
        self.key(pygame.K_e)
        self.frames(40)
        self.assertIsInstance(self.game.scenes.current,GarageScene)
        self.assertIs(self.game.scenes.current.owner,self.game.session.primary)
        self.key(pygame.K_ESCAPE)
        self.frames()
        self.assertIs(self.game.scenes.current,self.room)
