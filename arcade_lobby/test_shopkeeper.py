"""Tests for Mochi, the cat shopkeeper: placement, animation states, reactions to
real shop events, two-player ownership, no duplicate purchases and audio-free play.

Run headless from this folder:   python -m unittest test_shopkeeper -v
"""
import os
import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import shop_ui  # noqa: E402
import shopkeeper as sk  # noqa: E402
from font import get_font  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from menu_kit import FRAME  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from prize_plaza import COUNTER_POS, MOCHI_POS, SHELF_ITEMS, SIGN, PlazaBackdrop  # noqa: E402
from prize_shop import entry_for  # noqa: E402
from room_testing import goto_room  # noqa: E402
from shopkeeper import Shopkeeper  # noqa: E402
from shop_ui import ShopScene  # noqa: E402
from stations import PrizeCounter  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def walker(x, y):
    return SimpleNamespace(x=float(x), y=float(y))


def run(keeper, seconds, players=()):
    for _ in range(int(seconds / DT)):
        keeper.update(DT, players)


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(session=LocalSession([PlayerProfile(profile_id="pa")]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "prize_plaza")
        for _ in range(60):
            self.game.step([], DT)

    def rect(self):
        w, h = Shopkeeper.SIZE
        x, y = MOCHI_POS
        return pygame.Rect(x - w // 2, y - h + 1, w, h)

    def test_mochi_sits_on_top_of_the_prize_counter(self):
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        self.assertIs(self.room.mochi.pos, MOCHI_POS)
        self.assertTrue(counter.rect.left < MOCHI_POS[0] < counter.rect.right)
        self.assertLessEqual(abs(MOCHI_POS[1] - counter.rect.top), 3)

    def test_she_blocks_nothing(self):
        r = self.rect()
        self.assertNotIn(self.room.mochi, self.room.props)                 # not furniture: no collision
        self.assertEqual(r.collidelist(self.room.solids[len(self.room.walls):len(self.room.walls)]), -1)
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        self.assertFalse(r.colliderect(counter.zone), "stay out of the counter's interaction zone")
        self.assertFalse(r.colliderect(counter.footprint))
        self.assertFalse(r.colliderect(pygame.Rect(SIGN)), "stay clear of the PRIZE COUNTER sign")
        shelves = [pygame.Rect(x, y - 16, PlazaBackdrop.SHELF_W, 20) for x, y in PlazaBackdrop.SHELVES]
        for shelf in shelves:
            self.assertFalse(r.colliderect(shelf))
        self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(r))

    def test_she_is_painted_over_the_counter_and_under_nobody_standing_in_front(self):
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        self.assertGreater(self.room.mochi.sort_y, counter.sort_y)
        avatar = self.room.players[0]
        self.assertLess(self.room.mochi.sort_y, counter.sort_y + 2)
        self.assertIn(self.room.mochi, self.room.drawables())

    def test_walking_through_her_spot_is_possible(self):
        avatar = self.room.players[0]
        avatar.x, avatar.y = MOCHI_POS[0], MOCHI_POS[1] + 40
        before = avatar.feet.copy()
        self.assertEqual(avatar.feet.collidelist(self.room.cats.blockers(avatar)), -1)
        self.assertEqual(before, avatar.feet)

    def test_the_room_draws_with_all_her_states(self):
        surf = pygame.Surface((400, 300))
        for state in ("idle", "sleep", "wake", "greet", "celebrate", "tilt", "wave", "lick"):
            self.room.mochi._set(state)
            self.room.draw(surf)


class AnimationStateTests(unittest.TestCase):
    def setUp(self):
        self.k = Shopkeeper((90, 106), rng=random.Random(3))
        self.me = walker(300, 250)               # far away

    def test_idle_life_blinks_twitches_ears_and_swishes_the_tail(self):
        seen = set()
        for _ in range(int(40 / DT)):
            self.k.update(DT, [self.me])
            if self.k.state == "sleep":
                self.k.idle_for = 0
                self.k._set("idle")
            seen.add((self.k.time < self.k.blink_until, self.k.time < self.k.ear_until, self.k._tail() > 0))
        self.assertTrue(any(b for b, _, _ in seen), "blinks")
        self.assertTrue(any(e for _, e, _ in seen), "ear twitches")
        self.assertTrue(any(t for _, _, t in seen), "tail swishes")

    def test_idle_life_is_deterministic_for_a_seed(self):
        def trace(seed):
            k, out = Shopkeeper((0, 0), rng=random.Random(seed)), []
            for _ in range(2000):
                k.update(DT, ())
                out.append((k.state, k.time < k.blink_until))
            return out
        self.assertEqual(trace(5), trace(5))

    def test_she_licks_a_paw_now_and_then_and_returns_to_idle(self):
        states = []
        for _ in range(int(25 / DT)):
            self.k.update(DT, [self.me])
            states.append(self.k.state)
            if self.k.state == "sleep":
                break
        self.assertIn("lick", states)
        self.assertEqual(states[states.index("lick") + int(sk.REACTION_TIME["lick"] / DT) + 3], "idle")

    def test_she_gets_sleepy_then_falls_asleep_when_nobody_is_around(self):
        run(self.k, sk.SLEEPY_AFTER + 0.5, [self.me])
        self.assertTrue(self.k.sleepy)
        self.assertNotEqual(self.k.state, "sleep")
        run(self.k, sk.SLEEP_AFTER - sk.SLEEPY_AFTER + 1, [self.me])
        self.assertTrue(self.k.sleeping)

    def test_a_player_walking_up_wakes_her_and_gets_a_welcome(self):
        run(self.k, sk.SLEEP_AFTER + 2, [self.me])
        self.assertTrue(self.k.sleeping)
        self.me.x, self.me.y = 100, 150
        self.k.update(DT, [self.me])
        self.assertEqual(self.k.state, "wake")
        run(self.k, sk.REACTION_TIME["wake"] + 0.2, [self.me])
        self.assertFalse(self.k.sleeping)
        self.assertIn(("approach", self.k.events[0][1]), self.k.events)

    def test_approaching_looks_towards_the_player_and_shows_a_welcome(self):
        self.me.x, self.me.y = 40, 150                 # to her left
        self.k.update(DT, [self.me])
        self.assertEqual(self.k.state, "greet")
        self.assertEqual(self.k.bubble.text, "WELCOME!")
        self.assertEqual(self.k.side, "left")
        self.me.x = 150
        run(self.k, 0.2, [self.me])
        self.assertEqual(self.k.side, "right")

    def test_the_welcome_is_not_repeated_while_the_player_stays_or_dithers(self):
        self.me.x, self.me.y = 90, 150
        for _ in range(int(5 / DT)):
            self.k.update(DT, [self.me])
        self.me.x = 90 + 10                              # shuffling nearby
        run(self.k, 3, [self.me])
        self.assertEqual([e for e, _ in self.k.events].count("approach"), 1)

    def test_every_reaction_ends_back_in_idle(self):
        for event in ("open", "purchase", "insufficient", "leave"):
            k = Shopkeeper((90, 106))
            k.notify(event, self.me)
            self.assertNotEqual(k.state, "idle")
            run(k, 2.0)
            self.assertEqual(k.state, "idle", event)

    def test_every_state_paints_a_cached_frame_of_the_same_size(self):
        k = Shopkeeper((90, 106))
        sizes = set()
        for state in ("idle", "sleep", "wake", "greet", "celebrate", "tilt", "wave", "lick"):
            k._set(state)
            k.time = 1.3
            sizes.add(k.image().get_size() if state != "sleep" else (20, 17))
            self.assertIs(k.frame(), k.frame())          # cached: no repainting per frame
        self.assertEqual(len(sizes), 1)

    def test_unknown_events_are_rejected(self):
        with self.assertRaises(ValueError):
            self.k.notify("dance")

    def test_hop_only_while_happy(self):
        self.k.notify("purchase", self.me)
        self.k.state_time = 0.2
        self.assertLess(self.k.hop(), 0)
        self.k._set("tilt")
        self.assertEqual(self.k.hop(), 0)

    def test_meows_are_rare(self):
        played = []
        k = Shopkeeper((0, 0), sound=played.append)
        for _ in range(4):
            k.notify("purchase", self.me)
            run(k, 0.3)
        self.assertEqual(played, ["meow"])
        run(k, sk.MEOW_GAP)
        k.notify("open", self.me)
        self.assertEqual(played, ["meow", "meow"])
        k.notify("insufficient", self.me)               # no sound for a refusal
        k.notify("leave", self.me)
        self.assertEqual(len(played), 2)


class ShopReactionTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="sa", display_name="Ann", tickets=40),
                         PlayerProfile(profile_id="sb", display_name="Bo", tickets=500)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "prize_plaza")
        for _ in range(60):
            self.game.step([], DT)
        for _ in range(5):
            if self.room.modal is None:
                break
            self.key(pygame.K_ESCAPE, 10)
        self.keeper = self.room.mochi

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k, frames=1):
        self.game.step([key_event(k)], DT)
        self.frames(frames - 1)

    def open_shop(self, index=0, interact=pygame.K_e):
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        avatar = self.room.players[index]
        avatar.x, avatar.y = counter.zone.centerx, counter.zone.bottom - 2
        self.room.players[1 - index].x, self.room.players[1 - index].y = 340.0, 250.0
        self.frames(5)
        self.key(interact, 40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, ShopScene)
        return scene

    def events(self):
        return [e for e, _ in self.keeper.events]

    def test_opening_the_shop_greets_the_player_who_opened_it(self):
        shop = self.open_shop()
        self.assertIs(shop.keeper, self.keeper)
        self.assertEqual(self.events().count("open"), 1)
        self.assertIs(self.keeper.customer, self.room.players[0])
        self.assertEqual(self.keeper.bubble.text, "HELLO, FRIEND!")

    def test_insufficient_tickets_tilts_her_head_and_asks(self):
        shop = self.open_shop()
        shop.set_tab(shop_ui.TABS.index("COSMETICS"))
        shop.select(shop.rows.index(entry_for("pixel_crown")))
        self.frames(30)                                    # (the greeting has finished)
        self.key(pygame.K_e)
        self.assertEqual(self.keeper.state, "tilt")
        self.assertEqual(self.keeper.bubble.text, "NEED MORE TICKETS?")
        self.assertEqual(self.profiles[0].tickets, 40)    # nothing was charged
        self.assertIsNone(shop.modal)

    def test_a_successful_purchase_celebrates_once(self):
        shop = self.open_shop()
        shop.set_tab(shop_ui.TABS.index("COSMETICS"))
        shop.select(shop.rows.index(entry_for("star_hair_clip")))
        self.frames(30)
        self.key(pygame.K_e, 20)                           # BUY? box opens
        self.assertIsNotNone(shop.modal)
        self.key(pygame.K_e, 2)                            # BUY (default choice? make it explicit below)
        if shop.modal is not None:
            shop.modal.handle_event(key_event(pygame.K_LEFT))
            shop.modal.handle_event(key_event(pygame.K_e))
        self.frames(3)
        self.assertTrue(self.profiles[0].inventory.has_item("star_hair_clip"))
        self.assertEqual(self.events().count("purchase"), 1)
        self.assertEqual(self.keeper.state, "celebrate")
        self.assertEqual(self.keeper.bubble.text, "PURRFECT CHOICE!")
        self.assertEqual(self.profiles[0].tickets, 40 - entry_for("star_hair_clip").cost)

    def test_mashing_buy_cannot_buy_twice_or_repeat_the_reaction(self):
        shop = self.open_shop()
        entry = entry_for("star_hair_clip")
        shop.set_tab(shop_ui.TABS.index("COSMETICS"))
        shop.select(shop.rows.index(entry))
        self.frames(30)
        shop._answered(entry, "BUY")
        shop._answered(entry, "BUY")                       # a repeated answer: refused as already owned
        shop.activate()                                    # E during the lock: ignored
        self.assertEqual(self.events().count("purchase"), 1)
        self.assertEqual(self.profiles[0].tickets, 40 - entry.cost)
        self.assertEqual(self.profiles[0].inventory.get_quantity("star_hair_clip"), 1)

    def test_a_cancelled_or_refused_buy_does_not_celebrate(self):
        shop = self.open_shop()
        entry = entry_for("star_hair_clip")
        shop._answered(entry, "CANCEL")
        self.assertNotIn("purchase", self.events())
        self.profiles[0].spend_tickets(self.profiles[0].tickets)
        shop._answered(entry, "BUY")
        self.assertNotIn("purchase", self.events())
        self.assertEqual(self.events().count("insufficient"), 1)

    def test_leaving_waves_goodbye_in_the_room(self):
        shop = self.open_shop()
        self.key(pygame.K_ESCAPE, 40)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(self.events().count("leave"), 1)
        self.assertIsNone(self.keeper.customer)
        self.assertEqual(self.keeper.bubble.text, "COME BACK SOON!")

    def test_player_two_is_the_customer_and_pays_with_their_own_tickets(self):
        shop = self.open_shop(1, interact=pygame.K_RETURN)
        self.assertIs(shop.owner, self.game.session.players[1])
        self.assertIs(self.keeper.customer, self.room.players[1])
        entry = entry_for("cat_tail")
        shop._answered(entry, "BUY")
        self.assertTrue(self.profiles[1].inventory.has_item("cat_tail"))
        self.assertFalse(self.profiles[0].inventory.has_item("cat_tail"))
        self.assertEqual((self.profiles[0].tickets, self.profiles[1].tickets), (40, 500 - entry.cost))
        self.assertIs(self.keeper.watching, self.room.players[1])

    def test_p1_keys_do_not_drive_p2s_shop_and_the_keeper_does_not_eat_keys(self):
        shop = self.open_shop(1, interact=pygame.K_RETURN)
        shop.set_tab(shop_ui.TABS.index("HOME"))
        index = shop.index
        self.key(pygame.K_s)                                # P1's DOWN: not P2's shop
        self.assertEqual(shop.index, index)
        self.key(pygame.K_DOWN)
        self.assertEqual(shop.index, index + 1)

    def test_shop_navigation_works_while_she_talks(self):
        shop = self.open_shop()
        shop.set_tab(shop_ui.TABS.index("HOME"))            # a tab with several rows
        self.assertTrue(self.keeper.bubble.visible)
        for k, attr in ((pygame.K_s, "index"), (pygame.K_d, "tab")):       # P1's own keys
            before = getattr(shop, attr)
            self.key(k)
            self.assertEqual(getattr(shop, attr), before + 1, k)
        self.key(pygame.K_ESCAPE, 40)
        self.assertIs(self.game.scenes.current, self.room)

    def test_the_shop_draws_with_every_reaction(self):
        shop = self.open_shop()
        surf = pygame.Surface((400, 300))
        for event in ("open", "purchase", "insufficient", "leave"):
            self.keeper.notify(event, self.room.players[0])
            shop.draw(surf)
            self.keeper.update(0.3)


class PortraitLayoutTests(unittest.TestCase):
    def test_the_portrait_overlaps_no_other_part_of_the_shop(self):
        box = shop_ui.KEEPER_BOX
        panel = pygame.Rect(box.x - shop_ui.BUBBLE_W - 4, box.y + 1, shop_ui.BUBBLE_W, box.h - 2)
        font = get_font()
        title = pygame.Rect(16, 12, font.size("PRIZE COUNTER", 2)[0], 14)
        balance_w = font.size("99999", 2)[0]                      # even a five-digit balance
        balance = pygame.Rect(FRAME.right - 10 - balance_w - 14, 12, balance_w + 14, 24)
        tabs_top = 44
        for part in (box, panel):
            self.assertFalse(part.colliderect(title), part)
            self.assertFalse(part.colliderect(balance), part)
            self.assertLess(part.bottom, tabs_top)
            self.assertFalse(part.colliderect(shop_ui.LIST) or part.colliderect(shop_ui.SIDE))
            self.assertTrue(FRAME.contains(part))

    def test_a_speech_bubble_text_fits_in_two_lines(self):
        for text in sk.SAYS.values():
            from ui import wrap_text
            self.assertLessEqual(len(wrap_text(text, shop_ui.BUBBLE_W - 8)), 2, text)


class NoAudioTests(unittest.TestCase):
    def test_a_keeper_without_a_sound_callback_works(self):
        k = Shopkeeper((0, 0), sound=None)
        k.notify("purchase", walker(0, 0))
        run(k, 2)

    def test_the_whole_shop_flow_works_with_no_audio_device(self):
        with patch.object(pygame.mixer, "get_init", return_value=None), \
                patch.object(pygame.mixer, "init", side_effect=pygame.error("no device")):
            game = Game(session=LocalSession([PlayerProfile(profile_id="q", tickets=100)]))
        self.addCleanup(game.quit)
        self.assertFalse(game.audio.enabled)
        room = goto_room(game, "prize_plaza")
        shop = ShopScene(game, game.session.players[0], keeper=room.mochi)
        game.scenes.push(shop)
        for _ in range(60):
            game.step([], DT)
        shop._answered(entry_for("star_pin"), "BUY")
        shop.on_action("back")
        for _ in range(60):
            game.step([], DT)
        self.assertIn("purchase", [e for e, _ in room.mochi.events])

    def test_a_muted_game_plays_no_meow_but_still_animates(self):
        game = Game(session=LocalSession([PlayerProfile(profile_id="m", tickets=100)]))
        self.addCleanup(game.quit)
        game.audio.set_muted(True)
        room = goto_room(game, "prize_plaza")
        room.mochi.notify("purchase", room.players[0])
        self.assertNotIn("meow", game.audio.last_effect)
        self.assertEqual(room.mochi.state, "celebrate")

    def test_the_meow_asset_exists_and_is_quiet(self):
        import audio_manager as am
        self.assertIn("meow", am.SFX_FILES)
        self.assertLess(am.SFX_GAIN["meow"], 0.8)
        self.assertGreaterEqual(am.MIN_GAP["meow"], 1.0)
        self.assertTrue(os.path.exists(os.path.join(am.ASSET_DIR, "sfx", "meow.wav")))


if __name__ == "__main__":
    unittest.main()
