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

    def test_cat_difficulty_keys_start_replay_and_return(self):
        self.make_game()
        self.frames(1, pygame.K_RIGHT)
        self.frames(1, pygame.K_RIGHT, down=False)
        self.assertEqual(self.scene.volley.match.ai.difficulty.name, 'HARD')
        self.frames(1, pygame.K_RETURN)
        self.assertEqual(self.scene.volley.match.state, MatchState.PLAYING)
        self.frames(1, pygame.K_BACKSPACE)
        self.assertEqual(self.scene.volley.match.ai.difficulty.name, 'HARD')
        self.frames(30, pygame.K_ESCAPE)
        self.assertIs(self.game.scenes.current, self.room)
