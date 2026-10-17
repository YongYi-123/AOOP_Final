"""Tests for the Prize Plaza SHOWCASE and the redesigned centre of the room: choosing what is
displayed, persistence and older saves, P1/P2 isolation, the layout and the old GARAGE terminal
being gone.

Run headless from this folder:   python -m unittest test_showcase -v
"""
import json
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game import Game  # noqa: E402
from item_registry import COLLECTIBLE, ITEM_REGISTRY  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import SAVE_VERSION, PlayerProfile, ProfileStore  # noqa: E402
from plaza_stations import CapsuleStation, ShowcaseStation  # noqa: E402
from prize_plaza import CAPSULE_POS, COUNTER_POS, LUCKY_POS, SHOWCASE_POS, PrizePlazaScene  # noqa: E402
from racing_progression.service import PrizeService  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import FLOOR_BOTTOM, FLOOR_TOP, VIEW_H, VIEW_W  # noqa: E402
from showcase import CAR, COLLECTIBLE_SLOT, TROPHY, TROPHY_IDS, ShowcaseService  # noqa: E402
from showcase_ui import ShowcaseScene  # noqa: E402
from stations import PrizeCounter  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(tickets=500)
        self.s = ShowcaseService(self.p)

    def test_a_new_profile_displays_nothing_and_can_show_only_the_free_car(self):
        self.assertEqual(self.s.all_displayed(), {CAR: None, COLLECTIBLE_SLOT: None, TROPHY: None})
        self.assertEqual([o.value for o in self.s.options(CAR)], ["falcon"])
        self.assertEqual(self.s.options(COLLECTIBLE_SLOT), [])
        self.assertEqual(self.s.options(TROPHY), [])
        self.assertEqual(self.p.showcase, {})

    def test_owned_cars_are_offered_and_can_be_chosen(self):
        PrizeService(self.p).buy("car", "viper")
        self.assertEqual([o.value for o in self.s.options(CAR)], ["falcon", "viper"])
        self.assertTrue(self.s.choose(CAR, "viper"))
        self.assertEqual(self.s.displayed(CAR).name, "VIPER")
        self.assertEqual(self.p.showcase, {"car": "viper"})

    def test_an_unowned_car_cannot_be_displayed(self):
        self.assertFalse(self.s.choose(CAR, "titan"))
        self.assertEqual(self.p.showcase, {})

    def test_collectibles_and_trophies_go_in_their_own_bays(self):
        for item in ("retro_badge", "arcade_trophy", "cat_sticker"):
            self.p.inventory.add_item(item)
        self.assertEqual({o.value for o in self.s.options(COLLECTIBLE_SLOT)}, {"retro_badge", "cat_sticker"})
        self.assertEqual({o.value for o in self.s.options(TROPHY)}, {"arcade_trophy"})
        self.assertFalse(self.s.choose(COLLECTIBLE_SLOT, "arcade_trophy"))
        self.assertFalse(self.s.choose(TROPHY, "retro_badge"))
        self.assertTrue(self.s.choose(COLLECTIBLE_SLOT, "retro_badge"))
        self.assertTrue(self.s.choose(TROPHY, "arcade_trophy"))
        self.assertEqual({k: o.value for k, o in self.s.all_displayed().items() if o},
                         {COLLECTIBLE_SLOT: "retro_badge", TROPHY: "arcade_trophy"})

    def test_unowned_or_unknown_items_are_refused(self):
        self.assertFalse(self.s.choose(TROPHY, "arcade_trophy"))
        self.assertFalse(self.s.choose(COLLECTIBLE_SLOT, "no_such_item"))
        self.assertFalse(self.s.choose("nope", "falcon"))
        self.assertEqual(self.p.showcase, {})

    def test_trophy_ids_are_real_items(self):
        for item_id in TROPHY_IDS:
            self.assertIn(item_id, ITEM_REGISTRY)

    def test_capsule_collectibles_can_be_shown_and_report_how_many_are_owned(self):
        self.p.inventory.add_item("cat_paw_sticker", 3)
        option = self.s.options(COLLECTIBLE_SLOT)[0]
        self.assertEqual((option.value, option.count), ("cat_paw_sticker", 3))
        self.assertEqual(ITEM_REGISTRY.get("cat_paw_sticker").category, COLLECTIBLE)

    def test_an_item_that_is_no_longer_owned_leaves_an_empty_pedestal(self):
        self.p.inventory.add_item("retro_badge")
        self.s.choose(COLLECTIBLE_SLOT, "retro_badge")
        self.p.inventory.remove_item("retro_badge")
        self.assertIsNone(self.s.displayed(COLLECTIBLE_SLOT))

    def test_clear_and_replace(self):
        for item in ("retro_badge", "cat_sticker"):
            self.p.inventory.add_item(item)
        self.s.choose(COLLECTIBLE_SLOT, "retro_badge")
        self.s.choose(COLLECTIBLE_SLOT, "cat_sticker")
        self.assertEqual(self.p.showcase, {"collectible": "cat_sticker"})
        self.assertTrue(self.s.clear(COLLECTIBLE_SLOT))
        self.assertFalse(self.s.clear(COLLECTIBLE_SLOT))
        self.assertEqual(self.p.showcase, {})

    def test_profiles_never_share_a_showcase(self):
        a, b = PlayerProfile(), PlayerProfile()
        a.inventory.add_item("retro_badge")
        b.inventory.add_item("retro_badge")
        ShowcaseService(a).choose(COLLECTIBLE_SLOT, "retro_badge")
        self.assertEqual(b.showcase, {})
        self.assertIsNone(ShowcaseService(b).displayed(COLLECTIBLE_SLOT))


class SaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "p.json")

    def test_the_choice_persists_through_the_save_file(self):
        p = PlayerProfile()
        p.inventory.add_item("arcade_trophy")
        store = ProfileStore(self.path)
        store.autosave(p)
        ShowcaseService(p).choose(TROPHY, "arcade_trophy")
        ShowcaseService(p).choose(CAR, "falcon")
        loaded = ProfileStore(self.path).load()
        self.assertEqual(loaded.showcase, {"trophy": "arcade_trophy", "car": "falcon"})
        self.assertEqual(ShowcaseService(loaded).displayed(TROPHY).name, "ARCADE TROPHY")

    def test_an_empty_showcase_adds_nothing_to_the_save(self):
        self.assertNotIn("showcase", PlayerProfile().to_dict())

    def test_an_older_save_without_the_field_still_loads(self):
        old = PlayerProfile(tickets=33).to_dict()
        old.pop("showcase", None)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(old, f)
        loaded = ProfileStore(self.path).load()
        self.assertEqual(loaded.tickets, 33)
        self.assertEqual(loaded.showcase, {})
        self.assertEqual(loaded.to_dict()["version"], SAVE_VERSION)

    def test_damaged_showcase_data_is_dropped_not_fatal(self):
        for junk in ("text", 5, ["car"], {"car": 3, "bogus": "x", "trophy": "", "collectible": "retro_badge"}):
            data = PlayerProfile().to_dict()
            data["showcase"] = junk
            p = PlayerProfile.from_dict(data)
            self.assertEqual(p.showcase, {"collectible": "retro_badge"} if isinstance(junk, dict) else {})

    def test_a_stale_choice_for_an_item_no_longer_owned_loads_and_shows_empty(self):
        data = PlayerProfile().to_dict()
        data["showcase"] = {"trophy": "arcade_trophy", "car": "viper", "collectible": "removed_item"}
        p = PlayerProfile.from_dict(data)
        self.assertEqual(ShowcaseService(p).all_displayed(), {CAR: None, COLLECTIBLE_SLOT: None, TROPHY: None})
        self.assertEqual(PlayerProfile.from_dict(p.to_dict()).showcase, data["showcase"])        # kept, not lost

    def test_set_showcase_rejects_bad_input(self):
        p = PlayerProfile()
        for slot, value in (("nope", "x"), ("car", ""), ("car", 5)):
            with self.assertRaises(ValueError):
                p.set_showcase(slot, value)

    def test_a_change_triggers_exactly_one_save_and_a_repeat_none(self):
        p = PlayerProfile()
        saves = []
        p.subscribe_save(lambda: saves.append(1))
        self.assertTrue(p.set_showcase("car", "falcon"))
        self.assertFalse(p.set_showcase("car", "falcon"))
        self.assertEqual(len(saves), 1)


class RoomBase(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="sc_a", tickets=500), PlayerProfile(profile_id="sc_b", tickets=500)]
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

    @property
    def stand(self):
        return next(p for p in self.room.props if isinstance(p, ShowcaseStation))


class SceneTests(RoomBase):
    def open_for(self, index, interact_key):
        avatar = self.room.players[index]
        avatar.x, avatar.y = float(self.stand.zone.centerx), float(self.stand.zone.bottom - 2)
        self.frames(6)
        self.assertIs(avatar.nearby, self.stand)
        self.key(interact_key)
        self.frames(40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, ShowcaseScene)
        return scene

    def test_e_at_the_stand_opens_the_showcase_for_p1_and_esc_returns(self):
        scene = self.open_for(0, pygame.K_e)
        self.assertIs(scene.owner, self.game.session.primary)
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.key(pygame.K_ESCAPE)
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)

    def test_choosing_with_the_keys_saves_and_shows_in_the_room(self):
        p = self.profiles[0]
        p.inventory.add_item("mini_cabinet")
        scene = self.open_for(0, pygame.K_e)
        self.key(pygame.K_d)                                    # CAR -> COLLECTIBLE
        self.assertEqual(scene.slot, COLLECTIBLE_SLOT)
        self.key(pygame.K_s)                                    # first real row (row 0 is EMPTY)
        self.key(pygame.K_e)
        self.assertEqual(p.showcase, {"collectible": "mini_cabinet"})
        self.assertEqual(self.profiles[1].showcase, {})
        self.key(pygame.K_ESCAPE)
        self.frames(40)
        self.assertEqual(self.stand._shown[0][1][COLLECTIBLE_SLOT].value, "mini_cabinet")
        self.room.draw(pygame.Surface((VIEW_W, VIEW_H)))

    def test_pressing_e_twice_on_the_same_item_changes_nothing_further(self):
        p = self.profiles[0]
        scene = self.open_for(0, pygame.K_e)
        self.key(pygame.K_s)
        self.key(pygame.K_e)
        self.assertEqual(p.showcase, {"car": "falcon"})
        self.key(pygame.K_e)
        self.assertIn("ALREADY", scene.message)
        self.assertEqual(p.showcase, {"car": "falcon"})

    def test_the_empty_row_clears_a_bay(self):
        p = self.profiles[0]
        p.set_showcase("car", "falcon")
        scene = self.open_for(0, pygame.K_e)
        self.assertEqual(scene.index, 1)                         # the cursor starts on what is displayed
        self.key(pygame.K_w)
        self.key(pygame.K_e)
        self.assertEqual(p.showcase, {})

    def test_p2_edits_only_p2s_showcase_and_p1_keys_do_nothing_in_it(self):
        self.profiles[1].inventory.add_item("arcade_trophy")
        scene = self.open_for(1, pygame.K_RETURN)
        self.assertIs(scene.profile, self.profiles[1])
        self.key(pygame.K_a)                                     # P1's keys: ignored by P2's screen
        self.key(pygame.K_d)
        self.key(pygame.K_e)
        self.assertEqual(scene.slot, CAR)
        self.assertEqual(self.profiles[0].showcase, {})
        self.key(pygame.K_RIGHT)
        self.key(pygame.K_RIGHT)
        self.assertEqual(scene.slot, TROPHY)
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.profiles[1].showcase, {"trophy": "arcade_trophy"})
        self.assertEqual(self.profiles[0].showcase, {})
        self.assertEqual([p.tickets for p in self.profiles], [500, 500])

    def test_empty_bays_explain_where_to_get_items(self):
        scene = self.open_for(0, pygame.K_e)
        scene.set_tab(1)
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertEqual(scene.rows, [None])


class RoomLayoutTests(RoomBase):
    def test_the_garage_terminal_is_gone_and_the_stand_is_in_its_place(self):
        self.assertFalse(any(getattr(p, "prompt_label", "") == "GARAGE" for p in self.room.props))
        self.assertEqual(len([p for p in self.room.props if isinstance(p, ShowcaseStation)]), 1)
        self.assertEqual(len([p for p in self.room.props if isinstance(p, CapsuleStation)]), 2)

    def test_four_clear_zones(self):
        """left = counter, centre = showcase, upper right = capsules, lower right = Lucky Corner."""
        from prize_plaza import CAPSULE_RUG
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        capsules = [p for p in self.room.props if isinstance(p, CapsuleStation)]
        lucky = [p for p in self.room.props if hasattr(p, "kind")]
        stand = self.stand
        self.assertEqual(len(lucky), 5)
        self.assertGreater(stand.rect.left, counter.rect.right)                       # counter is left of the showcase
        self.assertLess(stand.rect.right, CAPSULE_RUG[0])                             # showcase is left of the right block
        self.assertTrue(VIEW_W * 0.3 < stand.rect.centerx < VIEW_W * 0.6)             # central
        self.assertLessEqual(stand.rect.top, FLOOR_TOP + 6)                           # standing against the back wall
        for c in capsules:
            self.assertGreater(c.rect.left, stand.rect.right)
        lucky_top = min(m.rect.top for m in lucky)
        self.assertLess(max(c.rect.bottom for c in capsules), lucky_top)             # capsules above the Lucky Corner
        for m in lucky:
            self.assertGreater(m.rect.left, stand.rect.right)                         # Lucky Corner is right of the showcase
        self.assertLess(self.room.mochi.pos[0], stand.rect.left)

    def test_the_stand_is_the_biggest_display_piece_in_the_room(self):
        sizes = {p.prompt_label: p.rect.w * p.rect.h for p in self.room.props
                 if isinstance(p, (CapsuleStation, ShowcaseStation))}
        self.assertEqual(max(sizes, key=sizes.get), "SHOWCASE")

    def test_the_upper_display_is_gone_and_there_is_only_one_display_system(self):
        import prize_plaza
        self.assertFalse(hasattr(prize_plaza, "SHELF_ITEMS"))
        self.assertFalse(hasattr(prize_plaza.PlazaBackdrop, "SHELVES"))
        self.assertEqual(len([p for p in self.room.props if isinstance(p, ShowcaseStation)]), 1)
        for x, y in prize_plaza.WALL_ART:                                             # wall decoration stays on the back wall
            self.assertLess(y + 22, FLOOR_TOP)
        self.assertTrue(all(not hasattr(p, "owners") or isinstance(p, ShowcaseStation) for p in self.room.props))
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        self.room.draw(canvas)
        self.assertFalse(any(isinstance(p, PrizeCounter) and p.rect.top < FLOOR_TOP for p in self.room.props))

    def test_the_centre_pieces_do_not_overlap_each_other_or_the_lucky_corner(self):
        pieces = [p for p in self.room.props if isinstance(p, (CapsuleStation, ShowcaseStation, PrizeCounter))]
        lucky = [p for p in self.room.props if hasattr(p, "kind")]
        for i, a in enumerate(pieces):
            for b in pieces[i + 1:]:
                self.assertFalse(a.footprint.colliderect(b.footprint), (a.prompt_label, b.prompt_label))
                self.assertFalse(a.rect.colliderect(b.rect), (a.prompt_label, b.prompt_label))
            for m in lucky:
                self.assertFalse(a.rect.colliderect(m.rect), (a.prompt_label, m.prompt_label))
                self.assertFalse(a.footprint.colliderect(m.footprint), (a.prompt_label, m.prompt_label))
            self.assertTrue(pygame.Rect(0, FLOOR_TOP, VIEW_W, FLOOR_BOTTOM - FLOOR_TOP).contains(a.rect), a.prompt_label)
        rug = pygame.Rect(LUCKY_POS[0] - 14, LUCKY_POS[1] - 20, 122, 128)
        for p in pieces:
            self.assertFalse(p.rect.colliderect(rug), p.prompt_label)

    def test_every_centre_prompt_is_reachable_by_walking(self):
        for target in [p for p in self.room.props if isinstance(p, (CapsuleStation, ShowcaseStation))]:
            avatar = self.room.players[0]
            avatar.x, avatar.y = float(target.zone.centerx), float(target.zone.bottom - 2)
            self.frames(6)
            self.assertIs(avatar.nearby, target, target.prompt_label)

    def test_the_room_draws_one_and_two_players_with_and_without_a_display(self):
        surf = pygame.Surface((VIEW_W, VIEW_H))
        self.room.draw(surf)
        p0, p1 = self.profiles
        for item in ("arcade_trophy", "retro_badge", "cat_paw_sticker"):
            p0.inventory.add_item(item)
        PrizeService(p1).buy("car", "comet")
        for slot, value in ((CAR, "falcon"), (TROPHY, "arcade_trophy"), (COLLECTIBLE_SLOT, "cat_paw_sticker")):
            ShowcaseService(p0).choose(slot, value)
        ShowcaseService(p1).choose(CAR, "comet")
        self.stand.refresh()
        before = pygame.image.tobytes(surf, "RGB")
        self.room.draw(surf)
        self.assertNotEqual(before, pygame.image.tobytes(surf, "RGB"))
        self.assertEqual(len(self.stand._shown), 2)
        self.assertEqual(self.stand._shown[0][0], "P1")
        self.assertEqual(self.stand._shown[1][1][CAR].value, "comet")
        self.frames(30)

    def test_the_stand_follows_the_saved_picks_without_reopening_the_room(self):
        p0 = self.profiles[0]
        p0.set_showcase("car", "falcon")
        self.frames(30)                                          # the stand re-reads the profiles on its own
        self.assertEqual(self.stand._shown[0][1][CAR].value, "falcon")
        p0.set_showcase("car", None)
        self.frames(30)
        self.assertIsNone(self.stand._shown[0][1][CAR])

    def test_single_player_session_shows_a_single_row(self):
        game = Game(session=LocalSession([PlayerProfile(profile_id="solo")]))
        self.addCleanup(game.quit)
        room = goto_room(game, "prize_plaza")
        stand = next(p for p in room.props if isinstance(p, ShowcaseStation))
        self.assertEqual(len(stand._shown), 1)
        room.draw(pygame.Surface((VIEW_W, VIEW_H)))

    def test_the_racing_counter_still_reaches_the_garage(self):
        from racing_progression.ui import GarageScene, PrizeCounterScene
        self.room.open_racing_counter()
        self.frames()
        self.assertIsInstance(self.game.scenes.current, PrizeCounterScene)
        self.key(pygame.K_i)
        self.frames()
        self.assertIsInstance(self.game.scenes.current, GarageScene)

    def test_layout_constants_describe_the_four_zones(self):
        from prize_plaza import CAPSULE_RUG
        self.assertLess(COUNTER_POS[0] + 80, SHOWCASE_POS[0])
        self.assertLess(SHOWCASE_POS[0] + 112, CAPSULE_RUG[0])
        for pos in CAPSULE_POS.values():
            self.assertGreaterEqual(pos[0], CAPSULE_RUG[0])
            self.assertLess(pos[1], LUCKY_POS[1] - 20)
        self.assertGreater(LUCKY_POS[1], CAPSULE_RUG[1] + CAPSULE_RUG[3] - 10)
        self.assertIsInstance(self.room, PrizePlazaScene)


if __name__ == "__main__":
    unittest.main()
