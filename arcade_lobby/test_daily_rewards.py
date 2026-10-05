"""Tests that daily login rewards and daily task rewards are delivered as
RewardBundles through RewardService, and the coupon task.

(The login streak rules and task mechanics themselves are covered in
test_economy.py.)  Run headless:   python -m unittest test_daily_rewards -v
"""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from daily_rewards import DailyRewardManager  # noqa: E402
from daily_tasks import DailyTaskManager  # noqa: E402
from daily_ui import TaskPanel  # noqa: E402
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from item_registry import FREE_PLAY_COUPON  # noqa: E402
from machine import ArcadeMachine  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from rewards import (RewardBundle, RewardGrantResult, RewardResult,  # noqa: E402
                     RewardService)
from settings import DAILY_TASK_COUNT, DAILY_TASK_POOL, MACHINES  # noqa: E402

DT = 1 / 60
DAY1 = date(2026, 3, 10)


def clock_at(day=DAY1):
    return GameClock(lambda: day)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


def profile_with_rewards(rewards, day=DAY1, **kw):
    return PlayerProfile(daily=DailyRewardManager(rewards=rewards), clock=clock_at(day), **kw)


def profile_with_tasks(*specs, day=DAY1, **kw):
    mgr = DailyTaskManager(pool=specs, count=len(specs))
    return PlayerProfile(daily_tasks=mgr, clock=clock_at(day), **kw)


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save_data.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def saved(self):
        with open(self.path) as f:
            return json.load(f)


# ---------------------------------------------------------------- daily login
class DailyLoginBundleTests(TempDirTest):
    def test_default_config_is_still_plain_token_amounts(self):
        m = DailyRewardManager()
        self.assertEqual([b.tokens for b in m.rewards], [5, 6, 7, 8, 10, 12, 15])
        self.assertTrue(all(isinstance(b, RewardBundle) and not b.items for b in m.rewards))
        self.assertTrue(all(b.reason == "DAILY LOGIN" for b in m.rewards))

    def test_claim_goes_through_reward_service(self):
        p = PlayerProfile(clock=clock_at())
        with mock.patch("player_profile.RewardService.grant", wraps=RewardService.grant) as grant:
            claim = p.claim_daily_reward()
            self.assertIsNone(p.claim_daily_reward())
        self.assertEqual(grant.call_count, 1)                    # and never on the refused claim
        self.assertIsInstance(claim.grant, RewardGrantResult)
        self.assertEqual((claim.grant.status, claim.grant.tokens_granted, p.tokens), ("success", 5, 15))
        self.assertEqual(p.history_lines()[-1], "+5 TOKEN  DAILY LOGIN")

    def test_status_exposes_the_bundle(self):
        s = PlayerProfile(clock=clock_at()).daily_status()
        self.assertEqual((s.bundle.tokens, s.tokens, s.bundle.lines()), (5, 5, ["+5 TOKENS"]))

    def test_a_day_can_reward_tickets_and_items_too(self):
        p = profile_with_rewards([{"tokens": 5, "tickets": 10, "items": {FREE_PLAY_COUPON: 1}}])
        claim = p.claim_daily_reward()
        self.assertEqual((p.tokens, p.tickets, p.inventory.get_quantity(FREE_PLAY_COUPON)), (15, 10, 1))
        self.assertEqual(claim.bundle.lines(), ["+5 TOKENS", "+10 TICKETS", "+1 FREE PLAY COUPON"])
        self.assertTrue(claim.grant.success)

    def test_streak_picks_each_days_own_bundle(self):
        p = profile_with_rewards([2, {"tokens": 3, "items": {"cat_sticker": 1}}, 4])
        got = []
        for i in range(3):
            p.clock = clock_at(DAY1 + timedelta(days=i))
            claim = p.claim_daily_reward()
            got.append((claim.day, claim.tokens))
        self.assertEqual(got, [(1, 2), (2, 3), (3, 4)])
        self.assertTrue(p.inventory.has_item("cat_sticker"))

    def test_unknown_item_in_a_daily_reward_does_not_break_the_claim(self):
        p = profile_with_rewards([{"tokens": 5, "items": {"mystery_hat": 1}}])
        claim = quiet(p.claim_daily_reward)
        self.assertEqual((claim.grant.status, p.tokens), ("partial", 15))
        self.assertEqual(p.daily_streak, 1)
        self.assertIsNone(p.claim_daily_reward())                # still counts as claimed today
        self.assertEqual(p.inventory.unknown_items, {})

    def test_full_inventory_does_not_block_the_tokens(self):
        p = profile_with_rewards([{"tokens": 5, "items": {"neon_cap": 1}}])
        p.inventory.add_item("neon_cap")
        claim = p.claim_daily_reward()
        self.assertEqual((claim.grant.item_results[0].reason, p.tokens), ("already_owned", 15))

    def test_one_save_holds_state_and_payout(self):
        store = ProfileStore(self.path, clock_at())
        p = store.load()
        store.autosave(p)
        with mock.patch.object(ProfileStore, "save", autospec=True, side_effect=ProfileStore.save) as save:
            p.claim_daily_reward()
        self.assertEqual(save.call_count, 1)
        data = self.saved()
        self.assertEqual((data["tokens"], data["daily_streak"], data["last_daily_reward_claimed"]),
                         (15, 1, DAY1.isoformat()))

    def test_reward_item_is_saved_and_cannot_be_claimed_again_after_reload(self):
        store = ProfileStore(self.path, clock_at())
        p = store.load()
        store.autosave(p)
        p.inventory.add_item("cat_sticker")
        p._daily = DailyRewardManager(rewards=[{"tokens": 1, "items": {FREE_PLAY_COUPON: 2}}])
        p.claim_daily_reward()
        q = ProfileStore(self.path, clock_at()).load()
        self.assertEqual(q.inventory.get_quantity(FREE_PLAY_COUPON), 2)
        self.assertIsNone(q.claim_daily_reward())
        self.assertEqual(q.inventory.get_quantity(FREE_PLAY_COUPON), 2)

    def test_bad_bundle_config_is_rejected(self):
        for bad in ([], [-1], [{"tokens": -3}], [{"tokens": 1.5}]):
            with self.assertRaises(ValueError):
                DailyRewardManager(rewards=bad)

    def test_popup_shows_the_reward_lines(self):
        from daily_ui import DailyBonusPopup
        popup = DailyBonusPopup(7, ["+15 TOKENS", "+1 FREE PLAY COUPON"], lambda: None)
        popup.update(0.5)
        popup.draw(pygame.Surface((400, 300)))
        self.assertEqual(len(popup.extras), 1)


# ---------------------------------------------------------------- task rewards
class TaskBundleTests(TempDirTest):
    PET = {"id": "c", "description": "PET 1", "event": "cat_petted", "target": 1, "reward": 3}

    def test_task_reward_is_a_bundle(self):
        p = profile_with_tasks(self.PET)
        task = p.daily_tasks[0]
        self.assertEqual(task.reward_bundle, RewardBundle(3, 0, {}, "DAILY TASK"))
        self.assertEqual(task.reward_tokens, 3)

    def test_claim_goes_through_reward_service_once(self):
        p = profile_with_tasks(self.PET)
        p.record_cat_petted()
        with mock.patch("player_profile.RewardService.grant", wraps=RewardService.grant) as grant:
            result = p.claim_task_reward("c")
            self.assertIsNone(p.claim_task_reward("c"))
            self.assertEqual(p.claim_task("c"), 0)
        self.assertEqual(grant.call_count, 1)
        self.assertEqual((result.status, result.tokens_granted, p.tokens), ("success", 3, 13))
        self.assertEqual(p.history_lines()[-1], "+3 TOKEN  DAILY TASK")

    def test_unfinished_or_unknown_task_pays_nothing(self):
        p = profile_with_tasks(self.PET)
        self.assertIsNone(p.claim_task_reward("c"))
        self.assertIsNone(p.claim_task_reward("nope"))
        self.assertEqual((p.tokens, p.daily_tasks[0].claimed), (10, False))

    def test_task_reward_can_include_tickets_and_items(self):
        spec = dict(self.PET, reward_tickets=7, reward_items={FREE_PLAY_COUPON: 1})
        p = profile_with_tasks(spec)
        p.record_cat_petted()
        result = p.claim_task_reward("c")
        self.assertEqual((p.tokens, p.tickets, p.inventory.get_quantity(FREE_PLAY_COUPON)), (13, 7, 1))
        self.assertEqual(result.requested.lines(), ["+3 TOKENS", "+7 TICKETS", "+1 FREE PLAY COUPON"])

    def test_unknown_item_in_a_task_reward_is_safe_and_not_claimable_twice(self):
        spec = dict(self.PET, reward_items={"mystery_hat": 1})
        p = profile_with_tasks(spec)
        p.record_cat_petted()
        result = quiet(p.claim_task_reward, "c")
        self.assertEqual((result.status, p.tokens), ("partial", 13))
        self.assertTrue(p.daily_tasks[0].claimed)
        self.assertIsNone(p.claim_task_reward("c"))
        self.assertEqual(p.tokens, 13)

    def test_claim_is_one_save_and_survives_reload(self):
        spec = dict(self.PET, reward_items={FREE_PLAY_COUPON: 1})
        store = ProfileStore(self.path, clock_at())
        p = store.load()
        p._tasks = DailyTaskManager(pool=[spec], count=1)
        p._tasks.ensure_current(DAY1)
        store.autosave(p)
        p.record_cat_petted()
        with mock.patch.object(ProfileStore, "save", autospec=True, side_effect=ProfileStore.save) as save:
            p.claim_task_reward("c")
        self.assertEqual(save.call_count, 1)
        data = self.saved()
        self.assertEqual((data["tokens"], data["inventory"]), (13, {FREE_PLAY_COUPON: 1}))
        task = data["daily_tasks"]["tasks"][0]
        self.assertEqual((task["id"], task["claimed"]), ("c", True))

    def test_reloaded_claimed_task_cannot_pay_again(self):
        store = ProfileStore(self.path, clock_at())
        p = store.load()
        store.autosave(p)
        for _ in range(3):
            p.record_cat_petted()
            p.record_game_played("retro_racer")
        p.add_tickets(60)
        for m in ("a", "b", "c"):
            p.record_machine_visit(m)
        first = p.daily_tasks[0].id
        self.assertIsNotNone(p.claim_task_reward(first))
        tokens = p.tokens
        q = ProfileStore(self.path, clock_at()).load()
        self.assertIsNone(q.claim_task_reward(first))
        self.assertEqual(q.tokens, tokens)

    def test_panel_claims_through_the_service_and_shows_item_rewards(self):
        spec = dict(self.PET, reward_items={FREE_PLAY_COUPON: 1})
        p = profile_with_tasks(spec)
        p.record_cat_petted()
        panel = TaskPanel(p)
        panel.update(1)
        panel.draw(pygame.Surface((400, 300)))
        for _ in range(5):                                       # mashing E
            panel.handle_event(key(pygame.K_e))
        self.assertEqual((p.tokens, p.inventory.get_quantity(FREE_PLAY_COUPON)), (13, 1))
        panel.draw(pygame.Surface((400, 300)))
        self.assertEqual(p.daily_tasks[0].reward_bundle.lines(), ["+3 TOKENS", "+1 FREE PLAY COUPON"])


# ---------------------------------------------------------------- the coupon task
class CouponTaskTests(unittest.TestCase):
    def pool_ids(self, p):
        return [t.id for t in p.daily_tasks]

    def test_pool_has_the_example_tasks(self):
        ids = {s["id"] for s in DAILY_TASK_POOL}
        self.assertTrue({"play_games", "pet_cats", "earn_tickets", "use_coupon", "beat_high_score"} <= ids)

    def test_coupon_task_only_offered_to_coupon_owners(self):
        for day in range(40):
            p = PlayerProfile(clock=clock_at(DAY1 + timedelta(days=day)))
            self.assertNotIn("use_coupon", self.pool_ids(p))
            self.assertEqual(len(p.daily_tasks), DAILY_TASK_COUNT)
        offered = 0
        for day in range(40):
            p = PlayerProfile(clock=clock_at(DAY1 + timedelta(days=day)))
            p.inventory.add_item(FREE_PLAY_COUPON)
            p.reset_daily_tasks()
            offered += "use_coupon" in self.pool_ids(p)
            self.assertEqual(len(p.daily_tasks), DAILY_TASK_COUNT)
        self.assertGreater(offered, 0)

    def test_new_day_roll_respects_eligibility(self):
        p = PlayerProfile(clock=clock_at())
        p.clock = clock_at(DAY1 + timedelta(days=1))
        p.sync_daily_tasks()
        self.assertNotIn("use_coupon", self.pool_ids(p))

    def spec(self):
        return {"id": "u", "description": "USE A COUPON", "event": "coupon_used", "target": 1, "reward": 4}

    def machine(self):
        return ArcadeMachine(dict(MACHINES[1], play_cost=1))

    def test_playing_with_a_coupon_completes_the_task(self):
        p = profile_with_tasks(self.spec())
        p.inventory.add_item(FREE_PLAY_COUPON)
        session = self.machine().start_play(p, use_coupon=True)
        self.assertFalse(p.daily_tasks[0].completed)             # not yet: the game has to be played
        session.settle(RewardResult("space_blaster", 5))
        session.settle(RewardResult("space_blaster", 5))
        self.assertEqual(p.daily_tasks[0].progress, 1)
        self.assertTrue(p.daily_tasks[0].completed)

    def test_paying_with_tokens_does_not_count(self):
        p = profile_with_tasks(self.spec())
        self.machine().start_play(p).settle(RewardResult("space_blaster", 5))
        self.assertEqual(p.daily_tasks[0].progress, 0)

    def test_a_refunded_coupon_does_not_count(self):
        p = profile_with_tasks(self.spec())
        p.inventory.add_item(FREE_PLAY_COUPON)
        session = self.machine().start_play(p, use_coupon=True)
        session.refund()
        self.assertEqual((p.daily_tasks[0].progress, p.inventory.get_quantity(FREE_PLAY_COUPON)), (0, 1))

    def test_coupon_task_through_the_arcade(self):
        d = tempfile.mkdtemp()
        try:
            path = os.path.join(d, "s.json")
            with open(path, "w") as f:
                json.dump({"tokens": 3, "inventory": {FREE_PLAY_COUPON: 1}}, f)
            g = Game(save_path=path, clock=clock_at())
            g.profile._tasks = DailyTaskManager(pool=[self.spec()], count=1)
            g.profile._tasks.ensure_current(DAY1)
            room = g.scenes.current

            def frames(n, events=()):
                g.step(list(events), DT)
                for _ in range(n - 1):
                    g.step([], DT)

            frames(3, [key(pygame.K_ESCAPE)])
            m = next(m for m in room.machines if m.id == "space_blaster")
            room.player.x, room.player.y = m.rect.centerx, m.rect.bottom + 12
            frames(5)
            frames(30, [key(pygame.K_e)])
            frames(1, [key(pygame.K_RETURN)])
            frames(30)
            frames(1, [key(pygame.K_RETURN)])                    # YES, use the coupon
            frames(40)
            frames(40, [key(pygame.K_ESCAPE)])
            frames(5)
            self.assertTrue(g.profile.daily_tasks[0].completed)
            self.assertEqual(g.profile.claim_task("u"), 4)
            self.assertEqual(g.profile.tokens, 3 + 4)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class ProfileBoundaryTests(unittest.TestCase):
    def test_profile_still_has_a_single_reward_path_for_tokens(self):
        """Claims pay through RewardService.grant, not by calling add_tokens themselves."""
        import inspect
        for name in ("claim_daily_reward", "claim_task_reward"):
            src = inspect.getsource(getattr(PlayerProfile, name))
            self.assertIn("RewardService.grant", src)
            self.assertNotIn("add_tokens", src)


if __name__ == "__main__":
    unittest.main()
