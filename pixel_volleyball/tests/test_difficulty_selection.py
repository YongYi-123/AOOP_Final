import unittest
from pixel_volleyball.game import VolleyGame
from pixel_volleyball.model import VolleyInput


class DifficultySelectionTests(unittest.TestCase):
    def test_difficulty_selection_pause_and_replay_persist(self):
        game = VolleyGame()
        self.addCleanup(game.audio.stop)
        self.assertTrue(game.select_difficulty(1))
        self.assertEqual(game.match.ai.difficulty.name,'HARD')
        game.confirm()
        self.assertFalse(game.select_difficulty(1))
        game.update(.1,[VolleyInput(1,True)])
        game.match.toggle_pause()
        before = (game.match.ball.rotation,game.match.players[0].y,game.match.elapsed)
        game.update(.1)
        self.assertEqual(before,(game.match.ball.rotation,game.match.players[0].y,game.match.elapsed))
        game.restart()
        self.assertEqual(game.match.ai.difficulty.name,'HARD')
        self.assertFalse(VolleyGame(2).select_difficulty(1))

