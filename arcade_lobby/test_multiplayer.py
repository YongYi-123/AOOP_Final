"""Tests for the local two-player session: LocalSession / LocalPlayer, the
shared HubPlayer class, controls, the hub with two players, ownership of
currencies / inventory / daily progress / machines, and the minigame
player-count API.

Run with:  python -m unittest test_multiplayer
"""
import json
import os
import random
import shutil
import tempfile
import unittest
from datetime import date

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from cat import CatState  # noqa: E402
from controls import (P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS, ControlScheme,  # noqa: E402
                      schemes_for)
from daily_tasks import DailyTaskManager  # noqa: E402
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from home_room import HomeRoomScene  # noqa: E402
from hud import CurrencyHUD  # noqa: E402
from inventory_ui import InventoryUI  # noqa: E402
from item_registry import FREE_PLAY_COUPON  # noqa: E402
from local_session import GameEvent, LocalPlayer, LocalSession, MachineInteraction  # noqa: E402
from minigame import MiniGameDefinition, MiniGameResult, MinigameScene, PlayerResult  # noqa: E402
from player import DEFAULT_LOOK, P1_LOOK, P2_LOOK, HubPlayer, Player  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402
from rewards import PlaySession, RewardBundle, RewardService  # noqa: E402
from room_scene import ENTRIES  # noqa: E402
from room_testing import goto_room  # noqa: E402
from scenes import (MINIGAME_DEFINITIONS, MinigamePlaceholderScene,  # noqa: E402
                    create_minigame_scene, minigame_definition)
from settings import (MACHINES, MAX_LOCAL_PLAYERS, PLACEHOLDER_REWARD_TICKETS,  # noqa: E402
                      SIDE_DOOR_H, SIDE_DOOR_Y, VIEW_W)
from stations import ChanceStation, DailyBoard  # noqa: E402

DT = 1 / 60
DAY1 = date(2025, 3, 10)
DOOR_MID_Y = SIDE_DOOR_Y + SIDE_DOOR_H // 2 + 2


def key(k, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=k, mod=0, unicode="")


class TwoPlayerTest(unittest.TestCase):
    P1_TOKENS, P2_TOKENS = 12, 7

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.manager = ProfileManager(os.path.join(self.dir, "saves"), clock=GameClock(lambda: DAY1))
        self.a = self.manager.create_profile("Alice")
        self.b = self.manager.create_profile("Bob")
        self.a.add_tokens(self.P1_TOKENS - 10, "SETUP")
        self.b.spend_tokens(10 - self.P2_TOKENS, "SETUP")
        self.session = LocalSession([self.a, self.b])
        self.game = Game(session=self.session)
        self.p1, self.p2 = self.session.players
        self.home = self.game.scenes.current

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    # ---- helpers
    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def settle(self):
        self.frames(int(0.8 / DT))

    def dismiss_popups(self):
        for _ in range(2):
            self.frames(3, [key(pygame.K_ESCAPE)])
        self.assertIsNone(self.home.popup)

    def quiet_cats(self, room):
        for i, cat in enumerate(room.cats):
            cat.x, cat.y = 120.0 + i * 20, 120.0
            cat.set_state(CatState.SLEEP, 999)

    def arcade(self):
        room = goto_room(self.game, "arcade_floor")
        self.quiet_cats(room)
        return room

    def machine(self, room, machine_id):
        return next(m for m in room.machines if m.id == machine_id)

    def stand_at(self, player, thing, dx=0):
        player.avatar.x = float(thing.rect.centerx + dx)
        player.avatar.y = float(thing.rect.bottom + 12)

    def use(self, player, frames=30):
        """Press that player's interact key."""
        self.frames(frames, [key(player.controls.interact[0])])

    def play_through_wipe(self):
        for _ in range(40):
            self.frames(1)

    def esc_out_of_game(self, room):
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.play_through_wipe()
        self.assertIs(self.game.scenes.current, room)
        self.frames(5)


class SessionTests(unittest.TestCase):
    def profiles(self, n):
        return [PlayerProfile(profile_id=f"id{i}", display_name=f"NAME{i}") for i in range(n)]

    def test_a_session_has_one_or_two_players(self):
        self.assertEqual(MAX_LOCAL_PLAYERS, 2)
        self.assertEqual(LocalSession(self.profiles(1)).player_count, 1)
        self.assertEqual(LocalSession(self.profiles(2)).player_count, 2)
        for n in (0, 3, 4):
            with self.assertRaises(ValueError):
                LocalSession(self.profiles(n))

    def test_the_same_profile_cannot_be_two_players(self):
        p = self.profiles(1)[0]
        with self.assertRaises(ValueError):
            LocalSession([p, p])
        a, b = self.profiles(2)
        b.profile_id = a.profile_id                 # even as two objects with one id
        with self.assertRaises(ValueError):
            LocalSession([a, b])
        bare = PlayerProfile()
        with self.assertRaises(ValueError):
            LocalSession([bare, bare])

    def test_local_players_have_a_profile_a_body_and_controls(self):
        s = LocalSession(self.profiles(2))
        for i, lp in enumerate(s):
            self.assertIsInstance(lp, LocalPlayer)
            self.assertEqual(lp.player_index, i)
            self.assertIs(lp.avatar.profile, lp.profile)
            self.assertIs(lp.avatar.controls, lp.controls)
            self.assertEqual(lp.label, f"P{i + 1}")
        self.assertIsNot(s.players[0].profile, s.players[1].profile)
        self.assertIs(s.primary, s.players[0])
        self.assertEqual(s.profiles, [lp.profile for lp in s])

    def test_the_persistent_profile_is_not_the_physical_player(self):
        s = LocalSession(self.profiles(2))
        lp = s.players[0]
        self.assertNotIsInstance(lp.profile, HubPlayer)
        self.assertFalse(hasattr(lp.profile, "x") or hasattr(lp.profile, "facing"))
        self.assertNotIsInstance(lp.avatar, PlayerProfile)

    def test_both_bodies_are_the_same_class_configured_differently(self):
        s = LocalSession(self.profiles(2))
        a, b = s.avatars
        self.assertIs(type(a), type(b))
        self.assertIs(type(a), HubPlayer)
        self.assertIs(Player, HubPlayer)                 # the old name still works
        self.assertIsNot(a.controls, b.controls)
        self.assertNotEqual(a.look, b.look)
        self.assertEqual((a.label, b.label), ("P1", "P2"))

    def test_a_one_player_session_has_no_labels_and_the_original_look_and_keys(self):
        s = LocalSession(self.profiles(1))
        lp = s.primary
        self.assertEqual(lp.label, "")
        self.assertEqual(lp.avatar.look, DEFAULT_LOOK)
        self.assertIs(lp.controls, SOLO_CONTROLS)
        lp.avatar.show_tag()
        self.assertEqual(lp.avatar.tag_left, 0)

    def test_two_player_looks_differ(self):
        self.assertNotEqual(P1_LOOK.outline, P2_LOOK.outline)
        self.assertNotEqual(P1_LOOK.shirt, P2_LOOK.shirt)
        self.assertNotEqual(P1_LOOK.accent, P2_LOOK.accent)
        sheets = [HubPlayer((0, 0), look=look).image for look in (P1_LOOK, P2_LOOK)]
        self.assertNotEqual(pygame.image.tobytes(sheets[0], "RGBA"), pygame.image.tobytes(sheets[1], "RGBA"))

    def test_events_reach_only_their_owner(self):
        s = LocalSession(self.profiles(2))
        p1, p2 = s.profiles
        self.assertTrue(s.dispatch(GameEvent("cat_petted", s.players[1].player_id)))
        self.assertEqual((p1.cats_petted, p2.cats_petted), (0, 1))
        s.dispatch(GameEvent("machine_visited", s.players[0].player_id, key="retro_racer"))
        self.assertFalse(s.dispatch(GameEvent("cat_petted", "nobody")))
        self.assertFalse(s.dispatch(GameEvent("mystery", s.players[0].player_id)))
        self.assertEqual((p1.cats_petted, p2.cats_petted), (0, 1))

    def test_menu_key_ownership(self):
        s = LocalSession(self.profiles(2))
        p1, p2 = s.players
        self.assertTrue(s.allows(p1, pygame.K_w))
        self.assertFalse(s.allows(p1, pygame.K_UP))          # P2's key
        self.assertFalse(s.allows(p2, pygame.K_s))           # P1's key
        self.assertFalse(s.allows(p2, pygame.K_e))
        self.assertTrue(s.allows(p2, pygame.K_RETURN))
        for shared in (pygame.K_ESCAPE, pygame.K_TAB, pygame.K_SPACE):
            self.assertTrue(s.allows(p1, shared) and s.allows(p2, shared))
        solo = LocalSession(self.profiles(1))
        for k in (pygame.K_UP, pygame.K_w, pygame.K_e, pygame.K_i):
            self.assertTrue(solo.allows(solo.primary, k))


class ControlsTests(unittest.TestCase):
    def test_the_two_player_schemes_do_not_overlap(self):
        self.assertFalse(P1_CONTROLS.keys & P2_CONTROLS.keys)
        self.assertFalse(set(P1_CONTROLS.move) & set(P2_CONTROLS.move))

    def test_bindings(self):
        self.assertEqual(set(P1_CONTROLS.move), {pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d})
        self.assertEqual(set(P2_CONTROLS.move), {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT})
        self.assertEqual(P1_CONTROLS.interact, (pygame.K_e,))
        self.assertEqual(P1_CONTROLS.inventory, (pygame.K_i,))
        self.assertIn(pygame.K_RETURN, P2_CONTROLS.interact)
        self.assertIn(pygame.K_RCTRL, P2_CONTROLS.interact)
        self.assertEqual(P2_CONTROLS.inventory, (pygame.K_o,))

    def test_solo_keeps_the_original_bindings(self):
        self.assertTrue(set(P1_CONTROLS.move) | set(P2_CONTROLS.move) <= set(SOLO_CONTROLS.move))
        self.assertEqual(SOLO_CONTROLS.interact, (pygame.K_e,))
        self.assertEqual(SOLO_CONTROLS.inventory, (pygame.K_i,))

    def test_schemes_per_player_count_and_custom_schemes(self):
        self.assertEqual(schemes_for(1), (SOLO_CONTROLS,))
        self.assertEqual(schemes_for(2), (P1_CONTROLS, P2_CONTROLS))
        with self.assertRaises(ValueError):
            schemes_for(3)
        custom = ControlScheme("X", {pygame.K_j: (-1, 0), pygame.K_l: (1, 0)}, (pygame.K_u,), (pygame.K_p,))
        self.assertTrue(custom.owns(pygame.K_j))
        self.assertEqual(custom.direction([pygame.K_j, pygame.K_l]), (0, 0))
        self.assertEqual(custom.direction([pygame.K_l]), (1, 0))

    def test_direction_is_clamped_per_axis(self):
        self.assertEqual(SOLO_CONTROLS.direction([pygame.K_w, pygame.K_UP]), (0, -1))
        self.assertEqual(P1_CONTROLS.direction([pygame.K_w, pygame.K_d]), (1, -1))


class HubTests(TwoPlayerTest):
    def test_the_hub_is_built_for_the_session(self):
        hub = self.game.hub
        self.assertIs(hub.session, self.session)
        self.assertEqual(hub.avatars, self.session.avatars)
        self.assertIs(hub.player, self.p1.avatar)
        self.assertIs(self.game.profile, self.a)
        self.assertEqual(len(hub.huds), 2)
        self.assertEqual([h.profile for h in hub.huds], [self.a, self.b])
        self.assertIs(hub.hud, hub.huds[0])
        for room_id in ("home", "arcade_floor", "prize_plaza"):
            room = hub.room(room_id)
            self.assertEqual(room.players, self.session.avatars)
            self.assertIs(room.player, self.p1.avatar)
            self.assertIs(room.profile, self.a)

    def test_both_players_appear_in_every_room_side_by_side(self):
        for room_id in ("home", "arcade_floor", "prize_plaza"):
            room = goto_room(self.game, room_id)
            self.frames(3)
            a, b = room.players
            self.assertNotEqual((a.x, a.y), (b.x, b.y), room_id)
            for p in room.players:
                self.assertEqual(p.feet.collidelist(room.solids), -1, (room_id, p.x, p.y))
            drawn = pygame.Surface((400, 300))
            room.draw(drawn)

    def test_both_characters_move_independently(self):
        self.dismiss_popups()
        a, b = self.p1.avatar, self.p2.avatar
        a.x, a.y, b.x, b.y = 120.0, 200.0, 280.0, 200.0
        self.quiet_cats(self.home)
        self.frames(1, [key(pygame.K_d)])
        self.frames(30)
        self.assertGreater(a.x, 125)
        self.assertEqual((b.x, b.y), (280.0, 200.0))
        self.frames(1, [key(pygame.K_d, down=False), key(pygame.K_LEFT)])
        ax, bx = a.x, b.x
        self.frames(30)
        self.assertEqual(a.x, ax)                               # P1 stopped
        self.assertLess(b.x, bx - 5)                            # P2 walks left
        self.assertEqual(b.facing, "left")
        self.frames(1, [key(pygame.K_LEFT, down=False)])

    def test_each_players_keys_only_drive_their_own_body(self):
        self.dismiss_popups()
        a, b = self.p1.avatar, self.p2.avatar
        a.x, a.y, b.x, b.y = 120.0, 200.0, 280.0, 200.0
        self.frames(1, [key(pygame.K_w), key(pygame.K_UP)])
        self.frames(20)
        self.assertLess(a.y, 199)
        self.assertLess(b.y, 199)
        self.assertEqual(a.held, [pygame.K_w])
        self.assertEqual(b.held, [pygame.K_UP])
        self.frames(1, [key(pygame.K_w, down=False)])
        self.assertEqual((a.held, b.held), ([], [pygame.K_UP]))

    def test_players_do_not_block_each_other(self):
        self.dismiss_popups()
        a, b = self.p1.avatar, self.p2.avatar
        a.x, a.y = 200.0, 200.0
        b.x, b.y = 200.0, 200.0                                  # on top of each other
        self.frames(1, [key(pygame.K_d), key(pygame.K_LEFT)])
        self.frames(30)
        self.assertGreater(a.x, 205)
        self.assertLess(b.x, 195)
        a.x, b.x = 150.0, 156.0                                  # walking straight through
        self.frames(1, [key(pygame.K_d, down=False), key(pygame.K_LEFT, down=False), key(pygame.K_d)])
        self.frames(20)
        self.assertGreater(a.x, 160)

    def test_the_p1_p2_tag_shows_briefly_and_one_player_has_none(self):
        self.assertGreater(self.p1.avatar.tag_left, 0)
        self.assertGreater(self.p2.avatar.tag_left, 0)
        self.frames(int(4 / DT))
        self.assertEqual(self.p1.avatar.tag_left, 0)
        surf = pygame.Surface((400, 300))
        self.p1.avatar.show_tag()
        self.p1.avatar.draw_tag(surf)

    def test_the_huds_show_each_players_own_wallet(self):
        h1, h2 = self.game.hub.huds
        self.assertEqual((h1.tag, h2.tag), ("P1 ALICE", "P2 BOB"))
        h1._rebuild()
        h2._rebuild()
        self.assertEqual(h1._key[:2], (self.P1_TOKENS, 0))
        self.assertEqual(h2._key[:2], (self.P2_TOKENS, 0))
        self.assertNotEqual(h1.rect.x, h2.rect.x)
        self.assertFalse(h1.rect.colliderect(h2.rect))
        self.b.add_tickets(31)
        self.frames(2)
        self.assertEqual(h2._key[:2], (self.P2_TOKENS, 31))
        self.assertEqual(h1._key[:2], (self.P1_TOKENS, 0))
        self.assertEqual(len(h2.floaters), 1)
        self.assertEqual(len(h1.floaters), 0)

    def test_the_one_player_hud_is_unchanged(self):
        hud = CurrencyHUD(PlayerProfile())
        self.assertIsNone(hud.tag)
        self.assertEqual(hud.slot, 0)


class OwnershipTests(TwoPlayerTest):
    def test_p1_playing_spends_p1_tokens_only(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(self.p1, racer)
        self.stand_at(self.p2, self.machine(room, "retro_racer"), dx=200)
        self.frames(5)
        self.assertIs(self.p1.avatar.nearby, racer)
        self.use(self.p1)
        self.assertIsNotNone(room.dialogue)
        self.assertIs(room.modal_owner, self.p1.avatar)
        self.assertIs(room.interaction.initiating_player, self.p1)
        self.frames(1, [key(pygame.K_e)])                        # PLAY
        self.play_through_wipe()
        self.assertEqual(self.a.tokens, self.P1_TOKENS - 1)
        self.assertEqual(self.b.tokens, self.P2_TOKENS)
        self.esc_out_of_game(room)
        self.assertEqual((self.a.tickets, self.b.tickets), (PLACEHOLDER_REWARD_TICKETS, 0))
        self.assertEqual((self.a.total_games_played, self.b.total_games_played), (1, 0))

    def test_p2_playing_spends_p2_tokens_only(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(self.p2, racer)
        self.stand_at(self.p1, racer, dx=-120)
        self.frames(5)
        self.assertIs(self.p2.avatar.nearby, racer)
        self.use(self.p2)
        self.assertIsNotNone(room.dialogue)
        self.assertIs(room.modal_owner, self.p2.avatar)
        self.assertEqual(room.interaction.initiating_player.tag, "P2 BOB")
        self.frames(1, [key(pygame.K_RETURN)])
        self.play_through_wipe()
        self.assertEqual(self.b.tokens, self.P2_TOKENS - 1)
        self.assertEqual(self.a.tokens, self.P1_TOKENS)
        self.esc_out_of_game(room)
        self.assertEqual((self.b.tickets, self.a.tickets), (PLACEHOLDER_REWARD_TICKETS, 0))
        self.assertEqual((self.b.total_games_played, self.a.total_games_played), (1, 0))

    def test_the_machine_remembers_who_started_it(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        for who, other in ((self.p2, self.p1), (self.p1, self.p2)):
            self.stand_at(who, racer)
            self.stand_at(other, racer, dx=-150)
            self.frames(5)
            self.use(who)
            self.assertIsInstance(room.interaction, MachineInteraction)
            self.assertIs(room.interaction.initiating_player, who)
            self.assertIs(room.interaction.profile, who.profile)
            self.assertIs(room.interaction.machine, racer)
            self.frames(1, [key(pygame.K_ESCAPE)])
            self.assertIsNone(room.dialogue)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS))

    def test_a_player_who_cannot_afford_does_not_borrow_from_the_other(self):
        self.b.spend_tokens(self.P2_TOKENS, "SETUP")
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(self.p2, racer)
        self.stand_at(self.p1, racer, dx=-150)
        self.frames(5)
        self.use(self.p2)
        self.frames(1, [key(pygame.K_RETURN)])                   # PLAY [LOCKED]
        self.frames(5)
        self.assertIs(self.game.scenes.current, room)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, 0))
        self.assertTrue(room.notice.visible)

    def test_coupons_belong_to_the_player_who_uses_them(self):
        RewardService.grant_item(self.b, FREE_PLAY_COUPON, 2)
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        # P1 has none: no coupon question
        self.stand_at(self.p1, racer)
        self.stand_at(self.p2, racer, dx=150)
        self.frames(5)
        self.use(self.p1)
        self.frames(1, [key(pygame.K_e)])
        self.play_through_wipe()
        self.assertEqual(self.a.tokens, self.P1_TOKENS - 1)
        self.assertEqual(self.b.inventory.get_quantity(FREE_PLAY_COUPON), 2)
        self.esc_out_of_game(room)
        # P2 has two: the coupon question appears and YES uses P2's coupon, no tokens
        self.stand_at(self.p2, racer)
        self.stand_at(self.p1, racer, dx=-150)
        self.frames(5)
        self.use(self.p2)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(room.dialogue.title, "COUPON")
        self.assertIs(room.modal_owner, self.p2.avatar)
        self.frames(30)
        self.frames(1, [key(pygame.K_RETURN)])                   # YES
        self.play_through_wipe()
        self.assertEqual(self.b.inventory.get_quantity(FREE_PLAY_COUPON), 1)
        self.assertEqual(self.b.tokens, self.P2_TOKENS)
        self.assertEqual(self.a.inventory.get_quantity(FREE_PLAY_COUPON), 0)
        self.assertEqual(self.a.tokens, self.P1_TOKENS - 1)
        self.esc_out_of_game(room)

    def test_a_game_that_never_ran_refunds_the_right_player(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(self.p2, racer)
        self.stand_at(self.p1, racer, dx=-150)
        self.frames(5)
        self.use(self.p2)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertIsNotNone(room.active_play)
        self.assertEqual(self.b.tokens, self.P2_TOKENS - 1)
        self.game.quit()                                         # the window closes before the wipe ends
        self.assertEqual(self.b.tokens, self.P2_TOKENS)
        self.assertEqual(self.a.tokens, self.P1_TOKENS)

    def test_the_prize_counter_and_lucky_corner_use_the_player_who_walked_up(self):
        plaza = goto_room(self.game, "prize_plaza")
        self.quiet_cats(plaza)
        self.b.add_tickets(31)
        counter = next(p for p in plaza.props if p.prompt_label == "PRIZE COUNTER")
        wheel = next(p for p in plaza.props if isinstance(p, ChanceStation))
        self.stand_at(self.p2, counter)
        self.p2.avatar.y = float(counter.zone.bottom - 2)
        self.stand_at(self.p1, wheel)
        self.p1.avatar.y = float(wheel.zone.bottom - 2)
        self.frames(5)
        self.use(self.p2)
        self.assertTrue(plaza.notice.visible)
        self.use(self.p1, frames=30)                             # P1 opens the wheel
        for _ in range(50):
            self.frames(1)
        scene = self.game.scenes.current
        self.assertIsNot(scene, plaza)
        self.assertIs(scene.profile, self.a)
        self.frames(1, [key(pygame.K_RETURN)])                   # P2's key: ignored in P1's game
        self.assertEqual(self.b.tokens, self.P2_TOKENS)
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(self.a.tokens, self.P1_TOKENS - 1)
        self.assertEqual(self.b.tokens, self.P2_TOKENS)


class InventoryTests(TwoPlayerTest):
    def test_each_player_opens_their_own_bag(self):
        self.dismiss_popups()
        RewardService.grant_item(self.a, "cat_sticker")
        RewardService.grant_item(self.b, FREE_PLAY_COUPON, 3)
        self.frames(1, [key(pygame.K_i)])
        self.assertIsInstance(self.home.inventory_ui, InventoryUI)
        self.assertIs(self.home.inventory_ui.inventory, self.a.inventory)
        self.assertEqual(self.home.inventory_ui.owner, "P1 ALICE")
        self.assertIs(self.home.modal_owner, self.p1.avatar)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(3)
        self.assertIsNone(self.home.inventory_ui)
        self.frames(1, [key(pygame.K_o)])
        self.assertIs(self.home.inventory_ui.inventory, self.b.inventory)
        self.assertEqual(self.home.inventory_ui.owner, "P2 BOB")
        self.assertIs(self.home.modal_owner, self.p2.avatar)
        names = [d.id for d, _ in self.home.inventory_ui.entries]
        self.assertEqual(names, [FREE_PLAY_COUPON])
        self.home.inventory_ui.draw(pygame.Surface((400, 300)))

    def test_the_other_player_cannot_open_a_second_window_but_can_keep_walking(self):
        self.dismiss_popups()
        self.quiet_cats(self.home)
        self.p2.avatar.x, self.p2.avatar.y = 280.0, 200.0
        self.frames(1, [key(pygame.K_i)])
        first = self.home.inventory_ui
        self.frames(1, [key(pygame.K_o)])                        # P2 tries to open theirs
        self.assertIs(self.home.inventory_ui, first)             # nothing replaced
        self.assertIsNone(self.home.panel)
        self.assertTrue(self.home.notice.visible)                # a polite "P2 WAIT / P1 IS BUSY"
        x = self.p2.avatar.x
        self.frames(1, [key(pygame.K_LEFT)])
        self.frames(20)
        self.assertLess(self.p2.avatar.x, x - 5)                 # P2 walks on
        self.assertEqual(self.p1.avatar.held, [])

    def test_the_other_players_keys_do_not_drive_a_window(self):
        self.dismiss_popups()
        RewardService.grant_item(self.a, "cat_sticker")
        self.frames(1, [key(pygame.K_i)])
        ui = self.home.inventory_ui
        sel = ui.selected
        for k in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_RETURN):
            self.frames(1, [key(k)])
        self.assertEqual((ui.selected, ui.inspecting), (sel, False))
        self.frames(1, [key(pygame.K_d)])                        # P1's own key does
        self.assertNotEqual(ui.selected, sel)
        self.frames(1, [key(pygame.K_TAB)])                      # shared keys work for the owner
        self.assertEqual(ui.tab, 1)

    def test_the_daily_panel_shows_the_players_own_tasks(self):
        self.dismiss_popups()
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        self.quiet_cats(self.home)
        self.p2.avatar.x, self.p2.avatar.y = board.zone.centerx, board.zone.bottom - 2
        self.p1.avatar.x, self.p1.avatar.y = 100.0, 250.0
        self.frames(5)
        self.use(self.p2)
        self.assertIsNotNone(self.home.panel)
        self.assertIs(self.home.panel.profile, self.b)
        self.assertEqual(self.home.panel.owner, "P2 BOB")
        self.home.panel.draw(pygame.Surface((400, 300)))


class DailyLoginTests(TwoPlayerTest):
    def test_each_profile_gets_its_own_login_and_bonus(self):
        self.assertEqual(self.a.last_login_date, DAY1)
        self.assertEqual(self.b.last_login_date, DAY1)
        self.assertTrue(self.a.daily_status().can_claim)
        self.assertTrue(self.b.daily_status().can_claim)

    def test_popups_come_one_after_the_other_for_the_right_owner(self):
        self.frames(3)
        first = self.home.popup
        self.assertIsNotNone(first)
        self.assertIs(first.player, self.p1.avatar)
        self.assertEqual(first.owner, "P1 ALICE")
        self.assertIs(self.home.modal_owner, self.p1.avatar)
        self.frames(1, [key(pygame.K_RETURN)])                   # P2's key does not claim P1's bonus
        self.assertFalse(first.claimed)
        bonus = first.reward_lines
        self.frames(1, [key(pygame.K_e)])                        # P1 claims
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS + 5, self.P2_TOKENS))
        self.assertFalse(self.a.daily_status().can_claim)
        self.assertTrue(self.b.daily_status().can_claim)
        self.frames(60)                                          # the claim animation ends ...
        second = self.home.popup
        self.assertIsNotNone(second)                             # ... then P2's popup
        self.assertIsNot(second, first)
        self.assertIs(second.player, self.p2.avatar)
        self.assertEqual(second.owner, "P2 BOB")
        self.assertEqual(second.reward_lines, bonus)
        self.assertIs(self.home.modal_owner, self.p2.avatar)
        self.frames(1, [key(pygame.K_e)])                        # P1's key does nothing to P2's popup
        self.assertFalse(second.claimed)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS + 5, self.P2_TOKENS + 5))
        self.frames(60)
        self.assertIsNone(self.home.popup)
        self.frames(1, [key(pygame.K_e), key(pygame.K_RETURN)])  # nothing pays twice
        self.frames(60)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS + 5, self.P2_TOKENS + 5))

    def test_putting_one_bonus_off_does_not_claim_or_skip_the_other(self):
        self.frames(3)
        self.frames(1, [key(pygame.K_ESCAPE)])                   # P1 later
        self.frames(3)
        self.assertIs(self.home.popup.player, self.p2.avatar)    # P2's still comes
        self.frames(1, [key(pygame.K_RETURN)])
        self.frames(60)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS + 5))
        self.assertTrue(self.a.daily_status().can_claim)          # P1's is still waiting
        self.assertIsNone(self.home.popup)
        self.frames(120)
        self.assertIsNone(self.home.popup)                        # and is not nagged again today

    def test_bonus_claims_are_saved_to_the_right_files(self):
        self.frames(3)
        self.frames(1, [key(pygame.K_e)])
        with open(self.manager.profile_path(self.a.profile_id)) as f:
            saved_a = json.load(f)
        with open(self.manager.profile_path(self.b.profile_id)) as f:
            saved_b = json.load(f)
        self.assertEqual(saved_a["tokens"], self.P1_TOKENS + 5)
        self.assertEqual(saved_b["tokens"], self.P2_TOKENS)
        self.assertNotEqual(saved_a["profile_id"], saved_b["profile_id"])

    def test_the_second_players_bonus_can_be_the_only_one(self):
        self.a.claim_daily_reward()                               # P1 already claimed today
        g = Game(session=LocalSession([self.a, self.b]))
        home = g.scenes.current
        self.assertIsInstance(home, HomeRoomScene)
        self.assertIs(home.popup.player, g.session.players[1].avatar)


class DailyTaskTests(TwoPlayerTest):
    def setUp(self):
        super().setUp()
        pet = {"id": "pet_cats", "description": "PET 3 CATS", "event": "cat_petted", "target": 3, "reward": 3}
        earn = {"id": "earn_tickets", "description": "EARN 50 TICKETS", "event": "tickets_earned",
                "target": 50, "reward": 8}
        for profile in (self.a, self.b):
            profile._tasks = DailyTaskManager(pool=(pet, earn), count=2)
            profile._tasks.ensure_current(DAY1, random.Random(1))

    def progress(self, profile):
        return {t.id: t.progress for t in profile.daily_tasks}

    def test_a_cat_event_advances_only_its_owners_task(self):
        self.session.dispatch(GameEvent("cat_petted", self.p2.player_id))
        self.assertEqual(self.progress(self.b)["pet_cats"], 1)
        self.assertEqual(self.progress(self.a)["pet_cats"], 0)

    def test_tickets_advance_only_the_earners_task(self):
        self.a.add_tickets(20)
        self.assertEqual(self.progress(self.a)["earn_tickets"], 20)
        self.assertEqual(self.progress(self.b)["earn_tickets"], 0)

    def test_petting_a_cat_in_the_world_is_owned_by_the_petter(self):
        self.dismiss_popups()
        cat = next(iter(self.home.cats))
        self.quiet_cats(self.home)
        cat.x, cat.y = 300.0, 200.0
        cat.set_state(CatState.IDLE, 999)
        self.p1.avatar.x, self.p1.avatar.y = 60.0, 250.0
        self.p2.avatar.x, self.p2.avatar.y = cat.x - 14, cat.y
        self.frames(3)
        self.assertIs(self.p2.avatar.nearby_cat, cat)
        self.assertIsNone(self.p1.avatar.nearby_cat)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual((self.a.cats_petted, self.b.cats_petted), (0, 1))
        self.assertEqual(self.progress(self.b)["pet_cats"], 1)
        self.assertEqual(self.progress(self.a)["pet_cats"], 0)

    def test_both_pressing_on_the_same_cat_at_once_counts_once(self):
        self.dismiss_popups()
        cat = next(iter(self.home.cats))
        self.quiet_cats(self.home)
        cat.x, cat.y = 300.0, 200.0
        cat.set_state(CatState.IDLE, 999)
        self.p1.avatar.x, self.p1.avatar.y = cat.x - 14, cat.y
        self.p2.avatar.x, self.p2.avatar.y = cat.x + 14, cat.y
        self.frames(3)
        self.assertIs(self.p1.avatar.nearby_cat, cat)
        self.assertIs(self.p2.avatar.nearby_cat, cat)
        self.frames(1, [key(pygame.K_e), key(pygame.K_RETURN)])  # the very same frame
        self.assertEqual(self.a.cats_petted + self.b.cats_petted, 1)
        self.assertEqual(self.progress(self.a)["pet_cats"] + self.progress(self.b)["pet_cats"], 1)
        self.frames(1, [key(pygame.K_e), key(pygame.K_RETURN)])  # still reacting: no second count
        self.assertEqual(self.a.cats_petted + self.b.cats_petted, 1)
        self.frames(60)                                          # the speech bubble plays out safely
        self.home.draw(pygame.Surface((400, 300)))

    def test_machine_visits_are_counted_for_the_visitor(self):
        visit = {"id": "visit_machines", "description": "VISIT 3 DIFFERENT MACHINES",
                 "event": "machine_visited", "distinct": True, "target": 3, "reward": 5}
        for profile in (self.a, self.b):
            profile._tasks = DailyTaskManager(pool=(visit,), count=1)
            profile._tasks.ensure_current(DAY1, random.Random(1))
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(self.p2, racer)
        self.stand_at(self.p1, racer, dx=-150)
        self.frames(5)
        self.use(self.p2)
        self.assertEqual(self.progress(self.b)["visit_machines"], 1)
        self.assertEqual(self.progress(self.a)["visit_machines"], 0)
        self.frames(1, [key(pygame.K_ESCAPE)])


class MiniGameTests(TwoPlayerTest):
    def test_the_definitions(self):
        d = MiniGameDefinition("x", 1, 2)
        self.assertTrue(d.supports(1) and d.supports(2) and d.multiplayer)
        one = MiniGameDefinition("y")
        self.assertEqual((one.min_players, one.max_players), (1, 1))
        self.assertTrue(one.supports(1))
        self.assertFalse(one.supports(2) or one.multiplayer)
        for lo, hi in ((0, 1), (2, 1), (1, 3)):
            with self.assertRaises(ValueError):
                MiniGameDefinition("z", lo, hi)

    def test_every_machine_has_a_definition_and_unknown_games_are_single_player(self):
        for data in MACHINES:
            d = minigame_definition(data.get("game_id", data["id"]))
            self.assertGreaterEqual(d.min_players, 1)
            self.assertLessEqual(d.max_players, MAX_LOCAL_PLAYERS)
        self.assertEqual(minigame_definition("space_blaster").max_players, 2)
        self.assertEqual(minigame_definition("puzzle_drop").max_players, 1)
        self.assertEqual(minigame_definition("who_knows"), MiniGameDefinition("who_knows"))
        self.assertIn("retro_racer", MINIGAME_DEFINITIONS)

    def test_a_scene_knows_its_participants(self):
        room = self.arcade()
        machine = self.machine(room, "space_blaster")
        scene = create_minigame_scene(self.game, machine, [self.a, self.b])
        self.assertEqual(scene.participants, [self.a, self.b])
        solo = create_minigame_scene(self.game, machine)
        self.assertEqual(solo.participants, [self.a])

    def test_results_are_one_per_player_and_never_combined(self):
        room = self.arcade()
        scene = create_minigame_scene(self.game, self.machine(room, "space_blaster"), [self.a, self.b])
        result = scene.get_result()
        self.assertIsInstance(result, MiniGameResult)
        self.assertEqual([r.profile_id for r in result.player_results], [self.a.profile_id, self.b.profile_id])
        for r in result.player_results:
            self.assertIsInstance(r, PlayerResult)
            self.assertIsInstance(r.reward, RewardBundle)
            self.assertEqual(r.reward.tickets, PLACEHOLDER_REWARD_TICKETS)
        self.assertIs(result.for_profile(self.b.profile_id), result.player_results[1])
        self.assertIsNone(result.for_profile("nobody"))

    def test_settling_a_player_result_pays_that_profile_once(self):
        session = PlaySession(self.b, "space_blaster", 1)
        pr = PlayerResult(self.b.profile_id, 500, RewardBundle(tickets=9))
        self.assertIs(session.settle_result(pr), pr)
        self.assertEqual((self.b.tickets, self.b.high_score("space_blaster"), self.b.total_games_played), (9, 500, 1))
        self.assertIsNone(session.settle_result(pr))             # once only
        self.assertFalse(session.refund())
        self.assertEqual((self.a.tickets, self.a.total_games_played), (0, 0))

    def test_a_two_player_machine_asks_how_many_play(self):
        room = self.arcade()
        blaster = self.machine(room, "space_blaster")
        self.stand_at(self.p1, blaster)
        self.stand_at(self.p2, blaster, dx=-150)
        self.frames(5)
        self.use(self.p1)
        self.frames(1, [key(pygame.K_e)])                        # PLAY
        self.assertEqual(room.dialogue.title, "PLAYERS")
        self.assertEqual(room.dialogue.options[0], "1 PLAYER")
        self.assertEqual(room.dialogue.options[1], "2 PLAYERS")
        self.assertIs(room.modal_owner, self.p1.avatar)
        self.frames(1, [key(pygame.K_ESCAPE)])                   # cancel: nothing charged
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS))
        self.assertIsNone(room.active_play)

    def test_one_player_choice_only_charges_the_starter(self):
        room = self.arcade()
        blaster = self.machine(room, "space_blaster")
        self.stand_at(self.p1, blaster)
        self.stand_at(self.p2, blaster, dx=-150)
        self.frames(5)
        self.use(self.p1)
        self.frames(1, [key(pygame.K_e)])
        self.frames(1, [key(pygame.K_e)])                        # 1 PLAYER
        self.play_through_wipe()
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS - 1, self.P2_TOKENS))
        self.assertEqual(len(room.active_plays), 1)
        self.esc_out_of_game(room)
        self.assertEqual((self.a.tickets, self.b.tickets), (PLACEHOLDER_REWARD_TICKETS, 0))

    def test_two_players_each_pay_and_each_are_rewarded_separately(self):
        room = self.arcade()
        blaster = self.machine(room, "space_blaster")
        self.stand_at(self.p2, blaster)
        self.stand_at(self.p1, blaster, dx=-150)
        self.frames(5)
        self.use(self.p2)                                        # P2 starts it this time
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(room.dialogue.title, "PLAYERS")
        self.frames(1, [key(pygame.K_DOWN)])
        self.frames(1, [key(pygame.K_RETURN)])                   # 2 PLAYERS
        self.play_through_wipe()
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS - 1, self.P2_TOKENS - 1))
        scene = self.game.scenes.current
        self.assertEqual(scene.participants, [self.b, self.a])    # the starter first
        self.assertIs(room.interaction.initiating_player, self.p2)
        self.assertEqual([p.profile for p, _ in room.active_plays], [self.b, self.a])
        self.esc_out_of_game(room)
        self.assertEqual((self.a.tickets, self.b.tickets), (PLACEHOLDER_REWARD_TICKETS,) * 2)
        self.assertEqual((self.a.total_games_played, self.b.total_games_played), (1, 1))
        self.assertEqual(self.a.lifetime_tickets_earned, PLACEHOLDER_REWARD_TICKETS)   # not doubled
        self.assertEqual(self.b.lifetime_tickets_earned, PLACEHOLDER_REWARD_TICKETS)
        room._end_play(ran=True)                                  # nothing more to settle
        self.assertEqual((self.a.tickets, self.b.tickets), (PLACEHOLDER_REWARD_TICKETS,) * 2)
        self.assertEqual(room.active_plays, [])

    def test_the_second_player_must_afford_to_join(self):
        self.b.spend_tokens(self.P2_TOKENS, "SETUP")
        room = self.arcade()
        blaster = self.machine(room, "space_blaster")
        self.stand_at(self.p1, blaster)
        self.stand_at(self.p2, blaster, dx=-150)
        self.frames(5)
        self.use(self.p1)
        self.frames(1, [key(pygame.K_e)])
        self.assertIn("NEEDS", room.dialogue.options[1])
        self.frames(1, [key(pygame.K_s)])
        self.frames(1, [key(pygame.K_e)])                        # the locked 2 PLAYERS choice
        self.assertIsNone(room.active_play)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, 0))
        self.assertTrue(room.notice.visible)

    def test_a_one_player_game_is_played_by_the_starter_while_the_other_watches(self):
        room = self.arcade()
        puzzle = self.machine(room, "puzzle_drop")
        self.stand_at(self.p1, puzzle)
        self.stand_at(self.p2, puzzle, dx=-150)
        self.frames(5)
        self.use(self.p1)
        self.frames(1, [key(pygame.K_e)])
        self.assertIsNone(room.dialogue)                         # no PLAYERS question for a 1-player game
        self.play_through_wipe()
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        pos = (self.p2.avatar.x, self.p2.avatar.y)
        self.frames(1, [key(pygame.K_LEFT)])
        self.frames(30)
        self.assertEqual((self.p2.avatar.x, self.p2.avatar.y), pos)   # P2 does not roam during the game
        self.frames(1, [key(pygame.K_LEFT, down=False)])
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS - 1, self.P2_TOKENS))
        self.esc_out_of_game(room)
        self.assertEqual((self.a.tickets, self.b.tickets), (PLACEHOLDER_REWARD_TICKETS, 0))
        self.assertEqual(len(room.players), 2)
        self.assertIs(self.game.scenes.current, room)


class RoomChangeTests(TwoPlayerTest):
    def setUp(self):
        super().setUp()
        self.dismiss_popups()

    def at_door(self, player, side="left"):
        player.avatar.x = 6.0 if side == "left" else VIEW_W - 6.0
        player.avatar.y = float(DOOR_MID_Y)

    def near_door(self, player, side="left"):
        player.avatar.x = 40.0 if side == "left" else VIEW_W - 40.0
        player.avatar.y = float(DOOR_MID_Y)

    def test_one_player_alone_at_the_exit_waits_for_the_other(self):
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.at_door(self.p1)
        self.p2.avatar.x, self.p2.avatar.y = 300.0, 150.0
        self.frames(30)
        self.assertIs(self.game.scenes.current, self.home)
        self.assertEqual(self.home.waiting_text, "WAITING FOR PLAYER 2")
        self.assertFalse(self.home.leaving)
        self.home.draw(pygame.Surface((400, 300)))               # the label draws

    def test_player_two_waits_for_player_one_too(self):
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.at_door(self.p2, "right")
        self.p1.avatar.x, self.p1.avatar.y = 100.0, 150.0
        self.frames(30)
        self.assertIs(self.game.scenes.current, self.home)
        self.assertEqual(self.home.waiting_text, "WAITING FOR PLAYER 1")

    def test_the_room_changes_once_both_are_at_the_same_exit(self):
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.at_door(self.p1)
        self.p2.avatar.x, self.p2.avatar.y = 300.0, 150.0
        self.frames(20)
        self.assertIs(self.game.scenes.current, self.home)
        self.near_door(self.p2)                                  # P2 arrives next to the door
        self.frames(5)
        self.settle()
        arcade = self.game.scenes.current
        self.assertEqual(arcade.room_id, "arcade_floor")
        self.assertEqual(arcade.players, self.session.avatars)   # both made it
        self.assertIsNone(arcade.waiting_text)

    def test_the_players_are_on_opposite_sides_of_two_different_exits(self):
        """Different doors never combine: one at each exit just waits."""
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.at_door(self.p1, "left")
        self.at_door(self.p2, "right")
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.home)
        self.assertIsNotNone(self.home.waiting_text)

    def test_both_survive_a_trip_through_all_three_rooms(self):
        route = (("left", "arcade_floor"), ("right", "home"), ("right", "prize_plaza"), ("left", "home"))
        for side, target in route:
            room = self.game.scenes.current
            self.quiet_cats(room)
            room.arrival_grace = 0
            self.near_door(self.p1, side)
            self.at_door(self.p2, side)
            self.frames(10)
            self.settle()
            room = self.game.scenes.current
            self.assertEqual(room.room_id, target)
            a, b = self.session.avatars
            self.assertEqual(a.feet.collidelist(room.solids), -1)
            self.assertEqual(b.feet.collidelist(room.solids), -1)
            self.assertNotEqual((a.x, a.y), (b.x, b.y))
            self.assertGreater(a.tag_left, 0)
            if target == "home" and room.popup:
                self.frames(3, [key(pygame.K_ESCAPE)] * 2)
        self.assertEqual(len(self.game.hub.built_rooms), 3)

    def test_arrival_keeps_each_player_apart_and_facing_in(self):
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.near_door(self.p1)
        self.at_door(self.p2)
        self.frames(10)
        self.settle()
        arcade = self.game.scenes.current
        a, b = arcade.players
        self.assertEqual((a.facing, b.facing), ("left", "left"))
        self.assertGreater(a.x, VIEW_W / 2)
        self.assertNotEqual(a.y, b.y)
        entry_x, entry_y = ENTRIES["right"][0]
        self.assertAlmostEqual((a.y + b.y) / 2, entry_y, delta=2)

    def test_a_player_standing_in_a_door_cannot_walk_off_the_screen(self):
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.at_door(self.p1)
        self.p2.avatar.x, self.p2.avatar.y = 300.0, 150.0
        self.frames(1, [key(pygame.K_a)])
        self.frames(60)
        self.assertGreater(self.p1.avatar.x, 0)
        self.assertIs(self.game.scenes.current, self.home)


class HomeOwnershipTests(TwoPlayerTest):
    def test_home_shows_player_ones_decorations(self):
        self.a.set_home_decoration("rug", "rug_lounge")
        self.assertIs(self.home.profile, self.a)
        self.assertIs(self.home.decorations.profile, self.a)
        self.b.set_home_decoration("rug", "rug_other")
        self.assertEqual(self.a.home_decorations, {"rug": "rug_lounge"})
        self.assertEqual(self.b.home_decorations, {"rug": "rug_other"})


class SavingTests(TwoPlayerTest):
    def test_each_players_changes_land_in_their_own_file(self):
        self.a.add_tickets(11)
        self.b.add_tickets(22)
        RewardService.grant_item(self.a, "cat_sticker")
        with open(self.manager.profile_path(self.a.profile_id)) as f:
            sa = json.load(f)
        with open(self.manager.profile_path(self.b.profile_id)) as f:
            sb = json.load(f)
        self.assertEqual((sa["tickets"], sb["tickets"]), (11, 22))
        self.assertEqual(sa["inventory"], {"cat_sticker": 1})
        self.assertEqual(sb["inventory"], {})
        self.assertEqual((sa["display_name"], sb["display_name"]), ("Alice", "Bob"))

    def test_a_whole_two_player_session_survives_a_restart(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(self.p2, racer)
        self.stand_at(self.p1, racer, dx=-150)
        self.frames(5)
        self.use(self.p2)
        self.frames(1, [key(pygame.K_RETURN)])
        self.play_through_wipe()
        self.esc_out_of_game(room)
        again = ProfileManager(os.path.join(self.dir, "saves"), clock=GameClock(lambda: DAY1))
        ra, rb = again.load_profile(self.a.profile_id), again.load_profile(self.b.profile_id)
        self.assertEqual((ra.tokens, ra.tickets), (self.P1_TOKENS, 0))
        self.assertEqual((rb.tokens, rb.tickets), (self.P2_TOKENS - 1, PLACEHOLDER_REWARD_TICKETS))


class OnePlayerRegressionTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_one_player_keeps_every_key_the_old_game_had(self):
        g = Game(save_path=os.path.join(self.dir, "s.json"), clock=GameClock(lambda: DAY1))
        home = g.scenes.current
        self.assertEqual(len(home.players), 1)
        self.assertFalse(home.two_player)
        self.assertIsNone(home.hud.tag)
        self.assertEqual(len(g.hub.huds), 1)
        for _ in range(3):
            g.step([key(pygame.K_ESCAPE)], DT)
        p = home.player
        p.x, p.y = 200.0, 200.0
        for k, axis, sign in ((pygame.K_w, "y", -1), (pygame.K_UP, "y", -1), (pygame.K_a, "x", -1),
                              (pygame.K_RIGHT, "x", 1)):
            before = getattr(p, axis)
            g.step([key(k)], DT)
            for _ in range(15):
                g.step([], DT)
            g.step([key(k, down=False)], DT)
            self.assertLess((getattr(p, axis) - before) * sign * -1, 0, k)
            p.x, p.y = 200.0, 200.0
        g.step([key(pygame.K_i)], DT)
        self.assertIsNotNone(home.inventory_ui)
        self.assertIsNone(home.inventory_ui.owner)               # no P1 label when playing alone
        self.assertEqual(home.build_hint_rows(), home.hint_rows)

    def test_one_player_has_no_waiting_or_player_choice(self):
        g = Game(save_path=os.path.join(self.dir, "s.json"), clock=GameClock(lambda: DAY1))
        room = goto_room(g, "arcade_floor")
        self.assertIsNone(room.waiting_text)
        self.assertEqual(g.session.primary.label, "")


if __name__ == "__main__":
    unittest.main()
