"""Run from the repository root: python -m neon_cat_maze (NEON CAT MAZE, standalone preview, no lobby, no saves)."""
import pygame

from .game import CatMazeGame
from .keyboard import Keyboard


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("NEON CAT MAZE")
    canvas = pygame.Surface((400, 300))
    game, keyboard, clock = CatMazeGame(), Keyboard(), pygame.time.Clock()
    while not game.wants_exit:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.wants_exit = True
            elif event.type == pygame.WINDOWFOCUSLOST:
                keyboard.reset()
                game.pause()
            else:
                keyboard.feed(event, game)
        if keyboard.held():
            game.steer(keyboard.held())
        game.update(dt)
        game.draw(canvas)
        pygame.transform.scale(canvas, screen.get_size(), screen)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
