"""Tests for collectibles: unlocking, progress, the display case, saving and the
COLLECTION screen.

Run headless from this folder:   python -m unittest test_collection -v
"""
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from collection import DISPLAY_SLOTS, CollectionService  # noqa: E402
from collection_ui import CollectionScene, silhouette  # noqa: E402
from game import Game  # noqa: E402
from home_stations import CollectionStation  # noqa: E402
from item_icons import item_icon  # noqa: E402
from item_registry import COLLECTIBLE, ITEM_REGISTRY  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from prize_shop import ShopService  # noqa: E402
from rewards import RewardService  # noqa: E402
from room_testing import goto_room  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class CollectionServiceTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(profile_id="c", tickets=1000)
        self.c = CollectionService(self.p)

    def test_the_collection_is_every_collectible_and_includes_the_originals(self):
        ids = [d.id for d in self.c.all_collectibles()]
        self.assertTrue(all(ITEM_REGISTRY.get(i).category == COLLECTIBLE for i in ids))
        self.assertIn("cat_sticker", ids)
        self.assertIn("retro_badge", ids)
        self.assertGreaterEqual(len(ids), 4)

    def test_nothing_is_unlocked_to_begin_with(self):
        owned, total = self.c.progress()
        self.assertEqual(owned, 0)
        self.assertEqual(total, len(self.c.all_collectibles()))
        self.assertFalse(any(owned for _, owned in self.c.entries()))

    def test_getting_an_item_unlocks_it_however_it_arrives(self):
        RewardService.grant_item(self.p, "cat_sticker")                  # a reward
        ShopService(self.p).purchase("retro_badge")                      # a purchase
        self.assertEqual(self.c.progress()[0], 2)
        unlocked = {d.id for d, owned in self.c.entries() if owned}
        self.assertEqual(unlocked, {"cat_sticker", "retro_badge"})

    def test_a_full_collection_reports_complete(self):
        for d in self.c.all_collectibles():
            self.p.inventory.add_item(d.id)
        owned, total = self.c.progress()
        self.assertEqual(owned, total)

    def test_other_item_kinds_do_not_count(self):
        self.p.inventory.add_item("neon_cap")
        self.p.inventory.add_item("free_play_coupon", 5)
        self.assertEqual(self.c.progress()[0], 0)

    def test_only_owned_collectibles_can_be_displayed(self):
        self.assertFalse(self.c.toggle_display("cat_sticker"))
        self.assertEqual(self.c.displayed(), [])
        self.p.inventory.add_item("cat_sticker")
        self.assertTrue(self.c.toggle_display("cat_sticker"))
        self.assertEqual(self.c.displayed(), ["cat_sticker"])
        self.assertFalse(self.c.toggle_display("neon_cap"))              # not a collectible
        self.p.inventory.add_item("neon_cap")
        self.assertFalse(self.c.toggle_display("neon_cap"))
        self.assertFalse(self.c.toggle_display("nope"))

    def test_toggle_unpins_and_the_case_holds_a_limited_number(self):
        for d in self.c.all_collectibles():
            self.p.inventory.add_item(d.id)
        ids = [d.id for d in self.c.all_collectibles()]
        for item in ids[:DISPLAY_SLOTS]:
            self.assertTrue(self.c.toggle_display(item))
        self.assertFalse(self.c.toggle_display(ids[DISPLAY_SLOTS]))      # full
        self.assertEqual(self.c.displayed(), ids[:DISPLAY_SLOTS])
        self.assertTrue(self.c.toggle_display(ids[0]))                   # unpin one ...
        self.assertTrue(self.c.toggle_display(ids[DISPLAY_SLOTS]))       # ... room for another
        self.assertEqual(self.c.displayed(), ids[1:DISPLAY_SLOTS] + [ids[DISPLAY_SLOTS]])

    def test_display_order_is_kept(self):
        for item in ("retro_badge", "cat_sticker"):
            self.p.inventory.add_item(item)
        self.c.toggle_display("retro_badge")
        self.c.toggle_display("cat_sticker")
        self.assertEqual(self.c.displayed(), ["retro_badge", "cat_sticker"])

    def test_a_pinned_item_that_is_no_longer_owned_leaves_the_case(self):
        self.p.inventory.add_item("cat_sticker")
        self.c.toggle_display("cat_sticker")
        self.p.inventory.remove_item("cat_sticker")
        self.assertEqual(self.c.displayed(), [])

    def test_collection_and_display_persist(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "p.json")
        store = ProfileStore(path)
        p = store.load()
        store.autosave(p)
        p.add_tickets(200)
        for item in ("cat_sticker", "retro_badge"):
            RewardService.grant_item(p, item)
        CollectionService(p).toggle_display("retro_badge")
        again = ProfileStore(path).load()
        service = CollectionService(again)
        self.assertEqual(service.progress()[0], 2)
        self.assertEqual(service.displayed(), ["retro_badge"])

    def test_collection_is_per_profile(self):
        other = PlayerProfile(profile_id="o")
        self.p.inventory.add_item("cat_sticker")
        self.c.toggle_display("cat_sticker")
        self.assertEqual(CollectionService(other).progress()[0], 0)
        self.assertEqual(CollectionService(other).displayed(), [])

    def test_bad_saved_display_data_is_ignored(self):
        p = PlayerProfile.from_dict({"collection_display": ["cat_sticker", 5, None, "neon_cap"],
                                     "inventory": {"cat_sticker": 1}})
        self.assertEqual(CollectionService(p).displayed(), ["cat_sticker"])
        self.assertEqual(PlayerProfile.from_dict({"collection_display": "oops"}).collection_display, [])

    def test_collectibles_give_no_gameplay_benefit(self):
        before = (self.p.tokens, self.p.tickets, self.p.lifetime_tickets_earned)
        for d in self.c.all_collectibles():
            self.p.inventory.add_item(d.id)
            self.c.toggle_display(d.id)
        self.assertEqual((self.p.tokens, self.p.tickets, self.p.lifetime_tickets_earned), before)


class SilhouetteTests(unittest.TestCase):
    def test_a_silhouette_keeps_the_shape_and_loses_the_colour(self):
        pygame.init()
        icon = item_icon(ITEM_REGISTRY.get("retro_badge"))
        flat = silhouette(icon)
        self.assertEqual(flat.get_size(), icon.get_size())
        self.assertEqual(pygame.mask.from_surface(flat).count(), pygame.mask.from_surface(icon).count())
        colours = {tuple(flat.get_at((x, y)))[:3] for x in range(flat.get_width()) for y in range(flat.get_height())
                   if flat.get_at((x, y)).a}
        self.assertEqual(len(colours), 1)


class CollectionSceneTests(unittest.TestCase):
    def setUp(self):
        self.profile = PlayerProfile(profile_id="cs", display_name="Ann", tickets=200)
        self.game = Game(session=LocalSession([self.profile]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.frames(60)
        if self.room.modal is not None:
            self.key(pygame.K_ESCAPE, 10)

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k, frames=1):
        self.game.step([key_event(k)], DT)
        self.frames(frames - 1)

    def open_collection(self):
        station = next(p for p in self.room.props if isinstance(p, CollectionStation))
        avatar = self.room.players[0]
        avatar.x, avatar.y = station.zone.centerx, station.zone.bottom - 2
        self.frames(5)
        self.assertIs(avatar.nearby, station)
        self.key(pygame.K_e, 40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, CollectionScene)
        return scene

    def test_the_case_opens_the_collection_and_esc_returns(self):
        self.open_collection()
        self.key(pygame.K_ESCAPE, 40)
        self.assertIs(self.game.scenes.current, self.room)

    def test_a_missing_item_cannot_be_pinned_and_says_so(self):
        scene = self.open_collection()
        self.key(pygame.K_e)
        self.assertEqual(self.profile.collection_display, [])
        self.assertIn("NOT FOUND", scene.message)

    def test_pin_and_unpin_with_e(self):
        self.profile.inventory.add_item("cat_sticker")
        scene = self.open_collection()
        names = [d.id for d, _ in scene.entries]
        scene.index = names.index("cat_sticker")
        self.key(pygame.K_e)
        self.assertEqual(self.profile.collection_display, ["cat_sticker"])
        self.key(pygame.K_e)
        self.assertEqual(self.profile.collection_display, [])

    def test_the_home_case_shows_what_is_pinned(self):
        self.profile.inventory.add_item("cat_sticker")
        station = next(p for p in self.room.props if isinstance(p, CollectionStation))
        canvas = pygame.Surface(self.game.canvas.get_size(), pygame.SRCALPHA)
        station.time = 100.0                                    # a moment with no glint over the glass
        station.draw(canvas)
        empty = pygame.image.tobytes(canvas, "RGBA")
        CollectionService(self.profile).toggle_display("cat_sticker")
        canvas.fill((0, 0, 0, 0))
        station.draw(canvas)
        self.assertNotEqual(pygame.image.tobytes(canvas, "RGBA"), empty)

    def test_navigation_wraps_and_every_cell_renders_found_or_missing(self):
        self.profile.inventory.add_item("retro_badge")
        scene = self.open_collection()
        total = len(scene.entries)
        for _ in range(total + 2):
            self.key(pygame.K_d)
            scene.draw(self.game.canvas)
        self.assertEqual(scene.index, 2 % total)
        for _ in range(4):
            self.key(pygame.K_s)
            self.key(pygame.K_w)
            scene.draw(self.game.canvas)
        self.assertTrue(0 <= scene.index < total)

    def test_progress_text_matches_the_service(self):
        self.profile.inventory.add_item("cat_sticker")
        scene = self.open_collection()
        owned, total = scene.service.progress()
        self.assertEqual((owned, total), (1, len(scene.entries)))


if __name__ == "__main__":
    unittest.main()
