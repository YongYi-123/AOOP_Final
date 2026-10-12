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

from display import DisplayManager
from audio_settings_ui import AudioSettingsScene, draw_debug_hud
from audio_manager import DEFAULT_SFX, DUCK_PAUSED, AudioManager
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
                 profiles=None, session=None, audio_prefs=None, display_prefs=None):
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
        self.display = DisplayManager(prefs_path=display_prefs, caption=TITLE)   # the window, resizing, fullscreen
        self.canvas = pygame.Surface((VIEW_W, VIEW_H))  # low-res pixel canvas
        self.clock = pygame.time.Clock()
        self.running = True

        self.audio = AudioManager(prefs_path=audio_prefs)     # volumes + mute are saved there (None: not saved)
        self.audio.preload()
        import cat_voice                    # the cats' meows follow the hub's effects volume and mute
        self._cat_gain = cat_voice.master_gain = lambda: self.audio.effective_sfx / DEFAULT_SFX
        self._cat_route = cat_voice.route = lambda sound, volume: self.audio.play_object(sound, "meow", 1, volume)
        self._cat_sfx = cat_voice.sfx_route = self.audio.play
        if session is None:
            self.audio.switch("lobby")      # the title / profile screens play the hub theme; a session picks its room's
        if not self.audio.enabled:
            print(f"[audio] OFF: {self.audio.init_error}  (run: python audio_diagnostics.py)", file=sys.stderr)
        self.audio_hud = False              # F10: the developer audio HUD
        self.volume_toast = 0.0             # seconds left on the "MUSIC 22%  SFX 70%" readout
        self.scenes = SceneManager()
        self.style = STYLES.get(style)      # None: the default (neon_lofi); unknown names fall back
        if session is not None:
            self.start_session(session)
        else:
            self.startup = StartupFlow(self, profiles)
            self.startup.begin()

    @property
    def screen(self):
        """The presentation surface every scene draws its final frame on (always 4:3; see display.py)."""
        return self.display.screen

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
                if self.display.handle_event(event):             # resize / maximise / minimise: dealt with once
                    continue
                event = self.display.convert_mouse(event)        # window pixels -> scene pixels; bars reject clicks
                if event is None:
                    continue
                if event.type == pygame.KEYDOWN and (
                        event.key == pygame.K_F11 or
                        (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and event.mod & pygame.KMOD_ALT)):
                    self.display.toggle_fullscreen()             # Alt+Enter / F11
                    continue
                if event.type == pygame.KEYDOWN:
                    actor = self.session.player_for_key(event.key) if self.session else None
                    action = actor.controls.action_for(event.key) if actor else None
                    own = getattr(self.scenes.current, "own_audio", False)    # a minigame has its own click sounds
                    if action == "interact" or event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if not own:
                            self.audio.play("confirm")
                    elif event.key == pygame.K_ESCAPE:
                        if not own:
                            self.audio.play("cancel")
                    elif event.key == pygame.K_F10:
                        self.audio_hud = not self.audio_hud        # developer HUD: off by default, never pauses play
                    elif event.key == pygame.K_F4:
                        self.open_audio_settings()
                        continue
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
        self.audio.sync_scenes(self.scene_keys())
        self.audio.switch(self.music_for(self.scenes.stack))
        self.audio.set_duck(self.duck_for(self.scenes.current))
        racer = getattr(self.scenes.current, "racer", None)
        if racer and hasattr(racer, "audio"):
            racer.audio.external_gain = self.audio.effective_sfx
        self.volume_toast = max(0.0, self.volume_toast - dt)
        self.scenes.draw(self.canvas, self.screen)
        if self.audio_hud:
            draw_debug_hud(self, self.screen)
        if self.volume_toast > 0:
            self._draw_volume_toast()
        elif self.audio.muted or not self.audio.enabled:
            self._draw_audio_badge()

    @staticmethod
    def music_for(scenes):
        """The music theme to play. `scenes` is the scene stack (or one scene): the topmost scene that has a
        theme decides - a minigame's own theme, or a room's / Lucky Corner game's `music_id` - so a menu or dialog
        opened on top of a game or room keeps that scene's music (and never restarts it), and a game that ends
        hands the music straight back to the room below it. None keeps whatever is playing (the start screens)."""
        for scene in reversed(scenes if isinstance(scenes, (list, tuple)) else [scenes]):
            machine = getattr(scene, "machine", None)
            theme = machine.id if machine is not None else getattr(scene, "music_id", None)
            if theme:
                return theme
        return None

    def scene_keys(self):
        """[(key, label)] of the scenes on the stack, bottom first: what the audio manager needs to give each scene
        one effect channel of its own and to free it when the scene leaves."""
        out = []
        for scene in self.scenes.stack:
            machine = getattr(scene, "machine", None)
            name = type(scene).__name__.replace("Scene", "")
            out.append((id(scene), (machine.id if machine is not None else name)[:10].upper()))
        return out

    PAUSABLE = ("racer", "volley", "galaxy", "territory", "cat_maze")

    @classmethod
    def duck_for(cls, scene):
        """Music level while a minigame is paused: lowered, so the pause card is easy to read.
        A scene can also ask for its own level with `music_duck` (e.g. the vending machine's secret page)."""
        own = getattr(scene, "music_duck", None)
        if own is not None:
            return own
        for attr in cls.PAUSABLE:
            inner = getattr(scene, attr, None)
            if inner is None:
                continue
            state = getattr(getattr(inner, "match", None), "state", None) or getattr(inner, "screen", None)
            if getattr(inner, "paused", False) is True or getattr(state, "name", "") == "PAUSED":
                return DUCK_PAUSED
        return 1.0

    def _draw_volume_toast(self):
        """A small readout of the music / effects volume, mute and the track playing, over the finished frame."""
        from font import get_font
        a = self.audio
        text = "MUTED  (M)" if a.muted else f"MUSIC {round(a.bgm_volume * 100)}%   SFX {round(a.sfx_volume * 100)}%"
        if not a.enabled:
            text = "NO AUDIO DEVICE"
        lines = [text] + ([a.track_title] if a.enabled and a.track_title else [])
        px = max(1, self.screen.get_height() // VIEW_H)
        y = 4 * px
        for i, line in enumerate(lines):
            colour, glow = ((255, 214, 90), (90, 60, 20)) if i == 0 else ((170, 150, 230), (50, 36, 90))
            img = get_font().render_glow(line, colour, glow, scale=px)
            rect = img.get_rect(midtop=(self.screen.get_width() // 2, y))
            self.screen.fill((14, 8, 34), rect.inflate(8 * px, 4 * px))
            self.screen.blit(img, rect)
            y = rect.bottom + 3 * px

    def open_audio_settings(self):
        """F4: the AUDIO SETTINGS screen (F4 again closes it). The music underneath keeps playing; a racing
        engine is silenced while the screen is up (the race is not updated behind it)."""
        current = self.scenes.current
        if isinstance(current, AudioSettingsScene):
            current.close()
            return
        if self.scenes.transitioning:
            return
        racer = getattr(current, "racer", None)
        if racer is not None and hasattr(racer, "audio"):
            racer.audio.engine(0, False)
        self.scenes.push(AudioSettingsScene(self))

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
            import cat_voice
            if cat_voice.master_gain is self._cat_gain:
                cat_voice.master_gain = lambda: 1.0
            if cat_voice.sfx_route == self._cat_sfx:
                cat_voice.sfx_route = None
            if cat_voice.route is self._cat_route:
                cat_voice.route = None

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.step(pygame.event.get(), dt)
            self.display.present()
        self.display.save()
        pygame.quit()
