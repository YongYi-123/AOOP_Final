"""Free Play Coupons through the real launch flow: PLAY -> "USE COUPON?" -> game.

Covers one coupon per launch, never a coupon and a token together, ESC / NO /
failure cases, repeated key presses, per-profile coupons, the Lucky Corner
(which never takes coupons) and the shop that sells them.

Run headless from this folder:   python -m unittest test_coupons -v
"""
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from chance_scene import ChanceGameScene  # noqa: E402
from game import Game  # noqa: E402
from item_registry import FREE_PLAY_COUPON  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from prize_shop import ShopService  # noqa: E402
from room_testing import goto_room  # noqa: E402
from scenes import MinigamePlaceholderScene  # noqa: E402
from stations import ChanceStation, Neon21Station  # noqa: E402

DT = 1 / 60


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


class CouponLaunchTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="cp_a", display_name="Ann", tokens=5, tickets=100),
                         PlayerProfile(profile_id="cp_b", display_name="Bo", tokens=5, tickets=100)]
        self.game = Game(session=LocalSession(self.profiles[:1]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        # any machine whose minigame is the placeholder screen: no real game needed
        patcher = mock.patch("room_scene.create_minigame_scene", self.placeholder)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.machine = self.room.machines[0]
        self.room.player.x = float(self.machine.rect.centerx)
        self.room.player.y = float(self.machine.rect.bottom + 12)
        self.frames(5)

    def placeholder(self, game, machine, participants=None):
        scene = MinigamePlaceholderScene(game, machine)
        scene.participants = [game.profile]
        return scene

    @property
    def p(self):
        return self.profiles[0]

    def coupons(self, profile=None):
        return (profile or self.p).inventory.get_quantity(FREE_PLAY_COUPON)

    def frames(self, n=1, key=None):
        events = [] if key is None else [key_event(key)]
        for i in range(n):
            self.game.step(events if i == 0 else [], DT)

    def to_coupon_question(self):
        self.frames(20, pygame.K_e)                         # open the machine
        self.assertEqual(self.room.dialogue.title, self.machine.name)
        self.frames(25, pygame.K_RETURN)                    # PLAY
        self.assertEqual(self.room.dialogue.title, "COUPON")

    def test_yes_spends_exactly_one_coupon_and_no_tokens(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON, 3)
        self.to_coupon_question()
        self.frames(25, pygame.K_RETURN)                    # YES (the first option)
        self.frames(40)
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.assertEqual(self.coupons(), 2)
        self.assertEqual(self.p.tokens, 5)

    def test_no_pays_a_token_and_keeps_the_coupon(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON, 2)
        self.to_coupon_question()
        self.frames(1, pygame.K_s)
        self.frames(25, pygame.K_RETURN)                    # NO
        self.frames(40)
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.assertEqual((self.p.tokens, self.coupons()), (4, 2))

    def test_esc_on_the_coupon_question_launches_nothing_and_charges_nothing(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON)
        self.to_coupon_question()
        self.frames(25, pygame.K_ESCAPE)
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual((self.p.tokens, self.coupons()), (5, 1))
        self.assertIsNone(self.room.active_play)

    def test_cancelling_the_machine_dialog_charges_nothing(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON)
        self.frames(20, pygame.K_e)
        self.frames(25, pygame.K_ESCAPE)
        self.assertEqual((self.p.tokens, self.coupons()), (5, 1))

    def test_mashing_confirm_cannot_use_two_coupons_or_a_coupon_and_a_token(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON, 5)
        self.to_coupon_question()
        self.frames(1, pygame.K_RETURN)
        for _ in range(15):
            self.frames(1, pygame.K_RETURN)
        self.frames(40)
        self.assertEqual(self.coupons(), 4)
        self.assertEqual(self.p.tokens, 5)

    def test_the_coupon_question_ignores_a_mashed_play_key(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON)
        self.frames(20, pygame.K_e)
        self.frames(1, pygame.K_RETURN)                     # PLAY opens COUPON ...
        self.frames(2, pygame.K_RETURN)                     # ... and an immediate extra press is ignored
        self.assertEqual(self.room.dialogue.title, "COUPON")
        self.assertEqual((self.p.tokens, self.coupons()), (5, 1))

    def test_the_coupon_count_is_shown_in_both_dialogs(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON, 3)
        self.frames(20, pygame.K_e)
        self.assertIn(("FREE PLAY COUPONS: 3", mock.ANY), self.room.dialogue.details)
        self.frames(25, pygame.K_RETURN)
        self.assertTrue(any("3" in text for text, _ in self.room.dialogue.details))

    def test_a_coupon_alone_is_enough_to_play(self):
        self.p.spend_tokens(5)
        self.p.inventory.add_item(FREE_PLAY_COUPON)
        self.frames(20, pygame.K_e)
        self.assertNotIn("LOCKED", self.room.dialogue.options[0])
        self.frames(25, pygame.K_RETURN)
        self.frames(25, pygame.K_RETURN)
        self.frames(40)
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.assertEqual((self.p.tokens, self.coupons()), (0, 0))

    def test_without_a_coupon_the_question_never_appears(self):
        self.frames(20, pygame.K_e)
        self.frames(25, pygame.K_RETURN)
        self.frames(40)
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.assertEqual(self.p.tokens, 4)

    def test_a_scene_that_cannot_be_built_charges_nothing(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON)
        with mock.patch("room_scene.create_minigame_scene", side_effect=RuntimeError("no game")):
            self.to_coupon_question()
            with self.assertRaises(RuntimeError):
                self.frames(25, pygame.K_RETURN)            # YES -> building the scene fails ...
        self.assertEqual((self.p.tokens, self.coupons()), (5, 1))       # ... before anything was taken
        self.assertIsNone(self.room.active_play)

    def test_a_game_that_fails_after_launch_returns_the_coupon_once(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON, 2)
        self.to_coupon_question()
        self.frames(25, pygame.K_RETURN)
        self.frames(40)
        scene = self.game.scenes.current
        self.assertEqual(self.coupons(), 1)
        with mock.patch.object(MinigamePlaceholderScene, "failed", new_callable=mock.PropertyMock,
                               return_value=True):
            self.frames(1, pygame.K_ESCAPE)
            self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual((self.p.tokens, self.coupons()), (5, 2))       # coupon back, tokens untouched
        self.room._end_play(ran=False)                                  # a second settle changes nothing
        self.assertEqual(self.coupons(), 2)

    def test_closing_the_window_before_the_game_opens_returns_the_coupon(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON)
        self.to_coupon_question()
        self.frames(1, pygame.K_RETURN)
        self.assertIsNotNone(self.room.active_play)
        self.game.quit()                                    # the wipe never finished
        self.assertEqual((self.p.tokens, self.coupons()), (5, 1))

    def test_a_played_coupon_game_still_pays_its_tickets(self):
        self.p.inventory.add_item(FREE_PLAY_COUPON)
        tickets = self.p.tickets
        self.to_coupon_question()
        self.frames(25, pygame.K_RETURN)
        self.frames(40)
        self.frames(1, pygame.K_ESCAPE)
        self.frames(40)
        self.assertGreater(self.p.tickets, tickets)
        self.assertEqual(self.coupons(), 0)


class CouponProfileIsolationTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="ci_a", display_name="Ann", tokens=5, tickets=100),
                         PlayerProfile(profile_id="ci_b", display_name="Bo", tokens=5, tickets=100)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")
        patcher = mock.patch("room_scene.create_minigame_scene", self.placeholder)
        patcher.start()
        self.addCleanup(patcher.stop)

    def placeholder(self, game, machine, participants=None):
        scene = MinigamePlaceholderScene(game, machine)
        scene.participants = [p.profile for p in game.session]
        return scene

    def test_p2s_coupon_pays_for_p2s_launch_and_p1_keeps_theirs(self):
        self.profiles[1].inventory.add_item(FREE_PLAY_COUPON, 2)
        self.profiles[0].inventory.add_item(FREE_PLAY_COUPON, 1)
        machine = self.room.machines[0]
        p2 = self.room.players[1]
        self.room._start_game(machine, use_coupon=True, player=p2)
        self.assertEqual(self.profiles[1].inventory.get_quantity(FREE_PLAY_COUPON), 1)
        self.assertEqual(self.profiles[0].inventory.get_quantity(FREE_PLAY_COUPON), 1)
        self.assertEqual((self.profiles[0].tokens, self.profiles[1].tokens), (5, 5))

    def test_a_player_with_no_coupon_cannot_borrow_the_other_players(self):
        self.profiles[0].inventory.add_item(FREE_PLAY_COUPON, 1)
        machine = self.room.machines[0]
        p2 = self.room.players[1]
        self.room._start_game(machine, use_coupon=True, player=p2)
        self.assertIsNone(self.room.active_play)
        self.assertEqual(self.profiles[0].inventory.get_quantity(FREE_PLAY_COUPON), 1)
        self.assertEqual(self.profiles[1].tokens, 5)

    def test_a_second_launch_while_one_is_running_takes_nothing(self):
        self.profiles[0].inventory.add_item(FREE_PLAY_COUPON, 3)
        machine = self.room.machines[0]
        self.room._start_game(machine, use_coupon=True, player=self.room.players[0])
        self.room._start_game(machine, use_coupon=True, player=self.room.players[0])
        self.assertEqual(self.profiles[0].inventory.get_quantity(FREE_PLAY_COUPON), 2)


class LuckyCornerNeverTakesCouponsTests(unittest.TestCase):
    def setUp(self):
        self.p = PlayerProfile(profile_id="lc", display_name="Ann", tokens=5, tickets=50)
        self.p.inventory.add_item(FREE_PLAY_COUPON, 2)
        self.game = Game(session=LocalSession([self.p]))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "prize_plaza")

    def test_chance_machines_and_blackjack_have_no_coupon_path(self):
        import chance_game
        import chance_scene
        import neon21
        import neon21_scene
        for module in (chance_game, chance_scene, neon21, neon21_scene):
            with open(module.__file__, encoding="utf-8") as f:
                self.assertNotIn("COUPON", f.read().upper(), module.__name__)

    def test_walking_into_spin_does_not_ask_for_or_spend_a_coupon(self):
        station = next(s for s in self.room.props if isinstance(s, ChanceStation))
        self.room.acting_player = self.room.players[0]
        station.interact(self.room)
        self.room.acting_player = None
        for _ in range(60):
            self.game.step([], DT)
        self.assertIsInstance(self.game.scenes.current, ChanceGameScene)
        self.assertEqual(self.p.inventory.get_quantity(FREE_PLAY_COUPON), 2)
        self.assertIsNone(self.room.dialogue)

    def test_the_blackjack_table_leaves_coupons_alone(self):
        station = next(s for s in self.room.props if isinstance(s, Neon21Station))
        self.room.acting_player = self.room.players[0]
        station.interact(self.room)
        self.room.acting_player = None
        for _ in range(60):
            self.game.step([], DT)
        self.assertEqual(self.p.inventory.get_quantity(FREE_PLAY_COUPON), 2)


class CouponShopTests(unittest.TestCase):
    def test_bought_coupons_work_at_machines(self):
        from machine import ArcadeMachine
        p = PlayerProfile(profile_id="cs", tokens=0, tickets=100)
        ShopService(p).purchase(FREE_PLAY_COUPON)
        game = Game(session=LocalSession([p]))
        self.addCleanup(game.quit)
        machine = goto_room(game, "arcade_floor").machines[0]
        self.assertIsInstance(machine, ArcadeMachine)
        self.assertTrue(machine.can_play(p))
        session = machine.start_play(p, use_coupon=True)
        self.assertTrue(session.coupon)
        self.assertEqual(p.inventory.get_quantity(FREE_PLAY_COUPON), 0)


if __name__ == "__main__":
    unittest.main()
