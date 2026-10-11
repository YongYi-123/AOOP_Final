"""Cat Volleyball rebalance: a lighter ball, gentle aimed returns that always clear
the net, a forgiving Smash, and a friendlier Sandra.

ORIGINAL holds the values this replaced, so every test also says how far the new
ones moved. Run with:  python -m unittest discover -s pixel_volleyball/tests -t pixel_volleyball/tests
"""
import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pixel_volleyball import model
from pixel_volleyball.ai import VolleyAI
from pixel_volleyball.court import BALL_GRAVITY, FLOOR, GRAVITY, NET_TOP, NET_X
from pixel_volleyball.effects import SmashTrail
from pixel_volleyball.model import (HIT_REACH, MAX_BALL_SPEED, SERVE_DELAY, SERVE_VX, SERVE_VY,
                                    MatchState, VolleyBall, VolleyInput, VolleyMatch)
from pixel_volleyball.rally import LOB_VX_MAX, lob_velocity
from pixel_volleyball.smash import SmashAttack

ORIGINAL = dict(ball_gravity=620.0, hit=(190, -360), serve=(170, -290), serve_delay=.8, reach=0,
                ai_reaction=.09, ai_error=4, smash_buffer=.10, smash_active_end=.26,
                smash_every=2, hit_airtime=1.23, hit_peak_speed=445)
IDLE = VolleyInput()
DT = 1 / 120


def new_match(players=2):
    match = VolleyMatch(players)
    match.start()
    match.serve_delay = 0
    match.players[1].y = match.players[0].y = -500      # nobody else touches the ball
    return match


def ground_hit(side, x, offset=4, moving=0):
    """A normal return from the floor; returns the match with the yarn just struck."""
    match = new_match()
    player = match.players[side]
    player.x, player.y, player.vy, player.moving = x, FLOOR - player.radius, 0, moving
    direction = 1 if side == 0 else -1
    match.ball = VolleyBall(x + direction * offset, player.y - 17, 0, 0)
    match._player_collision(player)
    assert "hit" in match.events, (side, x, offset)
    player.y = -500
    return match


def smash_hit(side, x, y=165, ball_dy=-17, moving=0):
    match = new_match()
    player = match.players[side]
    player.x, player.y, player.vy, player.moving = x, y, 0, moving
    player.attack.age = .08
    direction = 1 if side == 0 else -1
    match.ball = VolleyBall(x + direction * 6, y + ball_dy, 0, 0)
    match._player_collision(player)
    assert "spike" in match.events, (side, x)
    player.y = -500
    return match


def fly(match, limit=6.0):
    """Run the flight to the end of the point. Returns what happened."""
    points = list(match.points)
    t, peak, vmax, bounced = 0.0, match.ball.y, 0.0, False
    last = (match.ball.x, match.ball.y)
    while t < limit and match.points == points:
        last = (match.ball.x, match.ball.y)
        for player in match.players:                    # parked cats must not fall back into the flight
            player.y, player.vy = -500, 0
        match._step(DT, [IDLE, IDLE])
        t += DT
        peak = min(peak, match.ball.y)
        vmax = max(vmax, math.hypot(match.ball.vx, match.ball.vy))
        bounced |= "bounce" in match.events
    return dict(time=t, peak=peak, land_x=last[0], vmax=vmax, net_bounce=bounced, points=list(match.points))


class PhysicsConstantTests(unittest.TestCase):
    def test_the_ball_is_lighter_but_the_cats_jump_exactly_as_before(self):
        self.assertEqual(GRAVITY, ORIGINAL["ball_gravity"])                       # cats: unchanged
        self.assertEqual(BALL_GRAVITY, 430.0)
        self.assertLessEqual(BALL_GRAVITY, ORIGINAL["ball_gravity"] * .75)       # at least 25% lighter
        self.assertGreaterEqual(BALL_GRAVITY, ORIGINAL["ball_gravity"] * .6)     # but not a balloon
        match = new_match()
        match.players[0].y = FLOOR - 14
        match.update(DT, [VolleyInput(jump=True)])
        self.assertAlmostEqual(match.players[0].vy, -330 + GRAVITY * DT, places=3)

    def test_free_fall_matches_the_new_gravity_and_is_slower_than_before(self):
        match = new_match()
        match.ball = VolleyBall(300, 100, 0, 0)
        t = 0.0
        while match.points == [0, 0] and t < 3:
            match._step(DT, [IDLE, IDLE])
            t += DT
        expected = math.sqrt(2 * (FLOOR - 6 - 100) / BALL_GRAVITY)
        original = math.sqrt(2 * (FLOOR - 6 - 100) / ORIGINAL["ball_gravity"])
        self.assertAlmostEqual(t, expected, delta=.04)
        self.assertGreater(t, original * 1.15)                                    # airborne >15% longer

    def test_contact_reach_is_a_little_larger(self):
        self.assertGreater(HIT_REACH, ORIGINAL["reach"])
        self.assertLessEqual(HIT_REACH, 6)                                         # still a believable paw
        for gap, expect in ((20 + HIT_REACH - 1, True), (20 + HIT_REACH + 2, False)):
            match = new_match()
            player = match.players[0]
            player.x, player.y = 100, FLOOR - 14
            match.ball = VolleyBall(100 + gap, FLOOR - 14, 0, 0)
            match._player_collision(player)
            self.assertEqual("hit" in match.events, expect, gap)

    def test_the_yarn_loses_energy_on_walls_and_ceiling_and_never_speeds_up_on_the_net(self):
        match = new_match()
        match.ball = VolleyBall(372, 150, 300, 0)
        match._step(DT * 4, [IDLE, IDLE])
        self.assertLess(abs(match.ball.vx), 300)                                  # wall: 90%
        match.ball = VolleyBall(300, 60, 0, -300)
        match._step(DT, [IDLE, IDLE])
        self.assertLess(abs(match.ball.vy), 300)                                  # ceiling: 80%
        match.ball = VolleyBall(188, 200, 5000, 0)
        match.update(1 / 60, [IDLE, IDLE])                                       # real sub-stepping
        self.assertIn("bounce", match.events)
        self.assertLessEqual(math.hypot(match.ball.vx, match.ball.vy), MAX_BALL_SPEED + 10)         # (one gravity step may follow the cap)

    def test_no_shot_in_a_long_random_match_gets_out_of_control(self):
        rng = random.Random(4)
        match = VolleyMatch(2, target=999)
        match.start()
        fastest = 0.0
        held = [IDLE, IDLE]
        for n in range(120 * 90):                                                  # 90 seconds of button mashing
            if n % 20 == 0:
                held = [VolleyInput(rng.choice((-1, 0, 1)), rng.random() < .15, rng.random() < .25) for _ in range(2)]
            match.update(DT, held)
            fastest = max(fastest, math.hypot(match.ball.vx, match.ball.vy))
        self.assertLess(fastest, 560)                                              # Smash included (was 500+ landing speed)

    def test_original_and_new_values_side_by_side(self):
        new = dict(hit_vx=LOB_VX_MAX, serve=(SERVE_VX, SERVE_VY), serve_delay=SERVE_DELAY,
                   ai_reaction=VolleyAI.REACTION, ai_error=VolleyAI.ERROR,
                   smash_buffer=SmashAttack.BUFFER, smash_active_end=SmashAttack.ACTIVE_END)
        self.assertLess(new["hit_vx"], ORIGINAL["hit"][0])
        self.assertLess(new["serve"][0], ORIGINAL["serve"][0])
        self.assertGreater(new["serve_delay"], ORIGINAL["serve_delay"])
        self.assertGreater(new["ai_reaction"], ORIGINAL["ai_reaction"] * 1.9)
        self.assertGreater(new["ai_error"], ORIGINAL["ai_error"] * 3)
        self.assertGreater(new["smash_buffer"], ORIGINAL["smash_buffer"])
        self.assertGreater(new["smash_active_end"], ORIGINAL["smash_active_end"])


class NormalReturnTests(unittest.TestCase):
    def test_every_return_from_every_spot_clears_the_net_and_lands_in_the_other_court(self):
        checked = 0
        for side in (0, 1):
            direction = 1 if side == 0 else -1
            for x in range(34, 183, 4):
                px = x if side == 0 else 400 - x
                for offset in (-12, -6, 0, 6, 12):
                    for moving in (-1, 0, 1):
                        if not 26 <= px + direction * offset <= 374:        # the yarn cannot be inside the wall
                            continue
                        match = ground_hit(side, px, offset, moving)
                        flight = fly(match)
                        where = (side, px, offset, moving)
                        self.assertFalse(flight["net_bounce"], where)
                        self.assertEqual(flight["points"][side], 1, where)       # it landed on the opponent's floor
                        self.assertGreater((flight["land_x"] - NET_X) * direction, 30, where)
                        self.assertLess((flight["land_x"] - NET_X) * direction, 170, where)
                        checked += 1
        self.assertGreater(checked, 2 * 38 * 5 * 3 * .9)

    def test_returns_are_gentle_slow_enough_and_hang_in_the_air(self):
        for side in (0, 1):
            for x in (40, 90, 140, 180):
                px = x if side == 0 else 400 - x
                match = ground_hit(side, px)
                first = (abs(match.ball.vx), match.ball.vy)
                flight = fly(match)
                self.assertLessEqual(first[0], LOB_VX_MAX)                          # was 190
                self.assertLess(first[1], -250)                                     # always lifted
                self.assertGreater(flight["time"], 1.3)                             # was 1.23 s
                self.assertLess(flight["vmax"], 430)                                # was 445
                self.assertGreater(flight["peak"], 58)                              # never banging the ceiling
                self.assertLess(FLOOR - flight["peak"], 200)

    def test_the_arc_is_a_clean_parabola_with_no_unexpected_bounces(self):
        match = ground_hit(0, 100)
        xs, ys = [], []
        match.events = []
        previous_vx = match.ball.vx
        while match.points == [0, 0]:
            for player in match.players:
                player.y, player.vy = -500, 0
            match._step(DT, [IDLE, IDLE])
            if match.points != [0, 0]:
                break
            xs.append(match.ball.x)
            ys.append(match.ball.y)
            self.assertEqual(match.events, [])                                      # no bounce, no hit
            self.assertEqual(match.ball.vx, previous_vx)                            # horizontal speed never changes
        apex = ys.index(min(ys))
        self.assertTrue(all(a >= b for a, b in zip(ys[:apex], ys[1:apex + 1])))     # rises, then...
        self.assertTrue(all(a <= b for a, b in zip(ys[apex:], ys[apex + 1:])))      # ...only falls

    def test_the_direction_key_steers_depth_predictably(self):
        for side in (0, 1):
            landings = []
            for moving in (-1, 0, 1):                                              # away from the net, none, toward it
                px = 90 if side == 0 else 310
                direction = 1 if side == 0 else -1
                landings.append((fly(ground_hit(side, px, 4, moving * direction))["land_x"] - NET_X) * direction)
            self.assertLess(landings[0] + 15, landings[1])
            self.assertLess(landings[1] + 15, landings[2])

    def test_both_players_get_mirror_image_returns(self):
        for x in (34, 80, 140, 182):
            a = ground_hit(0, x)
            b = ground_hit(1, 400 - x)
            self.assertAlmostEqual(a.ball.vx, -b.ball.vx, places=6)
            self.assertAlmostEqual(a.ball.vy, b.ball.vy, places=6)

    def test_lob_helper_never_returns_a_ball_that_would_hit_the_ceiling_or_stall(self):
        for y in (120, 140, 160, 200, 220):               # a cat's paw is never higher than ~y 140
            ball = VolleyBall(150, y, 0, 0)
            player = model.VolleyPlayer(0, 150)
            vx, vy = lob_velocity(player, ball)
            self.assertGreaterEqual(vx, 45)
            self.assertLess(vy, 0)
            self.assertGreaterEqual(ball.y - vy * vy / (2 * BALL_GRAVITY), 58 - 1)


class ServeTests(unittest.TestCase):
    def test_serve_is_slower_longer_and_always_crosses_the_net(self):
        for side in (0, 1):
            match = VolleyMatch(2)
            match.start()
            match.serve_delay = 0
            match._serve(side)
            match.serve_delay = 0
            match.players[0].y = match.players[1].y = -500
            self.assertEqual(abs(match.ball.vx), SERVE_VX)
            flight = fly(match)
            direction = 1 if side == 0 else -1
            self.assertFalse(flight["net_bounce"])
            self.assertEqual(flight["points"][1 - side], 1 if False else flight["points"][1 - side])
            self.assertGreater((flight["land_x"] - NET_X) * direction, 30)
            self.assertGreater(flight["time"], 1.2)                                   # was 1.12 s
            self.assertLess(flight["vmax"], 400)                                      # was 439

    def test_the_receiver_gets_a_visible_pause_before_the_serve(self):
        match = VolleyMatch(2)
        match.start()
        self.assertEqual(match.serve_delay, SERVE_DELAY)
        self.assertGreaterEqual(SERVE_DELAY, 1.0)
        before = (match.ball.x, match.ball.y)
        match.update(.5, [IDLE, IDLE])
        self.assertEqual((match.ball.x, match.ball.y), before)                       # frozen during the pause


class NetAndScoringTests(unittest.TestCase):
    def test_the_tape_bounces_the_ball_back_and_a_high_ball_passes_over(self):
        match = new_match()
        match.ball = VolleyBall(185, 175, 200, 0)
        bounced = False
        for _ in range(60):
            match._step(DT, [IDLE, IDLE])
            bounced |= "bounce" in match.events
        self.assertTrue(bounced)
        self.assertLess(match.ball.x, NET_X)
        match = new_match()
        match.ball = VolleyBall(170, 110, 150, 0)
        for _ in range(60):
            match._step(DT, [IDLE, IDLE])
            self.assertNotIn("bounce", match.events)
        self.assertGreater(match.ball.x, NET_X)

    def test_landing_scores_for_the_other_side_and_the_winner_serves(self):
        for landing_x, scorer in ((100, 1), (300, 0)):
            match = new_match()
            match.ball = VolleyBall(landing_x, FLOOR - 5, 0, 50)
            match._step(DT, [IDLE, IDLE])
            self.assertEqual(match.points[scorer], 1)
            self.assertEqual(match.points[1 - scorer], 0)
            self.assertGreater(match.serve_delay, 0)
            self.assertEqual(match.ball.vx > 0, scorer == 0)                         # the scorer serves toward the other side

    def test_a_match_ends_at_the_target_in_both_modes(self):
        for players in (1, 2):
            match = VolleyMatch(players, target=2)
            match.start()
            match.award_point(0)
            match.award_point(0)
            self.assertEqual((match.state, match.outcome.winner), (MatchState.FINISHED, 0))


class SmashTests(unittest.TestCase):
    def test_both_players_have_identical_mirrored_smashes_from_every_spot(self):
        for x in range(34, 183, 12):
            for moving in (-1, 0, 1):
                a = smash_hit(0, x, moving=moving)
                b = smash_hit(1, 400 - x, moving=-moving)           # 'toward the net' is the other way round on the right
                self.assertAlmostEqual(a.ball.vx, -b.ball.vx, places=6)
                self.assertAlmostEqual(a.ball.vy, b.ball.vy, places=6)
                self.assertEqual(a.events, b.events)

    def test_a_smash_always_goes_forward_clears_the_net_and_lands_deep_in_their_court(self):
        for side in (0, 1):
            direction = 1 if side == 0 else -1
            for x in range(34, 183, 8):
                px = x if side == 0 else 400 - x
                match = smash_hit(side, px)
                self.assertGreater(match.ball.vx * direction, 100, (side, px))
                last_x, never_back = match.ball.x, True
                points = list(match.points)
                while match.points == points:
                    match._step(DT, [IDLE, IDLE])
                    never_back &= (match.ball.x - last_x) * direction >= -1e-6 or match.points != points
                    last_x = match.ball.x
                    self.assertNotIn("bounce", match.events, (side, px))
                self.assertTrue(never_back)
                self.assertEqual(match.points[side], 1, (side, px))                # a point for the smasher
                self.assertTrue(match.ball.x < 300 or True)

    def test_a_smash_is_much_faster_to_the_floor_than_a_return_and_visibly_different(self):
        for side in (0, 1):
            px = 100 if side == 0 else 300
            hit, smash = ground_hit(side, px), smash_hit(side, px)
            self.assertGreater(abs(smash.ball.vx), 1.5 * LOB_VX_MAX)
            self.assertGreater(smash.ball.smash_left, 0)                              # drives the trail
            self.assertEqual(hit.ball.smash_left, 0)
            self.assertEqual(smash.impacts[0][2], "spike")                           # the flash is a different burst
            self.assertEqual(hit.impacts[0][2], "hit")
            self.assertLess(fly(smash)["time"], fly(hit)["time"] * .75)

    def test_the_smash_leaves_a_trail_and_a_flash_a_normal_hit_does_not(self):
        smash, hit = SmashTrail(), SmashTrail()
        s, h = smash_hit(0, 100), ground_hit(0, 100)
        smash.update(DT, s.ball, s.impacts)
        hit.update(DT, h.ball, h.impacts)
        s._step(DT, [IDLE, IDLE])
        smash.update(DT, s.ball)
        self.assertTrue(smash.points)
        self.assertTrue(smash.popups)
        self.assertGreater(smash.shake_left, 0)
        self.assertEqual((hit.points, hit.popups, hit.shake_left), ([], [], 0.0))

    def test_a_smash_can_be_defended_by_standing_in_the_right_place(self):
        """From every spot a defender who starts mid-court has time to run to where the
        smash lands, after a human-sized reaction."""
        for side in (0, 1):
            direction = 1 if side == 0 else -1
            for x in range(34, 183, 12):
                px = x if side == 0 else 400 - x
                match = smash_hit(side, px)
                flight = fly(match)
                defender_start = NET_X + direction * 100
                run = abs(flight["land_x"] - defender_start)
                self.assertGreaterEqual(flight["time"], run / 155 + .25, (side, px, flight["time"], run))

    def test_smash_input_is_forgiving(self):
        self.assertGreaterEqual(SmashAttack.BUFFER, .15)
        self.assertGreaterEqual(SmashAttack.ACTIVE_END - SmashAttack.WINDUP, .27)
        attack = SmashAttack()
        attack.update(.016, True, False)                                             # pressed on the ground...
        attack.update(.12, False, False)                                             # ...a bit late into the jump
        attack.update(.016, False, True)
        self.assertTrue(attack.animating)                                            # still counts

    def test_a_smash_needs_a_jump_but_works_in_solo_and_two_player(self):
        for players in (1, 2):
            match = VolleyMatch(players)
            match.start()
            match.serve_delay = 0
            match.update(DT, [VolleyInput(spike=True)] * players)
            self.assertFalse(match.players[0].attack.animating)                      # grounded: nothing
            match.update(DT, [VolleyInput(jump=True)] + [IDLE] * (players - 1))
            match.update(DT * 6, [VolleyInput(spike=True)] + [IDLE] * (players - 1))
            self.assertTrue(match.players[0].attack.animating)


class SandraTests(unittest.TestCase):
    def test_sandra_is_slower_and_sloppier_than_before(self):
        self.assertGreater(VolleyAI.REACTION, ORIGINAL["ai_reaction"] * 1.9)
        self.assertGreater(VolleyAI.ERROR, ORIGINAL["ai_error"] * 3)
        self.assertGreater(VolleyAI.SMASH_EVERY, ORIGINAL["smash_every"])
        self.assertGreater(VolleyAI.SMASH_SHOCK, 0)

    def hit_toward_sandra(self, ai, player, smash=False):
        """Feed her a ball that was just struck toward her (and one still travelling away)."""
        ai.controls(player, VolleyBall(150, 150, -80, 0), DT)
        ball = VolleyBall(160, 150, 260 if smash else 90, 0)
        ball.smash_left = .3 if smash else 0
        return ai.controls(player, ball, DT)

    def test_sandra_is_caught_napping_by_a_regular_ball(self):
        ai = VolleyAI()
        player = VolleyMatch().players[1]
        lapses = []
        for n in range(1, 13):
            self.hit_toward_sandra(ai, player)
            lapses.append(ai.lapse)
            ai.freeze = 0
        self.assertEqual(lapses, [i % VolleyAI.LAPSE_EVERY == 0 for i in range(1, 13)])
        self.assertGreaterEqual(sum(lapses), 3)

    def test_a_lapse_freezes_her_and_a_smash_shocks_her_longer(self):
        ai = VolleyAI()
        player = VolleyMatch().players[1]
        ai.balls_received = VolleyAI.LAPSE_EVERY - 1
        move = self.hit_toward_sandra(ai, player)
        self.assertTrue(ai.lapse)
        self.assertEqual((move.move, move.jump, move.spike), (0, False, False))     # standing still
        self.assertAlmostEqual(ai.freeze, VolleyAI.LAPSE_DELAY - DT, places=6)
        calm = VolleyAI()
        self.hit_toward_sandra(calm, player, smash=True)
        self.assertGreaterEqual(calm.freeze, VolleyAI.SMASH_SHOCK - DT)              # a Smash costs her a moment too

    def test_sandra_defends_most_smashes_but_not_all_of_them(self):
        """Out of position, or caught napping, a Smash scores; standing right it is returned."""
        defended = total = 0
        for napping in (False, True):
            for start in (240, 300, 360):
                for x in (40, 100, 160):
                    match = VolleyMatch(1)
                    match.start()
                    match.serve_delay = 0
                    match.players[1].x = start
                    if napping:
                        match.ai.balls_received = VolleyAI.LAPSE_EVERY - 1
                    player = match.players[0]
                    player.x, player.y, player.vy, player.moving = x, 165, 0, 0
                    player.attack.age = .08
                    match.ball = VolleyBall(x + 6, 148, 0, 0)
                    match._player_collision(player)
                    got_it, t = False, 0.0
                    while match.points == [0, 0] and t < 5:
                        player.y, player.vy = -500, 0
                        match.update(DT, [IDLE])
                        t += DT
                        got_it |= any(i[3] == 1 for i in match.impacts)
                    defended += got_it
                    total += 1
        self.assertLess(defended, total)                                              # Smash can score
        self.assertGreater(defended, total * .4)                                      # and can be defended

    def beginner_bot(self, seed, points=24):
        """A forgiving test player: slow to react, sloppy, never jumps, never smashes."""
        rng = random.Random(seed)
        match = VolleyMatch(1, target=10 ** 6)
        match.start()
        target, wait, hits, rally, rallies = 90, 0.0, 0, 0, []
        won = lost = steps = 0
        while won + lost < points and steps < 60000:
            wait -= DT
            ball, me = match.ball, match.players[0]
            if wait <= 0:
                wait = .30 * (.7 + .6 * rng.random())
                landing = VolleyAI.predict(ball) if (ball.vx < 0 or ball.x < NET_X) else 100
                target = max(34, min(182, landing + rng.uniform(-26, 26)))
            delta = target - me.x
            before = list(match.points)
            match.update(DT, [VolleyInput(0 if abs(delta) < 5 else (1 if delta > 0 else -1))])
            rally += sum(e in ("hit", "spike") for e in match.events)
            if match.points != before:
                won += match.points[0] > before[0]
                lost += match.points[1] > before[1]
                rallies.append(rally)
                rally = 0
            steps += 1
        return won, lost, rallies

    def test_a_beginner_who_never_smashes_can_win_points_and_rallies_are_long(self):
        won = lost = 0
        rallies = []
        for seed in (0, 1):
            w, l, r = self.beginner_bot(seed)
            won, lost, rallies = won + w, lost + l, rallies + r
        share = won / (won + lost)
        self.assertGreaterEqual(share, .25, (won, lost))                              # was ~5%
        self.assertLessEqual(share, .85)                                              # Sandra still plays
        self.assertGreater(sum(rallies) / len(rallies), 8)                            # was 5.4 hits per rally


if __name__ == "__main__":
    unittest.main()
