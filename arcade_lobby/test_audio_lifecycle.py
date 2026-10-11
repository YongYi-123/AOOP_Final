"""Regression tests for the audio lifecycle: who owns the music, how it changes between rooms and
minigames, that nothing is left silent or ringing, and that Retro Racer's engine stays audible.

They use the real mixer on SDL's dummy driver (the mixer, channels, volumes and playback state are all
real; only the output device is fake).  Run from this folder:  python -m unittest test_audio_lifecycle -v
"""
import json
import math
import os
import shutil
import struct
import tempfile
import unittest
import wave
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
from audio_manager import AudioManager  # noqa: E402
from chance_scene import ChanceGameScene  # noqa: E402
from game import Game  # noqa: E402
from high_low import HighLowGame  # noqa: E402
from local_session import LocalSession  # noqa: E402
from lucky_wheel import LuckyWheelGame  # noqa: E402
from neon21_scene import Neon21Scene  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from retro_racer_scene import ENGINE_BOOST, RetroRacerScene  # noqa: E402
from room_testing import goto_room  # noqa: E402

DT = 1 / 60
GAMES = ("retro_racer", "pixel_volleyball", "cat_minesweeper", "galaxy_defender")
MUSIC_BUSY = (2, 3)
ENGINE = (0, 1)


def busy(i):
    return pygame.mixer.Channel(i).get_busy()


class HubCase(unittest.TestCase):
    """A running hub on the real mixer, with helpers to step it and to look at the music channels."""

    def setUp(self):
        self.prefs = os.path.join(tempfile.mkdtemp(), "audio.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(self.prefs), True)
        self.game = Game(session=LocalSession([PlayerProfile(profile_id="a", tickets=300, tokens=99)]),
                         audio_prefs=self.prefs)
        self.addCleanup(self.game.quit)
        self.audio = self.game.audio
        self.assertTrue(self.audio.enabled, self.audio.init_error)

    def frames(self, n=30, key=None):
        for i in range(n):
            events = [pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")] if key and i == 0 else []
            self.game.step(events, DT)

    def settle(self):
        self.frames(60)                                      # > the 700 ms crossfade

    def assert_only(self, theme):
        """Exactly `theme` is playing: on the active channel, at full music volume, nothing else left over."""
        a = self.audio
        self.assertEqual(a.theme, theme)
        self.assertTrue(a.music_playing())
        active, other = a.channels[a.active], a.channels[1 - a.active]
        self.assertIs(active.get_sound(), a.music[theme])
        self.assertAlmostEqual(active.get_volume(), 0 if a.muted else a.bgm_volume * a.duck, delta=.02)
        self.assertFalse(other.get_busy(), "a previous track is still playing")

    def start_game(self, game_id):
        room = goto_room(self.game, "arcade_floor")
        machine = next(m for m in room.machines if m.id == game_id)
        room._start_game(machine, player=room.players[0])
        for _ in range(900):                                 # the racer builds itself on its first visit
            self.frames(1)
            scene = self.game.scenes.current
            if getattr(scene, "machine", None) is not None and not getattr(scene, "leaving", False) and \
                    (game_id != "retro_racer" or scene.racer is not None):
                break
        self.frames(20)
        return self.game.scenes.current, room

    def leave(self, room):
        self.game.scenes.pop()
        self.frames(40)
        self.assertIs(self.game.scenes.current, room)


class MusicOwnershipTests(HubCase):
    def test_hub_to_every_game_and_back_restores_the_room_music(self):
        for game_id in GAMES:
            scene, room = self.start_game(game_id)
            self.settle()
            self.assert_only(game_id)
            self.leave(room)
            self.settle()
            self.assert_only("lobby")

    def test_repeated_transitions_never_leave_silence_or_overlap(self):
        for _ in range(3):
            for game_id in GAMES:
                scene, room = self.start_game(game_id)
                self.leave(room)
            self.settle()
            self.assert_only("lobby")
        self.assertEqual(self.audio.recoveries, 0, "the watchdog had to rescue the music")

    def test_rapid_back_and_forth_switching_ends_on_the_right_single_track(self):
        a = self.audio
        for theme in ("home", "lobby", "prize_plaza", "home", "lobby", "home") * 3:
            a.switch(theme)
            a.update(.1)
        for _ in range(30):
            a.update(.05)
        self.assert_only("home")

    def test_every_game_and_chance_scene_chooses_its_own_theme(self):
        want = {"retro_racer": "retro_racer", "pixel_volleyball": "pixel_volleyball",
                "cat_minesweeper": "cat_minesweeper", "galaxy_defender": "galaxy_defender"}
        for game_id, theme in want.items():
            scene, room = self.start_game(game_id)
            self.assertEqual(Game.music_for(self.game.scenes.stack), theme)
            self.leave(room)
        pl = self.game.session.players[0]
        for scene, theme in ((Neon21Scene(self.game, pl), "neon21"),
                             (ChanceGameScene(self.game, LuckyWheelGame, pl), "lucky_wheel"),
                             (ChanceGameScene(self.game, HighLowGame, pl), "high_low")):
            self.game.scenes.push(scene)
            self.frames(40)
            self.settle()
            self.assert_only(theme)
            self.game.scenes.pop()
            self.frames(40)
        for theme in want.values():
            self.assertIn(theme, am.MUSIC_FILES)

    def test_a_menu_on_top_of_a_game_keeps_the_games_music(self):
        from wardrobe_ui import WardrobeScene
        scene, room = self.start_game("pixel_volleyball")
        self.settle()
        starts = self.audio.music_starts
        self.game.scenes.push(WardrobeScene(self.game, self.game.session.players[0]))
        self.frames(60)
        self.assertEqual(self.audio.theme, "pixel_volleyball")
        self.game.scenes.pop()
        self.frames(60)
        self.assertEqual(self.audio.music_starts, starts)

    def test_entering_a_scene_starts_its_music_exactly_once(self):
        scene, room = self.start_game("galaxy_defender")
        starts = self.audio.music_starts
        self.frames(180)
        self.assertEqual(self.audio.music_starts, starts)    # nested / repeated scene updates never restart it
        self.leave(room)
        self.frames(180)
        self.assertEqual(self.audio.music_starts, starts + 1)

    def test_the_start_screens_keep_the_hub_theme_and_a_session_starts_straight_in_its_room(self):
        self.assertEqual(Game.music_for([]), None)
        self.assertEqual(Game.music_for([object()]), None)
        self.frames(5)
        self.assertEqual(self.audio.music_starts, 1)         # one start, not "hub theme, then the room's"


class CrossfadeTests(unittest.TestCase):
    def setUp(self):
        pygame.mixer.init()
        self.a = AudioManager()
        self.addCleanup(self.a.stop)

    def test_the_crossfade_finishes_by_game_time_and_stops_the_old_track(self):
        a = self.a
        a.switch("lobby")
        a.update(1.0)
        old = a.active
        a.switch("home")
        a.update(.35)
        self.assertTrue(all(c.get_busy() for c in a.channels))              # both audible mid-fade
        self.assertTrue(0 < a.channels[a.active].get_volume() < a.bgm_volume)
        a.update(.5)
        self.assertFalse(a.channels[old].get_busy())
        self.assertAlmostEqual(a.channels[a.active].get_volume(), a.bgm_volume, delta=.02)

    def test_a_stalled_audio_clock_cannot_leave_the_hub_silent(self):
        """The fade follows game time, not the sound card's clock: with every channel call that depends on the
        device frozen, the new track still reaches full volume and the old one is stopped."""
        a = self.a
        a.switch("lobby")
        a.update(1.0)
        a.switch("prize_plaza")
        for _ in range(20):
            a.update(.05)
        self.assertAlmostEqual(a.channels[a.active].get_volume(), a.bgm_volume, delta=.02)
        self.assertEqual(sum(c.get_busy() for c in a.channels), 1)

    def test_muting_and_unmuting_during_a_transition(self):
        a = self.a
        a.switch("lobby")
        a.update(1.0)
        a.switch("home")
        a.update(.2)
        a.set_muted(True)
        for c in a.channels:
            self.assertEqual(c.get_volume(), 0)
        a.update(.8)                                         # the fade completes while muted
        self.assertEqual(a.channels[a.active].get_volume(), 0)
        self.assertTrue(a.music_playing())                   # still running, just inaudible
        a.set_muted(False)
        self.assertAlmostEqual(a.channels[a.active].get_volume(), a.bgm_volume, delta=.02)
        a.set_volumes(bgm=.8)                                # immediate
        self.assertAlmostEqual(a.channels[a.active].get_volume(), .8, delta=.02)

    def test_pausing_a_game_ducks_the_music_and_resuming_restores_it(self):
        a = self.a
        a.switch("home")
        a.update(1.0)
        a.set_duck(am.DUCK_PAUSED)
        self.assertAlmostEqual(a.channels[a.active].get_volume(), a.bgm_volume * am.DUCK_PAUSED, delta=.02)
        a.set_duck(1.0)
        self.assertAlmostEqual(a.channels[a.active].get_volume(), a.bgm_volume, delta=.02)

    def test_the_watchdog_restarts_music_that_something_stopped(self):
        a = self.a
        a.switch("lobby")
        a.update(1.0)
        pygame.mixer.stop()                                  # what a misbehaving module could do
        self.assertFalse(a.music_playing())
        with self.assertLogs("arcade.audio", "WARNING"):
            for _ in range(40):
                a.update(.05)
        self.assertTrue(a.music_playing())
        self.assertEqual(a.recoveries, 1)
        self.assertAlmostEqual(a.channels[a.active].get_volume(), a.bgm_volume, delta=.02)

    def test_a_closed_mixer_is_reopened_not_left_dead(self):
        a = self.a
        a.switch("lobby")
        pygame.mixer.quit()
        with self.assertLogs("arcade.audio", "ERROR"):
            a.update(.1)
        self.assertTrue(a.enabled)
        self.assertIsNotNone(pygame.mixer.get_init())
        for _ in range(40):
            a.update(.05)
        self.assertTrue(a.music_playing())

    def test_stop_means_stop(self):
        a = self.a
        a.switch("lobby")
        a.stop()
        for _ in range(40):
            a.update(.05)
        self.assertFalse(a.music_playing())

    def test_missing_music_files_still_play_something_and_say_so(self):
        a = AudioManager(asset_dir=os.path.join(tempfile.gettempdir(), "no-assets-here"))
        self.addCleanup(a.stop)
        with self.assertLogs("arcade.audio", "WARNING"):
            a.switch("retro_racer")
        a.update(1.0)
        self.assertTrue(a.music_playing())
        self.assertEqual(sorted(a.status()["missing_music"]), sorted(am.MUSIC_FILES))


class ChannelSeparationTests(HubCase):
    def test_effects_never_use_the_music_or_engine_channels(self):
        self.audio.switch("home")
        self.settle()
        for name in list(am.SFX_FILES) + list(self.audio.EFFECTS):
            self.audio.time += 1
            self.audio.play(name)
        for i in ENGINE:
            self.assertFalse(busy(i), f"channel {i} (engine) was taken by an effect")
        music = {id(s) for s in self.audio.music.values()}
        for i in MUSIC_BUSY:
            sound = pygame.mixer.Channel(i).get_sound()
            self.assertTrue(sound is None or id(sound) in music, f"channel {i} was taken by an effect")

    def test_effects_do_not_interrupt_the_music(self):
        self.audio.switch("lobby")
        self.audio.update(1.0)
        for _ in range(10):
            for name in ("confirm", "footstep", "token", "machine", "cancel"):
                self.audio.time += .5
                self.audio.play(name)
        self.assert_only("lobby")

    def test_no_unintended_mixer_shutdown_across_a_full_tour(self):
        with patch.object(pygame.mixer, "quit", Mock(side_effect=pygame.mixer.quit)) as quit_, \
                patch.object(pygame.mixer, "init", Mock(side_effect=pygame.mixer.init)) as init:
            for game_id in GAMES:
                scene, room = self.start_game(game_id)
                self.leave(room)
            for room_id in ("prize_plaza", "home", "arcade_floor"):
                goto_room(self.game, room_id)
                self.frames(20)
            self.assertEqual(quit_.call_count, 0)
            self.assertEqual(init.call_count, 0)

    def test_generic_confirm_and_cancel_beeps_do_not_stack_on_a_minigames_own_sounds(self):
        scene, room = self.start_game("pixel_volleyball")
        self.audio.last_effect.clear()
        self.frames(2, pygame.K_RETURN)
        self.frames(2, pygame.K_ESCAPE)
        self.assertNotIn("confirm", self.audio.last_effect)
        self.assertNotIn("cancel", self.audio.last_effect)

    def test_a_pause_ducks_the_music_through_the_game_loop(self):
        scene, room = self.start_game("retro_racer")
        self.settle()
        scene.racer.set_paused(True)
        self.frames(5)
        self.assertEqual(self.audio.duck, am.DUCK_PAUSED)
        scene.racer.set_paused(False)
        self.frames(5)
        self.assertEqual(self.audio.duck, 1.0)


class RacerEngineTests(HubCase):
    def setUp(self):
        super().setUp()
        self.scene, self.room = self.start_game("retro_racer")
        self.racer = self.scene.racer
        self.assertIsNotNone(self.racer, self.scene.error)
        self.settle()

    def engine(self):
        return [(busy(i), pygame.mixer.Channel(i).get_volume()) for i in ENGINE]

    def drive(self, speed, frames=20):
        for _ in range(frames):
            self.racer.audio.engine(speed, True)
            self.game.step([], DT)

    def test_the_engine_is_audible_alongside_the_music(self):
        self.drive(.6)
        engine = self.engine()
        self.assertTrue(all(b for b, _ in engine))
        self.assertGreater(sum(v for _, v in engine), .12)
        self.assertEqual(self.racer.audio.engine_boost, ENGINE_BOOST)
        self.assert_only("retro_racer")                       # and the music did not stop

    def test_the_engine_pitch_follows_speed_and_is_never_silent_at_idle(self):
        self.drive(0)
        idle = sum(v for _, v in self.engine())
        self.assertGreater(idle, .05)
        self.drive(1.0)
        fast = sum(v for _, v in self.engine())
        self.assertGreater(fast, idle)
        self.assertNotEqual(self.racer.audio.loop_position(0), self.racer.audio.loop_position(1))

    def test_collision_and_race_effects_play_while_the_engine_and_music_run(self):
        self.drive(.7)
        for name in ("crash", "checkpoint", "go", "finish", "pickup"):
            self.racer.audio.clock += 1
            self.racer.audio.play(name)
        self.drive(.7, 5)
        self.assertTrue(all(b for b, _ in self.engine()))
        self.assert_only("retro_racer")

    def test_a_stopped_engine_channel_is_noticed_and_restarted(self):
        self.drive(.7)
        pygame.mixer.Channel(0).stop()
        pygame.mixer.Channel(1).stop()
        self.drive(.7, 3)
        self.assertTrue(all(b for b, _ in self.engine()))

    def test_pause_silences_the_engine_and_resume_brings_it_back(self):
        self.drive(.7)
        self.racer.set_paused(True)
        self.frames(30)
        self.racer.set_paused(False)
        self.drive(.7)
        self.assertTrue(all(b for b, _ in self.engine()))

    def test_leaving_leaves_no_engine_noise_and_replaying_restores_it(self):
        for visit in range(3):
            self.drive(.8)
            self.leave(self.room)
            self.assertFalse(any(b for b, _ in self.engine()), "engine still ringing after leaving")
            self.settle()
            self.assert_only("lobby")
            self.scene, self.room = self.start_game("retro_racer")
            self.racer = self.scene.racer
            self.drive(.8)
            self.assertTrue(all(b for b, _ in self.engine()), f"no engine on visit {visit + 2}")

    def test_effects_are_never_dropped_because_the_music_channels_look_busy(self):
        """The voice limit counts only effect channels - the two music channels are always busy."""
        self.assertEqual(self.racer.audio._voices_busy(), 0)

    def test_the_racers_own_mute_does_not_survive_into_a_new_visit(self):
        self.racer.audio.muted = True
        self.leave(self.room)
        self.scene, self.room = self.start_game("retro_racer")
        self.assertFalse(self.scene.racer.audio.muted)


class AssetQualityTests(unittest.TestCase):
    """Properties of the shipped WAVs that cause clicks, thumps, loudness jumps or stuck loops."""

    @staticmethod
    def read(path):
        with wave.open(path) as w:
            n = w.getnframes()
            return struct.unpack(f"<{n}h", w.readframes(n))

    def music(self, name):
        return self.read(os.path.join(am.ASSET_DIR, "music", f"{am.MUSIC_FILES[name]}.wav"))

    def test_every_theme_exists_loops_and_is_not_clipped(self):
        for theme in am.MUSIC_FILES:
            data = self.music(theme)
            self.assertGreater(len(data) / 22050, 20, theme)
            self.assertLess(len(data) / 22050, 60, theme)                   # lightweight
            self.assertLess(max(map(abs, data)) / 32767, .9, theme)
            self.assertLess(abs(data[0] - data[-1]) / 32767, .12, theme)    # the loop seam is not a click

    def test_themes_sit_at_a_similar_loudness_after_the_per_track_gain(self):
        levels = {}
        for theme in am.MUSIC_FILES:
            data = self.music(theme)
            rms = math.sqrt(sum(x * x for x in data) / len(data)) / 32767
            levels[theme] = 20 * math.log10(rms * am.TRACK_GAIN.get(theme, 1.0))
        racing = levels.pop("retro_racer")                   # deliberately lower: the engine sits on top of it
        self.assertLess(max(levels.values()) - min(levels.values()), 1.0, levels)
        self.assertLess(racing, min(levels.values()) - 1.5)

    def test_new_minigame_tracks_are_all_different_and_have_no_dc_offset(self):
        starts = set()
        for theme in ("retro_racer", "pixel_volleyball", "cat_minesweeper", "galaxy_defender", "neon21",
                      "lucky_wheel", "high_low"):
            data = self.music(theme)
            starts.add(data[2000:6000])
            self.assertLess(abs(sum(data) / len(data)) / 32767, .01, theme)
        self.assertEqual(len(starts), 7)

    def test_sound_effects_start_and_end_silent_without_a_dc_offset(self):
        for name in am.SFX_FILES:
            data = self.read(os.path.join(am.ASSET_DIR, "sfx", f"{name}.wav"))
            self.assertLess(abs(data[0]) / 32767, .01, f"{name} starts with a click")
            self.assertLess(abs(data[-1]) / 32767, .01, f"{name} ends with a click")
            self.assertLess(abs(sum(data) / len(data)) / 32767, .01, f"{name} has a DC offset (thump)")

    def test_busy_synthesized_effects_are_rate_limited_and_soft(self):
        self.assertGreaterEqual(am.MIN_GAP["laser"], .12)
        self.assertLessEqual(am.SFX_GAIN["laser"], .4)
        self.assertGreaterEqual(am.MIN_GAP["meow"], 1.0)

    def test_preloading_means_nothing_is_built_during_play(self):
        pygame.mixer.init()
        a = AudioManager()
        self.addCleanup(a.stop)
        a.preload()
        self.assertEqual(set(a.music), set(am.MUSIC_FILES))
        for name in (*am.SFX_FILES, *a.EFFECTS):
            self.assertIn(name, a.sounds)
        with patch.object(a, "_sound", side_effect=AssertionError("synthesized during play")), \
                patch.object(a, "_load", side_effect=AssertionError("loaded during play")):
            for theme in am.MUSIC_FILES:
                a.switch(theme)
            for name in (*am.SFX_FILES, *a.EFFECTS):
                a.time += 1
                a.play(name)


class SettingsTests(HubCase):
    def test_volume_and_mute_persist_and_apply_during_a_minigame(self):
        scene, room = self.start_game("pixel_volleyball")
        self.settle()
        self.frames(2, pygame.K_F6)
        self.frames(2, pygame.K_F9)
        self.frames(2, pygame.K_m)
        self.assertTrue(self.audio.muted)
        self.assertEqual(self.audio.channels[self.audio.active].get_volume(), 0)
        with open(self.prefs) as f:
            saved = json.load(f)
        self.assertEqual(saved["muted"], True)
        self.assertAlmostEqual(saved["music"], am.DEFAULT_BGM - .1, places=2)
        self.frames(2, pygame.K_m)
        self.assertAlmostEqual(self.audio.channels[self.audio.active].get_volume(), am.DEFAULT_BGM - .1, delta=.02)
        self.assertTrue(self.audio.music_playing())

    def test_cat_meows_follow_the_effects_volume_and_mute(self):
        import cat_voice
        sound = Mock()
        bank = Mock(get=Mock(return_value=sound))
        cat = cat_voice.CatVoice(bank=bank)
        self.audio.set_volumes(sfx=am.DEFAULT_SFX)
        cat.play("meow", 0)
        self.assertAlmostEqual(sound.play.return_value.set_volume.call_args[0][0], cat.volume, places=2)
        self.audio.set_muted(True)
        sound.reset_mock()
        self.assertTrue(cat.play("meow", 10))                # still "meows" (the speech bubble) ...
        sound.play.assert_not_called()                       # ... but makes no sound
        self.audio.set_muted(False)
        self.audio.set_volumes(sfx=.35)
        cat.play("meow", 20)
        self.assertAlmostEqual(sound.play.return_value.set_volume.call_args[0][0], cat.volume / 2, places=2)

    def test_the_readout_names_the_music_that_is_playing(self):
        self.frames(5)
        self.assertEqual(self.audio.track_title, "HOME")
        self.audio.switch("neon21")
        self.assertEqual(self.audio.track_title, "NEON 21")
        self.frames(2, pygame.K_F7)
        self.assertGreater(self.game.volume_toast, 0)         # (drawn with the title on a second line)

    def test_defaults_are_comfortable(self):
        self.assertTrue(.3 <= am.DEFAULT_BGM <= .6)
        self.assertTrue(.5 <= am.DEFAULT_SFX <= .8)


if __name__ == "__main__":
    unittest.main()
