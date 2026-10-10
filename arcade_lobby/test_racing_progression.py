import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
from unittest.mock import patch
from player_profile import PlayerProfile
from rewards import ItemGrantResult
from racing_progression.service import PrizeService,RacingGarage
from racing_progression.catalog import PRIZES,DEFAULTS


class RacingProgressionTests(unittest.TestCase):
    def test_free_defaults_exist_for_legacy_empty_and_corrupt_selections(self):
        for data in ({},{'racing_selection':[]},{'racing_selection':{'car':'unknown','track':'cloudpass'}}):
            profile = PlayerProfile.from_dict(data)
            garage = RacingGarage(profile)
            for kind,key in DEFAULTS.items():
                self.assertEqual(garage.selected(kind),key)
                self.assertTrue(garage.owns(kind,key))

    def test_purchase_charges_once_and_preserves_earned_totals(self):
        profile = PlayerProfile(tickets=200)
        shop = PrizeService(profile)
        earned = profile.lifetime_tickets_earned
        self.assertTrue(shop.buy('car','comet').success)
        self.assertEqual(profile.tickets,120)
        self.assertTrue(shop.garage.select('car','comet'))
        self.assertFalse(shop.buy('car','comet').success)
        self.assertEqual(profile.tickets,120)
        self.assertEqual(profile.lifetime_tickets_earned,earned)

    def test_insufficient_unknown_and_free_do_not_spend(self):
        profile = PlayerProfile(tickets=5)
        shop = PrizeService(profile)
        for kind,key in (('car','comet'),('car','missing'),('car','falcon')):
            self.assertFalse(shop.buy(kind,key).success)
            self.assertEqual(profile.tickets,5)
        self.assertFalse(shop.garage.select('car','comet'))

    def test_grant_failure_refunds_and_does_not_advance_tasks(self):
        profile = PlayerProfile(tickets=200)
        earned = profile.lifetime_tickets_earned
        with patch('racing_progression.service.RewardService.grant_item',return_value=
                   ItemGrantResult(False,'racing_car_comet',1,0,'stack_full')):
            self.assertFalse(PrizeService(profile).buy('car','comet').success)
        self.assertEqual(profile.tickets,200)
        self.assertEqual(profile.lifetime_tickets_earned,earned)
        self.assertFalse(RacingGarage(profile).owns('car','comet'))

    def test_every_prize_round_trips_in_independent_profile(self):
        a,b = PlayerProfile(tickets=5000),PlayerProfile(tickets=5000)
        shop = PrizeService(a)
        for prize in PRIZES:
            if not prize.free:
                self.assertTrue(shop.buy(prize.kind,prize.key).success)
            if prize.kind in DEFAULTS:
                self.assertTrue(shop.garage.select(prize.kind,prize.key))
        again = PlayerProfile.from_dict(a.to_dict())
        for prize in PRIZES:
            self.assertTrue(RacingGarage(again).owns(prize.kind,prize.key))
            self.assertEqual(RacingGarage(b).owns(prize.kind,prize.key),prize.free)
        self.assertEqual(again.racing_selection,a.racing_selection)
        self.assertEqual(b.tickets,5000)

    def test_purchase_is_one_autosave_with_final_inventory_and_wallet(self):
        profile = PlayerProfile(tickets=200)
        saved = []
        profile.subscribe_save(lambda: saved.append(profile.to_dict()))
        self.assertTrue(PrizeService(profile).buy('car','viper').success)
        self.assertEqual(len(saved),1)
        self.assertEqual(saved[0]['tickets'],80)
        self.assertEqual(saved[0]['inventory']['racing_car_viper'],1)

    def test_decoration_requires_ownership_and_fits_existing_slot(self):
        import pygame
        pygame.init()
        profile = PlayerProfile(tickets=200)
        shop = PrizeService(profile)
        self.assertFalse(shop.equip_decoration('poster_arcade'))
        self.assertTrue(shop.buy('decoration','poster_arcade').success)
        self.assertTrue(shop.equip_decoration('poster_arcade'))
        self.assertIn('poster_arcade',profile.home_decorations.values())

    def test_wallet_rejects_negative_noninteger_and_bool(self):
        profile = PlayerProfile(tickets=200)
        for amount in (-1,1.5,True):
            with self.assertRaises(ValueError):profile.spend_tickets(amount)
            with self.assertRaises(ValueError):profile.refund_tickets(amount)
