"""Interaction prompts across the whole hub: they stay readable, never cover a
cabinet marquee or sign, tell P1 from P2, and the selected machine is marked.
Collision and interaction zones are not touched by any of this.

Run headless from this folder:   python -m unittest test_prompt_placement -v
"""
import os
import shutil
import tempfile
import unittest
from datetime import date

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from local_session import LocalSession  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import MACHINES, ROOM_IDS, VIEW_H, VIEW_W  # noqa: E402
from stations import Neon21Station  # noqa: E402
from ui import PromptBubble, selection_brackets  # noqa: E402

DT = 1 / 60
DAY1 = date(2026, 3, 10)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def overlap(a, b):
    c = a.clip(b)
    return c.w * c.h


class PromptBubbleUnitTests(unittest.TestCase):
    def bubble(self, anchor=(200, 150), label="PLAY NEON 21", **kw):
        b = PromptBubble(**kw)
        b.update(1.0, anchor, label)
        return b

    def test_with_nothing_in_the_way_it_floats_above_the_head_as_before(self):
        b = self.bubble()
        rect, tail_up = b.place([])
        self.assertEqual((rect.centerx, rect.bottom), (200, 150))
        self.assertFalse(tail_up)

    def test_machines_prefer_below_the_feet_and_the_tail_points_up_at_them(self):
        b = self.bubble()
        rect, tail_up = b.place([], below_first=True)
        self.assertEqual(rect.top, 150 + PromptBubble.HEAD_GAP + 4)
        self.assertTrue(tail_up)

    def test_it_moves_off_anything_it_would_cover(self):
        b = self.bubble()
        sign = pygame.Rect(150, 100, 100, 12)                 # a marquee right above the head
        rect, _ = b.place([sign])
        self.assertEqual(overlap(rect, sign), 0)
        wall_of_signs = [pygame.Rect(x, 100, 30, 12) for x in range(0, 400, 36)]
        rect, _ = b.place(wall_of_signs)
        self.assertEqual(sum(overlap(rect, r) for r in wall_of_signs), 0)

    def test_it_always_stays_inside_the_screen(self):
        for anchor in ((2, 8), (398, 8), (2, 295), (399, 299), (200, 5), (200, 400)):
            b = self.bubble(anchor)
            rect, _ = b.place([pygame.Rect(0, 0, 400, 300)])      # everything is covered: still on screen
            self.assertTrue(pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(rect), (anchor, rect))

    def test_the_spot_does_not_jump_around_while_nothing_changes(self):
        b = self.bubble()
        sign = [pygame.Rect(150, 100, 100, 12)]
        first = b.place(sign)
        for _ in range(60):
            b.update(DT, (200, 150), "PLAY NEON 21")
            self.assertEqual(b.place(sign), first)

    def test_p1_and_p2_bubbles_look_different(self):
        solo = PromptBubble(key="E")
        p1 = PromptBubble(key="E", tag="P1", accent=(80, 240, 255))
        p2 = PromptBubble(key="ENTER", tag="P2", accent=(255, 168, 70))
        images = []
        for b in (solo, p1, p2):
            b.update(1.0, (200, 100), "PLAY")
            images.append(pygame.image.tobytes(b.frames[0], "RGBA"))
        self.assertEqual(len(set(images)), 3)
        self.assertGreater(p1.frames[0].get_width(), solo.frames[0].get_width())     # carries its P1 chip
        self.assertGreater(p2.frames[0].get_width(), p1.frames[0].get_width())       # and the longer ENTER key

    def test_selection_brackets_stay_outside_the_machine(self):
        surf = pygame.Surface((120, 120), pygame.SRCALPHA)
        rect = pygame.Rect(40, 40, 28, 40)
        selection_brackets(surf, rect, (255, 168, 70), 0.0)
        self.assertEqual(sum(1 for x in range(rect.left, rect.right) for y in range(rect.top, rect.bottom)
                             if surf.get_at((x, y)).a), 0)                           # nothing drawn over the sprite
        self.assertGreater(sum(1 for x in range(120) for y in range(120) if surf.get_at((x, y)).a), 10)


class HubBase(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def room(self, rid):
        room = goto_room(self.game, rid)
        for cat in room.cats:
            cat.x, cat.y = -50.0, -50.0
        return room


class SoloHubTests(HubBase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.game = Game(save_path=os.path.join(self.dir, "s.json"), clock=GameClock(lambda: DAY1))
        self.frames(3, [key(pygame.K_ESCAPE)])
        self.frames(3, [key(pygame.K_ESCAPE)])

    def test_every_prompt_in_every_room_avoids_all_signs_and_the_selected_machine(self):
        checked = 0
        for rid in ROOM_IDS:
            room = self.room(rid)
            for target in room.interactables:
                p = room.player
                p.x, p.y = float(target.zone.centerx), float(target.zone.bottom - 2)
                self.frames(8)
                if p.nearby is not target:
                    continue
                avoid = room.prompt_avoid_rects()
                canvas = pygame.Surface((VIEW_W, VIEW_H))
                room.draw(canvas)
                rect = p.prompt.place(avoid + [target.rect], below_first=True)[0]
                for sign in avoid:
                    self.assertEqual(overlap(rect, sign), 0, f"{rid}/{target.prompt_label}: prompt {rect} covers {sign}")
                self.assertEqual(overlap(rect, target.rect), 0, f"{rid}/{target.prompt_label}")
                self.assertTrue(pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(rect))
                checked += 1
        self.assertGreaterEqual(checked, 11)             # 5 arcade + daily board + counter + garage + 3 lucky corner

    def test_the_prompt_that_is_drawn_is_the_prompt_that_was_checked(self):
        room = self.room("prize_plaza")
        target = next(p for p in room.props if isinstance(p, Neon21Station))
        p = room.player
        p.x, p.y = float(target.zone.centerx), float(target.zone.bottom - 2)
        self.frames(30)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        before = pygame.image.tobytes(canvas, "RGB")
        room.draw(canvas)
        used = p.prompt.draw(canvas, room.time, room.prompt_avoid_rects() + [target.rect], below_first=True)
        self.assertIsNotNone(used)
        for sign in room.prompt_avoid_rects():
            self.assertEqual(overlap(used, sign), 0)

    def test_lucky_corner_signs_include_the_plaque_the_cabinets_and_the_soon_bays(self):
        room = self.room("prize_plaza")
        avoid = room.prompt_avoid_rects()
        soon = [p for p in room.props if p.__class__.__name__ == "SoonStation"]
        plaque = next(p for p in room.props if p.__class__.__name__ == "LuckySign")
        self.assertIn(plaque.sign_rect, avoid)
        for s in soon:
            self.assertTrue(any(r.x == s.rect.x and r.y == s.rect.y for r in avoid))

    def test_prompts_do_not_change_collision_or_interaction(self):
        room = self.room("prize_plaza")
        solids = [pygame.Rect(r) for r in room.solids]
        zones = [pygame.Rect(t.zone) for t in room.interactables]
        for target in room.interactables:
            room.player.x, room.player.y = float(target.zone.centerx), float(target.zone.bottom - 2)
            self.frames(10)
            self.assertIs(room.player.nearby, target)
        self.assertEqual([pygame.Rect(r) for r in room.solids], solids)
        self.assertEqual([pygame.Rect(t.zone) for t in room.interactables], zones)

    def test_machines_get_selection_brackets_only_while_selected(self):
        room = self.room("prize_plaza")
        target = next(p for p in room.props if isinstance(p, Neon21Station))
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        room.player.x, room.player.y = 60.0, 230.0
        self.frames(30)
        room.draw(canvas)
        away = pygame.image.tobytes(canvas.subsurface(target.rect.inflate(8, 8)), "RGB")
        room.player.x, room.player.y = float(target.zone.centerx), float(target.zone.bottom - 2)
        self.frames(30)
        room.draw(canvas)
        near = pygame.image.tobytes(canvas.subsurface(target.rect.inflate(8, 8)), "RGB")
        self.assertNotEqual(away, near)

    def test_the_prompt_text_is_unchanged_for_every_machine(self):
        room = self.room("arcade_floor")
        labels = {m.prompt_label for m in room.machines}
        self.assertEqual(labels, {"PLAY"})
        lucky = self.room("prize_plaza")
        self.assertEqual(sorted(t.prompt_label for t in lucky.interactables if hasattr(t, "kind")),
                         ["PLAY HI-LO", "PLAY NEON 21", "PLAY SPIN"])

    def test_cat_volleyball_keeps_its_player_facing_name(self):
        machine = next(m for m in MACHINES if m["id"] == "pixel_volleyball")
        self.assertEqual((machine["name"], machine["marquee"]), ("Cat Volleyball", "CAT VOLLEYBALL"))
        room = self.room("arcade_floor")
        found = next(m for m in room.machines if m.id == "pixel_volleyball")
        self.assertEqual(found.name, "Cat Volleyball")
        p = room.player
        p.x, p.y = float(found.zone.centerx), float(found.zone.bottom - 2)
        self.frames(8)
        self.frames(30, [key(pygame.K_e)])
        self.frames(20)
        self.assertIsNotNone(room.dialogue)
        self.assertIn("CAT VOLLEYBALL", room.dialogue.title.upper())


class TwoPlayerHubTests(HubBase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.manager = ProfileManager(os.path.join(self.dir, "saves"), clock=GameClock(lambda: DAY1))
        a, b = self.manager.create_profile("Alice"), self.manager.create_profile("Bob")
        self.game = Game(session=LocalSession([a, b]))
        self.p1, self.p2 = self.game.session.players
        for _ in range(3):
            self.frames(3, [key(pygame.K_ESCAPE)])

    def stand(self, player, target):
        player.avatar.x, player.avatar.y = float(target.zone.centerx), float(target.zone.bottom - 2)

    def test_two_players_at_one_machine_get_separate_non_overlapping_prompts(self):
        room = self.room("prize_plaza")
        target = next(p for p in room.props if isinstance(p, Neon21Station))
        self.stand(self.p1, target)
        self.stand(self.p2, target)
        self.p2.avatar.x += 5
        self.frames(30)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        room.draw(canvas)
        avoid = room.prompt_avoid_rects()
        rects = []
        for p in (self.p1, self.p2):
            used = p.avatar.prompt.draw(canvas, room.time, avoid + [target.rect] + rects, below_first=True)
            self.assertIsNotNone(used)
            rects.append(used)
        self.assertEqual(overlap(rects[0], rects[1]), 0)
        for r in rects:
            for sign in avoid:
                self.assertEqual(overlap(r, sign), 0)
        self.assertEqual((self.p1.avatar.prompt.tag, self.p2.avatar.prompt.tag), ("P1", "P2"))
        self.assertNotEqual(self.p1.avatar.prompt.accent, self.p2.avatar.prompt.accent)

    def test_p1_at_spin_and_p2_at_hilo_each_keep_clear_of_both_cabinets_signs(self):
        room = self.room("prize_plaza")
        cabinets = sorted((p for p in room.props if hasattr(p, "kind")), key=lambda p: p.rect.x)
        self.stand(self.p1, cabinets[0])
        self.stand(self.p2, cabinets[1])
        self.frames(30)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        room.draw(canvas)
        self.assertIs(self.p1.avatar.nearby, cabinets[0])
        self.assertIs(self.p2.avatar.nearby, cabinets[1])
        avoid = room.prompt_avoid_rects()
        used = []
        for p, cab in ((self.p1, cabinets[0]), (self.p2, cabinets[1])):
            r = p.avatar.prompt.draw(canvas, room.time, avoid + [cab.rect] + used, below_first=True)
            used.append(r)
            for sign in avoid:
                self.assertEqual(overlap(r, sign), 0)
        self.assertEqual(overlap(used[0], used[1]), 0)

    def test_each_player_still_launches_only_with_their_own_interact_key(self):
        room = self.room("prize_plaza")
        target = next(p for p in room.props if isinstance(p, Neon21Station))
        self.stand(self.p1, target)
        self.p2.avatar.x, self.p2.avatar.y = 60.0, 230.0
        self.frames(10)
        self.frames(30, [key(pygame.K_RETURN)])             # P2's key while P1 stands at the machine
        self.frames(30)
        self.assertIs(self.game.scenes.current, room)
        self.frames(30, [key(pygame.K_e)])
        self.frames(50)
        self.assertEqual(type(self.game.scenes.current).__name__, "Neon21Scene")
        self.assertIs(self.game.scenes.current.player, self.p1)


if __name__ == "__main__":
    unittest.main()
