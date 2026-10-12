"""Tests for the music / sound-effect system: shipped assets, preferences, mute,
music transitions and graceful behaviour without an audio device.

Run headless from this folder:   python -m unittest test_audio_system -v
"""
import json
import math
import os
import shutil
import struct
import tempfile
import unittest
import unittest.mock
import wave
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
from audio_manager import AudioManager  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from room_testing import goto_room  # noqa: E402
from wardrobe_ui import WardrobeScene  # noqa: E402

DT = 1 / 60


def read_wav(path):
    with wave.open(path) as w:
        n = w.getnframes()
        return w.getframerate(), struct.unpack(f"<{n}h", w.readframes(n))


class AssetTests(unittest.TestCase):
    def test_every_theme_has_a_real_loop_of_music(self):
        for theme, name in am.MUSIC_FILES.items():
            rate, data = read_wav(os.path.join(am.ASSET_DIR, "music", f"{name}.wav"))
            self.assertGreaterEqual(len(data) / rate, 20, name)
            rms = math.sqrt(sum(x * x for x in data) / len(data)) / 32767
            self.assertTrue(0.05 < rms < 0.4, (name, rms))
            self.assertLess(max(map(abs, data)) / 32767, 0.95, name)              # no clipping
            self.assertLess(abs(data[0] - data[-1]) / 32767, 0.15, name)           # loops without a click

    def test_every_theme_is_different_music(self):
        starts = {read_wav(os.path.join(am.ASSET_DIR, "music", f"{n}.wav"))[1][:4000] for n in am.MUSIC_FILES.values()}
        self.assertEqual(len(starts), len(am.MUSIC_FILES))
        self.assertEqual(len(am.MUSIC_FILES), 11)           # 4 rooms + 7 minigames

    def test_every_effect_file_exists_and_is_short_and_quiet(self):
        for name in am.SFX_FILES:
            rate, data = read_wav(os.path.join(am.ASSET_DIR, "sfx", f"{name}.wav"))
            self.assertLess(len(data) / rate, 0.8, name)
            self.assertLess(max(map(abs, data)) / 32767, 0.7, name)
            self.assertLess(abs(data[-1]) / 32767, 0.01, name)                    # fades out: no click

    def test_footsteps_are_much_quieter_than_confirm_beeps(self):
        self.assertLess(am.SFX_GAIN["footstep"], am.SFX_GAIN["confirm"])
        self.assertGreaterEqual(am.MIN_GAP["footstep"], .1)                       # never a machine-gun of steps


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "sub", "audio.json")

    def test_volumes_and_mute_are_saved_and_loaded(self):
        a = AudioManager(prefs_path=self.path)
        a.set_volumes(bgm=.4, sfx=.15)
        a.set_muted(True)
        b = AudioManager(prefs_path=self.path)
        self.assertAlmostEqual(b.bgm_volume, .4)
        self.assertAlmostEqual(b.sfx_volume, .15)
        self.assertTrue(b.muted)

    def test_music_and_effects_volumes_are_independent(self):
        a = AudioManager(prefs_path=self.path)
        a.set_volumes(bgm=0)
        self.assertEqual(a.sfx_volume, am.DEFAULT_SFX)
        a.set_volumes(sfx=1)
        self.assertEqual(a.bgm_volume, 0)

    def test_missing_or_damaged_files_give_defaults(self):
        self.assertEqual(AudioManager(prefs_path=self.path).bgm_volume, am.DEFAULT_BGM)
        os.makedirs(os.path.dirname(self.path))
        for bad in ("{not json", "[1, 2]", json.dumps({"music": "loud", "sfx": 7, "muted": "yes"})):
            with open(self.path, "w") as f:
                f.write(bad)
            a = AudioManager(prefs_path=self.path)
            self.assertEqual((a.bgm_volume, a.sfx_volume, a.muted), (am.DEFAULT_BGM, am.DEFAULT_SFX, False))

    def test_no_prefs_path_never_writes(self):
        a = AudioManager()
        a.set_volumes(bgm=.5)
        self.assertFalse(a.save_prefs())

    def test_an_unwritable_prefs_location_does_not_raise(self):
        a = AudioManager(prefs_path=os.path.join(self.dir, "file", "audio.json"))
        open(os.path.join(self.dir, "file"), "w").close()                        # a FILE where a folder is needed
        a.set_volumes(bgm=.3)
        self.assertAlmostEqual(a.bgm_volume, .3)


class NoDeviceTests(unittest.TestCase):
    def make(self):
        with patch.object(pygame.mixer, "get_init", return_value=None), \
                patch.object(pygame.mixer, "init", side_effect=pygame.error("no device")):
            return AudioManager()

    def test_everything_is_a_quiet_no_op(self):
        a = self.make()
        self.assertFalse(a.enabled)
        a.switch("home")
        a.switch(None)
        a.play("footstep")
        a.set_volumes(bgm=.1, sfx=.2)
        a.toggle_mute()
        a.update(.1)
        a.stop()
        self.assertEqual(a.theme, "home")                    # the wish is remembered: it plays if a device appears

    def test_a_mixer_that_fails_later_is_logged_and_recovers_without_raising(self):
        pygame.mixer.init()
        a = AudioManager()
        a.switch("lobby")

        class Broken:
            def get_busy(self):
                return False

            def fadeout(self, ms):
                raise pygame.error("device lost")

            set_volume = play = stop = fadeout
        good = a.channels
        a.channels = [Broken(), Broken()]
        with self.assertLogs("arcade.audio", "ERROR"):
            a.switch("home")
        self.assertTrue(a.enabled)                           # one failed call never switches audio off for good
        self.assertIn("device lost", a.last_error)
        a.channels = good
        for _ in range(60):                                  # the watchdog brings the music back
            a.update(.02)
        self.assertTrue(a.music_playing())
        a.play("confirm")

    def test_missing_asset_files_fall_back_to_synthesized_sound(self):
        pygame.mixer.init()
        a = AudioManager(asset_dir=os.path.join(tempfile.gettempdir(), "no-such-assets"))
        self.addCleanup(a.stop)
        a.switch("home")
        self.assertTrue(a.channels[a.active].get_busy())
        a.play("confirm")
        self.assertIn("confirm", a.last_effect)
        a.play("footstep")                                   # no synth fallback for it: silently skipped
        self.assertNotIn("footstep", a.last_effect)

    def test_the_game_runs_with_no_audio_device(self):
        with patch.object(pygame.mixer, "get_init", return_value=None), \
                patch.object(pygame.mixer, "init", side_effect=pygame.error("no device")):
            game = Game(session=LocalSession([PlayerProfile(profile_id="quiet")]))
        self.addCleanup(game.quit)
        room = goto_room(game, "arcade_floor")
        for _ in range(30):
            game.step([], DT)
        game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0, unicode="m")], DT)
        game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F7, mod=0, unicode="")], DT)
        for _ in range(5):
            game.step([], DT)
        self.assertFalse(game.audio.enabled)
        self.assertIs(game.scenes.current, room)


class MusicTransitionTests(unittest.TestCase):
    def setUp(self):
        pygame.mixer.init()
        self.a = AudioManager()
        self.addCleanup(self.a.stop)

    def test_each_room_theme_plays_a_looping_track(self):
        for theme in ("lobby", "prize_plaza", "lucky_corner", "home"):
            self.a.switch(theme)
            self.assertEqual(self.a.theme, theme)
            self.assertTrue(self.a.channels[self.a.active].get_busy())
            self.assertIsNotNone(self.a.music[theme])

    def test_the_same_theme_does_not_restart_and_none_keeps_it(self):
        self.a.switch("home")
        starts, channel = self.a.music_starts, self.a.active
        for _ in range(10):
            self.a.switch("home")
            self.a.switch(None)
        self.assertEqual((self.a.music_starts, self.a.active, self.a.theme), (starts, channel, "home"))

    def test_changing_theme_crossfades_onto_the_other_channel(self):
        self.a.switch("lobby")
        first = self.a.active
        self.a.switch("prize_plaza")
        self.assertNotEqual(self.a.active, first)
        self.assertEqual(self.a.music_starts, 2)

    def test_mute_silences_music_and_effects_and_unmute_restores(self):
        self.a.switch("lobby")
        self.a.update(1.0)                                   # the crossfade has finished
        self.a.set_muted(True)
        self.assertEqual(self.a.channels[self.a.active].get_volume(), 0)
        self.a.play("confirm")
        self.assertNotIn("confirm", self.a.last_effect)
        self.assertEqual(self.a.effective_sfx, 0)
        self.a.set_muted(False)
        self.assertAlmostEqual(self.a.channels[self.a.active].get_volume(), self.a.bgm_volume, places=1)
        self.a.play("confirm")
        self.assertIn("confirm", self.a.last_effect)

    def test_a_track_started_while_muted_stays_silent(self):
        self.a.set_muted(True)
        self.a.switch("home")
        self.assertEqual(self.a.channels[self.a.active].get_volume(), 0)

    def test_repeat_effects_are_rate_limited(self):
        self.a.play("footstep")
        first = self.a.last_effect["footstep"]
        self.a.update(.05)
        self.a.play("footstep")
        self.assertEqual(self.a.last_effect["footstep"], first)
        self.a.update(.2)
        self.a.play("footstep")
        self.assertGreater(self.a.last_effect["footstep"], first)


class GameMusicTests(unittest.TestCase):
    def setUp(self):
        self.prefs = os.path.join(tempfile.mkdtemp(), "audio.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(self.prefs), True)
        self.profile = PlayerProfile(profile_id="m", tickets=200, tokens=20)
        self.game = Game(session=LocalSession([self.profile]), audio_prefs=self.prefs)
        self.addCleanup(self.game.quit)

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k, n=1):
        self.game.step([pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")], DT)
        self.frames(n - 1)

    def test_each_room_has_its_own_music(self):
        for room_id, theme in (("arcade_floor", "lobby"), ("prize_plaza", "prize_plaza"), ("home", "home")):
            goto_room(self.game, room_id)
            self.frames(5)
            self.assertEqual(self.game.audio.theme, theme)

    def test_opening_menus_does_not_restart_the_music(self):
        room = goto_room(self.game, "home")
        self.frames(20)
        starts = self.game.audio.music_starts
        theme = self.game.audio.theme
        from cosmetics import SLOTS
        from stations import Station
        owner = self.game.session.players[0]
        for scene in (WardrobeScene(self.game, owner),):
            self.game.scenes.push(scene)
            self.frames(60)
            self.assertEqual(self.game.audio.theme, theme)
            self.game.scenes.pop()
            self.frames(60)
        self.assertEqual(self.game.audio.music_starts, starts)

    def test_lucky_corner_games_get_their_own_music_and_return_to_the_room_track(self):
        from chance_scene import ChanceGameScene
        from lucky_wheel import LuckyWheelGame
        room = goto_room(self.game, "prize_plaza")
        self.frames(20)
        self.game.scenes.push(ChanceGameScene(self.game, LuckyWheelGame, self.game.session.players[0]))
        self.frames(60)
        self.assertEqual(self.game.audio.theme, "lucky_wheel")          # SPIN has its own theme now
        self.game.scenes.pop()
        self.frames(60)
        self.assertEqual(self.game.audio.theme, "prize_plaza")

    def test_minigame_themes_are_unchanged(self):
        room = goto_room(self.game, "arcade_floor")
        machine = next(m for m in room.machines if m.id == "pixel_volleyball")
        room._start_game(machine, player=room.players[0])
        self.frames(40)
        self.assertEqual(self.game.audio.theme, "pixel_volleyball")

    def test_m_toggles_mute_and_the_preference_is_saved(self):
        self.key(pygame.K_m)
        self.assertTrue(self.game.audio.muted)
        with open(self.prefs) as f:
            self.assertEqual(json.load(f)["muted"], True)
        self.key(pygame.K_m)
        self.assertFalse(self.game.audio.muted)

    def test_volume_keys_save_and_next_launch_restores_them(self):
        self.key(pygame.K_F6)
        self.key(pygame.K_F9)
        bgm, sfx = self.game.audio.bgm_volume, self.game.audio.sfx_volume
        again = Game(session=LocalSession([PlayerProfile(profile_id="m2")]), audio_prefs=self.prefs)
        self.addCleanup(again.quit)
        self.assertAlmostEqual(again.audio.bgm_volume, bgm)
        self.assertAlmostEqual(again.audio.sfx_volume, sfx)

    def test_the_volume_readout_draws(self):
        self.key(pygame.K_F6, 3)
        self.assertGreater(self.game.volume_toast, 0)



class DiagnosticsTests(unittest.TestCase):
    def test_default_music_volume_is_comfortably_audible(self):
        self.assertGreaterEqual(am.DEFAULT_BGM, .4)

    def test_status_reports_the_state_that_explains_silence(self):
        a = AudioManager()
        a.switch("home")
        st = a.status()
        self.assertTrue(st["enabled"] and st["music_playing"])
        self.assertEqual((st["theme"], st["missing_music"], st["missing_sfx"]), ("home", [], []))
        a.set_muted(True)
        st = a.status()
        self.assertEqual((st["muted"], st["effective_music"], st["effective_sfx"]), (True, 0, 0))
        self.assertTrue(AudioManager(asset_dir=os.path.join(tempfile.gettempdir(), "nope")).status()["missing_music"])

    def test_a_failed_start_is_logged_and_recorded_not_swallowed(self):
        with patch("pygame.mixer.get_init", return_value=None), \
                patch("pygame.mixer.init", side_effect=pygame.error("libpulse.so.0 missing")):
            with self.assertLogs("arcade.audio", "WARNING") as logs:
                a = AudioManager()
        self.assertFalse(a.enabled)
        self.assertIn("libpulse", a.init_error)
        self.assertIn("apt install libpulse0", logs.output[0])

    def test_music_chosen_before_the_device_works_starts_after_a_retry(self):
        with patch("pygame.mixer.get_init", return_value=None), \
                patch("pygame.mixer.init", side_effect=pygame.error("no device")), self.assertLogs("arcade.audio"):
            a = AudioManager()
        a.switch("prize_plaza")
        self.assertFalse(a.music_playing())
        pygame.mixer.init()
        self.assertTrue(a.init_mixer())
        self.assertTrue(a.music_playing())
        self.assertEqual(a.theme, "prize_plaza")

    def test_a_playback_error_is_logged_and_kept(self):
        a = AudioManager()
        with patch.object(a, "_play_on_scene_channel", side_effect=pygame.error("boom")), \
                self.assertLogs("arcade.audio", "ERROR"):
            a.play("confirm")
        self.assertIn("boom", a.last_error)

    def test_test_tone_plays_even_when_muted_and_diagnostics_runs(self):
        a = AudioManager()
        a.set_muted(True)
        self.assertTrue(a.test_tone(.1))
        import audio_diagnostics
        with patch("audio_diagnostics.AudioManager", lambda prefs_path=None: a):
            self.assertEqual(audio_diagnostics.main(["--silent"]), 1)       # reports "muted" as a problem

    def test_mochi_meow_goes_through_the_shared_audio_system(self):
        game = Game(session=LocalSession([PlayerProfile(profile_id="mo")]))
        self.addCleanup(game.quit)
        room = goto_room(game, "prize_plaza")
        game.audio.play = unittest.mock.Mock()
        room.mochi.sound("meow")
        game.audio.play.assert_called_with("meow")
        self.assertIn("meow", am.SFX_FILES)

    def test_muted_or_missing_audio_shows_a_badge(self):
        game = Game(session=LocalSession([PlayerProfile(profile_id="bd")]))
        self.addCleanup(game.quit)
        game.audio.set_muted(True)
        before = pygame.image.tostring(game.screen, "RGB")
        game.step([], DT)
        game.step([], DT)
        self.assertNotEqual(before, pygame.image.tostring(game.screen, "RGB"))


if __name__ == "__main__":
    unittest.main()
