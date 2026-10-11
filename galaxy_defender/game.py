"""Starfall Assault flow: title, how to play, play, pause and game over, plus the per-play-session
best run that the lobby pays out. Input arrives as logical actions; drawing is in rendering.py."""
import random
from enum import Enum

from . import config as cfg
from .effects import Fx, Starfield
from .model import Run
from .rendering import Renderer
from .settlement import RunResult


class Screen(Enum):
    TITLE = "title"
    HOWTO = "howto"
    PLAYING = "playing"
    PAUSED = "paused"
    OVER = "over"


TITLE_MENU = ("START", "HOW TO PLAY")
PAUSE_MENU = ("RESUME", "RESTART", "RETURN TO LOBBY")
OVER_MENU = ("RETRY", "RETURN TO LOBBY")

SOUNDS = {"shoot": "laser", "enemy_down": "boom", "player_hit": "loss", "shield_break": "hit", "pickup": "powerup",
          "wave_clear": "win", "combo": "point", "boss_down": "win", "game_over": "loss", "boss_arrive": "machine"}


class GalaxyGame:
    def __init__(self, rng=None, audio=None):
        self.rng = rng or random.Random()
        self.audio = audio                   # anything with .play(name); None is silent
        self.screen = Screen.TITLE
        self.cursor = 0
        self.run = Run(self.rng)
        self.fx = Fx()
        self.stars = Starfield()
        self.renderer = Renderer()
        self.saved_score = 0                 # the profile's records, shown but never changed here
        self.saved_wave = 0
        self.best = RunResult()              # the best finished run of this play session (the one paid)
        self.session_wave = 0                # the highest wave reached in any run of this session
        self.wants_exit = False
        self._counted = None                 # the Run already folded into `best`
        self.time = 0.0

    # ------------------------------------------------------------ records
    @property
    def has_played(self):
        return self._counted is not None

    @property
    def personal_best(self):
        return max(self.saved_score, self.best.score, self.run.score)

    @property
    def best_wave(self):
        return max(self.saved_wave, self.best.wave, self.run.reached if self.run.score else 0)

    @property
    def new_record(self):
        return self.run.score > max(self.saved_score, 0) and self.run.score >= self.best.score

    def observe(self):
        """Fold the current run into the session best, once. A run that never scored adds nothing."""
        if self._counted is self.run or self.run.score <= 0:
            return
        self._counted = self.run
        result = self.run.result()
        self.session_wave = max(self.session_wave, result.wave)
        if result.better_than(self.best):
            self.best = result

    # ------------------------------------------------------------ flow
    def new_run(self):
        self.observe()
        self.run = Run(self.rng)
        self.fx = Fx(self.fx.reduced)
        self.screen, self.cursor = Screen.PLAYING, 0

    def leave(self):
        self.observe()
        self.wants_exit = True

    def toggle_reduced(self):
        self.fx.reduced = not self.fx.reduced

    def menu(self):
        return {Screen.TITLE: TITLE_MENU, Screen.PAUSED: PAUSE_MENU, Screen.OVER: OVER_MENU}.get(self.screen, ())

    def pause(self):
        if self.screen is Screen.PLAYING:
            self.screen, self.cursor = Screen.PAUSED, 0

    def act(self, action):
        """One logical key press: up, down, confirm or back (ESC)."""
        s, menu = self.screen, self.menu()
        if action in ("up", "down") and menu:
            self.cursor = (self.cursor + (1 if action == "down" else -1)) % len(menu)
            self._sound("confirm")
        elif action == "confirm":
            self._confirm(menu[self.cursor] if menu else None)
        elif action == "back":
            if s is Screen.PLAYING:
                self.pause()
            elif s is Screen.PAUSED:
                self.screen = Screen.PLAYING
            elif s is Screen.HOWTO:
                self.screen, self.cursor = Screen.TITLE, 1
            else:
                self.leave()

    def _confirm(self, choice):
        s = self.screen
        if s is Screen.HOWTO:
            self.screen, self.cursor = Screen.TITLE, 1
        elif choice in ("START", "RETRY", "RESTART"):
            self.new_run()
        elif choice == "HOW TO PLAY":
            self.screen = Screen.HOWTO
        elif choice == "RESUME":
            self.screen = Screen.PLAYING
        elif choice == "RETURN TO LOBBY":
            self.leave()
        self._sound("confirm")

    def _sound(self, name):
        if self.audio and name:
            self.audio.play(name)

    # ------------------------------------------------------------ frame
    def update(self, dt, move=0, fire=False):
        self.time += dt
        self.stars.update(dt, 4.0 if self.screen is Screen.PLAYING and self.run.banner_active else 1.0)
        if self.screen is not Screen.PLAYING:
            if self.screen is Screen.OVER:
                self.fx.update(dt)
            return
        self.run.update(dt, move, fire)
        for event in self.run.take_events():
            self._react(event)
        self.fx.update(dt)
        if self.run.over:
            self.observe()
            self.screen, self.cursor = Screen.OVER, 0

    def _react(self, event):
        fx, kind = self.fx, event.name
        if kind == "shoot":
            fx.muzzle(event.x, event.y, event.kind)
        elif kind == "enemy_down":
            fx.burst(event.x, event.y, event.kind)
        elif kind == "enemy_hit" and not fx.reduced:
            fx.burst(event.x, event.y, event.kind or "spark")
        elif kind == "player_hit":
            fx.burst(event.x, event.y, "player", True)
            fx.hit_shake()
            fx.pulse()
        elif kind == "shield_break":
            fx.burst(event.x, event.y, "spark")
            fx.ring(event.x, event.y, 20, (70, 130, 255))
            fx.hit_shake(0.12)
        elif kind == "boss_down":
            fx.burst(event.x, event.y, "boss", True)
            fx.hit_shake(0.45)
            fx.pulse(0.2)
        elif kind == "game_over":
            fx.burst(event.x, event.y, "player", True)
            fx.hit_shake(0.4)
        elif kind == "pickup":
            fx.burst(event.x, event.y, "core")
            fx.ring(event.x, event.y, 16, (255, 226, 100), 0.5)
            fx.popup(cfg.POWERUPS[event.kind]["label"], event.x, event.y)
        elif kind == "combo":
            fx.popup(f"COMBO X{event.kind}", event.x, event.y, (255, 160, 60))
        self._sound(SOUNDS.get(kind))

    def draw(self, surface):
        self.renderer.draw(surface, self)
