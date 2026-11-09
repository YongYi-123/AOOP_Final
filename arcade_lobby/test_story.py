"""Tests for the main story: the quest system (data, progress, sharing, saving, veteran saves), the dialogue box,
the opening cutscene, the quest screens (tracker, banner, Quest Log on Q), Miao Meow's hints, and the vending
machine's secret as the only thing that completes its quest.

Run headless from this folder:   python -m unittest test_story -v
"""
import json
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import miao_meow as mm  # noqa: E402
import quests as Q  # noqa: E402
import story as S  # noqa: E402
import legacy_terminal as LT  # noqa: E402
import settings  # noqa: E402
import story_dialogue as D  # noqa: E402
from controls import SOLO_CONTROLS  # noqa: E402
from game import Game  # noqa: E402
from local_session import GameEvent, LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore, clean_story  # noqa: E402
from quest_ui import ObjectiveTracker, QuestBanner, QuestLogUI  # noqa: E402
from quests import (QUESTS, TRIALS, Notification, QuestDef, QuestManager, TrialDef, exit_status, trial_cost,
                    trial_status)  # noqa: E402
from room_testing import goto_room  # noqa: E402
from vending_ui import SECRET_FLAG, SECRET_DUCK, VendingScene, GLITCH_TIME, TERMINAL_TYPED  # noqa: E402

DT = 1 / 60
K = pygame
CLASSIC = [K.K_UP, K.K_UP, K.K_DOWN, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_LEFT, K.K_RIGHT, K.K_b, K.K_a]


def down(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def up(k):
    return pygame.event.Event(pygame.KEYUP, key=k, mod=0)


def session_of(profile):
    return LocalSession(profile)


def fresh(pid="a", **kw):
    return PlayerProfile(profile_id=pid, display_name=pid.upper(), **kw)


def finished(profile_id="a", tour=True, **kw):
    """A manager whose opening is over (so quests are live), on a one-player session. The arcade tour (quests one and two,
    which need the conversations in tour.py) has been taken too unless `tour=False`: most tests are about what comes after."""
    p = fresh(profile_id, **kw)
    m = QuestManager(session_of(p))
    m.finish_opening()
    if tour:
        m.handle("tour_arcade")
        m.handle("met_mochi")
    m.notifications.clear()
    return p, m


def play(m, *games):
    for g in games:
        m.handle("game_played", g)


def all_text():
    texts = []
    for q in QUESTS:
        texts += [q.title, q.objective, q.hud, q.intro, *q.hints]
    texts += [line.text for line in S.OPENING_LINES]
    texts += [t for t, _ in S.GREETINGS + S.NO_QUEST_CHAT]
    texts += list(Q.PROTOCOL_LINES)
    return texts


# ------------------------------------------------------------------ the quest data
class QuestDataTests(unittest.TestCase):
    def test_the_five_opening_quests_and_the_way_out_in_order(self):
        self.assertEqual([q.id for q in QUESTS], ["grand_tour", "meet_the_locals", "arcade_explorer", "earn_some_rewards",
                                                  "check_the_vending_machine", "the_way_out"])
        self.assertEqual([q.title for q in QUESTS], ["The Grand Tour", "Meet the Locals", "Give It a Try",
                                                     "Earn Your Rewards", "Check the Vending Machine", "The Way Out"])
        self.assertEqual(QUESTS[0].objective, "Follow Miao Meow and see the Arcade Floor.")
        self.assertEqual(QUESTS[1].objective, "Go to the Prize Plaza and meet Mochi.")
        self.assertEqual(QUESTS[5].objective, "Collect 3 Secret Items and complete 3 Secret Trials.")

    def test_every_quest_is_well_formed(self):
        ids = [q.id for q in QUESTS]
        self.assertEqual(len(ids), len(set(ids)))
        for q in QUESTS:
            self.assertTrue(q.hints, q.id)
            self.assertIn(q.trigger[0], ("played", "event", "sticky", "counters"))
            for h in q.hints:
                self.assertLess(len(h), 100, h)

    def test_kevin_is_never_named_anywhere_in_the_story_text(self):
        for text in all_text():
            self.assertNotIn("kevin", text.lower(), text)

    def test_hints_do_not_give_the_secret_code_away(self):
        hints = " ".join(h for q in QUESTS for h in q.hints).lower()
        for giveaway in ("up up", "down down", "left right", "konami", "b a", "uudd"):
            self.assertNotIn(giveaway, hints)

    def test_opening_dialogue_is_the_nycu_deadline_conversation_in_order(self):
        expected = [
            ("PLAYER", "...Ugh. Did I fall asleep?"),
            ("PLAYER", "Wait... wasn't I just at NYCU trying to finish my deadline?"),
            ("PLAYER", "Where's my laptop?"),
            ("PLAYER", "...And why am I in an ARCADE?!"),
            ("MIAO MEOW", "Meow?! You're awake!"),
            ("MIAO MEOW", "Wait! A human?! A real human?!"),
            ("MIAO MEOW", "Oh my gosh!! Hi!!!"),
            ("PLAYER", "...A talking cat?"),
            ("MIAO MEOW", "Yep! That's me!"),
            ("MIAO MEOW", "I'm Miao Meow! Nice to meet you!"),
            ("PLAYER", "Okay... either I'm dreaming, or that deadline finally broke my brain."),
            ("MIAO MEOW", "Hehe! I don't know what a deadline is, but it sounds scary!"),
            ("MIAO MEOW", "Anyway, welcome to Neon Corner Arcade!"),
            ("PLAYER", "Do you know how I get back?"),
            ("MIAO MEOW", "Um... no. Sorry..."),
            ("MIAO MEOW", "But we can figure it out together!"),
            ("MIAO MEOW", "Come on! I'll show you around!"),
        ]
        self.assertEqual([(l.speaker, l.text) for l in S.OPENING_LINES], expected)
        self.assertEqual(S.OPENING_LINES, S.OPENING_WAKE + S.OPENING_MEET)
        self.assertTrue(all(l.speaker == "PLAYER" for l in S.OPENING_WAKE))        # the student wakes up alone first
        self.assertEqual(S.OPENING_MEET[0].speaker, "MIAO MEOW")

    def test_miao_meow_is_friendly_and_nothing_hints_at_kevin_or_the_twist(self):
        for line in S.OPENING_LINES:
            for word in ("kevin", "twist", "villain", "trap", "secret"):
                self.assertNotIn(word, line.text.lower())

    def test_every_beat_points_at_a_real_line(self):
        sizes = {"wake": len(S.OPENING_WAKE), "meet": len(S.OPENING_MEET)}
        for (part, index), actions in S.BEATS.items():
            self.assertLess(index, sizes[part], (part, index))
            for action in actions:
                self.assertIn(action[0], ("bubble", "hop", "meow", "jingle", "look", "pose"))

    def test_every_dialogue_line_fits_the_box_in_three_rows(self):
        for line in list(S.OPENING_LINES) + [D.Line("MIAO MEOW", t) for q in QUESTS for t in q.hints] + \
                [D.Line("MIAO MEOW", t) for t, _ in S.GREETINGS + S.NO_QUEST_CHAT]:
            from ui import wrap_text
            self.assertLessEqual(len(wrap_text(line.text, D.TEXT_W)), D.MAX_LINES, line.text)


# ------------------------------------------------------------------ progress
class QuestProgressTests(unittest.TestCase):
    def test_nothing_progresses_before_the_opening_is_over(self):
        p = fresh()
        m = QuestManager(session_of(p))
        self.assertFalse(m.opening_done)
        play(m, "retro_racer", "neon21", "pinball")
        p.add_tickets(10)
        self.assertEqual(m.completed_ids, [])
        self.assertFalse(m.notifications)

    def test_finishing_the_opening_starts_quest_one_and_announces_it(self):
        p = fresh()
        m = QuestManager(session_of(p))
        self.assertTrue(m.finish_opening())
        self.assertEqual(m.active.id, "grand_tour")
        n = list(m.notifications)
        self.assertEqual([(x.kind, x.quest.id) for x in n], [("quest", "grand_tour")])
        self.assertFalse(m.finish_opening())                          # (idempotent)
        self.assertEqual(len(m.notifications), 1)

    def test_the_tour_conversations_complete_quests_one_and_two(self):
        p, m = finished(tour=False)
        play(m, "retro_racer")                                          # playing does not skip the tour
        self.assertEqual(m.completed_ids, [])
        m.handle("tour_arcade")
        self.assertEqual(m.completed_ids, ["grand_tour"])
        self.assertEqual(m.active.id, "meet_the_locals")
        self.assertEqual([(x.kind, x.quest.id) for x in m.notifications], [("quest", "meet_the_locals")])
        m.handle("met_mochi")
        self.assertEqual(m.completed_ids, ["grand_tour", "meet_the_locals"])
        self.assertEqual(m.active.id, "arcade_explorer")
        self.assertEqual(m.progress(), (1, 3))                          # the machine played earlier still counts

    def test_a_real_game_played_event_from_the_profile_counts(self):
        p, m = finished()
        p.record_game_played("neon21")
        self.assertEqual(m.state["stats"]["played"], ["neon21"])

    def test_arcade_explorer_needs_three_different_machines(self):
        p, m = finished()
        play(m, "a", "a", "a", "a")
        self.assertEqual(m.active.id, "arcade_explorer")
        self.assertEqual(m.progress(), (1, 3))
        play(m, "b")
        self.assertEqual(m.progress(), (2, 3))
        play(m, "c")
        self.assertEqual(m.active.id, "earn_some_rewards")

    def test_machines_played_before_the_quest_started_still_count(self):
        p, m = finished()
        play(m, "a", "b")                                              # quest one done by "a"; "b" is played during quest two
        self.assertEqual(m.progress(), (2, 3))

    def test_earning_tickets_completes_earn_some_rewards_but_refunds_do_not(self):
        p, m = finished(tickets=50)
        play(m, "a", "b", "c")
        self.assertEqual(m.active.id, "earn_some_rewards")
        p.spend_tickets(10)
        p.refund_tickets(10)                                           # getting a purchase refunded is not earning
        self.assertEqual(m.active.id, "earn_some_rewards")
        p.add_tickets(5)
        self.assertEqual(m.active.id, "check_the_vending_machine")

    def test_tickets_won_before_quest_three_do_not_complete_it_early(self):
        p, m = finished()
        p.add_tickets(5)
        self.assertEqual(m.active.id, "arcade_explorer")
        play(m, "a", "b", "c")
        self.assertEqual(m.active.id, "earn_some_rewards")             # the player still gets to earn them

    def test_tokens_alone_never_count_as_rewards(self):
        p, m = finished()
        play(m, "a", "b", "c")
        p.add_tokens(10, "DAILY")
        self.assertEqual(m.active.id, "earn_some_rewards")

    def test_the_vending_event_completes_quest_four_and_opens_the_way_out(self):
        p, m = finished()
        play(m, "a", "b", "c")
        p.add_tickets(5)
        m.notifications.clear()
        m.handle("vending_secret")
        self.assertEqual(m.active.id, "the_way_out")
        kinds = [(x.kind, x.quest.id if x.quest else None) for x in m.notifications]
        self.assertEqual(kinds, [("protocol", None), ("quest", "the_way_out")])
        self.assertEqual(list(m.notifications)[0].lines,
                         ("LEGACY PROTOCOL ACTIVE", "3 SECRET ITEMS REQUIRED", "3 SECRET TRIALS REQUIRED"))
        self.assertTrue(m.protocol_active)

    def test_finding_the_secret_early_is_remembered_and_not_lost(self):
        p, m = finished()
        m.handle("vending_secret")                                     # long before quest five
        self.assertEqual(m.active.id, "arcade_explorer")
        play(m, "a", "b", "c")
        p.add_tickets(5)
        self.assertEqual(m.active.id, "the_way_out")                   # quest four completes the moment it is reached

    def test_the_way_out_tracks_secret_items_and_trials_without_new_levels(self):
        p, m = finished()
        play(m, "a", "b", "c")
        p.add_tickets(5)
        m.handle("vending_secret")
        self.assertEqual((m.secret_items, m.secret_trials), (0, 0))
        m.handle("secret_item_found", "gem_cyan")
        m.handle("secret_item_found", "gem_cyan")                      # the same item twice counts once
        m.handle("secret_item_found", "gem_pink")
        m.handle("secret_trial_done", "trial_1")
        self.assertEqual((m.secret_items, m.secret_trials), (2, 1))
        self.assertEqual(m.progress(), (3, 6))
        self.assertEqual(m.active.id, "the_way_out")
        m.handle("secret_item_found", "gem_gold")
        m.handle("secret_trial_done", "trial_2")
        m.handle("secret_trial_done", "trial_3")
        self.assertEqual(m.active, None)                               # all three and three: the story's current end
        self.assertEqual(m.completed_ids[-1], "the_way_out")

    def test_session_events_reach_the_manager(self):
        p, m = finished()
        session = m.session
        session.dispatch(GameEvent("vending_secret", "a"))
        self.assertTrue(m.state["flags"]["vending_secret"])
        session.dispatch(GameEvent("secret_item_found", "a", key="x"))
        self.assertEqual(m.counter("secret_items"), 1)

    def test_no_quest_goes_twice_and_a_finished_quest_never_rewards_again(self):
        quests = (QuestDef("one", "One", "Do one.", "DO ONE", ("played", 1), ("h",), reward_tokens=3),
                  QuestDef("two", "Two", "Do two.", "DO TWO", ("played", 2), ("h",), reward_tokens=4))
        p = fresh(tokens=10)
        m = QuestManager(session_of(p), quests)
        m.finish_opening()
        play(m, "a")
        self.assertEqual(p.tokens, 13)
        play(m, "a", "a")
        self.assertEqual(p.tokens, 13)
        self.assertEqual(m.completed_ids, ["one"])
        play(m, "b")
        self.assertEqual(p.tokens, 17)
        play(m, "b", "c")
        self.assertEqual(p.tokens, 17)
        m.close()
        again = QuestManager(session_of(p), quests)                    # a restart does not pay again either
        play(again, "a", "b")
        self.assertEqual(p.tokens, 17)
        self.assertEqual(again.completed_ids, ["one", "two"])

    def test_the_whole_story_can_be_finished_with_only_normal_play(self):
        """No step needs anything the player cannot always do: no dead end."""
        p, m = finished()
        for g in ("a", "b", "c"):
            p.record_game_played(g)
        p.add_tickets(8)
        m.handle("vending_secret")
        for i in range(3):
            m.handle("secret_item_found", f"i{i}")
            m.handle("secret_trial_done", f"t{i}")
        self.assertIsNone(m.active)

    def test_the_hud_text_follows_progress(self):
        p, m = finished()
        self.assertEqual(m.hud_text(), "TRY 3 MACHINES ON THE ARCADE FLOOR 0/3")
        play(m, "a")
        self.assertEqual(m.hud_text(), "TRY 3 MACHINES ON THE ARCADE FLOOR 1/3")


# ------------------------------------------------------------------ hints
class HintTests(unittest.TestCase):
    def test_hints_are_asked_for_one_tier_at_a_time_and_cap_at_the_last(self):
        p, m = finished()
        play(m, "a", "b", "c")
        p.add_tickets(5)
        q = m.active
        self.assertEqual(q.id, "check_the_vending_machine")
        self.assertEqual(m.current_hint(), q.hints[0])
        self.assertEqual(m.current_hint(), q.hints[0])                 # looking does not advance
        got = [m.take_hint() for _ in range(5)]
        self.assertEqual(got[:3], list(q.hints))
        self.assertEqual(got[3:], [q.hints[-1]] * 2)

    def test_the_hint_changes_with_story_progress(self):
        p, m = finished()
        first = m.take_hint()
        play(m, "a")
        play(m, "b", "c")                                              # the quest moves on to earning Tickets
        second = m.take_hint()
        self.assertNotEqual(first, second)
        self.assertEqual(second, QUESTS[3].hints[0])

    def test_no_hint_pops_up_by_itself(self):
        p, m = finished()
        before = dict(m.state.get("hints", {}))
        for _ in range(60 * 30):
            pass
        self.assertEqual(m.state.get("hints", {}), before)
        self.assertFalse(m.notifications)

    def test_hint_progress_is_saved(self):
        p, m = finished()
        m.take_hint()
        self.assertEqual(p.story["hints"], {"arcade_explorer": 1})


# ------------------------------------------------------------------ saving, sharing, old saves
class StorySaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "p.json")

    def reload(self, profile):
        ProfileStore(self.path).save(profile)
        return ProfileStore(self.path).load()

    def test_progress_is_written_into_the_profile_and_survives_a_restart(self):
        p = fresh()
        store = ProfileStore(self.path)
        store.autosave(p)
        m = QuestManager(session_of(p))
        m.finish_opening()
        m.handle("tour_arcade")
        m.handle("met_mochi")
        play(m, "a")
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(data["story"]["opening_done"])
        self.assertEqual(data["story"]["completed"], ["grand_tour", "meet_the_locals"])
        self.assertTrue(data["story"]["flags"]["tour_arcade"])
        loaded = ProfileStore(self.path).load()
        m2 = QuestManager(session_of(loaded))
        self.assertTrue(m2.opening_done)
        self.assertEqual(m2.active.id, "arcade_explorer")
        self.assertEqual(m2.progress(), (1, 3))
        self.assertFalse(m2.notifications)                              # nothing is re-announced after a restart

    def test_secret_counters_and_flags_survive(self):
        p, m = finished()
        m.handle("vending_secret")
        m.handle("secret_item_found", "x")
        loaded = self.reload(p)
        m2 = QuestManager(session_of(loaded))
        self.assertTrue(m2.state["flags"]["vending_secret"])
        self.assertEqual(m2.secret_items, 1)

    def test_a_save_without_a_story_loads_and_money_is_untouched(self):
        raw = {"version": 2, "tokens": 17, "tickets": 33, "total_games_played": 0, "lifetime_tickets_earned": 0}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(raw, f)
        p = ProfileStore(self.path).load()
        self.assertEqual((p.tokens, p.tickets), (17, 33))
        self.assertEqual(p.story, {})
        m = QuestManager(session_of(p))
        self.assertFalse(m.opening_done)                                # a profile that never played gets the opening
        self.assertEqual((p.tokens, p.tickets), (17, 33))

    def test_the_story_never_changes_tokens_or_tickets(self):
        p = fresh(tokens=12, tickets=7)
        before = (p.tokens, p.tickets, p.lifetime_tickets_earned, p.lifetime_tokens_earned)
        m = QuestManager(session_of(p))
        m.finish_opening()
        m.take_hint()
        play(m, "a", "b", "c")
        self.assertEqual((p.tokens, p.tickets, p.lifetime_tickets_earned, p.lifetime_tokens_earned), before)

    def test_damaged_story_data_is_cleaned_not_fatal(self):
        for junk in ("text", 5, [1, 2], {"completed": "no", "active": 3, "progress": 7, "flags": {"x": 1, "y": True},
                                         "hints": {"a": -1, "b": "x", "c": 2}, "opening_done": "yes"}):
            story = clean_story(junk)
            self.assertIsInstance(story, dict)
        cleaned = clean_story({"completed": ["a", "a", 3, "b"], "flags": {"x": 1, "y": True}, "hints": {"a": -1, "c": 2},
                               "opening_done": True, "progress": {"q": {"n": 1, "bad": object()}}, "evil": 1})
        self.assertEqual(cleaned["completed"], ["a", "b"])
        self.assertEqual(cleaned["flags"], {"y": True})
        self.assertEqual(cleaned["hints"], {"c": 2})
        self.assertNotIn("evil", cleaned)
        self.assertEqual(cleaned["progress"], {"q": {"n": 1}})
        p = PlayerProfile.from_dict({"story": "garbage", "tokens": 3})
        self.assertEqual((p.tokens, p.story), (3, {}))

    def test_an_unknown_quest_id_in_a_save_does_not_break_the_story(self):
        p = fresh()
        p.set_story({"opening_done": True, "completed": ["gone_quest", "get_your_bearings"], "active": "gone_quest"})
        m = QuestManager(session_of(p))
        self.assertEqual(m.active.id, "arcade_explorer")
        self.assertEqual([q.id for q in m.completed], ["grand_tour", "meet_the_locals"])

    def test_set_story_saves_only_when_it_changes(self):
        p = fresh()
        saves = []
        p.subscribe_save(lambda: saves.append(1))
        story = {"opening_done": True}
        self.assertTrue(p.set_story(story))
        self.assertFalse(p.set_story(story))
        self.assertEqual(len(saves), 1)


class VeteranSaveTests(unittest.TestCase):
    """A profile saved before the story existed is a veteran: no opening, finished steps ticked, never stuck."""

    def test_a_profile_that_has_played_skips_the_opening(self):
        p = fresh(total_games_played=4)
        m = QuestManager(session_of(p))
        self.assertTrue(m.opening_done)
        self.assertFalse(m.notifications)

    def test_finished_steps_are_ticked_and_the_first_open_one_is_active(self):
        p = fresh(total_games_played=5, lifetime_tickets_earned=40)
        m = QuestManager(session_of(p))
        self.assertEqual(m.completed_ids, ["grand_tour", "meet_the_locals", "arcade_explorer", "earn_some_rewards"])
        self.assertEqual(m.active.id, "check_the_vending_machine")
        self.assertFalse(m.notifications)
        self.assertEqual(p.story["completed"], m.completed_ids)

    def test_a_veteran_who_already_found_the_vending_secret_starts_at_the_way_out(self):
        p = fresh(total_games_played=9, lifetime_tickets_earned=90, secrets={SECRET_FLAG: True})
        m = QuestManager(session_of(p))
        self.assertEqual(m.active.id, "the_way_out")
        self.assertTrue(m.protocol_active)

    def test_a_veteran_with_gaps_is_not_stuck(self):
        p = fresh(total_games_played=1)
        m = QuestManager(session_of(p))
        self.assertEqual(m.active.id, "arcade_explorer")
        play(m, "a", "b", "c")
        p.add_tickets(5)
        m.handle("vending_secret")
        self.assertEqual(m.active.id, "the_way_out")

    def test_a_brand_new_profile_is_not_a_veteran(self):
        m = QuestManager(session_of(fresh()))
        self.assertFalse(m.opening_done)


class ProfileOwnedStoryTests(unittest.TestCase):
    """The main quest belongs to the profile being played; other saved profiles are never read or written."""

    def test_the_story_is_saved_in_the_playing_profile_only(self):
        a, b = fresh("a"), fresh("b")
        m = QuestManager(session_of(a))
        m.finish_opening()
        m.handle("tour_arcade")
        play(m, "x")
        self.assertEqual(a.story["completed"], ["grand_tour"])
        self.assertEqual(b.story, {})

    def test_the_players_own_actions_move_the_quest(self):
        a, b = fresh("a"), fresh("b")
        m = QuestManager(session_of(a))
        m.finish_opening()
        m.handle("tour_arcade")
        m.handle("met_mochi")
        a.record_game_played("one")
        b.record_game_played("two")                       # another saved profile's play means nothing here
        self.assertEqual(m.progress(), (1, 3))
        a.record_game_played("two")
        self.assertEqual(m.progress(), (2, 3))
        a.add_tickets(5)
        a.record_game_played("three")
        a.add_tickets(5)
        self.assertEqual(m.active.id, "check_the_vending_machine")
        self.assertEqual(b.story, {})

    def test_an_advanced_profile_skips_the_opening_and_a_new_one_still_gets_it(self):
        a = fresh("a", total_games_played=6, lifetime_tickets_earned=30)
        b = fresh("b")
        m = QuestManager(session_of(a))
        self.assertTrue(m.opening_done)
        self.assertEqual(m.active.id, "check_the_vending_machine")
        self.assertFalse(QuestManager(session_of(b)).opening_done)
        self.assertEqual(b.story.get("opening_done", False), False)

    def test_two_saves_that_drifted_apart_are_each_kept_exactly_as_they_are(self):
        """The old two-player game wrote one shared story into both saves; a profile now keeps its own copy."""
        a, b = fresh("a"), fresh("b")
        a.set_story({"opening_done": True, "completed": ["grand_tour"], "stats": {"played": ["x"]}})
        b.set_story({"opening_done": True, "completed": ["grand_tour", "meet_the_locals", "arcade_explorer"],
                     "stats": {"played": ["y", "z"]}, "flags": {"vending_secret": True}})
        before_a, before_b = a.story, b.story
        ma = QuestManager(session_of(a))
        self.assertEqual(ma.completed_ids, ["grand_tour"])
        self.assertNotIn("vending_secret", ma.state.get("flags", {}))
        self.assertEqual(ma.state["stats"]["played"], ["x"])
        self.assertEqual(b.story, before_b)               # never touched while A is played
        mb = QuestManager(session_of(b))
        self.assertEqual(mb.completed_ids[:3], ["grand_tour", "meet_the_locals", "arcade_explorer"])
        self.assertTrue(mb.state["flags"]["vending_secret"])
        self.assertEqual(sorted(mb.state["stats"]["played"]), ["y", "z"])
        self.assertEqual(a.story, before_a)

    def test_ticket_gains_count_once(self):
        a = fresh("a")
        m = QuestManager(session_of(a))
        m.finish_opening()
        m.handle("tour_arcade")
        m.handle("met_mochi")
        play(m, "x", "y", "z")
        a.add_tickets(3)
        self.assertEqual(m.active.id, "check_the_vending_machine")

    def test_merge_stories_no_longer_exists(self):
        import quests
        self.assertFalse(hasattr(quests, "merge_stories"))


# ------------------------------------------------------------------ the dialogue box
class DialogueTests(unittest.TestCase):
    def make(self, lines=None, **kw):
        self.done = []
        self.sounds = []
        lines = lines or [D.Line("MIAO MEOW", "Hello there!", "happy"), D.Line("PLAYER", "Hi."), D.Line("MIAO MEOW", "Bye.")]
        return D.StoryDialogue(lines, {"players": []}, on_done=lambda: self.done.append(1), play_sound=self.sounds.append, **kw)

    def type_out(self, d):
        for _ in range(int(len(d.line.text) / D.CPS / DT) + 30):
            d.update(DT)

    def test_text_is_typed_a_letter_at_a_time(self):
        d = self.make()
        self.assertEqual(int(d.shown), 0)
        d.update(0.1)
        self.assertTrue(0 < int(d.shown) < len(d.line.text))
        self.type_out(d)
        self.assertTrue(d.done_typing)

    def test_confirm_finishes_the_line_then_goes_on_then_closes_once(self):
        d = self.make()
        d.update(DT)
        for key in D.CONFIRM_KEYS:
            self.assertIn(key, (K.K_e, K.K_RETURN, K.K_KP_ENTER, K.K_SPACE))
        d.handle_event(down(K.K_SPACE))                                # first press: the rest of the line appears at once
        self.assertTrue(d.done_typing)
        self.assertEqual(d.index, 0)
        d.handle_event(down(K.K_SPACE))                                # second: the next line
        self.assertEqual((d.index, int(d.shown)), (1, 0))
        self.type_out(d)
        d.handle_event(down(K.K_RETURN))
        self.type_out(d)
        d.handle_event(down(K.K_e))
        self.assertTrue(d.closed)
        self.assertEqual(self.done, [1])
        d.handle_event(down(K.K_e))
        self.assertEqual(self.done, [1])                                # (never twice)

    def test_other_keys_do_nothing(self):
        d = self.make()
        d.update(0.1)
        shown = d.shown
        for key in (K.K_w, K.K_ESCAPE, K.K_q, K.K_i, K.K_t):
            d.handle_event(down(key))
        self.assertEqual((d.index, d.shown, d.closed), (0, shown, False))
        d.handle_event(up(K.K_e))
        self.assertEqual(d.index, 0)

    def test_a_soft_blip_plays_while_typing_not_on_spaces_or_when_finished(self):
        d = self.make([D.Line("MIAO MEOW", "Hello there, friend of mine!")])
        self.type_out(d)
        self.assertGreater(len(self.sounds), 2)
        self.assertEqual(set(self.sounds), {"vend_select"})
        n = len(self.sounds)
        for _ in range(60):
            d.update(DT)
        self.assertEqual(len(self.sounds), n)

    def test_it_supports_many_lines_in_order_and_remembers_the_speaker(self):
        d = self.make()
        names = []
        for _ in range(3):
            names.append(d.speaker.name)
            self.type_out(d)
            d.handle_event(down(K.K_e))
        self.assertEqual(names, ["MIAO MEOW", "PLAYER", "MIAO MEOW"])

    def test_a_new_speaker_and_new_expression_are_one_registration(self):
        faces = []

        def portrait(mood, ctx):
            faces.append(mood)
            return D.framed_portrait(pygame.Surface((10, 10)), 2)
        D.register_speaker("TESTER", D.Speaker("TESTER", (1, 2, 3), portrait))
        self.addCleanup(D.SPEAKERS.pop, "TESTER", None)
        d = self.make([D.Line("TESTER", "Hi", "grumpy")])
        d.draw(pygame.Surface((400, 300)))
        self.assertEqual(faces, ["grumpy"])
        self.assertEqual(d.speaker.name, "TESTER")

    def test_an_unknown_speaker_still_draws_without_a_portrait(self):
        d = self.make([D.Line("STRANGER", "Who am I?")])
        d.draw(pygame.Surface((400, 300)))
        self.assertEqual(d.speaker.name, "STRANGER")

    def test_unknown_mood_falls_back_to_the_normal_face(self):
        self.assertEqual(D.miao_portrait("moody").get_size(), (44, 44))
        self.assertIs(D.miao_portrait("moody"), D.miao_portrait("normal"))

    def test_moods_have_different_faces(self):
        faces = {m: pygame.image.tobytes(D.miao_portrait(m), "RGBA") for m in ("normal", "happy", "surprised", "gentle")}
        self.assertEqual(len(set(faces.values())), 4)

    def test_it_draws_inside_the_canvas_and_clear_of_the_corner_hud(self):
        self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(D.BOX))
        d = self.make()
        self.type_out(d)
        surf = pygame.Surface((400, 300))
        surf.fill((1, 2, 3))
        d.draw(surf)
        self.assertEqual(surf.get_at((200, 100))[:3], (1, 2, 3))        # nothing above the box except the portrait
        self.assertTrue(d.hides_hud)                                    # the room hides its HUD while it is open

    def test_story_panels_are_opaque_so_the_room_never_shows_through_the_text(self):
        for panel in (D.solid_panel(120, 40), D.StoryDialogue._panel()):
            w, h = panel.get_size()
            for y in range(3, h - 3):
                for x in (4, w // 2, w - 5):
                    self.assertEqual(panel.get_at((x, y))[3], 255, (x, y))

    def test_the_box_can_sit_on_top_and_still_draws_everything_inside_the_canvas(self):
        d = self.make(top=True)
        self.type_out(d)
        surf = pygame.Surface((400, 300), pygame.SRCALPHA)
        d.draw(surf)
        bounds = surf.get_bounding_rect()
        self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(bounds))
        self.assertLess(bounds.bottom, 120)                              # all of it up in the top part of the screen
        self.assertEqual(d.box, D.BOX_TOP)
        bottom = self.make()
        self.assertEqual(bottom.box, D.BOX)

    def test_a_dialogue_needs_lines(self):
        with self.assertRaises(ValueError):
            D.StoryDialogue([])

    def test_a_dialogue_takes_no_extra_players(self):
        self.assertFalse(hasattr(self.make(), "extra_players"))
        with self.assertRaises(TypeError):
            self.make(extra_players=["p2"])


# ------------------------------------------------------------------ the quest screens
class QuestUITests(unittest.TestCase):
    def setUp(self):
        self.p = fresh(tokens=15, tickets=42)
        self.game = Game(session=session_of(self.p))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.claim()
        self.story = self.game.hub.story
        self.story.manager.finish_opening()
        for _ in range(10):
            self.game.step([], DT)

    def claim(self):
        for pl in self.room.players:
            pl.profile.claim_daily_reward()
        self.room.popup = None

    def frames(self, n, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def test_q_opens_and_closes_the_log(self):
        self.assertIsNone(self.room.modal)
        self.frames(1, [down(K.K_q)])
        self.assertIsInstance(self.story.log, QuestLogUI)
        self.assertIs(self.room.modal, self.story.log)
        self.frames(2)
        self.frames(1, [down(K.K_q)])
        self.frames(2)
        self.assertIsNone(self.story.log)
        self.assertIsNone(self.room.modal)

    def test_esc_also_closes_the_log(self):
        self.frames(1, [down(K.K_q)])
        self.frames(1, [down(K.K_ESCAPE)])
        self.frames(2)
        self.assertIsNone(self.story.log)

    def test_the_log_holds_the_player_still_and_hides_nothing_it_should_not(self):
        self.frames(1, [down(K.K_q)])
        p = self.room.player
        x, y = p.x, p.y
        self.frames(1, [down(K.K_d)])
        self.frames(60)
        self.assertEqual((p.x, p.y), (x, y))
        self.assertFalse(self.story.hides_hud)

    def test_q_is_nobodys_game_key(self):
        for scheme in (SOLO_CONTROLS,):
            self.assertFalse(scheme.owns(K.K_q), scheme.name)
        self.assertTrue(self.room.session.input.route(down(K.K_q)) == (None, None))

    def test_q_does_not_open_over_another_window(self):
        self.room.inventory_ui = object()                              # any open window
        self.room.popup = None
        self.assertIsNotNone(self.room.modal)
        self.story.toggle_log(self.room)
        self.assertIsNone(self.story.log)
        self.room.inventory_ui = None

    def test_q_does_not_interfere_with_the_other_controls(self):
        p = self.room.player
        for key in (K.K_w, K.K_a, K.K_s, K.K_d, K.K_e, K.K_i, K.K_t):
            self.assertIs(self.room.session.input.route(down(key))[0].avatar, p, key)

    def test_the_log_draws_in_every_state_and_shows_the_numbers(self):
        m = self.story.manager
        surf = pygame.Surface((400, 300))
        states = [lambda: None, lambda: play(m, "a"), lambda: play(m, "b", "c"), lambda: self.p.add_tickets(5),
                  lambda: m.handle("vending_secret"), lambda: m.handle("secret_item_found", "i1"),
                  lambda: m.handle("secret_trial_done", "t1")]
        for step in states:
            step()
            log = QuestLogUI(m, self.p)
            log.draw(surf)
        self.assertEqual((m.secret_items, m.secret_trials), (1, 1))

    def test_the_log_reads_but_never_changes_the_story(self):
        m = self.story.manager
        before = json.dumps(m.state, sort_keys=True)
        log = QuestLogUI(m, self.p)
        for _ in range(5):
            log.update(DT)
            log.draw(pygame.Surface((400, 300)))
        self.assertEqual(json.dumps(m.state, sort_keys=True), before)

    def test_the_tracker_sits_above_the_wallet_and_clear_of_the_controls_and_player_info(self):
        surf = pygame.Surface((400, 300))
        self.frames(90)
        self.room.draw(surf)
        tracker = self.story.tracker.rect(self.room, animated=False)
        self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(tracker))
        for hud in self.room.huds:
            self.assertFalse(tracker.colliderect(hud.rect), "the wallet box")
        box = self.room.instructions.image.get_rect(bottomleft=(4, 296))
        self.assertFalse(tracker.colliderect(box), "the controls box")

    def test_the_tracker_shows_the_current_objective_and_nothing_before_the_opening(self):
        fresh_game = Game(session=session_of(fresh("z")))
        self.addCleanup(fresh_game.quit)
        room = goto_room(fresh_game, "home")
        for _ in range(5):
            fresh_game.step([], DT)
        t = fresh_game.hub.story.tracker
        t.update(1.0)
        self.assertEqual(t.appear, 0.0)
        self.story.tracker.update(1.0)
        self.assertEqual(self.story.tracker.appear, 1.0)
        self.assertIsNotNone(room)

    def test_the_tracker_pulses_when_the_objective_changes(self):
        t = self.story.tracker
        t.update(1.5)
        self.assertEqual(t.pulse, 0.0)
        play(self.story.manager, "a")
        self.assertGreater(t.pulse, 0.0)
        t.update(1.5)
        self.assertEqual(t.pulse, 0.0)

    def test_the_tracker_is_not_drawn_while_the_dialogue_is_open(self):
        self.story.open_dialogue(self.room, self.room.player, [D.Line("MIAO MEOW", "Hi")])
        self.assertTrue(self.story.hides_hud)

    def test_banner_slides_in_holds_and_leaves(self):
        b = QuestBanner()
        b.push(Notification("quest", QUESTS[0]))
        b.update(DT)
        surf = pygame.Surface((400, 300), pygame.SRCALPHA)
        ys = []
        for i in range(int((QuestBanner.SLIDE * 2 + QuestBanner.HOLD["quest"]) / DT) + 5):
            b.update(DT)
            surf.fill((0, 0, 0, 0))
            b.draw(surf)
            box = surf.get_bounding_rect()
            ys.append(box.top if box.h else None)
        shown = [y for y in ys if y is not None]
        self.assertTrue(shown)
        self.assertLessEqual(max(box for box in shown), 8)             # it comes from the top edge
        self.assertIsNone(ys[-1])
        self.assertFalse(b.busy)

    def test_banners_come_one_after_another_and_hold_back_for_an_open_window(self):
        m = self.story.manager
        m.notifications.append(Notification("quest", QUESTS[1]))
        m.notifications.append(Notification("protocol", lines=Q.PROTOCOL_LINES))
        self.room.inventory_ui = type("W", (), {"update": lambda s, dt: None, "closed": False, "draw": lambda s, x: None})()
        self.frames(30)
        self.assertEqual(len(m.notifications), 2)                       # waits while a window is open
        self.room.inventory_ui = None
        self.frames(5)
        self.assertEqual(len(m.notifications), 0)
        self.assertTrue(self.story.banner.busy)
        for _ in range(int(14 / DT)):
            self.game.step([], DT)
            self.room.draw(pygame.Surface((400, 300)))
        self.assertFalse(self.story.banner.busy)

    def test_protocol_banner_has_the_three_lines(self):
        b = QuestBanner()
        n = Notification("protocol", lines=Q.PROTOCOL_LINES)
        img = b._make(n)
        self.assertGreater(img.get_width(), 100)
        self.assertEqual(Q.PROTOCOL_LINES, ("LEGACY PROTOCOL ACTIVE", "3 SECRET ITEMS REQUIRED", "3 SECRET TRIALS REQUIRED"))

    def test_the_new_quest_banner_shows_the_title_and_the_objective(self):
        b = QuestBanner()
        img = b._make(Notification("quest", QUESTS[0]))
        self.assertGreater(img.get_width(), 200)

    def test_everything_draws_with_the_log_the_banner_and_the_tracker_in_the_room(self):
        a = fresh("a")
        game = Game(session=session_of(a))
        self.addCleanup(game.quit)
        room = goto_room(game, "home")
        for pl in room.players:
            pl.profile.claim_daily_reward()
        room.popup = None
        story = game.hub.story
        story.manager.finish_opening()
        for _ in range(60):
            game.step([], DT)
        surf = pygame.Surface((400, 300))
        room.draw(surf)
        tracker = story.tracker.rect(room, animated=False)
        for hud in room.huds:
            self.assertFalse(tracker.colliderect(hud.rect))
        game.step([down(K.K_q)], DT)
        room.draw(surf)
        self.assertIsNotNone(story.log)


# ------------------------------------------------------------------ talking to Miao Meow
class ChatTests(unittest.TestCase):
    def setUp(self):
        self.p = fresh()
        self.game = Game(session=session_of(self.p))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "home")
        self.p.claim_daily_reward()
        self.room.popup = None
        self.story = self.game.hub.story
        self.story.manager.finish_opening()
        self.story.brain.place("home", mm.SPOTS["home"]["hub"])
        self.story.brain.idle_left = 999
        for _ in range(30):
            self.game.step([], DT)

    def talk(self):
        p = self.room.player
        p.x, p.y = self.story.brain.x + 14, self.story.brain.y + 6
        for _ in range(30):
            self.game.step([], DT)
        self.game.step([down(K.K_e)], DT)
        for _ in range(60):
            self.game.step([], DT)
        d = self.story.dialogue
        self.assertIsNotNone(d)
        texts = []
        while self.story.dialogue is not None:
            for _ in range(120):
                self.game.step([], DT)
            texts.append(self.story.dialogue.line.text if self.story.dialogue else None)
            self.game.step([down(K.K_e)], DT)
            self.game.step([down(K.K_e)], DT)
        for _ in range(5):
            self.game.step([], DT)
        return d

    def test_talking_gives_a_greeting_and_the_current_hint(self):
        d = self.talk()
        self.assertEqual(len(d.lines), 2)
        self.assertEqual(d.lines[1].text, QUESTS[0].hints[0])
        self.assertTrue(all(l.speaker == "MIAO MEOW" for l in d.lines))

    def test_asking_again_gets_a_little_more_help_and_the_conversation_ends_cleanly(self):
        first = self.talk()
        self.assertNotEqual(self.story.brain.state, "talk")
        self.assertIsNone(self.room.modal)
        second = self.talk()
        self.assertEqual(second.lines[1].text, QUESTS[0].hints[1])
        self.assertNotEqual(first.lines[0].text, second.lines[0].text)

    def test_the_hint_follows_the_story(self):
        self.story.manager.handle("tour_arcade")
        self.assertEqual(self.talk().lines[1].text, QUESTS[1].hints[0])

    def test_the_box_goes_to_the_top_when_the_speakers_stand_low_and_stays_below_otherwise(self):
        p = self.room.player
        b = self.story.brain
        p.y = 150.0
        b.place("home", (186, 150))
        self.assertFalse(self.story.open_dialogue(self.room, p, [D.Line("MIAO MEOW", "Hi")]).top)
        self.story.dialogue = None
        p.y = 250.0
        self.assertTrue(self.story.open_dialogue(self.room, p, [D.Line("MIAO MEOW", "Hi")]).top)
        self.story.dialogue = None
        p.y = 150.0
        b.place("home", (186, 250))                                     # she is the low one
        self.assertTrue(self.story.open_dialogue(self.room, p, [D.Line("MIAO MEOW", "Hi")]).top)

    def test_prompts_keep_clear_of_the_objective_tracker(self):
        self.game.step([], DT)
        self.story.tracker.update(1.0)
        rects = self.room.prompt_avoid_rects()
        self.assertIn(self.story.tracker.rect(self.room, animated=False), rects)

    def test_talking_never_starts_by_itself(self):
        for _ in range(60 * 60):
            self.game.step([], DT)
        self.assertIsNone(self.story.dialogue)
        self.assertEqual(self.story.manager.state.get("hints", {}), {})

    def test_once_every_quest_is_done_she_just_chats(self):
        m = self.story.manager
        play(m, "a", "b", "c")
        self.p.add_tickets(5)
        m.handle("vending_secret")
        for i in range(3):
            m.handle("secret_item_found", f"i{i}")
            m.handle("secret_trial_done", f"t{i}")
        d = self.talk()
        self.assertEqual(len(d.lines), 2)

    def test_she_will_not_start_a_chat_over_the_open_quest_log_and_the_dialogue_hides_the_hud(self):
        self.game.step([down(K.K_q)], DT)
        self.assertIsNotNone(self.story.log)
        self.story.talk_to_miao(self.room, self.room.player)
        self.assertIsNone(self.story.dialogue)                         # (the log is a modal: one window at a time)
        self.game.step([down(K.K_q)], DT)
        self.game.step([], DT)
        self.assertIsNone(self.story.log)
        self.story.talk_to_miao(self.room, self.room.player)
        self.assertIsNotNone(self.story.dialogue)
        self.assertTrue(self.story.hides_hud)


# ------------------------------------------------------------------ the vending machine secret
class VendingStoryTests(unittest.TestCase):
    def setUp(self):
        self.p = fresh(tickets=100)
        self.p.set_story({"opening_done": True, "completed": ["get_your_bearings", "arcade_explorer", "earn_some_rewards"]})
        self.game = Game(session=session_of(self.p))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.room = goto_room(self.game, "arcade_floor")
        for _ in range(10):
            self.game.step([], DT)
        self.assertEqual(self.story.manager.active.id, "check_the_vending_machine")

    def frames(self, n, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def open_shop(self):
        self.room.acting_player = self.room.players[0]
        self.room.open_vending()
        self.room.acting_player = None
        self.frames(90)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, VendingScene)
        return scene

    def tap(self, k):
        self.frames(1, [down(k)])
        self.frames(1, [up(k)])

    def test_opening_the_ordinary_shop_does_not_complete_the_quest(self):
        self.open_shop()
        self.assertEqual(self.story.manager.active.id, "check_the_vending_machine")
        self.assertNotIn("vending_secret", self.story.manager.state.get("flags", {}))

    def test_browsing_and_buying_do_not_complete_it(self):
        shop = self.open_shop()
        for k in (K.K_DOWN, K.K_RIGHT, K.K_UP, K.K_LEFT):
            self.tap(k)
        self.tap(K.K_e)                                                # buy something
        self.frames(120)
        self.assertEqual(self.story.manager.active.id, "check_the_vending_machine")
        self.assertIsNone(shop.secret)

    def test_a_wrong_or_half_finished_code_does_not_complete_it(self):
        shop = self.open_shop()
        for k in CLASSIC[:7] + [K.K_x, K.K_b, K.K_a]:
            self.tap(k)
        self.assertIsNone(shop.secret)
        for k in CLASSIC[:5]:
            self.tap(k)
        self.assertEqual(self.story.manager.active.id, "check_the_vending_machine")

    def test_only_the_real_secret_screen_completes_it_and_opens_the_way_out(self):
        shop = self.open_shop()
        for k in CLASSIC:
            self.tap(k)
        self.assertIsNotNone(shop.secret)
        m = self.story.manager
        self.assertEqual(m.active.id, "the_way_out")
        self.assertTrue(self.p.has_secret(SECRET_FLAG))                 # the existing flag, set by the existing screen
        self.assertEqual([n.kind for n in m.notifications], ["protocol", "quest"])
        self.assertTrue(self.p.story["flags"]["vending_secret"])

    def test_the_announcement_waits_until_you_are_back_in_the_room(self):
        shop = self.open_shop()
        for k in CLASSIC:
            self.tap(k)
        self.frames(60 * 6)
        self.assertEqual(len(self.story.manager.notifications), 2)      # still queued: the room is not the scene on top
        self.frames(1, [down(K.K_ESCAPE)])
        self.frames(120)
        self.assertIs(self.game.scenes.current, self.room)
        for _ in range(8):
            self.game.step([], DT)
        self.assertEqual(len(self.story.manager.notifications), 0)
        self.assertTrue(self.story.banner.busy)

    def test_the_secret_is_not_reimplemented_the_existing_listener_is_used(self):
        shop = self.open_shop()
        from secret_input import SecretSequenceListener
        self.assertIsInstance(shop.listener, SecretSequenceListener)
        import quests
        with open(quests.__file__) as f:
            src = f.read()
        self.assertNotIn("K_UP", src)                                   # the quest system never reads keys itself

    def test_the_secret_counts_for_the_playing_profiles_story_only(self):
        a, b = fresh("a", tickets=100), fresh("b", tickets=100)
        story = {"opening_done": True, "completed": ["get_your_bearings", "arcade_explorer", "earn_some_rewards"]}
        a.set_story(story)
        b.set_story(story)
        game = Game(session=session_of(a))
        self.addCleanup(game.quit)
        room = goto_room(game, "arcade_floor")
        for _ in range(10):
            game.step([], DT)
        game.hub.story.manager.session.dispatch(GameEvent("vending_secret", "a"))
        self.assertEqual(game.hub.story.manager.active.id, "the_way_out")
        self.assertTrue(a.story["flags"]["vending_secret"])
        self.assertNotIn("vending_secret", b.story.get("flags", {}))           # b keeps the story it had
        self.assertIsNotNone(room)


# ------------------------------------------------------------------ the opening
class OpeningTests(unittest.TestCase):
    def start(self, profile=None, opening=True):
        profile = profile or fresh("new")
        self.profiles = (profile,)
        self.game = Game(session=session_of(profile), opening=opening)
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.room = self.game.scenes.current
        return self.game

    def frames(self, n, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def until(self, cond, seconds=30):
        for _ in range(int(seconds / DT)):
            self.game.step([], DT)
            if cond():
                return True
        return False

    def confirm_through(self, key=K.K_e, until_unlocked=True):
        """Press through every dialogue (the monologue, then the meeting) until control comes back."""
        guard = 0
        while (self.story.locked or self.story.dialogue is not None) and guard < 400:
            if self.story.dialogue is not None:
                self.frames(100)
                self.frames(1, [down(key)])
                self.frames(1, [down(key)])
            else:
                self.frames(10)
            guard += 1

    def test_it_does_not_play_unless_the_game_start_asks_for_it(self):
        self.start(opening=False)
        self.frames(60 * 12)
        self.assertIsNone(self.story.cutscene)
        self.assertFalse(self.story.locked)

    def test_a_new_profile_gets_the_opening_in_home_and_input_is_locked(self):
        self.start()
        self.assertEqual(self.room.room_id, "home")
        self.assertTrue(self.story.opening_pending)
        self.frames(30)
        self.assertIsNotNone(self.story.cutscene)
        self.assertTrue(self.story.locked)
        self.assertTrue(self.story.hides_hud)

    def test_the_stages_play_in_order_with_the_wake_up_monologue_before_miao_meow(self):
        self.start()
        stages = []
        def watch():
            c = self.story.cutscene
            if c and (not stages or stages[-1] != c.stage):
                stages.append(c.stage)
        spoke = []
        for _ in range(60 * 40):
            self.game.step([], DT)
            watch()
            d = self.story.dialogue
            if d is not None:
                if d.shown >= len(d.line.text) and (not spoke or spoke[-1] != (d.index, d.line.speaker, d.lines)):
                    spoke.append((d.index, d.line.speaker, d.lines))
                    self.game.step([down(K.K_e)], DT)
            if self.story.cutscene is None and stages:
                break
        self.assertEqual(stages, ["intro", "monologue", "approach", "talk"])
        speakers = [s for _, s, _ in spoke]
        self.assertEqual(speakers[:4], ["PLAYER"] * 4)                    # the student first, alone
        self.assertEqual(speakers[4], "MIAO MEOW")
        self.assertEqual(len(speakers), len(S.OPENING_LINES))

    def test_miao_meow_is_not_in_the_room_until_she_runs_in_through_the_door(self):
        self.start()
        self.assertTrue(self.until(lambda: self.story.dialogue is not None))
        self.assertFalse(self.story.brain.is_in("home"))                  # not there while the student wakes up
        self.confirm_through_monologue()
        b = self.story.brain
        self.assertEqual(self.story.cutscene.stage, "approach")
        self.assertTrue(b.is_in("home"))
        self.assertLess(b.x, 40)                                          # she appears at the left doorway ...
        self.assertTrue(self.until(lambda: self.story.cutscene.stage == "talk", 12))
        p = self.room.player
        self.assertLess(abs(b.x - (p.x - 30)), 6)                         # ... and stops beside the player

    def confirm_through_monologue(self):
        while self.story.cutscene.stage == "monologue":
            self.frames(100)
            self.frames(1, [down(K.K_e)])
            self.frames(1, [down(K.K_e)])

    def test_the_whole_opening_is_short_to_reach_the_first_line(self):
        self.start()
        t = 0.0
        while self.story.dialogue is None and t < 20:
            self.game.step([], DT)
            t += DT
        self.assertLess(t, 7.0)

    def test_players_stand_still_and_keys_do_nothing_until_it_ends(self):
        self.start()
        self.frames(30)
        p = self.room.player
        self.frames(1, [down(K.K_d), down(K.K_e), down(K.K_i), down(K.K_q), down(K.K_t)])
        pos = (p.x, p.y)
        self.frames(60 * 3)
        self.assertEqual((p.x, p.y), pos)
        self.assertEqual(p.held, [])
        self.assertIsNone(self.story.log)
        self.assertIsNone(self.room.inventory_ui)

    def test_the_scene_plays_above_the_dialogue_box_and_players_face_each_other(self):
        self.start()
        self.assertTrue(self.until(lambda: self.story.dialogue is not None))
        self.confirm_through_monologue()
        self.assertTrue(self.until(lambda: self.story.dialogue is not None and self.story.cutscene.stage == "talk", 12))
        p, b = self.room.player, self.story.brain
        self.assertLess(p.y, D.BOX.y - 20)
        self.assertEqual(b.side, "right")
        self.assertEqual(p.facing, "left")

    def test_confirming_through_both_conversations_unlocks_play_and_shows_the_first_quest(self):
        self.start()
        self.assertTrue(self.until(lambda: self.story.dialogue is not None))
        speakers = []
        guard = 0
        while (self.story.locked or self.story.dialogue is not None) and guard < 400:
            if self.story.dialogue is not None:
                speakers.append((self.story.dialogue.index, self.story.dialogue.line.speaker, self.story.dialogue.lines))
                self.frames(100)
                self.frames(1, [down(K.K_SPACE)])
                self.frames(1, [down(K.K_SPACE)])
            else:
                self.frames(10)
            guard += 1
        self.assertEqual([s for _, s, _ in speakers], [l.speaker for l in S.OPENING_LINES])
        self.frames(10)
        self.assertIsNone(self.story.cutscene)
        self.assertFalse(self.story.locked)
        m = self.story.manager
        self.assertTrue(m.opening_done)
        self.assertEqual(m.active.id, "grand_tour")
        self.assertIsNotNone(self.room.popup)                            # the daily bonus, held back for the opening
        self.frames(1, [down(K.K_e)])
        self.frames(120)
        self.assertIsNone(self.room.popup)
        self.frames(30)
        self.assertTrue(self.story.banner.busy)
        self.assertEqual(self.story.banner.current.quest.id, "grand_tour")

    def test_movement_works_again_after_the_opening(self):
        self.start()
        self.assertTrue(self.until(lambda: self.story.dialogue is not None))
        self.confirm_through()
        self.frames(10)
        if self.room.popup is not None:
            self.frames(1, [down(K.K_e)])
            self.frames(120)
        p = self.room.player
        x = p.x
        self.frames(1, [down(K.K_d)])
        self.frames(30)
        self.assertGreater(p.x, x)

    def test_miao_meow_goes_to_her_hub_spot_afterwards_and_stays_findable(self):
        self.start()
        self.assertTrue(self.until(lambda: self.story.dialogue is not None))
        self.confirm_through()
        self.frames(60 * 20)
        b = self.story.brain
        goal = mm.SPOTS["home"]["hub"]
        self.assertTrue(b.is_in("home"))
        self.assertLess(((b.x - goal[0]) ** 2 + (b.y - goal[1]) ** 2) ** 0.5, 3)

    def test_it_is_saved_the_moment_it_ends_and_never_plays_twice(self):
        profile = fresh("save")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "p.json")
        ProfileStore(path).autosave(profile)
        self.start(profile)
        self.assertTrue(self.until(lambda: self.story.dialogue is not None))
        self.confirm_through()
        with open(path, encoding="utf-8") as f:
            self.assertTrue(json.load(f)["story"]["opening_done"])
        self.game.quit()
        loaded = ProfileStore(path).load()
        again = Game(session=session_of(loaded), opening=True)
        self.addCleanup(again.quit)
        for _ in range(60 * 12):
            again.step([], DT)
        self.assertIsNone(again.hub.story.cutscene)
        self.assertFalse(again.hub.story.opening_pending)

    def test_a_veteran_profile_never_sees_it(self):
        self.start(fresh("old", total_games_played=7, lifetime_tickets_earned=20))
        self.frames(60 * 12)
        self.assertIsNone(self.story.cutscene)
        self.assertTrue(self.story.manager.opening_done)

    def test_the_daily_bonus_does_not_talk_over_the_opening(self):
        self.start()
        self.frames(60 * 5)
        self.assertIsNone(self.room.popup)
        self.assertTrue(self.until(lambda: self.story.dialogue is not None))
        self.assertIsNone(self.room.popup)

    def test_the_one_player_stands_still_and_either_confirm_key_advances_the_dialogue(self):
        self.start(fresh("a"))
        self.assertTrue(self.until(lambda: self.story.dialogue is not None))
        self.assertEqual(len(self.room.players), 1)
        pos = [(p.x, p.y) for p in self.room.players]
        self.frames(1, [down(K.K_d), down(K.K_RIGHT)])
        self.frames(30)
        self.assertEqual(pos, [(p.x, p.y) for p in self.room.players])
        self.frames(100)
        self.frames(1, [down(K.K_RETURN)])                              # ENTER confirms ...
        self.frames(1, [down(K.K_RETURN)])
        self.assertEqual(self.story.dialogue.index, 1)
        self.frames(100)
        self.frames(1, [down(K.K_e)])                                   # ... and so does E
        self.frames(1, [down(K.K_e)])
        self.assertEqual(self.story.dialogue.index, 2)
        self.frames(100)
        self.frames(1, [down(K.K_o)])                                   # the old second player's key does not
        self.frames(1, [down(K.K_o)])
        self.assertEqual(self.story.dialogue.index, 2)
        self.confirm_through(K.K_RETURN)
        self.frames(10)
        self.assertFalse(self.story.locked)
        self.assertTrue(self.profiles[0].story["opening_done"])

    def test_every_frame_of_the_opening_draws(self):
        self.start()
        surf = pygame.Surface((400, 300))
        for _ in range(60 * 7):
            self.game.step([], DT)
            self.game.scenes.draw(surf, pygame.Surface((800, 600)))
        self.assertIsNotNone(self.story.dialogue)

    def test_the_eyes_open_in_three_movements_and_the_cover_lifts(self):
        self.start()
        self.assertTrue(self.until(lambda: self.story.cutscene is not None, 3))
        c = self.story.cutscene
        surf = pygame.Surface((400, 300))
        def centre():
            self.room.draw(surf)
            return surf.get_at((200, 150))[:3]
        self.frames(10)
        self.assertEqual(centre(), (0, 0, 0))                            # black screen: the eyes are still shut
        self.assertTrue(self.until(lambda: c.clock >= 2.0))
        mid = self.room.player
        lids_half = int((1 - S.curve(S.OpeningCutscene.LIDS, c.clock)) * 150)
        self.assertTrue(0 < lids_half < 150)                             # first, only half open
        self.assertTrue(self.until(lambda: c.clock >= 2.55))
        self.assertGreater(int((1 - S.curve(S.OpeningCutscene.LIDS, c.clock)) * 150), lids_half)   # closing again
        self.assertTrue(self.until(lambda: c.clock >= 4.0))
        self.assertEqual(S.curve(S.OpeningCutscene.LIDS, c.clock), 1.0)  # wide open
        self.assertTrue(self.until(lambda: c.clock >= 5.1))
        self.assertNotEqual(centre(), (4, 2, 12))
        self.assertIsNotNone(mid)


# ------------------------------------------------------------------ opening: sound and picture on one timeline
class OpeningSyncTests(unittest.TestCase):
    """The intro's sounds, flicker, eyelids and ambience all hang on one clock; these tests read a trace, not a screenshot."""

    EXPECT = ["hum", "beep", "eyes_open_1", "eyes_close", "eyes_open_2", "neon_1", "neon_2", "neon_3", "neon_steady", "intro_end"]

    def start(self, dt, lag=None):
        p = fresh("sync")
        self.game = Game(session=session_of(p), opening=True)
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.played = []
        real = self.game.audio.play
        self.game.audio.play = lambda name, volume=1.0: (self.played.append((name, volume)), real(name, volume))[1]
        self.dt = dt
        for _ in range(int(0.6 / DT)):
            self.game.step([], DT)
        self.assertIsNotNone(self.story.cutscene)
        self.cut = self.story.cutscene
        return self.cut

    def run_clock(self, until, dt):
        guard = 0
        while self.cut.clock < until and guard < 20000 and self.story.cutscene is self.cut:
            self.game.step([], dt)
            guard += 1

    def test_every_event_fires_once_in_order_at_its_time(self):
        cut = self.start(DT)
        self.run_clock(5.0, DT)
        names = [n for n, _, _ in cut.trace]
        self.assertEqual(names, self.EXPECT)
        for name, scheduled, actual in cut.trace:
            self.assertGreaterEqual(actual, scheduled, name)               # never early
            self.assertLessEqual(actual - scheduled, DT + 1e-9, name)      # and at most one frame late

    def test_the_same_trace_at_other_frame_rates_and_through_a_hitch(self):
        for dt in (1 / 30, 1 / 120):
            cut = self.start(dt)
            self.run_clock(5.0, dt)
            self.assertEqual([n for n, _, _ in cut.trace], self.EXPECT, dt)
            for name, scheduled, actual in cut.trace:
                self.assertGreaterEqual(actual, scheduled)
                self.assertLessEqual(actual - scheduled, dt + 1e-9)
            self.game.quit()
        cut = self.start(DT)
        for step in (0.05, 0.05, 0.5, 0.05, 0.9, 0.05, 0.05):            # frame-time spikes: a long frame fires what it passed, in order
            self.game.step([], step)
        self.run_clock(5.0, DT)
        self.assertEqual([n for n, _, _ in cut.trace], self.EXPECT)
        times = [a for _, a, _ in cut.trace]
        self.assertEqual(times, sorted(times))

    def test_sounds_reach_the_audio_manager_with_the_events_and_never_repeat(self):
        cut = self.start(DT)
        self.run_clock(4.6, DT)
        intro = [(n, v) for n, v in self.played if v < 1.0 or n in ("vend_hum", "zap")]
        self.assertEqual([n for n, _ in intro], ["vend_hum", "vend_select", "emote", "vend_hum", "machine", "machine", "machine", "zap"])
        log = [e for e in self.story.sound_log if e[3]]
        self.assertEqual([e[3] for e in log], ["hum", "beep", "eyes_open_1", "eyes_open_2", "neon_1", "neon_2", "neon_3", "neon_steady"])
        times = [e[0] for e in log]
        self.assertEqual(times, sorted(times))
        for (clock, name, volume, event) in log:
            scheduled = dict((n, a) for n, a, _ in cut.trace)[event]
            self.assertLessEqual(abs(clock - scheduled), DT + 0.001, event)   # each sound is stamped with the time of its event

    def test_the_quiet_cues_never_jump_in_volume(self):
        cut = self.start(DT)
        self.run_clock(4.6, DT)
        for _, name, volume, event in self.story.sound_log:
            if event:
                self.assertLessEqual(volume, 0.4, event)
        loud = [v for n, v in self.played if n in ("machine", "zap", "vend_hum", "vend_select", "emote") and v < 1.0]
        self.assertLessEqual(max(loud), 0.35)

    def test_flicker_dips_line_up_with_the_electrical_sounds(self):
        cut = self.start(DT)
        cover = S.OpeningCutscene.COVER
        beep_at = dict((n, a) for a, n in S.OpeningCutscene.INTRO)
        for name in ("neon_1", "neon_2", "neon_3"):
            at = beep_at[name]
            before = S.curve(cover, at - 0.04)
            after = S.curve(cover, at + 0.02)
            self.assertLess(after, before - 40, name)                       # the screen brightens right as the sound plays
        beep = beep_at["beep"]
        self.assertLess(S.curve(cover, beep + 0.05), S.curve(cover, beep - 0.05))   # the first beep: a faint flicker

    def test_the_ambience_is_quiet_then_muffled_then_clear_and_the_music_follows(self):
        cut = self.start(DT)
        amb, duck = S.OpeningCutscene.AMBIENCE, S.OpeningCutscene.DUCK
        quiet, muffled, clear = S.curve(amb, 1.0), S.curve(amb, 2.8), S.curve(amb, 5.5)
        self.assertLess(muffled, quiet)                                     # eyes shut again: muffled
        self.assertGreater(clear, quiet)                                    # eyes open for good: clearer than ever
        self.assertEqual(clear, 1.0)
        self.assertLess(S.curve(duck, 2.8), S.curve(duck, 1.0))
        self.assertEqual(S.curve(duck, 5.5), 1.0)
        base = dict(self.room_mix())
        seen = {}
        for _ in range(int(5.6 / DT)):
            self.game.step([], DT)
            if self.cut.clock >= 1.0 and "q" not in seen:
                seen["q"] = max(self.game.hub.ambience.mix.values())
            if self.cut.clock >= 2.8 and "m" not in seen:
                seen["m"] = max(self.game.hub.ambience.mix.values())
            if self.story.cutscene is not self.cut:
                break
        self.assertLess(seen["m"], seen["q"])
        self.assertLess(seen["q"], max(base.values()))

    def room_mix(self):
        return self.game.scenes.current.ambience_mix

    def test_the_music_level_the_game_uses_follows_the_story(self):
        cut = self.start(DT)
        self.run_clock(2.8, DT)
        self.assertAlmostEqual(self.game.audio.duck, S.curve(S.OpeningCutscene.DUCK, cut.clock), delta=0.05)
        self.assertLess(self.game.audio.duck, 0.5)

    def test_the_run_in_jingles_while_she_moves_and_not_before_or_after(self):
        cut = self.start(DT)
        self.run_clock(4.9, DT)
        d = self.story.dialogue
        self.assertIsNotNone(d)
        before = [e for e in self.story.sound_log if e[3] == "bell"]
        self.assertEqual(before, [])                                         # no bell during the monologue
        for _ in range(4):
            self.game.step([], DT)
            while d.shown < len(d.line.text):
                self.game.step([], DT)
            self.game.step([down(K.K_e)], DT)
            self.game.step([down(K.K_e)], DT)
            d = self.story.dialogue or d
            if self.cut.stage == "approach":
                break
        guard = 0
        while self.cut.stage == "approach" and guard < 60 * 12:
            self.game.step([], DT)
            guard += 1
        bells = [e for e in self.story.sound_log if e[3] == "bell"]
        self.assertGreaterEqual(len(bells), 3)
        self.assertEqual(max(v for _, _, v, _ in bells) <= 0.5, True)
        vols = [v for _, _, v, _ in bells[:6]]
        self.assertEqual(vols[:3], sorted(vols[:3]))                         # louder as she gets close
        for _, name, _, _ in bells:
            self.assertEqual(name, "coin_clink")
        arrived_bells = len([e for e in self.story.sound_log if e[3] == "bell"])
        self.assertTrue(self.cut.stage in ("talk",) or self.story.cutscene is None or self.cut.stage != "approach")
        for _ in range(60 * 2):
            self.game.step([], DT)
        beat_bells = [e for e in self.story.sound_log[-6:] if e[3] == "bell"]
        total = len([e for e in self.story.sound_log if e[3] == "bell"])
        self.assertLessEqual(total - arrived_bells, 3)                       # only the line-beat jingles, no running bell after she stops
        self.assertTrue(all(e[2] <= 0.5 for e in beat_bells))

    def test_the_dialogue_beats_fire_as_their_lines_start_and_only_once(self):
        cut = self.start(DT)
        self.run_clock(5.0, DT)
        d = self.story.dialogue
        self.assertEqual(len(self.cut.bubbles), 1)                           # line 0 of the monologue: the "..." bubble
        self.assertEqual(self.cut.bubbles[0]["text"], "...")
        for _ in range(60):
            self.game.step([], DT)
        self.assertEqual(len(self.cut.bubbles), 1)                           # standing on a line does not repeat its beat
        self.assertIsNotNone(d)


class OpeningSkipTests(unittest.TestCase):
    def setUp(self):
        self.p = fresh("skip")
        self.game = Game(session=session_of(self.p), opening=True)
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.mix = None
        self.played = []
        real = self.game.audio.play
        self.game.audio.play = lambda name, volume=1.0: (self.played.append(name), real(name, volume))[1]
        for _ in range(40):
            self.game.step([], DT)
        self.cut = self.story.cutscene
        self.assertIsNotNone(self.cut)
        self.room = self.game.scenes.current

    def frames(self, n, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def test_esc_during_the_intro_skips_to_the_first_conversation_silently(self):
        self.frames(60 * 1)                                                  # in the middle of the dark, before the first eye opens
        before = len(self.played)
        self.frames(1, [down(K.K_ESCAPE)])
        self.frames(3)
        self.assertEqual(self.cut.stage, "monologue")
        self.assertIsNotNone(self.story.dialogue)
        self.assertTrue(self.cut.timeline.done)
        names = [n for n, _, _ in self.cut.trace]
        self.assertEqual(sum(1 for n in names if n.endswith("(skipped)")), len(names) - 2)    # hum and beep had already played
        later = self.played[before:]
        self.assertNotIn("machine", later)                                   # none of the skipped effects played late
        self.assertNotIn("zap", later)
        self.assertEqual(S.curve(S.OpeningCutscene.COVER, self.cut.clock), 0)  # the end state: lights on ...
        self.assertEqual(S.curve(S.OpeningCutscene.LIDS, self.cut.clock), 1.0)  # ... eyes open

    def test_a_skip_leaves_the_sound_state_clear_and_nothing_replays(self):
        self.frames(30)
        self.frames(1, [down(K.K_ESCAPE)])
        self.frames(60 * 3)
        self.assertGreater(self.game.audio.duck, 0.5)                        # the music is on its way back up, not stuck muffled
        self.assertGreater(max(self.game.hub.ambience.mix.values()), 0.2)    # the ambience is back at (or near) the room's level
        count = {n: self.played.count(n) for n in set(self.played)}
        self.frames(60 * 3)
        self.assertEqual(count.get("machine", 0), self.played.count("machine"))
        self.assertEqual(count.get("zap", 0), self.played.count("zap"))

    def test_pressing_esc_twice_or_late_does_nothing_odd(self):
        self.frames(1, [down(K.K_ESCAPE)])
        self.frames(1, [down(K.K_ESCAPE)])
        self.frames(60)
        self.assertEqual(self.cut.stage, "monologue")
        d = self.story.dialogue
        self.frames(1, [down(K.K_ESCAPE)])                                   # ESC in a conversation is not a skip
        self.assertIs(self.story.dialogue, d)
        self.assertEqual(d.index, 0)

    def test_esc_during_the_run_in_puts_her_beside_the_player_and_starts_talking(self):
        self.frames(1, [down(K.K_ESCAPE)])
        self.frames(60 * 2)
        for _ in range(4):
            while self.story.dialogue is not None and self.story.dialogue.shown < len(self.story.dialogue.line.text):
                self.frames(1)
            self.frames(1, [down(K.K_e)])
            self.frames(1, [down(K.K_e)])
            if self.cut.stage == "approach":
                break
        self.assertEqual(self.cut.stage, "approach")
        self.frames(20)
        self.frames(1, [down(K.K_ESCAPE)])
        self.frames(3)
        self.assertEqual(self.cut.stage, "talk")
        p, b = self.room.player, self.story.brain
        self.assertLess(abs(b.x - (p.x - 30)), 3)
        self.assertIsNotNone(self.story.dialogue)

    def test_cleanup_restores_the_ambience_and_music_however_it_ends(self):
        self.frames(60 * 2)
        self.assertLess(self.game.audio.duck, 1.0)
        self.cut.cleanup()
        self.assertIsNone(self.story.music_duck)
        self.assertEqual(self.game.hub.ambience.mix, self.room.ambience_mix)
        self.cut.cleanup()                                                   # (twice is harmless)
        self.assertEqual(self.game.hub.ambience.mix, self.room.ambience_mix)

    def test_closing_the_game_mid_scene_restores_the_sound(self):
        self.frames(60 * 2)
        self.game.hub.close()
        self.assertIsNone(self.story.music_duck)
        self.assertEqual(self.game.hub.ambience.mix, self.room.ambience_mix)

    def test_finishing_the_story_scene_leaves_nothing_muffled(self):
        self.frames(1, [down(K.K_ESCAPE)])
        guard = 0
        while (self.story.locked or self.story.dialogue is not None) and guard < 400:
            if self.story.dialogue is not None:
                self.frames(100)
                self.frames(1, [down(K.K_e)])
                self.frames(1, [down(K.K_e)])
            else:
                self.frames(10)
            guard += 1
        self.frames(5)
        self.assertIsNone(self.story.music_duck)
        self.assertEqual(self.game.audio.duck, 1.0)
        self.assertEqual(self.game.hub.ambience.mix, self.room.ambience_mix)

    def test_input_routing_is_normal_again_after_a_skipped_opening(self):
        self.frames(1, [down(K.K_ESCAPE)])
        guard = 0
        while (self.story.locked or self.story.dialogue is not None) and guard < 400:
            if self.story.dialogue is not None:
                self.frames(100)
                self.frames(1, [down(K.K_e)])
                self.frames(1, [down(K.K_e)])
            else:
                self.frames(10)
            guard += 1
        self.room.player.profile.claim_daily_reward()
        self.room.popup = None
        self.frames(5)
        self.frames(1, [down(K.K_q)])
        self.assertIsNotNone(self.story.log)
        self.frames(1, [down(K.K_q)])
        self.frames(3)
        self.assertIsNone(self.story.log)
        p = self.room.player
        x = p.x
        self.frames(1, [down(K.K_d)])
        self.frames(20)
        self.assertGreater(p.x, x)


# ------------------------------------------------------------------ the quest tracker's layout
def way_out_manager(title=None, objective=None):
    """A manager whose active quest is the secret-counter one (optionally with a very long title)."""
    if title:
        quests = (QuestDef("long", title, objective or "Do the thing.", "DO THE THING", ("counters", {"secret_items": 3, "secret_trials": 3}),
                           ("h",)),)
    else:
        quests = QUESTS
    p = fresh("lay")
    p.set_story({"opening_done": True, "completed": [q.id for q in quests[:-1]]})
    return p, QuestManager(session_of(p), quests)


class TrackerLayoutTests(unittest.TestCase):
    def rects(self, spec):
        out = [("label", spec["label"]), ("chip", spec["chip"])]
        out += [("hint", spec["hint"])]
        out += [(f"title{i}", r) for i, (_, r) in enumerate(spec["title"])]
        out += [(f"detail{i}", r) for i, (_, _, r) in enumerate(spec["detail"])]
        return out

    def check(self, spec):
        w, h = spec["size"]
        panel = pygame.Rect(0, 0, w, h)
        pad = ObjectiveTracker.PAD
        inner = panel.inflate(-2 * pad, -2 * pad + 4)
        items = self.rects(spec)
        for name, r in items:
            self.assertTrue(panel.contains(r), (name, r, panel))                      # nothing outside the panel
            self.assertGreaterEqual(r.left, pad, name)                                  # padding on the left
            self.assertLessEqual(r.right, w - pad, name)                                # ... and the right
            self.assertGreaterEqual(r.top, pad - 1, name)
            self.assertLessEqual(r.bottom, h - 2, name)
        for i, (a, ra) in enumerate(items):
            for b, rb in items[i + 1:]:
                self.assertFalse(ra.colliderect(rb), (a, b, ra, rb))                    # no two things overlap
        self.assertGreaterEqual(spec["chip"].left - spec["label"].right, ObjectiveTracker.GAP)   # label and Q are apart
        self.assertGreaterEqual(spec["title"][0][1].top - spec["label"].bottom, 3)       # the title sits clear of the label
        return inner

    def test_every_real_quest_lays_out_cleanly_with_the_label_the_title_and_the_q_apart(self):
        for quest in QUESTS:
            p = fresh("q" + quest.id)
            p.set_story({"opening_done": True, "completed": [q.id for q in QUESTS[:QUESTS.index(quest)]]})
            m = QuestManager(session_of(p))
            t = ObjectiveTracker(m)
            spec = t.layout()
            self.check(spec)
            self.assertLessEqual(spec["size"][0], ObjectiveTracker.MAX_W)
            self.assertGreaterEqual(spec["size"][0], ObjectiveTracker.MIN_W)

    def test_the_label_and_the_title_are_on_different_rows(self):
        p, m = way_out_manager()
        spec = ObjectiveTracker(m).layout()
        self.assertEqual(spec["label"].top, spec["chip"].top + 1)
        self.assertGreater(spec["title"][0][1].top, spec["label"].bottom)
        self.assertGreater(spec["detail"][0][2].top, spec["title"][-1][1].bottom)

    def test_the_secret_counters_are_two_readable_groups_side_by_side(self):
        p, m = way_out_manager()
        t = ObjectiveTracker(m)
        spec = t.layout()
        texts = [d[0] for d in spec["detail"]]
        self.assertEqual(texts, ["ITEMS 0/3", "TRIALS 0/3"])
        a, b = spec["detail"][0][2], spec["detail"][1][2]
        self.assertEqual(a.top, b.top)
        self.assertGreaterEqual(b.left - a.right, ObjectiveTracker.GAP)                  # clear space between them
        m.handle("secret_item_found", "x")
        m.handle("secret_trial_done", "trial_01")
        self.assertEqual([d[0] for d in t.layout()["detail"]], ["ITEMS 1/3", "TRIALS 1/3"])

    def test_long_quest_titles_wrap_instead_of_overflowing(self):
        p, m = way_out_manager("The Extraordinarily Long Name Of A Quest That Keeps Going And Going", "A very long objective sentence that also would not fit on one line of the tracker")
        t = ObjectiveTracker(m)
        spec = t.layout()
        self.check(spec)
        self.assertGreater(len(spec["title"]), 1)                                       # wrapped onto more rows
        self.assertLessEqual(spec["size"][0], ObjectiveTracker.MAX_W)
        for text, rect in spec["title"]:
            self.assertLessEqual(rect.right, spec["size"][0] - ObjectiveTracker.PAD)

    def test_a_narrow_space_wraps_further_and_still_fits(self):
        p, m = way_out_manager()
        t = ObjectiveTracker(m)
        for cap in (110, 96, 80):
            spec = t.layout(cap)
            self.check(spec)
            self.assertLessEqual(spec["size"][0], max(cap, ObjectiveTracker.MIN_W))
        wide, narrow = t.layout(196), t.layout(96)
        self.assertGreaterEqual(len(narrow["detail"]), len(wide["detail"]))              # the two counters stack when they cannot sit side by side

    def test_the_drawn_panel_is_as_big_as_its_layout_and_uses_one_border(self):
        p, m = way_out_manager()
        t = ObjectiveTracker(m)
        self.assertEqual(t._image().get_size(), t.layout()["size"])

    def test_the_tracker_is_placed_clear_of_the_wallet_and_controls_in_every_room(self):
        for names in (["a"],):
            profiles = [fresh(n) for n in names]
            for pr in profiles:
                pr.set_story({"opening_done": True, "completed": [q.id for q in QUESTS[:3]]})
            game = Game(session=session_of(profiles[0]))
            self.addCleanup(game.quit)
            for rid in ("home", "arcade_floor", "prize_plaza"):
                room = goto_room(game, rid)
                for pl in room.players:
                    pl.profile.claim_daily_reward()
                room.popup = None
                for _ in range(40):
                    game.step([], DT)
                surf = pygame.Surface((400, 300))
                room.draw(surf)
                tracker = game.hub.story.tracker
                rect = tracker.rect(room, animated=False)
                self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(rect), (names, rid, rect))
                for hud in room.huds:
                    self.assertFalse(rect.colliderect(hud.rect), (names, rid, "wallet"))
                box = room.instructions.image.get_rect(bottomleft=(4, 296))
                self.assertFalse(rect.colliderect(box), (names, rid, "controls"))
                self.assertGreaterEqual(rect.left, box.right + 4)                          # never reaches back over the controls box

    def test_the_tracker_works_with_a_wrapped_title(self):
        quests = (QuestDef("long", "A Quest With A Really Rather Long Title Indeed Yes", "Do it all.", "DO IT ALL", ("played", 99), ("h",)),)
        a = fresh("a")
        a.set_story({"opening_done": True})
        game = Game(session=session_of(a))
        self.addCleanup(game.quit)
        story = game.hub.story
        story.manager.quests = quests
        story.manager.by_id = {q.id: q for q in quests}
        room = goto_room(game, "home")
        for pl in room.players:
            pl.profile.claim_daily_reward()
        room.popup = None
        for _ in range(40):
            game.step([], DT)
        room.draw(pygame.Surface((400, 300)))
        rect = story.tracker.rect(room, animated=False)
        self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(rect))
        for hud in room.huds:
            self.assertFalse(rect.colliderect(hud.rect))
        self.assertGreater(len(story.tracker.layout(story.tracker._free_width(room))["title"]), 1)


# ------------------------------------------------------------------ the trial rules (data only, no screen)
class TrialRuleTests(unittest.TestCase):
    def setUp(self):
        self.p = fresh("tr", tickets=0, tokens=0)
        self.m = QuestManager(session_of(self.p))
        self.m.finish_opening()

    def st(self, n):
        return trial_status(self.m, self.p, TRIALS[n - 1])

    def test_there_are_three_trials_with_the_expected_names(self):
        self.assertEqual([t.title for t in TRIALS], ["THE GOLDEN AGE", "THE UNBEATEN RECORD", "THE FINAL LOCK"])
        self.assertEqual([t.number for t in TRIALS], [1, 2, 3])

    def test_trials_one_and_two_are_open_from_the_start_and_need_no_items_or_money(self):
        self.assertEqual(self.m.secret_items, 0)
        for n in (1, 2):
            s = self.st(n)
            self.assertEqual(s.code, "available", n)
            self.assertFalse(s.needs_currency)
            self.assertEqual(s.reasons, ())

    def test_one_and_two_can_be_done_in_either_order(self):
        self.m.handle("secret_trial_done", "trial_02")
        self.assertEqual((self.st(1).code, self.st(2).code), ("available", "done"))
        self.m.handle("secret_trial_done", "trial_01")
        self.assertEqual((self.st(1).code, self.st(2).code), ("done", "done"))
        p2, m2 = fresh("o"), None
        m2 = QuestManager(session_of(p2))
        m2.finish_opening()
        m2.handle("secret_trial_done", "trial_01")
        self.assertEqual(trial_status(m2, p2, TRIALS[1]).code, "available")

    def test_trial_three_is_locked_until_one_and_two_are_done_and_says_why(self):
        s = self.st(3)
        self.assertEqual(s.code, "locked")
        self.assertIn("COMPLETE TRIALS 01 AND 02 FIRST", s.reasons)
        self.m.handle("secret_trial_done", "trial_01")
        self.assertIn("COMPLETE TRIAL 02 FIRST", self.st(3).reasons)
        self.m.handle("secret_trial_done", "trial_02")
        self.assertFalse(any("COMPLETE TRIAL" in r for r in self.st(3).reasons))

    def test_trial_three_needs_enough_tickets_and_tokens_and_shows_the_balance(self):
        self.m.handle("secret_trial_done", "trial_01")
        self.m.handle("secret_trial_done", "trial_02")
        s = self.st(3)
        self.assertEqual((s.tickets_needed, s.tokens_needed), (300, 30))
        self.assertEqual((s.tickets_have, s.tokens_have), (self.p.tickets, self.p.tokens))
        self.assertEqual(s.code, "locked")
        self.assertIn(f"NEED 300 TICKETS (YOU HAVE {self.p.tickets})", s.reasons)
        self.assertIn(f"NEED 30 TOKENS (YOU HAVE {self.p.tokens})", s.reasons)
        self.p.add_tickets(300)
        s = self.st(3)
        self.assertEqual(s.code, "locked")                                                # tickets alone are not enough
        self.assertEqual(len(s.reasons), 1)
        self.assertTrue(s.reasons[0].startswith("NEED 30 TOKENS"))
        self.p.add_tokens(30, "TEST")
        self.assertEqual(self.st(3).code, "available")
        self.assertEqual((self.p.tickets, self.p.tokens), (300, 30))                      # holding is not spending

    def test_one_short_is_still_locked(self):
        self.m.handle("secret_trial_done", "trial_01")
        self.m.handle("secret_trial_done", "trial_02")
        self.p.add_tickets(299)
        self.p.add_tokens(30, "T")
        self.assertEqual(self.st(3).code, "locked")
        self.p.add_tickets(1)
        self.assertEqual(self.st(3).code, "available")

    def test_the_numbers_are_settings_not_hard_coded(self):
        old = (settings.TRIAL_FINAL_TICKETS, settings.TRIAL_FINAL_TOKENS)
        self.addCleanup(lambda: (setattr(settings, "TRIAL_FINAL_TICKETS", old[0]), setattr(settings, "TRIAL_FINAL_TOKENS", old[1])))
        settings.TRIAL_FINAL_TICKETS, settings.TRIAL_FINAL_TOKENS = 5, 2
        self.assertEqual(trial_cost(TRIALS[2]), (5, 2))
        self.m.handle("secret_trial_done", "trial_01")
        self.m.handle("secret_trial_done", "trial_02")
        self.p.add_tickets(5)
        self.p.add_tokens(2, "T")
        self.assertEqual(self.st(3).code, "available")
        self.assertEqual(old, (300, 30))                                                  # the provisional defaults

    def test_looking_never_changes_the_wallet_the_story_or_the_save(self):
        before = (self.p.to_dict(), json.dumps(self.m.state, sort_keys=True))
        for _ in range(5):
            for n in (1, 2, 3):
                self.st(n)
            exit_status(self.m)
        self.assertEqual((self.p.to_dict(), json.dumps(self.m.state, sort_keys=True)), before)

    def test_the_exit_needs_every_item_and_every_trial_but_items_do_not_gate_the_trials(self):
        ok, reasons = exit_status(self.m)
        self.assertFalse(ok)
        self.assertEqual(len(reasons), 2)
        self.m.handle("secret_trial_done", "trial_01")
        self.m.handle("secret_trial_done", "trial_02")
        self.p.add_tickets(300)
        self.p.add_tokens(30, "T")
        self.assertEqual(self.st(3).code, "available")                                    # with no items at all
        self.m.handle("secret_trial_done", "trial_03")
        ok, reasons = exit_status(self.m)
        self.assertFalse(ok)
        self.assertEqual(reasons, ("NEED 3 SECRET ITEMS (HAVE 0)",))
        for i in range(3):
            self.m.handle("secret_item_found", f"gem{i}")
        self.assertEqual(exit_status(self.m), (True, ()))

    def test_completed_trials_and_items_survive_a_save_and_load(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "p.json")
        store = ProfileStore(path)
        p = fresh("sv", tickets=50)
        store.autosave(p)
        m = QuestManager(session_of(p))
        m.finish_opening()
        m.handle("secret_trial_done", "trial_02")
        m.handle("secret_item_found", "gem_a")
        loaded = ProfileStore(path).load()
        m2 = QuestManager(session_of(loaded))
        self.assertTrue(m2.trial_done("trial_02"))
        self.assertFalse(m2.trial_done("trial_01"))
        self.assertEqual(m2.secret_items, 1)
        self.assertEqual(trial_status(m2, loaded, TRIALS[0]).code, "available")
        self.assertEqual(trial_status(m2, loaded, TRIALS[1]).code, "done")
        self.assertEqual(trial_status(m2, loaded, TRIALS[2]).code, "locked")
        self.assertEqual(loaded.tickets, 50)

    def test_each_profile_is_judged_by_its_own_wallet_and_its_own_trial_progress(self):
        a, b = fresh("a", tickets=400, tokens=40), fresh("b", tickets=5, tokens=0)
        m = QuestManager(session_of(a))
        m.finish_opening()
        m.handle("secret_trial_done", "trial_01")
        m.handle("secret_trial_done", "trial_02")
        self.assertEqual(trial_status(m, a, TRIALS[2]).code, "available")
        self.assertEqual(trial_status(m, b, TRIALS[2]).code, "locked")      # (b's wallet is judged by b's own money)
        self.assertEqual(b.story, {})                                         # and b never received a's progress

    def test_progress_is_never_marked_by_looking_or_choosing(self):
        self.assertEqual(self.m.secret_trials, 0)
        self.st(1), self.st(2), self.st(3)
        self.assertEqual(self.m.secret_trials, 0)


# ------------------------------------------------------------------ the legacy terminal (a real screen in the real game)
class LegacyBase(unittest.TestCase):
    PLAYERS = 1

    def setUp(self):
        names = ["a", "b"][:self.PLAYERS]
        self.profiles = [fresh(n, tickets=120, tokens=12) for n in names]
        for pr in self.profiles:
            pr.set_story({"opening_done": True, "completed": ["get_your_bearings", "arcade_explorer", "earn_some_rewards"]})
        self.game = Game(session=session_of(self.profiles[0]))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.room = goto_room(self.game, "arcade_floor")
        for _ in range(10):
            self.game.step([], DT)

    def frames(self, n, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def tap(self, k):
        self.frames(1, [down(k)])
        self.frames(1, [up(k)])

    def open_shop(self, who=0):
        self.room.acting_player = self.room.players[who]
        self.room.open_vending()
        self.room.acting_player = None
        self.frames(90)
        shop = self.game.scenes.current
        self.assertIsInstance(shop, VendingScene)
        return shop

    def enter_code(self, keys=None, who_keys=None):
        for k in (keys or CLASSIC):
            self.tap(k)

    def open_terminal(self, key=K.K_e):
        """Type the secret code; after the glitch the hidden page becomes the terminal by itself. Skips its boot typing."""
        shop = self.open_shop()
        self.enter_code()
        self.frames(int((GLITCH_TIME + 0.8) / DT))
        scene = self.game.scenes.current
        self.assertIsInstance(scene, LT.LegacyTerminalScene)
        self.assertTrue(scene.booting)
        self.tap(key)                                                    # (the use key finishes the boot typing)
        self.frames(30)
        self.assertFalse(scene.booting)
        return shop, scene


class LegacyTerminalTests(LegacyBase):
    def test_the_secret_code_still_activates_the_same_hidden_screen(self):
        shop = self.open_shop()
        self.enter_code()
        self.assertIsNotNone(shop.secret)
        self.assertTrue(self.profiles[0].has_secret(SECRET_FLAG))
        self.assertEqual(shop.music_duck, SECRET_DUCK)
        self.assertIsInstance(self.game.scenes.current, VendingScene)

    def test_the_hidden_page_becomes_the_terminal_by_itself_after_the_glitch(self):
        shop = self.open_shop()
        self.enter_code()
        self.frames(int((GLITCH_TIME * 0.5) / DT))
        self.assertIsInstance(self.game.scenes.current, VendingScene)       # still the glitch: nothing opens early
        self.frames(int((GLITCH_TIME + 0.8) / DT))
        self.assertIsInstance(self.game.scenes.current, LT.LegacyTerminalScene)   # no extra key needed

    def test_the_old_page_text_is_the_terminals_boot_sequence(self):
        shop = self.open_shop()
        self.enter_code()
        self.frames(int((GLITCH_TIME + 0.8) / DT))
        term = self.game.scenes.current
        self.assertEqual([l[0] for l in LT.BOOT_LINES if l[0]], ["SYSTEM OVERRIDE", "USER: UNKNOWN", "ACCESS LEVEL: 01", "THE ARCADE REMEMBERS."])
        surf = pygame.Surface((400, 300))
        term.draw(surf)                                                      # the boot page draws
        self.frames(int(term.boot_time / DT) + 10)
        self.assertFalse(term.booting)
        self.assertGreater(term.boot_time, 2.5)

    def test_esc_during_the_glitch_or_the_boot_still_leaves_at_once(self):
        shop = self.open_shop()
        self.enter_code()
        self.frames(int((GLITCH_TIME * 0.4) / DT))
        self.tap(K.K_ESCAPE)
        self.frames(90)
        self.assertIs(self.game.scenes.current, self.room)
        shop = self.open_shop()
        self.enter_code()
        self.frames(int((GLITCH_TIME + 0.8) / DT))
        self.assertTrue(self.game.scenes.current.booting)
        self.tap(K.K_ESCAPE)
        self.frames(150)
        self.assertIs(self.game.scenes.current, self.room)

    def test_leaving_the_terminal_leaves_the_hidden_page_too(self):
        shop, term = self.open_terminal()
        self.tap(K.K_ESCAPE)
        self.frames(150)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(self.game.audio.duck, 1.0)                          # and the music is back

    def test_visiting_again_after_leaving_works_and_shows_the_same_progress(self):
        self.story.manager.handle("secret_trial_done", "trial_01")
        shop, term = self.open_terminal()
        self.tap(K.K_ESCAPE)
        self.frames(150)
        shop2, term2 = self.open_terminal()
        self.assertIsNot(term2, term)
        self.assertEqual(term2.status(TRIALS[0]).code, "done")

    def test_normal_vending_never_opens_the_terminal(self):
        shop = self.open_shop()
        for k in (K.K_DOWN, K.K_RIGHT, K.K_UP, K.K_LEFT, K.K_e, K.K_e, K.K_SPACE, K.K_RETURN):
            self.tap(k)
            self.frames(30)
            self.assertNotIsInstance(self.game.scenes.current, LT.LegacyTerminalScene)
        for k in CLASSIC[:7] + [K.K_x, K.K_b, K.K_a]:                       # a wrong code
            self.tap(k)
        self.frames(int((GLITCH_TIME + 2) / DT))
        self.assertNotIsInstance(self.game.scenes.current, LT.LegacyTerminalScene)
        self.assertIsNone(shop.secret)

    def test_the_terminal_shows_the_real_progress_and_the_players_own_wallet(self):
        m = self.story.manager
        m.handle("secret_trial_done", "trial_01")
        m.handle("secret_item_found", "gem_a")
        m.handle("secret_item_found", "gem_b")
        shop, term = self.open_terminal()
        self.assertEqual([term.status(t).code for t in TRIALS], ["done", "available", "locked"])
        self.assertEqual(term.manager.secret_items, 2)
        self.assertEqual(term.status(TRIALS[2]).tickets_have, 120)
        self.assertEqual(term.status(TRIALS[2]).tokens_have, 12)
        self.assertIn("NEED 300 TICKETS (YOU HAVE 120)", term.status(TRIALS[2]).reasons)
        surf = pygame.Surface((400, 300))
        term.draw(surf)

    def test_selecting_an_open_trial_that_is_not_built_shows_the_placeholder_and_changes_nothing(self):
        shop, term = self.open_terminal()
        self.frames(60)
        self.tap(K.K_DOWN)                                                            # trial 02 (trial 01 is built now)
        self.assertEqual(term.trial.number, 2)
        before = (self.profiles[0].to_dict(), json.dumps(self.story.manager.state, sort_keys=True), term.index)
        self.tap(K.K_e)
        self.frames(5)
        self.assertEqual(term.notice["title"], "TRIAL NOT YET AVAILABLE")
        self.assertIn("NOTHING WAS CHARGED OR RECORDED.", term.notice["lines"])
        term.draw(pygame.Surface((400, 300)))
        after = (self.profiles[0].to_dict(), json.dumps(self.story.manager.state, sort_keys=True), term.index)
        self.assertEqual(before, after)
        self.assertEqual(self.story.manager.secret_trials, 0)                          # not falsely marked complete
        self.assertFalse(self.story.manager.trial_done("trial_02"))
        self.tap(K.K_e)                                                               # OK closes the card
        self.assertIsNone(term.notice)

    def test_selecting_the_locked_trial_explains_why_and_takes_nothing(self):
        shop, term = self.open_terminal()
        self.frames(60)
        self.tap(K.K_UP)                                                              # wraps to trial 03
        self.assertEqual(term.trial.number, 3)
        before = (self.profiles[0].tickets, self.profiles[0].tokens)
        self.tap(K.K_e)
        self.frames(5)
        self.assertEqual(term.notice["title"], "ACCESS DENIED")
        self.assertIn("COMPLETE TRIALS 01 AND 02 FIRST", term.notice["lines"])
        self.assertIn("NEED 300 TICKETS (YOU HAVE 120)", term.notice["lines"])
        self.assertIn("NEED 30 TOKENS (YOU HAVE 12)", term.notice["lines"])
        term.draw(pygame.Surface((400, 300)))
        self.assertEqual((self.profiles[0].tickets, self.profiles[0].tokens), before)

    def test_trial_three_available_still_charges_nothing_and_shows_the_placeholder(self):
        m = self.story.manager
        m.handle("secret_trial_done", "trial_01")
        m.handle("secret_trial_done", "trial_02")
        self.profiles[0].add_tickets(300)
        self.profiles[0].add_tokens(30, "T")
        shop, term = self.open_terminal()
        self.frames(60)
        self.tap(K.K_UP)
        wallet = (self.profiles[0].tickets, self.profiles[0].tokens)
        self.assertEqual(term.status().code, "available")
        self.tap(K.K_e)
        self.assertEqual(term.notice["title"], "TRIAL NOT YET AVAILABLE")
        self.assertEqual((self.profiles[0].tickets, self.profiles[0].tokens), wallet)
        self.assertFalse(m.trial_done("trial_03"))

    def test_a_finished_trial_that_has_no_room_says_so(self):
        self.story.manager.handle("secret_trial_done", "trial_02")
        shop, term = self.open_terminal()
        self.frames(60)
        self.tap(K.K_DOWN)
        self.tap(K.K_e)
        self.assertEqual(term.notice["title"], "TRIAL 02 COMPLETE")

    def test_selection_wraps_and_only_the_owners_keys_work(self):
        shop, term = self.open_terminal()
        self.frames(60)
        self.assertEqual(term.index, 0)
        self.tap(K.K_DOWN)
        self.tap(K.K_s)
        self.assertEqual(term.index, 2)
        self.tap(K.K_DOWN)
        self.assertEqual(term.index, 0)

    def test_the_music_stays_low_while_the_terminal_is_open(self):
        shop, term = self.open_terminal()
        self.frames(5)
        self.assertEqual(term.music_duck, LT.MUSIC_DUCK)
        self.assertAlmostEqual(self.game.audio.duck, LT.MUSIC_DUCK)

    def test_it_draws_every_state_inside_the_canvas(self):
        shop, term = self.open_terminal()
        m = self.story.manager
        steps = [lambda: None, lambda: m.handle("secret_trial_done", "trial_01"), lambda: m.handle("secret_item_found", "a"),
                 lambda: m.handle("secret_trial_done", "trial_02"), lambda: self.profiles[0].add_tickets(300),
                 lambda: self.profiles[0].add_tokens(30, "T"), lambda: m.handle("secret_trial_done", "trial_03"),
                 lambda: [m.handle("secret_item_found", f"g{i}") for i in range(3)]]
        for step in steps:
            step()
            for index in range(3):
                term.index = index
                term.notice = None
                surf = pygame.Surface((400, 300))
                term.draw(surf)
                term.select()
                term.draw(surf)
                term.notice = None
        self.assertEqual(exit_status(m), (True, ()))

    def test_a_registered_trial_scene_is_started_instead_of_the_placeholder(self):
        from menu_kit import MenuScene

        class Fake(MenuScene):
            started = []

            def __init__(self, game, owner):
                super().__init__(game, owner)
                Fake.started.append(owner)

            def on_action(self, action):
                self.close()

            def draw(self, surf):
                surf.fill((1, 2, 3))
        from unittest.mock import patch
        patcher = patch.dict(LT.TRIAL_SCENES, {"trial_01": Fake})          # (the real room is put back afterwards)
        patcher.start()
        self.addCleanup(patcher.stop)
        shop, term = self.open_terminal()
        self.frames(60)
        self.tap(K.K_e)
        self.frames(5)
        self.assertEqual(len(Fake.started), 1)
        self.assertIsNone(term.notice)
        self.assertEqual(self.story.manager.secret_trials, 0)                          # starting a trial records nothing by itself

    def test_the_staff_panel_secret_is_untouched(self):
        import staff_cheat
        self.assertEqual(staff_cheat.PASSWORD, "515106")
        entry = staff_cheat.PasswordEntry()
        for ch in "515106":
            entry.type(ch)
        self.assertEqual(entry.text, "515106")
        p = fresh("staff", tokens=1, tickets=1)
        result = staff_cheat.StaffService(p).grant(staff_cheat.PlayerProfile.TICKET, 10)
        self.assertIsNotNone(result)
        self.assertEqual(p.tickets, 11)
        self.assertEqual(self.story.manager.secret_trials, 0)                          # and it has nothing to do with the trials


class LegacyTerminalOtherSavedProfileTests(LegacyBase):
    """Another profile is saved (never played): the terminal belongs to the playing profile alone."""
    PLAYERS = 2

    def test_the_old_second_player_keys_cannot_drive_the_terminal(self):
        _shop, term = self.open_terminal()
        self.assertEqual(term.index, 0)
        for k in (K.K_o, K.K_RCTRL, K.K_SLASH, K.K_RSHIFT):                          # not keys of the game
            self.tap(k)
        self.assertEqual(term.index, 0)
        self.assertIsNone(term.notice)
        self.tap(K.K_DOWN)                                                            # the player's own key
        self.assertEqual(term.index, 1)

    def test_it_shows_the_wallet_of_the_playing_profile_only(self):
        self.profiles[0].add_tickets(500)
        self.profiles[0].add_tokens(50, "T")
        self.story.manager.handle("secret_trial_done", "trial_01")
        self.story.manager.handle("secret_trial_done", "trial_02")
        _shop, term = self.open_terminal()
        self.assertEqual(term.status(TRIALS[2]).code, "available")                    # the player's 500 / 50 qualify
        self.assertEqual(term.status(TRIALS[2]).tickets_have, 620)
        self.assertEqual(self.profiles[1].tickets, 120)                               # the other wallet: as it was


# ------------------------------------------------------------------ the collapsible quest drawer
class DrawerBase(unittest.TestCase):
    PLAYERS = 1

    def setUp(self):
        names = ["a", "b"][:self.PLAYERS]
        self.profiles = [fresh(n) for n in names]
        for pr in self.profiles:
            pr.set_story({"opening_done": True, "completed": [q.id for q in QUESTS[:3]]})
        self.game = Game(session=session_of(self.profiles[0]))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.tracker = self.story.tracker
        self.room = goto_room(self.game, "arcade_floor")
        for pl in self.room.players:
            pl.profile.claim_daily_reward()
        self.room.popup = None
        self.frames(240)                                           # let any opening flourish settle

    def frames(self, n, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def seconds(self, s):
        self.frames(int(round(s / DT)))

    def progress(self):
        self.story.manager.handle("secret_item_found", f"g{len(self.story.manager.state.get('stats', {}).get('secret_items', []))}")


class DrawerTests(DrawerBase):
    def test_it_starts_folded_with_only_the_small_tab_showing(self):
        t = self.tracker
        self.assertEqual((t.slide, t.pinned, t.auto_left), (0.0, False, 0.0))
        self.assertEqual(t.appear, 1.0)
        surf = pygame.Surface((400, 300), pygame.SRCALPHA)
        t.draw(surf, self.room)
        shown = surf.get_bounding_rect()
        self.assertEqual(shown, t.tab_rect(self.room))
        self.assertLessEqual(shown.w, 24)                                      # a small tab, not a panel
        self.assertGreater(shown.left, 400 - 30)                                # on the right edge

    def test_the_tab_shows_the_key_that_opens_it(self):
        t = self.tracker
        self.assertIsNotNone(t._tab_image(False))
        self.assertEqual(self.tracker.layout()["hint"].width, get_font_width("TAB HIDE"))

    def test_progress_opens_it_for_about_three_seconds_then_it_folds_itself(self):
        t = self.tracker
        self.progress()
        self.assertEqual(t.auto_left, ObjectiveTracker.AUTO_TIME)
        self.seconds(0.5)
        self.assertEqual(t.slide, 1.0)
        self.seconds(2.0)
        self.assertEqual(t.slide, 1.0)                                          # still open at 2.5 s
        self.seconds(1.2)
        self.assertEqual(t.slide, 0.0)                                          # folded again by ~3.7 s
        self.assertFalse(t.pinned)

    def test_a_new_quest_or_completion_also_opens_it(self):
        t = self.tracker
        play(self.story.manager, "a")                                         # completes a quest and starts the next
        self.seconds(0.5)
        self.assertGreater(t.slide, 0.9)

    def test_the_automatic_three_seconds_only_run_while_it_is_on_screen(self):
        t = self.tracker
        self.room.inventory_ui = type("W", (), {"update": lambda s, dt: None, "closed": False, "draw": lambda s, x: None})()
        self.progress()                                                       # happens while a window covers the screen
        self.seconds(6)
        self.assertGreater(t.auto_left, 2.9)                                  # the clock did not run behind the window
        self.assertEqual(t.slide, 0.0)
        self.room.inventory_ui = None
        self.seconds(0.6)
        self.assertEqual(t.slide, 1.0)                                        # it opens once the screen is clear ...
        self.seconds(3.5)
        self.assertEqual(t.slide, 0.0)                                        # ... and then keeps its full three seconds

    def test_tab_opens_it_and_keeps_it_open_until_tab_again(self):
        t = self.tracker
        self.frames(1, [down(K.K_TAB)])
        self.seconds(0.5)
        self.assertTrue(t.pinned)
        self.assertEqual(t.slide, 1.0)
        self.seconds(8)
        self.assertEqual(t.slide, 1.0)                                          # no timeout while the player holds it open
        self.frames(1, [down(K.K_TAB)])
        self.seconds(0.5)
        self.assertFalse(t.pinned)
        self.assertEqual(t.slide, 0.0)

    def test_tab_while_it_is_open_by_itself_folds_it_at_once(self):
        t = self.tracker
        self.progress()
        self.seconds(0.6)
        self.assertEqual(t.slide, 1.0)
        self.frames(1, [down(K.K_TAB)])
        self.seconds(0.5)
        self.assertEqual((t.slide, t.pinned, t.auto_left), (0.0, False, 0.0))

    def test_q_still_opens_the_full_quest_log_and_the_log_hides_the_drawer(self):
        t = self.tracker
        self.frames(1, [down(K.K_TAB)])
        self.seconds(0.4)
        self.frames(1, [down(K.K_q)])
        self.frames(30)
        self.assertIsNotNone(self.story.log)
        self.assertEqual(t.appear, 0.0)                                         # hidden while the log is open
        self.assertTrue(t.pinned)                                               # ... but the player's choice is remembered
        self.frames(1, [down(K.K_TAB)])                                         # TAB belongs to the open window now
        self.assertTrue(t.pinned)
        self.frames(1, [down(K.K_q)])
        self.seconds(0.6)
        self.assertIsNone(self.story.log)
        self.assertEqual(t.appear, 1.0)
        self.assertEqual(t.slide, 1.0)                                          # and it is back, open as it was

    def test_tab_is_nobodys_game_key_and_needs_no_new_control(self):
        for scheme in (SOLO_CONTROLS,):
            self.assertFalse(scheme.owns(K.K_TAB), scheme.name)
        self.assertEqual(self.room.session.input.route(down(K.K_TAB)), (None, None))

    def test_tab_does_not_disturb_a_window_that_uses_it(self):
        """The bag switches tabs with TAB: while it is open the key is the bag's, not the drawer's."""
        self.frames(1, [down(K.K_i)])
        self.frames(10)
        self.assertIsNotNone(self.room.inventory_ui)
        before = self.tracker.pinned
        self.frames(1, [down(K.K_TAB)])
        self.assertEqual(self.tracker.pinned, before)
        self.assertIsNotNone(self.room.inventory_ui)

    def test_it_hides_while_a_dialogue_or_a_window_is_open_and_comes_back(self):
        t = self.tracker
        self.frames(1, [down(K.K_TAB)])
        self.seconds(0.5)
        self.story.open_dialogue(self.room, self.room.player, [D.Line("MIAO MEOW", "Hi")])
        self.seconds(0.5)
        self.assertEqual(t.appear, 0.0)
        blank = pygame.Surface((400, 300), pygame.SRCALPHA)
        self.tracker.draw(blank, self.room)
        self.assertEqual(blank.get_bounding_rect().size, (0, 0))               # nothing of the drawer is drawn while it is hidden
        self.story.dialogue.closed = True
        self.seconds(0.6)
        self.assertEqual(t.appear, 1.0)
        self.assertEqual(t.slide, 1.0)

    def test_it_hides_while_the_opening_plays(self):
        fresh_game = Game(session=session_of(fresh("op")), opening=True)
        self.addCleanup(fresh_game.quit)
        room = fresh_game.scenes.current
        for _ in range(120):
            fresh_game.step([], DT)
        story = fresh_game.hub.story
        self.assertTrue(story.locked)
        self.assertEqual(story.tracker.appear, 0.0)
        fresh_game.step([down(K.K_TAB)], DT)
        self.assertFalse(story.tracker.pinned)                                  # TAB does nothing during the opening
        self.assertIsNotNone(room)

    def test_it_is_not_drawn_in_a_minigame_and_is_there_again_afterwards(self):
        from menu_kit import MenuScene

        class Game2(MenuScene):
            def on_action(self, action):
                pass

            def draw(self, surf):
                surf.fill((9, 9, 9))
        t = self.tracker
        self.frames(1, [down(K.K_TAB)])
        self.seconds(0.5)
        self.game.scenes.push(Game2(self.game, self.game.session.primary))
        self.seconds(1.5)
        self.assertIsInstance(self.game.scenes.current, Game2)
        self.game.scenes.draw(self.game.canvas, pygame.Surface((800, 600)))
        self.assertEqual(self.game.canvas.get_at((390, 240))[:3], (9, 9, 9))       # nothing of the room, nothing of the drawer
        self.game.scenes.pop()
        self.seconds(1.5)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual((t.pinned, t.slide, t.appear), (True, 1.0, 1.0))        # restored, still open

    def test_the_slide_is_short_smooth_and_never_jumps(self):
        t = self.tracker
        self.frames(1, [down(K.K_TAB)])
        seen = []
        for _ in range(int(0.5 / DT)):
            self.game.step([], DT)
            seen.append(t.eased)
        self.assertEqual(seen, sorted(seen))                                    # opens one way only
        self.assertEqual(seen[-1], 1.0)
        steps = [b - a for a, b in zip(seen, seen[1:])]
        self.assertLess(max(steps), 0.2)                                        # no big jumps
        self.assertGreater(len([s for s in seen if 0 < s < 1]), 5)              # and it really is a slide, not a pop
        self.assertLessEqual(next(i for i, s in enumerate(seen) if s >= 1.0) * DT, ObjectiveTracker.SLIDE_TIME + 0.1)

    def test_animation_speed_does_not_depend_on_the_frame_rate(self):
        for dt in (1 / 30, 1 / 120):
            q = QuestManager(session_of(fresh("fr")))
            q.finish_opening()
            tr = ObjectiveTracker(q)
            tr.toggle()
            for _ in range(int(0.1 / dt)):
                tr.update(dt)
            self.assertAlmostEqual(tr.slide, 0.1 / ObjectiveTracker.SLIDE_TIME, delta=0.15)

    def test_the_visible_part_never_covers_the_wallet_controls_or_leaves_the_screen(self):
        t = self.tracker
        for pinned in (False, True):
            t.pinned, t.slide = pinned, 1.0 if pinned else 0.0
            self.room.draw(pygame.Surface((400, 300)))
            for animated in (True, False):
                rect = t.rect(self.room, animated)
                self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(rect), (pinned, rect))
                for hud in self.room.huds:
                    self.assertFalse(rect.colliderect(hud.rect), "wallet")
                box = self.room.instructions.image.get_rect(bottomleft=(4, 296))
                self.assertFalse(rect.colliderect(box), "controls box")
        full = t.panel_rect(self.room)
        self.assertGreaterEqual(full.left, 4 + self.room.instructions.image.get_width() + 8)
        self.assertEqual(t.rect(self.room, animated=False).union(t.tab_rect(self.room)), t.rect(self.room, animated=False))

    def test_prompts_keep_clear_of_the_part_that_is_showing(self):
        t = self.tracker
        t.slide = 0.0
        self.assertIn(t.rect(self.room), self.room.prompt_avoid_rects())
        self.assertEqual(t.rect(self.room).size, t.tab_rect(self.room).size)
        t.pinned, t.slide = True, 1.0
        self.assertGreater(t.rect(self.room).w, 60)
        self.assertIn(t.rect(self.room), self.room.prompt_avoid_rects())

    def test_the_text_fits_inside_the_open_panel_at_the_real_resolution(self):
        t = self.tracker
        spec = t.layout(t._free_width(self.room))
        w, h = spec["size"]
        panel = pygame.Rect(0, 0, w, h)
        for name, r in ([("label", spec["label"]), ("chip", spec["chip"]), ("hint", spec["hint"])]
                        + [(f"t{i}", r) for i, (_, r) in enumerate(spec["title"])] + [(f"d{i}", r) for i, (_, _, r) in enumerate(spec["detail"])]):
            self.assertTrue(panel.inflate(-2, -2).contains(r), (name, r, panel))

    def test_a_long_title_still_fits_the_open_drawer(self):
        quests = (QuestDef("long", "A Quest With A Really Rather Long Title Indeed Yes And Then Some More", "Do it all.", "DO IT ALL", ("played", 99), ("h",)),)
        self.story.manager.quests = quests
        self.story.manager.by_id = {q.id: q for q in quests}
        self.story.manager.state["completed"] = []
        self.tracker.pinned, self.tracker.slide = True, 1.0
        self.room.draw(pygame.Surface((400, 300)))
        spec = self.tracker.layout(self.tracker._free_width(self.room))
        self.assertGreater(len(spec["title"]), 1)
        rect = self.tracker.rect(self.room, animated=False)
        self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(rect))
        for hud in self.room.huds:
            self.assertFalse(rect.colliderect(hud.rect))


class DrawerOtherSavedProfileTests(DrawerBase):
    """Another profile is saved (never played): the drawer is the playing profile's alone."""
    PLAYERS = 2

    def test_it_opens_and_pins_with_the_shared_tab_key(self):
        t = self.tracker
        self.assertEqual((t.slide, t.pinned), (0.0, False))
        self.progress()
        self.seconds(0.6)
        self.assertEqual(t.slide, 1.0)
        self.seconds(3.5)
        self.assertEqual(t.slide, 0.0)
        self.frames(1, [down(K.K_TAB)])                                         # TAB belongs to no scheme
        self.seconds(0.5)
        self.assertTrue(t.pinned)
        self.frames(1, [down(K.K_TAB)])
        self.seconds(0.5)
        self.assertFalse(t.pinned)
        self.assertEqual(self.profiles[1].story["completed"], [q.id for q in QUESTS[:3]])    # the other save: as it was

    def test_the_open_drawer_clears_the_wallet_box_and_the_controls(self):
        t = self.tracker
        t.pinned, t.slide = True, 1.0
        self.room.draw(pygame.Surface((400, 300)))
        rect = t.rect(self.room, animated=False)
        self.assertEqual(len(self.room.huds), 1)
        for hud in self.room.huds:
            self.assertFalse(rect.colliderect(hud.rect))
        box = self.room.instructions.image.get_rect(bottomleft=(4, 296))
        self.assertFalse(rect.colliderect(box))
        self.assertTrue(pygame.Rect(0, 0, 400, 300).contains(rect))

    def test_every_room_draws_the_drawer_in_both_states(self):
        surf = pygame.Surface((400, 300))
        for rid in ("home", "arcade_floor", "prize_plaza"):
            room = goto_room(self.game, rid)
            for pl in room.players:
                pl.profile.claim_daily_reward()
            room.popup = None
            self.frames(30)
            for pinned, slide in ((False, 0.0), (True, 1.0)):
                self.tracker.pinned, self.tracker.slide = pinned, slide
                room.draw(surf)
                rect = self.tracker.rect(room, animated=False)
                for hud in room.huds:
                    self.assertFalse(rect.colliderect(hud.rect), (rid, pinned))


def get_font_width(text):
    from font import get_font
    return get_font().size(text)[0]



class StoryGameTests(unittest.TestCase):
    """The story must not disturb the rest of the hub."""

    def setUp(self):
        self.p = fresh("g", tickets=30)
        self.game = Game(session=session_of(self.p))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.room = goto_room(self.game, "arcade_floor")
        for _ in range(10):
            self.game.step([], DT)

    def test_rooms_all_share_the_one_story_director(self):
        for rid in ("home", "arcade_floor", "prize_plaza"):
            self.assertIs(goto_room(self.game, rid).hub.story, self.story)

    def test_a_minigame_still_pays_and_counts_toward_the_quest(self):
        self.story.manager.finish_opening()
        self.story.manager.handle("tour_arcade")
        self.story.manager.handle("met_mochi")
        machine = self.room.machines[0]
        self.p.record_game_played(machine.game_id)
        self.assertEqual(self.story.manager.active.id, "arcade_explorer")

    def test_closing_the_game_detaches_the_story_from_the_profile(self):
        story_manager = self.story.manager
        self.game.hub.close()
        before = story_manager.state.copy()
        self.p.record_game_played("late")
        self.assertEqual(story_manager.state, before)


if __name__ == "__main__":
    unittest.main()
