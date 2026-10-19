"""Tests for the BROKEN CAT-CADE and MOCHI'S STAFF PANEL: the cabinet's place on the Arcade Floor, the fake
maintenance screen and its password, the panel's exact and de-duplicated grants, saving, one-player and
two-player ownership, ALL CATS DANCE, and that none of it touches the NEON VEND-O-MATIC's secret.

Run headless from this folder:   python -m unittest test_staff_panel -v
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from arcade_layout import ARCADE_SLOTS  # noqa: E402
from broken_cabinet import BrokenCatCade, SLOT  # noqa: E402
from cat import CatState  # noqa: E402
from display import DisplayManager, DisplaySettings, screen_to_window  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from machine import IdleCabinet  # noqa: E402
from player_profile import STAFF_BALANCE_CAP, PlayerProfile, ProfileStore  # noqa: E402
from room_testing import goto_room  # noqa: E402
from secret_input import SEQUENCE  # noqa: E402
from settings import MACHINES, VIEW_H, VIEW_W  # noqa: E402
from shopkeeper import CLUE_EVERY, CLUE_SAY, Shopkeeper  # noqa: E402
from staff_cheat import (GRANT_AMOUNTS, HINT_AFTER, MAX_INPUT, PASSWORD, WRONG_LINES, PasswordEntry,  # noqa: E402
                         StaffService)
from staff_ui import (ACTION_LOCK, DUCK, PANEL_PHASE, PASSWORD_PHASE, ROWS, MaintenanceScene)  # noqa: E402
from vending_ui import SECRET_FLAG, VendingScene  # noqa: E402

DT = 1 / 60
K = pygame
TOKEN, TICKET = PlayerProfile.TOKEN, PlayerProfile.TICKET


def down(k, ch=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=ch)


def up(k):
    return pygame.event.Event(pygame.KEYUP, key=k, mod=0)


def letter_key(ch):
    return getattr(pygame, f"K_{ch.lower()}")   # (also K_0 .. K_9)


class StaffBase(unittest.TestCase):
    players = 1

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.profiles = [PlayerProfile(profile_id="sa", display_name="Ann", tokens=20, tickets=30),
                         PlayerProfile(profile_id="sb", display_name="Bo", tokens=20, tickets=30)][:self.players]
        self.game = Game(session=LocalSession(self.profiles), audio_prefs=os.path.join(self.dir, "audio.json"))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")

    # ------------------------------------------------------------ driving
    def frames(self, n=30, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], DT)

    def seconds(self, s):
        self.frames(int(round(s / DT)))

    def tap(self, k, ch=""):
        self.frames(1, [down(k, ch)])
        self.frames(1, [up(k)])

    def type_text(self, text):
        for ch in text:
            self.tap(letter_key(ch), ch)

    def open_scene(self, who=0):
        self.room.acting_player = self.room.players[who]
        self.room.open_maintenance()
        self.room.acting_player = None
        self.seconds(1.2)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, MaintenanceScene)
        return scene

    def unlock(self, who=0, submit=None):
        """Open the screen and enter the password. `submit`: the key that submits (default: the owner's ENTER)."""
        scene = self.open_scene(who)
        self.type_text(PASSWORD)
        self.tap(submit or (K.K_TAB if self.players == 2 and who == 0 else K.K_RETURN))
        self.assertEqual(scene.phase, PANEL_PHASE)
        self.seconds(0.6)
        return scene

    def select(self, scene, row, col):
        scene.sel = [row, col]

    def press_button(self, scene, row, col, key=K.K_e):
        self.select(scene, row, col)
        self.tap(key)
        self.seconds(ACTION_LOCK + 0.1)

    def leave(self):
        self.tap(K.K_ESCAPE)
        self.seconds(1.2)
        self.assertIs(self.game.scenes.current, self.room)


# =============================================================================================== the cabinet
class CabinetTests(StaffBase):
    def cabinet(self):
        return next(p for p in self.room.props if isinstance(p, BrokenCatCade))

    def test_it_takes_over_a_spare_soon_slot_and_nothing_that_was_finished(self):
        cab = self.cabinet()
        self.assertEqual(cab.pos, (ARCADE_SLOTS[SLOT][0] - 1, ARCADE_SLOTS[SLOT][1] - 1))
        claimed = {d["slot"] for d in MACHINES if "slot" in d}
        self.assertNotIn(SLOT, claimed)                                      # no completed minigame lived there
        self.assertEqual([m.id for m in self.room.machines], [d["id"] for d in MACHINES])
        self.assertEqual(sum(isinstance(p, IdleCabinet) for p in self.room.props), 1)   # one SOON bay is left

    def test_same_footprint_as_the_dark_cabinet_it_replaces_so_paths_are_unchanged(self):
        self.assertEqual(self.cabinet().footprint, IdleCabinet(ARCADE_SLOTS[SLOT]).footprint)
        self.assertIn(self.cabinet().footprint, self.room.solids)

    def test_it_is_solid_listed_and_reachable_with_the_cats_at_home(self):
        cab = self.cabinet()
        self.assertIn(cab, self.room.interactables)
        blocks = list(self.room.solids) + [c.feet_at(*c.spots[0]) for c in self.room.cats]
        p = self.room.players[0]
        fw, fh = p.FEET_W, p.FEET_H
        free = lambda x, y: pygame.Rect(x - fw // 2, y - fh, fw, fh).collidelist(blocks) == -1    # noqa: E731
        start = (int(p.x), int(p.y))
        seen, todo = {start}, [start]
        while todo:
            x, y = todo.pop()
            for nx, ny in ((x + 4, y), (x - 4, y), (x, y + 4), (x, y - 4)):
                if (nx, ny) not in seen and free(nx, ny):
                    seen.add((nx, ny))
                    todo.append((nx, ny))
        self.assertTrue(any(cab.zone.collidepoint(q) for q in seen))
        for exit_ in self.room.exits:
            self.assertTrue(any(exit_.zone.collidepoint(q) for q in seen))

    def test_it_overlaps_no_other_solid_and_leaves_a_corridor_beside_it(self):
        cab = self.cabinet()
        others = [r for r in self.room.solids if r is not cab.footprint]
        self.assertEqual(cab.footprint.collidelist(others), -1)

    def test_walking_up_and_pressing_the_use_key_opens_the_maintenance_screen(self):
        cab = self.cabinet()
        a = self.room.players[0]
        a.x, a.y = cab.zone.centerx, cab.zone.bottom - 2
        self.frames(10)
        self.assertIs(a.nearby, cab)
        self.frames(1, [down(K.K_e)])
        self.seconds(2)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, MaintenanceScene)
        self.assertIs(scene.owner, self.game.session.players[0])
        self.assertEqual(scene.phase, PASSWORD_PHASE)

    def test_the_prompt_and_hints_do_not_advertise_the_panel(self):
        text = " ".join([self.cabinet().prompt_label, *self.room.hint_rows[0][0][:1]]).upper()
        scene = self.open_scene()
        text += " " + " ".join(scene.hints).upper()
        for word in ("CHEAT", "STAFF", "MOCHI", "PASSWORD", "5151"):
            self.assertNotIn(word, text)

    def test_it_animates_and_draws_every_phase_without_error(self):
        cab = self.cabinet()
        for _ in range(240):                                                 # covers static bursts, blips, dropouts
            cab.update(0.05)
            cab.draw(self.game.canvas)
        cab.highlight = True
        cab.draw(self.game.canvas)

    def test_static_bursts_come_and_go(self):
        cab = self.cabinet()
        cab.time = 0.1
        self.assertTrue(cab._static_on())
        cab.time = 2.0
        self.assertFalse(cab._static_on())

    def test_the_cabinet_has_discoverable_in_world_clues(self):
        import broken_cabinet
        self.assertIn("5151", broken_cabinet.MESSAGES)                        # the CRT blips the first half
        sprite = self.cabinet().sprite
        self.assertEqual(sprite.get_size(), (38, 64))                         # (outlined 36x62)


# ============================================================================================ the password
class PasswordEntryTests(unittest.TestCase):
    def test_the_password_is_the_six_digits(self):
        self.assertEqual(PASSWORD, "515106")

    def test_the_right_word_is_accepted_in_any_case(self):
        for text in ("515106",):
            entry = PasswordEntry()
            for ch in text:
                self.assertTrue(entry.type(ch))
            self.assertTrue(entry.submit(), text)
        for text in ("MEOWVELOPER", "meowveloper", "MeOwVeLoPeR"):          # letters match without regard to case
            entry = PasswordEntry(password="MEOWVELOPER")
            for ch in text:
                self.assertTrue(entry.type(ch))
            self.assertTrue(entry.submit(), text)

    def test_wrong_words_are_rejected_counted_and_clear_the_box(self):
        entry = PasswordEntry()
        for ch in "5151":
            entry.type(ch)
        self.assertFalse(entry.submit())
        self.assertEqual((entry.text, entry.attempts), ("", 1))
        for ch in "5151067":                                                 # a superset is wrong too
            entry.type(ch)
        self.assertFalse(entry.submit())
        self.assertEqual(entry.attempts, 2)
        self.assertFalse(entry.submit())                                     # empty is wrong too

    def test_backspace_and_clear(self):
        entry = PasswordEntry()
        for ch in "MEOWX":
            entry.type(ch)
        self.assertTrue(entry.backspace())
        self.assertEqual(entry.text, "MEOW")
        self.assertTrue(entry.clear())
        self.assertEqual(entry.text, "")
        self.assertFalse(entry.backspace())
        self.assertFalse(entry.clear())

    def test_the_length_is_limited(self):
        entry = PasswordEntry()
        for i in range(MAX_INPUT + 10):
            entry.type("A")
        self.assertEqual(len(entry.text), MAX_INPUT)
        self.assertFalse(entry.type("B"))
        self.assertGreater(MAX_INPUT, len(PASSWORD))

    def test_only_letters_and_digits_type(self):
        entry = PasswordEntry()
        for ch in ("", " ", "-", "*", "é", "ab", "\n", None):
            self.assertFalse(entry.type(ch), repr(ch))
        self.assertEqual(entry.text, "")
        self.assertIsNone(PasswordEntry.char_for(down(K.K_SPACE, " ")))
        self.assertIsNone(PasswordEntry.char_for(down(K.K_UP)))
        self.assertEqual(PasswordEntry.char_for(down(K.K_m)), "M")           # from the key name
        self.assertEqual(PasswordEntry.char_for(down(K.K_q, "a")), "A")      # from the layout's own character
        self.assertEqual(PasswordEntry.char_for(down(K.K_5)), "5")

    def test_every_wrong_answer_is_a_friendly_joke_and_none_leaks_the_password(self):
        entry = PasswordEntry()
        seen = []
        for _ in range(len(WRONG_LINES) + 1):
            entry.type("X")
            entry.submit()
            seen.append(entry.wrong_line())
        self.assertGreater(len(set(seen)), 3)
        for line in WRONG_LINES:
            self.assertNotIn(PASSWORD, line)

    def test_a_hint_appears_only_after_a_few_failures(self):
        entry = PasswordEntry()
        for _ in range(HINT_AFTER - 1):
            entry.type("X")
            entry.submit()
        self.assertFalse(entry.wants_hint)
        entry.type("X")
        entry.submit()
        self.assertTrue(entry.wants_hint)


class PasswordScreenTests(StaffBase):
    def test_typing_then_enter_unlocks_the_panel_and_the_screen_is_the_fake_terminal(self):
        scene = self.open_scene()
        self.assertTrue(scene.captures_text)
        self.type_text(PASSWORD)
        self.assertEqual(scene.entry.text, PASSWORD)
        self.tap(K.K_RETURN)
        self.assertEqual(scene.phase, PANEL_PHASE)
        self.assertFalse(scene.captures_text)

    def test_a_wrong_password_gives_feedback_clears_the_box_and_grants_nothing(self):
        scene = self.open_scene()
        before = self.profiles[0].to_dict()
        self.type_text("PURR")
        self.tap(K.K_RETURN)
        self.assertEqual(scene.phase, PASSWORD_PHASE)
        self.assertEqual(scene.entry.text, "")
        self.assertEqual(scene.entry.attempts, 1)
        self.assertGreater(scene.shake, 0)
        scene.draw(self.game.canvas)
        self.assertEqual(self.profiles[0].to_dict(), before)

    def test_backspace_and_delete_edit_the_text(self):
        scene = self.open_scene()
        self.type_text("MEOWX")
        self.tap(K.K_BACKSPACE)
        self.assertEqual(scene.entry.text, "MEOW")
        self.tap(K.K_DELETE)
        self.assertEqual(scene.entry.text, "")
        self.tap(K.K_BACKSPACE)                                              # nothing left: harmless
        self.assertEqual(scene.phase, PASSWORD_PHASE)

    def test_the_input_length_is_limited_on_screen(self):
        scene = self.open_scene()
        self.type_text("A" * (MAX_INPUT + 6))
        self.assertEqual(len(scene.entry.text), MAX_INPUT)

    def test_typing_has_no_side_effects_on_the_hub(self):
        """E, I, T, WASD and the arrows are game keys: here they are only letters or nothing."""
        scene = self.open_scene()
        profile, before = self.profiles[0], self.profiles[0].to_dict()
        self.type_text("EITWASD")
        for k in (K.K_UP, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_SPACE, K.K_F5):
            self.tap(k)
        self.assertEqual(scene.entry.text, "EITWASD")
        self.assertEqual(profile.to_dict(), before)
        self.assertIs(self.game.scenes.current, scene)
        self.assertEqual(self.room.players[0].held, [])

    def test_the_m_of_the_password_does_not_mute_the_game(self):
        scene = self.open_scene()
        self.assertFalse(self.game.audio.muted)
        self.type_text("MM")
        self.assertFalse(self.game.audio.muted)
        self.assertEqual(scene.entry.text, "MM")

    def test_m_still_mutes_outside_the_text_box(self):
        self.tap(K.K_m)
        self.assertTrue(self.game.audio.muted)

    def test_a_clue_appears_after_repeated_failures(self):
        scene = self.open_scene()
        for _ in range(HINT_AFTER):
            self.type_text("NOPE")
            self.tap(K.K_RETURN)
        self.assertTrue(scene.entry.wants_hint)
        scene.draw(self.game.canvas)

    def test_esc_leaves_cleanly_and_focus_returns_to_the_room(self):
        scene = self.open_scene()
        self.type_text("MEO")
        self.leave()
        self.assertTrue(scene.closing)
        self.assertIsNone(self.room.modal)
        self.assertEqual(self.room.players[0].held, [])
        self.frames(3, [down(K.K_d)])                                         # the room answers keys again
        self.assertIn(K.K_d, self.room.players[0].held)

    def test_reopening_starts_with_an_empty_locked_screen(self):
        self.open_scene()
        self.type_text("5151")
        self.leave()
        scene = self.open_scene()
        self.assertEqual(scene.entry.text, "")
        self.assertEqual(scene.phase, PASSWORD_PHASE)

    def test_the_room_is_frozen_while_the_screen_is_up(self):
        a = self.room.players[0]
        a.x, a.y = 100.0, 250.0
        cat_positions = [c.position for c in self.room.cats]
        self.open_scene()
        self.type_text("DDDD")
        self.seconds(1.0)
        self.assertEqual((a.x, a.y), (100.0, 250.0))
        self.assertEqual([c.position for c in self.room.cats], cat_positions)


# ================================================================================================ the panel
class GrantTests(StaffBase):
    def test_every_button_adds_exactly_its_amount(self):
        scene = self.unlock()
        profile = self.profiles[0]
        for row, currency in ((0, TOKEN), (1, TICKET)):
            for col, amount in enumerate(GRANT_AMOUNTS):
                before = profile.tokens if currency == TOKEN else profile.tickets
                self.press_button(scene, row, col)
                after = profile.tokens if currency == TOKEN else profile.tickets
                self.assertEqual(after - before, amount, (currency, amount))

    def test_the_balances_are_shown_and_feedback_is_clear(self):
        scene = self.unlock()
        self.press_button(scene, 0, 1)
        self.assertEqual(self.profiles[0].tokens, 120)
        self.assertEqual(scene.banner["text"], "+100 TOKENS")
        self.assertIn("GRANTED +100 TOKENS", scene.message)
        self.assertIn("120", scene.message)
        self.assertEqual(scene.granted, [(TOKEN, 100)])
        scene.draw(self.game.canvas)

    def test_the_use_key_held_down_grants_once(self):
        scene = self.unlock()
        self.select(scene, 0, 0)
        for _ in range(30):                                                   # repeats: KEYDOWN, KEYDOWN, ... no KEYUP
            self.frames(1, [down(K.K_e)])
        self.assertEqual(self.profiles[0].tokens, 30)
        self.frames(1, [up(K.K_e)])
        self.seconds(ACTION_LOCK + 0.1)
        self.tap(K.K_e)
        self.assertEqual(self.profiles[0].tokens, 40)

    def test_a_double_tap_inside_the_lock_grants_once(self):
        scene = self.unlock()
        self.select(scene, 1, 0)
        self.tap(K.K_e)
        self.tap(K.K_e)
        self.tap(K.K_e)
        self.assertEqual(self.profiles[0].tickets, 40)

    def test_the_press_that_submitted_the_password_does_not_also_press_a_button(self):
        scene = self.open_scene()
        self.type_text(PASSWORD)
        self.frames(1, [down(K.K_RETURN)])
        self.frames(1, [down(K.K_RETURN)])                                   # held Enter
        self.assertEqual(scene.phase, PANEL_PHASE)
        self.assertEqual((self.profiles[0].tokens, self.profiles[0].tickets), (20, 30))
        self.frames(1, [up(K.K_RETURN)])
        self.assertEqual((self.profiles[0].tokens, self.profiles[0].tickets), (20, 30))

    def test_losing_window_focus_releases_the_latch(self):
        scene = self.unlock()
        self.select(scene, 0, 0)
        self.frames(1, [down(K.K_e)])
        self.seconds(ACTION_LOCK + 0.1)
        self.frames(1, [down(K.K_e)])
        self.assertEqual(self.profiles[0].tokens, 30)
        self.frames(1, [pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.frames(1, [down(K.K_e)])
        self.assertEqual(self.profiles[0].tokens, 40)

    def test_balances_never_pass_the_cap_and_never_go_negative(self):
        profile = self.profiles[0]
        profile.grant_staff_currency(TOKEN, 1000)
        for _ in range(20):
            profile.grant_staff_currency(TOKEN, 1000)
        self.assertEqual(profile.tokens, STAFF_BALANCE_CAP)
        scene = self.unlock()
        self.press_button(scene, 0, 2)
        self.assertEqual(profile.tokens, STAFF_BALANCE_CAP)
        self.assertIn("FULL", scene.message)
        self.assertIsNone(scene.banner)
        profile.spend_tokens(profile.tokens)
        self.assertEqual(profile.tokens, 0)
        self.assertGreaterEqual(profile.tickets, 0)

    def test_a_grant_that_only_partly_fits_adds_the_rest_and_says_so(self):
        profile = self.profiles[0]
        profile._tickets = STAFF_BALANCE_CAP - 7
        scene = self.unlock()
        self.press_button(scene, 1, 1)
        self.assertEqual(profile.tickets, STAFF_BALANCE_CAP)
        self.assertEqual(scene.banner["text"], "+7 TICKETS")
        self.assertIn("WALLET FULL", scene.message)

    def test_the_service_refuses_anything_that_is_not_a_panel_button(self):
        profile = self.profiles[0]
        service = StaffService(profile)
        before = profile.to_dict()
        for currency, amount in ((TOKEN, 5), (TOKEN, -10), (TOKEN, 0), (TOKEN, True), (TOKEN, 10 ** 12), (TICKET, "100"),
                                 ("gold", 10), (None, 10)):
            self.assertEqual(service.grant(currency, amount).code, "invalid", (currency, amount))
        self.assertEqual(profile.to_dict(), before)
        for bad in (-1, 1.5, True, "10"):
            with self.assertRaises(ValueError):
                profile.grant_staff_currency(TOKEN, bad)
        with self.assertRaises(ValueError):
            profile.grant_staff_currency("gold", 10)

    def test_only_balances_and_the_flag_change_not_stats_history_caps_or_tasks(self):
        profile = self.profiles[0]
        keys = ("lifetime_tickets_earned", "lifetime_tokens_earned", "lifetime_tokens_spent", "total_games_played",
                "chance_games_played", "cats_petted", "high_scores", "daily_tasks", "transaction_history", "neon21",
                "inventory", "secrets", "showcase", "home_decorations", "racing_selection", "daily")
        before = {k: json.dumps(profile.to_dict().get(k), sort_keys=True) for k in keys}
        caps = (profile.neon21_tickets_today(), profile.pusher_tickets_today(), profile.pinball_tickets_today(),
                profile.pinball_tokens_today(), profile.neon21_ticket_room(), profile.pusher_ticket_room(),
                profile.pinball_ticket_room(), profile.pinball_token_room())
        scene = self.unlock()
        for row in (0, 1):
            for col in range(3):
                self.press_button(scene, row, col)
        after = profile.to_dict()
        for k in keys:
            self.assertEqual(json.dumps(after.get(k), sort_keys=True), before[k], k)
        self.assertEqual(caps, (profile.neon21_tickets_today(), profile.pusher_tickets_today(),
                                profile.pinball_tickets_today(), profile.pinball_tokens_today(),
                                profile.neon21_ticket_room(), profile.pusher_ticket_room(),
                                profile.pinball_ticket_room(), profile.pinball_token_room()))
        self.assertEqual((profile.tokens, profile.tickets), (20 + 1110, 30 + 1110))
        self.assertTrue(profile.cheats_used)

    def test_no_daily_task_progress_from_granted_tickets(self):
        profile = self.profiles[0]
        progress = json.dumps(profile.daily_tasks, sort_keys=True, default=str)
        scene = self.unlock()
        self.press_button(scene, 1, 2)
        self.assertEqual(json.dumps(profile.daily_tasks, sort_keys=True, default=str), progress)
        self.assertEqual(profile.claimable_tasks, [])

    def test_grants_give_no_story_progress(self):
        profile = self.profiles[0]
        scene = self.unlock()
        for row in (0, 1):
            self.press_button(scene, row, 2)
        self.assertEqual(profile.secrets, {})
        self.assertFalse(profile.has_secret(SECRET_FLAG))
        self.assertEqual(profile.inventory.to_dict(), PlayerProfile().inventory.to_dict())

    def test_exit_and_esc_close_the_panel_cleanly(self):
        scene = self.unlock()
        self.press_button(scene, 3, 0)
        self.assertTrue(scene.closing)
        self.seconds(1.2)
        self.assertIs(self.game.scenes.current, self.room)
        self.unlock()
        self.leave()
        self.assertIsNone(self.room.modal)

    def test_input_after_closing_is_ignored(self):
        scene = self.unlock()
        self.select(scene, 0, 0)
        self.tap(K.K_ESCAPE)
        scene.handle_event(down(K.K_e))
        scene.on_action("interact")
        self.assertEqual(self.profiles[0].tokens, 20)

    def test_navigation_wraps_and_columns_clamp(self):
        scene = self.unlock()
        self.tap(K.K_LEFT)
        self.assertEqual(scene.sel, [0, 2])
        self.tap(K.K_DOWN)
        self.tap(K.K_DOWN)                                                   # onto ALL CATS DANCE: one column
        self.assertEqual(scene.sel, [2, 0])
        self.tap(K.K_UP)
        self.assertEqual(scene.sel, [1, 0])
        self.tap(K.K_UP)
        self.tap(K.K_UP)
        self.assertEqual(scene.sel[0], len(ROWS) - 1)


class SaveTests(StaffBase):
    def test_a_grant_is_one_atomic_save_with_the_flag(self):
        path = os.path.join(self.dir, "p.json")
        profile = PlayerProfile(profile_id="sv", tokens=1, tickets=2)
        store = ProfileStore(path)
        writes = []
        profile.subscribe_save(lambda: writes.append(json.load(open(path)) if os.path.exists(path) else None))
        store.autosave(profile)
        profile.subscribe_save(lambda: writes.append(json.load(open(path))))      # runs after the store's own save
        self.assertNotIn("cheats_used", profile.to_dict())
        profile.grant_staff_currency(TOKEN, 100)
        self.assertEqual(len(writes), 2)                                      # (our two listeners, one request)
        saved = json.load(open(path))
        self.assertEqual((saved["tokens"], saved["tickets"], saved["cheats_used"]), (101, 2, True))
        self.assertFalse(os.path.exists(path + ".tmp"))
        self.assertEqual(saved["lifetime_tokens_earned"], 0)

    def test_it_survives_a_reload(self):
        path = os.path.join(self.dir, "q.json")
        store = ProfileStore(path)
        profile = store.load()
        store.autosave(profile)
        profile.grant_staff_currency(TICKET, 1000)
        profile.grant_staff_currency(TOKEN, 10)
        again = ProfileStore(path).load()
        self.assertEqual((again.tokens, again.tickets, again.cheats_used),
                         (profile.tokens, profile.tickets, True))

    def test_old_saves_and_junk_flags_load_as_not_used(self):
        self.assertFalse(PlayerProfile.from_dict({"tokens": 5}).cheats_used)
        for junk in (1, "yes", None, [], {}, 0, False):
            self.assertFalse(PlayerProfile.from_dict({"cheats_used": junk}).cheats_used, junk)
        self.assertNotIn("cheats_used", PlayerProfile.from_dict({"tokens": 5}).to_dict())

    def test_the_flag_blocks_nothing(self):
        profile = PlayerProfile.from_dict({"cheats_used": True, "tokens": 3})
        self.assertTrue(profile.cheats_used)
        self.assertTrue(profile.spend_tokens(1))
        self.assertTrue(profile.discover_secret(SECRET_FLAG))                  # story flags work as ever
        self.assertTrue(profile.has_secret(SECRET_FLAG))

    def test_a_full_wallet_writes_nothing_and_sets_no_flag(self):
        profile = PlayerProfile(tokens=STAFF_BALANCE_CAP)
        saves = []
        profile.subscribe_save(lambda: saves.append(1))
        self.assertEqual(profile.grant_staff_currency(TOKEN, 10), 0)
        self.assertEqual(saves, [])
        self.assertFalse(profile.cheats_used)

    def test_the_hud_hears_the_change(self):
        heard = []
        profile = PlayerProfile()
        profile.subscribe(heard.append)
        profile.grant_staff_currency(TICKET, 10)
        self.assertEqual([(c.field, c.delta) for c in heard], [(TICKET, 10)])

    def test_the_panel_save_reaches_the_file_through_the_game(self):
        path = os.path.join(self.dir, "g.json")
        ProfileStore(path).autosave(self.profiles[0])
        scene = self.unlock()
        self.press_button(scene, 0, 2)
        saved = json.load(open(path))
        self.assertEqual((saved["tokens"], saved["cheats_used"]), (1020, True))


# ====================================================================================== P1 / P2 isolation
class SoloIsolationTests(StaffBase):
    def test_solo_enter_and_the_use_key_both_work(self):
        scene = self.unlock(submit=K.K_KP_ENTER)
        self.press_button(scene, 0, 0, key=K.K_RETURN)
        self.assertEqual(self.profiles[0].tokens, 30)
        self.press_button(scene, 0, 0, key=K.K_e)
        self.assertEqual(self.profiles[0].tokens, 40)


class TwoPlayerTests(StaffBase):
    players = 2

    def test_p1_opens_it_and_only_p1_is_paid(self):
        scene = self.unlock(0)
        self.assertIs(scene.owner, self.game.session.players[0])
        self.assertIs(scene.service.profile, self.profiles[0])
        self.press_button(scene, 0, 2)
        self.press_button(scene, 1, 1)
        self.assertEqual((self.profiles[0].tokens, self.profiles[0].tickets), (1020, 130))
        self.assertEqual((self.profiles[1].tokens, self.profiles[1].tickets), (20, 30))
        self.assertFalse(self.profiles[1].cheats_used)
        self.assertTrue(self.profiles[0].cheats_used)

    def test_p2_opens_it_and_only_p2_is_paid(self):
        scene = self.unlock(1, submit=K.K_RETURN)
        self.assertIs(scene.owner, self.game.session.players[1])
        self.press_button(scene, 0, 1, key=K.K_RETURN)
        self.press_button(scene, 1, 0, key=K.K_RCTRL)
        self.assertEqual((self.profiles[1].tokens, self.profiles[1].tickets), (120, 40))
        self.assertEqual((self.profiles[0].tokens, self.profiles[0].tickets), (20, 30))
        self.assertFalse(self.profiles[0].cheats_used)

    def test_the_other_players_keys_cannot_press_buttons_or_move_the_cursor(self):
        scene = self.unlock(0)
        self.select(scene, 0, 0)
        for k in (K.K_RETURN, K.K_RCTRL, K.K_KP_ENTER, K.K_UP, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_o, K.K_SLASH):
            self.tap(k)
            self.seconds(ACTION_LOCK + 0.1)
        self.assertEqual(scene.sel, [0, 0])
        self.assertEqual((self.profiles[0].tokens, self.profiles[1].tokens), (20, 20))
        self.assertEqual((self.profiles[0].tickets, self.profiles[1].tickets), (30, 30))
        self.assertFalse(scene.closing)

    def test_p2_cannot_submit_or_grant_into_p1s_screen_with_enter(self):
        scene = self.open_scene(0)
        self.type_text("PURR")
        self.tap(K.K_RETURN)                                                  # P2's key: not P1's submit
        self.assertEqual(scene.entry.text, "PURR")
        self.assertEqual(scene.entry.attempts, 0)
        self.tap(K.K_TAB)
        self.assertEqual(scene.entry.attempts, 1)

    def test_p1_can_type_the_whole_password_and_game_keys_as_text(self):
        scene = self.open_scene(0)
        self.type_text(PASSWORD)
        self.assertEqual(scene.entry.text, PASSWORD)

    def test_p1_wasd_does_not_walk_p2_or_p1_while_the_screen_is_up(self):
        a, b = self.room.players
        a.x, a.y, b.x, b.y = 100.0, 250.0, 140.0, 250.0
        self.unlock(0)
        self.frames(1, [down(K.K_d), down(K.K_RIGHT)])
        self.seconds(1.0)
        self.assertEqual(((a.x, a.y), (b.x, b.y)), ((100.0, 250.0), (140.0, 250.0)))

    def test_both_players_can_use_it_one_after_the_other_each_for_themselves(self):
        scene = self.unlock(0)
        self.press_button(scene, 0, 0)
        self.leave()
        scene = self.unlock(1, submit=K.K_RETURN)
        self.press_button(scene, 0, 0, key=K.K_RETURN)
        self.assertEqual((self.profiles[0].tokens, self.profiles[1].tokens), (30, 30))

    def test_a_second_screen_cannot_open_on_top_of_the_first(self):
        scene = self.open_scene(0)
        self.room.acting_player = self.room.players[1]
        self.room.open_maintenance()
        self.seconds(1.2)
        self.assertIs(self.game.scenes.current, scene)
        self.assertEqual(self.game.scenes.stack.count(scene), 1)

    def test_the_spectating_player_is_listed_and_the_owner_tag_shows(self):
        scene = self.open_scene(1)
        self.assertEqual([p.number for p in scene.spectators], [1])
        self.assertEqual(scene.owner.tag, "P2 BO")


# ================================================================================ ALL CATS DANCE
class DanceTests(StaffBase):
    def press_dance(self):
        scene = self.unlock()
        self.select(scene, 2, 0)
        self.tap(K.K_e)
        self.seconds(1.2)
        return scene

    def snapshot(self):
        return [(c.position, c.state, c.anchor, c.target, c.timer, c.speed) for c in self.room.cats]

    def test_it_makes_the_cats_here_dance_and_closes_the_panel(self):
        scene = self.press_dance()
        self.assertTrue(scene.dance_started)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertTrue(self.room.cats.dancing)
        self.assertTrue(all(c.dance is not None for c in self.room.cats))

    def test_they_sway_on_the_same_beat_bob_and_show_hearts(self):
        self.press_dance()
        self.seconds(0.2)
        sides = {c.side for c in self.room.cats}
        self.assertEqual(len(sides), 1)                                      # one beat, every cat
        hops = []
        for _ in range(40):
            self.frames(1)
            hops.append(self.room.cats.cats[0]._hop())
            self.room.draw(self.game.canvas)
        self.assertGreater(max(hops), 0)
        self.assertTrue(all(0 <= h <= 3 for h in hops))

    def test_nothing_permanent_changes_position_ai_or_collision(self):
        solids = [r.copy() for r in self.room.solids]
        before = self.snapshot()
        self.press_dance()
        during = self.snapshot()
        self.assertEqual([d[0] for d in during], [b[0] for b in before])    # no cat moved
        self.assertEqual([(d[1], d[2], d[3], d[5]) for d in during], [(b[1], b[2], b[3], b[5]) for b in before])
        self.assertEqual(self.room.solids, solids)
        self.assertIs(self.room.cats.room_solids, self.room.solids)

    def test_it_ends_by_itself_and_the_cats_carry_on(self):
        self.press_dance()
        self.seconds(self.room.cats.DANCE_TIME + 0.5)
        self.assertFalse(self.room.cats.dancing)
        self.assertTrue(all(c.dance is None for c in self.room.cats))
        before = [c.position for c in self.room.cats]
        self.seconds(12)
        self.assertNotEqual([c.position for c in self.room.cats], before)    # ordinary AI is back (some cat walks)

    def test_it_never_runs_longer_than_its_duration(self):
        self.assertLessEqual(self.room.cats.DANCE_TIME, 6.0)
        self.press_dance()
        self.seconds(self.room.cats.DANCE_TIME - 1.5)
        self.assertTrue(self.room.cats.dancing)

    def test_a_dancing_cat_cannot_be_petted_but_can_again_afterwards(self):
        self.press_dance()
        self.assertFalse(any(c.can_pet for c in self.room.cats))
        self.seconds(self.room.cats.DANCE_TIME + 1.0)
        self.assertTrue(all(c.can_pet for c in self.room.cats))

    def test_leaving_the_room_or_a_minigame_cleans_up(self):
        self.press_dance()
        self.room.cats.pause()
        self.assertFalse(self.room.cats.dancing)
        self.assertTrue(all(c.dance is None for c in self.room.cats))
        self.assertFalse(self.room.cats.start_dance())                        # (paused: no dance)
        self.room.cats.resume()
        self.assertTrue(self.room.cats.start_dance())
        goto_room(self.game, "home")
        self.assertFalse(self.room.cats.dancing)

    def test_it_can_be_restarted_and_does_not_stack(self):
        self.press_dance()
        self.seconds(1.0)
        left = self.room.cats.dance_left
        self.assertTrue(self.room.cats.start_dance())
        self.assertGreater(self.room.cats.dance_left, left)
        self.assertLessEqual(self.room.cats.dance_left, self.room.cats.DANCE_TIME)

    def test_other_rooms_cats_and_the_shopkeeper_are_untouched(self):
        plaza = self.game.hub.room("prize_plaza")
        mochi_before = (plaza.mochi.state, plaza.mochi.idle_for, plaza.mochi.events[:])
        self.press_dance()
        self.assertFalse(plaza.cats.dancing)
        self.assertFalse(self.game.hub.room("home").cats.dancing)
        self.assertEqual((plaza.mochi.state, plaza.mochi.idle_for, plaza.mochi.events[:]), mochi_before)

    def test_follow_and_pet_state_do_not_interrupt_or_break_the_dance(self):
        cat = self.room.cats.cats[0]
        cat.set_state(CatState.PET)
        self.press_dance()
        self.seconds(self.room.cats.DANCE_TIME + 1.0)
        self.assertFalse(self.room.cats.dancing)
        self.assertTrue(all(c.dance is None for c in self.room.cats))

    def test_it_is_silent_when_muted_and_audible_when_not(self):
        audio = self.game.audio
        audio.set_muted(True)
        before = dict(audio.sfx_requested)
        self.press_dance()
        self.assertEqual(audio.sfx_requested.get("meow", 0), before.get("meow", 0))
        self.assertTrue(audio.muted)

    def test_it_plays_the_meow_through_the_shared_audio_when_not_muted(self):
        audio = self.game.audio
        before = audio.sfx_requested.get("meow", 0)
        self.press_dance()
        self.assertGreater(audio.sfx_requested.get("meow", 0), before)

    def test_no_cats_means_no_dance_and_the_panel_stays_open(self):
        scene = self.unlock()
        self.room.cats.cats.clear()
        self.select(scene, 2, 0)
        self.tap(K.K_e)
        self.seconds(0.8)
        self.assertIs(self.game.scenes.current, scene)
        self.assertFalse(scene.dance_started)
        self.assertIn("NO CATS", scene.message)

    def test_dancing_does_not_block_doors_stations_or_the_player(self):
        self.press_dance()
        a = self.room.players[0]
        a.x, a.y = 100.0, 250.0
        self.frames(1, [down(K.K_d)])
        self.seconds(0.5)
        self.assertGreater(a.x, 100.0)

    def test_the_dance_does_not_pay_or_grant_anything(self):
        before = self.profiles[0].to_dict()
        self.press_dance()
        self.assertEqual(self.profiles[0].to_dict(), before)


# ================================================================================ the vending secret
class VendingIsolationTests(StaffBase):
    def test_the_konami_sequence_is_unchanged(self):
        self.assertEqual(SEQUENCE, ("UP", "UP", "DOWN", "DOWN", "LEFT", "RIGHT", "LEFT", "RIGHT", "B", "A"))
        self.assertEqual(SECRET_FLAG, "vending_konami_discovered")

    def test_the_cabinet_never_touches_the_secret_listener_or_flags(self):
        import staff_cheat
        import staff_ui
        for module in (staff_cheat, staff_ui):
            source = open(module.__file__, encoding="utf-8").read()
            for name in ("SecretSequenceListener", "discover_secret", "SECRET_FLAG", "vending_ui", "secret_input"):
                self.assertNotIn(name, source, (module.__name__, name))

    def test_the_vending_machine_still_opens_and_its_code_still_works(self):
        self.room.open_vending()
        self.seconds(1.5)
        shop = self.game.scenes.current
        self.assertIsInstance(shop, VendingScene)
        for k in (K.K_UP, K.K_UP, K.K_DOWN, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_LEFT, K.K_RIGHT, K.K_b, K.K_a):
            self.tap(k)
        self.assertIsNotNone(shop.secret)
        self.assertTrue(self.profiles[0].has_secret(SECRET_FLAG))

    def test_the_maintenance_password_is_not_a_vending_code_and_vice_versa(self):
        scene = self.open_scene()
        for k in (K.K_UP, K.K_UP, K.K_DOWN, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_LEFT, K.K_RIGHT, K.K_b, K.K_a):
            self.tap(k)
        self.assertEqual(scene.phase, PASSWORD_PHASE)                         # B and A typed, arrows ignored
        self.assertEqual(scene.entry.text, "BA")
        self.assertFalse(self.profiles[0].has_secret(SECRET_FLAG))
        self.leave()
        self.room.open_vending()
        self.seconds(1.5)
        vend = self.game.scenes.current
        self.type_text(PASSWORD)
        self.assertIsNone(vend.secret)
        self.assertFalse(self.profiles[0].has_secret(SECRET_FLAG))

    def test_the_vending_secret_still_grants_nothing_and_the_panel_flag_is_separate(self):
        profile = self.profiles[0]
        scene = self.unlock()
        self.press_button(scene, 0, 0)
        self.assertTrue(profile.cheats_used)
        self.assertEqual(profile.secrets, {})
        self.leave()
        self.assertTrue(profile.discover_secret(SECRET_FLAG))
        self.assertEqual(profile.secrets, {SECRET_FLAG: True})

    def test_other_machines_prizes_capsules_and_showcase_data_are_untouched(self):
        profile = self.profiles[0]
        keys = ("showcase", "capsule_stamps", "collection_display", "inventory", "coin_pusher", "pinball", "neon21")
        before = {k: json.dumps(profile.to_dict().get(k), sort_keys=True) for k in keys}
        scene = self.unlock()
        for row in (0, 1):
            for col in range(3):
                self.press_button(scene, row, col)
        for k in keys:
            self.assertEqual(json.dumps(profile.to_dict().get(k), sort_keys=True), before[k], k)


class MochiClueTests(unittest.TestCase):
    def test_every_sixth_welcome_is_a_mumble_and_the_rest_are_unchanged(self):
        keeper = Shopkeeper()
        said = []
        for i in range(CLUE_EVERY * 2):
            keeper.notify("approach")
            said.append(keeper.bubble.text)
        self.assertEqual(said.count(CLUE_SAY), 2)
        self.assertEqual(said[CLUE_EVERY - 1], CLUE_SAY)
        self.assertEqual(said[0], "WELCOME!")
        self.assertNotEqual(PASSWORD, CLUE_SAY)
        self.assertNotIn(PASSWORD, CLUE_SAY)                                  # half the answer, never all of it
        keeper.notify("open")
        self.assertEqual(keeper.bubble.text, "HELLO, FRIEND!")


# ================================================================ display scaling and audio lifecycle
class ScalingAndAudioTests(StaffBase):
    SIZES = (("integer", (800, 600)), ("integer", (1280, 720)), ("integer", (1920, 1080)), ("integer", (2560, 1440)),
             ("fit", (1366, 768)), ("fit", (600, 1000)), ("integer", (330, 250)))

    def setUp(self):
        patcher = patch.object(DisplayManager, "desktop_size", lambda self: (7680, 4320))
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()

    def window_pos(self, canvas_pos):
        lay = self.game.display.layout
        return screen_to_window(lay, (canvas_pos[0] * lay.screen_size[0] / VIEW_W,
                                      canvas_pos[1] * lay.screen_size[1] / VIEW_H))

    def test_both_screens_draw_inside_the_canvas_at_every_window_size(self):
        scene = self.open_scene()
        for scaling, size in self.SIZES:
            self.game.display.apply(DisplaySettings("windowed", scaling, size))
            self.frames(2)
            self.game.scenes.draw(self.game.canvas, self.game.screen)
        self.type_text("NOPE")
        self.tap(K.K_RETURN)
        for scaling, size in self.SIZES:
            self.game.display.apply(DisplaySettings("windowed", scaling, size))
            self.frames(2)
            self.game.scenes.draw(self.game.canvas, self.game.screen)
        self.type_text(PASSWORD)
        self.tap(K.K_RETURN)
        self.seconds(0.5)
        self.press_button(scene, 0, 1)
        for scaling, size in self.SIZES:
            self.game.display.apply(DisplaySettings("windowed", scaling, size))
            self.frames(2)
            self.game.scenes.draw(self.game.canvas, self.game.screen)
        self.assertEqual(self.game.canvas.get_size(), (VIEW_W, VIEW_H))

    def test_every_panel_button_is_on_screen_big_enough_and_not_overlapping(self):
        scene = self.unlock()
        scene.draw(self.game.canvas)
        rects = [r for r, _ in scene._hit]
        self.assertEqual(len(rects), 8)
        screen = pygame.Rect(0, 0, VIEW_W, VIEW_H)
        for i, r in enumerate(rects):
            self.assertTrue(screen.contains(r), r)
            self.assertGreaterEqual(r.h, 20)
            self.assertGreaterEqual(r.w, 80)
            for other in rects[i + 1:]:
                self.assertFalse(r.colliderect(other), (r, other))

    def test_a_mouse_click_on_a_button_grants_once_at_every_window_size_and_never_on_the_bars(self):
        scene = self.unlock()
        expected = self.profiles[0].tokens
        for scaling, size in self.SIZES:
            self.game.display.apply(DisplaySettings("windowed", scaling, size))
            self.frames(2)
            scene.draw(self.game.canvas)
            target = next(r for r, _ in scene._hit if r.w == 80)              # the first (+10 TOKENS) button
            pos = self.window_pos(target.center)
            click = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)]
            self.frames(1, click)
            self.frames(1, click)                                            # a second click inside the lock
            expected += 10
            self.assertEqual(self.profiles[0].tokens, expected, (scaling, size))
            lay = self.game.display.layout
            w, h = lay.window
            for bar in ((1, h // 2), (w - 1, h // 2), (w // 2, 0), (w // 2, h - 1)):
                if not lay.rect.collidepoint(bar):
                    self.seconds(ACTION_LOCK + 0.1)
                    self.frames(1, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=bar, button=1)])
            self.assertEqual(self.profiles[0].tokens, expected, (scaling, size, "bars"))
            self.seconds(ACTION_LOCK + 0.1)

    def test_the_music_dips_while_the_screen_is_up_and_comes_back(self):
        self.assertEqual(Game.duck_for(self.game.scenes.current), 1.0)
        scene = self.open_scene()
        self.assertEqual(Game.duck_for(scene), DUCK)
        self.leave()
        self.assertIsNone(scene.music_duck)
        self.assertEqual(Game.duck_for(self.game.scenes.current), 1.0)

    def test_the_room_keeps_its_music_and_the_scene_channel_is_released(self):
        before = Game.music_for(self.game.scenes.stack)
        scene = self.open_scene()
        self.assertEqual(Game.music_for(self.game.scenes.stack), before)
        self.leave()
        self.frames(3)
        self.assertNotIn(id(scene), self.game.audio.scene_ch)
        self.assertEqual(Game.music_for(self.game.scenes.stack), before)

    def test_effects_follow_mute_and_never_raise(self):
        audio = self.game.audio
        audio.set_muted(True)
        scene = self.unlock()
        before = dict(audio.sfx_requested)
        self.press_button(scene, 0, 0)
        self.press_button(scene, 1, 0)
        self.assertEqual(audio.sfx_requested, before)                         # muted: nothing is even requested
        self.assertEqual(self.profiles[0].tokens, 30)                         # ... but the grant itself still works
        audio.set_muted(False)
        self.press_button(scene, 0, 0)
        self.assertGreater(audio.sfx_requested.get("token", 0), before.get("token", 0))


if __name__ == "__main__":
    unittest.main()
