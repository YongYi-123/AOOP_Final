import unittest
import math
from pixel_volleyball.model import VolleyMatch, VolleyBall, VolleyInput, NET_X


class ContactTests(unittest.TestCase):
    def match(self):
        match = VolleyMatch(2)
        match.start()
        match.serve_delay = 0
        return match

    def test_jump_reaches_ball_above_net_without_larger_hitbox(self):
        match = self.match()
        player = match.players[0]
        heights = []
        for frame in range(50):
            match.update(1 / 120, [VolleyInput(jump=frame == 0)])
            heights.append(player.y)
        self.assertLess(min(heights) - player.radius, 162 - 6)
        self.assertEqual(player.radius, 14)

    def test_fast_ball_cannot_pass_through_player(self):
        for fps in (30, 60, 144):
            match = self.match()
            player = match.players[0]
            match.ball = VolleyBall(player.x, player.y - 60, 0, 5000)
            events = []
            for _ in range(math.ceil(.02 * fps)):
                match.update(1 / fps)
                events.extend(match.events)
            self.assertIn('hit', events)
            self.assertEqual(match.points, [0, 0])

    def test_fast_ball_cannot_cross_net(self):
        match = self.match()
        match.ball = VolleyBall(170, 190, 5000, 0)
        match.update(.015)
        self.assertLess(match.ball.x, NET_X)
        self.assertLess(match.ball.vx, 0)

    def test_cooldown_preserves_contact_separation(self):
        match = self.match()
        player = match.players[0]
        player.hit_cooldown = .1
        match.ball = VolleyBall(player.x, player.y - 5, 0, 100)
        match._player_collision(player)
        self.assertGreaterEqual(math.hypot(match.ball.x-player.x, match.ball.y-player.y), 20)
        self.assertNotIn('hit', match.events)
