"""Standalone bindings; embedded matches use the lobby's PlayerInput instead."""
import pygame
from .model import VolleyInput


class VolleyKeyboard:
    def __init__(self):
        self.held = set()
        self.tapped = set()     # pressed since the last controls(), even if already released

    def feed(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:
            self.held.clear()
            self.tapped.clear()
        elif event.type == pygame.KEYDOWN:
            self.held.add(event.key)
            self.tapped.add(event.key)
        elif event.type == pygame.KEYUP:
            self.held.discard(event.key)

    def controls(self):
        """The one player's input, as a one-item list (what VolleyMatch.update takes)."""
        left, right = (pygame.K_a, pygame.K_LEFT), (pygame.K_d, pygame.K_RIGHT)
        jump, spike = (pygame.K_w, pygame.K_UP), (pygame.K_SPACE, pygame.K_LSHIFT)
        down = lambda keys: any(key in self.held for key in keys)
        tap = any(key in self.tapped for key in spike)
        self.tapped.clear()
        return [VolleyInput(int(down(right)) - int(down(left)), down(jump), down(spike) or tap)]
