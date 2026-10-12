"""Tests for the NEON VEND-O-MATIC: purchases, tickets, inventory, novelty items, P1/P2 ownership,
saving, and the hidden input sequence (see secret_input.py; it is deliberately not in the UI).

Run headless from this folder:   python -m unittest test_vending -v
"""
import os
import random
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from controls import P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS  # noqa: E402
from game import Game  # noqa: E402
from item_registry import CONSUMABLE, ITEM_REGISTRY, NOVELTY_STACK  # noqa: E402
from local_session import LocalSession  # noqa: E402
from novelty import MYSTERY_MESSAGES, NOVELTY_EFFECTS, is_usable, use_item  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from room_testing import goto_room  # noqa: E402
from secret_input import SEQUENCE, SecretSequenceListener  # noqa: E402
from vending_machine import VendingMachine  # noqa: E402
from vending_shop import VEND_ENTRIES, VendingService  # noqa: E402
from vending_ui import GLITCH_TIME, SECRET_DUCK, SECRET_FLAG, VendingScene  # noqa: E402

DT = 1 / 60
K = pygame
CLASSIC = [K.K_UP, K.K_UP, K.K_DOWN, K.K_DOWN, K.K_LEFT, K.K_RIGHT, K.K_LEFT, K.K_RIGHT, K.K_b, K.K_a]
PRICES = {"suspicious_soda": 5, "invisible_sandwich": 8, "pocket_rainbow": 12, "rubber_duck": 15,
          "questionable_battery": 20, "mystery_can": 25}


def down(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def up(k):
    return pygame.event.Event(pygame.KEYUP, key=k, mod=0)


def press(listener, keys):
    """Tap each key (down, up); True if any tap completed the sequence."""
    done = False
    for k in keys:
        done = listener.feed(down(k)) or done
        listener.feed(up(k))
    return done


class CatalogueTests(unittest.TestCase):
    def test_stock_and_prices(self):
        self.assertEqual({e.item_id: e.cost for e in VEND_ENTRIES}, PRICES)
        self.assertEqual([e.item_id for e in VEND_ENTRIES], list(PRICES))

    def test_goods_are_stackable_consumables_with_a_use_effect(self):
        for e in VEND_ENTRIES:
            d = ITEM_REGISTRY.get(e.item_id)
            self.assertEqual(d.category, CONSUMABLE)
            self.assertEqual(d.limit, NOVELTY_STACK)
            self.assertTrue(is_usable(e.item_id))
            self.assertIn(e.item_id, NOVELTY_EFFECTS)

    def test_player_facing_text_never_mentions_the_sequence(self):
        import vending_ui
        for text in (vending_ui.TITLE, *(e.name for e in VEND_ENTRIES),
                     *(ITEM_REGISTRY.get(e.item_id).description for e in VEND_ENTRIES)):
            self.assertNotIn("KONAMI", text.upper())
            self.assertNotIn("UP UP", text.upper())


class PurchaseTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(profile_id="a", tickets=100)
        self.shop = VendingService(self.p)

    def test_purchase_deducts_tickets_and_adds_one_item(self):
        r = self.shop.purchase("rubber_duck")
        self.assertTrue(r.success)
        self.assertEqual(self.p.tickets, 85)
        self.assertEqual(self.p.inventory.get_quantity("rubber_duck"), 1)

    def test_every_item_costs_exactly_its_price(self):
        for item_id, cost in PRICES.items():
            before = self.p.tickets
            self.p.add_tickets(cost)
            self.assertTrue(self.shop.purchase(item_id).success)
            self.assertEqual(self.p.tickets, before + 0)

    def test_quantities_stack(self):
        for _ in range(3):
            self.shop.purchase("suspicious_soda")
        self.assertEqual(self.p.inventory.get_quantity("suspicious_soda"), 3)
        self.assertEqual(self.p.tickets, 85)

    def test_not_enough_tickets_changes_nothing_and_never_goes_negative(self):
        self.p.spend_tickets(95)
        r = self.shop.purchase("mystery_can")
        self.assertFalse(r.success)
        self.assertEqual(r.code, "need_tickets")
        self.assertEqual(self.p.tickets, 5)
        self.assertEqual(self.p.inventory.get_quantity("mystery_can"), 0)

    def test_exact_balance_buys_and_leaves_zero(self):
        self.p.spend_tickets(95)
        self.assertTrue(self.shop.purchase("suspicious_soda").success)
        self.assertEqual(self.p.tickets, 0)
        self.assertFalse(self.shop.purchase("suspicious_soda").success)
        self.assertEqual(self.p.tickets, 0)

    def test_a_full_stack_refuses_without_charging(self):
        self.p.add_tickets(1000)
        for _ in range(NOVELTY_STACK):
            self.assertTrue(self.shop.purchase("suspicious_soda").success)
        before = self.p.tickets
        r = self.shop.purchase("suspicious_soda")
        self.assertEqual((r.success, r.code), (False, "stack_full"))
        self.assertEqual(self.p.tickets, before)
        self.assertEqual(self.p.inventory.get_quantity("suspicious_soda"), NOVELTY_STACK)

    def test_unknown_items_are_refused(self):
        self.assertEqual(self.shop.purchase("neon_cap").code, "unknown")      # a Prize Counter item
        self.assertEqual(self.p.tickets, 100)


class UseTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(profile_id="a", tickets=50, tokens=7)

    def test_using_consumes_exactly_one(self):
        self.p.inventory.add_item("rubber_duck", 3)
        r = use_item(self.p, "rubber_duck")
        self.assertTrue(r.success)
        self.assertEqual((r.effect, r.sound), ("squeak", "squeak"))
        self.assertEqual(self.p.inventory.get_quantity("rubber_duck"), 2)

    def test_using_the_last_one_removes_it(self):
        self.p.inventory.add_item("pocket_rainbow")
        use_item(self.p, "pocket_rainbow")
        self.assertFalse(self.p.inventory.has_item("pocket_rainbow"))
        r = use_item(self.p, "pocket_rainbow")
        self.assertEqual((r.success, r.code), (False, "none_owned"))

    def test_other_items_are_not_usable_and_stay_put(self):
        self.p.inventory.add_item("free_play_coupon")
        r = use_item(self.p, "free_play_coupon")
        self.assertEqual(r.code, "not_usable")
        self.assertEqual(self.p.inventory.get_quantity("free_play_coupon"), 1)

    def test_each_item_has_its_own_effect(self):
        kinds = set()
        for item_id in PRICES:
            self.p.inventory.add_item(item_id)
            kinds.add(use_item(self.p, item_id).effect)
        self.assertEqual(kinds, {"burp", "munch", "rainbow", "squeak", "flicker", "mystery"})

    def test_mystery_can_picks_a_harmless_joke(self):
        self.p.inventory.add_item("mystery_can", 3)
        seen = {use_item(self.p, "mystery_can", rng=random.Random(s)).message for s in range(3)}
        self.assertTrue(seen <= set(MYSTERY_MESSAGES))

    def test_use_never_touches_wallet_scores_or_economy(self):
        self.p.record_score("neon_drop", 120)
        earned = self.p.lifetime_tickets_earned
        for item_id in PRICES:
            self.p.inventory.add_item(item_id)
            use_item(self.p, item_id)
        self.assertEqual((self.p.tickets, self.p.tokens, self.p.high_score("neon_drop")), (50, 7, 120))
        self.assertEqual(self.p.lifetime_tickets_earned, earned)


class SaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "p.json")

    def roundtrip(self, profile):
        store = ProfileStore(self.path)
        store.save(profile)
        return ProfileStore(self.path).load()

    def test_purchases_and_discovery_survive_a_restart(self):
        p = PlayerProfile(profile_id="a", tickets=40)
        VendingService(p).purchase("pocket_rainbow")
        VendingService(p).purchase("pocket_rainbow")
        self.assertTrue(p.discover_secret(SECRET_FLAG))
        q = self.roundtrip(p)
        self.assertEqual(q.tickets, 16)
        self.assertEqual(q.inventory.get_quantity("pocket_rainbow"), 2)
        self.assertTrue(q.has_secret(SECRET_FLAG))
        self.assertEqual(q.secrets, {SECRET_FLAG: True})

    def test_the_save_format_is_additive(self):
        p = PlayerProfile(profile_id="a")
        self.assertNotIn("secrets", p.to_dict())                          # an old-style save looks unchanged
        old = PlayerProfile.from_dict({k: v for k, v in p.to_dict().items()})
        self.assertEqual(old.secrets, {})
        p.discover_secret(SECRET_FLAG)
        self.assertEqual(p.to_dict()["secrets"], {SECRET_FLAG: True})

    def test_bad_secret_data_is_ignored(self):
        for bad in ("yes", ["a"], {"x": "true", "y": 1, 5: True, "ok": True}):
            q = PlayerProfile.from_dict({"secrets": bad})
            self.assertTrue(set(q.secrets) <= {"ok"})

    def test_discovering_twice_changes_nothing_and_rewards_nothing(self):
        p = PlayerProfile(profile_id="a", tickets=9, tokens=3)
        earned = p.lifetime_tickets_earned
        self.assertTrue(p.discover_secret(SECRET_FLAG))
        snapshot = p.to_dict()
        self.assertFalse(p.discover_secret(SECRET_FLAG))
        self.assertEqual(p.to_dict(), snapshot)
        self.assertEqual((p.tickets, p.tokens), (9, 3))
        self.assertEqual(p.lifetime_tickets_earned, earned)

    def test_unrelated_progress_is_not_overwritten(self):
        p = PlayerProfile(profile_id="a", tickets=9)
        p.inventory.add_item("cat_sticker")
        p.record_score("neon_drop", 50)
        before = {k: v for k, v in p.to_dict().items() if k != "secrets"}
        p.discover_secret(SECRET_FLAG)
        self.assertEqual({k: v for k, v in p.to_dict().items() if k != "secrets"}, before)


class ListenerTests(unittest.TestCase):
    def test_the_classic_order_completes_with_arrows_and_b_a(self):
        self.assertTrue(press(SecretSequenceListener(SOLO_CONTROLS), CLASSIC))

    def test_solo_uses_the_arrow_keys_and_wasd_never_counts(self):
        wasd = [K.K_w, K.K_w, K.K_s, K.K_s, K.K_a, K.K_d, K.K_a, K.K_d, K.K_b, K.K_a]
        self.assertFalse(press(SecretSequenceListener(SOLO_CONTROLS), wasd))
        lis = SecretSequenceListener(SOLO_CONTROLS)
        press(lis, CLASSIC[:4])
        press(lis, [K.K_a])                                    # the A key is the A button, not LEFT
        self.assertEqual(lis.progress, 0)

    def test_every_key_has_exactly_one_meaning(self):
        for scheme in (SOLO_CONTROLS, P1_CONTROLS, P2_CONTROLS):
            lis = SecretSequenceListener(scheme)
            mapped = [lis.token_for(k) for k in (*lis.directions, lis.b_key, lis.a_key)]
            self.assertEqual(sorted(mapped), sorted(set(SEQUENCE)) + [])        # UP DOWN LEFT RIGHT B A, once each
            self.assertEqual(len(mapped), 6)

    def test_p1_uses_wasd_with_z_and_x(self):
        keys = [K.K_w, K.K_w, K.K_s, K.K_s, K.K_a, K.K_d, K.K_a, K.K_d, K.K_z, K.K_x]
        self.assertTrue(press(SecretSequenceListener(P1_CONTROLS), keys))
        self.assertFalse(press(SecretSequenceListener(P1_CONTROLS), keys[:8] + [K.K_b, K.K_a]))   # A is LEFT for P1

    def test_modifier_keys_do_not_break_a_run_but_other_keys_do(self):
        lis = SecretSequenceListener(SOLO_CONTROLS)
        press(lis, CLASSIC[:5] + [K.K_LSHIFT])
        self.assertEqual(lis.progress, 5)
        press(lis, [K.K_SPACE])
        self.assertEqual(lis.progress, 0)

    def test_p2_uses_its_own_arrows_and_its_own_b_a(self):
        keys = CLASSIC[:8] + [K.K_COMMA, K.K_PERIOD]
        self.assertTrue(press(SecretSequenceListener(P2_CONTROLS), keys))
        self.assertFalse(press(SecretSequenceListener(P2_CONTROLS), CLASSIC))        # B / A are not P2's keys

    def test_p1_cannot_use_p2s_keys_and_vice_versa(self):
        self.assertFalse(press(SecretSequenceListener(P1_CONTROLS), CLASSIC))
        self.assertFalse(press(SecretSequenceListener(P2_CONTROLS), [K.K_w, K.K_w, K.K_s, K.K_s]))

    def test_wrong_input_resets_and_detection_keeps_working(self):
        lis = SecretSequenceListener(SOLO_CONTROLS)
        self.assertFalse(press(lis, CLASSIC[:5] + [K.K_x]))
        self.assertEqual(lis.progress, 0)
        self.assertFalse(press(lis, CLASSIC[:9]))                          # one short
        self.assertFalse(press(lis, [K.K_b]))
        self.assertTrue(press(lis, CLASSIC))                               # still armed

    def test_a_mistake_that_starts_the_code_counts_as_its_first_step(self):
        lis = SecretSequenceListener(SOLO_CONTROLS)
        self.assertTrue(press(lis, [K.K_UP] + CLASSIC))                    # UP UP UP DOWN DOWN ...

    def test_it_can_fire_again_after_completing(self):
        lis = SecretSequenceListener(SOLO_CONTROLS)
        self.assertTrue(press(lis, CLASSIC))
        self.assertEqual(lis.progress, 0)
        self.assertTrue(press(lis, CLASSIC))

    def test_held_keys_and_repeats_do_not_advance(self):
        lis = SecretSequenceListener(SOLO_CONTROLS)
        self.assertFalse(lis.feed(down(K.K_UP)))
        for _ in range(5):                                                  # held: only KEYDOWN repeats
            lis.feed(down(K.K_UP))
        self.assertEqual(lis.progress, 1)
        rep = pygame.event.Event(pygame.KEYDOWN, key=K.K_DOWN, mod=0, unicode="", repeat=1)
        lis.feed(up(K.K_UP))
        lis.feed(rep)
        self.assertEqual(lis.progress, 1)                                  # a flagged repeat is ignored too

    def test_holding_the_last_key_never_completes_twice(self):
        lis = SecretSequenceListener(SOLO_CONTROLS)
        self.assertTrue(press(lis, CLASSIC[:9]) is False)
        self.assertTrue(lis.feed(down(K.K_a)))
        self.assertFalse(lis.feed(down(K.K_a)))

    def test_losing_focus_forgets_held_keys(self):
        lis = SecretSequenceListener(SOLO_CONTROLS)
        lis.feed(down(K.K_UP))
        lis.feed(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        lis.feed(down(K.K_UP))
        self.assertEqual(lis.progress, 2)

    def test_reset_clears_progress(self):
        lis = SecretSequenceListener(SOLO_CONTROLS)
        press(lis, CLASSIC[:6])
        lis.reset()
        self.assertEqual(lis.progress, 0)

    def test_sequence_constant_is_the_documented_one(self):
        self.assertEqual(SEQUENCE, ("UP", "UP", "DOWN", "DOWN", "LEFT", "RIGHT", "LEFT", "RIGHT", "B", "A"))


class VendingBase(unittest.TestCase):
    players = 1

    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="va", display_name="Ann", tickets=100),
                         PlayerProfile(profile_id="vb", display_name="Bo", tickets=100)][:self.players]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        self.dt = DT

    def frames(self, n=30, events=()):
        for i in range(n):
            self.game.step(list(events) if i == 0 else [], self.dt)

    def seconds(self, s):
        self.frames(int(round(s / self.dt)))

    def tap(self, k):
        self.frames(1, [down(k)])
        self.frames(1, [up(k)])

    def open_shop(self, who=0):
        self.room.acting_player = self.room.players[who]
        self.room.open_vending()
        self.room.acting_player = None
        self.seconds(1.5)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, VendingScene)
        return scene

    def close_shop(self):
        self.frames(1, [down(K.K_ESCAPE)])
        self.seconds(1.5)
        self.assertIs(self.game.scenes.current, self.room)


class VendingScreenTests(VendingBase):
    def test_the_machine_is_on_the_arcade_floor_in_its_old_place(self):
        vend = next(p for p in self.room.props if isinstance(p, VendingMachine))
        self.assertIn(vend, self.room.interactables)
        self.assertEqual(vend.pos, (332, 32))
        self.assertEqual((vend.footprint.x, vend.footprint.w, vend.footprint.h), (333, 30, 26))

    def test_walking_up_and_pressing_the_use_key_opens_it_for_free(self):
        vend = next(p for p in self.room.props if isinstance(p, VendingMachine))
        a = self.room.players[0]
        a.x, a.y = vend.zone.centerx, vend.zone.bottom - 2
        self.frames(10)
        self.assertIs(a.nearby, vend)
        self.frames(1, [down(K.K_e)])
        self.seconds(2)
        self.assertIsInstance(self.game.scenes.current, VendingScene)
        self.assertEqual(self.profiles[0].tickets, 100)

    def test_use_key_buys_the_selected_item(self):
        shop = self.open_shop()
        self.tap(K.K_e)
        self.assertEqual(self.profiles[0].tickets, 95)
        self.assertEqual(self.profiles[0].inventory.get_quantity("suspicious_soda"), 1)
        self.assertEqual(shop.index, 0)

    def test_navigation_selects_other_products(self):
        shop = self.open_shop()
        self.tap(K.K_RIGHT)
        self.tap(K.K_DOWN)
        self.assertEqual(shop.index, 4)
        self.tap(K.K_e)
        self.assertEqual(self.profiles[0].inventory.get_quantity("questionable_battery"), 1)
        self.assertEqual(self.profiles[0].tickets, 80)

    def test_mashing_the_buy_key_charges_once_per_vend(self):
        shop = self.open_shop()
        for _ in range(6):
            self.frames(1, [down(K.K_e)])
        self.assertEqual(self.profiles[0].inventory.get_quantity("suspicious_soda"), 1)
        self.assertEqual(self.profiles[0].tickets, 95)
        self.seconds(1.4)
        self.tap(K.K_e)
        self.assertEqual(self.profiles[0].tickets, 90)

    def test_too_few_tickets_shows_feedback_and_charges_nothing(self):
        self.profiles[0].spend_tickets(97)
        shop = self.open_shop()
        self.tap(K.K_e)
        self.assertEqual(self.profiles[0].tickets, 3)
        self.assertEqual(self.profiles[0].inventory.get_quantity("suspicious_soda"), 0)
        self.assertIn("NEED", shop.message)
        self.assertGreater(shop.flash, 0)

    def test_it_draws_every_state_without_error(self):
        shop = self.open_shop()
        self.tap(K.K_e)
        for _ in range(8):
            self.seconds(0.2)
            shop.draw(self.game.canvas)

    def test_normal_text_does_not_advertise_the_secret(self):
        shop = self.open_shop()
        for text in shop.hints:
            self.assertNotIn("KONAMI", text.upper())
        self.assertEqual(shop.listener.progress, 0)


class SecretTests(VendingBase):
    def enter_code(self, keys=CLASSIC):
        for k in keys:
            self.tap(k)

    def test_the_sequence_opens_the_secret_and_saves_the_flag_for_that_player(self):
        shop = self.open_shop()
        self.enter_code()
        self.assertIsNotNone(shop.secret)
        self.assertTrue(self.profiles[0].has_secret(SECRET_FLAG))

    def test_no_tickets_or_items_are_spent_during_code_entry(self):
        shop = self.open_shop()
        p = self.profiles[0]
        earned = p.lifetime_tickets_earned
        self.enter_code()
        self.assertEqual(p.tickets, 100)
        self.assertEqual(p.inventory.to_dict(), {})
        self.assertEqual(p.lifetime_tickets_earned, earned)

    def test_no_purchase_while_typing_a_wrong_code_either(self):
        self.open_shop()
        self.enter_code(CLASSIC[:7] + [K.K_x, K.K_b, K.K_a])
        self.assertEqual(self.profiles[0].tickets, 100)
        self.assertEqual(self.profiles[0].inventory.to_dict(), {})

    def test_wrong_code_does_not_activate_and_a_later_right_one_does(self):
        shop = self.open_shop()
        self.enter_code(CLASSIC[:9])
        self.assertIsNone(shop.secret)
        self.assertFalse(self.profiles[0].secrets)
        self.enter_code()
        self.assertIsNotNone(shop.secret)

    def test_normal_navigation_still_works_while_the_code_is_typed(self):
        shop = self.open_shop()
        self.tap(K.K_DOWN)
        self.assertEqual(shop.index, 3)
        self.tap(K.K_RIGHT)
        self.assertEqual(shop.index, 4)

    def test_key_repeats_do_not_trigger_it(self):
        shop = self.open_shop()
        for k in CLASSIC:                                                    # never released: every key stays "held"
            self.frames(1, [down(k), down(k)])
        self.assertIsNone(shop.secret)
        self.frames(1, [up(k) for k in CLASSIC])
        self.enter_code(CLASSIC[:3])
        self.assertIsNone(shop.secret)

    def test_it_does_nothing_outside_the_vending_screen(self):
        self.enter_code()                                                    # in the room itself
        self.seconds(1)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertFalse(self.profiles[0].secrets)
        self.assertEqual(self.profiles[0].tickets, 100)

    def test_other_menus_ignore_it_too(self):
        self.frames(1, [down(K.K_i)])
        self.seconds(0.5)
        self.enter_code()
        self.assertFalse(self.profiles[0].secrets)

    def test_only_the_vending_screen_freezes_and_the_game_keeps_running(self):
        shop = self.open_shop()
        self.enter_code()
        index = shop.index
        t0 = self.room.time
        self.tap(K.K_DOWN)                                                    # ignored: the shop UI is frozen
        self.assertEqual(shop.index, index)
        self.tap(K.K_e)
        self.assertEqual(self.profiles[0].tickets, 100)
        self.assertEqual(self.game.scenes.current, shop)
        self.assertGreaterEqual(self.room.time, t0)

    def test_it_activates_exactly_once_per_entry(self):
        shop = self.open_shop()
        self.enter_code()
        first = shop.secret
        self.enter_code()                                                    # typed again on the frozen screen
        self.seconds(0.5)
        self.assertIs(shop.secret, first)
        self.assertTrue(first["new"])
        self.assertEqual(self.profiles[0].secrets, {SECRET_FLAG: True})

    def test_wasd_mid_code_restarts_it_for_solo(self):
        shop = self.open_shop()
        self.enter_code(CLASSIC[:5] + [K.K_w] + CLASSIC[5:])
        self.assertIsNone(shop.secret)
        self.assertEqual(self.profiles[0].tickets, 100)

    def test_the_a_key_navigates_but_never_buys_or_counts_as_left(self):
        shop = self.open_shop()
        self.tap(K.K_a)                                                      # nav LEFT: wraps to the last column
        self.assertEqual(shop.index, 2)
        self.assertEqual(shop.listener.progress, 0)
        self.assertEqual(self.profiles[0].tickets, 100)

    def test_the_music_ducks_for_the_secret_and_returns_afterwards(self):
        shop = self.open_shop()
        self.assertEqual(self.game.audio.duck, 1.0)
        self.enter_code()
        self.frames(2)
        self.assertEqual(shop.music_duck, SECRET_DUCK)
        self.assertEqual(self.game.audio.duck, SECRET_DUCK)
        self.assertAlmostEqual(self.game.audio._music_level(), self.game.audio.bgm_volume * SECRET_DUCK)
        self.close_shop()
        self.assertEqual(self.game.audio.duck, 1.0)
        self.assertAlmostEqual(self.game.audio._music_level(), self.game.audio.bgm_volume)

    def test_the_glitch_then_the_terminal_then_esc_returns_to_the_floor(self):
        shop = self.open_shop()
        self.enter_code()
        self.seconds(GLITCH_TIME / 2)
        shop.draw(self.game.canvas)
        self.assertLess(shop.secret["t"], GLITCH_TIME)
        self.seconds(GLITCH_TIME + 4)
        shop.draw(self.game.canvas)
        self.assertGreater(shop.secret["t"], GLITCH_TIME)
        self.close_shop()

    def test_reopening_the_secret_gives_no_new_reward(self):
        p = self.profiles[0]
        shop = self.open_shop()
        self.enter_code()
        self.assertTrue(shop.secret["new"])
        snapshot = p.to_dict()
        self.close_shop()
        shop = self.open_shop()
        self.enter_code()
        self.assertFalse(shop.secret["new"])
        self.assertEqual(p.to_dict(), snapshot)
        self.close_shop()

    def test_closing_the_shop_resets_detection(self):
        shop = self.open_shop()
        self.enter_code(CLASSIC[:6])
        self.assertGreater(shop.listener.progress, 0)
        self.close_shop()
        self.assertEqual(shop.listener.progress, 0)
        shop = self.open_shop()
        self.enter_code(CLASSIC[6:])
        self.assertIsNone(shop.secret)

    def test_it_works_with_sound_muted_or_unavailable(self):
        for setup in (lambda a: setattr(a, "muted", True), lambda a: setattr(a, "enabled", False)):
            setup(self.game.audio)
            shop = self.open_shop()
            self.enter_code()
            self.assertIsNotNone(shop.secret)
            self.seconds(3)
            shop.draw(self.game.canvas)
            self.close_shop()

    def test_detection_does_not_depend_on_frame_rate(self):
        for dt in (1 / 15, 1 / 240):
            with self.subTest(dt=dt):
                self.setUp()
                self.dt = dt
                shop = self.open_shop()
                self.enter_code()
                self.assertIsNotNone(shop.secret)
                self.game.quit()


class TwoPlayerTests(VendingBase):
    players = 2

    def test_a_purchase_goes_to_the_player_who_opened_the_machine(self):
        self.open_shop(who=1)
        self.tap(K.K_RETURN)                                  # P2's use key
        a, b = self.profiles
        self.assertEqual((a.tickets, b.tickets), (100, 95))
        self.assertEqual(a.inventory.to_dict(), {})
        self.assertEqual(b.inventory.get_quantity("suspicious_soda"), 1)

    def test_the_other_players_keys_do_nothing_in_my_shop(self):
        shop = self.open_shop(who=0)
        self.tap(K.K_RETURN)                                  # P2's key in P1's shop
        self.tap(K.K_DOWN)
        self.assertEqual(shop.index, 0)
        self.assertEqual(self.profiles[0].tickets, 100)
        self.assertEqual(self.profiles[1].tickets, 100)

    def test_the_secret_is_saved_for_the_player_who_typed_it_only(self):
        shop = self.open_shop(who=1)
        for k in CLASSIC[:8] + [K.K_COMMA, K.K_PERIOD]:
            self.tap(k)
        self.assertIsNotNone(shop.secret)
        self.assertEqual(self.game.audio.duck, SECRET_DUCK)
        a, b = self.profiles
        self.assertTrue(b.has_secret(SECRET_FLAG))
        self.assertFalse(a.has_secret(SECRET_FLAG))
        self.assertEqual(a.secrets, {})

    def test_p1_finds_it_with_wasd_z_x_and_p2_gets_nothing(self):
        shop = self.open_shop(who=0)
        for k in (K.K_w, K.K_w, K.K_s, K.K_s, K.K_a, K.K_d, K.K_a, K.K_d, K.K_z, K.K_x):
            self.tap(k)
        self.assertIsNotNone(shop.secret)
        a, b = self.profiles
        self.assertEqual((a.has_secret(SECRET_FLAG), b.has_secret(SECRET_FLAG)), (True, False))
        self.assertEqual((a.tickets, b.tickets), (100, 100))

    def test_p1_typing_the_other_players_keys_finds_nothing(self):
        shop = self.open_shop(who=0)
        for k in CLASSIC:
            self.tap(k)
        self.assertIsNone(shop.secret)
        self.assertFalse(any(p.secrets for p in self.profiles))

    def test_each_player_uses_items_from_their_own_bag(self):
        a, b = self.profiles
        a.inventory.add_item("rubber_duck")
        b.inventory.add_item("rubber_duck", 2)
        self.room.use_novelty("rubber_duck", self.room.players[1])
        self.assertEqual((a.inventory.get_quantity("rubber_duck"), b.inventory.get_quantity("rubber_duck")), (1, 1))
        self.assertEqual(len(self.room.novelty_fx.shows), 1)
        self.assertIs(self.room.novelty_fx.shows[0].player, self.room.players[1])


class BagUseTests(VendingBase):
    def open_bag_on_consumables(self):
        self.frames(1, [down(K.K_i)])
        self.seconds(0.5)
        for _ in range(3):
            self.tap(K.K_TAB)
        return self.room.inventory_ui

    def test_use_from_the_bag_consumes_one_and_plays_the_effect(self):
        p = self.profiles[0]
        p.inventory.add_item("suspicious_soda", 2)
        bag = self.open_bag_on_consumables()
        self.assertTrue(bag.can_use)
        self.tap(K.K_SPACE)
        self.assertEqual(p.inventory.get_quantity("suspicious_soda"), 1)
        self.assertTrue(self.room.novelty_fx.active)
        self.assertIsNone(self.room.inventory_ui)
        self.seconds(0.5)
        self.room.draw(self.game.canvas)
        self.seconds(3)
        self.assertFalse(self.room.novelty_fx.active)
        self.assertEqual(p.tickets, 100)

    def test_every_effect_draws(self):
        p = self.profiles[0]
        for item_id in PRICES:
            p.inventory.add_item(item_id)
            self.room.use_novelty(item_id)
            for _ in range(12):
                self.seconds(0.1)
                self.room.draw(self.game.canvas)
            self.room.novelty_fx.clear()

    def test_the_space_key_does_nothing_on_items_that_cannot_be_used(self):
        p = self.profiles[0]
        p.inventory.add_item("free_play_coupon")
        self.frames(1, [down(K.K_i)])
        self.seconds(0.5)
        self.tap(K.K_TAB)
        self.tap(K.K_TAB)                                     # ARCADE tab
        self.assertFalse(self.room.inventory_ui.can_use)
        self.tap(K.K_SPACE)
        self.assertEqual(p.inventory.get_quantity("free_play_coupon"), 1)
        self.assertFalse(self.room.novelty_fx.active)


if __name__ == "__main__":
    unittest.main()
