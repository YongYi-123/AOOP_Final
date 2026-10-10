import unittest
from tracks import TRACKS


class AICircuitTests(unittest.TestCase):
    def test_ai_finishes_three_laps_on_every_circuit_with_generated_oil(self):
        import os
        os.environ.setdefault('SDL_VIDEODRIVER','dummy')
        os.environ.setdefault('SDL_AUDIODRIVER','dummy')
        from game import Game
        import random
        game=Game()
        self.addCleanup(game.audio.stop_engine)
        for track in TRACKS:
            game.track=track
            game.apply_look()
            game.manager.field.rng.seed(123)
            game.start_race(); game.begin_playing()
            field=game.manager.field
            for racer in field.racers:
                racer.driver.rng=random.Random(123)
            for _ in range(8000):
                field.update(.05,game.player)
                game.hazards.update(.05,game.player,field.racers)
                if all(r in field.finish_order for r in field.racers):
                    break
            self.assertTrue(all(r in field.finish_order for r in field.racers),track.key)
