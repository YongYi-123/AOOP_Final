import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import random
import unittest
import pygame
from cat_territory.game import TerritoryGame
from cat_territory.model import BoardState


class TerritoryGameTests(unittest.TestCase):
    def game(self):
        game=TerritoryGame(random.Random(2))
        self.addCleanup(game.audio.stop)
        game.confirm()
        return game

    def test_double_click_only_places_cat_single_click_waits(self):
        game=self.game(); point=game.layout.cell_rect(0,0).center
        game.click(point,1)
        self.assertEqual(game.board.marks,set())
        game.update(.1); game.click(point,1)
        self.assertIn((0,0),game.board.cats)
        game.update(.4)
        self.assertNotIn((0,0),game.board.marks)
        point=game.layout.cell_rect(3,3).center
        game.click(point,1); game.update(.3)
        self.assertIn((3,3),game.board.marks)

    def test_pause_cancels_pending_input_and_freezes_board(self):
        game=self.game()
        game.click(game.layout.cell_rect(0,0).center,1)
        game.toggle_pause(); before=game.board.elapsed
        game.update(1)
        self.assertEqual(game.board.elapsed,before)
        self.assertEqual(game.board.marks,set())
        game.confirm(); game.update(.5)
        self.assertEqual(game.board.marks,set())

    def test_win_replay_best_rewards_do_not_accumulate(self):
        game=self.game()
        for y,x in enumerate(game.board.puzzle.solution): game.place_cat(x,y)
        self.assertIs(game.board.state,BoardState.WON)
        self.assertEqual(game.outcome().tickets,10)
        game.confirm()
        for y,x in enumerate(game.board.puzzle.solution): game.place_cat(x,y)
        self.assertEqual(game.outcome().tickets,10)
        game.draw(pygame.Surface((400,300)))

    def test_mark_and_cat_cancel_without_losing_hearts(self):
        game=self.game()
        game.mark(0,0); game.mark(0,0)
        self.assertNotIn((0,0),game.board.marks)
        game.place_cat(0,0); game.place_cat(0,0)
        self.assertEqual(game.board.cats,set())
        self.assertEqual(game.board.hearts,3)

    def test_keyboard_placement_cancels_pending_mouse_mark(self):
        game=self.game()
        game.click(game.layout.cell_rect(0,0).center,1)
        game.confirm()
        game.update(.4)
        self.assertIn((0,0),game.board.cats)
        self.assertNotIn((0,0),game.board.marks)
        self.assertEqual(game.board.hearts,3)
