"""Standalone Cat Territory: python -m cat_territory."""
import pygame
from .game import TerritoryGame
from cat_minesweeper.mouse import MineMouseInput


def main():
    pygame.init()
    screen=pygame.display.set_mode((800,600))
    pygame.display.set_caption('Neon Corner - Cat Territory')
    surface=pygame.Surface((400,300))
    game=TerritoryGame()
    clock=pygame.time.Clock()
    running=True
    try:
        while running:
            dt=min(.1,clock.tick(60)/1000)
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    running=False
                elif event.type==pygame.WINDOWFOCUSLOST:
                    if game.active: game.toggle_pause()
                elif event.type==pygame.MOUSEBUTTONDOWN:
                    game.click(MineMouseInput.canvas_position(event.pos,screen.get_size()),event.button)
                elif event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE: running=False
                    elif event.key in (pygame.K_RETURN,pygame.K_e): game.confirm()
                    elif event.key==pygame.K_BACKSPACE: game.select_difficulty()
                    elif event.key==pygame.K_p: game.toggle_pause()
                    elif event.key in (pygame.K_SPACE,pygame.K_x): game.mark(*game.cursor)
                    elif event.key in (pygame.K_UP,pygame.K_DOWN,pygame.K_LEFT,pygame.K_RIGHT):
                        directions={pygame.K_UP:(0,-1),pygame.K_DOWN:(0,1),pygame.K_LEFT:(-1,0),pygame.K_RIGHT:(1,0)}
                        dx,dy=directions[event.key]
                        if game.selecting: game.move_selection(dy)
                        else: game.move_cursor(dx,dy)
            game.update(dt); game.draw(surface)
            pygame.transform.scale(surface,screen.get_size(),screen)
            pygame.display.flip()
    finally:
        game.audio.stop(); pygame.quit()


if __name__=='__main__':
    main()
