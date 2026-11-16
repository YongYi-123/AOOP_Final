"""Drive the real confirm sequence from a description to its paper page."""
import pygame

def open_paper(game):
    for _ in range(3):
        if game.inspection_intro is None:return
        game.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    raise AssertionError('Inspection description did not open its page')
