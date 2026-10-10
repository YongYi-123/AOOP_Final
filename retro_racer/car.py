"""Cars: base Car, the player-controlled PlayerCar and AI-driven EnemyCar."""
import pygame
import settings as S
import assets
from car_specs import CAR_CATALOG, player_livery
from effects import ShieldBreakEffect


def draw_car_rear(surf, cx, y, width, variant, lean=0.0, livery=None, marker=False, yaw=0.0):
    """Blit a pixel-art rear-view car, `width` px wide, with its bottom-centre at (cx, y).
    `marker` adds the small player-only chevron above the roof."""
    w = int(width)
    if w < 2:
        return
    frame = (pygame.time.get_ticks() // 90) % 2           # alternates the tyre tread
    sprite = assets.car_sprite(variant, w, frame, livery)
    if abs(yaw) >= 0.5:
        sprite = pygame.transform.rotate(sprite, round(yaw))
    h = sprite.get_height()
    shadow_h = max(1, int(w * 0.09))
    pygame.draw.ellipse(surf, (0, 0, 0), (cx - w * 0.56, y - shadow_h, w * 1.12, shadow_h * 2.4))
    surf.blit(sprite, (cx - sprite.get_width() / 2 + lean, y - h))
    if marker:
        size = max(4, int(w * 0.075))
        tip = (cx + lean, y - h - 3)
        pts = ((tip[0] - size, tip[1] - size), (tip[0] + size, tip[1] - size), tip)
        pygame.draw.polygon(surf, (0, 0, 0), [(px + dx, py + dy) for px, py in pts for dx, dy in ((0, 0),)], 0)
        pygame.draw.polygon(surf, (60, 230, 255), pts)
        pygame.draw.polygon(surf, (0, 0, 0), pts, 1)


class Car:
    WIDTH = 0.2   # car width in road half-widths (matches the 150px player car on screen)

    def __init__(self, x=0.0, z=0.0):
        self.x = x          # lateral position: -1..1 is on the road
        self.z = z          # distance along the track (world units)
        self.speed = 0.0    # world units per second

    @property
    def max_speed(self):        # read live so tuning MAX_SPEED takes effect immediately
        return S.MAX_SPEED

    @property
    def front_z(self):
        """Track position of the car itself (PlayerCar overrides: its z is the camera behind it)."""
        return self.z

    @property
    def speed_percent(self):
        """Speed as a fraction of THIS car's own top speed."""
        return self.speed / self.max_speed

    @property
    def speed_ratio(self):
        """Speed relative to the baseline top speed in settings.py (what the physics and km/h use)."""
        return self.speed / S.MAX_SPEED


class EnemyCar(Car):
    def __init__(self, x, z, speed, color_index=0):
        super().__init__(x, z)
        self.speed = speed
        self.variant = color_index % assets.ENEMY_VARIANTS   # look only; behaviour is identical
        self.prev_dz = None     # last frame's depth offset from the player, for swept collision tests

    def update(self, dt, road_length):
        self.z = (self.z + self.speed * dt) % road_length

    def draw(self, surf, sx, sy, sw):
        """(sx, sy) = projected bottom-centre of the car's lane position; sw = projected road half-width in px."""
        draw_car_rear(surf, sx, sy, sw * self.WIDTH, self.variant)


class DrivenCar(Car):
    """A car with the full driving model: CarSpec physics, crashes, temporary effects and one item slot.

    PlayerCar and RacerCar both extend this, so the physics exists exactly once. Only the *source of the
    controls* differs (keyboard vs AIDriver).
    """
    HIT_COOLDOWN = 1.0      # seconds of collision immunity after a crash
    HIT_PUSH = 2.0          # baseline sideways push after a crash (road half-widths / s)
    start_progress = 0.0    # where on the track this car starts (grid slot)

    def __init__(self, spec=None):
        super().__init__()
        self.spec = spec or CAR_CATALOG.default
        self.distance = 0.0      # world units driven since the start
        self.steer_visual = 0.0  # -1..1, only for drawing
        self.collisions = 0
        self.hit_cooldown = 0.0
        self.push = 0.0
        self.livery = None       # CarLivery (paint only); None = the CarStyle's own colours
        self.item = None         # the held Item (one at a time)
        self.item_age = 0.0
        self.effects = []        # ActiveEffect objects

    # ---- derived values -----------------------------------------------------
    MOD_FLOOR = {"max_speed": 0.35, "acceleration": 0.2, "steering": 0.0}      # stacked penalties never go lower

    def mod(self, stat):
        """Product of every active effect's multiplier for `stat` (1.0 when there are none),
        never below a floor, so Spin + Slow + Slow can't crush a car to a standstill."""
        m = 1.0
        for effect in self.effects:
            m *= effect.multipliers.get(stat, 1.0)
        return max(m, self.MOD_FLOOR.get(stat, 0.0)) if m < 1.0 else m

    @property
    def max_speed(self):
        return S.MAX_SPEED * self.spec.max_speed * self.mod("max_speed")

    @property
    def WIDTH(self):            # hit box and sprite width both follow the spec
        return Car.WIDTH * self.spec.width

    @property
    def off_road(self):
        return abs(self.x) > 1.0

    @property
    def race_progress(self):
        """Total track distance from the start line; only ever increases (never wraps)."""
        return self.start_progress + self.distance

    @property
    def recently_hit(self):
        return self.hit_cooldown > 0

    # ---- effects ------------------------------------------------------------
    def has_effect(self, key):
        return any(e.key == key for e in self.effects)

    def has_hostile_effect(self):
        return any(e.hostile for e in self.effects)

    def add_effect(self, effect):
        for old in [e for e in self.effects if e.key == effect.key]:      # same kind: combine, don't duplicate
            effect.merge(old)
            old.expire(self)
            self.effects.remove(old)
        self.effects.append(effect)
        effect.begin(self)

    def _shield_absorbs(self):
        """True if a shield swallowed the incoming hit; the used-up shield is removed at once."""
        absorbed = any(e.absorbs_hostile(self) for e in list(self.effects))
        if absorbed:
            for used in [e for e in self.effects if e.expired]:
                used.expire(self)
                self.effects.remove(used)
            self.add_effect(ShieldBreakEffect())                    # visible pop, once per block
        return absorbed

    def receive_hostile(self, effect):
        """Apply a hostile effect unless a shield swallows it. Returns True if it landed."""
        if self._shield_absorbs():
            return False
        self.add_effect(effect)
        return True

    def _tick_effects(self, dt):
        self.item_age += dt
        for effect in self.effects:
            effect.update(dt, self)
        for effect in [e for e in self.effects if e.expired]:
            effect.expire(self)
            self.effects.remove(effect)

    # ---- collisions ---------------------------------------------------------
    def collide(self, other):
        """React to hitting `other`: lose speed and get shoved sideways, as the spec dictates.
        Returns False if a shield absorbed the crash."""
        spec = self.spec
        away = self.x - other.x
        direction = 1.0 if away > 0 or (away == 0 and self.x <= 0) else -1.0
        if self._shield_absorbs():
            self.hit_cooldown = self.HIT_COOLDOWN
            self.push = direction * 0.8
            return False
        self.collisions += 1
        self.hit_cooldown = self.HIT_COOLDOWN
        retained = min(0.95, (1.0 - S.COLLISION_SPEED_PENALTY) * spec.collision_retention)
        follow_cap = other.speed * S.COLLISION_FOLLOW_FACTOR * spec.collision_retention
        self.speed = min(self.speed * retained, follow_cap)
        self.push = direction * self.HIT_PUSH * spec.collision_push
        return True

    def nudge(self, direction):
        """Shoved sideways by a car that hit us from behind (no speed loss, no crash counted)."""
        self.push += direction * 0.9 * self.spec.collision_push

    # ---- physics ------------------------------------------------------------
    def update(self, dt, road, accelerate, brake, steer):
        """steer: -1 (left), 0, +1 (right)."""
        self._tick_effects(dt)
        # Speed
        if accelerate:
            self.speed += S.ACCEL * self.spec.acceleration * self.mod("acceleration") * dt
        elif brake:
            self.speed -= S.BRAKING * self.spec.braking * dt
        else:
            self.speed -= S.DECEL * dt
        if self.off_road and self.speed > S.OFFROAD_LIMIT:
            self.speed -= S.OFFROAD_DECEL * self.spec.offroad_penalty * dt
        self.speed = max(0.0, min(self.speed, self.max_speed))

        # Steering (needs speed), centrifugal push on curves, and crash shove
        sp = self.speed_ratio
        self.x += steer * S.STEER_RATE * self.spec.steering * self.mod("steering") * dt * sp
        curve = road.segment_at(self.front_z).curve
        self.x -= curve * (S.CENTRIFUGAL / self.spec.centrifugal_resistance) * S.STEER_RATE * dt * sp * sp
        self.x += self.push * dt
        self.push *= max(0.0, 1.0 - 6.0 * dt)
        self.x = max(-2.5, min(2.5, self.x))
        self.steer_visual += (steer - self.steer_visual) * min(1.0, dt * 10)
        self.hit_cooldown = max(0.0, self.hit_cooldown - dt)

        # Advance along the track
        step = self.speed * dt
        self.z = (self.z + step) % road.length
        self.distance += step

    def decorate(self, surf, cx, bottom, width):
        for effect in self.effects:
            effect.decorate(surf, cx, bottom, width)


class PlayerCar(DrivenCar):
    """The player's car: keyboard-driven, drawn at a fixed spot; its z is the camera behind the car."""
    start_progress = S.PLAYER_START_PROGRESS

    def __init__(self, spec=None):
        super().__init__(spec)
        self.score = 0.0

    @property
    def livery(self):
        return self._custom_livery or player_livery(self.spec)

    @livery.setter
    def livery(self, value):
        self._custom_livery = value

    @property
    def front_z(self):
        """Track position of the car itself; self.z is the camera behind it."""
        return self.z + S.CAMERA_HEIGHT * S.CAMERA_DEPTH

    def update(self, dt, road, accelerate, brake, steer):
        before = self.distance
        super().update(dt, road, accelerate, brake, steer)
        self.score += (self.distance - before) * (1.0 + self.speed_ratio) * 0.01

    def draw(self, surf, visual_offset=0.0, visual_yaw=0.0):
        bob = 2 if (pygame.time.get_ticks() // 60) % 2 and self.speed > 0 else 0
        width, bottom = 150 * self.spec.width, S.HEIGHT - 30 + bob
        center = S.WIDTH // 2 + visual_offset
        oil_yaw = sum(getattr(effect, "visual_yaw", 0.0) for effect in self.effects)
        visual_yaw += oil_yaw if S.DRIVING_FX_INTENSITY > 0 else 0.0
        draw_car_rear(surf, center, bottom, width, self.spec.style.key, lean=int(self.steer_visual * 8),
                      livery=self.livery, marker=True, yaw=visual_yaw)
        self.decorate(surf, center, bottom, width)
