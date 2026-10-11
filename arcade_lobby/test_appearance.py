"""Tests for Character Creator 2.0: the free basic appearance, its persistence,
the creator screen, Wardrobe editing, the new cosmetics and sprite layering.

Run headless from this folder:   python -m unittest test_appearance -v
"""
import json
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import avatar_style as A  # noqa: E402
from character_creator import CharacterCreatorScene  # noqa: E402
from cosmetics import COSMETICS, SLOTS, CosmeticService  # noqa: E402
from game import Game  # noqa: E402
from item_registry import ITEM_REGISTRY  # noqa: E402
from item_icons import item_icon  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player import DEFAULT_LOOK, FACINGS, P1_LOOK, P2_LOOK, POSES, styled_sheet  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from prize_shop import SHOP_ENTRIES, ShopService, entry_for  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402
from room_testing import goto_room  # noqa: E402
from wardrobe_ui import WardrobeScene  # noqa: E402
from home_stations import WardrobeStation  # noqa: E402

DT = 1 / 60
NEW_ITEMS = ("star_hair_clip", "cat_tail", "neon_headphones", "pixel_crown", "rainbow_jacket",
             "glowing_visor", "champion_badge")


def pixels(surface):
    return pygame.image.tobytes(surface, "RGBA")


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class BasicAppearanceTests(unittest.TestCase):
    def test_every_field_offers_enough_free_options(self):
        self.assertGreaterEqual(len(A.SKIN_TONES), 5)
        self.assertGreaterEqual(len(A.EYE_STYLES), 4)
        self.assertGreaterEqual(len(A.OUTFIT_COLORS), 4)
        self.assertGreaterEqual(len(A.HAIR_COLORS), 3)

    def test_nothing_basic_is_an_inventory_item_or_for_sale(self):
        for field, options in A.OPTIONS.items():
            for o in options:
                self.assertNotIn(o.id, ITEM_REGISTRY, o.id)
                self.assertIsNone(entry_for(o.id))
        self.assertFalse({"skin", "eyes", "hair"} & set(SLOTS))

    def test_default_appearance_is_the_original_character(self):
        for look in (DEFAULT_LOOK, P1_LOOK, P2_LOOK):
            plain = styled_sheet(look, {})
            basic = styled_sheet(look, {}, A.DEFAULT_BASIC) if look is DEFAULT_LOOK else None
            if basic:
                self.assertEqual(pixels(plain["down"]["idle"][0]), pixels(basic["down"]["idle"][0]))

    def test_each_skin_and_eye_style_changes_the_sprite(self):
        base = pixels(styled_sheet(P1_LOOK, {}, A.DEFAULT_BASIC)["down"]["idle"][0])
        for o in A.SKIN_TONES[1:]:
            self.assertNotEqual(pixels(styled_sheet(P1_LOOK, {}, A.BasicAppearance(skin=o.id))["down"]["idle"][0]), base)
        for o in A.EYE_STYLES[1:]:
            self.assertNotEqual(pixels(styled_sheet(P1_LOOK, {}, A.BasicAppearance(eyes=o.id))["down"]["idle"][0]), base)

    def test_outfit_colour_keeps_the_players_outline_and_accent(self):
        look = A.apply_basic(P2_LOOK, A.BasicAppearance(outfit="rose"))
        self.assertEqual((look.outline, look.accent), (P2_LOOK.outline, P2_LOOK.accent))
        self.assertNotEqual(look.shirt, P2_LOOK.shirt)
        self.assertEqual(A.apply_basic(P2_LOOK, A.DEFAULT_BASIC).shirt, P2_LOOK.shirt)    # teal = own colours

    def test_unknown_choices_are_ignored(self):
        b = A.DEFAULT_BASIC.with_choice("skin", "nope").with_choice("hat", "x")
        self.assertEqual(b, A.DEFAULT_BASIC)
        self.assertEqual(A.BasicAppearance.from_dict({"skin": 5, "eyes": "zzz"}), A.DEFAULT_BASIC)
        self.assertEqual(A.BasicAppearance.from_dict("junk"), A.DEFAULT_BASIC)

    def test_dark_skin_keeps_readable_eyes(self):
        look = A.apply_basic(P1_LOOK, A.BasicAppearance(skin="deep"))
        self.assertNotEqual(look.eye, look.skin)
        self.assertGreater(sum(look.eye), sum(look.skin))


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_basic_appearance_round_trips_through_the_profile_file(self):
        path = os.path.join(self.dir, "p.json")
        store = ProfileStore(path)
        profile = store.load()
        store.autosave(profile)
        profile.set_basic_appearance(A.BasicAppearance(skin="deep", eyes="happy", hair="long",
                                                       hair_color="pink", outfit="sky"))
        again = ProfileStore(path).load()
        self.assertEqual(again.basic_appearance, profile.basic_appearance)
        self.assertEqual(again.basic_appearance.skin, "deep")

    def test_an_old_save_without_the_field_keeps_everything_and_gets_defaults(self):
        path = os.path.join(self.dir, "old.json")
        old = PlayerProfile(tickets=33, tokens=7).to_dict()
        old.pop("basic_appearance")
        old["inventory"] = {"neon_cap": 1}
        old["appearance"] = {"hat": "neon_cap"}
        with open(path, "w") as f:
            json.dump(old, f)
        profile = ProfileStore(path).load()
        self.assertEqual(profile.basic_appearance, A.DEFAULT_BASIC)
        self.assertEqual((profile.tickets, profile.tokens), (33, 7))
        self.assertTrue(profile.inventory.has_item("neon_cap"))
        self.assertEqual(profile.appearance, {"hat": "neon_cap"})

    def test_a_damaged_field_falls_back_to_defaults(self):
        data = PlayerProfile().to_dict()
        data["basic_appearance"] = {"skin": ["x"], "eyes": "happy"}
        profile = PlayerProfile.from_dict(data)
        self.assertEqual(profile.basic_appearance.skin, A.DEFAULT_BASIC.skin)
        self.assertEqual(profile.basic_appearance.eyes, "happy")

    def test_changing_the_look_is_free_and_changes_no_wallet_or_inventory(self):
        p = PlayerProfile(tickets=5, tokens=5)
        before = (p.tickets, p.tokens, p.inventory.to_dict())
        for field in A.FIELDS:
            for o in A.OPTIONS[field]:
                p.set_basic_appearance(p.basic_appearance, field, o.id)
        self.assertEqual((p.tickets, p.tokens, p.inventory.to_dict()), before)

    def test_profiles_keep_separate_looks(self):
        a, b = PlayerProfile(profile_id="a"), PlayerProfile(profile_id="b")
        a.set_basic_appearance(A.BasicAppearance(skin="deep"))
        self.assertEqual(b.basic_appearance, A.DEFAULT_BASIC)

    def test_change_notifies_so_avatars_and_autosave_follow(self):
        p, seen, saves = PlayerProfile(), [], []
        p.subscribe(lambda c: seen.append(c.field))
        p.subscribe_save(lambda: saves.append(1))
        p.set_basic_appearance(p.basic_appearance, "skin", "tan")
        p.set_basic_appearance(p.basic_appearance, "skin", "tan")       # no change: no event
        self.assertEqual(seen, ["basic_appearance"])
        self.assertEqual(len(saves), 1)


class CreatorFlowTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.manager = ProfileManager(os.path.join(self.dir, "saves"))
        self.game = Game(profiles=self.manager)
        self.addCleanup(self.game.quit)
        self.results = []

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def creator(self, name="KIT", slot=0):
        scene = CharacterCreatorScene(self.game, self.game.startup, name, P1_LOOK,
                                      self.results.append, lambda: self.results.append("back"))
        self.game.scenes.stack.append(scene)
        return scene

    def press(self, scene, k):
        scene.handle_event(key_event(k))

    def test_keyboard_changes_every_field_and_confirm_returns_the_choice(self):
        s = self.creator()
        for row in range(len(A.FIELDS)):
            self.assertEqual(s.row, row)
            self.press(s, pygame.K_RIGHT)
            self.press(s, pygame.K_DOWN)
        self.assertEqual(s.basic, A.BasicAppearance(*[A.OPTIONS[f][1].id for f in A.FIELDS]))
        self.press(s, pygame.K_DOWN)
        self.assertEqual(s.row, len(A.FIELDS) + 1)
        self.press(s, pygame.K_RETURN)
        self.assertEqual(self.results, [s.basic])

    def test_left_wraps_and_back_reports_back_once(self):
        s = self.creator()
        self.press(s, pygame.K_LEFT)
        self.assertEqual(s.basic.skin, A.SKIN_TONES[-1].id)
        self.press(s, pygame.K_ESCAPE)
        self.press(s, pygame.K_ESCAPE)
        self.assertEqual(self.results, ["back"])

    def test_mouse_selects_swatches_and_buttons(self):
        s = self.creator()
        surf = pygame.Surface((400, 300))
        s.draw(surf)
        size = self.game.screen.get_size()
        rect = next(r for r, cb in s._hit if r.size == (14, 11) and r.y < 70 and r.x > 220)   # 2nd skin swatch
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                   pos=(rect.centerx * size[0] / 400, rect.centery * size[1] / 300))
        s.handle_event(click)
        self.assertNotEqual(s.basic.skin, A.DEFAULT_BASIC.skin)
        s.draw(surf)
        confirm = [r for r, cb in s._hit if r.size == (82, 16)][-1]
        s.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=(confirm.centerx * size[0] / 400, confirm.centery * size[1] / 300)))
        self.assertEqual(self.results, [s.basic])

    def test_preview_shows_front_and_side_and_draws(self):
        s = self.creator()
        surf = pygame.Surface((400, 300))
        s.draw(surf)
        self.assertNotEqual(pixels(s.avatar("down")), pixels(s.avatar("left")))

    def test_new_profile_is_created_only_after_confirm_with_the_chosen_look(self):
        flow = self.game.startup
        flow.count = 1
        flow.show_creator(0, "Mira")
        for _ in range(60):
            self.game.step([], DT)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, CharacterCreatorScene)
        self.assertEqual(len(self.manager), 0)                       # nothing saved yet
        scene.choose("skin", "deep")
        scene.choose("eyes", "sparkle")
        scene.confirm()
        profile = self.manager.load_profile(self.manager.list_profiles()[0].profile_id)
        self.assertEqual((profile.basic_appearance.skin, profile.basic_appearance.eyes), ("deep", "sparkle"))
        # survives a restart of the manager
        again = ProfileManager(os.path.join(self.dir, "saves")).load_profile(profile.profile_id)
        self.assertEqual(again.basic_appearance, profile.basic_appearance)

    def test_back_creates_nothing(self):
        flow = self.game.startup
        flow.count = 1
        flow.show_creator(0, "Mira")
        for _ in range(60):
            self.game.step([], DT)
        self.game.scenes.current.back()
        self.assertEqual(len(self.manager), 0)


class HomeWardrobeTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="wa", display_name="Ann", tickets=500),
                         PlayerProfile(profile_id="wb", display_name="Bo", tickets=500)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.frames(60)
        for _ in range(4):
            if self.room.modal is None:
                break
            self.key(pygame.K_ESCAPE, 10)
        for p in self.room.players:
            p.x, p.y = 200.0, 250.0

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k, frames=1):
        self.game.step([key_event(k)], DT)
        self.frames(frames - 1)

    def open_wardrobe(self, index=0, interact=pygame.K_e):
        station = next(p for p in self.room.props if isinstance(p, WardrobeStation))
        avatar = self.room.players[index]
        avatar.x, avatar.y = station.zone.centerx, station.zone.bottom - 2
        self.frames(5)
        self.key(interact, 40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, WardrobeScene)
        return scene

    def go_to_look_tab(self, scene, field):
        scene.set_tab(scene.TABS.index(("look", field)))

    def test_free_looks_apply_without_ownership_or_tickets(self):
        scene = self.open_wardrobe()
        self.go_to_look_tab(scene, "skin")
        tickets = self.profiles[0].tickets
        scene.select(3)
        scene.activate()
        self.assertEqual(self.profiles[0].basic_appearance.skin, A.SKIN_TONES[3].id)
        self.assertEqual(self.profiles[0].tickets, tickets)
        self.assertEqual(self.room.players[0].look.skin, A.SKIN_TONES[3].value[0])

    def test_previewing_a_free_look_does_not_save_it(self):
        scene = self.open_wardrobe()
        self.go_to_look_tab(scene, "eyes")
        scene.select(2)
        self.assertNotEqual(scene.preview_look().eyes, self.profiles[0].basic_appearance.eyes)
        self.assertEqual(self.profiles[0].basic_appearance, A.DEFAULT_BASIC)

    def test_previewing_an_item_does_not_grant_it_and_unowned_cannot_be_worn(self):
        scene = self.open_wardrobe()
        scene.set_tab(SLOTS.index("jacket"))
        scene.select(1)
        scene.activate()
        self.assertFalse(self.profiles[0].inventory.has_item("rainbow_jacket"))
        self.assertEqual(self.profiles[0].appearance, {})

    def test_p1_and_p2_edit_only_their_own_look(self):
        scene = self.open_wardrobe(1, interact=pygame.K_RETURN)
        self.go_to_look_tab(scene, "hair_color")
        scene.select(4)
        scene.activate()
        self.assertEqual(self.profiles[0].basic_appearance, A.DEFAULT_BASIC)
        self.assertEqual(self.profiles[1].basic_appearance.hair_color, A.HAIR_COLORS[4].id)
        self.assertNotEqual(self.room.players[0].look.hair, self.room.players[1].look.hair)

    def test_the_look_is_the_same_in_every_room(self):
        self.profiles[0].set_basic_appearance(A.BasicAppearance(skin="tan"))
        for room_id in ("arcade_floor", "prize_plaza", "home"):
            goto_room(self.game, room_id)
            self.frames(5)
            self.assertEqual(self.game.hub.avatars[0].look.skin, A.SKIN_TONES[2].value[0])

    def test_wardrobe_draws_every_tab(self):
        scene = self.open_wardrobe()
        surf = pygame.Surface((400, 300))
        for tab in range(len(scene.TABS)):
            scene.set_tab(tab)
            scene.draw(surf)


class NewCosmeticTests(unittest.TestCase):
    def test_all_new_items_exist_are_priced_and_have_icons(self):
        for item_id in NEW_ITEMS:
            self.assertIn(item_id, COSMETICS)
            self.assertIn(item_id, ITEM_REGISTRY)
            self.assertIsNotNone(entry_for(item_id))
            icon = item_icon(ITEM_REGISTRY.get(item_id))
            self.assertNotEqual(ITEM_REGISTRY.get(item_id).icon.get("shape"), None)
            self.assertGreater(pygame.mask.from_surface(icon).count(), 20)
        self.assertEqual(len({i.item_id for i in SHOP_ENTRIES}), len(SHOP_ENTRIES))

    def test_buy_then_equip_then_persist(self):
        dirpath = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, dirpath, True)
        m = ProfileManager(os.path.join(dirpath, "s"))
        profile = m.create_profile("Kit")
        profile.add_tickets(1000)
        service, shop = CosmeticService(profile), ShopService(profile)
        for item_id in NEW_ITEMS:
            slot = COSMETICS[item_id].slot
            self.assertFalse(service.equip(slot, item_id))              # not owned yet
            self.assertTrue(shop.purchase(item_id).success)
            self.assertTrue(service.equip(slot, item_id))
        worn = ProfileManager(os.path.join(dirpath, "s")).load_profile(profile.profile_id)
        self.assertEqual(set(CosmeticService(worn).worn().values()), set(NEW_ITEMS) - {"neon_headphones"})   # one hat at a time: the later one wins

    def test_each_cosmetic_is_visible_in_every_direction_and_pose(self):
        for item_id in NEW_ITEMS:
            slot = COSMETICS[item_id].slot
            for facing in FACINGS:
                if (item_id in ("champion_badge",) and facing == "up"):
                    continue                                              # worn on the chest
                plain = styled_sheet(P1_LOOK, {})[facing]
                worn = styled_sheet(P1_LOOK, {slot: item_id})[facing]
                for kind in ("idle", "walk") + POSES:
                    frames = range(len(worn[kind]))
                    self.assertTrue(any(pixels(worn[kind][i]) != pixels(plain[kind][i]) for i in frames),
                                    (item_id, facing, kind))

    def test_layers_stay_inside_the_sprite_and_keep_the_same_size_per_pose(self):
        full = {"hat": "pixel_crown", "face": "glowing_visor", "accessory": "champion_badge",
                "clip": "star_hair_clip", "tail": "cat_tail", "jacket": "rainbow_jacket"}
        plain, dressed = styled_sheet(P1_LOOK, {}), styled_sheet(P1_LOOK, full)
        for facing in FACINGS:
            for kind in ("idle", "walk") + POSES:
                for a, b in zip(plain[facing][kind], dressed[facing][kind]):
                    self.assertEqual(a.get_size(), b.get_size())
                    self.assertGreater(pygame.mask.from_surface(b).count(), 0)

    def test_hat_slot_items_replace_each_other_and_other_slots_stack(self):
        p = PlayerProfile()
        for i in ("pixel_crown", "neon_headphones", "cat_tail", "rainbow_jacket"):
            p.inventory.add_item(i)
        s = CosmeticService(p)
        s.equip("hat", "pixel_crown")
        s.equip("hat", "neon_headphones")
        s.equip("tail", "cat_tail")
        s.equip("jacket", "rainbow_jacket")
        self.assertEqual(s.worn(), {"hat": "neon_headphones", "tail": "cat_tail", "jacket": "rainbow_jacket"})


if __name__ == "__main__":
    unittest.main()
