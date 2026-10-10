import os
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import unittest
from unittest.mock import patch
import pygame
from pixel_volleyball.effects import SmashTrail
from pixel_volleyball.model import VolleyBall, VolleyInput
from pixel_volleyball.game import VolleyGame
from pixel_volleyball.cat_art import CatAnimation, CatAthleteRenderer
from pixel_volleyball.audio import VolleySounds


class SmashPresentationTests(unittest.TestCase):
    def test_trail_expires_is_bounded_and_resets_on_serve(self):
        trail = SmashTrail()
        ball = VolleyBall(90,100,330,80,smash_left=.4)
        for _ in range(100):
            trail.update(.001, ball)
        self.assertEqual(len(trail.points), trail.LIMIT)
        ball.smash_left = 0
        trail.update(.2, ball)
        self.assertFalse(trail.points)
        ball.smash_left = .2
        trail.update(.01, ball)
        trail.update(0, VolleyBall(90,185,170,-290))
        self.assertFalse(trail.points)

    def test_pause_and_draw_do_not_advance_effects_or_physics(self):
        game = VolleyGame(2)
        self.addCleanup(game.audio.stop)
        game.confirm()
        game.match.serve_delay = 0
        game.match.ball.smash_left = .4
        game.update(.01)
        game.match.toggle_pause()
        before = (list(game.effects.points),game.effects.time,vars(game.match.ball).copy())
        game.update(.1)
        surface = pygame.Surface((400,300))
        game.draw(surface)
        game.draw(surface)
        self.assertEqual(before,(game.effects.points,game.effects.time,vars(game.match.ball)))
        game.restart()
        self.assertFalse(game.effects.points)

    def test_swing_animation_follows_attack_and_expires(self):
        game = VolleyGame(2)
        self.addCleanup(game.audio.stop)
        player = game.match.players[0]
        player.y = 170
        player.attack.update(.01,True,True)
        self.assertIs(CatAthleteRenderer.state(player,game.match),CatAnimation.SMASH)
        game.draw(pygame.Surface((400,300)))
        player.attack.update(.4,False,True)
        self.assertIs(CatAthleteRenderer.state(player,game.match),CatAnimation.JUMP)

    def test_sound_unavailable_is_safe_and_smash_uses_longer_original_synth(self):
        with patch.object(pygame.mixer,'get_init',return_value=None):
            silent = VolleySounds()
            silent.play(['spike'])
            silent.stop()
        pygame.mixer.init()
        sounds = VolleySounds()
        self.addCleanup(sounds.stop)
        self.assertGreater(sounds.sounds['spike'].get_length(),sounds.sounds['hit'].get_length())
        sounds.play(['spike'])
