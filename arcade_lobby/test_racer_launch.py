"""Regression tests drive Enter through the actual lobby frame loop."""
import os
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game import Game
from item_registry import FREE_PLAY_COUPON
from retro_racer_scene import RetroRacerScene
from room_testing import goto_room
from daily_tasks import DailyTask, TaskSpec


class RacerLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = mock.patch.object(RetroRacerScene, "_racer", None)
        self.cache.start()
        self.addCleanup(self.cache.stop)
        self.title = mock.patch.object(RetroRacerScene, "_title_state", None)
        self.title.start()
        self.addCleanup(self.title.stop)
        self.game = Game(save_path=os.path.join(self.temp.name, "profile.json"))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.machine = self.room.machines[0]
        self.room.player.x = float(self.machine.rect.centerx)
        self.room.player.y = float(self.machine.rect.bottom + 12)
        self.frames(5)

    def frames(self, count=1, key=None):
        events = [] if key is None else [pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")]
        for index in range(count):
            self.game.step(events if index == 0 else [], 1 / 60)

    def open_machine(self, key=pygame.K_RETURN):
        self.frames(20, key)
        self.assertIsNotNone(self.room.dialogue)
        self.assertEqual(self.room.dialogue.title, "Retro Racer")

    def launch(self):
        self.open_machine()
        self.frames(40, pygame.K_RETURN)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, RetroRacerScene)
        return scene

    def test_enter_opens_machine_without_charging(self):
        before = self.game.profile.tokens
        self.open_machine()
        self.assertEqual(self.game.profile.tokens, before)

    def test_keypad_enter_and_e_still_interact(self):
        for key in (pygame.K_KP_ENTER, pygame.K_e):
            with self.subTest(key=key):
                self.open_machine(key)
                self.frames(2, pygame.K_ESCAPE)

    def test_enter_loads_actual_racer_and_returns(self):
        before = self.game.profile.tokens
        scene = self.launch()
        self.assertIsNotNone(scene.racer, scene.error)
        self.assertEqual(self.game.profile.tokens, before - 1)
        self.frames(40, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertIsNone(self.room.active_play)
        self.assertEqual(self.game.profile.tickets, 0)

    def test_repeated_enter_never_charges_twice(self):
        before = self.game.profile.tokens
        self.open_machine()
        self.frames(1, pygame.K_RETURN)
        for _ in range(10):
            self.frames(1, pygame.K_RETURN)
        self.frames(40)
        self.assertIsInstance(self.game.scenes.current, RetroRacerScene)
        self.assertEqual(self.game.profile.tokens, before - 1)

    def test_no_tokens_shows_locked_choice(self):
        self.game.profile.spend_tokens(self.game.profile.tokens)
        self.open_machine()
        self.assertIn("LOCKED", self.room.dialogue.options[0])
        self.frames(2, pygame.K_RETURN)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertIsNone(self.room.active_play)

    def test_coupon_starts_with_zero_tokens(self):
        self.game.profile.spend_tokens(self.game.profile.tokens)
        self.game.profile.inventory.add_item(FREE_PLAY_COUPON)
        self.open_machine()
        self.frames(25, pygame.K_RETURN)
        self.assertEqual(self.room.dialogue.title, "COUPON")
        self.frames(40, pygame.K_RETURN)
        self.assertIsInstance(self.game.scenes.current, RetroRacerScene)
        self.assertEqual(self.game.profile.tokens, 0)
        self.assertFalse(self.game.profile.inventory.has_item(FREE_PLAY_COUPON))

    def test_import_failure_shows_error_and_refunds(self):
        before = self.game.profile.tokens
        with mock.patch("retro_racer_scene.load_retro_racer", side_effect=ImportError("test load failure")):
            scene = self.launch()
            self.assertTrue(scene.failed)
            self.assertIsNotNone(scene.error)
            self.frames(40, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(self.game.profile.tokens, before)

    def test_initialization_failure_cannot_render_broken_racer(self):
        with mock.patch("retro_racer_scene.load_retro_racer") as loader:
            loader.return_value = (SimpleNamespace(Game=mock.Mock(side_effect=RuntimeError("test init failure"))),
                                   SimpleNamespace(State=SimpleNamespace(TITLE="title")))
            scene = self.launch()
            self.assertTrue(scene.failed)
            self.assertIsNone(scene.racer)

    def test_partial_restart_failure_clears_cache_and_allows_return(self):
        before = self.game.profile.tokens
        broken = mock.Mock()
        broken.reset.side_effect = RuntimeError("test reset failure")
        with mock.patch("retro_racer_scene.load_retro_racer", return_value=(
                SimpleNamespace(Game=lambda **kwargs: broken),
                SimpleNamespace(State=SimpleNamespace(TITLE="title")))):
            scene = self.launch()
            self.assertTrue(scene.failed)
            self.assertEqual(scene.error_kind, "RUNTIMEERROR")
            self.assertIsNone(scene.racer)
            broken.render.assert_not_called()
            self.frames(40, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(self.game.profile.tokens, before)

    def test_actual_finish_returns_reward_and_high_score(self):
        scene = self.launch()
        r = scene.racer
        for _ in range(4):
            self.frames(1, pygame.K_RETURN)
        self.assertEqual(r.state.value, "COUNTDOWN")
        r.begin_playing()
        r.player.score = 3000
        r.player.distance = r.road.length * r.manager.laps
        self.frames()
        expected = scene.results.outcome
        self.assertEqual(expected.status, "completed")
        self.frames(1, pygame.K_BACKSPACE)
        self.frames(1, pygame.K_ESCAPE)
        self.frames(40, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(self.game.profile.tickets, expected.tickets)
        self.assertEqual(self.game.profile.high_score("retro_racer"), expected.score)

    def test_embedded_v_key_reaches_visual_setting(self):
        scene = self.launch()
        r = scene.racer
        settings = r.update.__globals__["S"]
        original = settings.DRIVING_FX_INTENSITY
        self.addCleanup(setattr, settings, "DRIVING_FX_INTENSITY", original)
        self.frames(1, pygame.K_v)
        self.assertNotEqual(settings.DRIVING_FX_INTENSITY, original)
        self.assertEqual(r.drift.intensity, settings.DRIVING_FX_INTENSITY)

    def test_embedded_map_and_mute_keys_remain_independent(self):
        scene = self.launch()
        racer = scene.racer
        muted = racer.audio.muted
        self.frames(1, pygame.K_m)
        self.assertFalse(racer.minimap.visible)
        self.assertEqual(racer.audio.muted, muted)
        self.frames(1, pygame.K_n)
        self.assertNotEqual(racer.audio.muted, muted)
        self.assertFalse(racer.minimap.visible)
        self.frames(1, pygame.K_m)
        self.assertTrue(racer.minimap.visible)

    def test_scenery_thumbnails_select_from_lobby_and_settle_normally(self):
        scene = self.launch()
        racer = scene.racer
        for _ in range(2):
            self.frames(1, pygame.K_RETURN)
        route = racer.road.route
        for index, theme in enumerate(racer.themes.themes):
            self.assertEqual(racer.theme_index, index)
            self.assertIs(racer.road.theme, theme)
            self.assertIs(racer.road.route, route)
            self.frames(1, pygame.K_RIGHT)
        self.assertEqual(len(racer.scenery_gallery.renderer._previews), 6)
        self.frames(1, pygame.K_LEFT)
        chosen = racer.theme
        self.assertEqual(chosen.key, "forest")
        self.frames(1, pygame.K_RETURN)
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(racer.state.value, "COUNTDOWN")
        self.assertIs(racer.road.theme, chosen)
        racer.begin_playing()
        racer.player.score = 2500
        racer.player.distance = racer.road.length * racer.manager.laps
        self.frames()
        expected = scene.results.outcome
        self.assertEqual(expected.status, "completed")
        self.frames(1, pygame.K_BACKSPACE)
        self.frames(1, pygame.K_ESCAPE)
        self.frames(40, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(self.game.profile.tickets, expected.tickets)
        self.assertEqual(self.game.profile.high_score("retro_racer"), expected.score)

    def test_all_original_tracks_settle_once_and_record_daily_score(self):
        task = DailyTask(TaskSpec("racer_best", "Racer best", "high_score", 1, 1,
                                  game_id="retro_racer"))
        self.game.profile._tasks.tasks = [task]
        scene = self.launch()
        racer = scene.racer
        for _ in range(2):
            self.frames(1, pygame.K_RETURN)
        for index, track in enumerate(racer.tracks):
            if index:
                self.frames(1, pygame.K_BACKSPACE)
                self.frames(1, pygame.K_RETURN)
            self.assertEqual(racer.state.value, "TRACK_SELECT")
            if index:
                self.frames(1, pygame.K_DOWN)
            self.assertIs(racer.track, track)
            self.frames(1, pygame.K_RETURN)
            self.frames(1, pygame.K_RETURN)
            self.assertEqual(racer.state.value, "COUNTDOWN")
            racer.begin_playing()
            racer.player.score = 3000 + index * 1000
            racer.player.distance = racer.road.length * racer.manager.laps
            self.frames()
            self.assertEqual(scene.results.outcome.status, "completed")
            self.assertIs(racer.minimap.route, racer.road.route)
        expected = scene.results.outcome
        self.frames(1, pygame.K_BACKSPACE)
        self.frames(1, pygame.K_ESCAPE)
        self.frames(40, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
        tickets = self.game.profile.tickets
        self.assertEqual(tickets, expected.tickets)
        self.assertEqual(self.game.profile.high_score("retro_racer"), expected.score)
        self.assertEqual(task.progress, 1)
        self.frames(10)
        self.assertEqual(self.game.profile.tickets, tickets)
