import os
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import unittest
from unittest.mock import patch
import pygame
from audio_manager import AudioManager, GameSoundBus


class AudioTests(unittest.TestCase):
    def test_device_failure_is_silent(self):
        with patch.object(pygame.mixer, 'get_init', return_value=None), patch.object(
                pygame.mixer, 'init', side_effect=pygame.error('no device')):
            audio = AudioManager()
        self.assertFalse(audio.enabled)
        audio.switch('lobby')
        audio.play('confirm')
        audio.stop()

    def test_music_switch_loop_and_independent_volumes(self):
        pygame.mixer.init()
        audio = AudioManager()
        self.addCleanup(audio.stop)
        audio.switch('lobby')
        self.assertTrue(audio.channels[audio.active].get_busy())
        channel = audio.active
        audio.switch('lobby')
        self.assertEqual(channel, audio.active)
        audio.switch('pixel_volleyball')
        self.assertNotEqual(channel, audio.active)
        audio.set_volumes(bgm=0, sfx=.8)
        self.assertEqual(audio.sfx_volume, .8)
        self.assertEqual(audio.channels[audio.active].get_volume(), 0)
        audio.switch('lobby')
        self.assertEqual(audio.theme, 'lobby')

    def test_game_bus_and_cooldown(self):
        pygame.mixer.init()
        audio = AudioManager()
        self.addCleanup(audio.stop)
        bus = GameSoundBus(audio)
        bus.play(['hit', 'hit', 'point'])
        self.assertEqual(set(audio.last_effect), {'hit', 'point'})
        previous = audio.last_effect['hit']
        bus.play('hit', 10)
        self.assertEqual(audio.last_effect['hit'], previous)
        audio.update(.1)
        bus.play('hit')
        self.assertGreater(audio.last_effect['hit'], previous)

    def test_lobby_minigame_return_and_volume_keys(self):
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        from game import Game
        from player_profile import PlayerProfile
        from local_session import LocalSession
        from room_testing import goto_room
        game = Game(session=LocalSession([PlayerProfile(profile_id='audio_test')]))
        self.addCleanup(game.quit)
        room = goto_room(game, 'arcade_floor')
        for game_id in ('pixel_volleyball', 'cat_minesweeper', 'retro_racer'):
            machine = next(m for m in room.machines if m.id == game_id)
            room._start_game(machine, player=room.players[0])
            for _ in range(30):
                game.step([], 1 / 60)
            self.assertEqual(game.audio.theme, game_id)
            self.assertTrue(game.audio.channels[game.audio.active].get_busy())
            game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0)], 1 / 60)
            for _ in range(30):
                game.step([], 1 / 60)
            self.assertEqual(game.audio.theme, 'lobby')
        before = game.audio.bgm_volume
        game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F6, mod=0)], 1 / 60)
        self.assertAlmostEqual(game.audio.bgm_volume, before - .1)
        before = game.audio.sfx_volume
        game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F9, mod=0)], 1 / 60)
        self.assertAlmostEqual(game.audio.sfx_volume, before + .1)
