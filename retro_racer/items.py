"""Arcade items (original designs): polymorphic Item classes, pickup boxes, road hazards and the ItemManager.

Every item implements the same interface, so nothing in Game / RaceField switches on an item name:

    use(user, world)          do the effect (world = the RaceField)
    advice(user, world)       would an AI racer want to use it right now?
    draw_icon(surf, rect)     HUD icon
    base_weight / rank_bias   how likely it is to be handed out, and how much that leans toward trailing racers
"""
import math
import random
import pygame
import settings as S
from effects import SpeedBoostEffect, SlowEffect, ShieldEffect, SpinEffect
from assets import BLACK, WHITE, YELLOW, ORANGE, RED, CYAN, GREEN, GREY, NAVY


def wrap(d, length):
    """Signed track distance wrapped into [-length/2, length/2)."""
    return (d + length / 2) % length - length / 2


# ============================================================================== items
class Item:
    key = "item"
    name = "ITEM"
    color = WHITE
    base_weight = 1.0
    rank_bias = 0.0              # >0: more likely for trailing racers, <0: for leaders
    cooldown = 0.0               # seconds during which the same racer is unlikely to be handed this item again

    def use(self, user, world):
        raise NotImplementedError

    def advice(self, user, world):
        return True

    def draw_icon(self, surf, rect):
        pygame.draw.rect(surf, (8, 8, 28), rect)
        pygame.draw.rect(surf, self.color, rect, 3)
        self.draw_symbol(surf, rect.inflate(-14, -14))

    def draw_symbol(self, surf, r):
        raise NotImplementedError


class TurboItem(Item):
    key, name, color = "turbo", "TURBO", ORANGE
    base_weight, rank_bias, cooldown = 3.0, 0.8, 6.0

    def use(self, user, world):
        user.add_effect(SpeedBoostEffect())

    def advice(self, user, world):
        return not user.has_effect("boost") and (abs(world.curve_ahead(user)) < 2.0 or world.rank(user) > 1)

    def draw_symbol(self, surf, r):
        for k, col in enumerate((ORANGE, YELLOW)):
            y = r.bottom - 4 - k * r.h * 0.4
            pygame.draw.polygon(surf, col, ((r.left, y), (r.centerx, y - r.h * 0.4), (r.right, y), (r.right - r.w * 0.25, y), (r.centerx, y - r.h * 0.22), (r.left + r.w * 0.25, y)))


class ShieldItem(Item):
    key, name, color = "shield", "SHIELD", CYAN
    base_weight, rank_bias = 2.0, -0.5

    def use(self, user, world):
        user.add_effect(ShieldEffect())

    def advice(self, user, world):
        return not user.has_effect("shield") and (world.threatened(user) or user.item_age > 5.0)

    def draw_symbol(self, surf, r):
        pts = ((r.left, r.top), (r.right, r.top), (r.right, r.centery), (r.centerx, r.bottom), (r.left, r.centery))
        pygame.draw.polygon(surf, CYAN, pts)
        pygame.draw.polygon(surf, WHITE, pts, 2)


class OilItem(Item):
    key, name, color = "oil", "OIL", (150, 110, 200)
    base_weight, rank_bias = 2.0, -0.8

    def use(self, user, world):
        world.items.hazards.append(OilSlick(user, (user.front_z - 700) % world.length, user.x))

    def advice(self, user, world):
        behind = world.opponent_behind(user, 5000)          # someone reasonably behind, not right on the bumper
        return behind is not None and abs(wrap(behind.front_z - user.front_z, world.length)) > 600

    def draw_symbol(self, surf, r):
        pygame.draw.ellipse(surf, (30, 20, 50), r.inflate(0, -r.h * 0.3))
        pygame.draw.ellipse(surf, (170, 140, 220), pygame.Rect(r.x + r.w * 0.2, r.y + r.h * 0.22, r.w * 0.25, r.h * 0.18))


class PulseItem(Item):
    key, name, color = "pulse", "PULSE", (90, 160, 255)
    base_weight, rank_bias, cooldown = 2.0, 0.7, 20.0
    RADIUS = 6000

    def use(self, user, world):
        world.items.hazards.append(PulseRing(user))
        for other in world.opponents_near(user, self.RADIUS):
            world.hostile(other, SlowEffect(1.8, speed=0.68, grip=0.85))

    def advice(self, user, world):
        return bool(world.opponents_near(user, 4000))

    def draw_symbol(self, surf, r):
        for k, rad in enumerate((0.5, 0.33, 0.16)):
            pygame.draw.circle(surf, CYAN if k % 2 == 0 else WHITE, r.center, int(r.w * rad), 3)


class RepairItem(Item):
    key, name, color = "repair", "REPAIR", GREEN
    base_weight, rank_bias = 1.0, 0.0

    def use(self, user, world):
        user.effects = [e for e in user.effects if not e.hostile]      # clear slow / spin
        user.collisions = max(0, user.collisions - 1)                  # restore one durability unit
        user.hit_cooldown = 0.0

    def advice(self, user, world):
        return user.recently_hit or user.has_hostile_effect()

    def draw_symbol(self, surf, r):
        t = max(6, r.w // 3)
        pygame.draw.rect(surf, GREEN, (r.centerx - t // 2, r.top, t, r.h))
        pygame.draw.rect(surf, GREEN, (r.left, r.centery - t // 2, r.w, t))


class SeekerItem(Item):
    key, name, color = "seeker", "SEEKER", RED
    base_weight, rank_bias, cooldown = 2.0, 1.0, 25.0
    RANGE = 40000

    def use(self, user, world):
        target = world.next_ahead(user, self.RANGE)
        if target is not None:
            world.items.hazards.append(SeekerShot(user, target, world.length))

    def advice(self, user, world):
        return world.next_ahead(user, 30000) is not None

    def draw_symbol(self, surf, r):
        pygame.draw.circle(surf, RED, r.center, r.w // 2, 3)
        pygame.draw.line(surf, RED, (r.left - 2, r.centery), (r.right + 2, r.centery), 2)
        pygame.draw.line(surf, RED, (r.centerx, r.top - 2), (r.centerx, r.bottom + 2), 2)


ITEM_TYPES = [TurboItem, ShieldItem, OilItem, PulseItem, RepairItem, SeekerItem]


# ============================================================================== world objects
class WorldObject:
    """Anything drawn on the road with Road.draw(): needs z (track position), x, draw(surf, sx, sy, sw)."""
    z = 0.0
    x = 0.0
    speed = 0.0
    WIDTH = 0.2


class ItemBox(WorldObject):
    COLORS = (RED, ORANGE, YELLOW, GREEN, CYAN)

    def __init__(self, z, x, phase):
        self.z, self.x, self.phase = z, x, phase
        self.active = True
        self.timer = 0.0
        self.age = 0.0

    def update(self, dt):
        self.age += dt
        if not self.active:
            self.timer -= dt
            if self.timer <= 0:
                self.active = True

    def collect(self):
        self.active, self.timer = False, S.ITEM_RESPAWN

    def draw(self, surf, sx, sy, sw):
        if not self.active or sw < 3:
            return
        spin = abs(math.cos(self.age * 3 + self.phase))
        size = sw * 0.17
        w, h = max(2, size * (0.35 + 0.65 * spin)), max(2, size)
        y = sy - sw * 0.05 * (1 + math.sin(self.age * 4 + self.phase)) - h
        col = self.COLORS[int(self.age * 6 + self.phase) % len(self.COLORS)]
        pygame.draw.rect(surf, WHITE, (sx - w / 2 - 2, y - 2, w + 4, h + 4))
        pygame.draw.rect(surf, col, (sx - w / 2, y, w, h))
        pygame.draw.polygon(surf, WHITE, ((sx, y + h * 0.2), (sx + w * 0.22, y + h * 0.5), (sx, y + h * 0.8), (sx - w * 0.22, y + h * 0.5)))


class Hazard(WorldObject):
    """A thing on the road that acts on cars. update() returns False when it should vanish."""
    lifetime = 10.0

    def __init__(self, owner, z, x):
        self.owner, self.z, self.x = owner, z, x
        self.age = 0.0

    def update(self, dt, world):
        self.age += dt
        return self.age < self.lifetime

    def draw(self, surf, sx, sy, sw):
        pass


class OilSlick(Hazard):
    lifetime = 14.0
    DEPTH, HALF = 420.0, 0.26

    def __init__(self, owner, z, x):
        super().__init__(owner, z, x)
        self.touched = {}                      # car id -> time it last triggered, so one pass = one hit

    def update(self, dt, world):
        alive = super().update(dt, world)
        for car in world.entities:
            if car is self.owner and self.age < 1.0:
                continue                         # the dropper isn't hit by its own oil straight away
            if abs(wrap(car.front_z - self.z, world.length)) < self.DEPTH and abs(car.x - self.x) < self.HALF + car.WIDTH / 2:
                if self.age - self.touched.get(id(car), -9.0) > 1.5:
                    self.touched[id(car)] = self.age
                    world.hostile(car, SlowEffect(1.8, speed=0.55, grip=0.5))
        return alive

    def draw(self, surf, sx, sy, sw):
        w, h = max(3, sw * 0.5), max(2, sw * 0.09)
        pygame.draw.ellipse(surf, (14, 10, 24), (sx - w / 2, sy - h / 2, w, h))
        pygame.draw.ellipse(surf, (110, 80, 170), (sx - w * 0.25, sy - h * 0.35, w * 0.3, h * 0.35))


class PulseRing(Hazard):
    """Purely visual shock-wave around the user."""
    lifetime = 0.6

    def __init__(self, owner):
        super().__init__(owner, owner.front_z, owner.x)

    def update(self, dt, world):
        self.z, self.x = self.owner.front_z, self.owner.x
        return super().update(dt, world)

    def draw(self, surf, sx, sy, sw):
        r = int(sw * (0.2 + 1.1 * self.age / self.lifetime))
        if r > 2:
            pygame.draw.ellipse(surf, CYAN, (sx - r, sy - r * 0.35, 2 * r, r * 0.7), 3)


class SeekerShot(Hazard):
    """Homing shot: flies along the track toward its target, then spins it."""
    lifetime = 9.0

    def __init__(self, owner, target, length):
        super().__init__(owner, owner.front_z, owner.x)
        self.target, self.length = target, length

    def update(self, dt, world):
        alive = super().update(dt, world)
        gap = wrap(self.target.front_z - self.z, self.length)
        self.z = (self.z + max(9000.0, self.target.speed * 1.6 + 4000.0) * dt) % self.length
        self.x += (self.target.x - self.x) * min(1.0, 3.0 * dt)
        if gap < 400 and abs(self.target.x - self.x) < 0.35:
            world.hostile(self.target, SpinEffect())
            return False
        return alive

    def draw(self, surf, sx, sy, sw):
        r = max(2, int(sw * 0.07))
        y = sy - sw * 0.1
        pygame.draw.circle(surf, RED, (sx, y), r)
        pygame.draw.circle(surf, WHITE, (sx, y), max(1, r // 2))


# ============================================================================== manager
class ItemManager:
    """Pickup boxes, respawns, random item choice (with mild rubber-banding) and live hazards."""

    STREAK_PENALTY = 0.3         # weight multiplier for the same item twice in a row
    COOLDOWN_PENALTY = 0.25      # weight multiplier while an item's cooldown is running for that racer

    def __init__(self, road, rng):
        self.road, self.rng = road, rng
        self.boxes = []
        self.hazards = []
        self.clock = 0.0
        self.history = {}            # id(car) -> [(item key, time received)]

    def clear(self):
        self.boxes, self.hazards = [], []
        self.clock = 0.0
        self.history = {}

    def deploy(self, avoid=()):
        """Rows of three boxes spread around the lap, skipping any row near a start-grid position in `avoid`."""
        self.clear()
        n, length = S.ITEM_ROWS_PER_LAP, self.road.length
        for row in range(n):
            z = (row + 0.5) * length / n
            if any(abs(wrap(z - a, length)) < S.GRID_CLEAR_ZONE for a in avoid):
                continue
            for k, lane in enumerate((-0.55, 0.0, 0.55)):
                self.boxes.append(ItemBox(z, lane, phase=row * 1.3 + k))

    def drawables(self):
        return [b for b in self.boxes if b.active] + self.hazards

    def roll_item(self, rank_frac, car=None):
        """rank_frac 0 = leader ... 1 = last. Trailing racers lean toward Turbo/Pulse/Seeker, leaders toward Oil/Shield.
        Anti-streak (needs `car`): the same item twice in a row, or a strong item again inside its cooldown,
        is much less likely. Still random: nothing is ever impossible."""
        lean = S.ITEM_RUBBER_BAND * (2 * rank_frac - 1)
        past = self.history.get(id(car), []) if car is not None else []
        weights = []
        for t in ITEM_TYPES:
            w = max(0.1, t.base_weight * (1 + t.rank_bias * lean))
            if past and past[-1][0] == t.key:
                w *= self.STREAK_PENALTY
            if t.cooldown and any(k == t.key and self.clock - when < t.cooldown for k, when in past):
                w *= self.COOLDOWN_PENALTY
            weights.append(w)
        item = self.rng.choices(ITEM_TYPES, weights)[0]()
        if car is not None:
            self.history.setdefault(id(car), []).append((item.key, self.clock))
            del self.history[id(car)][:-6]
        return item

    def use(self, user, world):
        item, user.item = user.item, None
        if item is None:
            return False
        item.use(user, world)
        world.emit(user, "item")
        return True

    def update(self, dt, world):
        self.clock += dt
        for box in self.boxes:
            box.update(dt)
        self.hazards = [h for h in self.hazards if h.update(dt, world)]
        for car in world.entities:
            if car.item is not None:
                continue
            reach = 350.0 + car.speed * dt
            for box in self.boxes:
                if box.active and abs(wrap(car.front_z - box.z, world.length)) < reach and abs(car.x - box.x) < 0.28 + car.WIDTH / 2:
                    frac = (world.rank(car) - 1) / max(1, len(world.entities) - 1)
                    car.item, car.item_age = self.roll_item(frac, car), 0.0
                    box.collect()
                    world.emit(car, "pickup")
                    break
