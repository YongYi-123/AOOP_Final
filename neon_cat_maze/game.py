"""NEON CAT MAZE flow: title, how to play, play, pause and results, plus the per-play-session best run that the lobby
pays out. Input arrives as logical actions; drawing is in rendering.py."""
import random
from enum import Enum

from . import config as cfg
from .effects import Fx
from .mazes import MAZES
from .model import Run, STOP
from .rendering import Renderer, tile_center
from .settlement import RunResult


class Screen(Enum):
    TITLE = "title"
    HOWTO = "howto"
    PLAYING = "playing"
    PAUSED = "paused"
    OVER = "over"          # the results screen (the GAME OVER banner is a phase of the run)


TITLE_MENU = ("START", "HOW TO PLAY")
PAUSE_MENU = ("RESUME", "RESTART", "RETURN TO LOBBY")
OVER_MENU = ("PLAY AGAIN", "RETURN TO LOBBY")
DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

SOUNDS = {"fish": "maze_fish", "golden": "maze_golden", "catnip": "maze_catnip", "disable": "maze_disable",
          "life_lost": "maze_life", "level_clear": "maze_clear", "game_over": "maze_over", "extra_life": "powerup",
          "golden_spawn": "maze_golden_spawn", "catnip_end": "maze_catnip_end"}


class CatMazeGame:
    def __init__(self, rng=None, audio=None, seed=None):
        self.seed = seed
        self.rng = rng or random.Random(seed)
        self.audio = audio                   # anything with .play(name); None is silent
        self.screen = Screen.TITLE
        self.cursor = 0
        self.run = Run(self.rng)
        self.fx = Fx()
        self.renderer = Renderer()
        self.demo_maze = MAZES[0]
        self.saved_score = 0                 # the profile's records, shown but never changed here
        self.saved_level = 0
        self.best = RunResult()              # the run of this play session with the most tickets (the one paid)
        self.session_score = 0               # the highest score of ANY run this session: a record is never lowered
                                             # just because another run earned more tickets (e.g. more levels, less score)
        self.session_level = 0               # the highest level reached in any run of this session
        self.wants_exit = False
        self.keys = {"move": "WASD", "pause": "P"}       # labels the lobby scene fills in for the player's own keys
        self._counted = None                 # the last Run folded into the session records
        self._fish_toggle = False
        self.time = 0.0
        self.paused = False

    # ------------------------------------------------------------ records
    @property
    def has_played(self):
        return self._counted is not None

    @property
    def personal_best(self):
        return max(self.saved_score, self.session_score, self.run.score if self.screen is not Screen.TITLE else 0)

    @property
    def best_level(self):
        return max(self.saved_level, self.best.level, self.run.level if self.run.score else 0)

    @property
    def new_record(self):
        return self.run.score > self.saved_score and self.run.score >= self.session_score

    def observe(self):
        """Fold the current run into the session records. Safe to call any number of times, at any moment (a run only
        ever grows, so folding it again can only raise a record, never double-count it). A run that never scored adds
        nothing."""
        if self.run.score <= 0:
            return
        self._counted = self.run
        result = self.run.result()
        self.session_score = max(self.session_score, result.score)
        self.session_level = max(self.session_level, result.level)
        if result.better_than(self.best):
            self.best = result

    def hint_line(self):
        return f"{self.keys['move']} MOVE  {self.keys['pause']} PAUSE  ESC MENU"

    # ------------------------------------------------------------ flow
    def new_run(self):
        self.observe()
        self.run = Run(self.rng)
        self.fx = Fx(self.fx.reduced)
        self.screen, self.cursor, self.paused = Screen.PLAYING, 0, False

    def leave(self):
        self.observe()
        self.wants_exit = True

    def toggle_reduced(self):
        self.fx.reduced = not self.fx.reduced

    def menu(self):
        return {Screen.TITLE: TITLE_MENU, Screen.PAUSED: PAUSE_MENU, Screen.OVER: OVER_MENU}.get(self.screen, ())

    def pause(self):
        if self.screen is Screen.PLAYING and self.run.phase != "over":
            self.screen, self.cursor, self.paused = Screen.PAUSED, 0, True

    def resume(self):
        if self.screen is Screen.PAUSED:
            self.screen, self.paused = Screen.PLAYING, False

    def steer(self, direction):
        """A direction key: (dx, dy) or its name. Only meaningful while playing."""
        if isinstance(direction, str):
            direction = DIRECTIONS[direction]
        if self.screen is Screen.PLAYING:
            self.run.steer(direction)

    def act(self, action):
        """One logical key press: up, down, confirm or back (ESC)."""
        s, menu = self.screen, self.menu()
        if s is Screen.PLAYING and action in DIRECTIONS:
            self.steer(action)
        elif action in ("up", "down") and menu:
            self.cursor = (self.cursor + (1 if action == "down" else -1)) % len(menu)
            self._sound("confirm")
        elif action == "confirm":
            if s is Screen.PLAYING:
                if self.run.phase == "clear":
                    self.run.skip_clear()
                elif self.run.phase == "over" and self.run.phase_time > 0.4:
                    self._to_results()
                return
            self._confirm(menu[self.cursor] if menu else None)
        elif action == "back":
            if s is Screen.PLAYING:
                self.pause()
            elif s is Screen.PAUSED:
                self.resume()
            elif s is Screen.HOWTO:
                self.screen, self.cursor = Screen.TITLE, 1
            else:
                self.leave()

    def _confirm(self, choice):
        s = self.screen
        if s is Screen.HOWTO:
            self.screen, self.cursor = Screen.TITLE, 1
        elif choice in ("START", "PLAY AGAIN", "RESTART"):
            self.new_run()
        elif choice == "HOW TO PLAY":
            self.screen = Screen.HOWTO
        elif choice == "RESUME":
            self.resume()
        elif choice == "RETURN TO LOBBY":
            self.leave()
        self._sound("confirm")

    def _sound(self, name):
        if self.audio and name:
            self.audio.play(name)

    def _to_results(self):
        self.observe()
        self.screen, self.cursor = Screen.OVER, 0

    # ------------------------------------------------------------ frame
    def update(self, dt):
        self.time += dt
        if self.screen is not Screen.PLAYING:
            if self.screen is Screen.OVER:
                self.fx.update(dt)
            return
        self.run.update(dt)
        for event in self.run.take_events():
            self._react(event)
        if self.run.phase == "clear":
            self.fx.confetti(dt, cfg.FIELD_W)
        self.fx.update(dt)
        if self.run.over and self.run.phase_time >= cfg.OVER_SECONDS:
            self._to_results()

    def _react(self, event):
        fx, kind = self.fx, event.name
        x, y = tile_center(event.x, event.y)
        if kind == "fish":
            fx.burst("fish", x, y)
        elif kind == "golden":
            fx.burst("golden", x, y)
            fx.ring(x, y, 20, (255, 214, 90))
            fx.popup(f"+{event.amount}", x, y - 6, (255, 214, 90))
        elif kind == "catnip":
            fx.burst("catnip", x, y)
            fx.ring(x, y, 46, (130, 255, 160), 0.7)
            fx.ring(x, y, 28, (90, 240, 255), 0.5)
            fx.popup("CATNIP POWER!", x, y - 12, (130, 255, 160), 1.3)
            fx.pulse(0.1, (60, 220, 130))
        elif kind == "disable":
            fx.burst("disable", x, y)
            fx.ring(x, y, 22, (255, 150, 60), 0.45)
            fx.popup(f"+{event.amount}", x, y - 6, (255, 255, 255))
        elif kind == "life_lost":
            fx.burst("death", x, y)
            fx.hit_shake(0.3)
            fx.pulse(0.2)
        elif kind == "game_over":
            fx.hit_shake(0.2)
        elif kind == "level_clear":
            for _ in range(3):
                fx.burst("confetti", x, y)
            fx.ring(x, y, 60, (255, 214, 90), 0.8)
        elif kind == "extra_life":
            fx.popup("EXTRA LIFE!", x, y - 10, (255, 120, 205), 1.3)
        elif kind == "golden_spawn":
            fx.ring(x, y, 14, (255, 214, 90), 0.5)
        if kind == "fish":                                    # two alternating pitches make a happy munch
            self._fish_toggle = not self._fish_toggle
            self._sound("maze_fish" if self._fish_toggle else "maze_fish_b")
        else:
            self._sound(SOUNDS.get(kind))

    def draw(self, surface):
        self.renderer.draw(surface, self)


__all__ = ["CatMazeGame", "Screen", "STOP"]
