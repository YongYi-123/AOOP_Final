"""Scene plumbing: BaseScene and the stack-based SceneManager with its
scanline-wipe transition. Kept separate from scenes.py so minigame modules
can subclass BaseScene without a circular import."""
import math

import pygame

from settings import Col, TRANSITION_TIME, VIEW_H


class BaseScene:
    # False: draw() gets the low-res pixel canvas, which is upscaled afterwards.
    # True:  draw() gets the full-size window surface (e.g. an embedded game
    #        that renders at 800x600 itself).
    full_resolution = False

    def __init__(self, game):
        self.game = game

    def on_enter(self):
        """Called when the scene is pushed onto the stack."""

    def on_exit(self):
        """Called when the scene is popped off the stack."""

    def on_resume(self):
        """Called when the scene above this one is popped."""

    def on_quit(self):
        """Called when the program closes while this scene is on the stack."""

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


class SceneManager:
    """Keeps a stack of scenes; only the top one receives input and updates.
    push/pop are wrapped in a quick arcade scanline wipe (close, swap, open)."""
    BAND = 6  # height of each wipe band, in canvas pixels

    def __init__(self):
        self.stack = []
        self.fade = 0.0
        self.fade_dir = 0
        self._pending = None

    @property
    def current(self):
        return self.stack[-1] if self.stack else None

    @property
    def transitioning(self):
        return self.fade_dir != 0

    def push(self, scene, fade=True):
        self._request(lambda: self._push(scene), fade)

    def pop(self, fade=True):
        self._request(self._pop, fade)

    def _request(self, action, fade):
        if not fade:
            action()
        elif self._pending is None:
            self._pending = action
            self.fade_dir = 1

    def _push(self, scene):
        self.stack.append(scene)
        scene.on_enter()

    def _pop(self):
        self.stack.pop().on_exit()
        if self.current:
            self.current.on_resume()

    def quit(self):
        """The program is closing: let every scene wrap up, top first. A
        pending push/pop is dropped (the wipe never finishes)."""
        self._pending = None
        self.fade_dir = 0
        for scene in reversed(self.stack):
            scene.on_quit()

    def handle_event(self, event):
        if self.current and not self.transitioning:
            self.current.handle_event(event)

    def update(self, dt):
        if self.fade_dir == 1:
            self.fade = min(1.0, self.fade + dt / TRANSITION_TIME)
            if self.fade >= 1.0:
                self._pending()
                self._pending = None
                self.fade_dir = -1
        elif self.fade_dir == -1:
            self.fade = max(0.0, self.fade - dt / TRANSITION_TIME)
            if self.fade <= 0.0:
                self.fade_dir = 0
        if self.current:
            self.current.update(dt)

    def draw(self, canvas, screen):
        """Draw the top scene into `screen` (via the upscaled pixel canvas
        unless the scene is full-resolution), then the transition on top."""
        scene = self.current
        if scene and scene.full_resolution:
            scene.draw(screen)
        else:
            if scene:
                scene.draw(canvas)
            pygame.transform.scale(canvas, screen.get_size(), screen)
        if self.fade > 0:
            self._draw_wipe(screen)

    def _draw_wipe(self, screen):
        # interleaved bands grow to cover the screen, with a neon leading edge
        px = screen.get_height() // VIEW_H
        band = self.BAND * px
        h = math.ceil(band * self.fade)
        w = screen.get_width()
        for y in range(0, screen.get_height(), band):
            screen.fill(Col.FADE, (0, y, w, h))
            if self.fade < 1.0:
                screen.fill(Col.MAGENTA if (y // band) % 2 else Col.CYAN, (0, y + h, w, px))
