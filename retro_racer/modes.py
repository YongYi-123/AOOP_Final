"""Game modes: the GameMode enum and the interface every mode manager (Race, Endless) implements."""
from enum import Enum
import settings as S


class GameMode(Enum):
    COMPETITIVE = "COMPETITIVE"
    ENDLESS = "ENDLESS"


class BaseModeManager:
    """What Game needs from a mode. Subclasses supply the rules; Game runs one shared loop."""
    mode = None
    uses_markers = False        # draw the start/finish line and checkpoint gates on the road?
    next_checkpoint = 0         # Game watches this to trigger checkpoint feedback
    banner = ()
    banner_time = 0.0
    banner_alpha = 0.0
    result = None
    again_text = "PRESS ENTER TO RACE AGAIN"
    traffic_count = S.TRAFFIC_COUNT      # civilian cars this mode starts with

    def reset(self):
        raise NotImplementedError

    def update(self, dt, player):
        """Advance one frame; return the State the game should be in (PLAYING / FINISHED / GAME_OVER)."""
        raise NotImplementedError

    def summary(self, state, end_t):
        """(title, [(label, value_text), ...]) for the end screen."""
        raise NotImplementedError

    def apply_difficulty(self, traffic, player):
        """Hook to scale traffic each frame (only Endless uses it)."""

    def on_tune(self, name, old, new):
        """Hook for live tuning changes."""

    # ---- racing hooks: only the competitive manager overrides these -----------------------
    has_items = False                    # does this mode hand out items (so SPACE means something)?
    has_ai_levels = False                # does this mode have selectable AI difficulty?

    def set_ai_level(self, level):
        """Choose the AI difficulty for the next setup()."""

    def mode_note(self):
        """Short subtle HUD note, e.g. 'AI HARD'."""
        return ""

    def setup(self, player):
        """Called right after a reset when a race/run is about to start (e.g. deploy the AI grid)."""

    def drawables(self):
        """Extra world objects for Road.draw (racers, item boxes, hazards)."""
        return []

    def use_item(self, user):
        return False

    def pop_events(self):
        """Sound / effect events raised this frame, e.g. "pickup", "crash"."""
        return []

    def position_of(self, player):
        """(position, field size) or None when the mode has no race positions."""
        return None

    def standings_lines(self, state):
        return []

    def standings_colors(self, state):
        return []
