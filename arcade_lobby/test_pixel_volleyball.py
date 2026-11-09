"""Actual lobby play sessions of Pixel Volleyball (the player against Sandra, the CPU cat), input ownership and
one-time payouts."""
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
from pixel_volleyball.ai import VolleyAI
from pixel_volleyball.rally import LOB_VX_MAX


class VolleyballLobbyTests(unittest.TestCase):
    def make_game(self, other_saved=False):
        """The player is profiles[0]; with `other_saved` a second profile exists (saved, never played)."""
        profiles = [PlayerProfile(profile_id="volley_a")]
        if other_saved:
            profiles.append(PlayerProfile(profile_id="volley_b"))
        self.game = Game(session=LocalSession(profiles[0]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.machine = next(m for m in self.room.machines if m.id == "pixel_volleyball")
        self.room._start_game(self.machine, player=self.room.players[0])
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
        self.assertFalse(hasattr(minigame_definition("pixel_volleyball"), "max_players"))
        self.assertTrue(self.scene.volley.match.cpu)                  # the opponent is always Sandra
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.volley.match.state, MatchState.PLAYING)
        self.frames(30, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(profiles[0].tickets, 0)
        self.assertNotIn("pixel_volleyball", profiles[0].high_scores)
        self.assertIsNone(self.room.active_play)

    def test_the_player_moves_sandra_plays_by_herself_and_pause_freezes_both(self):
        self.make_game()
        self.frames(1, pygame.K_e)
        match = self.scene.volley.match
        match.serve_delay = 0
        self.frames(1, pygame.K_d)
        self.frames(20)
        self.assertGreater(match.players[0].x, 90)
        self.assertNotEqual(match.players[1].x, 310)                   # Sandra moved on her own (the AI)
        self.frames(1, pygame.K_i)
        before = (match.elapsed, match.players[0].x, match.players[1].x)
        self.frames(10)
        self.assertEqual((match.elapsed, match.players[0].x, match.players[1].x), before)

    def test_the_reward_is_the_players_only_and_paid_once(self):
        profiles = self.make_game(other_saved=True)
        self.frames(1, pygame.K_e)
        self.scene.volley.match.award_point(1)
        for _ in range(5):
            self.scene.volley.match.award_point(0)
        self.frames()
        result = self.scene.get_result()
        self.assertEqual([r.reward.tickets for r in result.player_results], [20])
        self.assertEqual(self.scene.get_result(), result)
        self.frames(30, pygame.K_ESCAPE)
        self.assertEqual([p.tickets for p in profiles], [20, 0])
        self.assertEqual([p.high_score("pixel_volleyball") for p in profiles], [1000, 0])
        self.frames(10)
        self.assertEqual([p.tickets for p in profiles], [20, 0])

    def test_losing_to_sandra_pays_little_and_is_recorded(self):
        profiles = self.make_game()
        self.frames(1, pygame.K_e)
        self.scene.volley.match.award_point(0)
        for _ in range(5):
            self.scene.volley.match.award_point(1)
        self.frames()
        self.assertEqual(self.scene.volley.match.state, MatchState.FINISHED)
        self.assertEqual(self.scene.volley.match.outcome.winner, 1)
        self.frames(30, pygame.K_ESCAPE)
        self.assertEqual(profiles[0].tickets, 2)
        self.assertEqual(profiles[0].high_score("pixel_volleyball"), 100)

    def test_the_old_second_player_keys_do_not_reach_the_match(self):
        profiles = [PlayerProfile(profile_id="watch_a"), PlayerProfile(profile_id="watch_b")]
        self.game = Game(session=LocalSession(profiles[0]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.machine = next(m for m in self.room.machines if m.id == "pixel_volleyball")
        self.room._start_game(self.machine, player=self.room.players[0])
        self.frames(30)
        self.scene = self.game.scenes.current
        self.assertFalse(hasattr(self.scene, "spectators"))
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.volley.match.state, MatchState.PLAYING)       # ENTER is the player's confirm
        match = self.scene.volley.match
        match.serve_delay = 99                                                     # nobody moves yet
        for old in (pygame.K_RCTRL, pygame.K_o, pygame.K_KP0, pygame.K_RSHIFT):
            self.frames(10, old)
        self.assertEqual(match.players[0].x, 90)
        self.assertFalse(any(p.attack.animating for p in match.players))

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
        self.assertEqual(self.scene.volley.match.ai.REACTION, VolleyAI.REACTION)
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.volley.match.state, MatchState.PLAYING)
        self.frames(1, pygame.K_BACKSPACE)
        self.assertEqual(self.scene.volley.match.ai.REACTION, VolleyAI.REACTION)
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

class VolleyballSmashHubTests(unittest.TestCase):
    """Smash played through the real Arcade Hub: key routing, scene, physics and scoring."""
    make_game = VolleyballLobbyTests.make_game
    frames = VolleyballLobbyTests.frames

    def start(self):
        self.make_game()
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
            self.assertGreater(match.ball.vx, 1.5 * LOB_VX_MAX)      # Smash: far faster than a return
            self.assertGreater(match.ball.vy, -150)
            for _ in range(120):
                self.frames(1)
                if match.points != [0, 0]:
                    break
            self.assertEqual(match.points, [1, 0], key)
            match.serve_delay = 0

    def test_the_wrong_keys_and_the_old_second_player_keys_never_swing(self):
        match = self.start()
        match.players[0].y, match.players[0].vy = 168, 0
        match.serve_delay = 99
        for wrong in (pygame.K_RETURN, pygame.K_e, pygame.K_w, pygame.K_UP, pygame.K_RSHIFT, pygame.K_KP0):
            self.frames(1, wrong)
            self.frames(1, wrong, down=False)
        self.assertFalse(match.players[0].attack.animating)
        self.frames(1, pygame.K_LSHIFT)                              # a real smash key does
        self.assertTrue(match.players[0].attack.animating)

    def test_sandra_smashes_back_toward_the_players_court_through_the_hub(self):
        from pixel_volleyball.model import VolleyBall
        match = self.start()
        sandra = match.players[1]
        sandra.y, sandra.vy = 168, 0
        match.players[0].y = -500
        sandra.attack.age = .08
        match.ball = VolleyBall(sandra.x - 6, sandra.y - 17, 0, 0)
        match._player_collision(sandra)
        self.assertLess(match.ball.vx, 0)                            # the ball leaves toward the player's side

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
        self.assertTrue(0 < match.ball.vx <= LOB_VX_MAX)      # a gentle aimed return, not a Smash
        self.assertLess(match.ball.vy, -250)            # the high lob, not a flat smash
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
        lines = self.scene.volley.hints
        self.assertEqual(len(lines), 1)                         # one player: one control line
        self.assertNotIn("P1", lines[0])
        self.assertNotIn("P2", lines[0])
        surface = pygame.Surface((400, 300))
        self.scene.draw(surface)


if __name__ == "__main__":
    unittest.main()
