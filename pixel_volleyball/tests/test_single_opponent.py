import unittest
from pixel_volleyball.game import VolleyGame
from pixel_volleyball.model import VolleyInput


class SingleOpponentTests(unittest.TestCase):
    def test_pause_and_replay_preserve_single_opponent(self):
        game = VolleyGame()
        self.addCleanup(game.audio.stop)
        self.assertFalse(hasattr(game, 'select_difficulty'))
        game.confirm()
        game.update(.1,[VolleyInput(1,True)])
        game.match.toggle_pause()
        before = (game.match.ball.rotation,game.match.players[0].y,game.match.elapsed)
        game.update(.1)
        self.assertEqual(before,(game.match.ball.rotation,game.match.players[0].y,game.match.elapsed))
        reaction = game.match.ai.REACTION
        game.restart()
        self.assertEqual(game.match.ai.REACTION,reaction)
        self.assertFalse(hasattr(VolleyGame(2), 'select_difficulty'))
