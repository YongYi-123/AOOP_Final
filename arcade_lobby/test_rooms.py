"""Tests for the three-room hub: ARCADE FLOOR <-> HOME <-> PRIZE PLAZA.

Run with:  python -m unittest test_rooms
"""
import json
import os
import shutil
import tempfile
import unittest
from datetime import date
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from arcade_floor import ArcadeFloorScene  # noqa: E402
from arcade_layout import (ARCADE_SLOTS, ArcadeLayout, ArcadeMachineDefinition,  # noqa: E402
                           MachineTheme)
from cat import CatState  # noqa: E402
from decorations import (CAT_BED, NEON_SIGN, PLANT, WALL_POSTER, DecorationCatalog,  # noqa: E402
                         DecorationDefinition, DecorationSlot, HomeDecorationManager,
                         default_catalog)
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from home_room import HOME_SLOTS, HomeRoomScene  # noqa: E402
from item_registry import FREE_PLAY_COUPON  # noqa: E402
from machine import ArcadeMachine, IdleCabinet  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from prize_plaza import PrizePlazaScene  # noqa: E402
from room_scene import BaseRoomScene, RoomExit  # noqa: E402
from room_testing import goto_room  # noqa: E402
from scenes import MinigamePlaceholderScene  # noqa: E402
from settings import (CATS, MACHINES, PLAYER_START, ROOM_IDS, ROOM_TITLE_TIME,  # noqa: E402
                      SIDE_DOOR_H, SIDE_DOOR_Y, START_ROOM, VIEW_H, VIEW_W)
from stations import ChanceStation, DailyBoard  # noqa: E402

DT = 1 / 60
DAY1 = date(2025, 3, 10)
DOOR_MID_Y = SIDE_DOOR_Y + SIDE_DOOR_H // 2 + 2


def key(k, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=k, mod=0, unicode="")


class HubTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")
        self.clock = GameClock(lambda: DAY1)
        self.game = Game(save_path=self.path, clock=self.clock)
        self.hub = self.game.hub
        self.home = self.game.scenes.current

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    # ---- helpers
    def frames(self, n, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def current_id(self):
        return self.game.scenes.current.room_id

    def dismiss_popup(self):
        self.frames(3, [key(pygame.K_ESCAPE)])
        self.assertIsNone(self.home.popup)

    def quiet_cats(self, room):
        """Park the room's cats out of the way, asleep."""
        for i, cat in enumerate(room.cats):
            cat.x, cat.y = 120.0 + i * 20, 120.0
            cat.set_state(CatState.SLEEP, 999)

    def walk(self, room, direction_key, seconds=6.0, until=None):
        """Hold a movement key until the scene changes (or time runs out)."""
        self.frames(1, [key(direction_key)])
        for _ in range(int(seconds / DT)):
            self.frames(1)
            if until and until():
                break
        self.frames(1, [key(direction_key, down=False)])

    def settle(self):
        self.frames(int(0.8 / DT))      # let a wipe finish

    def walk_through(self, door_key, target_id):
        room = self.game.scenes.current
        self.quiet_cats(room)
        room.player.y = float(DOOR_MID_Y)
        self.walk(room, door_key, until=lambda: self.current_id() == target_id and
                  not self.game.scenes.transitioning)
        self.settle()
        self.assertEqual(self.current_id(), target_id)
        return self.game.scenes.current

    def assert_valid_position(self, room):
        p = room.player
        self.assertEqual(p.feet.collidelist(room.solids), -1, (room.room_id, p.x, p.y))
        self.assertTrue(0 < p.x < VIEW_W and 0 < p.y < VIEW_H)


class StartTests(HubTest):
    def test_game_starts_in_home(self):
        self.assertIsInstance(self.home, HomeRoomScene)
        self.assertEqual(self.home.room_id, START_ROOM)
        self.assertEqual((self.home.player.x, self.home.player.y), PLAYER_START)
        self.assert_valid_position(self.home)

    def test_only_the_visited_rooms_are_built(self):
        self.assertEqual(list(self.hub.built_rooms), ["home"])

    def test_home_holds_the_daily_systems(self):
        self.assertIsNotNone(self.home.popup)                          # the login bonus
        self.assertTrue(any(isinstance(p, DailyBoard) for p in self.home.props))
        self.assertEqual(self.home.machines, [])
        self.assertGreaterEqual(len(self.home.cats), 3)

    def test_arcade_and_plaza_keep_their_own_things(self):
        arcade, plaza = self.hub.room("arcade_floor"), self.hub.room("prize_plaza")
        self.assertEqual([m.id for m in arcade.machines], [d["id"] for d in MACHINES])
        self.assertFalse(any(isinstance(p, DailyBoard) for p in arcade.props + plaza.props))
        self.assertTrue(any(isinstance(p, ChanceStation) for p in plaza.props))
        self.assertEqual(plaza.machines, [])

    def test_exits_form_the_three_room_line(self):
        """ARCADE <-> HOME <-> PLAZA, every door has a way back, and the
        arcade never connects straight to the plaza."""
        rooms = {rid: self.hub.room(rid) for rid in ROOM_IDS}
        links = {rid: {e.target for e in r.exits} for rid, r in rooms.items()}
        self.assertEqual(links, {"home": {"arcade_floor", "prize_plaza"},
                                 "arcade_floor": {"home"}, "prize_plaza": {"home"}})
        for rid, room in rooms.items():
            for door in room.exits:
                back = [e for e in rooms[door.target].exits if e.target == rid]
                self.assertEqual(len(back), 1)
                self.assertEqual(back[0].side, door.entry)       # arrive through the matching door
                self.assertNotEqual(door.side, door.entry)       # left door -> right door of the next
        self.assertEqual(rooms["home"].exits[0].side, "left")     # ARCADE is on the left
        self.assertEqual(rooms["home"].exits[1].side, "right")    # PRIZES on the right


class WalkingTests(HubTest):
    def test_home_to_arcade_and_back(self):
        self.dismiss_popup()
        arcade = self.walk_through(pygame.K_a, "arcade_floor")
        self.assertIsInstance(arcade, ArcadeFloorScene)
        self.assert_valid_position(arcade)
        self.assertGreater(arcade.player.x, VIEW_W / 2)           # came in through the right door
        home = self.walk_through(pygame.K_d, "home")
        self.assertIs(home, self.home)
        self.assert_valid_position(home)
        self.assertLess(home.player.x, VIEW_W / 2)                # back through HOME's left door

    def test_home_to_plaza_and_back(self):
        self.dismiss_popup()
        plaza = self.walk_through(pygame.K_d, "prize_plaza")
        self.assertIsInstance(plaza, PrizePlazaScene)
        self.assert_valid_position(plaza)
        self.assertLess(plaza.player.x, VIEW_W / 2)
        home = self.walk_through(pygame.K_a, "home")
        self.assertIs(home, self.home)
        self.assert_valid_position(home)
        self.assertGreater(home.player.x, VIEW_W / 2)

    def test_arcade_and_plaza_are_not_directly_connected(self):
        self.assertFalse([e for e in self.hub.room("arcade_floor").exits if e.target == "prize_plaza"])
        self.assertFalse([e for e in self.hub.room("prize_plaza").exits if e.target == "arcade_floor"])

    def test_walls_close_the_sides_that_have_no_door(self):
        arcade = self.hub.room("arcade_floor")                    # only a right door
        arcade.player.x, arcade.player.y = 40.0, 150.0
        goto_room(self.game, "arcade_floor")
        self.frames(1, [key(pygame.K_a)])
        self.frames(120)
        self.assertEqual(self.current_id(), "arcade_floor")
        self.assertGreater(self.game.scenes.current.player.x, 15)

    def test_arrival_is_through_the_matching_door_and_clear(self):
        for door_key, target, side in ((pygame.K_a, "arcade_floor", "right"),
                                       (pygame.K_d, "prize_plaza", "left")):
            self.dismiss_popup()
            room = self.walk_through(door_key, target)
            self.assertEqual(room.player.facing, "left" if side == "right" else "right")
            self.assertTrue(room.exits[0].side == side)
            self.walk_through(pygame.K_d if side == "right" else pygame.K_a, "home")

    def test_walk_across_the_whole_home_room(self):
        """The doorways are reachable from the spawn point (nothing blocks the path)."""
        self.dismiss_popup()
        self.quiet_cats(self.home)
        self.home.player.x, self.home.player.y = float(PLAYER_START[0]), float(DOOR_MID_Y)
        self.walk(self.home, pygame.K_a, until=lambda: self.current_id() != "home")
        self.settle()
        self.assertEqual(self.current_id(), "arcade_floor")


class TransitionSafetyTests(HubTest):
    def test_a_doorway_cannot_trigger_twice(self):
        self.dismiss_popup()
        enters = []
        arcade = self.hub.room("arcade_floor")
        real_enter = arcade.on_enter
        arcade.on_enter = lambda: (enters.append(1), real_enter())
        self.quiet_cats(self.home)
        self.home.player.x, self.home.player.y = 30.0, float(DOOR_MID_Y)
        self.frames(1, [key(pygame.K_a)])
        for _ in range(240):                       # keep pushing into the door the whole time
            self.frames(1)
        self.assertEqual(enters, [1])
        self.assertEqual(self.current_id(), "arcade_floor")
        self.assertFalse(self.hub.travel(self.home, self.home.exits[0]))   # stale request: refused

    def test_standing_in_the_trigger_after_arriving_does_not_bounce(self):
        self.dismiss_popup()
        arcade = self.walk_through(pygame.K_a, "arcade_floor")
        for _ in range(180):
            self.frames(1)
        self.assertEqual(self.current_id(), "arcade_floor")
        self.assertIs(self.game.scenes.current, arcade)

    def test_travel_is_refused_during_a_wipe_and_from_a_hidden_room(self):
        self.dismiss_popup()
        self.assertTrue(self.hub.travel(self.home, self.home.exits[0]))
        self.assertTrue(self.game.scenes.transitioning)
        self.assertFalse(self.hub.travel(self.home, self.home.exits[1]))
        self.settle()
        self.assertEqual(self.current_id(), "arcade_floor")
        self.assertFalse(self.hub.travel(self.home, self.home.exits[1]))   # HOME is not on screen

    def test_dialogue_closes_during_a_transition(self):
        arcade = goto_room(self.game, "arcade_floor")
        machine = arcade.machines[1]
        arcade.player.x, arcade.player.y = machine.rect.centerx, machine.rect.bottom + 12
        self.frames(5)
        self.frames(30, [key(pygame.K_e)])
        self.assertIsNotNone(arcade.dialogue)
        tokens = self.game.profile.tokens
        self.assertTrue(self.hub.travel(arcade, arcade.exits[0]))          # forced while the box is open
        self.settle()
        self.assertEqual(self.current_id(), "home")
        self.assertIsNone(arcade.dialogue)
        self.assertIsNone(arcade.activating)
        self.assertEqual(self.game.profile.tokens, tokens)                 # nothing was charged
        self.hub.travel(self.game.scenes.current, self.game.scenes.current.exits[0])
        self.settle()
        self.assertIsNone(arcade.dialogue)

    def test_task_panel_inventory_and_popup_close_on_leaving_home(self):
        self.home.open_task_panel()
        self.assertTrue(self.hub.travel(self.home, self.home.exits[1]))
        self.settle()
        self.assertIsNone(self.home.panel)
        self.assertIsNone(self.home.popup)

    def test_held_keys_are_released_on_arrival(self):
        self.dismiss_popup()
        self.home.player.x, self.home.player.y = 30.0, float(DOOR_MID_Y)
        self.frames(1, [key(pygame.K_a), key(pygame.K_w)])
        self.settle()
        room = self.game.scenes.current
        self.assertEqual(room.room_id, "arcade_floor")
        x, y = room.player.x, room.player.y
        self.frames(30)
        self.assertEqual((room.player.x, room.player.y), (x, y))           # nothing stuck held

    def test_repeated_room_switching_never_crashes(self):
        self.dismiss_popup()
        route = ["arcade_floor", "home", "prize_plaza", "home"] * 12
        for i, target in enumerate(route):
            cur = self.game.scenes.current
            door = next(e for e in cur.exits if e.target == target)
            self.assertTrue(self.hub.travel(cur, door), (i, target))
            self.frames(int(0.5 / DT) if i % 2 else 5)          # sometimes mid-wipe
            if self.game.scenes.transitioning:
                self.settle()
            self.assertEqual(self.current_id(), target)
            self.assert_valid_position(self.game.scenes.current)
            self.game.scenes.current.draw(self.game.canvas)

    def test_random_input_while_switching(self):
        import random
        rng = random.Random(3)
        keys = [pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_e, pygame.K_i,
                pygame.K_ESCAPE, pygame.K_RETURN]
        for n in range(1500):
            room = self.game.scenes.current
            if n % 45 == 0 and isinstance(room, BaseRoomScene) and room.exits:
                door = rng.choice(room.exits)                    # drift toward a doorway now and then
                room.player.x = 40.0 if door.side == "left" else VIEW_W - 40.0
                room.player.y = float(DOOR_MID_Y)
            events = [key(rng.choice(keys), rng.random() < 0.6) for _ in range(rng.randrange(3))]
            self.frames(1, events)
            room = self.game.scenes.current
            if isinstance(room, MinigamePlaceholderScene):
                self.frames(1, [key(pygame.K_ESCAPE)])
            elif not self.game.scenes.transitioning:
                self.assertIsInstance(room, BaseRoomScene)
                self.assert_valid_position(room)
            room.draw(self.game.canvas) if hasattr(room, "draw") else None


class SharedStateTests(HubTest):
    def test_one_player_and_one_profile_for_every_room(self):
        rooms = [self.hub.room(r) for r in ROOM_IDS]
        self.assertEqual(len({id(r.player) for r in rooms}), 1)
        self.assertTrue(all(r.player is self.hub.player for r in rooms))
        self.assertEqual(len({id(r.hud) for r in rooms}), 1)
        self.assertTrue(all(r.profile is self.game.profile for r in rooms))
        self.assertEqual(len({id(r) for r in rooms}), 3)
        self.assertEqual(len({id(r.cats) for r in rooms}), 3)

    def test_rooms_are_kept_not_rebuilt(self):
        before = {r: self.hub.room(r) for r in ROOM_IDS}
        for target in ("arcade_floor", "home", "prize_plaza", "home"):
            cur = self.game.scenes.current
            self.hub.travel(cur, next(e for e in cur.exits if e.target == target))
            self.settle()
        self.assertTrue(all(self.hub.room(r) is before[r] for r in ROOM_IDS))

    def test_currency_inventory_and_daily_progress_persist(self):
        self.dismiss_popup()
        p = self.game.profile
        p.add_tokens(7, "TEST")
        p.add_tickets(33)
        p.inventory.add_item("cat_sticker", 2)
        p.inventory.add_item(FREE_PLAY_COUPON, 1)
        p.record_cat_petted()
        def snap():
            return (p.tokens, p.tickets, p.inventory.to_dict(), p.cats_petted,
                    [t.to_dict() for t in p.daily_tasks], p.to_dict()["daily_streak"])

        before = snap()
        for target in ("arcade_floor", "home", "prize_plaza", "home"):
            cur = self.game.scenes.current
            self.hub.travel(cur, next(e for e in cur.exits if e.target == target))
            self.settle()
            self.assertIs(self.game.profile, p)
            self.assertEqual(snap(), before)
        self.assertEqual(self.hub.hud.profile, p)

    def test_the_login_bonus_is_not_paid_or_offered_again_by_room_changes(self):
        self.frames(3, [key(pygame.K_RETURN)])                    # claim today's bonus in HOME
        self.frames(60)
        self.assertIsNone(self.home.popup)
        tokens = self.game.profile.tokens
        for target in ("arcade_floor", "home", "prize_plaza", "home", "arcade_floor", "home"):
            cur = self.game.scenes.current
            self.hub.travel(cur, next(e for e in cur.exits if e.target == target))
            self.settle()
            self.assertIsNone(self.home.popup)
            self.assertEqual(self.game.profile.tokens, tokens)

    def test_a_declined_bonus_comes_back_only_in_home_and_never_twice(self):
        self.dismiss_popup()
        self.assertEqual(self.game.profile.tokens, 10)
        self.hub.travel(self.home, self.home.exits[0])
        self.settle()
        self.assertIsNone(self.game.scenes.current.popup)          # not in the arcade
        cur = self.game.scenes.current
        self.hub.travel(cur, cur.exits[0])
        self.settle()
        self.assertIsNone(self.home.popup)                        # declined today: left alone
        self.game.profile.clock.advance_days(1)
        self.frames(80)
        self.assertIsNotNone(self.home.popup)                     # a new day offers it again
        self.frames(3, [key(pygame.K_RETURN)])
        self.frames(60)
        paid = self.game.profile.tokens
        self.hub.travel(self.home, self.home.exits[0])
        self.settle()
        cur = self.game.scenes.current
        self.hub.travel(cur, cur.exits[0])
        self.settle()
        self.assertEqual(self.game.profile.tokens, paid)
        self.assertIsNone(self.home.popup)

    def test_only_the_active_room_is_updated(self):
        self.dismiss_popup()
        arcade, plaza = self.hub.room("arcade_floor"), self.hub.room("prize_plaza")
        times = (arcade.time, plaza.time, arcade.cats.cats[0].time, arcade.machines[0].marquee.image)
        home_time = self.home.time
        self.frames(120)
        self.assertGreater(self.home.time, home_time)
        self.assertEqual((arcade.time, plaza.time, arcade.cats.cats[0].time,
                          arcade.machines[0].marquee.image), times)

    def test_room_state_is_kept_while_away(self):
        self.dismiss_popup()
        cat = self.home.cats.get("miso")
        cat.x, cat.y = 300.0, 150.0
        cat.set_state(CatState.SIT, 999)
        pos, state = cat.position, cat.state
        self.hub.travel(self.home, self.home.exits[0])
        self.settle()
        self.frames(200)
        cur = self.game.scenes.current
        self.hub.travel(cur, cur.exits[0])
        self.settle()
        self.assertEqual(self.home.cats.get("miso").position, pos)
        self.assertEqual(self.home.cats.get("miso").state, state)
        self.assertIs(self.home.cats.get("miso"), cat)

    def test_a_cat_never_follows_into_another_room(self):
        self.dismiss_popup()
        cat = self.home.cats.get("miso")
        self.home.cats.request_follow(cat)
        cat.start_follow(99)
        self.hub.travel(self.home, self.home.exits[1])
        self.settle()
        self.assertIsNone(self.home.cats.follower)
        self.assertNotEqual(cat.state, CatState.FOLLOW)
        self.assertNotIn(cat, self.game.scenes.current.cats.cats)


class GameplayInRoomsTests(HubTest):
    def go_arcade(self):
        self.dismiss_popup()
        return self.walk_through(pygame.K_a, "arcade_floor")

    def stand_at(self, room, machine):
        room.player.x, room.player.y = machine.rect.centerx, machine.rect.bottom + 12
        self.frames(5)
        self.assertIs(room.nearby, machine)

    def play_once(self, room, machine, confirm_coupon=None):
        self.stand_at(room, machine)
        self.frames(30, [key(pygame.K_e)])
        self.assertIsNotNone(room.dialogue)
        self.frames(1, [key(pygame.K_RETURN)])
        if confirm_coupon is not None:
            self.frames(30)
            self.assertEqual(room.dialogue.title, "COUPON")
            if confirm_coupon:
                self.frames(1, [key(pygame.K_RETURN)])
            else:
                self.frames(1, [key(pygame.K_DOWN)])
                self.frames(1, [key(pygame.K_RETURN)])
        self.frames(40)
        self.assertIsInstance(self.game.scenes.current, MinigamePlaceholderScene)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(40)
        self.assertIs(self.game.scenes.current, room)

    def test_machine_payment_after_travelling(self):
        arcade = self.go_arcade()
        machine = next(m for m in arcade.machines if m.id == "space_blaster")
        tokens = self.game.profile.tokens
        self.play_once(arcade, machine)
        self.assertEqual(self.game.profile.tokens, tokens - machine.play_cost)
        self.assertGreater(self.game.profile.tickets, 0)
        self.assertEqual(self.game.profile.total_games_played, 1)

    def test_machine_payment_charges_once_even_when_mashing(self):
        arcade = self.go_arcade()
        machine = arcade.machines[1]
        self.stand_at(arcade, machine)
        self.frames(30, [key(pygame.K_e)])
        self.frames(1, [key(pygame.K_RETURN)] * 6)
        self.frames(60, [key(pygame.K_RETURN)])
        self.assertEqual(self.game.profile.tokens, 10 - machine.play_cost)

    def test_coupon_payment_after_travelling(self):
        arcade = self.go_arcade()
        self.game.profile.inventory.add_item(FREE_PLAY_COUPON, 1)
        machine = arcade.machines[1]
        tokens = self.game.profile.tokens
        self.play_once(arcade, machine, confirm_coupon=True)
        self.assertEqual(self.game.profile.tokens, tokens)
        self.assertEqual(self.game.profile.inventory.get_quantity(FREE_PLAY_COUPON), 0)

    def test_declining_the_coupon_pays_tokens(self):
        arcade = self.go_arcade()
        self.game.profile.inventory.add_item(FREE_PLAY_COUPON, 1)
        machine = arcade.machines[1]
        self.play_once(arcade, machine, confirm_coupon=False)
        self.assertEqual(self.game.profile.tokens, 10 - machine.play_cost)
        self.assertEqual(self.game.profile.inventory.get_quantity(FREE_PLAY_COUPON), 1)

    def test_cannot_leave_while_a_paid_game_is_running(self):
        arcade = self.go_arcade()
        machine = arcade.machines[1]
        self.stand_at(arcade, machine)
        self.frames(30, [key(pygame.K_e)])
        self.frames(1, [key(pygame.K_RETURN)])
        self.frames(40)
        self.assertIsNotNone(arcade.active_play)
        self.assertFalse(self.hub.travel(arcade, arcade.exits[0]))
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(40)
        self.assertIsNone(arcade.active_play)

    def test_lucky_corner_is_in_the_plaza_and_charges_tokens(self):
        self.dismiss_popup()
        plaza = self.walk_through(pygame.K_d, "prize_plaza")
        wheel = next(p for p in plaza.props if isinstance(p, ChanceStation)
                     and p.game_cls.__name__ == "LuckyWheelGame")
        plaza.player.x, plaza.player.y = wheel.zone.centerx, wheel.zone.bottom - 2
        self.frames(5)
        self.assertIs(plaza.nearby, wheel)
        self.frames(30, [key(pygame.K_e)])
        self.frames(40)
        self.assertEqual(self.game.profile.tokens, 10)             # entering is free
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(self.game.profile.tokens, 9)

    def test_prize_counter_is_a_placeholder_that_shows_tickets(self):
        self.dismiss_popup()
        plaza = self.walk_through(pygame.K_d, "prize_plaza")
        self.game.profile.add_tickets(12)
        counter = next(p for p in plaza.props if p.prompt_label == "PRIZE COUNTER" if hasattr(p, "prompt_label"))
        plaza.player.x, plaza.player.y = counter.zone.centerx, counter.zone.bottom - 2
        self.frames(5)
        self.assertIs(plaza.nearby, counter)
        tickets, tokens = self.game.profile.tickets, self.game.profile.tokens
        self.frames(30, [key(pygame.K_e)])
        self.assertTrue(plaza.notice.visible)
        self.assertEqual((self.game.profile.tickets, self.game.profile.tokens), (tickets, tokens))

    def test_daily_board_and_tasks_work_in_home_after_travelling(self):
        self.dismiss_popup()
        self.walk_through(pygame.K_a, "arcade_floor")
        self.walk_through(pygame.K_d, "home")
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        self.home.player.x, self.home.player.y = board.zone.centerx, board.zone.bottom - 2
        self.frames(5)
        self.assertIs(self.home.nearby, board)
        self.frames(30, [key(pygame.K_e)])
        self.assertIsNotNone(self.home.panel)

    def test_cats_can_still_be_petted_after_travelling(self):
        self.dismiss_popup()
        self.walk_through(pygame.K_d, "prize_plaza")
        self.walk_through(pygame.K_a, "home")
        cat = self.home.cats.get("miso")
        for c in self.home.cats:
            c.set_state(CatState.SLEEP, 999)
        cat.set_state(CatState.SIT, 999)
        cat.chat_timer = 999
        self.home.player.x, self.home.player.y = cat.x - 14, cat.y
        self.frames(3)
        self.assertIs(self.home.nearby_cat, cat)
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(cat.state, CatState.PET)
        self.assertEqual(self.game.profile.cats_petted, 1)

    def test_inventory_opens_in_every_room_and_closes_on_leaving(self):
        self.dismiss_popup()
        self.frames(2, [key(pygame.K_i)])
        self.assertIsNotNone(self.home.inventory_ui)
        self.hub.travel(self.home, self.home.exits[0])
        self.settle()
        self.assertIsNone(self.home.inventory_ui)

    def test_debug_keys_work_in_every_room(self):
        g = Game(save_path=self.path, clock=self.clock, debug=True)
        for room_id in ROOM_IDS:
            goto_room(g, room_id)
            g.step([key(pygame.K_ESCAPE)], DT)               # (HOME opens with the login bonus)
            before = g.profile.tokens
            g.step([key(pygame.K_F5)], DT)
            self.assertEqual(g.profile.tokens, before + 10)


class HudAndLabelTests(HubTest):
    def test_every_room_hints_the_bag_and_only_its_own_controls(self):
        rooms = [self.hub.room(r) for r in ROOM_IDS]
        for room in rooms:
            texts = [t for row in room.hint_rows for t, _ in row]
            self.assertIn("BAG", texts, room.room_id)               # inventory is global, so the hint is too
            self.assertIn("MOVE: WASD", texts)
            self.assertEqual(len(room.hint_rows), 3)                # still small
        self.assertIn("PLAY", [t for row in self.hub.room("arcade_floor").hint_rows for t, _ in row])
        for room in (self.home, self.hub.room("prize_plaza")):
            self.assertIn("INTERACT", [t for row in room.hint_rows for t, _ in row])
        self.assertEqual(len({id(r.hud) for r in rooms}), 1)

    def test_inventory_really_opens_in_every_room(self):
        self.frames(3, [key(pygame.K_ESCAPE)])
        for room_id in ROOM_IDS:
            room = goto_room(self.game, room_id)
            self.frames(2, [key(pygame.K_i)])
            self.assertIsNotNone(room.inventory_ui, room_id)
            self.frames(2, [key(pygame.K_ESCAPE)])
            self.assertIsNone(room.inventory_ui)

    def test_room_title_shows_on_entering_and_fades(self):
        self.assertTrue(self.home.title.age is not None)
        self.frames(30)
        self.assertGreater(self.home.title.alpha(), 0)
        self.frames(int((ROOM_TITLE_TIME + 1) / DT))
        self.assertEqual(self.home.title.alpha(), 0)
        self.assertFalse(self.home.title.visible)
        self.dismiss_popup()
        arcade = self.walk_through(pygame.K_a, "arcade_floor")
        self.assertIsNotNone(arcade.title.age)
        self.assertEqual(arcade.title.image.get_size()[0] > 0, True)

    def test_titles_are_the_room_names(self):
        names = {r: self.hub.room(r).theme.name for r in ROOM_IDS}
        self.assertEqual(names, {"home": "HOME", "arcade_floor": "ARCADE FLOOR",
                                 "prize_plaza": "PRIZE PLAZA"})

    def test_all_rooms_draw(self):
        for room_id in ROOM_IDS:
            room = goto_room(self.game, room_id)
            self.frames(5)
            room.draw(self.game.canvas)

    def test_prize_plaza_has_no_cats_arcade_has_one(self):
        self.assertEqual(len(self.hub.room("prize_plaza").cats), 0)
        self.assertEqual([c.name for c in self.hub.room("arcade_floor").cats], ["Pixel"])
        self.assertEqual(len(self.hub.room("home").cats), len(CATS) - 1)


class TransitionRegressionTests(HubTest):
    def test_spawn_is_exactly_the_matching_entry_after_each_hop(self):
        from room_scene import ENTRIES
        self.dismiss_popup()
        for door_key, target, entry in ((pygame.K_a, "arcade_floor", "right"), (pygame.K_d, "home", "left"),
                                        (pygame.K_d, "prize_plaza", "left"), (pygame.K_a, "home", "right")):
            room = self.walk_through(door_key, target)
            self.assertEqual(self.current_id(), target)
            self.assertTrue(abs(room.player.x - ENTRIES[entry][0][0]) < 60)
            self.assertAlmostEqual(room.player.y, ENTRIES[entry][0][1], delta=2)
            self.assert_valid_position(room)

    def test_inventory_closes_when_leaving_the_arcade(self):
        arcade = goto_room(self.game, "arcade_floor")
        self.frames(2, [key(pygame.K_i)])
        self.assertIsNotNone(arcade.inventory_ui)
        self.assertTrue(self.hub.travel(arcade, arcade.exits[0]))
        self.settle()
        self.assertIsNone(arcade.inventory_ui)
        self.assertIsNone(self.home.inventory_ui)

    def test_machine_interaction_does_not_leak_between_rooms(self):
        arcade = goto_room(self.game, "arcade_floor")
        machine = arcade.machines[0]
        arcade.player.x, arcade.player.y = machine.rect.centerx, machine.rect.bottom + 12
        self.frames(5)
        self.frames(1, [key(pygame.K_e)])                         # E-flash running
        self.assertIsNotNone(arcade.activating)
        self.assertTrue(self.hub.travel(arcade, arcade.exits[0]))
        self.settle()
        self.assertIsNone(arcade.activating)
        self.assertIsNone(arcade.nearby)
        self.assertFalse(machine.highlight)
        self.assertEqual(machine.flash_time, 0.0)
        self.assertIsNone(self.home.dialogue)                     # nothing opened in HOME
        self.frames(60)
        self.assertIsNone(self.home.dialogue)
        self.assertEqual(self.game.profile.tokens, 10)

    def test_ambience_follows_the_room(self):
        class FakeSound:
            volume = None

            def set_volume(self, v):
                self.volume = v

        amb = self.hub.ambience
        amb.sounds = {n: FakeSound() for n in ("machine_hum", "arcade_buzz", "rain")}
        seen = {}
        for room_id in ("arcade_floor", "home", "prize_plaza"):
            room = goto_room(self.game, room_id)
            seen[room_id] = {n: s.volume for n, s in amb.sounds.items()}
            self.assertEqual(amb.mix, room.ambience_mix)
        self.assertGreater(seen["arcade_floor"]["machine_hum"], seen["home"]["machine_hum"])
        self.assertGreater(seen["home"]["rain"], 0)
        self.assertEqual(seen["arcade_floor"]["rain"], 0.0)          # the rain stays in HOME
        self.assertEqual(seen["prize_plaza"]["rain"], 0.0)

    def test_every_ambience_mix_names_real_layers(self):
        from ambience import LAYERS
        for room_id in ROOM_IDS:
            self.assertLessEqual(set(self.hub.room(room_id).ambience_mix), set(LAYERS))

    def test_no_production_module_can_teleport_between_rooms(self):
        here = os.path.dirname(os.path.abspath(__file__))
        for fname in os.listdir(here):
            if fname.endswith(".py") and not fname.startswith("test_") and fname != "room_testing.py":
                with open(os.path.join(here, fname)) as f:
                    self.assertNotIn("room_testing", f.read(), fname)


class CatPersistenceTests(HubTest):
    def test_each_cat_lives_in_exactly_one_room_and_is_never_recreated(self):
        self.dismiss_popup()
        rooms = {r: self.hub.room(r) for r in ROOM_IDS}
        identity = {r: [id(c) for c in room.cats] for r, room in rooms.items()}
        names = [c.name for room in rooms.values() for c in room.cats]
        self.assertEqual(sorted(names), sorted(d["name"] for d in CATS))
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(len({id(c) for room in rooms.values() for c in room.cats}), len(names))
        for target in ("arcade_floor", "home", "prize_plaza", "home", "arcade_floor", "home"):
            cur = self.game.scenes.current
            self.hub.travel(cur, next(e for e in cur.exits if e.target == target))
            self.settle()
        self.assertEqual(identity, {r: [id(c) for c in room.cats] for r, room in rooms.items()})
        self.assertEqual(sorted(c.name for room in rooms.values() for c in room.cats), sorted(names))

    def test_cats_keep_their_place_and_personality_across_trips(self):
        self.dismiss_popup()
        pixel = self.hub.room("arcade_floor").cats.get("pixel")
        pixel.x, pixel.y = 200.0, 128.0
        pixel.set_state(CatState.SIT, 999)
        before = (pixel.position, pixel.state, pixel.personality, pixel.name, pixel.home)
        for target in ("arcade_floor", "home", "arcade_floor", "home"):
            cur = self.game.scenes.current
            self.hub.travel(cur, next(e for e in cur.exits if e.target == target))
            self.settle()
            if target == "home":
                self.frames(90)
        pixel_after = self.hub.room("arcade_floor").cats.get("pixel")
        self.assertIs(pixel_after, pixel)
        self.assertEqual((pixel.position, pixel.state, pixel.personality, pixel.name, pixel.home), before)

    def test_cats_do_not_walk_between_rooms(self):
        self.dismiss_popup()
        for _ in range(int(20 / DT)):
            self.frames(1)
        for room_id in ROOM_IDS:
            room = self.hub.room(room_id)
            for cat in room.cats:
                self.assertTrue(20 < cat.x < VIEW_W - 20 and 64 < cat.y < 282, (room_id, cat.name))


class ArcadeLayoutTests(unittest.TestCase):
    def definition(self, machine_id, position, **kw):
        return ArcadeMachineDefinition(
            machine_id, kw.get("game_id", machine_id), machine_id.upper(), "A test game.", position,
            kw.get("cost", 1), MachineTheme((255, 0, 0), (0, 255, 0), "space", "TEST"))

    def test_layout_is_built_from_the_machine_data(self):
        layout = ArcadeLayout.from_settings()
        self.assertEqual([d.machine_id for d in layout.definitions], [m["id"] for m in MACHINES])
        machines = layout.build_machines()
        self.assertTrue(all(isinstance(m, ArcadeMachine) for m in machines))
        self.assertEqual([m.rect.topleft for m in machines], [d.position for d in layout.definitions])

    def test_unclaimed_slots_hold_idle_cabinets(self):
        layout = ArcadeLayout.from_settings()
        free = layout.free_slots()
        self.assertEqual(len(free) + len(layout.definitions), len(ARCADE_SLOTS))
        idle = layout.build_idle_cabinets()
        self.assertEqual(len(idle), len(free))
        self.assertTrue(all(isinstance(c, IdleCabinet) for c in idle))

    def test_a_new_machine_only_needs_a_data_entry(self):
        extra = dict(MACHINES[0], id="new_game", name="New Game", slot="island_1", game_id="new_game",
                     play_cost=2)
        del extra["x"]
        with tempfile.TemporaryDirectory() as d:
            layout = ArcadeLayout.from_settings(list(MACHINES) + [extra])
            self.assertEqual(layout.definitions[-1].position, ARCADE_SLOTS["island_1"])
            self.assertEqual(layout.definitions[-1].cost, 2)
            self.assertNotIn("island_1", layout.free_slots())
            new = layout.build_machines()[-1]
            self.assertEqual((new.id, new.game_id, new.play_cost), ("new_game", "new_game", 2))
            self.assertEqual(new.rect.topleft, ARCADE_SLOTS["island_1"])

    def test_the_room_builds_machines_from_the_layout(self):
        d = tempfile.mkdtemp()
        try:
            game = Game(save_path=os.path.join(d, "s.json"))
            extra = dict(MACHINES[0], id="new_game", name="New Game", slot="island_0")
            del extra["x"]
            with mock.patch("arcade_layout.MACHINES", list(MACHINES) + [extra]):
                room = ArcadeFloorScene(game, game.hub)
            self.assertIn("new_game", [m.id for m in room.machines])
            for m in room.machines:                    # new machines collide and are reachable
                self.assertIn(m.footprint, room.solids)
                self.assertIn(m, room.interactables)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_duplicate_ids_or_positions_are_rejected(self):
        a, b = self.definition("a", (36, 30)), self.definition("a", (92, 30))
        with self.assertRaises(ValueError):
            ArcadeLayout([a, b])
        with self.assertRaises(ValueError):
            ArcadeLayout([self.definition("a", (36, 30)), self.definition("b", (36, 30))])

    def test_game_id_defaults_to_the_machine_id_and_drives_the_minigame(self):
        for m in ArcadeLayout.from_settings().build_machines():
            self.assertEqual(m.game_id, m.id)
        data = dict(MACHINES[1], game_id="space_blaster", id="space_blaster_2")
        self.assertEqual(ArcadeMachine(data).game_id, "space_blaster")

    def test_every_slot_is_in_bounds_and_the_machines_do_not_overlap(self):
        rects = [pygame.Rect(x, y, 36, 62) for x, y in ARCADE_SLOTS.values()]
        for i, a in enumerate(rects):
            self.assertTrue(pygame.Rect(20, 20, VIEW_W - 40, 262).contains(a), a)
            for b in rects[i + 1:]:
                self.assertFalse(a.colliderect(b), (a, b))


class DecorationTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "s.json")
        self.profile = PlayerProfile(clock=GameClock(lambda: DAY1))
        self.mgr = HomeDecorationManager(self.profile, HOME_SLOTS, default_catalog())

    def tearDown(self):
        self.mgr.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_every_slot_shows_its_default_to_start_with(self):
        for slot in HOME_SLOTS:
            self.assertEqual(self.mgr.decoration_for(slot.slot_id).decoration_id, slot.default_id)
        self.assertEqual(self.profile.home_decorations, {})

    def test_all_the_planned_slot_kinds_exist(self):
        kinds = {s.slot_type for s in HOME_SLOTS}
        self.assertEqual(kinds, {"wall_poster", "rug", "table_decor", "plant", "neon_sign", "cat_bed"})

    def test_equip_changes_the_decoration_and_the_save(self):
        self.assertTrue(self.mgr.equip("poster_left", "poster_cat"))
        self.assertEqual(self.mgr.decoration_for("poster_left").decoration_id, "poster_cat")
        self.assertEqual(self.profile.home_decorations, {"poster_left": "poster_cat"})
        self.assertEqual(self.profile.to_dict()["home_decorations"], {"poster_left": "poster_cat"})
        self.mgr.reset_slot("poster_left")
        self.assertEqual(self.mgr.decoration_for("poster_left").decoration_id, "poster_cassette")

    def test_wrong_kind_unknown_or_missing_slot_is_refused(self):
        self.assertFalse(self.mgr.equip("poster_left", "plant_monstera"))       # wrong slot type
        self.assertFalse(self.mgr.equip("poster_left", "nope"))
        self.assertFalse(self.mgr.equip("no_such_slot", "poster_cat"))
        self.assertEqual(self.profile.home_decorations, {})

    def test_a_decoration_too_big_for_the_slot_is_refused(self):
        big = DecorationDefinition("huge_poster", "Huge", WALL_POSTER, lambda: pygame.Surface((80, 80)))
        catalog = default_catalog()
        catalog.register(big)
        mgr = HomeDecorationManager(self.profile, HOME_SLOTS, catalog)
        self.assertFalse(mgr.equip("poster_left", "huge_poster"))
        mgr.close()

    def test_a_stale_saved_choice_falls_back_to_the_default(self):
        self.profile.set_home_decoration("poster_left", "removed_in_a_later_version")
        self.profile.set_home_decoration("rug", "plant_monstera")
        self.assertEqual(self.mgr.decoration_for("poster_left").decoration_id, "poster_cassette")
        self.assertEqual(self.mgr.decoration_for("rug").decoration_id, "rug_lounge")

    def test_props_and_the_change_callback(self):
        calls = []
        self.mgr.on_change = lambda: calls.append(1)
        n = len(self.mgr.props)
        self.assertEqual(n, sum(1 for s in HOME_SLOTS if s.slot_type in ("plant", "table_decor", "cat_bed")))
        self.mgr.equip("plant_back", "plant_bushy")
        self.assertEqual(calls, [1])
        self.assertEqual(len(self.mgr.props), n)
        self.mgr.equip("plant_back", "plant_bushy")           # no change: no rebuild
        self.assertEqual(calls, [1])

    def test_decorations_survive_save_and_load(self):
        store = ProfileStore(self.path, GameClock(lambda: DAY1))
        profile = store.load()
        store.autosave(profile)
        mgr = HomeDecorationManager(profile, HOME_SLOTS, default_catalog())
        mgr.equip("cat_bed_left", "bed_blue")
        mgr.equip("neon_sign", "neon_heart")
        mgr.close()
        again = ProfileStore(self.path, GameClock(lambda: DAY1)).load()
        mgr2 = HomeDecorationManager(again, HOME_SLOTS, default_catalog())
        self.assertEqual(mgr2.decoration_for("cat_bed_left").decoration_id, "bed_blue")
        self.assertEqual(mgr2.decoration_for("neon_sign").decoration_id, "neon_heart")
        mgr2.close()

    def test_old_saves_without_decoration_fields_still_load(self):
        old = {"version": 2, "tokens": 14, "tickets": 21, "high_scores": {"retro_racer": 90},
               "inventory": {"cat_sticker": 1}}
        with open(self.path, "w") as f:
            json.dump(old, f)
        profile = ProfileStore(self.path, GameClock(lambda: DAY1)).load()
        self.assertEqual((profile.tokens, profile.tickets, profile.high_score("retro_racer")), (14, 21, 90))
        self.assertEqual(profile.home_decorations, {})
        self.assertTrue(profile.inventory.has_item("cat_sticker"))

    def test_bad_decoration_data_in_a_save_is_ignored(self):
        for bad in ("oops", [1, 2], {"a": 3}, {1: "x"}, None):
            p = PlayerProfile.from_dict({"home_decorations": bad})
            self.assertEqual(p.home_decorations, {})

    def test_bad_definitions_are_rejected(self):
        with self.assertRaises(ValueError):
            DecorationDefinition("x", "X", "ceiling_fan", lambda: pygame.Surface((1, 1)))
        with self.assertRaises(ValueError):
            DecorationDefinition("x", "X", NEON_SIGN, lambda: pygame.Surface((1, 1)))      # no colours
        with self.assertRaises(ValueError):
            DecorationSlot("s", "ceiling_fan", (0, 0), (1, 1), "x")
        catalog = DecorationCatalog([DecorationDefinition("a", "A", PLANT, lambda: pygame.Surface((4, 4)))])
        with self.assertRaises(ValueError):
            catalog.register(DecorationDefinition("a", "A2", PLANT, lambda: pygame.Surface((4, 4))))
        with self.assertRaises(ValueError):                    # a default that does not fit its slot
            HomeDecorationManager(self.profile, [DecorationSlot("s", CAT_BED, (0, 0), (9, 9), "a")], catalog)

    def test_swapping_a_solid_decoration_updates_the_rooms_collision(self):
        d = tempfile.mkdtemp()
        try:
            game = Game(save_path=os.path.join(d, "s.json"))
            home = game.scenes.current
            plant_props = [p for p in home.decorations.props if p.solid]
            self.assertTrue(plant_props)
            for p in plant_props:
                self.assertIn(p.footprint, home.solids)
            n = len(home.solids)
            self.assertTrue(home.decorations.equip("plant_back", "plant_bushy"))
            self.assertEqual(len(home.solids), n)
            self.assertIs(home.cats.room_solids, home.solids)      # cats see the same collision list
            for p in home.decorations.props:
                self.assertIn(p, home.props)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class ExitGeometryTests(unittest.TestCase):
    def test_triggers_are_inside_the_doorway_and_zones_cover_them(self):
        for side in ("left", "right"):
            door = RoomExit(side, "home", "left")
            self.assertEqual((door.trigger.top, door.trigger.height), (SIDE_DOOR_Y, SIDE_DOOR_H))
            self.assertTrue(door.zone.contains(door.trigger))


if __name__ == "__main__":
    unittest.main()
