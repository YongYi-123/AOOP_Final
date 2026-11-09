"""Tests for the single-player hub: LocalSession (exactly one player), the HubPlayer body, controls, the hub with
one player, ownership of currencies / inventory / daily progress / machines, the minigame API, and the
guarantee that nothing of the old two-player game (join prompts, P2 keys, labels, waiting at doors) is left.

Several saved profiles still exist (Alice and Bob below are both SAVED), but only one is ever played: the other
profile must stay exactly as it was.

Run with:  python -m unittest test_single_player
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
import controls  # noqa: E402
from controls import SOLO_CONTROLS, ControlScheme  # noqa: E402
from daily_tasks import DailyTaskManager  # noqa: E402
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from home_room import HomeRoomScene  # noqa: E402
from hud import CurrencyHUD  # noqa: E402
from inventory_ui import InventoryUI  # noqa: E402
from item_registry import FREE_PLAY_COUPON  # noqa: E402
import local_session  # noqa: E402
from local_session import GameEvent, LocalPlayer, LocalSession, MachineInteraction  # noqa: E402
from minigame import MiniGameDefinition, MiniGameResult, PlayerResult  # noqa: E402
from player import DEFAULT_LOOK, HubPlayer, Player  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402
from rewards import PlaySession, RewardBundle, RewardService  # noqa: E402
from room_scene import ENTRIES  # noqa: E402
from room_testing import goto_room, with_placeholder_minigame  # noqa: E402
import scenes  # noqa: E402
from scenes import (MINIGAME_DEFINITIONS, MinigamePlaceholderScene,  # noqa: E402
                    create_minigame_scene, minigame_definition)
import settings  # noqa: E402
from settings import MACHINES, PLACEHOLDER_REWARD_TICKETS, SIDE_DOOR_H, SIDE_DOOR_Y, VIEW_W  # noqa: E402
from stations import ChanceStation, DailyBoard  # noqa: E402
import ui  # noqa: E402

DT = 1 / 60
DAY1 = date(2025, 3, 10)
DOOR_MID_Y = SIDE_DOOR_Y + SIDE_DOOR_H // 2 + 2


def key(k, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=k, mod=0, unicode="")


class SoloTest(unittest.TestCase):
    """Alice is the player (12 tokens). Bob is a second SAVED profile that is never played: whatever happens,
    his file and wallet must stay as they were."""
    TOKENS, OTHER_TOKENS = 12, 7

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.manager = ProfileManager(os.path.join(self.dir, "saves"), clock=GameClock(lambda: DAY1))
        self.a = self.manager.create_profile("Alice")
        self.b = self.manager.create_profile("Bob")
        self.a.add_tokens(self.TOKENS - 10, "SETUP")
        self.b.spend_tokens(10 - self.OTHER_TOKENS, "SETUP")
        self.session = LocalSession(self.a)
        self.game = Game(session=self.session)
        self.player = self.session.primary
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

    def stand_at(self, thing, dx=0):
        self.player.avatar.x = float(thing.rect.centerx + dx)
        self.player.avatar.y = float(thing.rect.bottom + 12)

    def use(self, frames=30):
        self.frames(frames, [key(pygame.K_e)])

    def play_through_wipe(self):
        for _ in range(40):
            self.frames(1)

    def esc_out_of_game(self, room):
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.play_through_wipe()
        self.assertIs(self.game.scenes.current, room)
        self.frames(5)

    def bob_is_untouched(self):
        self.assertEqual((self.b.tokens, self.b.tickets, self.b.total_games_played), (self.OTHER_TOKENS, 0, 0))


class SessionTests(unittest.TestCase):
    def profiles(self, n):
        return [PlayerProfile(profile_id=f"id{i}", display_name=f"NAME{i}") for i in range(n)]

    def test_a_session_has_exactly_one_player(self):
        self.assertEqual(len(LocalSession(self.profiles(1)[0])), 1)
        self.assertEqual(len(LocalSession(self.profiles(1))), 1)           # a one-item list is accepted
        for n in (0, 2, 3):
            with self.assertRaises(ValueError):
                LocalSession(self.profiles(n))

    def test_the_same_profile_cannot_be_two_players(self):
        p = self.profiles(1)[0]
        with self.assertRaises(ValueError):
            LocalSession([p, p])

    def test_the_local_player_has_a_profile_a_body_and_controls(self):
        profile = self.profiles(1)[0]
        s = LocalSession(profile)
        lp = s.primary
        self.assertIsInstance(lp, LocalPlayer)
        self.assertIs(lp.avatar.profile, profile)
        self.assertIs(lp.avatar.controls, lp.controls)
        self.assertIs(lp.controls, SOLO_CONTROLS)
        self.assertEqual(lp.avatar.look, DEFAULT_LOOK)
        self.assertEqual(s.profiles, [profile])
        self.assertEqual(s.avatars, [lp.avatar])
        self.assertEqual(lp.name, "NAME0")
        self.assertEqual(lp.tag, "NAME0")

    def test_the_persistent_profile_is_not_the_physical_player(self):
        lp = LocalSession(self.profiles(1)[0]).primary
        self.assertNotIsInstance(lp.profile, HubPlayer)
        self.assertFalse(hasattr(lp.profile, "x") or hasattr(lp.profile, "facing"))
        self.assertNotIsInstance(lp.avatar, PlayerProfile)
        self.assertIs(Player, HubPlayer)                                    # the old name still works

    def test_the_body_has_no_player_labels_or_tags(self):
        body = LocalSession(self.profiles(1)[0]).primary.avatar
        for gone in ("label", "tag_left", "tag_note", "show_tag", "draw_tag", "number"):
            self.assertFalse(hasattr(body, gone), gone)

    def test_events_reach_only_their_owner_and_unknown_owners_are_ignored(self):
        profile = self.profiles(1)[0]
        s = LocalSession(profile)
        self.assertTrue(s.dispatch(GameEvent("cat_petted", s.primary.player_id)))
        self.assertEqual(profile.cats_petted, 1)
        self.assertFalse(s.dispatch(GameEvent("cat_petted", "nobody")))
        self.assertFalse(s.dispatch(GameEvent("mystery", s.primary.player_id)))
        self.assertEqual(profile.cats_petted, 1)

    def test_listeners_hear_delivered_events_only(self):
        s = LocalSession(self.profiles(1)[0])
        heard = []
        s.add_listener(lambda owner, event: heard.append((owner, event.type)))
        s.dispatch(GameEvent("cat_petted", s.primary.player_id))
        s.dispatch(GameEvent("cat_petted", "nobody"))
        self.assertEqual(heard, [(s.primary, "cat_petted")])

    def test_nothing_of_the_two_player_session_is_left(self):
        s = LocalSession(self.profiles(1)[0])
        for gone in ("player_count", "allows", "MAX_PLAYERS"):
            self.assertFalse(hasattr(s, gone), gone)
        self.assertFalse(hasattr(local_session, "MAX_LOCAL_PLAYERS"))
        self.assertFalse(hasattr(settings, "MAX_LOCAL_PLAYERS"))
        for gone in ("label", "player_index", "number"):
            self.assertFalse(hasattr(s.primary, gone), gone)


class ControlsTests(unittest.TestCase):
    def test_solo_is_the_only_scheme(self):
        for gone in ("P1_CONTROLS", "P2_CONTROLS", "SCHEMES", "schemes_for"):
            self.assertFalse(hasattr(controls, gone), gone)

    def test_solo_bindings(self):
        self.assertEqual(set(SOLO_CONTROLS.move), {pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_UP,
                                                   pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT})
        self.assertEqual(SOLO_CONTROLS.interact, (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER))
        self.assertEqual(SOLO_CONTROLS.inventory, (pygame.K_i,))

    def test_the_old_second_player_keys_mean_nothing(self):
        for k in (pygame.K_RCTRL, pygame.K_o, pygame.K_RSHIFT, pygame.K_KP0, pygame.K_SLASH):
            self.assertFalse(SOLO_CONTROLS.owns(k), pygame.key.name(k))
            self.assertIsNone(SOLO_CONTROLS.action_for(k))

    def test_a_custom_scheme_still_works(self):
        custom = ControlScheme("X", {pygame.K_j: (-1, 0), pygame.K_l: (1, 0)}, (pygame.K_u,), (pygame.K_p,))
        self.assertTrue(custom.owns(pygame.K_j))
        self.assertEqual(custom.direction([pygame.K_j, pygame.K_l]), (0, 0))
        self.assertEqual(custom.direction([pygame.K_l]), (1, 0))

    def test_direction_is_clamped_per_axis(self):
        self.assertEqual(SOLO_CONTROLS.direction([pygame.K_w, pygame.K_UP]), (0, -1))
        self.assertEqual(SOLO_CONTROLS.direction([pygame.K_w, pygame.K_d]), (1, -1))


class HubTests(SoloTest):
    def test_the_hub_is_built_for_the_session(self):
        hub = self.game.hub
        self.assertIs(hub.session, self.session)
        self.assertEqual(hub.avatars, self.session.avatars)
        self.assertEqual(len(hub.avatars), 1)
        self.assertIs(hub.player, self.player.avatar)
        self.assertIs(self.game.profile, self.a)
        self.assertEqual(len(hub.huds), 1)
        self.assertIs(hub.hud, hub.huds[0])
        self.assertIs(hub.hud.profile, self.a)
        for room_id in ("home", "arcade_floor", "prize_plaza"):
            room = hub.room(room_id)
            self.assertEqual(room.players, [self.player.avatar])
            self.assertIs(room.player, self.player.avatar)
            self.assertIs(room.profile, self.a)

    def test_one_player_appears_in_every_room_clear_of_walls(self):
        for room_id in ("home", "arcade_floor", "prize_plaza"):
            room = goto_room(self.game, room_id)
            self.frames(3)
            self.assertEqual(len(room.players), 1)
            p = room.players[0]
            self.assertEqual(p.feet.collidelist(room.solids), -1, (room_id, p.x, p.y))
            room.draw(pygame.Surface((400, 300)))

    def test_wasd_and_the_arrows_both_walk(self):
        self.dismiss_popups()
        self.quiet_cats(self.home)
        body = self.player.avatar
        for k, axis, sign in ((pygame.K_w, "y", -1), (pygame.K_UP, "y", -1), (pygame.K_a, "x", -1),
                              (pygame.K_RIGHT, "x", 1)):
            body.x, body.y = 200.0, 200.0
            before = getattr(body, axis)
            self.frames(1, [key(k)])
            self.frames(15)
            self.frames(1, [key(k, down=False)])
            self.assertGreater((getattr(body, axis) - before) * sign, 5, pygame.key.name(k))

    def test_no_key_can_add_a_second_player(self):
        """Not one key of the keyboard (nor any of the old P2 / join keys) makes a second body appear."""
        self.dismiss_popups()
        self.quiet_cats(self.home)
        room = self.home
        old_p2_and_join_keys = (pygame.K_RCTRL, pygame.K_RSHIFT, pygame.K_KP0, pygame.K_o, pygame.K_SLASH,
                                pygame.K_KP_ENTER, pygame.K_RETURN, pygame.K_j, pygame.K_2, pygame.K_KP2,
                                pygame.K_F2, pygame.K_INSERT, pygame.K_TAB, pygame.K_PLUS, pygame.K_p)
        for k in old_p2_and_join_keys:
            self.frames(1, [key(k)])
            self.frames(2, [key(k, down=False)])
            if self.game.scenes.current is not room:             # a key may open a window or a game: back out
                self.frames(1, [key(pygame.K_ESCAPE)])
            for _ in range(3):
                if room.modal is None:
                    break
                self.frames(2, [key(pygame.K_ESCAPE)])
            self.assertEqual(len(room.players), 1, pygame.key.name(k))
            self.assertEqual(len(self.session), 1)
            self.assertEqual(len(self.game.hub.avatars), 1)
        self.assertEqual(sum(isinstance(t, HubPlayer) for t in room.drawables() + room.players), 1)

    def test_nothing_in_the_ui_names_a_second_player(self):
        self.assertFalse(hasattr(ui, "JoinPrompt"))
        for room_id in ("home", "arcade_floor", "prize_plaza"):
            room = self.game.hub.room(room_id)
            self.assertFalse(hasattr(room, "two_player"))
            self.assertFalse(hasattr(room, "waiting_text"))
            self.assertFalse(hasattr(room, "guest_note"))
            self.assertEqual(room.build_hint_rows(), room.hint_rows)

    def test_the_hud_shows_the_wallet_without_any_owner_tag(self):
        hud = self.game.hub.hud
        hud._rebuild()
        self.assertEqual(hud._key[:2], (self.TOKENS, 0))
        self.assertFalse(hasattr(hud, "tag"))
        self.assertFalse(hasattr(hud, "slot"))
        self.a.add_tickets(31)
        self.frames(2)
        self.assertEqual(hud._key[:2], (self.TOKENS, 31))
        self.assertEqual(len(hud.floaters), 1)
        self.bob_is_untouched()

    def test_the_hud_class_takes_only_a_profile(self):
        hud = CurrencyHUD(PlayerProfile())
        hud._rebuild()
        self.assertEqual(hud.rect.bottomright, (396, 296))


@with_placeholder_minigame
class OwnershipTests(SoloTest):
    def test_playing_spends_the_players_tokens_only(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(racer)
        self.frames(5)
        self.assertIs(self.player.avatar.nearby, racer)
        self.use()
        self.assertIsNotNone(room.dialogue)
        self.assertIs(room.modal_owner, self.player.avatar)
        self.assertIs(room.interaction.initiating_player, self.player)
        self.assertNotIn("PLAYER", " ".join(str(d) for d, _ in room.dialogue.details))
        self.frames(1, [key(pygame.K_e)])                        # PLAY
        self.play_through_wipe()
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        self.esc_out_of_game(room)
        self.assertEqual(self.a.tickets, PLACEHOLDER_REWARD_TICKETS)
        self.assertEqual(self.a.total_games_played, 1)
        self.bob_is_untouched()

    def test_the_machine_remembers_who_started_it(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(racer)
        self.frames(5)
        self.use()
        self.assertIsInstance(room.interaction, MachineInteraction)
        self.assertIs(room.interaction.initiating_player, self.player)
        self.assertIs(room.interaction.profile, self.a)
        self.assertIs(room.interaction.machine, racer)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertIsNone(room.dialogue)
        self.assertEqual(self.a.tokens, self.TOKENS)

    def test_a_player_who_cannot_afford_does_not_borrow_from_another_profile(self):
        self.a.spend_tokens(self.TOKENS, "SETUP")
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(racer)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])                        # PLAY [LOCKED]
        self.frames(5)
        self.assertIs(self.game.scenes.current, room)
        self.assertEqual(self.a.tokens, 0)
        self.assertTrue(room.notice.visible)
        self.bob_is_untouched()

    def test_coupons_are_the_players_own(self):
        RewardService.grant_item(self.b, FREE_PLAY_COUPON, 2)    # Bob's coupons are not Alice's
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(racer)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])                        # no coupon question: Alice has none
        self.play_through_wipe()
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        self.assertEqual(self.b.inventory.get_quantity(FREE_PLAY_COUPON), 2)
        self.esc_out_of_game(room)
        RewardService.grant_item(self.a, FREE_PLAY_COUPON, 1)
        self.stand_at(racer)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(room.dialogue.title, "COUPON")
        self.assertIs(room.modal_owner, self.player.avatar)
        self.frames(30)
        self.frames(1, [key(pygame.K_RETURN)])                   # YES
        self.play_through_wipe()
        self.assertEqual(self.a.inventory.get_quantity(FREE_PLAY_COUPON), 0)
        self.assertEqual(self.a.tokens, self.TOKENS - 1)         # no tokens for the coupon game
        self.assertEqual(self.b.inventory.get_quantity(FREE_PLAY_COUPON), 2)
        self.esc_out_of_game(room)

    def test_a_game_that_never_ran_refunds_the_player(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(racer)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])
        self.assertIsNotNone(room.active_play)
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        self.game.quit()                                         # the window closes before the wipe ends
        self.assertEqual(self.a.tokens, self.TOKENS)
        self.bob_is_untouched()

    def test_the_prize_counter_and_lucky_corner_use_the_player(self):
        plaza = goto_room(self.game, "prize_plaza")
        self.quiet_cats(plaza)
        self.a.add_tickets(31)
        counter = next(p for p in plaza.props if p.prompt_label == "PRIZE COUNTER")
        wheel = next(p for p in plaza.props if isinstance(p, ChanceStation))
        self.stand_at(counter)
        self.player.avatar.y = float(counter.zone.bottom - 2)
        self.frames(5)
        self.use()
        from shop_ui import ShopScene
        shop = self.game.scenes.current
        self.assertIsInstance(shop, ShopScene)
        self.assertIs(shop.owner, self.player)
        self.assertIs(shop.shop.profile, self.a)
        self.frames(20)
        self.frames(40, [key(pygame.K_ESCAPE)])
        self.assertIs(self.game.scenes.current, plaza)
        self.stand_at(wheel)
        self.player.avatar.y = float(wheel.zone.bottom - 2)
        self.frames(5)
        self.use(frames=30)
        for _ in range(50):
            self.frames(1)
        scene = self.game.scenes.current
        self.assertIsNot(scene, plaza)
        self.assertIs(scene.profile, self.a)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        self.bob_is_untouched()


class InventoryTests(SoloTest):
    def test_the_player_opens_their_own_bag(self):
        self.dismiss_popups()
        RewardService.grant_item(self.a, "cat_sticker")
        RewardService.grant_item(self.b, FREE_PLAY_COUPON, 3)
        self.frames(1, [key(pygame.K_i)])
        self.assertIsInstance(self.home.inventory_ui, InventoryUI)
        self.assertIs(self.home.inventory_ui.inventory, self.a.inventory)
        self.assertIsNone(self.home.inventory_ui.owner)          # no "P1 ALICE" header
        self.assertIs(self.home.modal_owner, self.player.avatar)
        names = [d.id for d, _ in self.home.inventory_ui.entries]
        self.assertEqual(names, ["cat_sticker"])
        self.home.inventory_ui.draw(pygame.Surface((400, 300)))
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(3)
        self.assertIsNone(self.home.inventory_ui)

    def test_the_old_second_players_bag_key_opens_nothing(self):
        self.dismiss_popups()
        self.frames(1, [key(pygame.K_o)])
        self.assertIsNone(self.home.inventory_ui)

    def test_the_bag_answers_the_players_keys(self):
        self.dismiss_popups()
        RewardService.grant_item(self.a, "cat_sticker")
        self.frames(1, [key(pygame.K_i)])
        ui_ = self.home.inventory_ui
        sel = ui_.selected
        self.frames(1, [key(pygame.K_d)])
        self.assertNotEqual(ui_.selected, sel)
        self.frames(1, [key(pygame.K_TAB)])
        self.assertEqual(ui_.tab, 1)

    def test_the_daily_panel_shows_the_players_own_tasks(self):
        self.dismiss_popups()
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        self.quiet_cats(self.home)
        self.player.avatar.x, self.player.avatar.y = board.zone.centerx, board.zone.bottom - 2
        self.frames(5)
        self.use()
        self.assertIsNotNone(self.home.panel)
        self.assertIs(self.home.panel.profile, self.a)
        self.assertIsNone(self.home.panel.owner)
        self.home.panel.draw(pygame.Surface((400, 300)))


class DailyLoginTests(SoloTest):
    def test_only_the_playing_profile_logs_in(self):
        self.assertEqual(self.a.last_login_date, DAY1)
        self.assertIsNone(self.b.last_login_date)                # Bob was not played: no login recorded
        self.assertTrue(self.a.daily_status().can_claim)

    def test_the_popup_belongs_to_the_player_and_pays_once(self):
        self.frames(3)
        popup = self.home.popup
        self.assertIsNotNone(popup)
        self.assertIs(popup.player, self.player.avatar)
        self.assertIsNone(popup.owner)
        self.assertIs(self.home.modal_owner, self.player.avatar)
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(self.a.tokens, self.TOKENS + 5)
        self.assertFalse(self.a.daily_status().can_claim)
        self.frames(60)
        self.assertIsNone(self.home.popup)
        self.frames(1, [key(pygame.K_e), key(pygame.K_RETURN)])  # nothing pays twice
        self.frames(60)
        self.assertEqual(self.a.tokens, self.TOKENS + 5)
        self.bob_is_untouched()

    def test_putting_the_bonus_off_does_not_claim_it_or_nag(self):
        self.frames(3)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(3)
        self.assertEqual(self.a.tokens, self.TOKENS)
        self.assertTrue(self.a.daily_status().can_claim)
        self.assertIsNone(self.home.popup)
        self.frames(120)
        self.assertIsNone(self.home.popup)

    def test_the_claim_is_saved_to_the_players_file_only(self):
        self.frames(3)
        self.frames(1, [key(pygame.K_e)])
        with open(self.manager.profile_path(self.a.profile_id)) as f:
            saved_a = json.load(f)
        with open(self.manager.profile_path(self.b.profile_id)) as f:
            saved_b = json.load(f)
        self.assertEqual(saved_a["tokens"], self.TOKENS + 5)
        self.assertEqual(saved_b["tokens"], self.OTHER_TOKENS)
        self.assertNotEqual(saved_a["profile_id"], saved_b["profile_id"])

    def test_switching_profile_gives_that_profile_its_own_bonus(self):
        self.a.claim_daily_reward()
        g = Game(session=LocalSession(self.b))
        home = g.scenes.current
        self.assertIsInstance(home, HomeRoomScene)
        self.assertIs(home.popup.player, g.session.primary.avatar)
        self.assertIs(home.popup.player.profile, self.b)


class DailyTaskTests(SoloTest):
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

    def test_a_cat_event_advances_the_players_task(self):
        self.session.dispatch(GameEvent("cat_petted", self.player.player_id))
        self.assertEqual(self.progress(self.a)["pet_cats"], 1)
        self.assertEqual(self.progress(self.b)["pet_cats"], 0)

    def test_tickets_advance_the_earners_task_only(self):
        self.a.add_tickets(20)
        self.assertEqual(self.progress(self.a)["earn_tickets"], 20)
        self.assertEqual(self.progress(self.b)["earn_tickets"], 0)

    def test_petting_a_cat_in_the_world_counts_for_the_player(self):
        self.dismiss_popups()
        cat = next(iter(self.home.cats))
        self.quiet_cats(self.home)
        cat.x, cat.y = 300.0, 200.0
        cat.set_state(CatState.IDLE, 999)
        self.player.avatar.x, self.player.avatar.y = cat.x - 14, cat.y
        self.frames(3)
        self.assertIs(self.player.avatar.nearby_cat, cat)
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(self.a.cats_petted, 1)
        self.assertEqual(self.progress(self.a)["pet_cats"], 1)
        self.assertEqual(self.b.cats_petted, 0)
        self.frames(1, [key(pygame.K_e), key(pygame.K_RETURN)])  # still reacting: no second count
        self.assertEqual(self.a.cats_petted, 1)
        self.frames(60)
        self.home.draw(pygame.Surface((400, 300)))

    def test_machine_visits_are_counted_for_the_visitor(self):
        visit = {"id": "visit_machines", "description": "VISIT 3 DIFFERENT MACHINES",
                 "event": "machine_visited", "distinct": True, "target": 3, "reward": 5}
        for profile in (self.a, self.b):
            profile._tasks = DailyTaskManager(pool=(visit,), count=1)
            profile._tasks.ensure_current(DAY1, random.Random(1))
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(racer)
        self.frames(5)
        self.use()
        self.assertEqual(self.progress(self.a)["visit_machines"], 1)
        self.assertEqual(self.progress(self.b)["visit_machines"], 0)
        self.frames(1, [key(pygame.K_ESCAPE)])


@with_placeholder_minigame
class MiniGameTests(SoloTest):
    def test_a_definition_is_just_the_game_id(self):
        d = MiniGameDefinition("x")
        self.assertEqual(d.game_id, "x")
        for gone in ("min_players", "max_players", "supports", "multiplayer"):
            self.assertFalse(hasattr(d, gone), gone)
        with self.assertRaises(TypeError):
            MiniGameDefinition("y", 1, 2)

    def test_every_real_minigame_has_a_definition(self):
        for data in MACHINES:
            d = minigame_definition(data.get("game_id", data["id"]))
            self.assertEqual(d.game_id, data.get("game_id", data["id"]))
        for game_id in ("retro_racer", "puzzle_drop", "pixel_volleyball", "cat_minesweeper",
                        "galaxy_defender", "puzzle_maze"):
            self.assertIn(game_id, MINIGAME_DEFINITIONS)
        self.assertEqual(minigame_definition("who_knows"), MiniGameDefinition("who_knows"))

    def test_a_scene_knows_its_participant(self):
        room = self.arcade()
        machine = self.machine(room, "puzzle_drop")
        scene = create_minigame_scene(self.game, machine, [self.a])
        self.assertEqual(scene.participants, [self.a])
        solo = create_minigame_scene(self.game, machine)
        self.assertEqual(solo.participants, [self.a])

    def test_the_result_is_one_players(self):
        room = self.arcade()
        scene = create_minigame_scene(self.game, self.machine(room, "puzzle_drop"), [self.a])
        result = scene.get_result()
        self.assertIsInstance(result, MiniGameResult)
        self.assertEqual([r.profile_id for r in result.player_results], [self.a.profile_id])
        for r in result.player_results:
            self.assertIsInstance(r, PlayerResult)
            self.assertIsInstance(r.reward, RewardBundle)
            self.assertEqual(r.reward.tickets, PLACEHOLDER_REWARD_TICKETS)
        self.assertIs(result.for_profile(self.a.profile_id), result.player_results[0])
        self.assertIsNone(result.for_profile("nobody"))

    def test_settling_a_player_result_pays_that_profile_once(self):
        session = PlaySession(self.a, "puzzle_drop", 1)
        pr = PlayerResult(self.a.profile_id, 500, RewardBundle(tickets=9))
        self.assertIs(session.settle_result(pr), pr)
        self.assertEqual((self.a.tickets, self.a.high_score("puzzle_drop"), self.a.total_games_played), (9, 500, 1))
        self.assertIsNone(session.settle_result(pr))             # once only
        self.assertFalse(session.refund())
        self.assertEqual((self.b.tickets, self.b.total_games_played), (0, 0))

    def test_no_machine_asks_how_many_play(self):
        room = self.arcade()
        for data in MACHINES:
            self.assertFalse(hasattr(minigame_definition(data.get("game_id", data["id"])), "multiplayer"))
        machine = self.machine(room, "puzzle_drop")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])                        # PLAY: straight into the game
        self.assertIsNone(room.dialogue)
        self.assertIsNotNone(room.active_play)
        self.play_through_wipe()
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        scene = self.game.scenes.current
        self.assertEqual(scene.participants, [self.a])
        self.assertEqual(len(scene.players), 1)
        self.assertFalse(hasattr(scene, "spectators"))
        self.esc_out_of_game(room)
        self.assertEqual(self.a.tickets, PLACEHOLDER_REWARD_TICKETS)
        self.assertEqual(len(room.players), 1)
        self.assertIs(self.game.scenes.current, room)
        room._end_play(ran=True)                                  # nothing more to settle
        self.assertEqual(self.a.tickets, PLACEHOLDER_REWARD_TICKETS)
        self.assertIsNone(room.active_play)
        self.bob_is_untouched()

    def test_the_old_second_player_keys_do_nothing_inside_a_game(self):
        room = self.arcade()
        machine = self.machine(room, "puzzle_drop")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])
        self.play_through_wipe()
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        before = (self.a.tokens, len(room.players))
        for k in (pygame.K_RCTRL, pygame.K_KP0, pygame.K_o, pygame.K_RSHIFT):
            self.frames(2, [key(k)])
        self.assertEqual((self.a.tokens, len(room.players)), before)
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.esc_out_of_game(room)


class RoomChangeTests(SoloTest):
    def setUp(self):
        super().setUp()
        self.dismiss_popups()

    def at_door(self, side="left"):
        self.player.avatar.x = 6.0 if side == "left" else VIEW_W - 6.0
        self.player.avatar.y = float(DOOR_MID_Y)

    def near_door(self, side="left"):
        self.player.avatar.x = 40.0 if side == "left" else VIEW_W - 40.0
        self.player.avatar.y = float(DOOR_MID_Y)

    def test_the_player_alone_at_the_exit_changes_room_at_once(self):
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.at_door()
        self.frames(10)
        self.settle()
        arcade = self.game.scenes.current
        self.assertEqual(arcade.room_id, "arcade_floor")
        self.assertEqual(arcade.players, self.session.avatars)
        self.assertFalse(hasattr(arcade, "waiting_text"))

    def test_the_player_survives_a_trip_through_all_three_rooms(self):
        route = (("left", "arcade_floor"), ("right", "home"), ("right", "prize_plaza"), ("left", "home"))
        for side, target in route:
            room = self.game.scenes.current
            self.quiet_cats(room)
            room.arrival_grace = 0
            self.at_door(side)
            self.frames(10)
            self.settle()
            room = self.game.scenes.current
            self.assertEqual(room.room_id, target)
            self.assertEqual(self.player.avatar.feet.collidelist(room.solids), -1)
            if target == "home" and room.popup:
                self.frames(3, [key(pygame.K_ESCAPE)] * 2)
        self.assertEqual(len(self.game.hub.built_rooms), 3)

    def test_arrival_is_at_the_doorway_facing_in(self):
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.at_door()
        self.frames(10)
        self.settle()
        arcade = self.game.scenes.current
        p = arcade.player
        self.assertEqual(p.facing, "left")
        self.assertGreater(p.x, VIEW_W / 2)
        self.assertAlmostEqual(p.y, ENTRIES["right"][0][1], delta=2)

    def test_a_player_standing_in_a_door_cannot_walk_off_the_screen(self):
        self.quiet_cats(self.home)
        self.home.arrival_grace = 0
        self.player.avatar.x, self.player.avatar.y = 6.0, float(DOOR_MID_Y)
        self.home.leaving = True        # (the doorway has fired; keys must not push the body out of the room)
        self.frames(1, [key(pygame.K_a)])
        self.frames(60)
        self.assertGreater(self.player.avatar.x, 0)


class HomeOwnershipTests(SoloTest):
    def test_home_shows_the_players_decorations(self):
        self.a.set_home_decoration("rug", "rug_lounge")
        self.assertIs(self.home.profile, self.a)
        self.assertIs(self.home.decorations.profile, self.a)
        self.b.set_home_decoration("rug", "rug_other")
        self.assertEqual(self.a.home_decorations, {"rug": "rug_lounge"})
        self.assertEqual(self.b.home_decorations, {"rug": "rug_other"})

    def test_the_player_can_always_decorate_their_own_home(self):
        self.dismiss_popups()
        self.home.open_decoration_mode()
        self.frames(40)
        from decor_ui import DecorationScene
        self.assertIsInstance(self.game.scenes.current, DecorationScene)


@with_placeholder_minigame
class SavingTests(SoloTest):
    def test_the_players_changes_land_in_their_own_file(self):
        self.a.add_tickets(11)
        RewardService.grant_item(self.a, "cat_sticker")
        with open(self.manager.profile_path(self.a.profile_id)) as f:
            sa = json.load(f)
        with open(self.manager.profile_path(self.b.profile_id)) as f:
            sb = json.load(f)
        self.assertEqual((sa["tickets"], sb["tickets"]), (11, 0))
        self.assertEqual(sa["inventory"], {"cat_sticker": 1})
        self.assertEqual(sb["inventory"], {})
        self.assertEqual((sa["display_name"], sb["display_name"]), ("Alice", "Bob"))

    def test_a_whole_session_survives_a_restart(self):
        room = self.arcade()
        racer = self.machine(room, "puzzle_drop")
        self.stand_at(racer)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])
        self.play_through_wipe()
        self.esc_out_of_game(room)
        again = ProfileManager(os.path.join(self.dir, "saves"), clock=GameClock(lambda: DAY1))
        ra, rb = again.load_profile(self.a.profile_id), again.load_profile(self.b.profile_id)
        self.assertEqual((ra.tokens, ra.tickets), (self.TOKENS - 1, PLACEHOLDER_REWARD_TICKETS))
        self.assertEqual((rb.tokens, rb.tickets), (self.OTHER_TOKENS, 0))


class SinglePlayerRegressionTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_plain_save_file_still_starts_a_one_player_hub(self):
        g = Game(save_path=os.path.join(self.dir, "s.json"), clock=GameClock(lambda: DAY1))
        home = g.scenes.current
        self.assertEqual(len(home.players), 1)
        self.assertEqual(len(g.hub.huds), 1)
        self.assertEqual(g.session.primary.name, "PLAYER")
        for _ in range(3):
            g.step([key(pygame.K_ESCAPE)], DT)
        g.step([key(pygame.K_i)], DT)
        self.assertIsNotNone(home.inventory_ui)
        self.assertIsNone(home.inventory_ui.owner)
        self.assertEqual(home.build_hint_rows(), home.hint_rows)

    def test_the_arcade_floor_has_no_player_choice_or_waiting(self):
        g = Game(save_path=os.path.join(self.dir, "s.json"), clock=GameClock(lambda: DAY1))
        room = goto_room(g, "arcade_floor")
        self.assertFalse(hasattr(room, "waiting_text"))
        self.assertEqual(len(room.players), 1)


if __name__ == "__main__":
    unittest.main()
