import unittest
from pixel_volleyball.smash import SmashAttack
from pixel_volleyball.model import VolleyMatch, VolleyBall, VolleyInput
from pixel_volleyball.court import NET_TOP


class SmashTests(unittest.TestCase):
    def test_swing_has_windup_window_and_requires_release(self):
        attack = SmashAttack()
        attack.update(.01, True, True)
        self.assertFalse(attack.active)
        attack.update(.04, True, True)
        self.assertTrue(attack.active)
        attack.update(.2, True, True)
        self.assertTrue(attack.active)
        attack.update(.05, True, True)
        self.assertFalse(attack.active)
        attack.update(1, True, True)
        self.assertFalse(attack.animating)
        attack.update(.01, False, True)
        attack.update(.01, True, True)
        self.assertTrue(attack.animating)

    def test_ground_press_does_not_arm_later_jump(self):
        attack = SmashAttack()
        attack.update(.01, True, False)
        attack.update(attack.BUFFER + .01, True, True)
        self.assertFalse(attack.active)
        self.assertFalse(attack.animating)

    def match(self, side=0):
        match = VolleyMatch(2)
        match.start()
        match.serve_delay = 0
        player = match.players[side]
        player.y = 170
        player.attack.age = .05
        match.ball = VolleyBall(player.x, 152, 0, 100)
        return match, player

    def test_airborne_contact_smashes_once_toward_opponent(self):
        for side in (0, 1):
            match, player = self.match(side)
            match._player_collision(player)
            self.assertIn('spike', match.events)
            self.assertTrue(player.attack.connected)
            self.assertEqual(match.ball.vx > 0, side == 0)
            self.assertGreaterEqual(abs(match.ball.vx), 250)
            self.assertGreater(match.ball.smash_left, 0)
            player.hit_cooldown = 0
            match.ball.y = player.y - 18
            match._player_collision(player)
            self.assertEqual(match.events.count('spike'), 1)

    def test_late_low_and_behind_contacts_receive_normally(self):
        for kind in ('late', 'low', 'behind'):
            match, player = self.match()
            if kind == 'late':
                player.attack.age = .3
            elif kind == 'low':
                player.y = 200
                match.ball.y = 182
            else:
                match.ball.x = player.x - 12
                match.ball.y = player.y - 12
            match._player_collision(player)
            self.assertIn('hit', match.events)
            self.assertNotIn('spike', match.events)

    def test_backcourt_smash_clears_net_and_direction_changes_power(self):
        match, player = self.match()
        for x in (34, 90, 182):
            player.x = x
            match.ball.x, match.ball.y = x, 150
            vx, vy = SmashAttack.velocity(player, match.ball)
            time = (200 - x) / vx
            self.assertLessEqual(150 + vy*time + 310*time*time, NET_TOP - match.ball.radius - 3 + .001)
        player.x, match.ball.x, match.ball.y = 90, 90, 150
        player.moving = 1
        fast = SmashAttack.velocity(player, match.ball)
        player.moving = -1
        slow = SmashAttack.velocity(player, match.ball)
        self.assertGreater(fast[0], slow[0])

    def test_pause_freezes_swing_and_restart_resets_it(self):
        match, player = self.match()
        match.toggle_pause()
        before = player.attack.age
        match.update(.1, [VolleyInput(spike=True)])
        self.assertEqual(player.attack.age, before)
        match._serve(0)
        self.assertFalse(player.attack.animating)

    def test_human_timed_smash_survives_different_frame_rates(self):
        for fps in (30, 60, 144):
            for side in (0, 1):
                match = VolleyMatch(2)
                match.start()
                match.serve_delay = 0
                player = match.players[side]
                player.y, player.vy = 174, -40
                match.ball = VolleyBall(player.x,144,0,100)
                controls = [VolleyInput(),VolleyInput()]
                controls[side] = VolleyInput(spike=True)
                events = []
                for _ in range(round(.2*fps)):
                    match.update(1/fps, controls)
                    events.extend(match.events)
                self.assertEqual(events.count('spike'),1,(fps,side,events))
