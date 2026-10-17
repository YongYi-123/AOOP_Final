"""Tests for the CAT CAPSULE / RETRO CAPSULE machines in Prize Plaza: pricing, the Ticket
spend, the prize, duplicates, P1/P2 ownership and the machines in the room.

Run headless from this folder:   python -m unittest test_capsule -v
"""
import os
import random
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from capsule import CAPSULE_MACHINES, CAT, RETRO, CapsuleService  # noqa: E402
from capsule_ui import DROP_TIME, INPUT_DELAY, OPEN_TIME, CapsuleScene  # noqa: E402
from game import Game  # noqa: E402
from item_registry import COLLECTIBLE, ITEM_REGISTRY  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from plaza_stations import CapsuleStation  # noqa: E402
from rewards import ItemGrantResult, RewardService  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class Picks:
    """A stand-in random generator that always picks the prize with a given item id."""

    def __init__(self, *item_ids):
        self.ids = list(item_ids)

    def choices(self, pool, weights=None):
        wanted = self.ids.pop(0) if len(self.ids) > 1 else self.ids[0]
        return [next(p for p in pool if p.item_id == wanted)]


class CatalogTests(unittest.TestCase):
    def test_prices_are_fifteen_and_thirty_tickets(self):
        self.assertEqual(CAPSULE_MACHINES[CAT].cost, 15)
        self.assertEqual(CAPSULE_MACHINES[RETRO].cost, 30)
        self.assertEqual(CAPSULE_MACHINES[CAT].name, "CAT CAPSULE")
        self.assertEqual(CAPSULE_MACHINES[RETRO].name, "RETRO CAPSULE")

    def test_every_prize_is_a_real_item_and_nothing_is_currency_or_a_coupon(self):
        for spec in CAPSULE_MACHINES.values():
            ids = [p.item_id for p in spec.prizes]
            self.assertEqual(len(ids), len(set(ids)), spec.name)
            for prize in spec.prizes:
                with self.subTest(machine=spec.name, item=prize.item_id):
                    definition = ITEM_REGISTRY.get(prize.item_id)
                    self.assertIsNotNone(definition)
                    self.assertGreater(prize.weight, 0)
                    self.assertNotEqual(prize.item_id, "free_play_coupon")
                    self.assertNotEqual(definition.category, "CONSUMABLE")

    def test_the_machines_share_no_capsule_only_prize(self):
        cat = {p.item_id for p in CAPSULE_MACHINES[CAT].prizes}
        retro = {p.item_id for p in CAPSULE_MACHINES[RETRO].prizes}
        self.assertFalse(cat & retro)
        self.assertTrue(any(i.startswith("cat_") for i in cat))
        self.assertTrue(any(i.startswith("retro_") for i in retro))

    def test_capsule_collectibles_are_stackable_collectibles(self):
        for spec in CAPSULE_MACHINES.values():
            for prize in spec.prizes:
                d = ITEM_REGISTRY.get(prize.item_id)
                if prize.item_id.startswith(("cat_paw", "cat_bell", "retro_pixel", "retro_cartridge")):
                    self.assertTrue(d.stackable)
                    self.assertEqual(d.category, COLLECTIBLE)


class PullTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(tickets=100, tokens=7)
        self.saves = 0
        self.p.subscribe_save(self._count_save)

    def _count_save(self):
        self.saves += 1

    def test_a_pull_charges_the_price_once_and_grants_one_prize(self):
        svc = CapsuleService(self.p, rng=Picks("cat_paw_sticker"))
        r = svc.pull(CAT)
        self.assertTrue(r.success)
        self.assertEqual(r.item_id, "cat_paw_sticker")
        self.assertEqual(r.cost, 15)
        self.assertEqual(self.p.tickets, 85)
        self.assertEqual(self.p.tokens, 7)                           # Tokens are never touched
        self.assertEqual(self.p.inventory.get_quantity("cat_paw_sticker"), 1)
        self.assertEqual(sum(self.p.inventory.to_dict().values()), 1)
        self.assertEqual(self.p.lifetime_tickets_earned, 0)          # a pull never counts as earning Tickets

    def test_retro_costs_thirty(self):
        r = CapsuleService(self.p, rng=Picks("retro_cartridge")).pull(RETRO)
        self.assertTrue(r.success)
        self.assertEqual(self.p.tickets, 70)

    def test_one_pull_is_one_save(self):
        CapsuleService(self.p, rng=Picks("cat_paw_sticker")).pull(CAT)
        self.assertEqual(self.saves, 1)

    def test_not_enough_tickets_changes_nothing(self):
        poor = PlayerProfile(tickets=14)
        r = CapsuleService(poor).pull(CAT)
        self.assertFalse(r.success)
        self.assertEqual(r.code, "need_tickets")
        self.assertEqual(r.cost, 0)
        self.assertEqual(poor.tickets, 14)
        self.assertEqual(poor.inventory.to_dict(), {})

    def test_exactly_the_price_is_enough(self):
        p = PlayerProfile(tickets=15)
        self.assertTrue(CapsuleService(p).pull(CAT).success)
        self.assertEqual(p.tickets, 0)
        self.assertFalse(CapsuleService(p).pull(CAT).success)
        self.assertEqual(p.tickets, 0)

    def test_unknown_machine_changes_nothing(self):
        r = CapsuleService(self.p).pull("nope")
        self.assertFalse(r.success)
        self.assertEqual(self.p.tickets, 100)

    def test_a_prize_that_cannot_be_granted_refunds_the_tickets(self):
        failed = ItemGrantResult(False, "cat_paw_sticker", 1, 0, "stack_full")
        with mock.patch.object(RewardService, "grant_item", return_value=failed):
            r = CapsuleService(self.p, rng=Picks("cat_paw_sticker")).pull(CAT)
        self.assertFalse(r.success)
        self.assertEqual(r.code, "failed")
        self.assertEqual(self.p.tickets, 100)
        self.assertEqual(self.p.inventory.to_dict(), {})

    def test_the_prize_comes_from_the_machines_own_pool(self):
        cat = {p.item_id for p in CAPSULE_MACHINES[CAT].prizes}
        retro = {p.item_id for p in CAPSULE_MACHINES[RETRO].prizes}
        rich = PlayerProfile(tickets=100000)
        svc = CapsuleService(rich, rng=random.Random(5))
        for _ in range(60):
            self.assertIn(svc.pull(CAT).item_id, cat)
            self.assertIn(svc.pull(RETRO).item_id, retro)


class DuplicateTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(tickets=500)

    def test_first_copy_is_new_second_is_a_counted_duplicate(self):
        svc = CapsuleService(self.p, rng=Picks("cat_paw_sticker"))
        first = svc.pull(CAT)
        self.assertFalse(first.duplicate)
        self.assertEqual((first.count, first.message), (1, "NEW!"))
        second = svc.pull(CAT)
        self.assertTrue(second.duplicate)
        self.assertEqual(second.count, 2)
        self.assertIn("DUPLICATE", second.message)
        self.assertIn("X2", second.message)
        self.assertEqual(self.p.inventory.get_quantity("cat_paw_sticker"), 2)
        self.assertEqual(self.p.tickets, 470)                         # a duplicate still costs the price, once

    def test_a_single_copy_item_you_own_is_never_pulled_again(self):
        self.p = PlayerProfile(tickets=100000)
        self.p.inventory.add_item("star_hair_clip")
        pool = {pr.item_id for pr in CapsuleService(self.p).available(CAT)}
        self.assertNotIn("star_hair_clip", pool)
        svc = CapsuleService(self.p, rng=random.Random(1))
        for _ in range(80):
            r = svc.pull(CAT)
            self.assertTrue(r.success)
            if not ITEM_REGISTRY.get(r.item_id).stackable:
                self.assertFalse(r.duplicate)                         # unique prizes only ever arrive as NEW
                self.assertEqual(r.count, 1)

    def test_owning_every_single_copy_prize_still_leaves_the_stackable_ones(self):
        for spec in CAPSULE_MACHINES.values():
            for prize in spec.prizes:
                d = ITEM_REGISTRY.get(prize.item_id)
                if not d.stackable:
                    self.p.inventory.add_item(prize.item_id)
        for kind in (CAT, RETRO):
            svc = CapsuleService(self.p)
            self.assertTrue(svc.available(kind))
            self.assertTrue(all(ITEM_REGISTRY.get(pr.item_id).stackable for pr in svc.available(kind)))
            self.assertTrue(svc.pull(kind).success)

    def test_a_full_stack_is_skipped_and_nothing_breaks(self):
        d = ITEM_REGISTRY.get("cat_paw_sticker")
        self.p.inventory.add_item("cat_paw_sticker", d.limit)
        svc = CapsuleService(self.p, rng=random.Random(2))
        self.assertNotIn("cat_paw_sticker", {pr.item_id for pr in svc.available(CAT)})
        for _ in range(30):
            self.assertTrue(svc.pull(CAT).success)
        self.assertEqual(self.p.inventory.get_quantity("cat_paw_sticker"), d.limit)


class IsolationTests(unittest.TestCase):
    def test_a_pull_only_touches_the_pulling_profile(self):
        a, b = PlayerProfile(tickets=100), PlayerProfile(tickets=100)
        CapsuleService(a, rng=Picks("cat_bell_charm")).pull(CAT)
        self.assertEqual((a.tickets, b.tickets), (85, 100))
        self.assertEqual(b.inventory.to_dict(), {})

    def test_the_prize_survives_a_save_round_trip(self):
        p = PlayerProfile(tickets=100)
        CapsuleService(p, rng=Picks("retro_pixel_heart")).pull(RETRO)
        back = PlayerProfile.from_dict(p.to_dict())
        self.assertEqual(back.tickets, 70)
        self.assertEqual(back.inventory.get_quantity("retro_pixel_heart"), 1)


class RoomBase(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="cap_a", tickets=200), PlayerProfile(profile_id="cap_b", tickets=200)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "prize_plaza")
        for cat in self.room.cats:
            cat.x, cat.y = -50.0, -50.0

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k):
        self.game.step([key_event(k)], DT)

    def machine(self, kind):
        return next(p for p in self.room.props if isinstance(p, CapsuleStation) and p.capsule_kind == kind)

    def stand_at(self, index, target):
        avatar = self.room.players[index]
        avatar.x, avatar.y = float(target.zone.centerx), float(target.zone.bottom - 2)
        self.frames(6)
        self.assertIs(avatar.nearby, target)

    def finish_reveal(self, scene):
        for _ in range(int((INPUT_DELAY + DROP_TIME + OPEN_TIME) * 60) + 10):
            self.game.step([], DT)


class RoomTests(RoomBase):
    def test_both_capsule_machines_form_the_upper_right_capsule_corner_above_the_lucky_corner(self):
        from prize_plaza import CAPSULE_RUG, LUCKY_POS
        cat, retro = self.machine(CAT), self.machine(RETRO)
        self.assertEqual((cat.prompt_label, retro.prompt_label), ("CAT CAPSULE", "RETRO CAPSULE"))
        self.assertLess(cat.rect.x, retro.rect.x)
        rug = pygame.Rect(CAPSULE_RUG)
        for m in (cat, retro):
            self.assertTrue(rug.contains(m.rect), m.prompt_label)
            self.assertGreater(m.rect.centerx, VIEW_W // 2)                       # right half of the room
            self.assertLessEqual(m.rect.bottom, LUCKY_POS[1] - 20)               # entirely above the Lucky Corner's rug

    def test_e_on_each_machine_opens_its_own_screen_for_p1(self):
        for kind in (CAT, RETRO):
            self.stand_at(0, self.machine(kind))
            self.key(pygame.K_e)
            self.frames(40)
            scene = self.game.scenes.current
            self.assertIsInstance(scene, CapsuleScene)
            self.assertEqual(scene.kind, kind)
            self.assertIs(scene.owner, self.game.session.primary)
            scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
            self.key(pygame.K_ESCAPE)
            self.frames(40)
            self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual([p.tickets for p in self.profiles], [200, 200])      # opening is free

    def test_p2_opening_a_machine_pulls_with_p2_tickets_only(self):
        self.stand_at(1, self.machine(CAT))
        self.key(pygame.K_RETURN)
        self.frames(40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, CapsuleScene)
        self.assertIs(scene.owner, self.game.session.players[1])
        self.assertIs(scene.profile, self.profiles[1])
        self.finish_reveal(scene)
        self.key(pygame.K_RETURN)
        self.assertEqual((self.profiles[0].tickets, self.profiles[1].tickets), (200, 185))
        self.assertEqual(self.profiles[0].inventory.to_dict(), {})
        self.assertEqual(sum(self.profiles[1].inventory.to_dict().values()), 1)

    def test_the_other_players_keys_cannot_pull(self):
        self.stand_at(0, self.machine(RETRO))
        self.key(pygame.K_e)
        self.frames(40)
        scene = self.game.scenes.current
        self.finish_reveal(scene)
        for k in (pygame.K_RETURN, pygame.K_KP_ENTER):                         # P2's interact keys
            self.key(k)
        self.assertEqual([p.tickets for p in self.profiles], [200, 200])
        self.assertEqual(scene.phase, "idle")

    def test_a_double_press_pulls_only_once_and_the_screen_locks_while_it_plays(self):
        self.stand_at(0, self.machine(CAT))
        self.key(pygame.K_e)
        self.frames(40)
        scene = self.game.scenes.current
        self.key(pygame.K_e)                                                   # inside the opening delay: ignored
        self.assertEqual(self.profiles[0].tickets, 200)
        self.finish_reveal(scene)
        self.key(pygame.K_e)
        self.key(pygame.K_e)                                                   # mid-animation: ignored
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[0].tickets, 185)
        self.finish_reveal(scene)
        self.key(pygame.K_e)                                                   # a new capsule after it settled
        self.assertEqual(self.profiles[0].tickets, 170)

    def test_not_enough_tickets_shows_a_message_and_takes_nothing(self):
        self.profiles[0].spend_tickets(190)
        self.stand_at(0, self.machine(RETRO))
        self.key(pygame.K_e)
        self.frames(40)
        scene = self.game.scenes.current
        self.finish_reveal(scene)
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[0].tickets, 10)
        self.assertIn("NEED 20", scene.message)
        self.assertIsNone(scene.result)
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))

    def test_the_screen_reports_new_then_duplicate(self):
        scene = CapsuleScene(self.game, self.game.session.primary, CAT, rng=Picks("cat_bell_charm"))
        scene.lock = 0
        scene.pull()
        scene.update(DROP_TIME + 0.01)
        scene.update(OPEN_TIME + 0.01)
        self.assertEqual(scene.phase, "shown")
        self.assertIn("NEW", scene.message)
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        scene.lock = 0
        scene.pull()
        scene.update(DROP_TIME + 0.01)
        scene.update(OPEN_TIME + 0.01)
        self.assertIn("DUPLICATE", scene.message)
        self.assertIn("X2", scene.message)
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertEqual(self.profiles[0].tickets, 170)

    def test_both_machines_draw_in_every_animation_phase(self):
        surf = pygame.Surface((VIEW_W, VIEW_H))
        for kind in (CAT, RETRO):
            scene = CapsuleScene(self.game, self.game.session.primary, kind)
            scene.draw(surf)
            scene.lock = 0
            scene.pull()
            for _ in range(80):
                scene.update(DT)
                scene.draw(surf)
            scene.on_action("down")
            scene.draw(surf)


if __name__ == "__main__":
    unittest.main()
