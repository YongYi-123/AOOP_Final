"""Territory replaces mine gameplay; preserve mouse, settlement and isolation coverage."""
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
from cat_territory_scene import CatTerritoryScene
from cat_territory.model import BoardState


class CatTerritoryLobbyTests(unittest.TestCase):
    def start(self, two=False, starter=0):
        self.profiles = [PlayerProfile(profile_id="mine_a")]
        if two:
            self.profiles.append(PlayerProfile(profile_id="mine_b"))
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        machine = next(m for m in self.room.machines if m.id == "cat_minesweeper")
        self.room._start_game(machine, player=self.room.players[starter])
        self.frames(30)
        self.scene = self.game.scenes.current
        self.assertIsInstance(self.scene, CatTerritoryScene)

    def frames(self, count=1, events=()):
        for i in range(count):
            self.game.step(list(events) if i == 0 else [], 1 / 60)

    def key(self, key):
        self.frames(events=[pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)])

    def click(self, x, y, button=1):
        point = self.scene.territory.layout.cell_rect(x, y).center
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(point[0] * 2, point[1] * 2), button=button)
        self.frames(events=[event])

    def win(self):
        for y,x in enumerate(self.scene.territory.board.puzzle.solution):
            self.click(x,y)
            self.click(x,y)
        self.assertEqual(self.scene.territory.board.state, BoardState.WON)

    def leave(self):
        self.key(pygame.K_ESCAPE)
        self.frames(30)
        self.assertIs(self.game.scenes.current, self.room)

    def test_scaled_mouse_single_and_double_click(self):
        self.start()
        self.assertFalse(minigame_definition("cat_minesweeper").supports(2))
        self.key(pygame.K_RETURN)
        self.click(0,0)
        self.frames(20)
        self.assertIn((0,0),self.scene.territory.board.marks)
        self.click(0,0)
        self.click(0,0)
        self.assertIn((0,0),self.scene.territory.board.cats)
        self.assertNotIn((0,0),self.scene.territory.board.marks)
        self.assertEqual(self.scene.territory.board.hearts,3)

    def test_fixed_board_replays_and_records_best_score(self):
        self.start()
        for index in range(3):
            if index:
                self.key(pygame.K_BACKSPACE)
            else:
                self.key(pygame.K_RETURN)
            self.assertEqual(self.scene.territory.board.size, 8)
            self.win()
        result = self.scene.get_result().player_results[0]
        self.assertEqual(result.reward.tickets, 20)
        self.leave()
        self.assertEqual(self.profiles[0].tickets, 20)
        self.assertEqual(self.profiles[0].high_score("cat_minesweeper"), result.score)
        self.frames(10)
        self.assertEqual(self.profiles[0].tickets, 20)

    def test_second_player_can_play_and_spectator_is_not_rewarded(self):
        self.start(True, starter=1)
        self.key(pygame.K_e)
        self.assertTrue(self.scene.territory.selecting)
        self.key(pygame.K_RETURN)
        self.win()
        result = self.scene.get_result()
        self.assertIsNone(result.for_profile(self.profiles[0].profile_id))
        self.leave()
        self.assertEqual(self.profiles[0].tickets, 0)
        self.assertEqual(self.profiles[1].tickets, 20)

    def test_abandonment_and_loss_return_without_tickets(self):
        self.start()
        self.key(pygame.K_RETURN)
        self.click(0,0); self.click(0,0)
        for _ in range(3):
            self.click(1,0); self.click(1,0)
        self.assertEqual(self.scene.territory.board.state,BoardState.LOST)
        self.assertEqual(self.scene.get_result().player_results[0].reward.tickets,0)
        self.leave()
        self.assertEqual(self.profiles[0].tickets,0)

    def test_pause_blocks_mouse_and_freezes_timer(self):
        self.start()
        self.key(pygame.K_RETURN)
        self.click(0, 0)
        self.key(pygame.K_i)
        before = self.scene.territory.board.elapsed
        self.click(5, 5, 3)
        self.frames(5)
        self.assertEqual(self.scene.territory.board.elapsed, before)
        self.assertNotIn((5,5),self.scene.territory.board.marks)

    def test_unfinished_board_does_not_create_high_score(self):
        self.start()
        self.key(pygame.K_RETURN)
        self.click(0, 0)
        self.assertIsNone(self.scene.get_result().player_results[0].score)
        self.leave()
        self.assertNotIn("cat_minesweeper", self.profiles[0].high_scores)
        self.assertEqual(self.profiles[0].tickets, 0)
