import unittest
from pixel_volleyball.model import *


class VolleyPhysicsTests(unittest.TestCase):
    def setUp(self):
        self.match = VolleyMatch(2)
        self.match.start()
        self.match.serve_delay = 0

    def test_jump_gravity_and_half_court_boundaries(self):
        m = self.match
        m.update(.1, [VolleyInput(1, True), VolleyInput(-1, True)])
        self.assertLess(m.players[0].y, FLOOR - 14)
        for _ in range(20):
            m.update(.1, [VolleyInput(1), VolleyInput(-1)])
        self.assertLessEqual(m.players[0].x, NET_X - 18)
        self.assertGreaterEqual(m.players[1].x, NET_X + 18)
        self.assertEqual(m.players[0].y, FLOOR - 14)

    def test_floor_awards_opposite_side_and_resets_serve(self):
        m = self.match
        m.ball = VolleyBall(40, FLOOR - 5, 0, 50)
        m.update(.02)
        self.assertEqual(m.points, [0, 1])
        self.assertGreater(m.serve_delay, 0)

    def test_net_and_walls_bounce_without_tunnelling(self):
        m = self.match
        m.ball = VolleyBall(180, 190, 285, 0)
        m.update(.1)
        self.assertLess(m.ball.x, NET_X)
        self.assertLess(m.ball.vx, 0)
        m.ball = VolleyBall(370, 90, 200, 0)
        m.update(.1)
        self.assertLess(m.ball.vx, 0)

    def test_normal_receive_and_airborne_spike(self):
        m = self.match
        player = m.players[0]
        m.ball = VolleyBall(player.x, player.y - 18, 0, 100)
        m._player_collision(player)
        self.assertLess(m.ball.vy, 0)
        self.assertIn("hit", m.events)
        player.y = 170
        player.attack.age, player.hit_cooldown = .05, 0
        m.ball = VolleyBall(player.x, player.y - 18, 0, 100)
        m._player_collision(player)
        self.assertGreater(m.ball.vy, -360)
        self.assertGreater(m.ball.vx, 250)

    def test_pause_freezes_physics_and_finished_outcome_is_immutable(self):
        m = self.match
        m.toggle_pause()
        before = (m.ball.x, m.ball.y, m.elapsed)
        m.update(.1)
        self.assertEqual((m.ball.x, m.ball.y, m.elapsed), before)
        m.toggle_pause()
        for _ in range(5):
            m.award_point(0)
        self.assertEqual(m.state, MatchState.FINISHED)
        outcome = m.outcome
        m.award_point(1)
        m.update(.1)
        self.assertIs(m.outcome, outcome)
        self.assertEqual(m.outcome.points, (5, 0))

    def test_solo_ai_moves_and_plays_rallies(self):
        m = VolleyMatch(1)
        m.start()
        before = m.players[1].x
        m.ball = VolleyBall(250, 140, 0, 0)
        m.serve_delay = 0
        m.update(.1)
        self.assertLess(m.players[1].x, before)
        hits = 0
        crossed = False
        for _ in range(1500):
            m.update(1 / 60)
            hits += m.events.count("hit") + m.events.count("spike")
            crossed |= m.ball.x < NET_X
        self.assertGreater(hits, 2)
        self.assertTrue(crossed)

    def test_large_frame_stalls_are_bounded(self):
        self.match.update(10)
        self.assertLessEqual(self.match.elapsed, .101)
