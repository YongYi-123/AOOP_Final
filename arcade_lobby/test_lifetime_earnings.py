"""Lifetime earnings: the persistent counters the Secret Trials read (PlayerProfile.lifetime_tokens_earned and
lifetime_tickets_received = lifetime_tickets_earned + lifetime_tickets_won), and the one-time settling of older saves.

    python3 -m unittest test_lifetime_earnings
"""
import json
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import staff_cheat  # noqa: E402
from player_profile import LIFETIME_BASELINE_VERSION, PlayerProfile, ProfileStore  # noqa: E402
from rewards import PlaySession, RewardBundle, RewardResult, RewardService  # noqa: E402


def totals(p):
    return p.lifetime_tokens_earned, p.lifetime_tickets_received


class EarningTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(tokens=10, tickets=0)

    def test_a_new_profile_has_earned_nothing_and_its_starting_wallet_is_not_earnings(self):
        self.assertEqual(totals(self.p), (0, 0))
        self.assertEqual(self.p.lifetime_baseline, {"version": LIFETIME_BASELINE_VERSION})

    def test_rewards_raise_the_totals(self):
        self.p.add_tokens(7, "DAILY LOGIN")
        self.p.add_tickets(25)
        self.assertEqual(totals(self.p), (7, 25))

    def test_a_minigame_round_pays_its_tickets_exactly_once(self):
        self.p.spend_tokens(1, "PLAY")
        play = PlaySession(self.p, "galaxy_defender", 1)
        result = RewardResult("galaxy_defender", score=500, tickets_earned=12)
        play.settle(result)
        play.settle(result)                                                   # a second settle is ignored
        play.refund()                                                         # ... and so is a refund afterwards
        self.assertEqual(totals(self.p), (0, 12))
        self.assertEqual(self.p.tickets, 12)

    def test_a_reward_bundle_counts_once(self):
        RewardService.grant(self.p, RewardBundle(tokens=5, tickets=40, reason="QUEST"))
        self.assertEqual(totals(self.p), (5, 40))

    def test_game_room_winnings_count_once_and_keep_the_daily_task_counter_apart(self):
        self.p.award_neon21_tickets(10)
        self.p.award_pusher_tickets(4)
        paid = self.p.award_pinball(6, 3)                                    # (tokens are clipped to the daily cap)
        self.assertEqual(paid[0], 6)
        self.assertEqual(self.p.lifetime_tickets_won, 20)
        self.assertEqual(self.p.lifetime_tickets_earned, 0)                  # (the EARN TICKETS task counter is unchanged)
        self.assertEqual(totals(self.p), (paid[1], 20))                      # pinball tokens: once, exactly what was paid
        self.assertEqual(self.p.tokens, 10 + paid[1])

    def test_claw_prize_tickets_count_once_toward_trials_but_not_as_an_arcade_floor_win(self):
        from local_session import LocalSession
        from quests import QuestManager
        p = PlayerProfile(profile_id="claw", display_name="C", tokens=10, tickets=0)
        p.set_story({"opening_done": True, "completed": ["grand_tour", "meet_the_locals", "arcade_explorer"]})
        m = QuestManager(LocalSession(p))
        self.assertEqual(m.active.id, "earn_some_rewards")
        p.award_prize_tickets(25)
        self.assertEqual((p.tickets, p.lifetime_tickets_won, p.lifetime_tickets_earned), (25, 25, 0))
        self.assertEqual(totals(p), (0, 25))
        self.assertEqual(m.active.id, "earn_some_rewards")                  # (only an Arcade Floor win completes it)

    def test_spending_never_lowers_the_totals(self):
        self.p.add_tokens(30, "WIN")
        self.p.add_tickets(300)
        self.p.spend_tokens(40, "PLAY")
        self.p.spend_tickets(300)
        self.assertEqual((self.p.tokens, self.p.tickets), (0, 0))
        self.assertEqual(totals(self.p), (30, 300))

    def test_refunds_and_staff_grants_never_raise_the_totals(self):
        self.p.spend_tokens(5, "PLAY")
        self.p.refund_tokens(5, "PLAY")
        self.p.add_tickets(10)
        self.p.spend_tickets(10)
        self.p.refund_tickets(10)
        staff = staff_cheat.StaffService(self.p)
        staff.grant(PlayerProfile.TOKEN, 10)
        staff.grant(PlayerProfile.TICKET, 100)
        self.assertEqual(totals(self.p), (0, 10))

    def test_a_refunded_play_is_not_earnings(self):
        self.p.spend_tokens(1, "PLAY")
        PlaySession(self.p, "galaxy_defender", 1).refund()
        self.assertEqual(totals(self.p), (0, 0))
        self.assertEqual(self.p.tokens, 10)

    def test_reading_the_totals_changes_nothing(self):
        before = self.p.to_dict()
        for _ in range(3):
            totals(self.p)
            self.p.lifetime_baseline
        self.assertEqual(self.p.to_dict(), before)


class SaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def write(self, data, name="p.json"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_save_and_load_keep_the_counters_and_reloading_never_adds_anything(self):
        p = PlayerProfile(profile_id="s", display_name="S", tokens=0, tickets=0)
        p.add_tokens(18, "WIN")
        p.add_tickets(90)
        p.award_neon21_tickets(10)
        p.spend_tickets(95)
        path = os.path.join(self.dir, "s.json")
        store = ProfileStore(path)
        store.save(p)
        for _ in range(3):                                                    # load, save, load again ...
            p = store.load()
            store.save(p)
        self.assertEqual(totals(p), (18, 100))
        self.assertEqual((p.lifetime_tickets_earned, p.lifetime_tickets_won), (90, 10))
        self.assertEqual((p.tokens, p.tickets), (18, 5))

    def old_save(self, **fields):
        data = {"version": 2, "profile_id": "old", "display_name": "OLD", "tokens": 14, "tickets": 20,
                "lifetime_tickets_earned": 20, "lifetime_tokens_earned": 10, "lifetime_tokens_spent": 6,
                "transaction_history": [{"date": "2026-11-01", "delta": 10, "reason": "DAILY LOGIN"},
                                        {"date": "2026-11-01", "delta": -6, "reason": "PLAY"}]}
        data.update(fields)
        return {k: v for k, v in data.items() if v is not None}

    def test_an_old_save_whose_counters_cover_everything_is_read_as_saved(self):
        p = PlayerProfile.from_dict(self.old_save())
        self.assertEqual(totals(p), (10, 20))                                # tokens tracked from the first wallet: kept
        self.assertEqual(p.lifetime_baseline, {"version": LIFETIME_BASELINE_VERSION})

    def test_old_untracked_winnings_are_recovered_from_the_machines_records(self):
        p = PlayerProfile.from_dict(self.old_save(tickets=40, neon21={"date": "2026-11-02", "tickets": 12},
                                                  pinball={"date": "2026-11-03", "tickets": 3, "tokens": 0}))
        self.assertEqual(p.lifetime_tickets_won, 20)                         # 15 on record, 20 needed to explain the wallet
        self.assertEqual(p.lifetime_baseline["tickets_won_recovered"], 15)
        self.assertEqual(p.lifetime_baseline["tickets_won_assumed"], 5)
        self.assertEqual(p.lifetime_tickets_received, 40)

    def test_tickets_held_but_unexplained_are_never_treated_as_zero(self):
        p = PlayerProfile.from_dict(self.old_save(tickets=820, lifetime_tickets_earned=60))
        self.assertEqual(p.lifetime_tickets_received, 820)                   # at least what the player owns
        self.assertEqual(p.lifetime_baseline["tickets_won_assumed"], 760)

    def test_an_old_save_without_a_token_counter_gets_a_safe_baseline(self):
        history = [{"date": "d", "delta": 30, "reason": "DAILY LOGIN"}, {"date": "d", "delta": 5, "reason": "PLAY REFUND"},
                   {"date": "d", "delta": -25, "reason": "PLAY"}]
        p = PlayerProfile.from_dict(self.old_save(lifetime_tokens_earned=None, tokens=12, transaction_history=history))
        self.assertEqual(p.lifetime_tokens_earned, 30)                       # the history shows 30 earned (refund excluded)
        self.assertEqual(p.lifetime_baseline["tokens_earned_assumed"], 30)
        p2 = PlayerProfile.from_dict(self.old_save(lifetime_tokens_earned=None, tokens=50, transaction_history=[]))
        self.assertEqual(p2.lifetime_tokens_earned, 50)                      # no history: the current balance

    def test_the_settling_happens_once(self):
        path = self.write(self.old_save(tickets=40, neon21={"date": "d", "tickets": 12}))
        store = ProfileStore(path)
        first = store.load()
        store.save(first)
        again = store.load()
        again.spend_tickets(40)
        store.save(again)
        third = store.load()                                                # balance 0 now: nothing is re-derived
        self.assertEqual(third.lifetime_tickets_received, first.lifetime_tickets_received)
        self.assertEqual(third.lifetime_baseline, first.lifetime_baseline)
        self.assertEqual(third.tickets, 0)

    def test_loading_an_old_save_does_not_rewrite_the_file_or_touch_the_wallet(self):
        data = self.old_save(tickets=40)
        path = self.write(data)
        with open(path, "rb") as f:
            raw = f.read()
        p = ProfileStore(path).load()
        with open(path, "rb") as f:
            self.assertEqual(f.read(), raw)                                  # (it is saved by the game as it is played)
        self.assertEqual((p.tokens, p.tickets), (14, 40))

    def test_damaged_counters_fall_back_safely(self):
        p = PlayerProfile.from_dict(self.old_save(lifetime_tickets_won=-5, lifetime_baseline="junk",
                                                  lifetime_tokens_earned="x", tokens=9))
        self.assertGreaterEqual(p.lifetime_tokens_earned, 9)
        self.assertGreaterEqual(p.lifetime_tickets_received, p.tickets)
        self.assertEqual(p.lifetime_baseline["version"], LIFETIME_BASELINE_VERSION)

    def test_a_profile_from_before_any_counter_loads(self):
        p = PlayerProfile.from_dict({"coins": 7})
        self.assertEqual((p.tokens, p.lifetime_tokens_earned), (7, 7))
        self.assertEqual(p.lifetime_tickets_received, 0)


if __name__ == "__main__":
    unittest.main()
