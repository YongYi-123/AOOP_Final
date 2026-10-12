"""Tests for the AUDIO SETTINGS screen (F4), the AUDIO DEBUG HUD (F10) and the scene-transition audio matrix.

Real mixer on SDL's dummy driver. Run from this folder:  python -m unittest test_audio_settings -v
"""
import json
import os
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
from audio_settings_ui import (ROWS, STEP, AudioSettingsScene, debug_lines,  # noqa: E402
                               draw_debug_hud)
from chance_scene import ChanceGameScene  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from neon21_scene import Neon21Scene  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from retro_racer_scene import ENGINE_BOOST  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402
from test_audio_lifecycle import HubCase  # noqa: E402

DT = 1 / 60


class SettingsScreenTests(HubCase):
    def open(self):
        self.frames(2, pygame.K_F4)
        self.frames(40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, AudioSettingsScene)
        return scene

    def click(self, scene, pos, up=True):
        """A left click at canvas position `pos` (translated to window pixels)."""
        w, h = self.game.screen.get_size()
        px = (pos[0] * w // VIEW_W, pos[1] * h // VIEW_H)
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=px, button=1))
        if up:
            scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=px, button=1))

    def key(self, scene, key):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))

    def saved(self):
        with open(self.prefs) as f:
            return json.load(f)

    def test_f4_opens_and_closes_without_touching_the_music(self):
        self.frames(5)
        starts, theme = self.audio.music_starts, self.audio.theme
        room = self.game.scenes.current
        scene = self.open()
        self.assertEqual(self.audio.theme, theme)
        self.assertEqual(self.audio.music_starts, starts)
        self.assertTrue(self.audio.music_playing())
        self.frames(2, pygame.K_F4)
        self.frames(40)
        self.assertIs(self.game.scenes.current, room)
        self.assertEqual(self.audio.music_starts, starts)
        self.frames(2, pygame.K_F4)
        self.frames(40)
        self.frames(2, pygame.K_ESCAPE)
        self.frames(40)
        self.assertIs(self.game.scenes.current, room)

    def test_keyboard_sliders_apply_immediately_and_persist(self):
        scene = self.open()
        before = self.audio.bgm_volume
        self.key(scene, pygame.K_LEFT)
        self.assertAlmostEqual(self.audio.bgm_volume, before - STEP, places=2)
        self.audio.update(1.0)
        self.assertAlmostEqual(self.audio.channels[self.audio.active].get_volume(), before - STEP, delta=.02)
        self.assertAlmostEqual(self.saved()["music"], before - STEP, places=2)
        self.key(scene, pygame.K_DOWN)
        before_sfx = self.audio.sfx_volume
        self.key(scene, pygame.K_RIGHT)
        self.key(scene, pygame.K_RIGHT)
        self.assertAlmostEqual(self.audio.sfx_volume, before_sfx + 2 * STEP, places=2)
        self.assertAlmostEqual(self.saved()["sfx"], before_sfx + 2 * STEP, places=2)
        for _ in range(40):                                  # sliders stop at the ends
            self.key(scene, pygame.K_RIGHT)
        self.assertEqual(self.audio.sfx_volume, 1.0)

    def test_the_music_and_effects_sliders_are_independent(self):
        scene = self.open()
        music, sfx = self.audio.bgm_volume, self.audio.sfx_volume
        self.key(scene, pygame.K_RIGHT)
        self.assertEqual(self.audio.sfx_volume, sfx)
        self.assertNotEqual(self.audio.bgm_volume, music)

    def test_mouse_click_and_drag_set_a_slider_and_save_once_on_release(self):
        scene = self.open()
        self.frames(2)                                       # (draw: layout is fixed, nothing to rebuild)
        track = scene.slider_rect(0)
        with patch.object(self.audio, "save_prefs", wraps=self.audio.save_prefs) as save:
            self.click(scene, (track.x + track.w // 4, track.centery), up=False)
            self.assertAlmostEqual(self.audio.bgm_volume, .25, delta=.02)
            w, h = self.game.screen.get_size()
            for frac in (.4, .6, .8):
                x = (track.x + int(track.w * frac)) * w // VIEW_W
                scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(x, track.centery * h // VIEW_H),
                                                      rel=(1, 0), buttons=(1, 0, 0)))
            self.assertAlmostEqual(self.audio.bgm_volume, .8, delta=.02)
            self.assertEqual(save.call_count, 0)             # nothing written while dragging
            scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(0, 0), button=1))
            self.assertEqual(save.call_count, 1)
        self.assertAlmostEqual(self.saved()["music"], .8, delta=.02)
        scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(1, 1), rel=(1, 0), buttons=(0, 0, 0)))
        self.assertAlmostEqual(self.audio.bgm_volume, .8, delta=.02)       # not dragging any more

    def test_clicking_the_sfx_track_and_the_mouse_wheel(self):
        scene = self.open()
        track = scene.slider_rect(1)
        self.click(scene, (track.x + track.w, track.centery))
        self.assertEqual(self.audio.sfx_volume, 1.0)
        self.click(scene, (track.x, track.centery))
        self.assertEqual(self.audio.sfx_volume, 0.0)
        scene.row = 0
        before = self.audio.bgm_volume
        scene.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1))
        self.assertAlmostEqual(self.audio.bgm_volume, before + STEP, places=2)

    def test_mute_toggle_by_key_and_by_click_and_it_persists(self):
        scene = self.open()
        scene.row = ROWS.index("MUTE")
        self.key(scene, pygame.K_RETURN)
        self.assertTrue(self.audio.muted)
        self.assertTrue(self.saved()["muted"])
        self.assertEqual(self.audio.channels[self.audio.active].get_volume(), 0)
        self.assertTrue(self.audio.music_playing())          # muted, not stopped
        self.click(scene, scene.row_rect(ROWS.index("MUTE")).center)
        self.assertFalse(self.audio.muted)
        self.assertFalse(self.saved()["muted"])
        self.audio.update(1.0)
        self.assertAlmostEqual(self.audio.channels[self.audio.active].get_volume(), self.audio.bgm_volume, delta=.02)

    def test_the_global_shortcuts_still_work_with_the_screen_open(self):
        self.open()
        before = self.audio.bgm_volume
        self.frames(2, pygame.K_F7)
        self.assertAlmostEqual(self.audio.bgm_volume, min(1, before + .1), places=2)
        self.frames(2, pygame.K_F9)
        self.frames(2, pygame.K_m)
        self.assertTrue(self.audio.muted)

    def test_test_sound_plays_an_effect_but_says_why_when_muted_or_deviceless(self):
        scene = self.open()
        scene.row = ROWS.index("TEST SOUND")
        self.audio.last_effect.clear()
        self.key(scene, pygame.K_RETURN)
        self.assertIn("purchase", self.audio.last_effect)
        self.assertEqual(scene.message, "PLAYING TEST SOUND")
        self.audio.last_effect.clear()
        self.audio.set_muted(True)
        self.key(scene, pygame.K_RETURN)
        self.assertNotIn("purchase", self.audio.last_effect)
        self.assertIn("UNMUTE", scene.message)
        self.audio.enabled = False
        self.key(scene, pygame.K_RETURN)
        self.assertEqual(scene.message, "NO AUDIO DEVICE")

    def test_restore_defaults_resets_volumes_and_mute_and_saves(self):
        scene = self.open()
        self.audio.set_volumes(bgm=.1, sfx=.2)
        self.audio.set_muted(True)
        scene.row = ROWS.index("RESTORE DEFAULTS")
        self.key(scene, pygame.K_RETURN)
        self.assertEqual((self.audio.bgm_volume, self.audio.sfx_volume, self.audio.muted),
                         (am.DEFAULT_BGM, am.DEFAULT_SFX, False))
        self.assertEqual(self.saved(), {"music": am.DEFAULT_BGM, "sfx": am.DEFAULT_SFX, "muted": False})

    def test_back_button_and_keyboard_navigation_wrap(self):
        room = self.game.scenes.current
        scene = self.open()
        self.key(scene, pygame.K_UP)
        self.assertEqual(scene.row, len(ROWS) - 1)
        self.key(scene, pygame.K_DOWN)
        self.assertEqual(scene.row, 0)
        scene.row = ROWS.index("BACK")
        self.key(scene, pygame.K_e)
        self.frames(40)
        self.assertIs(self.game.scenes.current, room)

    def test_changes_made_in_the_screen_survive_a_restart(self):
        scene = self.open()
        self.key(scene, pygame.K_LEFT)
        self.key(scene, pygame.K_LEFT)
        scene.row = ROWS.index("MUTE")
        self.key(scene, pygame.K_RETURN)
        want = (self.audio.bgm_volume, self.audio.sfx_volume, True)
        again = Game(session=LocalSession([PlayerProfile(profile_id="again")]), audio_prefs=self.prefs)
        self.addCleanup(again.quit)
        self.assertEqual((again.audio.bgm_volume, again.audio.sfx_volume, again.audio.muted), want)

    def test_it_draws_every_state(self):
        scene = self.open()
        for row in range(len(ROWS)):
            scene.row = row
            self.frames(2)
        self.audio.set_muted(True)
        self.frames(2)
        self.audio.enabled = False
        self.frames(2)

    def test_opening_it_silences_a_racing_engine_and_the_music_continues(self):
        scene, room = self.start_game("retro_racer")
        self.settle()
        for _ in range(10):
            scene.racer.audio.engine(.7, True)
        self.assertTrue(pygame.mixer.Channel(0).get_busy() or pygame.mixer.Channel(1).get_busy())
        self.frames(2, pygame.K_F4)
        self.frames(60)
        self.assertIsInstance(self.game.scenes.current, AudioSettingsScene)
        self.assertEqual(self.audio.theme, "retro_racer")
        self.assertTrue(self.audio.music_playing())
        self.assertAlmostEqual(self.audio.channels[self.audio.active].get_volume(), self.audio.bgm_volume, delta=.02)


class DebugHudTests(HubCase):
    def test_it_is_off_by_default_and_f10_toggles_it_without_pausing(self):
        self.assertFalse(self.game.audio_hud)
        room = self.game.scenes.current
        t0 = room.time if hasattr(room, "time") else None
        self.frames(2, pygame.K_F10)
        self.assertTrue(self.game.audio_hud)
        self.frames(30)
        if t0 is not None:
            self.assertGreater(room.time, t0)                # the game kept running
        self.assertIs(self.game.scenes.current, room)
        self.frames(2, pygame.K_F10)
        self.assertFalse(self.game.audio_hud)

    def test_it_shows_the_audio_state(self):
        self.frames(60)
        text = "\n".join(debug_lines(self.game))
        for needle in ("SCENE", "HomeRoom", "PLAYING", "STEADY", "MUSIC 50", "SFX 70", "ON", "MIXER", "SFX    0 PLAYING"):
            self.assertIn(needle, text)
        self.audio.set_muted(True)
        self.assertIn("MUTED", "\n".join(debug_lines(self.game)))
        self.audio.set_muted(False)
        self.audio.switch("lobby")
        self.assertIn("CROSSFADING", "\n".join(debug_lines(self.game)))
        self.audio.update(1.0)
        self.assertIn("STEADY", "\n".join(debug_lines(self.game)))

    def test_it_lists_playing_effect_channels(self):
        self.audio.play("purchase")
        self.assertRegex("\n".join(debug_lines(self.game)), r"SFX    [1-9] PLAYING  CH [4-9]")
        self.assertTrue(all(i >= am.SCENE_SFX[0] for i in self.audio.sfx_busy()))

    def test_it_shows_the_racer_engine_only_while_racing(self):
        self.assertNotIn("ENGINE", "\n".join(debug_lines(self.game)))
        scene, room = self.start_game("retro_racer")
        for _ in range(10):
            scene.racer.audio.engine(.7, True)
        text = "\n".join(debug_lines(self.game))
        self.assertIn("ENGINE RUNNING", text)
        self.assertIn(f"BOOST {ENGINE_BOOST:.1f}", text)
        self.assertIn("racer", text.lower())
        scene.racer.audio.stop_all()
        self.assertIn("ENGINE OFF", "\n".join(debug_lines(self.game)))

    def test_it_reports_errors_and_restarts(self):
        self.audio.last_error = "play effect 'x': boom"
        self.audio.recoveries = 2
        self.assertIn("2 RESTARTS", "\n".join(debug_lines(self.game)))

    def test_it_draws_over_the_frame_and_stays_small(self):
        self.game.audio_hud = True
        self.frames(3)
        surf = pygame.Surface(self.game.screen.get_size())
        surf.fill((0, 0, 0))
        draw_debug_hud(self.game, surf)
        w, h = surf.get_size()
        lit = lambda x, y: surf.get_at((x, y))[:3] != (0, 0, 0)       # noqa: E731
        self.assertFalse(lit(0, 0))                                  # a small margin, top-left
        self.assertTrue(lit(6, 6))
        right = max(x for x in range(0, w, 2) if lit(x, 8))
        bottom = max(y for y in range(0, h, 2) if lit(8, y))
        self.assertLess(right, w * .55)
        self.assertLess(bottom, h * .35)
        self.assertFalse(lit(w - 4, h - 4))                          # the bottom HUD is left alone

    def test_busy_corners_are_avoided(self):
        from retro_racer_scene import RetroRacerScene
        self.assertEqual(RetroRacerScene.audio_hud_anchor, "midleft")       # the racer's stats own the top-left
        self.assertEqual(AudioSettingsScene.audio_hud_anchor, "bottomleft")
        scene, room = self.start_game("retro_racer")
        surf = pygame.Surface(self.game.screen.get_size())
        surf.fill((0, 0, 0))
        draw_debug_hud(self.game, surf)
        w, h = surf.get_size()
        self.assertFalse(any(surf.get_at((x, y))[:3] != (0, 0, 0) for x in range(0, w // 2, 6) for y in range(0, h // 4, 6)))

    def test_it_is_cheap(self):
        import time
        surf = pygame.Surface(self.game.screen.get_size())
        t = time.perf_counter()
        for _ in range(60):
            draw_debug_hud(self.game, surf)
        self.assertLess((time.perf_counter() - t) / 60, 0.01)   # well under a frame (16 ms)


class NoDeviceTests(unittest.TestCase):
    def make_game(self):
        with patch.object(pygame.mixer, "get_init", return_value=None), \
                patch.object(pygame.mixer, "init", side_effect=pygame.error("no device")):
            game = Game(session=LocalSession([PlayerProfile(profile_id="quiet")]))
        self.addCleanup(game.quit)
        return game

    def test_hud_and_settings_screen_work_without_an_audio_device(self):
        game = self.make_game()
        self.assertFalse(game.audio.enabled)
        goto_room(game, "arcade_floor")
        with patch.object(pygame.mixer, "get_init", return_value=None):
            for key in (pygame.K_F10, pygame.K_F4):
                game.step([pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")], DT)
                for _ in range(40):
                    game.step([], DT)
            self.assertIsInstance(game.scenes.current, AudioSettingsScene)
            text = "\n".join(debug_lines(game))
            self.assertIn("UNAVAILABLE", text)
            self.assertIn("no device", text)
            scene = game.scenes.current
            for key in (pygame.K_LEFT, pygame.K_DOWN, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_RETURN, pygame.K_DOWN,
                        pygame.K_RETURN):
                scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
            game.step([], DT)
            self.assertEqual(game.audio.sfx_busy(), [])
            game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F4, mod=0, unicode="")], DT)


class TransitionMatrixTests(HubCase):
    """The five transitions the arcade is used through, with music, effects, duplicates, volume and mute checked."""

    def check_back_to(self, theme, volume, muted):
        self.frames(90)                                      # the crossfade is done
        time.sleep(.6)                                       # the longest effect is 0.55 s of real audio
        self.assert_only(theme)
        self.assertTrue(self.audio.music_playing())
        self.assertEqual(self.audio.sfx_busy(), [], "an effect is still playing")
        self.assertEqual(sum(c.get_busy() for c in self.audio.channels), 1, "more than one music track is playing")
        self.assertEqual((self.audio.bgm_volume, self.audio.muted), (volume, muted))
        level = self.audio.channels[self.audio.active].get_volume()
        self.assertAlmostEqual(level, 0 if muted else volume, delta=.02)

    def run_matrix(self, muted):
        self.audio.set_volumes(bgm=.4)
        self.audio.set_muted(muted)
        for game_id in ("retro_racer", "pixel_volleyball", "galaxy_defender"):         # Arcade Floor -> game -> Arcade Floor
            scene, room = self.start_game(game_id)
            self.frames(60)
            self.assertEqual(self.audio.theme, game_id)
            self.assertEqual(sum(c.get_busy() for c in self.audio.channels), 1)
            if game_id == "retro_racer":
                scene.racer.audio.engine(.7, True)
            self.leave(room)
            self.check_back_to("lobby", .4, muted)
            self.assertFalse(any(pygame.mixer.Channel(i).get_busy() for i in (0, 1)), "engine left running")
        goto_room(self.game, "prize_plaza")                                          # Prize Plaza -> Home -> Prize Plaza
        self.check_back_to("prize_plaza", .4, muted)
        goto_room(self.game, "home")
        self.check_back_to("home", .4, muted)
        goto_room(self.game, "prize_plaza")
        self.check_back_to("prize_plaza", .4, muted)
        pl = self.game.session.players[0]                                            # Lucky Corner -> NEON 21 -> back
        self.game.scenes.push(Neon21Scene(self.game, pl))
        self.frames(60)
        self.assertEqual(self.audio.theme, "neon21")
        self.audio.play("card")
        self.game.scenes.pop()
        self.frames(40)
        self.check_back_to("prize_plaza", .4, muted)

    def test_every_transition_with_sound_on(self):
        self.run_matrix(False)

    def test_every_transition_while_muted_stays_muted_and_keeps_playing(self):
        self.run_matrix(True)

    def test_engine_boost_stays_in_a_comfortable_range(self):
        self.assertTrue(1.0 <= ENGINE_BOOST <= 1.4)


if __name__ == "__main__":
    unittest.main()
