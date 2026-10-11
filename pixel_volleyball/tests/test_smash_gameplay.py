"""Smash as a gameplay mechanic: input, timing, trajectory, AI and court interaction."""
import math
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import unittest
import pygame
from pixel_volleyball.ai import VolleyAI
from pixel_volleyball.court import FLOOR, NET_TOP, NET_X
from pixel_volleyball.effects import SmashTrail
from pixel_volleyball.game import VolleyGame
from pixel_volleyball.keyboard import VolleyKeyboard
from pixel_volleyball.keyboard_hints import default_hints, hint_lines
from pixel_volleyball.model import MatchState, VolleyBall, VolleyInput, VolleyMatch
from pixel_volleyball.smash import SmashAttack

IDLE = VolleyInput()


def key(type_, code):
    return pygame.event.Event(type_, key=code)


def airborne_match(side=0, x=None, ball_dy=-17, y=165, swing_age=.08, players=2, solo=False):
    """A match with the player in the air, mid-swing, and the yarn on top of the paw."""
    match = VolleyMatch(1 if solo else players)
    match.start()
    match.serve_delay = 0
    player = match.players[side]
    if x is not None:
        player.x = x
    player.y, player.vy = y, 0
    player.attack.age = swing_age
    direction = 1 if side == 0 else -1
    match.ball = VolleyBall(player.x + direction * 6, player.y + ball_dy, 0, 0)
    match.players[1 - side].x = 215 if side == 0 else 185   # parked, never in the way
    match.players[1 - side].y = -500
    return match, player


def fly(match, limit=4.0):
    """Step the live physics until the point is decided; returns the flight record."""
    start_points = list(match.points)
    t, peak, rise_from = 0.0, match.ball.y, match.ball.y
    last = (match.ball.x, match.ball.y, match.ball.vx, match.ball.vy)
    while t < limit and match.points == start_points:
        last = (match.ball.x, match.ball.y, match.ball.vx, match.ball.vy)
        match._step(1 / 240, [IDLE, IDLE])
        peak = min(peak, match.ball.y)
        t += 1 / 240
    return dict(time=t, peak=peak, rise=rise_from - peak, events=list(match.events), land=last,
                angle=math.degrees(math.atan2(last[3], abs(last[2]))),
                speed=math.hypot(last[2], last[3]), points=list(match.points))


def strike(side, smash, x=100, y_contact=None):
    """One contact (normal hit from the ground, or a Smash in the air) then the flight."""
    direction = 1 if side == 0 else -1
    x = x if side == 0 else 400 - x
    if smash:
        match, player = airborne_match(side, x=x)
    else:
        match, player = airborne_match(side, x=x, y=FLOOR - 14, swing_age=1)
        match.ball = VolleyBall(x + direction * 6, FLOOR - 14 - 17, 0, 0)
    match._player_collision(player)
    first = dict(vx=match.ball.vx, vy=match.ball.vy, events=list(match.events))
    player.y = -500           # the hitter leaves; only the ball's flight matters now
    return first, fly(match), match


class SmashInputTests(unittest.TestCase):
    def test_standalone_keys_map_to_the_right_player_only(self):
        for local, key_a, key_b in ((1, pygame.K_SPACE, pygame.K_LSHIFT), (2, pygame.K_SPACE, pygame.K_LSHIFT)):
            keyboard = VolleyKeyboard()
            keyboard.feed(key(pygame.KEYDOWN, key_a))
            self.assertTrue(keyboard.controls(local)[0].spike)
            keyboard.feed(key(pygame.KEYUP, key_a))
            keyboard.controls(local)
            keyboard.feed(key(pygame.KEYDOWN, key_b))
            self.assertTrue(keyboard.controls(local)[0].spike)
        two = VolleyKeyboard()
        two.feed(key(pygame.KEYDOWN, pygame.K_SPACE))
        p1, p2 = two.controls(2)
        self.assertEqual((p1.spike, p2.spike), (True, False))
        for code in (pygame.K_RSHIFT, pygame.K_RCTRL):
            two = VolleyKeyboard()
            two.feed(key(pygame.KEYDOWN, code))
            p1, p2 = two.controls(2)
            self.assertEqual((p1.spike, p2.spike), (False, True))

    def test_a_tap_released_within_one_frame_is_not_lost(self):
        keyboard = VolleyKeyboard()
        keyboard.feed(key(pygame.KEYDOWN, pygame.K_RSHIFT))
        keyboard.feed(key(pygame.KEYUP, pygame.K_RSHIFT))
        self.assertTrue(keyboard.controls(2)[1].spike)
        self.assertFalse(keyboard.controls(2)[1].spike)      # consumed exactly once

    def test_smash_only_arms_in_the_air_and_never_changes_movement_or_jump(self):
        match = VolleyMatch(2)
        match.start()
        match.serve_delay = 0
        match.update(1 / 60, [VolleyInput(spike=True), IDLE])
        self.assertFalse(match.players[0].attack.animating)
        match.players[0].attack = SmashAttack()
        match.update(1 / 60, [VolleyInput(jump=True), IDLE])
        self.assertLess(match.players[0].y, FLOOR - 14)
        match.update(1 / 60, [VolleyInput(move=1, spike=True), IDLE])
        self.assertTrue(match.players[0].attack.animating)
        self.assertGreater(match.players[0].x, 90)


class SmashTimingTests(unittest.TestCase):
    def contact(self, age=None, dy=-17, y=165, side=0, dx=6):
        match, player = airborne_match(side, ball_dy=dy, y=y, swing_age=.08 if age is None else age)
        direction = 1 if side == 0 else -1
        match.ball.x = player.x + direction * dx
        match._player_collision(player)
        return match

    def test_activation_window_edges(self):
        edges = [(SmashAttack.WINDUP - .01, False), (SmashAttack.WINDUP + .01, True),
                 (SmashAttack.ACTIVE_END - .01, True), (SmashAttack.ACTIVE_END + .01, False)]
        for age, expect in edges:
            self.assertEqual('spike' in self.contact(age=age).events, expect, age)

    def test_window_is_wide_enough_for_a_human(self):
        self.assertGreaterEqual(SmashAttack.ACTIVE_END - SmashAttack.WINDUP, .2)

    def test_ball_must_be_above_the_paw_in_front_and_above_the_net(self):
        self.assertIn('spike', self.contact().events)
        self.assertNotIn('spike', self.contact(dy=-4).events)             # ball level with the body
        self.assertNotIn('spike', self.contact(y=190, dy=-17).events)     # ball under net height
        self.assertNotIn('spike', self.contact(dx=-14, dy=-12).events)    # behind the cat

    def test_out_of_reach_ball_is_not_touched(self):
        match, player = airborne_match()
        match.ball.x += 40
        match._player_collision(player)
        self.assertEqual(match.events, [])
        self.assertEqual((match.ball.vx, match.ball.vy), (0, 0))

    def test_swing_connects_exactly_once_and_cooldown_blocks_a_second_hit(self):
        match, player = airborne_match()
        match._player_collision(player)
        self.assertEqual(match.events, ['spike'])
        match.ball.x, match.ball.y = player.x + 6, player.y - 17
        match._player_collision(player)       # same swing, cooldown running: nothing new
        self.assertEqual(match.events, ['spike'])
        player.hit_cooldown = 0
        match.ball.x, match.ball.y = player.x + 6, player.y - 17
        match._player_collision(player)       # cooldown over but the swing is spent: normal hit
        self.assertEqual(match.events, ['spike', 'hit'])


class SmashBufferTests(unittest.TestCase):
    def test_press_just_before_takeoff_is_remembered(self):
        attack = SmashAttack()
        attack.update(.016, True, False)
        attack.update(.016, False, False)
        attack.update(.016, False, True)
        self.assertTrue(attack.animating)

    def test_press_too_early_is_forgotten(self):
        attack = SmashAttack()
        attack.update(.016, True, False)
        attack.update(SmashAttack.BUFFER + .05, False, False)
        attack.update(.016, False, True)
        self.assertFalse(attack.animating)

    def test_press_during_recovery_swings_the_moment_recovery_ends(self):
        attack = SmashAttack()
        attack.update(.016, True, True)
        attack.update(.016, False, True)
        attack.update(SmashAttack.RECOVER - .08, False, True)
        attack.update(.016, True, True)                       # pressed ~60 ms early
        self.assertFalse(attack.age < .01)
        attack.update(.06, False, True)
        self.assertTrue(attack.age < .05)

    def test_held_key_never_repeats_and_release_is_required(self):
        attack = SmashAttack()
        swings = 0
        for _ in range(180):
            before = attack.age
            attack.update(1 / 60, True, True)
            swings += attack.age < before
        self.assertEqual(swings, 1)
        attack.update(1 / 60, False, True)
        attack.age = 1
        attack.update(1 / 60, True, True)
        self.assertTrue(attack.animating)

    def test_holding_through_a_landing_does_not_swing_on_the_next_jump(self):
        match = VolleyMatch(2)
        match.start()
        match.serve_delay = 0
        match.ball = VolleyBall(300, 100, 0, 0)
        swings = 0
        for frame in range(200):
            was = match.players[0].attack.age
            match.update(1 / 60, [VolleyInput(jump=frame % 50 < 2, spike=frame == 5 or frame > 70), IDLE])
            swings += match.players[0].attack.age < was
        self.assertEqual(swings, 1)

    def live_jump(self, fps, side, press_at):
        """Jump at t=0 under a descending ball; tap Smash for one frame at `press_at` seconds."""
        match, player = airborne_match(side, y=FLOOR - 14, swing_age=1)
        player.vy = 0
        direction = 1 if side == 0 else -1
        match.ball = VolleyBall(player.x + direction * 6, 125, 0, 0)
        contacts = []
        for n in range(int(.7 * fps)):
            t = n / fps
            inputs = [IDLE, IDLE]
            inputs[side] = VolleyInput(jump=n == 0, spike=press_at <= t < press_at + 1 / fps)
            match.update(1 / fps, inputs)
            contacts += [e for e in match.events if e in ('spike', 'hit')]
        return contacts

    def test_press_window_is_wide_and_works_at_every_frame_rate(self):
        for fps in (30, 60, 144):
            for side in (0, 1):
                self.assertEqual(self.live_jump(fps, side, .15), ['spike'], (fps, side))
                self.assertEqual(self.live_jump(fps, side, .0)[:1], ['hit'], (fps, side))     # far too early
                self.assertEqual(self.live_jump(fps, side, .45)[:1], ['hit'], (fps, side))    # after contact
        working = [t / 100 for t in range(0, 50)
                   if self.live_jump(60, 0, t / 100)[:1] == ['spike']]
        self.assertGreaterEqual(working[-1] - working[0], .2)
        self.assertEqual(len(working), working[-1] * 100 - working[0] * 100 + 1)     # one unbroken window

    def test_one_press_in_the_air_never_produces_two_smashes(self):
        for fps in (30, 60, 144):
            contacts = self.live_jump(fps, 0, .15)
            self.assertEqual(contacts.count('spike'), 1)


class SmashTrajectoryTests(unittest.TestCase):
    def test_smash_flight_is_meaningfully_different_from_a_normal_hit(self):
        for side in (0, 1):
            hit_first, hit, _ = strike(side, False)
            smash_first, smash, _ = strike(side, True)
            self.assertEqual(hit_first['events'], ['hit'])
            self.assertEqual(smash_first['events'], ['spike'])
            # Normal return: the slow 190/-360 lob that climbs to the ceiling area.
            self.assertEqual((abs(hit_first['vx']), hit_first['vy']), (190, -360))
            self.assertGreater(hit['rise'], 80)
            self.assertGreater(hit['time'], 1.0)
            # Smash: faster, never climbs, and drops on the floor much sooner at a steep angle.
            self.assertLess(smash['time'], hit['time'] * .75)
            self.assertLess(smash['rise'], 20)
            self.assertGreaterEqual(smash['angle'], 45)
            self.assertGreater(abs(smash_first['vx']), abs(hit_first['vx']) + 60)
            self.assertGreater(smash['speed'], 400)
            self.assertGreater(smash['land'][3], 300)           # slamming down at landing

    def test_smash_scores_for_the_attacker_when_undefended(self):
        for side in (0, 1):
            _, flight, match = strike(side, True)
            self.assertEqual(flight['points'][side], 1)
            self.assertEqual(flight['points'][1 - side], 0)
            self.assertNotIn('bounce', flight['events'])

    def test_direction_depends_on_side_and_is_mirrored(self):
        for x in (40, 100, 160, 182):
            p1, f1, _ = strike(0, True, x=x)
            p2, f2, _ = strike(1, True, x=x)
            self.assertGreater(p1['vx'], 0)
            self.assertLess(p2['vx'], 0)
            self.assertAlmostEqual(p1['vx'], -p2['vx'], delta=.01)
            self.assertAlmostEqual(p1['vy'], p2['vy'], delta=.01)
            self.assertAlmostEqual(f1['land'][0], 400 - f2['land'][0], delta=.5)
            self.assertGreater(f1['land'][0], NET_X + 20)      # lands in the opponent's court

    def test_smash_clears_the_net_and_lands_inside_the_court_everywhere(self):
        for side in (0, 1):
            for x in range(30, 183, 8):
                for height in (118, 135, 150):
                    xx = x if side == 0 else 400 - x
                    match, player = airborne_match(side, x=xx, y=height + 17)
                    match.ball.y = height
                    match._player_collision(player)
                    self.assertIn('spike', match.events, (side, x, height))
                    flight = fly(match)
                    self.assertNotIn('bounce', flight['events'], (side, x, height))
                    landed = flight['land'][0]
                    self.assertTrue(30 < landed < 370, (x, landed))
                    self.assertGreater((landed - NET_X) * (1 if side == 0 else -1), 40)
                    self.assertEqual(flight['points'][side], 1, (side, x, height))

    def test_net_edge_cases_never_pass_through_or_fall_short(self):
        # A ball struck right beside the net is steep but still clears the tape.
        for side in (0, 1):
            xx = 182 if side == 0 else 218
            for height, steep in ((152, -60), (135, 60), (118, 120)):
                match, player = airborne_match(side, x=xx, y=height + 17)
                match._player_collision(player)
                self.assertGreater(match.ball.vy, steep, height)   # the higher the contact, the steeper
                flight = fly(match)
                self.assertNotIn('bounce', flight['events'])
                self.assertEqual(flight['points'][side], 1, (side, height))
        # Even if aimed behind the cat or off the court the shot is clamped inside.
        for aim in (-500, 5, 395, 900):
            player = airborne_match(0, x=100)[1]
            ball = VolleyBall(106, 140, 0, 0)
            vx, vy = SmashAttack.velocity(player, ball, aim)
            self.assertGreater(vx, 0)
            self.assertTrue(math.isfinite(vy))

    def test_smash_is_defendable_by_a_cat_waiting_at_home(self):
        for side in (0, 1):
            for x in range(34, 183, 16):
                xx = x if side == 0 else 400 - x
                match, player = airborne_match(side, x=xx)
                defender = match.players[1 - side]
                match._player_collision(player)
                flight = fly(match)
                home = 310 if side == 0 else 90
                reach = 155 * (flight['time'] - VolleyAI.REACTION) + 14 + 6
                self.assertLess(abs(flight['land'][0] - home), reach, (side, x))

    def test_a_chasing_defender_actually_returns_smashes(self):
        for side in (0, 1):
            for x in (40, 110, 182):
                xx = x if side == 0 else 400 - x
                match, player = airborne_match(side, x=xx)
                defender = match.players[1 - side]
                defender.x, defender.y = (310 if side == 0 else 90), FLOOR - 14
                match._player_collision(player)
                player.y = -500
                returned = False
                for _ in range(int(2.5 * 120)):
                    landing = VolleyAI.predict(_mirror(match.ball) if side == 1 else match.ball)
                    target = landing if side == 0 else 400 - landing
                    move = 0 if abs(target - defender.x) < 4 else (1 if target > defender.x else -1)
                    inputs = [IDLE, IDLE]
                    inputs[1 - side] = VolleyInput(move=move)
                    match._step(1 / 120, inputs)
                    if 'hit' in match.events and match.ball.vx * (1 if side == 0 else -1) < 0:
                        returned = True
                        break
                    if match.points != [0, 0]:
                        break
                self.assertTrue(returned, (side, x))


def _mirror(ball):
    from types import SimpleNamespace
    return SimpleNamespace(x=400 - ball.x, y=ball.y, vx=-ball.vx, vy=ball.vy)


class SmashAiTests(unittest.TestCase):
    def solo_rally(self, seconds=30):
        """P1 lobs the ball over like a beginner; Sandra plays on."""
        match = VolleyMatch(1, target=99)
        match.start()
        match.serve_delay = 0
        spikes = []
        for frame in range(int(seconds * 60)):
            b = match.ball
            # Beginner stand-in: waits at home, then runs to wherever the ball will land.
            landing = max(40, min(182, 400 - VolleyAI.predict(_mirror(b)))) if b.x < 200 else 90
            move = 1 if landing > match.players[0].x + 4 else (-1 if landing < match.players[0].x - 4 else 0)
            match.update(1 / 60, [VolleyInput(move=move)])
            spikes += [(frame, i) for i in match.impacts if i[2] == 'spike']
        return match, spikes

    def test_sandra_smashes_in_solo_play_toward_the_player_court(self):
        match, spikes = self.solo_rally()
        self.assertGreaterEqual(len(spikes), 3)
        for _, (x, y, kind, side) in spikes:
            self.assertEqual(side, 1)
            self.assertLess(y, NET_TOP)

    def test_sandra_does_not_smash_every_ball_and_the_player_can_return_them(self):
        match, spikes = self.solo_rally(60)
        offered = match.ai.opportunities
        self.assertGreater(offered, len(spikes) // 2)
        self.assertLess(len(spikes), offered * .85)         # many balls get a normal return
        self.assertLess(match.points[1], len(spikes))       # not every smash is a point

    def test_ai_smash_uses_the_same_swing_rules_as_a_human(self):
        match = VolleyMatch(1)
        match.start()
        match.serve_delay = 0
        sandra = match.players[1]
        sandra.y, sandra.vy = 170, 0
        sandra.attack.age = .08
        match.ball = VolleyBall(sandra.x - 6, 153, 0, 0)
        match.players[0].y = -500
        match.players[0].x = 60
        match._player_collision(sandra)
        self.assertEqual(match.events, ['spike'])
        self.assertLess(match.ball.vx, 0)
        self.assertTrue(30 < match.ball.x < 370)
        self.assertGreaterEqual(fly(match)['angle'], 40)

    def test_ai_aims_away_from_the_player_without_leaving_the_court(self):
        for p1_x in (40, 100, 180):
            match = VolleyMatch(1)
            match.start()
            match.serve_delay = 0
            match.players[0].x = p1_x
            match.players[0].y = -500
            sandra = match.players[1]
            sandra.y = 172
            sandra.attack.age = .08
            match.ball = VolleyBall(sandra.x - 6, 154, 0, 0)
            match._player_collision(sandra)
            self.assertIn('spike', match.events)
            flight = fly(match)
            self.assertEqual(flight['points'][1], 1)
            self.assertTrue(30 < flight['land'][0] < NET_X - 30)
            self.assertGreaterEqual(abs(flight['land'][0] - p1_x), 45)

    def test_intercept_prediction_matches_real_flight(self):
        ball = VolleyBall(90, 185, 170, -290)
        x, seconds = VolleyAI.intercept(ball)
        match = VolleyMatch(1)
        match.start()
        match.serve_delay = 0
        match.ball = VolleyBall(90, 185, 170, -290)
        match.players[0].y = match.players[1].y = -500
        t = 0
        while match.ball.y < 150 or match.ball.vy < 0:
            match._step(1 / 120, [IDLE, IDLE])
            t += 1 / 120
        self.assertAlmostEqual(match.ball.x, x, delta=4)
        self.assertAlmostEqual(t, seconds, delta=.03)


class SmashFeedbackTests(unittest.TestCase):
    def test_game_flow_creates_flash_popup_trail_and_shake_then_cleans_up(self):
        game = VolleyGame(2)
        self.addCleanup(game.audio.stop)
        game.confirm()
        match, player = airborne_match()
        game.match = match
        game.effects = SmashTrail()
        # Let the live match produce the Smash contact.
        match.ball.x, match.ball.y = player.x + 6, player.y - 17
        game.update(1 / 60, [IDLE, IDLE])
        effects = game.effects
        self.assertEqual([b[2] for b in effects.bursts], ['spike'])
        self.assertEqual(len(effects.popups), 1)
        self.assertGreater(effects.shake_left, 0)
        self.assertNotEqual(effects.shake_offset(), (0, 0))
        for _ in range(12):
            game.update(1 / 60, [IDLE, IDLE])
        self.assertGreaterEqual(len(effects.points), 8)           # visible speed trail
        surface = pygame.Surface((400, 300))
        game.draw(surface)
        for _ in range(60):
            game.update(1 / 60, [IDLE, IDLE])
            if game.match.state is not MatchState.PLAYING:
                break
        self.assertEqual(effects.shake_offset(), (0, 0))
        self.assertFalse(effects.bursts)
        self.assertFalse(effects.popups)

    def test_normal_hit_gets_only_a_small_ring_and_no_shake(self):
        trail = SmashTrail()
        ball = VolleyBall(100, 100, 0, 0)
        trail.update(.01, ball, [(100, 100, 'hit', 0)])
        self.assertEqual(trail.shake_offset(), (0, 0))
        self.assertFalse(trail.popups)
        self.assertLess(trail.BURST_LIFE['hit'], trail.BURST_LIFE['spike'])

    def test_smash_impact_paints_far_more_pixels_than_a_hit(self):
        def painted(kind):
            trail = SmashTrail()
            trail.update(.01, VolleyBall(100, 100, 0, 0), [(100, 100, kind, 0)])
            surface = pygame.Surface((200, 200))
            trail.draw(surface)
            return sum(surface.get_at((x, y))[:3] != (0, 0, 0) for x in range(200) for y in range(200))
        self.assertGreater(painted('spike'), painted('hit') * 3)

    def test_screen_shake_is_bounded_and_drawing_is_pure(self):
        game = VolleyGame(2)
        self.addCleanup(game.audio.stop)
        game.confirm()
        game.effects.update(.01, game.match.ball, [(100, 100, 'spike', 0)])
        before = (game.effects.shake_left, list(game.effects.bursts))
        surface = pygame.Surface((400, 300))
        for _ in range(3):
            game.draw(surface)
        self.assertEqual(before, (game.effects.shake_left, game.effects.bursts))
        dx, dy = game.effects.shake_offset()
        self.assertLessEqual(max(abs(dx), abs(dy)), SmashTrail.SHAKE_PIXELS)

    def test_swing_pose_is_drawn_while_the_paw_is_live(self):
        game = VolleyGame(2)
        self.addCleanup(game.audio.stop)
        game.confirm()
        player = game.match.players[0]
        player.y = 170

        def frame(age):
            player.attack.age = age
            surface = pygame.Surface((400, 300))
            game.renderer.cats.draw(surface, player, game.match)
            return pygame.image.tobytes(surface, 'RGB')
        self.assertNotEqual(frame(.1), frame(.30))     # live swoosh vs. follow-through
        self.assertNotEqual(frame(.1), frame(1))       # smash pose vs. plain jump


class SmashInstructionTests(unittest.TestCase):
    def test_hint_text_names_the_real_standalone_keys(self):
        self.assertIn('SPACE SMASH', default_hints(1)[0])
        two = default_hints(2)
        self.assertIn('SPACE SMASH', two[0])
        self.assertTrue(two[0].startswith('P1') and two[1].startswith('P2'))
        self.assertIn('R-SHIFT SMASH', two[1])
        self.assertEqual(len(hint_lines([('', 'A', 'D', 'W', 'Z')])), 1)

    def test_hints_are_drawn_on_the_court_screen(self):
        for local in (1, 2):
            game = VolleyGame(local)
            self.addCleanup(game.audio.stop)
            plain = pygame.Surface((400, 300))
            game.hints = ('',) * len(game.hints)
            game.draw(plain)
            labelled = pygame.Surface((400, 300))
            game.hints = default_hints(local)
            game.draw(labelled)
            self.assertNotEqual(pygame.image.tobytes(plain, 'RGB'), pygame.image.tobytes(labelled, 'RGB'))


if __name__ == '__main__':
    unittest.main()
