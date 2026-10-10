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
from racer_results import RacerVisitResults
from rewards import RewardResult
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


# The embedded racer only knows its own keys. This adapter turns the playing
# player's actions into those keys, so the racer never reads the keyboard
# itself and never sees anybody else's keys.
RACER_KEYS = {
    "up": pygame.K_UP, "down": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
    "interact": pygame.K_RETURN, "item": pygame.K_SPACE, "menu": pygame.K_p,
    "pause": pygame.K_p, "back": pygame.K_ESCAPE,
}

# The racer is laid out for this logical size (retro_racer/settings.py WIDTH x HEIGHT). It always
# renders into its own surface of exactly this size, which is then scaled uniformly into whatever
# the window offers, so the window size can never crop or stretch the game.
RACER_SIZE = (800, 600)
SPECTATOR_Y = 148           # logical y of the spectator tag: under the DISTANCE readout, clear of the HUD


def fit_rect(source, target):
    """The largest rect of `source`'s aspect ratio that fits in `target` (both (w, h)),
    centred: uniform scale, letterboxed - never stretched."""
    sw, sh = source
    tw, th = target
    scale = min(tw / sw, th / sh)
    w, h = max(1, round(sw * scale)), max(1, round(sh * scale))
    return pygame.Rect((tw - w) // 2, (th - h) // 2, w, h)


def racer_key_labels(scheme):
    """What the racer's screens should call this player's keys."""
    return {
        "accelerate": scheme.label("up"), "brake": scheme.label("down"),
        "steer": f"{scheme.label('left')}  {scheme.label('right')}",
        "confirm": scheme.label("interact", "confirm"), "back": "ESC",
        "item": scheme.label("item"), "item_long": scheme.label("item", limit=3),
        "resume": f"{scheme.label('menu', 'pause')}/ESC", "menu": "BACKSPACE", "quit": "Q",
    }


class RetroRacerScene(MinigameScene):
    full_resolution = True

    # The embedded game takes ~2 s to build (sound synthesis, sprite caches),
    # so it is built on the first visit and reused afterwards.
    _racer = None
    _title_state = None

    def __init__(self, game, machine):
        super().__init__(game, machine)
        self.leaving = False
        self.surface = pygame.Surface(RACER_SIZE)       # the racer's own logical screen
        self.loading_drawn = False
        self.error = None
        self.results = RacerVisitResults()
        font = get_font()
        self.title = font.render_glow(machine.name, shade(machine.accent, 0.6), machine.neon, scale=6)
        self.loading = font.render_glow("LOADING...", Col.TEXT, scale_color(machine.accent, 0.6), scale=3)

    @property
    def racer(self):
        return type(self)._racer

    @property
    def failed(self):
        # A racer that failed to load is refunded by the existing room flow.
        return self.error is not None

    def get_result(self):
        return self.results.get_result(self.participants)

    def get_reward(self):
        outcome = self.results.outcome
        return RewardResult(self.machine.id, outcome.tickets,
                            None if outcome.status == "abandoned" else outcome.score)

    def on_quit(self):
        if self.racer and not self.error:
            self.results.observe(self.racer)
            self.racer.audio.stop_engine()

    # ------------------------------------------------------------ lifecycle
    def on_enter(self):
        if self.racer:
            try:
                self._restart()
            except Exception as exc:
                self._load_failed(exc)

    def on_exit(self):
        if self.racer and not self.error:
            self.results.observe(self.racer)
            self.racer.set_paused(False)
            self.racer.audio.stop_engine()   # otherwise the engine hum follows you out

    def _load(self):
        cls = type(self)
        try:
            game_mod, race_mod = load_retro_racer()
            cls._racer = game_mod.Game(screen=self.surface)
            cls._title_state = race_mod.State.TITLE
            self._restart()
        except Exception as exc:
            self._load_failed(exc)

    def _load_failed(self, exc):
        traceback.print_exc()
        if self.racer:
            try:
                self.racer.audio.stop_engine()
            except Exception:
                pass  # Initialization may not have created the audio object.
        type(self)._racer = None
        type(self)._title_state = None
        self.error = "COULD NOT START RETRO RACER"
        self.error_kind = type(exc).__name__.upper()

    def _restart(self):
        r = self.racer
        r.screen = self.surface
        r.hud.keys.update(racer_key_labels(self.input.scheme))     # print the player's own keys
        from racing_progression.service import RacingGarage
        profile = self.participants[0] if self.participants else self.game.session.primary.profile
        r.configure_progression(RacingGarage(profile))
        r.reset()
        r.state = self._title_state
        r.running = True

    # ------------------------------------------------------------ input
    def racer_event(self, event):
        """The racer-side key event for `event`, or None if it is not the
        playing player's (the other player's keys vanish here)."""
        inp = self.input
        action = inp.feed(event)
        if event.type != pygame.KEYDOWN:
            return None
        if action:
            key = RACER_KEYS.get(action)
        elif inp.is_shared(event):
            key = event.key
        else:
            return None
        return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="") if key else None

    def racer_controls(self):
        """The racer's steering input, from the playing player's held actions."""
        inp = self.input
        return {"accelerate": inp.held("up"), "brake": inp.held("down"),
                "steer": inp.axis("left", "right")}

    # ------------------------------------------------------------ frame
    def handle_event(self, event):
        if self.error:
            if event.type == pygame.KEYDOWN and event.key in BACK_KEYS:
                self._leave()
        elif self.racer and not self.leaving:
            # Capture the ended run before ENTER / BACKSPACE resets its data.
            self.results.observe(self.racer)
            translated = self.racer_event(event)
            if translated is not None:
                self.racer.handle_event(translated)

    def update(self, dt):
        if self.error or self.leaving:
            return
        if self.racer is None:
            # First visit: once the wipe has opened on the loading card, build.
            if self.loading_drawn and not self.error and not self.game.scenes.transitioning:
                self._load()
            return
        if not self.racer.running:           # the racer asked to quit
            self.racer.audio.stop_engine()
            self._leave()
            return
        self.racer.update(dt, self.racer_controls())
        self.results.observe(self.racer)

    def _leave(self):
        if self.leaving:
            return
        self.leaving = True
        self.game.scenes.pop()

    def draw(self, surf):
        if self.error or self.racer is None:
            self._draw_card(surf)
            self.loading_drawn = True
        else:
            self.racer.screen = self.surface
            self.racer.render()
            self._draw_spectators(self.surface)
            self._present(surf)

    def _present(self, surf):
        """Scale the racer's logical screen uniformly into `surf`, centred (letterboxed)."""
        rect = fit_rect(RACER_SIZE, surf.get_size())
        if rect.size == RACER_SIZE and rect.topleft == (0, 0):
            surf.blit(self.surface, (0, 0))
            return
        surf.fill((0, 0, 0))
        pygame.transform.smoothscale(self.surface, rect.size, surf.subsurface(rect))

    def _draw_spectators(self, surf):
        """A small 'P2 ALICE - SPECTATING' tag, always in free space: while racing, just under the DISTANCE
        readout between the two HUD columns (clear of the stat blocks and the minimap); on the menu and
        result screens, the bottom-right corner."""
        if not self.spectators or self.racer.paused:      # (the pause card owns the centre)
            return
        text = "  ".join(f"{p.tag} - SPECTATING" for p in self.spectators)
        img = get_font().render_glow(text, Col.TEXT_MUTED, (30, 24, 60), scale=2)
        if self.racer.state.name in ("PLAYING", "COUNTDOWN"):
            surf.blit(img, img.get_rect(midtop=(RACER_SIZE[0] // 2, SPECTATOR_Y)))
        else:           # menus and result screens have no HUD: the bottom-right corner is free there
            surf.blit(img, img.get_rect(bottomright=(RACER_SIZE[0] - 10, RACER_SIZE[1] - 6)))

    def draw_overlay(self, surf, px=1):
        pass            # the spectator tag is part of the racer's own screen (see _draw_spectators)

    def _draw_card(self, surf):
        surf.fill(Col.FADE)
        w, h = surf.get_size()
        surf.blit(self.title, self.title.get_rect(center=(w // 2, h // 2 - 40)))
        if self.error:
            font = get_font()
            msg = font.render_glow(self.error, Col.MAGENTA, scale_color(Col.MAGENTA, 0.4), scale=2)
            hint = font.render("PRESS ESC TO RETURN TO ARCADE", Col.YELLOW, scale=2)
            surf.blit(msg, msg.get_rect(center=(w // 2, h // 2 + 40)))
            detail = font.render(getattr(self, "error_kind", "LOAD ERROR"), Col.TEXT_MUTED, scale=2)
            surf.blit(detail, detail.get_rect(center=(w // 2, h // 2 + 60)))
            surf.blit(hint, hint.get_rect(center=(w // 2, h // 2 + 80)))
        else:
            surf.blit(self.loading, self.loading.get_rect(center=(w // 2, h // 2 + 50)))
