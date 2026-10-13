"""LUCKY CAT PINBALL inside the Arcade Hub: the Lucky Corner cabinet, launching, the scene's
controls (solo, P1, P2), pause / exit, saving and crash recovery, audio and rendering.
Run headless from this folder:   python -m unittest test_pinball_integration
"""
import json
import os
import shutil
import tempfile
import unittest
from datetime import date
from unittest.mock import Mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import pinball as pb  # noqa: E402
from controls import P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS  # noqa: E402
from display import compute_layout  # noqa: E402
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from local_session import LocalSession  # noqa: E402
from pinball_scene import PinballScene  # noqa: E402
from prize_plaza import LUCKY_POS, PrizePlazaScene  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import PINBALL_DAILY_TICKET_CAP, VIEW_H, VIEW_W  # noqa: E402
from stations import CoinPusherStation, PinballStation, SoonStation  # noqa: E402

DT = 1 / 60
DAY1 = date(2026, 3, 10)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def release(k):
    return pygame.event.Event(pygame.KEYUP, key=k, mod=0)


def drain_now(scene):
    """Put the ball over the drain line (the physics is covered in test_pinball)."""
    w = scene.table.world
    w.phase, w.bx, w.by, w.vx, w.vy = "play", 60.0, pb.DRAIN_Y + 1, 0.0, 40.0


class HubBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")
        self.game = Game(save_path=self.path, clock=GameClock(lambda: DAY1))
        self.frames(3, [key(pygame.K_ESCAPE)])
        self.frames(3, [key(pygame.K_ESCAPE)])
        self.game.profile.add_tokens(30, "TEST")
        self.start_tokens = self.game.profile.tokens

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def plaza(self):
        room = goto_room(self.game, "prize_plaza")
        for cat in room.cats:
            cat.x, cat.y = 100.0, 120.0
        return room

    def station(self, room):
        return next(p for p in room.props if isinstance(p, PinballStation))

    def open_machine(self):
        room = self.plaza()
        station = self.station(room)
        room.player.x, room.player.y = station.zone.centerx, station.zone.bottom - 2
        self.frames(5)
        self.assertIs(room.nearby, station)
        self.frames(30, [key(pygame.K_e)])
        self.frames(40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, PinballScene)
        return room, scene

    def start_run(self):
        room, scene = self.open_machine()
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(1, [release(pygame.K_SPACE)])
        self.assertTrue(scene.table.live)
        return room, scene

    def finish_run(self, scene, score):
        scene.table.world.score = score
        for _ in range(3):
            drain_now(scene)
            self.frames(1)
            self.frames(int((pb.BONUS_TIME + 0.2) * 60))


class LuckyCornerTests(HubBase):
    def test_the_last_soon_bay_became_lucky_cat_pinball_next_to_the_coin_pusher(self):
        room = self.plaza()
        pinball = self.station(room)
        self.assertEqual(pinball.rect.topleft, (LUCKY_POS[0] + 40, LUCKY_POS[1] + 70))
        self.assertEqual([p for p in room.props if isinstance(p, SoonStation)], [])
        pusher = next(p for p in room.props if isinstance(p, CoinPusherStation))
        self.assertEqual(pusher.rect.topleft, (LUCKY_POS[0], LUCKY_POS[1] + 70))             # the coin pusher did not move
        self.assertEqual(pinball.prompt_label, "PLAY LUCKY CAT PINBALL")
        self.assertEqual(sorted(p.prompt_label for p in room.interactables if hasattr(p, "kind")),
                         ["PLAY COIN PUSHER", "PLAY HI-LO", "PLAY LUCKY CAT PINBALL", "PLAY NEON 21", "PLAY SPIN"])

    def test_it_is_interactable_solid_and_leaves_a_walkable_gap(self):
        room = self.plaza()
        pinball = self.station(room)
        self.assertIn(pinball, room.interactables)
        self.assertIn(pinball.footprint, room.solids)
        for other in room.props:
            if other is not pinball and getattr(other, "solid", True):
                self.assertFalse(pinball.footprint.colliderect(other.footprint), type(other).__name__)
        pusher = next(p for p in room.props if isinstance(p, CoinPusherStation))
        self.assertGreaterEqual(pinball.footprint.left - pusher.footprint.right, 8)
        self.assertLessEqual(pinball.rect.right, VIEW_W - 20)
        self.assertLessEqual(pinball.rect.bottom, VIEW_H - 20)

    def test_the_cabinet_matches_the_game_and_its_screen_is_animated(self):
        from lucky_cabinets import KINDS, build_cabinet
        self.assertEqual(KINDS["pinball"]["label"], "PIN")
        sprite = build_cabinet("pinball")
        self.assertEqual(sprite.get_size(), (28, 40))
        others = {pygame.image.tobytes(build_cabinet(k), "RGBA") for k in KINDS if k != "pinball"}
        self.assertNotIn(pygame.image.tobytes(sprite, "RGBA"), others)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        pinball = self.station(self.plaza())
        frames = set()
        for t in (0.0, 0.4, 0.9, 1.3, 2.0, 3.1):
            pinball.time = t
            canvas.fill((0, 0, 0))
            pinball.draw(canvas)
            frames.add(pygame.image.tobytes(canvas.subsurface(pinball.rect), "RGB"))
        self.assertGreater(len(frames), 3)

    def test_walking_up_and_pressing_e_opens_it_for_free_and_the_hub_music_comes_back(self):
        room, scene = self.open_machine()
        self.assertEqual(self.game.profile.tokens, self.start_tokens)               # opening charges nothing
        self.assertEqual(scene.table.state, "idle")
        self.assertEqual(self.game.music_for(self.game.scenes.stack), "lucky_corner")
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        self.assertIsInstance(self.game.scenes.current, PrizePlazaScene)
        self.assertEqual(self.game.profile.tokens, self.start_tokens)
        self.assertTrue(self.game.scenes.current.player.controls.owns(pygame.K_a))   # the room has its controls back

    def test_the_other_lucky_corner_cabinets_still_open_their_own_games(self):
        room = self.plaza()
        for station in room.interactables:
            if getattr(station, "kind", None) in ("spin", "hilo", "neon21", "pusher"):
                self.assertNotIsInstance(station, PinballStation)


class SoloControlTests(HubBase):
    def test_start_costs_one_token_and_mashing_charges_once(self):
        room, scene = self.open_machine()
        self.frames(1, [key(pygame.K_SPACE)] * 6)
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 1)
        self.assertEqual((scene.table.state, scene.table.world.ball_no), ("play", 1))
        self.assertEqual(self.game.profile.pinball_run, {"score": 0, "ball": 1})
        self.frames(1, [release(pygame.K_SPACE)])
        self.frames(10)
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 1)

    def test_e_also_starts_and_a_held_key_does_not_restart(self):
        room, scene = self.open_machine()
        repeat = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode="", repeat=True)
        self.frames(1, [key(pygame.K_e)])
        self.frames(120, [repeat])
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 1)
        self.assertFalse(scene.table.world.pulling)                                 # the starting press does not pull the plunger

    def test_out_of_tokens_charges_nothing_and_says_so(self):
        room, scene = self.open_machine()
        prof = self.game.profile
        prof.spend_tokens(prof.tokens, "TEST")
        self.frames(1, [key(pygame.K_SPACE)] * 3)
        self.assertEqual((prof.tokens, scene.table.state, prof.pinball_run), (0, "idle", None))
        self.assertEqual(scene.alert, "OUT OF TOKENS!")
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        self.frames(120)
        self.assertEqual(prof.tokens, 0)

    def test_holding_launch_pulls_the_plunger_and_releasing_launches_the_ball(self):
        room, scene = self.start_run()
        w = scene.table.world
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(30)
        self.assertGreater(w.pull, 0.3)
        self.assertEqual(w.phase, "ready")                                          # still waiting while held
        self.frames(1, [release(pygame.K_SPACE)])
        self.frames(10)
        self.assertEqual(w.phase, "play")
        self.assertLess(w.vy, 0)
        self.assertEqual(w.pull, 0)
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 1)           # launching is free

    def test_a_and_d_move_the_left_and_right_flippers_and_the_arrows_work_too(self):
        room, scene = self.start_run()
        w = scene.table.world
        left, right = w.flippers[-1], w.flippers[1]
        self.frames(1, [key(pygame.K_a)])
        self.frames(10)
        self.assertGreater(left.raised, 0.9)
        self.assertLess(right.raised, 0.1)
        self.frames(1, [release(pygame.K_a), key(pygame.K_RIGHT)])
        self.frames(10)
        self.assertLess(left.raised, 0.1)
        self.assertGreater(right.raised, 0.9)
        self.frames(1, [release(pygame.K_RIGHT), key(pygame.K_d)])
        self.frames(10)
        self.assertGreater(right.raised, 0.9)
        self.frames(1, [release(pygame.K_d)])
        self.frames(15)
        self.assertLess(right.raised, 0.05)

    def test_a_tap_inside_one_frame_still_flips(self):
        room, scene = self.start_run()
        w = scene.table.world
        self.frames(1, [key(pygame.K_a), release(pygame.K_a)])                      # pressed and released in the same frame
        self.frames(3)
        self.assertGreater(w.flippers[-1].raised, 0.3)

    def test_a_scripted_ball_is_scored_through_the_scene(self):
        room, scene = self.start_run()
        w = scene.table.world
        bx, by = pb.BUMPERS[1]
        w.phase, w.bx, w.by, w.vx, w.vy = "play", bx - pb.BUMPER_R - pb.R + 0.5, by, 60.0, 0.0
        self.frames(6)
        self.assertEqual(w.score, pb.BUMPER_POINTS)
        self.assertTrue(scene.popups)
        self.assertTrue(scene.particles)

    def test_cat_completion_through_the_scene_lights_lucky_cat_mode(self):
        room, scene = self.start_run()
        w = scene.table.world
        w.phase, w.targets = "play", [True, True, False]
        (x0, y0), (x1, y1) = pb.TARGETS[2]
        w.bx, w.by, w.vx, w.vy = x0 - pb.R - 1.0, (y0 + y1) / 2, 80.0, 0.0
        self.frames(6)
        self.assertGreater(w.lucky_left, 10)
        self.assertIn("LUCKY CAT MODE", scene.ticker)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)

    def test_a_drain_loses_a_ball_and_three_drains_end_the_run_with_a_payout(self):
        room, scene = self.start_run()
        w = scene.table.world
        for ball in (1, 2):
            self.assertEqual(w.ball_no, ball)
            drain_now(scene)
            self.frames(2)
            self.assertEqual(w.phase, "bonus")
            self.frames(int((pb.BONUS_TIME + 0.2) * 60))
            self.assertEqual(w.phase, "ready")
        w.score = 12000
        drain_now(scene)
        self.frames(2)
        self.frames(int((pb.BONUS_TIME + 0.2) * 60))
        self.assertEqual(scene.table.state, "result")
        r = scene.table.result
        self.assertEqual((r.tickets, self.game.profile.tickets), (2, 2))
        self.assertIsNone(self.game.profile.pinball_run)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        self.frames(600)
        self.assertEqual(self.game.profile.tickets, 2)                              # exactly once

    def test_play_again_charges_a_second_token_only_when_pressed(self):
        room, scene = self.start_run()
        self.finish_run(scene, 5000)
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 1)
        self.frames(1, [key(pygame.K_SPACE)] * 3)
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 2)
        self.assertEqual((scene.table.state, scene.table.world.ball_no, scene.table.world.score), ("play", 1, 0))

    def test_pause_freezes_resume_continues_and_exit_works_from_pause(self):
        room, scene = self.start_run()
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(1, [release(pygame.K_SPACE)])
        self.frames(30)
        self.frames(1, [key(pygame.K_p)])
        self.assertTrue(scene.paused)
        t = scene.table.world.time
        self.frames(1, [key(pygame.K_SPACE), key(pygame.K_a)])
        self.frames(60)
        self.assertEqual(scene.table.world.time, t)
        self.assertEqual(scene.table.world.flippers[-1].raised, 0)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        self.frames(1, [key(pygame.K_i)])                                            # the bag key is a pause key too
        self.assertFalse(scene.paused)
        self.frames(30)
        self.assertGreater(scene.table.world.time, t)
        self.frames(1, [key(pygame.K_p)])
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        self.assertIsInstance(self.game.scenes.current, PrizePlazaScene)

    def test_escape_during_a_run_pauses_first_and_a_second_escape_cashes_out_and_leaves(self):
        room, scene = self.start_run()
        scene.table.world.score = 11000
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertTrue(scene.paused)
        self.assertIs(self.game.scenes.current, scene)                              # not gone yet
        self.assertEqual(self.game.profile.tickets, 0)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        self.assertIsInstance(self.game.scenes.current, PrizePlazaScene)
        self.assertEqual(self.game.profile.tickets, 2)                              # the score so far paid
        self.assertIsNone(self.game.profile.pinball_run)

    def test_resuming_after_the_leave_prompt_cancels_it(self):
        room, scene = self.start_run()
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(1, [key(pygame.K_p)])
        self.assertFalse(scene.paused)
        self.assertFalse(scene.confirm_leave)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertTrue(scene.paused)                                                # asks again

    def test_the_controls_box_shows_the_real_keys(self):
        room, scene = self.open_machine()
        self.assertEqual(scene.controls_lines(),
                         [("A", "L FLIPPER"), ("D", "R FLIPPER"), ("SPACE/E", "PLUNGER"), ("P", "PAUSE"), ("ESC", "LEAVE")])


class SavingTests(HubBase):
    def test_leaving_mid_run_settles_saves_and_a_restart_does_not_pay_again(self):
        room, scene = self.start_run()
        scene.table.world.score = 26000
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        data = self.saved()
        self.assertEqual((data["tokens"], data["tickets"]), (self.start_tokens - 1, 5))
        self.assertNotIn("run", data["pinball"])
        self.assertEqual(data["high_scores"]["lucky_cat_pinball"], 26000)
        game2 = Game(save_path=self.path, clock=GameClock(lambda: DAY1))
        scene2 = PinballScene(game2, None)
        self.assertEqual((game2.profile.tokens, game2.profile.tickets), (self.start_tokens - 1, 5))
        self.assertIsNone(scene2.table.result)                                      # nothing owed

    def test_reopening_costs_nothing_and_starts_a_clean_idle_machine(self):
        for _ in range(3):
            room, scene = self.open_machine()
            self.assertEqual(scene.table.state, "idle")
            self.frames(1, [key(pygame.K_ESCAPE)])
            self.frames(60)
        self.assertEqual(self.game.profile.tokens, self.start_tokens)

    def test_a_crash_mid_run_keeps_the_token_spent_and_the_next_visit_pays_the_saved_score_once(self):
        room, scene = self.start_run()
        scene.table.world.score = 16000
        drain_now(scene)
        self.frames(3)                                                              # the ball end saved the score; the app "dies" here
        data = self.saved()
        self.assertEqual(data["tokens"], self.start_tokens - 1)
        self.assertEqual(data["pinball"]["run"]["ball"], 2)
        game2 = Game(save_path=self.path, clock=GameClock(lambda: DAY1))
        scene2 = PinballScene(game2, None)
        self.assertTrue(scene2.table.result.recovered)
        self.assertEqual(game2.profile.tickets, 3)
        draw = pygame.Surface((VIEW_W, VIEW_H))
        scene2.draw(draw)                                                           # the recovered run is shown, not replayed
        game3 = Game(save_path=self.path, clock=GameClock(lambda: DAY1))
        self.assertEqual(game3.profile.tickets, 3)
        self.assertIsNone(PinballScene(game3, None).table.result)

    def test_quitting_the_program_with_a_run_open_settles_it_once_and_saves(self):
        room, scene = self.start_run()
        scene.table.world.score = 5200
        self.game.scenes.quit()
        data = self.saved()
        self.assertEqual((data["tokens"], data["tickets"]), (self.start_tokens - 1, 1))
        self.assertNotIn("run", data["pinball"])

    def test_the_daily_cap_applies_through_the_scene(self):
        self.game.profile.award_pinball(PINBALL_DAILY_TICKET_CAP, 0)
        tickets = self.game.profile.tickets
        room, scene = self.start_run()
        self.finish_run(scene, 100000)
        self.assertEqual(self.game.profile.tickets, tickets)
        self.assertTrue(scene.table.result.capped)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)


class TwoPlayerTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.manager = ProfileManager(os.path.join(self.dir, "saves"), clock=GameClock(lambda: DAY1))
        self.a = self.manager.create_profile("Alice")
        self.b = self.manager.create_profile("Bob")
        self.a.add_tokens(10, "SETUP")
        self.b.add_tokens(10, "SETUP")
        self.session = LocalSession([self.a, self.b])
        self.game = Game(session=self.session)
        self.p1, self.p2 = self.session.players
        self.ta, self.tb = self.a.tokens, self.b.tokens

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def scene_for(self, player):
        scene = PinballScene(self.game, player)
        self.game.scenes.push(scene, fade=False)
        return scene

    def test_p1_plays_with_a_d_and_space_p2_only_watches(self):
        scene = self.scene_for(self.p1)
        self.assertEqual(scene.spectators, [self.p2])
        self.frames(1, [key(pygame.K_RETURN), key(pygame.K_RSHIFT), key(pygame.K_KP0), key(pygame.K_RCTRL)])   # P2's keys
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta, self.tb))
        self.assertEqual(scene.table.state, "idle")
        self.frames(1, [key(pygame.K_SPACE)])
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta - 1, self.tb))
        self.frames(1, [release(pygame.K_SPACE)])
        flippers = scene.table.world.flippers
        self.frames(1, [key(pygame.K_LEFT), key(pygame.K_RIGHT)])
        self.frames(15)
        self.assertEqual((flippers[-1].raised, flippers[1].raised), (0, 0))         # P2's arrows do not flip P1's flippers
        self.frames(1, [key(pygame.K_a)])
        self.frames(10)
        self.assertGreater(flippers[-1].raised, 0.9)
        self.assertEqual(flippers[1].raised, 0)
        self.frames(1, [key(pygame.K_RETURN)])                                      # P2's launch key while P1 plays
        self.frames(1, [release(pygame.K_RETURN)])
        self.assertEqual(scene.table.world.phase, "ready")

    def test_p2_plays_with_arrows_and_enter_or_rshift_and_p1_only_watches(self):
        scene = self.scene_for(self.p2)
        self.assertEqual(scene.spectators, [self.p1])
        self.frames(1, [key(pygame.K_e), key(pygame.K_SPACE), key(pygame.K_LSHIFT), key(pygame.K_a), key(pygame.K_d)])
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta, self.tb))
        self.assertEqual(scene.table.state, "idle")
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta, self.tb - 1))
        self.frames(1, [release(pygame.K_RETURN)])
        flippers = scene.table.world.flippers
        self.frames(1, [key(pygame.K_a), key(pygame.K_d)])                          # P1's flipper keys do nothing
        self.frames(15)
        self.assertEqual((flippers[-1].raised, flippers[1].raised), (0, 0))
        self.frames(1, [key(pygame.K_LEFT)])
        self.frames(10)
        self.assertGreater(flippers[-1].raised, 0.9)
        self.frames(1, [release(pygame.K_LEFT), key(pygame.K_RIGHT)])
        self.frames(10)
        self.assertGreater(flippers[1].raised, 0.9)
        self.frames(1, [release(pygame.K_RIGHT), key(pygame.K_RSHIFT)])             # RSHIFT pulls the plunger
        self.frames(20)
        self.assertGreater(scene.table.world.pull, 0.1)
        self.frames(1, [release(pygame.K_RSHIFT)])
        self.assertEqual(scene.table.world.phase, "play")
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta, self.tb - 1))

    def test_the_spectator_cannot_pause_leave_or_spend_the_active_players_tokens(self):
        scene = self.scene_for(self.p2)
        self.frames(1, [key(pygame.K_i)])                      # P1's bag / pause key
        self.assertFalse(scene.paused)
        self.frames(1, [key(pygame.K_o)])                      # P2's own
        self.assertTrue(scene.paused)
        self.frames(1, [key(pygame.K_o)])
        self.assertFalse(scene.paused)
        self.assertEqual(self.a.tokens, self.ta)

    def test_rewards_and_runs_stay_with_their_own_profile(self):
        scene = self.scene_for(self.p1)
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(1, [release(pygame.K_SPACE)])
        scene.table.world.score = 25000
        self.assertEqual(self.b.pinball_run, None)
        self.game.scenes.pop(fade=False)                       # P1 leaves: the score so far pays Alice
        self.assertEqual((self.a.tickets, self.b.tickets), (5, 0))
        self.assertEqual(self.b.pinball_ticket_room(), PINBALL_DAILY_TICKET_CAP)
        scene_b = self.scene_for(self.p2)
        self.assertEqual(scene_b.table.state, "idle")
        self.assertEqual(scene_b.profile, self.b)

    def test_each_player_sees_their_own_keys(self):
        self.assertEqual(PinballScene(self.game, self.p1).controls_lines(),
                         [("A", "L FLIPPER"), ("D", "R FLIPPER"), ("SPACE/E", "PLUNGER"), ("I", "PAUSE"), ("ESC", "LEAVE")])
        self.assertEqual(PinballScene(self.game, self.p2).controls_lines(),
                         [("LEFT", "L FLIPPER"), ("RIGHT", "R FLIPPER"), ("R-SHIFT/ENTER", "PLUNGER"), ("O", "PAUSE"), ("ESC", "LEAVE")])
        self.assertIs(PinballScene(self.game, self.p1).controls, P1_CONTROLS)
        self.assertIs(PinballScene(self.game, self.p2).controls, P2_CONTROLS)
        self.assertIs(PinballScene(Game(save_path=os.path.join(self.dir, "solo.json")), None).controls, SOLO_CONTROLS)


class ScreenLayoutTests(HubBase):
    """All text sits inside the 400x300 canvas and no two strings overlap, in every state."""

    def check(self, scene, label):
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        bounds = canvas.get_rect()
        for r in scene.text_rects:
            self.assertTrue(bounds.contains(r), f"{label}: text {r} leaves the screen")
        for i, a in enumerate(scene.text_rects):
            for b in scene.text_rects[i + 1:]:
                self.assertFalse(a.colliderect(b), f"{label}: text overlap {a} vs {b}")

    def test_every_state_fits(self):
        room, scene = self.open_machine()
        self.check(scene, "title")
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(1, [release(pygame.K_SPACE)])
        self.frames(3)
        self.check(scene, "ball ready")
        self.game.profile.add_tokens(9990, "TEST")
        scene.table.world.score = 9999999
        self.check(scene, "huge balance and score")
        scene.table.world.lucky_left = 9
        scene.table.world.targets = [True, True, True]
        scene.table.world.phase = "play"
        scene.table.world.bx, scene.table.world.by = 60.0, 150.0
        self.check(scene, "lucky cat mode")
        scene.table.world.lucky_left = 0
        drain_now(scene)
        self.frames(3)
        self.check(scene, "end of ball bonus")
        self.frames(1, [key(pygame.K_p)])
        self.check(scene, "paused")
        self.frames(1, [key(pygame.K_p)])
        self.frames(int((pb.BONUS_TIME + 0.2) * 60))
        self.finish_run(scene, 123456)
        self.check(scene, "result")
        self.game.profile.spend_tokens(self.game.profile.tokens, "TEST")
        self.frames(1, [key(pygame.K_SPACE)])
        self.check(scene, "out of tokens")

    def test_it_renders_at_800x600_and_16_by_9_windows(self):
        room, scene = self.start_run()
        frames = {}
        for size in ((800, 600), (1280, 720), (1920, 1080), (1366, 768)):
            layout = compute_layout(size)
            screen = pygame.Surface(layout.screen_size)
            canvas = pygame.Surface((VIEW_W, VIEW_H))
            self.game.scenes.draw(canvas, screen)
            self.assertEqual(screen.get_size(), layout.screen_size)
            self.assertGreater(len({screen.get_at((x, y))[:3] for x in range(0, screen.get_width(), 37)
                                    for y in range(0, screen.get_height(), 29)}), 8, size)
            frames[size] = pygame.image.tobytes(canvas, "RGB")
        self.assertEqual(len(set(frames.values())), 1)                              # one canvas, scaled to any window

    def test_the_table_fits_inside_the_canvas_and_the_panels(self):
        import pinball_art as art
        table = pygame.Rect(art.TX, art.TY, int(pb.W), int(pb.H))
        self.assertTrue(pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(table.inflate(14, 40)))
        self.assertFalse(table.colliderect(pygame.Rect(16, 40, 106, 232)))
        self.assertFalse(table.colliderect(pygame.Rect(278, 40, 106, 232)))

    def test_each_animated_part_changes_the_picture(self):
        room, scene = self.start_run()
        canvas = pygame.Surface((VIEW_W, VIEW_H))

        def shot():
            scene.draw(canvas)
            return pygame.image.tobytes(canvas, "RGB")
        base = shot()
        scene.table.world.pull = 0.8
        self.assertNotEqual(shot(), base)                                            # the plunger pulls back
        scene.table.world.pull = 0
        self.frames(1, [key(pygame.K_a)])
        self.frames(10)
        flipped = shot()
        self.assertNotEqual(flipped, base)                                           # the flipper moves
        self.frames(1, [release(pygame.K_a)])
        self.frames(20)
        w = scene.table.world
        before = shot()
        w.bumper_flash[0] = 0.18
        self.assertNotEqual(shot(), before)                                          # a bumper flashes
        w.bumper_flash[0] = 0
        before = shot()
        w.targets[1] = True
        self.assertNotEqual(shot(), before)                                          # a target lights
        w.targets[1] = False
        w.phase, w.lucky_left = "play", 8.0
        self.assertNotEqual(shot(), before)                                          # Lucky Cat Mode glows
        scene.drain_flash = 0.9
        self.assertNotEqual(shot(), before)


class AudioTests(HubBase):
    NAMES = ("pin_launch", "pin_flipper", "pin_bumper", "pin_rail", "pin_target", "pin_scoop", "pin_bonus", "pin_drain")

    def test_sound_effects_exist_and_the_busy_ones_stay_quiet_and_never_cut_off_big_moments(self):
        import audio_manager as am
        for name in self.NAMES:
            self.assertIn(name, am.SFX_FILES)
            self.assertTrue(os.path.exists(os.path.join(am.ASSET_DIR, "sfx", f"{name}.wav")), name)
        self.assertLess(am.PRIORITY["pin_rail"], am.PRIORITY["pin_bumper"])
        self.assertLess(am.PRIORITY["pin_flipper"], am.PRIORITY["pin_bumper"])
        self.assertLess(am.PRIORITY["pin_bumper"], am.PRIORITY["pin_drain"])
        self.assertLess(am.PRIORITY["pin_drain"], am.PRIORITY["pin_bonus"])
        self.assertLess(am.SFX_GAIN["pin_rail"], 0.7)
        self.assertGreaterEqual(am.MIN_GAP["pin_rail"], 0.07)
        self.assertGreater(am.MIN_GAP["pin_bumper"], 0.06)

    def test_the_scene_plays_launch_flipper_bumper_rail_target_scoop_bonus_and_drain_sounds(self):
        room, scene = self.start_run()
        self.game.audio = audio = Mock()
        w = scene.table.world
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(20)
        self.frames(1, [release(pygame.K_SPACE)])                                    # launch
        self.frames(1, [key(pygame.K_a)])                                            # flipper
        bx, by = pb.BUMPERS[1]
        w.bx, w.by, w.vx, w.vy = bx - pb.BUMPER_R - pb.R + 0.5, by, 60.0, 0.0       # bumper
        self.frames(6)
        w.bx, w.by, w.vx, w.vy = 5.0, 100.0, -300.0, 0.0                             # wall tick
        self.frames(6)
        (x0, y0), (x1, y1) = pb.TARGETS[0]
        w.bx, w.by, w.vx, w.vy = x0 - pb.R - 1.0, (y0 + y1) / 2, 80.0, 0.0           # target
        self.frames(6)
        w.bx, w.by, w.vx, w.vy, w.scoop_cool = pb.SCOOP[0] + 1, pb.SCOOP[1], 0.0, 0.0, 0   # scoop
        self.frames(6)
        w.targets, w.captured = [True, True, False], 0
        w.bx, w.by, w.vx, w.vy = x0 - pb.R - 1.0, pb.TARGETS[2][0][1] + 6, 80.0, 0.0
        self.frames(1)
        (a, b) = pb.TARGETS[2]
        w.bx, w.by, w.vx, w.vy = a[0] - pb.R - 1.0, (a[1] + b[1]) / 2, 80.0, 0.0     # CAT complete: the fanfare
        self.frames(6)
        drain_now(scene)                                                             # drain
        self.frames(3)
        played = {c.args[0] for c in audio.play.call_args_list}
        for name in self.NAMES:
            self.assertIn(name, played, name)

    def test_collision_ticks_are_rate_limited(self):
        w = pb.PinballWorld()
        w.start_run()
        w.phase = "play"
        ticks = 0
        for i in range(60 * 10):
            if w.phase != "play":
                break
            w.bx, w.by, w.vx, w.vy = 5.0, 100.0, -400.0, 0.0
            ticks += sum(1 for e in w.advance(DT) if e.kind == "rail")
        self.assertLessEqual(ticks / 10.0, 1 / 0.07 + 6)                             # the world itself never ticks faster than ~14 / s

    def test_a_muted_game_still_plays_the_machine(self):
        room, scene = self.open_machine()
        self.game.audio.set_muted(True)
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(1, [release(pygame.K_SPACE)])
        self.frames(60)
        self.assertTrue(scene.table.live)


if __name__ == "__main__":
    unittest.main()
