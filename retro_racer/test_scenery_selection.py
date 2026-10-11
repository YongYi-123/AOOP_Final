import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from game import Game
from race import State


class ScenerySelectionTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.addCleanup(self.game.audio.stop_engine)
        self.game.press_enter()
        self.game.press_enter()

    def key(self, key):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))

    def test_arrow_keys_select_scenery_and_track_independently(self):
        game = self.game
        road, field, traffic = game.road, game.manager.field, game.traffic
        ai = game.ai_level
        for i in range(6):
            self.assertEqual(game.theme_index, i)
            self.assertIs(game.road.theme, game.themes.themes[i])
            self.assertIs(game.road, road)
            self.assertIs(game.manager.field, field)
            self.assertIs(game.traffic, traffic)
            self.assertIs(game.ai_level, ai)
            self.key(pygame.K_RIGHT)
        self.assertEqual(game.theme_index, 0)
        self.key(pygame.K_LEFT)
        self.assertEqual(game.theme_index, 5)
        chosen = game.theme
        self.key(pygame.K_DOWN)
        self.assertEqual(game.track_index, 1)
        self.assertIs(game.theme, chosen)
        self.assertIs(game.road.theme, chosen)

    def test_all_scenery_choices_survive_confirmation_and_replay(self):
        game = self.game
        for index, theme in enumerate(game.themes.themes):
            game.state = State.TRACK_SELECT
            game.theme_index = index
            game.theme = theme
            game.apply_look()
            self.key(pygame.K_RETURN)
            self.assertIs(game.selected_theme, theme)
            self.key(pygame.K_RETURN)
            self.assertEqual(game.state, State.COUNTDOWN)
            self.assertIs(game.road.theme, theme)
            game.begin_playing()
            game.player.distance = game.road.length * game.manager.laps
            game.update(1 / 60, {"accelerate": False, "brake": False, "steer": 0})
            self.assertEqual(game.state, State.FINISHED)
            self.key(pygame.K_RETURN)
            self.assertIs(game.road.theme, theme)

    def test_escape_discards_unconfirmed_scenery_and_track(self):
        game = self.game
        theme, track = game.selected_theme, game.selected_track
        self.key(pygame.K_LEFT)
        self.key(pygame.K_DOWN)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(game.state, State.MODE_SELECT)
        self.assertIs(game.road.theme, theme)
        self.assertIs(game.track, track)
        self.key(pygame.K_RETURN)
        self.assertEqual(game.theme_index, game.themes.themes.index(theme))

    def test_gallery_fits_below_track_cards_and_above_existing_footer(self):
        game = self.game
        rects = game.scenery_gallery.thumbnail_rects()
        self.assertEqual(len(rects), 6)
        for rect, theme in zip(rects, game.themes.themes):
            self.assertTrue(game.screen.get_rect().contains(rect.inflate(6, 6)))
            self.assertGreater(rect.top, 400)                      # below the track cards and the info panel
            label = game.hud.small.render(theme.name, False, (255, 255, 255))
            self.assertLess(rect.bottom + 23 + label.get_height() + 2, 524)    # name and LOCKED rows end above the footer
            self.assertLess(label.get_width(), 125)
        for a, b in zip(rects, rects[1:]):
            self.assertFalse(a.inflate(6, 6).colliderect(b.inflate(6, 6)))

    def test_existing_track_card_pixels_remain_unchanged(self):
        game = self.game
        area = pygame.Rect(0, 130, 800, 260)               # title, cards and info panel (the gallery is below)
        with mock.patch("pygame.time.get_ticks", return_value=0):      # the background cars' tyre tread animates by wall time
            with mock.patch.object(game.scenery_gallery, "draw"):
                game.render()
                before = pygame.image.tobytes(game.screen.subsurface(area), "RGB")
            game.render()
        self.assertEqual(pygame.image.tobytes(game.screen.subsurface(area), "RGB"), before)
        self.assertEqual(len(game.scenery_gallery.renderer._previews), 6)
