"""Run independently from the repository root: python -m cat_minesweeper."""
import pygame
from .game import MineGame
from .mouse import MineMouseInput


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Neon Corner - Cat Minesweeper")
    canvas = pygame.Surface((400, 300))
    game, clock, running = MineGame(), pygame.time.Clock(), True
    try:
        while running:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.WINDOWFOCUSLOST:
                    if not game.paused:
                        game.toggle_pause()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
                        game.confirm()
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        game.move_selection(-1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        game.move_selection(1)
                    elif event.key in (pygame.K_p, pygame.K_i):
                        game.toggle_pause()
                    elif event.key == pygame.K_BACKSPACE:
                        game.select_difficulty()
                    elif event.key == pygame.K_r:
                        game.restart()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    game.click(MineMouseInput.canvas_position(event.pos, screen.get_size()), event.button)
            game.update(dt)
            game.draw(canvas)
            pygame.transform.scale(canvas, screen.get_size(), screen)
            pygame.display.flip()
    finally:
        game.audio.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
