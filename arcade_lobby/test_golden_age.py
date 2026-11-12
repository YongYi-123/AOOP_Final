"""Tests for TRIAL 01 - THE GOLDEN AGE (the old bedroom escape room behind the vending machine's Legacy Terminal).

The rules are tested on their own (circuit, Morse, cabinet, terminal menu, objectives) and the room is played with real key
events through the real Game (golden_age_testing.Driver): walking, the fuse board, the telephone, the keypad, the journal,
the old computer, the finish card, and the way back out.

Run headless from this folder:   python -m unittest test_golden_age -v
"""
import os
import re
import shutil
import tempfile
import unittest
import wave
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
import audio_synth  # noqa: E402
import golden_age as G  # noqa: E402
import golden_age_art as A  # noqa: E402
import golden_age_content as C  # noqa: E402
import golden_age_scene as GS  # noqa: E402
import golden_age_ui as UI  # noqa: E402
import happy_breakout as HB  # noqa: E402
import legacy_terminal as LT  # noqa: E402
import quest_ui  # noqa: E402
import quests  # noqa: E402
from controls import SOLO_CONTROLS  # noqa: E402
from game import Game  # noqa: E402
from golden_age_testing import DT, Driver, K, key_down, key_up  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from quests import TRIALS, trial_status  # noqa: E402
from room_testing import goto_room  # noqa: E402
from vending_ui import GLITCH_TIME, VendingScene  # noqa: E402

CLASSIC = [K.K_UP, K.K_UP, K.K_DOWN, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_LEFT, K.K_RIGHT, K.K_b, K.K_a]
HERE = os.path.dirname(os.path.abspath(__file__))


class TrialCase(unittest.TestCase):
    """A real game, one player, standing in the arcade with the vending machine's secret already typed (when asked)."""
    TICKETS, TOKENS = 120, 12

    def setUp(self):
        self.profile = PlayerProfile(profile_id="alice", display_name="ALICE", tickets=self.TICKETS, tokens=self.TOKENS)
        self.profile.set_story({"opening_done": True, "completed": ["get_your_bearings", "arcade_explorer", "earn_some_rewards"]})
        self.game = Game(session=LocalSession(self.profile))
        self.addCleanup(self.game.quit)
        self.story = self.game.hub.story
        self.manager = self.story.manager
        self.manager.state.setdefault("stats", {})["secret_items"] = [quests.SECRET_ITEM_RETRO_RACER]   # the Reverse Gear, already owned
        self.room = goto_room(self.game, "arcade_floor")
        self.d = Driver(self.game)
        self.d.frames(10)
        self.events = []
        self.game.session.add_listener(lambda owner, event: self.events.append(event.type))

    # ------------------------------------------------------------ ways in
    def open_shop(self):
        self.room.acting_player = self.room.players[0]
        self.room.open_vending()
        self.room.acting_player = None
        self.d.frames(90)
        shop = self.game.scenes.current
        self.assertIsInstance(shop, VendingScene)
        return shop

    def open_terminal(self):
        shop = self.open_shop()
        for k in CLASSIC:
            self.d.tap(k)
        self.d.frames(int((GLITCH_TIME + 0.8) / DT))
        term = self.game.scenes.current
        self.assertIsInstance(term, LT.LegacyTerminalScene)
        self.d.tap(K.K_e)                                   # (the use key finishes the boot typing)
        self.d.frames(30)
        return shop, term

    def enter(self, watch_intro=True):
        """Vending machine > Legacy Terminal > TRIAL 01. Returns the scene (the opening has been watched by default)."""
        self.shop, self.term = self.open_terminal()
        scene = self.d.enter_trial()
        self.assertIsInstance(scene, GS.GoldenAgeScene)
        if watch_intro:
            self.d.watch_intro()
        return scene

    def leave_to_terminal(self):
        """ESC, choose LEAVE, and land back on the Legacy Terminal."""
        self.d.tap(K.K_ESCAPE)
        panel = self.game.scenes.current.panel
        self.assertIsInstance(panel, UI.ConfirmPanel)
        self.d.tap(K.K_LEFT)                                # (the default is STAY)
        self.d.tap(K.K_e)
        self.d.seconds(1.0)
        self.assertIsInstance(self.game.scenes.current, LT.LegacyTerminalScene)


# ------------------------------------------------------------------ 1. the way in
class EntryTests(TrialCase):
    def test_the_secret_interface_leads_to_trial_01(self):
        scene = self.enter(watch_intro=False)
        stack = [type(s).__name__ for s in self.game.scenes.stack]
        self.assertEqual(stack[-3:], ["VendingScene", "LegacyTerminalScene", "GoldenAgeScene"])
        self.assertIs(self.game.scenes.stack[-4], self.room)                      # the arcade is still underneath, frozen as it was
        self.assertIs(LT.TRIAL_SCENES["trial_01"], GS.GoldenAgeScene)
        self.assertTrue(self.manager.secret_interface_unlocked)
        self.assertEqual(scene.music_id, "golden_age")

    def test_an_ordinary_vending_machine_cannot_get_you_in(self):
        shop = self.open_shop()
        self.assertFalse(self.manager.secret_interface_unlocked)
        for k in (K.K_e, K.K_DOWN, K.K_e, K.K_UP, K.K_b, K.K_a, K.K_e):
            self.d.tap(k)
        self.d.frames(int((GLITCH_TIME + 1.0) / DT))
        self.assertFalse(any(isinstance(s, (GS.GoldenAgeScene, LT.LegacyTerminalScene)) for s in self.game.scenes.stack))
        self.assertFalse(self.manager.secret_interface_unlocked)

    def test_a_half_typed_code_does_not_open_the_terminal(self):
        self.open_shop()
        for k in CLASSIC[:-2]:                               # ... up to RIGHT, without B A
            self.d.tap(k)
        self.d.frames(int((GLITCH_TIME + 1.0) / DT))
        self.assertFalse(any(isinstance(s, LT.LegacyTerminalScene) for s in self.game.scenes.stack))

    def test_it_uses_the_existing_code_and_terminal_not_a_second_menu(self):
        self.shop, term = self.open_terminal()
        self.assertEqual(term.trial.id, "trial_01")
        self.assertEqual(LT.TRIAL_SCENES, {"trial_01": GS.GoldenAgeScene})          # trials 02 and 03 are not built (yet)
        import vending_ui
        self.assertTrue(hasattr(vending_ui, "SECRET_FLAG") and hasattr(vending_ui, "LegacyTerminalScene"))

    def test_only_the_reverse_gear_is_needed_no_other_item_and_no_other_trial(self):
        self.assertTrue(self.manager.has_secret_item(quests.SECRET_ITEM_RETRO_RACER))
        self.assertEqual(self.manager.secret_items, 1)                               # just the gear: no other Secret Item
        self.assertEqual(self.manager.secret_trials, 0)
        self.enter(watch_intro=False)
        self.assertIsInstance(self.game.scenes.current, GS.GoldenAgeScene)

    def test_without_the_reverse_gear_the_terminal_keeps_the_trial_shut(self):
        self.manager.state["stats"]["secret_items"].clear()                          # (this player never found the gear)
        self.assertFalse(self.manager.has_secret_item(quests.SECRET_ITEM_RETRO_RACER))
        _shop, term = self.open_terminal()
        status = term.status(TRIALS[0])
        self.assertEqual(status.code, "locked")
        self.assertIn("NEED THE REVERSE GEAR (SECRET ITEM 01)", status.reasons)
        term.draw(pygame.Surface((400, 300)))
        wallet = (self.profile.tickets, self.profile.tokens)
        self.d.tap(K.K_e)
        self.d.frames(10)
        self.assertIs(self.game.scenes.current, term)
        self.assertEqual(term.notice["title"], "ACCESS DENIED")
        self.assertIn("NEED THE REVERSE GEAR (SECRET ITEM 01)", term.notice["lines"])
        self.assertFalse(any(isinstance(s, GS.GoldenAgeScene) for s in self.game.scenes.stack))
        self.assertEqual((self.profile.tickets, self.profile.tokens), wallet)
        self.assertEqual(self.manager.secret_trials, 0)
        self.manager.handle("secret_item_found", quests.SECRET_ITEM_RETRO_RACER)    # find it, and the same door opens
        self.d.tap(K.K_e)
        self.d.tap(K.K_e)
        self.d.frames(60)
        self.assertIsInstance(self.game.scenes.current, GS.GoldenAgeScene)

    def test_the_gear_is_only_looked_at_never_taken_or_spent(self):
        self.enter()
        self.d.play_through()
        self.d.finish_card()
        self.assertTrue(self.manager.has_secret_item(quests.SECRET_ITEM_RETRO_RACER))
        self.assertEqual(self.manager.secret_items, 1)

    def test_an_old_save_that_already_finished_trial_02_keeps_it_and_trial_01_still_opens(self):
        self.manager.state["stats"]["secret_trials"] = ["trial_02"]                     # (the old any-order rules allowed it)
        _shop, term = self.open_terminal()
        self.assertEqual(term.status(TRIALS[0]).code, "available")
        self.assertEqual(term.status(TRIALS[1]).code, "done")

    def test_entering_and_leaving_changes_neither_wallet_nor_story(self):
        self.shop, self.term = self.open_terminal()                  # (typing the secret is what completes "check the vending machine")
        self.d.tap(K.K_ESCAPE)
        self.d.frames(90)
        self.assertIs(self.game.scenes.current, self.room)
        before = (self.profile.tickets, self.profile.tokens, self.profile.to_dict()["inventory"], list(self.manager.completed_ids),
                  self.manager.secret_items, self.manager.secret_trials)
        self.enter()
        self.leave_to_terminal()
        after = (self.profile.tickets, self.profile.tokens, self.profile.to_dict()["inventory"], list(self.manager.completed_ids),
                 self.manager.secret_items, self.manager.secret_trials)
        self.assertEqual(before, after)
        self.assertEqual((self.profile.tickets, self.profile.tokens), (self.TICKETS, self.TOKENS))


# ------------------------------------------------------------------ 3. the fuse board
class CircuitTests(unittest.TestCase):
    def test_there_is_a_correct_way_to_solve_it(self):
        c = G.Circuit()
        c.rots = c.solution()
        self.assertTrue(c.solved)
        lit = c.powered()
        self.assertEqual(lit, set(G.ROUTE))                  # the current runs through exactly the route
        self.assertIn(G.OUTPUT, lit)

    def test_it_starts_unsolved_and_one_turn_never_solves_it(self):
        c = G.Circuit()
        self.assertFalse(c.solved)
        self.assertGreaterEqual(c.turns_needed(), 4)
        for cell in list(c.rots):
            d = G.Circuit()
            for _ in range(3):
                d.rotate(*cell)
                self.assertFalse(d.solved, f"turning {cell} gives the answer")

    def test_every_tile_kind_turns_a_quarter_at_a_time(self):
        self.assertEqual(G.openings("corner", 0), {G.N, G.E})
        self.assertEqual(G.openings("corner", 1), {G.E, G.S})
        self.assertEqual(G.openings("straight", 1), {G.E, G.W})
        c = G.Circuit()
        r = c.rots[(0, 0)]
        c.rotate(0, 0)
        self.assertEqual(c.rots[(0, 0)], (r + 1) % 4)
        for _ in range(3):
            c.rotate(0, 0)
        self.assertEqual(c.rots[(0, 0)], r)

    def test_a_partly_right_board_lights_only_the_part_that_is_connected(self):
        c = G.Circuit()
        c.rots = c.solution()
        c.rotate(1, 2)                                       # break the middle of the route
        self.assertFalse(c.solved)
        self.assertIn((0, 1), c.powered())
        self.assertNotIn(G.OUTPUT, c.powered())

    def test_the_run_only_gets_power_from_a_solved_board(self):
        run = G.TrialRun()
        self.assertFalse(run.restore_power())
        self.assertFalse(run.power)
        run.circuit.rots = run.circuit.solution()
        self.assertTrue(run.restore_power())
        self.assertTrue(run.power)
        self.assertFalse(run.restore_power())                # (and only once)

    def test_the_panel_needs_real_turns_and_reports_solved_only_at_the_end(self):
        sounds = []
        panel = UI.CircuitPanel(G.Circuit(), sounds.append)
        panel.handle_event(key_down(K.K_e))
        self.assertFalse(panel.closed)
        self.assertEqual(sounds, ["circuit_click"])
        panel.circuit.rots = panel.circuit.solution()
        panel.circuit.rotate(0, 0, 2)                        # (straight: the same picture after a half turn)
        panel.handle_event(key_down(K.K_e))                  # one more turn on (0, 0), which is a straight piece again
        panel.handle_event(key_down(K.K_e))
        for _ in range(int(UI.CircuitPanel.SURGE / DT) + 5):
            panel.update(DT)
        self.assertEqual(panel.result, "solved")
        self.assertIn("circuit_connect", sounds)

    def test_the_board_can_be_drawn_in_every_state(self):
        panel = UI.CircuitPanel(G.Circuit())
        surf = pygame.Surface((400, 300))
        panel.draw(surf)
        panel.circuit.rots = panel.circuit.solution()
        panel.surge = 0.4
        panel.draw(surf)


class PowerTests(TrialCase):
    def test_nothing_is_on_until_the_board_is_solved(self):
        scene = self.enter()
        self.assertFalse(scene.run.power)
        self.assertEqual(scene.light, 0.0)
        self.d.use("power_box")
        self.assertIsInstance(scene.panel, UI.CircuitPanel)
        self.d.tap(K.K_e)                                    # one press is not enough: it is a puzzle, not a switch
        self.d.seconds(3.0)
        self.assertFalse(scene.run.power)
        self.assertEqual(scene.light, 0.0)
        self.d.tap(K.K_ESCAPE)
        self.assertIsNone(scene.panel)
        self.assertFalse(scene.run.power)
        self.assertNotIn("power_on", [n for _, n in self.d.sounds])

    def test_solving_it_with_the_keyboard_lights_the_room_once(self):
        scene = self.enter()
        self.d.restore_power()
        self.assertTrue(scene.run.power)
        self.assertEqual(scene.light, 1.0)
        names = [n for _, n in self.d.sounds]
        self.assertEqual(names.count("power_on"), 1)
        self.assertEqual(names.count("phone_blip"), 1)
        self.assertEqual(names.count("circuit_connect"), 1)
        self.assertEqual(scene.run.objective, "phone")

    def test_the_light_comes_up_gradually_and_never_flashes(self):
        scene = self.enter()
        self.d.use("power_box")
        self.d.solve_circuit()
        levels = []
        for _ in range(int(5 / DT)):
            self.d.frames(1)
            levels.append(scene.light)
        self.assertEqual(levels[-1], 1.0)
        self.assertTrue(all(b >= a for a, b in zip(levels, levels[1:])), "the light only ever goes up")
        self.assertLess(max(b - a for a, b in zip(levels, levels[1:])), 0.03)          # in small steps: no sudden jump

    def test_the_computer_waits_in_standby_after_the_power_comes_back(self):
        scene = self.enter()
        self.d.restore_power()
        self.assertEqual(scene.run.computer_state(), "standby")
        self.d.use("computer")
        self.assertIsNone(scene.panel)
        self.assertTrue(scene.notice.visible)

    def test_the_phone_and_the_cabinet_are_dead_without_power(self):
        scene = self.enter()
        self.d.use("phone")
        self.assertIsNone(scene.panel)
        self.d.use("cabinet")
        self.assertIsNone(scene.panel)
        self.d.use("computer")
        self.assertIsNone(scene.panel)
        self.assertEqual(scene.run.phone_plays, 0)
        self.assertEqual(scene.run.try_cabinet("SHELF"), "locked")

    def test_the_trial_lights_are_drawn_in_every_stage_inside_the_canvas(self):
        scene = self.enter()
        surf = pygame.Surface((400, 300))
        scene.draw(surf)
        self.d.restore_power()
        scene.draw(surf)
        self.assertGreater(sum(surf.get_at((x, 150))[0] for x in range(40, 360, 8)), 0)


# ------------------------------------------------------------------ 5. the telephone
class MorseTests(unittest.TestCase):
    def test_the_encoding_is_the_standard_one(self):
        self.assertEqual({ch: G.MORSE[ch] for ch in "SHELF"}, {"S": "...", "H": "....", "E": ".", "L": ".-..", "F": "..-."})
        self.assertEqual(G.encode("SHELF"), "... / .... / . / .-.. / ..-.")
        self.assertEqual(len(G.MORSE), 26)
        for code in G.MORSE.values():
            self.assertTrue(set(code) <= {".", "-"})

    def test_the_timing_is_dot_dash_and_the_standard_gaps(self):
        u = G.MORSE_UNIT
        pulses = G.morse_pulses("SHELF")
        self.assertEqual(len(pulses), 16)
        self.assertEqual("".join(p.symbol for p in pulses), "".join(G.MORSE[c] for c in "SHELF"))
        for p in pulses:
            self.assertAlmostEqual(p.length, u if p.symbol == "." else 3 * u, places=6)
        for a, b in zip(pulses, pulses[1:]):
            gap = b.start - a.end
            expected = 1 * u if a.letter == b.letter else 3 * u                # 1 unit inside a letter, 3 between letters
            self.assertAlmostEqual(gap, expected, places=5)
        self.assertAlmostEqual(pulses[0].start, G.LEAD_IN)
        self.assertAlmostEqual(G.morse_duration("SHELF"), pulses[-1].end)

    def test_the_synth_and_the_rules_agree_on_one_unit(self):
        self.assertEqual(audio_synth.MORSE_UNIT, G.MORSE_UNIT)

    def test_the_tone_files_are_exactly_a_dot_and_a_dash_long(self):
        for name, units in (("morse_dot", 1), ("morse_dash", 3)):
            path = os.path.join(HERE, "assets", "sfx", f"{name}.wav")
            with wave.open(path) as w:
                seconds = w.getnframes() / w.getframerate()
            self.assertAlmostEqual(seconds, units * G.MORSE_UNIT, delta=0.01, msg=name)

    def test_playback_fires_each_tone_once_on_the_frame_the_lamp_lights(self):
        play = G.MorsePlayback("SHELF")
        fired, lamp_frames, t = [], [], 0.0
        while play.playing:
            started = play.advance(DT)
            t += DT
            fired += [(round(t, 4), p) for p in started]
            lamp_frames.append(play.lit)
            if started:
                self.assertTrue(play.lit or started[0].start < play.t - DT)      # (it is lit from the very frame a tone starts)
        self.assertEqual([p for _, p in fired], list(G.morse_pulses("SHELF")))
        for when, p in fired:
            self.assertLessEqual(when - p.start, DT + 1e-3)                       # never late by more than one frame
            self.assertGreaterEqual(when - p.start, -1e-6)
        self.assertEqual(play.advance(1.0), [])                                  # finished: nothing more

    def test_the_lamp_is_lit_exactly_while_a_tone_sounds(self):
        play = G.MorsePlayback("SHELF")
        while play.playing:
            play.advance(DT)
            inside = any(p.start <= play.t < p.end for p in play.pulses)
            self.assertEqual(play.lit, inside and play.playing)

    def test_the_same_message_every_time(self):
        a, b = G.morse_pulses(), G.morse_pulses()
        self.assertEqual(a, b)


class PhoneTests(TrialCase):
    def setUp(self):
        super().setUp()
        self.scene = self.enter()
        self.d.restore_power()

    def test_it_plays_the_message_with_the_lamp_in_step_and_can_be_repeated(self):
        self.d.use("phone")
        panel = self.scene.panel
        self.assertIsInstance(panel, UI.PhonePanel)
        first = len(self.d.sounds)
        t0 = self.d.clock
        lit_ok = []
        self.d.tap(K.K_e)
        for _ in range(int((G.morse_duration() + 0.5) / DT)):
            self.d.frames(1)
            lit_ok.append((panel.lit, panel.playback.lit))
        tones = [(t, n) for t, n in self.d.sounds[first:] if n.startswith("morse")]
        self.assertEqual(len(tones), 16)
        pulses = G.morse_pulses()
        for (when, name), p in zip(tones, pulses):
            self.assertEqual(name, p.sound)
            self.assertLessEqual(abs((when - t0) - p.start), 3 * DT)             # on the beat (the tap itself takes two frames)
        self.assertTrue(all(a == b for a, b in lit_ok))
        self.assertFalse(panel.playing)
        before = len(self.d.sounds)
        self.d.tap(K.K_e)                                                        # again
        self.d.seconds(G.morse_duration() + 0.5)
        self.assertEqual(len([1 for _, n in self.d.sounds[before:] if n.startswith("morse")]), 16)
        self.assertEqual(panel.plays, 2)
        self.assertEqual(self.scene.run.phone_plays, 2)

    def test_pressing_again_while_it_plays_does_not_double_the_tones(self):
        self.d.use("phone")
        before = len(self.d.sounds)
        self.d.tap(K.K_e)
        self.d.seconds(1.0)
        self.d.tap(K.K_e)
        self.d.tap(K.K_e)
        self.d.seconds(G.morse_duration())
        self.assertEqual(len([1 for _, n in self.d.sounds[before:] if n.startswith("morse")]), 16)

    def test_the_answer_is_never_shown_on_the_phone_screen(self):
        self.d.use("phone")
        self.d.tap(K.K_e)
        shown = []
        real = UI.draw_text

        def spy(surf, text, *a, **k):
            shown.append(str(text))
            return real(surf, text, *a, **k)
        with patch.object(UI, "draw_text", spy):
            for _ in range(int(G.morse_duration() / DT)):
                self.d.frames(1)
        self.assertTrue(shown)
        for text in shown:
            self.assertNotRegex(text.upper(), r"SHELF")
            self.assertIsNone(re.fullmatch(r"[.\- /]+", text), text)                # no dots-and-dashes text spelling it out either

    def test_the_phone_only_plays_but_opens_the_morse_note_once_the_drawer_gave_it(self):
        self.d.use("phone")
        self.d.tap(K.K_c)
        self.assertIsInstance(self.scene.panel, UI.PhonePanel)                      # no note yet: C does nothing
        self.d.tap(K.K_ESCAPE)
        self.d.read_drawer()
        self.d.use("phone")
        self.d.tap(K.K_c)
        self.assertIsInstance(self.scene.panel, UI.PagedPanel)
        self.assertTrue(self.scene.panel.pages[0]["chart"])
        self.d.tap(K.K_e)                                                           # "back to the phone"
        self.assertIsInstance(self.scene.panel, UI.PhonePanel)
        self.assertEqual(self.scene.run.phone_plays, 0)                            # reading the note is not listening
        self.d.tap(K.K_e)
        self.d.seconds(2.0)
        self.assertEqual(self.scene.panel.shown and True, True)
        pixels = pygame.Surface((400, 300))
        self.scene.panel.draw(pixels)                                               # (nothing draws the dots and dashes any more)

    def test_it_asks_for_the_next_step_after_the_phone_is_used(self):
        self.assertEqual(self.scene.run.objective, "phone")
        self.d.listen_to_phone()
        self.assertEqual(self.scene.run.objective, "cabinet")


# ------------------------------------------------------------------ 6. the desk drawer and the file cabinet
class CabinetRuleTests(unittest.TestCase):
    def powered(self):
        run = G.TrialRun()
        run.circuit.rots = run.circuit.solution()
        run.restore_power()
        return run

    def test_it_accepts_shelf_in_any_case(self):
        for code in ("SHELF", "shelf", " Shelf "):
            run = self.powered()
            self.assertEqual(run.try_cabinet(code), "open")
            self.assertTrue(run.cabinet_open)

    def test_wrong_passwords_do_not_unlock_it(self):
        run = self.powered()
        for code in ("", "SHELL", "SHELVE", "BOOKS", "FLESH", "SHELFS", "12345", "HELFS"):
            self.assertEqual(run.try_cabinet(code), "wrong", code)
        self.assertFalse(run.cabinet_open)
        self.assertEqual(run.wrong_codes, 8)
        self.assertNotIn("note", run.clues)

    def test_it_stays_shut_without_power_even_for_the_right_word(self):
        run = G.TrialRun()
        self.assertEqual(run.try_cabinet("SHELF"), "locked")
        self.assertFalse(run.cabinet_open)

    def test_the_drawer_hints_never_spell_out_the_answer(self):
        for line in G.DRAWER_PAPER:
            self.assertNotRegex(line.upper(), r"\bSHELF\b")
        self.assertEqual(G.DRAWER_PAPER[1], 'It reads: "When words fail, patterns speak."')
        for key in ("paper", "chart"):
            for page in UI.paper_pages(key):
                self.assertNotRegex((page.get("text") or "").upper(), r"\bSHELF\b")
        self.assertTrue(UI.paper_pages("chart")[0]["chart"])                      # the chart is a table of every letter, not of this word
        self.assertEqual(G.CABINET_NOTE, ("The best ideas were never locked in drawers.", "Look where stories sleep."))

    def test_the_drawer_adds_the_paper_and_the_chart_once(self):
        run = self.powered()
        self.assertTrue(run.open_drawer())
        self.assertFalse(run.open_drawer())
        self.assertEqual(run.clues, ["paper", "chart"])


class CabinetPlayTests(TrialCase):
    def setUp(self):
        super().setUp()
        self.scene = self.enter()
        self.d.restore_power()
        self.d.read_drawer()
        self.d.listen_to_phone()

    def test_the_keyboard_opens_it_with_shelf_and_the_note_is_kept(self):
        self.d.open_cabinet("shelf")
        self.assertTrue(self.scene.run.cabinet_open)
        self.assertIsInstance(self.scene.panel, UI.PagedPanel)
        self.assertEqual(self.scene.panel.pages[0]["text"], "The best ideas were never locked in drawers.\nLook where stories sleep.")
        self.d.read_note()
        self.assertIn("note", self.scene.run.clues)
        self.assertEqual(self.scene.run.objective, "bookshelf")
        names = [n for _, n in self.d.sounds]
        self.assertGreaterEqual(names.count("drawer_open"), 2)                    # the desk drawer, then the cabinet

    def test_a_wrong_word_gives_access_denied_and_clears_the_keys(self):
        self.d.open_cabinet("shell")
        self.assertFalse(self.scene.run.cabinet_open)
        self.assertEqual(self.scene.run.wrong_codes, 1)
        self.assertIsInstance(self.scene.panel, UI.KeypadPanel)
        self.assertEqual(self.scene.panel.text, "")
        self.d.type_word("shelf")                                                 # and it can be tried again
        self.d.tap(K.K_RETURN)
        self.d.seconds(2.0)
        self.assertTrue(self.scene.run.cabinet_open)

    def test_too_few_letters_are_not_sent(self):
        self.d.use("cabinet")
        self.d.type_word("she")
        self.d.tap(K.K_RETURN)
        self.assertEqual(self.scene.run.wrong_codes, 0)
        self.assertFalse(self.scene.run.cabinet_open)

    def test_the_note_can_be_read_again_from_the_cabinet_and_from_the_notes(self):
        self.d.open_cabinet()
        self.d.read_note()
        self.d.use("cabinet")
        self.assertIsInstance(self.scene.panel, UI.PagedPanel)
        self.d.tap(K.K_ESCAPE)
        self.d.tap(K.K_TAB)
        self.assertIsInstance(self.scene.panel, UI.NotesPanel)
        self.assertEqual(self.scene.panel.entries, ["paper", "chart", "note"])
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_e)
        self.assertIsInstance(self.scene.panel, UI.PagedPanel)
        self.d.tap(K.K_ESCAPE)
        self.assertIsInstance(self.scene.panel, UI.NotesPanel)                    # back to the list
        self.d.tap(K.K_TAB)
        self.assertIsNone(self.scene.panel)

    def test_the_keypad_takes_letters_and_not_the_players_movement_keys(self):
        self.d.use("cabinet")
        x, y = self.scene.avatar.x, self.scene.avatar.y
        self.d.type_word("wasd")                                                  # W A S D are letters here
        self.assertEqual(self.scene.panel.text, "WASD")
        self.assertEqual((self.scene.avatar.x, self.scene.avatar.y), (x, y))
        self.assertTrue(self.scene.captures_text)
        self.d.tap(K.K_BACKSPACE)
        self.assertEqual(self.scene.panel.text, "WAS")


# ------------------------------------------------------------------ 7. the bookshelf
class BookshelfTests(TrialCase):
    def prepared(self):
        scene = self.enter()
        self.d.restore_power()
        self.d.listen_to_phone()
        self.d.open_cabinet()
        self.d.read_note()
        return scene

    def test_the_shelf_is_a_browser_and_hands_nothing_over(self):
        scene = self.enter()
        wallet = (self.profile.tickets, self.profile.tokens)
        self.d.use("bookshelf")
        self.assertIsInstance(scene.panel, UI.BookshelfPanel)
        self.assertEqual(scene.panel.keys, list(C.BOOK_ORDER))                      # seven ordinary books, no notebook yet
        self.assertFalse(scene.run.has_boot_disk)
        self.assertFalse(scene.run.journal_found)
        self.d.tap(K.K_e)                                                           # take the first one down: it is just a book
        self.assertIsInstance(scene.panel, UI.PagedPanel)
        self.assertEqual(scene.panel.tag, "programming")
        self.assertFalse(scene.run.has_boot_disk)
        self.assertEqual((self.profile.tickets, self.profile.tokens), wallet)

    def test_every_ordinary_book_can_be_read_and_none_holds_the_disk(self):
        scene = self.enter()
        self.d.use("bookshelf")
        for i, key in enumerate(C.BOOK_ORDER):
            self.assertIsInstance(scene.panel, UI.BookshelfPanel)
            while scene.panel.index != i:
                self.d.tap(K.K_DOWN)
            self.d.tap(K.K_e)
            reader = scene.panel
            self.assertEqual(reader.tag, key)
            self.assertEqual(len(reader.pages), len(C.BOOKS[key][2]))
            for _ in reader.pages:                                                  # page through to the end
                self.d.tap(K.K_e)
            self.assertIsInstance(scene.panel, UI.BookshelfPanel)                    # and the shelf is open again
        self.assertEqual(scene.run.books_read, list(C.BOOK_ORDER))
        self.assertFalse(scene.run.has_boot_disk)
        self.assertEqual(scene.run.objective, "phone" if scene.run.power else "power")     # reading changed no progress

    def test_the_plain_notebook_only_turns_up_after_the_cabinets_note(self):
        scene = self.prepared()
        self.assertEqual(scene.run.shelf(), list(C.BOOK_ORDER) + [C.NOTEBOOK_KEY])
        self.d.use("bookshelf")
        self.assertEqual(scene.panel.keys[-1], C.NOTEBOOK_KEY)
        self.assertEqual(len(scene.panel.keys), 8)
        self.assertEqual(UI.BookshelfPanel.spine(C.NOTEBOOK_KEY)[0], "UNTITLED NOTEBOOK")

    def test_the_notebook_has_a_cover_and_twelve_entries_and_gives_the_disk(self):
        scene = self.prepared()
        wallet = (self.profile.tickets, self.profile.tokens)
        bag = repr(self.profile.to_dict()["inventory"])
        self.assertEqual(len(C.JOURNAL_ENTRIES), 12)
        self.assertEqual(len(C.JOURNAL_PAGES), 13)
        self.d.use("bookshelf")
        self.d.tap(K.K_UP)
        self.d.tap(K.K_e)
        panel = scene.panel
        self.assertEqual(panel.tag, "notebook")
        self.assertEqual(len(panel.pages), 13)
        self.assertFalse(scene.run.has_boot_disk)                                    # not before the last page
        for _ in range(len(panel.pages) - 1):
            self.d.tap(K.K_e)
        self.assertFalse(scene.run.has_boot_disk)
        self.d.tap(K.K_e)
        self.d.seconds(1.0)
        self.assertIsNotNone(scene.dialogue)                                          # Miao answers in the story's dialogue box
        spoken = []
        while scene.dialogue is not None:
            spoken.append(scene.dialogue.line.text)
            self.d.seconds(1.8)
            self.d.tap(K.K_e)
            self.d.frames(5)
        self.assertEqual(spoken[:3], [t for _, t, _ in C.JOURNAL_REACTION])
        self.assertEqual(scene.run.inventory, ["OLD BOOT DISK"])
        self.assertEqual((self.profile.tickets, self.profile.tokens), wallet)       # a trial item, not a shop item
        self.assertEqual(repr(self.profile.to_dict()["inventory"]), bag)

    def test_leaving_the_notebook_halfway_gives_no_disk_and_it_can_be_read_again(self):
        scene = self.prepared()
        self.d.use("bookshelf")
        self.d.tap(K.K_UP)
        self.d.tap(K.K_e)
        self.d.tap(K.K_e)
        self.d.tap(K.K_ESCAPE)
        self.assertFalse(scene.run.has_boot_disk)
        self.assertIsInstance(scene.panel, UI.BookshelfPanel)                        # back at the shelf
        self.d.tap(K.K_ESCAPE)
        self.d.get_boot_disk()
        self.assertEqual(scene.run.inventory.count("OLD BOOT DISK"), 1)
        self.d.get_boot_disk()                                                        # reading it again hands out nothing more
        self.assertEqual(scene.run.inventory.count("OLD BOOT DISK"), 1)

    def test_closing_the_notebook_with_esc_on_the_last_page_gives_the_disk_too(self):
        scene = self.prepared()
        self.d.use("bookshelf")
        self.d.tap(K.K_UP)
        self.d.tap(K.K_e)
        panel = scene.panel
        for _ in range(len(panel.pages) - 1):
            self.d.tap(K.K_e)
        self.assertEqual(panel.index, 12)                                            # page 13 of 13
        self.assertFalse(scene.run.has_boot_disk)
        self.d.tap(K.K_ESCAPE)
        self.d.seconds(1.0)
        self.assertIsNotNone(scene.dialogue)
        self.d.talk_through()
        self.assertEqual(scene.run.inventory, ["OLD BOOT DISK"])

    def test_esc_before_the_last_page_still_gives_nothing(self):
        scene = self.prepared()
        self.d.use("bookshelf")
        self.d.tap(K.K_UP)
        self.d.tap(K.K_e)
        for _ in range(11):
            self.d.tap(K.K_e)
        self.assertEqual(scene.panel.index, 11)                                      # page 12
        self.d.tap(K.K_ESCAPE)
        self.assertFalse(scene.run.has_boot_disk)

    def test_the_notebook_can_be_reread_from_the_notes(self):
        scene = self.prepared()
        self.d.get_boot_disk()
        self.d.tap(K.K_TAB)
        self.assertIn("journal", scene.panel.entries)
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_DOWN)
        self.d.tap(K.K_e)
        self.assertEqual(len(scene.panel.pages), 13)


# ------------------------------------------------------------------ 11-13. HAPPY BREAKOUT.EXE
def bot(game, err=0.0, seconds=900.0, rng=None):
    """Play a game with a paddle that follows the ball (a little off). Returns the seconds it took."""
    import random
    rnd = rng or random.Random(1)
    t = 0.0
    while game.state != "clear" and t < seconds:
        if game.state in ("ready", "over"):
            game.launch()
        cx = game.paddle_x + HB.PADDLE_W / 2
        tx = game.ball_x + HB.BALL / 2 + err
        game.step(DT, 0 if abs(tx - cx) < 3 else (1 if tx > cx else -1))
        t += DT
        if rnd.random() < 0.02:
            err = rnd.uniform(-14, 14)
    return t


class BreakoutRuleTests(unittest.TestCase):
    def test_the_wall_and_the_start(self):
        g = HB.Breakout()
        self.assertEqual(g.remaining, HB.COLS * HB.ROWS)
        self.assertEqual(g.lives, 3)
        self.assertEqual(g.state, "ready")
        self.assertEqual(g.score, 0)
        for b in g.bricks:                                                           # every brick is inside the field and none overlap
            self.assertTrue(0 <= b.x and b.x + HB.BRICK_W <= HB.FIELD_W)
        rects = [b.rect for b in g.bricks]
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                self.assertFalse(pygame.Rect(a).colliderect(pygame.Rect(b)))

    def test_the_paddle_follows_the_keys_and_stays_inside_the_field(self):
        g = HB.Breakout()
        x0 = g.paddle_x
        g.step(0.2, 1)
        self.assertGreater(g.paddle_x, x0)
        g.step(0.2, -1)
        self.assertAlmostEqual(g.paddle_x, x0, delta=1.0)
        for _ in range(100):
            g.step(0.1, 1)
        self.assertEqual(g.paddle_x, HB.FIELD_W - HB.PADDLE_W)
        for _ in range(100):
            g.step(0.1, -1)
        self.assertEqual(g.paddle_x, 0)
        self.assertEqual(g.state, "ready")                                           # moving never launches the ball

    def test_the_ball_rides_the_paddle_until_launched(self):
        g = HB.Breakout()
        g.step(0.3, 1)
        self.assertAlmostEqual(g.ball_x + HB.BALL / 2, g.paddle_x + HB.PADDLE_W / 2, delta=0.01)
        g.launch()
        self.assertEqual(g.state, "playing")
        self.assertLess(g.vy, 0)

    def test_the_ball_bounces_off_the_walls_and_the_paddle(self):
        g = HB.Breakout()
        g.launch()
        g.ball_x, g.ball_y, g.vx, g.vy = 1.0, 100.0, -80.0, -60.0
        g.step(0.05)
        self.assertGreater(g.vx, 0)
        self.assertIn("wall", [e[0] for e in g.take_events()])
        g.ball_x, g.ball_y, g.vx, g.vy = 100.0, 0.5, 20.0, -90.0
        g.step(0.02)
        self.assertGreater(g.vy, 0)
        g.paddle_x = 80.0
        g.ball_x, g.ball_y, g.vx, g.vy = 98.0, HB.PADDLE_Y - 6.0, 0.0, 90.0
        g.step(0.05)
        self.assertLess(g.vy, 0)
        self.assertIn("paddle", [e[0] for e in g.take_events()])

    def test_hitting_the_edge_of_the_paddle_sends_the_ball_that_way(self):
        for offset, sign in ((-16, -1), (16, 1)):
            g = HB.Breakout()
            g.launch()
            g.paddle_x = 100.0
            g.ball_x, g.ball_y, g.vx, g.vy = 100 + HB.PADDLE_W / 2 + offset - 2, HB.PADDLE_Y - 3.0, 0.0, 100.0
            g.step(0.03)
            self.assertEqual((g.vx > 0) - (g.vx < 0), sign)
            self.assertGreaterEqual(abs(g.vy), HB.MIN_VERTICAL * g.speed - 1e-6)

    def test_a_brick_disappears_when_hit_and_scores(self):
        g = HB.Breakout()
        g.launch()
        brick = g.bricks[-1]
        g.ball_x, g.ball_y = brick.x + 10.0, brick.y + HB.BRICK_H + 1.0
        g.vx, g.vy = 0.0, -100.0
        before = g.remaining
        g.step(0.05)
        self.assertEqual(g.remaining, before - 1)
        self.assertFalse(brick.alive)
        self.assertEqual(g.score, HB.POINTS)
        self.assertGreater(g.vy, 0)                                                  # and the ball turned round
        self.assertIn("brick", [e[0] for e in g.take_events()])

    def test_the_ball_never_tunnels_through_a_brick_even_in_one_long_frame(self):
        g = HB.Breakout()
        g.launch()
        g.ball_x, g.ball_y = g.bricks[-1].x + 10.0, g.bricks[-1].y + HB.BRICK_H + 9.0
        g.vx, g.vy = 0.0, -HB.MAX_SPEED
        g.step(0.1)                                                                  # the longest frame the game allows
        self.assertLess(g.remaining, HB.COLS * HB.ROWS)

    def test_clearing_every_brick_wins(self):
        g = HB.Breakout()
        for b in g.bricks[1:]:
            b.alive = False
        last = g.bricks[0]
        g.launch()
        g.ball_x, g.ball_y, g.vx, g.vy = last.x + 10.0, last.y + HB.BRICK_H + 1.0, 0.0, -100.0
        g.step(0.05)
        self.assertEqual(g.remaining, 0)
        self.assertEqual(g.state, "clear")
        self.assertIn("clear", [e[0] for e in g.take_events()])
        g.step(1.0, 1)                                                               # (nothing moves once it is won)
        self.assertEqual(g.state, "clear")

    def test_three_lives_then_a_free_restart(self):
        g = HB.Breakout()
        for expected in (2, 1, 0):
            g.launch()
            g.ball_y = HB.FIELD_H + 5
            g.step(0.02)
            self.assertEqual(g.lives, expected)
            self.assertIn("lose", [e[0] for e in g.take_events()])
            if expected:
                self.assertEqual(g.state, "ready")                                   # the ball is back on the paddle
        self.assertEqual(g.state, "over")
        g.step(1.0, 1)
        self.assertEqual(g.state, "over")
        g.launch()                                                                   # a launch press starts a brand new game
        self.assertEqual((g.state, g.lives, g.score, g.remaining), ("ready", 3, 0, HB.COLS * HB.ROWS))

    def test_the_ball_always_keeps_a_real_vertical_speed(self):
        g = HB.Breakout()
        g.launch()
        for _ in range(4000):
            cx = g.paddle_x + HB.PADDLE_W / 2
            g.step(DT, 0 if abs(g.ball_x - cx) < 3 else (1 if g.ball_x > cx else -1))
            if g.state == "playing":
                speed = (g.vx ** 2 + g.vy ** 2) ** 0.5
                self.assertGreaterEqual(abs(g.vy), HB.MIN_VERTICAL * speed * 0.98 - 1e-6) if speed else None
            self.assertTrue(-5 <= g.ball_x <= HB.FIELD_W + 5)
            if g.state != "playing":
                g.launch() if g.state in ("ready", "over") else None
            if g.state == "clear":
                break

    def test_a_ball_inside_the_paddle_or_a_brick_is_pushed_out_not_stuck(self):
        g = HB.Breakout()
        g.launch()
        brick = g.bricks[10]
        g.ball_x, g.ball_y = brick.x + 12.0, brick.y + 2.0                           # right in the middle of a brick
        g.vx, g.vy = 30.0, -20.0
        g.step(0.05)
        self.assertFalse(brick.alive)
        for _ in range(200):
            g.step(DT)
        self.assertNotEqual(g.vy, 0.0)

    def test_the_game_can_be_cleared_in_a_sensible_time_by_players_of_different_accuracy(self):
        import random
        times = []
        for seed in range(5):
            g = HB.Breakout()
            times.append(bot(g, err=random.Random(seed).uniform(-14, 14), rng=random.Random(seed)))
            self.assertEqual(g.state, "clear", seed)
            self.assertEqual(g.score, HB.POINTS * HB.COLS * HB.ROWS)
            self.assertEqual(g.lives, 3)
        self.assertLess(max(times), 240)                                              # nobody is stuck for minutes
        self.assertGreater(min(times), 45)                                            # and it is not over in a blink

    def test_no_rally_goes_on_for_ever_without_a_brick_falling(self):
        import random
        for seed in range(8):
            g = HB.Breakout()
            rnd = random.Random(seed)
            err, last, since, worst, total = rnd.uniform(-14, 14), g.remaining, 0.0, 0.0, 0.0
            while g.state != "clear" and total < 900:
                if g.state in ("ready", "over"):
                    g.launch()
                cx = g.paddle_x + HB.PADDLE_W / 2
                g.step(DT, 0 if abs(g.ball_x + 2 + err - cx) < 3 else (1 if g.ball_x + 2 + err > cx else -1))
                since += DT
                total += DT
                if rnd.random() < 0.02:
                    err = rnd.uniform(-16, 16)                                      # (a person's aim is never the same twice)
                if g.remaining != last:
                    last, worst, since = g.remaining, max(worst, since), 0.0
            self.assertEqual(g.state, "clear", f"seed {seed}")
            self.assertLess(max(worst, since), 45, f"seed {seed}: {worst:.0f} s without a brick")

    def test_even_a_paddle_that_always_aims_the_same_way_gets_there(self):
        for seed in (0, 4, 6):
            import random
            g = HB.Breakout()
            err = random.Random(seed).uniform(-14, 14)
            t = 0.0
            while g.state != "clear" and t < 900:
                if g.state in ("ready", "over"):
                    g.launch()
                cx = g.paddle_x + HB.PADDLE_W / 2
                g.step(DT, 0 if abs(g.ball_x + 2 + err - cx) < 3 else (1 if g.ball_x + 2 + err > cx else -1))
                t += DT
            self.assertEqual(g.state, "clear", seed)

    def test_the_speed_stays_in_range(self):
        g = HB.Breakout()
        bot(g, seconds=40)
        self.assertLessEqual(g.speed, HB.MAX_SPEED)
        self.assertGreaterEqual(g.speed, HB.BASE_SPEED)


# ------------------------------------------------------------------ 9. the computer's desktop
class DesktopTests(unittest.TestCase):
    def test_the_menu_is_the_one_that_was_asked_for(self):
        d = G.Desktop()
        self.assertEqual(d.items, ("PLAY GAME", "HIGH SCORES", "LOCKED FILES", "EXIT"))
        self.assertEqual(G.BOOT_LINES, ("BOOTING...", "CHECKING DISK...", "LOADING ARCHIVE..."))
        self.assertEqual(C.BREAKOUT_TITLE, "HAPPY BREAKOUT v0.3")
        self.assertEqual(C.BREAKOUT_BLURB, '"A tiny game I made instead of doing homework."')

    def test_each_entry_does_its_own_thing(self):
        d = G.Desktop()
        self.assertEqual(d.choose(False), "play")
        d.pick(2)
        self.assertEqual(d.choose(False), "scores")
        d.pick(4)
        self.assertEqual(d.choose(False), "exit")
        self.assertFalse(d.pick(5))
        self.assertFalse(d.pick(0))

    def test_the_locked_files_stay_locked_until_the_game_is_cleared(self):
        d = G.Desktop()
        d.pick(3)
        self.assertEqual(d.choose(False), "locked")
        self.assertIn("ACCESS DENIED", d.message)
        self.assertEqual(d.choose(True), "files")
        self.assertEqual(d.message, "")

    def test_the_cursor_wraps(self):
        d = G.Desktop()
        d.move(-1)
        self.assertEqual(d.items[d.cursor], "EXIT")
        d.move(1)
        self.assertEqual(d.items[d.cursor], "PLAY GAME")


class ComputerTests(TrialCase):
    def prepared(self):
        scene = self.enter()
        self.d.restore_power()
        self.d.listen_to_phone()
        self.d.open_cabinet()
        self.d.read_note()
        return scene

    def to_desktop(self):
        scene = self.prepared()
        self.d.get_boot_disk()
        self.d.use("computer")
        self.assertIsInstance(scene.panel, UI.ComputerPanel)
        self.d.tap(K.K_e)                                                           # INSERT BOOT DISK? YES
        self.d.seconds(4.7)
        self.assertEqual(scene.panel.stage, "desktop")
        return scene

    def test_it_cannot_be_started_without_the_boot_disk(self):
        scene = self.prepared()
        self.assertEqual(scene.run.computer_state(), "standby")
        self.assertFalse(scene.run.finish_computer())
        self.d.use("computer")
        self.assertIsNone(scene.panel)
        self.assertFalse(scene.run.computer_done)
        self.assertEqual(self.manager.secret_trials, 0)

    def test_it_needs_the_power_the_cabinet_the_disk_and_the_game(self):
        run = G.TrialRun()
        self.assertEqual(run.computer_state(), "dark")
        run.power = True
        self.assertEqual(run.computer_state(), "standby")
        run.inventory.append("OLD BOOT DISK")                                      # a disk alone (without the cabinet) is not enough
        self.assertEqual(run.computer_state(), "standby")
        run.cabinet_open = True
        self.assertEqual(run.computer_state(), "ready")
        self.assertFalse(run.finish_computer())                                    # the game has not been cleared
        run.clear_breakout()
        self.assertTrue(run.finish_computer())
        self.assertEqual(run.computer_state(), "done")

    def test_the_disk_question_boots_into_the_desktop_with_its_texts(self):
        scene = self.prepared()
        self.d.get_boot_disk()
        shown = []
        real = UI.draw_text

        def spy(surf, text, *a, **k):
            shown.append(str(text))
            return real(surf, text, *a, **k)
        with patch.object(UI, "draw_text", spy):
            self.d.use("computer")
            self.assertEqual(scene.panel.stage, "ask")
            self.d.frames(2)
            self.d.tap(K.K_e)
            self.assertEqual(scene.panel.stage, "boot")
            self.d.seconds(4.7)
        joined = "\n".join(shown).upper()
        for needle in ("INSERT BOOT DISK?", "BOOTING...", "CHECKING DISK...", "LOADING ARCHIVE...", "PERSONAL COMPUTER", "DISK A:",
                       "HAPPY BREAKOUT V0.3", "A TINY GAME I MADE INSTEAD OF DOING HOMEWORK.", "[1] PLAY GAME", "[2] HIGH SCORES",
                       "[3] LOCKED FILES", "[4] EXIT"):
            self.assertIn(needle, joined, needle)
        names = [n for _, n in self.d.sounds]
        self.assertEqual(names.count("disk_insert"), 1)
        self.assertEqual(names.count("crt_boot"), 1)

    def test_saying_no_keeps_the_disk_and_closes_the_screen(self):
        scene = self.prepared()
        self.d.get_boot_disk()
        self.d.use("computer")
        self.d.tap(K.K_RIGHT)
        self.d.tap(K.K_e)
        self.assertIsNone(scene.panel)
        self.assertTrue(scene.run.has_boot_disk)

    def test_the_locked_files_refuse_to_open_before_the_game_is_cleared(self):
        scene = self.to_desktop()
        self.d.tap(K.K_3)
        self.assertEqual(scene.panel.stage, "desktop")
        self.assertIn("ACCESS DENIED", scene.panel.desktop.message)
        for _ in range(10):                                                          # mashing E there does not open them either
            self.d.tap(K.K_e)
        self.assertEqual(scene.panel.stage, "desktop")
        self.assertFalse(scene.run.computer_done)
        self.assertFalse(scene.run.breakout_cleared)

    def test_high_scores_and_exit_work_and_cost_nothing(self):
        scene = self.to_desktop()
        wallet = (self.profile.tickets, self.profile.tokens)
        self.d.tap(K.K_2)
        self.assertEqual(scene.panel.stage, "scores")
        self.d.tap(K.K_e)
        self.assertEqual(scene.panel.stage, "desktop")
        self.d.tap(K.K_4)
        self.assertIsNone(scene.panel)
        self.assertEqual((self.profile.tickets, self.profile.tokens), wallet)
        self.assertTrue(scene.run.has_boot_disk)

    def test_the_paddle_answers_the_arrow_keys_and_the_game_does_not_clash_with_other_keys(self):
        scene = self.to_desktop()
        self.d.tap(K.K_1)
        panel = scene.panel
        self.assertEqual(panel.stage, "game")
        x0 = panel.game.paddle_x
        self.d.frames(1, [key_down(K.K_RIGHT)])
        self.d.frames(20)
        self.d.frames(1, [key_up(K.K_RIGHT)])
        x1 = panel.game.paddle_x
        self.assertGreater(x1, x0 + 20)
        self.d.frames(10)
        self.assertEqual(panel.game.paddle_x, x1)                                    # released: it stops
        self.d.frames(1, [key_down(K.K_a)])
        self.d.frames(20)
        self.d.frames(1, [key_up(K.K_a)])
        self.assertLess(panel.game.paddle_x, x1)                                     # A moves left, too
        px, py = scene.avatar.x, scene.avatar.y
        self.d.tap(K.K_q)                                                            # the Quest Log key does nothing in here
        self.d.tap(K.K_TAB)
        self.assertIs(scene.panel, panel)
        self.assertEqual(self.story.log, None)
        self.assertEqual((scene.avatar.x, scene.avatar.y), (px, py))                 # the player's own movement keys do not walk the player
        self.d.tap(K.K_SPACE)
        self.assertEqual(panel.game.state, "playing")
        self.assertIn("breakout_paddle", [n for _, n in self.d.sounds])

    def test_esc_pauses_and_a_second_esc_goes_back_to_the_desktop_without_losing_anything(self):
        scene = self.to_desktop()
        self.d.tap(K.K_1)
        panel = scene.panel
        self.d.tap(K.K_SPACE)
        self.d.seconds(0.5)
        self.d.tap(K.K_ESCAPE)
        self.assertTrue(panel.paused)
        y = panel.game.ball_y
        self.d.seconds(1.0)
        self.assertEqual(panel.game.ball_y, y)                                       # paused: the ball is frozen
        self.d.tap(K.K_e)
        self.assertFalse(panel.paused)
        self.d.tap(K.K_ESCAPE)
        self.d.tap(K.K_ESCAPE)
        self.assertEqual(panel.stage, "desktop")
        self.assertIs(scene.panel, panel)

    def test_losing_all_three_lives_just_lets_you_try_again_for_free(self):
        scene = self.to_desktop()
        wallet = (self.profile.tickets, self.profile.tokens)
        self.d.tap(K.K_1)
        panel = scene.panel
        g = panel.game
        for expected in (2, 1, 0):
            self.d.tap(K.K_SPACE)
            g.ball_y = HB.FIELD_H + 3                                               # (the ball slips past the paddle)
            self.d.seconds(0.1)
            self.assertEqual(g.lives, expected)
        self.assertEqual(g.state, "over")
        self.assertIn("breakout_lose", [n for _, n in self.d.sounds])
        self.d.frames(2)
        shown = []
        real = UI.draw_text
        with patch.object(UI, "draw_text", lambda surf, text, *a, **k: (shown.append(str(text)), real(surf, text, *a, **k))[1]):
            self.d.frames(2)
        self.assertTrue(any("TRY AGAIN" in t for t in shown))
        self.assertFalse(scene.run.breakout_cleared)
        self.d.tap(K.K_e)                                                           # restart
        self.assertEqual((g.state, g.lives, g.remaining), ("ready", 3, HB.COLS * HB.ROWS))
        self.assertEqual((self.profile.tickets, self.profile.tokens), wallet)       # nothing was charged

    def test_clearing_the_game_shows_game_clear_and_opens_the_locked_files(self):
        scene = self.to_desktop()
        self.d.tap(K.K_1)
        shown = []
        real = UI.draw_text
        with patch.object(UI, "draw_text", lambda surf, text, *a, **k: (shown.append(str(text)), real(surf, text, *a, **k))[1]):
            self.d.play_breakout()
            self.d.seconds(4.5)
        self.assertEqual(scene.panel.stage, "clear")
        joined = "\n".join(shown).upper()
        for needle in ("GAME CLEAR!", "FINALLY FIXED THE COLLISION BUG.", "ONLY TOOK ME THREE NIGHTS.", "I SHOULD PROBABLY DO MY HOMEWORK NOW."):
            self.assertIn(needle, joined, needle)
        self.assertTrue(scene.run.breakout_cleared)
        self.assertIn("breakout_clear", [n for _, n in self.d.sounds])
        self.d.tap(K.K_e)
        self.assertEqual(scene.panel.stage, "desktop")                              # back on the old computer's desktop
        self.d.tap(K.K_3)
        self.assertEqual(scene.panel.stage, "files")
        self.assertFalse(scene.run.computer_done)                                    # not done until the files are read
        self.d.seconds(1.0)
        self.d.tap(K.K_e)
        self.assertEqual(scene.panel.stage, "files")                                 # (too early to skip the reveal)
        self.d.seconds(3.7)
        shown.clear()
        with patch.object(UI, "draw_text", lambda surf, text, *a, **k: (shown.append(str(text)), real(surf, text, *a, **k))[1]):
            self.d.frames(2)
        joined = "\n".join(shown).upper()
        for needle in ("PLAYER_000", "SYSTEM ADMINISTRATOR ACCESS"):
            self.assertIn(needle, joined)
        self.assertNotIn("KEVIN", joined)

    def test_the_trial_finishes_after_the_files_and_miaos_lines_and_not_before(self):
        scene = self.to_desktop()
        self.d.tap(K.K_1)
        self.d.play_breakout()
        self.d.seconds(0.5)
        self.d.tap(K.K_e)
        self.d.tap(K.K_3)
        self.d.seconds(4.6)
        self.assertFalse(self.manager.trial_done("trial_01"))                       # the files are on screen: not yet
        self.d.tap(K.K_e)
        self.d.seconds(0.5)
        spoken = []
        while scene.dialogue is not None:
            spoken.append((scene.dialogue.line.speaker, scene.dialogue.line.text))
            self.assertFalse(self.manager.trial_done("trial_01"))                   # still not, while the lines are being read
            self.d.seconds(1.8)
            self.d.tap(K.K_e)
            self.d.frames(5)
        self.assertEqual(spoken, [("PLAYER", "Wait... the top player had administrator access?"),
                                  ("MIAO MEOW", "I think I've seen that name on the leaderboard before..."),
                                  ("MIAO MEOW", "But I thought they just really liked playing games.")])
        self.assertIsInstance(scene.panel, UI.CompletePanel)
        self.assertTrue(self.manager.trial_done("trial_01"))

    def test_the_game_can_be_played_with_real_key_presses_from_start_to_finish(self):
        scene = self.to_desktop()
        self.d.tap(K.K_1)
        for b in scene.panel.game.bricks[:-5]:                                       # (the rest of the wall is cleared to keep the test short)
            b.alive = False
        self.d.play_breakout(real=True)
        self.assertEqual(scene.panel.game.state, "clear")
        self.assertTrue(scene.run.breakout_cleared)
        self.assertEqual(scene.panel.stage, "clear")


# ------------------------------------------------------------------ 8. the plushie
class PlushieTests(TrialCase):
    def test_it_is_an_optional_scene_with_no_reward(self):
        scene = self.enter()
        before = (self.manager.secret_items, self.manager.secret_trials, list(scene.run.clues), list(scene.run.inventory),
                  self.profile.tickets, self.profile.tokens, scene.run.objective)
        events = len(self.events)
        self.d.use("plushie")
        spoken = []
        while scene.dialogue is not None:
            spoken.append((scene.dialogue.line.speaker, scene.dialogue.line.text))
            self.d.seconds(1.8)
            self.d.tap(K.K_e)
            self.d.frames(5)
        self.assertEqual(spoken, [("PLAYER", "Wait... doesn't this look like you?"), ("MIAO MEOW", "Me?!"),
                                  ("MIAO MEOW", "Hey! That plushie is adorable!"),
                                  ("MIAO MEOW", "...Actually, I think it looks smarter than me."),
                                  ("PLAYER", "That's a pretty low bar."), ("MIAO MEOW", "HEY!!")])
        after = (self.manager.secret_items, self.manager.secret_trials, list(scene.run.clues), list(scene.run.inventory),
                 self.profile.tickets, self.profile.tokens, scene.run.objective)
        self.assertEqual(before, after)
        self.assertEqual(self.events[events:], [])                                  # no story event, no secret item, no trial credit
        self.assertTrue(scene.run.plushie_seen)

    def test_the_trial_can_be_finished_without_ever_touching_it(self):
        scene = self.enter()
        self.d.play_through(plushie=False)
        self.assertFalse(scene.run.plushie_seen)
        self.assertTrue(self.manager.trial_done("trial_01"))

    def test_it_is_a_toy_not_the_npc_sprite(self):
        plush = A.plushie()
        npc = __import__("miao_meow").miao_frame()
        self.assertNotEqual(plush.get_size(), npc.get_size())
        self.assertNotEqual(pygame.image.tostring(pygame.transform.scale(plush, npc.get_size()), "RGBA"), pygame.image.tostring(npc, "RGBA"))

    def test_the_second_time_is_short(self):
        scene = self.enter()
        self.d.use("plushie")
        self.d.talk_through()
        self.d.use("plushie")
        self.assertEqual(len(scene.dialogue.lines), 1)


# ------------------------------------------------------------------ 10-14. completion, once, leaving, replaying, saving
class CompletionTests(TrialCase):
    def test_a_full_playthrough_records_the_trial_once_with_its_fragment(self):
        scene = self.enter()
        self.d.play_through()
        self.assertIsInstance(scene.panel, UI.CompletePanel)
        self.assertTrue(self.manager.trial_done("trial_01"))
        self.assertEqual(self.manager.secret_trials, 1)
        self.assertEqual(self.manager.memory_fragments, 1)
        self.assertTrue(self.manager.has_memory_fragment("trial_01"))
        self.assertTrue(self.manager.state["flags"]["memory_fragment_01"])
        self.assertEqual(self.events.count("secret_trial_done"), 1)
        self.assertEqual(self.manager.secret_items, 1)                              # the Secret Items are untouched (just the gear)
        self.assertEqual((self.profile.tickets, self.profile.tokens), (self.TICKETS, self.TOKENS))

    def test_it_is_not_recorded_while_the_room_is_still_unfinished(self):
        scene = self.enter()
        self.d.restore_power()
        self.d.listen_to_phone()
        self.d.open_cabinet()
        self.d.read_note()
        self.assertFalse(self.manager.trial_done("trial_01"))
        self.assertEqual(self.manager.secret_trials, 0)
        self.assertNotIn("secret_trial_done", self.events)
        self.assertFalse(self.manager.has_memory_fragment("trial_01"))

    def test_the_finish_card_offers_a_way_back_and_it_works(self):
        before = (self.room.player.x, self.room.player.y, self.room.player.facing)
        scene = self.enter()
        self.d.play_through()
        self.d.finish_card()
        self.assertIsInstance(self.game.scenes.current, LT.LegacyTerminalScene)
        self.assertEqual(self.game.scenes.current.status(TRIALS[0]).code, "done")
        self.assertEqual((self.room.player.x, self.room.player.y, self.room.player.facing), before)
        self.d.tap(K.K_ESCAPE)                                                       # out of the terminal, out of the vending machine
        self.d.frames(90)
        self.assertIs(self.game.scenes.current, self.room)

    def test_staying_in_the_room_after_the_finish_is_allowed(self):
        scene = self.enter()
        self.d.play_through()
        self.d.finish_card(stay=True)
        self.assertIs(self.game.scenes.current, scene)
        self.assertIsNone(scene.panel)
        self.d.tap(K.K_RIGHT)
        self.d.frames(30)                                                           # still walkable
        self.assertGreater(scene.avatar.x, GS.START[0])

    def test_the_quest_log_and_the_terminal_show_one_of_three(self):
        scene = self.enter()
        self.d.play_through()
        self.d.finish_card()
        term = self.game.scenes.current
        self.assertEqual(term.manager.secret_trials, 1)
        shown = []
        real = quest_ui.draw_text

        def spy(surf, text, *a, **k):
            shown.append(str(text))
            return real(surf, text, *a, **k)
        with patch.object(quest_ui, "draw_text", spy):
            quest_ui.QuestLogUI(self.manager, self.profile).draw(pygame.Surface((400, 300)))
        self.assertIn("1/3", shown)
        self.assertEqual(self.manager.secret_trials, 1)

    def test_other_trials_and_items_are_not_touched(self):
        self.enter()
        self.d.play_through()
        self.d.finish_card()
        status = trial_status(self.manager, self.profile, TRIALS[1])                  # chapter 02 opens; nothing earned yet
        self.assertEqual((status.code, status.lock), ("locked", quests.LOCK_EARNINGS))
        self.assertTrue(self.manager.chapter_unlocked(2))
        self.assertFalse(self.manager.trial_done("trial_02"))
        self.assertFalse(self.manager.trial_done("trial_03"))
        self.assertEqual(self.manager.secret_items, 1)
        status = trial_status(self.manager, self.profile, TRIALS[2])
        self.assertEqual(status.code, "locked")
        self.assertIn("COMPLETE CHAPTER 02 FIRST", status.reasons)
        self.assertEqual(self.manager.state["stats"]["secret_trials"], ["trial_01"])

    def test_an_old_save_with_trial_02_done_first_makes_no_difference(self):
        self.manager.state["stats"]["secret_trials"] = ["trial_02"]
        self.enter()
        self.d.play_through()
        self.assertEqual(self.manager.secret_trials, 2)
        self.assertFalse(self.manager.has_memory_fragment("trial_02"))               # (only trial 01 has a fragment here)


class LeaveAndReturnTests(TrialCase):
    def test_leaving_halfway_records_nothing_and_coming_back_carries_on(self):
        scene = self.enter()
        self.d.restore_power()
        self.d.read_drawer()
        self.leave_to_terminal()
        self.assertFalse(self.manager.trial_done("trial_01"))
        self.assertEqual(self.manager.secret_trials, 0)
        self.assertNotIn("secret_trial_done", self.events)
        again = self.d.enter_trial()
        self.assertIsInstance(again, GS.GoldenAgeScene)
        self.assertIsNot(again, scene)
        self.assertTrue(again.run.power)                                             # where they left off
        self.assertIn("paper", again.run.clues)
        self.assertEqual(again.light, 1.0)
        self.d.seconds(1.5)
        self.assertIsNone(again.dialogue)                                           # the opening does not play twice

    def test_esc_asks_first_and_stay_keeps_you_in_the_room(self):
        scene = self.enter()
        self.d.tap(K.K_ESCAPE)
        self.assertIsInstance(scene.panel, UI.ConfirmPanel)
        self.d.tap(K.K_e)                                                           # STAY is the default
        self.assertIs(self.game.scenes.current, scene)
        self.assertIsNone(scene.panel)

    def test_the_door_leaves_too(self):
        scene = self.enter()
        self.d.use("door")
        self.assertIsInstance(scene.panel, UI.ConfirmPanel)
        self.d.tap(K.K_LEFT)
        self.d.tap(K.K_e)
        self.d.seconds(1.0)
        self.assertIsInstance(self.game.scenes.current, LT.LegacyTerminalScene)

    def test_the_player_is_put_back_exactly_and_can_walk_in_the_arcade_again(self):
        px, py, facing = self.room.player.x, self.room.player.y, self.room.player.facing
        self.enter()
        self.d.walk_to("bookshelf")
        self.leave_to_terminal()
        self.assertEqual((self.room.player.x, self.room.player.y, self.room.player.facing), (px, py, facing))
        self.d.tap(K.K_ESCAPE)
        self.d.frames(90)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(self.room.player.feet.collidelist(self.room.solids), -1)
        self.assertEqual(self.room.player.held, [])
        self.d.frames(1, [key_down(K.K_LEFT)])
        self.d.frames(20)
        self.d.frames(1, [key_up(K.K_LEFT)])
        self.assertLess(self.room.player.x, px)                                     # no longer stuck


class ReplayTests(TrialCase):
    def test_a_finished_trial_can_be_played_again_but_pays_nothing_twice(self):
        scene = self.enter()
        self.d.play_through()
        self.d.finish_card()
        before = (self.manager.secret_trials, self.manager.memory_fragments, dict(self.manager.state["flags"]),
                  dict(self.manager.state["stats"]), self.profile.tickets, self.profile.tokens)
        events = self.events.count("secret_trial_done")
        self.d.tap(K.K_e)                                                           # the terminal's use key: visit the room again
        self.d.frames(60)
        again = self.game.scenes.current
        self.assertIsInstance(again, GS.GoldenAgeScene)
        self.assertIsNot(again, scene)
        self.assertFalse(again.run.power)                                           # a fresh, dark room
        self.assertEqual(again.light, 0.0)
        self.d.seconds(2.0)
        self.assertIsNone(again.dialogue)                                           # (no second opening)
        self.d.play_through()
        self.assertIsInstance(again.panel, UI.CompletePanel)
        self.assertFalse(again.panel.first_time)
        after = (self.manager.secret_trials, self.manager.memory_fragments, dict(self.manager.state["flags"]),
                 dict(self.manager.state["stats"]), self.profile.tickets, self.profile.tokens)
        self.assertEqual(before, after)
        self.assertEqual(self.events.count("secret_trial_done"), events)           # no second completion event
        self.assertEqual(self.manager.secret_trials, 1)

    def test_the_terminal_says_the_room_can_be_visited_again(self):
        self.manager.handle("vending_secret")
        self.manager.handle("secret_trial_done", "trial_01")
        _shop, term = self.open_terminal()
        term.draw(pygame.Surface((400, 300)))
        self.assertEqual(term.status().code, "done")
        self.d.tap(K.K_e)
        self.d.frames(60)
        self.assertIsInstance(self.game.scenes.current, GS.GoldenAgeScene)


class SaveTests(TrialCase):
    def test_the_finish_survives_saving_and_loading_and_the_unfinished_room_does_not(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "alice.json")
        ProfileStore(path).autosave(self.profile)
        self.enter()
        self.d.restore_power()
        loaded = ProfileStore(path).load()                                          # halfway: nothing about it was saved
        self.assertFalse(quests.QuestManager(LocalSession(loaded)).trial_done("trial_01"))
        self.d.read_drawer()
        self.d.listen_to_phone()
        self.d.open_cabinet()
        self.d.read_note()
        self.d.get_boot_disk()
        self.d.boot_computer()
        loaded = ProfileStore(path).load()
        m2 = quests.QuestManager(LocalSession(loaded))
        self.assertTrue(m2.trial_done("trial_01"))
        self.assertEqual(m2.secret_trials, 1)
        self.assertEqual(m2.memory_fragments, 1)
        self.assertTrue(m2.state["flags"]["trial01_intro"])
        self.assertEqual((loaded.tickets, loaded.tokens), (self.TICKETS, self.TOKENS))
        self.assertEqual(m2.secret_items, 1)
        game2 = Game(session=LocalSession(loaded))                                 # a new game: the trial is done, the room starts fresh
        self.addCleanup(game2.quit)
        self.assertIsNone(getattr(game2.hub, "trial01_run", None))
        self.assertEqual(trial_status(game2.hub.story.manager, loaded, TRIALS[0]).code, "done")

    def test_a_damaged_save_never_invents_a_completion(self):
        p = PlayerProfile(profile_id="bad", display_name="BAD")
        p.set_story({"opening_done": True, "stats": {"secret_trials": "trial_01", "secret_items": "gem"},
                     "flags": {"memory_fragment_01": "yes"}})
        m = quests.QuestManager(LocalSession(p))
        self.assertFalse(m.trial_done("trial_01"))                                  # a bare string is not a list of trials
        self.assertEqual(m.secret_trials, 0)
        self.assertEqual(m.secret_items, 0)
        self.assertFalse(m.has_secret_item("gem"))
        self.assertFalse(m.has_memory_fragment("trial_01"))                         # and "yes" is not True


# ------------------------------------------------------------------ 17. furniture, walking, collisions
class RoomTests(TrialCase):
    def setUp(self):
        super().setUp()
        self.scene = self.enter()

    def test_every_interaction_can_be_reached_by_walking(self):
        for key in self.scene.spots:
            self.d.walk_to(key)
            self.assertEqual(self.scene.nearby.key, key)
            self.assertEqual(self.scene.avatar.feet.collidelist(self.scene.solids), -1)

    PUZZLE = ("power_box", "phone", "drawer", "cabinet", "bookshelf", "computer")

    def test_every_thing_says_the_same_word_so_a_clue_looks_like_decoration(self):
        prompts = {k: sp.prompt for k, sp in self.scene.spots.items()}
        self.assertEqual({k for k, v in prompts.items() if v != "INSPECT"}, {"door"})
        self.assertEqual(prompts["door"], "LEAVE ROOM")
        for key in self.PUZZLE + ("desk", "window", "noodle_cup", "plushie", "poster"):
            self.assertEqual(prompts[key], "INSPECT", key)

    def test_there_are_at_least_twenty_things_to_inspect_and_the_main_ones_are_among_them(self):
        things = [k for k in self.scene.spots if k != "door"]
        self.assertGreaterEqual(len(things), 20)
        for key in self.PUZZLE:
            self.assertIn(key, things)
        for key in ("plushie", "alarm_clock", "window", "noodle_cup", "coffee_mug", "homework", "textbook", "cartridges", "poster",
                    "photo_frame", "trash_bin", "cookie_jar", "desk_lamp", "bedside_lamp", "drawer", "desk"):
            self.assertIn(key, things, key)

    def test_nothing_glows_or_jumps_to_say_it_matters(self):
        for sp in self.scene.spots.values():
            self.assertFalse(hasattr(sp, "highlight") or hasattr(sp, "sparkle") or hasattr(sp, "icon"), sp.key)
        self.d.walk_to("power_box")
        self.d.frames(30)
        a = pygame.Surface((400, 300))
        self.scene.draw(a)
        self.d.walk_to("window")
        self.d.frames(30)
        self.assertEqual(self.scene.avatar.prompt.label, "INSPECT")

    def test_looking_at_ordinary_things_never_moves_the_story_along(self):
        scene = self.scene
        before = (scene.run.objective, list(scene.run.clues), list(scene.run.inventory), scene.run.power, scene.run.cabinet_open,
                  scene.run.phone_plays, self.manager.secret_items, self.manager.secret_trials, self.profile.tickets, self.profile.tokens)
        ordinary = ("window", "alarm_clock", "bedside_lamp", "plushie", "photo_frame", "poster", "cartridges", "noodle_cup",
                    "cookie_jar", "coffee_mug", "homework", "textbook", "plant", "trash_bin", "desk", "desk_lamp")
        for key in ordinary:
            self.d.use(key)
            self.assertTrue(scene.dialogue is not None or scene.panel is not None or scene.notice.visible, key)
            while scene.dialogue is not None or scene.panel is not None:
                if scene.panel is not None:
                    self.d.tap(K.K_ESCAPE)
                else:
                    self.d.seconds(1.5)
                    self.d.tap(K.K_e)
                self.d.frames(3)
        after = (scene.run.objective, list(scene.run.clues), list(scene.run.inventory), scene.run.power, scene.run.cabinet_open,
                 scene.run.phone_plays, self.manager.secret_items, self.manager.secret_trials, self.profile.tickets, self.profile.tokens)
        self.assertEqual(before, after)
        self.assertEqual(scene.run.objective, "power")
        self.assertEqual(set(scene.run.inspected), set(ordinary) - {"desk_lamp", "bedside_lamp"})        # (the lamps keep no count)

    def test_the_things_in_the_room_say_what_was_asked_for(self):
        lines = {k: [[t for _, t, _ in v] for v in info["lines"]] for k, info in C.LIFE.items()}
        self.assertEqual(lines["window"][0], ["Why is it so windy outside?", "Wait... this almost feels like NYCU."])
        self.assertEqual(lines["noodle_cup"][0], ["Instant noodles. The universal language of university students."])
        self.assertEqual(lines["coffee_mug"][0], ["There's still coffee inside.", "...I'm not drinking that."])
        self.assertEqual(lines["alarm_clock"][0], ["3:47 AM.", "Somebody really needed a better sleep schedule."])
        self.assertEqual(lines["trash_bin"][0], ["Rejected game ideas. A lot of them.", "Honestly, relatable."])
        self.assertEqual(lines["cookie_jar"][0], ["Cookies!", "...It's empty.", "That's the saddest thing I've seen all day."])
        speakers = [sp for sp, _, _ in C.LIFE["cookie_jar"]["lines"][0]]
        self.assertEqual(speakers, ["PLAYER", "PLAYER", "MIAO MEOW"])
        for key, info in C.LIFE.items():
            self.assertGreaterEqual(len(info["lines"]), 1, key)

    def test_each_visit_to_a_thing_can_say_something_different(self):
        scene = self.scene
        self.d.use("window")
        first = scene.dialogue.lines[0].text
        self.d.talk_through()
        self.d.use("window")
        self.assertNotEqual(scene.dialogue.lines[0].text, first)
        self.d.talk_through()

    def test_lamps_answer_differently_with_and_without_power(self):
        scene = self.scene
        self.d.use("desk_lamp")
        self.assertEqual(scene.dialogue.lines[0].text, C.LAMP_OFF[0][1])
        self.d.talk_through()
        scene.run.circuit.rots = scene.run.circuit.solution()
        scene.run.restore_power()
        self.d.use("desk_lamp")
        self.assertEqual(scene.dialogue.lines[0].text, C.LAMP_ON[0][1])
        self.d.talk_through()

    def test_things_to_read_open_the_book_reader_and_can_be_read_again(self):
        scene = self.scene
        for key, tag in (("homework", "homework"), ("textbook", "textbook"), ("desk", "sticky"), ("trash_bin", "trash")):
            self.d.use(key)
            self.d.talk_through()
            self.assertIsInstance(scene.panel, UI.PagedPanel, key)
            self.assertEqual(scene.panel.tag, tag)
            pages = len(scene.panel.pages)
            for _ in range(pages):
                self.d.tap(K.K_e)
            self.assertIsNone(scene.panel)
            self.d.use(key)                                                         # the second time: straight to the pages
            self.assertIsInstance(scene.panel, UI.PagedPanel)
            self.d.tap(K.K_ESCAPE)

    def test_prompt_areas_do_not_pile_up_on_each_other(self):
        spots = list(self.scene.spots.values())
        for i, a in enumerate(spots):
            for b in spots[i + 1:]:
                inter = a.zone.clip(b.zone)
                self.assertLessEqual(inter.w * inter.h, 160, (a.key, b.key, inter))
        for sp in spots:
            self.assertGreaterEqual(sp.zone.w, 13, sp.key)

    def test_no_prompt_area_is_walled_in_by_furniture(self):
        for sp in self.scene.spots.values():
            self.assertIsNotNone(self.d.route(self.scene, sp.key), sp.key)

    def test_the_player_cannot_walk_through_walls_or_furniture(self):
        av = self.scene.avatar
        for key, limit in ((K.K_LEFT, lambda: av.x >= 20 + 5 - 0.01), (K.K_UP, lambda: av.y - 5 >= A.WALL_SOLID_BOTTOM - 0.01),
                           (K.K_DOWN, lambda: av.y <= A.FLOOR_BOTTOM + 0.01), (K.K_RIGHT, lambda: av.x <= 400 - 20 - 5 + 0.01)):
            self.d.frames(1, [key_down(key)])
            for _ in range(600):
                self.d.frames(1)
                self.assertEqual(av.feet.collidelist(self.scene.solids), -1)
            self.d.frames(1, [key_up(key)])
            self.assertTrue(limit(), key)

    def test_walking_into_the_desk_and_the_bed_stops_at_their_edge(self):
        av = self.scene.avatar
        self.d.walk_to("computer")                                                  # (standing below the desk, push straight up into it)
        self.d.frames(1, [key_down(K.K_UP)])
        self.d.frames(90)
        self.d.frames(1, [key_up(K.K_UP)])
        self.assertGreaterEqual(av.y - 5, 112 - 0.01)

    def test_nothing_blocks_the_way_from_the_door_to_anything(self):
        for key in self.scene.spots:
            self.assertIsNotNone(self.d.route(self.scene, key), key)

    def test_the_start_is_clear_and_nothing_is_stacked_on_a_prompt_area(self):
        av = self.scene.avatar
        self.assertEqual(pygame.Rect(int(GS.START[0]) - 5, int(GS.START[1]) - 5, 10, 5).collidelist(self.scene.solids), -1)
        self.assertIsNone(self.scene.spot_at(*GS.START))                              # no prompt on arrival

    def test_miao_stands_on_open_floor_away_from_everything_you_can_use(self):
        spots = self.scene.miao_spots
        self.assertGreaterEqual(len(spots), 6)
        zones = [s.zone.inflate(8, 8) for s in self.scene.spots.values()]
        for p in spots:
            self.assertEqual(pygame.Rect(p[0] - 5, p[1] - 4, 10, 5).collidelist(self.scene.solids), -1)
            self.assertTrue(all(not z.collidepoint(p) for z in zones), p)
        for p in GS.MIAO_SPOTS:
            self.assertIn(p, spots, f"{p} is not clear: remove or move it")

    def test_miao_keeps_near_the_player_without_blocking_a_prompt(self):
        for key in ("power_box", "drawer", "bookshelf", "phone", "plushie"):
            self.d.walk_to(key)
            self.d.seconds(3.0)
            miao = self.scene.companion
            for sp in self.scene.spots.values():
                self.assertFalse(sp.rect.inflate(-2, -2).collidepoint(miao.x, miao.y - 4) and sp.key != "door", (key, sp.key))
            self.assertLess(((miao.x - self.scene.avatar.x) ** 2 + (miao.y - self.scene.avatar.y) ** 2) ** 0.5, 170)

    def test_a_prompt_shows_for_the_nearest_thing_and_e_uses_it(self):
        self.d.walk_to("phone")
        self.assertEqual(self.scene.nearby.key, "phone")
        self.d.frames(20)
        self.assertGreater(self.scene.avatar.prompt.alpha, 0.5)
        self.assertEqual(self.scene.avatar.prompt.label, "INSPECT")

    def test_every_sprite_is_drawn_and_the_whole_room_fits_the_canvas(self):
        surf = pygame.Surface((400, 300))
        for _ in range(3):
            self.scene.draw(surf)
        self.assertEqual(A.room_shell().get_size(), (400, 300))
        for name in ("bed", "plushie", "bookshelf", "power_box", "desk", "cabinet", "plant", "game_boxes", "pouf", "door", "window",
                     "corkboard", "bedside_table", "keyboard", "wall_clock", "photo_frame", "trophy_shelf", "rug", "alarm_clock",
                     "noodle_cup", "coffee_mug", "cookie_jar", "low_table", "homework", "textbook", "trash_bin", "side_frame",
                     "side_poster"):
            self.assertGreater(getattr(A, name)().get_width(), 0, name)
        for state in ("off", "standby", "on"):
            self.assertGreater(A.crt(state).get_width(), 0)

    def test_the_room_is_warm_not_neon(self):
        shell = A.room_shell()
        r = g = b = 0
        for x in range(30, 370, 10):
            for y in range(90, 270, 10):
                c = shell.get_at((x, y))
                r, g, b = r + c[0], g + c[1], b + c[2]
        self.assertGreater(r, g)
        self.assertGreater(g, b)                                                    # wood: red > green > blue, nothing like the navy arcade


# ------------------------------------------------------------------ the opening and the hints
class OpeningTests(TrialCase):
    def test_the_opening_plays_once_with_the_exact_lines_then_hands_back_control(self):
        scene = self.enter(watch_intro=False)
        self.d.seconds(1.0)
        spoken = []
        while scene.dialogue is not None:
            spoken.append((scene.dialogue.line.speaker, scene.dialogue.line.text))
            self.d.seconds(2.0)
            self.d.tap(K.K_e)
            self.d.frames(5)
        self.assertEqual(spoken, [("SYSTEM", "TRIAL 01 - THE GOLDEN AGE"), ("SYSTEM", "Explore the room."),
                                  ("PLAYER", "This doesn't look like an arcade..."), ("PLAYER", "More like someone's old bedroom."),
                                  ("MIAO MEOW", "Whoa... it's actually kind of cozy!"),
                                  ("MIAO MEOW", "Well, except for the part where nothing works.")])
        self.assertTrue(self.manager.state["flags"][G.INTRO_FLAG])
        x = scene.avatar.x
        self.d.frames(1, [key_down(K.K_RIGHT)])
        self.d.frames(20)
        self.d.frames(1, [key_up(K.K_RIGHT)])
        self.assertGreater(scene.avatar.x, x)                                       # control is back

    def test_the_opening_uses_the_existing_dialogue_box(self):
        import story_dialogue
        scene = self.enter(watch_intro=False)
        self.d.seconds(1.0)
        self.assertIsInstance(scene.dialogue, story_dialogue.StoryDialogue)
        self.assertEqual(scene.dialogue.speaker.name, "SYSTEM")

    def test_esc_skips_the_opening_and_it_is_not_shown_again(self):
        scene = self.enter(watch_intro=False)
        self.d.seconds(1.0)
        self.d.tap(K.K_ESCAPE)
        self.assertIsNone(scene.dialogue)
        self.assertTrue(self.manager.state["flags"][G.INTRO_FLAG])
        self.leave_to_terminal()
        again = self.d.enter_trial()
        self.d.seconds(2.0)
        self.assertIsNone(again.dialogue)


class HiddenGoalTests(TrialCase):
    """The room never tells the player what to do next: no goal list, no objective banner, no answer-shaped text."""
    BANNED = ("RESTORE THE POWER", "DECODE", "FIND THE BOOKSHELF", "ENTER SHELF", "FIND THE BOOT DISK", "NEW OBJECTIVE", "OBJECTIVE",
              "GOAL:", "SEARCH THE BOOKSHELF", "UNLOCK THE FILE CABINET", "BOOT THE OLD COMPUTER", "INVESTIGATE THE TELEPHONE")

    def record(self):
        shown = []
        real_text, real_show = GS.draw_text, GS.Notice.show

        def text(surf, t, *a, **k):
            shown.append(str(t))
            return real_text(surf, t, *a, **k)

        def show(notice, title, lines=(), *a, **k):
            shown.append(title)
            shown.extend(t for t, _ in lines)
            return real_show(notice, title, lines, *a, **k)
        return shown, patch.object(GS, "draw_text", text), patch.object(GS.Notice, "show", show)

    def test_a_whole_playthrough_never_shows_a_goal_or_an_answer_shaped_instruction(self):
        shown, p1, p2 = self.record()
        said = []
        with p1, p2:
            scene = self.enter()
            self.d.play_through(plushie=True)
        for text in shown:
            for banned in self.BANNED:
                self.assertNotIn(banned, text.upper(), text)
        self.assertNotIn("SHELF", " ".join(shown).upper().replace("BOOKSHELF", ""))

    def test_the_hud_is_just_the_notes_key(self):
        scene = self.enter()
        shown, p1, p2 = self.record()
        with p1, p2:
            for _ in range(5):
                scene.draw(pygame.Surface((400, 300)))
        self.assertEqual({t for t in shown if t.strip()}, {"[TAB] NOTES"})

    def test_the_notes_list_has_no_objective(self):
        scene = self.enter()
        self.d.tap(K.K_TAB)
        shown = []
        real = UI.draw_text
        with patch.object(UI, "draw_text", lambda surf, text, *a, **k: (shown.append(str(text)), real(surf, text, *a, **k))[1]):
            scene.panel.draw(pygame.Surface((400, 300)))
        joined = " ".join(shown).upper()
        self.assertNotIn("OBJECTIVE", joined)
        self.assertIn("CLUES FOUND", joined)

    def test_coming_back_shows_only_the_title_and_explore_the_room(self):
        self.enter()
        self.leave_to_terminal()
        shown = []
        real_show = GS.Notice.show

        def show(notice, title, lines=(), *a, **k):
            shown.append((title, [t for t, _ in lines]))
            return real_show(notice, title, lines, *a, **k)
        with patch.object(GS.Notice, "show", show):
            self.d.enter_trial()
            self.d.seconds(1.0)
        self.assertEqual(shown, [("TRIAL 01 - THE GOLDEN AGE", ["Explore the room."])])

    def test_miao_does_not_volunteer_hints(self):
        scene = self.enter()
        self.d.seconds(90)
        self.assertFalse(scene.bubble.visible)
        self.assertIsNone(scene.dialogue)
        self.assertEqual(scene.run.hints, {})


class HintTests(TrialCase):
    def talk_to_miao(self, scene):
        scene.avatar.x, scene.avatar.y = 270.0, 162.0                               # open floor, nothing to use here
        scene.companion.x, scene.companion.y = 282.0, 166.0
        scene.companion.target = None
        self.d.frames(2)
        self.assertEqual(scene.nearby.key, "miao")
        self.d.tap(K.K_e)

    def test_hints_come_only_from_talking_to_miao_in_three_steps_and_never_give_the_password(self):
        scene = self.enter()
        self.talk_to_miao(scene)
        self.assertTrue(scene.bubble.visible)
        first = scene.bubble.text
        self.assertEqual(first, C.HINTS["power"][0])
        self.talk_to_miao(scene)
        second = scene.bubble.text
        self.talk_to_miao(scene)
        third = scene.bubble.text
        self.assertEqual([first, second, third], list(C.HINTS["power"]))
        self.assertEqual(len({first, second, third}), 3)
        self.talk_to_miao(scene)
        self.assertEqual(scene.bubble.text, third)                                  # the last one just repeats
        for tiers in C.HINTS.values():
            for text in tiers:
                self.assertNotRegex(text.upper(), r"\bSHELF\b")
                self.assertNotRegex(text, r"\.\.\.\.")
                self.assertNotIn("SHELF", text.upper().replace("SHELVES", "").replace("BOOKSHELF", ""))

    def test_the_old_hint_key_does_nothing(self):
        scene = self.enter()
        self.d.tap(K.K_h)
        self.assertFalse(scene.bubble.visible)
        self.assertEqual(scene.run.hints, {})

    def test_each_stage_has_three_steps_vague_then_area_then_direction(self):
        run = G.TrialRun()
        order = [run.objective]
        run.circuit.rots = run.circuit.solution()
        run.restore_power()
        order.append(run.objective)
        run.play_phone()
        order.append(run.objective)
        run.try_cabinet("SHELF")
        order.append(run.objective)
        run.finish_journal()
        order.append(run.objective)
        run.clear_breakout()
        run.finish_computer()
        order.append(run.objective)
        self.assertEqual(order, ["power", "phone", "cabinet", "bookshelf", "computer", "done"])
        for key in order[:5]:
            self.assertEqual(len(C.HINTS[key]), 3, key)
        self.assertEqual(len(C.HINTS["done"]), 1)

    def test_hints_never_cover_a_puzzle_screen(self):
        scene = self.enter()
        self.talk_to_miao(scene)
        self.assertTrue(scene.bubble.visible)
        self.d.walk_to("power_box")
        self.d.tap(K.K_e)
        self.assertIsInstance(scene.panel, UI.CircuitPanel)
        self.assertFalse(scene.bubble.visible)                                       # opening a puzzle clears it

    def test_miao_is_never_what_you_get_when_a_thing_is_in_reach(self):
        scene = self.enter()
        self.d.walk_to("power_box")
        scene.companion.x, scene.companion.y = scene.avatar.x + 4, scene.avatar.y + 4
        self.d.frames(2)
        self.assertEqual(scene.nearby.key, "power_box")

    def test_the_notes_list_shows_the_inventory_and_nothing_pushy(self):
        scene = self.enter()
        self.d.tap(K.K_TAB)
        self.assertIsInstance(scene.panel, UI.NotesPanel)
        surf = pygame.Surface((400, 300))
        scene.panel.draw(surf)
        self.d.tap(K.K_TAB)
        self.assertIsNone(scene.panel)
        scene.run.inventory.append("OLD BOOT DISK")
        self.d.tap(K.K_n)
        scene.panel.draw(surf)


# ------------------------------------------------------------------ the writing: English only, funny, anonymous, fits the page
def all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from all_strings(k)
            yield from all_strings(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from all_strings(v)


class ContentTests(unittest.TestCase):
    @staticmethod
    def player_visible():
        """Every string a player can read in the trial (content, rules and the screens' own words)."""
        out = []
        for name in dir(C):
            if name.isupper():
                out += list(all_strings(getattr(C, name)))
        out += list(all_strings([G.CABINET_NOTE, G.DRAWER_PAPER, G.BOOT_LINES, [c.title for c in G.CLUES.values()]]))
        out += list(all_strings([G.MORSE]))
        return out

    def test_all_the_text_is_english_and_drawable_by_the_pixel_font(self):
        from font import _GLYPHS
        allowed = set(_GLYPHS) | set(" \n")
        strings = self.player_visible()
        self.assertGreater(len(strings), 150)
        for text in strings:
            self.assertTrue(text.isascii(), text)                                    # no Chinese, no curly quotes, no dashes
            for ch in text.upper():
                self.assertIn(ch, allowed, f"{ch!r} in {text[:50]!r}")

    def test_the_scenes_and_screens_have_no_non_english_text_in_their_sources(self):
        for name in ("golden_age.py", "golden_age_content.py", "golden_age_ui.py", "golden_age_scene.py", "happy_breakout.py"):
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                for line in f:
                    self.assertTrue(line.isascii(), f"{name}: {line.strip()[:60]}")

    def test_the_notebook_is_twelve_entries_behind_a_cover_with_the_dates_and_jokes_that_were_asked_for(self):
        self.assertEqual(len(C.JOURNAL_ENTRIES), 12)
        titles = [e["title"] for e in C.JOURNAL_ENTRIES]
        self.assertEqual(len(set(titles)), 12)
        text = " ".join(e["text"] for e in C.JOURNAL_ENTRIES).upper()
        for word in ("NYCU", "WIND", "PROFESSOR", "ASSIGNMENT", "DEADLINE", "NOODLES", "3 AM", "BUG", "COLLISION", "CAT", "HOMEWORK",
                     "FORGOT", "FRIEND", "LAUGH"):
            self.assertIn(word, text, word)
        self.assertIn("The wind at NYCU almost launched me into another dimension today.", C.JOURNAL_ENTRIES[0]["text"])
        self.assertTrue(C.JOURNAL_ENTRIES[0]["title"].startswith("OCT 17"))
        self.assertIn("Maybe you do not always have to win.", " ".join(e["text"] for e in C.JOURNAL_ENTRIES))

    def test_the_owner_stays_anonymous_and_no_ending_is_given_away(self):
        text = " ".join(self.player_visible()).upper()
        for banned in ("KEVIN", "I CREATED THIS ARCADE", "I BUILT THIS ARCADE", "MAKE EVERYONE HAPPY", "MY NAME", "SINCERELY", "YOURS,"):
            self.assertNotIn(banned, text, banned)
        self.assertEqual(text.count("PLAYER_000"), 1)                                # the one mysterious name, once
        self.assertNotIn("ARCADE", " ".join(e["text"] for e in C.JOURNAL_ENTRIES).upper())

    def test_there_are_seven_books_on_the_shelf_each_a_few_pages(self):
        self.assertEqual(set(C.BOOK_ORDER), set(C.BOOKS))
        self.assertGreaterEqual(len(C.BOOKS), 5)
        self.assertLessEqual(len(C.BOOKS) + 1, 8)
        for key, (title, colour, pages) in C.BOOKS.items():
            self.assertGreaterEqual(len(pages), 2, key)
            self.assertEqual(len(colour), 3)
        self.assertEqual(len(C.STICKY_NOTES), 5)
        self.assertGreaterEqual(len(C.HOMEWORK_PAGES), 3)

    def test_every_page_fits_on_the_paper_without_shrinking_and_wraps_to_the_width(self):
        from font import get_font
        pages = [("journal", p) for p in C.JOURNAL_PAGES] + [("trash", p) for p in C.TRASH_PAGES] + \
                [("sticky", p) for p in C.STICKY_NOTES] + [("homework", p) for p in C.HOMEWORK_PAGES] + \
                [("textbook", p) for p in C.TEXTBOOK_PAGES]
        for _, (title, colour, book_pages) in C.BOOKS.items():
            pages += [("book", p) for p in book_pages]
        font = get_font()
        for kind, page in pages:
            rows = UI.page_rows(page["text"], 1)
            self.assertLessEqual(len(rows), UI.MAX_ROWS, f"{kind}: {page['title']} has {len(rows)} rows")
            for row in rows:
                self.assertLessEqual(font.size(row)[0], UI.TEXT_W, row)
            self.assertLessEqual(len(UI.wrap_text(page["title"], UI.TEXT_W)), 2, page["title"])
        self.assertEqual(UI.page_rows("a\n\nb"), ["a", "", "b"])                        # paragraphs keep their blank line
        long_word = "X" * 80
        self.assertTrue(all(font.size(r)[0] <= UI.TEXT_W * 3 for r in UI.page_rows(long_word)))

    def test_the_reader_draws_every_page_inside_the_canvas_and_pages_turn(self):
        sounds = []
        keys = ["journal", "sticky", "homework", "textbook", "trash"] + list(C.BOOK_ORDER)
        for key in keys:
            panel = UI.PagedPanel(UI.paper_pages(key), sounds.append, tag=key)
            surf = pygame.Surface((400, 300))
            for i in range(len(panel.pages)):
                panel.draw(surf)
                panel.handle_event(key_down(K.K_RIGHT))
            self.assertEqual(panel.index, len(panel.pages) - 1)
            for i in range(len(panel.pages)):
                panel.handle_event(key_down(K.K_LEFT))
            self.assertEqual(panel.index, 0)
        self.assertTrue(sounds and set(sounds) == {"page_turn"})                      # a soft page-turn sound, nothing else
        panel = UI.PagedPanel(UI.paper_pages("journal"), tag="journal")
        panel.handle_event(key_down(K.K_ESCAPE))
        self.assertTrue(panel.closed)                                                 # closes at any page, and can be opened again
        again = UI.PagedPanel(UI.paper_pages("journal"), tag="journal")
        self.assertFalse(again.closed)
        self.assertEqual(again.index, 0)

    def test_the_page_number_is_shown(self):
        panel = UI.PagedPanel(UI.paper_pages("journal"))
        shown = []
        real = UI.draw_text
        with patch.object(UI, "draw_text", lambda surf, text, *a, **k: (shown.append(str(text)), real(surf, text, *a, **k))[1]):
            panel.draw(pygame.Surface((400, 300)))
        self.assertIn("1/13", shown)

    def test_the_hints_and_the_opening_use_the_words_that_were_asked_for(self):
        self.assertEqual(C.OPENING[0][1], "TRIAL 01 - THE GOLDEN AGE")
        self.assertEqual(C.OPENING[1][1], "Explore the room.")
        self.assertEqual(len(C.OPENING), 6)
        for text in ("Restore the power", "Decode", "Boot Disk", "SHELF"):
            self.assertNotIn(text.upper(), " ".join(t for _, t, _ in C.OPENING).upper())


# ------------------------------------------------------------------ 18. the story and the save
class BreakoutSaveTests(TrialCase):
    def test_a_cleared_game_is_remembered_in_the_save_and_a_failed_replay_does_not_take_it_away(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "alice.json")
        ProfileStore(path).autosave(self.profile)
        scene = self.enter()
        self.d.restore_power()
        self.d.listen_to_phone()
        self.d.open_cabinet()
        self.d.read_note()
        self.d.get_boot_disk()
        self.assertFalse(self.manager.state.get("flags", {}).get(G.BREAKOUT_FLAG))
        self.d.use("computer")
        self.d.tap(K.K_e)
        self.d.seconds(4.7)
        self.d.tap(K.K_1)
        self.d.play_breakout()
        self.d.seconds(0.5)
        self.assertTrue(self.manager.state["flags"][G.BREAKOUT_FLAG])
        loaded = ProfileStore(path).load()
        self.assertTrue(quests.QuestManager(LocalSession(loaded)).state["flags"][G.BREAKOUT_FLAG])
        self.assertFalse(quests.QuestManager(LocalSession(loaded)).trial_done("trial_01"))        # cleared the game, not yet the trial
        panel = scene.panel
        self.d.tap(K.K_e)                                                           # desktop
        self.d.tap(K.K_1)                                                           # play again and lose on purpose
        for _ in range(3):
            self.d.tap(K.K_SPACE)
            panel.game.ball_y = HB.FIELD_H + 3
            self.d.seconds(0.1)
        self.assertEqual(panel.game.state, "over")
        self.assertTrue(scene.run.breakout_cleared)                                  # still cleared
        self.assertTrue(self.manager.state["flags"][G.BREAKOUT_FLAG])
        self.d.tap(K.K_ESCAPE)                                                       # pause ...
        self.d.tap(K.K_ESCAPE)                                                       # ... and back to the desktop
        self.d.tap(K.K_3)
        self.assertEqual(panel.stage, "files")                                       # and the files still open

    def test_a_game_that_was_cleared_before_opens_the_files_in_a_later_visit(self):
        self.manager.handle(G.BREAKOUT_FLAG)
        scene = self.enter()
        self.assertTrue(scene.run.breakout_cleared)
        self.d.restore_power()
        self.d.listen_to_phone()
        self.d.open_cabinet()
        self.d.read_note()
        self.d.get_boot_disk()
        self.d.use("computer")
        self.d.tap(K.K_e)
        self.d.seconds(4.7)
        self.d.tap(K.K_3)
        self.assertEqual(scene.panel.stage, "files")

    def test_the_memory_fragment_and_the_trial_are_recorded_once_with_the_game_in_the_chain(self):
        self.enter()
        self.d.play_through()
        self.assertEqual(self.manager.memory_fragments, 1)
        self.assertEqual(self.manager.secret_trials, 1)
        self.assertEqual(self.manager.state["stats"]["secret_trials"], ["trial_01"])
        self.assertEqual(self.manager.secret_items, 1)
        self.assertEqual(self.events.count("secret_trial_done"), 1)

    def test_an_old_profile_without_any_of_the_new_notes_loads_and_works(self):
        p = PlayerProfile(profile_id="old", display_name="OLD", tickets=50, tokens=5)
        p.set_story({"opening_done": True, "completed": ["get_your_bearings"], "flags": {"vending_secret": True},
                     "stats": {"secret_trials": ["trial_02"]}})
        m = quests.QuestManager(LocalSession(p))
        self.assertTrue(m.trial_done("trial_02"))
        self.assertFalse(m.state.get("flags", {}).get(G.BREAKOUT_FLAG))
        self.assertEqual(m.memory_fragments, 0)
        m.handle("secret_trial_done", "trial_01")
        self.assertEqual(m.memory_fragments, 1)
        self.assertEqual(m.secret_trials, 2)
        m.handle("secret_trial_done", "trial_01")
        self.assertEqual(m.secret_trials, 2)


# ------------------------------------------------------------------ 19. one player, and everything else stays as it was
class SinglePlayerTests(TrialCase):
    def test_one_player_the_solo_keys_and_no_second_player_anywhere(self):
        scene = self.enter()
        self.assertEqual(len(self.game.session.players), 1)
        self.assertIs(scene.controls, SOLO_CONTROLS)
        x = scene.avatar.x
        for k in (K.K_o, K.K_RCTRL, K.K_SLASH, K.K_RSHIFT, K.K_l, K.K_k):
            self.d.frames(1, [key_down(k)])
            self.d.frames(10)
            self.d.frames(1, [key_up(k)])
        self.assertEqual(scene.avatar.x, x)

    def test_the_trial_sources_know_nothing_of_a_second_player_or_of_kevin(self):
        text = ""
        for name in ("golden_age.py", "golden_age_art.py", "golden_age_ui.py", "golden_age_scene.py", "golden_age_testing.py",
                     "golden_age_content.py", "happy_breakout.py"):
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                text += f.read().lower()
        for banned in ("kevin", "player 2", "player2", "p2 ", "two-player", "two player", "joinprompt", "join prompt"):
            self.assertNotIn(banned, text, banned)

    def test_the_hub_rooms_are_as_they_were_after_a_visit(self):
        self.enter()
        self.d.play_through()
        self.d.finish_card()
        self.d.tap(K.K_ESCAPE)
        self.d.frames(90)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertFalse(any(isinstance(s, GS.GoldenAgeScene) for s in self.game.scenes.stack))
        self.assertIs(self.room.player.profile, self.profile)
        self.assertEqual(len(self.game.session.players), 1)


# ------------------------------------------------------------------ audio
class AudioTests(unittest.TestCase):
    NEW_SFX = ("circuit_click", "circuit_connect", "power_on", "phone_blip", "morse_dot", "morse_dash", "drawer_open", "page_turn",
               "disk_insert", "crt_boot", "trial_complete",
               "breakout_paddle", "breakout_brick", "breakout_wall", "breakout_lose", "breakout_clear")

    def test_every_new_effect_is_registered_generated_and_on_disk(self):
        for name in self.NEW_SFX:
            self.assertIn(name, am.SFX_FILES)
            self.assertIn(name, audio_synth.SFX)
            self.assertIn(name, am.PRIORITY)
            path = os.path.join(HERE, "assets", "sfx", f"{name}.wav")
            self.assertTrue(os.path.isfile(path), path)
        self.assertEqual(am.MUSIC_FILES["golden_age"], "golden_age")
        self.assertTrue(os.path.isfile(os.path.join(HERE, "assets", "music", "golden_age.wav")))
        self.assertIn("golden_age", audio_synth.MUSIC)

    def test_every_sound_the_trial_asks_for_exists(self):
        names = set()
        for fn in ("golden_age_scene.py", "golden_age_ui.py"):
            with open(os.path.join(HERE, fn), encoding="utf-8") as f:
                names |= set(re.findall(r'play\("([a-z_]+)"\)', f.read()))
        names |= {"breakout_" + n for n in ("paddle", "wall", "lose")}                  # (built from the event names in the computer's screen)
        known = set(am.SFX_FILES) | set(am.AudioManager.EFFECTS)
        self.assertTrue(names)
        self.assertLessEqual(names, known)

    def test_the_music_is_quiet_in_the_dark_and_warmer_with_the_lights_on(self):
        self.assertLess(GS.MUSIC_DARK, GS.MUSIC_LIT)


class SoundTimingTests(TrialCase):
    def test_each_event_plays_its_sound_once(self):
        scene = self.enter()
        self.d.use("drawer")
        self.d.tap(K.K_ESCAPE)
        self.assertEqual([n for _, n in self.d.sounds].count("drawer_open"), 1)
        self.d.use("drawer")
        self.d.tap(K.K_ESCAPE)
        self.assertEqual([n for _, n in self.d.sounds].count("drawer_open"), 1)       # opening it again is silent
        self.d.use("drawer")
        self.d.tap(K.K_e)
        self.assertEqual([n for _, n in self.d.sounds].count("page_turn"), 1)          # one page turned, one sound
        self.d.tap(K.K_e)                                                              # (the last page: no turn)
        self.assertEqual([n for _, n in self.d.sounds].count("page_turn"), 1)

    def test_the_finish_chime_plays_once_with_the_card(self):
        self.enter()
        self.d.play_through()
        names = [n for _, n in self.d.sounds]
        self.assertEqual(names.count("trial_complete"), 1)
        self.assertEqual(names.count("disk_insert"), 1)
        self.assertEqual(names.count("crt_boot"), 1)


if __name__ == "__main__":
    unittest.main()
