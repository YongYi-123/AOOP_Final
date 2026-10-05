"""Top-level Game object: window, main loop and pixel-perfect upscaling."""
import pygame

from game_clock import GameClock
from player_profile import ProfileStore
from arcade_style import STYLES
from room_scene import RoomHub
from scene_base import SceneManager
from settings import (DEBUG, FPS, SAVE_FILE, SCREEN_H, SCREEN_W, TITLE, VIEW_H,
                      VIEW_W)


class Game:
    def __init__(self, style=None, save_path=SAVE_FILE, debug=DEBUG, clock=None):
        # The profile is loaded before any scene exists and autosaves on
        # every change; scenes reach it through game.profile.
        self.debug = debug
        self.clock = clock or GameClock()
        self.store = ProfileStore(save_path, self.clock)
        self.profile = self.store.load()
        self.store.autosave(self.profile)

        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.canvas = pygame.Surface((VIEW_W, VIEW_H))  # low-res pixel canvas
        self.clock = pygame.time.Clock()
        self.running = True

        self.scenes = SceneManager()
        # The hub owns the three rooms and what they share; the game starts in HOME.
        self.style = STYLES.get(style)      # None: the default (neon_lofi); unknown names fall back
        self.hub = RoomHub(self, self.style)
        self.hub.start()

    def step(self, events, dt):
        """Process one frame. Separate from run() so it can be driven by tests."""
        for event in events:
            if event.type == pygame.QUIT:
                self.quit()
            else:
                self.scenes.handle_event(event)
        self.scenes.update(dt)
        self.scenes.draw(self.canvas, self.screen)

    def quit(self):
        """Close the program; scenes settle anything still in progress (e.g.
        a paid minigame) so its tokens are not lost."""
        if self.running:
            self.running = False
            self.scenes.quit()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.step(pygame.event.get(), dt)
            pygame.display.flip()
        pygame.quit()
