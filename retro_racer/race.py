"""Race rules: game states, countdown timer, checkpoints, laps and the finish condition."""
from enum import Enum
import settings as S
from modes import GameMode, BaseModeManager
from racer import RaceField
from difficulty import DEFAULT_DIFFICULTY


class State(Enum):
    TITLE = "TITLE"
    START = "TITLE"           # alias: the title screen
    MODE_SELECT = "MODE_SELECT"
    TRACK_SELECT = "TRACK_SELECT"
    CAR_SELECT = "CAR_SELECT"
    COUNTDOWN = "COUNTDOWN"
    PLAYING = "PLAYING"
    FINISHED = "FINISHED"
    GAME_OVER = "GAME_OVER"


class RaceManager(BaseModeManager):
    mode = GameMode.COMPETITIVE
    uses_markers = True
    traffic_count = S.RACE_TRAFFIC_COUNT      # fewer civilians: the real opponents are the AI racers
    has_ai_levels = True
    has_items = True
    ai_level = DEFAULT_DIFFICULTY

    def __init__(self, road, traffic=None):
        self.road = road
        self.laps = S.RACE_LAPS
        self.field = RaceField(road, traffic, self.laps)   # AI racers, items, standings
        if traffic is not None:
            traffic.protected = self.field.racer_positions  # civilians never spawn on top of a racer pack
        self.checkpoints = sorted(road.checkpoint_z)     # track position of each checkpoint in a lap
        self.reset()

    def reset(self):
        self.time_left = S.START_TIME
        self.elapsed = 0.0
        self.lap = 1
        self.next_checkpoint = 0        # index into the lap-after-lap sequence of checkpoints
        self.banner = []                # message lines shown briefly on screen
        self.banner_time = 0.0
        self.result = None              # frozen stats once the race ends
        self.field.clear()              # racers, items, finish order

    # ---- progress -----------------------------------------------------------
    @staticmethod
    def progress(player):
        """Total track distance covered by the car itself; only ever increases (never wraps)."""
        return player.distance + S.CAMERA_HEIGHT * S.CAMERA_DEPTH

    def checkpoint_position(self, n):
        lap, i = divmod(n, len(self.checkpoints))
        return lap * self.road.length + self.checkpoints[i]

    @property
    def total_checkpoints(self):
        return self.laps * len(self.checkpoints)

    @property
    def banner_alpha(self):
        return max(0.0, min(1.0, self.banner_time / S.BANNER_TIME))

    def _show(self, *lines):
        self.banner, self.banner_time = list(lines), S.BANNER_TIME

    # ---- per frame ----------------------------------------------------------
    def update(self, dt, player):
        """Advance the race one frame. Returns the State the game should be in afterwards."""
        self.field.update(dt, player)       # AI racers, items, collisions, finish order
        self.banner_time = max(0.0, self.banner_time - dt)
        self.time_left -= dt
        self.elapsed += dt
        progress = self.progress(player)

        # Checkpoints: a monotonic pointer, so each one can fire exactly once.
        while self.next_checkpoint < self.total_checkpoints \
                and progress >= self.checkpoint_position(self.next_checkpoint):
            self.next_checkpoint += 1
            self.time_left += S.CHECKPOINT_BONUS
            self._show("CHECKPOINT!", f"+{S.CHECKPOINT_BONUS} SEC")

        # Laps: derived from monotonic progress, so wrapping z can never double-count.
        lap = min(self.laps, int(progress // self.road.length) + 1)
        if lap > self.lap:
            self.lap = lap
            self._show("FINAL LAP!" if lap == self.laps else f"LAP {lap}")

        if progress >= self.laps * self.road.length:
            return self._end(player, State.FINISHED)
        if self.time_left <= 0:
            self.time_left = 0.0
            return self._end(player, State.GAME_OVER)
        return State.PLAYING

    def _end(self, player, state):
        bonus = int(self.time_left * S.TIME_BONUS_SCORE) if state is State.FINISHED else 0
        self.result = {
            "score": int(player.score) + bonus,
            "time_bonus": bonus,
            "distance_km": player.distance / S.SEGMENT_LENGTH / 100,
            "collisions": player.collisions,
            "time_left": self.time_left,
            "elapsed": self.elapsed,
            "position": self.field.rank(player) if self.field.active else 1,
            "field_size": len(self.field.entities) or 1,
            "standings": self.field.snapshot() if self.field.active else [],
            "standings_colors": self.field.snapshot_colors() if self.field.active else [],
        }
        return state

    # ---- Game-facing hooks (shared interface with EndlessManager) -----------
    def summary(self, state, end_t):
        r = self.result
        score = int(r["score"] * min(1.0, end_t / 1.2))      # rolls up like an arcade counter
        place = [("POSITION", f"{r['position']} / {r['field_size']}")] if self.field_racing(r) else []
        if state is State.FINISHED:
            return "RACE COMPLETE", place + [("SCORE", f"{score:07d}"), ("TIME LEFT", f"{r['time_left']:4.1f} SEC"),
                                             ("COLLISIONS", f"{r['collisions']:02d}")]
        return "TIME UP", place + [("SCORE", f"{score:07d}"), ("DISTANCE", f"{r['distance_km']:.2f} KM"),
                                   ("COLLISIONS", f"{r['collisions']:02d}")]

    @staticmethod
    def field_racing(result):
        return bool(result.get("standings"))

    def standings_lines(self, state):
        return [f"{pos}. {label}" for pos, label in (self.result or {}).get("standings", [])]

    def standings_colors(self, state):
        return list((self.result or {}).get("standings_colors", []))

    # ---- racing hooks ---------------------------------------------------------
    def set_ai_level(self, level):
        self.ai_level = level

    def mode_note(self):
        return f"AI {self.ai_level.name}"

    def setup(self, player):
        self.field.deploy(player, self.ai_level)

    def drawables(self):
        return self.field.drawables()

    def use_item(self, user):
        return self.field.items.use(user, self.field) if self.field.active else False

    def pop_events(self):
        return self.field.pop_events()

    def position_of(self, player):
        return (self.field.rank(player), len(self.field.entities)) if self.field.active else None

    def on_tune(self, name, old, new):
        if name == "START_TIME":       # nudge the running clock so a tuned start time is felt immediately
            self.time_left = max(1.0, self.time_left + (new - old))
