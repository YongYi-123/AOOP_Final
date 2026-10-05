"""Tests for reward delivery (RewardBundle / RewardService.grant) and for paying
at a machine with a Free Play Coupon.

Run headless from this folder:   python -m unittest test_rewards -v
"""
import contextlib
import io
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

import scenes  # noqa: E402
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from item_registry import FREE_PLAY_COUPON  # noqa: E402
from machine import ArcadeMachine  # noqa: E402
from minigame import MinigameScene  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from rewards import (PlaySession, RewardBundle, RewardGrantResult,  # noqa: E402
                     RewardResult, RewardService)
from scenes import ArcadeRoomScene, MinigamePlaceholderScene  # noqa: E402
from settings import MACHINES, PLACEHOLDER_REWARD_TICKETS  # noqa: E402

DT = 1 / 60
CLOCK = lambda: GameClock(lambda: date(2026, 3, 10))  # noqa: E731


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


# ---------------------------------------------------------------- bundles
class RewardBundleTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(tokens=10, clock=CLOCK())

    def grant(self, **kw):
        return quiet(RewardService.grant, self.p, RewardBundle(**kw))

    def test_bundle_is_plain_data(self):
        b = RewardBundle()
        self.assertEqual((b.tokens, b.tickets, dict(b.items), b.is_empty), (0, 0, {}, True))
        src = {"cat_sticker": 1}
        b = RewardBundle(items=src)
        src["neon_cap"] = 1                              # later edits to the source do not leak in
        self.assertEqual(dict(b.items), {"cat_sticker": 1})
        with self.assertRaises(TypeError):
            b.items["neon_cap"] = 1
        with self.assertRaises(Exception):
            b.tokens = 5

    def test_token_only(self):
        r = self.grant(tokens=7, reason="daily login")
        self.assertIsInstance(r, RewardGrantResult)
        self.assertEqual((r.tokens_granted, r.tickets_granted, r.item_results), (7, 0, ()))
        self.assertEqual((r.success, r.partial, r.status), (True, False, "success"))
        self.assertEqual((self.p.tokens, self.p.tickets), (17, 0))
        self.assertEqual(self.p.history_lines()[-1], "+7 TOKEN  DAILY LOGIN")

    def test_ticket_only(self):
        r = self.grant(tickets=25)
        self.assertEqual((r.tokens_granted, r.tickets_granted, r.success), (0, 25, True))
        self.assertEqual((self.p.tokens, self.p.tickets, self.p.lifetime_tickets_earned), (10, 25, 25))

    def test_item_only(self):
        r = self.grant(items={"free_play_coupon": 3})
        self.assertEqual((r.item_results[0].granted_quantity, r.item_results[0].reason), (3, "ok"))
        self.assertTrue(r.success)
        self.assertEqual(self.p.inventory.get_quantity("free_play_coupon"), 3)
        self.assertEqual((self.p.tokens, self.p.tickets), (10, 0))

    def test_mixed(self):
        r = self.grant(tokens=5, tickets=40, items={"free_play_coupon": 2, "cat_sticker": 1})
        self.assertEqual((r.tokens_granted, r.tickets_granted, len(r.item_results)), (5, 40, 2))
        self.assertEqual(r.status, "success")
        self.assertEqual((self.p.tokens, self.p.tickets), (15, 40))
        self.assertEqual(self.p.inventory.to_dict(), {"free_play_coupon": 2, "cat_sticker": 1})
        self.assertEqual(r.requested.tokens, 5)

    def test_partial_item_stack(self):
        self.p.inventory.add_item("free_play_coupon", 95)
        r = self.grant(tokens=2, items={"free_play_coupon": 10})
        item = r.item_results[0]
        self.assertEqual((item.granted_quantity, item.requested_quantity, item.reason), (4, 10, "partial"))
        self.assertEqual((r.success, r.partial, r.status), (False, True, "partial"))
        self.assertEqual(self.p.inventory.get_quantity("free_play_coupon"), 99)
        self.assertEqual(self.p.tokens, 12)              # the rest was still granted

    def test_unknown_item_in_mixed_reward(self):
        r = self.grant(tokens=3, tickets=9, items={"mystery_hat": 1, "cat_sticker": 1})
        reasons = {i.item_id: i.reason for i in r.item_results}
        self.assertEqual(reasons, {"mystery_hat": "unknown_item", "cat_sticker": "ok"})
        self.assertEqual(r.status, "partial")
        self.assertEqual((self.p.tokens, self.p.tickets), (13, 9))
        self.assertTrue(self.p.inventory.has_item("cat_sticker"))
        self.assertEqual(self.p.inventory.unknown_items, {})      # never added

    def test_only_unknown_item_is_a_failure(self):
        r = self.grant(items={"mystery_hat": 1})
        self.assertEqual((r.status, r.granted_anything, r.success), ("failed", False, False))

    def test_invalid_amounts_are_skipped_not_raised(self):
        for bad in (-5, 1.5, "7", None, True):
            r = self.grant(tokens=bad, tickets=4)
            self.assertEqual((r.tokens_granted, r.tickets_granted, r.status), (0, 4, "partial"), bad)
            self.assertEqual(len(r.errors), 1)
        self.assertEqual(self.p.tokens, 10)
        r = self.grant(tokens=-1, tickets=-1)
        self.assertEqual(r.status, "failed")

    def test_invalid_item_quantity_is_reported(self):
        r = self.grant(items={"cat_sticker": 0})
        self.assertEqual(r.item_results[0].reason, "invalid_quantity")
        self.assertEqual(r.status, "failed")

    def test_empty_bundle_is_a_trivial_success(self):
        r = self.grant()
        self.assertEqual((r.success, r.status), (True, "success"))
        self.assertEqual((self.p.tokens, self.p.tickets), (10, 0))

    def test_unknown_item_is_logged(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            RewardService.grant(self.p, RewardBundle(items={"mystery_hat": 1}))
        self.assertIn("mystery_hat", out.getvalue())

    def test_duplicate_non_stackable_is_not_a_crash(self):
        self.grant(items={"neon_cap": 1})
        r = self.grant(items={"neon_cap": 1})
        self.assertEqual((r.item_results[0].reason, r.status), ("already_owned", "failed"))

    def test_task_progress_still_counts_granted_tickets(self):
        from daily_tasks import DailyTaskManager
        mgr = DailyTaskManager(pool=[{"id": "t", "description": "T", "event": "tickets_earned",
                                      "target": 20, "reward": 5}], count=1)
        p = PlayerProfile(daily_tasks=mgr, clock=CLOCK())
        quiet(RewardService.grant, p, RewardBundle(tickets=20))
        self.assertTrue(p.daily_tasks[0].completed)


class RewardSaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "s.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_mixed_bundle_saves_once_with_everything(self):
        store = ProfileStore(self.path, CLOCK())
        p = store.load()
        store.autosave(p)
        with mock.patch.object(ProfileStore, "save", autospec=True, side_effect=ProfileStore.save) as save:
            quiet(RewardService.grant, p, RewardBundle(tokens=5, tickets=10, items={
                "free_play_coupon": 2, "cat_sticker": 1, "nope": 1}))
        self.assertEqual(save.call_count, 1)
        with open(self.path) as f:
            data = json.load(f)
        self.assertEqual((data["tokens"], data["tickets"]), (15, 10))
        self.assertEqual(data["inventory"], {"free_play_coupon": 2, "cat_sticker": 1})

    def test_single_changes_still_save_immediately(self):
        store = ProfileStore(self.path, CLOCK())
        p = store.load()
        store.autosave(p)
        p.add_tokens(3, "x")
        with open(self.path) as f:
            self.assertEqual(json.load(f)["tokens"], 13)

    def test_nested_batches_save_once_and_listeners_still_hear_everything(self):
        p = PlayerProfile(clock=CLOCK())
        saves, heard = [], []
        p.subscribe_save(lambda: saves.append(1))
        p.subscribe(heard.append)
        with p.batch():
            with p.batch():
                p.add_tokens(1, "x")
            p.add_tickets(1)
            self.assertEqual(saves, [])
        self.assertEqual(len(saves), 1)
        self.assertEqual([c.field for c in heard if c.field in ("tokens", "tickets")], ["tokens", "tickets"])
        with p.batch():
            pass                                           # nothing changed: nothing saved
        self.assertEqual(len(saves), 1)

    def test_batch_saves_even_if_the_body_raises(self):
        p = PlayerProfile(clock=CLOCK())
        saves = []
        p.subscribe_save(lambda: saves.append(1))
        with self.assertRaises(RuntimeError):
            with p.batch():
                p.add_tokens(1, "x")
                raise RuntimeError
        self.assertEqual(len(saves), 1)

    def test_play_session_settle_saves_once(self):
        p = PlayerProfile(clock=CLOCK())
        saves = []
        p.subscribe_save(lambda: saves.append(1))
        PlaySession(p, "retro_racer", 1).settle(RewardResult("retro_racer", 5, 100))
        self.assertEqual(len(saves), 1)


# ---------------------------------------------------------------- machine level
class CouponMachineTests(unittest.TestCase):
    def machine(self):
        return ArcadeMachine(dict(MACHINES[1], play_cost=1))

    def profile(self, tokens=5, coupons=1):
        p = PlayerProfile(tokens=tokens, clock=CLOCK())
        if coupons:
            p.inventory.add_item(FREE_PLAY_COUPON, coupons)
        return p

    def test_coupon_play_costs_no_tokens(self):
        p, m = self.profile(), self.machine()
        s = m.start_play(p, use_coupon=True)
        self.assertTrue(s.coupon)
        self.assertEqual((p.tokens, p.inventory.get_quantity(FREE_PLAY_COUPON), p.lifetime_tokens_spent),
                         (5, 0, 0))
        self.assertEqual(p.history, [])

    def test_only_one_coupon_per_play(self):
        p, m = self.profile(coupons=3), self.machine()
        m.start_play(p, use_coupon=True)
        self.assertEqual(p.inventory.get_quantity(FREE_PLAY_COUPON), 2)

    def test_no_coupon_means_no_play_and_no_token_charge(self):
        p, m = self.profile(coupons=0), self.machine()
        self.assertIsNone(m.start_play(p, use_coupon=True))
        self.assertEqual(p.tokens, 5)

    def test_token_path_never_touches_the_coupon(self):
        p, m = self.profile(), self.machine()
        s = m.start_play(p)
        self.assertFalse(s.coupon)
        self.assertEqual((p.tokens, p.inventory.get_quantity(FREE_PLAY_COUPON)), (4, 1))

    def test_can_play_rules(self):
        m = self.machine()
        self.assertTrue(m.can_play(self.profile(tokens=0, coupons=1)))
        self.assertTrue(m.can_play(self.profile(tokens=1, coupons=0)))
        self.assertFalse(m.can_play(self.profile(tokens=0, coupons=0)))
        self.assertFalse(m.can_afford(self.profile(tokens=0, coupons=1)))

    def test_coupon_session_refund_returns_the_coupon_once(self):
        p, m = self.profile(tokens=0), self.machine()
        s = m.start_play(p, use_coupon=True)
        self.assertTrue(s.refund())
        self.assertFalse(s.refund())
        self.assertIsNone(s.settle(RewardResult(m.id, 5)))
        self.assertEqual((p.tokens, p.inventory.get_quantity(FREE_PLAY_COUPON)), (0, 1))

    def test_coupon_session_settles_once(self):
        p, m = self.profile(), self.machine()
        s = m.start_play(p, use_coupon=True)
        s.settle(RewardResult(m.id, 5))
        s.settle(RewardResult(m.id, 5))
        self.assertFalse(s.refund())
        self.assertEqual((p.tickets, p.total_games_played, p.inventory.get_quantity(FREE_PLAY_COUPON)),
                         (5, 1, 0))


# ---------------------------------------------------------------- in the arcade
class CouponFlowTests(unittest.TestCase):
    MACHINE = "space_blaster"          # a placeholder minigame (no slow racer load)

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save_data.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def saved(self):
        with open(self.path) as f:
            return json.load(f)

    def make_game(self, tokens=10, coupons=1):
        data = {"tokens": tokens, "inventory": {FREE_PLAY_COUPON: coupons} if coupons else {}}
        with open(self.path, "w") as f:
            json.dump(data, f)
        g = Game(save_path=self.path, clock=CLOCK())
        room = g.scenes.current
        self.frames(g, 3, [key(pygame.K_ESCAPE)])            # put off the daily bonus
        machine = next(m for m in room.machines if m.id == self.MACHINE)
        room.player.x, room.player.y = machine.rect.centerx, machine.rect.bottom + 12
        self.frames(g, 5)
        return g, room, machine

    def frames(self, g, n, events=()):
        g.step(list(events), DT)
        for _ in range(n - 1):
            g.step([], DT)

    def to_coupon_question(self, g, room):
        self.frames(g, 30, [key(pygame.K_e)])
        self.assertIsNotNone(room.dialogue)
        self.frames(g, 1, [key(pygame.K_RETURN)])             # PLAY
        self.assertEqual(room.dialogue.title, "COUPON")
        self.frames(g, 30)                                     # past the input delay

    def coupons(self, g):
        return g.profile.inventory.get_quantity(FREE_PLAY_COUPON)

    def leave_game(self, g, room):
        self.frames(g, 40)
        self.assertIsInstance(g.scenes.current, MinigamePlaceholderScene)
        self.frames(g, 40, [key(pygame.K_ESCAPE)])
        self.assertIs(g.scenes.current, room)
        self.frames(g, 5)

    def test_question_text_and_options(self):
        g, room, _ = self.make_game()
        self.to_coupon_question(g, room)
        self.assertEqual(room.dialogue.body, "USE FREE PLAY COUPON?")
        self.assertEqual(room.dialogue.options, ["YES", "NO"])
        self.assertEqual(room.dialogue.selected, 0)           # YES is the default cursor

    def test_yes_uses_one_coupon_and_no_tokens(self):
        g, room, _ = self.make_game(tokens=10, coupons=2)
        self.to_coupon_question(g, room)
        self.frames(g, 1, [key(pygame.K_RETURN)])             # YES
        self.leave_game(g, room)
        self.assertEqual((g.profile.tokens, self.coupons(g)), (10, 1))
        self.assertEqual(g.profile.tickets, PLACEHOLDER_REWARD_TICKETS)
        self.assertEqual(g.profile.total_games_played, 1)
        self.assertEqual(g.profile.lifetime_tokens_spent, 0)
        data = self.saved()
        self.assertEqual((data["tokens"], data["inventory"]), (10, {FREE_PLAY_COUPON: 1}))

    def test_last_coupon_is_removed_from_the_inventory(self):
        g, room, _ = self.make_game(coupons=1)
        self.to_coupon_question(g, room)
        self.frames(g, 1, [key(pygame.K_RETURN)])
        self.leave_game(g, room)
        self.assertEqual(self.saved()["inventory"], {})

    def test_no_pays_tokens_and_keeps_the_coupon(self):
        g, room, _ = self.make_game(tokens=10, coupons=1)
        self.to_coupon_question(g, room)
        self.frames(g, 1, [key(pygame.K_DOWN), key(pygame.K_RETURN)])   # NO
        self.leave_game(g, room)
        self.assertEqual((g.profile.tokens, self.coupons(g)), (9, 1))

    def test_esc_cancels_everything(self):
        g, room, _ = self.make_game()
        self.to_coupon_question(g, room)
        self.frames(g, 40, [key(pygame.K_ESCAPE)])
        self.assertIsNone(room.dialogue)
        self.assertIs(g.scenes.current, room)
        self.assertEqual((g.profile.tokens, self.coupons(g), g.profile.total_games_played), (10, 1, 0))

    def test_cancelling_the_machine_menu_consumes_nothing(self):
        g, room, _ = self.make_game()
        self.frames(g, 30, [key(pygame.K_e)])
        self.frames(g, 5, [key(pygame.K_ESCAPE)])
        self.frames(g, 30, [key(pygame.K_e)])
        self.frames(g, 5, [key(pygame.K_DOWN), key(pygame.K_RETURN)])    # CANCEL
        self.assertEqual((g.profile.tokens, self.coupons(g)), (10, 1))

    def test_no_tokens_but_a_coupon_can_still_play(self):
        g, room, _ = self.make_game(tokens=0, coupons=1)
        self.frames(g, 30, [key(pygame.K_e)])
        self.assertNotIn("LOCKED", room.dialogue.options[0])
        self.frames(g, 1, [key(pygame.K_RETURN)])
        self.frames(g, 30)
        self.frames(g, 1, [key(pygame.K_RETURN)])             # YES
        self.leave_game(g, room)
        self.assertEqual((g.profile.tokens, self.coupons(g), g.profile.total_games_played), (0, 0, 1))

    def test_no_tokens_and_choosing_no_shows_not_enough_tokens(self):
        g, room, _ = self.make_game(tokens=0, coupons=1)
        self.to_coupon_question(g, room)
        self.frames(g, 40, [key(pygame.K_DOWN), key(pygame.K_RETURN)])   # NO
        self.assertIs(g.scenes.current, room)
        self.assertTrue(room.notice.visible)
        self.assertEqual((g.profile.tokens, self.coupons(g), g.profile.total_games_played), (0, 1, 0))

    def test_no_tokens_and_no_coupon_is_locked(self):
        g, room, _ = self.make_game(tokens=0, coupons=0)
        self.frames(g, 30, [key(pygame.K_e)])
        self.assertIn("LOCKED", room.dialogue.options[0])
        self.frames(g, 40, [key(pygame.K_RETURN)])
        self.assertIs(g.scenes.current, room)
        self.assertTrue(room.notice.visible)
        self.assertEqual((g.profile.tokens, self.coupons(g)), (0, 0))

    def test_no_coupon_flows_unchanged(self):
        g, room, _ = self.make_game(tokens=10, coupons=0)
        self.frames(g, 30, [key(pygame.K_e)])
        self.frames(g, 1, [key(pygame.K_RETURN)])
        self.assertIsNone(room.dialogue)                      # straight to the game: no question
        self.leave_game(g, room)
        self.assertEqual(g.profile.tokens, 9)

    def test_mashing_play_cannot_answer_the_coupon_question(self):
        g, room, _ = self.make_game()
        self.frames(g, 30, [key(pygame.K_e)])
        self.frames(g, 1, [key(pygame.K_RETURN)] * 8 + [key(pygame.K_e)] * 4)   # one frame of mashing
        self.assertIsNotNone(room.dialogue)
        self.assertEqual(room.dialogue.title, "COUPON")
        self.frames(g, 5, [key(pygame.K_RETURN)] * 3)         # still inside the delay
        self.assertIsNotNone(room.dialogue)
        self.assertEqual((g.profile.tokens, self.coupons(g)), (10, 1))

    def test_mashing_yes_consumes_exactly_one(self):
        g, room, _ = self.make_game(coupons=3)
        self.to_coupon_question(g, room)
        self.frames(g, 1, [key(pygame.K_RETURN), key(pygame.K_RETURN), key(pygame.K_e)] * 4)
        for _ in range(40):
            self.frames(g, 1, [key(pygame.K_RETURN), key(pygame.K_e)])
        self.assertEqual((g.profile.tokens, self.coupons(g)), (10, 2))
        self.assertIsInstance(g.scenes.current, MinigamePlaceholderScene)
        self.frames(g, 40, [key(pygame.K_ESCAPE)] * 4)
        self.frames(g, 5)
        self.assertEqual((g.profile.tokens, self.coupons(g), g.profile.total_games_played), (10, 2, 1))

    def test_direct_start_during_a_transition_does_not_consume_twice(self):
        g, room, machine = self.make_game(coupons=3)
        self.to_coupon_question(g, room)
        self.frames(g, 1, [key(pygame.K_RETURN)])
        room._start_game(machine, use_coupon=True)            # stray calls mid-wipe
        room._start_game(machine, use_coupon=True)
        room._start_game(machine)
        self.frames(g, 40)
        self.assertEqual((g.profile.tokens, self.coupons(g)), (10, 2))

    def test_quit_before_the_game_opens_returns_the_coupon(self):
        g, room, _ = self.make_game(tokens=4, coupons=1)
        self.to_coupon_question(g, room)
        self.frames(g, 2, [key(pygame.K_RETURN)])             # consumed, wipe still closing
        self.assertEqual(self.coupons(g), 0)
        g.step([pygame.event.Event(pygame.QUIT)], DT)
        data = self.saved()
        self.assertEqual((data["tokens"], data["inventory"], data["total_games_played"]),
                         (4, {FREE_PLAY_COUPON: 1}, 0))

    def test_failed_game_returns_the_coupon(self):
        class BrokenGame(MinigameScene):
            failed = True

            def handle_event(self, event):
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.game.scenes.pop()

        with mock.patch.dict(scenes.MINIGAME_SCENES, {self.MACHINE: BrokenGame}):
            g, room, _ = self.make_game(tokens=4, coupons=1)
            self.to_coupon_question(g, room)
            self.frames(g, 40, [key(pygame.K_RETURN)])
            self.assertEqual(self.coupons(g), 0)
            self.frames(g, 40, [key(pygame.K_ESCAPE)])
        self.assertIs(g.scenes.current, room)
        self.assertEqual((g.profile.tokens, self.coupons(g), g.profile.total_games_played), (4, 1, 0))
        self.assertTrue(room.notice.visible)

    def test_quit_during_a_coupon_game_still_pays_tickets(self):
        g, room, _ = self.make_game(coupons=1)
        self.to_coupon_question(g, room)
        self.frames(g, 40, [key(pygame.K_RETURN)])
        g.step([pygame.event.Event(pygame.QUIT)], DT)
        data = self.saved()
        self.assertEqual((data["tickets"], data["inventory"], data["tokens"]), (5, {}, 10))

    def test_coupon_is_gone_if_used_elsewhere_before_yes(self):
        g, room, machine = self.make_game(coupons=1)
        g.profile.consume_item(FREE_PLAY_COUPON)
        room._start_game(machine, use_coupon=True)
        self.assertIs(g.scenes.current, room)
        self.assertEqual(g.profile.tokens, 10)                # never falls back to charging tokens
        self.assertTrue(room.notice.visible)

    def test_inventory_screen_shows_the_remaining_coupons(self):
        g, room, _ = self.make_game(coupons=2)
        self.to_coupon_question(g, room)
        self.frames(g, 1, [key(pygame.K_RETURN)])
        self.leave_game(g, room)
        self.frames(g, 2, [key(pygame.K_i)])
        self.assertEqual(room.inventory_ui.selected_entry[1], 1)


if __name__ == "__main__":
    unittest.main()
