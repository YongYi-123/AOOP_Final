"""TrafficManager: keeps a handful of EnemyCars on the track around the player."""
import random
import settings as S
from car import EnemyCar


class TrafficManager:
    def __init__(self, road, seed=None):
        self.road = road
        self.rng = random.Random(seed)
        self.cars = []
        self.speed_scale = 1.0      # multiplier on newly spawned cars' speed (Endless lowers it)
        self.protected = lambda: []  # track positions of racers to keep clear of (set by the race manager)

    def reset(self, player, count=None):
        self.cars = []
        self.speed_scale = 1.0
        n = S.TRAFFIC_COUNT if count is None else count
        for i in range(n):
            # Spread the initial cars out ahead so the road is populated at the start.
            lo = S.TRAFFIC_SPAWN_MIN + i * (S.TRAFFIC_SPAWN_MAX - S.TRAFFIC_SPAWN_MIN) / n
            self.cars.append(self._spawn(player, lo, lo + 4000, i, self.cars))

    # ---- helpers ------------------------------------------------------------
    def relative_z(self, car, player):
        """Signed distance of car ahead (+) / behind (-) the player, wrapped around the loop."""
        length = self.road.length
        return (car.z - player.front_z + length / 2) % length - length / 2

    def _spawn(self, player, lo, hi, color_index, others=()):
        length = self.road.length
        for _ in range(30):
            dz = self.rng.uniform(lo, hi)
            x = self.rng.choice(S.TRAFFIC_LANES) + self.rng.uniform(-0.08, 0.08)
            spot = (player.front_z + dz) % length
            same_lane_ok = all(abs(self._wrap(o.z - spot, length)) > S.TRAFFIC_MIN_GAP or abs(o.x - x) > 0.4 for o in others)
            crowd = sum(abs(self._wrap(o.z - spot, length)) < S.TRAFFIC_ABREAST_ZONE for o in others)
            clear_of_racers = all(abs(self._wrap(rz - spot, length)) > S.TRAFFIC_CLEAR_OF_RACERS for rz in self.protected())
            if same_lane_ok and crowd < S.TRAFFIC_MAX_ABREAST and clear_of_racers:
                break
        speed = self.rng.uniform(S.TRAFFIC_MIN_SPEED, S.TRAFFIC_MAX_SPEED) * self.speed_scale
        return EnemyCar(x, (player.front_z + dz) % length, speed, color_index)

    @staticmethod
    def _wrap(d, length):
        return (d + length / 2) % length - length / 2

    def set_count(self, n, player):
        """Grow the traffic to n cars (never shrinks); new cars appear far ahead."""
        while len(self.cars) < n:
            self.cars.append(self._spawn(player, S.TRAFFIC_SPAWN_MAX - 12000, S.TRAFFIC_SPAWN_MAX,
                                         len(self.cars), self.cars))

    # ---- per frame ----------------------------------------------------------
    def update(self, dt, player):
        length = self.road.length
        for car in self.cars:
            car.update(dt, length)
        self._avoid_rear_ending()
        for i, car in enumerate(self.cars):
            dz = self.relative_z(car, player)
            if dz < -S.TRAFFIC_DESPAWN_BEHIND or dz > S.TRAFFIC_DESPAWN_AHEAD:
                # Recycle far ahead of the player, away from the other cars.
                others = self.cars[:i] + self.cars[i + 1:]
                self.cars[i] = self._spawn(player, S.TRAFFIC_SPAWN_MAX - 12000, S.TRAFFIC_SPAWN_MAX, i, others)

    def _avoid_rear_ending(self):
        """A car that catches up to a slower one in its lane matches its speed instead of driving through it."""
        length = self.road.length
        for a in self.cars:
            for b in self.cars:
                if a is b or abs(a.x - b.x) > 0.4:
                    continue
                gap = self._wrap(b.z - a.z, length)
                if 0 < gap < 1500 and a.speed > b.speed:
                    a.speed = b.speed

    def find_collision(self, player):
        """Return the EnemyCar the player is touching, or None.

        A hit needs (1) depth overlap: |dz| < COLLISION_DEPTH, or the car passed through the
        player's depth this frame (swept test, so fast closing speeds can't tunnel), and
        (2) horizontal overlap: lateral distance below half the two car widths' sum.
        The player's hit_cooldown prevents a crash from registering every frame.
        """
        hit = None
        for car in self.cars:
            dz = self.relative_z(car, player)
            prev, car.prev_dz = car.prev_dz, dz
            if player.hit_cooldown > 0 or hit:
                continue
            crossed = prev is not None and abs(prev) < S.TRAFFIC_DESPAWN_BEHIND and prev * dz < 0
            if (abs(dz) < S.COLLISION_DEPTH or crossed) and abs(car.x - player.x) < (car.WIDTH + player.WIDTH) / 2:
                hit = car
        return hit
