"""End-to-end check of the main story, Chapter 01 -> Chapter 02, on a brand-new THROW-AWAY profile.

    python3 verify_main_story.py            (headless: SDL's dummy video and audio drivers, no window)

Everything happens in a temporary save folder that is deleted at the end; your real saves/ folder is never opened.
The game is driven ONLY through its own input: key events into Game.step(), one frame (1/60 s of game time) at a time,
so the screens, scene transitions, doorways, menus, minigames and saves are the real ones. What is automated:

  * a walking bot: plans a path on the room's real collision boxes and holds W/A/S/D to follow it, then presses E
  * minigame bots that press the game's own keys (NEON CAT MAZE, STARFALL ASSAULT, CAT VOLLEYBALL, RETRO RACER,
    HAPPY BREAKOUT.EXE in Trial 01 with real arrow-key events, the claw machine)
  * the Trial 01 puzzles are solved with golden_age_testing.Driver (it walks the room and presses keys the same way)
  * F5 (the game's own debug key: +10 Tokens) is used when the wallet runs dry, so the run is not limited by luck;
    every use is logged. Nothing else is injected: no story flags are set and no item is granted by hand.

Screenshots of the real frames go to review_screenshots/main_story/. A log of every step is printed.
"""
import collections
import json
import os
import shutil
import sys
import tempfile
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

import pygame  # noqa: E402
from game import Game  # noqa: E402

import claw_machine as cm  # noqa: E402
import forgotten_games as fg  # noqa: E402
import golden_age_testing as GT  # noqa: E402
import quests as Q  # noqa: E402
from capsule_ui import CapsuleScene  # noqa: E402
from cat_maze_scene import CatMazeScene  # noqa: E402
from claw_scene import ClawScene  # noqa: E402
from collection_ui import CollectionScene  # noqa: E402
from galaxy_defender_scene import GalaxyDefenderScene  # noqa: E402
from legacy_terminal import LegacyTerminalScene  # noqa: E402
from claw_lock import ClawLockScene  # noqa: E402
from maintenance_note import MaintenanceNoteScene  # noqa: E402
from mochi_chat import MochiChatScene  # noqa: E402
from pixel_volleyball_scene import PixelVolleyballScene  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402
from retro_racer_scene import RetroRacerScene  # noqa: E402
from room_scene import BaseRoomScene  # noqa: E402
from shop_ui import ShopScene  # noqa: E402
from vending_ui import VendingScene  # noqa: E402
from galaxy_defender.game import Screen as GS  # noqa: E402
from neon_cat_maze import corridor  # noqa: E402
from neon_cat_maze.game import Screen as MS  # noqa: E402
from pixel_volleyball.model import MatchState  # noqa: E402

DT = 1 / 60
K = pygame
OUT = os.path.join(os.path.dirname(HERE), "review_screenshots", "main_story")
TMP = tempfile.mkdtemp(prefix="main_story_")
SAVES = os.path.join(TMP, "saves")
os.makedirs(OUT, exist_ok=True)
for _f in os.listdir(OUT):
    os.remove(os.path.join(OUT, _f))

LOG = []
CHECKS = []         # (name, passed)
F5_USES = [0]
T0 = time.time()


def say(*a):
    msg = " ".join(str(x) for x in a)
    LOG.append(msg)
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


def check(name, ok):
    CHECKS.append((name, bool(ok)))
    say(("PASS " if ok else "FAIL ") + name)
    return ok


# ------------------------------------------------------------------ frames and keys
game = None
held = set()


def ev(t, k, u=""):
    return pygame.event.Event(t, key=k, mod=0, unicode=u, scancode=0)


def step(events=()):
    game.step(list(events), DT)


def frames(n, events=()):
    for i in range(n):
        step(events if i == 0 else ())


def seconds(s):
    frames(int(round(s / DT)))


def hold(keys):
    """Hold exactly `keys` from this frame on (KEYUP for the others)."""
    keys = set(keys)
    events = [ev(K.KEYUP, k) for k in held - keys] + [ev(K.KEYDOWN, k) for k in keys - held]
    held.clear()
    held.update(keys)
    return events


def release():
    if held:
        step(hold(()))


def tap(k, u="", after=1):
    release()
    step([ev(K.KEYDOWN, k, u)])
    step([ev(K.KEYUP, k)])
    if after > 1:
        frames(after - 1)


def type_text(text):
    for ch in text:
        tap(K.K_SPACE if ch == " " else getattr(K, "K_" + ch.lower()), ch)


def shot(name):
    pygame.image.save(game.canvas, os.path.join(OUT, name + ".png"))
    say("  screenshot", name)


def scene():
    return game.scenes.current


def room():
    s = scene()
    return s if isinstance(s, BaseRoomScene) else None


def story():
    return game.hub.story


def manager():
    return game.hub.story.manager


def profile():
    return game.session.primary.profile


def wait_for(cond, limit=20.0, what=""):
    for _ in range(int(limit / DT)):
        if cond():
            return True
        step()
    say(f"  (timed out waiting for {what})")
    return False


def need_tokens(n):
    """Top the wallet up with the game's own debug key (F5: +10 Tokens) while it is below `n`."""
    while profile().tokens < n:
        tap(K.K_F5, after=2)
        F5_USES[0] += 1
        say(f"  F5 debug: +10 tokens (now {profile().tokens})")


# ------------------------------------------------------------------ the hub: dialogue, pop-ups, walking
def read_dialogue(limit=80):
    """Press E through the story's dialogue box (the real one), a line at a time."""
    n = 0
    while story().dialogue is not None and n < limit:
        seconds(0.9)
        if story().dialogue is None:
            break
        tap(K.K_e, after=3)
        n += 1
    return n


def settle(max_s=12.0):
    """Let the hub get to a state where the player can walk: read dialogue, close pop-ups, wait for banners and wipes."""
    for _ in range(int(max_s / DT)):
        r = room()
        if story().dialogue is not None:
            read_dialogue()
            continue
        if r is not None and r.popup is not None:
            seconds(0.6)
            tap(K.K_e, after=20)
            if r.popup is not None:
                tap(K.K_ESCAPE, after=20)
            continue
        if game.scenes.transitioning or (r is not None and (story().locked or r.leaving)):
            step()
            continue
        if r is not None:
            return r
        step()
    return room()


DIRS = {(0, -4): K.K_w, (0, 4): K.K_s, (-4, 0): K.K_a, (4, 0): K.K_d}


def plan(r, goal_rect, start):
    p = r.players[0]
    solids = r.solids + r.cats.blockers(p) + story().blockers(r, p)
    fw, fh = p.FEET_W, p.FEET_H

    def free(x, y):
        feet = pygame.Rect(x - fw // 2 - 1, y - fh - 1, fw + 2, fh + 2)
        if feet.left < 0 or feet.right > 400 or feet.top < 0 or feet.bottom > 300:
            return False
        return not any(feet.colliderect(s) for s in solids)

    def goal(x, y):
        return pygame.Rect(x - fw // 2, y - fh, fw, fh).colliderect(goal_rect)

    sx, sy = start
    prev = {(sx, sy): None}
    q = collections.deque([(sx, sy)])
    end = None
    while q:
        node = q.popleft()
        if goal(*node):
            end = node
            break
        for d in DIRS:
            n = (node[0] + d[0], node[1] + d[1])
            if n in prev or not free(*n):
                continue
            prev[n] = node
            q.append(n)
    if end is None:
        return None
    path = []
    while end is not None:
        path.append(end)
        end = prev[end]
    return path[::-1]


def walk_to(goal_rect, limit=40.0, label=""):
    """Walk the player (W/A/S/D held) until their feet touch `goal_rect`. Dialogue on the way is read through."""
    frames_left = int(limit / DT)
    stuck, last = 0, None
    start_room = settle()
    while frames_left > 0:
        r = settle()
        if r is None or r is not start_room:              # through a doorway (or into a screen): the walk is over
            release()
            return r is not None
        p = r.players[0]
        if p.feet.colliderect(goal_rect):
            release()
            return True
        path = plan(r, goal_rect, (int(p.x), int(p.y)))
        if not path or len(path) < 2:
            # (standing a pixel or two off the grid, or a cat in the way: nudge and plan again)
            step(hold([K.K_s if p.y < 200 else K.K_w]))
            frames(4)
            frames_left -= 5
            continue
        for node in path[1:8]:
            for _ in range(30):
                frames_left -= 1
                if story().dialogue is not None or room() is not r or r.popup is not None:
                    break
                dx, dy = node[0] - p.x, node[1] - p.y
                if abs(dx) < 1.5 and abs(dy) < 1.5:
                    break
                k = (K.K_d if dx > 0 else K.K_a) if abs(dx) >= abs(dy) else (K.K_s if dy > 0 else K.K_w)
                step(hold([k]))
                if p.feet.colliderect(goal_rect):
                    break
            if p.feet.colliderect(goal_rect) or room() is not r:
                break
        pos = (int(p.x), int(p.y))
        stuck = stuck + 1 if pos == last else 0
        last = pos
        if stuck > 6:
            say(f"  (walk to {label}: stuck at {pos}, nudging)")
            step(hold([K.K_s]))
            frames(10)
            stuck = 0
    release()
    say(f"  (walk to {label} gave up)")
    return False


def tour_here(flag, limit=60.0):
    """A first visit: Miao Meow leads the way to her spot; walk up to her and read the conversation through."""
    for _ in range(int(limit / DT)):
        if manager().state.get("flags", {}).get(flag):
            settle(5)
            return True
        if story().dialogue is not None:
            read_dialogue()
            continue
        guide, r = story().guide, room()
        if guide.leading is not None and r is not None:
            box = story().brain.footprint().inflate(24, 24)
            if not r.players[0].feet.colliderect(box):
                walk_to(box, limit=2.0, label="Miao Meow")
                continue
        step()
    return bool(manager().state.get("flags", {}).get(flag))


def talk_to_miao(limit=90.0):
    """Find Miao Meow in whichever room she is, walk up to her and press E (hints and talks are only ever asked for)."""
    for _ in range(6):
        brain = story().brain
        target = brain.room_id if brain.room_id in ("home", "arcade_floor", "prize_plaza") else "home"
        r = go_to_room(target)
        miao = getattr(r, "miao", None)
        if miao is None or not miao.present:
            seconds(3)
            continue
        walk_to(miao.zone, limit=10, label="Miao Meow")
        frames(3)
        r = room()
        if r is not None and r.players[0].nearby is getattr(r, "miao", None):
            tap(K.K_e, after=20)
            if story().dialogue is not None:
                return True
        seconds(2)
    return False


def through_door(target_room):
    r = settle()
    door = next(e for e in r.exits if e.target == target_room)
    walk_to(door.trigger, label=f"door to {target_room}")
    wait_for(lambda: room() is not None and room().room_id == target_room and not game.scenes.transitioning,
             10, f"room {target_room}")
    frames(10)
    return settle()


def go_to_room(target):
    """Walk through doors: the hub is ARCADE FLOOR <-> HOME <-> PRIZE PLAZA."""
    r = settle()
    if r.room_id == target:
        return r
    if r.room_id != "home":
        r = through_door("home")
    if target != "home":
        r = through_door(target)
    return r


def find(r, label=None, machine=None, kind=None):
    for m in r.interactables:
        if machine is not None and getattr(m, "id", None) == machine:
            return m
        if label is not None and getattr(m, "prompt_label", None) == label:
            return m
        if kind is not None and type(m).__name__ == kind:
            return m
    raise LookupError((label, machine, kind))


def use(target_room, label=None, machine=None, kind=None, until=None, wait=8.0):
    """Walk to a machine / station and press E on it. `until(scene)`: what must be on screen afterwards."""
    r = go_to_room(target_room)
    thing = find(r, label, machine, kind)
    z = thing.zone
    middle = pygame.Rect(z.centerx - 4, z.y, 8, z.h)          # the middle of its zone (neighbours' zones touch at the edges)
    for attempt in range(4):
        walk_to(middle if attempt < 2 else z, label=label or machine or kind)
        frames(3)
        r = room()
        if r is not None and r.players[0].nearby is thing:
            tap(K.K_e, after=20)
            for _ in range(3):                                # a machine asks first: PLAY (COST 1 TOKEN)?
                rr = room()
                if rr is not None and scene() is rr and (rr.panel is not None or rr.interaction is not None):
                    tap(K.K_e, after=20)
            if until is None or wait_for(lambda: until(scene()) and not game.scenes.transitioning, wait, "screen"):
                frames(5)
                return scene()
        settle()
        r = room()
        say(f"  (use {label or machine or kind}: nearby is {r.players[0].nearby if r else None}, scene {scene()})")
    shot("error_use")
    raise RuntimeError(f"could not use {label or machine or kind}")


def back_to_room(limit=10):
    """ESC until a room is on screen again."""
    for _ in range(limit):
        if room() is not None and not game.scenes.transitioning:
            return settle()
        release()
        tap(K.K_ESCAPE, after=30)
    wait_for(lambda: room() is not None, 10, "room")
    return settle()


def leave_game():
    """Mid-run: the game's own pause menu (ESC), then RETURN TO LOBBY. CAT VOLLEYBALL's ESC goes to the lobby at once."""
    release()
    sc = scene()
    if isinstance(sc, (CatMazeScene, GalaxyDefenderScene)):
        tap(K.K_ESCAPE, after=10)                                    # PAUSED: RESUME / RESTART / RETURN TO LOBBY
        tap(K.K_DOWN, after=5)
        tap(K.K_DOWN, after=5)
        tap(K.K_RETURN, after=30)
    elif isinstance(sc, PixelVolleyballScene):
        tap(K.K_ESCAPE, after=30)
    wait_for(lambda: room() is not None and not game.scenes.transitioning, 10, "lobby")
    return back_to_room()


# ------------------------------------------------------------------ minigame bots (they press the games' own keys)
MAZE_DIRS = {(0, -1): K.K_UP, (0, 1): K.K_DOWN, (-1, 0): K.K_LEFT, (1, 0): K.K_RIGHT}


def maze_step_towards(run, goal_fn, avoid):
    view = run._cat_maze()
    start = run.cat.nearest_tile()
    prev = {start: None}
    q = collections.deque([start])
    found = None
    while q:
        t = q.popleft()
        if goal_fn(t):
            found = t
            break
        for d in MAZE_DIRS:
            n = (t[0] + d[0], t[1] + d[1])
            if n in prev or not view.is_open(n) or n in view.restricted or (n in avoid and n != start):
                continue
            prev[n] = t
            q.append(n)
    if found is None or found == start:
        return None
    while prev[found] != start:
        found = prev[found]
    return (found[0] - start[0], found[1] - start[1])


def maze_bot(sc, seek_corridor=True, careless=False):
    g = sc.cat_maze
    run = g.run
    if g.screen is MS.OVER:
        return "over"
    if g.screen is not MS.PLAYING:
        step(hold(()))
        return None
    danger = set()
    if not careless:
        for r in run.robots:
            if r.hostile and not r.fright:
                rt = r.nearest_tile()
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        if abs(dx) + abs(dy) <= 2:
                            danger.add((rt[0] + dx, rt[1] + dy))
    if seek_corridor and run.corridor is not None and not run.corridor.found:
        goal = lambda t: t == corridor.END
    else:
        goal = lambda t: t in run.fish
    d = maze_step_towards(run, goal, danger) or maze_step_towards(run, goal, set())
    step(hold([MAZE_DIRS[d]] if d else ()))
    return None


def galaxy_bot(sc, seek_signal=True, dodge=False):
    g = sc.galaxy
    run = g.run
    if g.screen is GS.OVER:
        return "over"
    if g.screen is not GS.PLAYING:
        step(hold(()))
        return None
    keys = {K.K_SPACE}
    if seek_signal and run.signal is not None and not run.signal.received:
        target = run.signal.x
    else:
        threats = [b for b in run.enemy_bolts if 180 < b.y < 272 and abs(b.x - run.x) < 14] if dodge else []
        if threats:
            target = run.x + (30 if threats[0].x < run.x else -30)
        elif run.boss:
            target = run.boss.x
        elif run.enemies:
            target = max(run.enemies, key=lambda e: (e.y, -abs(e.x - run.x))).x
        else:
            target = 200
    if target < run.x - 2:
        keys.add(K.K_a)
    elif target > run.x + 2:
        keys.add(K.K_d)
    step(hold(keys))
    return None


def volley_bot(sc, seek_ticket=True):
    v = sc.volley
    match = v.match
    if match.state is MatchState.FINISHED:
        if v.ticket_playing:                                          # the ticket scene plays before the result card
            step(hold(()))
            return None
        return "over"
    if match.state is not MatchState.PLAYING:
        step(hold(()))
        return None
    me, ball = match.players[0], match.ball
    keys = set()
    x, y, vx, vy = ball.x, ball.y, ball.vx, ball.vy
    for _ in range(240):
        vy += 430 * (1 / 120)
        x += vx / 120
        y += vy / 120
        if x < 26 or x > 374:
            vx = -vx
        if y >= me.y - 10 and vy > 0:
            break
    target = (min(x, 186) - 5) if x < 200 else 90
    if abs(ball.x - me.x) < 26 and 0 < me.y - ball.y < 70 and ball.vy > 0:
        keys.add(K.K_w)
    if target < me.x - 3:
        keys.add(K.K_a)
    elif target > me.x + 3:
        keys.add(K.K_d)
    step(hold(keys))
    return None


def play_machine(machine_id, cls):
    need_tokens(2)
    return use("arcade_floor", machine=machine_id, until=lambda s: isinstance(s, cls), wait=15)


def one_round(machine_id, cls, start_key, bot, limit_s=600, shot_name=None, **kw):
    """Start a minigame from its cabinet, play ONE run to its end with the bot, and walk back out (ESC)."""
    sc = play_machine(machine_id, cls)
    tap(start_key, after=10)
    for _ in range(int(limit_s / DT)):
        if bot(sc, **kw) == "over":
            break
    release()
    frames(60)
    shot(shot_name or f"early_{machine_id}")
    back_to_room()


# ------------------------------------------------------------------ RETRO RACER (Secret Item 01)
def racer_drive(run, sc):
    """The racer package's own autopilot (test_reverse_road.drive_bot), turned into held arrow keys."""
    p, road = run.player, run.road
    lane = 0.0
    ahead = [c for c in run.traffic.cars if 0 < c.z - p.front_z < 9000]
    if ahead:
        lane = -0.66 if ahead[0].x >= 0 else 0.66
    steer = max(-1, min(1, (lane - p.x) * 3 + road.segment_at(p.front_z).curve * 0.6))
    keys = set()
    if p.speed_percent < 0.55:
        keys.add(K.K_UP)
    if steer < -0.25:
        keys.add(K.K_LEFT)
    elif steer > 0.25:
        keys.add(K.K_RIGHT)
    return keys


# ================================================================== THE RUN
def main():
    global game
    pygame.init()
    say("temporary save folder:", TMP)

    # ---------------------------------------------------------- 1. a new profile through the real startup screens
    game = Game(profiles=ProfileManager(SAVES), debug=True)
    frames(30)
    shot("00_title")
    tap(K.K_RETURN, after=60)                                         # title -> SELECT PROFILE
    tap(K.K_RETURN, after=20)                                         # + NEW PROFILE
    type_text("tester")
    tap(K.K_RETURN, after=60)
    for k in (K.K_RETURN,) * 5 + (K.K_DOWN, K.K_RETURN):            # the character creator: defaults, CONFIRM
        tap(k, after=12)
    frames(60)
    tap(K.K_RETURN, after=10)                                         # play the new profile
    wait_for(lambda: game.hub is not None, 10, "hub")
    check("1 a new isolated profile is playing", game.profile is not None and game.profile.display_name == "TESTER"
          and game.profile.story.get("opening_done", False) is False)
    say("  profile:", game.profile.profile_id, "tokens", game.profile.tokens, "tickets", game.profile.tickets)

    # ---------------------------------------------------------- 2-3. the opening cutscene, meeting Miao Meow
    seconds(6)
    shot("01_opening_wake")
    lines_seen = 0
    for _ in range(int(120 / DT)):
        if story().dialogue is not None:
            if lines_seen == 6:
                shot("02_opening_meet_miao")
            lines_seen += 1
            seconds(1.0)
            tap(K.K_e, after=3)
        elif manager().opening_done and not story().locked:
            break
        else:
            step()
    check("2-3 the opening played and Miao Meow was met", manager().opening_done and lines_seen >= 10)
    seconds(1.5)
    shot("03_first_quest")
    settle(20)

    # ---------------------------------------------------------- 4. the introductory tour
    r = go_to_room("arcade_floor")
    seconds(2)
    shot("04_tour_arcade_floor")
    tour_here("tour_arcade")
    r = go_to_room("prize_plaza")
    seconds(2)
    shot("05_tour_prize_plaza")
    tour_here("met_mochi")
    check("4 tour: arcade floor and Mochi met", manager().state["flags"].get("tour_arcade") and
          manager().state["flags"].get("met_mochi"))
    # Give It a Try (3 machines) and Earn Your Rewards (tickets from an Arcade Floor game): real rounds
    one_round("puzzle_drop", CatMazeScene, K.K_RETURN, maze_bot, limit_s=400, careless=True)
    one_round("galaxy_defender", GalaxyDefenderScene, K.K_RETURN, galaxy_bot, limit_s=600)
    one_round("pixel_volleyball", PixelVolleyballScene, K.K_e, volley_bot, limit_s=900)
    settle(20)
    if manager().active.id == "earn_some_rewards":                   # (Tickets count once that quest is the active one)
        say("  one more NEON CAT MAZE round for EARN YOUR REWARDS")
        one_round("puzzle_drop", CatMazeScene, K.K_RETURN, maze_bot, limit_s=400, careless=True)
        settle(20)
    say("  quests completed:", manager().state.get("completed"), "active:", manager().active.id)
    check("4 tutorial quests done", manager().active.id == "check_the_vending_machine")
    check("  no Chapter 02 symbol could be recorded before the chapter", manager().clues_found == 0)

    # ---------------------------------------------------------- 5-6. the vending machine's Secret Interface
    def konami():
        for k in (K.K_UP, K.K_UP, K.K_DOWN, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_LEFT, K.K_RIGHT, K.K_b, K.K_a):
            tap(k, after=4)

    use("arcade_floor", kind="VendingMachine", until=lambda s: isinstance(s, VendingScene))
    seconds(1)
    konami()
    seconds(1.0)
    shot("06_vending_secret")
    wait_for(lambda: isinstance(scene(), LegacyTerminalScene), 15, "legacy terminal")
    seconds(8)
    shot("07_legacy_terminal_ch1")
    check("5-6 Secret Interface found, Chapter 01 open", manager().chapter_unlocked(1) and
          manager().active.id == "ch1_secret_item")
    back_to_room()
    settle(20)

    # Mochi's Retro Racer story (Prize Counter, then the bag key opens CHAT WITH MOCHI)
    use("prize_plaza", label="PRIZE COUNTER", until=lambda s: isinstance(s, ShopScene))
    tap(K.K_i, after=60)
    chat = scene()
    if isinstance(chat, MochiChatScene):
        say("  Mochi options:", [label for label, _ in chat.options])
        tap(K.K_e, after=10)
        while chat.talk is not None:
            seconds(0.8)
            tap(K.K_RETURN, after=3)
        shot("08_mochi_story")
    check("  Mochi told the Retro Racer story", manager().state["flags"].get(Q.MOCHI_ARCADE_STORY))
    back_to_room()

    # ---------------------------------------------------------- 7. the Reverse Gear in Retro Racer
    need_tokens(3)
    sc = use("arcade_floor", machine="retro_racer", until=lambda s: isinstance(s, RetroRacerScene), wait=30)
    wait_for(lambda: sc.racer is not None and sc.racer.state.name == "TITLE", 60, "racer title")
    racer = sc.racer
    for _ in range(40):                                               # ENTER through the menus to a race
        if racer.state.name in ("COUNTDOWN", "PLAYING"):
            break
        tap(K.K_RETURN, after=20)
    wait_for(lambda: racer.state.name == "PLAYING", 20, "race start")
    say("  racer state", racer.state.name)
    seconds(20.5)                                                    # stand completely still ...
    step(hold([K.K_DOWN]))                                           # ... then really back up
    wait_for(lambda: racer.secret is not None, 10, "reverse road")
    release()
    shot("09_reverse_road_cutscene")
    run = racer.secret
    tap(K.K_RETURN, after=30)                                         # skip the cutscene
    wait_for(lambda: run.phase == run.DRIVE, 10, "highway")
    for i in range(int(400 / DT)):
        if run.phase == run.DRIVE:
            step(hold(racer_drive(run, sc)))
            if i == 600:
                shot("10_forgotten_highway")
        elif run.phase == run.REWARD or manager().has_secret_item(Q.SECRET_ITEM_RETRO_RACER):
            break
        else:
            step(hold(()))
    release()
    seconds(3)
    shot("11_reverse_gear")
    check("7 Secret Item 01 (Reverse Gear) recorded", manager().has_secret_item(Q.SECRET_ITEM_RETRO_RACER))
    tap(K.K_RETURN, after=60)
    back_to_room()
    settle(10)
    if talk_to_miao():                                              # Miao Meow's secret-road talk: E on her
        seconds(1)
        shot("11b_miao_reverse_road_talk")
        read_dialogue()
    settle(10)
    check("  Miao Meow's Reverse Road talk told", manager().state["flags"].get(Q.MIAO_REVERSE_ROAD))

    # ---------------------------------------------------------- 8. Trial 01: The Golden Age, for real
    use("arcade_floor", kind="VendingMachine", until=lambda s: isinstance(s, VendingScene))
    seconds(1)
    konami()
    wait_for(lambda: isinstance(scene(), LegacyTerminalScene), 15, "legacy terminal")
    seconds(8)
    shot("12_legacy_terminal_trial01")
    driver = GT.Driver(game, shot=lambda name: shot("trial01_" + name))
    driver.enter_trial()
    seconds(2)
    driver.watch_intro()
    shot("13_trial01_dark_room")
    driver.restore_power()
    driver.read_drawer()
    driver.listen_to_phone()
    driver.open_cabinet()
    driver.read_note()
    driver.get_boot_disk()
    driver.use("computer")
    driver.tap(K.K_e)                                               # INSERT BOOT DISK? YES
    driver.seconds(4.7)
    driver.tap(K.K_1)                                               # [1] PLAY GAME
    driver.seconds(0.5)
    shot("14_happy_breakout")
    t = driver.play_breakout(real=True, limit=1200.0)
    say(f"  HAPPY BREAKOUT.EXE cleared with real arrow-key events in {t:.0f}s of game time")
    driver.seconds(0.5)
    driver.tap(K.K_e)
    driver.tap(K.K_3)                                               # [3] LOCKED FILES
    driver.seconds(4.6)
    driver.tap(K.K_e)
    driver.seconds(0.5)
    driver.talk_through()
    driver.seconds(1.0)
    shot("15_trial01_complete")
    check("8 Trial 01 complete", manager().trial_done("trial_01"))
    driver.finish_card()
    wait_for(lambda: isinstance(scene(), LegacyTerminalScene) or room() is not None, 30, "terminal")
    seconds(2)
    shot("16_terminal_after_trial01")
    back_to_room()
    settle(30)

    # ---------------------------------------------------------- 9. Chapter 02 opens by itself
    check("9 Chapter 02 opened naturally", manager().chapter_two_open and manager().active.id == "ch2_secret_item")
    seconds(1)
    tap(K.K_q, after=20)
    shot("16_chapter02_open_quest_log")
    tap(K.K_ESCAPE, after=20)

    # ---------------------------------------------------------- 10. the hint cards from ordinary capsule pulls
    cards = tuple(fg.HINT_CARDS.values())
    pulls, rounds = 0, 0
    labels = ("CAT CAPSULE", "RETRO CAPSULE")
    while not all(profile().inventory.has_item(c) for c in cards) and pulls < 40:
        if profile().tickets < 15:
            # Pulls cost 15 Tickets: earn them in NEON CAT MAZE (the bot ignores the corridor here)
            rounds += 1
            before = profile().tickets
            one_round("puzzle_drop", CatMazeScene, K.K_RETURN, maze_bot, limit_s=600,
                      shot_name="ticket_round", seek_corridor=False)
            say(f"  ticket round {rounds}: {before} -> {profile().tickets} tickets")
            continue
        cap = use("prize_plaza", label=labels[pulls % 2], until=lambda s: isinstance(s, CapsuleScene))
        while profile().tickets >= 15 and not all(profile().inventory.has_item(c) for c in cards):
            tap(K.K_e, after=90)
            pulls += 1
            if cap.result is not None and cap.result.item_id in cards:
                say(f"  pull {pulls} ({cap.spec.name if hasattr(cap, 'spec') else labels[pulls % 2]}): "
                    f"{cap.result.name}  (pity counter now {manager().card_pity})")
                if not os.path.exists(os.path.join(OUT, "17_capsule_hint_card.png")):
                    shot("17_capsule_hint_card")
            if pulls % 2 == 0:
                break                                               # (and the other machine next time)
        back_to_room()
    check("10 all three hint cards from ordinary pulls, single copies",
          all(profile().inventory.get_quantity(c) == 1 for c in cards))
    say(f"  pulls: {pulls}; maze rounds played for Tickets: {rounds}")

    # ---------------------------------------------------------- 11-13. the three symbols
    def hunt(machine_id, cls, start_key, bot, clue, found_shot, limit_s=1800):
        sc = play_machine(machine_id, cls)
        tap(start_key, after=10)
        routes = []
        for i in range(int(limit_s / DT)):
            out = bot(sc)
            if out == "over":
                release()
                frames(40)
                say(f"  {machine_id}: run over; tries counted {manager().clue_tries(clue)}")
                need_tokens(1)
                tap(start_key if machine_id != "pixel_volleyball" else K.K_e, after=10)
            if manager().clue_found(clue):
                break
        frames(30)
        shot(found_shot)
        release()
        found = manager().clue_found(clue)
        return sc, found

    sc, ok = hunt("puzzle_drop", CatMazeScene, K.K_RETURN, maze_bot, "maze", "18_maze_star_I")
    say(f"  maze: corridor found by the {manager().clue_route('maze')} route, in level "
        f"{sc.cat_maze.run.level if sc.cat_maze.run else '-'}; tries {manager().clue_tries('maze')}")
    check("11 STAR (I) discovered in Neon Cat Maze", ok)
    leave_game()
    tracker = [t for t, _ in story().tracker._detail()]
    check("  tracker shows SYMBOLS 1/3 (count only)", "SYMBOLS 1/3" in tracker)
    tap(K.K_q, after=20)
    tap(K.K_RIGHT, after=10)
    shot("19_quest_log_symbols_1")
    tap(K.K_ESCAPE, after=20)

    # III before II: the order of discovery does not matter
    sc, ok = hunt("pixel_volleyball", PixelVolleyballScene, K.K_e, volley_bot, "volley", "20_volley_paw_III")
    check("13 PAW (III) discovered in Cat Volleyball", ok)
    say(f"  volley: ticket found by the {manager().clue_route('volley')} route; tries {manager().clue_tries('volley')}")
    leave_game()
    sc, ok = hunt("galaxy_defender", GalaxyDefenderScene, K.K_RETURN, galaxy_bot, "galaxy", "21_galaxy_moon_II")
    check("12 MOON (II) discovered in Starfall Assault", ok)
    say(f"  galaxy: signal found by the {manager().clue_route('galaxy')} route; tries {manager().clue_tries('galaxy')}")
    leave_game()
    rows = manager().recovered_symbols()
    check("  Quest Log order I II III", [r[1] for r in rows] == ["STAR", "MOON", "PAW"])

    # ---------------------------------------------------------- 14. Miao Meow's hint (once)
    r = settle(1)
    told = False
    for _ in range(int(40 / DT)):
        if story().dialogue is not None:
            seconds(1.5)
            shot("22_miao_hint")
            told = [l.text for l in story().dialogue.lines] == [l.text for l in fg.MIAO_HINT_LINES]
            read_dialogue()
            break
        step()
    check("14 Miao Meow's Chapter 02 hint played", told and manager().state["flags"].get(Q.MIAO_CH2_HINT))
    go_to_room("home")
    seconds(8)
    check("  ... and only once", story().dialogue is None)

    # ---------------------------------------------------------- 15. Mochi's maintenance lock
    use("prize_plaza", label="PRIZE COUNTER", until=lambda s: isinstance(s, ShopScene))
    tap(K.K_i, after=60)
    chat = scene()
    keys = [k for _, k in chat.options]
    say("  Mochi options:", [label for label, _ in chat.options])
    while chat.options[chat.index][1] != "unusual":
        tap(K.K_DOWN, after=4)
    tap(K.K_e, after=10)
    while chat.talk is not None:
        seconds(0.8)
        tap(K.K_RETURN, after=3)
    wait_for(lambda: isinstance(scene(), MaintenanceNoteScene), 10, "record")
    seconds(1)
    shot("23_mochi_record")
    check("  Mochi's record is read only and points to the claw machine",
          not hasattr(scene(), "wheels") and any("claw machine" in l.text.lower() for l in fg.RECORD_INTRO))
    back_to_room()

    # ---------------------------------------------------------- 15b. the prize lock on the claw machine
    need_tokens(10)
    claw = use("prize_plaza", label="CLAW MACHINE", until=lambda s: isinstance(s, ClawScene))
    seconds(1)
    shot("24_claw_lock_waiting")
    check("  the claw machine shows its prize lock", claw.lock_waiting)
    tap(K.K_w, after=30)                                            # UP: look at the lock
    note = scene()
    check("  the lock opens from the claw machine and starts empty",
          isinstance(note, ClawLockScene) and note.marks == [None, None, None] and not manager().riddle_solved)
    tap(K.K_q, after=10)                                            # Q: the Quest Log's recovered symbols, right here
    shot("25_claw_lock_quest_log")
    check("  Q shows the recovered symbols over the lock", note.log is not None and
          [r[1] for r in note.log.symbol_rows()] == ["STAR", "MOON", "PAW"])
    tap(K.K_q, after=10)

    def set_lock(marks):
        for i, mark in enumerate(marks):
            while note.cursor != i:
                tap(K.K_RIGHT, after=3)
            for _ in range(len(fg.LOCK_CHOICES) + 1):
                if note.marks[i] == mark:
                    break
                tap(K.K_DOWN, after=3)
        tap(K.K_e, after=10)

    set_lock(("MOON", "STAR", "PAW"))
    shot("26_claw_lock_wrong")
    check("  a wrong order is refused gently", not manager().riddle_solved and note.reply in fg.WRONG_LINES)
    seconds(3)
    set_lock(("STAR", "MOON", "PAW"))
    seconds(0.5)
    shot("27_claw_lock_open")
    check("15 STAR MOON PAW opens the lock; no item yet", manager().riddle_solved and
          not manager().has_secret_item(Q.SECRET_ITEM_CLAW))
    wait_for(lambda: scene() is claw, 10, "back to the claw machine")
    seconds(1.5)

    # ---------------------------------------------------------- 16-17. the Golden Cat, with the real claw
    g = claw.claw
    shot("28_claw_golden_cat")
    check("16 the Golden Cat is in the machine", any(p.spec is fg.GOLDEN_CAT for p in g.plushies))
    tries = 0
    while not manager().has_secret_item(Q.SECRET_ITEM_CLAW) and tries < 12:
        tries += 1
        need_tokens(cm.CLAW_PLAY_COST if hasattr(cm, "CLAW_PLAY_COST") else 2)
        tap(K.K_e, after=3)
        target = next((p for p in g.plushies if p.spec is fg.GOLDEN_CAT), None)
        if target is None:
            break
        for _ in range(600):
            if g.phase != cm.AIM or abs(g.x - target.x) <= 1.2:
                break
            step(hold([K.K_d if g.x < target.x else K.K_a]))
        release()
        frames(15)
        tap(K.K_e)
        for _ in range(int(30 / DT)):
            step()
            if g.phase == cm.WON and manager().has_secret_item(Q.SECRET_ITEM_CLAW):
                frames(25)
                shot("29_claw_golden_cat_won")
                break
            if g.phase == cm.IDLE:
                break
        wait_for(lambda: g.phase == cm.IDLE, 20, "claw idle")
        say(f"  claw try {tries}: won {g.attempt.won if g.attempt else '-'}; slips counted {manager().golden_misses}")
    check("17 Secret Item 02 awarded by a real grab", manager().has_secret_item(Q.SECRET_ITEM_CLAW))
    check("  one Golden Cat in the bag, and it left the machine", profile().inventory.get_quantity("claw_golden_cat") == 1
          and not any(p.spec is fg.GOLDEN_CAT for p in g.plushies))
    back_to_room()
    settle(20)
    check("  no more hint cards in the capsule machines now", fg.HintCardDraw(manager()).missing(profile()) == [])

    # ---------------------------------------------------------- 18. Chapter 02's trial: lifetime earnings
    check("18 next step is Secret Trial 02", manager().active.id == "ch2_secret_trial")
    have_k, have_t = Q.lifetime_earnings(profile())
    need_k, need_t = Q.trial_earnings("trial_02")
    trial = next(t for t in Q.TRIALS if t.id == "trial_02")
    status = Q.trial_status(manager(), profile(), trial)
    say(f"  lifetime earned: {have_k} tokens / {have_t} tickets; Trial 02 needs {need_k} / {need_t};"
        f" wallet {profile().tokens} / {profile().tickets}; status {status.code} {status.short}")
    use("arcade_floor", kind="VendingMachine", until=lambda s: isinstance(s, VendingScene))
    seconds(1)
    konami()
    wait_for(lambda: isinstance(scene(), LegacyTerminalScene), 15, "legacy terminal")
    seconds(8)
    shot("30_legacy_terminal_trial02")
    expected = "available" if have_k >= need_k and have_t >= need_t else "locked"
    check(f"  Trial 02 status follows lifetime earnings ({expected})", status.code == expected)
    check("  Chapter 03 still closed", not manager().chapter_unlocked(3))
    back_to_room()

    # ---------------------------------------------------------- 19. Quest Log, bag, collection; then save and reload
    settle(5)
    tap(K.K_q, after=20)
    shot("31_quest_log_overview")
    tap(K.K_RIGHT, after=10)
    shot("32_quest_log_symbols_all")
    tap(K.K_ESCAPE, after=20)
    tap(K.K_i, after=20)
    ui = room().inventory_ui
    say("  bag (ALL):", [d.id for d, _ in ui.entries])
    index = [d.id for d, _ in ui.entries].index("claw_golden_cat")
    for _ in range(index // 4):                                     # arrow keys to its slot
        tap(K.K_DOWN, after=4)
    for _ in range(index % 4):
        tap(K.K_RIGHT, after=4)
    say("  bag cursor on slot", room().inventory_ui.selected, "for index", index)
    tap(K.K_e, after=10)
    r = room()
    check("19 the Golden Cat can be found and inspected in the bag",
          r.inventory_ui is not None and r.inventory_ui.inspecting and r.inventory_ui.selected_entry[0].id == "claw_golden_cat")
    shot("33_inventory_golden_cat")
    tap(K.K_ESCAPE, after=5)
    tap(K.K_ESCAPE, after=20)
    col = use("home", label="COLLECTION", until=lambda s: isinstance(s, CollectionScene))
    while col.selected[0].id != "claw_golden_cat":
        tap(K.K_RIGHT, after=3)
    shot("34_collection_golden_cat")
    owned_bag = {d.id for d, _ in profile().inventory.get_all_items() if d.category == "COLLECTIBLE"}
    owned_col = {d.id for d, o in col.service.entries() if o}
    check("19 bag and collection agree", owned_bag == owned_col)
    back_to_room()

    before = json.loads(json.dumps(profile().to_dict()))
    pid = profile().profile_id
    game.quit()
    say("  quit; reloading the same save folder")
    game = Game(profiles=ProfileManager(SAVES), debug=True)
    frames(30)
    tap(K.K_RETURN, after=60)
    sel = scene()
    sel.selected = next(i for i, info in enumerate(sel.infos) if info.profile_id == pid)
    tap(K.K_RETURN, after=60)
    wait_for(lambda: game.hub is not None, 10, "hub")
    settle(20)
    m2 = manager()
    after = profile().to_dict()
    check("19 reload keeps the story", m2.has_secret_item(Q.SECRET_ITEM_CLAW) and m2.trial_done("trial_01")
          and m2.riddle_solved and [r[1] for r in m2.recovered_symbols()] == ["STAR", "MOON", "PAW"])
    check("19 reload keeps the inventory", after["inventory"] == before["inventory"])
    tap(K.K_q, after=20)
    tap(K.K_RIGHT, after=10)
    shot("35_quest_log_after_reload")
    tap(K.K_ESCAPE, after=10)
    game.quit()

    say("")
    say(f"F5 (+10 tokens) used {F5_USES[0]} times")
    failed = [n for n, ok in CHECKS if not ok]
    say(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    for n in failed:
        say("FAILED:", n)
    return not failed


if __name__ == "__main__":
    ok = False
    try:
        ok = main()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
        say("temporary save folder removed")
    sys.exit(0 if ok else 1)
