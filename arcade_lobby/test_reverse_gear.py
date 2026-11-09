"""Secret Item 01 inside the Arcade Hub: the Retro Racer scene reports the Reverse Gear through the existing story event, the
shared main quest saves it (Secret Items 1/3), it is never given twice, quitting or failing gives nothing, the music is never
left low, the player lands back in the arcade, and Miao Meow / Mochi talk about it at the right moments.

Run headless from this folder:   python -m unittest test_reverse_gear -v
"""
import os
import shutil
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import mochi_chat as C  # noqa: E402
import story as ST  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from quest_ui import ObjectiveTracker, QuestLogUI  # noqa: E402
from quests import MIAO_REVERSE_ROAD, SECRET_ITEM_RETRO_RACER, QuestManager  # noqa: E402
from retro_racer_scene import RetroRacerScene  # noqa: E402
from room_testing import goto_room  # noqa: E402

DT = 1 / 60
K = pygame


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def keyup(k):
    return pygame.event.Event(pygame.KEYUP, key=k, mod=0)


class RacerHubBase(unittest.TestCase):
    players = 1

    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="ra", display_name="Ann", tokens=20, tickets=50),
                         PlayerProfile(profile_id="rb", display_name="Bo", tokens=20, tickets=50)][:self.players]
        self.start()

    def start(self):
        self.game = Game(session=LocalSession(self.profiles[0]))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.m = self.story.manager
        self.m.finish_opening()

    # ------------------------------------------------------------ driving the real scene
    def launch(self):
        room = goto_room(self.game, "arcade_floor")
        machine = next(m for m in room.machines if m.id == "retro_racer")
        session = self.game.session
        player = session.primary
        scene = RetroRacerScene(self.game, machine)
        scene.attach_players([player])
        self.game.scenes.push(scene)
        for _ in range(1200):                               # wipe, loading card, first-time build, title screen
            self.game.step([], DT)
            if scene.racer is not None and scene.racer.state.name == "TITLE" and not self.game.scenes.transitioning:
                break
        self.assertIsNotNone(scene.racer, scene.error)
        self.scene = scene
        self.racer = scene.racer
        return scene

    def begin_race(self):
        r = self.racer
        r.start_race()
        r.begin_playing()
        r.secret_events.clear()

    def frames(self, n=1, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def scene_frames(self, seconds, events=()):
        """Frames through the scene only (no drawing), the quick way to pass racer time."""
        for i in range(round(seconds / DT)):
            for e in (events if i == 0 else ()):
                self.scene.handle_event(e)
            self.scene.update(DT)

    def move_key(self, direction):
        scheme = self.scene.input.scheme
        want = {"up": (0, -1), "down": (0, 1)}[direction]
        return next(k for k, d in scheme.move.items() if d == want)

    def hold(self, k):
        self.scene.handle_event(key(k))

    def release(self, k):
        self.scene.handle_event(keyup(k))

    def to_secret(self):
        """The real secret: still 20 s in a race, then the brake held until the car really backs up."""
        self.begin_race()
        self.scene_frames(20.3)
        down = self.move_key("down")
        self.hold(down)
        for _ in range(60 * 8):
            self.scene.update(DT)
            if self.racer.secret is not None:
                break
        self.release(down)
        self.assertIsNotNone(self.racer.secret)
        return self.racer.secret

    def finish_run(self, run=None):
        """From the cutscene onwards: skip it and put the car just before the finish with the gates collected, then drive in."""
        run = run or self.racer.secret
        run.skip()
        self.scene_frames(3.0)
        self.assertEqual(run.phase, run.DRIVE)
        run.checkpoints = 3
        run.player.distance = run.road.finish_z - 4000 - run.offset
        run.player.z = run.player.distance
        run.player.speed = 5000.0
        up = self.move_key("up")
        self.hold(up)
        for _ in range(60 * 20):
            self.scene.update(DT)
            if run.phase == run.REWARD:
                break
        self.release(up)
        self.assertEqual(run.phase, run.REWARD)
        return run


class TheItemTests(RacerHubBase):
    def test_finishing_the_secret_road_records_the_item_in_the_shared_story(self):
        self.launch()
        self.assertEqual(self.m.secret_items, 0)
        self.to_secret()
        self.finish_run()
        self.assertTrue(self.m.has_secret_item(SECRET_ITEM_RETRO_RACER))
        self.assertEqual(self.m.secret_items, 1)
        self.assertEqual(self.m.state["stats"]["secret_items"], [SECRET_ITEM_RETRO_RACER])

    def test_it_is_only_given_once_however_often_the_road_is_driven(self):
        self.launch()
        self.to_secret()
        self.finish_run()
        self.racer.reset()
        self.begin_race()
        self.assertTrue(self.racer.gear_owned)                 # the host says it is already found
        self.to_secret()
        run = self.finish_run()
        self.assertFalse(run.first_time)
        self.assertEqual(self.m.secret_items, 1)
        self.assertEqual(self.m.state["stats"]["secret_items"], [SECRET_ITEM_RETRO_RACER])

    def test_quitting_or_failing_the_road_gives_nothing(self):
        self.launch()
        run = self.to_secret()
        run.skip()
        self.scene_frames(3.0)
        run._fail("TEST")
        self.scene_frames(2.0)
        self.racer.handle_event(key(K.K_p))
        self.racer.handle_event(key(K.K_BACKSPACE))            # quit to the menu
        self.assertEqual(self.m.secret_items, 0)
        self.assertFalse(self.m.has_secret_item(SECRET_ITEM_RETRO_RACER))
        self.assertFalse(self.racer.gear_owned)

    def test_a_secret_road_left_by_closing_the_machine_gives_nothing(self):
        self.launch()
        self.to_secret()
        self.scene._leave()
        self.frames(60)
        self.assertEqual(self.m.secret_items, 0)

    def test_it_can_be_found_before_the_vending_secret_and_mochi_stays_silent(self):
        self.assertFalse(self.m.secret_interface_unlocked)
        self.launch()
        self.to_secret()
        self.finish_run()
        self.assertEqual(self.m.secret_items, 1)
        self.assertIsNone(self.m.mochi_story_stage)             # no chat option until the real Secret Interface opens
        self.assertEqual(C.chat_options(self.m.mochi_story_stage), [])
        self.m.handle("vending_secret")
        self.assertEqual(self.m.mochi_story_stage, "found")     # ... and then she goes straight to the found-talk
        self.assertIn(C.RACE, [label for label, _ in C.chat_options(self.m.mochi_story_stage)])
        self.assertNotIn(C.HINT, [label for label, _ in C.chat_options(self.m.mochi_story_stage)])

    def test_the_quest_log_and_tracker_show_one_of_three(self):
        for event, k in (("tour_arcade", None), ("met_mochi", None), ("game_played", "a"), ("game_played", "b"),
                         ("game_played", "c"), ("tickets_earned", None), ("vending_secret", None)):
            self.m.handle(event, k)
        self.assertEqual(self.m.active.id, "the_way_out")
        self.launch()
        self.to_secret()
        self.finish_run()
        detail = ObjectiveTracker(self.m)._detail()
        self.assertEqual(detail[0][0], "ITEMS 1/3")
        log = QuestLogUI(self.m, self.profiles[0])
        shown = []
        with mock.patch("quest_ui.draw_text", lambda surf, text, *a, **k: shown.append(str(text))):
            log.draw(pygame.Surface((384, 300)))
        self.assertIn("1/3", shown)

    def test_the_racer_is_told_when_the_gear_is_already_found(self):
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        self.launch()
        self.assertTrue(self.racer.gear_owned)


class SaveAndSessionTests(RacerHubBase):
    def test_the_item_survives_a_save_and_reload(self):
        self.launch()
        self.to_secret()
        self.finish_run()
        path = os.path.join(tempfile.mkdtemp(), "p.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(path), True)
        ProfileStore(path).save(self.profiles[0])
        again = QuestManager(LocalSession(ProfileStore(path).load()))
        self.assertTrue(again.has_secret_item(SECRET_ITEM_RETRO_RACER))
        self.assertEqual(again.secret_items, 1)

    def test_a_reloaded_game_remembers_it_and_does_not_hand_it_out_again(self):
        self.launch()
        self.to_secret()
        self.finish_run()
        self.game.quit()
        self.start()
        self.assertEqual(self.m.secret_items, 1)
        self.launch()
        self.assertTrue(self.racer.gear_owned)
        self.to_secret()
        self.finish_run()
        self.assertEqual(self.m.secret_items, 1)

    def test_an_old_save_without_any_story_loads_and_has_no_item(self):
        old = PlayerProfile(profile_id="old", display_name="Old", tokens=3, tickets=9)
        m = QuestManager(LocalSession(old))
        self.assertEqual(m.secret_items, 0)
        self.assertFalse(m.has_secret_item(SECRET_ITEM_RETRO_RACER))
        self.assertIsNone(m.mochi_story_stage)

    def test_an_old_save_whose_story_has_other_items_keeps_them(self):
        self.m.handle("secret_item_found", "gem_cyan")
        self.launch()
        self.to_secret()
        self.finish_run()
        self.assertEqual(self.m.secret_items, 2)


class OtherSavedProfileTests(RacerHubBase):
    """A second profile is saved but never played: the secret belongs to the playing profile alone."""
    players = 2

    def test_finding_it_updates_the_playing_profiles_story_only(self):
        self.launch()
        self.to_secret()
        self.finish_run()
        self.assertEqual(self.m.secret_items, 1)
        self.assertEqual(self.profiles[0].story["stats"]["secret_items"], [SECRET_ITEM_RETRO_RACER])
        self.assertEqual(self.profiles[1].story, {})

    def test_the_old_second_player_keys_cannot_steer_the_secret(self):
        self.launch()
        self.to_secret()
        before = self.racer.secret.t
        for k in (pygame.K_o, pygame.K_RCTRL, pygame.K_RSHIFT):
            self.scene.handle_event(key(k))
        self.assertEqual(self.racer.secret.t, before)


class ReturnToTheArcadeTests(RacerHubBase):
    def test_the_reward_screen_returns_to_the_arcade_with_the_music_restored(self):
        self.launch()
        run = self.to_secret()
        self.scene_frames(1.5)
        self.assertLess(self.scene.music_duck, 1.0)             # the hub is asked to lower the music in the cutscene
        self.finish_run(run)
        self.scene_frames(2.7)
        self.scene.handle_event(key(self.scene.input.scheme.interact[0]))
        self.frames(120)
        room = self.game.hub.room("arcade_floor")
        self.assertIs(self.game.scenes.current, room)
        self.assertEqual(self.game.audio.duck, 1.0)
        self.assertEqual(self.racer.music_duck, 1.0)
        self.assertIsNone(self.scene.music_duck)

    def test_leaving_in_the_middle_of_the_cutscene_never_leaves_the_music_low(self):
        self.launch()
        self.to_secret()
        self.scene_frames(2.5)
        self.assertLess(self.scene.music_duck, 0.5)
        self.scene._leave()
        self.frames(120)
        self.assertIs(self.game.scenes.current, self.game.hub.room("arcade_floor"))
        self.assertEqual(self.game.audio.duck, 1.0)

    def test_a_normal_visit_does_not_touch_the_music_level(self):
        self.launch()
        self.begin_race()
        self.scene_frames(3.0)
        self.assertIsNone(self.scene.music_duck)

    def test_a_secret_run_earns_no_tickets_for_the_visit(self):
        self.launch()
        self.to_secret()
        self.finish_run()
        self.assertEqual(self.scene.get_reward().tickets_earned, 0)


class StoryReactionTests(RacerHubBase):
    def talk(self):
        room = goto_room(self.game, "home")
        self.story.talk_to_miao(room, room.player)
        d = self.story.dialogue
        self.assertIsNotNone(d)
        return d

    def close_dialogue(self):
        d = self.story.dialogue
        for _ in range(len(d.lines) * 2 + 2):
            if self.story.dialogue is None:
                break
            for _ in range(80):
                self.game.step([], DT)
            self.game.step([key(K.K_RETURN)], DT)
        self.game.step([], DT)

    def test_miao_meow_has_nothing_to_say_about_it_before_the_item(self):
        d = self.talk()
        self.assertNotIn("SECRET ROAD", " ".join(l.text.upper() for l in d.lines))

    def test_after_the_item_she_tells_the_secret_road_talk_once(self):
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        d = self.talk()
        self.assertEqual([(l.speaker, l.text) for l in d.lines], [
            ("MIAO MEOW", "YOU FOUND A SECRET ROAD?!"),
            ("PLAYER", "Yeah... apparently driving backwards was the answer."),
            ("MIAO MEOW", "BACKWARDS?!"),
            ("MIAO MEOW", "Hahaha! Humans are so weird!"),
            ("MIAO MEOW", "Can we try it together next time?")])
        self.assertFalse(self.m.state.get("flags", {}).get(MIAO_REVERSE_ROAD))      # told, not yet finished
        self.close_dialogue()
        self.assertTrue(self.m.state["flags"][MIAO_REVERSE_ROAD])
        again = self.talk()
        self.assertNotIn("SECRET ROAD", " ".join(l.text.upper() for l in again.lines))

    def test_the_talk_is_saved_and_not_repeated_after_a_reload(self):
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        self.talk()
        self.close_dialogue()
        self.game.quit()
        self.start()
        d = self.talk()
        self.assertNotIn("SECRET ROAD", " ".join(l.text.upper() for l in d.lines))

    def test_she_is_never_moved_by_it_and_kevin_is_never_named(self):
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        brain = self.story.brain
        brain.place("home", (100, 100))
        before = (brain.room_id, brain.x, brain.y)
        self.talk()
        self.assertEqual((brain.room_id, brain.x, brain.y), before)
        text = " ".join(l.text for l in ST.REVERSE_ROAD_CHAT).lower()
        self.assertNotIn("kevin", text)

    def test_the_miao_flag_cannot_be_set_without_the_item(self):
        self.m.handle(MIAO_REVERSE_ROAD)
        self.assertFalse(self.m.state.get("flags", {}).get(MIAO_REVERSE_ROAD))

    def test_mochi_updates_to_the_found_talk_once_the_interface_is_open(self):
        self.m.handle("vending_secret")
        self.assertEqual(self.m.mochi_story_stage, "new")
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        self.assertEqual(self.m.mochi_story_stage, "found")


class RealKeyFlowTest(RacerHubBase):
    def test_the_whole_secret_through_real_key_events_and_the_full_frame_loop(self):
        """Still 20 s, then DOWN held: all through game.step (drawing included), one real key event per press."""
        self.launch()
        self.begin_race()
        run_events = []
        for _ in range(round(20.3 / DT)):
            self.game.step([], DT)
        down = self.move_key("down")
        self.game.step([key(down)], DT)
        for _ in range(60 * 8):
            self.game.step([], DT)
            if self.racer.secret is not None:
                break
        self.game.step([keyup(down)], DT)
        self.assertIsNotNone(self.racer.secret)
        self.assertEqual(self.racer.state.name, "SECRET")
        for _ in range(60 * 2):
            self.game.step([], DT)                               # (the cutscene draws through the scene, scaled to the window)
        self.assertLess(self.scene.music_duck or 1.0, 1.0)


class OutOfTimeHubTests(RacerHubBase):
    players = 2

    def egg(self):
        """With the Reverse Gear already found, take the secret road and cross the hidden plate at speed."""
        self.m.handle("secret_item_found", SECRET_ITEM_RETRO_RACER)
        self.launch()
        run = self.to_secret()
        run.skip()
        self.scene_frames(3.0)
        self.assertEqual(run.phase, run.DRIVE)
        self.assertTrue(run.owned_at_entry)
        run.player.distance = 240000 - 4000 - run.offset
        run.player.z = run.player.distance
        up = self.move_key("up")
        self.hold(up)
        for _ in range(60 * 4):
            run.player.speed = max(run.player.speed, run.player.max_speed * 0.95)
            self.scene.update(DT)
            if run.phase == run.TIMETRAVEL:
                break
        self.release(up)
        self.assertEqual(run.phase, run.TIMETRAVEL)
        return run

    def test_it_is_noted_in_the_story_but_adds_no_item_trial_or_reward(self):
        tickets = [p.tickets for p in self.profiles]
        stats_before = None
        run = self.egg()
        self.scene_frames(7.0)
        self.assertTrue(self.m.egg_found("out_of_time"))
        self.assertEqual(self.m.secret_items, 1)                         # still only the Reverse Gear
        self.assertEqual(self.m.secret_trials, 0)
        self.assertEqual(self.m.state["stats"]["secret_items"], [SECRET_ITEM_RETRO_RACER])
        self.assertEqual([p.tickets for p in self.profiles], tickets)
        self.assertEqual(self.scene.get_reward().tickets_earned, 0)

    def test_it_can_be_triggered_again_without_changing_anything(self):
        self.egg()
        self.scene_frames(7.0)
        flags = dict(self.m.state["flags"])
        self.scene._leave()
        self.frames(90)
        self.egg_again = self.egg()
        self.scene_frames(7.0)
        self.assertEqual(self.m.state["flags"], flags)
        self.assertEqual(self.m.secret_items, 1)

    def test_it_survives_a_save_and_the_racer_is_told_on_the_next_visit(self):
        self.egg()
        self.scene_frames(7.0)
        path = os.path.join(tempfile.mkdtemp(), "p.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(path), True)
        ProfileStore(path).save(self.profiles[0])
        self.assertTrue(QuestManager(LocalSession(ProfileStore(path).load())).egg_found("out_of_time"))
        self.scene._leave()
        self.frames(90)
        self.launch()
        self.assertTrue(self.racer.egg_found)

    def test_finding_it_is_noted_in_the_playing_profiles_story_only(self):
        self.egg()
        self.scene_frames(7.0)
        self.assertTrue(self.profiles[0].story["flags"]["egg_out_of_time"])
        self.assertEqual(self.profiles[1].story, {})

    def test_the_exit_of_the_restored_road_returns_to_the_arcade_with_the_music_restored(self):
        run = self.egg()
        self.scene_frames(9.5)
        self.assertEqual(run.phase, run.PAST)
        run.player.distance = run.road.exit_z - 3000 - run.offset
        run.player.z = run.player.distance
        up = self.move_key("up")
        self.hold(up)
        for _ in range(60 * 10):
            self.scene.update(DT)
            if run.phase == run.LEAVING:
                break
        self.release(up)
        self.assertEqual(run.phase, run.LEAVING)
        self.scene_frames(3.0)
        self.frames(150)
        self.assertIs(self.game.scenes.current, self.game.hub.room("arcade_floor"))
        self.assertEqual(self.game.audio.duck, 1.0)
        self.assertEqual(self.m.secret_items, 1)

    def test_on_a_first_visit_the_round_trip_through_time_earns_the_reverse_gear(self):
        self.launch()
        run = self.to_secret()
        run.skip()
        self.scene_frames(3.0)
        run.player.distance = 240000 - 4000 - run.offset
        run.player.z = run.player.distance
        up = self.move_key("up")
        self.hold(up)
        for _ in range(60 * 4):
            run.player.speed = max(run.player.speed, run.player.max_speed * 0.95)
            self.scene.update(DT)
            if run.phase == run.TIMETRAVEL:
                break
        self.assertEqual(self.m.secret_items, 0)                      # not yet: you have to get back
        self.scene_frames(9.5)
        run.player.distance = run.road.exit_z - 3000 - run.offset
        run.player.z = run.player.distance
        for _ in range(60 * 10):
            self.scene.update(DT)
            if run.phase == run.REWARD:
                break
        self.release(up)
        self.assertEqual(run.phase, run.REWARD)
        self.assertEqual(self.m.secret_items, 1)
        self.assertTrue(self.m.egg_found("out_of_time"))

    def test_quitting_in_the_middle_of_the_time_travel_returns_cleanly(self):
        self.egg()
        self.scene_frames(1.5)
        self.scene._leave()
        self.frames(120)
        self.assertIs(self.game.scenes.current, self.game.hub.room("arcade_floor"))
        self.assertEqual(self.game.audio.duck, 1.0)


if __name__ == "__main__":
    unittest.main()
