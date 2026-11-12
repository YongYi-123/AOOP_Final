"""Tests for the ARCADE TOUR: the one-time conversations the first time the players reach HOME, the ARCADE FLOOR and the
PRIZE PLAZA (Miao Meow's guided tour and her fond bickering with Mochi), and the quests built on them (THE GRAND TOUR,
MEET THE LOCALS). Covers the triggers, the dialogue, no replays, saving and reloading, two players, old saves, that the
vending machine's secret is still the only way to finish its quest, and that Miao Meow never gets stuck or blocks a machine.

Run headless from this folder:   python -m unittest test_tour -v
"""
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import tour as T  # noqa: E402
import story_dialogue as D  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from miao_meow import ARCADE, HOME, PLAZA, SPOTS, point_clear  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from quests import QUESTS, TOUR_EVENTS, QuestManager, migrate_story  # noqa: E402
from room_testing import goto_room  # noqa: E402
from tour import ARCADE_TOUR, HOME_TOUR, PLAZA_TOUR, TOURS  # noqa: E402

DT = 1 / 60
K = pygame


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def fresh(pid="a", name=None, **kw):
    return PlayerProfile(profile_id=pid, display_name=name or pid.upper(), tokens=12, tickets=30, **kw)


class TourBase(unittest.TestCase):
    """A real game start (the opening is over, tours are on) in which only the chosen tours are still unseen."""
    players = 1
    seen = ("tour_home",)               # tours already told when the test starts

    def setUp(self):
        self.profiles = [fresh("a", "Ann"), fresh("b", "Bo")][:self.players]
        self.start()

    def start(self, profiles=None):
        self.game = Game(session=LocalSession((profiles or self.profiles)[0]))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.story.opening_enabled = True
        self.m = self.story.manager
        self.m.finish_opening()
        for event in self.seen:
            self.m.handle(event)
        self.room = goto_room(self.game, "home")
        for p in self.profiles:
            p.claim_daily_reward()
        self.room.popup = None
        self.quiet()

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def quiet(self):
        """Let the NEW MAIN QUEST banner pass, as a player would."""
        for _ in range(900):
            if not self.story.banner.busy and not self.m.notifications:
                break
            self.frames(1)

    def go(self, room_id, wait=90, follow=True):
        """Enter a room. With `follow` the players then walk up to Miao Meow if she is leading them, as a player would."""
        self.quiet()
        self.room = goto_room(self.game, room_id)
        self.frames(wait)
        if follow:
            self.follow()
        return self.room

    def follow(self, limit=900):
        """Walk up to her while she leads (the conversation starts when somebody is close)."""
        brain = self.story.brain
        for _ in range(limit):
            if self.story.guide.leading is None or self.story.dialogue is not None:
                break
            if brain.arrived:
                for p in self.room.players:
                    p.x, p.y = brain.x - 40.0, brain.y + 2.0
                    p.stop()
            self.frames(5)
        self.frames(5)

    def confirm_through(self, key_code=K.K_e, limit=60):
        """Read a whole conversation: one press finishes a line's typing, the next goes on. Returns the lines shown."""
        shown = []
        for _ in range(limit):
            d = self.story.dialogue
            if d is None:
                break
            if d.closed:
                self.frames(1)
                continue
            shown.append(d.line)
            if not d.done_typing:
                self.frames(1, [key(key_code)])
            self.frames(1, [key(key_code)])
        self.frames(30)
        return shown


# ------------------------------------------------------------------ the text
class TextTests(unittest.TestCase):
    def test_the_plaza_scene_has_the_requested_bickering_in_order(self):
        wanted = [("MIAO MEOW", "And this is the Prize Plaza!"),
                  ("MIAO MEOW", "Where all your hard-earned Tickets become wonderful prizes!"),
                  ("MOCHI", "And where certain cats keep asking for free snacks."),
                  ("MIAO MEOW", "That was ONE time!"),
                  ("MOCHI", "It was this morning."),
                  ("MIAO MEOW", "...Okay, but I said please!"),
                  ("PLAYER", "Are you two always like this?"),
                  ("MOCHI", "Unfortunately."),
                  ("MIAO MEOW", "HEY!")]
        self.assertEqual([(l.speaker, l.text) for l in PLAZA_TOUR[:len(wanted)]], wanted)

    def test_mochi_then_explains_the_shop_kindly_and_miao_gets_the_last_word(self):
        tail = " ".join(l.text for l in PLAZA_TOUR[len(PLAZA_TOUR) - 5:] if l.speaker == "MOCHI").upper()
        self.assertIn("TICKETS", tail)
        self.assertIn("PRIZES", tail)
        self.assertEqual(PLAZA_TOUR[-1].speaker, "MIAO MEOW")
        self.assertEqual(PLAZA_TOUR[-1].text, "SNACK?!")

    def test_every_speaker_is_registered_and_has_a_portrait(self):
        for line in HOME_TOUR + ARCADE_TOUR + PLAZA_TOUR:
            self.assertIn(line.speaker, D.SPEAKERS, line)
        pygame.init()
        pygame.display.set_mode((400, 300))
        for mood in ("normal", "happy", "surprised", "gentle"):
            self.assertEqual(D.SPEAKERS["MOCHI"].face(mood, {}).get_size(), (44, 44))
        self.assertEqual(D.SPEAKERS["MOCHI"].name, "MOCHI")
        self.assertNotEqual(D.SPEAKERS["MOCHI"].accent, D.SPEAKERS["MIAO MEOW"].accent)

    def test_lines_fit_the_dialogue_box(self):
        from ui import wrap_text
        for line in HOME_TOUR + ARCADE_TOUR + PLAZA_TOUR:
            self.assertLessEqual(len(wrap_text(line.text, D.TEXT_W)), D.MAX_LINES, line.text)

    def test_the_conversations_are_short_and_never_name_the_secret_or_spoil_the_story(self):
        for name, lines, limit in (("home", HOME_TOUR, 6), ("arcade", ARCADE_TOUR, 8), ("plaza", PLAZA_TOUR, 16)):
            self.assertLessEqual(len(lines), limit, name)
        text = " ".join(l.text for l in HOME_TOUR + ARCADE_TOUR + PLAZA_TOUR).upper()
        for word in ("KONAMI", "KEVIN", "PLAYER_000", "VENDING", "CHEAT", "ARROW", "UP UP", "DOWN DOWN", "B A", "SECRET",
                     "MAGAZINE", "CODE", "TERMINAL"):
            self.assertNotIn(word, text, word)

    def test_the_plaza_tour_introduces_the_lucky_corner_and_capsules_and_points_back_to_the_arcade(self):
        text = " ".join(l.text for l in PLAZA_TOUR).upper()
        self.assertIn("LUCKY CORNER", text)
        self.assertIn("WIN MORE TOKENS", text)                        # Lucky Corner pays Tokens (it is played with them)
        self.assertIn("CAPSULE CORNER", text)
        self.assertIn("TAKES TICKETS", text)                          # capsules are bought with Tickets
        self.assertIn("ARCADE FLOOR", text)

    def test_mochi_is_kind_and_miao_is_never_bullied(self):
        mochi = " ".join(l.text for l in PLAZA_TOUR if l.speaker == "MOCHI").lower()
        for rude in ("stupid", "idiot", "shut up", "hate", "dumb", "go away"):
            self.assertNotIn(rude, mochi)
        self.assertIn("best greeter", mochi)
        self.assertIn("snack under the counter", mochi)

    def test_the_tours_cover_home_arcade_and_plaza_with_their_own_events(self):
        self.assertEqual(set(TOURS), {HOME, ARCADE, PLAZA})
        self.assertEqual({t.event for t in TOURS.values()}, set(TOUR_EVENTS))
        self.assertEqual(TOURS[ARCADE].event, "tour_arcade")
        self.assertEqual(TOURS[PLAZA].event, "met_mochi")


# ------------------------------------------------------------------ the quests
class QuestTests(unittest.TestCase):
    def test_the_five_quests_in_the_requested_order_then_chapter_01(self):
        self.assertEqual([q.title.upper() for q in QUESTS[:5]],
                         ["THE GRAND TOUR", "MEET THE LOCALS", "GIVE IT A TRY", "EARN YOUR REWARDS",
                          "CHECK THE VENDING MACHINE"])
        self.assertEqual(QUESTS[5].id, "ch1_secret_item")

    def test_the_tour_quests_wait_for_the_conversations_not_for_any_other_action(self):
        self.assertEqual(QUESTS[0].trigger, ("sticky", "tour_arcade"))
        self.assertEqual(QUESTS[1].trigger, ("sticky", "met_mochi"))
        self.assertEqual(QUESTS[4].trigger, ("sticky", "vending_secret"))

    def test_hints_only_point_at_places_and_never_at_the_secret(self):
        for q in QUESTS[:4]:
            text = " ".join(q.hints).upper()
            for word in ("KONAMI", "CODE", "ARROW", "UP UP", "MAGAZINE", "COUCH", "CHEAT", "VENDING"):
                self.assertNotIn(word, text, (q.id, word))
        self.assertIn("LEFT DOOR", " ".join(QUESTS[0].hints).upper())
        self.assertIn("RIGHT DOOR", " ".join(QUESTS[1].hints).upper())

    def test_the_arcade_quests_say_they_happen_on_the_arcade_floor(self):
        for quest_id in ("arcade_explorer", "earn_some_rewards"):
            q = next(x for x in QUESTS if x.id == quest_id)
            self.assertIn("ARCADE FLOOR", q.objective.upper(), quest_id)
            self.assertIn("ARCADE FLOOR", q.hud.upper(), quest_id)
        self.assertIn("ARCADE FLOOR", " ".join(QUESTS[2].hints).upper())

    def test_no_new_rewards_were_added(self):
        self.assertEqual([q.reward_tokens for q in QUESTS], [0] * len(QUESTS))

    def test_vending_quest_needs_the_real_secret_after_everything_else_is_done(self):
        p = fresh()
        m = QuestManager(LocalSession([p]))
        m.finish_opening()
        m.handle("tour_arcade")
        m.handle("met_mochi")
        for g in ("a", "b", "c"):
            m.handle("game_played", g)
        p.add_tickets(5)
        self.assertEqual(m.active.id, "check_the_vending_machine")
        for event in TOUR_EVENTS:                                    # no tour event, however often fired, completes it
            m.handle(event)
        self.assertEqual(m.active.id, "check_the_vending_machine")
        m.handle("vending_secret")
        self.assertEqual(m.active.id, "ch1_secret_item")


# ------------------------------------------------------------------ first entry
class FirstEntryTests(TourBase):
    def test_the_arcade_floor_conversation_starts_on_first_entry_and_completes_quest_one(self):
        self.assertEqual(self.m.active.id, "grand_tour")
        self.go(ARCADE)
        self.assertIsNotNone(self.story.dialogue)
        shown = self.confirm_through()
        self.assertEqual([l.text for l in shown], [l.text for l in ARCADE_TOUR])
        self.assertTrue(self.m.state["flags"]["tour_arcade"])
        self.assertEqual(self.m.completed_ids, ["grand_tour"])
        self.assertEqual(self.m.active.id, "meet_the_locals")

    def test_the_plaza_conversation_is_the_whole_mochi_scene_and_completes_quest_two(self):
        self.m.handle("tour_arcade")
        self.quiet()
        self.go(PLAZA)
        self.assertIsNotNone(self.story.dialogue)
        shown = self.confirm_through()
        self.assertEqual([(l.speaker, l.text) for l in shown], [(l.speaker, l.text) for l in PLAZA_TOUR])
        self.assertTrue(self.m.state["flags"]["met_mochi"])
        self.assertEqual(self.m.active.id, "arcade_explorer")

    def test_home_is_toured_once_after_the_opening_and_its_banner(self):
        self.m.state["flags"].pop("tour_home")
        self.go(HOME, 60)
        self.assertIsNotNone(self.story.dialogue)
        shown = self.confirm_through()
        self.assertEqual([l.text for l in shown], [l.text for l in HOME_TOUR])
        self.assertTrue(self.m.state["flags"]["tour_home"])
        self.assertEqual(self.m.active.id, "grand_tour")              # (home is part of the tour, not its end)

    def test_nothing_starts_without_a_real_game_start(self):
        self.story.opening_enabled = False
        self.go(ARCADE, 200)
        self.assertIsNone(self.story.dialogue)

    def test_nothing_starts_while_the_quest_banner_is_still_showing_or_a_popup_is_open(self):
        self.m.notifications.append(__import__("quests").Notification("quest", QUESTS[0]))
        self.go(ARCADE, 30)
        self.assertIsNone(self.story.dialogue)                         # the banner has not been shown yet
        self.quiet()
        self.frames(100)
        self.follow()
        self.assertIsNotNone(self.story.dialogue)

    def test_nothing_starts_in_the_middle_of_a_transition(self):
        self.room = room = goto_room(self.game, ARCADE)
        room.arrival_grace = 5.0
        self.frames(120)
        self.assertIsNone(self.story.dialogue)
        self.assertIsNone(self.story.guide.leading)                    # not even the walk
        room.arrival_grace = 0.0
        self.frames(120)
        self.assertIsNotNone(self.story.guide.leading)
        self.follow()
        self.assertIsNotNone(self.story.dialogue)

    def test_the_tour_waits_for_the_players_to_look_around_first(self):
        self.go(ARCADE, 20, follow=False)
        self.assertIsNone(self.story.guide.leading)                    # a moment to look around first
        self.assertIsNone(self.story.dialogue)
        self.frames(60)
        self.assertIsNotNone(self.story.guide.leading)                 # then she sets off, nobody is stopped


# ------------------------------------------------------------------ Miao Meow leads the way
class LeadingTests(TourBase):
    def lead_start(self, room_id=ARCADE):
        self.go(room_id, 80, follow=False)
        self.assertIsNotNone(self.story.guide.leading)

    def test_she_runs_in_through_the_door_and_walks_to_the_stage_while_the_players_stay_free(self):
        self.story.brain.place(HOME, SPOTS[HOME]["bed"])
        self.lead_start()
        brain = self.story.brain
        self.assertTrue(brain.is_in(ARCADE))
        start = (brain.x, brain.y)
        self.assertGreater(start[0], 300)                              # she came in by the right-hand door
        self.assertFalse(self.story.locked)                            # no cutscene: the players keep the controls
        self.assertIsNone(self.story.dialogue)
        p = self.room.players[0]
        x0 = p.x
        self.frames(1, [key(K.K_a)])
        self.frames(20)
        self.assertNotEqual(p.x, x0)                                   # they can walk
        self.frames(120)
        self.assertLess(brain.x, start[0])                             # she has moved on towards the middle

    def test_she_waits_at_the_stage_and_the_conversation_starts_when_somebody_walks_up(self):
        self.lead_start()
        brain = self.story.brain
        for p in self.room.players:                                    # far from her
            p.x, p.y = 40.0, 250.0
            p.stop()
        self.frames(60 * 6)
        self.assertTrue(brain.arrived)
        self.assertIsNone(self.story.dialogue)                         # nobody is near: she just waits
        self.assertEqual((round(brain.x), round(brain.y)), tuple(SPOTS[ARCADE]["centre"]))
        self.follow()
        self.assertIsNotNone(self.story.dialogue)

    def test_pressing_e_on_her_while_she_leads_starts_the_tour_at_once(self):
        self.lead_start()
        brain = self.story.brain
        self.frames(30)
        self.story.talk_to_miao(self.room)
        self.assertIsNotNone(self.story.dialogue)
        self.assertEqual(self.story.dialogue.lines[0].text, ARCADE_TOUR[0].text)
        self.assertTrue(brain.is_in(ARCADE))

    def test_if_nobody_comes_she_starts_anyway_after_a_generous_wait(self):
        self.lead_start()
        for p in self.room.players:
            p.x, p.y = 40.0, 250.0
            p.stop()
        self.frames(int((T.LEAD_WAIT + 12) * 60))
        self.assertIsNotNone(self.story.dialogue)

    def test_leaving_the_room_drops_the_walk_and_the_tour_is_told_next_visit(self):
        self.lead_start()
        self.go(HOME, 30, follow=False)
        self.assertIsNone(self.story.guide.leading)
        self.assertFalse(self.story.brain.scripted)
        self.assertNotIn("tour_arcade", self.m.state.get("flags", {}))
        self.go(ARCADE)
        self.assertIsNotNone(self.story.dialogue)
        self.confirm_through()
        self.assertTrue(self.m.state["flags"]["tour_arcade"])

    def test_she_leads_in_the_plaza_to_a_spot_by_the_prize_counter(self):
        self.m.handle("tour_arcade")
        self.lead_start(PLAZA)
        self.follow()
        self.assertIsNotNone(self.story.dialogue)
        self.assertEqual((round(self.story.brain.x), round(self.story.brain.y)), tuple(SPOTS[PLAZA]["left"]))

    def test_home_has_no_walk_she_is_already_there(self):
        self.m.state["flags"].pop("tour_home")
        self.go(HOME, 80, follow=False)
        self.assertIsNone(self.story.guide.leading)
        self.assertIsNotNone(self.story.dialogue)

    def test_while_she_leads_every_machine_can_still_be_reached_and_used(self):
        self.lead_start()
        room = self.room
        for machine in room.machines[:3]:
            player = room.players[0]
            player.x, player.y = float(machine.zone.centerx), float(machine.zone.bottom - 2)
            player.stop()
            self.frames(8)
            self.assertIs(player.nearby, machine, machine.id)


# ------------------------------------------------------------------ no replays, saves
class NoReplayTests(TourBase):
    def test_re_entering_rooms_never_replays_a_conversation(self):
        self.go(ARCADE)
        self.confirm_through()
        self.go(HOME)
        self.go(ARCADE, 200)
        self.assertIsNone(self.story.dialogue)
        self.go(PLAZA)
        self.confirm_through()
        for room_id in (HOME, ARCADE, PLAZA, HOME, PLAZA):
            self.go(room_id, 200)
            self.assertIsNone(self.story.dialogue, room_id)
        self.assertEqual(self.story.guide.played, ["tour_arcade", "met_mochi"])

    def test_the_flags_are_saved_in_the_profile_and_a_restart_does_not_replay(self):
        self.go(ARCADE)
        self.confirm_through()
        story = self.profiles[0].story
        self.assertTrue(story["flags"]["tour_arcade"])
        self.assertEqual(story["completed"], ["grand_tour"])
        self.game.quit()
        again = Game(session=LocalSession([self.profiles[0]]))
        self.addCleanup(again.quit)
        story2 = again.hub.story
        story2.opening_enabled = True
        self.assertTrue(story2.manager.state["flags"]["tour_arcade"])
        self.assertEqual(story2.manager.active.id, "meet_the_locals")
        goto_room(again, ARCADE)
        for _ in range(240):
            again.step([], DT)
        self.assertIsNone(story2.dialogue)

    def test_a_profile_written_to_disk_and_read_back_keeps_the_tour(self):
        path = os.path.join(tempfile.mkdtemp(), "p.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(path), True)
        self.go(ARCADE)
        self.confirm_through()
        ProfileStore(path).save(self.profiles[0])
        loaded = ProfileStore(path).load()
        m = QuestManager(LocalSession([loaded]))
        self.assertEqual(m.completed_ids, ["grand_tour"])
        self.assertTrue(m.state["flags"]["tour_arcade"])
        self.assertTrue(m.opening_done)


# ------------------------------------------------------------------ exploring early
class EarlyExplorationTests(TourBase):
    def test_visiting_the_plaza_first_plays_it_and_quest_two_completes_the_moment_it_is_reached(self):
        self.assertEqual(self.m.active.id, "grand_tour")
        self.go(PLAZA)
        self.confirm_through()
        self.assertEqual(self.m.completed_ids, [])                       # quest one still waits for the arcade floor
        self.assertTrue(self.m.state["flags"]["met_mochi"])
        self.go(ARCADE)
        self.confirm_through()
        self.assertEqual(self.m.completed_ids, ["grand_tour", "meet_the_locals"])
        self.assertEqual(self.m.active.id, "arcade_explorer")

    def test_only_the_last_step_of_a_run_is_announced(self):
        self.go(PLAZA)
        self.confirm_through()
        self.m.notifications.clear()
        self.go(ARCADE)
        self.confirm_through()
        quests = [(n.kind, n.quest.id) for n in self.m.notifications] + \
                 ([("banner", self.story.banner.current.quest.id)] if self.story.banner.current else [])
        self.assertLessEqual(len(quests), 1)

    def test_machines_played_before_the_tour_still_count_towards_give_it_a_try(self):
        for g in ("a", "b"):
            self.m.handle("game_played", g)
        self.go(ARCADE)
        self.confirm_through()
        self.go(PLAZA)
        self.confirm_through()
        self.assertEqual(self.m.active.id, "arcade_explorer")
        self.assertEqual(self.m.progress(), (2, 3))


# ------------------------------------------------------------------ old saves
class OldSaveTests(unittest.TestCase):
    def test_a_save_that_was_past_get_your_bearings_skips_the_whole_tour(self):
        p = fresh()
        p.set_story({"opening_done": True, "completed": ["get_your_bearings"], "stats": {"played": ["x"]}})
        m = QuestManager(LocalSession([p]))
        self.assertEqual(m.completed_ids, ["grand_tour", "meet_the_locals"])
        self.assertEqual(m.active.id, "arcade_explorer")
        for event in TOUR_EVENTS:
            self.assertTrue(m.state["flags"][event])
        self.assertFalse(m.notifications)

    def test_a_save_with_later_quests_done_keeps_them_and_is_not_sent_back(self):
        p = fresh()
        p.set_story({"opening_done": True, "completed": ["get_your_bearings", "arcade_explorer", "earn_some_rewards"],
                     "stats": {"played": ["a", "b", "c"]}})
        m = QuestManager(LocalSession([p]))
        self.assertEqual(m.completed_ids, ["grand_tour", "meet_the_locals", "arcade_explorer", "earn_some_rewards"])
        self.assertEqual(m.active.id, "check_the_vending_machine")

    def test_a_save_that_already_found_the_secret_goes_straight_to_chapter_01(self):
        p = fresh()
        p.set_story({"opening_done": True, "completed": ["get_your_bearings", "arcade_explorer", "earn_some_rewards"],
                     "flags": {"vending_secret": True}})
        m = QuestManager(LocalSession([p]))
        self.assertEqual(m.active.id, "ch1_secret_item")

    def test_a_save_still_at_the_first_step_gets_the_tour(self):
        p = fresh()
        p.set_story({"opening_done": True})
        m = QuestManager(LocalSession([p]))
        self.assertEqual(m.active.id, "grand_tour")
        self.assertNotIn("tour_arcade", m.state.get("flags", {}))

    def test_a_veteran_without_a_story_never_sees_the_tour(self):
        p = fresh(total_games_played=5, lifetime_tickets_earned=40)
        m = QuestManager(LocalSession([p]))
        self.assertEqual(m.active.id, "check_the_vending_machine")
        for event in TOUR_EVENTS:
            self.assertTrue(m.state["flags"][event])

    def test_migration_is_idempotent_and_leaves_a_new_style_story_alone(self):
        new = {"opening_done": True, "completed": ["grand_tour"], "flags": {"tour_arcade": True}}
        self.assertEqual(migrate_story(new), new)
        old = {"opening_done": True, "completed": ["get_your_bearings"]}
        once = migrate_story(old)
        self.assertEqual(migrate_story(once), once)

    def test_an_old_save_in_a_real_game_never_replays_a_conversation(self):
        p = fresh()
        p.set_story({"opening_done": True, "completed": ["get_your_bearings", "arcade_explorer"]})
        game = Game(session=LocalSession([p]))
        self.addCleanup(game.quit)
        game.hub.story.opening_enabled = True
        for room_id in (HOME, ARCADE, PLAZA):
            goto_room(game, room_id)
            for _ in range(240):
                game.step([], DT)
            self.assertIsNone(game.hub.story.dialogue, room_id)


# ------------------------------------------------------------------ another saved profile
class OtherSavedProfileTourTests(TourBase):
    players = 2

    def test_the_tour_belongs_to_the_playing_profile_and_the_other_save_is_untouched(self):
        self.go(ARCADE)
        self.assertIsNotNone(self.story.dialogue)
        self.assertIs(self.room.modal_owner, self.game.session.primary.avatar)
        self.confirm_through()
        a, b = self.profiles
        self.assertTrue(a.story["flags"]["tour_arcade"])
        self.assertEqual(a.story["completed"], ["grand_tour"])
        self.assertEqual(b.story, {})

    def test_the_old_second_player_keys_do_not_advance_the_talk(self):
        self.go(ARCADE)
        before = self.story.dialogue.index
        self.frames(80)
        for k in (pygame.K_RCTRL, pygame.K_o, pygame.K_KP0):
            self.frames(1, [key(k)])
        self.assertEqual(self.story.dialogue.index, before)
        self.confirm_through()

    def test_the_plaza_scene_plays_once(self):
        self.go(PLAZA)
        self.confirm_through()
        self.assertEqual(self.story.guide.played, ["met_mochi"])
        self.go(HOME)
        self.go(PLAZA, 200)
        self.assertIsNone(self.story.dialogue)

    def test_an_advanced_profile_skips_what_its_story_already_saw_and_the_other_keeps_its_own(self):
        a = fresh("c")
        a.set_story({"opening_done": True, "completed": ["grand_tour", "meet_the_locals"],
                     "flags": {"tour_home": True, "tour_arcade": True, "met_mochi": True}})
        b = fresh("d")
        game = Game(session=LocalSession(a))
        self.addCleanup(game.quit)
        game.hub.story.opening_enabled = True
        goto_room(game, PLAZA)
        for _ in range(240):
            game.step([], DT)
        self.assertIsNone(game.hub.story.dialogue)
        self.assertEqual(b.story, {})                                 # never merged into another profile


# ------------------------------------------------------------------ Miao Meow never gets stuck
class MiaoBehaviourTests(TourBase):
    def test_she_is_brought_to_the_room_if_she_was_elsewhere_and_given_back_afterwards(self):
        brain = self.story.brain
        brain.place(HOME, SPOTS[HOME]["bed"])
        self.go(ARCADE)
        self.assertTrue(brain.is_in(ARCADE))
        self.assertTrue(brain.scripted)                                 # held only for the talk
        self.confirm_through()
        self.assertFalse(brain.scripted)
        self.assertNotEqual(brain.state, "script")
        self.assertIsNone(self.story.dialogue)

    def test_the_tour_spots_are_open_floor_outside_every_machine_prompt_area(self):
        for room_id, spot_name in ((ARCADE, "right"), (PLAZA, "left"), (HOME, "hub")):
            room = goto_room(self.game, room_id)
            x, y = SPOTS[room_id][spot_name]
            self.assertTrue(point_clear(x, y, room.solids, 2), room_id)
            for thing in room.interactables:
                if type(thing).__name__ == "MiaoMeow":
                    continue
                self.assertFalse(thing.zone.collidepoint(x, y), (room_id, type(thing).__name__))

    def test_after_the_conversation_the_players_can_walk_up_to_every_machine(self):
        self.go(ARCADE)
        self.confirm_through()
        self.frames(30)
        room = self.room
        player = room.players[0]
        machine = room.machines[0]
        player.x, player.y = float(machine.zone.centerx), float(machine.zone.bottom - 2)
        player.stop()
        self.frames(10)
        self.assertIs(player.nearby, machine)
        self.assertFalse(self.story.locked)
        self.assertIsNone(self.story.modal)

    def test_she_does_not_stay_in_a_scripted_state_when_the_conversation_is_cut_short(self):
        self.go(ARCADE)
        brain = self.story.brain
        self.assertTrue(brain.scripted)
        self.story.dialogue = None                                      # (any way a dialogue can disappear)
        self.frames(5)
        self.assertFalse(brain.scripted)
        self.assertIsNone(self.story.guide.playing)
        self.assertNotIn("tour_arcade", self.m.state.get("flags", {}))   # not played: it will be told next time

    def test_talking_to_her_afterwards_is_the_normal_hint_chat(self):
        self.go(ARCADE)
        self.confirm_through()
        self.story.talk_to_miao(self.room)
        self.assertIsNotNone(self.story.dialogue)
        self.assertEqual(self.story.dialogue.lines[1].text, QUESTS[1].hints[0])


# ------------------------------------------------------------------ the screen
class ScreenTests(TourBase):
    def test_the_box_hides_the_corner_hud_and_prompts_and_the_tracker_slides_away(self):
        self.go(ARCADE)
        self.assertTrue(self.story.hides_hud)
        self.assertTrue(self.story.dialogue.hides_hud)
        self.assertIsNotNone(self.room.modal)
        surf = pygame.Surface((400, 300))
        self.room.draw(surf)
        self.frames(30)
        self.assertEqual(self.story.tracker.appear, 0)

    def test_every_page_of_the_conversation_draws_for_both_speakers_without_error(self):
        self.go(PLAZA)
        surf = pygame.Surface((400, 300))
        for _ in range(len(PLAZA_TOUR) * 2 + 2):
            if self.story.dialogue is None:
                break
            self.frames(80)
            self.room.draw(surf)
            self.frames(1, [key(K.K_e)])

    def test_the_box_never_covers_the_speakers(self):
        self.go(PLAZA)
        d = self.story.dialogue
        brain = self.story.brain
        for p in self.room.players:
            self.assertFalse(d.box.collidepoint(int(p.x), int(p.y)))
        self.assertFalse(d.box.collidepoint(int(brain.x), int(brain.y)))


if __name__ == "__main__":
    unittest.main()
