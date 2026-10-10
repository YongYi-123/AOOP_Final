import os
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import unittest
from unittest.mock import patch
import pygame
from audio import Audio, RATE


class SharedAudioTests(unittest.TestCase):
    def test_existing_mixer_and_music_survive_racer_initialization(self):
        pygame.mixer.quit()
        pygame.mixer.init(44100, -16, 2)
        sound = pygame.mixer.Sound(buffer=bytes(44100 * 4))
        music = pygame.mixer.Channel(2)
        music.play(sound, loops=-1)
        with patch.object(pygame.mixer, 'quit', wraps=pygame.mixer.quit) as quit_mixer:
            audio = Audio()
        self.addCleanup(audio.stop_engine)
        quit_mixer.assert_not_called()
        self.assertTrue(music.get_busy())
        self.assertEqual(pygame.mixer.get_init()[0], 44100)
        self.assertAlmostEqual(audio._make([0.0] * RATE).get_length(), 1, places=3)
        music.stop()

    def test_external_sfx_volume_preserves_racer_volume_and_mute(self):
        audio = Audio(volume=.8)
        self.addCleanup(audio.stop_engine)
        audio.external_gain = .5
        self.assertAlmostEqual(audio.master, .4)
        self.assertEqual(audio.volume, .8)
        audio.muted = True
        self.assertEqual(audio.master, 0)
