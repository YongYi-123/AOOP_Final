"""MIAO MEOW, the arcade's friendly guide cat.

LOOK. She is built on exactly the same sprite pipeline as Mochi (cat_sprites.draw_cat: same body, head, ears, tail,
poses and 1px outline, so the same cute proportions) with her own colours and three extras:
  * a deep navy-black coat with soft-grey nose and light / dark steps so the face reads on a dark floor
  * the chosen small gold pixel crown, between the ear tips (painted into every frame, before the head leans,
    so it can never drift off the head or cover the eyes)
  * a coin-bell on the chest: dark gold until a player walks close, then it fades up to a soft warm gold.
    Only the coin (and the fur pixels right beside it) brightens; the cat and the crown never glow.
Frames are painted once and cached; a fade is just a different cached frame, so it costs nothing per frame.

LIFE. One MiaoBrain lives in the hub (she is one cat, not one per room). It is a small, predictable state machine:

    idle -> (look around | walk to another spot | leave through a door) -> idle ...
    walk follows a short path between hand-placed spots (a visibility graph: no spot-to-spot line crosses a solid)
    leave walks out of a doorway, spends a moment in transit, and arrives in the next room through its door
    greet / talk are short reactions; script is handed to the story (cutscene walks)
    away: while the player is in another room she is only a few timers (where she is, when she moves on)

She lives in HOME (the central room) and visits ARCADE FLOOR and PRIZE PLAZA now and then. A quest can pin her
to a spot (`anchor`) so a story NPC is never hard to find. She only ever stops for the player or a cat in her
way (never pushes), and she never stands inside a machine's prompt area.

Each room carries a MiaoMeow Station (the view): it draws her when she is there, and is the E-prompt "TALK".
Mochi is untouched: nothing here changes shopkeeper.py or cat_sprites.py.
"""
import heapq
import math
import random

import pygame

from cat_sprites import CatLook, draw_cat
from gfx import lerp_color, outlined
from settings import ENTRY_INSET, Col
from stations import Station

NAME = "MIAO MEOW"

# ------------------------------------------------------------------ colours
GOLD = (255, 214, 90)                                       # Mochi's iris colour
IRIS, PUPIL, SHINE, LID = GOLD, (34, 24, 50), (255, 255, 255), (60, 36, 40)    # Mochi's eye colours
SOFT_GREY = (176, 178, 206)                                 # nose and inner ears (Mochi's pink, softened)
FUR_HI, FUR_LO = (92, 98, 154), (36, 38, 72)                # light / dark steps on the black fur
LOOK = CatLook(fur=(58, 62, 104), shade=(40, 43, 80), belly=(158, 162, 206), lid=GOLD, nose=SOFT_GREY)

CROWN_GOLD, CROWN_LIGHT, CROWN_SHADE = (255, 214, 90), (255, 240, 168), (214, 156, 56)

COLLAR = (122, 100, 74)                                     # the thin string the coin hangs from
COIN_DIM = {"hl": (176, 138, 64), "main": (132, 100, 44), "edge": (88, 66, 36)}      # dark gold
COIN_LIT = {"hl": (255, 240, 168), "main": (255, 212, 98), "edge": (214, 156, 56)}   # soft warm gold
COIN_WASH = (255, 210, 100)                                 # the tint of the light on the fur beside the coin
COIN_AT = (4, 10)                                           # top-left pixel of the 2x2 coin (left-facing frame)
LEVELS = 6                                                  # brightness steps of the coin

SIZE = (20, 17)                                             # exactly Mochi's frame size
WALK_LEGS = (1, 0, 2, 0)                                    # the cats' own walk cycle
WALK_STEP = 0.14                                            # seconds per walk frame


# ------------------------------------------------------------------ sprites
_FRAMES = {}
_FLIPPED = {}


def _px(s, color, x, y, w=1, h=1):
    s.fill(color, (x, y, w, h))


def _eyes(s, hy, mode, gaze):
    """Mochi's eye painter: big 2x3 eyes. mode: open / sleepy. gaze: (pupil column, looking down)."""
    col, down = gaze
    top = hy + 2
    for x in (1, 5):
        if mode == "sleepy":
            _px(s, LID, x, top, 2, 1)
            _px(s, IRIS, x, top + 1, 2, 2)
            _px(s, PUPIL, x + col, top + 1 + down, 1, 1 + (not down))
            continue
        _px(s, IRIS, x, top, 2, 3)
        _px(s, PUPIL, x + col, top + down, 1, 2)
        _px(s, SHINE, x + 1 - col, top + down)


def _fur_layers(s):
    """Light and dark steps on the black fur, so the face and body stay readable on a dark floor."""
    for x, y in ((3, 3), (4, 3), (4, 4), (1, 2), (7, 3), (8, 5), (9, 5), (10, 6)):     # forehead, ear edges, back
        if s.get_at((x, y))[:3] == LOOK.fur:
            s.set_at((x, y), FUR_HI)
    for x, y in ((2, 8), (3, 8), (4, 8), (5, 8), (3, 7), (7, 8),                          # under the chin, cheek edge
                 (8, 12), (9, 12), (10, 12), (11, 12), (8, 13), (9, 13), (7, 12)):         # belly side
        if s.get_at((x, y))[:3] == LOOK.fur:
            s.set_at((x, y), FUR_LO)


def _crown(s):
    """The chosen crown: five pixels wide, three gold points, no gem. It lives on rows 0-3, between the ear
    tips, and never reaches the eyes (which start on row 4)."""
    g, li, sh = CROWN_GOLD, CROWN_LIGHT, CROWN_SHADE
    s.set_at((2, 1), li); s.set_at((4, 0), li); s.set_at((6, 1), g); s.set_at((4, 1), g)
    for x in range(2, 7):
        s.set_at((x, 2), g)
        s.set_at((x, 3), sh)
    s.set_at((4, 2), li)


def _coin(s, level):
    """The collar string and the 2x2 coin-bell, `level` (0..LEVELS) steps from dark gold to warm gold, plus a
    faint wash of the same warm light on the fur pixels right around it."""
    t = level / LEVELS
    for x in (4, 5, 6):
        if s.get_at((x, 9))[3]:
            s.set_at((x, 9), COLLAR)
    x, y = COIN_AT
    if level:
        for gx in range(x - 1, x + 3):
            for gy in range(y - 1, y + 3):
                if x <= gx < x + 2 and y <= gy < y + 2 or s.get_at((gx, gy))[3] == 0:
                    continue
                corner = gx in (x - 1, x + 2) and gy in (y - 1, y + 2)
                s.set_at((gx, gy), (*lerp_color(s.get_at((gx, gy))[:3], COIN_WASH, (0.12 if corner else 0.26) * t), 255))
    col = {k: lerp_color(COIN_DIM[k], COIN_LIT[k], t) for k in COIN_DIM}
    s.set_at((x, y), col["hl"]); s.set_at((x + 1, y), col["main"])
    s.set_at((x, y + 1), col["main"]); s.set_at((x + 1, y + 1), col["edge"])


def miao_frame(pose="sit", eyes="open", gaze=(0, 1), tail=0, ear=0, tilt=False, level=0, legs=0):
    """One left-facing, outlined 20x17 frame (Mochi's size).
    pose: sit (the approved look) or stand (the walk cycle; legs 0-2 pick the step).
    eyes: open, sleepy, surprised, closed, happy. ear: 0 still, 1 right ear flicked, 2 left ear flicked.
    level: coin brightness 0..LEVELS."""
    key = (pose, eyes, gaze, tail, ear, tilt, level, legs)
    frame = _FRAMES.get(key)
    if frame is not None:
        return frame
    hy = 2
    base = "happy" if eyes == "happy" else "closed"
    if pose == "sit":
        s = draw_cat(LOOK, "sit", tail, base)
    else:                                                   # the standing cat, one pixel down so its head matches the sitting head
        s = pygame.Surface((18, 15), pygame.SRCALPHA)
        s.blit(draw_cat(LOOK, "stand", tail, base, legs), (0, 1))
    if eyes in ("open", "sleepy", "surprised"):
        _eyes(s, hy, "sleepy" if eyes == "sleepy" else "open", gaze)
    if eyes == "surprised":
        _px(s, PUPIL, 1, hy + 5, 1, 1)                      # a little round 'o'
    if ear == 1:                                            # flick the right ear outward (as Mochi does)
        s.fill((0, 0, 0, 0), (7, hy - 1, 1, 1))
        _px(s, LOOK.fur, 8, hy, 1, 1)
    elif ear == 2:
        s.fill((0, 0, 0, 0), (1, hy - 1, 1, 1))
        _px(s, LOOK.fur, 0, hy, 1, 1)
    if ear == 0:
        _px(s, SOFT_GREY, 2, hy, 1, 1)                      # inner ear
    _fur_layers(s)
    _crown(s)                                               # before the lean: the crown travels with the head
    if tilt:                                                # the head leans: shift it down and across
        head = s.subsurface(pygame.Rect(0, 0, 9, 10)).copy()
        s.fill((0, 0, 0, 0), (0, 0, 9, 10))
        s.blit(head, (1, 1))
    _coin(s, level)                                         # the chest does not move with the head
    frame = _FRAMES[key] = outlined(s)
    return frame


def facing_frame(frame, side):
    """Frames face left; 'right' is the mirror image (cached per frame)."""
    if side == "left":
        return frame
    flipped = _FLIPPED.get(id(frame))
    if flipped is None:
        flipped = _FLIPPED[id(frame)] = pygame.transform.flip(frame, True, False)
    return flipped


_WASH = {}


def _wash(level):
    """A small soft additive glow for the coin (cached per level); drawn after the room lighting."""
    img = _WASH.get(level)
    if img is None:
        r = 7
        img = pygame.Surface((r * 2, r * 2))
        img.fill((0, 0, 0))
        t = level / LEVELS
        for y in range(r * 2):
            for x in range(r * 2):
                d = math.hypot(x + 0.5 - r, y + 0.5 - r) / r
                if d < 1:
                    k = (1 - d) ** 2 * 0.5 * t
                    img.set_at((x, y), tuple(int(c * k) for c in COIN_WASH))
        _WASH[level] = img
    return img


# ------------------------------------------------------------------ the map of where she goes
HOME, ARCADE, PLAZA = "home", "arcade_floor", "prize_plaza"
DOOR_Y = 226                                                # the middle of every doorway

# Hand-placed resting spots (her feet), per room. Each one is open floor, outside every machine's prompt area
# and outside the doorway zones (test_miao_meow checks all of it against the real rooms).
SPOTS = {
    HOME: {"hub": (186, 216), "couch": (176, 152), "nook": (70, 150), "corner": (300, 232), "bed": (128, 244)},
    ARCADE: {"corner": (130, 250), "centre": (210, 252), "right": (300, 240)},
    PLAZA: {"walkway": (230, 232), "left": (104, 230), "island": (222, 172)},   # (walkway clears the claw machine)
}
# door spot (just inside) and the point inside the doorway itself, per room and side
DOORS = {
    HOME: {"left": (ENTRY_INSET, DOOR_Y), "right": (400 - ENTRY_INSET, DOOR_Y)},
    ARCADE: {"right": (400 - ENTRY_INSET, DOOR_Y)},
    PLAZA: {"left": (ENTRY_INSET, DOOR_Y)},
}
THRESHOLD = {"left": (12, DOOR_Y), "right": (388, DOOR_Y)}
# (from room, to room) -> (door side to leave by, door side to arrive through)
LINKS = {(HOME, ARCADE): ("left", "right"), (ARCADE, HOME): ("right", "left"),
         (HOME, PLAZA): ("right", "left"), (PLAZA, HOME): ("left", "right")}
NEIGHBOURS = {HOME: (ARCADE, PLAZA), ARCADE: (HOME,), PLAZA: (HOME,)}


def next_room(here, goal):
    """The next room on the way from `here` to `goal` (everything goes through HOME)."""
    if here == goal:
        return here
    return goal if goal in NEIGHBOURS[here] else HOME


def foot_rect(x, y):
    return pygame.Rect(int(x) - 5, int(y) - 4, 10, 5)


def point_clear(x, y, solids, pad=1):
    return foot_rect(x, y).inflate(pad * 2, pad * 2).collidelist(solids) == -1


def segment_clear(a, b, solids, pad=1):
    dist = math.hypot(b[0] - a[0], b[1] - a[1])
    steps = max(1, int(dist / 3))
    return all(point_clear(a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps, solids, pad)
               for i in range(steps + 1))


def room_nodes(room_id):
    """name -> point for every waypoint of a room: the spots, the door spots and the doorway thresholds."""
    nodes = dict(SPOTS[room_id])
    for side, pos in DOORS.get(room_id, {}).items():
        nodes[f"door_{side}"] = pos
        nodes[f"out_{side}"] = THRESHOLD[side]
    return nodes


def find_path(start, goal, nodes, solids):
    """The shortest clear route start -> goal through `nodes` (a list of points): a list of points to walk to,
    or None. Straight when the way is open."""
    pts = [tuple(start)] + [tuple(p) for p in nodes] + [tuple(goal)]
    last = len(pts) - 1
    cache = {}

    def clear(i, j):
        key = (min(i, j), max(i, j))
        if key not in cache:
            cache[key] = segment_clear(pts[i], pts[j], solids)
        return cache[key]

    best, heap = {0: 0.0}, [(0.0, 0, None)]
    came = {}
    while heap:
        d, i, parent = heapq.heappop(heap)
        if i in came:
            continue
        came[i] = parent
        if i == last:
            path, k = [], i
            while k is not None:
                path.append(pts[k])
                k = came[k]
            return path[::-1][1:]
        for j in range(len(pts)):
            if j != i and j not in came and clear(i, j):
                nd = d + math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
                if nd < best.get(j, 1e18):
                    best[j] = nd
                    heapq.heappush(heap, (nd, j, i))
    return None


# ------------------------------------------------------------------ behaviour numbers
SPEED = 34.0                                                # pixels per second (the player walks 72)
LIGHT_ON_RANGE = 58                                         # a player this close (feet to her feet) lights the coin
LIGHT_OFF_RANGE = 76                                        # ... and must go this far away to dim it again
FADE_TIME = 0.45                                            # seconds for the coin to fade fully up or down
WATCH_RANGE = 110                                           # she turns her head towards a player this close
GREET_COOLDOWN = 8.0
REACTION_TIME = {"greet": 0.8}
MEOW_GAP = 2.5
IDLE_TIME = (3.5, 8.0)                                      # seconds she stands about before deciding something
LOOK_TIME = (1.8, 3.4)
STUCK_REPLAN = 2.0                                          # blocked this long by a player / cat: find another way
STUCK_GIVE_UP = 5.0                                         # ... this long: forget the walk
TRANSIT_TIME = (1.2, 2.4)                                   # out of sight between two rooms
AWAY_TIME = {HOME: (28.0, 55.0), ARCADE: (14.0, 30.0), PLAZA: (14.0, 30.0)}   # how long she stays before moving on
VISIT_CHANCE = 0.2                                          # per idle decision at HOME: go and visit another room
RETURN_CHANCE = 0.4                                         # per idle decision elsewhere: go back to HOME


class MiaoBrain:
    """Miao Meow's whole state, shared by every room. `players()` returns the avatars (for gaze, greeting and the
    coin light); `sound(name)` plays an effect (may be None). Rooms call update() on their own frame; a room she is
    not in only ever hears about her through is_in()."""

    def __init__(self, players=lambda: (), sound=None, rng=None):
        self.players = players
        self.sound = sound
        self.rng = rng or random.Random(21)
        self.room_id = HOME
        self.x, self.y = SPOTS[HOME]["hub"]
        self.side = "right"
        self.state, self.state_time, self.time = "idle", 0.0, 0.0
        self.idle_left = self.rng.uniform(2.0, 4.0)
        self.look_left = 0.0
        self.path = []
        self.moving = False
        self.leaving_to = None          # the room she is walking out to
        self.dest = None                # the room she is in transit to
        self.transit_left = 0.0
        self.away_left = self.rng.uniform(*AWAY_TIME[HOME])
        self.anchor = None              # (room_id, spot): the story wants her there
        self.scripted = False
        self._script_goal = None
        self.script_speed = None        # the story may walk her faster than she strolls
        self._nearest = (None, 1e9)
        self.stuck = 0.0
        self.watching = None
        self.near, self.welcomed = {}, {}
        self.lit, self.light = False, 0.0
        self.last_meow = -99.0
        self.talks = 0
        self.events = []                # (event, time): what reached her (tests, debugging)
        self.blink_until, self.next_blink = 0.0, self.rng.uniform(1.5, 3.0)
        self.ear_until, self.ear_side, self.next_ear = 0.0, 1, self.rng.uniform(3.0, 6.0)

    # ------------------------------------------------------------ facts
    @property
    def pos(self):
        return (self.x, self.y)

    @property
    def in_transit(self):
        return self.state == "transit"

    def is_in(self, room_id):
        """Is she standing in that room right now (not between rooms)?"""
        return self.room_id == room_id and self.state != "transit"

    @property
    def level(self):
        """The coin's brightness step, 0 (dark gold) .. LEVELS (soft warm gold)."""
        return int(round(self.light * LEVELS))

    def footprint(self):
        return foot_rect(self.x, self.y)

    # ------------------------------------------------------------ placing her
    def place(self, room_id, pos, side=None):
        """Put her somewhere (story, tests, a room that was never on screen). Cancels any walk."""
        self.room_id, self.x, self.y = room_id, float(pos[0]), float(pos[1])
        if side:
            self.side = side
        self._stop()
        self.state, self.state_time = "idle", 0.0
        self.idle_left = self.rng.uniform(*IDLE_TIME)

    def _stop(self):
        self.path, self.moving, self.leaving_to, self.dest, self.stuck = [], False, None, None, 0.0

    def script_walk(self, pos):
        """The story walks her to `pos` (it keeps her from wandering until release())."""
        self.scripted = True
        self.state, self.state_time = "script", 0.0
        self.path = []
        self._script_goal = tuple(pos)

    @property
    def arrived(self):
        """A scripted walk is finished (or she was never asked to walk)."""
        return self.scripted and not self.path and self.state == "script" and self._script_goal is None

    def release(self):
        """The story is done with her: she goes back to her own life."""
        self.scripted = False
        self._script_goal = None
        self.script_speed = None
        self.path = []
        self.state, self.state_time = "idle", 0.0
        self.idle_left = self.rng.uniform(1.0, 2.5)

    def on_room_enter(self, room):
        """The players have just arrived in `room`: make what they see consistent."""
        if self.room_id != room.room_id or self.state == "transit":
            return
        self.path, self.moving, self.leaving_to, self.stuck = [], False, None, 0.0
        if self.scripted:
            return
        self.state, self.state_time = "idle", 0.0
        self.idle_left = self.rng.uniform(1.0, 3.0)
        if not self._free_here(room, self.x, self.y):                # never appear inside a solid or on a player
            spot = self._nearest_free_spot(room)
            if spot:
                self.x, self.y = spot

    # ------------------------------------------------------------ geometry
    def _static_solids(self, room):
        return list(room.solids)

    def _dynamic_blockers(self, room):
        out = [p.feet.inflate(6, 4) for p in room.players]
        out += [c.feet.inflate(2, 2) for c in getattr(getattr(room, "cats", None), "cats", ())]
        return out

    def _free_here(self, room, x, y):
        rect = foot_rect(x, y)
        return point_clear(x, y, self._static_solids(room)) and rect.collidelist(self._dynamic_blockers(room)) == -1

    def _spot_ok(self, room, name):
        x, y = room_nodes(room.room_id)[name]
        return point_clear(x, y, self._static_solids(room), 2)

    def _nearest_free_spot(self, room):
        spots = [p for n, p in SPOTS[room.room_id].items() if self._free_here(room, *p)]
        return min(spots, key=lambda p: math.hypot(p[0] - self.x, p[1] - self.y), default=None)

    def _route(self, room, goal):
        """A clear path from where she is to `goal`, or None."""
        nodes = [p for p in room_nodes(room.room_id).values() if point_clear(*p, self._static_solids(room), 1)]
        return find_path((self.x, self.y), goal, nodes, self._static_solids(room))

    def _walk_to(self, room, goal, state="walk", keep_stuck=False):
        path = self._route(room, goal)
        if not path:
            return False
        self.path, self.state, self.state_time = path, state, 0.0
        if not keep_stuck:
            self.stuck = 0.0                                           # (a re-plan keeps counting how long she has been held up)
        return True

    # ------------------------------------------------------------ the frame loop
    def update(self, dt, room):
        """Advance her life by dt. `room` is the room on screen. Always safe to call: it works out for itself
        whether she is here or elsewhere."""
        self.time += dt
        self.state_time += dt
        self._update_light(dt, room)
        if self.room_id != room.room_id or self.state == "transit":
            self._away(dt, room)
            return
        self._notice_players(room)
        if self.state in REACTION_TIME and self.state_time >= REACTION_TIME[self.state]:
            self.state, self.state_time = "idle", 0.0
        handler = {"idle": self._do_idle, "look": self._do_look, "walk": self._do_walk, "leave": self._do_walk,
                   "script": self._do_script, "greet": lambda *_: None, "talk": lambda *_: None}[self.state]
        self.moving = False
        handler(dt, room)
        if self.state in ("idle", "look"):
            self._idle_life()

    # ---- the coin light
    def _update_light(self, dt, room):
        here = self.is_in(room.room_id)
        players = list(self.players()) if here else []
        best = min((math.hypot(p.x - self.x, p.y - self.y) for p in players), default=1e9)
        self.lit = (best <= LIGHT_OFF_RANGE) if self.lit else (best <= LIGHT_ON_RANGE)
        target = 1.0 if self.lit else 0.0
        step = dt / FADE_TIME
        self.light = min(target, self.light + step) if self.light < target else max(target, self.light - step)
        self._nearest = (min(players, key=lambda p: math.hypot(p.x - self.x, p.y - self.y), default=None), best)

    def _notice_players(self, room):
        nearest, best = self._nearest
        for p in self.players():
            d = math.hypot(p.x - self.x, p.y - self.y)
            key = id(p)
            if d <= LIGHT_ON_RANGE and key not in self.near:
                self.near[key] = p
                if self.time - self.welcomed.get(key, -99.0) >= GREET_COOLDOWN and self.state in ("idle", "look"):
                    self.welcomed[key] = self.time
                    self.notify("greet", p)
            elif d > LIGHT_OFF_RANGE:
                self.near.pop(key, None)
        self.watching = nearest if nearest is not None and best <= WATCH_RANGE else None
        if self.watching is not None and self.state in ("idle", "look", "greet", "talk"):
            self.side = "left" if self.watching.x < self.x else "right"

    # ---- states
    def _do_idle(self, dt, room):
        if self.scripted:                                          # the story has her: no wandering off
            return
        if self.anchor and self._enforce_anchor(room):
            return
        self.idle_left -= dt
        if self.idle_left <= 0:
            self._decide(room)

    def _do_look(self, dt, room):
        self.look_left -= dt
        if self.watching is None and int(self.look_left / 0.9) != int((self.look_left + dt) / 0.9):
            self.side = "left" if self.side == "right" else "right"      # turns her head from side to side
        if self.look_left <= 0:
            self.state, self.state_time = "idle", 0.0
            self.idle_left = self.rng.uniform(*IDLE_TIME)

    def _do_walk(self, dt, room):
        if self.scripted:
            return self._do_script(dt, room)
        if not self.path:
            return self._finish_walk(room)
        self._step(dt, room)
        if not self.path:
            self._finish_walk(room)

    def _do_script(self, dt, room):
        goal = self._script_goal
        if goal is None:
            if self.watching is not None:                              # arrived: she looks at the player
                self.side = "left" if self.watching.x < self.x else "right"
            return
        if not self.path:
            self.path = self._route(room, goal) or [goal]
        self._step(dt, room, force=True)
        if not self.path:
            self._script_goal = None

    def _step(self, dt, room, force=False):
        """Walk along the path. Stops (never pushes) for a player or a cat; asks for another route when the way is shut."""
        tx, ty = self.path[0]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        step = (self.script_speed if self.scripted and self.script_speed else SPEED) * dt
        if dist <= step:
            nx, ny = tx, ty
        else:
            nx, ny = self.x + dx / dist * step, self.y + dy / dist * step
        new, old = foot_rect(nx, ny), foot_rect(self.x, self.y)
        if not force and new.inflate(2, 2).collidelist(self._static_solids(room)) != -1:
            return self._replan(room)                                  # a decoration moved: another way
        blockers = self._dynamic_blockers(room)
        if new.collidelist(blockers) != -1 and old.collidelist(blockers) == -1:
            self.stuck += dt                                           # someone is in the way: wait
            if self.stuck > STUCK_GIVE_UP:
                self._stop()
                self.state, self.state_time, self.idle_left = "idle", 0.0, self.rng.uniform(*IDLE_TIME)
            elif self.stuck > STUCK_REPLAN:
                self._replan(room)
            return
        self.stuck = 0.0
        if abs(dx) > 0.4:
            self.side = "left" if dx < 0 else "right"
        self.x, self.y = nx, ny
        self.moving = True
        if dist <= step:
            self.path.pop(0)

    def _replan(self, room):
        goal = self.path[-1] if self.path else None
        self.path = []
        if goal is None or not self._walk_to(room, goal, self.state if self.state in ("leave", "script") else "walk",
                                             keep_stuck=True):
            self._stop()
            self.state, self.state_time, self.idle_left = "idle", 0.0, self.rng.uniform(*IDLE_TIME)

    def _finish_walk(self, room):
        if self.state == "leave" and self.leaving_to:
            dest = self.leaving_to
            self._stop()
            self.dest = dest
            self.state, self.state_time = "transit", 0.0
            self.transit_left = self.rng.uniform(*TRANSIT_TIME)
            return
        self.state, self.state_time = "idle", 0.0
        self.idle_left = self.rng.uniform(*IDLE_TIME)

    # ---- decisions
    def _enforce_anchor(self, room):
        """The story wants her at a spot: go there (even from another room) and stay."""
        a_room, a_spot = self.anchor
        if self.room_id != a_room:
            return self._head_for_room(room, a_room)
        goal = SPOTS[a_room][a_spot]
        if math.hypot(goal[0] - self.x, goal[1] - self.y) > 6 and self._walk_to(room, goal):
            return True
        return False

    def _decide(self, room):
        rng = self.rng
        if self.anchor:
            self._start_look()
            return
        roll = rng.random()
        if self.room_id == HOME and roll < VISIT_CHANCE:
            if self._head_for_room(room, rng.choice(NEIGHBOURS[HOME])):
                return
        elif self.room_id != HOME and roll < RETURN_CHANCE:
            if self._head_for_room(room, HOME):
                return
        if roll < 0.55:
            self._wander(room)
        else:
            self._start_look()

    def _start_look(self):
        self.state, self.state_time = "look", 0.0
        self.look_left = self.rng.uniform(*LOOK_TIME)
        if self.rng.random() < 0.5:
            self.ear_until, self.ear_side = self.time + 0.3, self.rng.choice((1, 2))

    def _wander(self, room):
        here = (self.x, self.y)
        spots = [p for n, p in SPOTS[room.room_id].items()
                 if math.hypot(p[0] - here[0], p[1] - here[1]) > 24 and self._free_here(room, *p)]
        self.rng.shuffle(spots)
        for goal in spots:
            if self._walk_to(room, goal):
                return
        self._start_look()

    def _head_for_room(self, room, goal_room):
        """Start walking out of this room towards `goal_room` (visible). Returns False if she cannot."""
        nxt = next_room(self.room_id, goal_room)
        if nxt == self.room_id:
            return False
        out_side, _ = LINKS[(self.room_id, nxt)]
        if self._walk_to(room, THRESHOLD[out_side], "leave"):
            self.leaving_to = nxt
            return True
        return False

    # ---- out of sight
    def _away(self, dt, room):
        """She is in another room (or between rooms): only timers. If she turns up here she walks in through a door."""
        self.moving = False
        if self.state == "transit":
            self.transit_left -= dt
            if self.transit_left <= 0:
                self._arrive(self.dest, room)
            return
        self.away_left -= dt
        if self.away_left > 0 or self.scripted:
            return
        goal = self.anchor[0] if self.anchor else (HOME if self.room_id != HOME else self.rng.choice(NEIGHBOURS[HOME]))
        if goal == self.room_id:
            self.away_left = self.rng.uniform(*AWAY_TIME[self.room_id])
            return
        self.dest = next_room(self.room_id, goal)
        self.state, self.state_time = "transit", 0.0
        self.transit_left = self.rng.uniform(*TRANSIT_TIME)

    def _arrive(self, dest, room):
        """She comes out of a door into `dest`."""
        came_from = self.room_id
        self._stop()
        self.room_id = dest
        self.away_left = self.rng.uniform(*AWAY_TIME[dest])
        self.state, self.state_time = "idle", 0.0
        self.idle_left = self.rng.uniform(*IDLE_TIME)
        if dest != room.room_id:                                     # nobody sees it: she is just somewhere there
            if self.anchor and self.anchor[0] == dest:
                self.x, self.y = SPOTS[dest][self.anchor[1]]
            else:
                self.x, self.y = self.rng.choice(list(SPOTS[dest].values()))
            return
        in_side = LINKS[(came_from, dest)][1]                        # visible: she walks in through the door
        self.x, self.y = THRESHOLD[in_side]
        self.side = "right" if in_side == "left" else "left"
        spot = SPOTS[dest][self.anchor[1]] if self.anchor and self.anchor[0] == dest else \
            self.rng.choice(list(SPOTS[dest].values()))
        if not self._walk_to(room, spot):
            self.place(dest, self._nearest_free_spot(room) or SPOTS[dest][next(iter(SPOTS[dest]))])

    # ------------------------------------------------------------ reactions
    def _meow(self):
        if self.sound is not None and self.time - self.last_meow >= MEOW_GAP:
            self.last_meow = self.time
            self.sound("meow")

    def notify(self, event, player=None):
        """'greet': a player walked up. 'talk': they pressed E (she stops, faces them and stays put until end_talk())."""
        if event not in ("greet", "talk"):
            raise ValueError(f"unknown Miao Meow event {event!r}")
        self.events.append((event, round(self.time, 3)))
        if player is not None:
            self.watching = player
            self.side = "left" if player.x < self.x else "right"
        self.path, self.moving = [], False
        self.state, self.state_time = event, 0.0
        if event == "talk":
            self._meow()                                              # (a greeting is a happy hop; she only speaks up when talked to)

    def end_talk(self):
        """The conversation is over: she goes back to what she was doing."""
        if self.state == "talk":
            self.state, self.state_time = "idle", 0.0
            self.idle_left = self.rng.uniform(1.5, 3.5)

    def _idle_life(self):
        t = self.time
        if t >= self.next_blink:
            self.blink_until = t + 0.14
            self.next_blink = t + self.rng.uniform(2.6, 4.6)
        if t >= self.next_ear:
            self.ear_until, self.ear_side = t + 0.3, self.rng.choice((1, 2))
            self.next_ear = t + self.rng.uniform(4.5, 8.0)

    # ------------------------------------------------------------ drawing
    def _gaze(self):
        who = self.watching
        if who is None:
            return (0, 1)
        dx, dy = who.x - self.x, who.y - self.y
        return (0 if abs(dx) > 22 else 1, 1 if dy > -4 else 0)

    def _tail(self):
        if self.state in ("greet", "talk"):
            return (0, 1, 2, 1)[int(self.time * 10) % 4]
        phase = self.time % 3.2                              # a lazy swish once per cycle
        return (0, 1, 2, 1)[int((phase - 2.2) / 0.25) % 4] if phase >= 2.2 else 0

    def frame(self):
        """The current (left-facing) frame for her state."""
        level = self.level
        if self.moving:                                      # the walk cycle: standing frames
            i = int(self.time / WALK_STEP) % 4
            return miao_frame("stand", "open", tail=(0, 1, 2, 1)[i], legs=WALK_LEGS[i], level=level)
        if self.state in ("greet", "talk"):
            return miao_frame(eyes="happy", tail=self._tail(), level=level)
        if self.time < self.blink_until:
            return miao_frame(eyes="closed", tail=self._tail(), level=level)
        ear = self.ear_side if self.time < self.ear_until else 0
        return miao_frame(eyes="open", gaze=self._gaze(), tail=self._tail(), ear=ear, level=level)

    def hop(self):
        """Vertical offset in pixels (negative = up) during a happy hop."""
        if self.state == "greet":
            return -int(abs(math.sin(self.state_time * math.pi / 0.4)) * 3)
        return 0

    def image(self):
        return facing_frame(self.frame(), self.side)

    def coin_center(self):
        """Screen position of the middle of the coin. The image is the 18x15 cat plus a 1px outline, so a core
        pixel (x, y) is at (x + 1, y + 1); facing right mirrors it."""
        w, h = SIZE
        left = int(self.x) - w // 2
        top = int(self.y) + self.hop() - h + 1
        cx = COIN_AT[0] + 2                                   # +1 outline, +1 to the middle of the 2px coin
        if self.side == "right":
            cx = w - cx
        return left + cx, top + COIN_AT[1] + 2


# ------------------------------------------------------------------ the view each room carries
class MiaoMeow(Station):
    """Miao Meow as one room sees her. A Station, so the room treats her like any other thing the player can walk
    up to and press E on ("TALK"); it draws her only while she is in that room, and a room she is not in has no
    prompt, no collision and no glow for her."""
    prompt_label = "TALK"
    solid = False                       # players are stopped by her through the story's blockers(); cats and walls ignore her

    def __init__(self, brain, room_id):
        super().__init__(miao_frame(), (0, 0), (0, 0, 10, 5), Col.YELLOW, Col.YELLOW, glow_strength=0.0, outline=False)
        self.brain = brain
        self.room_id = room_id
        self.sync()

    @property
    def present(self):
        return self.brain.is_in(self.room_id)

    def sync(self):
        """Follow the brain: where her feet, picture and prompt area are (none at all while she is elsewhere)."""
        b = self.brain
        if not self.present:
            self.footprint = pygame.Rect(-100, -100, 0, 0)
            self.rect = pygame.Rect(-100, -100, 0, 0)
            self.zone = pygame.Rect(-100, -100, 0, 0)
            return
        w, h = SIZE
        self.footprint = b.footprint()
        self.rect = pygame.Rect(int(b.x) - w // 2, int(b.y) - h + 1, w, h)
        self.zone = self.footprint.inflate(*self.REACH)

    def update(self, dt):
        super().update(dt)
        self.sync()

    def activate(self):
        """E pressed: the reaction starts when the press completes (interact)."""

    def interact(self, scene):
        """The player pressed E on her: the story opens a conversation."""
        scene.hub.story.talk_to_miao(scene, getattr(scene, "acting_player", None))

    def draw_under(self, surf):
        if self.present:
            surf.blit(self.shadow, (self.footprint.x - 2, self.footprint.bottom - 4))

    def draw(self, surf):
        if not self.present:
            return
        b = self.brain
        image = b.image()
        surf.blit(image, (int(b.x) - image.get_width() // 2, int(b.y) + b.hop() - image.get_height() + 1))

    def draw_glow(self, surf):
        """Over the room lighting: the coin's faint warm wash (and nothing else on her glows)."""
        if self.present and self.brain.level:
            img = _wash(self.brain.level)
            surf.blit(img, img.get_rect(center=self.brain.coin_center()), special_flags=pygame.BLEND_RGB_ADD)
