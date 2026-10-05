"""Tests for tokens, tickets, save/load and the machine play/reward flow.

Run headless from this folder:   python -m unittest test_currency -v
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import scenes  # noqa: E402
from game import Game  # noqa: E402
from machine import ArcadeMachine  # noqa: E402
from minigame import MinigameScene  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from rewards import PlaySession, RewardResult  # noqa: E402
from scenes import ArcadeRoomScene, MinigamePlaceholderScene  # noqa: E402
from settings import (DEBUG_TOKENS, MACHINES, PLACEHOLDER_REWARD_TICKETS,  # noqa: E402
                      STARTING_TOKENS, STARTING_TICKETS)

DT = 1 / 60


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save_data.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)


# ---------------------------------------------------------------- profile
class PlayerProfileTests(unittest.TestCase):
    def test_new_profile_defaults(self):
        p = PlayerProfile()
        self.assertEqual((p.tokens, p.tickets), (STARTING_TOKENS, STARTING_TICKETS))
        self.assertEqual((p.tokens, p.tickets), (10, 0))
        self.assertEqual(p.high_scores, {})

    def test_spend_and_afford(self):
        p = PlayerProfile(tokens=2)
        self.assertTrue(p.can_afford_tokens(2))
        self.assertTrue(p.spend_tokens(2))
        self.assertEqual(p.tokens, 0)
        self.assertFalse(p.can_afford_tokens(1))
        self.assertFalse(p.spend_tokens(1))
        self.assertEqual(p.tokens, 0)

    def test_tickets_track_lifetime(self):
        p = PlayerProfile()
        p.add_tickets(5)
        p.add_tickets(7)
        self.assertEqual((p.tickets, p.lifetime_tickets_earned), (12, 12))

    def test_rejects_negative_or_non_int_amounts(self):
        p = PlayerProfile()
        for bad in (-1, 1.5, "3", True, None):
            with self.assertRaises(ValueError):
                p.add_tokens(bad)
            with self.assertRaises(ValueError):
                p.spend_tokens(bad)
            with self.assertRaises(ValueError):
                p.add_tickets(bad)
        self.assertEqual((p.tokens, p.tickets), (10, 0))

    def test_fields_are_read_only(self):
        p = PlayerProfile()
        with self.assertRaises(AttributeError):
            p.tokens -= 1
        p.high_scores["x"] = 99          # a copy: does not leak in
        self.assertEqual(p.high_scores, {})

    def test_record_score_keeps_best(self):
        p = PlayerProfile()
        self.assertTrue(p.record_score("retro_racer", 0))
        self.assertTrue(p.record_score("retro_racer", 5200))
        self.assertFalse(p.record_score("retro_racer", 100))
        self.assertEqual(p.high_score("retro_racer"), 5200)

    def test_change_events(self):
        p = PlayerProfile()
        seen = []
        p.subscribe(seen.append)
        p.spend_tokens(1)
        p.add_tickets(5)
        p.spend_tokens(99)               # refused: no event
        self.assertEqual([(c.field, c.delta, c.value) for c in seen if c.field != "tasks"],
                         [("tokens", -1, 9), ("tickets", 5, 5)])


# ---------------------------------------------------------------- save / load
class ProfileStoreTests(TempDirTest):
    def test_missing_file_creates_default_save(self):
        p = ProfileStore(self.path).load()
        self.assertEqual((p.tokens, p.tickets), (10, 0))
        self.assertTrue(os.path.exists(self.path))
        self.assertEqual(self.saved()["tokens"], 10)

    def test_round_trip_with_high_scores(self):
        store = ProfileStore(self.path)
        p = PlayerProfile(tokens=3, tickets=125, high_scores={"retro_racer": 5200},
                          total_games_played=4, lifetime_tickets_earned=175)
        p.record_score("space_blaster", 3200)
        store.save(p)
        q = store.load()
        self.assertEqual(q.to_dict(), p.to_dict())
        self.assertEqual(q.high_scores, {"retro_racer": 5200, "space_blaster": 3200})

    def test_corrupted_json_does_not_crash(self):
        for junk in ("{not json", "", "[1, 2, 3]", "null", "\xff\xfe"):
            with open(self.path, "w", encoding="latin-1") as f:
                f.write(junk)
            p = ProfileStore(self.path).load()
            self.assertEqual((p.tokens, p.tickets), (10, 0), junk)
            self.assertTrue(os.path.exists(self.path + ".corrupt"))   # kept for inspection
            self.assertEqual(self.saved()["tokens"], 10)               # fresh save written

    def test_invalid_fields_fall_back_to_defaults(self):
        with open(self.path, "w") as f:
            json.dump({"tokens": "lots", "tickets": -4, "total_games_played": 2.5,
                       "high_scores": {"retro_racer": 900, "bad": "x", "neg": -1}}, f)
        p = ProfileStore(self.path).load()
        self.assertEqual((p.tokens, p.tickets, p.total_games_played), (10, 0, 0))
        self.assertEqual(p.high_scores, {"retro_racer": 900})

    def test_partial_file_keeps_valid_fields(self):
        with open(self.path, "w") as f:
            json.dump({"tickets": 40}, f)
        p = ProfileStore(self.path).load()
        self.assertEqual((p.tokens, p.tickets, p.lifetime_tickets_earned), (10, 40, 40))

    def test_unwritable_path_does_not_crash(self):
        store = ProfileStore(os.path.join(self.dir, "missing_dir", "save.json"))
        p = store.load()                 # cannot create the file: still a profile
        self.assertEqual(p.tokens, 10)
        self.assertFalse(store.save(p))

    def test_autosave(self):
        store = ProfileStore(self.path)
        p = store.load()
        store.autosave(p)
        p.spend_tokens(1)
        self.assertEqual(self.saved()["tokens"], 9)
        p.add_tickets(5)
        self.assertEqual(self.saved()["tickets"], 5)


# ---------------------------------------------------------------- machine / session
class MachineAndSessionTests(unittest.TestCase):
    def machine(self, cost=None):
        data = dict(MACHINES[0])
        if cost is None:
            data.pop("play_cost", None)
        else:
            data["play_cost"] = cost
        return ArcadeMachine(data)

    def test_default_and_custom_costs(self):
        self.assertEqual(self.machine().play_cost, 1)
        self.assertEqual(self.machine().cost_label, "1 TOKEN")
        premium = self.machine(2)
        self.assertEqual(premium.cost_label, "2 TOKENS")
        p = PlayerProfile(tokens=3)
        self.assertIsNotNone(premium.start_play(p))
        self.assertEqual(p.tokens, 1)
        self.assertFalse(premium.can_afford(p))
        self.assertIsNone(premium.start_play(p))
        self.assertEqual(p.tokens, 1)
        self.assertEqual(p.total_games_played, 0)   # counted when the game settles

    def test_free_machine(self):
        p = PlayerProfile(tokens=0)
        self.assertIsNotNone(self.machine(0).start_play(p))
        self.assertEqual(p.tokens, 0)

    def test_session_settles_once(self):
        p = PlayerProfile()
        s = PlaySession(p, "retro_racer", 1)
        r = RewardResult("retro_racer", tickets_earned=5, score=4200)
        self.assertIs(s.settle(r), r)
        self.assertIsNone(s.settle(r))
        self.assertIsNone(s.settle(r))
        self.assertEqual(p.tickets, 5)
        self.assertEqual(p.high_score("retro_racer"), 4200)
        self.assertEqual(p.total_games_played, 1)
        self.assertFalse(s.refund())    # already settled: no refund either
        self.assertEqual(p.tokens, 10)

    def test_refund_once(self):
        p = PlayerProfile(tokens=3)
        s = ArcadeMachine(dict(MACHINES[0], play_cost=2)).start_play(p)
        self.assertEqual(p.tokens, 1)
        self.assertTrue(s.refund())
        self.assertFalse(s.refund())
        self.assertIsNone(s.settle(RewardResult("retro_racer", 5)))
        self.assertEqual((p.tokens, p.tickets, p.total_games_played), (3, 0, 0))

    def test_session_rejects_other_games_reward(self):
        s = PlaySession(PlayerProfile(), "retro_racer", 1)
        with self.assertRaises(ValueError):
            s.settle(RewardResult("space_blaster", 5))


# ---------------------------------------------------------------- full game flow
class ArcadeFlowTests(TempDirTest):
    """Drives the real Game/SceneManager/ArcadeRoomScene with key events."""
    MACHINE = "space_blaster"   # a placeholder minigame (no slow racer load)

    def make_game(self, **kw):
        g = Game(save_path=self.path, **kw)
        room = g.scenes.current
        if room.popup:                   # put off the daily bonus (ESC): not under test here
            self.run_frames(g, 3, [key(pygame.K_ESCAPE)])
            self.assertIsNone(room.popup)
        machine = next(m for m in room.machines if m.id == self.MACHINE)
        room.player.x, room.player.y = machine.rect.centerx, machine.rect.bottom + 12
        self.run_frames(g, 5)
        self.assertIs(room.nearby, machine)
        return g, room, machine

    def run_frames(self, g, n, events=()):
        g.step(list(events), DT)
        for _ in range(n - 1):
            g.step([], DT)

    def open_dialogue(self, g, room):
        self.run_frames(g, 30, [key(pygame.K_e)])
        self.assertIsNotNone(room.dialogue)

    def play_once(self, g, room, extra_presses=0):
        """E -> dialogue -> ENTER on PLAY (plus spam) -> placeholder -> ESC (plus spam)."""
        self.open_dialogue(g, room)
        spam = [key(pygame.K_RETURN), key(pygame.K_e)] * extra_presses
        self.run_frames(g, 1, [key(pygame.K_RETURN)] + spam)
        for _ in range(40):              # keep mashing during the wipe
            self.run_frames(g, 1, spam)
        self.assertIsInstance(g.scenes.current, MinigamePlaceholderScene)
        esc = [key(pygame.K_ESCAPE)] * (1 + extra_presses)
        self.run_frames(g, 1, esc)
        for _ in range(40):
            self.run_frames(g, 1, esc if extra_presses else ())
        self.assertIs(g.scenes.current, room)
        self.run_frames(g, 5)

    def test_cancel_and_close_cost_nothing(self):
        g, room, _ = self.make_game()
        for _ in range(3):
            self.open_dialogue(g, room)
            self.run_frames(g, 5, [key(pygame.K_ESCAPE)])            # close
            self.assertIsNone(room.dialogue)
            self.open_dialogue(g, room)
            self.run_frames(g, 5, [key(pygame.K_DOWN), key(pygame.K_RETURN)])  # CANCEL
            self.assertIs(g.scenes.current, room)
        self.assertEqual((g.profile.tokens, g.profile.total_games_played), (10, 0))
        self.assertEqual(self.saved()["tokens"], 10)

    def test_multiple_play_cycles_and_save(self):
        g, room, _ = self.make_game()
        self.assertEqual((g.profile.tokens, g.profile.tickets), (10, 0))
        self.play_once(g, room)
        self.assertEqual((g.profile.tokens, g.profile.tickets), (9, PLACEHOLDER_REWARD_TICKETS))
        self.play_once(g, room)
        self.assertEqual((g.profile.tokens, g.profile.tickets), (8, 2 * PLACEHOLDER_REWARD_TICKETS))
        data = self.saved()
        self.assertEqual((data["tokens"], data["tickets"], data["total_games_played"],
                          data["lifetime_tickets_earned"]), (8, 10, 2, 10))

        # "restart": a new Game loads the same values
        g2, _, _ = self.make_game()
        self.assertEqual(g2.profile.to_dict(), g.profile.to_dict())

    def test_key_mashing_charges_and_rewards_once(self):
        g, room, _ = self.make_game()
        self.play_once(g, room, extra_presses=6)
        self.assertEqual((g.profile.tokens, g.profile.tickets, g.profile.total_games_played),
                         (9, 5, 1))

    def test_same_frame_double_confirm(self):
        g, room, machine = self.make_game()
        self.open_dialogue(g, room)
        # both presses land in one frame, before the wipe starts
        self.run_frames(g, 1, [key(pygame.K_RETURN), key(pygame.K_RETURN), key(pygame.K_e)])
        room._start_game(machine)        # a stray direct call mid-transition is ignored too
        self.run_frames(g, 40)
        self.assertEqual(g.profile.tokens, 9)

    def test_resume_without_new_game_pays_nothing(self):
        g, room, _ = self.make_game()
        self.play_once(g, room)
        room.on_resume()                 # e.g. a second pop notification
        room.on_resume()
        self.assertEqual(g.profile.tickets, 5)

    def test_insufficient_tokens_blocks_entry(self):
        with open(self.path, "w") as f:
            json.dump({"tokens": 0, "tickets": 7}, f)
        g, room, _ = self.make_game()
        self.open_dialogue(g, room)
        self.assertIn("LOCKED", room.dialogue.options[0])
        self.run_frames(g, 40, [key(pygame.K_RETURN)])
        self.assertIs(g.scenes.current, room)
        self.assertTrue(room.notice.visible)
        self.assertEqual((g.profile.tokens, g.profile.tickets, g.profile.total_games_played),
                         (0, 7, 0))

    def test_hud_updates_immediately(self):
        g, room, _ = self.make_game()
        self.open_dialogue(g, room)
        self.run_frames(g, 1, [key(pygame.K_RETURN)])   # charged before the wipe ends
        self.assertEqual(room.hud._key[0], 9)
        self.assertEqual(len(room.hud.floaters), 1)

    def test_failed_game_is_refunded(self):
        class BrokenGame(MinigameScene):
            failed = True

            def handle_event(self, event):
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.game.scenes.pop()

        with mock.patch.dict(scenes.MINIGAME_SCENES, {self.MACHINE: BrokenGame}):
            g, room, _ = self.make_game()
            self.open_dialogue(g, room)
            self.run_frames(g, 40, [key(pygame.K_RETURN)])
            self.assertIsInstance(g.scenes.current, BrokenGame)
            self.assertEqual(g.profile.tokens, 9)
            self.run_frames(g, 40, [key(pygame.K_ESCAPE)])
        self.assertIs(g.scenes.current, room)
        self.assertEqual((g.profile.tokens, g.profile.tickets, g.profile.total_games_played),
                         (10, 0, 0))
        self.assertEqual(self.saved()["tokens"], 10)

    def test_quit_during_game_still_pays(self):
        g, room, _ = self.make_game()
        self.open_dialogue(g, room)
        self.run_frames(g, 40, [key(pygame.K_RETURN)])
        self.assertIsInstance(g.scenes.current, MinigamePlaceholderScene)
        g.step([pygame.event.Event(pygame.QUIT)], DT)
        g.quit()                         # a second close is harmless
        self.assertFalse(g.running)
        data = self.saved()
        self.assertEqual((data["tokens"], data["tickets"], data["total_games_played"]), (9, 5, 1))

    def test_quit_before_game_opens_refunds(self):
        g, room, _ = self.make_game()
        self.open_dialogue(g, room)
        self.run_frames(g, 2, [key(pygame.K_RETURN)])   # charged, wipe still closing
        self.assertEqual(g.profile.tokens, 9)
        g.step([pygame.event.Event(pygame.QUIT)], DT)
        data = self.saved()
        self.assertEqual((data["tokens"], data["tickets"], data["total_games_played"]), (10, 0, 0))

    def test_quit_in_room_changes_nothing(self):
        g, room, _ = self.make_game()
        self.play_once(g, room)
        g.step([pygame.event.Event(pygame.QUIT)], DT)
        self.assertEqual((self.saved()["tokens"], self.saved()["tickets"]), (9, 5))

    def test_debug_refill_only_in_debug(self):
        g, room, _ = self.make_game()
        self.run_frames(g, 2, [key(pygame.K_F5)])
        self.assertEqual(g.profile.tokens, 10)
        g, room, _ = self.make_game(debug=True)
        self.run_frames(g, 2, [key(pygame.K_F5)])
        self.assertEqual(g.profile.tokens, 10 + DEBUG_TOKENS)
        self.assertEqual(self.saved()["tokens"], 10 + DEBUG_TOKENS)


if __name__ == "__main__":
    unittest.main()
