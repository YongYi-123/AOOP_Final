"""The Retro Racer minigame: embeds the standalone game in ../retro_racer.

retro_racer is its own program (it normally opens a window and runs its own
loop), so this scene drives it frame by frame instead: it forwards events to
`Game.handle_event`, calls `Game.update` and draws with `Game.render` at the
full 800x600 resolution. When the racer quits (ESC on its title screen, or Q
in its pause menu) the player is returned to the arcade.
"""
import importlib
import os
import sys
import traceback

import pygame

from font import get_font
from gfx import scale_color, shade
from minigame import MinigameScene
from settings import BACK_KEYS, Col

RETRO_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "retro_racer"))


def load_retro_racer():
    """Import retro_racer's `game` and `race` modules in isolation.

    Both projects have top-level modules called `game`, `settings` and `main`,
    so retro_racer is imported with its folder first on sys.path and its
    modules are then moved out of sys.modules (kept under a "retro_racer."
    prefix), restoring the arcade's own modules. retro_racer's modules keep
    references to each other, so it keeps working afterwards.
    """
    names = {f[:-3] for f in os.listdir(RETRO_DIR) if f.endswith(".py")}
    saved = {n: sys.modules.pop(n) for n in names if n in sys.modules}
    sys.path.insert(0, RETRO_DIR)
    try:
        game_mod = importlib.import_module("game")
        race_mod = importlib.import_module("race")
    finally:
        sys.path.remove(RETRO_DIR)
        for n in names:
            mod = sys.modules.pop(n, None)
            if mod is not None:
                sys.modules[f"retro_racer.{n}"] = mod
        sys.modules.update(saved)
    return game_mod, race_mod


class RetroRacerScene(MinigameScene):
    full_resolution = True

    # The embedded game takes ~2 s to build (sound synthesis, sprite caches),
    # so it is built on the first visit and reused afterwards.
    _racer = None
    _title_state = None

    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.leaving = False
        self.loading_drawn = False
        self.error = None
        font = get_font()
        self.title = font.render_glow(machine.name, shade(machine.accent, 0.6), machine.neon, scale=6)
        self.loading = font.render_glow("LOADING...", Col.TEXT, scale_color(machine.accent, 0.6), scale=3)

    @property
    def racer(self):
        return type(self)._racer

    @property
    def failed(self):
        # No race scoring is wired up yet, so a successful run gets the base
        # class's placeholder payout; a racer that failed to load is refunded.
        return self.error is not None

    # ------------------------------------------------------------ lifecycle
    def on_enter(self):
        if self.racer:
            self._restart()

    def on_exit(self):
        if self.racer:
            self.racer.set_paused(False)
            self.racer.audio.stop_engine()   # otherwise the engine hum follows you out

    def _load(self):
        cls = type(self)
        try:
            game_mod, race_mod = load_retro_racer()
            cls._racer = game_mod.Game(screen=self.game.screen)
            cls._title_state = race_mod.State.TITLE
        except Exception:
            traceback.print_exc()
            self.error = "COULD NOT START RETRO RACER"
            return
        self._restart()

    def _restart(self):
        r = self.racer
        r.screen = self.game.screen
        r.reset()
        r.state = self._title_state
        r.running = True

    # ------------------------------------------------------------ frame
    def handle_event(self, event):
        if self.error:
            if event.type == pygame.KEYDOWN and event.key in BACK_KEYS:
                self._leave()
        elif self.racer and not self.leaving:
            self.racer.handle_event(event)

    def update(self, dt):
        if self.racer is None:
            # First visit: once the wipe has opened on the loading card, build.
            if self.loading_drawn and not self.error and not self.game.scenes.transitioning:
                self._load()
            return
        if self.leaving:
            return
        if not self.racer.running:           # the racer asked to quit
            self.racer.audio.stop_engine()
            self._leave()
            return
        self.racer.update(dt, self.racer.read_controls())

    def _leave(self):
        self.leaving = True
        self.game.scenes.pop()

    def draw(self, surf):
        if self.racer is None:
            self._draw_card(surf)
            self.loading_drawn = True
        else:
            self.racer.screen = surf
            self.racer.render()

    def _draw_card(self, surf):
        surf.fill(Col.FADE)
        w, h = surf.get_size()
        surf.blit(self.title, self.title.get_rect(center=(w // 2, h // 2 - 40)))
        if self.error:
            font = get_font()
            msg = font.render_glow(self.error, Col.MAGENTA, scale_color(Col.MAGENTA, 0.4), scale=2)
            hint = font.render("PRESS ESC TO RETURN TO ARCADE", Col.YELLOW, scale=2)
            surf.blit(msg, msg.get_rect(center=(w // 2, h // 2 + 40)))
            surf.blit(hint, hint.get_rect(center=(w // 2, h // 2 + 80)))
        else:
            surf.blit(self.loading, self.loading.get_rect(center=(w // 2, h // 2 + 50)))
