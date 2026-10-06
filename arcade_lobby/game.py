"""Top-level Game object: window, main loop and pixel-perfect upscaling.

How the game starts:
  Game(profiles=ProfileManager(...))  the real startup flow: TITLE, PLAYER COUNT,
                                      PROFILE SELECT, then the arcade hub
  Game(session=LocalSession(...))     straight into the hub with those players
  Game(save_path=...)                 straight into a one-player hub with the one
                                      profile stored in that single file (the
                                      original behaviour; used by tools and tests)
"""
import pygame

from game_clock import GameClock
from menus import StartupFlow
from player_profile import ProfileStore
from arcade_style import STYLES
from local_session import LocalSession
from room_scene import RoomHub
from scene_base import SceneManager
from settings import (DEBUG, FPS, SAVE_FILE, SCREEN_H, SCREEN_W, TITLE, VIEW_H,
                      VIEW_W)


class Game:
    def __init__(self, style=None, save_path=SAVE_FILE, debug=DEBUG, clock=None,
                 profiles=None, session=None):
        self.debug = debug
        self.clock = clock or GameClock()
        self.profiles = profiles            # ProfileManager, when the startup flow is used
        self.session = None                 # the LocalSession, once players have been chosen
        self.hub = None
        self.store = None
        if session is None and profiles is None:
            # One profile in one file, autosaved on every change.
            self.store = ProfileStore(save_path, self.clock)
            profile = self.store.load()
            self.store.autosave(profile)
            session = LocalSession([profile])

        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.canvas = pygame.Surface((VIEW_W, VIEW_H))  # low-res pixel canvas
        self.clock = pygame.time.Clock()
        self.running = True

        self.scenes = SceneManager()
        self.style = STYLES.get(style)      # None: the default (neon_lofi); unknown names fall back
        if session is not None:
            self.start_session(session)
        else:
            self.startup = StartupFlow(self, profiles)
            self.startup.begin()

    @property
    def profile(self):
        """P1's profile (the only one in a one-player game); None until players are chosen."""
        return self.session.primary.profile if self.session else None

    def start_session(self, session, from_menu=False):
        """Begin play with `session`. The hub owns the three rooms and what they
        share; the game starts in HOME."""
        self.session = session
        self.hub = RoomHub(self, self.style)
        self.hub.start(replace=from_menu)

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
