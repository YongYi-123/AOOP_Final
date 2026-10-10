"""Oil-specific temporary control loss, independent of base driving physics."""
from effects import SlowEffect


class OilSpinEffect(SlowEffect):
    """Reuse oil's speed penalty and restore steering after one smooth revolution."""

    def __init__(self):
        super().__init__(1.8, speed=0.55, grip=0.0)

    def update(self, dt, car):
        super().update(dt, car)
        progress = min(1.0, self.elapsed / self.duration)
        recovery = max(0.0, (progress - 0.35) / 0.65)
        self.multipliers['steering'] = 0.5 * recovery * recovery * (3 - 2 * recovery)

    @property
    def visual_yaw(self):
        progress = min(1.0, max(0.0, self.elapsed / self.duration))
        return 360.0 * progress * progress * (3 - 2 * progress)
