"""Tests for the Prize Counter: pricing, purchases (tickets and inventory),
profile isolation and the shop screen reached through PRIZE PLAZA.

Run headless from this folder:   python -m unittest test_prize_shop -v
"""
import os
import shutil
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from decorations import decoration_item_id, default_catalog  # noqa: E402
from font import get_font  # noqa: E402
from game import Game  # noqa: E402
from inventory import Inventory  # noqa: E402
from item_registry import FREE_PLAY_COUPON, ITEM_REGISTRY  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from prize_shop import (CATEGORIES, COUPON_PRICE, SHOP_ENTRIES, ShopService,  # noqa: E402
                        entries_in, entry_for)
from racing_progression.catalog import prize_for  # noqa: E402
from room_testing import goto_room  # noqa: E402
from shop_ui import RACING, TABS, ShopScene  # noqa: E402
from racing_progression.ui import PrizeCounterScene  # noqa: E402
from stations import PrizeCounter  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class CatalogTests(unittest.TestCase):
    def test_every_entry_is_a_real_item_with_a_positive_price(self):
        for e in SHOP_ENTRIES:
            with self.subTest(item=e.item_id):
                self.assertIn(e.item_id, ITEM_REGISTRY)
                self.assertGreater(e.cost, 0)
                self.assertIn(e.category, CATEGORIES)

    def test_ids_are_unique(self):
        ids = [e.item_id for e in SHOP_ENTRIES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_four_categories_are_stocked_with_the_requested_goods(self):
        names = {c: {e.item_id for e in entries_in(c)} for c in CATEGORIES}
        self.assertEqual(names["FREE PLAY"], {FREE_PLAY_COUPON})
        for wanted in ("decor_table_lamp", "decor_cat_plush", "racing_decoration_poster_arcade",
                       "decor_pixel_plant", "decor_retro_clock"):
            self.assertIn(wanted, names["HOME"])
        for wanted in ("neon_cap", "cat_ears", "retro_sunglasses", "palette_sunset"):
            self.assertIn(wanted, names["COSMETICS"])
        for wanted in ("cat_sticker", "retro_badge", "arcade_trophy"):
            self.assertIn(wanted, names["COLLECT"])

    def test_decoration_prices_come_from_the_decoration_catalogue(self):
        catalogue = default_catalog()
        for e in entries_in("HOME"):
            self.assertEqual(e.cost, catalogue.get(e.decoration_id).ticket_cost)
            self.assertEqual(e.item_id, decoration_item_id(e.decoration_id))

    def test_decorations_shared_with_the_racing_counter_cost_the_same_and_share_ids(self):
        for e in entries_in("HOME"):
            prize = prize_for("decoration", e.decoration_id)
            if prize is not None:
                self.assertEqual(prize.cost, e.cost)
                self.assertEqual(prize.item_id, e.item_id)

    def test_names_fit_the_list_column(self):
        font = get_font()
        pygame.font.init()
        for e in SHOP_ENTRIES:
            self.assertLessEqual(font.size(e.name)[0], 98, e.name)


class ShopServiceTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(profile_id="a", tickets=100)
        self.shop = ShopService(self.p)

    def test_purchase_charges_the_price_and_grants_the_item(self):
        r = self.shop.purchase("neon_cap")
        self.assertTrue(r.success)
        self.assertEqual(self.p.tickets, 100 - entry_for("neon_cap").cost)
        self.assertTrue(self.p.inventory.has_item("neon_cap"))

    def test_not_enough_tickets_changes_nothing(self):
        self.p.spend_tickets(95)
        r = self.shop.purchase("neon_cap")
        self.assertFalse(r.success)
        self.assertEqual(r.code, "need_tickets")
        self.assertEqual(self.p.tickets, 5)
        self.assertFalse(self.p.inventory.has_item("neon_cap"))

    def test_exact_balance_can_buy(self):
        cost = entry_for("cat_ears").cost
        self.p.spend_tickets(100 - cost)
        self.assertTrue(self.shop.purchase("cat_ears").success)
        self.assertEqual(self.p.tickets, 0)

    def test_unique_items_cannot_be_bought_twice_and_cost_nothing_the_second_time(self):
        self.shop.purchase("retro_sunglasses")
        left = self.p.tickets
        r = self.shop.purchase("retro_sunglasses")
        self.assertEqual((r.success, r.code), (False, "owned"))
        self.assertEqual(self.p.tickets, left)
        self.assertEqual(self.p.inventory.get_quantity("retro_sunglasses"), 1)

    def test_an_item_owned_from_elsewhere_is_not_sold_again(self):
        self.p.inventory.add_item("cat_sticker")                  # e.g. from a daily reward
        self.assertEqual(self.shop.purchase("cat_sticker").code, "owned")
        self.assertEqual(self.p.tickets, 100)

    def test_coupons_stack(self):
        for expected in (1, 2, 3):
            self.assertTrue(self.shop.purchase(FREE_PLAY_COUPON).success)
            self.assertEqual(self.p.inventory.get_quantity(FREE_PLAY_COUPON), expected)
        self.assertEqual(self.p.tickets, 100 - 3 * COUPON_PRICE)

    def test_a_full_coupon_stack_is_not_charged(self):
        self.p.add_tickets(5000)
        self.p.inventory.add_item(FREE_PLAY_COUPON, 99)
        before = self.p.tickets
        r = self.shop.purchase(FREE_PLAY_COUPON)
        self.assertEqual((r.success, r.code), (False, "stack_full"))
        self.assertEqual(self.p.tickets, before)
        self.assertEqual(self.p.inventory.get_quantity(FREE_PLAY_COUPON), 99)

    def test_unknown_item_is_refused(self):
        self.assertEqual(self.shop.purchase("nope").code, "unknown")
        self.assertEqual(self.shop.purchase("racing_car_viper").code, "unknown")    # not sold here
        self.assertEqual(self.p.tickets, 100)

    def test_a_failed_grant_refunds_the_tickets(self):
        from rewards import ItemGrantResult
        with mock.patch("prize_shop.RewardService.grant_item",
                        return_value=ItemGrantResult(False, "neon_cap", 1, 0, "unknown_item")):
            r = self.shop.purchase("neon_cap")
        self.assertEqual((r.success, r.code), (False, "failed"))
        self.assertEqual(self.p.tickets, 100)
        self.assertFalse(self.p.inventory.has_item("neon_cap"))

    def test_a_purchase_is_one_save(self):
        saves = []
        self.p.subscribe_save(lambda: saves.append(1))
        self.shop.purchase("neon_cap")
        self.assertEqual(len(saves), 1)

    def test_purchases_do_not_touch_tokens_or_lifetime_ticket_stats(self):
        tokens, earned = self.p.tokens, self.p.lifetime_tickets_earned
        self.shop.purchase("neon_cap")
        self.assertEqual((self.p.tokens, self.p.lifetime_tickets_earned), (tokens, earned))

    def test_profiles_are_isolated(self):
        a, b = PlayerProfile(profile_id="a", tickets=60), PlayerProfile(profile_id="b", tickets=60)
        ShopService(a).purchase("neon_cap")
        self.assertEqual(b.tickets, 60)
        self.assertFalse(b.inventory.has_item("neon_cap"))
        ShopService(b).purchase("neon_cap")                         # b can still buy its own
        self.assertEqual(a.tickets, b.tickets)

    def test_inventory_survives_a_restart(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "p.json")
        store = ProfileStore(path)
        p = store.load()
        store.autosave(p)
        p.add_tickets(80)
        ShopService(p).purchase("neon_cap")
        ShopService(p).purchase(FREE_PLAY_COUPON)
        reloaded = ProfileStore(path).load()
        self.assertTrue(reloaded.inventory.has_item("neon_cap"))
        self.assertEqual(reloaded.inventory.get_quantity(FREE_PLAY_COUPON), 1)
        self.assertEqual(reloaded.tickets, p.tickets)

    def test_old_saves_without_the_new_fields_still_load(self):
        old = {"version": 2, "tokens": 7, "tickets": 33, "inventory": {"cat_sticker": 1, "free_play_coupon": 2}}
        p = PlayerProfile.from_dict(old)
        self.assertEqual((p.tokens, p.tickets), (7, 33))
        self.assertEqual(p.inventory.get_quantity("free_play_coupon"), 2)
        self.assertEqual(p.appearance, {})
        self.assertEqual(p.collection_display, [])
        self.assertEqual(p.to_dict()["appearance"], {})

    def test_items_the_registry_does_not_know_are_kept(self):
        p = PlayerProfile.from_dict({"inventory": {"mystery_item": 2, "neon_cap": 1}})
        self.assertEqual(p.inventory.unknown_items, {"mystery_item": 2})
        self.assertEqual(p.to_dict()["inventory"]["mystery_item"], 2)

    def test_racing_decoration_bought_at_the_racing_counter_counts_here(self):
        from racing_progression.service import PrizeService
        self.assertTrue(PrizeService(self.p).buy("decoration", "poster_arcade").success)
        self.assertEqual(self.shop.purchase("racing_decoration_poster_arcade").code, "owned")


class ShopSceneTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="shop_a", display_name="Ann", tickets=200),
                         PlayerProfile(profile_id="shop_b", display_name="Bo", tickets=200)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "prize_plaza")

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k, frames=1):
        self.game.step([key_event(k)], DT)
        self.frames(frames - 1)

    def stand_at_counter(self, index=0):
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        for i, avatar in enumerate(self.room.players):
            avatar.x, avatar.y = (counter.zone.centerx, counter.zone.bottom - 2) if i == index \
                else (350.0, 250.0)
        self.frames(5)
        return counter

    def open_shop(self, owner=0):
        self.room.acting_player = self.room.players[owner]
        self.room.open_prize_counter()
        self.room.acting_player = None
        self.frames()
        scene = self.game.scenes.current
        self.assertIsInstance(scene, ShopScene)
        return scene

    def go_to(self, scene, tab, item_id, buy_key=pygame.K_e):
        scene.tab = TABS.index(tab)
        scene.index = [e.item_id for e in scene.rows].index(item_id)
        scene.first = max(0, scene.index - scene.VISIBLE + 1)

    def test_walking_up_and_pressing_e_opens_the_shop_for_that_player(self):
        counter = self.stand_at_counter(0)
        self.assertIs(self.room.players[0].nearby, counter)
        self.key(pygame.K_e, 40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, ShopScene)
        self.assertIs(scene.owner, self.game.session.players[0])

    def test_p2_pressing_enter_opens_the_shop_for_p2(self):
        self.stand_at_counter(1)
        self.key(pygame.K_RETURN, 40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, ShopScene)
        self.assertIs(scene.owner, self.game.session.players[1])

    def test_esc_leaves_safely_to_the_plaza(self):
        self.open_shop()
        self.key(pygame.K_ESCAPE, 30)
        self.assertIs(self.game.scenes.current, self.room)

    def test_categories_cycle_with_left_right_and_cover_every_tab(self):
        scene = self.open_shop()
        seen = [scene.category]
        for _ in range(len(TABS) - 1):
            self.key(pygame.K_d)
            seen.append(scene.category)
        self.assertEqual(seen, list(TABS))
        self.key(pygame.K_d)
        self.assertEqual(scene.category, TABS[0])           # wraps
        self.key(pygame.K_a)
        self.assertEqual(scene.category, TABS[-1])

    def test_confirm_dialog_buys_exactly_once_even_when_e_is_mashed(self):
        scene = self.open_shop()
        self.go_to(scene, "COSMETICS", "neon_cap")
        self.key(pygame.K_e, 20)                            # open BUY?
        self.assertIsNotNone(scene.modal)
        for _ in range(12):                                 # mash E: the first accepted press buys,
            self.key(pygame.K_e)                            # later ones meet the lock / owned check
        self.frames(30)
        self.assertEqual(self.profiles[0].inventory.get_quantity("neon_cap"), 1)
        self.assertEqual(self.profiles[0].tickets, 200 - entry_for("neon_cap").cost)

    def test_the_first_moments_of_the_dialog_ignore_keys(self):
        scene = self.open_shop()
        self.go_to(scene, "COSMETICS", "neon_cap")
        self.key(pygame.K_e)                                # opens the dialog this frame ...
        self.key(pygame.K_e)                                # ... a held / mashed key cannot answer it
        self.assertFalse(self.profiles[0].inventory.has_item("neon_cap"))
        self.assertEqual(self.profiles[0].tickets, 200)

    def test_cancel_charges_nothing(self):
        scene = self.open_shop()
        self.go_to(scene, "COSMETICS", "cat_ears")
        self.key(pygame.K_e, 20)
        self.key(pygame.K_s)                                # CANCEL
        self.key(pygame.K_e)
        self.assertIsNone(scene.modal)
        self.assertEqual(self.profiles[0].tickets, 200)
        self.assertFalse(self.profiles[0].inventory.has_item("cat_ears"))

    def test_esc_in_the_dialog_cancels_and_keeps_the_shop_open(self):
        scene = self.open_shop()
        self.go_to(scene, "COSMETICS", "cat_ears")
        self.key(pygame.K_e, 20)
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(scene.modal)
        self.assertIs(self.game.scenes.current, scene)
        self.assertEqual(self.profiles[0].tickets, 200)

    def test_too_poor_never_opens_the_dialog(self):
        self.profiles[0].spend_tickets(195)
        scene = self.open_shop()
        self.go_to(scene, "COLLECT", "arcade_trophy")
        self.key(pygame.K_e, 10)
        self.assertIsNone(scene.modal)
        self.assertEqual(self.profiles[0].tickets, 5)
        self.assertIn("MORE", scene.message)

    def test_owned_item_explains_instead_of_charging(self):
        self.profiles[0].inventory.add_item("cat_sticker")
        scene = self.open_shop()
        self.go_to(scene, "COLLECT", "cat_sticker")
        self.key(pygame.K_e, 10)
        self.assertIsNone(scene.modal)
        self.assertIn("ALREADY OWN", scene.message)
        self.assertEqual(self.profiles[0].tickets, 200)

    def test_coupons_can_be_bought_repeatedly_one_confirmation_each(self):
        scene = self.open_shop()
        self.go_to(scene, "FREE PLAY", FREE_PLAY_COUPON)
        for n in (1, 2):
            self.key(pygame.K_e, 20)
            self.key(pygame.K_e, 30)
            self.assertEqual(self.profiles[0].inventory.get_quantity(FREE_PLAY_COUPON), n)
        self.assertEqual(self.profiles[0].tickets, 200 - 2 * COUPON_PRICE)

    def test_p2_buys_from_p2s_wallet_only(self):
        scene = self.open_shop(owner=1)
        self.go_to(scene, "COSMETICS", "neon_cap")
        self.key(pygame.K_RETURN, 20)
        self.key(pygame.K_RETURN, 30)
        self.assertEqual(self.profiles[1].tickets, 200 - entry_for("neon_cap").cost)
        self.assertTrue(self.profiles[1].inventory.has_item("neon_cap"))
        self.assertEqual(self.profiles[0].tickets, 200)
        self.assertFalse(self.profiles[0].inventory.has_item("neon_cap"))

    def test_the_other_players_keys_do_not_drive_the_shop(self):
        scene = self.open_shop(owner=0)                     # P1's shop; P2 mashes Enter and arrows
        index = scene.index
        for k in (pygame.K_RETURN, pygame.K_DOWN, pygame.K_RIGHT):
            self.key(k)
        self.assertEqual((scene.index, scene.tab), (index, 0))
        self.assertIsNone(scene.modal)

    def test_mouse_selects_and_buys(self):
        scene = self.open_shop()
        self.go_to(scene, "COSMETICS", "neon_cap")
        scene.index = 0
        self.game.step([], DT)
        w, h = self.game.screen.get_size()
        row = pygame.Rect(14, 60, 200, 16)
        scene.draw(self.game.canvas)
        click = lambda cx, cy: self.game.step([pygame.event.Event(            # noqa: E731
            pygame.MOUSEBUTTONDOWN, button=1, pos=(cx * w // 400, cy * h // 300))], DT)
        click(row.centerx, row.y + 5 + 18)                  # second row
        self.assertEqual(scene.index, 1)
        click(row.centerx, row.y + 5 + 18)                  # again: asks to buy
        self.frames(1)
        self.assertIsNotNone(scene.modal)

    def test_racing_tab_opens_the_racing_counter_and_back(self):
        scene = self.open_shop()
        scene.tab = TABS.index(RACING)
        self.key(pygame.K_e, 40)
        self.assertIsInstance(self.game.scenes.current, PrizeCounterScene)
        self.assertIs(self.game.scenes.current.owner, scene.owner)
        self.key(pygame.K_ESCAPE, 40)
        self.assertIs(self.game.scenes.current, scene)

    def test_every_tab_and_row_renders_without_error(self):
        scene = self.open_shop()
        for tab in TABS:
            scene.tab, scene.index, scene.first = TABS.index(tab), 0, 0
            for i in range(max(1, len(scene.rows))):
                scene.select(i)
                scene.draw(self.game.canvas)

    def test_navigation_between_hub_rooms_still_works_after_shopping(self):
        scene = self.open_shop()
        self.key(pygame.K_ESCAPE, 40)
        self.assertIs(self.game.scenes.current, self.room)
        home = goto_room(self.game, "home")
        self.assertIs(self.game.scenes.current, home)
        self.assertIs(goto_room(self.game, "arcade_floor"), self.game.scenes.current)
        self.assertIs(goto_room(self.game, "prize_plaza"), self.room)


if __name__ == "__main__":
    unittest.main()
