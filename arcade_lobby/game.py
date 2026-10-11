"""Top-level Game object: window, main loop and pixel-perfect upscaling.

How the game starts:
  Game(profiles=ProfileManager(...))  the real startup flow: TITLE, PLAYER COUNT,
                                      PROFILE SELECT, then the arcade hub
  Game(session=LocalSession(...))     straight into the hub with those players
  Game(save_path=...)                 straight into a one-player hub with the one
                                      profile stored in that single file (the
                                      original behaviour; used by tools and tests)
"""
import sys

import pygame

from audio_manager import AudioManager
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
                 profiles=None, session=None, audio_prefs=None):
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

        self.audio = AudioManager(prefs_path=audio_prefs)     # volumes + mute are saved there (None: not saved)
        if session is None:
            self.audio.switch("lobby")      # the title / profile screens play the hub theme; a session picks its room's
        if not self.audio.enabled:
            print(f"[audio] OFF: {self.audio.init_error}  (run: python audio_diagnostics.py)", file=sys.stderr)
        self.volume_toast = 0.0             # seconds left on the "MUSIC 22%  SFX 70%" readout
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
                if event.type == pygame.KEYDOWN:
                    actor = self.session.player_for_key(event.key) if self.session else None
                    action = actor.controls.action_for(event.key) if actor else None
                    if action == "interact" or event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.audio.play("confirm")
                    elif event.key == pygame.K_ESCAPE:
                        self.audio.play("cancel")
                    elif event.key in (pygame.K_F6, pygame.K_F7):
                        self.audio.set_volumes(bgm=self.audio.bgm_volume + (-.1 if event.key == pygame.K_F6 else .1))
                        self.volume_toast = 2.0
                    elif event.key in (pygame.K_F8, pygame.K_F9):
                        self.audio.set_volumes(sfx=self.audio.sfx_volume + (-.1 if event.key == pygame.K_F8 else .1))
                        self.volume_toast = 2.0
                    elif event.key == pygame.K_m and not (actor and actor.controls.owns(event.key)):
                        self.audio.toggle_mute()
                        self.volume_toast = 2.0
                self.scenes.handle_event(event)
        self.scenes.update(dt)
        self.audio.update(dt)
        self.audio.switch(self.music_for(self.scenes.current))
        racer = getattr(self.scenes.current, "racer", None)
        if racer and hasattr(racer, "audio"):
            racer.audio.external_gain = self.audio.effective_sfx
        self.volume_toast = max(0.0, self.volume_toast - dt)
        self.scenes.draw(self.canvas, self.screen)
        if self.volume_toast > 0:
            self._draw_volume_toast()
        elif self.audio.muted or not self.audio.enabled:
            self._draw_audio_badge()

    @staticmethod
    def music_for(scene):
        """The music theme a scene wants: a minigame's own theme, a room's or Lucky Corner
        game's `music_id`, or None for menus / dialogs / the start screens, which keep
        whatever is already playing (so opening a menu never restarts the song)."""
        machine = getattr(scene, "machine", None)
        if machine is not None:
            return machine.id
        return getattr(scene, "music_id", None)

    def _draw_volume_toast(self):
        """A small readout of the music / effects volume and mute, over the finished frame."""
        from font import get_font
        a = self.audio
        text = "MUTED  (M)" if a.muted else f"MUSIC {round(a.bgm_volume * 100)}%   SFX {round(a.sfx_volume * 100)}%"
        if not a.enabled:
            text = "NO AUDIO DEVICE"
        px = max(1, self.screen.get_height() // VIEW_H)
        img = get_font().render_glow(text, (255, 214, 90), (90, 60, 20), scale=px)
        rect = img.get_rect(midtop=(self.screen.get_width() // 2, 4 * px))
        self.screen.fill((14, 8, 34), rect.inflate(8 * px, 4 * px))
        self.screen.blit(img, rect)

    def _draw_audio_badge(self):
        """A small always-visible reminder in the top-right corner while music is off."""
        from font import get_font
        px = max(1, self.screen.get_height() // VIEW_H)
        text = "MUTED (M)" if self.audio.muted else "NO AUDIO"
        img = get_font().render_glow(text, (255, 120, 140), (90, 20, 40), scale=px)
        rect = img.get_rect(topright=(self.screen.get_width() - 4 * px, 3 * px))
        self.screen.fill((14, 8, 34), rect.inflate(4 * px, 2 * px))
        self.screen.blit(img, rect)

    def quit(self):
        """Close the program; scenes settle anything still in progress (e.g.
        a paid minigame) so its tokens are not lost."""
        if self.running:
            self.running = False
            self.scenes.quit()
            self.audio.stop()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.step(pygame.event.get(), dt)
            pygame.display.flip()
        pygame.quit()
