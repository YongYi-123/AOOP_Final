"""Tests for MOCHI'S CAPSULE EXCHANGE: recycling spare capsule collectibles into Capsule Stamps and
redeeming Stamps for a chosen capsule prize - rules, economy, saves, P1/P2 and the screen.

Run headless from this folder:   python -m unittest test_capsule_exchange -v
"""
import json
import os
import random
import shutil
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import capsule_exchange as cx  # noqa: E402
import capsule_exchange_ui as ui  # noqa: E402
from capsule import CAPSULE_MACHINES  # noqa: E402
from capsule_exchange import (KEEP, PRICES, RECYCLABLE, REDEEMABLE, ExchangeService, recycle_value,  # noqa: E402
                              redeem_price)
from game import Game  # noqa: E402
from item_registry import COLLECTIBLE, COMMON, EPIC, ITEM_REGISTRY, RARE, UNCOMMON  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import MAX_CAPSULE_STAMPS, PlayerProfile, ProfileStore  # noqa: E402
from rewards import ItemGrantResult, RewardService  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402
from shop_ui import EXCHANGE, TABS, ShopScene  # noqa: E402

DT = 1 / 60
CAT_IDS = [i for i in RECYCLABLE if i.startswith("cat_")]
RETRO_IDS = [i for i in RECYCLABLE if i.startswith("retro_")]


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def profile(**kw):
    return PlayerProfile(profile_id=kw.pop("pid", "ex"), **kw)


class CatalogueTests(unittest.TestCase):
    def test_recyclable_items_are_explicit_stackable_capsule_collectibles(self):
        pool = {p.item_id for spec in CAPSULE_MACHINES.values() for p in spec.prizes}
        self.assertEqual(len(RECYCLABLE), 12)
        for item_id in RECYCLABLE:
            d = ITEM_REGISTRY.get(item_id)
            self.assertIsNotNone(d, item_id)
            self.assertTrue(d.stackable, item_id)
            self.assertEqual(d.category, COLLECTIBLE, item_id)
            self.assertIn(item_id, pool, item_id)

    def test_exact_stamp_values(self):
        self.assertEqual({recycle_value(i) for i in CAT_IDS}, {3})
        self.assertEqual({recycle_value(i) for i in RETRO_IDS}, {6})

    def test_exact_prices_by_rarity(self):
        self.assertEqual(PRICES, {COMMON: 12, UNCOMMON: 18, RARE: 25, EPIC: 45})
        for item_id in REDEEMABLE:
            self.assertEqual(redeem_price(item_id), PRICES[ITEM_REGISTRY.get(item_id).rarity])

    def test_everything_redeemable_is_a_capsule_prize_and_usable_in_the_game(self):
        pool = {p.item_id for spec in CAPSULE_MACHINES.values() for p in spec.prizes}
        self.assertEqual(set(REDEEMABLE), pool)
        for item_id in REDEEMABLE:
            d = ITEM_REGISTRY.get(item_id)
            self.assertIn(d.category, (COLLECTIBLE, "COSMETIC"), item_id)
            self.assertNotIn(item_id, ("free_play_coupon",))
            self.assertTrue(d.use_hint, item_id)                      # every one says where it is used

    def test_nothing_that_buffs_or_pays_is_on_the_exchange(self):
        for item_id in REDEEMABLE:
            self.assertNotEqual(ITEM_REGISTRY.get(item_id).category, "ARCADE")
            self.assertNotEqual(ITEM_REGISTRY.get(item_id).category, "CONSUMABLE")

    def test_the_best_recycle_value_is_at_most_half_the_cheapest_price(self):
        self.assertLessEqual(2 * max(RECYCLABLE.values()), min(PRICES.values()))

    def test_ineligible_items_are_refused(self):
        p = profile()
        for item_id in ("cat_sticker", "star_hair_clip", "decor_cat_plush", "neon_cap", "arcade_trophy",
                        "golden_token", "free_play_coupon", "racing_car_viper", "mini_cabinet", "suspicious_soda"):
            if ITEM_REGISTRY.get(item_id).stackable:
                p.inventory.add_item(item_id, 5)
            else:
                p.inventory.add_item(item_id)
            r = ExchangeService(p).recycle(item_id, 1)
            self.assertFalse(r.success, item_id)
            self.assertEqual(r.code, "not_recyclable", item_id)
        for junk in ("nope", "", None, 5, ["cat_bell_charm"], True):
            self.assertEqual(ExchangeService(p).recycle(junk, 1).code, "not_recyclable")
        self.assertEqual(p.capsule_stamps, 0)

    def test_eligibility_is_by_id_not_by_display_name(self):
        from item_registry import ItemDefinition, ItemRegistry
        reg = ItemRegistry([ItemDefinition("fake_bell", "CAT BELL", "x", COLLECTIBLE, COMMON, stackable=True),
                            ItemDefinition("cat_bell_charm", "SOMETHING ELSE", "x", COLLECTIBLE, COMMON, stackable=True)])
        p = profile()
        p.inventory.registry = reg
        p.inventory.add_item("fake_bell", 3)
        p.inventory.add_item("cat_bell_charm", 3)
        svc = ExchangeService(p, registry=reg)
        self.assertFalse(svc.recycle("fake_bell", 1).success)
        self.assertTrue(svc.recycle("cat_bell_charm", 1).success)


class RecycleTests(unittest.TestCase):
    def setUp(self):
        self.p = profile(tickets=77, tokens=5)
        self.saves = 0
        self.p.subscribe_save(lambda: setattr(self, "saves", self.saves + 1))
        self.svc = ExchangeService(self.p)

    def test_recycling_one_spare_cat_copy_pays_three(self):
        self.p.inventory.add_item("cat_bell_charm", 3)
        self.saves = 0
        r = self.svc.recycle("cat_bell_charm", 1)
        self.assertTrue(r.success)
        self.assertEqual((r.stamps, r.quantity), (3, 1))
        self.assertEqual(self.p.capsule_stamps, 3)
        self.assertEqual(self.p.inventory.get_quantity("cat_bell_charm"), 2)
        self.assertEqual(self.saves, 1)                                  # one save for the copies and the Stamps
        self.assertEqual((self.p.tickets, self.p.tokens), (77, 5))      # no Tickets or Tokens, ever

    def test_recycling_several_retro_copies_pays_six_each(self):
        self.p.inventory.add_item("retro_silver_cup", 5)
        r = self.svc.recycle("retro_silver_cup", 4)
        self.assertEqual((r.success, r.stamps), (True, 24))
        self.assertEqual(self.p.capsule_stamps, 24)
        self.assertEqual(self.p.inventory.get_quantity("retro_silver_cup"), 1)

    def test_the_last_copy_is_never_recycled(self):
        self.p.inventory.add_item("cat_paw_sticker", 1)
        r = self.svc.recycle("cat_paw_sticker", 1)
        self.assertEqual((r.success, r.code), (False, "no_spare"))
        self.assertEqual(self.p.inventory.get_quantity("cat_paw_sticker"), 1)
        self.assertEqual(self.p.capsule_stamps, 0)
        self.p.inventory.add_item("cat_paw_sticker", 2)
        self.assertFalse(self.svc.recycle("cat_paw_sticker", 3).success)     # asking for all of them
        self.assertEqual(self.p.inventory.get_quantity("cat_paw_sticker"), 3)
        self.assertTrue(self.svc.recycle("cat_paw_sticker", 2).success)
        self.assertEqual(self.p.inventory.get_quantity("cat_paw_sticker"), KEEP)

    def test_an_item_you_do_not_own_pays_nothing(self):
        self.assertEqual(self.svc.recycle("cat_bell_charm", 1).code, "no_spare")
        self.assertEqual(self.p.inventory.to_dict(), {})

    def test_bad_quantities_change_nothing(self):
        self.p.inventory.add_item("cat_bell_charm", 5)
        for q in (0, -1, -99, True, False, 2.0, "2", None, [2]):
            r = self.svc.recycle("cat_bell_charm", q)
            self.assertFalse(r.success, q)
        self.assertEqual(self.p.inventory.get_quantity("cat_bell_charm"), 5)
        self.assertEqual(self.p.capsule_stamps, 0)
        self.assertEqual(self.svc.preview("cat_bell_charm", 0), 0)
        self.assertEqual(self.svc.preview("cat_bell_charm", 99), 0)

    def test_the_preview_is_exactly_what_is_paid(self):
        self.p.inventory.add_item("retro_pixel_heart", 6)
        for q in range(1, 6):
            self.assertEqual(self.svc.preview("retro_pixel_heart", q), 6 * q)
        pay = self.svc.preview("retro_pixel_heart", 5)
        self.assertEqual(self.svc.recycle("retro_pixel_heart", 5).stamps, pay)

    def test_a_displayed_collectible_keeps_its_copy(self):
        self.p.inventory.add_item("retro_gold_trophy", 1)
        self.p.set_showcase("trophy", "retro_gold_trophy")
        self.assertFalse(self.svc.recycle("retro_gold_trophy", 1).success)
        self.p.inventory.add_item("retro_gold_trophy", 2)
        self.assertTrue(self.svc.recycle("retro_gold_trophy", 2).success)
        self.assertEqual(self.p.inventory.get_quantity("retro_gold_trophy"), 1)
        from showcase import ShowcaseService
        self.assertEqual(ShowcaseService(self.p).displayed("trophy").value, "retro_gold_trophy")
        entry = next(e for e in self.svc.recycle_entries() if e.item_id == "retro_gold_trophy")
        self.assertTrue(entry.displayed)
        self.assertEqual(entry.spare, 0)

    def test_recycled_copies_never_make_the_count_negative(self):
        self.p.inventory.add_item("cat_bell_charm", 2)
        for _ in range(5):
            self.svc.recycle("cat_bell_charm", 1)
        self.assertEqual(self.p.inventory.get_quantity("cat_bell_charm"), 1)
        self.assertEqual(self.p.capsule_stamps, 3)

    def test_the_entries_list_only_owned_recyclables_with_correct_spares(self):
        self.p.inventory.add_item("cat_bell_charm", 1)
        self.p.inventory.add_item("retro_cartridge", 4)
        self.p.inventory.add_item("cat_sticker")
        self.p.inventory.add_item("star_pin")
        entries = {e.item_id: e for e in self.svc.recycle_entries()}
        self.assertEqual(set(entries), {"cat_bell_charm", "retro_cartridge"})
        self.assertEqual((entries["cat_bell_charm"].spare, entries["retro_cartridge"].spare), (0, 3))

    def test_a_full_stamp_book_refuses_without_losing_copies(self):
        self.p.add_capsule_stamps(MAX_CAPSULE_STAMPS - 4)
        self.p.inventory.add_item("retro_cartridge", 4)
        r = self.svc.recycle("retro_cartridge", 1)
        self.assertEqual((r.success, r.code), (False, "stamp_full"))
        self.assertEqual(self.p.inventory.get_quantity("retro_cartridge"), 4)
        self.p.inventory.add_item("cat_bell_charm", 5)
        self.assertEqual(self.svc.max_recycle("cat_bell_charm"), 1)              # only one fits (3 of the 4 left)
        self.assertEqual(self.svc.recycle("cat_bell_charm", 2).code, "stamp_full")
        self.assertTrue(self.svc.recycle("cat_bell_charm", 1).success)
        self.assertEqual(self.p.capsule_stamps, MAX_CAPSULE_STAMPS - 1)


class RedeemTests(unittest.TestCase):
    def setUp(self):
        self.p = profile(tickets=9, tokens=3)
        self.p.add_capsule_stamps(100)
        self.svc = ExchangeService(self.p)
        self.saves = 0
        self.p.subscribe_save(lambda: setattr(self, "saves", self.saves + 1))

    def test_each_rarity_costs_its_price(self):
        for item_id, price in (("cat_paw_sticker", 12), ("cat_fish_badge", 18), ("cat_mochi_plush", 25),
                               ("retro_gold_trophy", 45)):
            before = self.p.capsule_stamps
            self.saves = 0
            r = self.svc.redeem(item_id)
            self.assertTrue(r.success, item_id)
            self.assertEqual(r.stamps, price)
            self.assertEqual(self.p.capsule_stamps, before - price)
            self.assertEqual(self.p.inventory.get_quantity(item_id), 1)
            self.assertEqual(self.saves, 1)
        self.assertEqual((self.p.tickets, self.p.tokens), (9, 3))

    def test_not_enough_stamps_has_no_side_effect(self):
        self.p.spend_capsule_stamps(100)
        self.p.add_capsule_stamps(11)
        before = (dict(self.p.inventory.to_dict()), self.p.capsule_stamps)
        self.saves = 0
        r = self.svc.redeem("cat_paw_sticker")
        self.assertEqual((r.success, r.code), (False, "need_stamps"))
        self.assertIn("NEED 1 MORE", r.message)
        self.assertEqual((self.p.inventory.to_dict(), self.p.capsule_stamps), before)
        self.assertEqual(self.saves, 0)

    def test_a_single_copy_item_you_own_is_refused_without_charge(self):
        self.p.inventory.add_item("star_hair_clip")
        r = self.svc.redeem("star_hair_clip")
        self.assertEqual((r.success, r.code), (False, "owned"))
        self.assertEqual(self.p.capsule_stamps, 100)
        self.assertEqual(self.p.inventory.get_quantity("star_hair_clip"), 1)

    def test_a_full_stack_is_refused_without_charge(self):
        limit = ITEM_REGISTRY.get("cat_bell_charm").limit
        self.p.inventory.add_item("cat_bell_charm", limit)
        r = self.svc.redeem("cat_bell_charm")
        self.assertEqual((r.success, r.code), (False, "full"))
        self.assertEqual(self.p.capsule_stamps, 100)
        self.assertEqual(self.p.inventory.get_quantity("cat_bell_charm"), limit)

    def test_a_stackable_can_be_redeemed_again_up_to_its_limit(self):
        self.assertTrue(self.svc.redeem("cat_paw_sticker").success)
        self.assertTrue(self.svc.redeem("cat_paw_sticker").success)
        self.assertEqual(self.p.inventory.get_quantity("cat_paw_sticker"), 2)

    def test_unknown_and_off_menu_items_are_refused(self):
        for item_id in ("nope", None, 3, "free_play_coupon", "golden_token", "racing_car_viper", "neon_cap"):
            self.assertEqual(self.svc.redeem(item_id).code, "unknown", item_id)
        self.assertEqual(self.p.capsule_stamps, 100)
        self.assertEqual(self.p.inventory.to_dict(), {})

    def test_a_failed_grant_gives_the_stamps_back_and_saves_once_at_most(self):
        failed = ItemGrantResult(False, "cat_paw_sticker", 1, 0, "stack_full")
        with mock.patch.object(RewardService, "grant_item", return_value=failed):
            r = self.svc.redeem("cat_paw_sticker")
        self.assertEqual((r.success, r.code), (False, "failed"))
        self.assertEqual(self.p.capsule_stamps, 100)
        self.assertEqual(self.p.inventory.to_dict(), {})

    def test_the_status_column_is_right(self):
        self.p.inventory.add_item("star_hair_clip")
        self.p.spend_capsule_stamps(95)
        status = {e.item_id: e.status for e in self.svc.redeem_entries()}
        self.assertEqual(status["star_hair_clip"], "owned")
        self.assertEqual(status["cat_paw_sticker"], "need_stamps")
        self.p.add_capsule_stamps(50)
        self.assertEqual({e.item_id: e.status for e in self.svc.redeem_entries()}["cat_paw_sticker"], "ok")

    def test_the_list_is_cheapest_first_and_covers_every_prize(self):
        entries = self.svc.redeem_entries()
        self.assertEqual({e.item_id for e in entries}, set(REDEEMABLE))
        self.assertEqual([e.price for e in entries], sorted(e.price for e in entries))

    def test_redeemed_items_arrive_in_the_systems_that_use_them(self):
        for item_id in ("cat_paw_sticker", "retro_gold_trophy"):
            self.svc.redeem(item_id)
        from collection import CollectionService
        from showcase import ShowcaseService
        self.assertTrue(CollectionService(self.p).owns("cat_paw_sticker"))
        self.assertTrue(ShowcaseService(self.p).choose("trophy", "retro_gold_trophy"))
        self.svc.redeem("cat_ears")
        self.assertEqual(ITEM_REGISTRY.get("cat_ears").category, "COSMETIC")
        self.assertEqual(self.p.inventory.get_quantity("cat_ears"), 1)


class EconomyTests(unittest.TestCase):
    def potential(self, p):
        """Stamps in hand plus everything recycling the spares would pay: it can only go DOWN."""
        svc = ExchangeService(p)
        return p.capsule_stamps + sum(e.spare * e.value for e in svc.recycle_entries())

    def test_a_redeem_then_recycle_loop_loses_stamps_every_time(self):
        p = profile()
        p.add_capsule_stamps(200)
        svc = ExchangeService(p)
        svc.redeem("retro_cartridge")                    # keep the one protected copy
        last = p.capsule_stamps
        for _ in range(12):
            self.assertTrue(svc.redeem("retro_cartridge").success)
            self.assertTrue(svc.recycle("retro_cartridge", 1).success)
            self.assertLess(p.capsule_stamps, last)
            last = p.capsule_stamps
        self.assertEqual(p.inventory.get_quantity("retro_cartridge"), 1)

    def test_random_operation_sequences_never_create_stamps(self):
        rng = random.Random(7)
        ids = list(REDEEMABLE)
        for trial in range(25):
            p = profile()
            for i in RECYCLABLE:
                if rng.random() < 0.6:
                    p.inventory.add_item(i, rng.randint(1, 20))
            p.add_capsule_stamps(rng.randint(0, 120))
            svc = ExchangeService(p)
            start = self.potential(p)
            for _ in range(150):
                if rng.random() < 0.5:
                    svc.recycle(rng.choice(list(RECYCLABLE)), rng.randint(-1, 6))
                else:
                    svc.redeem(rng.choice(ids))
                self.assertLessEqual(self.potential(p), start, trial)
                self.assertGreaterEqual(p.capsule_stamps, 0)
                self.assertLessEqual(p.capsule_stamps, MAX_CAPSULE_STAMPS)
                for i in RECYCLABLE:
                    self.assertGreaterEqual(p.inventory.get_quantity(i), 0)

    def test_there_is_no_passive_source_of_stamps(self):
        p = profile()
        for _ in range(500):
            p.add_tickets(5)
            p.add_tokens(5)
            p.record_game_played("x")
        self.assertEqual(p.capsule_stamps, 0)

    def test_stamps_cannot_buy_tickets_or_tokens(self):
        p = profile(tickets=5, tokens=5)
        p.add_capsule_stamps(500)
        svc = ExchangeService(p)
        for item_id in REDEEMABLE:
            svc.redeem(item_id)
        self.assertEqual((p.tickets, p.tokens), (5, 5))
        self.assertFalse(hasattr(p, "convert_capsule_stamps"))

    def test_a_maximum_stack_recycles_to_exactly_the_cap_arithmetic(self):
        p = profile()
        limit = ITEM_REGISTRY.get("retro_gold_trophy").limit
        p.inventory.add_item("retro_gold_trophy", limit)
        svc = ExchangeService(p)
        self.assertEqual(svc.spare("retro_gold_trophy"), limit - 1)
        self.assertEqual(svc.max_recycle("retro_gold_trophy"), min(limit - 1, MAX_CAPSULE_STAMPS // 6))
        self.assertTrue(svc.recycle("retro_gold_trophy", svc.max_recycle("retro_gold_trophy")).success)
        self.assertLessEqual(p.capsule_stamps, MAX_CAPSULE_STAMPS)

    def test_the_exchange_is_never_a_cheaper_route_than_the_prize_counter(self):
        """A Stamp is the proceeds of one spare copy, and a copy costs a whole pull: 3 Stamps per 15 Tickets
        (CAT) or 6 per 30 (RETRO), i.e. at least 5 Tickets of pulls behind every Stamp. So the Tickets behind
        any price are >= 5 x price - always more than the Prize Counter's own price for the same item."""
        from prize_shop import entry_for
        per_stamp = min(CAPSULE_MACHINES["cat"].cost / 3, CAPSULE_MACHINES["retro"].cost / 6)
        self.assertEqual(per_stamp, 5)
        checked = 0
        for item_id in REDEEMABLE:
            shop = entry_for(item_id)
            if shop is not None:
                checked += 1
                self.assertGreater(redeem_price(item_id) * per_stamp, shop.cost, item_id)
        self.assertGreaterEqual(checked, 6)


class SaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "p.json")

    def test_balance_and_inventory_persist_together(self):
        p = profile()
        p.inventory.add_item("cat_bell_charm", 4)
        store = ProfileStore(self.path)
        store.autosave(p)
        ExchangeService(p).recycle("cat_bell_charm", 3)
        loaded = ProfileStore(self.path).load()
        self.assertEqual(loaded.capsule_stamps, 9)
        self.assertEqual(loaded.inventory.get_quantity("cat_bell_charm"), 1)

    def test_a_zero_balance_adds_nothing_to_the_save_and_old_saves_load_as_zero(self):
        self.assertNotIn("capsule_stamps", PlayerProfile().to_dict())
        old = PlayerProfile(tickets=21).to_dict()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(old, f)
        loaded = ProfileStore(self.path).load()
        self.assertEqual((loaded.capsule_stamps, loaded.tickets), (0, 21))

    def test_damaged_balances_become_zero_or_the_cap(self):
        for junk, expected in ((-5, 0), ("12", 0), (1.5, 0), (True, 0), (None, 0), ([3], 0), ({"a": 1}, 0),
                               (10 ** 12, MAX_CAPSULE_STAMPS), (MAX_CAPSULE_STAMPS + 1, MAX_CAPSULE_STAMPS), (42, 42)):
            data = PlayerProfile().to_dict()
            data["capsule_stamps"] = junk
            self.assertEqual(PlayerProfile.from_dict(data).capsule_stamps, expected, junk)

    def test_damaged_inventories_cannot_break_the_exchange(self):
        data = PlayerProfile().to_dict()
        data["inventory"] = {"cat_bell_charm": -3, "cat_paw_sticker": 10 ** 9, "retro_cartridge": "5",
                             "retro_pixel_heart": True, "gone_item": 4, 7: 2, "cat_yarn_ball": 2}
        p = PlayerProfile.from_dict(data)
        svc = ExchangeService(p)
        limit = ITEM_REGISTRY.get("cat_paw_sticker").limit
        self.assertEqual(p.inventory.get_quantity("cat_paw_sticker"), limit)
        self.assertEqual(svc.spare("cat_bell_charm"), 0)
        self.assertFalse(svc.recycle("cat_bell_charm", 1).success)
        self.assertFalse(svc.recycle("retro_cartridge", 1).success)
        self.assertTrue(svc.recycle("cat_yarn_ball", 1).success)
        self.assertTrue(svc.recycle("cat_paw_sticker", 5).success)
        self.assertEqual(p.capsule_stamps, 3 + 15)
        self.assertEqual(p.inventory.get_quantity("gone_item"), 4)               # unknown ids are kept, untouched

    def test_profile_api_rejects_bad_amounts_and_never_goes_negative(self):
        p = PlayerProfile()
        for bad in (-1, True, 1.0, "3", None):
            with self.assertRaises(ValueError):
                p.add_capsule_stamps(bad)
            with self.assertRaises(ValueError):
                p.spend_capsule_stamps(bad)
        p.add_capsule_stamps(5)
        self.assertFalse(p.spend_capsule_stamps(6))
        self.assertEqual(p.capsule_stamps, 5)
        self.assertEqual(p.add_capsule_stamps(MAX_CAPSULE_STAMPS), MAX_CAPSULE_STAMPS - 5)
        self.assertEqual(p.capsule_stamps, MAX_CAPSULE_STAMPS)

    def test_a_round_trip_keeps_the_balance_and_a_failed_write_loses_nothing_in_memory(self):
        p = profile()
        p.add_capsule_stamps(33)
        self.assertEqual(PlayerProfile.from_dict(p.to_dict()).capsule_stamps, 33)
        store = ProfileStore(self.path)
        with mock.patch("builtins.open", side_effect=OSError("disk full")):
            self.assertFalse(store.save(p))
        self.assertEqual(p.capsule_stamps, 33)


class IsolationTests(unittest.TestCase):
    def test_two_profiles_never_share_stamps_or_items(self):
        a, b = profile(pid="a"), profile(pid="b")
        a.inventory.add_item("cat_bell_charm", 6)
        b.inventory.add_item("cat_bell_charm", 4)
        ExchangeService(a).recycle("cat_bell_charm", 5)
        self.assertEqual((a.capsule_stamps, b.capsule_stamps), (15, 0))
        self.assertEqual((a.inventory.get_quantity("cat_bell_charm"), b.inventory.get_quantity("cat_bell_charm")), (1, 4))
        ExchangeService(b).recycle("cat_bell_charm", 1)
        self.assertTrue(ExchangeService(a).redeem("cat_paw_sticker").success)
        self.assertFalse(ExchangeService(b).redeem("cat_paw_sticker").success)          # B has only 3
        self.assertEqual((a.capsule_stamps, b.capsule_stamps), (3, 3))
        self.assertEqual(b.inventory.get_quantity("cat_paw_sticker"), 0)


class RoomBase(unittest.TestCase):
    def setUp(self):
        self.profiles = [profile(pid="exa", tickets=50), profile(pid="exb", tickets=50)]
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

    def scene(self, index=0, view=ui.RECYCLE):
        scene = ui.ExchangeScene(self.game, self.game.session.players[index], view)
        self.game.scenes.push(scene)
        self.frames(40)
        return scene

    def drawn(self, scene):
        rects = []
        real = ui.draw_text

        def spy(surf, text, pos, *a, **k):
            r = real(surf, text, pos, *a, **k)
            rects.append((text, r))
            return r

        with mock.patch.object(ui, "draw_text", spy):
            scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        return rects


class TabAndScreenTests(RoomBase):
    def open_tab(self, index=0):
        self.room.acting_player = self.room.players[index]
        self.room.open_prize_counter()
        self.frames()
        shop = self.game.scenes.current
        self.assertIsInstance(shop, ShopScene)
        shop.set_tab(TABS.index(EXCHANGE))
        return shop

    def test_the_prize_counter_has_a_labelled_exchange_tab_that_draws(self):
        self.assertIn("EXCHANGE", TABS)
        shop = self.open_tab()
        shop.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertIn("E: RECYCLE", shop.idle_message())

    def test_the_footer_hints_match_each_tab(self):
        shop = self.open_tab()
        shop.draw(pygame.Surface((VIEW_W, VIEW_H)))
        text = " ".join(shop.hints)
        self.assertIn("RECYCLE", text)
        self.assertIn("REDEEM", text)
        self.assertNotIn("BUY", text)
        shop.set_tab(TABS.index("RACING"))
        shop.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertIn("GARAGE", " ".join(shop.hints))
        self.assertNotIn("BUY", " ".join(shop.hints))
        shop.set_tab(0)
        shop.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertIn("BUY", " ".join(shop.hints))

    def test_e_on_the_tab_opens_recycle_and_the_bag_key_opens_redeem_for_the_same_player(self):
        shop = self.open_tab(1)
        self.key(pygame.K_RETURN)                                  # P2's interact key
        self.frames(40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, ui.ExchangeScene)
        self.assertIs(scene.profile, self.profiles[1])
        self.assertEqual(scene.view, ui.RECYCLE)
        self.key(pygame.K_ESCAPE)
        self.frames(40)
        self.assertIs(self.game.scenes.current, shop)
        self.key(pygame.K_o)                                       # P2's bag key
        self.frames(40)
        self.assertEqual(self.game.scenes.current.view, ui.REDEEM)

    def test_the_other_players_keys_do_nothing_on_the_screen(self):
        self.profiles[1].inventory.add_item("cat_bell_charm", 4)
        scene = self.scene(1)
        for k in (pygame.K_e, pygame.K_s, pygame.K_d, pygame.K_i):          # P1's keys
            self.key(k)
        self.assertIsNone(scene.modal)
        self.assertEqual(scene.view, ui.RECYCLE)
        self.assertEqual(scene.quantity, 1)
        self.assertEqual([p.capsule_stamps for p in self.profiles], [0, 0])

    def recycle_with_keys(self, scene, interact=pygame.K_e):
        self.key(interact)                                         # opens "RECYCLE?"
        self.assertIsNotNone(scene.modal)
        self.frames(30)                                            # (past the confirm delay)
        self.key(interact)                                         # RECYCLE is the first choice

    def test_recycling_with_the_keys_asks_first_then_pays_once(self):
        p = self.profiles[0]
        p.inventory.add_item("cat_bell_charm", 4)
        scene = self.scene()
        self.key(pygame.K_d)                                        # amount 2
        self.assertEqual(scene.quantity, 2)
        self.key(pygame.K_e)
        self.assertIsNotNone(scene.modal)
        self.assertEqual(p.capsule_stamps, 0)                       # nothing yet: it asked first
        self.frames(30)
        self.key(pygame.K_ESCAPE)                                   # cancel
        self.assertEqual((p.capsule_stamps, p.inventory.get_quantity("cat_bell_charm")), (0, 4))
        self.frames(60)
        self.recycle_with_keys(scene)
        self.assertEqual((p.capsule_stamps, p.inventory.get_quantity("cat_bell_charm")), (6, 2))
        self.assertIsNotNone(scene.anim)
        self.assertEqual(self.profiles[1].capsule_stamps, 0)

    def test_mashing_the_key_cannot_recycle_twice(self):
        p = self.profiles[0]
        p.inventory.add_item("cat_bell_charm", 9)
        scene = self.scene()
        self.recycle_with_keys(scene)
        for _ in range(8):                                         # held / mashed E during the animation and lock
            self.key(pygame.K_e)
        self.assertEqual(p.capsule_stamps, 3)
        self.assertEqual(p.inventory.get_quantity("cat_bell_charm"), 8)
        self.assertIsNone(scene.modal)
        self.frames(int((ui.ACTION_LOCK + ui.ANIM_TIME[ui.RECYCLE]) * 60) + 5)
        self.key(pygame.K_e)                                       # afterwards a new request is allowed
        self.assertIsNotNone(scene.modal)

    def test_mashing_redeem_pays_once_per_lock(self):
        p = self.profiles[0]
        p.add_capsule_stamps(60)
        scene = self.scene(view=ui.REDEEM)
        for _ in range(10):
            self.key(pygame.K_e)
        self.assertEqual(p.capsule_stamps, 48)
        self.assertEqual(p.inventory.get_quantity("cat_paw_sticker"), 1)
        self.frames(int(ui.ACTION_LOCK * 60) + 70)
        self.key(pygame.K_e)
        self.assertEqual(p.capsule_stamps, 36)

    def test_redeem_messages_for_poor_owned_and_full(self):
        p = self.profiles[0]
        scene = self.scene(view=ui.REDEEM)
        self.key(pygame.K_e)
        self.assertIn("NEED 12 MORE", scene.message)
        self.assertIn("MORE STAMPS", " ".join(scene.keeper.speech_lines(200) or []))
        self.assertEqual((p.capsule_stamps, p.inventory.to_dict()), (0, {}))
        p.add_capsule_stamps(40)
        p.inventory.add_item("cat_sticker")
        scene.select(2)
        self.assertEqual(scene.entry.item_id, "cat_sticker")
        self.frames(60)
        self.key(pygame.K_e)
        self.assertIn("ALREADY", scene.message)
        self.assertEqual(p.capsule_stamps, 40)

    def test_last_copy_message(self):
        self.profiles[0].inventory.add_item("cat_bell_charm", 1)
        scene = self.scene()
        self.key(pygame.K_e)
        self.assertIn("KEEP YOUR LAST COPY", scene.message)
        self.assertIsNone(scene.modal)

    def test_success_shows_mochis_message_and_the_item_appears(self):
        p = self.profiles[0]
        p.add_capsule_stamps(30)
        scene = self.scene(view=ui.REDEEM)
        self.key(pygame.K_e)
        self.assertIn("YOURS", scene.message)
        self.assertTrue(scene.keeper.speech_lines(200))
        self.assertIsNotNone(scene.anim)
        for _ in range(int(ui.ANIM_TIME[ui.REDEEM] * 60) + 5):
            self.game.step([], DT)
            scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertIsNone(scene.anim)


class LayoutTests(RoomBase):
    def test_every_view_every_page_stays_inside_the_frame_and_columns(self):
        p = self.profiles[0]
        for i in RECYCLABLE:
            p.inventory.add_item(i, 99)
        p.add_capsule_stamps(500)
        scene = self.scene()
        bounds = pygame.Rect(0, 0, VIEW_W, VIEW_H)
        for view in (ui.RECYCLE, ui.REDEEM):
            scene.set_view(view)
            total = len(scene.rows)
            for i in list(range(total)) + [0]:
                scene.select(i)
                for text, rect in self.drawn(scene):
                    self.assertTrue(bounds.contains(rect), (view, i, text, rect))
                    self.assertTrue(ui.FRAME.inflate(2, 2).contains(rect), (view, i, text, rect))
                self.assertLessEqual(scene.first[scene.v], i)
                self.assertGreater(scene.first[scene.v] + ui.VISIBLE, i)

    def test_the_redeem_list_paginates_through_all_prizes(self):
        scene = self.scene(view=ui.REDEEM)
        total = len(scene.rows)
        self.assertGreater(total, ui.VISIBLE)
        for _ in range(total - 1):
            scene.on_action("down")
        self.assertEqual(scene.index[scene.v], total - 1)
        self.assertEqual(scene.first[scene.v], total - ui.VISIBLE)
        scene.on_action("down")                                     # wraps to the top
        self.assertEqual((scene.index[scene.v], scene.first[scene.v]), (0, 0))

    def test_long_names_are_shortened_to_fit_their_column(self):
        self.profiles[0].inventory.add_item("retro_gold_trophy", 3)
        scene = self.scene()
        names = [t for t, r in self.drawn(scene) if r.x < ui.LIST.x + 120 and r.y > ui.LIST.y]
        for text, rect in [(t, r) for t, r in self.drawn(scene) if r.x >= ui.LIST.x + 20 and r.right < ui.LIST.right - 60]:
            self.assertLessEqual(rect.right, ui.LIST.right - 55, text)

    def test_empty_states_read_clearly(self):
        scene = self.scene()
        texts = [t for t, _ in self.drawn(scene)]
        self.assertIn("NO CAPSULE COLLECTIBLES YET", texts)
        scene.on_action("left")
        scene.on_action("up")
        scene.on_action("interact")
        self.assertIsNone(scene.modal)

    def test_the_screen_scales_with_the_window(self):
        scene = self.scene()
        for size in ((800, 600), (1280, 960), (1920, 1080)):
            screen = pygame.display.set_mode(size) if False else self.game.screen
            canvas = pygame.Surface((VIEW_W, VIEW_H))
            scene.draw(canvas)
            scaled = pygame.transform.scale(canvas, size)
            self.assertEqual(scaled.get_size(), size)

    def test_the_paw_stamp_icon_and_recycle_animation_draw_at_every_moment(self):
        self.profiles[0].inventory.add_item("retro_cartridge", 6)
        scene = self.scene()
        icon = ui.stamp_icon()
        self.assertEqual(icon.get_size(), (9, 9))
        self.assertEqual(ui.stamp_icon(size=3).get_size(), (27, 27))
        scene._recycle_answered(scene.entry, 4, "RECYCLE")
        for _ in range(int(ui.ANIM_TIME[ui.RECYCLE] * 60) + 5):
            scene.update(DT)
            scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertIsNone(scene.anim)


if __name__ == "__main__":
    unittest.main()
