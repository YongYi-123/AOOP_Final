"""Raw keys -> logical input for the standalone preview. The lobby scene uses the profile's own
PlayerInput instead and never reads this."""
import pygame

LEFT, RIGHT = (pygame.K_a, pygame.K_LEFT), (pygame.K_d, pygame.K_RIGHT)
FIRE = (pygame.K_SPACE,)
ACTIONS = {pygame.K_w: "up", pygame.K_UP: "up", pygame.K_s: "down", pygame.K_DOWN: "down",
           pygame.K_RETURN: "confirm", pygame.K_KP_ENTER: "confirm", pygame.K_ESCAPE: "back"}


class Keyboard:
    def __init__(self):
        self.down = set()

    def reset(self):
        self.down.clear()

    def feed(self, event, game):
        if event.type == pygame.KEYUP:
            self.down.discard(event.key)
        elif event.type == pygame.KEYDOWN:
            self.down.add(event.key)
            if event.key == pygame.K_f:
                game.toggle_reduced()
            elif event.key in ACTIONS:
                game.act(ACTIONS[event.key])

    def move(self):
        return int(any(k in self.down for k in RIGHT)) - int(any(k in self.down for k in LEFT))

    def fire(self):
        return any(k in self.down for k in FIRE)
