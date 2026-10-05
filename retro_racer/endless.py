"""EndlessManager: drive until you crash too many times; traffic slowly gets busier."""
import settings as S
from modes import GameMode, BaseModeManager
from race import State


def fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


class EndlessManager(BaseModeManager):
    mode = GameMode.ENDLESS
    uses_markers = False
    again_text = "PRESS ENTER TO RESTART"

    def __init__(self):
        self.reset()

    def reset(self):
        self.elapsed = 0.0
        self.level = 1
        self.max_crashes = S.ENDLESS_MAX_CRASHES
        self.banner, self.banner_time = [], 0.0
        self.result = None

    @property
    def difficulty(self):
        """0.0 at the start, rising linearly to 1.0 after ENDLESS_RAMP_SECONDS."""
        return min(1.0, self.elapsed / S.ENDLESS_RAMP_SECONDS)

    @property
    def banner_alpha(self):
        return max(0.0, min(1.0, self.banner_time / S.BANNER_TIME))

    def update(self, dt, player):
        self.elapsed += dt
        self.banner_time = max(0.0, self.banner_time - dt)
        level = 1 + int(self.difficulty * (S.ENDLESS_LEVELS - 1))
        if level > self.level:
            self.level = level
            self.banner, self.banner_time = [f"LEVEL {level}", "TRAFFIC UP"], S.BANNER_TIME
        if player.collisions >= self.max_crashes:
            self.result = {"score": int(player.score), "distance_km": player.distance / S.SEGMENT_LENGTH / 100,
                           "collisions": player.collisions, "elapsed": self.elapsed, "level": self.level}
            return State.GAME_OVER
        return State.PLAYING

    def apply_difficulty(self, traffic, player):
        d = self.difficulty
        traffic.speed_scale = 1.0 - d * (1.0 - S.ENDLESS_MIN_SPEED_SCALE)
        traffic.set_count(S.TRAFFIC_COUNT + round(d * (S.ENDLESS_MAX_CARS - S.TRAFFIC_COUNT)), player)

    def summary(self, state, end_t):
        r = self.result
        score = int(r["score"] * min(1.0, end_t / 1.2))      # rolls up like an arcade counter
        return "ENDLESS RUN OVER", [("SCORE", f"{score:07d}"), ("DISTANCE", f"{r['distance_km']:.2f} KM"),
                                    ("TIME SURVIVED", fmt_time(r["elapsed"])), ("COLLISIONS", f"{r['collisions']:02d}")]
