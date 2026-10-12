"""A dedicated listener for the NEON VEND-O-MATIC's hidden input sequence.

For testers (this is deliberately not mentioned in any player-facing text):

    UP UP DOWN DOWN LEFT RIGHT LEFT RIGHT B A

Every key means exactly one thing, so the reading is predictable:

    scheme   directions            B        A
    SOLO     the arrow keys        B        A
    P2       the arrow keys        COMMA    PERIOD
    P1       W A S D (arrows are   Z        X
             P2's on the shared
             keyboard)

* SOLO ignores W A S D for the code: the A key is only ever the A button, never LEFT, so there is no
  double meaning. (A WASD key pressed mid-code is simply a wrong key and restarts the sequence.)
* P1 cannot use the real B / A keys without clashing with its own A = LEFT, so it uses Z and X.
* The listener is built by the vending screen and fed that screen's raw key events, so it cannot fire anywhere
  else. Another player's keys are never read.
* Only fresh presses count: key repeats and keys still held are ignored; a key must be released (KEYUP)
  before it can count again. It is event-driven, so frame rate does not matter.
* A wrong key restarts the sequence, but a key that begins the sequence still counts as its first step, so a
  mistake never locks the detector. Bare modifier keys (Shift, Ctrl, Alt, Caps Lock) are neutral.
"""
import pygame

SEQUENCE = ("UP", "UP", "DOWN", "DOWN", "LEFT", "RIGHT", "LEFT", "RIGHT", "B", "A")
_ARROWS = {pygame.K_UP: "UP", pygame.K_DOWN: "DOWN", pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT"}
_WASD = {pygame.K_w: "UP", pygame.K_s: "DOWN", pygame.K_a: "LEFT", pygame.K_d: "RIGHT"}
# scheme name -> (direction keys, B key, A key)
_MAPS = {"SOLO": (_ARROWS, pygame.K_b, pygame.K_a),
         "P2": (_ARROWS, pygame.K_COMMA, pygame.K_PERIOD),
         "P1": (_WASD, pygame.K_z, pygame.K_x)}
_NEUTRAL = frozenset((pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_LCTRL, pygame.K_RCTRL, pygame.K_LALT,
                      pygame.K_RALT, pygame.K_CAPSLOCK, pygame.K_NUMLOCK))


class SecretSequenceListener:
    def __init__(self, scheme, sequence=SEQUENCE):
        self.scheme = scheme
        self.sequence = tuple(sequence)
        self.directions, self.b_key, self.a_key = _MAPS.get(scheme.name, _MAPS["SOLO"])
        self.reset()

    # ------------------------------------------------------------ state
    def reset(self):
        """Forget progress and any key believed to be held (called when the screen closes)."""
        self._progress = 0
        self._recent = []
        self._down = set()

    @property
    def progress(self):
        """How many steps of the sequence are matched right now."""
        return self._progress

    def token_for(self, key):
        """The sequence step `key` stands for, or None. Each key has at most one meaning."""
        if key in self.directions:
            return self.directions[key]
        if key == self.b_key:
            return "B"
        if key == self.a_key:
            return "A"
        return None

    def is_secret_key(self, key):
        return self.token_for(key) is not None

    # ------------------------------------------------------------ input
    def feed(self, event):
        """Returns True exactly when this event completed the sequence."""
        if event.type == pygame.KEYUP:
            self._down.discard(event.key)
            return False
        if event.type == pygame.WINDOWFOCUSLOST:
            self._down.clear()
            return False
        if event.type != pygame.KEYDOWN:
            return False
        key = event.key
        if key in self._down or getattr(event, "repeat", 0):
            return False                                  # a held key / auto-repeat is not a new press
        self._down.add(key)
        if key in _NEUTRAL:
            return False
        token = self.token_for(key)
        if token is None:                                 # some other key: back to the start
            self._progress, self._recent = 0, []
            return False
        self._progress = self._advance(token)
        if self._progress == len(self.sequence):
            self._progress, self._recent = 0, []
            return True
        return False

    def _advance(self, token):
        """The new progress after `token`: the longest run of the sequence's start that the recent keys
        still spell (so UP UP UP DOWN DOWN ... recovers instead of locking up)."""
        recent = self._recent + [token]
        for start in range(len(recent)):
            tail = recent[start:]
            if tuple(tail) == self.sequence[:len(tail)]:
                self._recent = tail
                return len(tail)
        self._recent = []
        return 0
