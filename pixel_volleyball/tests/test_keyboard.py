import os
import unittest
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from pixel_volleyball.keyboard import VolleyKeyboard


class VolleyKeyboardTests(unittest.TestCase):
    def test_solo_accepts_original_wasd_and_arrow_bindings(self):
        keyboard = VolleyKeyboard()
        for key in (pygame.K_d, pygame.K_UP, pygame.K_LSHIFT):
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
        control = keyboard.controls(1)[0]
        self.assertEqual((control.move, control.jump, control.spike), (1, True, True))

    def test_local_controls_are_independent_and_focus_loss_clears_them(self):
        keyboard = VolleyKeyboard()
        for key in (pygame.K_a, pygame.K_RIGHT, pygame.K_RSHIFT):
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
        p1, p2 = keyboard.controls(2)
        self.assertEqual((p1.move, p1.spike), (-1, False))
        self.assertEqual((p2.move, p2.spike), (1, True))
        keyboard.feed(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(keyboard.held)
