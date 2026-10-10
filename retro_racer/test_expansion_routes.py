import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from tracks import TRACKS
from game import Game
from oil_spin import OilSpinEffect
import settings as S


class ExpansionRouteTests(unittest.TestCase):
    def test_new_routes_have_continuous_geometry_and_distinct_elevation(self):
        street, mountain = [next(t for t in TRACKS if t.key == k) for k in ("starlight","cloudpass")]
        self.assertEqual((street.key,mountain.key),('starlight','cloudpass'))
        routes = [track.build() for track in (street,mountain)]
        for route in routes:
            self.assertEqual(route.points[0],route.points[-1])
            self.assertLess(max(abs(route.curves[(i+1)%len(route.curves)]-c)
                                for i,c in enumerate(route.curves)),.8)
            self.assertGreater(sum(c < -1 for c in route.curves),20)
            self.assertGreater(sum(c > 1 for c in route.curves),20)
        self.assertGreater(max(routes[1].heights)-min(routes[1].heights),500)
        self.assertLess(max(routes[0].heights)-min(routes[0].heights),100)
        self.assertGreater(sum(abs(c)<.04 for c in routes[1].curves),
                           sum(abs(c)<.04 for c in routes[0].curves))

    def test_oil_is_visible_and_triggers_live_spin_on_both_new_tracks(self):
        game = Game()
        self.addCleanup(game.audio.stop_engine)
        for track in TRACKS[3:]:
            game.track = track
            game.apply_look()
            game.start_race()
            game.begin_playing()
            self.assertIs(game.minimap.route,game.road.route)
            self.assertEqual(tuple(s.curve for s in game.road.segments),track.build().curves)
            self.assertEqual(len(game.hazards.puddles),5)
            plain, oily = pygame.Surface((800,600)),pygame.Surface((800,600))
            game.road.draw(plain,game.player.z,game.player.x)
            game.road.draw(oily,game.player.z,game.player.x,game.hazards.drawables())
            self.assertNotEqual(pygame.image.tobytes(plain,'RGB'),pygame.image.tobytes(oily,'RGB'))
            oil = game.hazards.puddles[0]
            game.player.z = oil.z-S.CAMERA_HEIGHT*S.CAMERA_DEPTH
            game.player.x = oil.x
            game.update(1/60,{'accelerate':False,'brake':False,'steer':0})
            self.assertTrue(any(isinstance(effect,OilSpinEffect) for effect in game.player.effects))
            self.assertIsNotNone(game.audio.last_played.get('skid'))
            game.render()
