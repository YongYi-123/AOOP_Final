"""Effect-channel management: one dedicated effect channel per scene, music kept apart, nothing left behind when a
scene leaves, no per-frame repeats, no piling up of channels (what a device that stops consuming samples used to cause:
"SFX PLAYING CH 4,7,8,9,10,11,12,13").

Real mixer on SDL's dummy driver. Run from this folder:  python -m unittest test_audio_channels -v
"""
import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
from audio_manager import AudioManager  # noqa: E402
from audio_settings_ui import debug_lines  # noqa: E402
from room_testing import goto_room  # noqa: E402
from test_audio_lifecycle import HubCase  # noqa: E402

DT = 1 / 60
ALL_EFFECTS = list(am.SFX_FILES) + list(AudioManager.EFFECTS)


class Clock:
    def __init__(self, t=5000.0):
        self.t = t

    def __call__(self):
        return self.t


def long_sounds(a, seconds=30):
    """Replace every effect by a 30 s sound: stands in for effects that never finish (a device that stopped consuming)."""
    for name in ALL_EFFECTS:
        n = int(a.rate * seconds)
        a.sounds[name] = pygame.mixer.Sound(buffer=bytes(n * 2 * a.stereo))


def busy_pool(a):
    return [c for c in am.SCENE_SFX if pygame.mixer.Channel(c).get_busy()]


class ChannelCase(unittest.TestCase):
    def setUp(self):
        pygame.mixer.init()
        self.a = AudioManager()
        self.a.clock = Clock()
        self.a._probe_sound = None                       # (simulated time must not look like a stalled device)
        self.addCleanup(self.a.stop)
        self.a.preload()

    def tick(self, seconds=1.0, step=0.1):
        end = self.a.clock.t + seconds
        while self.a.clock.t < end:
            self.a.clock.t += step
            self.a.update(step)


class PerSceneChannelTests(ChannelCase):
    def test_every_effect_of_a_scene_shares_one_channel(self):
        a = self.a
        a.sync_scenes([(1, "HOME")])
        long_sounds(a)
        for name in ALL_EFFECTS * 3:
            a.time += 1
            a.play(name)
        self.assertEqual(len(a.scene_ch), 1)
        self.assertEqual(busy_pool(a), [a.scene_ch[1]])
        self.assertEqual(a.sfx_busy(), [a.scene_ch[1]])                # and no other channel anywhere

    def test_a_new_effect_replaces_the_old_one_on_that_channel(self):
        a = self.a
        a.sync_scenes([(1, "HOME")])
        a.play("confirm")
        ch = a.scene_ch[1]
        a.time += 1
        a.play("token")
        self.assertEqual(a.ch_playing[ch][0], "token")
        self.assertEqual(a.scene_ch, {1: ch})

    def test_priority_decides_what_a_busy_channel_gives_up(self):
        a = self.a
        a.sync_scenes([(1, "HOME")])
        long_sounds(a)
        a.play("purchase")
        a.time += 1
        a.play("footstep")                                             # least important: dropped, purchase keeps playing
        ch = a.scene_ch[1]
        self.assertEqual(a.ch_playing[ch][0], "purchase")
        self.assertEqual(a.sfx_dropped.get("footstep"), 1)
        a.time += 1
        a.play("win")                                                  # more important: replaces
        self.assertEqual(a.ch_playing[ch][0], "win")
        a.time += 1
        a.play("confirm")                                              # less important than 'win' while it sounds
        self.assertEqual(a.ch_playing[ch][0], "win")

    def test_effects_still_play_after_a_dropped_one_when_the_channel_is_free(self):
        a = self.a
        a.sync_scenes([(1, "HOME")])
        a.play("footstep")
        time.sleep(.2)                                                 # the real 0.1 s footstep has finished
        a.time += 1
        a.play("purchase")
        self.assertIn("purchase", a.last_effect)
        self.assertEqual(a.sfx_played["purchase"], 1)

    def test_the_music_is_never_touched_by_effects(self):
        a = self.a
        a.switch("home")
        a.update(1.0)
        starts, sound = a.music_starts, a.channels[a.active].get_sound()
        a.sync_scenes([(1, "HOME")])
        long_sounds(a)
        for _ in range(5):
            for name in ALL_EFFECTS:
                a.time += 1
                a.play(name)
        self.assertEqual((a.music_starts, a.channels[a.active].get_sound()), (starts, sound))
        self.assertTrue(a.music_playing())
        self.assertAlmostEqual(a.channels[a.active].get_volume(), a.bgm_volume, delta=.02)
        self.assertFalse(any(pygame.mixer.Channel(i).get_busy() for i in (0, 1)))     # nor the engine channels

    def test_effects_never_pile_up_when_they_never_finish(self):
        """The reported symptom: 'SFX PLAYING CH 4,7,8,9,10,11,12,13'. Effects that never end must not take channel
        after channel."""
        a = self.a
        a.sync_scenes([(1, "ARCADE")])
        long_sounds(a)
        for frame in range(600):
            a.time += 0.2
            a.play(ALL_EFFECTS[frame % len(ALL_EFFECTS)])
        self.assertEqual(len(a.sfx_busy()), 1)

    def test_a_scene_that_makes_no_sound_takes_no_channel(self):
        a = self.a
        a.sync_scenes([(1, "A"), (2, "B"), (3, "C")])
        self.assertEqual(a.scene_ch, {})
        a.play("confirm")
        self.assertEqual(list(a.scene_ch), [3])                        # only the top scene, only when it first sounds


class SceneChangeTests(ChannelCase):
    def test_a_scene_that_leaves_frees_its_channel_after_the_grace_period(self):
        a = self.a
        long_sounds(a)
        a.sync_scenes([(1, "HOME"), (2, "RACER")])
        a.play("machine")
        racer_ch = a.scene_ch[2]
        a.sync_scenes([(1, "HOME")])                                   # the minigame is popped
        self.assertNotIn(2, a.scene_ch)
        self.assertIn(racer_ch, a.orphans)
        self.assertTrue(pygame.mixer.Channel(racer_ch).get_busy())     # its last effect may finish ...
        self.tick(am.ORPHAN_GRACE + 0.3)
        self.assertFalse(pygame.mixer.Channel(racer_ch).get_busy())    # ... but not for ever
        self.assertEqual((a.orphans, a.ch_label, a.ch_playing), ({}, {}, {}))
        a.play("confirm")
        self.assertEqual(a.scene_ch[1] in am.SCENE_SFX, True)

    def test_a_short_effect_is_allowed_to_finish_when_its_scene_leaves(self):
        a = self.a
        a.sync_scenes([(1, "HOME"), (2, "SHOP")])
        a.play("purchase")                                             # 0.5 s of real audio
        ch = a.scene_ch[2]
        a.sync_scenes([(1, "HOME")])
        self.assertTrue(pygame.mixer.Channel(ch).get_busy())
        time.sleep(.7)
        a.update(.05)
        self.assertEqual(a.orphans, {})
        self.assertFalse(pygame.mixer.Channel(ch).get_busy())

    def test_never_more_than_four_scene_channels_and_the_top_scene_always_sounds(self):
        a = self.a
        long_sounds(a)
        stack = []
        for key in range(1, 9):
            stack.append((key, f"S{key}"))
            a.sync_scenes(list(stack))
            a.time += 1
            a.play("confirm")
            self.assertLessEqual(len(a.scene_ch) + len(a.orphans), len(am.SCENE_SFX))
            self.assertIn(key, a.scene_ch)
            self.assertTrue(pygame.mixer.Channel(a.scene_ch[key]).get_busy())
        self.assertLessEqual(len(a.sfx_busy()), len(am.SCENE_SFX))

    def test_a_returning_scene_gets_a_channel_again_and_old_effects_do_not_linger(self):
        a = self.a
        long_sounds(a)
        for _ in range(5):
            a.sync_scenes([(1, "ROOM"), (2, "GAME")])
            a.time += 1
            a.play("machine")
            a.sync_scenes([(1, "ROOM")])
            self.tick(am.ORPHAN_GRACE + 0.2)
            self.assertEqual(a.sfx_busy(), [])
        a.play("confirm")
        self.assertEqual(len(a.sfx_busy()), 1)

    def test_stuck_effects_are_stopped_logged_and_counted(self):
        a = self.a
        a.sync_scenes([(1, "HOME")])
        long_sounds(a)
        a.play("confirm")                                              # a 30 s sound standing in for one that never ends
        ch = a.scene_ch[1]
        name, prio, started, length = a.ch_playing[ch]
        a.ch_playing[ch] = (name, prio, started, 0.2)                  # it "should" have ended after 0.2 s
        with self.assertLogs("arcade.audio", "WARNING") as logs:
            self.tick(am.SFX_STUCK_GRACE + 0.5)
        self.assertIn("never finished", logs.output[0])
        self.assertEqual(a.stuck_sfx, 1)
        self.assertFalse(pygame.mixer.Channel(ch).get_busy())
        self.assertEqual(a.scene_ch, {1: ch})                          # the live scene keeps its channel
        a.time += 1
        a.play("token")
        self.assertTrue(pygame.mixer.Channel(ch).get_busy())

    def test_a_mixer_reopen_clears_every_channel_assignment(self):
        a = self.a
        a.sync_scenes([(1, "HOME")])
        a.play("confirm")
        with self.assertLogs("arcade.audio", "WARNING"):
            a.reopen_mixer("test")
        self.assertEqual((a.scene_ch, a.orphans, a.ch_playing), ({}, {}, {}))
        a.time += 1
        a.play("confirm")
        self.assertEqual(len(a.sfx_busy()), 1)


class CatVoiceAndReservationTests(HubCase):
    def test_meows_share_the_scenes_channel_instead_of_taking_new_ones(self):
        import cat_voice
        goto_room(self.game, "home")
        self.frames(5)
        sound = pygame.mixer.Sound(buffer=bytes(self.audio.rate * 2 * self.audio.stereo * 5))     # a 5 s "meow"
        bank = type("Bank", (), {"get": lambda self, kind, pitch: sound})()
        voices = [cat_voice.CatVoice(pitch=1 + i / 10, bank=bank) for i in range(6)]
        for i, voice in enumerate(voices):
            voice.play("meow", i * 5)
        self.assertEqual(len(self.audio.sfx_busy()), 1)
        self.assertLessEqual(len(self.audio.scene_ch), 1)

    def test_reservations_survive_the_racer_loading(self):
        """Retro Racer calls set_reserved itself; it must keep channels 0-7 off automatic allocation."""
        scene, room = self.start_game("retro_racer")
        sound = pygame.mixer.Sound(buffer=bytes(self.audio.rate * 2 * self.audio.stereo * 5))
        taken = [sound.play() for _ in range(12)]
        busy_low = [i for i in range(8) if pygame.mixer.Channel(i).get_busy() and
                    pygame.mixer.Channel(i).get_sound() is sound]
        self.assertEqual(busy_low, [], "an automatic effect landed on a reserved channel")
        for ch in taken:
            if ch:
                ch.stop()


class NoRepeatTests(HubCase):
    def test_idle_scenes_trigger_no_effects_and_walking_a_sensible_few(self):
        a = self.audio
        for room_id in ("arcade_floor", "home", "prize_plaza"):
            goto_room(self.game, room_id)
            self.frames(30)
            before = dict(a.sfx_requested)
            self.frames(600)                                          # ten seconds of doing nothing
            self.assertEqual(a.sfx_requested, before, f"{room_id}: effects triggered while idle")
        room = goto_room(self.game, "arcade_floor")
        self.frames(30)
        before = a.sfx_requested.get("footstep", 0)
        self.game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a")], DT)
        self.frames(300)                                              # five seconds of walking
        steps = a.sfx_requested.get("footstep", 0) - before
        self.assertTrue(0 < steps <= 5 * 6 + 2, steps)                # a footstep per foot-fall, never one per frame

    def test_minigames_and_lucky_corner_trigger_nothing_by_themselves(self):
        from neon21_scene import Neon21Scene
        a = self.audio
        for game_id in ("pixel_volleyball", "galaxy_defender", "cat_minesweeper"):
            scene, room = self.start_game(game_id)
            before = dict(a.sfx_requested)
            self.frames(300)
            self.assertEqual(a.sfx_requested, before, game_id)
            self.leave(room)
        self.game.scenes.push(Neon21Scene(self.game, self.game.session.players[0]), fade=False)
        self.frames(20)
        before = dict(a.sfx_requested)
        self.frames(300)
        self.assertEqual(a.sfx_requested, before)
        self.game.scenes.pop(fade=False)
        self.frames(20)


class FullGameChannelTests(HubCase):
    def test_a_tour_of_every_scene_never_exceeds_the_scene_channels_and_leaves_none_behind(self):
        a = self.audio
        peak = 0
        with patch.object(pygame.mixer, "quit") as quit_, patch.object(pygame.mixer, "init") as init:
            for _ in range(2):
                for game_id in ("retro_racer", "pixel_volleyball", "galaxy_defender", "cat_minesweeper"):
                    scene, room = self.start_game(game_id)
                    for name in ("confirm", "machine", "token", "purchase"):
                        a.time += 1
                        a.play(name)
                    self.frames(5)
                    peak = max(peak, len(a.scene_ch) + len(a.orphans))
                    self.leave(room)
                for room_id in ("prize_plaza", "home", "arcade_floor"):
                    goto_room(self.game, room_id)
                    self.frames(20)
                    a.time += 1
                    a.play("confirm")
            self.assertEqual((quit_.call_count, init.call_count), (0, 0))
        self.assertLessEqual(peak, len(am.SCENE_SFX))
        time.sleep(.7)
        self.frames(60)
        self.assertEqual(a.orphans, {})
        self.assertLessEqual(len(a.scene_ch), len(self.game.scenes.stack))
        self.assertEqual(a.sfx_busy(), [])
        self.assert_only("lobby")
        self.assertEqual((a.reopens, a.recoveries), (0, 0))

    def test_the_hud_shows_who_owns_which_channel_and_other_users(self):
        a = self.audio
        goto_room(self.game, "home")
        self.frames(30)
        a.time += 1
        a.play("purchase")
        text = "\n".join(debug_lines(self.game))
        self.assertRegex(text, r"OWNER  [4-7]=HOME(:purchase)?")
        sound = pygame.mixer.Sound(buffer=bytes(a.rate * 2 * a.stereo * 2))
        pygame.mixer.Channel(12).play(sound)                          # something outside the scene channels
        text = "\n".join(debug_lines(self.game))
        self.assertIn("OTHER  CH 12", text)
        self.assertIn("12", text.split("SFX    ")[1].split("\n")[0])
        a.stuck_sfx = 2
        self.assertIn("STUCK 2", "\n".join(debug_lines(self.game)))
        pygame.mixer.Channel(12).stop()

    def test_volume_and_mute_still_apply_to_scene_channel_effects(self):
        a = self.audio
        a.sync_scenes([(1, "HOME")])
        a.set_volumes(sfx=.5)
        a.time += 1
        a.play("confirm")
        ch = a.scene_ch[1]
        self.assertAlmostEqual(a.sounds["confirm"].get_volume(), .5 * am.SFX_GAIN["confirm"], places=2)
        a.set_muted(True)
        a.time += 1
        a.play("token")
        self.assertEqual(a.ch_playing[ch][0], "confirm")              # muted: nothing new is started


if __name__ == "__main__":
    unittest.main()
