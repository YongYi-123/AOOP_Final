"""Helpers that play TRIAL 01 the way a person does: real key events fed to the real Game, one frame at a time.

Used by test_golden_age.py (the automatic tests) and by the screenshot / playthrough run, so "the room can be finished"
is proved with the keyboard, not by calling the scene's methods. Walking is real too: a breadth-first search over the
room's own collision boxes gives a route, and the driver holds the arrow keys along it.
"""
from collections import deque

import pygame

import golden_age as G
import golden_age_art as A
import golden_age_ui as UI

DT = 1 / 60
K = pygame


def key_down(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def key_up(k):
    return pygame.event.Event(pygame.KEYUP, key=k, mod=0)


class Driver:
    """Drives a Game that has the arcade floor on screen. `shot(name)` (optional) is called to save screenshots."""

    def __init__(self, game, shot=None):
        self.game = game
        self.shot = shot or (lambda name: None)
        self.sounds = []                        # (game time, effect) of every sound the game was asked to play
        self.clock = 0.0
        audio = game.audio
        real = audio.play

        def spy(name, volume=1.0):
            self.sounds.append((round(self.clock, 4), name))
            return real(name, volume)
        audio.play = spy

    # ------------------------------------------------------------ frames and keys
    def frames(self, n, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)
            self.clock += DT

    def seconds(self, s):
        self.frames(int(round(s / DT)))

    def tap(self, k, after=2):
        self.frames(1, [key_down(k)])
        self.frames(1, [key_up(k)])
        if after > 2:
            self.frames(after - 2)

    def type_word(self, word):
        for ch in word.lower():
            self.tap(getattr(K, f"K_{ch}"))

    @property
    def scene(self):
        return self.game.scenes.current

    # ------------------------------------------------------------ the way in
    def enter_trial(self, trial_key=K.K_e):
        """From the open Legacy Terminal, choose TRIAL 01 (the first row) with the use key."""
        term = self.scene
        assert term.index == 0
        self.tap(trial_key)
        self.frames(60)
        return self.scene

    # ------------------------------------------------------------ the dialogue box
    def talk_through(self, limit=40):
        """Press E until the story's dialogue box is gone. Returns how many presses it took."""
        presses = 0
        while self.scene.dialogue is not None and presses < limit:
            self.seconds(1.2)                   # let the line type itself out
            if self.scene.dialogue is None:
                break
            self.tap(K.K_e)
            presses += 1
        self.frames(10)
        return presses

    # ------------------------------------------------------------ walking
    def _clear(self, scene, x, y, margin=2):
        """Could the feet stand at (x, y) with `margin` pixels to spare (the arrow keys overshoot a node by a pixel or so)?"""
        feet = pygame.Rect(int(x) - 5, int(y) - 5, 10, 5).inflate(2 * margin, 2 * margin)
        return feet.collidelist(scene.solids) == -1

    def route(self, scene, goal):
        """A list of (dx, dy) 4-pixel steps from the player to a spot where E would use `goal` (a spot key)."""
        av = scene.avatar
        start = (av.x, av.y)                    # (floats: the nodes are exactly where the arrow keys will put the feet)
        seen = {start: None}
        todo = deque([start])
        while todo:
            cur = todo.popleft()
            hit = scene.spot_at(*cur)
            if hit is not None and hit.key == goal and all(
                    getattr(scene.spot_at(cur[0] + dx, cur[1] + dy), "key", None) == goal for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2))):
                path = []
                while seen[cur] is not None:
                    prev = seen[cur]
                    path.append((cur[0] - prev[0], cur[1] - prev[1]))
                    cur = prev
                return path[::-1]
            for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4)):
                nxt = (cur[0] + dx, cur[1] + dy)
                if nxt not in seen and 0 <= nxt[0] < 400 and 0 <= nxt[1] < 300 and self._clear(scene, *nxt):
                    seen[nxt] = cur
                    todo.append(nxt)
        return None

    def walk_to(self, spot_key, limit=1500):
        """Hold the arrow keys along a real route until the player stands where `spot_key` can be used."""
        scene = self.scene
        steps = self.route(scene, spot_key)
        assert steps is not None, f"no way to reach {spot_key}"
        av = scene.avatar
        used = 0
        tx, ty = av.x, av.y
        held = None
        for dx, dy in steps:
            tx, ty = tx + dx, ty + dy
            key = {(1, 0): K.K_RIGHT, (-1, 0): K.K_LEFT, (0, 1): K.K_DOWN, (0, -1): K.K_UP}[((dx > 1) - (dx < -1), (dy > 1) - (dy < -1))]
            if held != key:
                if held is not None:
                    self.frames(1, [key_up(held)])
                self.frames(1, [key_down(key)])
                held = key
            while ((dx > 0 and av.x < tx - 0.01) or (dx < 0 and av.x > tx + 0.01) or (dy > 0 and av.y < ty - 0.01)
                   or (dy < 0 and av.y > ty + 0.01)) and used < limit:
                self.frames(1)
                used += 1
        if held is not None:
            self.frames(1, [key_up(held)])
        self.frames(8)
        near = scene.nearby
        assert near is not None and near.key == spot_key, f"stopped at {(av.x, av.y)} near {near and near.key}, wanted {spot_key}"
        return used

    def use(self, spot_key):
        """Walk there and press E."""
        self.walk_to(spot_key)
        self.tap(K.K_e)
        self.frames(6)

    # ------------------------------------------------------------ the fuse board
    def solve_circuit(self):
        panel = self.scene.panel
        assert isinstance(panel, UI.CircuitPanel)
        circuit = panel.circuit
        goal = circuit.solution()
        for (r, c) in sorted(goal):
            need = (goal[(r, c)] - circuit.rots[(r, c)]) % 4
            if need == 0 or (r, c) not in G.ROUTE:
                continue
            self.move_cursor(panel, r, c)
            for _ in range(need):
                self.tap(K.K_e)
        return circuit

    def move_cursor(self, panel, r, c):
        while panel.cursor[0] != r:
            self.tap(K.K_DOWN if panel.cursor[0] < r else K.K_UP)
        while panel.cursor[1] != c:
            self.tap(K.K_RIGHT if panel.cursor[1] < c else K.K_LEFT)

    # ------------------------------------------------------------ whole stages, played with the keyboard
    def watch_intro(self):
        """Let the opening play and press E through all of it."""
        self.seconds(1.0)
        return self.talk_through()

    def restore_power(self):
        self.use("power_box")
        self.solve_circuit()
        self.seconds(3.5)                       # the surge, the lights coming up, then POWER RESTORED
        self.talk_through()
        self.seconds(3.0)

    def read_drawer(self):
        self.use("drawer")
        self.tap(K.K_e)
        self.tap(K.K_ESCAPE)
        self.seconds(0.3)

    def listen_to_phone(self, times=1):
        self.use("phone")
        for _ in range(times):
            self.tap(K.K_e)
            self.seconds(G.morse_duration() + 0.6)
        self.tap(K.K_ESCAPE)
        self.seconds(0.3)

    def open_cabinet(self, code=G.ANSWER):
        self.use("cabinet")
        self.type_word(code)
        self.tap(K.K_RETURN)
        self.seconds(2.0)

    def read_note(self):
        """After the cabinet opens, the note is on screen: take it."""
        self.tap(K.K_e)
        self.seconds(3.0)

    def read_notebook(self):
        """Open the bookshelf, pick the plain notebook (the last book once the cabinet's note is read) and read it to the end."""
        self.use("bookshelf")
        assert isinstance(self.scene.panel, UI.BookshelfPanel)
        self.tap(K.K_UP)                                  # (from the top, UP wraps round to the last book)
        self.tap(K.K_e)
        panel = self.scene.panel
        assert isinstance(panel, UI.PagedPanel) and panel.tag == "notebook", panel
        for _ in range(len(panel.pages)):
            self.tap(K.K_e)
        self.seconds(0.5)

    def get_boot_disk(self):
        self.read_notebook()
        self.talk_through()                     # Miao's three lines, then the disk
        self.seconds(3.0)

    def play_breakout(self, real=False, limit=900.0):
        """Clear HAPPY BREAKOUT.EXE. The paddle follows the ball. real=True does it with arrow-key events frame by frame (slow);
        otherwise the same bot drives the game's rules directly, without drawing every frame, and the panel hears the result."""
        panel = self.scene.panel
        g = panel.game
        t = 0.0
        held = None
        while g.state != "clear" and t < limit:
            if g.state in ("ready", "over"):
                if real:
                    self.tap(K.K_SPACE)
                else:
                    g.launch()
            cx = g.paddle_x + 20
            tx = g.ball_x + 2
            want = 0 if abs(tx - cx) < 4 else (1 if tx > cx else -1)
            if real:
                key = {1: K.K_RIGHT, -1: K.K_LEFT, 0: None}[want]
                if key != held:
                    if held is not None:
                        self.frames(1, [key_up(held)])
                    if key is not None:
                        self.frames(1, [key_down(key)])
                    held = key
                self.frames(1)
            else:
                g.step(DT, want)
                panel._events(g.take_events())
            t += DT
        if held is not None:
            self.frames(1, [key_up(held)])
        self.frames(2)                                 # (the panel notices the clear on its next update)
        assert g.state == "clear", g.state
        return t

    def boot_computer(self):
        """Insert the disk, wait through the boot, clear HAPPY BREAKOUT, open LOCKED FILES, read them, press on to the end."""
        self.use("computer")
        self.tap(K.K_e)                         # INSERT BOOT DISK? YES
        self.seconds(4.7)
        assert self.scene.panel.stage == "desktop", self.scene.panel.stage
        self.tap(K.K_1)                         # [1] PLAY GAME
        self.play_breakout()
        self.seconds(0.5)
        self.tap(K.K_e)                         # GAME CLEAR > the desktop
        self.tap(K.K_3)                         # [3] LOCKED FILES
        self.seconds(4.6)
        self.tap(K.K_e)
        self.seconds(0.5)
        self.talk_through()
        self.seconds(1.0)

    def play_through(self, plushie=False):
        """The whole trial in the order of its objectives. Ends with the finish card on screen."""
        self.restore_power()
        self.read_drawer()
        self.listen_to_phone()
        self.open_cabinet()
        self.read_note()
        self.get_boot_disk()
        if plushie:
            self.use("plushie")
            self.talk_through()
        self.boot_computer()

    def finish_card(self, stay=False):
        """On the finish card: RETURN TO ARCADE (the first button) or STAY IN THE ROOM."""
        assert isinstance(self.scene.panel, UI.CompletePanel), self.scene.panel
        if stay:
            self.tap(K.K_RIGHT)
        self.tap(K.K_e)
        self.seconds(1.0)
