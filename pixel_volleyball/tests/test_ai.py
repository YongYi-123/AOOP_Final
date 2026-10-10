import unittest
from pixel_volleyball.ai import VolleyAI
from pixel_volleyball.model import VolleyMatch, VolleyBall, VolleyInput


class AITests(unittest.TestCase):
    def test_predicts_gravity_and_wall_reflection(self):
        self.assertAlmostEqual(VolleyAI.predict(VolleyBall(300, 180, 0, 50)), 300)
        self.assertLess(VolleyAI.predict(VolleyBall(350, 170, 250, 100)), 350)

    def test_reaction_is_limited_with_bounded_prediction_error(self):
        player = VolleyMatch().players[1]
        ball = VolleyBall(250, 180, 0, 80)
        ai = VolleyAI()
        for _ in range(120):
            ai.controls(player, ball, 1/120)
        self.assertTrue(8 <= ai.decisions <= 12)
        self.assertLessEqual(abs(ai.target - 250), 4)
        self.assertGreater(abs(ai.target - 250), .1)

    def test_sandra_times_swing_before_head_contact(self):
        match = VolleyMatch()
        player = match.players[1]
        player.y, player.vy = 170, -40
        ball = VolleyBall(player.x, 145, 0, 100)
        ai = VolleyAI()
        self.assertTrue(ai.controls(player, ball).spike)
        player.attack.update(.01, True, True)
        self.assertFalse(ai.controls(player, ball).spike)
        player.attack.age = 1
        player.attack.held = False
        ball.y = 200
        self.assertFalse(ai.controls(player, ball).spike)

    def test_ai_movement_has_no_speed_or_position_cheat(self):
        match = VolleyMatch()
        match.start()
        before = match.players[1].x
        match.ball = VolleyBall(230, 180, 0, 50)
        match.update(.1)
        self.assertLessEqual(abs(match.players[1].x-before), 155*.1+.001)
        match = VolleyMatch(2)
        match.start()
        before = match.players[1].x
        match.update(.1, [VolleyInput(), VolleyInput()])
        self.assertEqual(match.players[1].x, before)

    def test_sandra_receives_descending_ball(self):
        match = VolleyMatch()
        match.start()
        match.serve_delay = 0
        match.ball = VolleyBall(280,180,0,100)
        events = []
        for _ in range(90):
            match.update(1/120)
            events.extend(match.events)
        self.assertIn('hit', events)

    def test_unreachable_fast_shot_can_beat_sandra(self):
        match = VolleyMatch()
        match.start()
        match.serve_delay = 0
        match.ball = VolleyBall(365,230,0,300)
        match.update(.1)
        self.assertEqual(match.points, [1,0])

    def test_sandra_does_not_rejump_while_airborne_or_after_hit(self):
        match = VolleyMatch()
        player = match.players[1]
        ai = VolleyAI()
        ball = VolleyBall(player.x,120,0,80)
        self.assertTrue(ai.controls(player,ball).jump)
        self.assertFalse(ai.controls(player,ball).jump)
        player.y = 180
        ai.jump_wait = 0
        self.assertFalse(ai.controls(player,ball).jump)
        player.y = 244
        player.hit_cooldown = .1
        self.assertFalse(ai.controls(player,ball).jump)

    def test_sandra_executes_legal_smash_in_live_physics(self):
        match = VolleyMatch()
        match.start()
        match.serve_delay = 0
        match.ball = VolleyBall(310,110,0,60)
        events = []
        for _ in range(120):
            match.update(1/120)
            events.extend(match.events)
        self.assertIn('spike', events)
