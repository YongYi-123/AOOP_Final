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
        self.manager.handle("secret_item_found", quests.SECRET_ITEM_RETRO_RACER)        # the Reverse Gear: the way in needs it
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

    def test_it_can_be_done_before_or_after_trial_02(self):
        self.manager.handle("secret_trial_done", "trial_02")
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
