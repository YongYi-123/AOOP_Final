"""Tests for Mochi's Retro Racer talk (mochi_chat.py): the chat entry only exists after the vending machine's REAL Secret
Interface has opened; the first story is recorded once; the hint appears after it; Secret Item 01 updates the talk; saves
and two players follow the shared story; the Prize Counter shop is untouched.

Run headless from this folder:   python -m unittest test_mochi_chat -v
"""
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import mochi_chat as C  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from miao_meow import PLAZA  # noqa: E402
from mochi_chat import MochiChatScene  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from quests import MOCHI_ARCADE_STORY, SECRET_ITEM_RETRO_RACER, QuestManager  # noqa: E402
from room_testing import goto_room  # noqa: E402
from shop_ui import ShopScene  # noqa: E402
from vending_ui import VendingScene  # noqa: E402

DT = 1 / 60
K = pygame
KONAMI = [K.K_UP, K.K_UP, K.K_DOWN, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_LEFT, K.K_RIGHT, K.K_b, K.K_a]


def down(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def up(k):
    return pygame.event.Event(pygame.KEYUP, key=k, mod=0)


class Base(unittest.TestCase):
    players = 1

    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="ma", display_name="Ann", tickets=100),
                         PlayerProfile(profile_id="mb", display_name="Bo", tickets=100)][:self.players]
        self.start()

    def start(self):
        self.game = Game(session=LocalSession(self.profiles[0]))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.m = self.story.manager
        self.m.finish_opening()

    def frames(self, n=30, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def tap(self, k):
        self.frames(1, [down(k)])
        self.frames(1, [up(k)])

    # ------------------------------------------------------------ the real secret
    def unlock_for_real(self):
        """Open the vending machine's hidden screen with its own key sequence, exactly as a player does."""
        room = goto_room(self.game, "arcade_floor")
        room.acting_player = room.players[0]
        room.open_vending()
        room.acting_player = None
        self.frames(90)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, VendingScene)
        for k in KONAMI:
            self.tap(k)
        self.assertIsNotNone(scene.secret)
        while self.game.scenes.current is not room:                 # leave the hidden screens
            self.frames(1, [down(K.K_ESCAPE)])
            self.frames(90)
        return room

    # ------------------------------------------------------------ Mochi
    def open_shop(self, who=0):
        room = goto_room(self.game, PLAZA)
        room.acting_player = room.players[who]
        room.open_prize_counter()
        room.acting_player = None
        self.frames(90)
        shop = self.game.scenes.current
        self.assertIsInstance(shop, ShopScene)
        return shop

    def bag(self, shop):
        return shop.owner.controls.inventory[0]

    def open_chat(self, who=0):
        shop = self.open_shop(who)
        self.tap(self.bag(shop))
        self.frames(90)
        chat = self.game.scenes.current
        self.assertIsInstance(chat, MochiChatScene)
        return chat

    def labels(self, chat):
        return [label for label, _ in chat.options]

    def read(self, chat, index=0):
        """Choose option `index` and read the whole conversation (confirm until the box closes)."""
        chat.index = index
        owner_key = chat.owner.controls.interact[0]
        self.tap(owner_key)
        self.assertIsNotNone(chat.talk)
        lines = [l for l in chat.talk.lines]
        for _ in range(len(lines) * 2 + 4):
            if chat.talk is None:
                break
            self.frames(60)                                         # finish typing
            self.frames(1, [down(K.K_RETURN)])
            self.frames(1, [up(K.K_RETURN)])
        self.assertIsNone(chat.talk)
        return lines


# ------------------------------------------------------------------ before the unlock
class LockedTests(Base):
    def test_no_chat_option_exists_before_the_secret_interface_opens(self):
        self.assertIsNone(self.m.mochi_story_stage)
        self.assertEqual(C.chat_options(self.m.mochi_story_stage), [])
        shop = self.open_shop()
        self.assertFalse(shop.chat_ready())

    def test_the_bag_key_in_the_shop_does_nothing_and_the_hint_row_is_unchanged(self):
        shop = self.open_shop()
        self.tap(self.bag(shop))
        self.frames(5)
        self.assertIs(self.game.scenes.current, shop)
        shop.draw(pygame.Surface((384, 300)))
        self.assertFalse(any("CHAT" in h for h in shop.hints))

    def test_ordinary_use_of_the_vending_machine_does_not_unlock_it(self):
        room = goto_room(self.game, "arcade_floor")
        room.acting_player = room.players[0]
        room.open_vending()
        room.acting_player = None
        self.frames(90)
        scene = self.game.scenes.current
        for k in (K.K_DOWN, K.K_UP, K.K_e, K.K_RIGHT, K.K_LEFT):      # browse and buy, nothing like the sequence
            self.tap(k)
        for k in KONAMI[:-1]:                                         # ... and an unfinished sequence
            self.tap(k)
        self.tap(K.K_c)
        self.assertIsNone(scene.secret)
        self.assertIsNone(self.m.mochi_story_stage)
        self.assertFalse(self.m.secret_interface_unlocked)

    def test_the_story_cannot_be_marked_heard_before_the_unlock(self):
        self.m.handle(MOCHI_ARCADE_STORY)
        self.assertNotIn(MOCHI_ARCADE_STORY, self.m.state.get("flags", {}))
        self.assertIsNone(self.m.mochi_story_stage)

    def test_a_secret_item_alone_does_not_open_the_chat(self):
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        self.assertIsNone(self.m.mochi_story_stage)


# ------------------------------------------------------------------ the unlock and the first story
class UnlockedTests(Base):
    def test_the_real_secret_screen_makes_the_old_arcade_option_appear(self):
        self.unlock_for_real()
        self.assertEqual(self.m.mochi_story_stage, "new")
        chat = self.open_chat()
        self.assertEqual(self.labels(chat), [C.STORIES])

    def test_with_the_earlier_quests_done_the_secret_moves_the_story_to_the_way_out(self):
        for event, key in (("tour_arcade", None), ("met_mochi", None), ("game_played", "a"), ("game_played", "b"),
                           ("game_played", "c"), ("tickets_earned", None)):
            self.m.handle(event, key)
        self.unlock_for_real()
        self.assertEqual(self.m.active.id, "the_way_out")
        self.assertEqual(self.m.mochi_story_stage, "new")

    def test_the_shop_names_the_chat_key_once_unlocked(self):
        self.unlock_for_real()
        shop = self.open_shop()
        shop.draw(pygame.Surface((384, 300)))
        self.assertTrue(any("CHAT" in h for h in shop.hints))

    def test_the_first_story_is_the_scripted_dialogue_and_unlocks_the_hint(self):
        self.unlock_for_real()
        chat = self.open_chat()
        lines = self.read(chat)
        self.assertEqual([(l.speaker, l.text) for l in lines][:3], [
            ("MOCHI", "You know, back when this arcade was packed, Retro Racer was everyone's favorite."),
            ("PLAYER", "Really? Racing games were that popular?"),
            ("MOCHI", "Oh, absolutely. People would line up just to get a turn.")])
        self.assertEqual(lines[-1].text, "Heh. Let's just say some of them spent more time doing everything except racing.")
        self.assertEqual(self.m.mochi_story_stage, "heard")
        self.assertEqual(self.labels(chat), [C.STORIES, C.HINT])

    def test_miao_meow_joins_only_when_she_is_already_in_the_plaza_and_is_never_moved(self):
        self.unlock_for_real()
        brain = self.story.brain
        brain.place("home", (100, 100))
        chat = self.open_chat()
        away = self.read(chat)
        self.assertNotIn("MIAO MEOW", [l.speaker for l in away])
        self.assertEqual(brain.room_id, "home")                   # not teleported over
        brain.place(PLAZA, (200, 200))
        there = self.read(chat)
        self.assertEqual([(l.speaker, l.text) for l in there][-3:], [
            ("MIAO MEOW", "I tried that once! I finished last!"),
            ("MOCHI", "You finished last when you were actually racing, too."),
            ("MIAO MEOW", "MOCHI!!")])

    def test_the_first_story_is_recorded_once_however_often_it_is_read(self):
        self.unlock_for_real()
        chat = self.open_chat()
        self.read(chat)
        flags = dict(self.m.state["flags"])
        self.read(chat)
        self.read(chat)
        self.assertEqual(self.m.state["flags"], flags)
        self.assertTrue(flags[MOCHI_ARCADE_STORY])

    def test_quitting_the_story_halfway_does_not_record_it(self):
        self.unlock_for_real()
        chat = self.open_chat()
        chat.index = 0
        self.tap(chat.owner.controls.interact[0])
        self.assertIsNotNone(chat.talk)
        self.assertEqual(self.m.mochi_story_stage, "new")

    def test_the_hint_only_says_to_stop(self):
        self.unlock_for_real()
        chat = self.open_chat()
        self.read(chat)
        lines = self.read(chat, 1)
        self.assertEqual([l.text for l in lines], ["Funny thing about racing...",
                                                    "Everyone thinks the only way to win is to go faster.",
                                                    "But the weirdest players? They knew when to stop."])
        text = " ".join(l.text for l in C.HINT_LINES + C.OLD_ARCADE + C.RACE_LINES).lower()
        for word in ("20", "second", "reverse", "backward", "kevin"):
            self.assertNotIn(word, text)


# ------------------------------------------------------------------ Secret Item 01
class SecretItemTests(Base):
    def test_after_the_item_the_talk_changes_and_the_hint_is_gone(self):
        self.unlock_for_real()
        chat = self.open_chat()
        self.read(chat)
        self.assertIn(C.HINT, self.labels(chat))
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        self.assertEqual(self.m.mochi_story_stage, "found")
        self.assertEqual(self.labels(chat), [C.STORIES, C.RACE])
        lines = self.read(chat, 1)
        self.assertEqual([l.text for l in lines], ["So you actually found that strange road, huh?",
                                                    "Heh. Guess you're one of those players who don't follow the rules either."])

    def test_an_item_found_before_the_unlock_goes_straight_to_the_found_talk(self):
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        self.assertIsNone(self.m.mochi_story_stage)
        self.unlock_for_real()
        self.assertEqual(self.m.mochi_story_stage, "found")
        chat = self.open_chat()
        self.assertNotIn(C.HINT, self.labels(chat))
        self.assertIn(C.RACE, self.labels(chat))

    def test_another_secret_item_does_not_count_as_item_one(self):
        self.unlock_for_real()
        self.m.handle("secret_item_found", "gem_cyan")
        self.assertEqual(self.m.mochi_story_stage, "new")


# ------------------------------------------------------------------ saves and two players
class SaveTests(Base):
    def test_everything_comes_back_after_a_save_and_reload(self):
        self.unlock_for_real()
        chat = self.open_chat()
        self.read(chat)
        path = os.path.join(tempfile.mkdtemp(), "p.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(path), True)
        ProfileStore(path).save(self.profiles[0])
        loaded = ProfileStore(path).load()
        m = QuestManager(LocalSession([loaded]))
        self.assertEqual(m.mochi_story_stage, "heard")
        m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        ProfileStore(path).save(loaded)
        self.assertEqual(QuestManager(LocalSession([ProfileStore(path).load()])).mochi_story_stage, "found")

    def test_a_reloaded_game_shows_the_right_options_in_the_shop(self):
        self.unlock_for_real()
        self.read(self.open_chat())
        self.game.quit()
        self.start()
        self.assertEqual(self.m.mochi_story_stage, "heard")
        self.assertEqual(self.labels(self.open_chat()), [C.STORIES, C.HINT])

    def test_a_locked_save_stays_locked(self):
        path = os.path.join(tempfile.mkdtemp(), "p.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(path), True)
        ProfileStore(path).save(self.profiles[0])
        self.assertIsNone(QuestManager(LocalSession([ProfileStore(path).load()])).mochi_story_stage)


class OtherSavedProfileTests(Base):
    """A second profile exists on disk; only the playing one has a story, and the other keeps its own."""
    players = 2

    def test_the_progress_is_the_playing_profiles_alone(self):
        self.unlock_for_real()                                  # the player opens the secret ...
        chat = self.open_chat(who=0)                            # ... and chats about it
        self.assertEqual(self.labels(chat), [C.STORIES])
        self.read(chat)
        self.assertTrue(self.profiles[0].story["flags"][MOCHI_ARCADE_STORY])
        self.assertEqual(self.profiles[1].story, {})            # the other save is untouched
        self.assertEqual(self.labels(self.open_chat(who=0)), [C.STORIES, C.HINT])

    def test_the_option_is_not_there_before_the_secret(self):
        shop = self.open_shop(who=0)
        self.tap(self.bag(shop))
        self.assertIs(self.game.scenes.current, shop)


# ------------------------------------------------------------------ the shop is untouched
class ShopUntouchedTests(Base):
    def buy_first(self, shop):
        before = shop.profile.tickets
        shop.index = 0
        shop.activate()
        shop.modal.on_choice("BUY") if shop.modal else None
        return before

    def test_buying_works_the_same_before_and_after_the_unlock(self):
        for unlocked in (False, True):
            if unlocked:
                self.unlock_for_real()
            shop = self.open_shop()
            entry = shop.entry
            profile = shop.profile
            if shop.shop.blocked(entry):
                shop.select(1)
                entry = shop.entry
            tickets, owned = profile.tickets, shop.shop.quantity(entry)
            shop.activate()
            self.assertIsNotNone(shop.modal)
            shop._answered(entry, "BUY")
            self.assertEqual(profile.tickets, tickets - entry.cost)
            self.assertEqual(shop.shop.quantity(entry), owned + 1)
            self.tap(K.K_ESCAPE)
            self.frames(90)

    def test_the_shop_tabs_keys_and_hints_for_racing_and_exchange_are_unchanged(self):
        self.unlock_for_real()
        shop = self.open_shop()
        from shop_ui import EXCHANGE, RACING, TABS
        for tab in (RACING, EXCHANGE):
            shop.set_tab(TABS.index(tab))
            shop.draw(pygame.Surface((384, 300)))
            self.assertFalse(any("CHAT" in h for h in shop.hints), tab)

    def test_leaving_the_chat_returns_to_the_shop_and_then_the_room(self):
        self.unlock_for_real()
        chat = self.open_chat()
        self.tap(K.K_ESCAPE)
        self.frames(90)
        self.assertIsInstance(self.game.scenes.current, ShopScene)
        self.tap(K.K_ESCAPE)
        self.frames(90)
        self.assertIs(self.game.scenes.current, self.game.hub.room(PLAZA))


if __name__ == "__main__":
    unittest.main()
