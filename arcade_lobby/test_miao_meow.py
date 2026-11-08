"""Tests for MIAO MEOW: her Mochi-based sprite frames (size, crown placement, eyes, grey face details, walk cycle),
the coin-bell light (distance, hysteresis, fade), her brain (idle / look / walk / leave / transit / anchor, never
through a wall or into a player), the map of spots she uses (checked against the real rooms), and that she sits in
the hub without disturbing machines, players, two-player mode, Mochi or the other rooms.

Run headless from this folder:   python -m unittest test_miao_meow -v
"""
import hashlib
import math
import os
import random
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import miao_meow as mm  # noqa: E402
import shopkeeper as sk  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from machine import ArcadeMachine  # noqa: E402
from miao_meow import ARCADE, HOME, PLAZA, MiaoBrain, MiaoMeow  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from room import room_walls  # noqa: E402
from room_testing import goto_room  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class Body:
    """A stand-in for a player body: only what the brain reads (position and a feet box)."""

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)

    @property
    def feet(self):
        return pygame.Rect(int(self.x) - 5, int(self.y) - 5, 10, 5)


def open_room(room_id=HOME, players=()):
    """A bare room: just the walls (with the doorways of the real room), no furniture, no cats."""
    sides = {HOME: ("left", "right"), ARCADE: ("right",), PLAZA: ("left",)}[room_id]
    return SimpleNamespace(room_id=room_id, solids=room_walls(sides), players=list(players),
                           cats=SimpleNamespace(cats=[]))


def digest(surface):
    return hashlib.sha1(pygame.image.tobytes(surface, "RGBA")).hexdigest()


def run(brain, room, seconds):
    for _ in range(int(seconds / DT)):
        brain.update(DT, room)


def all_frame_variants():
    """Every distinct look she can show (coin level aside)."""
    for pose, legs in (("sit", 0), ("stand", 0), ("stand", 1), ("stand", 2)):
        for eyes in ("open", "closed", "happy", "sleepy", "surprised"):
            for tail in (0, 1, 2):
                for ear in (0, 1, 2):
                    for tilt in ((False, True) if pose == "sit" else (False,)):
                        yield dict(pose=pose, eyes=eyes, tail=tail, ear=ear, tilt=tilt, gaze=(0, 1), legs=legs)


class SpriteTests(unittest.TestCase):
    def test_frames_have_mochis_exact_size(self):
        mochi = sk.mochi_frame("sit")
        for kw in all_frame_variants():
            self.assertEqual(mm.miao_frame(**kw).get_size(), mochi.get_size(), kw)
        self.assertEqual(mm.SIZE, sk.Shopkeeper.SIZE)

    def test_crown_stays_above_the_eyes_and_between_the_ears(self):
        probe = pygame.Surface((18, 15), pygame.SRCALPHA)
        mm._crown(probe)
        pts = [(x, y) for x in range(18) for y in range(15) if probe.get_at((x, y))[3]]
        self.assertTrue(pts)
        eye_top = 2 + 2                                         # hy + 2, as in Mochi's eye painter
        self.assertLess(max(y for _, y in pts), eye_top)
        self.assertEqual(min(y for _, y in pts), 0)
        self.assertTrue(all(2 <= x <= 6 for x, _ in pts))       # inside the ear tips (x 1 and 7)
        self.assertEqual(len(pts), 5 + 5 + 3 + 1)               # 5-wide band + 5-wide base + 3 points: the approved shape

    def test_crown_is_in_every_frame_and_travels_with_the_head(self):
        """The crown's tall centre pixel is a fixed light pixel: (5, 1) in the image, one down and across (6, 2) when the
        head leans. Standing (walking) frames put the head where sitting ones do, so the crown never bobs off."""
        for kw in all_frame_variants():
            f = mm.miao_frame(**kw)
            at = (6, 2) if kw["tilt"] else (5, 1)
            self.assertEqual(f.get_at(at)[:3], mm.CROWN_LIGHT, kw)
            self.assertEqual(f.get_at((at[0], at[1] - 1))[3], 255, "outline above the crown")

    def test_crown_has_the_chosen_wide_three_point_shape(self):
        f = mm.miao_frame()
        self.assertEqual(f.get_at((3, 2))[:3], mm.CROWN_LIGHT)
        self.assertEqual(f.get_at((7, 2))[:3], mm.CROWN_GOLD)
        for x in range(3, 8):
            self.assertEqual(f.get_at((x, 4))[:3], mm.CROWN_SHADE, x)
        for x in range(f.get_width()):                          # no gem: nothing lilac on the cat
            for y in range(f.get_height()):
                r, g, b, a = f.get_at((x, y))
                self.assertFalse(a and r < 235 and b > 230 and g < 150 and b > r, (x, y))

    def test_eyes_are_mochis_exactly(self):
        for gaze in ((0, 1), (1, 1), (0, 0), (1, 0)):
            mine = mm.miao_frame(eyes="open", gaze=gaze)
            theirs = sk.mochi_frame(eyes="open", gaze=gaze)
            for x in (1, 2, 5, 6):
                for y in (4, 5, 6):
                    self.assertEqual(mine.get_at((x + 1, y + 1))[:3], theirs.get_at((x + 1, y + 1))[:3], (gaze, x, y))

    def test_standing_frames_have_the_same_eyes_as_sitting_ones(self):
        sit, stand = mm.miao_frame("sit"), mm.miao_frame("stand")
        for x in (1, 2, 5, 6):
            for y in (4, 5, 6):
                self.assertEqual(sit.get_at((x + 1, y + 1)), stand.get_at((x + 1, y + 1)), (x, y))

    def test_face_details_are_soft_grey_not_pink(self):
        self.assertEqual(mm.miao_frame().get_at((1, 7))[:3], mm.SOFT_GREY)    # nose
        for kw in all_frame_variants():
            g = mm.miao_frame(**kw)
            for x in range(g.get_width()):
                for y in range(g.get_height()):
                    self.assertNotEqual(g.get_at((x, y))[:3], (255, 150, 180), (kw, x, y))

    def test_fur_has_light_and_dark_steps(self):
        f = mm.miao_frame()
        colors = {tuple(f.get_at((x, y))[:3]) for x in range(f.get_width()) for y in range(f.get_height())}
        self.assertTrue({mm.LOOK.fur, mm.FUR_HI, mm.FUR_LO} <= colors)

    def test_walk_cycle_changes_the_legs_but_not_the_head(self):
        a, b = mm.miao_frame("stand", legs=1), mm.miao_frame("stand", legs=2)
        self.assertNotEqual(digest(a), digest(b))
        for x in range(2, 10):
            for y in range(0, 10):
                self.assertEqual(a.get_at((x, y)), b.get_at((x, y)), (x, y))

    def test_mochi_is_untouched(self):
        looks = [dict(), dict(eyes="happy"), dict(eyes="sleepy", ear=1), dict(pose="nap", eyes="closed"), dict(tilt=True)]
        before = [digest(sk.mochi_frame(**k)) for k in looks]
        fur = sk.LOOK.fur
        for kw in all_frame_variants():
            mm.miao_frame(**kw)
        for level in range(mm.LEVELS + 1):
            mm.miao_frame(level=level)
        self.assertEqual(before, [digest(sk.mochi_frame(**k)) for k in looks])
        self.assertEqual(sk.LOOK.fur, fur)
        self.assertNotEqual(mm.LOOK.fur, sk.LOOK.fur)

    def test_miao_meow_has_her_own_file_and_does_not_edit_mochis(self):
        here = os.path.dirname(os.path.abspath(__file__))
        self.assertTrue(os.path.exists(os.path.join(here, "miao_meow.py")))
        with open(os.path.join(here, "shopkeeper.py")) as f:
            self.assertNotIn("miao", f.read().lower())

    def test_facing_right_is_a_cached_mirror(self):
        f = mm.miao_frame()
        right = mm.facing_frame(f, "right")
        self.assertIs(mm.facing_frame(f, "right"), right)
        self.assertIs(mm.facing_frame(f, "left"), f)


class CoinTests(unittest.TestCase):
    def coin(self, level, **kw):
        f = mm.miao_frame(level=level, **kw)
        x, y = mm.COIN_AT
        return {"hl": f.get_at((x + 1, y + 1))[:3], "main": f.get_at((x + 2, y + 1))[:3], "edge": f.get_at((x + 2, y + 2))[:3]}

    @staticmethod
    def lum(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]

    def test_coin_is_dark_gold_when_off_and_warm_gold_when_lit(self):
        off, on = self.coin(0), self.coin(mm.LEVELS)
        self.assertEqual(off["main"], mm.COIN_DIM["main"])
        self.assertEqual(on["main"], mm.COIN_LIT["main"])
        for part in off:
            self.assertGreater(self.lum(on[part]), self.lum(off[part]) + 40, part)
        self.assertGreater(off["main"][0], off["main"][2])

    def test_coin_brightens_step_by_step(self):
        lums = [self.lum(self.coin(l)["main"]) for l in range(mm.LEVELS + 1)]
        self.assertEqual(lums, sorted(lums))
        self.assertEqual(len(set(lums)), mm.LEVELS + 1)

    def test_the_coin_is_in_the_same_place_standing_and_sitting(self):
        for legs in (0, 1, 2):
            self.assertEqual(self.coin(mm.LEVELS, pose="stand", legs=legs)["main"], mm.COIN_LIT["main"])

    def test_only_the_coin_area_changes_between_levels(self):
        for pose in ("sit", "stand"):
            a, b = mm.miao_frame(pose, level=0), mm.miao_frame(pose, level=mm.LEVELS)
            x, y = mm.COIN_AT
            near = pygame.Rect(x + 1 - 1, y + 1 - 1, 4, 4)
            for px in range(a.get_width()):
                for py in range(a.get_height()):
                    if not near.collidepoint(px, py):
                        self.assertEqual(a.get_at((px, py)), b.get_at((px, py)), (pose, px, py))

    def test_the_wash_is_small_cached_and_soft(self):
        img = mm._wash(mm.LEVELS)
        self.assertIs(mm._wash(mm.LEVELS), img)
        self.assertLessEqual(img.get_width(), 16)
        peak = max(max(img.get_at((x, y))[:3]) for x in range(img.get_width()) for y in range(img.get_height()))
        self.assertLess(peak, 140)


class LightTests(unittest.TestCase):
    def setUp(self):
        self.players = []
        self.brain = MiaoBrain(players=lambda: self.players, rng=random.Random(5))
        self.brain.place(HOME, (100, 200))
        self.brain.idle_left = 99999                             # she stays where she is while the light is measured
        self.room = open_room(HOME)

    def run_for(self, s):
        run(self.brain, self.room, s)

    def test_far_player_leaves_the_coin_dark(self):
        self.players.append(Body(100 + mm.LIGHT_OFF_RANGE + 40, 200))
        self.run_for(1.0)
        self.assertFalse(self.brain.lit)
        self.assertEqual(self.brain.level, 0)

    def test_nobody_in_the_room_is_fine(self):
        self.run_for(1.0)
        self.assertEqual(self.brain.level, 0)

    def test_approaching_player_lights_the_coin_with_a_short_gradual_fade(self):
        w = Body(400, 200)
        self.players.append(w)
        self.run_for(0.5)
        w.x = 100 + mm.LIGHT_ON_RANGE - 4
        levels = []
        for _ in range(int((mm.FADE_TIME + 0.2) / DT)):
            self.brain.update(DT, self.room)
            levels.append(self.brain.level)
        self.assertEqual(levels[-1], mm.LEVELS)
        self.assertEqual(levels, sorted(levels))
        self.assertGreater(len(set(levels)), 3)

    def test_fade_never_jumps(self):
        w = Body(400, 200)
        self.players.append(w)
        self.run_for(0.3)
        prev = self.brain.light
        w.x = 110
        for _ in range(120):
            self.brain.update(DT, self.room)
            self.assertLessEqual(abs(self.brain.light - prev), DT / mm.FADE_TIME + 1e-9)
            prev = self.brain.light

    def test_leaving_dims_the_coin_back_to_its_original_level(self):
        w = Body(110, 200)
        self.players.append(w)
        self.run_for(1.0)
        self.assertEqual(self.brain.level, mm.LEVELS)
        w.x = 400
        self.run_for(1.0)
        self.assertEqual(self.brain.level, 0)

    def test_hysteresis_stops_flicker_at_the_boundary(self):
        w = Body(100 + mm.LIGHT_ON_RANGE - 2, 200)
        self.players.append(w)
        self.run_for(1.0)
        self.assertTrue(self.brain.lit)
        flips = 0
        for i in range(600):
            w.x = 100 + (mm.LIGHT_ON_RANGE + 6 if i % 2 else mm.LIGHT_ON_RANGE - 6)
            was = self.brain.lit
            self.brain.update(DT, self.room)
            flips += was != self.brain.lit
        self.assertEqual(flips, 0)
        w.x = 100 + mm.LIGHT_OFF_RANGE + 2
        self.run_for(1.0)
        self.assertFalse(self.brain.lit)

    def test_dark_coin_stays_dark_inside_the_wide_band(self):
        self.players.append(Body(100 + (mm.LIGHT_ON_RANGE + mm.LIGHT_OFF_RANGE) // 2, 200))
        self.run_for(1.0)
        self.assertFalse(self.brain.lit)

    def test_two_players_the_nearer_one_counts(self):
        a, b = Body(400, 200), Body(105, 200)
        self.players += [a, b]
        self.run_for(1.0)
        self.assertEqual(self.brain.level, mm.LEVELS)
        b.x = 400
        self.run_for(1.0)
        self.assertEqual(self.brain.level, 0)

    def test_the_coin_is_dark_when_she_is_not_in_the_room_the_player_is_in(self):
        self.players.append(Body(110, 200))
        self.run_for(1.0)
        self.assertEqual(self.brain.level, mm.LEVELS)
        self.brain.room_id = ARCADE                              # she is somewhere else; the player stays here
        self.run_for(1.0)
        self.assertEqual(self.brain.level, 0)

    def test_light_state_does_not_depend_on_frame_rate(self):
        def make():
            b = MiaoBrain(players=lambda: [Body(110, 200)], rng=random.Random(5))
            b.place(HOME, (100, 200))
            return b
        slow, fast = make(), make()
        for _ in range(30):
            slow.update(1 / 30, self.room)
        for _ in range(60):
            fast.update(1 / 60, self.room)
        self.assertAlmostEqual(slow.light, fast.light, places=6)

    def test_only_the_coin_glows_not_the_cat(self):
        view = MiaoMeow(self.brain, HOME)
        surf = pygame.Surface((400, 300))
        surf.fill((20, 16, 40))
        before = digest(surf)
        view.draw_glow(surf)
        self.assertEqual(digest(surf), before, "a dark coin adds no wash")
        self.players.append(Body(110, 200))
        self.run_for(1.0)
        view.draw_glow(surf)
        changed = [(x, y) for x in range(400) for y in range(300) if surf.get_at((x, y))[:3] != (20, 16, 40)]
        self.assertTrue(changed)
        xs, ys = [p[0] for p in changed], [p[1] for p in changed]
        self.assertLessEqual(max(xs) - min(xs), 16)
        self.assertLessEqual(max(ys) - min(ys), 16)
        cx, cy = self.brain.coin_center()
        self.assertLessEqual(abs((max(xs) + min(xs)) / 2 - cx), 2)
        self.assertLessEqual(abs((max(ys) + min(ys)) / 2 - cy), 2)

    def test_wash_follows_the_coin_when_she_turns(self):
        self.players.append(Body(30, 200))
        self.run_for(0.5)
        left = self.brain.coin_center()
        self.players[:] = [Body(190, 200)]
        self.run_for(0.5)
        right = self.brain.coin_center()
        self.assertEqual(self.brain.side, "right")
        self.assertGreater(right[0], left[0])
        self.assertEqual(right[1], left[1])


class BrainBehaviourTests(unittest.TestCase):
    def setUp(self):
        self.sounds = []
        self.players = []
        self.brain = MiaoBrain(players=lambda: self.players, sound=self.sounds.append, rng=random.Random(3))
        self.brain.place(HOME, (100, 200))
        self.room = open_room(HOME)

    def test_idle_animation_runs_and_never_crashes(self):
        seen = set()
        for _ in range(60 * 30):
            self.brain.update(DT, self.room)
            seen.add(id(self.brain.frame()))
            self.assertEqual(self.brain.image().get_size(), mm.SIZE)
        self.assertGreater(len(seen), 3)

    def test_frame_cache_is_bounded_in_steady_state(self):
        for _ in range(60 * 40):
            self.brain.update(DT, self.room)
            self.brain.image()
        n = len(mm._FRAMES)
        for _ in range(60 * 40):
            self.brain.update(DT, self.room)
            self.brain.image()
        self.assertLessEqual(len(mm._FRAMES) - n, 12)
        self.assertLess(len(mm._FRAMES), 600)

    def test_she_turns_to_face_the_player(self):
        self.players.append(Body(40, 200))
        run(self.brain, self.room, 0.2)
        self.assertEqual(self.brain.side, "left")
        self.players[0].x = 170
        run(self.brain, self.room, 0.2)
        self.assertEqual(self.brain.side, "right")

    def test_first_approach_greets_once_with_a_happy_hop(self):
        self.brain.idle_left = 99
        self.players.append(Body(100 + mm.LIGHT_ON_RANGE - 5, 200))
        self.brain.update(DT, self.room)
        self.assertEqual(self.brain.state, "greet")
        self.assertEqual(self.sounds, [])                               # a greeting is a hop, not a noise (she meows when talked to)
        run(self.brain, self.room, 2.0)
        self.assertNotEqual(self.brain.state, "greet")
        self.assertEqual([e for e, _ in self.brain.events], ["greet"])

    def test_greeting_returns_after_leaving_and_the_cooldown(self):
        self.brain.idle_left = 99
        w = Body(110, 200)
        self.players.append(w)
        run(self.brain, self.room, 1.0)
        w.x = 400
        run(self.brain, self.room, mm.GREET_COOLDOWN + 1)
        self.brain.idle_left = 99
        w.x = 110
        run(self.brain, self.room, 0.2)
        self.assertEqual([e for e, _ in self.brain.events].count("greet"), 2)

    def test_talking_stops_her_and_faces_the_player_until_the_chat_ends(self):
        p = Body(60, 200)
        self.players.append(p)
        self.brain.path = [(200, 200)]
        self.brain.state = "walk"
        self.brain.notify("talk", p)
        before = self.brain.pos
        run(self.brain, self.room, 3.0)
        self.assertEqual(self.brain.state, "talk")
        self.assertEqual(self.brain.pos, before)
        self.assertEqual(self.brain.side, "left")
        self.brain.end_talk()
        self.assertEqual(self.brain.state, "idle")

    def test_meows_are_rate_limited(self):
        for _ in range(5):
            self.brain.notify("talk")
        self.assertEqual(len(self.sounds), 1)

    def test_unknown_event_is_rejected(self):
        with self.assertRaises(ValueError):
            self.brain.notify("dance")

    def test_hop_stays_small_and_returns_to_the_ground(self):
        self.brain.notify("greet")
        hops = []
        for _ in range(int(1.5 / DT)):
            self.brain.update(DT, self.room)
            hops.append(self.brain.hop())
        self.assertLessEqual(max(hops), 0)
        self.assertGreaterEqual(min(hops), -3)
        self.assertEqual(hops[-1], 0)

    def test_works_without_a_sound_callback(self):
        quiet = MiaoBrain(players=lambda: [Body(110, 200)])
        quiet.place(HOME, (100, 200))
        run(quiet, self.room, 1.0)
        quiet.notify("talk")


class MovementTests(unittest.TestCase):
    """Her walks, on a bare room: only the walls (and the real doorways) are in the way."""

    def setUp(self):
        self.brain = MiaoBrain(players=lambda: [], rng=random.Random(8))
        self.room = open_room(HOME)
        self.brain.place(HOME, mm.SPOTS[HOME]["hub"])

    def test_a_wander_reaches_its_spot(self):
        goal = mm.SPOTS[HOME]["nook"]
        self.assertTrue(self.brain._walk_to(self.room, goal))
        for _ in range(60 * 20):
            self.brain.update(DT, self.room)
            if self.brain.state != "walk":
                break
        self.assertNotEqual(self.brain.state, "walk")
        self.assertLess(math.hypot(self.brain.x - goal[0], self.brain.y - goal[1]), 1.5)

    def test_she_never_enters_a_solid_while_wandering(self):
        solids = self.room.solids
        for seed in range(6):
            b = MiaoBrain(players=lambda: [], rng=random.Random(seed))
            b.place(HOME, mm.SPOTS[HOME]["hub"])
            for _ in range(60 * 90):
                b.update(DT, self.room)
                if b.is_in(HOME):
                    self.assertEqual(mm.foot_rect(b.x, b.y).collidelist(solids), -1, (seed, b.pos))

    def test_she_stays_on_the_floor(self):
        floor = pygame.Rect(20, 64, 360, 218)
        doorways = [pygame.Rect(0, 198, 20, 52), pygame.Rect(380, 198, 20, 52)]    # the gaps in the side walls
        b = MiaoBrain(players=lambda: [], rng=random.Random(2))
        b.place(HOME, mm.SPOTS[HOME]["hub"])
        for _ in range(60 * 120):
            b.update(DT, self.room)
            if b.is_in(HOME):
                foot = mm.foot_rect(b.x, b.y)
                for corner in (foot.topleft, foot.topright, foot.bottomleft, foot.bottomright):
                    self.assertTrue(floor.collidepoint(corner) or any(d.collidepoint(corner) for d in doorways), b.pos)

    def test_walking_speed_is_a_stroll(self):
        goal = mm.SPOTS[HOME]["corner"]
        self.brain._walk_to(self.room, goal)
        start = self.brain.pos
        run(self.brain, self.room, 1.0)
        moved = math.hypot(self.brain.x - start[0], self.brain.y - start[1])
        self.assertLessEqual(moved, mm.SPEED * 1.0 + 1)
        self.assertGreater(moved, 10)

    def test_walking_uses_the_walk_cycle_and_standing_still_sits(self):
        self.brain._walk_to(self.room, mm.SPOTS[HOME]["corner"])
        self.brain.update(DT, self.room)
        self.brain.update(DT, self.room)
        self.assertTrue(self.brain.moving)
        self.assertEqual(self.brain.image().get_size(), mm.SIZE)
        calm = MiaoBrain(players=lambda: [], rng=random.Random(1))
        calm.place(HOME, mm.SPOTS[HOME]["hub"])
        calm.idle_left = 99
        calm.update(DT, self.room)
        self.assertFalse(calm.moving)

    def test_a_player_in_the_way_is_waited_for_never_pushed(self):
        b = MiaoBrain(players=lambda: [], rng=random.Random(1))
        b.place(HOME, (200, 232))
        body = Body(230, 232)
        room = open_room(HOME, [body])
        b.players = lambda: [body]
        b.path = [(300, 232)]
        b.state = "walk"
        b.update(DT, room)
        run(b, room, 1.0)
        self.assertEqual(body.x, 230.0)                                 # she did not move the player
        self.assertLess(b.x, 230)                                       # and did not walk through them
        run(b, room, mm.STUCK_GIVE_UP + 1)
        self.assertNotEqual(b.state, "walk")                            # she gave up the walk instead of being stuck for ever

    def test_she_walks_on_once_the_player_steps_away(self):
        b = MiaoBrain(players=lambda: [], rng=random.Random(1))
        b.place(HOME, (200, 232))
        body = Body(230, 232)
        room = open_room(HOME, [body])
        b.players = lambda: [body]
        b.path = [(300, 232)]
        b.state = "walk"
        run(b, room, 1.0)
        body.x, body.y = 230.0, 150.0
        run(b, room, 6.0)
        self.assertGreater(b.x, 260)

    def test_a_player_already_overlapping_her_does_not_freeze_her(self):
        b = MiaoBrain(players=lambda: [], rng=random.Random(1))
        b.place(HOME, (200, 232))
        body = Body(202, 232)
        room = open_room(HOME, [body])
        b.path = [(260, 232)]
        b.state = "walk"
        run(b, room, 1.0)
        self.assertGreater(b.x, 215)

    def test_a_blocked_route_is_replanned_not_walked_through(self):
        wall = pygame.Rect(236, 200, 12, 60)
        room = open_room(HOME)
        room.solids = room.solids + [wall]
        b = MiaoBrain(players=lambda: [], rng=random.Random(1))
        b.place(HOME, (200, 232))
        b.path = [(300, 232)]                                          # the straight line now crosses the new wall
        b.state = "walk"
        for _ in range(60 * 20):
            b.update(DT, room)
            self.assertEqual(mm.foot_rect(b.x, b.y).collidelist([wall]), -1)

    def test_scripted_walk_arrives_and_can_be_released(self):
        b = MiaoBrain(players=lambda: [], rng=random.Random(1))
        b.place(HOME, (92, 182))
        b.script_walk((184, 178))
        b.script_speed = 50.0
        self.assertFalse(b.arrived)
        run(b, self.room, 5.0)
        self.assertTrue(b.arrived)
        self.assertLess(math.hypot(b.x - 184, b.y - 178), 1.5)
        b.release()
        self.assertFalse(b.scripted)
        self.assertEqual(b.state, "idle")

    def test_a_scripted_cat_does_not_wander_off(self):
        b = MiaoBrain(players=lambda: [], rng=random.Random(1))
        b.place(HOME, (92, 182))
        b.scripted = True
        pos = b.pos
        run(b, self.room, 120)
        self.assertEqual(b.pos, pos)


class RoomTravelTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(session=LocalSession([PlayerProfile(profile_id="pa")]))
        self.addCleanup(self.game.quit)
        self.brain = self.game.hub.story.brain
        self.home = goto_room(self.game, HOME)
        for pl in self.home.players:
            pl.profile.claim_daily_reward()
        self.home.popup = None
        for _ in range(10):
            self.game.step([], DT)
        self.player = self.home.player
        self.player.x, self.player.y = 60, 120                     # out of her way

    def frames(self, n):
        for _ in range(n):
            self.game.step([], DT)

    def test_she_leaves_home_through_a_door_and_arrives_in_the_next_room(self):
        self.assertTrue(self.brain._head_for_room(self.home, ARCADE))
        self.assertEqual(self.brain.state, "leave")
        for _ in range(60 * 40):
            self.game.step([], DT)
            if self.brain.room_id == ARCADE:
                break
        self.assertEqual(self.brain.room_id, ARCADE)
        self.assertFalse(self.brain.is_in(HOME))

    def test_in_transit_she_is_in_no_room(self):
        self.assertTrue(self.brain._head_for_room(self.home, PLAZA))
        seen = False
        for _ in range(60 * 40):
            self.game.step([], DT)
            if self.brain.in_transit:
                seen = True
                self.assertFalse(self.brain.is_in(HOME) or self.brain.is_in(PLAZA))
                self.assertFalse(self.home.miao.present)
                self.assertEqual(self.home.miao.zone.size, (0, 0))
        self.assertTrue(seen)

    def test_she_walks_in_through_the_door_when_she_arrives_in_the_room_you_are_in(self):
        b = self.brain
        b.place(ARCADE, mm.SPOTS[ARCADE]["centre"])
        b.away_left = 0.0
        self.assertFalse(self.home.miao.present)
        entered = None
        for _ in range(60 * 60):
            self.game.step([], DT)
            if b.is_in(HOME):
                entered = b.pos
                break
        self.assertIsNotNone(entered)
        self.assertIn(entered, (mm.THRESHOLD["left"], mm.THRESHOLD["right"]))      # appears in a doorway, never mid-room
        self.assertEqual(b.state, "walk")
        self.frames(60 * 30)
        self.assertEqual(mm.foot_rect(b.x, b.y).collidelist(self.home.solids), -1)

    def test_anchor_brings_her_to_the_spot_even_from_another_room(self):
        b = self.brain
        self.game.hub.story.manager.finish_opening()                 # quest 1 is active: it pins her to HOME's hub spot
        b.place(PLAZA, mm.SPOTS[PLAZA]["walkway"])
        goal = mm.SPOTS[HOME]["hub"]
        for _ in range(60 * 150):
            self.game.step([], DT)
            if b.is_in(HOME) and math.hypot(b.x - goal[0], b.y - goal[1]) < 3 and b.state != "walk":
                break
        self.assertTrue(b.is_in(HOME))
        self.assertLess(math.hypot(b.x - goal[0], b.y - goal[1]), 3)

    def test_an_anchored_cat_stays_put(self):
        b = self.brain
        self.game.hub.story.manager.finish_opening()
        self.frames(60 * 90)
        self.assertTrue(b.is_in(HOME))
        goal = mm.SPOTS[HOME]["hub"]
        self.assertLess(math.hypot(b.x - goal[0], b.y - goal[1]), 3)

    def test_she_is_home_most_of_the_time_and_visits_now_and_then(self):
        brain = MiaoBrain(players=lambda: [], rng=random.Random(9))
        room = open_room(HOME)
        spent = {HOME: 0, ARCADE: 0, PLAZA: 0}
        for _ in range(60 * 60 * 20):                                  # twenty minutes with the player standing in HOME
            brain.update(DT, room)
            spent[brain.room_id] += 1
        total = sum(spent.values())
        self.assertGreater(spent[HOME] / total, 0.45)
        self.assertGreater(spent[ARCADE] + spent[PLAZA], 0)

    def test_on_room_enter_never_leaves_her_inside_a_player_or_a_solid(self):
        b = self.brain
        b.place(HOME, (self.player.x, self.player.y))                  # exactly on top of the player
        b.on_room_enter(self.home)
        self.assertEqual(mm.foot_rect(b.x, b.y).collidelist([p.feet for p in self.home.players]), -1)
        b.place(HOME, (60, 100))
        b.x, b.y = 150.0, 55.0                                         # inside the back wall
        b.on_room_enter(self.home)
        self.assertEqual(mm.foot_rect(b.x, b.y).collidelist(self.home.solids), -1)


class SpotTests(unittest.TestCase):
    """The hand-placed spots, checked against the real rooms (furniture, machines, doors)."""

    @classmethod
    def setUpClass(cls):
        cls.game = Game(session=LocalSession([PlayerProfile(profile_id="spots")]))
        cls.rooms = {rid: goto_room(cls.game, rid) for rid in (HOME, ARCADE, PLAZA)}
        for _ in range(5):
            cls.game.step([], DT)

    @classmethod
    def tearDownClass(cls):
        cls.game.quit()

    def test_every_spot_and_door_point_is_clear_of_solids(self):
        for rid, room in self.rooms.items():
            for name, (x, y) in mm.room_nodes(rid).items():
                self.assertTrue(mm.point_clear(x, y, list(room.solids), 1), (rid, name))

    def test_no_spot_sits_in_another_things_prompt_area_or_a_doorway_zone(self):
        for rid, room in self.rooms.items():
            for name, (x, y) in mm.SPOTS[rid].items():
                zone = mm.foot_rect(x, y).inflate(26, 24)
                for it in room.interactables:
                    if it is not room.miao:
                        self.assertFalse(it.zone.colliderect(zone), (rid, name, type(it).__name__))
                for area in room.keep_clear_areas:
                    self.assertFalse(area.colliderect(mm.foot_rect(x, y).inflate(6, 6)), (rid, name))

    def test_every_spot_reaches_every_other_and_every_door(self):
        for rid, room in self.rooms.items():
            nodes = mm.room_nodes(rid)
            pts = list(nodes.values())
            for a in mm.SPOTS[rid]:
                for b in list(mm.SPOTS[rid]) + [n for n in nodes if n.startswith("out_")]:
                    if a != b:
                        self.assertIsNotNone(mm.find_path(nodes[a], nodes[b], pts, list(room.solids)), (rid, a, b))

    def test_the_links_match_the_real_doorways(self):
        for room in self.rooms.values():
            for ex in room.exits:
                out_side, in_side = mm.LINKS[(room.room_id, ex.target)]
                self.assertEqual(out_side, ex.side)
                self.assertEqual(in_side, ex.entry)
        for (a, b), (out_side, in_side) in mm.LINKS.items():
            self.assertIn(out_side, mm.DOORS[a])
            self.assertIn(in_side, mm.DOORS[b])
        self.assertEqual(set(mm.NEIGHBOURS[HOME]), {ARCADE, PLAZA})

    def test_every_room_has_a_view_of_the_one_brain(self):
        brain = self.game.hub.story.brain
        for rid, room in self.rooms.items():
            self.assertIsInstance(room.miao, MiaoMeow)
            self.assertIs(room.miao.brain, brain)
            self.assertIn(room.miao, room.props)
            self.assertNotIn(room.miao, room.interactables)                 # the fixed list: she moves, so she is added only while here
            self.assertFalse(room.miao.solid)
        self.assertEqual(sum(brain.is_in(rid) for rid in self.rooms), 1)


class RoomTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(session=LocalSession([PlayerProfile(profile_id="pa")]))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.brain = self.story.brain
        self.room = goto_room(self.game, HOME)
        for pl in self.room.players:                              # (a fresh profile is offered the daily bonus in HOME)
            pl.profile.claim_daily_reward()
        self.room.popup = None
        self.brain.place(HOME, mm.SPOTS[HOME]["hub"])
        self.brain.idle_left = 999
        for _ in range(30):
            self.game.step([], DT)

    def frames(self, n):
        for _ in range(n):
            self.game.step([], DT)

    def near_her(self):
        p = self.room.player
        p.x, p.y = self.brain.x + 14, self.brain.y + 6
        self.frames(30)

    def test_the_view_draws_her_only_in_the_room_she_is_in(self):
        self.assertTrue(self.room.miao.present)
        other = self.game.hub.room(ARCADE)
        self.assertFalse(other.miao.present)
        surf = pygame.Surface((400, 300), pygame.SRCALPHA)
        other.miao.draw(surf)
        self.assertEqual(surf.get_bounding_rect().size, (0, 0))
        self.room.miao.draw(surf)
        self.assertGreater(surf.get_bounding_rect().w, 10)

    def test_walking_up_selects_her_with_a_talk_prompt_and_lights_the_coin(self):
        p = self.room.player
        p.x, p.y = 60, 120
        self.frames(60)
        self.assertEqual(self.brain.level, 0)
        self.assertIsNone(p.nearby)
        self.near_her()
        self.assertIs(p.nearby, self.room.miao)
        self.assertEqual(p.nearby.prompt_label, "TALK")
        self.assertEqual(self.brain.level, mm.LEVELS)
        p.x, p.y = 60, 120
        self.frames(90)
        self.assertIsNone(p.nearby)
        self.assertEqual(self.brain.level, 0)

    def test_she_is_pressable_only_while_she_is_in_the_room(self):
        self.assertIn(self.room.miao, self.room._candidates())
        self.brain.room_id = ARCADE
        self.assertNotIn(self.room.miao, self.room._candidates())
        self.assertEqual(self.room._candidates(), self.room.interactables)
        self.brain.room_id = HOME

    def test_arriving_in_a_room_is_quiet_even_if_she_is_close_to_where_you_appear(self):
        sounds = []
        self.brain.sound = sounds.append
        self.room.player.x, self.room.player.y = self.brain.x + 20, self.brain.y + 10
        self.brain.welcomed.clear()
        self.brain.near.clear()
        self.frames(30)
        self.assertEqual(sounds, [])

    def test_pressing_e_next_to_her_opens_a_conversation_and_she_stops(self):
        self.near_her()
        self.game.step([key_event(pygame.K_e)], DT)
        self.frames(60)
        self.assertIsNotNone(self.story.dialogue)
        self.assertIs(self.room.modal, self.story.dialogue)
        self.assertEqual(self.brain.state, "talk")
        self.assertIn("talk", [e for e, _ in self.brain.events])

    def test_she_blocks_the_player_but_never_traps_them(self):
        p = self.room.player
        p.x, p.y = self.brain.x - 40, self.brain.y
        self.frames(5)
        p.held.append(pygame.K_d)
        self.frames(120)
        self.assertLess(p.x, self.brain.x)                          # she is in the way: the player stops short of her
        p.held.clear()
        self.assertEqual(self.story.blockers(self.room, p)[0], self.brain.footprint())
        p.x, p.y = self.brain.x, self.brain.y                       # standing inside her box: free to walk out
        self.assertEqual(self.story.blockers(self.room, p), [])
        p.held.append(pygame.K_s)
        self.frames(60)
        self.assertGreater(p.y, self.brain.y + 3)

    def test_she_does_not_block_a_room_she_is_not_in(self):
        other = self.game.hub.room(ARCADE)
        self.assertEqual(self.story.blockers(other, other.player), [])

    def test_machines_still_work_and_prompts_stay_intact(self):
        room = goto_room(self.game, ARCADE)
        self.frames(10)
        machine = next(m for m in room.machines if isinstance(m, ArcadeMachine))
        p = room.player
        p.x, p.y = machine.rect.centerx, machine.zone.bottom - 2
        self.frames(30)
        self.assertIs(p.nearby, machine)

    def test_room_draws_with_her_walking_and_talking_without_error(self):
        surf = pygame.Surface((400, 300))
        self.brain._walk_to(self.room, mm.SPOTS[HOME]["corner"])
        for _ in range(30):
            self.game.step([], DT)
            self.room.draw(surf)
        self.brain.notify("talk")
        self.room.draw(surf)

    def test_mochi_and_the_prize_plaza_are_unchanged(self):
        prize = goto_room(self.game, PLAZA)
        self.assertTrue(hasattr(prize, "mochi"))
        self.frames(30)
        prize.draw(pygame.Surface((400, 300)))


class TwoPlayerTests(unittest.TestCase):
    def test_either_player_lights_the_coin_and_can_chat(self):
        a, b = PlayerProfile(profile_id="pa", display_name="A"), PlayerProfile(profile_id="pb", display_name="B")
        game = Game(session=LocalSession([a, b]))
        self.addCleanup(game.quit)
        room = goto_room(game, HOME)
        for pl in room.players:
            pl.profile.claim_daily_reward()
        room.popup = None
        brain = game.hub.story.brain
        brain.place(HOME, mm.SPOTS[HOME]["hub"])
        brain.idle_left = 999
        for _ in range(30):
            game.step([], DT)
        p1, p2 = room.players
        p1.x, p1.y = 60, 120
        p2.x, p2.y = brain.x + 14, brain.y + 6
        for _ in range(60):
            game.step([], DT)
        self.assertEqual(brain.level, mm.LEVELS)
        self.assertIs(p2.nearby, room.miao)
        self.assertIsNone(p1.nearby)
        p2.x, p2.y = 60, 135
        for _ in range(90):
            game.step([], DT)
        self.assertEqual(brain.level, 0)
        room.draw(pygame.Surface((400, 300)))


if __name__ == "__main__":
    unittest.main()
