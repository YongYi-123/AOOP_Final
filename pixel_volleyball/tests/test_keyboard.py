import os
import unittest
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from pixel_volleyball.keyboard import VolleyKeyboard


class VolleyKeyboardTests(unittest.TestCase):
    def test_wasd_and_arrow_bindings_both_drive_the_one_player(self):
        keyboard = VolleyKeyboard()
        for key in (pygame.K_d, pygame.K_UP, pygame.K_LSHIFT):
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
        control = keyboard.controls()[0]
        self.assertEqual((control.move, control.jump, control.spike), (1, True, True))
        for key, expected in ((pygame.K_RIGHT, (1, False)), (pygame.K_w, (0, True))):
            keyboard = VolleyKeyboard()
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
            control = keyboard.controls()[0]
            self.assertEqual((control.move, control.jump), expected, pygame.key.name(key))

    def test_there_is_only_one_player_input(self):
        keyboard = VolleyKeyboard()
        self.assertEqual(len(keyboard.controls()), 1)

    def test_second_player_smash_keys_do_nothing(self):
        for key in (pygame.K_RSHIFT, pygame.K_KP0, pygame.K_RCTRL, pygame.K_LCTRL):
            keyboard = VolleyKeyboard()
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
            self.assertFalse(keyboard.controls()[0].spike, pygame.key.name(key))

    def test_focus_loss_clears_the_held_keys(self):
        keyboard = VolleyKeyboard()
        for key in (pygame.K_a, pygame.K_SPACE):
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
        control = keyboard.controls()[0]
        self.assertEqual((control.move, control.spike), (-1, True))
        keyboard.feed(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(keyboard.held)
        self.assertEqual(keyboard.controls()[0].move, 0)
