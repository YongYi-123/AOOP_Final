"""NEON COIN PUSHER inside the Arcade Hub: the Lucky Corner cabinet, launching, the scene's
controls (solo, P1, P2), pause / exit, saving and crash recovery, audio and rendering.
Run headless from this folder:   python -m unittest test_coin_pusher_integration
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

import coin_pusher as cp  # noqa: E402
from coin_pusher_scene import CoinPusherScene  # noqa: E402
from controls import P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS  # noqa: E402
from display import compute_layout  # noqa: E402
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from local_session import LocalSession  # noqa: E402
from prize_plaza import LUCKY_POS, PrizePlazaScene  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402
from stations import CoinPusherStation, SoonStation  # noqa: E402

DT = 1 / 60
DAY1 = date(2026, 3, 10)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def release(k):
    return pygame.event.Event(pygame.KEYUP, key=k, mod=0)


def edge_coin(world, kind=cp.NORMAL, prize=None, x=65.0):
    coin = world.place(x, cp.D - 2, kind, prize)
    coin.y = cp.D - 0.5
    coin.vy = 30
    return coin


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
        return next(p for p in room.props if isinstance(p, CoinPusherStation))

    def open_machine(self):
        room = self.plaza()
        station = self.station(room)
        room.player.x, room.player.y = station.zone.centerx, station.zone.bottom - 2
        self.frames(5)
        self.assertIs(room.nearby, station)
        self.frames(30, [key(pygame.K_e)])
        self.frames(40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, CoinPusherScene)
        return room, scene


class LuckyCornerTests(HubBase):
    def test_the_first_soon_bay_became_the_coin_pusher_and_the_second_is_lucky_cat_pinball(self):
        room = self.plaza()
        pusher = self.station(room)
        self.assertEqual(pusher.rect.topleft, (LUCKY_POS[0], LUCKY_POS[1] + 70))
        self.assertEqual([p for p in room.props if isinstance(p, SoonStation)], [])
        self.assertEqual(sorted(p.prompt_label for p in room.interactables if hasattr(p, "kind")),
                         ["PLAY COIN PUSHER", "PLAY HI-LO", "PLAY LUCKY CAT PINBALL", "PLAY NEON 21", "PLAY SPIN"])

    def test_it_is_interactable_solid_and_blocks_no_walking_route(self):
        room = self.plaza()
        pusher = self.station(room)
        self.assertIn(pusher, room.interactables)
        self.assertIn(pusher.footprint, room.solids)
        for other in room.props:
            if other is not pusher and getattr(other, "solid", True):
                self.assertFalse(pusher.footprint.colliderect(other.footprint), type(other).__name__)
        neighbour = next(p for p in room.props if p.__class__.__name__ == "PinballStation")
        self.assertGreaterEqual(neighbour.footprint.left - pusher.footprint.right, 8)     # the player can walk between
        self.assertLessEqual(pusher.rect.bottom, VIEW_H - 20)

    def test_the_cabinet_has_a_readable_marquee_and_its_own_sprite(self):
        from lucky_cabinets import KINDS, build_cabinet
        self.assertEqual(KINDS["pusher"]["label"], "COIN")
        sprite = build_cabinet("pusher")
        self.assertEqual(sprite.get_size(), (28, 40))
        others = {pygame.image.tobytes(build_cabinet(k), "RGBA") for k in KINDS if k != "pusher"}
        self.assertNotIn(pygame.image.tobytes(sprite, "RGBA"), others)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        pusher = self.station(self.plaza())
        frames = set()
        for t in (0.0, 0.6, 1.2, 2.0, 3.1):
            pusher.time = t
            canvas.fill((0, 0, 0))
            pusher.draw(canvas)
            frames.add(pygame.image.tobytes(canvas.subsurface(pusher.rect), "RGB"))
        self.assertGreater(len(frames), 2)                                          # the screen preview is animated

    def test_walking_up_and_pressing_e_opens_it_for_free_and_the_hub_music_comes_back(self):
        room, scene = self.open_machine()
        self.assertEqual(self.game.profile.tokens, self.start_tokens)               # opening charges nothing
        self.assertEqual(self.game.music_for(self.game.scenes.stack), "lucky_corner")
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        self.assertIsInstance(self.game.scenes.current, PrizePlazaScene)
        self.assertEqual(self.game.music_for(self.game.scenes.stack), "prize_plaza")
        self.assertEqual(self.game.profile.tokens, self.start_tokens)
        self.assertTrue(self.game.scenes.current.player.controls.owns(pygame.K_a))   # the room has its controls back


class SoloControlTests(HubBase):
    def test_space_drops_one_coin_for_one_token_and_mashing_charges_once(self):
        room, scene = self.open_machine()
        n = len(scene.table.world.coins)
        self.frames(1, [key(pygame.K_SPACE)] * 8)
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 1)
        self.assertEqual(scene.table.world.count, n + 1)
        self.frames(30)
        self.frames(1, [key(pygame.K_e), key(pygame.K_e)])                           # E drops too, once
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 2)

    def test_a_held_key_does_not_machine_gun_coins(self):
        room, scene = self.open_machine()
        repeat = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode="", repeat=True)
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(120, [repeat])
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 1)

    def test_a_and_d_slide_the_chute_and_the_coin_lands_below_it(self):
        room, scene = self.open_machine()
        t = scene.table
        x0 = t.chute_x
        self.frames(1, [key(pygame.K_a)])
        self.frames(30)
        self.frames(1, [release(pygame.K_a)])
        left = t.chute_x
        self.assertLess(left, x0)
        self.frames(30)
        self.assertEqual(t.chute_x, left)                                            # released: it stops
        self.frames(1, [key(pygame.K_d)])
        self.frames(60)
        self.frames(1, [release(pygame.K_d)])
        self.assertGreater(t.chute_x, left)
        self.frames(1, [key(pygame.K_LEFT)])                                         # solo also has the arrows
        self.frames(10)
        self.frames(1, [release(pygame.K_LEFT)])
        t.chute_x = 33.0
        self.frames(1, [key(pygame.K_SPACE)])
        self.assertEqual(t.world.drops[-1].x, 33.0)

    def test_opposite_keys_cancel_and_the_chute_stays_inside_the_walls(self):
        room, scene = self.open_machine()
        self.frames(1, [key(pygame.K_a), key(pygame.K_d)])
        x = scene.table.chute_x
        self.frames(20)
        self.assertEqual(scene.table.chute_x, x)
        self.frames(1, [release(pygame.K_d)])
        self.frames(200)
        self.assertEqual(scene.table.chute_x, cp.R)

    def test_out_of_tokens_charges_nothing_and_says_so(self):
        room, scene = self.open_machine()
        prof = self.game.profile
        prof.spend_tokens(prof.tokens, "TEST")
        n = scene.table.world.count
        self.frames(1, [key(pygame.K_SPACE)] * 3)
        self.assertEqual((prof.tokens, scene.table.world.count), (0, n))
        self.assertEqual(scene.alert, "OUT OF TOKENS!")
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)                                                           # the alert draws
        self.frames(120)
        self.assertEqual(prof.tokens, 0)

    def test_pause_freezes_everything_resume_continues_and_exit_works_from_pause(self):
        room, scene = self.open_machine()
        self.frames(1, [key(pygame.K_p)])
        self.assertTrue(scene.paused)
        motor = scene.table.world.motor
        self.frames(1, [key(pygame.K_SPACE)] * 3)
        self.frames(60)
        self.assertEqual((self.game.profile.tokens, scene.table.world.motor), (self.start_tokens, motor))
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        self.frames(1, [key(pygame.K_i)])                                            # the bag key is a pause key too
        self.assertFalse(scene.paused)
        self.frames(30)
        self.assertGreater(scene.table.world.motor, motor)
        self.frames(1, [key(pygame.K_p)])
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        self.assertIsInstance(self.game.scenes.current, PrizePlazaScene)

    def test_the_controls_box_shows_the_real_keys(self):
        room, scene = self.open_machine()
        self.assertEqual(scene.controls_lines(),
                         [("A/D", "MOVE CHUTE"), ("SPACE/E", "DROP COIN"), ("P", "PAUSE"), ("ESC", "LEAVE")])


class SavingTests(HubBase):
    def test_leaving_saves_the_board_and_a_restart_brings_back_the_same_coins(self):
        room, scene = self.open_machine()
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(200)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        tokens = self.game.profile.tokens
        board = self.game.profile.pusher_state["board"]
        data = self.saved()
        self.assertEqual(data["tokens"], tokens)
        self.assertEqual(data["coin_pusher"]["board"]["coins"], board["coins"])
        game2 = Game(save_path=self.path, clock=GameClock(lambda: DAY1))
        self.assertEqual(game2.profile.tokens, tokens)
        scene2 = CoinPusherScene(game2, None)
        self.assertEqual(len(scene2.table.world.coins), len(board["coins"]))
        self.assertEqual(game2.profile.tokens, tokens)                               # reopening costs nothing

    def test_reopening_again_and_again_does_not_reset_the_board_or_the_wallet(self):
        seeds, counts = set(), set()
        for _ in range(4):
            room, scene = self.open_machine()
            seeds.add(scene.table.seed)
            counts.add(len(scene.table.world.coins))
            self.frames(1, [key(pygame.K_ESCAPE)])
            self.frames(60)
        self.assertEqual((len(seeds), len(counts)), (1, 1))
        self.assertEqual(self.game.profile.tokens, self.start_tokens)

    def test_a_crash_with_the_machine_open_loses_neither_the_token_nor_the_coin(self):
        room, scene = self.open_machine()
        n = len(scene.table.world.coins)
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(5)                                       # the coin is still in the air; the app "dies" here
        data = self.saved()
        self.assertEqual(data["tokens"], self.start_tokens - 1)
        self.assertEqual(len(data["coin_pusher"]["board"]["coins"]) + len(data["coin_pusher"]["board"]["drops"]), n + 1)
        game2 = Game(save_path=self.path, clock=GameClock(lambda: DAY1))
        scene2 = CoinPusherScene(game2, None)
        self.assertEqual((game2.profile.tokens, len(scene2.table.world.coins)), (self.start_tokens - 1, n + 1))

    def test_a_payout_reaches_the_save_together_with_the_removal_of_the_coin(self):
        room, scene = self.open_machine()
        scene.table.world.coins = []
        edge_coin(scene.table.world, cp.SILVER)
        self.frames(10)
        data = self.saved()
        self.assertEqual(data["tokens"], self.start_tokens + 3)
        self.assertEqual(data["coin_pusher"]["board"]["coins"], [])
        self.frames(300)
        self.assertEqual(self.game.profile.tokens, self.start_tokens + 3)           # once

    def test_quitting_the_program_with_the_machine_open_settles_and_saves(self):
        room, scene = self.open_machine()
        self.frames(1, [key(pygame.K_SPACE)])
        self.game.scenes.quit()
        data = self.saved()
        self.assertEqual(data["coin_pusher"]["board"]["drops"], [])
        self.assertEqual(data["tokens"], self.start_tokens - 1)


class RewardTests(HubBase):
    def test_collected_coins_pay_the_playing_profile_and_show_in_the_session_counters(self):
        room, scene = self.open_machine()
        scene.table.world.coins = []
        edge_coin(scene.table.world, cp.GOLDEN, x=40)
        edge_coin(scene.table.world, cp.SILVER, x=80)
        self.frames(15)
        self.assertEqual((self.game.profile.tickets, self.game.profile.tokens),
                         (5, self.start_tokens + 3))
        self.assertEqual((scene.table.session_tickets, scene.table.session_tokens), (5, 3))
        self.assertGreater(scene.gold_until, scene.time)                             # the Golden Cat celebration
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        self.assertTrue(scene.particles)

    def test_the_daily_ticket_cap_applies_through_the_scene(self):
        room, scene = self.open_machine()
        self.game.profile.award_pusher_tickets(30)
        tickets = self.game.profile.tickets
        scene.table.world.coins = []
        edge_coin(scene.table.world, cp.GOLDEN)
        self.frames(15)
        self.assertEqual(self.game.profile.tickets, tickets)
        self.assertEqual(self.game.profile.tokens, self.start_tokens + 1)


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
        scene = CoinPusherScene(self.game, player)
        self.game.scenes.push(scene, fade=False)
        return scene

    def test_p1_plays_with_wasd_and_space_p2_only_watches(self):
        scene = self.scene_for(self.p1)
        self.assertEqual(scene.spectators, [self.p2])
        self.frames(1, [key(pygame.K_RETURN), key(pygame.K_RSHIFT), key(pygame.K_KP0), key(pygame.K_RCTRL)])   # P2's keys
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta, self.tb))
        x = scene.table.chute_x
        self.frames(1, [key(pygame.K_LEFT)])
        self.frames(20)
        self.assertEqual(scene.table.chute_x, x)                                    # P2's arrows do not steer P1's chute
        self.frames(1, [key(pygame.K_SPACE)])
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta - 1, self.tb))

    def test_p2_plays_with_arrows_and_enter_and_p1_only_watches(self):
        scene = self.scene_for(self.p2)
        self.assertEqual(scene.spectators, [self.p1])
        self.frames(1, [key(pygame.K_e), key(pygame.K_SPACE), key(pygame.K_LSHIFT), key(pygame.K_a), key(pygame.K_d)])
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta, self.tb))
        x = scene.table.chute_x
        self.frames(1, [key(pygame.K_RIGHT)])
        self.frames(20)
        self.frames(1, [release(pygame.K_RIGHT)])
        self.assertGreater(scene.table.chute_x, x)
        self.frames(1, [key(pygame.K_RETURN)])
        self.assertEqual((self.a.tokens, self.b.tokens), (self.ta, self.tb - 1))
        self.frames(30)
        self.frames(1, [key(pygame.K_RSHIFT)])
        self.assertEqual(self.b.tokens, self.tb - 2)
        self.assertEqual(self.a.tokens, self.ta)

    def test_the_spectator_cannot_pause_or_spend_the_active_players_tokens(self):
        scene = self.scene_for(self.p2)
        self.frames(1, [key(pygame.K_i)])                      # P1's bag / pause key
        self.assertFalse(scene.paused)
        self.frames(1, [key(pygame.K_o)])                      # P2's own
        self.assertTrue(scene.paused)
        self.frames(1, [key(pygame.K_o)])
        self.assertFalse(scene.paused)

    def test_rewards_and_boards_stay_with_their_own_profile(self):
        scene = self.scene_for(self.p1)
        board_b = self.b.pusher_state
        self.assertIsNone(board_b)                             # Bob has not visited the machine
        scene.table.world.coins = []
        edge_coin(scene.table.world, cp.GOLDEN)
        self.frames(15)
        self.assertEqual((self.a.tickets, self.b.tickets), (5, 0))
        self.assertEqual(self.b.pusher_ticket_room(), 30)
        self.game.scenes.pop(fade=False)
        scene_b = self.scene_for(self.p2)
        self.assertNotEqual(scene_b.table.seed, scene.table.seed)
        self.assertGreater(len(scene_b.table.world.coins), 30)                      # Bob got his own full board

    def test_each_player_sees_their_own_keys(self):
        self.assertEqual(CoinPusherScene(self.game, self.p1).controls_lines(),
                         [("A/D", "MOVE CHUTE"), ("SPACE/E", "DROP COIN"), ("I", "PAUSE"), ("ESC", "LEAVE")])
        self.assertEqual(CoinPusherScene(self.game, self.p2).controls_lines(),
                         [("LEFT/RIGHT", "MOVE CHUTE"), ("R-SHIFT/ENTER", "DROP COIN"), ("O", "PAUSE"), ("ESC", "LEAVE")])
        self.assertIs(CoinPusherScene(self.game, self.p1).controls, P1_CONTROLS)
        self.assertIs(CoinPusherScene(self.game, self.p2).controls, P2_CONTROLS)
        self.assertIs(CoinPusherScene(Game(save_path=os.path.join(self.dir, "solo.json")), None).controls, SOLO_CONTROLS)


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
        self.check(scene, "initial")
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(30)
        self.check(scene, "after a drop")
        self.game.profile.add_tokens(9990, "TEST")
        self.check(scene, "huge balance")
        scene.table.session_tickets, scene.table.session_tokens = 1234, 5678
        self.check(scene, "big winnings")
        scene.table.world.coins = []
        edge_coin(scene.table.world, cp.GOLDEN)
        self.frames(12)
        self.check(scene, "golden cat")
        self.game.profile.spend_tokens(self.game.profile.tokens, "TEST")
        self.frames(30)
        self.frames(1, [key(pygame.K_SPACE)])
        self.check(scene, "out of tokens")
        self.frames(1, [key(pygame.K_p)])
        self.check(scene, "paused")

    def test_a_crowded_machine_still_draws_every_coin_kind(self):
        room, scene = self.open_machine()
        world = scene.table.world
        for kind in cp.KINDS:
            world.place(30 + 20 * cp.KINDS.index(kind), 60, kind, ("tokens", 2) if kind == cp.MYSTERY else None)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        import coin_pusher_art as art
        sprites = {pygame.image.tobytes(art.coin_sprite(k, 16), "RGBA") for k in cp.KINDS}
        self.assertEqual(len(sprites), 4)                                            # four visibly different coins

    def test_it_renders_at_800x600_and_16_by_9_windows(self):
        room, scene = self.open_machine()
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


class AudioTests(HubBase):
    def test_sound_effects_exist_and_clinks_stay_quiet_and_never_cut_off_a_payout(self):
        import audio_manager as am
        for name in ("coin_drop", "coin_clink", "coin_tray", "coin_win", "coin_gold", "pusher_hum"):
            self.assertIn(name, am.SFX_FILES)
            self.assertTrue(os.path.exists(os.path.join(am.ASSET_DIR, "sfx", f"{name}.wav")), name)
        self.assertLess(am.PRIORITY["coin_clink"], am.PRIORITY["coin_tray"])
        self.assertLess(am.PRIORITY["coin_tray"], am.PRIORITY["coin_win"])
        self.assertLess(am.PRIORITY["coin_win"], am.PRIORITY["coin_gold"])
        self.assertLess(am.SFX_GAIN["coin_clink"], 0.7)
        self.assertGreaterEqual(am.MIN_GAP["coin_clink"], 0.1)
        self.assertGreaterEqual(am.MIN_GAP["pusher_hum"], 1.0)

    def test_the_scene_plays_drop_tray_win_and_gold_sounds(self):
        room, scene = self.open_machine()
        self.game.audio = audio = Mock()
        scene.table.world.coins = []
        self.frames(1, [key(pygame.K_SPACE)])
        edge_coin(scene.table.world, cp.NORMAL, x=20)
        edge_coin(scene.table.world, cp.SILVER, x=60)
        edge_coin(scene.table.world, cp.GOLDEN, x=100)
        self.frames(15)
        played = [c.args[0] for c in audio.play.call_args_list]
        for name in ("coin_drop", "coin_tray", "coin_win", "coin_gold"):
            self.assertIn(name, played)

    def test_collision_clinks_are_rate_limited(self):
        room, scene = self.open_machine()
        self.game.audio = audio = Mock()
        rng_x = [20, 50, 80, 110, 40, 90]
        for i in range(24):
            scene.table.chute_x = rng_x[i % 6]
            self.game.profile.add_tokens(1, "TEST")
            scene.table.cooldown = 0
            scene.table.drop()
            self.frames(30)
        seconds = 24 * 0.5
        clinks = sum(1 for c in audio.play.call_args_list if c.args[0] == "coin_clink")
        self.assertLess(clinks / seconds, 11.5)
        self.assertGreater(clinks, 0)

    def test_the_motor_hums_once_per_stroke(self):
        room, scene = self.open_machine()
        self.game.audio = audio = Mock()
        self.frames(int(3 * cp.PUSH_PERIOD * 60))
        hums = sum(1 for c in audio.play.call_args_list if c.args[0] == "pusher_hum")
        self.assertIn(hums, (3, 4))

    def test_a_muted_game_still_plays_the_machine(self):
        room, scene = self.open_machine()
        self.game.audio.set_muted(True)
        self.frames(1, [key(pygame.K_SPACE)])
        self.frames(60)
        self.assertEqual(self.game.profile.tokens, self.start_tokens - 1)

    def test_the_machine_has_its_own_effect_channel_and_gives_it_back(self):
        keys_before = self.game.scene_keys()
        room, scene = self.open_machine()
        self.assertEqual(len(self.game.scene_keys()), len(keys_before) + 1)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        self.assertEqual(len(self.game.scene_keys()), len(keys_before))


if __name__ == "__main__":
    unittest.main()
