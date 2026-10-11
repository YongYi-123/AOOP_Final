"""The whole reward loop, driven only with key presses through the real scenes:
earn tickets -> Prize Counter -> buy -> HOME (wardrobe / decoration mode /
collection) -> visible result -> restart -> still there.

Run headless from this folder:   python -m unittest test_reward_loop -v
"""
import json
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from collection_ui import CollectionScene  # noqa: E402
from cosmetics import HAT  # noqa: E402
from decor_ui import DecorationScene  # noqa: E402
from game import Game  # noqa: E402
from home_stations import CollectionStation, DecorStation, WardrobeStation  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore, SAVE_VERSION  # noqa: E402
from prize_shop import entry_for  # noqa: E402
from room_testing import goto_room  # noqa: E402
from shop_ui import TABS, ShopScene  # noqa: E402
from stations import PrizeCounter  # noqa: E402
from wardrobe_ui import WardrobeScene  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class RewardLoopTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "save.json")
        self.start()

    def start(self, new_game=True):
        store = ProfileStore(self.path)
        self.profile = store.load()
        store.autosave(self.profile)
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

    def use_station(self, kind):
        station = next(p for p in self.room.props if isinstance(p, kind))
        avatar = self.room.players[0]
        avatar.x, avatar.y = station.zone.centerx, station.zone.bottom - 2
        self.frames(5)
        self.key(pygame.K_e, 40)
        return self.game.scenes.current

    def buy_in_shop(self, tab, item_id):
        self.room = goto_room(self.game, "prize_plaza")
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        avatar = self.room.players[0]
        avatar.x, avatar.y = counter.zone.centerx, counter.zone.bottom - 2
        self.frames(5)
        self.key(pygame.K_e, 40)
        shop = self.game.scenes.current
        self.assertIsInstance(shop, ShopScene)
        shop.tab = TABS.index(tab)
        shop.index = [e.item_id for e in shop.rows].index(item_id)
        shop.first = max(0, shop.index - shop.VISIBLE + 1)
        self.key(pygame.K_e, 20)                    # BUY?
        self.key(pygame.K_e, 30)                    # BUY
        self.key(pygame.K_ESCAPE, 40)               # leave the shop
        self.assertIs(self.game.scenes.current, self.room)
        self.room = goto_room(self.game, "home")

    def test_buy_wear_decorate_collect_and_it_all_survives_a_restart(self):
        self.profile.add_tickets(300)
        start = self.profile.tickets
        costs = sum(entry_for(i).cost for i in ("neon_cap", "decor_table_lamp", "cat_sticker"))

        self.buy_in_shop("COSMETICS", "neon_cap")
        self.buy_in_shop("HOME", "decor_table_lamp")
        self.buy_in_shop("COLLECT", "cat_sticker")
        self.assertEqual(self.profile.tickets, start - costs)
        for item in ("neon_cap", "decor_table_lamp", "cat_sticker"):
            self.assertTrue(self.profile.inventory.has_item(item), item)

        # wear the cap
        wardrobe = self.use_station(WardrobeStation)
        self.assertIsInstance(wardrobe, WardrobeScene)
        self.key(pygame.K_d)
        self.key(pygame.K_s)
        self.key(pygame.K_e)
        self.key(pygame.K_ESCAPE, 40)
        self.assertEqual(self.room.players[0].appearance, {HAT: "neon_cap"})

        # put the lamp on the table
        decor = self.use_station(DecorStation)
        self.assertIsInstance(decor, DecorationScene)
        while decor.slot.slot_id != "table_decor":
            self.key(pygame.K_TAB)
        self.key(pygame.K_e)
        while decor.rows[decor.index] != "table_lamp":
            self.key(pygame.K_s)
        self.key(pygame.K_e)
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_ESCAPE, 40)
        self.assertEqual(self.room.decorations.current_id("table_decor"), "table_lamp")

        # show the sticker
        collection = self.use_station(CollectionStation)
        self.assertIsInstance(collection, CollectionScene)
        collection.index = [d.id for d, _ in collection.entries].index("cat_sticker")
        self.key(pygame.K_e)
        self.key(pygame.K_ESCAPE, 40)
        self.assertEqual(self.profile.collection_display, ["cat_sticker"])

        # a different "run" of the game from the same save file
        self.game.quit()
        self.start()
        self.assertEqual(self.profile.tickets, start - costs)
        self.assertEqual(self.room.players[0].appearance, {HAT: "neon_cap"})
        self.assertEqual(self.room.decorations.current_id("table_decor"), "table_lamp")
        self.assertEqual(self.profile.collection_display, ["cat_sticker"])

    def test_the_save_file_gains_only_additive_keys(self):
        with open(self.path, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["version"], SAVE_VERSION)
        self.assertEqual(saved["appearance"], {})
        self.assertEqual(saved["collection_display"], [])
        self.assertIn("home_decorations", saved)
        self.assertIn("inventory", saved)

    def test_an_old_save_file_opens_and_keeps_everything(self):
        old = {"version": 2, "tokens": 9, "tickets": 77, "inventory": {"neon_cap": 1, "cat_sticker": 1},
               "home_decorations": {"poster_left": "poster_cat"}, "high_scores": {"x": 3}}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(old, f)
        self.game.quit()
        self.start()
        self.assertEqual((self.profile.tokens, self.profile.tickets), (9, 77))
        self.assertEqual(self.profile.high_score("x"), 3)
        self.assertEqual(self.room.decorations.current_id("poster_left"), "poster_cat")
        self.assertEqual(self.profile.appearance, {})                      # nothing worn yet,
        self.assertTrue(self.profile.inventory.has_item("neon_cap"))      # but the old cap is wearable


class PlazaHomeNavigationTests(unittest.TestCase):
    def test_hub_rooms_connect_and_the_plaza_has_its_shop_and_garage(self):
        profile = PlayerProfile(profile_id="nav", tickets=10)
        game = Game(session=LocalSession([profile]))
        self.addCleanup(game.quit)
        home = goto_room(game, "home")
        self.assertEqual({e.target for e in home.exits}, {"arcade_floor", "prize_plaza"})
        plaza = goto_room(game, "prize_plaza")
        self.assertEqual([e.target for e in plaza.exits], ["home"])
        kinds = {type(p).__name__ for p in plaza.props}
        self.assertTrue({"PrizeCounter", "GarageStation", "ChanceStation", "Neon21Station"} <= kinds)
        for _ in range(120):                                  # the new animations run without error
            game.step([], DT)
        game.scenes.current.draw(game.canvas)

    def test_plaza_walkways_are_still_clear(self):
        profile = PlayerProfile(profile_id="nav2", tickets=10)
        game = Game(session=LocalSession([profile]))
        self.addCleanup(game.quit)
        plaza = goto_room(game, "prize_plaza")
        for prop in plaza.props + plaza.machines:                      # (the room walls frame the doors)
            for zone in plaza.keep_clear_areas:
                self.assertFalse(prop.footprint.colliderect(zone), (type(prop).__name__, zone))
        for p in plaza.props:
            if p.solid:
                self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(p.footprint), type(p).__name__)


if __name__ == "__main__":
    unittest.main()
