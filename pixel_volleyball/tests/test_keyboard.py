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

    def test_simultaneous_p1_and_p2_input_never_crosses_over(self):
        keyboard = VolleyKeyboard()
        down = (pygame.K_d, pygame.K_w, pygame.K_LEFT, pygame.K_RSHIFT)
        for key in down:
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
        p1, p2 = keyboard.controls(2)
        self.assertEqual((p1.move, p1.jump, p1.spike), (1, True, False))
        self.assertEqual((p2.move, p2.jump, p2.spike), (-1, False, True))

    def test_each_smash_key_belongs_to_one_player(self):
        for key, expected in ((pygame.K_SPACE, (True, False)), (pygame.K_LSHIFT, (True, False)),
                              (pygame.K_RSHIFT, (False, True)), (pygame.K_KP0, (False, True)),
                              (pygame.K_RCTRL, (False, False)), (pygame.K_LCTRL, (False, False))):
            keyboard = VolleyKeyboard()
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
            p1, p2 = keyboard.controls(2)
            self.assertEqual((p1.spike, p2.spike), expected, pygame.key.name(key))

    def test_arrows_and_up_do_not_drive_p1_in_two_player_mode(self):
        keyboard = VolleyKeyboard()
        for key in (pygame.K_RIGHT, pygame.K_UP):
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
        p1, p2 = keyboard.controls(2)
        self.assertEqual((p1.move, p1.jump), (0, False))
        self.assertEqual((p2.move, p2.jump), (1, True))

    def test_local_controls_are_independent_and_focus_loss_clears_them(self):
        keyboard = VolleyKeyboard()
        for key in (pygame.K_a, pygame.K_RIGHT, pygame.K_RSHIFT):
            keyboard.feed(pygame.event.Event(pygame.KEYDOWN, key=key))
        p1, p2 = keyboard.controls(2)
        self.assertEqual((p1.move, p1.spike), (-1, False))
        self.assertEqual((p2.move, p2.spike), (1, True))
        keyboard.feed(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(keyboard.held)
