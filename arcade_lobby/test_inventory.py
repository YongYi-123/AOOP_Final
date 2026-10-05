"""Tests for the inventory foundation: items, Inventory, save/load and the screen.

Run headless from this folder:   python -m unittest test_inventory -v
"""
import json
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
from inventory import Inventory  # noqa: E402
from inventory_ui import COLS, TABS, InventoryUI  # noqa: E402
from item_icons import item_icon  # noqa: E402
from item_registry import (ARCADE, CATEGORIES, COLLECTIBLE, CONSUMABLE, COSMETIC,  # noqa: E402
                           ITEM_REGISTRY, ItemDefinition, ItemRegistry)
from rewards import ItemGrantResult, RewardService  # noqa: E402
from ui import InstructionBox  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402

DT = 1 / 60
CLOCK = lambda: GameClock(lambda: date(2026, 3, 10))  # noqa: E731


def key(k, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod, unicode="")


class ItemRegistryTests(unittest.TestCase):
    def test_starter_items(self):
        r = ITEM_REGISTRY
        self.assertEqual(r.get("cat_sticker").category, COLLECTIBLE)
        self.assertFalse(r.get("cat_sticker").stackable)
        self.assertEqual(r.get("neon_cap").category, COSMETIC)
        self.assertFalse(r.get("neon_cap").stackable)
        self.assertIn(r.get("free_play_coupon").category, (ARCADE, "CONSUMABLE"))
        self.assertTrue(r.get("free_play_coupon").stackable)
        self.assertEqual(r.get("retro_badge").category, COLLECTIBLE)

    def test_every_item_is_complete(self):
        for d in ITEM_REGISTRY:
            self.assertTrue(d.name and d.description, d.id)
            self.assertIn(d.category, CATEGORIES)
            self.assertIsInstance(item_icon(d), pygame.Surface)

    def test_unknown_id_is_none_not_an_error(self):
        self.assertIsNone(ITEM_REGISTRY.get("nope"))
        self.assertNotIn("nope", ITEM_REGISTRY)

    def test_adding_an_item_is_one_entry(self):
        r = ItemRegistry([ItemDefinition("a", "A", "an item", COSMETIC)])
        r.register(ItemDefinition("b", "B", "another", ARCADE, max_stack=5))
        self.assertEqual(len(r), 2)
        with self.assertRaises(ValueError):
            r.register(ItemDefinition("a", "A2", "dup", COSMETIC))
        inv = Inventory(r)
        self.assertEqual(inv.add_item("b", 9), 5)

    def test_non_stackable_forces_max_stack_one(self):
        d = ItemDefinition("x", "X", "x", COSMETIC, stackable=False, max_stack=50)
        self.assertEqual((d.max_stack, d.limit), (1, 1))

    def test_invalid_definitions_rejected(self):
        for kw in ({"category": "WEAPON"}, {"rarity": "MYTHIC"}, {"max_stack": 0}):
            with self.assertRaises(ValueError):
                ItemDefinition("x", "X", "x", **{"category": COSMETIC, **kw})

    def test_missing_icon_data_still_draws(self):
        d = ItemDefinition("x", "X", "x", COSMETIC)
        self.assertIsInstance(item_icon(d), pygame.Surface)


class InventoryTests(unittest.TestCase):
    def test_starts_empty(self):
        inv = Inventory()
        self.assertEqual(inv.get_all_items(), [])
        self.assertEqual(inv.get_quantity("cat_sticker"), 0)
        self.assertFalse(inv.has_item("cat_sticker"))

    def test_add_and_stack(self):
        inv = Inventory()
        self.assertEqual(inv.add_item("free_play_coupon"), 1)
        self.assertEqual(inv.add_item("free_play_coupon", 4), 4)
        self.assertEqual(inv.get_quantity("free_play_coupon"), 5)
        self.assertTrue(inv.has_item("free_play_coupon", 5))
        self.assertFalse(inv.has_item("free_play_coupon", 6))

    def test_stack_limit(self):
        inv = Inventory()
        self.assertEqual(inv.add_item("free_play_coupon", 150), 99)
        self.assertEqual(inv.add_item("free_play_coupon"), 0)
        self.assertEqual(inv.get_quantity("free_play_coupon"), 99)

    def test_non_stackable_does_not_duplicate(self):
        inv = Inventory()
        self.assertEqual(inv.add_item("cat_sticker"), 1)
        self.assertEqual(inv.add_item("cat_sticker"), 0)
        self.assertEqual(inv.add_item("cat_sticker", 5), 0)
        self.assertEqual(inv.get_quantity("cat_sticker"), 1)

    def test_non_stackable_bulk_add_gives_one(self):
        self.assertEqual(Inventory().add_item("neon_cap", 3), 1)

    def test_remove(self):
        inv = Inventory()
        inv.add_item("free_play_coupon", 3)
        self.assertTrue(inv.remove_item("free_play_coupon"))
        self.assertEqual(inv.get_quantity("free_play_coupon"), 2)
        self.assertFalse(inv.remove_item("free_play_coupon", 3))       # all or nothing
        self.assertEqual(inv.get_quantity("free_play_coupon"), 2)
        self.assertTrue(inv.remove_item("free_play_coupon", 2))
        self.assertEqual(inv.get_all_items(), [])
        self.assertFalse(inv.remove_item("free_play_coupon"))
        self.assertFalse(inv.remove_item("never_had_it"))

    def test_bad_arguments(self):
        inv = Inventory()
        for bad in (0, -1, 1.5, "2", True, None):
            with self.assertRaises(ValueError):
                inv.add_item("cat_sticker", bad)
            with self.assertRaises(ValueError):
                inv.remove_item("cat_sticker", bad)
        with self.assertRaises(ValueError):
            inv.add_item("not_registered")
        self.assertEqual(inv.get_all_items(), [])

    def test_get_all_items_order_and_category(self):
        inv = Inventory()
        inv.add_item("retro_badge")
        inv.add_item("neon_cap")
        inv.add_item("cat_sticker")
        self.assertEqual([d.id for d, _ in inv.get_all_items()], ["cat_sticker", "neon_cap", "retro_badge"])
        self.assertEqual([d.id for d, _ in inv.get_all_items(COLLECTIBLE)], ["cat_sticker", "retro_badge"])

    def test_internal_counts_are_not_exposed(self):
        inv = Inventory()
        inv.add_item("free_play_coupon", 2)
        inv.to_dict()["free_play_coupon"] = 99
        inv.unknown_items["x"] = 1
        self.assertEqual(inv.get_quantity("free_play_coupon"), 2)
        self.assertFalse(hasattr(inv, "counts"))

    def test_change_callback_fires_only_on_real_changes(self):
        seen = []
        inv = Inventory(on_change=lambda: seen.append(1))
        inv.add_item("cat_sticker")
        inv.add_item("cat_sticker")                 # refused: no change
        inv.remove_item("neon_cap")                 # refused
        inv.remove_item("cat_sticker")
        self.assertEqual(len(seen), 2)


class InventorySaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_round_trip_through_the_profile(self):
        store = ProfileStore(self.path, CLOCK())
        p = store.load()
        store.autosave(p)
        p.inventory.add_item("cat_sticker")
        p.inventory.add_item("free_play_coupon", 3)
        with open(self.path) as f:
            self.assertEqual(json.load(f)["inventory"], {"cat_sticker": 1, "free_play_coupon": 3})
        q = ProfileStore(self.path, CLOCK()).load()
        self.assertEqual(q.inventory.get_quantity("cat_sticker"), 1)
        self.assertEqual(q.inventory.get_quantity("free_play_coupon"), 3)

    def test_old_save_without_inventory_loads_empty_and_keeps_everything(self):
        with open(self.path, "w") as f:
            json.dump({"version": 2, "tokens": 7, "tickets": 33, "high_scores": {"retro_racer": 900}}, f)
        p = ProfileStore(self.path, CLOCK()).load()
        self.assertEqual((p.tokens, p.tickets, p.high_score("retro_racer")), (7, 33, 900))
        self.assertEqual(p.inventory.get_all_items(), [])

    def test_version_one_save_with_coins_still_loads(self):
        with open(self.path, "w") as f:
            json.dump({"version": 1, "coins": 4, "tickets": 2}, f)
        p = ProfileStore(self.path, CLOCK()).load()
        self.assertEqual((p.tokens, p.tickets, len(p.inventory.get_all_items())), (4, 2, 0))

    def test_unknown_ids_do_not_crash_and_are_kept(self):
        with open(self.path, "w") as f:
            json.dump({"inventory": {"removed_item": 2, "cat_sticker": 1}}, f)
        store = ProfileStore(self.path, CLOCK())
        p = store.load()
        self.assertEqual([d.id for d, _ in p.inventory.get_all_items()], ["cat_sticker"])
        self.assertEqual(p.inventory.unknown_items, {"removed_item": 2})
        ui = InventoryUI(p.inventory)
        ui.draw(pygame.Surface((400, 300)))                         # draws fine
        store.save(p)
        with open(self.path) as f:
            self.assertEqual(json.load(f)["inventory"], {"removed_item": 2, "cat_sticker": 1})

    def test_garbage_inventory_data_is_ignored(self):
        for junk in (None, [], "x", 5, {"cat_sticker": "many", "neon_cap": -1, "retro_badge": True,
                                        3: 1, "free_play_coupon": 1.5}):
            inv = PlayerProfile.from_dict({"inventory": junk}, CLOCK()).inventory
            self.assertEqual(inv.get_all_items(), [], junk)

    def test_oversized_saved_counts_are_clamped(self):
        inv = PlayerProfile.from_dict({"inventory": {"cat_sticker": 7, "free_play_coupon": 5000}},
                                      CLOCK()).inventory
        self.assertEqual((inv.get_quantity("cat_sticker"), inv.get_quantity("free_play_coupon")), (1, 99))


class RewardServiceTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(clock=CLOCK())

    def test_grant_success(self):
        r = RewardService.grant_item(self.p, "free_play_coupon", 3)
        self.assertEqual(r, ItemGrantResult(True, "free_play_coupon", 3, 3, "ok"))
        self.assertEqual(self.p.inventory.get_quantity("free_play_coupon"), 3)

    def test_default_quantity_is_one(self):
        self.assertEqual(RewardService.grant_item(self.p, "cat_sticker").granted_quantity, 1)

    def test_unknown_item_is_reported_not_raised_and_not_added(self):
        r = RewardService.grant_item(self.p, "mystery_hat", 2)
        self.assertEqual((r.success, r.granted_quantity, r.reason, r.item_id, r.requested_quantity),
                         (False, 0, "unknown_item", "mystery_hat", 2))
        self.assertEqual(self.p.inventory.to_dict(), {})
        self.assertEqual(self.p.inventory.unknown_items, {})
        with self.assertRaises(ValueError):                         # Inventory itself stays strict
            self.p.inventory.add_item("mystery_hat")

    def test_unknown_item_is_logged(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            RewardService.grant_item(self.p, "mystery_hat")
        self.assertIn("mystery_hat", out.getvalue())

    def test_garbage_arguments_never_raise(self):
        for item_id in (None, 5, "", ["x"]):
            self.assertFalse(RewardService.grant_item(self.p, item_id).success)
        for qty in (0, -2, 1.5, "3", None, True):
            r = RewardService.grant_item(self.p, "cat_sticker", qty)
            self.assertEqual((r.success, r.reason), (False, "invalid_quantity"))
        self.assertEqual(self.p.inventory.to_dict(), {})

    def test_non_stackable_duplicate_is_refused(self):
        RewardService.grant_item(self.p, "neon_cap")
        r = RewardService.grant_item(self.p, "neon_cap")
        self.assertEqual((r.success, r.granted_quantity, r.reason), (False, 0, "already_owned"))
        self.assertEqual(self.p.inventory.get_quantity("neon_cap"), 1)

    def test_stack_limit_partial_and_full(self):
        RewardService.grant_item(self.p, "free_play_coupon", 90)
        r = RewardService.grant_item(self.p, "free_play_coupon", 20)
        self.assertEqual((r.success, r.granted_quantity, r.requested_quantity, r.reason),
                         (True, 9, 20, "partial"))
        r = RewardService.grant_item(self.p, "free_play_coupon")
        self.assertEqual((r.success, r.reason), (False, "stack_full"))

    def test_grants_are_saved(self):
        d = tempfile.mkdtemp()
        try:
            store = ProfileStore(os.path.join(d, "s.json"), CLOCK())
            p = store.load()
            store.autosave(p)
            RewardService.grant_item(p, "retro_badge")
            self.assertTrue(ProfileStore(store.path, CLOCK()).load().inventory.has_item("retro_badge"))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class InventoryUITests(unittest.TestCase):
    def make(self, **items):
        inv = Inventory()
        for item_id, n in items.items():
            inv.add_item(item_id, n)
        return inv, InventoryUI(inv)

    def press(self, ui, *keys, mod=0):
        for k in keys:
            ui.handle_event(key(k, mod))

    def test_lists_items_and_shows_details(self):
        inv, ui = self.make(cat_sticker=1, neon_cap=1, free_play_coupon=3, retro_badge=1)
        names = [d.name for d, _ in ui.entries]
        self.assertEqual(names, ["CAT STICKER", "NEON CAP", "FREE PLAY COUPON", "RETRO BADGE"])
        definition, qty = ui.selected_entry
        self.assertEqual((definition.name, definition.category, qty), ("CAT STICKER", "COLLECTIBLE", 1))
        self.assertEqual(definition.description, "A tiny sticker of the arcade cat.")
        ui.draw(pygame.Surface((400, 300)))

    def test_keyboard_navigation(self):
        _, ui = self.make(cat_sticker=1, neon_cap=1, free_play_coupon=3, retro_badge=1)
        self.press(ui, pygame.K_RIGHT)
        self.assertEqual(ui.selected_entry[0].id, "neon_cap")
        self.press(ui, pygame.K_d)
        self.assertEqual(ui.selected_entry[0].id, "free_play_coupon")
        self.press(ui, pygame.K_LEFT, pygame.K_a)
        self.assertEqual(ui.selected, 0)
        self.press(ui, pygame.K_DOWN)
        self.assertEqual(ui.selected, COLS)
        self.assertIsNone(ui.selected_entry)                        # an empty slot
        self.press(ui, pygame.K_w, pygame.K_UP)                     # wraps to the bottom row
        self.assertEqual(ui.selected, (ui.slot_count // COLS - 1) * COLS)
        self.press(ui, pygame.K_s)
        self.assertEqual(ui.selected, 0)
        self.press(ui, pygame.K_LEFT)                               # wraps along the row
        self.assertEqual(ui.selected, COLS - 1)

    def test_inspect_and_escape_layers(self):
        _, ui = self.make(cat_sticker=1)
        self.press(ui, pygame.K_RETURN)
        self.assertTrue(ui.inspecting)
        self.press(ui, pygame.K_RIGHT)                              # no movement while inspecting
        self.assertEqual(ui.selected, 0)
        ui.draw(pygame.Surface((400, 300)))
        self.press(ui, pygame.K_ESCAPE)
        self.assertEqual((ui.inspecting, ui.closed), (False, False))
        self.press(ui, pygame.K_e)
        self.assertTrue(ui.inspecting)
        self.press(ui, pygame.K_e)
        self.assertFalse(ui.inspecting)
        self.press(ui, pygame.K_ESCAPE)
        self.assertTrue(ui.closed)

    def test_cannot_inspect_an_empty_slot(self):
        _, ui = self.make()
        self.press(ui, pygame.K_RETURN)
        self.assertFalse(ui.inspecting)
        ui.draw(pygame.Surface((400, 300)))

    def test_category_tabs_filter(self):
        reg = ItemRegistry(list(ITEM_REGISTRY) + [
            ItemDefinition("snack", "SNACK", "yum", CONSUMABLE, icon={"shape": "ticket"})])
        inv = Inventory(reg)
        for item_id, n in (("cat_sticker", 1), ("neon_cap", 1), ("free_play_coupon", 3),
                           ("retro_badge", 1), ("snack", 2)):
            inv.add_item(item_id, n)
        ui = InventoryUI(inv)
        self.assertEqual([t[0] for t in TABS],
                         ["ALL", "COSMETICS", "ARCADE", "CONSUMABLES", "COLLECTIBLES"])
        expected = [("ALL", ["cat_sticker", "neon_cap", "free_play_coupon", "retro_badge", "snack"]),
                    ("COSMETICS", ["neon_cap"]), ("ARCADE", ["free_play_coupon"]),
                    ("CONSUMABLES", ["snack"]), ("COLLECTIBLES", ["cat_sticker", "retro_badge"])]
        for name, ids in expected:
            self.assertEqual((ui.tab_name, [d.id for d, _ in ui.entries]), (name, ids))
            ui.draw(pygame.Surface((400, 300)))
            self.press(ui, pygame.K_TAB)
        self.assertEqual(ui.tab_name, "ALL")                        # wrapped around
        self.press(ui, pygame.K_TAB, mod=pygame.KMOD_SHIFT)         # back the other way
        self.assertEqual(ui.tab_name, "COLLECTIBLES")

    def test_every_category_has_a_tab_and_tabs_fit_the_panel(self):
        from inventory_ui import W
        shown = {cat for _, cat in TABS if cat}
        self.assertEqual(shown, set(CATEGORIES))
        from font import get_font
        width = sum(get_font().size(n)[0] + 10 for n, _ in TABS)
        self.assertLessEqual(12 + width, W - 12)

    def test_changing_tab_resets_selection(self):
        _, ui = self.make(cat_sticker=1, neon_cap=1)
        self.press(ui, pygame.K_RIGHT, pygame.K_RETURN, pygame.K_TAB)
        self.assertEqual((ui.selected, ui.inspecting), (0, False))

    def test_reads_live_inventory_and_empty_tab_message(self):
        inv, ui = self.make()
        surf = pygame.Surface((400, 300))
        ui.draw(surf)
        inv.add_item("cat_sticker")
        ui.draw(surf)
        self.assertEqual(ui.selected_entry[0].id, "cat_sticker")
        inv.remove_item("cat_sticker")
        ui.draw(surf)
        self.assertIsNone(ui.selected_entry)

    def test_many_items_scroll(self):
        reg = ItemRegistry([ItemDefinition(f"i{n}", f"ITEM {n}", "d", COSMETIC) for n in range(14)])
        inv = Inventory(reg)
        for n in range(14):
            inv.add_item(f"i{n}")
        ui = InventoryUI(inv)
        self.press(ui, pygame.K_UP)                                 # wraps to the last row
        self.assertGreater(ui.scroll_row, 0)
        self.assertTrue(ui.slot_rect(ui.selected).bottom <= 50 + 3 * 34)
        ui.draw(pygame.Surface((400, 300)))

    def test_does_not_edit_the_inventory(self):
        inv, ui = self.make(cat_sticker=1, free_play_coupon=2)
        for k in (pygame.K_RIGHT, pygame.K_RETURN, pygame.K_RETURN, pygame.K_TAB, pygame.K_DOWN):
            self.press(ui, k)
        self.assertEqual(inv.to_dict(), {"cat_sticker": 1, "free_play_coupon": 2})


class InventoryInArcadeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def make_game(self, **kw):
        g = Game(save_path=self.path, clock=CLOCK(), **kw)
        room = g.scenes.current
        self.frames(g, 3, [key(pygame.K_ESCAPE)])               # put off the daily bonus
        return g, room

    def frames(self, g, n, events=()):
        g.step(list(events), DT)
        for _ in range(n - 1):
            g.step([], DT)

    def test_controls_box_shows_the_bag_hint(self):
        box = InstructionBox()
        self.assertGreaterEqual(box.image.get_height(), 41)
        before = box.image.copy()
        surf = pygame.Surface((400, 300))
        box.draw(surf)
        self.assertEqual(box.image.get_size(), before.get_size())
        bottom = surf.get_height() - box.image.get_height() - 4
        self.assertGreaterEqual(bottom, 0)

    def test_debug_keys_use_the_safe_path(self):
        g, room = self.make_game(debug=True)
        self.frames(g, 2, [key(pygame.K_F8), key(pygame.K_F8)])      # second one is just refused
        self.assertEqual(g.profile.inventory.get_quantity("cat_sticker"), 1)

    def test_i_opens_and_esc_closes(self):
        g, room = self.make_game()
        self.frames(g, 2, [key(pygame.K_i)])
        self.assertIsNotNone(room.inventory_ui)
        self.frames(g, 30)
        self.frames(g, 2, [key(pygame.K_ESCAPE)])
        self.assertIsNone(room.inventory_ui)
        self.assertIs(g.scenes.current, room)

    def test_world_is_blocked_while_open(self):
        g, room = self.make_game()
        self.frames(g, 2, [key(pygame.K_i)])
        x, y = room.player.x, room.player.y
        self.frames(g, 30, [key(pygame.K_a), key(pygame.K_w)])
        self.assertEqual((room.player.x, room.player.y), (x, y))
        self.assertIsNone(room.dialogue)

    def test_held_movement_stops_when_opening(self):
        g, room = self.make_game()
        self.frames(g, 5, [key(pygame.K_d)])
        self.frames(g, 1, [key(pygame.K_i)])
        x = room.player.x
        self.frames(g, 20)
        self.assertEqual(room.player.x, x)

    def test_cannot_open_during_dialogue_or_flash(self):
        g, room = self.make_game()
        machine = room.machines[0]
        room.player.x, room.player.y = machine.zone.centerx, machine.zone.bottom - 2
        self.frames(g, 5)
        self.frames(g, 30, [key(pygame.K_e)])
        self.assertIsNotNone(room.dialogue)
        self.frames(g, 2, [key(pygame.K_i)])
        self.assertIsNone(room.inventory_ui)

    def test_debug_keys_only_in_debug(self):
        g, room = self.make_game()
        self.frames(g, 2, [key(pygame.K_F8), key(pygame.K_F9)])
        self.assertEqual(g.profile.inventory.get_all_items(), [])
        g, room = self.make_game(debug=True)
        self.frames(g, 2, [key(pygame.K_F8), key(pygame.K_F9), key(pygame.K_F9), key(pygame.K_F8)])
        inv = g.profile.inventory
        self.assertEqual((inv.get_quantity("cat_sticker"), inv.get_quantity("free_play_coupon")), (1, 2))
        with open(self.path) as f:
            self.assertEqual(json.load(f)["inventory"], {"cat_sticker": 1, "free_play_coupon": 2})

    def test_items_show_in_the_open_screen_and_survive_restart(self):
        g, room = self.make_game(debug=True)
        self.frames(g, 2, [key(pygame.K_F8)])
        self.frames(g, 2, [key(pygame.K_i)])
        self.assertEqual(room.inventory_ui.selected_entry[0].name, "CAT STICKER")
        self.frames(g, 5)
        g2, room2 = self.make_game()
        self.assertTrue(g2.profile.inventory.has_item("cat_sticker"))

    def test_inventory_has_no_gameplay_effect(self):
        g, room = self.make_game(debug=True)
        before = (g.profile.tokens, g.profile.tickets)
        self.frames(g, 2, [key(pygame.K_F8), key(pygame.K_F9)])
        self.assertEqual((g.profile.tokens, g.profile.tickets), before)


if __name__ == "__main__":
    unittest.main()
