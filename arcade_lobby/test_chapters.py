"""The main quest's three chapters: Secret Item order, sequential unlocking, the lifetime-earnings milestones of Trials 02 and 03,
old-save compatibility, and the Quest Log / Legacy Terminal telling the same story.

    python3 -m unittest test_chapters
"""
import json
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import legacy_terminal as LT  # noqa: E402
import quests as Q  # noqa: E402
import settings  # noqa: E402
from game import Game  # noqa: E402
from local_session import GameEvent, LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from quest_ui import ObjectiveTracker, QuestLogUI  # noqa: E402
from quests import (CHAPTERS, QUESTS, SECRET_ITEMS, TRIALS, QuestManager, exit_status, trial_earnings,  # noqa: E402
                    trial_status)
from room_testing import goto_room  # noqa: E402

pygame.init()
DT = 1 / 60
OPENING = ["grand_tour", "meet_the_locals", "arcade_explorer", "earn_some_rewards"]
RACER, CLAW, DUNGEON = Q.SECRET_ITEM_RETRO_RACER, Q.SECRET_ITEM_CLAW, Q.SECRET_ITEM_DUNGEON


def profile(pid="ch", tokens=0, tickets=0, story=None):
    p = PlayerProfile(profile_id=pid, display_name=pid.upper(), tokens=tokens, tickets=tickets)
    p.set_story(story if story is not None else {"opening_done": True, "completed": list(OPENING)})
    return p


def manager(p):
    return QuestManager(LocalSession(p))


def finish(m, *chapters):
    for n in chapters:
        ch = CHAPTERS[n - 1]
        m.handle("secret_item_found", ch.item)
        m.handle("secret_trial_done", ch.trial)


class Base(unittest.TestCase):
    def setUp(self):
        self.p = profile()
        self.m = manager(self.p)

    def st(self, n, p=None):
        return trial_status(self.m, p or self.p, TRIALS[n - 1])

    def earn(self, tokens, tickets):
        """Earn until the LIFETIME totals are exactly this much (real rewards: add_tokens / add_tickets)."""
        p = self.p
        if p.lifetime_tokens_earned < tokens:
            p.add_tokens(tokens - p.lifetime_tokens_earned, "TEST")
        if p.lifetime_tickets_received < tickets:
            p.add_tickets(tickets - p.lifetime_tickets_received)
        self.assertEqual((p.lifetime_tokens_earned, p.lifetime_tickets_received), (tokens, tickets))

    def spend_all(self):
        self.p.spend_tokens(self.p.tokens, "TEST")
        self.p.spend_tickets(self.p.tickets)


# ------------------------------------------------------------------ the order
class OrderTests(unittest.TestCase):
    def test_the_secret_items_in_their_new_order_with_stable_ids(self):
        self.assertEqual([(i.slot, i.key, i.chapter) for i in SECRET_ITEMS],
                         [(1, "retro_racer_reverse_gear", 1), (2, "claw_secret_reward", 2), (3, "dungeon_grey_pixel", 3)])
        self.assertEqual([i.source for i in SECRET_ITEMS], ["RETRO RACER", "CLAW MACHINE", "DUNGEON MAZE"])

    def test_the_racers_own_item_name_is_the_same_item(self):
        self.assertEqual(Q.canonical_item("reverse_gear"), RACER)
        self.assertIsNone(Q.canonical_item("gem_cyan"))

    def test_the_chapters_and_their_trials(self):
        self.assertEqual([(c.number, c.title, c.item, c.trial) for c in CHAPTERS],
                         [(1, "THE GOLDEN AGE", RACER, "trial_01"), (2, "THE FORGOTTEN GAMES", CLAW, "trial_02"),
                          (3, "THE FINAL CHALLENGE", DUNGEON, "trial_03")])
        self.assertEqual([(t.id, t.chapter) for t in TRIALS], [("trial_01", 1), ("trial_02", 2), ("trial_03", 3)])
        self.assertEqual(TRIALS[0].title, "THE GOLDEN AGE")

    def test_the_quests_after_the_vending_machine_follow_the_chapters(self):
        tail = QUESTS[5:]
        self.assertEqual([q.trigger for q in tail],
                         [("item", RACER), ("trial", "trial_01"), ("item", CLAW), ("trial", "trial_02"),
                          ("item", DUNGEON), ("trial", "trial_03"), ("event", Q.FINALE_EVENT)])
        self.assertEqual([q.chapter for q in tail], [1, 1, 2, 2, 3, 3, 4])

    def test_the_milestones_live_in_one_settings_table(self):
        self.assertEqual(settings.SECRET_TRIAL_EARNINGS, {"trial_01": {"tokens": 0, "tickets": 0},
                                                         "trial_02": {"tokens": 15, "tickets": 150},
                                                         "trial_03": {"tokens": 30, "tickets": 300}})
        self.assertEqual([trial_earnings(t) for t in TRIALS], [(0, 0), (15, 150), (30, 300)])
        self.assertFalse(hasattr(settings, "TRIAL_FINAL_TICKETS"))          # the older, separate constants are gone
        self.assertFalse(hasattr(settings, "SECRET_TRIAL_BALANCE"))         # renamed: one name everywhere

    def test_the_milestones_are_configurable(self):
        old = json.loads(json.dumps(settings.SECRET_TRIAL_EARNINGS))
        self.addCleanup(setattr, settings, "SECRET_TRIAL_EARNINGS", old)
        settings.SECRET_TRIAL_EARNINGS = dict(old, trial_02={"tokens": 1, "tickets": 2})
        self.assertEqual(trial_earnings(TRIALS[1]), (1, 2))
        q = next(x for x in QUESTS if x.id == "ch2_secret_trial")
        self.assertIn("1 Tokens and 2 Tickets", Q.objective_text(q))


# ------------------------------------------------------------------ chapter unlocks
class ChapterUnlockTests(Base):
    def test_nothing_is_open_before_the_secret_interface(self):
        self.assertEqual(self.m.current_chapter, 0)
        self.assertFalse(any(self.m.chapter_unlocked(n) for n in (1, 2, 3, 4)))
        self.assertEqual([self.st(n).lock for n in (1, 2, 3)], [Q.LOCK_CHAPTER] * 3)

    def test_the_secret_interface_opens_chapter_01_only(self):
        self.m.handle("vending_secret")
        self.assertEqual(self.m.current_chapter, 1)
        self.assertEqual([self.m.chapter_unlocked(n) for n in (1, 2, 3, 4)], [True, False, False, False])
        self.assertEqual(self.m.active.id, "ch1_secret_item")

    def test_trial_01_is_available_first(self):
        self.m.handle("vending_secret")
        self.assertEqual(self.st(1).lock, Q.LOCK_ITEM)                       # its own way in: the Reverse Gear
        self.m.handle("secret_item_found", RACER)
        self.assertEqual(self.st(1).code, "available")                       # with an empty wallet: chapter 01 asks nothing
        self.assertEqual((self.p.tokens, self.p.tickets), (0, 0))
        self.assertEqual([self.st(n).code for n in (2, 3)], ["locked", "locked"])

    def test_chapter_02_needs_both_the_item_and_the_trial_of_chapter_01(self):
        self.m.handle("vending_secret")
        self.earn(99, 999)
        self.m.handle("secret_item_found", RACER)
        self.assertFalse(self.m.chapter_unlocked(2))
        self.assertEqual(self.st(2).lock, Q.LOCK_CHAPTER)
        self.assertEqual(self.st(2).reasons, ("COMPLETE CHAPTER 01 FIRST",))
        self.m.handle("secret_trial_done", "trial_01")
        self.assertTrue(self.m.chapter_unlocked(2))
        self.assertEqual(self.st(2).code, "available")
        self.assertEqual(self.m.active.id, "ch2_secret_item")

    def test_chapter_03_needs_chapter_02_complete(self):
        self.m.handle("vending_secret")
        self.earn(99, 999)
        finish(self.m, 1)
        self.m.handle("secret_trial_done", "trial_02")                      # trial without the claw prize: not complete
        self.assertFalse(self.m.chapter_unlocked(3))
        self.assertEqual(self.st(3).lock, Q.LOCK_CHAPTER)
        self.assertEqual(self.st(3).reasons, ("COMPLETE CHAPTER 02 FIRST",))
        self.m.handle("secret_item_found", CLAW)
        self.assertTrue(self.m.chapter_unlocked(3))
        self.assertEqual(self.st(3).code, "available")
        self.assertEqual(self.m.active.id, "ch3_secret_item")

    def test_the_finale_needs_all_six(self):
        self.m.handle("vending_secret")
        finish(self.m, 1, 2)
        self.m.handle("secret_item_found", DUNGEON)
        self.assertFalse(self.m.finale_unlocked)
        self.assertFalse(exit_status(self.m)[0])
        self.m.handle("secret_trial_done", "trial_03")
        self.assertTrue(self.m.finale_unlocked)
        self.assertEqual(exit_status(self.m), (True, ()))
        self.assertEqual(self.m.current_chapter, 4)
        self.assertEqual(self.m.active.id, "reopen_the_arcade")

    def test_quests_announce_each_new_chapter_step_in_order(self):
        self.m.handle("vending_secret")
        seen = []
        for ch in CHAPTERS:
            self.m.notifications.clear()
            self.m.handle("secret_item_found", ch.item)
            seen += [n.quest.id for n in self.m.notifications if n.kind == "quest"]
            self.m.notifications.clear()
            self.m.handle("secret_trial_done", ch.trial)
            seen += [n.quest.id for n in self.m.notifications if n.kind == "quest"]
        self.assertEqual(seen, ["ch1_secret_trial", "ch2_secret_item", "ch2_secret_trial", "ch3_secret_item",
                                "ch3_secret_trial", "reopen_the_arcade"])


# ------------------------------------------------------------------ nothing can be collected early
class EarlyCollectionTests(Base):
    def test_no_item_or_trial_counts_before_its_chapter(self):
        for key in (RACER, CLAW, DUNGEON):
            self.m.handle("secret_item_found", key)
        for t in ("trial_01", "trial_02", "trial_03"):
            self.m.handle("secret_trial_done", t)
        self.assertEqual((self.m.secret_items, self.m.secret_trials), (0, 0))
        self.assertEqual(self.p.story.get("stats", {}).get("secret_items", []), [])
        self.m.handle("vending_secret")
        self.m.handle("secret_item_found", CLAW)                             # chapter 02 still shut
        self.m.handle("secret_item_found", DUNGEON)
        self.m.handle("secret_trial_done", "trial_02")
        self.assertEqual((self.m.secret_items, self.m.secret_trials), (0, 0))
        self.assertFalse(self.m.can_collect(CLAW))
        self.assertFalse(self.m.can_collect(DUNGEON))
        self.assertTrue(self.m.can_collect(RACER))

    def test_unknown_keys_never_count(self):
        self.m.handle("vending_secret")
        for key in ("gem_cyan", "", None, 7):
            self.m.handle("secret_item_found", key)
        self.m.handle("secret_trial_done", "trial_99")
        self.assertEqual((self.m.secret_items, self.m.secret_trials), (0, 0))

    def test_the_racers_alias_is_recorded_under_the_stable_key(self):
        self.m.handle("vending_secret")
        self.m.handle("secret_item_found", "reverse_gear")
        self.assertEqual(self.m.state["stats"]["secret_items"], [RACER])

    def test_events_from_the_session_go_through_the_same_gate(self):
        me = self.p.profile_id
        self.assertTrue(self.m.session.dispatch(GameEvent("secret_item_found", me, key=RACER)))
        self.assertEqual(self.m.secret_items, 0)
        self.m.session.dispatch(GameEvent("vending_secret", me))
        self.m.session.dispatch(GameEvent("secret_item_found", me, key=RACER))
        self.assertEqual(self.m.secret_items, 1)


# ------------------------------------------------------------------ lifetime earnings milestones (not the wallet, not fees)
class EarningsTests(Base):
    def setUp(self):
        super().setUp()
        self.m.handle("vending_secret")

    def open_chapter(self, n):
        finish(self.m, *range(1, n))
        self.assertTrue(self.m.chapter_unlocked(n))

    def test_exact_milestones_let_the_player_in(self):
        self.open_chapter(2)
        self.earn(15, 150)
        self.assertEqual(self.st(2).code, "available")
        finish(self.m, 2)
        self.earn(30, 300)
        self.assertEqual(self.st(3).code, "available")

    def test_both_milestones_must_be_reached(self):
        self.open_chapter(2)
        self.earn(14, 150)
        s = self.st(2)
        self.assertEqual((s.code, s.lock, s.reasons), ("locked", Q.LOCK_EARNINGS, ("EARN 15 TOKENS IN TOTAL (EARNED 14)",)))
        self.p.add_tokens(1, "WIN")
        self.assertEqual(self.st(2).code, "available")
        finish(self.m, 2)
        self.earn(30, 299)
        self.assertEqual(self.st(3).reasons, ("EARN 300 TICKETS IN TOTAL (EARNED 299)",))
        self.p.add_tickets(1)
        self.assertEqual(self.st(3).code, "available")

    def test_the_example_from_the_brief_200_earned_180_spent(self):
        self.open_chapter(2)
        self.p.add_tickets(200)
        self.p.spend_tickets(180)
        self.p.add_tokens(15, "WIN")
        self.assertEqual((self.p.tickets, self.p.lifetime_tickets_received), (20, 200))
        self.assertEqual(self.st(2).code, "available")

    def test_spending_below_the_milestone_never_locks_the_trial_again(self):
        self.open_chapter(2)
        self.earn(15, 150)
        self.spend_all()
        self.assertEqual((self.p.tokens, self.p.tickets), (0, 0))
        self.assertEqual(self.st(2).code, "available")
        self.assertEqual((self.st(2).tokens_earned, self.st(2).tickets_earned), (15, 150))

    def test_a_large_wallet_does_not_count_as_earnings(self):
        rich = profile("rich", tokens=500, tickets=5000)                    # a starting wallet, nothing earned
        m = manager(rich)
        m.handle("vending_secret")
        finish(m, 1)
        s = trial_status(m, rich, TRIALS[1])
        self.assertEqual((s.lock, s.tokens_earned, s.tickets_earned), (Q.LOCK_EARNINGS, 0, 0))

    def test_staff_panel_grants_and_refunds_are_not_earnings(self):
        import staff_cheat
        self.open_chapter(2)
        staff_cheat.StaffService(self.p).grant(PlayerProfile.TICKET, 100)
        staff_cheat.StaffService(self.p).grant(PlayerProfile.TOKEN, 10)
        self.p.refund_tokens(5, "TEST")
        self.p.refund_tickets(5)
        self.assertEqual((self.p.lifetime_tokens_earned, self.p.lifetime_tickets_received), (0, 0))
        self.assertEqual(self.st(2).lock, Q.LOCK_EARNINGS)

    def test_checking_and_entering_never_deduct_anything(self):
        self.open_chapter(2)
        self.earn(15, 150)
        before = self.p.to_dict()
        for _ in range(5):
            for n in (1, 2, 3):
                self.st(n)
            exit_status(self.m)
        self.m.handle("secret_trial_done", "trial_02")
        after = self.p.to_dict()
        self.assertEqual({k: v for k, v in before.items() if k != "story"}, {k: v for k, v in after.items() if k != "story"})

    def test_completed_trials_stay_done_whatever_happens_to_the_wallet(self):
        self.open_chapter(3)
        self.earn(30, 300)
        self.m.handle("secret_item_found", DUNGEON)
        self.m.handle("secret_trial_done", "trial_03")
        self.spend_all()
        for n in (1, 2, 3):
            self.assertEqual(self.st(n).code, "done")
        self.assertTrue(self.m.has_memory_fragment("trial_01"))
        self.assertTrue(self.m.finale_unlocked)

    def test_earnings_from_before_the_chapter_opened_count(self):
        self.earn(30, 300)                                                  # earned long before chapter 02
        self.open_chapter(2)
        self.assertEqual(self.st(2).code, "available")

    def test_chapter_01_never_asks_for_earnings(self):
        self.m.handle("secret_item_found", RACER)
        s = self.st(1)
        self.assertEqual((s.code, s.needs_earnings), ("available", False))

    def test_earnings_never_skip_a_chapter(self):
        self.earn(99, 999)
        self.assertEqual([self.st(n).lock for n in (2, 3)], [Q.LOCK_CHAPTER, Q.LOCK_CHAPTER])


# ------------------------------------------------------------------ saves
class SaveTests(unittest.TestCase):
    def store(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return ProfileStore(os.path.join(d, "p.json"))

    def test_earnings_and_completions_survive_save_and_load(self):
        store = self.store()
        p = profile("sv", tokens=0, tickets=0)
        p.add_tokens(20, "WIN")
        p.add_tickets(170)
        p.spend_tickets(160)
        m = manager(p)
        m.handle("vending_secret")
        finish(m, 1)
        m.handle("secret_item_found", CLAW)
        store.save(p)
        loaded = store.load()
        m2 = manager(loaded)
        self.assertEqual((loaded.tokens, loaded.tickets), (20, 10))
        self.assertEqual((loaded.lifetime_tokens_earned, loaded.lifetime_tickets_received), (20, 170))
        self.assertEqual(m2.secret_items, 2)
        self.assertEqual(m2.secret_trials, 1)
        self.assertEqual(m2.current_chapter, 2)
        self.assertEqual(m2.active.id, "ch2_secret_trial")
        self.assertEqual(trial_status(m2, loaded, TRIALS[0]).code, "done")
        self.assertEqual(trial_status(m2, loaded, TRIALS[1]).code, "available")

    def test_an_old_way_out_profile_with_the_reverse_gear_keeps_it_and_lands_in_the_right_chapter(self):
        old = {"opening_done": True, "completed": OPENING + ["check_the_vending_machine"],
               "flags": {"vending_secret": True, "miao_reverse_road": True},
               "stats": {"played": ["a", "b", "c"], "secret_items": [RACER]}, "hints": {"the_way_out": 1}}
        p = profile("old", tokens=3, tickets=40, story=old)
        m = manager(p)
        self.assertTrue(m.has_secret_item(RACER))
        self.assertEqual(m.active.id, "ch1_secret_trial")
        self.assertEqual(m.current_chapter, 1)
        self.assertEqual(p.story["stats"]["secret_items"], [RACER])
        self.assertEqual(p.story["hints"], {"the_way_out": 1})              # nothing in the save is thrown away
        self.assertEqual((p.tokens, p.tickets), (3, 40))

    def test_an_old_profile_that_finished_trial_01_reaches_chapter_02(self):
        old = {"opening_done": True, "completed": OPENING + ["check_the_vending_machine"],
               "flags": {"vending_secret": True, "memory_fragment_01": True},
               "stats": {"secret_items": [RACER], "secret_trials": ["trial_01"]}}
        m = manager(profile("old2", story=old))
        self.assertEqual(m.current_chapter, 2)
        self.assertEqual(m.active.id, "ch2_secret_item")
        self.assertTrue(m.has_memory_fragment("trial_01"))

    def test_an_item_found_early_under_the_old_rules_is_kept_and_counts_when_its_chapter_comes(self):
        old = {"opening_done": True, "completed": list(OPENING), "stats": {"secret_items": [RACER, "gem_cyan"]}}
        p = profile("early", story=old)
        m = manager(p)
        self.assertTrue(m.has_secret_item(RACER))                            # kept, even before the Secret Interface
        self.assertEqual(m.active.id, "check_the_vending_machine")
        m.handle("vending_secret")
        self.assertEqual(m.active.id, "ch1_secret_trial")                    # step one is already done
        self.assertEqual(p.story["stats"]["secret_items"], [RACER, "gem_cyan"])
        self.assertEqual(m.secret_items, 1)

    def test_a_later_trial_done_out_of_order_in_an_old_save_stays_done(self):
        old = {"opening_done": True, "completed": OPENING + ["check_the_vending_machine"],
               "flags": {"vending_secret": True}, "stats": {"secret_trials": ["trial_02"]}}
        p = profile("ooo", story=old)
        m = manager(p)
        self.assertEqual(trial_status(m, p, TRIALS[1]).code, "done")
        self.assertEqual(m.current_chapter, 1)                               # the chapters still run in order
        finish(m, 1)
        m.handle("secret_item_found", CLAW)
        self.assertEqual(m.current_chapter, 3)                               # ... and the old trial fills chapter 02 at once

    def test_a_profile_from_before_the_story_still_loads(self):
        p = PlayerProfile(profile_id="ancient", display_name="A", tokens=5, tickets=9)
        m = manager(p)
        self.assertEqual((m.secret_items, m.secret_trials, m.current_chapter), (0, 0, 0))
        self.assertEqual((p.tokens, p.tickets), (5, 9))


# ------------------------------------------------------------------ the Quest Log, the tracker and the terminal agree
class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.p = profile("ds", tokens=0, tickets=0)
        self.p.set_story({"opening_done": True, "completed": list(OPENING)})
        self.p.add_tokens(20, "WIN")                     # earned 20 / 120 in total ...
        self.p.add_tickets(120)
        self.p.spend_tokens(8, "PLAY")                   # ... and spent some: the wallet (12 / 120) is NOT what is shown
        self.game = Game(session=LocalSession(self.p))
        self.addCleanup(self.game.quit)
        self.m = self.game.hub.story.manager
        self.room = goto_room(self.game, "arcade_floor")
        for _ in range(10):
            self.game.step([], DT)

    def shown(self, drawable, *args):
        from unittest import mock
        texts = []
        targets = ["quest_ui.draw_text"] if isinstance(drawable, QuestLogUI) else ["legacy_terminal.draw_text"]
        with mock.patch(targets[0], lambda surf, text, *a, **k: texts.append(str(text)) or pygame.Rect(0, 0, 1, 1)):
            drawable.draw(pygame.Surface((400, 300)), *args)
        return texts

    def terminal(self):
        term = LT.LegacyTerminalScene(self.game, self.game.session.primary)
        term.time = term.boot_time + 5
        return term

    def test_the_quest_log_names_the_current_chapter_and_the_next_objective(self):
        self.m.handle("vending_secret")
        finish(self.m, 1)
        log = QuestLogUI(self.m, self.p)
        texts = self.shown(log)
        self.assertIn("Chapter 02: The Forgotten Games", texts)
        self.assertIn("CHAPTERS", texts)
        self.assertEqual(log.chapter_rows(), [("01", "THE GOLDEN AGE", "DONE"), ("02", "THE FORGOTTEN GAMES", "NOW"),
                                              ("03", "THE FINAL CHALLENGE", "LOCKED"), ("FIN", "REOPEN THE ARCADE", "LOCKED")])

    def test_the_quest_log_shows_the_earnings_a_trial_step_asks_for(self):
        self.m.handle("vending_secret")
        finish(self.m, 1)
        self.m.handle("secret_item_found", CLAW)
        texts = self.shown(QuestLogUI(self.m, self.p))
        self.assertIn("TOKENS EARNED 20/15", texts)                       # lifetime, not the 12 in the wallet
        self.assertIn("TICKETS EARNED 120/150", texts)
        self.assertIn("Earn 15 Tokens and 150 Tickets in total", self.m.objective_text())
        detail = [t for t, _ in ObjectiveTracker(self.m)._detail()]
        self.assertEqual(detail, ["CH 02: COMPLETE SECRET TRIAL 02", "TOKENS EARNED 20/15", "TICKETS EARNED 120/150"])
        self.assertFalse(any(t.startswith("TOKENS 12") for t in texts))

    def test_locked_chapters_never_name_where_or_how_their_secret_is_found(self):
        self.m.handle("vending_secret")
        texts = " ".join(self.shown(QuestLogUI(self.m, self.p)) + self.shown(self.terminal())).upper()
        for word in ("CLAW", "DUNGEON", "GREY", "PIXEL"):
            self.assertNotIn(word, texts, word)

    def test_the_terminal_and_the_log_agree_on_the_counts_and_the_chapter(self):
        self.m.handle("vending_secret")
        finish(self.m, 1)
        term = self.terminal()
        self.assertEqual(term.chapter_line(), "CHAPTER 02  THE FORGOTTEN GAMES")
        log = QuestLogUI(self.m, self.p)
        now = [r for r in log.chapter_rows() if r[2] == "NOW"][0]
        self.assertEqual(f"CHAPTER {now[0]}  {now[1]}", term.chapter_line())
        texts = self.shown(term)
        self.assertIn("1 / 3", texts)                                      # items and trials alike

    def test_the_terminal_shows_four_distinct_states(self):
        self.m.handle("vending_secret")
        finish(self.m, 1)                                                  # 01 done, 02 open but 120 tickets earned, 03 chapter-locked
        term = self.terminal()
        self.assertEqual([term.status(t).short for t in TRIALS], ["COMPLETE", "NEED EARNINGS", "LOCKED"])
        term.index = 1
        rows = [r[0] for r in term.detail_rows()]
        self.assertEqual(rows[:2], ["TOKENS EARNED: 20 / 15", "TICKETS EARNED: 120 / 150"])   # the real lifetime totals
        term.index = 2
        rows = [r[0] for r in term.detail_rows()]
        self.assertIn("COMPLETE CHAPTER 02 FIRST", rows)
        self.assertIn("TOKENS EARNED: 20 / 30", rows)
        self.assertIn("TICKETS EARNED: 120 / 300", rows)
        term.index = 0
        self.assertIn("COMPLETE. REPLAYABLE.", [r[0] for r in term.detail_rows()])
        self.p.add_tickets(30)
        self.p.spend_tickets(self.p.tickets)                              # earned it, then spent everything
        self.assertEqual(term.status(TRIALS[1]).short, "AVAILABLE")
        self.shown(term)

    def test_choosing_a_trial_with_too_little_earned_says_so_and_charges_nothing(self):
        self.m.handle("vending_secret")
        finish(self.m, 1)
        term = self.terminal()
        term.index = 1
        wallet = (self.p.tokens, self.p.tickets)
        term.select()
        self.assertEqual(term.notice["title"], "EARNINGS REQUIRED")
        self.assertIn("EARN 150 TICKETS IN TOTAL (EARNED 120)", term.notice["lines"])
        self.assertNotIn("EARN 15 TOKENS IN TOTAL (EARNED 20)", term.notice["lines"])      # 20 earned: that one is met
        self.assertEqual((self.p.tokens, self.p.tickets), wallet)

    def test_a_completed_trial_is_replayed_even_when_the_wallet_is_empty(self):
        self.m.handle("vending_secret")
        finish(self.m, 1)
        self.p.spend_tokens(self.p.tokens, "T")
        self.p.spend_tickets(self.p.tickets)
        term = self.terminal()
        pushed = []
        from unittest import mock
        with mock.patch.object(self.game.scenes, "push", lambda scene, *a, **k: pushed.append(scene)):
            term.index = 0
            term.select()
        self.assertEqual(len(pushed), 1)
        self.assertIsInstance(pushed[0], LT.TRIAL_SCENES["trial_01"])
        self.assertIsNone(term.notice)


# ------------------------------------------------------------------ everything else stays as it was
class OrdinaryPlayTests(unittest.TestCase):
    def test_every_minigame_machine_still_launches_without_any_chapter(self):
        p = profile("free", tokens=50, tickets=0)
        game = Game(session=LocalSession(p))
        self.addCleanup(game.quit)
        room = goto_room(game, "arcade_floor")
        self.assertEqual(game.hub.story.manager.current_chapter, 0)
        ids = {m.id for m in room.machines}
        for needed in ("retro_racer", "puzzle_maze"):
            self.assertIn(needed, ids)
        from scenes import MINIGAME_DEFINITIONS
        for game_id in MINIGAME_DEFINITIONS:
            self.assertNotIn("chapter", repr(MINIGAME_DEFINITIONS[game_id]).lower())

    def test_the_game_is_still_one_player(self):
        p = profile("solo")
        game = Game(session=LocalSession(p))
        self.addCleanup(game.quit)
        self.assertEqual(len(game.session.players), 1)
        self.assertEqual(game.hub.story.manager.profiles, [p])

    def test_kevin_is_never_named_before_the_finale(self):
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("quests.py", "quest_ui.py", "legacy_terminal.py", "story.py", "miao_meow.py", "mochi_chat.py"):
            with open(os.path.join(here, name), encoding="utf-8") as f:
                self.assertNotIn("kevin", f.read().lower(), name)
        texts = [q.title + q.objective + q.hud + " ".join(q.hints) for q in QUESTS]
        self.assertFalse(any("kevin" in t.lower() for t in texts))

    def test_the_finale_stays_locked_until_all_six(self):
        p = profile("fin")
        m = manager(p)
        m.handle("vending_secret")
        steps = [("secret_item_found", RACER), ("secret_trial_done", "trial_01"), ("secret_item_found", CLAW),
                 ("secret_trial_done", "trial_02"), ("secret_item_found", DUNGEON), ("secret_trial_done", "trial_03")]
        for i, step in enumerate(steps):
            self.assertFalse(m.finale_unlocked, i)
            m.handle(*step)
        self.assertTrue(m.finale_unlocked)

    def test_all_new_story_text_is_english_and_printable_in_the_pixel_font(self):
        from font import _GLYPHS
        texts = [q.title.upper() for q in QUESTS] + [Q.objective_text(q).upper() for q in QUESTS] + \
            [q.hud for q in QUESTS] + [h.upper() for q in QUESTS for h in q.hints] + \
            [c.title for c in CHAPTERS] + [t.title for t in TRIALS] + [Q.FINAL_CHAPTER_TITLE]
        for text in texts:
            for ch in text:
                self.assertTrue(ch == " " or ch in _GLYPHS, (ch, text))


if __name__ == "__main__":
    unittest.main()
