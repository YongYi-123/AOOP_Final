"""Run from the repository root: python -m pixel_volleyball [--two-player]."""
import argparse
import pygame
from .game import VolleyGame
from .keyboard import VolleyKeyboard


def main():
    parser = argparse.ArgumentParser(description="Original Cat Volleyball")
    parser.add_argument("--two-player", action="store_true")
    args = parser.parse_args()
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Neon Corner - Cat Volleyball")
    canvas = pygame.Surface((400, 300))
    game = VolleyGame(2 if args.two_player else 1)
    clock = pygame.time.Clock()
    running = True
    keyboard = VolleyKeyboard()
    try:
        while running:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                keyboard.feed(event)
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.WINDOWFOCUSLOST:
                    if game.match.state.value == "playing":
                        game.match.toggle_pause()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_RETURN, pygame.K_e):
                        game.confirm()
                    elif event.key in (pygame.K_p, pygame.K_i, pygame.K_o):
                        game.match.toggle_pause()
                    elif event.key in (pygame.K_r, pygame.K_BACKSPACE):
                        game.restart()
            game.update(dt, keyboard.controls(game.local_players))
            game.draw(canvas)
            pygame.transform.scale(canvas, screen.get_size(), screen)
            pygame.display.flip()
    finally:
        game.audio.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
