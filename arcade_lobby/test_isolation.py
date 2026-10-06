"""Multiplayer isolation / ownership / clarity tests: input routing, Retro Racer
control isolation, spectators, neutral world displays, modal ownership, the
join flow and result ownership.

Run with:  python -m unittest test_isolation
"""
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from arcade_floor import HighScorePlates  # noqa: E402
from controls import P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS  # noqa: E402
from daily_tasks import DailyTaskManager  # noqa: E402
from input_router import InputRouter, PlayerInput  # noqa: E402
from item_registry import FREE_PLAY_COUPON  # noqa: E402
from local_session import LocalSession  # noqa: E402
from minigame import PlayerResult  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from rewards import PlaySession, RewardBundle, RewardService  # noqa: E402
from retro_racer_scene import RACER_KEYS, RetroRacerScene  # noqa: E402
from room_testing import goto_room  # noqa: E402
from scenes import MinigamePlaceholderScene, minigame_definition  # noqa: E402
from stations import ChanceStation, DailyBoard  # noqa: E402
from test_multiplayer import DAY1, DT, TwoPlayerTest, key  # noqa: E402


def up(k):
    return key(k, down=False)


def tasks(profile, *specs):
    profile._tasks = DailyTaskManager(pool=specs, count=len(specs))
    profile._tasks.ensure_current(DAY1, random.Random(1))


def progress(profile):
    return {t.id: t.progress for t in profile.daily_tasks}


GAME_TASKS = (
    {"id": "played", "description": "PLAY", "event": "game_played", "target": 5, "reward": 1},
    {"id": "tickets", "description": "TICKETS", "event": "tickets_earned", "target": 50, "reward": 1},
    {"id": "coupon", "description": "COUPON", "event": "coupon_used", "target": 5, "reward": 1},
    {"id": "best", "description": "BEST", "event": "high_score", "target": 5, "reward": 1},
    {"id": "pet", "description": "PET", "event": "cat_petted", "target": 5, "reward": 1},
)


class RouterTests(unittest.TestCase):
    def test_a_player_input_only_sees_its_own_keys_as_actions(self):
        p1, p2 = PlayerInput(P1_CONTROLS), PlayerInput(P2_CONTROLS)
        self.assertEqual(p1.action(key(pygame.K_w)), "up")
        self.assertIsNone(p1.action(key(pygame.K_UP)))
        self.assertEqual(p2.action(key(pygame.K_UP)), "up")
        self.assertIsNone(p2.action(key(pygame.K_w)))
        self.assertEqual(p1.action(key(pygame.K_e)), "interact")
        self.assertEqual(p2.action(key(pygame.K_RETURN)), "interact")
        self.assertEqual(p2.action(key(pygame.K_o)), "menu")
        self.assertEqual(p2.action(key(pygame.K_RSHIFT)), "item")
        self.assertEqual(p1.action(key(pygame.K_SPACE)), "item")
        self.assertEqual(PlayerInput(SOLO_CONTROLS).action(key(pygame.K_p)), "pause")

    def test_escape_is_the_one_shared_back_key(self):
        for scheme in (P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS):
            self.assertEqual(PlayerInput(scheme).action(key(pygame.K_ESCAPE)), "back")

    def test_held_state_follows_only_the_owners_events(self):
        p1, p2 = PlayerInput(P1_CONTROLS), PlayerInput(P2_CONTROLS)
        for ev in (key(pygame.K_w), key(pygame.K_UP), key(pygame.K_d), key(pygame.K_LEFT)):
            p1.feed(ev)
            p2.feed(ev)
        self.assertTrue(p1.held("up") and p1.held("right"))
        self.assertFalse(p1.held("left"))
        self.assertEqual(p1.axis("left", "right"), 1)
        self.assertTrue(p2.held("up") and p2.held("left"))
        self.assertEqual(p2.axis("left", "right"), -1)
        p1.feed(up(pygame.K_w))
        self.assertFalse(p1.held("up"))
        self.assertTrue(p2.held("up"))
        p2.feed(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(p2.held("up") or p2.held("left"))

    def test_the_router_sends_each_key_to_its_player(self):
        s = LocalSession([PlayerProfile(profile_id="a", display_name="A"),
                          PlayerProfile(profile_id="b", display_name="B")])
        router = InputRouter(s)
        self.assertEqual(router.route(key(pygame.K_w)), (s.players[0], "up"))
        self.assertEqual(router.route(key(pygame.K_DOWN)), (s.players[1], "down"))
        self.assertEqual(router.route(key(pygame.K_o)), (s.players[1], "menu"))
        self.assertEqual(router.route(key(pygame.K_F5)), (None, None))
        self.assertEqual(router.route(up(pygame.K_w)), (None, None))
        self.assertIsNot(router.input_for(s.players[0]), router.input_for(s.players[0]))
        self.assertIs(s.input.session, s)


class RetroIsolationTests(TwoPlayerTest):
    def start_racer(self, starter, other):
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        self.stand_at(starter, machine)
        self.stand_at(other, machine, dx=-150)
        self.frames(5)
        self.use(starter)
        self.frames(1, [key(starter.controls.interact[0])])      # PLAY
        for _ in range(60):
            self.frames(1)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, RetroRacerScene)
        return room, scene

    def load(self, scene):
        for _ in range(400):                                      # the first visit builds the racer
            self.frames(1)
            if scene.racer is not None:
                break
        self.assertIsNotNone(scene.racer, scene.error)
        self.frames(3)

    def test_retro_racer_stays_one_player(self):
        d = minigame_definition("retro_racer")
        self.assertEqual((d.min_players, d.max_players), (1, 1))

    def test_the_dialogue_says_one_player_and_who_spectates(self):
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        self.stand_at(self.p1, machine)
        self.stand_at(self.p2, machine, dx=-150)
        self.frames(5)
        self.use(self.p1)
        self.assertEqual(room.dialogue.title, "Retro Racer")
        self.assertIn("1 PLAYER ONLY - P2 SPECTATES", [text for text, _ in room.dialogue.details])
        self.frames(1, [key(pygame.K_ESCAPE)])
        blaster = self.machine(room, "space_blaster")
        self.stand_at(self.p1, blaster)
        self.frames(5)
        self.use(self.p1)
        self.assertIn("1-2 PLAYERS", [text for text, _ in room.dialogue.details])

    def test_the_adapter_maps_only_the_starters_keys(self):
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        scene = RetroRacerScene(self.game, machine)
        scene.attach_players([self.p1], [self.p2])
        self.assertEqual(scene.racer_event(key(pygame.K_w)).key, pygame.K_UP)
        self.assertEqual(scene.racer_event(key(pygame.K_e)).key, pygame.K_RETURN)
        self.assertEqual(scene.racer_event(key(pygame.K_SPACE)).key, pygame.K_SPACE)
        self.assertEqual(scene.racer_event(key(pygame.K_i)).key, pygame.K_p)
        for p2_key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN,
                       pygame.K_RCTRL, pygame.K_o, pygame.K_RSHIFT):
            self.assertIsNone(scene.racer_event(key(p2_key)), p2_key)
        self.assertEqual(scene.racer_event(key(pygame.K_ESCAPE)).key, pygame.K_ESCAPE)   # shared back
        self.assertIsNone(scene.racer_event(key(pygame.K_F1)))                           # no tuner

    def test_p2_starting_the_racer_uses_p2_controls_only(self):
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        scene = RetroRacerScene(self.game, machine)
        scene.attach_players([self.p2], [self.p1])
        self.assertEqual(scene.racer_event(key(pygame.K_UP)).key, pygame.K_UP)
        self.assertEqual(scene.racer_event(key(pygame.K_RETURN)).key, pygame.K_RETURN)
        self.assertEqual(scene.racer_event(key(pygame.K_o)).key, pygame.K_p)
        self.assertEqual(scene.racer_event(key(pygame.K_RSHIFT)).key, pygame.K_SPACE)
        for p1_key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_e, pygame.K_i, pygame.K_SPACE):
            self.assertIsNone(scene.racer_event(key(p1_key)), p1_key)

    def test_steering_comes_from_the_starters_held_keys_not_the_global_keyboard(self):
        room = self.arcade()
        scene = RetroRacerScene(self.game, self.machine(room, "retro_racer"))
        scene.attach_players([self.p1], [self.p2])
        for k in (pygame.K_UP, pygame.K_LEFT, pygame.K_DOWN):       # P2 holds everything
            scene.racer_event(key(k))
        self.assertEqual(scene.racer_controls(), {"accelerate": False, "brake": False, "steer": 0})
        scene.racer_event(key(pygame.K_w))
        scene.racer_event(key(pygame.K_d))
        self.assertEqual(scene.racer_controls(), {"accelerate": True, "brake": False, "steer": 1})
        scene.racer_event(up(pygame.K_w))
        self.assertFalse(scene.racer_controls()["accelerate"])
        scene2 = RetroRacerScene(self.game, self.machine(room, "retro_racer"))
        scene2.attach_players([self.p2], [self.p1])
        for k in (pygame.K_w, pygame.K_a):
            scene2.racer_event(key(k))
        self.assertEqual(scene2.racer_controls()["steer"], 0)
        scene2.racer_event(key(pygame.K_LEFT))
        self.assertEqual(scene2.racer_controls()["steer"], -1)

    def test_the_racer_never_reads_the_global_keyboard(self):
        room = self.arcade()
        scene = RetroRacerScene(self.game, self.machine(room, "retro_racer"))
        scene.attach_players([self.p1], [self.p2])
        calls = []
        real = pygame.key.get_pressed
        pygame.key.get_pressed = lambda: calls.append(1) or real()
        try:
            scene.racer_event(key(pygame.K_w))
            scene.racer_controls()
        finally:
            pygame.key.get_pressed = real
        self.assertEqual(calls, [])

    def test_in_the_real_racer_p1_keys_work_and_p2_keys_do_not(self):
        room, scene = self.start_racer(self.p1, self.p2)
        self.load(scene)
        state = scene.racer.state
        self.frames(1, [key(pygame.K_RETURN), key(pygame.K_UP), key(pygame.K_RCTRL)])   # P2's keys
        self.frames(3)
        self.assertEqual(scene.racer.state, state)
        self.frames(1, [key(pygame.K_e)])                         # P1's confirm
        self.frames(3)
        self.assertNotEqual(scene.racer.state, state)
        self.assertEqual(self.a.tokens, self.P1_TOKENS - 1)
        self.assertEqual(self.b.tokens, self.P2_TOKENS)

    def test_in_the_real_racer_p2_can_drive_when_p2_started_it(self):
        room, scene = self.start_racer(self.p2, self.p1)
        self.load(scene)
        state = scene.racer.state
        self.frames(1, [key(pygame.K_e), key(pygame.K_w)])        # P1's keys
        self.frames(3)
        self.assertEqual(scene.racer.state, state)
        self.frames(1, [key(pygame.K_RETURN)])
        self.frames(3)
        self.assertNotEqual(scene.racer.state, state)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS - 1))


class SpectatorTests(TwoPlayerTest):
    def play_puzzle(self, starter, other):
        room = self.arcade()
        machine = self.machine(room, "puzzle_drop")
        self.stand_at(starter, machine)
        self.stand_at(other, machine, dx=-150)
        self.frames(5)
        self.use(starter)
        self.frames(1, [key(starter.controls.interact[0])])
        self.play_through_wipe()
        return room, self.game.scenes.current

    def test_the_scene_knows_who_plays_and_who_watches(self):
        room, scene = self.play_puzzle(self.p1, self.p2)
        self.assertEqual(scene.players, [self.p1])
        self.assertEqual(scene.spectators, [self.p2])
        self.assertEqual(scene.participants, [self.a])

    def test_a_quiet_spectating_tag_is_drawn(self):
        room, scene = self.play_puzzle(self.p1, self.p2)
        canvas = pygame.Surface((400, 300))
        scene.draw(canvas)
        before = pygame.image.tobytes(canvas, "RGB")
        scene.draw_overlay(canvas)
        self.assertNotEqual(pygame.image.tobytes(canvas, "RGB"), before)
        alone = MinigamePlaceholderScene(self.game, self.machine(room, "puzzle_drop"))
        canvas.fill((0, 0, 0))
        alone.draw_overlay(canvas)                                 # nobody spectating: nothing drawn
        self.assertEqual(pygame.image.tobytes(canvas, "RGB").count(b"\x00"), 400 * 300 * 3)
        self.assertIn("SPECTATING", f"{self.p2.tag} - SPECTATING")

    def test_the_game_scene_is_spectator_aware_in_the_manager_draw(self):
        room, scene = self.play_puzzle(self.p1, self.p2)
        self.frames(2)                                             # SceneManager.draw runs the overlay

    def test_spectator_keys_do_nothing_but_esc_still_leaves(self):
        room, scene = self.play_puzzle(self.p1, self.p2)
        pos = (self.p2.avatar.x, self.p2.avatar.y)
        for k in (pygame.K_LEFT, pygame.K_RETURN, pygame.K_o, pygame.K_RSHIFT):
            self.frames(1, [key(k)])
        self.frames(20)
        self.assertIs(self.game.scenes.current, scene)
        self.assertEqual((self.p2.avatar.x, self.p2.avatar.y), pos)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS - 1, self.P2_TOKENS))
        self.esc_out_of_game(room)                                 # the explicit global back rule

    def test_the_spectator_pays_nothing_and_gets_no_reward(self):
        room, scene = self.play_puzzle(self.p2, self.p1)           # P2 plays, P1 watches
        self.esc_out_of_game(room)
        self.assertEqual((self.a.tokens, self.a.tickets, self.a.total_games_played), (self.P1_TOKENS, 0, 0))
        self.assertEqual((self.b.tokens, self.b.tickets, self.b.total_games_played),
                         (self.P2_TOKENS - 1, 5, 1))
        self.assertEqual((self.a.lifetime_tickets_earned, self.a.lifetime_tokens_spent), (0, 0))

    def test_the_spectators_daily_tasks_do_not_progress(self):
        for p in (self.a, self.b):
            tasks(p, *GAME_TASKS)
        room, scene = self.play_puzzle(self.p1, self.p2)
        self.esc_out_of_game(room)
        mine, theirs = progress(self.a), progress(self.b)
        self.assertEqual((mine["played"], mine["tickets"]), (1, 5))
        self.assertEqual(set(theirs.values()), {0})

    def test_a_coupon_play_counts_for_the_player_only(self):
        for p in (self.a, self.b):
            tasks(p, *GAME_TASKS)
        RewardService.grant_item(self.a, FREE_PLAY_COUPON)
        RewardService.grant_item(self.b, FREE_PLAY_COUPON)
        room = self.arcade()
        machine = self.machine(room, "puzzle_drop")
        self.stand_at(self.p1, machine)
        self.stand_at(self.p2, machine, dx=-150)
        self.frames(5)
        self.use(self.p1)
        self.frames(1, [key(pygame.K_e)])
        self.frames(30)
        self.frames(1, [key(pygame.K_e)])                          # YES, use the coupon
        self.play_through_wipe()
        self.esc_out_of_game(room)
        self.assertEqual(progress(self.a)["coupon"], 1)
        self.assertEqual(progress(self.b)["coupon"], 0)
        self.assertEqual(self.b.inventory.get_quantity(FREE_PLAY_COUPON), 1)

    def test_a_beaten_high_score_belongs_to_whoever_scored(self):
        for p in (self.a, self.b):
            tasks(p, *GAME_TASKS)
        PlaySession(self.a, "puzzle_drop", 1).settle_result(PlayerResult(self.a.profile_id, 900, RewardBundle()))
        self.assertEqual(progress(self.a)["best"], 1)
        self.assertEqual(progress(self.b)["best"], 0)
        self.assertEqual(self.b.high_score("puzzle_drop"), 0)

    def test_chance_games_have_spectators_too(self):
        plaza = goto_room(self.game, "prize_plaza")
        self.quiet_cats(plaza)
        wheel = next(p for p in plaza.props if isinstance(p, ChanceStation))
        self.stand_at(self.p2, wheel)
        self.p2.avatar.y = float(wheel.zone.bottom - 2)
        self.stand_at(self.p1, wheel, dx=-150)
        self.frames(5)
        self.use(self.p2)
        for _ in range(50):
            self.frames(1)
        scene = self.game.scenes.current
        self.assertEqual(scene.spectators, [self.p1])
        self.frames(1, [key(pygame.K_e), key(pygame.K_d)])        # the spectator's keys: ignored
        self.assertEqual(self.a.tokens, self.P1_TOKENS)
        self.assertEqual(self.b.tokens, self.P2_TOKENS)


class NeutralWorldTests(TwoPlayerTest):
    def test_the_daily_board_looks_the_same_whatever_the_profiles_have_done(self):
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        self.assertFalse(hasattr(board, "profile"))

        def render():
            surf = pygame.Surface((400, 300))
            board.time = 0.9
            board.draw(surf)
            return pygame.image.tobytes(surf, "RGB")

        before = render()
        for t in self.a.daily_tasks:                              # P1 finishes everything
            t.progress  # noqa: B018 (read only)
        for spec in (self.a, self.b):
            tasks(spec, *GAME_TASKS)
        self.a._tasks.on_event("game_played", 9)
        self.a._tasks.on_event("cat_petted", 9)
        self.assertTrue(self.a.claimable_tasks)
        self.assertEqual(render(), before)

    def test_the_board_animates_on_its_own(self):
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        frames = set()
        for t in (0.0, 1.0, 2.0, 3.0):
            surf = pygame.Surface((400, 300))
            board.time = t
            board.draw(surf)
            frames.add(pygame.image.tobytes(surf, "RGB"))
        self.assertGreater(len(frames), 1)

    def test_the_panel_still_shows_the_players_own_progress(self):
        self.dismiss_popups()
        tasks(self.a, *GAME_TASKS)
        tasks(self.b, *GAME_TASKS)
        self.b._tasks.on_event("cat_petted", 2)
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        self.quiet_cats(self.home)
        self.p2.avatar.x, self.p2.avatar.y = board.zone.centerx, board.zone.bottom - 2
        self.p1.avatar.x, self.p1.avatar.y = 100.0, 250.0
        self.frames(5)
        self.use(self.p2)
        panel = self.home.panel
        self.assertEqual(panel.owner, "P2 BOB")
        self.assertEqual({t.id: t.progress for t in panel.tasks}["pet"], 2)
        self.assertEqual(progress(self.a)["pet"], 0)

    def test_plates_name_the_owner_of_the_score(self):
        self.a.record_score("retro_racer", 1200)
        self.b.record_score("retro_racer", 5200)
        room = self.arcade()
        plates = room.plates
        self.assertEqual(plates.best("retro_racer"), (5200, "BOB"))
        self.assertEqual(plates.best("puzzle_drop"), (0, ""))          # nobody: no name, dashes
        self.b.record_score("retro_racer", 100)                        # (not a record)
        self.a.record_score("retro_racer", 9000)
        self.assertEqual(plates.best("retro_racer"), (9000, "ALICE"))
        machine = self.machine(room, "retro_racer")
        one = plates._plate(machine, 5200, "BOB")
        two = plates._plate(machine, 5200, "ALICE")
        self.assertNotEqual(pygame.image.tobytes(one, "RGB"), pygame.image.tobytes(two, "RGB"))
        surf = pygame.Surface((400, 300))
        plates.draw(surf)

    def test_a_one_player_plate_still_shows_that_profiles_best_with_its_name(self):
        p = PlayerProfile(profile_id="x", display_name="Solo")
        p.record_score("retro_racer", 4200)
        plates = HighScorePlates([], p)
        self.assertEqual(plates.best("retro_racer"), (4200, "SOLO"))

    def test_home_says_whose_home_it_is_and_marks_the_guest(self):
        self.assertEqual(self.home.title_subtitle(), "ALICE'S HOME")
        self.assertEqual(self.p1.avatar.tag_note, "")
        self.assertEqual(self.p2.avatar.tag_note, "GUEST")
        arcade = self.arcade()
        self.assertIsNone(arcade.title_subtitle())
        self.assertEqual(self.p2.avatar.tag_note, "")
        self.home.title.show()
        self.home.draw(pygame.Surface((400, 300)))

    def test_hints_are_compact_and_name_both_players(self):
        rows = self.home.build_hint_rows()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][1][0], "WASD / E / I")
        self.assertEqual(rows[1][1][0], "ARROWS / ENTER / O")
        self.assertEqual((rows[0][0][0], rows[1][0][0]), ("P1", "P2"))

    def test_the_machine_dialogue_names_the_player_count(self):
        room = self.arcade()
        lines = {}
        for machine_id in ("retro_racer", "space_blaster"):
            machine = self.machine(room, machine_id)
            self.stand_at(self.p1, machine)
            self.stand_at(self.p2, machine, dx=-150)
            self.frames(5)
            self.use(self.p1)
            lines[machine_id] = room.dialogue
            self.assertIsNotNone(room.dialogue)
            self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertIsNotNone(lines["retro_racer"])


class ModalOwnershipTests(TwoPlayerTest):
    """Every window records who opened it, and only that player's keys drive it."""

    def open_inventory(self, player):
        self.frames(1, [key(player.controls.inventory[0])])
        return self.home.inventory_ui

    def test_each_modal_records_its_owner_and_ignores_the_other_players_keys(self):
        self.dismiss_popups()
        RewardService.grant_item(self.a, "cat_sticker")
        RewardService.grant_item(self.b, "cat_sticker")
        for owner, other in ((self.p1, self.p2), (self.p2, self.p1)):
            ui = self.open_inventory(owner)
            self.assertIs(self.home.modal_owner, owner.avatar)
            before = (ui.selected, ui.inspecting, ui.tab, ui.closed)
            for k in [k for k in other.controls.keys if k != other.controls.inventory[0]]:
                self.frames(1, [key(k)])
            self.assertEqual((ui.selected, ui.inspecting, ui.tab, ui.closed), before)
            self.frames(1, [key(pygame.K_ESCAPE)])
            self.frames(3)
            self.assertIsNone(self.home.modal)

    def test_machine_dialogues_belong_to_the_starter(self):
        room = self.arcade()
        machine = self.machine(room, "space_blaster")
        for starter, other in ((self.p1, self.p2), (self.p2, self.p1)):
            self.stand_at(starter, machine)
            self.stand_at(other, machine, dx=-150)
            self.frames(5)
            self.use(starter)
            dialogue = room.dialogue
            self.assertIs(room.modal_owner, starter.avatar)
            for k in (other.controls.interact[0], *other.controls.move):
                self.frames(1, [key(k)])
            self.assertIs(room.dialogue, dialogue)
            self.assertEqual(dialogue.selected, 0)
            self.assertFalse(dialogue.closed)
            self.frames(1, [key(pygame.K_ESCAPE)])
            self.assertIsNone(room.dialogue)

    def test_the_coupon_and_players_prompts_keep_their_owner(self):
        RewardService.grant_item(self.b, FREE_PLAY_COUPON)
        room = self.arcade()
        machine = self.machine(room, "space_blaster")
        self.stand_at(self.p2, machine)
        self.stand_at(self.p1, machine, dx=-150)
        self.frames(5)
        self.use(self.p2)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(room.dialogue.title, "COUPON")
        self.assertIs(room.modal_owner, self.p2.avatar)
        self.frames(30)
        self.frames(1, [key(pygame.K_e), key(pygame.K_s)])          # P1's keys: nothing
        self.assertEqual((room.dialogue.title, room.dialogue.selected), ("COUPON", 0))
        self.frames(1, [key(pygame.K_DOWN)])
        self.frames(1, [key(pygame.K_RETURN)])                        # NO: pay tokens
        self.assertEqual(room.dialogue.title, "PLAYERS")
        self.assertIs(room.modal_owner, self.p2.avatar)
        self.frames(1, [key(pygame.K_s), key(pygame.K_e)])
        self.assertEqual(room.dialogue.title, "PLAYERS")
        self.assertEqual(room.dialogue.selected, 0)

    def test_the_daily_panel_and_popups_belong_to_their_players(self):
        self.frames(3)
        popup = self.home.popup
        self.assertIs(self.home.modal_owner, popup.player)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertFalse(popup.claimed)                                # P1's popup, P2's key
        self.frames(1, [key(pygame.K_e)])
        self.assertTrue(popup.claimed)
        self.frames(60)
        self.assertIs(self.home.modal_owner, self.p2.avatar)           # P2's popup next
        self.frames(1, [key(pygame.K_e)])
        self.assertFalse(self.home.popup.claimed)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(self.b.tokens, self.P2_TOKENS + 5)

    def test_every_modal_creation_path_sets_an_owner(self):
        self.dismiss_popups()
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        for who in (self.p1, self.p2):
            self.home.acting_player = who.avatar
            self.home.open_task_panel()
            self.assertIs(self.home.modal_owner, who.avatar)
            self.assertIs(self.home._modal_owner, who.avatar)
            self.home.panel = None
        self.home.acting_player = None
        self.assertIsNotNone(board)

    def test_the_lucky_corner_belongs_to_the_player_who_walked_up(self):
        plaza = goto_room(self.game, "prize_plaza")
        self.quiet_cats(plaza)
        wheel = next(p for p in plaza.props if isinstance(p, ChanceStation))
        self.stand_at(self.p1, wheel)
        self.p1.avatar.y = float(wheel.zone.bottom - 2)
        self.stand_at(self.p2, wheel, dx=-150)
        self.frames(5)
        self.use(self.p1)
        for _ in range(50):
            self.frames(1)
        scene = self.game.scenes.current
        self.assertIs(scene.player, self.p1)
        self.frames(1, [key(pygame.K_RETURN), key(pygame.K_RCTRL)])
        self.assertEqual(self.b.tokens, self.P2_TOKENS)
        self.assertEqual(scene.round.phase, scene.round.IDLE)
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(self.a.tokens, self.P1_TOKENS - 1)

    def test_the_other_player_cannot_replace_an_open_window(self):
        self.dismiss_popups()
        first = self.open_inventory(self.p1)
        self.frames(1, [key(pygame.K_o)])
        self.assertIs(self.home.inventory_ui, first)
        self.assertIs(self.home.modal_owner, self.p1.avatar)


class JoinFlowTests(TwoPlayerTest):
    def start_join(self, starter, other):
        room = self.arcade()
        blaster = self.machine(room, "space_blaster")
        self.stand_at(starter, blaster)
        self.stand_at(other, blaster, dx=-150)
        self.frames(5)
        self.use(starter)
        self.frames(1, [key(starter.controls.interact[0])])         # PLAY
        self.frames(1, [key(next(k for k, v in starter.controls.move.items() if v == (0, 1)))])
        self.frames(1, [key(starter.controls.interact[0])])         # 2 PLAYERS
        return room

    def test_the_join_prompt_shows_ready_and_the_joiners_key(self):
        room = self.start_join(self.p1, self.p2)
        prompt = room.dialogue
        self.assertEqual(type(prompt).__name__, "JoinPrompt")
        self.assertIs(room.modal_owner, self.p1.avatar)
        prompt.draw(pygame.Surface((400, 300)))
        self.assertEqual(prompt.joiner, self.p2)
        self.assertEqual(prompt.joiner.controls.interact_hint, "ENTER")
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS))

    def test_nobody_is_charged_until_the_second_player_joins(self):
        room = self.start_join(self.p1, self.p2)
        for _ in range(120):
            self.frames(1)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS))
        self.assertIsNone(room.active_play)
        self.frames(1, [key(pygame.K_RETURN)])                       # P2 joins
        self.play_through_wipe()
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS - 1, self.P2_TOKENS - 1))
        self.esc_out_of_game(room)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS - 1, self.P2_TOKENS - 1))   # once

    def test_cancelling_the_join_charges_nobody(self):
        room = self.start_join(self.p1, self.p2)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertIsNone(room.dialogue)
        self.assertIsNone(room.active_play)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS))

    def test_the_starters_own_key_does_not_join_them(self):
        room = self.start_join(self.p1, self.p2)
        self.frames(1, [key(pygame.K_e), key(pygame.K_SPACE), key(pygame.K_i)])
        self.assertIsNotNone(room.dialogue)
        self.assertIsNone(room.active_play)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS))

    def test_p2_starting_lets_p1_join_with_p1s_key(self):
        room = self.start_join(self.p2, self.p1)
        self.assertEqual(room.dialogue.joiner, self.p1)
        self.frames(1, [key(pygame.K_RETURN)])                       # the starter's key: no
        self.assertIsNone(room.active_play)
        self.frames(1, [key(pygame.K_e)])
        self.play_through_wipe()
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS - 1, self.P2_TOKENS - 1))
        self.assertEqual([p.profile for p, _ in room.active_plays], [self.b, self.a])


class ResultOwnershipTests(TwoPlayerTest):
    def play_two(self):
        room = self.arcade()
        blaster = self.machine(room, "space_blaster")
        self.stand_at(self.p1, blaster)
        self.stand_at(self.p2, blaster, dx=-150)
        self.frames(5)
        self.use(self.p1)
        self.frames(1, [key(pygame.K_e)])
        self.frames(1, [key(pygame.K_s)])
        self.frames(1, [key(pygame.K_e)])
        self.frames(1, [key(pygame.K_RETURN)])
        self.play_through_wipe()
        return room

    def test_a_two_player_game_reports_both_players_in_the_real_flow(self):
        room = self.arcade()
        shown = []
        room.notice.show = lambda title, lines=(), color=None, duration=None: shown.append(list(lines))
        blaster = self.machine(room, "space_blaster")
        self.stand_at(self.p1, blaster)
        self.stand_at(self.p2, blaster, dx=-150)
        self.frames(5)
        self.use(self.p1)
        self.frames(1, [key(pygame.K_e)])
        self.frames(1, [key(pygame.K_s)])
        self.frames(1, [key(pygame.K_e)])
        self.frames(1, [key(pygame.K_RETURN)])
        self.play_through_wipe()
        self.esc_out_of_game(room)
        self.assertEqual([t for t, _ in shown[-1]], ["P1 ALICE", "+5 TICKETS", "P2 BOB", "+5 TICKETS"])
        self.assertEqual((self.a.tickets, self.b.tickets), (5, 5))

    def test_the_result_card_names_both_players_with_their_own_scores(self):
        room = self.arcade()
        shown = []
        room.notice.show = lambda title, lines=(), color=None, duration=None: shown.append((title, list(lines)))
        blaster = self.machine(room, "space_blaster")
        sa = PlaySession(self.a, "space_blaster", 1)
        sb = PlaySession(self.b, "space_blaster", 1)
        scene = type("S", (), {"failed": False, "get_result": lambda s: type("R", (), {
            "player_results": (PlayerResult(self.a.profile_id, 700, RewardBundle(tickets=7)),
                               PlayerResult(self.b.profile_id, 300, RewardBundle(tickets=3))),
            "for_profile": lambda self_, pid: {self.a.profile_id: PlayerResult(self.a.profile_id, 700, RewardBundle(tickets=7)),
                                               self.b.profile_id: PlayerResult(self.b.profile_id, 300, RewardBundle(tickets=3))}[pid]})()})()
        room.active_play = (sa, scene)
        room.active_plays = [(self.p1.avatar, sa), (self.p2.avatar, sb)]
        room._end_play(ran=True)
        title, lines = shown[0]
        texts = [t for t, _ in lines]
        self.assertEqual(title, "GAME COMPLETE")
        self.assertEqual(texts, ["P1 ALICE", "SCORE 700  +7 TICKETS", "P2 BOB", "SCORE 300  +3 TICKETS"])
        self.assertEqual((self.a.tickets, self.b.tickets), (7, 3))
        self.assertEqual((self.a.high_score("space_blaster"), self.b.high_score("space_blaster")), (700, 300))
        self.assertIsNotNone(blaster)

    def test_a_one_player_game_reports_only_the_active_player(self):
        room = self.arcade()
        shown = []
        room.notice.show = lambda title, lines=(), color=None, duration=None: shown.append(list(lines))
        machine = self.machine(room, "puzzle_drop")
        self.stand_at(self.p2, machine)
        self.stand_at(self.p1, machine, dx=-150)
        self.frames(5)
        self.use(self.p2)
        self.frames(1, [key(pygame.K_RETURN)])
        self.play_through_wipe()
        self.esc_out_of_game(room)
        texts = [t for lines in shown for t, _ in lines]
        self.assertEqual(texts, ["P2 BOB", "+5 TICKETS"])
        self.assertEqual((self.a.tickets, self.b.tickets), (0, 5))

    def test_a_one_player_session_result_is_unchanged(self):
        import tempfile
        from game import Game
        from scenes import create_minigame_scene
        with tempfile.TemporaryDirectory() as d:
            g = Game(save_path=os.path.join(d, "s.json"))
            room = goto_room(g, "arcade_floor")
            shown = []
            room.notice.show = lambda title, lines=(), color=None, duration=None: shown.append(list(lines))
            machine = next(m for m in room.machines if m.id == "puzzle_drop")
            room.active_play = (machine.start_play(g.profile), create_minigame_scene(g, machine))
            room._end_play(ran=True)
            self.assertEqual([t for t, _ in shown[0]], ["+5 TICKETS"])
            self.assertEqual(g.profile.tickets, 5)


class ProfileSelectPolishTests(unittest.TestCase):
    def setUp(self):
        import shutil
        import tempfile
        from game_clock import GameClock
        from profile_manager import ProfileManager
        from game import Game
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.m = ProfileManager(os.path.join(self.dir, "s"), clock=GameClock(lambda: DAY1))
        self.ids = {n: self.m.create_profile(n).profile_id for n in ("A", "B", "C", "D", "E", "F", "G", "H", "I")}
        self.game = Game(profiles=self.m)

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def go(self, *keys):
        for k in keys:
            self.frames(1, [key(k)])
            self.frames(50)

    def test_recent_profiles_come_first_and_are_highlighted(self):
        self.m.record_session([self.m.load_profile(self.ids["G"])], 1)
        self.m.record_session([self.m.load_profile(self.ids["C"])], 1)
        self.game.scenes.stack.clear()
        from menus import StartupFlow
        flow = StartupFlow(self.game, self.m)
        flow.begin()
        flow.count = 1
        flow.choose_count(1)
        self.frames(50)
        sel = self.game.scenes.current
        self.assertEqual([i.display_name for i in sel.infos][:3], ["C", "G", "A"])
        self.assertEqual(sel.selected_info.display_name, "C")

    def test_end_reaches_new_profile_and_up_from_the_top_wraps_to_it(self):
        self.go(pygame.K_RETURN, pygame.K_RETURN)
        sel = self.game.scenes.current
        self.frames(1, [key(pygame.K_END)])
        self.assertTrue(sel.on_new_profile)
        self.assertLess(sel.selected, sel.top + 6)
        self.frames(1, [key(pygame.K_HOME)])
        self.assertEqual((sel.selected, sel.top), (0, 0))
        self.frames(1, [key(pygame.K_UP)])
        self.assertTrue(sel.on_new_profile)
        self.frames(1, [key(pygame.K_PAGEUP)])
        self.assertEqual(sel.selected, sel.total - 1 - 6)
        self.assertTrue(sel.top <= sel.selected < sel.top + 6)

    def test_p1s_profile_is_visibly_unavailable_to_p2(self):
        self.go(pygame.K_RETURN, pygame.K_DOWN, pygame.K_RETURN)
        sel = self.game.scenes.current
        first = sel.selected_info.profile_id
        self.go(pygame.K_RETURN)
        p2 = self.game.scenes.current
        self.assertIn(first, p2.taken)
        p2.selected = next(i for i, info in enumerate(p2.infos) if info.profile_id == first)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertIn("ALREADY", p2.message)
        self.frames(1, [key(pygame.K_DELETE)])
        self.assertIsNone(p2.dialog)
        surf = pygame.Surface((400, 300))
        p2.draw(surf)


if __name__ == "__main__":
    unittest.main()
