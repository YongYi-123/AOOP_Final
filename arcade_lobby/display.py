"""The display system: one authoritative pipeline from the arcade's drawing surfaces to the real window and
back again for the mouse.

Rendering, unchanged for every scene:  scenes draw into the 400x300 logical canvas (or, for Retro Racer, their
own 800x600 surface), the SceneManager scales the canvas by a whole number onto `DisplayManager.screen`, the
*presentation surface*, and HUD overlays are drawn on that. The presentation surface is always 4:3
(400*s x 300*s) so every scene keeps its layout whatever the window does.

Presentation (this module): the presentation surface is placed on the real window, centred, with black bars
where the aspect ratios differ.
    INTEGER  the surface is a whole multiple of the 400x300 canvas and is blitted 1:1 - crisp pixels. A window
             smaller than the canvas falls back to a smooth shrink (nothing is ever clipped).
    FIT      the largest 4:3 rectangle that fits, never stretched unevenly; a smooth filter is used when the
             window's scale is not a whole number.

Input: `Game.step` sends every mouse event through `DisplayManager.convert_mouse`, which turns window pixels
into presentation-surface pixels (the coordinates all scenes already use) and rejects clicks in the bars.
Everything here that is arithmetic is a pure function (compute_layout, window_to_screen, ...) so it is tested
without a window.

Persistence: saves/display.json (mode, scaling, windowed size), separate from the player profiles.
"""
import json
import logging
import math
import os
import time
from dataclasses import dataclass

import pygame

from settings import VIEW_H, VIEW_W

log = logging.getLogger("arcade.display")

BASE_W, BASE_H = VIEW_W, VIEW_H
MIN_WINDOW = (320, 240)                 # smallest window we ask the OS for (smaller reports are still survived)
SAFE_SIZE = (800, 600)                  # where every failure falls back to
INT_MAX = 6                             # largest whole-number scale used by INTEGER mode
FIT_SURFACE_MAX = 4                     # largest presentation-surface scale in FIT mode (bigger windows scale it up)
MODES = ("windowed", "borderless", "fullscreen")
SCALINGS = ("integer", "fit")
PRESETS = ((640, 480), (800, 600), (1024, 768), (1280, 720), (1366, 768), (1600, 900), (1920, 1080), (2560, 1440))
RESIZE_EVENTS = tuple(getattr(pygame, n) for n in ("VIDEORESIZE", "WINDOWRESIZED", "WINDOWSIZECHANGED",
                                                   "WINDOWMAXIMIZED", "WINDOWMINIMIZED", "WINDOWRESTORED",
                                                   "WINDOWDISPLAYCHANGED") if hasattr(pygame, n))
MOUSE_EVENTS = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL)


# ------------------------------------------------------------------ pure calculations
@dataclass(frozen=True)
class Layout:
    window: tuple           # the real window size
    rect: pygame.Rect       # where the presentation surface sits in the window
    screen_size: tuple      # the presentation surface (400*scale x 300*scale)
    scale: int              # the presentation surface's whole-number scale of the canvas
    factor: float           # window pixels per presentation-surface pixel (1.0 when exact)
    scaling: str            # the scaling mode asked for
    exact: bool             # blitted 1:1: no filtering at all

    @property
    def bars(self):
        return self.rect.size != self.window


def compute_layout(window, scaling="integer"):
    """Where the 4:3 presentation surface goes in a window of size `window` (never zero-sized)."""
    ww, wh = max(1, int(window[0])), max(1, int(window[1]))
    fit = min(ww / BASE_W, wh / BASE_H)
    if scaling == "integer" and fit >= 1:
        k = min(int(fit), INT_MAX)
        scale, size, factor = k, (BASE_W * k, BASE_H * k), 1.0
    else:
        scale = 1 if fit < 1 else min(FIT_SURFACE_MAX, max(1, math.ceil(fit - 1e-9)))
        size = (min(ww, max(1, int(BASE_W * fit + .5))), min(wh, max(1, int(BASE_H * fit + .5))))
        factor = size[0] / (BASE_W * scale)
    rect = pygame.Rect(0, 0, *size)
    rect.center = (ww // 2, wh // 2)
    rect.clamp_ip(pygame.Rect(0, 0, ww, wh))
    screen_size = (BASE_W * scale, BASE_H * scale)
    return Layout((ww, wh), rect, screen_size, scale, factor, scaling, size == screen_size)


def window_to_screen(layout, pos):
    """Window pixel -> presentation-surface pixel, or None when the point is in a black bar."""
    if not layout.rect.collidepoint(pos):
        return None
    return clamp_point(((pos[0] - layout.rect.x) / layout.factor, (pos[1] - layout.rect.y) / layout.factor),
                       layout.screen_size)


def clamp_point(point, size):
    return (max(0, min(size[0] - 1, int(point[0]))), max(0, min(size[1] - 1, int(point[1]))))


def clamp_to_screen(layout, pos):
    """Like window_to_screen but a point in a bar lands on the nearest edge (for releases and drags)."""
    r = layout.rect
    inside = (max(r.left, min(r.right - 1, pos[0])), max(r.top, min(r.bottom - 1, pos[1])))
    return window_to_screen(layout, inside)


def screen_to_window(layout, pos):
    return (int(layout.rect.x + pos[0] * layout.factor), int(layout.rect.y + pos[1] * layout.factor))


def screen_to_canvas(pos, screen_size):
    """Presentation-surface pixel -> 400x300 canvas pixel (what every menu hit-test uses)."""
    w, h = max(1, screen_size[0]), max(1, screen_size[1])
    return int(pos[0] * VIEW_W / w), int(pos[1] * VIEW_H / h)


# ------------------------------------------------------------------ settings
@dataclass(frozen=True)
class DisplaySettings:
    mode: str = "windowed"
    scaling: str = "integer"
    size: tuple = SAFE_SIZE

    def to_dict(self):
        return {"mode": self.mode, "scaling": self.scaling, "size": list(self.size)}


DEFAULTS = DisplaySettings()


def validate_settings(data, desktop=None):
    """Saved / requested settings made safe: unknown values become the defaults, a window size is kept inside
    [MIN_WINDOW, the desktop]. Never raises."""
    if not isinstance(data, dict):
        return DEFAULTS
    mode = data.get("mode") if data.get("mode") in MODES else DEFAULTS.mode
    scaling = data.get("scaling") if data.get("scaling") in SCALINGS else DEFAULTS.scaling
    size = data.get("size")
    ok = (isinstance(size, (list, tuple)) and len(size) == 2 and
          all(isinstance(v, int) and not isinstance(v, bool) for v in size))
    if not ok:
        size = SAFE_SIZE
    w, h = size
    top = desktop or (16384, 16384)
    w, h = max(MIN_WINDOW[0], min(w, max(MIN_WINDOW[0], top[0]))), max(MIN_WINDOW[1], min(h, max(MIN_WINDOW[1], top[1])))
    return DisplaySettings(mode, scaling, (w, h))


def size_presets(desktop, current=None):
    """The window-size choices: the standard presets that fit the desktop, plus the actual current size."""
    sizes = [p for p in PRESETS if p[0] <= desktop[0] and p[1] <= desktop[1]] or [SAFE_SIZE]
    if current and tuple(current) not in sizes:
        sizes.append(tuple(current))
    return sorted(set(sizes), key=lambda s: (s[0] * s[1], s))


# ------------------------------------------------------------------ the manager
class DisplayManager:
    """Owns the window, the presentation surface and the display settings. Never raises into the game: a
    failed mode change falls back to the safe 800x600 window."""

    def __init__(self, prefs_path=None, caption=None):
        self.prefs_path = prefs_path
        self.caption = caption
        self.window = None                      # the pygame display Surface
        self.window_size = (0, 0)
        self.screen = pygame.Surface((BASE_W * 2, BASE_H * 2))          # the presentation surface
        self.layout = compute_layout(SAFE_SIZE)
        self.minimized = False
        self.last_error = None
        self.rebuilds = 0                       # presentation-surface rebuilds (tests: no duplicate rebuilds)
        self.pending_size = None                # a windowed size we asked the OS for and are waiting to see
        self.pending_tries = 0
        self.pending_until = 0.0
        self.mode_changes = 0
        pygame.display.init()
        self.settings = validate_settings(self._load(), self.desktop_size())
        self.windowed_size = self.settings.size
        self.last_good = self.settings
        if not self.apply(self.settings, remember=False):
            log.warning("saved display settings failed; using the safe window")

    # ---------------------------------------------------------------- environment
    def display_index(self):
        """The monitor the window is on (0 before there is a window)."""
        try:
            return max(0, pygame.display.get_window_display_index()) if pygame.display.get_surface() else 0
        except (pygame.error, AttributeError):
            return 0

    def desktop_size(self):
        """The size of the monitor the window is on (a second monitor can be a different size from the first)."""
        try:
            sizes = pygame.display.get_desktop_sizes()
            i = self.display_index()
            size = sizes[i] if i < len(sizes) else sizes[0]
            if size[0] > 0 and size[1] > 0:
                return tuple(size)
        except (pygame.error, IndexError):
            pass
        return (1920, 1080)

    def presets(self):
        return size_presets(self.desktop_size(), self.windowed_size)

    # ---------------------------------------------------------------- persistence
    def _load(self):
        if not self.prefs_path:
            return None
        try:
            with open(self.prefs_path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            log.warning("could not read display settings %s (%s); using defaults", self.prefs_path, exc)
            return None

    def save(self):
        if not self.prefs_path:
            return False
        data = DisplaySettings(self.settings.mode, self.settings.scaling, tuple(self.windowed_size)).to_dict()
        tmp = self.prefs_path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.prefs_path) or ".", exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, self.prefs_path)
        except OSError as exc:
            log.warning("could not save display settings to %s: %s", self.prefs_path, exc)
            return False
        return True

    # ---------------------------------------------------------------- changing the window
    def apply(self, settings, remember=True):
        """Switch to `settings` (no restart). Returns True on success; on failure the safe 800x600 window is
        opened instead and False is returned."""
        settings = validate_settings(settings.to_dict() if isinstance(settings, DisplaySettings) else settings,
                                     self.desktop_size())
        previous = self.settings
        try:
            self._open_window(settings)
        except pygame.error as exc:
            self.last_error = str(exc)
            log.error("display change to %s failed (%s); falling back to a safe window", settings, exc)
            try:
                settings = DisplaySettings("windowed", settings.scaling, SAFE_SIZE)
                self._open_window(settings)
            except pygame.error as exc2:
                self.last_error = str(exc2)
                log.error("even the safe window failed: %s", exc2)
                self.settings = previous
                return False
            self.settings, self.windowed_size = settings, SAFE_SIZE
            return False
        if settings.mode == "windowed":
            self.windowed_size = tuple(settings.size)       # the PREFERENCE: what was asked for, not what a transition showed
            if tuple(self.window.get_size()) == self.windowed_size:
                self.pending_size = None                    # the OS gave exactly what was asked for
            else:
                self._expect_size(self.windowed_size)
        else:
            self.pending_size = None
        self.settings = settings
        if remember:
            self.last_good = settings
        self.mode_changes += 1
        return True

    def _open_window(self, s):
        flags, size = pygame.RESIZABLE, s.size
        if s.mode == "borderless":
            flags, size = pygame.NOFRAME, self.desktop_size()
        elif s.mode == "fullscreen":
            flags, size = pygame.FULLSCREEN, self.desktop_size()
        import warnings
        with warnings.catch_warnings(record=True) as caught:        # "the OS forcibly resized the window"
            warnings.simplefilter("always")
            self.window = pygame.display.set_mode(size, flags)
        for w in caught:
            log.info("display: %s", str(w.message).replace("\n", " "))
        if self.caption:
            pygame.display.set_caption(self.caption)
        if s.mode == "borderless":
            try:
                pygame.display.set_window_position((0, 0))
            except (pygame.error, AttributeError):
                pass
        self._set_min_size()
        self.minimized = False
        self.window_size = (0, 0)
        self._relayout(self.window.get_size(), s.scaling)

    def _set_min_size(self):
        try:
            import warnings
            from pygame._sdl2.video import Window
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                Window.from_display_module().minimum_size = MIN_WINDOW
        except Exception:               # noqa: BLE001 - optional: not every platform / driver has it
            pass

    def _relayout(self, window_size, scaling=None):
        layout = compute_layout(window_size, scaling or self.settings.scaling)
        if layout.screen_size != self.screen.get_size():
            self.screen = pygame.Surface(layout.screen_size)            # a fresh surface: nothing stale survives
            self.rebuilds += 1
        self.layout, self.window_size = layout, tuple(window_size)

    def _expect_size(self, size):
        """We asked for a windowed `size`. Some compositors (WSLg's) keep the old full-screen size when a window
        is re-created, or report it for a moment: remember what we want and re-request it until it shows."""
        self.pending_size, self.pending_tries = tuple(size), 0
        self.pending_until = time.monotonic() + 2.0

    def _request_size(self, size):
        try:
            import warnings
            from pygame._sdl2.video import Window
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                Window.from_display_module().size = tuple(size)
            return True
        except Exception:               # noqa: BLE001 - optional API
            return False

    def tick(self):
        """Once a frame: settle a requested windowed size. Gives up quietly after a couple of seconds - then the
        window simply keeps the size the OS insists on, and the preference is left as the player chose it."""
        if self.pending_size is None:
            return
        actual = tuple(self.window_size)
        if actual == self.pending_size or self.settings.mode != "windowed" or time.monotonic() > self.pending_until:
            if actual != self.pending_size and self.settings.mode == "windowed":
                log.info("the OS kept a %sx%s window instead of the requested %sx%s",
                         *actual, *self.pending_size)
            self.pending_size = None
            return
        if self.pending_tries < 4 and time.monotonic() >= getattr(self, "_next_try", 0.0):
            self.pending_tries += 1
            self._next_try = time.monotonic() + 0.25
            self._request_size(self.pending_size)

    def toggle_fullscreen(self):
        """Alt+Enter / F11: windowed <-> borderless fullscreen (the chosen full-screen kind if one was picked)."""
        s = self.settings
        if s.mode == "windowed":
            target = DisplaySettings(self._fullscreen_kind(), s.scaling, tuple(self.windowed_size))
        else:
            target = DisplaySettings("windowed", s.scaling, tuple(self.windowed_size))
        ok = self.apply(target)
        self.save()
        return ok

    def _fullscreen_kind(self):
        return getattr(self, "preferred_fullscreen", "borderless")

    def set_scaling(self, scaling):
        if scaling in SCALINGS and scaling != self.settings.scaling:
            self.settings = DisplaySettings(self.settings.mode, scaling, self.settings.size)
            self._relayout(self.window_size, scaling)

    # ---------------------------------------------------------------- events
    def handle_event(self, event):
        """Window events. True when the event was a window-size/state event and has been dealt with."""
        t = event.type
        if t not in RESIZE_EVENTS:
            return False
        if t == getattr(pygame, "WINDOWMINIMIZED", -1):
            self.minimized = True
            return True
        if t == getattr(pygame, "WINDOWRESTORED", -2):
            self.minimized = False
        self.refresh()
        return True

    def refresh(self):
        """Re-read the window size and rebuild only if it really changed (one resize arrives as several events)."""
        surface = pygame.display.get_surface()
        if surface is None:
            return False
        size = surface.get_size()
        if size[0] <= 0 or size[1] <= 0:
            self.minimized = True                   # a zero-size report: keep what we have, draw nothing
            return False
        self.minimized = False
        self.window = surface
        if tuple(size) == tuple(self.window_size):
            return False
        self._relayout(size)
        if self.settings.mode == "windowed" and self.pending_size is None:      # a real drag of the window edge
            self.windowed_size = tuple(size)
            self.settings = DisplaySettings("windowed", self.settings.scaling, tuple(size))
        elif self.pending_size is not None and tuple(size) == self.pending_size:
            self.pending_size = None
        return True

    # ---------------------------------------------------------------- mouse
    def convert_mouse(self, event):
        """The event with its position in presentation-surface pixels, or None when it must be ignored (a press
        or wheel turn in a black bar). Releases and drags in a bar are clamped to the nearest edge; plain
        hovering over a bar moves the pointer off-screen so nothing stays highlighted."""
        t = event.type
        if t not in MOUSE_EVENTS:
            return event
        if t == pygame.MOUSEWHEEL:
            return event if window_to_screen(self.layout, pygame.mouse.get_pos()) is not None else None
        attrs = dict(event.dict)
        pos = window_to_screen(self.layout, event.pos)
        if pos is None:
            if t == pygame.MOUSEBUTTONDOWN:
                return None
            if t == pygame.MOUSEMOTION and not any(attrs.get("buttons", (0, 0, 0))):
                pos = (-1, -1)
            else:
                pos = clamp_to_screen(self.layout, event.pos)
        attrs["pos"] = pos
        if t == pygame.MOUSEMOTION and "rel" in attrs:
            attrs["rel"] = (int(attrs["rel"][0] / self.layout.factor), int(attrs["rel"][1] / self.layout.factor))
        return pygame.event.Event(t, attrs)

    # ---------------------------------------------------------------- presenting
    def present(self):
        """Put the presentation surface on the window and flip. Safe with a minimised or odd-sized window."""
        if self.minimized:
            return
        surface = pygame.display.get_surface()
        if surface is None:
            return
        if surface is not self.window or surface.get_size() != tuple(self.window_size):
            self.refresh()
            surface = self.window
        self.tick()
        if self.minimized or min(surface.get_size()) <= 0:
            return
        lay = self.layout
        try:
            if lay.bars:
                surface.fill((0, 0, 0))
            if lay.exact:
                surface.blit(self.screen, lay.rect.topleft)
            elif lay.factor < 1 or lay.scale >= FIT_SURFACE_MAX or lay.scaling == "fit":
                pygame.transform.smoothscale(self.screen, lay.rect.size, surface.subsurface(lay.rect))
            else:
                pygame.transform.scale(self.screen, lay.rect.size, surface.subsurface(lay.rect))
            pygame.display.flip()
        except (pygame.error, ValueError) as exc:
            self.last_error = str(exc)
            log.error("presenting failed: %s", exc)
