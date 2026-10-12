"""Raw keys -> logical input for the standalone preview. The lobby scene uses the profile's own PlayerInput
instead and never reads this."""
import pygame

ACTIONS = {pygame.K_w: "up", pygame.K_UP: "up", pygame.K_s: "down", pygame.K_DOWN: "down",
           pygame.K_a: "left", pygame.K_LEFT: "left", pygame.K_d: "right", pygame.K_RIGHT: "right",
           pygame.K_RETURN: "confirm", pygame.K_KP_ENTER: "confirm", pygame.K_ESCAPE: "back"}


class Keyboard:
    def __init__(self):
        self.order = []

    def reset(self):
        self.order.clear()

    def feed(self, event, game):
        if event.type == pygame.KEYUP:
            action = ACTIONS.get(event.key)
            if action in self.order:
                self.order.remove(action)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                game.toggle_reduced()
            elif event.key == pygame.K_p:
                game.pause() if game.screen.value == "playing" else game.resume()
            elif event.key in ACTIONS:
                action = ACTIONS[event.key]
                if action in ("up", "down", "left", "right"):
                    self.order.append(action)
                game.act(action)

    def held(self):
        """The most recently pressed direction key that is still down (or None)."""
        return self.order[-1] if self.order else None
