"""A transient hub-room easter egg: stay still and become a cat nap spot."""
import math
import heapq
from dataclasses import dataclass
from cat import CatNPC, CatState


@dataclass
class NapPlan:
    goal: tuple
    path: list
    delay: float
    stuck: float = 0.0


class IdleCatNap:
    WAIT = 30.0
    YIELD_TIME = 1.2

    def __init__(self, room):
        self.room = room
        self.enabled = getattr(room, 'room_id', None) in ('home', 'arcade_floor', 'prize_plaza')
        self.idle_time = 0.0
        self.last_player = None
        self.last_position = None
        self.plans = {}
        self.yielding = set()
        self.yield_left = 0.0
        self.active = False
        self.retry_left = 0.0

    def reset(self):
        if self.plans:
            self.yielding.update(self.plans)
            self.yield_left = self.YIELD_TIME
        for cat in self.plans:
            if cat.state in (CatState.WALK, CatState.SLEEP, CatState.SIT):
                if cat.state == CatState.WALK and not self.room.cats.is_free(cat.position):
                    continue  # Finish leaving a doorway before returning to the ordinary AI.
                cat.anchor = cat.position
                cat.set_state(CatState.SIT)
        self.plans.clear()
        self.active = False
        self.idle_time = 0.0
        self.retry_left = 0.0
        self.last_player = self.last_position = None

    def update(self, dt, colony, busy):
        dt = max(0.0, dt)
        if not self.enabled:return
        self.yield_left = max(0.0, self.yield_left-dt)
        if self.yield_left == 0:
            self.yielding.clear()
        player = colony.players[0] if len(colony.players) == 1 else None
        if player is None:
            self.reset()
            return
        story = getattr(getattr(self.room, 'hub', None), 'story', None)
        busy = busy or bool(story and story.locked) or getattr(self.room, 'edit_mode', False)
        position = (player.x, player.y)
        changed = self.last_player is not player or self.last_position is None or math.dist(position, self.last_position) > .001
        direction = getattr(player, 'direction', (0, 0))
        if busy or player.moving or direction != (0, 0) or getattr(player, 'action', None) is not None or changed:
            self.reset()
            self.last_player, self.last_position = player, position
            return
        self.idle_time += dt
        if not self.active and self.idle_time > self.WAIT:
            self.active = True
            colony.stop_following()
            self._gather(colony, player)
            self.retry_left = 2.0
        elif self.active:
            self.retry_left -= dt
            if self.retry_left <= 0:
                self._gather(colony, player)
                self.retry_left = 2.0

    def _route(self, colony, cat, goal, extra=()):
        # Use the resident cats' actual footprint, including narrow furniture gaps.
        from miao_meow import room_nodes
        solids = colony.room_solids + [p.feet for p in colony.players] + list(extra)
        nodes = list(room_nodes(self.room.room_id).values())
        nodes += [point for other in colony.cats for point in other.spots]
        for rect in solids:
            nodes += [(x, y) for x in (rect.left-6, rect.right+6)
                      for y in (rect.top-1, rect.bottom+5)]
        clear = lambda p: CatNPC.feet_at(*p).collidelist(solids) == -1
        points = [cat.position, goal] + list(dict.fromkeys(p for p in nodes if clear(p)))
        edges = {}

        def visible(i, j):
            key = tuple(sorted((i, j)))
            if key not in edges:
                a, b = points[i], points[j]
                steps = max(1, math.ceil(math.dist(a, b)))
                edges[key] = all(clear((a[0]+(b[0]-a[0])*n/steps,
                                        a[1]+(b[1]-a[1])*n/steps)) for n in range(steps+1))
            return edges[key]

        queue, best, parents = [(0, 0)], {0: 0}, {}
        while queue:
            distance, i = heapq.heappop(queue)
            if distance > best[i]:continue
            if i == 1:
                path = [goal]
                while i in parents:
                    i = parents[i]
                    if i: path.append(points[i])
                return path[::-1]
            for j in range(1, len(points)):
                cost = distance + math.dist(points[i], points[j])
                if cost < best.get(j, math.inf) and visible(i, j):
                    best[j], parents[j] = cost, i
                    heapq.heappush(queue, (cost, j))
        return None

    def _gather(self, colony, player):
        reserved = [CatNPC.feet_at(*plan.goal).inflate(5, 6) for plan in self.plans.values()]
        offsets = [(math.cos(i*math.tau/12)*radius, math.sin(i*math.tau/12)*radius*.65)
                   for radius in (20, 30, 40) for i in range(12)]
        for cat in colony.cats:
            if cat in self.plans or cat.state == CatState.PET:
                continue
            choices = [(round(player.x+dx), round(player.y+dy)) for dx,dy in offsets]
            choices.sort(key=lambda p: math.dist(p, (player.x, player.y)) + math.dist(p, cat.position)*.15)
            for goal in choices:
                feet = CatNPC.feet_at(*goal)
                if not colony.is_free(goal) or feet.colliderect(player.feet.inflate(4, 4)):
                    continue
                if feet.inflate(4, 4).collidelist(colony.keep_clear) != -1:
                    continue
                if feet.inflate(5, 6).collidelist(reserved) != -1:
                    continue
                path = self._route(colony, cat, goal)
                if path is None:
                    continue
                self.plans[cat] = NapPlan(goal, path, len(self.plans)*.55)
                reserved.append(feet.inflate(5, 6))
                cat.bubble.clear()
                cat.purr_in = None
                cat.set_state(CatState.SIT if colony.is_free(cat.position) else CatState.WALK)
                break

    def drives(self, cat):
        return cat in self.plans

    def step(self, cat, dt, colony):
        plan = self.plans[cat]
        if plan.delay > 0:
            plan.delay -= dt
            return
        if not plan.path:
            if cat.state != CatState.SLEEP:
                cat.set_state(CatState.SLEEP, math.inf)
            cat.face(colony.players[0])
            return
        target = plan.path[0]
        if cat.state != CatState.WALK or cat.target != target:
            cat.walk_to(target, min(cat.personality.speed, 28))
        before = cat.position
        others = [other.feet for other in colony.cats if other is not cat]
        cat._walk(dt, colony.cat_solids()+others)
        if math.dist(cat.position, target) < 2:
            plan.path.pop(0)
            plan.stuck = 0.0
        else:
            plan.stuck = plan.stuck+dt if math.dist(before, cat.position) < .1 else 0.0
            if plan.stuck > 1.5:
                path = self._route(colony, cat, plan.goal, others)
                if path is not None:
                    plan.path = path
                plan.stuck = 0.0

    def ignores_collision(self, cat):
        return cat in self.plans or cat in self.yielding
