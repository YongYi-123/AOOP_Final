"""A Smash near the net used to be forced into a slow, floaty arc: the landing spot was
shallow, and the ball is only a few pixels above the tape, so only a long flight cleared it.
SmashAttack.velocity now looks a little deeper for a quicker flight (never past
SMASH_MAX_DEPTH), so a Smash struck near the net is a punchy downward shot, and a Smash
struck from the back keeps its depth and its steering.

Run with:  python -m unittest discover -s pixel_volleyball/tests -t pixel_volleyball/tests
"""
import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pixel_volleyball.court import BALL_GRAVITY, FLOOR, NET_X
from pixel_volleyball.model import VolleyBall, VolleyPlayer
from pixel_volleyball.smash import SmashAttack

BALL_Y = 140            # a typical Smash contact: just above the cat's apex head, a little over the tape


def shot(side, to_net, moving=0, y=BALL_Y, aim=None):
    """Velocity of a Smash struck `to_net` px from the net by `side`, mirrored for side 1.
    `moving` is +1 toward the net, -1 away (so P1 and P2 steer the same way)."""
    direction = 1 if side == 0 else -1
    x = NET_X - direction * to_net
    player = VolleyPlayer(side, x, y + 17)
    player.moving = moving * direction
    ball = VolleyBall(x + direction * 6, y, 0, 0)
    return ball, SmashAttack.velocity(player, ball, aim)


def fall_time(ball, vy):
    return (-vy + math.sqrt(vy * vy + 2 * BALL_GRAVITY * (FLOOR - ball.radius - ball.y))) / BALL_GRAVITY


def baseline(side, to_net, moving=0):
    """What the solver gave before: the quickest flight to the un-deepened landing spot."""
    direction = 1 if side == 0 else -1
    ball, _ = shot(side, to_net, moving)
    depth = 62 + .5 * max(0, to_net) + 22 * moving
    target = NET_X + direction * max(35, min(170, max(50, min(150, depth))))
    return SmashAttack._quickest(ball, target, (NET_X - ball.x) * direction, direction)


class SmashQuicknessTests(unittest.TestCase):
    def test_a_smash_near_the_net_is_quick_and_goes_downward(self):
        for side in (0, 1):
            for to_net in (20, 30):
                ball, (vx, vy) = shot(side, to_net)
                self.assertGreater(vy, 60, (side, to_net))                       # leaves the paw pointing down
                self.assertLessEqual(fall_time(ball, vy), .55, (side, to_net))   # and is on the floor in about half a second

    def test_it_is_never_slower_than_before_and_is_quicker_near_the_net(self):
        gained = 0
        for to_net in range(10, 140, 10):
            for moving in (-1, 0, 1):
                ball, (vx, vy) = shot(0, to_net, moving)
                old_vx, old_vy, old_flight = baseline(0, to_net, moving)
                now = fall_time(ball, vy)
                self.assertLessEqual(now, old_flight + .02, (to_net, moving))
                gained += old_flight - now > .1
        self.assertGreaterEqual(gained, 6)                                       # it matters in many spots, not one

    def test_the_landing_is_always_forward_in_court_and_never_at_the_back_wall(self):
        for side in (0, 1):
            direction = 1 if side == 0 else -1
            for to_net in range(5, 170, 5):
                for moving in (-1, 0, 1):
                    ball, (vx, vy) = shot(side, to_net, moving)
                    land = ball.x + vx * fall_time(ball, vy)
                    depth = (land - NET_X) * direction
                    self.assertGreater(vx * direction, 0)
                    self.assertTrue(35 <= depth <= SmashAttack.SMASH_MAX_DEPTH + 1, (side, to_net, moving, depth))

    def test_every_smash_still_clears_the_net(self):
        for side in (0, 1):
            direction = 1 if side == 0 else -1
            for to_net in range(5, 170, 5):
                ball, (vx, vy) = shot(side, to_net)
                self.assertTrue(SmashAttack._clears_net(ball, vx, vy, direction), (side, to_net))

    def test_p1_and_p2_get_mirror_image_smashes(self):
        for to_net in range(5, 170, 10):
            for moving in (-1, 0, 1):
                (b0, (vx0, vy0)), (b1, (vx1, vy1)) = shot(0, to_net, moving), shot(1, to_net, moving)
                self.assertAlmostEqual(vx0, -vx1, places=6)
                self.assertAlmostEqual(vy0, vy1, places=6)

    def test_the_move_key_still_steers_how_hard_and_deep_a_smash_goes(self):
        for to_net in (30, 60, 90, 120):
            fast, slow = shot(0, to_net, 1)[1], shot(0, to_net, -1)[1]
            self.assertGreaterEqual(fast[0], slow[0] - 1e-6, to_net)

    def test_sandras_aimed_smash_is_exactly_as_before(self):
        for aim in (60, 150):
            for to_net in (20, 60, 120):
                ball, got = shot(1, to_net, aim=aim)
                direction = -1
                target = NET_X + direction * max(35, min(170, (aim - NET_X) * direction))
                vx, vy, _ = SmashAttack._quickest(ball, target, (NET_X - ball.x) * direction, direction)
                self.assertEqual(got, (vx, vy))

    def test_the_quickest_flight_never_drops_below_the_minimum(self):
        for to_net in range(5, 170, 5):
            ball, (vx, vy) = shot(0, to_net)
            self.assertGreaterEqual(fall_time(ball, vy), SmashAttack.MIN_FLIGHT - .01, to_net)


if __name__ == "__main__":
    unittest.main()
