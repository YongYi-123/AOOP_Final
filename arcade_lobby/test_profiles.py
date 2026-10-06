"""Tests for multiple saved profiles: the ProfileManager, old-save migration,
the profile select screens and the startup flow.

Run with:  python -m unittest test_profiles
"""
import json
import os
import shutil
import tempfile
import unittest
from datetime import date
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from menus import (NEW_PROFILE, VISIBLE_ROWS, PlayerCountScene, ProfileSelectScene,  # noqa: E402
                   TitleScene, scroll_window)
from player_profile import PlayerProfile  # noqa: E402
from profile_manager import (DuplicateNameError, InvalidNameError, ProfileManager,  # noqa: E402
                             normalize_name)
from room_scene import BaseRoomScene  # noqa: E402
from settings import PROFILE_NAME_MAX  # noqa: E402

DT = 1 / 60
DAY1 = date(2025, 3, 10)
CLOCK = lambda: GameClock(lambda: DAY1)  # noqa: E731


def key(k, down=True, char=""):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=k, mod=0, unicode=char)


def typed(text):
    return [key(ord(c.lower()) if c.isalnum() else pygame.K_SPACE, char=c) for c in text]


class TempTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.root = os.path.join(self.dir, "saves")
        self.legacy = os.path.join(self.dir, "save_data.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def manager(self, **kw):
        kw.setdefault("clock", CLOCK())
        return ProfileManager(self.root, **kw)

    def read(self, path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)


class ManagerTests(TempTest):
    def test_a_first_launch_has_no_profiles_and_writes_the_index(self):
        m = self.manager()
        self.assertEqual(m.list_profiles(), [])
        self.assertTrue(os.path.exists(os.path.join(self.root, "profiles.json")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "profiles")))

    def test_create_the_first_profile(self):
        m = self.manager()
        p = m.create_profile("YongYi")
        self.assertEqual(p.display_name, "YongYi")
        self.assertTrue(m.profile_exists(p.profile_id))
        self.assertEqual([i.display_name for i in m.list_profiles()], ["YongYi"])
        self.assertTrue(os.path.exists(os.path.join(self.root, "profiles", f"{p.profile_id}.json")))
        info = m.list_profiles()[0]
        self.assertTrue(info.created_at)
        self.assertIsNone(info.last_played)

    def test_file_names_use_the_id_never_the_display_name(self):
        m = self.manager()
        for name in ("../evil", "a/b\\c", "CON", "two  words"):
            p = m.create_profile(name)
            self.assertRegex(p.profile_id, r"^[0-9a-f]{32}$")
        files = sorted(os.listdir(os.path.join(self.root, "profiles")))
        self.assertEqual(len(files), 4)
        for f in files:
            self.assertRegex(f, r"^[0-9a-f]{32}\.json$")
        self.assertEqual(os.listdir(self.root).count("evil"), 0)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "evil")))

    def test_the_display_name_is_not_the_identity(self):
        m = self.manager()
        a = m.create_profile("Alice")
        m.delete_profile(a.profile_id)
        b = m.create_profile("Alice")               # same name again, a different profile
        self.assertNotEqual(a.profile_id, b.profile_id)

    def test_names_are_trimmed_blank_ones_rejected_and_length_limited(self):
        m = self.manager()
        self.assertEqual(m.create_profile("  Bob   Smith  ").display_name, "Bob Smith")
        for bad in ("", "   ", "\t\n", "///"):
            with self.assertRaises(InvalidNameError, msg=repr(bad)):
                m.create_profile(bad)
        with self.assertRaises(InvalidNameError):
            m.create_profile("X" * (PROFILE_NAME_MAX + 1))
        self.assertEqual(m.create_profile("X" * PROFILE_NAME_MAX).display_name, "X" * PROFILE_NAME_MAX)
        with self.assertRaises(InvalidNameError):
            normalize_name(None)

    def test_duplicate_display_names_are_refused_ignoring_case_and_spaces(self):
        m = self.manager()
        m.create_profile("Alice")
        for dup in ("alice", "ALICE", "  Alice "):
            with self.assertRaises(DuplicateNameError):
                m.create_profile(dup)
        self.assertEqual(len(m), 1)
        self.assertFalse(m.name_available("alice"))
        self.assertTrue(m.name_available("Alicia"))

    def test_many_profiles_are_all_kept_there_is_no_cap(self):
        m = self.manager()
        for i in range(120):
            m.create_profile(f"P{i}")
        self.assertEqual(len(m.list_profiles()), 120)
        self.assertEqual(len({i.profile_id for i in m.list_profiles()}), 120)
        again = self.manager()
        self.assertEqual([i.display_name for i in again.list_profiles()], [f"P{i}" for i in range(120)])

    def test_profiles_keep_their_own_tokens_tickets_inventory_daily_and_decorations(self):
        m = self.manager()
        a, b = m.create_profile("Alice"), m.create_profile("Bob")
        a.add_tokens(5, "T")
        a.add_tickets(40)
        a.inventory.add_item("cat_sticker", 1)
        a.inventory.add_item("free_play_coupon", 2)
        a.record_login()
        a.set_home_decoration("rug", "rug_lounge")
        a.record_score("retro_racer", 900)
        b.spend_tokens(3, "T")
        b.add_tickets(7)
        b.inventory.add_item("free_play_coupon", 4)
        b.set_home_decoration("rug", "rug_other")
        self.assertEqual((a.tokens, a.tickets), (15, 40))
        self.assertEqual((b.tokens, b.tickets), (7, 7))
        self.assertEqual(a.inventory.get_quantity("cat_sticker"), 1)
        self.assertEqual(a.inventory.get_quantity("free_play_coupon"), 2)
        self.assertEqual(b.inventory.get_quantity("cat_sticker"), 0)
        self.assertEqual(b.inventory.get_quantity("free_play_coupon"), 4)
        self.assertEqual(a.last_login_date, DAY1)
        self.assertIsNone(b.last_login_date)
        self.assertEqual(a.home_decorations, {"rug": "rug_lounge"})
        self.assertEqual(b.home_decorations, {"rug": "rug_other"})
        self.assertEqual(a.high_score("retro_racer"), 900)
        self.assertEqual(b.high_score("retro_racer"), 0)

        restarted = self.manager()                              # "close the game and reopen it"
        ids = {i.display_name: i.profile_id for i in restarted.list_profiles()}
        ra, rb = restarted.load_profile(ids["Alice"]), restarted.load_profile(ids["Bob"])
        self.assertEqual((ra.tokens, ra.tickets, rb.tokens, rb.tickets), (15, 40, 7, 7))
        self.assertEqual(ra.inventory.get_quantity("cat_sticker"), 1)
        self.assertEqual(ra.inventory.get_quantity("free_play_coupon"), 2)
        self.assertEqual(rb.inventory.get_quantity("free_play_coupon"), 4)
        self.assertEqual(ra.last_login_date, DAY1)
        self.assertIsNone(rb.last_login_date)
        self.assertEqual(ra.home_decorations, {"rug": "rug_lounge"})
        self.assertEqual(rb.home_decorations, {"rug": "rug_other"})
        self.assertEqual(ra.high_scores, {"retro_racer": 900})
        self.assertEqual((ra.profile_id, ra.display_name), (ids["Alice"], "Alice"))

    def test_daily_state_is_per_profile(self):
        m = self.manager()
        a, b = m.create_profile("Alice"), m.create_profile("Bob")
        a.record_login()
        claim = a.claim_daily_reward()
        self.assertIsNotNone(claim)
        self.assertFalse(a.daily_status().can_claim)
        self.assertTrue(b.daily_status().can_claim)             # Alice's claim is not Bob's
        self.assertEqual(b.tokens, 10)
        r = self.manager().load_profile(a.profile_id)
        self.assertFalse(r.daily_status().can_claim)

    def test_load_returns_the_one_live_instance(self):
        m = self.manager()
        a = m.create_profile("Alice")
        self.assertIs(m.load_profile(a.profile_id), a)
        self.assertIs(m.load_profile(a.profile_id), m.load_profile(a.profile_id))

    def test_every_change_autosaves_to_its_own_file_only(self):
        m = self.manager()
        a, b = m.create_profile("Alice"), m.create_profile("Bob")
        pa, pb = m.profile_path(a.profile_id), m.profile_path(b.profile_id)
        before_b = self.read(pb)
        a.add_tokens(5, "T")                                    # only Alice's file changes
        self.assertEqual(self.read(pa)["tokens"], 15)
        self.assertEqual(self.read(pb), before_b)
        b.add_tickets(3)
        self.assertEqual(self.read(pb)["tickets"], 3)
        self.assertEqual(self.read(pa)["tickets"], 0)
        self.assertEqual(self.read(pa)["profile_id"], a.profile_id)

    def test_interleaved_changes_never_cross_over(self):
        m = self.manager()
        a, b = m.create_profile("Alice"), m.create_profile("Bob")
        with a.batch(), b.batch():                              # both mid-change at the same time
            for _ in range(5):
                a.add_tokens(1, "T")
                b.spend_tokens(1, "T")
                a.add_tickets(2)
                b.add_tickets(1)
        ra, rb = self.read(m.profile_path(a.profile_id)), self.read(m.profile_path(b.profile_id))
        self.assertEqual((ra["tokens"], ra["tickets"]), (15, 10))
        self.assertEqual((rb["tokens"], rb["tickets"]), (5, 5))
        self.assertEqual((ra["display_name"], rb["display_name"]), ("Alice", "Bob"))

    def test_a_stale_copy_cannot_overwrite_a_profile(self):
        m = self.manager()
        a = m.create_profile("Alice")
        a.add_tokens(5, "T")
        stale = PlayerProfile(clock=CLOCK(), profile_id=a.profile_id, display_name="Alice")   # tokens 10
        self.assertFalse(m.save_profile(stale))
        self.assertEqual(self.read(m.profile_path(a.profile_id))["tokens"], 15)
        self.assertFalse(m.save_profile(PlayerProfile(clock=CLOCK())))               # not managed at all
        self.assertFalse(m.save_profile(PlayerProfile(clock=CLOCK(), profile_id="nope")))

    def test_saves_are_atomic(self):
        m = self.manager()
        a = m.create_profile("Alice")
        a.add_tokens(5, "T")
        path = m.profile_path(a.profile_id)
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            a.add_tokens(100, "T")                              # the write fails ...
        self.assertEqual(self.read(path)["tokens"], 15)         # ... and the old file is intact
        self.assertEqual(len(os.listdir(os.path.join(self.root, "profiles"))), 2)   # file + leftover tmp
        a.add_tokens(1, "T")
        self.assertEqual(self.read(path)["tokens"], 116)
        self.assertFalse(any(f.endswith(".tmp") for f in os.listdir(os.path.join(self.root, "profiles"))))

    def test_delete_removes_the_profile_and_its_file(self):
        m = self.manager()
        a, b = m.create_profile("Alice"), m.create_profile("Bob")
        path = m.profile_path(a.profile_id)
        self.assertTrue(m.delete_profile(a.profile_id))
        self.assertFalse(m.profile_exists(a.profile_id))
        self.assertFalse(os.path.exists(path))
        self.assertTrue(m.profile_exists(b.profile_id))
        self.assertFalse(m.delete_profile(a.profile_id))
        self.assertEqual([i.display_name for i in self.manager().list_profiles()], ["Bob"])
        self.assertTrue(m.name_available("Alice"))              # the name is free again

    def test_recent_profiles_and_player_count_are_remembered(self):
        m = self.manager()
        a, b, c = (m.create_profile(n) for n in "ABC")
        self.assertEqual(m.last_player_count, 1)
        m.record_session([a], 1)
        m.record_session([b, c], 2)
        again = self.manager()
        self.assertEqual(again.last_player_count, 2)
        self.assertEqual(again.recent_ids[:3], [b.profile_id, c.profile_id, a.profile_id])
        self.assertEqual(again.most_recent(), b.profile_id)
        self.assertEqual(again.most_recent(exclude=[b.profile_id]), c.profile_id)
        self.assertTrue(again.info(a.profile_id).last_played)

    def test_a_lost_index_is_rebuilt_from_the_profile_files(self):
        m = self.manager()
        a = m.create_profile("Alice")
        a.add_tickets(9)
        with open(m.index_path, "w") as f:
            f.write("{ not json")
        again = self.manager()
        self.assertEqual([i.display_name for i in again.list_profiles()], ["Alice"])
        self.assertEqual(again.load_profile(a.profile_id).tickets, 9)
        self.assertTrue(os.path.exists(m.index_path + ".corrupt"))

    def test_a_corrupt_profile_file_does_not_crash_the_manager(self):
        m = self.manager()
        a = m.create_profile("Alice")
        with open(m.profile_path(a.profile_id), "w") as f:
            f.write("garbage")
        again = self.manager()
        p = again.load_profile(a.profile_id)
        self.assertEqual((p.tokens, p.display_name), (10, "Alice"))


class MigrationTests(TempTest):
    OLD = {"version": 2, "tokens": 23, "tickets": 140, "total_games_played": 6,
           "lifetime_tickets_earned": 150, "lifetime_tokens_earned": 40, "lifetime_tokens_spent": 17,
           "chance_games_played": 3, "cats_petted": 9, "high_scores": {"retro_racer": 1200},
           "last_login_date": "2025-03-09", "daily_streak": 4, "last_daily_reward_claimed": "2025-03-09",
           "inventory": {"cat_sticker": 1, "free_play_coupon": 3},
           "home_decorations": {"rug": "rug_lounge", "plant_back": "plant_bushy"}}

    def write_legacy(self, data=None):
        with open(self.legacy, "w") as f:
            json.dump(self.OLD if data is None else data, f)

    def test_the_old_single_save_becomes_the_first_profile(self):
        self.write_legacy()
        m = self.manager(legacy_path=self.legacy)
        infos = m.list_profiles()
        self.assertEqual(len(infos), 1)
        self.assertEqual(infos[0].display_name, "PLAYER")
        p = m.load_profile(infos[0].profile_id)
        self.assertEqual((p.tokens, p.tickets), (23, 140))
        self.assertEqual(p.inventory.get_quantity("cat_sticker"), 1)
        self.assertEqual(p.inventory.get_quantity("free_play_coupon"), 3)
        self.assertEqual(p.high_scores, {"retro_racer": 1200})
        self.assertEqual(p.home_decorations, {"rug": "rug_lounge", "plant_back": "plant_bushy"})
        self.assertEqual((p.total_games_played, p.chance_games_played, p.cats_petted), (6, 3, 9))
        self.assertEqual((p.lifetime_tickets_earned, p.lifetime_tokens_earned, p.lifetime_tokens_spent),
                         (150, 40, 17))
        self.assertEqual((p.daily_streak, str(p.last_login_date)), (4, "2025-03-09"))

    def test_the_old_file_is_kept_not_wiped(self):
        self.write_legacy()
        self.manager(legacy_path=self.legacy)
        self.assertFalse(os.path.exists(self.legacy))
        self.assertEqual(self.read(self.legacy + ".migrated")["tokens"], 23)

    def test_migration_happens_exactly_once(self):
        self.write_legacy()
        first = self.manager(legacy_path=self.legacy)
        pid = first.list_profiles()[0].profile_id
        first.load_profile(pid).add_tokens(5, "T")
        self.write_legacy({"tokens": 999})                       # an old file shows up again ...
        again = self.manager(legacy_path=self.legacy)
        self.assertEqual([i.profile_id for i in again.list_profiles()], [pid])   # ... and is ignored
        self.assertEqual(again.load_profile(pid).tokens, 28)
        self.assertTrue(os.path.exists(self.legacy))             # (left alone)

    def test_migration_does_not_repeat_after_the_migrated_profile_is_deleted(self):
        self.write_legacy()
        m = self.manager(legacy_path=self.legacy)
        m.delete_profile(m.list_profiles()[0].profile_id)
        self.assertEqual(self.manager(legacy_path=self.legacy).list_profiles(), [])

    def test_no_old_save_means_no_migration(self):
        m = self.manager(legacy_path=self.legacy)
        self.assertEqual(m.list_profiles(), [])
        self.assertIsNone(m.migrated_from)

    def test_an_unreadable_old_save_is_left_alone(self):
        with open(self.legacy, "w") as f:
            f.write("{ nope")
        m = self.manager(legacy_path=self.legacy)
        self.assertEqual(m.list_profiles(), [])
        self.assertTrue(os.path.exists(self.legacy))
        self.assertFalse(os.path.exists(os.path.join(self.root, "profiles.json")))   # may retry next launch

    def test_a_version_1_save_with_coins_migrates_too(self):
        self.write_legacy({"version": 1, "coins": 4, "tickets": 2})
        m = self.manager(legacy_path=self.legacy)
        p = m.load_profile(m.list_profiles()[0].profile_id)
        self.assertEqual((p.tokens, p.tickets), (4, 2))

    def test_unknown_inventory_ids_survive_migration(self):
        self.write_legacy({"inventory": {"removed_item": 2, "cat_sticker": 1}})
        m = self.manager(legacy_path=self.legacy)
        data = self.read(m.profile_path(m.list_profiles()[0].profile_id))
        self.assertEqual(data["inventory"], {"removed_item": 2, "cat_sticker": 1})

    def test_the_migrated_profile_works_in_a_game(self):
        self.write_legacy()
        m = self.manager(legacy_path=self.legacy)
        pid = m.list_profiles()[0].profile_id
        g = Game(profiles=m)
        self.assertIsInstance(g.scenes.current, TitleScene)
        self.assertEqual(m.load_profile(pid).tokens, 23)


class ScrollTests(unittest.TestCase):
    def test_the_window_only_moves_when_the_selection_leaves_it(self):
        rows = 6
        top = 0
        for sel in range(0, 6):
            top = scroll_window(sel, top, 40, rows)
            self.assertEqual(top, 0)
        top = scroll_window(6, top, 40, rows)
        self.assertEqual(top, 1)
        top = scroll_window(39, top, 40, rows)
        self.assertEqual(top, 34)
        top = scroll_window(0, top, 40, rows)
        self.assertEqual(top, 0)

    def test_a_short_list_never_scrolls(self):
        self.assertEqual(scroll_window(3, 0, 4, 6), 0)


class FlowTest(TempTest):
    """Drives the real startup screens through Game."""

    def setUp(self):
        super().setUp()
        self.game = None

    def start(self, names=(), **kw):
        m = self.manager(**kw)
        self.ids = {n: m.create_profile(n).profile_id for n in names}
        self.m = m
        self.game = Game(profiles=m, clock=CLOCK())
        return self.game

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def press(self, *keys):
        for k in keys:
            self.frames(1, [key(k)])

    def settle(self):
        self.frames(int(0.8 / DT))

    @property
    def scene(self):
        return self.game.scenes.current

    def go(self, *keys):
        """Press keys, letting each screen wipe finish."""
        for k in keys:
            self.press(k)
            self.settle()


class ListScrollTests(FlowTest):
    def test_the_profile_list_scrolls_with_many_profiles(self):
        self.start([f"N{i:02d}" for i in range(30)])
        self.go(pygame.K_RETURN, pygame.K_RETURN)               # title, 1 player
        sel = self.scene
        self.assertIsInstance(sel, ProfileSelectScene)
        self.assertEqual(sel.total, 31)
        self.assertEqual(sel.top, 0)
        for _ in range(VISIBLE_ROWS + 3):
            self.press(pygame.K_DOWN)
        self.assertEqual(sel.selected, VISIBLE_ROWS + 3)
        self.assertGreater(sel.top, 0)
        self.assertTrue(sel.top <= sel.selected < sel.top + VISIBLE_ROWS)
        for _ in range(60):                                     # wraps around through "+ NEW PROFILE"
            self.press(pygame.K_DOWN)
            self.assertTrue(sel.top <= sel.selected < sel.top + VISIBLE_ROWS)
        self.press(pygame.K_UP)
        self.frames(2)

    def test_the_last_row_is_new_profile(self):
        self.start(["A", "B"])
        self.go(pygame.K_RETURN, pygame.K_RETURN)
        sel = self.scene
        self.press(pygame.K_UP)                                  # (starts on a profile; up wraps)
        for _ in range(3):
            self.press(pygame.K_DOWN)
        sel.selected = sel.total - 1
        self.assertTrue(sel.on_new_profile)
        self.assertEqual(NEW_PROFILE, "+ NEW PROFILE")
        self.frames(2)                                           # draws without error


class StartupFlowTests(FlowTest):
    def test_the_game_starts_on_the_title_with_no_hub(self):
        self.start(["A"])
        self.assertIsInstance(self.scene, TitleScene)
        self.assertIsNone(self.game.hub)
        self.assertIsNone(self.game.profile)

    def test_one_player_flow_ends_in_the_hub_with_the_chosen_profile(self):
        self.start(["Alice", "Bob"])
        self.go(pygame.K_RETURN)
        self.assertIsInstance(self.scene, PlayerCountScene)
        self.go(pygame.K_RETURN)                                 # 1 PLAYER
        self.assertIsInstance(self.scene, ProfileSelectScene)
        self.assertEqual(self.scene.title, "SELECT PROFILE")
        self.go(pygame.K_DOWN)
        self.go(pygame.K_RETURN)
        self.assertIsInstance(self.scene, BaseRoomScene)
        self.assertEqual(self.scene.room_id, "home")
        self.assertEqual(self.game.session.player_count, 1)
        self.assertEqual(self.game.profile.profile_id, self.ids["Bob"] if self.scene.profile.display_name == "Bob"
                         else self.ids["Alice"])

    def test_two_player_flow_needs_two_different_profiles(self):
        self.start(["Alice", "Bob"])
        self.go(pygame.K_RETURN, pygame.K_DOWN)                  # title, then pick 2 PLAYERS
        self.go(pygame.K_RETURN)
        p1 = self.scene
        self.assertEqual(p1.title, "P1 SELECT PROFILE")
        p1.selected = 0
        self.go(pygame.K_RETURN)                                 # P1 = Alice
        p2 = self.scene
        self.assertIsInstance(p2, ProfileSelectScene)
        self.assertEqual(p2.title, "P2 SELECT PROFILE")
        self.assertEqual(p2.taken, {self.ids["Alice"]})
        p2.selected = 0                                          # Alice again: refused
        self.go(pygame.K_RETURN)
        self.assertIs(self.scene, p2)
        self.assertIn("ALREADY", p2.message)
        p2.selected = 1                                          # Bob
        self.go(pygame.K_RETURN)
        self.assertIsInstance(self.scene, BaseRoomScene)
        s = self.game.session
        self.assertEqual(s.player_count, 2)
        self.assertEqual([p.profile.display_name for p in s], ["Alice", "Bob"])
        self.assertNotEqual(s.players[0].profile.profile_id, s.players[1].profile.profile_id)

    def test_the_most_recent_profile_is_highlighted_but_never_auto_entered(self):
        self.start(["Alice", "Bob", "Cy"])
        self.m.record_session([self.m.load_profile(self.ids["Cy"])], 2)
        self.game = Game(profiles=self.manager(), clock=CLOCK())
        self.go(pygame.K_RETURN)
        self.assertIsInstance(self.scene, PlayerCountScene)
        self.assertEqual(self.scene.count, 2)                    # the last player count is preselected
        self.go(pygame.K_RETURN)
        self.assertIsInstance(self.scene, ProfileSelectScene)    # still waiting for confirmation
        self.assertEqual(self.scene.selected_info.profile_id, self.ids["Cy"])
        self.assertIsNone(self.game.session)

    def test_starting_a_session_records_the_recents(self):
        self.start(["Alice", "Bob"])
        self.go(pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)
        again = self.manager()
        self.assertEqual(again.last_player_count, 1)
        self.assertEqual(len(again.recent_ids), 1)

    def test_escape_walks_back_through_the_screens(self):
        self.start(["Alice", "Bob"])
        self.go(pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN)
        self.assertEqual(self.scene.title, "P1 SELECT PROFILE")
        self.go(pygame.K_RETURN)
        self.assertEqual(self.scene.title, "P2 SELECT PROFILE")
        self.go(pygame.K_ESCAPE)
        self.assertEqual(self.scene.title, "P1 SELECT PROFILE")
        self.go(pygame.K_ESCAPE)
        self.assertIsInstance(self.scene, PlayerCountScene)
        self.go(pygame.K_ESCAPE)
        self.assertIsInstance(self.scene, TitleScene)

    def test_a_profile_can_be_created_from_the_select_screen(self):
        self.start([])
        self.go(pygame.K_RETURN, pygame.K_RETURN)
        sel = self.scene
        self.assertTrue(sel.on_new_profile)
        self.go(pygame.K_RETURN)                                 # + NEW PROFILE
        self.assertIsNotNone(sel.entry)
        self.frames(1, [*typed("  kev"), key(pygame.K_i, char="i"), key(pygame.K_n, char="n")])
        self.frames(1, [key(pygame.K_BACKSPACE)])
        self.assertEqual(sel.entry.text, "KEVI")
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertIsNone(sel.entry)
        self.assertEqual([i.display_name for i in self.m.list_profiles()], ["KEVI"])
        self.assertEqual(sel.selected_info.display_name, "KEVI")

    def test_blank_and_duplicate_names_are_rejected_in_the_entry_box(self):
        self.start(["Alice"])
        self.go(pygame.K_RETURN, pygame.K_RETURN)
        sel = self.scene
        sel.selected = sel.total - 1
        self.go(pygame.K_RETURN)
        self.frames(1, [key(pygame.K_RETURN)])                   # blank
        self.assertIsNotNone(sel.entry)
        self.assertEqual(sel.entry.error, "ENTER A NAME")
        self.frames(1, typed("alice"))
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertIsNotNone(sel.entry)
        self.assertEqual(sel.entry.error, "NAME ALREADY USED")
        self.assertEqual(len(self.m), 1)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertIsNone(sel.entry)

    def test_the_name_box_stops_at_the_length_limit(self):
        self.start([])
        self.go(pygame.K_RETURN, pygame.K_RETURN, pygame.K_RETURN)
        sel = self.scene
        self.frames(1, typed("a" * 30))
        self.assertEqual(len(sel.entry.text), PROFILE_NAME_MAX)

    def test_new_profile_is_offered_to_player_two_as_well(self):
        self.start(["Alice"])
        self.go(pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN, pygame.K_RETURN)   # P1 = Alice
        p2 = self.scene
        self.assertEqual(p2.title, "P2 SELECT PROFILE")
        p2.selected = p2.total - 1
        self.go(pygame.K_RETURN)
        self.frames(1, typed("zed"))
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(p2.selected_info.display_name, "ZED")
        self.go(pygame.K_RETURN)
        self.assertEqual([p.profile.display_name for p in self.game.session], ["Alice", "ZED"])

    def test_delete_asks_first_and_defaults_to_no(self):
        self.start(["Alice", "Bob"])
        self.go(pygame.K_RETURN, pygame.K_RETURN)
        sel = self.scene
        sel.selected = 0
        self.frames(1, [key(pygame.K_DELETE)])
        self.assertIsNotNone(sel.dialog)
        self.assertEqual(sel.dialog.title, "DELETE PROFILE?")
        self.frames(30, [key(pygame.K_RETURN)])                  # an immediate ENTER: ignored (input delay)
        self.assertIsNotNone(sel.dialog)
        self.frames(30)
        self.frames(1, [key(pygame.K_RETURN)])                   # NO is the default choice
        self.assertIsNone(sel.dialog)
        self.assertEqual(len(self.m), 2)
        self.frames(1, [key(pygame.K_DELETE)])                   # again, but ESC
        self.frames(30)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertEqual(len(self.m), 2)

    def test_delete_only_happens_on_an_explicit_yes(self):
        self.start(["Alice", "Bob"])
        self.go(pygame.K_RETURN, pygame.K_RETURN)
        sel = self.scene
        sel.selected = 0
        self.frames(1, [key(pygame.K_DELETE)])
        self.frames(30)
        self.frames(1, [key(pygame.K_DOWN)])
        self.frames(1, [key(pygame.K_RETURN)])                   # YES, DELETE IT
        self.assertEqual([i.display_name for i in self.m.list_profiles()], ["Bob"])
        self.assertFalse(os.path.exists(self.m.profile_path(self.ids["Alice"])))

    def test_a_profile_in_use_by_p1_cannot_be_deleted_from_the_p2_screen(self):
        self.start(["Alice", "Bob"])
        self.go(pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN)
        self.scene.selected = 0
        self.go(pygame.K_RETURN)
        p2 = self.scene
        p2.selected = 0
        self.frames(1, [key(pygame.K_DELETE)])
        self.assertIsNone(p2.dialog)
        self.assertEqual(len(self.m), 2)

    def test_the_old_single_player_entry_points_still_work(self):
        g = Game(save_path=os.path.join(self.dir, "single.json"), clock=CLOCK())
        self.assertIsInstance(g.scenes.current, BaseRoomScene)
        self.assertEqual(g.session.player_count, 1)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "single.json")))


if __name__ == "__main__":
    unittest.main()
