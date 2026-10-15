"""Regression tests for audio-device liveness: the mixer reporting "playing" while the sound device (e.g. WSLg's
PulseAudio sink) has stopped consuming samples, recovery by reopening the stream, the diagnostics that show it,
and proof that the recovery is not an aggressive watchdog.

Root cause being guarded (found on WSL2/WSLg): the PulseAudio stream SDL opens stops being consumed after a few tens
of seconds. pygame's mixer keeps saying "busy / playing", every state check in AudioManager passed, and the music was
silent for good. A 40 ms silent probe that never finishes exposes it, and reopening the mixer gets a live stream.

Run from this folder:  python -m unittest test_audio_device -v
"""
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
from audio_manager import AudioManager  # noqa: E402
from audio_settings_ui import debug_lines  # noqa: E402
from display import DisplayManager, DisplaySettings  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from room_testing import goto_room  # noqa: E402
from test_audio_lifecycle import HubCase  # noqa: E402

DT = 1 / 60


class FakeDevice:
    """A sound device whose probe channel never finishes until the mixer has been reopened `fix_after` times."""

    def __init__(self, audio, fix_after=1):
        self.audio, self.fix_after, self.plays = audio, fix_after, 0
        self.base = audio.reopens

    def play(self, sound):
        self.plays += 1

    def get_busy(self):
        return self.audio.reopens - self.base < self.fix_after

    def stop(self):
        pass


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, seconds, audio, step=0.25):
        end = self.t + seconds
        while self.t < end:
            self.t += step
            audio.update(step)


def make_audio(**kw):
    pygame.mixer.init()
    return AudioManager(**kw)                    # (the real clock; tests that simulate time install a Clock + FakeDevice)


class StallRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.a = make_audio()
        self.addCleanup(self.a.stop)

    def stall(self, fix_after=1):
        self.a.clock = Clock()                                         # simulated time needs a simulated device too
        self.a.probe_started, self.a.next_probe = None, 0.0
        device = FakeDevice(self.a, fix_after)
        patcher = patch.object(AudioManager, "_probe_channel", lambda s: device)
        patcher.start()
        self.addCleanup(patcher.stop)
        return device

    def test_a_stalled_device_is_detected_and_the_music_is_brought_back(self):
        """THE regression: before this fix nothing noticed - music_playing() stayed True and no recovery ever ran."""
        a = self.a
        a.switch("lobby")
        a.update(1.0)
        self.assertTrue(a.music_playing())
        self.stall()
        a.update(0.0)
        with self.assertLogs("arcade.audio", "WARNING") as logs:
            a.clock.advance(am.PROBE_EVERY + am.PROBE_STALL + 1.0, a)
        text = "\n".join(logs.output)
        self.assertIn("AUDIO DEVICE STALLED", text)
        self.assertIn("reopening the mixer", text)
        self.assertEqual(a.device_stalls, 1)
        self.assertEqual(a.reopens, 1)
        a.update(1.0)
        self.assertIsNotNone(pygame.mixer.get_init())
        self.assertTrue(a.enabled and a.music_playing())
        self.assertEqual(a.theme, "lobby")
        self.assertAlmostEqual(a.channels[a.active].get_volume(), a.bgm_volume, delta=.02)

    def test_a_healthy_device_never_triggers_a_reopen_or_a_music_restart(self):
        a = self.a
        a.switch("home")
        a.update(1.0)
        starts = a.music_starts
        t0 = time.monotonic()
        while time.monotonic() - t0 < 1.0:                             # the real clock, the real (dummy) device
            a.update(.02)
            time.sleep(.02)
        self.assertEqual(a.device_state, "OK")
        self.assertLess(a.probe_ms, 500)
        self.assertEqual((a.reopens, a.device_stalls, a.recoveries, a.music_starts), (0, 0, 0, starts))

    def test_a_late_look_at_a_finished_probe_is_not_a_stall(self):
        """A frozen game loop (dragging the window, a long frame) must not look like a frozen device."""
        a = self.a
        a.switch("home")
        a.update(0.0)                                                  # a probe goes out on the real device
        self.assertIsNotNone(a.probe_started)
        time.sleep(.15)                                                # the device finishes it
        real = a.clock
        a.clock = lambda: real() + 30.0                                # ... and the loop only looks 30 s later
        a.update(.02)
        self.assertEqual((a.device_state, a.device_stalls, a.reopens), ("OK", 0, 0))

    def test_reopening_backs_off_when_it_does_not_help(self):
        a = self.a
        a.switch("lobby")
        a.update(1.0)
        self.stall(fix_after=99)                                      # the device stays dead whatever we do
        with self.assertLogs("arcade.audio", "WARNING"):
            a.clock.advance(300, a)
        # gaps of 6, 12, 24, 48, 60, 60 ... seconds: far fewer than "once per probe" (that would be ~75)
        self.assertLessEqual(a.reopens, 8)
        self.assertGreaterEqual(a.reopens, 3)
        self.assertEqual(a.reopen_gap, am.REOPEN_MAX_GAP)

    def test_a_device_that_stalls_again_and_again_is_reopened_at_most_every_20_seconds(self):
        a = self.a
        a.switch("lobby")
        a.update(1.0)
        device = self.stall(fix_after=1)

        class Flaky(FakeDevice):                                       # every reopen fixes it ... for 8 seconds
            def get_busy(inner):
                return (a.clock.t - getattr(inner, "fixed_at", -99)) > 8.0 if a.reopens else True
        flaky = Flaky(a)
        orig = AudioManager.reopen_mixer

        stamps = []

        def reopen(s, reason):
            flaky.fixed_at = a.clock.t
            stamps.append(a.clock.t)
            return orig(s, reason)
        with patch.object(AudioManager, "_probe_channel", lambda s: flaky), patch.object(AudioManager, "reopen_mixer", reopen):
            with self.assertLogs("arcade.audio", "WARNING") as logs:
                a.clock.advance(180, a)
        self.assertTrue(any("keeps stalling" in line for line in logs.output))
        self.assertGreater(len(stamps), 5)
        late = [b - x for x, b in zip(stamps[3:], stamps[4:])]
        self.assertTrue(late and min(late) >= am.FLAP_GAP - 1, (stamps, late))   # once flapping: never closer than 20 s
        self.assertLess(len(stamps), 14)

    def test_after_a_successful_recovery_the_backoff_resets(self):
        a = self.a
        a.switch("lobby")
        a.update(1.0)
        self.stall(fix_after=1)
        with self.assertLogs("arcade.audio", "WARNING"):
            a.clock.advance(20, a)
        self.assertEqual(a.reopens, 1)
        a.clock.advance(1.0, a)                                        # the (fixed) device answers the next probe
        a.clock.advance(am.PROBE_EVERY + 1.0, a)
        self.assertEqual(a.device_state, "OK")
        self.assertEqual(a.reopen_gap, am.REOPEN_MIN_GAP)

    def test_reopening_keeps_volumes_mute_theme_and_the_sound_caches(self):
        a = self.a
        a.set_volumes(bgm=.33, sfx=.44)
        a.set_muted(True)
        a.switch("prize_plaza")
        a.update(1.0)
        a.preload()
        music, sounds = dict(a.music), dict(a.sounds)
        with self.assertLogs("arcade.audio", "WARNING"):
            self.assertTrue(a.reopen_mixer("test"))
        a.update(1.0)
        self.assertEqual((a.bgm_volume, a.sfx_volume, a.muted, a.theme), (.33, .44, True, "prize_plaza"))
        self.assertEqual(a.channels[a.active].get_volume(), 0)        # still muted, still playing underneath
        self.assertTrue(a.music_playing())
        self.assertTrue(all(a.music[k] is v for k, v in music.items()))
        self.assertTrue(all(a.sounds[k] is v for k, v in sounds.items()))
        a.set_muted(False)
        self.assertAlmostEqual(a.channels[a.active].get_volume(), .33, delta=.02)
        a.time += 1
        a.play("confirm")
        self.assertIn("confirm", a.last_effect)

    def test_if_the_device_cannot_be_reopened_nothing_raises_and_it_is_retried(self):
        a = self.a
        a.switch("lobby")
        real = pygame.mixer.init
        with patch("pygame.mixer.init", side_effect=pygame.error("device gone")), self.assertLogs("arcade.audio", "ERROR"):
            self.assertFalse(a.reopen_mixer("test"))
        self.assertFalse(a.enabled)
        a.play("confirm")
        a.update(.1)                                                  # silent no-ops
        self.assertIn("device gone", a.init_error)
        a.retry_in = 0
        a.update(.1)                                                  # the device is back: the existing retry path
        self.assertTrue(a.enabled)
        a.update(1.0)
        self.assertTrue(a.music_playing())
        self.assertEqual(a.theme, "lobby")

    def test_the_probe_is_silent_tiny_and_never_on_a_music_engine_or_effect_channel(self):
        a = self.a
        self.assertEqual(pygame.mixer.get_num_channels() - 1, 23)
        index = pygame.mixer.get_num_channels() - 1
        self.assertGreater(index, am.SFX_CHANNELS + 10)
        samples = a._probe_sound.get_raw()
        self.assertEqual(set(samples), {0})                           # silence
        self.assertLessEqual(a._probe_sound.get_length(), 0.05)
        a.switch("lobby")
        a.update(1.0)
        a.update(0.0)                                                  # a probe is on the channel right now
        self.assertTrue(pygame.mixer.Channel(index).get_busy())
        self.assertNotIn(index, a.sfx_busy())
        self.assertTrue(pygame.mixer.Channel(2).get_busy() or pygame.mixer.Channel(3).get_busy())

    def test_the_liveness_check_is_cheap(self):
        a = self.a
        a.switch("home")
        a.update(1.0)
        t = time.perf_counter()
        for _ in range(2000):
            a._check_device()
        self.assertLess((time.perf_counter() - t) / 2000, 0.0005)

    def test_real_stall_reopen_cycle_preserves_prefs_on_disk(self):
        path = os.path.join(tempfile.mkdtemp(), "audio.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(path), True)
        a = make_audio(prefs_path=path)
        self.addCleanup(a.stop)
        a.set_volumes(bgm=.25, sfx=.6)
        a.set_muted(False)
        with open(path) as f:
            before = f.read()
        a.switch("home")
        with self.assertLogs("arcade.audio", "WARNING"):
            a.reopen_mixer("test")
        with open(path) as f:
            self.assertEqual(f.read(), before)
        again = AudioManager(prefs_path=path)
        self.assertEqual((again.bgm_volume, again.sfx_volume, again.muted), (.25, .6, False))
        again.stop()


class HudDiagnosticsTests(HubCase):
    def text(self):
        return "\n".join(debug_lines(self.game))

    def test_device_stalled_vs_ok_vs_unavailable(self):
        self.frames(60)
        self.assertRegex(self.text(), r"DEVICE (OK|UNKNOWN)")
        self.audio.device_state = "STALLED"
        self.assertIn("DEVICE STALLED!", self.text())
        with patch("pygame.mixer.get_init", return_value=None):
            self.assertIn("MIXER  UNAVAILABLE", "\n".join(debug_lines(self.game)))

    def test_music_playing_but_muted_is_distinguished_from_silent(self):
        self.frames(60)
        self.audio.set_muted(True)
        self.assertIn("PLAYING (MUTED)", self.text())
        pygame.mixer.stop()
        self.assertIn("SILENT", self.text())

    def test_wrong_track_and_missing_files_and_stuck_fade_and_stopped_engine_are_flagged(self):
        self.frames(60)
        self.audio.theme = "neon21"                                  # while the room wants its own
        self.assertIn("WRONG!", self.text())
        self.audio.theme = "home"
        self.assertNotIn("WRONG!", self.text())
        self.audio.asset_dir = os.path.join(tempfile.gettempdir(), "no-assets")
        self.audio._files = None
        self.assertIn("FILES  MISSING", self.text())
        a = self.audio
        self.audio.asset_dir = am.ASSET_DIR
        a._files = None
        a.mix[a.active] = 0.0
        a.channels[a.active].set_volume(0)
        self.assertTrue(a.fade_stuck())
        self.assertIn("STUCK AT 0!", self.text())

    def test_a_stopped_racer_engine_is_flagged_while_racing(self):
        scene, room = self.start_game("retro_racer")
        racer = scene.racer
        racer.state = type(racer.state)["PLAYING"]
        racer.paused = False
        for i in (0, 1):
            pygame.mixer.Channel(i).stop()
        self.assertIn("ENGINE STOPPED!", self.text())
        racer.audio.engine(.7, True)
        self.assertIn("ENGINE RUNNING", self.text())

    def test_status_counts_are_in_the_status_report(self):
        st = self.audio.status()
        for key in ("device_state", "probe_ms", "device_stalls", "reopens", "fade_stuck"):
            self.assertIn(key, st)


class EngineAfterReopenTests(HubCase):
    def test_the_racer_engine_and_the_hub_music_come_back_after_a_reopen(self):
        scene, room = self.start_game("retro_racer")
        racer = scene.racer
        for _ in range(10):
            racer.audio.engine(.7, True)
        self.settle()
        with self.assertLogs("arcade.audio", "WARNING"):
            self.audio.reopen_mixer("test")
        self.frames(60)
        for _ in range(5):
            self.game.step([], DT)
            racer.audio.engine(.7, True)
        self.assertTrue(all(pygame.mixer.Channel(i).get_busy() for i in (0, 1)), "engine did not restart")
        self.assert_only("retro_racer")
        self.leave(room)
        self.settle()
        self.assert_only("lobby")


class NoDisturbanceTests(HubCase):
    """Display, window and settings activity must never restart audio, reopen the mixer, or leak resources."""

    def test_resize_fullscreen_minimize_f4_and_mute_do_not_touch_playback(self):
        goto_room(self.game, "arcade_floor")
        self.frames(60)
        a = self.audio
        starts, cache, inits = a.music_starts, len(am._SOUND_CACHE), 0
        with patch.object(pygame.mixer, "quit") as quit_, patch.object(pygame.mixer, "init") as init:
            for size in ((1280, 720), (1920, 1080), (640, 480)):
                pygame.display.set_mode(size, pygame.RESIZABLE)
                self.game.step([pygame.event.Event(pygame.VIDEORESIZE, size=size, w=size[0], h=size[1])], DT)
                self.frames(5)
            for key, mod in ((pygame.K_F11, 0), (pygame.K_F11, 0), (pygame.K_RETURN, pygame.KMOD_ALT), (pygame.K_RETURN, pygame.KMOD_ALT)):
                self.game.step([pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode="")], DT)
                self.frames(20)
            self.game.step([pygame.event.Event(pygame.WINDOWMINIMIZED)], DT)
            self.frames(10)
            self.game.step([pygame.event.Event(pygame.WINDOWRESTORED)], DT)
            self.frames(10)
            self.frames(2, pygame.K_F4)
            self.frames(60)
            self.frames(2, pygame.K_F4)
            self.frames(60)
            self.frames(2, pygame.K_m)
            self.frames(2, pygame.K_m)
            self.assertEqual((quit_.call_count, init.call_count), (0, 0))
        self.settle()
        self.assert_only("lobby")
        self.assertEqual((a.music_starts, len(am._SOUND_CACHE), a.reopens, a.recoveries), (starts, cache, 0, 0))

    def test_many_scene_transitions_do_not_leak_channels_or_sounds(self):
        a = self.audio
        self.settle()
        base = (len(a.music), len(a.sounds), len(am._SOUND_CACHE), pygame.mixer.get_num_channels())
        for _ in range(4):
            for game_id in ("retro_racer", "pixel_volleyball", "galaxy_defender", "cat_minesweeper"):
                scene, room = self.start_game(game_id)
                self.leave(room)
            for room_id in ("prize_plaza", "home", "arcade_floor"):
                goto_room(self.game, room_id)
                self.frames(30)
        self.settle()
        time.sleep(.6)
        self.assertEqual((len(a.music), len(a.sounds), len(am._SOUND_CACHE), pygame.mixer.get_num_channels()), base)
        self.assert_only("lobby")
        self.assertEqual(a.sfx_busy(), [])
        self.assertEqual(sum(c.get_busy() for c in a.channels), 1)
        self.assertEqual((a.reopens, a.recoveries), (0, 0))


class GameWideRecoveryTests(HubCase):
    def test_a_stall_in_the_middle_of_a_game_session_is_recovered_end_to_end(self):
        goto_room(self.game, "arcade_floor")
        self.settle()
        self.assert_only("lobby")
        self.audio.probe_started, self.audio.next_probe = None, 0.0
        self.audio.clock = Clock()
        device = FakeDevice(self.audio, 1)
        with patch.object(AudioManager, "_probe_channel", lambda s: device), self.assertLogs("arcade.audio", "WARNING"):
            for _ in range(int((am.PROBE_EVERY + am.PROBE_STALL + 2) * 4)):
                self.audio.clock.t += .25
                self.game.step([], DT)
        self.assertEqual(self.audio.reopens, 1)
        self.settle()
        self.assertTrue(self.audio.music_playing())
        goto_room(self.game, "home")
        self.settle()
        self.assert_only("home")


if __name__ == "__main__":
    unittest.main()
