"""Drive real observation, NOTE scrolling, page turning and close input."""
import pygame
from puzzle_maze.game import GameScene

def open_paper(game):
    game.update(.8)
    for _ in range(100):
        if game.inspection_intro is None:return
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    raise AssertionError('Inspection observation did not finish')

def close_inspection(game):
    open_paper(game)
    for _ in range(100):
        if game.scene!=GameScene.SCROLL:return
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    raise AssertionError('Inspection did not close')
