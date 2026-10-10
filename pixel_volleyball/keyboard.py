"""Standalone bindings; embedded matches use the lobby's PlayerInput instead."""
import pygame
from .model import VolleyInput


class VolleyKeyboard:
    def __init__(self):
        self.held = set()

    def feed(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:
            self.held.clear()
        elif event.type == pygame.KEYDOWN:
            self.held.add(event.key)
        elif event.type == pygame.KEYUP:
            self.held.discard(event.key)

    def controls(self, local_players):
        bindings = [((pygame.K_a,), (pygame.K_d,), (pygame.K_w,),
                     (pygame.K_SPACE, pygame.K_LSHIFT))]
        if local_players == 1:
            bindings = [((pygame.K_a, pygame.K_LEFT), (pygame.K_d, pygame.K_RIGHT),
                         (pygame.K_w, pygame.K_UP), (pygame.K_SPACE, pygame.K_LSHIFT))]
        else:
            bindings.append(((pygame.K_LEFT,), (pygame.K_RIGHT,), (pygame.K_UP,),
                             (pygame.K_RSHIFT, pygame.K_RCTRL)))
        result = []
        for left, right, jump, spike in bindings:
            down = lambda keys: any(key in self.held for key in keys)
            result.append(VolleyInput(int(down(right)) - int(down(left)), down(jump), down(spike)))
        return result
