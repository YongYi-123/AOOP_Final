import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from player_profile import PlayerProfile
from racing_progression.service import PrizeService,RacingGarage
from retro_racer_scene import load_retro_racer


class RacerProgressionIntegrationTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((800,600))
        self.module,self.race = load_retro_racer()
        self.game = self.module.Game(screen=pygame.Surface((800,600)))
        self.addCleanup(self.game.audio.stop_engine)
        self.profile = PlayerProfile(tickets=1000)
        self.shop = PrizeService(self.profile)
        self.game.configure_progression(self.shop.garage)

    def test_locked_track_and_car_are_previewable_but_cannot_start(self):
        game = self.game
        game.state = self.race.State.TRACK_SELECT
        game.track = game.tracks[1]
        game.apply_look()
        game.press_enter()
        self.assertIs(game.state,self.race.State.TRACK_SELECT)
        self.assertIn('60 TICKETS',game.toast)
        self.assertTrue(self.shop.buy('track','harbor').success)
        game.press_enter()
        self.assertIs(game.state,self.race.State.CAR_SELECT)
        game.car_menu.move(1)
        game.press_enter()
        self.assertIs(game.state,self.race.State.CAR_SELECT)
        self.assertIn('120 TICKETS',game.toast)
        self.assertTrue(self.shop.buy('car','viper').success)
        game.press_enter()
        self.assertIs(game.state,self.race.State.COUNTDOWN)
        self.assertEqual(game.player.spec.key,'viper')
        self.assertEqual(self.profile.racing_selection['track'],'harbor')
        self.assertEqual(self.profile.racing_selection['car'],'viper')

    def test_locked_scenery_is_blocked_then_applied_after_purchase(self):
        game = self.game
        game.theme = game.themes.themes[1]
        game.apply_look()
        game.state = self.race.State.TRACK_SELECT
        game.press_enter()
        self.assertIs(game.state,self.race.State.TRACK_SELECT)
        self.assertTrue(self.shop.buy('scenery','city').success)
        game.press_enter()
        self.assertIs(game.state,self.race.State.CAR_SELECT)
        self.assertEqual(game.selected_theme.key,'city')
        game.render()

    def test_paint_survives_reset_without_changing_car_stats(self):
        self.assertTrue(self.shop.buy('paint','tuxedo').success)
        self.assertTrue(self.shop.garage.select('paint','tuxedo'))
        self.game.configure_progression(self.shop.garage)
        before = self.game.player.spec.stats()
        color = self.game.player.livery.primary
        self.assertEqual(color,(235,235,245))
        self.game.start_race()
        self.assertEqual(self.game.player.livery.primary,color)
        self.assertEqual(self.game.player.spec.stats(),before)

    def test_reused_racer_forgets_previous_visitors_unlocks_and_paint(self):
        self.shop.buy('car','comet')
        self.shop.garage.select('car','comet')
        self.shop.buy('track','cloudpass')
        self.shop.garage.select('track','cloudpass')
        self.shop.buy('paint','neon')
        self.shop.garage.select('paint','neon')
        self.game.configure_progression(self.shop.garage)
        self.assertEqual(self.game.player.spec.key,'comet')
        self.assertEqual(self.game.road.route.key,'cloudpass')
        other = PlayerProfile()
        self.game.configure_progression(RacingGarage(other))
        self.assertEqual(self.game.player.spec.key,'falcon')
        self.assertEqual(self.game.road.route.key,'emerald')
        self.assertFalse(self.game.progression.owns('car','comet'))
        self.assertNotEqual(self.game.player.livery.primary,(255,80,185))
