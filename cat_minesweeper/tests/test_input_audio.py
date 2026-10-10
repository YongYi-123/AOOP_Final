import os
import unittest
from unittest import mock
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from cat_minesweeper.game import MineGame
from cat_minesweeper.mouse import MineMouseInput


class MineInputAudioTests(unittest.TestCase):
    def test_mouse_scaling_matches_canvas_at_multiple_window_sizes(self):
        for width, height in ((800, 600), (400, 300), (1200, 900)):
            self.assertEqual(MineMouseInput.canvas_position((width / 2, height / 2), (width, height)),
                             (200, 150))

    def test_only_accepted_actions_request_audio_and_pause_blocks_it(self):
        pygame.init()
        game = MineGame()
        self.addCleanup(game.audio.stop)
        game.confirm()
        point = game.layout.cell_rect(0, 0).center
        with mock.patch.object(game.audio, "play") as play:
            game.click(point, 3)
            play.assert_called_once_with("flag", 0)
            game.click(point, 1)
            self.assertEqual(play.call_count, 1)
            game.toggle_pause()
            game.click(point, 3)
            self.assertEqual(play.call_count, 1)
