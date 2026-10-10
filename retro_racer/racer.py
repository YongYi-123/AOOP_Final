"""Computer racers and the field they race in.

    RacerCar    a DrivenCar (same CarSpec physics as the player) whose controls come from an AIDriver
    RaceField   owns the racers, the starting grid, live standings, finish order, racer collisions and
                the ItemManager. It is the "world" that items and AI drivers query.
"""
import random
import settings as S
from car import DrivenCar, draw_car_rear
from car_specs import CAR_CATALOG, pick_liveries
from ai import AIDriver, LANES
from difficulty import DEFAULT_DIFFICULTY
from vehicle_identity import RivalBadge
from items import ItemManager, SeekerShot, OilSlick, wrap


class RacerCar(DrivenCar):
    """A computer-controlled competitor. HAS-A AIDriver; everything physical comes from DrivenCar."""

    def __init__(self, spec, driver, name, start_progress, lane, length, livery=None):
        super().__init__(spec)
        self.driver, self.name, self.livery = driver, name, livery
        self.start_progress = start_progress
        self.race_number = 1
        self.x = lane
        self.z = start_progress % length

    def drive(self, dt, field):
        controls = self.driver.drive(self, field, dt)
        self.driver.maybe_use_item(self, field, dt)
        self.update(dt, field.road, **controls)

    def draw(self, surf, sx, sy, sw):
        width = sw * self.WIDTH
        draw_car_rear(surf, sx, sy, width, self.spec.style.key, lean=int(self.steer_visual * 8), livery=self.livery,
                      yaw=sum(getattr(e, "visual_yaw", 0.0) for e in self.effects)
                      if S.DRIVING_FX_INTENSITY > 0 else 0.0)
        RivalBadge.draw(surf,sx,sy,width,self.race_number)
        self.decorate(surf, sx, sy, width)


def grid_slot(k):
    """(track offset relative to the player's row, lane) for opponent k. Staggered rows:

            CPU   CPU        +1 row
              PLAYER         player's row
            CPU   CPU        -1 row
              CPU            -2 rows
    """
    rows = [(1, -0.5), (1, 0.5), (-1, -0.5), (-1, 0.5), (-2, 0.0)]
    if k < len(rows):
        row, lane = rows[k]
    else:
        row, lane = -3 - (k - len(rows)) // 2, (-0.5, 0.5)[k % 2]
    return row * S.GRID_ROW_GAP, lane


class RaceField:
    def __init__(self, road, traffic=None, laps=S.RACE_LAPS):
        self.road, self.traffic, self.laps = road, traffic, laps
        self.length = road.length
        self.rng = random.Random()
        self.items = ItemManager(road, self.rng)
        self.player = None
        self.racers = []
        self.entities = []
        self.finish_order = []
        self.events = []

    # ---- setup ------------------------------------------------------------------------------
    def clear(self):
        self.racers, self.entities, self.finish_order, self.events = [], [], [], []
        self.player = None
        self.items.clear()

    @property
    def active(self):
        return bool(self.racers)

    @property
    def total_progress(self):
        return self.laps * self.length

    def deploy(self, player, level=DEFAULT_DIFFICULTY):
        """Put the opponents on the starting grid (they stay parked until the manager starts updating)."""
        self.clear()
        self.player = player
        specs = list(CAR_CATALOG)
        self.rng.shuffle(specs)
        counts = {}
        liveries = pick_liveries(S.RACE_OPPONENTS, player.livery.primary, self.rng)   # six distinct paint jobs
        for k in range(S.RACE_OPPONENTS):
            spec = specs[k % len(specs)]
            counts[spec.name] = counts.get(spec.name, 0) + 1
            name = spec.name if counts[spec.name] == 1 else f"{spec.name} {counts[spec.name]}"
            offset, lane = grid_slot(k)
            driver = AIDriver(skill=self.rng.uniform(*level.skill), aggression=self.rng.uniform(*level.aggression),
                              line=lane if self.rng.random() < 0.7 else self.rng.choice(LANES),
                              reaction=self.rng.uniform(0.25, 0.5), rng=random.Random(self.rng.random()),
                              difficulty=level)
            self.racers.append(RacerCar(spec, driver, name, player.start_progress + offset, lane, self.length, liveries[k]))
        for number, racer in enumerate(self.racers, 1):
            racer.race_number = number
        self.entities = [player] + self.racers
        grid = [player.start_progress + grid_slot(k)[0] for k in range(S.RACE_OPPONENTS)] + [player.start_progress]
        self.items.deploy(avoid=grid)          # no pickups sitting on the starting grid

    # ---- per frame --------------------------------------------------------------------------
    def update(self, dt, player):
        if not self.racers:
            return
        for racer in self.racers:
            racer.drive(dt, self)
        self.items.update(dt, self)
        self._collide_entities()
        self._collide_traffic()
        self._record_finishes()

    def _collide_entities(self):
        ents = self.entities
        for i in range(len(ents)):
            for j in range(i + 1, len(ents)):
                a, b = ents[i], ents[j]
                dz = wrap(b.front_z - a.front_z, self.length)
                if abs(dz) < S.COLLISION_DEPTH and abs(a.x - b.x) < (a.WIDTH + b.WIDTH) / 2:
                    rear, front = (a, b) if dz > 0 else (b, a)
                    if rear.hit_cooldown > 0:
                        continue
                    landed = rear.collide(front)                 # the car behind pays, per its own CarSpec
                    front.nudge(1.0 if front.x >= rear.x else -1.0)
                    if rear is self.player:
                        self.events.append("crash" if landed else "shield")
                    elif front is self.player and landed:
                        self.events.append("bump")

    def _collide_traffic(self):
        if self.traffic is None:
            return
        for racer in self.racers:
            if racer.hit_cooldown > 0:
                continue
            for car in self.traffic.cars:
                if abs(wrap(car.z - racer.z, self.length)) < S.COLLISION_DEPTH and abs(car.x - racer.x) < (racer.WIDTH + car.WIDTH) / 2:
                    racer.collide(car)
                    break

    def _record_finishes(self):
        done = [e for e in self.entities if e not in self.finish_order and e.race_progress >= self.total_progress]
        self.finish_order += sorted(done, key=lambda e: -e.race_progress)

    # ---- standings --------------------------------------------------------------------------
    def ranking(self):
        """Everyone, best first: finishers in finishing order, then the rest by total race progress."""
        rest = sorted((e for e in self.entities if e not in self.finish_order), key=lambda e: -e.race_progress)
        return self.finish_order + rest

    def rank(self, car):
        order = self.ranking()
        return order.index(car) + 1 if car in order else 1

    def label(self, car):
        return "PLAYER" if car is self.player else car.name

    def snapshot(self):
        return [(i + 1, self.label(e)) for i, e in enumerate(self.ranking())]

    def snapshot_colors(self):
        """Body colour of each car in ranking order (for the results screen swatches)."""
        return [e.livery.primary if e.livery else (200, 200, 200) for e in self.ranking()]

    # ---- queries used by AI drivers and items -------------------------------------------------
    def obstacles_ahead(self, car, look):
        """[(distance ahead, object)] for every other car (racers, player, traffic) within `look`."""
        found = []
        others = self.entities + (self.traffic.cars if self.traffic is not None else [])
        for o in others:
            if o is car:
                continue
            d = wrap(o.front_z - car.front_z, self.length)
            if 0 < d < look:
                found.append((d, o))
        return found

    def catch_up(self, car):
        """Mild rubber band: racers far behind the player squeeze out a little extra speed, leaders ease off."""
        if self.player is None:
            return 0.0
        lead = self.player.race_progress - car.race_progress
        scale = car.driver.difficulty.catch_up if hasattr(car, "driver") else 1.0
        return max(-0.02, min(0.05, lead / 30000.0 * 0.04)) * scale

    def curve_ahead(self, car):
        return self.road.segment_at(car.front_z + 900).curve

    def opponents_near(self, user, radius):
        return [e for e in self.entities if e is not user and abs(wrap(e.front_z - user.front_z, self.length)) < radius]

    def opponent_behind(self, user, dist):
        best = None
        for e in self.entities:
            d = wrap(e.front_z - user.front_z, self.length)
            if e is not user and -dist < d < 0 and (best is None or d > best[0]):
                best = (d, e)
        return best[1] if best else None

    def next_ahead(self, user, maxdist):
        best = None
        for e in self.entities:
            d = wrap(e.front_z - user.front_z, self.length)
            if e is not user and 0 < d < maxdist and (best is None or d < best[0]):
                best = (d, e)
        return best[1] if best else None

    def threatened(self, user):
        for h in self.items.hazards:
            if isinstance(h, SeekerShot) and h.target is user:
                return True
            if isinstance(h, OilSlick) and 0 < wrap(h.z - user.front_z, self.length) < 3000 and abs(h.x - user.x) < 0.5:
                return True
        return False

    # ---- effects / events ---------------------------------------------------------------------
    def hostile(self, target, effect):
        """Apply a hostile effect to `target` (a shield may swallow it). Player gets a sound event either way."""
        landed = target.receive_hostile(effect)
        self.emit(target, getattr(effect, "sound", "hit") if landed else "shield")
        return landed

    REMOTE_EVENTS = ("item", "hit", "shield")      # AI item use is heard, quietly, only when it is close
    REMOTE_RANGE = 9000

    def emit(self, car, name):
        if car is self.player:
            self.events.append(name)
        elif self.player is not None and name in self.REMOTE_EVENTS \
                and abs(wrap(car.front_z - self.player.front_z, self.length)) < self.REMOTE_RANGE:
            self.events.append("remote_" + name)

    def pop_events(self):
        events, self.events = self.events, []
        return events

    def racer_positions(self):
        """Track positions of the racers (civilian traffic keeps away from them when it spawns)."""
        return [r.front_z for r in self.racers]

    def drawables(self):
        return self.racers + self.items.drawables() if self.racers else []
