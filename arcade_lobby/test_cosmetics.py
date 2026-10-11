"""Tests for avatar customisation: ownership, slots, saving, sprite layers,
the WARDROBE screen, and P1 / P2 wearing different things.

Run headless from this folder:   python -m unittest test_cosmetics -v
"""
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from cosmetics import (ACCESSORY, COSMETICS, FACE, HAT, PALETTE, SLOTS, CosmeticService,  # noqa: E402
                       apply_palette, cosmetics_for, resolve_appearance)
from game import Game  # noqa: E402
from home_stations import WardrobeStation  # noqa: E402
from item_registry import ITEM_REGISTRY  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player import (CAP, DEFAULT_LOOK, FACINGS, HubPlayer, P1_LOOK, P2_LOOK, PLAYER_SPEED,  # noqa: E402
                    _draw_frame, outfit_of, player_sheet, styled_sheet)
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from preview_art import avatar_image  # noqa: E402
from room_testing import goto_room  # noqa: E402
from wardrobe_ui import WardrobeScene  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def pixels(surface):
    return pygame.image.tobytes(surface, "RGBA")


def top_row_with(surface, rgb):
    """The first y that has a pixel of exactly this colour, else None."""
    w, h = surface.get_size()
    for y in range(h):
        for x in range(w):
            if tuple(surface.get_at((x, y)))[:3] == rgb:
                return y
    return None


class CosmeticDataTests(unittest.TestCase):
    def test_every_cosmetic_is_an_inventory_item_with_a_known_slot(self):
        for c in COSMETICS.values():
            self.assertIn(c.item_id, ITEM_REGISTRY)
            self.assertIn(c.slot, SLOTS)

    def test_slots_have_content(self):
        for slot in SLOTS:
            self.assertTrue(cosmetics_for(slot), slot)
        self.assertGreaterEqual(len(cosmetics_for(HAT)), 2)
        self.assertGreaterEqual(len(cosmetics_for(PALETTE)), 3)

    def test_palette_keeps_the_players_outline_and_ui_accent(self):
        look = apply_palette(P2_LOOK, "palette_mint")
        self.assertNotEqual(look.shirt, P2_LOOK.shirt)
        self.assertEqual((look.outline, look.accent, look.name), (P2_LOOK.outline, P2_LOOK.accent, "p2"))
        self.assertEqual(apply_palette(P2_LOOK, "neon_cap"), P2_LOOK)       # not a palette
        self.assertEqual(apply_palette(P2_LOOK, None), P2_LOOK)


class CosmeticServiceTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(profile_id="a")
        self.s = CosmeticService(self.p)

    def test_unowned_items_cannot_be_worn(self):
        self.assertFalse(self.s.equip(HAT, "neon_cap"))
        self.assertEqual(self.p.appearance, {})

    def test_owned_items_can_be_worn_and_removed(self):
        self.p.inventory.add_item("neon_cap")
        self.assertTrue(self.s.equip(HAT, "neon_cap"))
        self.assertEqual(self.s.worn(), {HAT: "neon_cap"})
        self.assertTrue(self.s.unequip(HAT))
        self.assertEqual(self.s.worn(), {})
        self.assertFalse(self.s.unequip(HAT))                # nothing left to remove

    def test_only_compatible_items_fit_a_slot(self):
        for item in ("neon_cap", "retro_sunglasses", "star_pin", "palette_mint"):
            self.p.inventory.add_item(item)
        self.assertFalse(self.s.equip(FACE, "neon_cap"))
        self.assertFalse(self.s.equip(HAT, "retro_sunglasses"))
        self.assertFalse(self.s.equip(PALETTE, "star_pin"))
        self.assertFalse(self.s.equip(ACCESSORY, "palette_mint"))
        self.assertFalse(self.s.equip(HAT, "cat_sticker"))   # a collectible is not a cosmetic
        self.assertFalse(self.s.equip("feet", "neon_cap"))   # no such slot
        self.assertEqual(self.p.appearance, {})

    def test_a_slot_holds_one_item_and_slots_are_independent(self):
        for item in ("neon_cap", "cat_ears", "retro_sunglasses"):
            self.p.inventory.add_item(item)
        self.s.equip(HAT, "neon_cap")
        self.s.equip(FACE, "retro_sunglasses")
        self.s.equip(HAT, "cat_ears")                        # replaces the cap
        self.assertEqual(self.s.worn(), {HAT: "cat_ears", FACE: "retro_sunglasses"})

    def test_an_item_that_is_no_longer_owned_is_not_worn(self):
        self.p.inventory.add_item("neon_cap")
        self.s.equip(HAT, "neon_cap")
        self.p.inventory.remove_item("neon_cap")
        self.assertEqual(resolve_appearance(self.p), {})

    def test_appearance_is_saved_and_loaded_per_profile(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "p.json")
        store = ProfileStore(path)
        p = store.load()
        store.autosave(p)
        p.inventory.add_item("cat_ears")
        p.inventory.add_item("palette_grape")
        s = CosmeticService(p)
        s.equip(HAT, "cat_ears")
        s.equip(PALETTE, "palette_grape")
        again = ProfileStore(path).load()
        self.assertEqual(CosmeticService(again).worn(), {HAT: "cat_ears", PALETTE: "palette_grape"})

    def test_bad_saved_appearance_is_ignored(self):
        p = PlayerProfile.from_dict({"appearance": {"hat": 5, "face": "neon_cap", 3: "x", "pin": "star_pin"}})
        self.assertEqual(CosmeticService(p).worn(), {})      # nothing owned / wrong slot / bad types


class SpriteLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_every_frame_keeps_the_same_size_with_any_outfit(self):
        base = player_sheet(P1_LOOK)
        outfit = player_sheet(P1_LOOK, ("neon_cap", "retro_sunglasses", "star_pin"))
        for f in FACINGS:
            for anim in ("idle", "walk"):
                self.assertEqual([fr.get_size() for fr in base[f][anim]],
                                 [fr.get_size() for fr in outfit[f][anim]])

    def test_a_cosmetic_changes_pixels_but_the_default_outfit_is_unchanged(self):
        self.assertEqual(pixels(_draw_frame("down", look=P1_LOOK)), pixels(player_sheet(P1_LOOK)["down"]["idle"][0]))
        for outfit in (("neon_cap", None, None), ("cat_ears", None, None), (None, "retro_sunglasses", None),
                       (None, None, "star_pin")):
            with self.subTest(outfit=outfit):
                self.assertNotEqual(pixels(_draw_frame("down", look=P1_LOOK, outfit=outfit)),
                                    pixels(_draw_frame("down", look=P1_LOOK)))

    def test_the_hat_replaces_the_beanie(self):
        beanie = P1_LOOK.beanie

        def head(frame):                    # the rows above the shoulders (the shirt logo shares the colour)
            return frame.subsurface((0, 0, frame.get_width(), 8))
        self.assertIsNotNone(top_row_with(head(_draw_frame("down", look=P1_LOOK)), beanie))
        self.assertIsNone(top_row_with(head(_draw_frame("down", look=P1_LOOK, outfit=("cat_ears", None, None))),
                                       beanie))

    def test_layers_follow_the_body_bob_in_every_direction(self):
        """The cap sits one pixel lower exactly when the body bobs one pixel lower."""
        for facing in FACINGS:
            with self.subTest(facing=facing):
                level = _draw_frame(facing, bob=0, look=P1_LOOK, outfit=("neon_cap", None, None))
                bobbed = _draw_frame(facing, bob=1, look=P1_LOOK, outfit=("neon_cap", None, None))
                self.assertEqual(top_row_with(bobbed, CAP), top_row_with(level, CAP) + 1)

    def test_glasses_and_pin_move_with_the_body_too(self):
        for facing, colour in (("down", (28, 22, 60)), ("left", (28, 22, 60))):
            level = _draw_frame(facing, bob=0, look=P1_LOOK, outfit=(None, "retro_sunglasses", None))
            bobbed = _draw_frame(facing, bob=1, look=P1_LOOK, outfit=(None, "retro_sunglasses", None))
            self.assertEqual(top_row_with(bobbed, colour), top_row_with(level, colour) + 1, facing)
        gold = (255, 214, 90)
        a = _draw_frame("down", bob=0, look=P1_LOOK, outfit=(None, None, "star_pin"))
        b = _draw_frame("down", bob=1, look=P1_LOOK, outfit=(None, None, "star_pin"))
        self.assertEqual(top_row_with(b, gold), top_row_with(a, gold) + 1)

    def test_the_pin_is_hidden_from_behind_and_sunglasses_show_only_arms_there(self):
        gold = (255, 214, 90)
        self.assertIsNone(top_row_with(_draw_frame("up", look=P1_LOOK, outfit=(None, None, "star_pin")), gold))

    def test_idle_and_walk_cycles_are_all_dressed(self):
        outfit = ("neon_cap", None, None)
        sheet = player_sheet(P1_LOOK, outfit)
        for f in FACINGS:
            for frame in sheet[f]["idle"] + sheet[f]["walk"]:
                self.assertIsNotNone(top_row_with(frame, CAP), f)

    def test_palette_recolours_the_outfit(self):
        plain = player_sheet(P1_LOOK)["down"]["idle"][0]
        sunset = styled_sheet(P1_LOOK, {PALETTE: "palette_sunset"})["down"]["idle"][0]
        self.assertNotEqual(pixels(plain), pixels(sunset))
        self.assertIsNotNone(top_row_with(sunset, COSMETICS["palette_sunset"].colors[0]))

    def test_preview_image_matches_the_in_world_frame(self):
        appearance = {HAT: "cat_ears", FACE: "retro_sunglasses"}
        self.assertEqual(pixels(avatar_image(P1_LOOK, appearance, "down", 0)),
                         pixels(styled_sheet(P1_LOOK, appearance)["down"]["idle"][0]))

    def test_outfit_of_reads_the_three_layer_slots(self):
        self.assertEqual(outfit_of({HAT: "a", FACE: "b", ACCESSORY: "c", PALETTE: "d"}), ("a", "b", "c", None, None, None))


class AvatarInTheHubTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="ca", display_name="Ann", tickets=50),
                         PlayerProfile(profile_id="cb", display_name="Bo", tickets=50)]
        self.session = LocalSession(self.profiles)
        self.game = Game(session=self.session)
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.p1, self.p2 = self.room.players

    def dress(self, profile, **items):
        for item in items.values():
            profile.inventory.add_item(item)
        s = CosmeticService(profile)
        for slot, item in items.items():
            self.assertTrue(s.equip(slot, item))

    def test_the_avatar_changes_when_the_profile_equips(self):
        before = pixels(self.p1.image)
        self.dress(self.profiles[0], hat="neon_cap")
        self.assertEqual(self.p1.appearance, {HAT: "neon_cap"})
        self.assertNotEqual(pixels(self.p1.image), before)

    def test_p1_and_p2_can_look_different_at_the_same_time(self):
        self.dress(self.profiles[0], hat="neon_cap", face="retro_sunglasses")
        self.dress(self.profiles[1], hat="cat_ears", palette="palette_mint")
        self.assertEqual(self.p1.appearance, {HAT: "neon_cap", FACE: "retro_sunglasses"})
        self.assertEqual(self.p2.appearance, {HAT: "cat_ears", PALETTE: "palette_mint"})
        self.assertNotEqual(pixels(self.p1.image), pixels(self.p2.image))

    def test_one_players_wardrobe_does_not_dress_the_other(self):
        self.dress(self.profiles[0], hat="neon_cap")
        self.assertEqual(self.p2.appearance, {})
        self.assertEqual(self.profiles[1].appearance, {})

    def test_removing_returns_to_the_default_frames(self):
        default = pixels(self.p1.image)
        self.dress(self.profiles[0], hat="neon_cap")
        CosmeticService(self.profiles[0]).unequip(HAT)
        self.assertEqual(pixels(self.p1.image), default)

    def test_losing_the_item_undresses_the_avatar(self):
        self.dress(self.profiles[0], hat="neon_cap")
        self.profiles[0].inventory.remove_item("neon_cap")
        self.assertEqual(self.p1.appearance, {})

    def test_a_new_session_starts_dressed_from_the_save(self):
        self.dress(self.profiles[0], hat="cat_ears")
        again = LocalSession([PlayerProfile.from_dict(self.profiles[0].to_dict())])
        self.assertEqual(again.avatars[0].appearance, {HAT: "cat_ears"})

    def test_animation_state_and_frame_survive_a_change_of_clothes(self):
        self.p1.facing = "left"
        self.p1.update(DT, (-1, 0), [])
        self.p1.update(DT * 7, (-1, 0), [])
        name, frame = self.p1.anim.name, self.p1.anim.frame_index
        self.dress(self.profiles[0], hat="neon_cap")
        self.assertEqual((self.p1.anim.name, self.p1.anim.frame_index), (name, frame))
        self.assertEqual(name, "walk_left")

    def test_collision_box_speed_and_movement_are_unchanged_by_cosmetics(self):
        plain = HubPlayer((200, 200), profile=PlayerProfile(profile_id="x"), look=P1_LOOK)
        dressed_profile = PlayerProfile(profile_id="y")
        for item in ("neon_cap", "retro_sunglasses", "star_pin"):
            dressed_profile.inventory.add_item(item)
        CosmeticService(dressed_profile).equip(HAT, "neon_cap")
        dressed = HubPlayer((200, 200), profile=dressed_profile, look=P1_LOOK)
        solids = [pygame.Rect(240, 150, 10, 100)]
        for _ in range(120):
            plain.update(DT, (1, 0), solids)
            dressed.update(DT, (1, 0), solids)
        self.assertEqual(plain.feet, dressed.feet)
        self.assertEqual((plain.x, plain.y, plain.facing), (dressed.x, dressed.y, dressed.facing))
        self.assertEqual((plain.FEET_W, plain.FEET_H), (HubPlayer.FEET_W, HubPlayer.FEET_H))
        self.assertEqual(PLAYER_SPEED, 72)

    def test_look_identity_colours_stay_the_players_own(self):
        self.dress(self.profiles[1], palette="palette_cherry")
        self.assertEqual(self.p2.look, P2_LOOK)                  # base identity untouched
        self.assertEqual(self.p2.look.accent, P2_LOOK.accent)


class WardrobeSceneTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="wa", display_name="Ann", tickets=100),
                         PlayerProfile(profile_id="wb", display_name="Bo", tickets=100)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.frames(60)
        for _ in range(4):                                     # put off each player's daily bonus popup
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

    def stand_at_wardrobe(self, index=0):
        station = next(p for p in self.room.props if isinstance(p, WardrobeStation))
        avatar = self.room.players[index]
        avatar.x, avatar.y = station.zone.centerx, station.zone.bottom - 2
        self.frames(5)
        return station

    def open_wardrobe(self, index=0, interact=pygame.K_e):
        station = self.stand_at_wardrobe(index)
        self.assertIs(self.room.players[index].nearby, station)
        self.key(interact, 40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, WardrobeScene)
        self.assertIs(scene.owner, self.game.session.players[index])
        return scene

    def test_e_at_the_wardrobe_opens_it_and_esc_returns_home(self):
        self.open_wardrobe()
        self.key(pygame.K_ESCAPE, 40)
        self.assertIs(self.game.scenes.current, self.room)

    def test_wearing_an_owned_item_dresses_the_avatar_immediately(self):
        self.profiles[0].inventory.add_item("neon_cap")
        scene = self.open_wardrobe()
        self.key(pygame.K_d)                                    # HAT tab
        self.key(pygame.K_s)                                    # NEON CAP
        self.assertEqual(scene.highlighted, "neon_cap")
        self.assertEqual(self.profiles[0].appearance, {})       # only previewed so far
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[0].appearance, {HAT: "neon_cap"})
        self.assertEqual(self.room.players[0].appearance, {HAT: "neon_cap"})

    def test_an_unowned_item_can_be_tried_on_but_not_worn(self):
        scene = self.open_wardrobe()
        self.key(pygame.K_d)
        self.key(pygame.K_s)
        preview = scene.preview_appearance()
        self.assertEqual(preview, {HAT: "neon_cap"})
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[0].appearance, {})
        self.assertIn("NOT OWNED", scene.message)

    def test_e_on_the_worn_item_takes_it_off_and_none_row_clears_the_slot(self):
        self.profiles[0].inventory.add_item("cat_ears")
        scene = self.open_wardrobe()
        self.key(pygame.K_d)
        self.key(pygame.K_s)
        self.key(pygame.K_s)                                    # CAT EARS
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[0].appearance, {HAT: "cat_ears"})
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[0].appearance, {})
        self.key(pygame.K_e)
        self.key(pygame.K_w)
        self.key(pygame.K_w)                                    # NONE
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[0].appearance, {})

    def test_every_tab_renders(self):
        scene = self.open_wardrobe()
        for tab in range(len(SLOTS)):
            scene.set_tab(tab)
            for i in range(len(scene.rows)):
                scene.select(i)
                scene.draw(self.game.canvas)

    def test_p2_dresses_p2_only_with_their_own_keys(self):
        self.profiles[1].inventory.add_item("retro_sunglasses")
        scene = self.open_wardrobe(1, interact=pygame.K_RETURN)
        self.key(pygame.K_RIGHT)
        self.key(pygame.K_RIGHT)                                # FACE tab
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.profiles[1].appearance, {FACE: "retro_sunglasses"})
        self.assertEqual(self.profiles[0].appearance, {})
        self.assertEqual(self.room.players[0].appearance, {})

    def test_the_wardrobe_does_not_move_the_player(self):
        self.profiles[0].inventory.add_item("neon_cap")
        self.open_wardrobe()
        x, y = self.room.players[0].x, self.room.players[0].y
        self.key(pygame.K_d)
        self.key(pygame.K_w)
        self.key(pygame.K_ESCAPE, 40)
        self.assertEqual((self.room.players[0].x, self.room.players[0].y), (x, y))


if __name__ == "__main__":
    unittest.main()
