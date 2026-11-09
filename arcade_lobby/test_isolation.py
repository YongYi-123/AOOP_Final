"""Single-player input / ownership / clarity tests: input routing, Retro Racer control mapping, the one-player
minigame flow, neutral world displays, modal ownership, result display and the profile screen.

Run with:  python -m unittest test_isolation
"""
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from arcade_floor import HighScorePlates  # noqa: E402
from controls import SOLO_CONTROLS  # noqa: E402
from daily_tasks import DailyTaskManager  # noqa: E402
from input_router import InputRouter, PlayerInput  # noqa: E402
from item_registry import FREE_PLAY_COUPON  # noqa: E402
from local_session import LocalSession  # noqa: E402
from minigame import PlayerResult  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from rewards import PlaySession, RewardBundle, RewardService  # noqa: E402
from retro_racer_scene import RetroRacerScene  # noqa: E402
from room_testing import goto_room, with_placeholder_minigame  # noqa: E402
from scenes import MinigamePlaceholderScene, minigame_definition  # noqa: E402
from stations import ChanceStation, DailyBoard  # noqa: E402
from test_single_player import DAY1, DT, SoloTest, key  # noqa: E402


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
    def test_a_player_input_reads_the_solo_keys_as_actions(self):
        p = PlayerInput(SOLO_CONTROLS)
        self.assertEqual(p.action(key(pygame.K_w)), "up")
        self.assertEqual(p.action(key(pygame.K_UP)), "up")
        self.assertEqual(p.action(key(pygame.K_e)), "interact")
        self.assertEqual(p.action(key(pygame.K_RETURN)), "interact")
        self.assertEqual(p.action(key(pygame.K_i)), "menu")
        self.assertEqual(p.action(key(pygame.K_SPACE)), "item")
        self.assertEqual(p.action(key(pygame.K_p)), "pause")
        for old_p2_key in (pygame.K_o, pygame.K_RCTRL, pygame.K_RSHIFT, pygame.K_KP0):
            self.assertIsNone(p.action(key(old_p2_key)))

    def test_escape_is_the_back_key(self):
        self.assertEqual(PlayerInput(SOLO_CONTROLS).action(key(pygame.K_ESCAPE)), "back")

    def test_held_state_follows_the_players_events(self):
        p = PlayerInput(SOLO_CONTROLS)
        for ev in (key(pygame.K_w), key(pygame.K_d), key(pygame.K_o)):
            p.feed(ev)
        self.assertTrue(p.held("up") and p.held("right"))
        self.assertFalse(p.held("left"))
        self.assertEqual(p.axis("left", "right"), 1)
        p.feed(up(pygame.K_w))
        self.assertFalse(p.held("up"))
        p.feed(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(p.held("right"))

    def test_the_router_sends_the_key_to_the_one_player(self):
        s = LocalSession(PlayerProfile(profile_id="a", display_name="A"))
        router = InputRouter(s)
        self.assertEqual(router.route(key(pygame.K_w)), (s.primary, "up"))
        self.assertEqual(router.route(key(pygame.K_DOWN)), (s.primary, "down"))
        self.assertEqual(router.route(key(pygame.K_i)), (s.primary, "menu"))
        self.assertEqual(router.route(key(pygame.K_o)), (None, None))        # nobody's key
        self.assertEqual(router.route(key(pygame.K_F5)), (None, None))
        self.assertEqual(router.route(up(pygame.K_w)), (None, None))
        self.assertIsNot(router.input_for(s.primary), router.input_for(s.primary))
        self.assertIs(s.input.session, s)


class RetroInputTests(SoloTest):
    def start_racer(self):
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])                        # PLAY
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

    def test_retro_racer_is_a_one_player_game(self):
        d = minigame_definition("retro_racer")
        self.assertFalse(hasattr(d, "max_players"))

    def test_the_dialogue_has_no_player_count_or_spectator_line(self):
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        self.assertEqual(room.dialogue.title, "Retro Racer")
        texts = [text for text, _ in room.dialogue.details]
        self.assertEqual(texts, [f"COST: {machine.cost_label}", f"TOKENS: {self.TOKENS}"])
        self.assertFalse(any("PLAYER" in t or "SPECTAT" in t for t in texts))

    def test_the_adapter_maps_the_players_keys(self):
        room = self.arcade()
        scene = RetroRacerScene(self.game, self.machine(room, "retro_racer"))
        scene.attach_players([self.player])
        self.assertEqual(scene.racer_event(key(pygame.K_w)).key, pygame.K_UP)
        self.assertEqual(scene.racer_event(key(pygame.K_UP)).key, pygame.K_UP)
        self.assertEqual(scene.racer_event(key(pygame.K_e)).key, pygame.K_RETURN)
        self.assertEqual(scene.racer_event(key(pygame.K_SPACE)).key, pygame.K_SPACE)
        self.assertEqual(scene.racer_event(key(pygame.K_i)).key, pygame.K_p)
        for old_p2_key in (pygame.K_o, pygame.K_RCTRL, pygame.K_RSHIFT):
            self.assertIsNone(scene.racer_event(key(old_p2_key)), old_p2_key)
        self.assertEqual(scene.racer_event(key(pygame.K_ESCAPE)).key, pygame.K_ESCAPE)
        self.assertIsNone(scene.racer_event(key(pygame.K_F1)))                           # no tuner

    def test_steering_comes_from_the_held_keys_not_the_global_keyboard(self):
        room = self.arcade()
        scene = RetroRacerScene(self.game, self.machine(room, "retro_racer"))
        scene.attach_players([self.player])
        self.assertEqual(scene.racer_controls(), {"accelerate": False, "brake": False, "steer": 0})
        scene.racer_event(key(pygame.K_w))
        scene.racer_event(key(pygame.K_d))
        self.assertEqual(scene.racer_controls(), {"accelerate": True, "brake": False, "steer": 1})
        scene.racer_event(up(pygame.K_w))
        self.assertFalse(scene.racer_controls()["accelerate"])
        scene.racer_event(key(pygame.K_LEFT))
        scene.racer_event(up(pygame.K_d))
        self.assertEqual(scene.racer_controls()["steer"], -1)

    def test_the_racer_never_reads_the_global_keyboard(self):
        room = self.arcade()
        scene = RetroRacerScene(self.game, self.machine(room, "retro_racer"))
        scene.attach_players([self.player])
        calls = []
        real = pygame.key.get_pressed
        pygame.key.get_pressed = lambda: calls.append(1) or real()
        try:
            scene.racer_event(key(pygame.K_w))
            scene.racer_controls()
        finally:
            pygame.key.get_pressed = real
        self.assertEqual(calls, [])

    def test_in_the_real_racer_the_players_keys_work_and_the_old_p2_keys_do_not(self):
        room, scene = self.start_racer()
        self.load(scene)
        state = scene.racer.state
        self.frames(1, [key(pygame.K_RCTRL), key(pygame.K_o), key(pygame.K_RSHIFT)])
        self.frames(3)
        self.assertEqual(scene.racer.state, state)
        self.frames(1, [key(pygame.K_e)])                         # the confirm key
        self.frames(3)
        self.assertNotEqual(scene.racer.state, state)
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        self.bob_is_untouched()
        self.assertFalse(hasattr(scene, "spectators"))
        self.assertFalse(hasattr(scene, "_draw_spectators"))


@with_placeholder_minigame
class OnePlayerGameTests(SoloTest):
    def play_puzzle(self):
        room = self.arcade()
        machine = self.machine(room, "puzzle_drop")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])
        self.play_through_wipe()
        return room, self.game.scenes.current

    def test_the_scene_knows_its_one_player(self):
        room, scene = self.play_puzzle()
        self.assertEqual(scene.players, [self.player])
        self.assertEqual(scene.participants, [self.a])

    def test_nothing_spectating_is_drawn(self):
        room, scene = self.play_puzzle()
        self.assertFalse(hasattr(scene, "draw_overlay"))
        self.frames(2)

    def test_the_old_second_player_keys_do_nothing_but_esc_leaves(self):
        room, scene = self.play_puzzle()
        for k in (pygame.K_RCTRL, pygame.K_o, pygame.K_RSHIFT, pygame.K_KP0):
            self.frames(1, [key(k)])
        self.frames(20)
        self.assertIs(self.game.scenes.current, scene)
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        self.esc_out_of_game(room)

    def test_only_the_playing_profile_pays_and_is_rewarded(self):
        room, scene = self.play_puzzle()
        self.esc_out_of_game(room)
        self.assertEqual((self.a.tokens, self.a.tickets, self.a.total_games_played), (self.TOKENS - 1, 5, 1))
        self.bob_is_untouched()
        self.assertEqual(self.b.lifetime_tickets_earned, 0)

    def test_daily_tasks_progress_for_the_player_only(self):
        for p in (self.a, self.b):
            tasks(p, *GAME_TASKS)
        room, scene = self.play_puzzle()
        self.esc_out_of_game(room)
        mine, theirs = progress(self.a), progress(self.b)
        self.assertEqual((mine["played"], mine["tickets"]), (1, 5))
        self.assertEqual(set(theirs.values()), {0})

    def test_a_coupon_play_counts_for_the_player(self):
        for p in (self.a, self.b):
            tasks(p, *GAME_TASKS)
        RewardService.grant_item(self.a, FREE_PLAY_COUPON)
        RewardService.grant_item(self.b, FREE_PLAY_COUPON)
        room = self.arcade()
        machine = self.machine(room, "puzzle_drop")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])
        self.frames(30)
        self.frames(1, [key(pygame.K_e)])                          # YES, use the coupon
        self.play_through_wipe()
        self.esc_out_of_game(room)
        self.assertEqual(progress(self.a)["coupon"], 1)
        self.assertEqual(progress(self.b)["coupon"], 0)
        self.assertEqual(self.a.inventory.get_quantity(FREE_PLAY_COUPON), 0)
        self.assertEqual(self.b.inventory.get_quantity(FREE_PLAY_COUPON), 1)

    def test_a_beaten_high_score_belongs_to_whoever_scored(self):
        for p in (self.a, self.b):
            tasks(p, *GAME_TASKS)
        PlaySession(self.a, "puzzle_drop", 1).settle_result(PlayerResult(self.a.profile_id, 900, RewardBundle()))
        self.assertEqual(progress(self.a)["best"], 1)
        self.assertEqual(progress(self.b)["best"], 0)
        self.assertEqual(self.b.high_score("puzzle_drop"), 0)

    def test_chance_games_have_no_spectators(self):
        plaza = goto_room(self.game, "prize_plaza")
        self.quiet_cats(plaza)
        wheel = next(p for p in plaza.props if isinstance(p, ChanceStation))
        self.stand_at(wheel)
        self.player.avatar.y = float(wheel.zone.bottom - 2)
        self.frames(5)
        self.use()
        for _ in range(50):
            self.frames(1)
        scene = self.game.scenes.current
        self.assertIs(scene.player, self.player)
        self.assertFalse(hasattr(scene, "spectators"))
        self.frames(1, [key(pygame.K_RCTRL), key(pygame.K_o)])    # old P2 keys: nothing
        self.assertEqual(self.a.tokens, self.TOKENS)
        self.assertEqual(scene.round.phase, scene.round.IDLE)
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        self.bob_is_untouched()


class NeutralWorldTests(SoloTest):
    def test_the_daily_board_looks_the_same_whatever_the_profile_has_done(self):
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        self.assertFalse(hasattr(board, "profile"))

        def render():
            surf = pygame.Surface((400, 300))
            board.time = 0.9
            board.draw(surf)
            return pygame.image.tobytes(surf, "RGB")

        before = render()
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

    def test_the_panel_shows_the_players_own_progress(self):
        self.dismiss_popups()
        tasks(self.a, *GAME_TASKS)
        tasks(self.b, *GAME_TASKS)
        self.a._tasks.on_event("cat_petted", 2)
        board = next(p for p in self.home.props if isinstance(p, DailyBoard))
        self.quiet_cats(self.home)
        self.player.avatar.x, self.player.avatar.y = board.zone.centerx, board.zone.bottom - 2
        self.frames(5)
        self.use()
        panel = self.home.panel
        self.assertIsNone(panel.owner)
        self.assertEqual({t.id: t.progress for t in panel.tasks}["pet"], 2)
        self.assertEqual(progress(self.b)["pet"], 0)

    def test_plates_show_the_playing_profiles_best(self):
        self.a.record_score("retro_racer", 1200)
        self.b.record_score("retro_racer", 5200)                 # Bob is not playing: his score is not shown
        room = self.arcade()
        plates = room.plates
        self.assertEqual(plates.best("retro_racer"), (1200, "ALICE"))
        self.assertEqual(plates.best("puzzle_drop"), (0, ""))          # nobody: no name, dashes
        self.a.record_score("retro_racer", 9000)
        self.assertEqual(plates.best("retro_racer"), (9000, "ALICE"))
        machine = self.machine(room, "retro_racer")
        one = plates._plate(machine, 5200, "BOB")
        two = plates._plate(machine, 5200, "ALICE")
        self.assertNotEqual(pygame.image.tobytes(one, "RGB"), pygame.image.tobytes(two, "RGB"))
        plates.draw(pygame.Surface((400, 300)))

    def test_a_plate_shows_that_profiles_best_with_its_name(self):
        p = PlayerProfile(profile_id="x", display_name="Solo")
        p.record_score("retro_racer", 4200)
        plates = HighScorePlates([], p)
        self.assertEqual(plates.best("retro_racer"), (4200, "SOLO"))

    def test_home_has_no_guest_marker_or_owner_subtitle(self):
        self.assertIsNone(self.home.title_subtitle())
        self.home.title.show()
        self.home.draw(pygame.Surface((400, 300)))

    def test_the_hints_are_the_rooms_own_rows(self):
        rows = self.home.build_hint_rows()
        self.assertEqual(rows, self.home.hint_rows)
        flat = " ".join(text for row in rows for text, _ in row)
        self.assertNotIn("P1", flat)
        self.assertNotIn("P2", flat)


class ModalOwnershipTests(SoloTest):
    """Every window records who opened it (the one player) and the player's keys drive it."""

    def test_the_bag_records_its_owner(self):
        self.dismiss_popups()
        RewardService.grant_item(self.a, "cat_sticker")
        self.frames(1, [key(pygame.K_i)])
        ui_ = self.home.inventory_ui
        self.assertIs(self.home.modal_owner, self.player.avatar)
        before = (ui_.selected, ui_.inspecting, ui_.tab, ui_.closed)
        for k in (pygame.K_o, pygame.K_RCTRL, pygame.K_RSHIFT):    # old second-player keys: no effect
            self.frames(1, [key(k)])
        self.assertEqual((ui_.selected, ui_.inspecting, ui_.tab, ui_.closed), before)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(3)
        self.assertIsNone(self.home.modal)

    def test_machine_dialogues_belong_to_the_player(self):
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        dialogue = room.dialogue
        self.assertIs(room.modal_owner, self.player.avatar)
        for k in (pygame.K_RCTRL, pygame.K_o):
            self.frames(1, [key(k)])
        self.assertIs(room.dialogue, dialogue)
        self.assertEqual(dialogue.selected, 0)
        self.assertFalse(dialogue.closed)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertIsNone(room.dialogue)

    def test_the_coupon_prompt_keeps_its_owner_and_goes_straight_to_the_game(self):
        RewardService.grant_item(self.a, FREE_PLAY_COUPON)
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(room.dialogue.title, "COUPON")
        self.assertIs(room.modal_owner, self.player.avatar)
        self.frames(30)
        self.frames(1, [key(pygame.K_DOWN)])
        self.frames(1, [key(pygame.K_RETURN)])                        # NO: pay tokens
        self.assertIsNone(room.dialogue)                              # no "PLAYERS" question follows
        self.assertIsNotNone(room.active_play)
        self.assertEqual(self.a.tokens, self.TOKENS - 1)

    def test_the_daily_popup_and_panel_belong_to_the_player(self):
        self.frames(3)
        popup = self.home.popup
        self.assertIs(self.home.modal_owner, popup.player)
        self.assertIs(popup.player, self.player.avatar)
        self.frames(1, [key(pygame.K_o)])                              # not a key of the game
        self.assertFalse(popup.claimed)
        self.frames(1, [key(pygame.K_e)])
        self.assertTrue(popup.claimed)
        self.frames(60)
        self.assertEqual(self.a.tokens, self.TOKENS + 5)
        self.assertIsNone(self.home.popup)

    def test_every_modal_creation_path_sets_an_owner(self):
        self.dismiss_popups()
        self.home.open_task_panel()
        self.assertIs(self.home.modal_owner, self.player.avatar)
        self.assertIs(self.home._modal_owner, self.player.avatar)

    def test_the_lucky_corner_belongs_to_the_player(self):
        plaza = goto_room(self.game, "prize_plaza")
        self.quiet_cats(plaza)
        wheel = next(p for p in plaza.props if isinstance(p, ChanceStation))
        self.stand_at(wheel)
        self.player.avatar.y = float(wheel.zone.bottom - 2)
        self.frames(5)
        self.use()
        for _ in range(50):
            self.frames(1)
        scene = self.game.scenes.current
        self.assertIs(scene.player, self.player)
        self.frames(1, [key(pygame.K_RCTRL)])
        self.assertEqual(scene.round.phase, scene.round.IDLE)
        self.frames(1, [key(pygame.K_e)])
        self.assertEqual(self.a.tokens, self.TOKENS - 1)

    def test_a_second_window_cannot_replace_an_open_one(self):
        self.dismiss_popups()
        self.frames(1, [key(pygame.K_i)])
        first = self.home.inventory_ui
        self.frames(1, [key(pygame.K_i)])
        self.assertIs(self.home.inventory_ui, first)
        self.assertIs(self.home.modal_owner, self.player.avatar)


@with_placeholder_minigame
class ResultCardTests(SoloTest):
    def test_the_result_lists_only_the_tickets(self):
        room = self.arcade()
        shown = []
        room.notice.show = lambda title, lines=(), color=None, duration=None: shown.append(list(lines))
        machine = self.machine(room, "puzzle_drop")
        self.stand_at(machine)
        self.frames(5)
        self.use()
        self.frames(1, [key(pygame.K_e)])
        self.play_through_wipe()
        self.esc_out_of_game(room)
        texts = [t for lines in shown for t, _ in lines]
        self.assertEqual(texts, ["+5 TICKETS"])
        self.assertEqual(self.a.tickets, 5)
        self.bob_is_untouched()

    def test_a_scored_result_is_paid_and_recorded_for_the_player(self):
        room = self.arcade()
        shown = []
        room.notice.show = lambda title, lines=(), color=None, duration=None: shown.append((title, list(lines)))
        machine = self.machine(room, "puzzle_drop")
        session = PlaySession(self.a, "puzzle_drop", 1)
        result = PlayerResult(self.a.profile_id, 700, RewardBundle(tickets=7))
        scene = type("S", (), {"failed": False, "get_result": lambda s: type("R", (), {
            "player_results": (result,), "for_profile": lambda self_, pid: result})()})()
        room.active_play = (session, scene)
        room._end_play(ran=True)
        title, lines = shown[0]
        self.assertEqual(title, "GAME COMPLETE")
        self.assertEqual([t for t, _ in lines], ["+7 TICKETS"])
        self.assertEqual(self.a.tickets, 7)
        self.assertEqual(self.a.high_score("puzzle_drop"), 700)
        self.assertIsNotNone(machine)

    def test_a_game_that_could_not_start_is_refunded(self):
        room = self.arcade()
        machine = self.machine(room, "puzzle_drop")
        session = machine.start_play(self.a)
        self.assertEqual(self.a.tokens, self.TOKENS - 1)
        room.active_play = (session, type("S", (), {"failed": True})())
        room._end_play(ran=True)
        self.assertEqual(self.a.tokens, self.TOKENS)
        self.assertTrue(room.notice.visible)

    def test_a_plain_save_file_result_is_unchanged(self):
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
        self.m.record_session(self.m.load_profile(self.ids["G"]))
        self.m.record_session(self.m.load_profile(self.ids["C"]))
        self.game.scenes.stack.clear()
        from menus import StartupFlow
        flow = StartupFlow(self.game, self.m)
        flow.begin()
        flow.show_profile_select()
        self.frames(50)
        sel = self.game.scenes.current
        self.assertEqual([i.display_name for i in sel.infos][:3], ["C", "G", "A"])
        self.assertEqual(sel.selected_info.display_name, "C")

    def test_end_reaches_new_profile_and_up_from_the_top_wraps_to_it(self):
        self.go(pygame.K_RETURN)                                # TITLE -> PROFILE SELECT
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

    def test_every_profile_can_be_picked_or_deleted_there_is_no_in_use_state(self):
        self.go(pygame.K_RETURN)
        sel = self.game.scenes.current
        self.assertEqual(sel.title, "SELECT PROFILE")
        self.assertFalse(hasattr(sel, "taken"))
        self.assertFalse(hasattr(sel, "slot"))
        self.frames(1, [key(pygame.K_DELETE)])
        self.assertIsNotNone(sel.dialog)                        # a delete confirmation (NO by default)
        surf = pygame.Surface((400, 300))
        sel.draw(surf)


if __name__ == "__main__":
    unittest.main()
