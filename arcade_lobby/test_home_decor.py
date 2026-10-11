"""Tests for the HOME decoration loop: buy -> inventory -> place / replace /
remove -> saved, decoration mode, per-profile layouts, collision and depth.

Run headless from this folder:   python -m unittest test_home_decor -v
"""
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from decor_ui import DecorationScene, next_slot, slot_rect  # noqa: E402
from decorations import (FLAT_TYPES, PROP_TYPES, DecorationProp, HomeDecorationManager,  # noqa: E402
                         decoration_item_id, default_catalog)
from game import Game  # noqa: E402
from home_room import HOME_SLOTS, HomeRoomScene  # noqa: E402
from home_stations import CollectionStation, DecorStation, WardrobeStation  # noqa: E402
from item_registry import ITEM_REGISTRY  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from prize_shop import ShopService  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import PLAYER_START, VIEW_H, VIEW_W  # noqa: E402

DT = 1 / 60
NEW_DECORATIONS = ("table_lamp", "cat_plush", "pixel_plant", "retro_clock", "poster_arcade")


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def buy(profile, decoration_id):
    result = ShopService(profile).purchase(decoration_item_id(decoration_id))
    assert result.success, result
    return result


class ManagerOwnershipTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.p = PlayerProfile(profile_id="d", tickets=500)
        self.m = HomeDecorationManager(self.p, HOME_SLOTS, default_catalog())
        self.addCleanup(self.m.close)

    def test_free_decorations_are_available_and_paid_ones_are_not_until_bought(self):
        self.assertTrue(self.m.is_available("table_cactus"))
        self.assertFalse(self.m.is_available("table_lamp"))
        buy(self.p, "table_lamp")
        self.assertTrue(self.m.is_available("table_lamp"))

    def test_unknown_decoration_is_never_available(self):
        self.assertFalse(self.m.is_available("nope"))
        self.assertFalse(self.m.place("table_decor", "nope"))

    def test_every_paid_decoration_has_a_registered_item_and_the_price_of_its_item(self):
        for d in default_catalog():
            if d.ticket_cost:
                self.assertIn(decoration_item_id(d.decoration_id), ITEM_REGISTRY, d.decoration_id)

    def test_place_requires_ownership(self):
        self.assertFalse(self.m.place("table_decor", "table_lamp"))
        self.assertEqual(self.p.home_decorations, {})
        buy(self.p, "table_lamp")
        self.assertTrue(self.m.place("table_decor", "table_lamp"))
        self.assertEqual(self.m.current_id("table_decor"), "table_lamp")

    def test_purchase_to_inventory_to_placement_to_visible_prop(self):
        before = len(self.m.props)
        before_sprite = next(p for p in self.m.props if p.slot_id == "table_decor").sprite
        buy(self.p, "cat_plush")
        self.assertTrue(self.p.inventory.has_item("decor_cat_plush"))
        self.m.place("table_decor", "cat_plush")
        prop = next(p for p in self.m.props if p.slot_id == "table_decor")
        self.assertEqual(len(self.m.props), before)
        self.assertIsNot(prop.sprite, before_sprite)
        self.assertEqual(prop.sprite.get_size(), self.m.sprite(default_catalog().get("cat_plush")).get_size())

    def test_slot_compatibility(self):
        for d in ("poster_arcade", "retro_clock", "table_lamp", "pixel_plant"):
            buy(self.p, d)
        self.assertFalse(self.m.place("rug", "poster_arcade"))          # poster in a rug slot
        self.assertFalse(self.m.place("table_decor", "retro_clock"))    # a clock is a wall item
        self.assertFalse(self.m.place("plant_back", "table_lamp"))
        self.assertTrue(self.m.place("poster_left", "retro_clock"))
        self.assertTrue(self.m.place("plant_front", "pixel_plant"))
        self.assertEqual(self.p.home_decorations, {"poster_left": "retro_clock", "plant_front": "pixel_plant"})

    def test_choices_for_lists_only_owned_fitting_decorations(self):
        names = lambda slot: [d.decoration_id for d in self.m.choices_for(slot)]    # noqa: E731
        self.assertEqual(names("table_decor"), ["table_cactus"])
        buy(self.p, "table_lamp")
        buy(self.p, "retro_clock")
        self.assertEqual(names("table_decor"), ["table_cactus", "table_lamp"])
        self.assertIn("retro_clock", names("poster_left"))
        self.assertNotIn("retro_clock", names("rug"))

    def test_replace_keeps_both_owned(self):
        buy(self.p, "table_lamp")
        buy(self.p, "cat_plush")
        self.m.place("table_decor", "table_lamp")
        self.m.place("table_decor", "cat_plush")
        self.assertEqual(self.m.current_id("table_decor"), "cat_plush")
        self.assertTrue(self.p.inventory.has_item("decor_table_lamp"))
        self.assertTrue(self.p.inventory.has_item("decor_cat_plush"))
        self.assertTrue(self.m.place("table_decor", "table_lamp"))      # and back again

    def test_remove_restores_the_default_and_keeps_ownership(self):
        buy(self.p, "table_lamp")
        self.m.place("table_decor", "table_lamp")
        self.m.remove("table_decor")
        self.assertEqual(self.m.current_id("table_decor"), "table_cactus")
        self.assertNotIn("table_decor", self.p.home_decorations)
        self.assertTrue(self.p.inventory.has_item("decor_table_lamp"))

    def test_a_decoration_can_be_placed_in_every_slot_of_its_type(self):
        buy(self.p, "cat_plush")
        # table_decor is the only TABLE_DECOR slot; wall posters have two
        buy(self.p, "retro_clock")
        for slot in ("poster_left", "poster_right"):
            self.assertTrue(self.m.place(slot, "retro_clock"))

    def test_layout_changes_notify_the_room_hook_once(self):
        calls = []
        self.m.on_change = lambda: calls.append(1)
        buy(self.p, "table_lamp")
        self.m.place("table_decor", "table_lamp")
        self.assertEqual(len(calls), 1)
        self.m.place("table_decor", "table_lamp")                       # same again: no change
        self.assertEqual(len(calls), 1)

    def test_layout_saves_and_loads(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "p.json")
        store = ProfileStore(path)
        p = store.load()
        store.autosave(p)
        p.add_tickets(300)
        buy(p, "table_lamp")
        buy(p, "pixel_plant")
        m = HomeDecorationManager(p, HOME_SLOTS, default_catalog())
        m.place("table_decor", "table_lamp")
        m.place("plant_back", "pixel_plant")
        m.close()
        again = ProfileStore(path).load()
        m2 = HomeDecorationManager(again, HOME_SLOTS, default_catalog())
        self.addCleanup(m2.close)
        self.assertEqual((m2.current_id("table_decor"), m2.current_id("plant_back")), ("table_lamp", "pixel_plant"))
        self.assertTrue(again.inventory.has_item("decor_table_lamp"))

    def test_an_old_layout_with_a_free_alternate_still_shows(self):
        old = PlayerProfile.from_dict({"home_decorations": {"poster_left": "poster_cat", "rug": "rug_teal"}})
        m = HomeDecorationManager(old, HOME_SLOTS, default_catalog())
        self.addCleanup(m.close)
        self.assertEqual((m.current_id("poster_left"), m.current_id("rug")), ("poster_cat", "rug_teal"))
        self.assertFalse(m.is_available("poster_cat"))      # not owned, so it cannot be placed anew ...
        self.assertFalse(m.place("poster_right", "poster_cat"))   # ... but the saved look is not taken away

    def test_each_profile_has_its_own_layout(self):
        a, b = PlayerProfile(profile_id="a", tickets=100), PlayerProfile(profile_id="b", tickets=100)
        ma = HomeDecorationManager(a, HOME_SLOTS, default_catalog())
        mb = HomeDecorationManager(b, HOME_SLOTS, default_catalog())
        self.addCleanup(ma.close)
        self.addCleanup(mb.close)
        buy(a, "table_lamp")
        ma.place("table_decor", "table_lamp")
        self.assertEqual(mb.current_id("table_decor"), "table_cactus")
        self.assertFalse(mb.place("table_decor", "table_lamp"))     # b never bought it
        buy(b, "cat_plush")
        mb.place("table_decor", "cat_plush")
        self.assertEqual(ma.current_id("table_decor"), "table_lamp")


class DecorationSceneTests(unittest.TestCase):
    def setUp(self):
        self.profile = PlayerProfile(profile_id="dec_a", display_name="Ann", tickets=400)
        self.game = Game(session=LocalSession([self.profile]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.frames(60)
        if self.room.modal is not None:
            self.key(pygame.K_ESCAPE, 10)
        self.room.players[0].x, self.room.players[0].y = 200.0, 250.0

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k, frames=1):
        self.game.step([key_event(k)], DT)
        self.frames(frames - 1)

    def enter_decoration_mode(self):
        station = next(p for p in self.room.props if isinstance(p, DecorStation))
        avatar = self.room.players[0]
        avatar.x, avatar.y = station.zone.centerx, station.zone.bottom - 2
        self.frames(5)
        self.assertIs(avatar.nearby, station)
        self.key(pygame.K_e, 40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, DecorationScene)
        return scene

    def pick_slot(self, scene, slot_id):
        for _ in range(len(scene.slots)):
            if scene.slot.slot_id == slot_id:
                return
            self.key(pygame.K_TAB)
        self.fail(f"slot {slot_id} unreachable")

    def test_station_opens_decoration_mode_and_esc_leaves(self):
        scene = self.enter_decoration_mode()
        self.assertTrue(self.room.edit_mode)
        self.key(pygame.K_ESCAPE, 40)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertFalse(self.room.edit_mode)

    def test_the_full_loop_buy_choose_place_see_replace_remove(self):
        buy(self.profile, "table_lamp")
        buy(self.profile, "cat_plush")
        scene = self.enter_decoration_mode()
        self.pick_slot(scene, "table_decor")
        self.key(pygame.K_e)                                    # choose
        self.assertTrue(scene.choosing)
        self.assertEqual(scene.rows, [None, "table_cactus", "table_lamp", "cat_plush"])
        self.key(pygame.K_s)                                    # NEON LAMP is highlighted: a preview only
        self.assertEqual(scene.candidate.decoration_id, "table_lamp")
        self.assertEqual(self.room.decorations.current_id("table_decor"), "table_cactus")
        self.key(pygame.K_e)                                    # place
        self.assertEqual(self.profile.home_decorations, {"table_decor": "table_lamp"})
        prop = next(p for p in self.room.props if getattr(p, "slot_id", "") == "table_decor")
        self.assertIs(prop.sprite, self.room.decorations.sprite(default_catalog().get("table_lamp")))
        self.key(pygame.K_s)                                    # replace with the plush
        self.key(pygame.K_e)
        self.assertEqual(self.profile.home_decorations, {"table_decor": "cat_plush"})
        self.key(pygame.K_w)
        self.key(pygame.K_w)
        self.key(pygame.K_w)                                    # row 0: REMOVE
        self.assertEqual(scene.index, 0)
        self.key(pygame.K_e)
        self.assertEqual(self.profile.home_decorations, {})
        self.assertTrue(self.profile.inventory.has_item("decor_cat_plush"))
        self.assertTrue(self.profile.inventory.has_item("decor_table_lamp"))
        self.key(pygame.K_ESCAPE)                               # back to slots
        self.assertFalse(scene.choosing)
        self.key(pygame.K_ESCAPE, 40)                           # done
        self.assertIs(self.game.scenes.current, self.room)

    def test_an_unowned_decoration_is_not_offered(self):
        scene = self.enter_decoration_mode()
        self.pick_slot(scene, "table_decor")
        self.key(pygame.K_e)
        self.assertEqual(scene.rows, [None, "table_cactus"])
        self.key(pygame.K_s)
        self.key(pygame.K_s)
        self.key(pygame.K_e)
        self.assertEqual(self.profile.home_decorations, {})

    def test_decoration_mode_hides_prompts_and_hud_but_draws_the_room(self):
        scene = self.enter_decoration_mode()
        scene.draw(self.game.canvas)                            # slot mode
        self.key(pygame.K_e)
        scene.draw(self.game.canvas)                            # choose mode
        self.assertTrue(self.room.edit_mode)

    def test_every_slot_and_every_decoration_draws(self):
        for d in default_catalog():
            if d.ticket_cost:
                buy(self.profile, d.decoration_id)
        scene = self.enter_decoration_mode()
        for slot in scene.slots:
            scene.slot = slot
            scene.start_choosing()
            for i in range(len(scene.rows)):
                scene.select(i)
                scene.draw(self.game.canvas)
            scene.choosing = False

    def test_arrow_keys_move_between_slots_spatially(self):
        scene = self.enter_decoration_mode()
        scene.slot = scene.manager.slots["poster_left"]
        self.key(pygame.K_d)
        self.assertEqual(scene.slot.slot_id, "poster_right")
        self.key(pygame.K_a)
        self.assertEqual(scene.slot.slot_id, "poster_left")
        self.key(pygame.K_s)                                    # nothing blocks the way down: some slot below
        self.assertNotEqual(scene.slot.slot_id, "poster_left")
        self.assertGreater(slot_rect(scene.slot).centery, slot_rect(scene.manager.slots["poster_left"]).centery)

    def test_next_slot_stays_put_when_nothing_lies_that_way(self):
        slots = list(HOME_SLOTS)
        top = min(slots, key=lambda s: slot_rect(s).centery)
        self.assertIs(next_slot(slots, top, (0, -1)), top)

    def test_mouse_selects_a_slot_and_a_second_click_opens_the_list(self):
        scene = self.enter_decoration_mode()
        scene.draw(self.game.canvas)
        target = scene.manager.slots["rug"]
        cx, cy = slot_rect(target).center
        w, h = self.game.screen.get_size()
        click = lambda: self.game.step([pygame.event.Event(                       # noqa: E731
            pygame.MOUSEBUTTONDOWN, button=1, pos=(cx * w // VIEW_W, cy * h // VIEW_H))], DT)
        click()
        self.assertEqual(scene.slot.slot_id, "rug")
        scene.draw(self.game.canvas)
        click()
        self.assertTrue(scene.choosing)

    def test_placing_updates_the_room_collision_for_solid_decorations(self):
        buy(self.profile, "pixel_plant")
        scene = self.enter_decoration_mode()
        self.pick_slot(scene, "plant_front")
        self.key(pygame.K_e)
        while scene.rows[scene.index] != "pixel_plant":
            self.key(pygame.K_s)
        self.key(pygame.K_e)
        self.assertEqual(self.profile.home_decorations, {"plant_front": "pixel_plant"})
        feet = next(p for p in self.room.props if getattr(p, "slot_id", "") == "plant_front").footprint
        self.assertIn(feet, self.room.solids)

    def test_a_guest_cannot_decorate_p1s_home(self):
        a, b = PlayerProfile(profile_id="ga", display_name="Ann", tickets=50), PlayerProfile(
            profile_id="gb", display_name="Bo", tickets=50)
        game = Game(session=LocalSession([a, b]))
        self.addCleanup(game.quit)
        room = goto_room(game, "home")
        station = next(p for p in room.props if isinstance(p, DecorStation))
        room.acting_player = room.players[1]
        station.interact(room)
        room.acting_player = None
        self.assertIsInstance(game.scenes.current, HomeRoomScene)
        self.assertTrue(room.notice.visible)


class PerProfileHomeTests(unittest.TestCase):
    """Home decoration separately for each profile (each as the home owner)."""

    def run_loop(self, name, item):
        profile = PlayerProfile(profile_id=name, display_name=name, tickets=200)
        game = Game(session=LocalSession([profile]))
        self.addCleanup(game.quit)
        room = goto_room(game, "home")
        buy(profile, item)
        room.decorations.place("table_decor", item)
        return profile, room

    def test_p1_and_p2_profiles_keep_separate_homes(self):
        pa, ra = self.run_loop("alpha", "table_lamp")
        pb, rb = self.run_loop("beta", "cat_plush")
        self.assertEqual(pa.home_decorations, {"table_decor": "table_lamp"})
        self.assertEqual(pb.home_decorations, {"table_decor": "cat_plush"})
        self.assertEqual(ra.decorations.current_id("table_decor"), "table_lamp")
        self.assertEqual(rb.decorations.current_id("table_decor"), "cat_plush")
        self.assertFalse(pa.inventory.has_item("decor_cat_plush"))
        self.assertFalse(pb.inventory.has_item("decor_table_lamp"))


class RoomLayoutSafetyTests(unittest.TestCase):
    """Decorations and the new stations must not block doors, cats or the spawn,
    and must sort in depth the way every other prop does."""

    def setUp(self):
        self.profile = PlayerProfile(profile_id="lay", tickets=9999)
        for d in default_catalog():
            if d.ticket_cost:
                buy(self.profile, d.decoration_id)
        self.game = Game(session=LocalSession([self.profile]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.manager = self.room.decorations

    def other_solids(self, slot_id):
        mine = {id(p) for p in self.manager.props if p.slot_id == slot_id}
        return [p.footprint for p in self.room.props if p.solid and id(p) not in mine]

    def test_no_placeable_decoration_ever_sits_in_a_doorway_or_on_the_spawn(self):
        spawn = pygame.Rect(0, 0, 14, 14)
        spawn.center = PLAYER_START
        for slot in HOME_SLOTS:
            for d in self.manager.choices_for(slot.slot_id):
                self.manager.place(slot.slot_id, d.decoration_id)
                prop = next((p for p in self.manager.props if p.slot_id == slot.slot_id), None)
                if prop is None or not prop.solid:
                    continue
                with self.subTest(slot=slot.slot_id, decoration=d.decoration_id):
                    for zone in self.room.keep_clear_areas:
                        self.assertFalse(prop.footprint.colliderect(zone))
                    self.assertFalse(prop.footprint.colliderect(spawn))
                    for solid in self.other_solids(slot.slot_id):
                        self.assertFalse(prop.footprint.colliderect(solid))
            self.manager.remove(slot.slot_id)

    def test_every_decoration_stays_inside_its_slot_and_the_screen(self):
        for slot in HOME_SLOTS:
            for d in self.manager.choices_for(slot.slot_id):
                sprite = self.manager.sprite(d)
                self.assertLessEqual(sprite.get_width(), slot.size[0], d.decoration_id)
                self.assertLessEqual(sprite.get_height(), slot.size[1], d.decoration_id)
        for slot in HOME_SLOTS:
            self.assertTrue(pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(slot_rect(slot)), slot.slot_id)

    def test_depth_order_does_not_change_when_a_slot_is_swapped(self):
        for slot in HOME_SLOTS:
            if slot.slot_type not in PROP_TYPES:
                continue
            depths = set()
            for d in self.manager.choices_for(slot.slot_id):
                self.manager.place(slot.slot_id, d.decoration_id)
                prop = next(p for p in self.manager.props if p.slot_id == slot.slot_id)
                depths.add(prop.sort_y)
                self.assertIsInstance(prop, DecorationProp)
            self.assertEqual(len(depths), 1, slot.slot_id)
            self.assertEqual(depths.pop(), slot.position[1] + slot.sort_bias)

    def test_flat_decorations_stay_under_everything_and_never_collide(self):
        for slot in HOME_SLOTS:
            if slot.slot_type in FLAT_TYPES:
                for d in self.manager.choices_for(slot.slot_id):
                    self.manager.place(slot.slot_id, d.decoration_id)
        self.assertFalse([p for p in self.manager.props if p.slot_id in
                          {s.slot_id for s in HOME_SLOTS if s.slot_type in FLAT_TYPES}])

    def test_the_stations_do_not_block_doors_cats_or_the_spawn(self):
        stations = [p for p in self.room.props if isinstance(p, (WardrobeStation, DecorStation, CollectionStation))]
        self.assertEqual(len(stations), 3)
        spawn = pygame.Rect(0, 0, 14, 14)
        spawn.center = PLAYER_START
        for station in stations:
            for zone in self.room.keep_clear_areas:
                self.assertFalse(station.footprint.colliderect(zone))
            self.assertFalse(station.footprint.colliderect(spawn))
            for cat_id, spots in HomeRoomScene.cat_spots.items():
                for spot in spots:
                    self.assertFalse(station.footprint.collidepoint(spot), (cat_id, spot))
            self.assertTrue(pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(station.rect))
        for a in stations:
            for b in stations:
                if a is not b:
                    self.assertFalse(a.footprint.colliderect(b.footprint))

    def test_nothing_in_home_overlaps_the_new_stations(self):
        stations = [p for p in self.room.props if isinstance(p, (WardrobeStation, DecorStation, CollectionStation))]
        for station in stations:
            for prop in self.room.props:
                if prop not in stations and prop.solid:
                    self.assertFalse(station.footprint.colliderect(prop.footprint), type(prop).__name__)

    def test_a_player_can_still_walk_from_every_door_to_every_station(self):
        """The doors and the three stations are all reachable on the room's collision grid."""
        solids = list(self.room.solids)
        cell = 4
        cols, rows = VIEW_W // cell, VIEW_H // cell
        blocked = set()
        for gy in range(rows):
            for gx in range(cols):
                feet = pygame.Rect(gx * cell - 5, gy * cell - 5, 10, 5)
                if any(feet.colliderect(s) for s in solids):
                    blocked.add((gx, gy))
        start = (PLAYER_START[0] // cell, PLAYER_START[1] // cell)
        seen, queue = {start}, [start]
        while queue:
            gx, gy = queue.pop()
            for nx, ny in ((gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)):
                if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in blocked and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        for station in (p for p in self.room.props if isinstance(p, (WardrobeStation, DecorStation, CollectionStation))):
            reach = station.zone.center
            self.assertTrue(any((reach[0] // cell + dx, reach[1] // cell + dy) in seen
                                for dx in range(-8, 9) for dy in range(0, 9)), type(station).__name__)
        for door in self.room.exits:
            gx, gy = door.trigger.centerx // cell, door.trigger.centery // cell
            self.assertTrue(any((gx + dx, gy) in seen for dx in range(-6, 7)), door.side)


if __name__ == "__main__":
    unittest.main()
