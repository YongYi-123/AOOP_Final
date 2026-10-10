import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from street_details import StreetDetail, StreetDistricts
from vehicle_identity import RivalBadge
from tracks import TRACKS
from theme import THEMES

class StreetIdentityTests(unittest.TestCase):
    def test_each_theme_has_distinct_art_and_variations(self):
        images=[]
        for theme in THEMES:
            variants=[]
            for variant in (0,1):
                surface=pygame.Surface((160,160))
                StreetDetail(0,2,theme.key,variant).draw(surface,80,140,100)
                variants.append(pygame.image.tostring(surface,'RGB'))
            self.assertNotEqual(*variants,theme.key)
            images.append(variants[0])
        self.assertEqual(len(set(images)),len(THEMES))

    def test_districts_follow_actual_route_and_switch_theme_without_geometry_changes(self):
        from road import Road
        road=Road(THEMES[0],route=TRACKS[-1].build())
        route=road.route
        for theme in THEMES:
            road.apply(theme)
            expected=StreetDistricts.for_road(route,theme)
            self.assertEqual(road.districts,expected)
            self.assertIs(road.route,route)
            self.assertEqual({d.x for d in expected},{-2.1,2.1})
            self.assertTrue(all(0 <= d.z < road.length and d.theme==theme.key for d in expected))

    def test_rivals_receive_unique_numbers_and_badge_changes_only_pixels(self):
        from game import Game
        game=Game()
        self.addCleanup(game.audio.stop_engine)
        game.start_race()
        racers=game.manager.field.racers
        self.assertEqual([r.race_number for r in racers],list(range(1,len(racers)+1)))
        surface=pygame.Surface((160,160))
        before=pygame.image.tostring(surface,'RGB')
        RivalBadge.draw(surface,80,140,70,3)
        self.assertNotEqual(before,pygame.image.tostring(surface,'RGB'))
        tiny=pygame.Surface((40,40))
        before=pygame.image.tostring(tiny,'RGB')
        RivalBadge.draw(tiny,20,30,8,3)
        self.assertEqual(before,pygame.image.tostring(tiny,'RGB'))
