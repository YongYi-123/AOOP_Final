import unittest
from pixel_volleyball.ai import VolleyAI
from pixel_volleyball.model import VolleyMatch, VolleyBall, VolleyInput


class AITests(unittest.TestCase):
    def test_predicts_gravity_and_wall_reflection(self):
        self.assertAlmostEqual(VolleyAI.predict(VolleyBall(300, 180, 0, 50)), 300)
        self.assertLess(VolleyAI.predict(VolleyBall(350, 170, 250, 100)), 350)

    def test_reaction_intervals_and_accuracy(self):
        player = VolleyMatch().players[1]
        ball = VolleyBall(250, 180, 0, 80)
        brains = [VolleyAI(name) for name in ('EASY', 'NORMAL', 'HARD')]
        for ai in brains:
            for _ in range(120):
                ai.controls(player, ball, 1/120)
        self.assertLess(brains[0].decisions, brains[1].decisions)
        self.assertLess(brains[1].decisions, brains[2].decisions)
        self.assertEqual(brains[2].target, 250)
        self.assertGreater(abs(brains[0].target-250), 5)

    def test_easy_never_spikes_hard_aims_away_from_opponent(self):
        match = VolleyMatch()
        player = match.players[1]
        player.y = 170
        ball = VolleyBall(player.x, 145, 0, 0)
        self.assertFalse(VolleyAI('EASY').controls(player, ball).spike)
        self.assertTrue(VolleyAI('HARD').controls(player, ball).spike)
        ai = VolleyAI('HARD')
        match.players[0].x = 50
        near = ai.attack_velocity(ball, match.players[0])[0]
        match.players[0].x = 170
        far = ai.attack_velocity(ball, match.players[0])[0]
        self.assertLess(far, near)
        self.assertTrue(-300 <= far <= -125)

    def test_ai_movement_has_no_speed_or_position_cheat(self):
        match = VolleyMatch(difficulty='HARD')
        match.start()
        before = match.players[1].x
        match.ball = VolleyBall(230, 180, 0, 50)
        match.update(.1)
        self.assertLessEqual(abs(match.players[1].x-before), 155*.1+.001)
        match = VolleyMatch(2, difficulty='HARD')
        match.start()
        before = match.players[1].x
        match.update(.1, [VolleyInput(), VolleyInput()])
        self.assertEqual(match.players[1].x, before)
