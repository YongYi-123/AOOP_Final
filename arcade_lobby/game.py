"""Top-level Game object: window, main loop and pixel-perfect upscaling."""
import pygame

from scene_base import SceneManager
from scenes import ArcadeRoomScene
from settings import (BACKGROUND_STYLE, FPS, SCREEN_H, SCREEN_W, TITLE,
                      VIEW_H, VIEW_W)


class Game:
    def __init__(self, style=BACKGROUND_STYLE):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.canvas = pygame.Surface((VIEW_W, VIEW_H))  # low-res pixel canvas
        self.clock = pygame.time.Clock()
        self.running = True

        self.scenes = SceneManager()
        self.scenes.push(ArcadeRoomScene(self, style), fade=False)

    def step(self, events, dt):
        """Process one frame. Separate from run() so it can be driven by tests."""
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            else:
                self.scenes.handle_event(event)
        self.scenes.update(dt)
        self.scenes.draw(self.canvas, self.screen)

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.step(pygame.event.get(), dt)
            pygame.display.flip()
        pygame.quit()
