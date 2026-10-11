"""Actual lobby play sessions, participant input ownership and one-time payouts."""
import os
import unittest
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from game import Game
from local_session import LocalSession
from player_profile import PlayerProfile
from room_testing import goto_room
from scenes import minigame_definition
from pixel_volleyball_scene import PixelVolleyballScene
from pixel_volleyball.model import MatchState


class VolleyballLobbyTests(unittest.TestCase):
    def make_game(self, two=False):
        profiles = [PlayerProfile(profile_id="volley_a")]
        if two:
            profiles.append(PlayerProfile(profile_id="volley_b"))
        self.game = Game(session=LocalSession(profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.machine = next(m for m in self.room.machines if m.id == "pixel_volleyball")
        self.room._start_game(self.machine, player=self.room.players[0],
                              participants=self.room.players if two else None)
        self.frames(30)
        self.scene = self.game.scenes.current
        self.assertIsInstance(self.scene, PixelVolleyballScene)
        return profiles

    def frames(self, count=1, key=None, down=True):
        events = [] if key is None else [pygame.event.Event(
            pygame.KEYDOWN if down else pygame.KEYUP, key=key, mod=0)]
        for i in range(count):
            self.game.step(events if i == 0 else [], 1 / 60)

    def test_solo_starts_with_enter_and_returns_without_unearned_tickets(self):
        profiles = self.make_game()
        self.assertTrue(minigame_definition("pixel_volleyball").supports(2))
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.volley.match.state, MatchState.PLAYING)
        self.frames(30, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(profiles[0].tickets, 0)
        self.assertNotIn("pixel_volleyball", profiles[0].high_scores)
        self.assertIsNone(self.room.active_play)

    def test_two_players_move_independently_and_pause(self):
        self.make_game(True)
        self.frames(1, pygame.K_e)
        self.frames(1, pygame.K_d)
        self.frames(10, pygame.K_LEFT)
        match = self.scene.volley.match
        self.assertGreater(match.players[0].x, 90)
        self.assertLess(match.players[1].x, 310)
        self.frames(1, pygame.K_i)
        before = (match.elapsed, match.players[0].x, match.players[1].x)
        self.frames(10)
        self.assertEqual((match.elapsed, match.players[0].x, match.players[1].x), before)

    def test_rewards_and_high_scores_are_separate_and_paid_once(self):
        profiles = self.make_game(True)
        self.frames(1, pygame.K_e)
        self.scene.volley.match.award_point(1)
        for _ in range(5):
            self.scene.volley.match.award_point(0)
        self.frames()
        result = self.scene.get_result()
        self.assertEqual([r.reward.tickets for r in result.player_results], [20, 2])
        self.assertEqual(self.scene.get_result(), result)
        self.frames(30, pygame.K_ESCAPE)
        self.assertEqual([p.tickets for p in profiles], [20, 2])
        self.assertEqual([p.high_score("pixel_volleyball") for p in profiles], [1000, 100])
        self.frames(10)
        self.assertEqual([p.tickets for p in profiles], [20, 2])

    def test_spectator_controls_do_not_reach_solo_match(self):
        profiles = [PlayerProfile(profile_id="watch_a"), PlayerProfile(profile_id="watch_b")]
        self.game = Game(session=LocalSession(profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.machine = next(m for m in self.room.machines if m.id == "pixel_volleyball")
        self.room._start_game(self.machine, player=self.room.players[0])
        self.frames(30)
        self.scene = self.game.scenes.current
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.volley.match.state, MatchState.TITLE)
        self.frames(1, pygame.K_e)
        self.frames(10, pygame.K_RIGHT)
        self.assertEqual(self.scene.volley.match.players[0].x, 90)

    def test_completed_reward_survives_restart_without_accumulation(self):
        self.make_game()
        self.frames(1, pygame.K_e)
        for _ in range(5):
            self.scene.volley.match.award_point(0)
        self.frames()
        first = self.scene.get_result()
        self.frames(1, pygame.K_BACKSPACE)
        self.assertEqual(self.scene.get_result(), first)

    def test_movement_keys_do_not_change_sandra_start_replay_and_return(self):
        self.make_game()
        self.frames(1, pygame.K_RIGHT)
        self.frames(1, pygame.K_RIGHT, down=False)
        self.assertEqual(self.scene.volley.match.ai.REACTION, .09)
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.volley.match.state, MatchState.PLAYING)
        self.frames(1, pygame.K_BACKSPACE)
        self.assertEqual(self.scene.volley.match.ai.REACTION, .09)
        self.frames(30, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)

    def test_start_key_does_not_arm_smash_and_item_key_does(self):
        self.make_game()
        self.frames(1, pygame.K_e)
        match = self.scene.volley.match
        player = match.players[0]
        player.y, player.vy = 174, -40
        match.serve_delay = 0
        from pixel_volleyball.model import VolleyBall
        match.ball = VolleyBall(40,90,0,0)
        self.frames(2)
        self.assertFalse(player.attack.animating)
        self.frames(1, pygame.K_SPACE)
        self.assertTrue(player.attack.animating)

    def test_two_players_can_swing_independently(self):
        self.make_game(True)
        self.frames(1, pygame.K_e)
        match = self.scene.volley.match
        for player in match.players:
            player.y, player.vy = 174, -40
        self.frames(1, pygame.K_SPACE)
        self.assertTrue(match.players[0].attack.animating)
        self.assertFalse(match.players[1].attack.animating)
        self.frames(1, pygame.K_RSHIFT)
        self.assertTrue(match.players[1].attack.animating)


class VolleyballSmashHubTests(unittest.TestCase):
    """Smash played through the real Arcade Hub: key routing, scene, physics and scoring."""
    make_game = VolleyballLobbyTests.make_game
    frames = VolleyballLobbyTests.frames

    def start(self, two=False):
        self.make_game(two)
        self.frames(1, pygame.K_e)
        match = self.scene.volley.match
        match.serve_delay = 0
        return match

    def airborne(self, match, side):
        from pixel_volleyball.model import VolleyBall
        player = match.players[side]
        player.y, player.vy = 168, 0
        match.players[1 - side].y = -500
        match.ball = VolleyBall(200, 60, 0, 0)       # parked up high until the swing is live
        return player

    def smash(self, match, side, key):
        """Press `key` in the air, wait for the paw to wind up, then deliver the ball to it."""
        from pixel_volleyball.model import VolleyBall
        player = self.airborne(match, side)
        self.frames(1, key)
        self.frames(1, key, down=False)
        self.frames(4)
        self.assertTrue(player.attack.active)
        direction = 1 if side == 0 else -1
        match.ball = VolleyBall(player.x + direction * 6, player.y - 17, 0, 0)
        self.frames(1)
        return player

    def test_solo_smash_key_drives_a_real_smash_to_a_point(self):
        match = self.start()
        for key in (pygame.K_SPACE, pygame.K_LSHIFT):
            match.points[:] = [0, 0]
            player = self.smash(match, 0, key)
            self.assertTrue(player.attack.connected)
            self.assertGreater(match.ball.vx, 250)
            self.assertGreater(match.ball.vy, -150)
            for _ in range(120):
                self.frames(1)
                if match.points != [0, 0]:
                    break
            self.assertEqual(match.points, [1, 0], key)
            match.serve_delay = 0

    def test_two_player_smash_keys_are_independent_and_aim_at_the_other_court(self):
        match = self.start(True)
        player = self.smash(match, 0, pygame.K_SPACE)
        self.assertTrue(player.attack.connected)
        self.assertGreater(match.ball.vx, 250)
        self.assertFalse(match.players[1].attack.animating)
        match.points[:] = [0, 0]
        match._serve(0)
        match.serve_delay = 0
        player = self.smash(match, 1, pygame.K_RSHIFT)
        self.assertTrue(player.attack.connected)
        self.assertLess(match.ball.vx, -250)
        self.assertFalse(match.players[0].attack.animating)
        for _ in range(120):
            self.frames(1)
            if match.points != [0, 0]:
                break
        self.assertEqual(match.points, [0, 1])

    def test_each_players_other_smash_key_and_the_wrong_keys_do_nothing_wrong(self):
        match = self.start(True)
        for p in match.players:
            p.y, p.vy = 168, 0
        self.frames(1, pygame.K_LSHIFT)
        self.assertTrue(match.players[0].attack.animating)
        self.assertFalse(match.players[1].attack.animating)
        self.frames(1, pygame.K_LSHIFT, down=False)
        self.frames(1, pygame.K_KP0)
        self.assertTrue(match.players[1].attack.animating)
        self.assertFalse(match.players[0].attack.animating and match.players[0].attack.age < .001)
        self.frames(1, pygame.K_KP0, down=False)
        match._serve(0)
        match.serve_delay = 0
        for p in match.players:
            p.y, p.vy = 168, 0
        for wrong in (pygame.K_RETURN, pygame.K_e, pygame.K_w, pygame.K_UP):
            self.frames(1, wrong)
            self.frames(1, wrong, down=False)
        self.assertFalse(any(p.attack.animating for p in match.players))

    def test_smash_tap_released_inside_one_frame_still_swings(self):
        match = self.start()
        match.players[0].y, match.players[0].vy = 168, 0
        self.game.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0),
                        pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE, mod=0)], 1 / 60)
        self.assertTrue(match.players[0].attack.animating)

    def test_buffered_smash_press_just_before_takeoff_works_through_the_hub(self):
        match = self.start()
        self.frames(1, pygame.K_SPACE)             # pressed on the ground
        self.frames(1, pygame.K_SPACE, down=False)
        self.assertFalse(match.players[0].attack.animating)
        self.frames(1, pygame.K_w)                 # then jump
        self.frames(3)                             # off the ground well within the buffer
        self.assertTrue(match.players[0].attack.animating)
        self.assertLess(match.players[0].attack.age, .1)

    def test_normal_hit_still_works_and_is_not_a_smash(self):
        from pixel_volleyball.model import VolleyBall
        match = self.start()
        player = match.players[0]
        match.ball = VolleyBall(player.x + 6, player.y - 17, 0, 0)
        self.frames(1)
        self.assertFalse(player.attack.connected)
        self.assertEqual(match.ball.vx, 190)
        self.assertLess(match.ball.vy, -330)            # the high lob, not a flat smash
        crossed_high = False
        for _ in range(90):
            self.frames(1)
            crossed_high |= match.ball.x > 210 and match.ball.y < 160
        self.assertTrue(crossed_high)                   # a slow lob over the net, played on normally

    def test_on_screen_instructions_name_the_real_smash_keys(self):
        from controls import key_label
        self.make_game()
        solo = " ".join(self.scene.volley.hints)
        self.assertIn("SMASH", solo)
        for key in self.scene.players[0].controls.item[:2]:
            self.assertIn(key_label(key), solo)
        self.make_game(True)
        lines = self.scene.volley.hints
        self.assertEqual(len(lines), 2)
        for line, player, name in zip(lines, self.scene.players, ("P1", "P2")):
            self.assertTrue(line.startswith(name), line)
            for key in player.controls.item[:2]:
                self.assertIn(key_label(key), line)
        self.assertIn("R-SHIFT", lines[1])
        surface = pygame.Surface((400, 300))
        self.scene.draw(surface)


if __name__ == "__main__":
    unittest.main()
