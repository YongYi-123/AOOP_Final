"""Tests for the TRIAL 01 expansion: PUZZLE 05 THE FORGOTTEN PHOTOGRAPHS (mandatory) and THE CAT'S SECRET (optional).

The rules are tested on their own (golden_age.PhotoBoard / Bell / TrialRun keepsakes), and the room is played with real key
events through the real Game (golden_age_testing.Driver), like test_golden_age.py.

Run headless from this folder:   python -m unittest test_photo_and_cat_puzzles -v
"""
import itertools
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import golden_age as G  # noqa: E402
import golden_age_art as A  # noqa: E402
import golden_age_content as C  # noqa: E402
import golden_age_scene as GS  # noqa: E402
import golden_age_ui as UI  # noqa: E402
import quests  # noqa: E402
from game import Game  # noqa: E402
from golden_age_testing import K  # noqa: E402
from item_registry import COLLECTIBLE, ITEM_REGISTRY  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import ProfileStore  # noqa: E402
from test_golden_age import TrialCase, all_strings  # noqa: E402

PLACES = ("drawer", "programming", "homework", "bedside")


def solved_run():
    run = G.TrialRun()
    for place in PLACES:
        run.find_photo(place)
    for i, photo in enumerate(G.PHOTOS):
        run.place_photo(photo, i)
    assert run.check_board()
    return run


def ready_run():
    """A run with the whole original chain done (power, cabinet, disk): the computer is "ready"."""
    run = G.TrialRun()
    run.power = run.cabinet_open = True
    run.inventory.append(run.BOOT_DISK)
    return run


# ------------------------------------------------------------------ 1-6. the photographs, by their rules
class PhotoRuleTests(unittest.TestCase):
    def test_all_four_photos_are_hidden_in_ordinary_places_and_each_is_found_once(self):
        self.assertEqual(sorted(G.PHOTO_HIDING.values()), sorted(G.PHOTOS))
        self.assertEqual(set(G.PHOTO_HIDING), set(PLACES))
        run = G.TrialRun()
        for place in PLACES:
            self.assertEqual(run.find_photo(place), G.PHOTO_HIDING[place])
            self.assertIsNone(run.find_photo(place))                                  # looking again finds nothing new
        self.assertEqual(sorted(run.photos_found), sorted(G.PHOTOS))
        self.assertIsNone(run.find_photo("window"))

    def test_the_order_they_are_collected_in_does_not_matter(self):
        for order in itertools.permutations(PLACES):
            run = G.TrialRun()
            for place in order:
                run.find_photo(place)
            for i, photo in enumerate(G.PHOTOS):
                self.assertTrue(run.place_photo(photo, i))
            self.assertTrue(run.check_board(), order)
            self.assertTrue(run.archive_index)

    def test_only_the_right_arrangement_solves_it(self):
        right = 0
        for order in itertools.permutations(G.PHOTOS):
            run = G.TrialRun()
            for place in PLACES:
                run.find_photo(place)
            for i, photo in enumerate(order):
                run.place_photo(photo, i)
            solved = run.check_board()
            self.assertEqual(solved, order == G.PHOTOS, order)
            self.assertEqual(run.archive_index, solved)
            self.assertEqual(G.C.ARCHIVE_INDEX in run.inventory, solved)
            right += solved
        self.assertEqual(right, 1)

    def test_a_wrong_board_can_be_rearranged_freely_and_then_solved(self):
        run = G.TrialRun()
        for place in PLACES:
            run.find_photo(place)
        for i, photo in enumerate(reversed(G.PHOTOS)):
            run.place_photo(photo, i)
        for _ in range(3):
            self.assertFalse(run.check_board())                                      # no penalty, no lock-out
        run.place_photo("desk", 0)                                                   # swaps with what was there
        self.assertEqual(run.board.slots[0], "desk")
        self.assertEqual(sorted(p for p in run.board.slots if p), sorted(G.PHOTOS))
        run.take_photo("build")
        self.assertIn("build", run.photos_in_hand)
        for i, photo in enumerate(G.PHOTOS):
            run.place_photo(photo, i)
        self.assertTrue(run.check_board())

    def test_an_incomplete_board_or_missing_photos_never_open_it(self):
        run = G.TrialRun()
        run.find_photo("drawer")
        run.find_photo("programming")
        self.assertFalse(run.place_photo("friends", 3))                              # (not found yet: cannot be placed)
        run.place_photo("desk", 0)
        run.place_photo("game", 2)
        self.assertFalse(run.board.full)
        self.assertFalse(run.check_board())
        self.assertFalse(run.archive_index)

    def test_the_solution_is_unique_and_can_be_deduced_from_the_pictures(self):
        self.assertEqual(G.consistent_orders(), [G.PHOTOS])
        for missed in G.PHOTO_FACTS:                                                  # even a player who misses one kind of clue
            facts = {k: v for k, v in G.PHOTO_FACTS.items() if k != missed}
            self.assertEqual(G.consistent_orders(facts), [G.PHOTOS], missed)
        for table in G.PHOTO_FACTS.values():
            self.assertEqual(set(table), set(G.PHOTOS))
        for a in G.PHOTOS:                                                            # four different pictures
            for b in G.PHOTOS:
                if a != b:
                    self.assertNotEqual(pygame.image.tostring(A.photo(a), "RGB"), pygame.image.tostring(A.photo(b), "RGB"))

    def test_the_pictures_differ_where_the_facts_say(self):
        """The art draws what PHOTO_FACTS claims: the plant's leaves, people only in the last one, a lit screen in the
        last two, the idea sheet on the wall after the first."""
        def count(img, rect, test):
            return sum(1 for x in range(rect[0], rect[0] + rect[2]) for y in range(rect[1], rect[1] + rect[3])
                       if test(img.get_at((x, y))))
        green = lambda c: c.g > c.r + 30 and c.g > c.b + 30                       # noqa: E731 (the plant)
        pink = lambda c: c.r > 220 and c.g < 190 and c.b > 150                    # noqa: E731 (its flower)
        lit = lambda c: c.g < 120 and c.g > c.r + 20 and c.g > c.b + 10            # noqa: E731 (a glowing green screen)
        imgs = {k: A.photo_base(k) for k in G.PHOTOS}
        plant = [count(imgs[k], (54, 12, 10, 14), green) for k in G.PHOTOS]
        self.assertEqual(plant, sorted(plant))
        self.assertEqual(len(set(plant)), 3)                                           # it grows (the last one flowers instead)
        self.assertGreater(count(imgs["friends"], (50, 13, 12, 6), pink), 0)
        for k in ("desk", "build", "game"):
            self.assertEqual(count(imgs[k], (50, 13, 12, 6), pink), 0, k)
        screen = [count(imgs[k], (24, 14, 18, 12), lit) for k in G.PHOTOS]
        self.assertEqual([n > 0 for n in screen], [False, False, True, True])         # the screen only works from the third

    def test_the_backs_of_the_photos_give_no_numbers_or_dates(self):
        for text in C.PHOTO_BACKS.values():
            self.assertFalse(any(ch.isdigit() for ch in text), text)
            for word in ("FIRST", "SECOND", "THIRD", "LAST", "BEGINNING", "BEFORE", "AFTER", "STEP"):
                self.assertNotIn(word, text.upper())

    def test_the_archive_index_is_given_once(self):
        run = solved_run()
        self.assertTrue(run.check_board())                                            # (again: still solved)
        run.take_index()
        run.load_keepsakes(run.keepsakes())
        self.assertEqual(run.inventory.count(C.ARCHIVE_INDEX), 1)
        self.assertEqual(run.clues.count("index"), 1)
        again = G.TrialRun()
        again.load_keepsakes(run.keepsakes())
        again.load_keepsakes(run.keepsakes())                                          # loading is idempotent
        self.assertEqual(again.inventory.count(C.ARCHIVE_INDEX), 1)
        self.assertEqual(again.keepsakes(), run.keepsakes())

    def test_a_damaged_keepsake_save_is_ignored_not_trusted(self):
        run = G.TrialRun()
        run.load_keepsakes({"photos": ["desk", "desk", "dog", 3], "board": ["desk", "desk", "x", None, "game"],
                            "photos_solved": "yes", "archive_index": 1, "bell": ["a", 2], "bell_solved": 1, "sketch": "y"})
        self.assertEqual(run.photos_found, ["desk"])
        self.assertEqual(run.board.slots, ["desk", None, None, None])
        self.assertFalse(run.photos_solved or run.archive_index or run.bell_solved or run.sketch_given)
        run.load_keepsakes("nonsense")
        run.load_keepsakes({"photos_solved": True})                                    # solved without the photos: not believed
        self.assertFalse(run.photos_solved)


# ------------------------------------------------------------------ 7-10. the computer's two halves
class ComputerGateRuleTests(unittest.TestCase):
    def test_breakout_alone_does_not_unlock_the_archive(self):
        run = ready_run()
        run.clear_breakout()
        self.assertFalse(run.archive_open)
        self.assertFalse(run.finish_computer())
        desk = G.Desktop()
        desk.pick(3)
        self.assertEqual(desk.choose(True, run.indexed), "noindex")
        self.assertEqual(desk.message, "ARCHIVE INDEX NOT FOUND.")

    def test_the_photographs_alone_do_not_unlock_the_archive(self):
        run = solved_run()
        run.power = run.cabinet_open = True
        run.inventory.append(run.BOOT_DISK)
        self.assertFalse(run.finish_computer())
        desk = G.Desktop()
        desk.pick(3)
        self.assertEqual(desk.choose(False, run.indexed), "locked")                     # the game comes first

    def test_both_together_unlock_it_in_either_order(self):
        for photos_first in (True, False):
            run = ready_run()
            if not photos_first:
                run.clear_breakout()
            for place in PLACES:
                run.find_photo(place)
            for i, photo in enumerate(G.PHOTOS):
                run.place_photo(photo, i)
            run.check_board()
            if photos_first:
                run.clear_breakout()
            self.assertTrue(run.archive_open)
            self.assertTrue(run.finish_computer())

    def test_the_no_index_message_never_gives_the_board_away(self):
        text = " ".join(C.NO_INDEX).upper()
        for word in ("PHOTO", "BOARD", "WALL", "PICTURE", "DESK", "ORDER"):
            self.assertNotIn(word, text)


class ComputerGatePlayTests(TrialCase):
    def prepared(self):
        scene = self.enter()
        self.d.restore_power()
        self.d.listen_to_phone()
        self.d.open_cabinet()
        self.d.read_note()
        self.d.get_boot_disk()
        self.d.close_all()
        return scene

    def boot(self):
        self.d.use("computer")
        self.assertIsInstance(self.game.scenes.current.panel, UI.ComputerPanel)
        self.d.tap(K.K_e)
        self.d.seconds(4.7)
        self.assertEqual(self.game.scenes.current.panel.stage, "desktop")
        return self.game.scenes.current.panel

    def test_the_boot_disk_still_starts_happy_breakout_without_any_photo(self):
        scene = self.prepared()
        self.assertEqual(scene.run.photos_found, [])                                   # (no photo has been found at all)
        panel = self.boot()
        self.d.tap(K.K_1)
        self.assertEqual(panel.stage, "game")
        self.d.play_breakout()
        self.assertTrue(scene.run.breakout_cleared)
        self.assertTrue(self.manager.state["flags"][G.BREAKOUT_FLAG])

    def test_breakout_alone_says_archive_index_not_found_and_records_nothing(self):
        scene = self.prepared()
        panel = self.boot()
        self.d.tap(K.K_1)
        self.d.play_breakout()
        self.d.seconds(0.5)
        self.d.tap(K.K_e)
        self.d.tap(K.K_3)
        self.assertEqual(panel.stage, "desktop")
        self.assertEqual(panel.desktop.message, "ARCHIVE INDEX NOT FOUND.")
        self.assertFalse(scene.run.computer_done)
        self.assertFalse(self.manager.trial_done("trial_01"))
        self.assertFalse(self.manager.has_memory_fragment("trial_01"))

    def test_the_photographs_alone_keep_the_files_locked(self):
        scene = self.prepared()
        self.d.collect_photos()
        self.d.solve_photo_board()
        self.assertTrue(scene.run.archive_index)
        panel = self.boot()
        self.d.tap(K.K_3)
        self.assertEqual(panel.stage, "desktop")
        self.assertEqual(panel.desktop.message, " ".join(C.LOCKED_DENIED))
        self.assertFalse(self.manager.trial_done("trial_01"))

    def test_breakout_first_then_the_photos_opens_the_archive_without_playing_again(self):
        scene = self.prepared()
        panel = self.boot()
        self.d.tap(K.K_1)
        self.d.play_breakout()
        self.d.seconds(0.5)
        self.d.tap(K.K_e)
        self.d.tap(K.K_ESCAPE)                                                        # leave the computer
        self.d.close_all()
        self.d.collect_photos()
        self.d.solve_photo_board()
        panel = self.boot()
        self.d.tap(K.K_3)                                                             # no second game needed
        self.assertEqual(panel.stage, "files")
        self.assertEqual(panel.files_lines[:2], C.INDEX_LINES)
        self.d.seconds(panel.files_ready + 0.6)
        self.d.tap(K.K_e)
        self.d.seconds(0.5)
        self.d.talk_through()
        self.assertIsInstance(scene.panel, UI.CompletePanel)
        self.assertTrue(self.manager.trial_done("trial_01"))
        self.assertTrue(self.manager.has_memory_fragment("trial_01"))
        self.assertEqual(self.manager.memory_fragments, 1)


# ------------------------------------------------------------------ the photographs, played with the keyboard
class PhotoPlayTests(TrialCase):
    def test_every_photo_is_found_by_inspecting_ordinary_things_in_any_order(self):
        scene = self.enter()
        found = self.d.collect_photos(order=("bedside", "homework", "programming", "drawer"))
        self.assertEqual(found, [G.PHOTO_HIDING[p] for p in ("bedside", "homework", "programming", "drawer")])
        self.assertEqual(sorted(scene.run.photos_found), sorted(G.PHOTOS))
        self.assertEqual(self.manager.trial_progress("trial_01")["photos"], scene.run.photos_found)   # kept as they turn up
        for place in PLACES:
            self.assertIsNone(self.d.find_photo(place))                                # nothing more to find

    def test_a_found_photo_is_shown_full_size_with_its_back(self):
        scene = self.enter()
        self.d.use("drawer")
        self.d.tap(K.K_ESCAPE)
        panel = scene.panel
        self.assertIsInstance(panel, UI.PagedPanel)
        self.assertEqual(panel.tag, "photo")
        page = panel.pages[0]
        self.assertEqual(page["picture"], "photo_game")
        self.assertEqual(page["text"], C.PHOTO_BACKS["game"])
        self.assertEqual(A.picture(page["picture"]).get_size(), (A.PHOTO_SIZE[0] * 3, A.PHOTO_SIZE[1] * 3))
        panel.draw(pygame.Surface((400, 300)))
        self.d.tap(K.K_e)
        self.assertIsNone(scene.panel)

    def test_the_board_with_nothing_found_just_says_it_is_empty(self):
        scene = self.enter()
        self.d.use("photo_board")
        self.assertEqual([l.text for l in scene.dialogue.lines], [t for _, t, _ in C.PHOTO_BOARD_FIRST])
        self.d.talk_through()
        self.assertIsNone(scene.panel)
        self.d.use("photo_board")
        self.assertEqual(scene.dialogue.lines[0].text, C.PHOTO_BOARD_EMPTY[0][1])
        self.d.talk_through()
        self.assertIsNone(scene.panel)

    def test_a_wrong_order_does_nothing_and_the_right_one_opens_the_compartment(self):
        scene = self.enter()
        self.d.collect_photos()
        self.d.use("photo_board")
        self.d.talk_through()
        panel = self.d.arrange_photos(("friends", "game", "build", "desk"))
        self.d.frames(5)
        self.assertTrue(scene.run.board.full)
        self.assertFalse(scene.run.photos_solved)
        self.assertFalse(scene.run.archive_index)
        self.assertIsNone(panel.opening)
        self.assertNotIn(C.ARCHIVE_INDEX, scene.run.inventory)
        before = (self.profile.tickets, self.profile.tokens, self.manager.secret_items, self.manager.secret_trials)
        self.d.tap(K.K_v)                                                              # a close look at one
        self.assertIsNotNone(panel.zoom)
        panel.draw(pygame.Surface((400, 300)))
        self.d.tap(K.K_e)
        self.assertIsNone(panel.zoom)
        self.d.arrange_photos(G.PHOTOS)
        self.assertIsNotNone(panel.opening)
        self.assertIn("board_click", [n for _, n in self.d.sounds])
        self.d.seconds(UI.PhotoBoardPanel.OPEN_TIME + 0.3)
        self.assertEqual([l.text for l in scene.dialogue.lines], [t for _, t, _ in C.INDEX_FOUND])
        self.d.talk_through()
        self.assertIsInstance(scene.panel, UI.PagedPanel)
        self.assertEqual(scene.panel.pages[0]["title"], "MEMORY ARCHIVE INDEX - 01")
        self.assertIn("It started with a desk, a computer, and a really terrible idea.", scene.panel.pages[0]["text"])
        self.d.tap(K.K_e)
        self.assertEqual(scene.run.inventory.count(C.ARCHIVE_INDEX), 1)
        self.assertIn("index", scene.run.clues)
        self.assertTrue(self.manager.trial_progress("trial_01")["photos_solved"])
        self.assertEqual(before, (self.profile.tickets, self.profile.tokens, self.manager.secret_items, self.manager.secret_trials))
        self.assertFalse(self.manager.trial_done("trial_01"))                          # the board alone finishes nothing

    def test_the_board_is_just_another_thing_to_inspect(self):
        scene = self.enter()
        self.assertEqual(scene.spots["photo_board"].prompt, "INSPECT")
        self.assertEqual(scene.spots["bedside_cabinet"].prompt, "INSPECT")
        for key in ("photo_board", "bedside_cabinet"):
            sp = scene.spots[key]
            self.assertFalse(hasattr(sp, "highlight") or hasattr(sp, "sparkle") or hasattr(sp, "icon"))
        self.assertEqual(A.side_photo_board().get_size(), (14, 48))                   # a small board on the side wall

    def test_the_notes_show_the_photos_in_hand_and_the_index_strip(self):
        scene = self.enter()
        self.d.collect_photos(order=("drawer", "homework"))
        self.d.tap(K.K_TAB)
        rows = [label for _, label in scene.panel.inventory_rows()]
        self.assertIn("OLD PHOTOGRAPH X2", rows)
        scene.panel.draw(pygame.Surface((400, 300)))
        self.d.tap(K.K_TAB)
        self.solve_photos_by_rules(scene.run)
        self.d.tap(K.K_TAB)
        rows = [label for _, label in scene.panel.inventory_rows()]
        self.assertEqual(rows, [C.ARCHIVE_INDEX])
        idx = scene.panel.entries.index("index")
        while scene.panel.index != idx:
            self.d.tap(K.K_DOWN)
        self.d.tap(K.K_e)
        self.assertEqual(scene.panel.pages[0]["title"], "MEMORY ARCHIVE INDEX - 01")       # re-readable from the notes


# ------------------------------------------------------------------ 12-17. the cat's secret
class CatRuleTests(unittest.TestCase):
    def test_the_bell_turns_and_only_its_own_order_rings(self):
        bell = G.Bell()
        self.assertNotEqual(bell.symbols, G.BELL_ANSWER)                               # it never starts solved
        bell.turn(0)
        self.assertEqual(bell.symbols[0], G.BELL_SYMBOLS[(G.BELL_START[0] + 1) % 4])
        right = [combo for combo in itertools.product(range(4), repeat=3) if G.Bell(list(combo)).correct]
        self.assertEqual(len(right), 1)
        self.assertEqual(G.Bell(list(right[0])).symbols, ("sit", "sleep", "play"))

    def test_the_routine_note_gives_the_order_without_naming_the_symbols(self):
        text = C.CAT_ROUTINE["text"].upper()
        self.assertLess(text.index("SITS"), text.index("ASLEEP"))
        self.assertLess(text.index("ASLEEP"), text.index("PLAYTIME"))
        self.assertIn(C.CAT_ROUTINE, C.STICKY_NOTES)                                   # a handwritten note, among the others
        for word in ("BELL", "SYMBOL", "DIAL", "PLUSHIE"):
            self.assertNotIn(word, text)

    def test_wrong_jingles_cost_nothing_and_change_nothing(self):
        run = G.TrialRun()
        for _ in range(5):
            self.assertEqual(run.jingle(), "dull")
        self.assertFalse(run.bell_solved)
        self.assertFalse(run.find_cat_note())
        run.bell = G.Bell([G.BELL_SYMBOLS.index(s) for s in G.BELL_ANSWER])
        self.assertEqual(run.jingle(), "open")
        self.assertEqual(run.jingle(), "ring")                                          # again: rings, opens nothing twice
        self.assertTrue(run.find_cat_note())
        self.assertFalse(run.find_cat_note())

    def test_the_cat_puzzle_never_touches_the_computer(self):
        run = ready_run()
        run.bell = G.Bell([0, 1, 2])
        run.jingle()
        run.find_cat_note()
        run.clear_breakout()
        self.assertFalse(run.indexed)
        self.assertFalse(run.finish_computer())


class CatPlayTests(TrialCase):
    def test_the_three_cat_drawings_can_be_inspected(self):
        scene = self.enter()
        for spot, mark in (("textbook", "sit"), ("cartridges", "sleep"), ("bedside_cabinet", "play")):
            self.d.use(spot)
            self.d.talk_through()
            self.d.keep_photo()                                                        # (the cabinet's photo comes first)
            panel = scene.panel
            self.assertIsInstance(panel, UI.PagedPanel, spot)
            for _ in range(len(panel.pages)):
                if mark in panel.marks_seen:
                    break
                self.d.tap(K.K_RIGHT)
            self.assertIn(mark, panel.marks_seen, spot)
            page = panel.pages[panel.index]
            self.assertEqual(page["mark"], mark)
            self.assertGreater(A.picture(page["picture"]).get_width(), 0)
            panel.draw(pygame.Surface((400, 300)))
            self.d.close_all()
            self.assertIn(mark, scene.run.cat_marks)
        self.assertEqual(sorted(self.manager.trial_progress("trial_01")["cat_marks"]), sorted(G.CAT_MARKS))

    def test_the_plushie_keeps_its_old_lines_and_then_shows_the_bell(self):
        scene = self.enter()
        self.d.use("plushie")
        self.assertEqual([l.text for l in scene.dialogue.lines], [t for _, t, _ in C.LIFE["plushie"]["lines"][0]])
        self.d.talk_through()
        self.assertIsInstance(scene.panel, UI.BellPanel)

    def test_the_bell_can_be_turned_and_a_wrong_jingle_has_no_penalty(self):
        scene = self.enter()
        panel = self.d.open_bell()
        start = panel.bell.symbols
        self.d.tap(K.K_DOWN)
        self.assertNotEqual(panel.bell.symbols, start)
        self.d.tap(K.K_RIGHT)
        self.d.tap(K.K_UP)
        self.assertEqual(panel.cursor, 1)
        self.assertIn("bell_tick", [n for _, n in self.d.sounds])
        before = (self.profile.tickets, self.profile.tokens, dict(self.profile.inventory._counts), self.manager.secret_items,
                  self.manager.secret_trials, scene.run.objective, list(scene.run.clues))
        events = len(self.events)
        for wrong in (("play", "sit", "sleep"), ("sleep", "sleep", "sleep"), ("fish", "play", "sit")):
            self.d.set_bell(wrong)
            self.assertIsNone(panel.ringing)
            self.assertEqual(panel.last, "dull")
        self.assertIn("bell_dull", [n for _, n in self.d.sounds])
        self.assertFalse(scene.run.bell_solved)
        self.assertEqual(A.bedside_table(scene._bedside_look()), A.bedside_table("shut"))
        after = (self.profile.tickets, self.profile.tokens, dict(self.profile.inventory._counts), self.manager.secret_items,
                 self.manager.secret_trials, scene.run.objective, list(scene.run.clues))
        self.assertEqual(before, after)
        self.assertEqual(self.events[events:], [])
        self.d.set_bell(G.BELL_ANSWER)                                                  # and it can still be solved
        self.assertIsNotNone(panel.ringing)

    def test_the_cabinet_photo_comes_first_and_the_carving_follows_it(self):
        scene = self.enter()
        self.d.use("bedside_cabinet")
        self.d.talk_through()
        self.assertEqual(scene.panel.tag, "photo")
        self.assertEqual(self.d.keep_photo(), G.PHOTO_HIDING["bedside"])
        self.assertEqual(scene.panel.tag, "carving")                                     # the carving right after it
        self.d.close_all()
        self.d.use("bedside_cabinet")                                                   # second time: just the carving
        self.assertIsNone(scene.dialogue)
        self.assertEqual(scene.panel.tag, "carving")
        self.d.close_all()
        self.assertEqual(scene.run.photos_found.count(G.PHOTO_HIDING["bedside"]), 1)

    def test_the_right_order_rings_opens_the_cabinet_and_gives_the_sketch_once(self):
        scene = self.enter()
        before = (self.profile.tickets, self.profile.tokens, self.manager.secret_items, self.manager.secret_trials,
                  self.manager.memory_fragments)
        self.d.solve_bell()
        self.assertTrue(scene.run.bell_solved)
        self.assertIn("bell_ring", [n for _, n in self.d.sounds])
        self.assertEqual(scene._bedside_look(), "note")                                # the compartment is open
        self.assertFalse(self.profile.inventory.has_item(C.SKETCH_ITEM))                # (not until the note is found)
        self.d.use("bedside_cabinet")                                                   # (never opened before)
        self.assertEqual(scene.dialogue.lines[0].text, C.BEDSIDE_FIRST[0][1])
        self.d.talk_through()
        self.assertEqual(scene.panel.tag, "photo")                                       # its ordinary photo comes first...
        self.assertEqual(scene.panel.pages[0]["title"], C.PHOTO_FOUND["bedside"])
        self.assertFalse(scene.run.cat_note)
        self.d.keep_photo()
        self.assertEqual(scene.dialogue.lines[0].text, C.BEDSIDE_OPEN[0][1])            # ...then the gap at the back
        self.d.talk_through()
        panel = scene.panel
        self.assertEqual(panel.tag, "catnote")
        self.assertEqual(panel.pages[0]["text"], "For my favorite little troublemaker.\n\nPlease stop sleeping on my keyboard.")
        self.assertEqual(panel.pages[1]["picture"], "sketch")
        for _ in panel.pages:
            self.d.tap(K.K_e)
        spoken = []
        while scene.dialogue is not None:
            spoken.append((scene.dialogue.line.speaker, scene.dialogue.line.text))
            self.d.seconds(2.0)
            self.d.tap(K.K_e)
            self.d.frames(5)
        self.assertEqual(spoken, [
            ("PLAYER", "Apparently someone had a serious problem with cats sleeping on keyboards."),
            ("MIAO MEOW", "Excuse me!"), ("MIAO MEOW", "Sleeping on keyboards is a perfectly reasonable hobby!"),
            ("PLAYER", "Is it?"), ("MIAO MEOW", "Of course! They're warm!"), ("MIAO MEOW", "Also... that note is kind of sweet.")])
        self.assertEqual(self.profile.inventory.get_quantity(C.SKETCH_ITEM), 1)
        self.assertEqual(scene._bedside_look(), "empty")
        after = (self.profile.tickets, self.profile.tokens, self.manager.secret_items, self.manager.secret_trials,
                 self.manager.memory_fragments)
        self.assertEqual(before, after)                                                  # no tokens, tickets, items or trials
        # everything stays inspectable, and nothing is given twice
        self.d.use("bedside_cabinet")
        self.assertEqual([p.get("title") for p in scene.panel.pages], [C.CARVING_PAGE["title"], C.CAT_NOTE["title"], C.CAT_SKETCH["title"]])
        self.d.close_all()
        panel = self.d.open_bell()
        self.d.tap(K.K_e)
        self.assertEqual(panel.last, "ring")
        self.d.close_all()
        self.assertEqual(self.profile.inventory.get_quantity(C.SKETCH_ITEM), 1)

    def test_the_sketch_is_a_lore_collectible_in_the_existing_collection(self):
        item = ITEM_REGISTRY.get(C.SKETCH_ITEM)
        self.assertEqual(item.name, "OLD CAT SKETCH")
        self.assertEqual(item.category, COLLECTIBLE)
        self.assertFalse(item.stackable)
        from collection import CollectionService
        self.assertIn(C.SKETCH_ITEM, [d.id for d, _ in CollectionService(self.profile).entries()])
        import item_icons
        self.assertIn(item.icon["shape"], item_icons.PAINTERS)

    def test_the_cat_puzzle_is_not_needed_to_finish_the_trial(self):
        scene = self.enter()
        self.d.play_through()
        self.assertTrue(self.manager.trial_done("trial_01"))
        self.assertFalse(scene.run.bell_solved)
        self.assertFalse(self.profile.inventory.has_item(C.SKETCH_ITEM))

    def test_it_can_still_be_found_after_the_trial_is_complete(self):
        self.enter()
        self.d.play_through()
        self.d.finish_card(stay=True)                                                   # stay in the room
        scene = self.game.scenes.current
        self.assertIsInstance(scene, GS.GoldenAgeScene)
        self.d.solve_bell()
        self.d.take_cat_note()
        self.assertEqual(self.profile.inventory.get_quantity(C.SKETCH_ITEM), 1)
        self.assertEqual(self.manager.secret_trials, 1)

    def test_miao_hints_only_when_asked_and_by_what_was_looked_at(self):
        scene = self.enter()
        self.d.seconds(5)
        self.assertFalse(scene.bubble.visible)
        self.d.open_bell()
        self.d.close_all()
        scene.run.hints.clear()
        self.assertEqual(scene.run.hint_topic(), "cat")
        self.assertEqual(scene.run.hint(), C.HINTS["cat"][0])
        self.assertEqual(scene.run.hint(), C.HINTS["cat"][1])
        scene.run.last_looked = "photo_board"
        self.assertEqual(scene.run.hint_topic(), "photos")
        run = ready_run()
        run.clear_breakout()
        self.assertEqual(run.hint_topic(), "photos")                                     # the game is cleared: the index is next
        for tiers in (C.HINTS["photos"], C.HINTS["cat"]):
            self.assertEqual(len(tiers), 3)
            joined = " ".join(tiers).upper()
            for spoiler in ("SIT, SLEEP", "SITTING, SLEEPING", "DESK, COMPUTER, GAME"):
                self.assertNotIn(spoiler, joined)


# ------------------------------------------------------------------ 11, 18, 19. saving, old profiles, replays
class SaveAndReplayTests(TrialCase):
    def store(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "alice.json")
        ProfileStore(path).autosave(self.profile)
        return path

    def new_game(self, profile):
        game = Game(session=LocalSession(profile))
        self.addCleanup(game.quit)
        return game

    def test_found_photos_their_places_and_a_solved_board_survive_saving_and_loading(self):
        path = self.store()
        scene = self.enter()
        self.d.collect_photos(order=("drawer", "programming", "homework"))
        self.d.use("photo_board")
        self.d.talk_through()
        panel = scene.panel
        if panel.row == 0:
            self.d.tap(K.K_DOWN)
        self.d.tap(K.K_e)                                                               # pick up the first in hand ...
        held = panel.held
        self.d._cursor_to(panel, 0, 2)
        self.d.tap(K.K_e)                                                               # ... and pin it on slot 3
        self.d.tap(K.K_ESCAPE)
        loaded = ProfileStore(path).load()
        kept = quests.QuestManager(LocalSession(loaded)).trial_progress("trial_01")
        self.assertEqual(sorted(kept["photos"]), sorted(["game", "desk", "friends"]))
        self.assertEqual(kept["board"], ["", "", held, ""])                              # (gaps keep their places)
        run = G.TrialRun()
        run.load_keepsakes(kept)                                                         # a new game picks them up
        self.assertEqual(run.board.slots[2], held)
        self.assertEqual(sorted(run.photos_found), sorted(["game", "desk", "friends"]))
        # finish the board, then a brand new game from the save: still solved, nothing to redo
        self.d.find_photo("bedside")
        self.d.solve_photo_board()
        self.d.solve_bell()
        self.d.take_cat_note()
        loaded = ProfileStore(path).load()
        game2 = self.new_game(loaded)
        scene2 = GS.GoldenAgeScene(game2, game2.session.primary)
        self.assertTrue(scene2.run.photos_solved and scene2.run.archive_index and scene2.run.indexed)
        self.assertEqual(scene2.run.inventory, [C.ARCHIVE_INDEX])
        self.assertTrue(scene2.run.bell_solved and scene2.run.cat_note and scene2.run.sketch_given)
        self.assertEqual(loaded.inventory.get_quantity(C.SKETCH_ITEM), 1)
        self.assertFalse(scene2.run.power)                                               # (the rest of the room starts over)
        self.assertEqual(scene2._bedside_look(), "empty")

    def test_leaving_and_coming_back_keeps_both_puzzles(self):
        scene = self.enter()
        self.d.collect_photos()
        self.d.solve_photo_board()
        self.d.solve_bell()
        self.leave_to_terminal()
        self.d.enter_trial()
        again = self.game.scenes.current
        self.assertTrue(again.run.photos_solved)
        self.assertTrue(again.run.bell_solved)

    def test_an_old_completed_profile_keeps_its_trial_and_fragment_and_is_not_forced_through_the_board(self):
        path = self.store()
        self.manager.handle("vending_secret")
        self.manager.handle(G.BREAKOUT_FLAG)
        self.manager.handle("secret_trial_done", "trial_01")                             # finished before the board existed
        self.assertEqual(self.manager.trial_progress("trial_01"), {})
        loaded = ProfileStore(path).load()
        m = quests.QuestManager(LocalSession(loaded))
        self.assertTrue(m.trial_done("trial_01"))
        self.assertTrue(m.has_memory_fragment("trial_01"))
        self.assertEqual(m.trial_progress("trial_01"), {})                               # nothing was written by loading
        # a replay: the archive opens with the game alone (no board needed), and nothing is paid twice
        scene = self.enter()
        self.assertTrue(scene.run.legacy_archive)
        self.assertTrue(scene.run.indexed)
        self.d.restore_power()
        self.d.listen_to_phone()
        self.d.open_cabinet()
        self.d.read_note()
        self.d.get_boot_disk()
        self.d.close_all()
        self.d.boot_computer()
        self.assertIsInstance(scene.panel, UI.CompletePanel)
        self.assertFalse(scene.panel.first_time)
        self.assertEqual(self.manager.secret_trials, 1)
        self.assertEqual(self.manager.memory_fragments, 1)
        self.assertTrue(self.manager.has_memory_fragment("trial_01"))

    def test_a_new_player_does_not_get_the_fragment_from_breakout_alone(self):
        scene = self.enter()
        self.assertFalse(scene.run.legacy_archive)
        self.manager.handle(G.BREAKOUT_FLAG)
        self.assertFalse(self.manager.has_memory_fragment("trial_01"))
        run = ready_run()
        run.breakout_cleared = True
        self.assertFalse(run.finish_computer())

    def test_a_replay_shows_the_solved_board_and_bell_and_pays_nothing_twice(self):
        scene = self.enter()
        self.d.play_through()
        self.d.finish_card(stay=True)
        self.d.solve_bell()
        self.d.take_cat_note()
        self.leave_to_terminal()
        snapshot = (self.manager.secret_trials, self.manager.memory_fragments, self.profile.tickets, self.profile.tokens,
                    self.profile.inventory.get_quantity(C.SKETCH_ITEM), dict(self.manager.trial_progress("trial_01")))
        self.d.enter_trial()
        again = self.game.scenes.current
        self.assertIsNot(again, scene)
        self.assertFalse(again.run.power)                                                # a fresh, dark room ...
        self.assertTrue(again.run.photos_solved)                                         # ... with the board still solved
        self.assertEqual(again.run.inventory, [C.ARCHIVE_INDEX])
        self.d.use("photo_board")
        panel = again.panel
        self.assertIsInstance(panel, UI.PhotoBoardPanel)
        self.assertTrue(panel.solved)
        self.assertEqual(again.run.board.slots, list(G.PHOTOS))
        self.d.tap(K.K_e)                                                                # a close look still works
        self.assertEqual(panel.zoom, G.PHOTOS[0])
        self.d.tap(K.K_e)
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_ESCAPE)
        self.assertEqual(again.run.board.slots, list(G.PHOTOS))                          # nothing can be moved any more
        panel = self.d.open_bell()
        self.d.tap(K.K_DOWN)
        self.assertEqual(panel.bell.symbols, G.BELL_ANSWER)                              # the dials stay put
        self.d.tap(K.K_e)
        self.assertEqual(panel.last, "ring")
        self.d.close_all()
        self.d.use("bedside_cabinet")
        self.d.talk_through()
        self.assertEqual(again.panel.pages[1]["title"], C.CAT_NOTE["title"])             # the note is still there to read
        self.d.close_all()
        self.d.play_through()
        self.assertFalse(again.panel.first_time)
        after = (self.manager.secret_trials, self.manager.memory_fragments, self.profile.tickets, self.profile.tokens,
                 self.profile.inventory.get_quantity(C.SKETCH_ITEM), dict(self.manager.trial_progress("trial_01")))
        self.assertEqual(snapshot, after)

    def test_trial_02_progression_is_unchanged(self):
        scene = self.enter()
        self.d.play_through()
        self.assertTrue(self.manager.trial_done("trial_01"))
        self.assertEqual(self.manager.trial_progress("trial_02"), {})                    # Trial 01's keepsakes are its own
        self.assertFalse(self.manager.trial_done("trial_02"))
        self.assertEqual(self.manager.can_finish_trial("trial_02"), self.manager.chapter_unlocked(quests.TRIALS_BY_ID["trial_02"].chapter))
        self.assertFalse(self.manager.has_secret_item("claw_secret_reward"))
        self.assertEqual(self.manager.secret_items, 1)
        self.assertEqual(self.manager.memory_fragments, 1)
        del scene


# ------------------------------------------------------------------ the writing and the story's boundary
class ContentBoundaryTests(unittest.TestCase):
    NEW = ("PHOTO_BACKS", "PHOTO_FOUND", "PHOTO_BOARD_FIRST", "PHOTO_BOARD_EMPTY", "INDEX_STRIP", "INDEX_FOUND", "NO_INDEX",
           "INDEX_LINES", "CAT_ROUTINE", "TEXTBOOK_DOODLE", "CARTRIDGE_PAGES", "CARVING_PAGE", "BEDSIDE_FIRST", "BEDSIDE_AGAIN",
           "BEDSIDE_OPEN", "BELL_RANG", "CAT_NOTE", "CAT_SKETCH", "CAT_NOTE_TALK")

    def strings(self):
        return [t for name in self.NEW for t in all_strings(getattr(C, name))]

    def test_everything_new_is_english_and_drawable(self):
        from font import _GLYPHS
        allowed = set(_GLYPHS) | set(" \n")
        for text in self.strings():
            self.assertTrue(text.isascii(), text)
            for ch in text.upper():
                self.assertIn(ch, allowed, f"{ch!r} in {text[:40]!r}")

    def test_nothing_new_reveals_who_lived_here_or_later_story(self):
        text = " ".join(self.strings()).upper()
        for banned in ("KEV" + "IN", "ARCADE", "BEST FRIEND", "I REMEMBER", "REMEMBER", "GOODBYE", "SHUTDOWN", "FOUNDER",
                       "MY NAME", "PLAYER_000"):
            self.assertNotIn(banned, text, banned)
        self.assertGreaterEqual(G.PHOTO_FACTS["people"][G.PHOTOS[-1]], 3)              # the last photo: friends playing a game
        self.assertGreaterEqual(G.PHOTO_FACTS["game_art"][G.PHOTOS[-1]], 2)

    def test_miaos_reaction_is_affection_not_recognition(self):
        miao = [t.upper() for sp, t, _ in C.CAT_NOTE_TALK if sp == "MIAO MEOW"]
        for line in miao:
            for banned in ("REMEMBER", "MINE", "MY NOTE", "HE ", "HIS ", "OWNER", "FRIEND"):
                self.assertNotIn(banned, line)

    def test_every_new_page_fits_its_paper(self):
        from font import get_font
        font = get_font()
        pages = [C.INDEX_STRIP, C.CAT_ROUTINE, C.TEXTBOOK_DOODLE, C.CARVING_PAGE, C.CAT_NOTE, C.CAT_SKETCH] + list(C.CARTRIDGE_PAGES)
        pages += [UI.photo_page(k, title=C.PHOTO_FOUND[p]) for p, k in G.PHOTO_HIDING.items()]
        for page in pages:
            rows = UI.page_rows(page["text"], page.get("scale", 1))
            limit = UI.MAX_ROWS
            if page.get("picture"):
                pic_h = A.picture(page["picture"]).get_height()
                limit = (UI.PAGE_H - 22 - (30 + pic_h + 8)) // 12
            self.assertLessEqual(len(rows), limit, page["title"])
            for row in rows:
                self.assertLessEqual(font.size(row)[0] * page.get("scale", 1), UI.TEXT_W, row)
            self.assertLessEqual(len(UI.wrap_text(page["title"], UI.TEXT_W)), 2, page["title"])
            panel = UI.PagedPanel([page])
            panel.draw(pygame.Surface((400, 300)))

    def test_the_new_screens_draw_inside_the_canvas(self):
        run = G.TrialRun()
        for place in PLACES:
            run.find_photo(place)
        surf = pygame.Surface((400, 300))
        board = UI.PhotoBoardPanel(run)
        board.draw(surf)
        board.held = "desk"
        board.draw(surf)
        bell = UI.BellPanel(run)
        bell.draw(surf)
        for name in ("doodle_sit", "cartridge_sleep", "carving_play", "sketch", "index_strip", "photo_desk"):
            pic = A.picture(name)
            self.assertLessEqual(pic.get_width(), UI.PAGE_W - 20, name)


if __name__ == "__main__":
    unittest.main()
