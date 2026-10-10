import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame
from pixel_volleyball.cat_art import CatAnimation, CatAthleteRenderer, YarnRenderer
from pixel_volleyball.model import VolleyMatch, VolleyInput
from pixel_volleyball.game import VolleyGame


class CatPresentationTests(unittest.TestCase):
    def test_animation_states_follow_actual_player_state(self):
        match = VolleyMatch(2)
        player = match.players[0]
        renderer = CatAthleteRenderer()
        self.assertIs(renderer.state(player, match), CatAnimation.IDLE)
        player.moving = 1
        self.assertIs(renderer.state(player, match), CatAnimation.MOVE)
        player.y -= 30
        self.assertIs(renderer.state(player, match), CatAnimation.JUMP)
        player.hit_flash = .1
        self.assertIs(renderer.state(player, match), CatAnimation.HIT)
        match.start()
        for _ in range(5):
            match.award_point(0)
        self.assertIs(renderer.state(player, match), CatAnimation.VICTORY)

    def test_cats_have_different_fur_and_yarn_rotates_without_physics_mutation(self):
        match = VolleyMatch(2)
        renderer = CatAthleteRenderer()
        images = []
        for player in match.players:
            surface = pygame.Surface((400,300))
            renderer.draw(surface, player, match)
            images.append(surface.get_at((round(player.x),round(player.y)-10)))
        self.assertNotEqual(images[0],images[1])
        yarn = YarnRenderer()
        first, second = pygame.Surface((400,300)), pygame.Surface((400,300))
        yarn.draw(first, match.ball)
        match.ball.rotation = 45
        before = vars(match.ball).copy()
        yarn.draw(second, match.ball)
        self.assertNotEqual(pygame.image.tobytes(first,'RGB'),pygame.image.tobytes(second,'RGB'))
        self.assertEqual(vars(match.ball),before)

    def test_cat_game_headless_render(self):
        game = VolleyGame()
        self.addCleanup(game.audio.stop)
        surface = pygame.Surface((400,300))
        game.draw(surface)
        game.confirm()
        game.update(.1,[VolleyInput(1,True,True)])
        game.draw(surface)
        self.assertTrue(any(pygame.image.tobytes(surface,'RGB')))
