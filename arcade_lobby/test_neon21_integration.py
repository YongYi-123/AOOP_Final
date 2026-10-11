"""NEON 21 inside the Arcade Hub: the Lucky Corner layout, launching from the
cabinet, the scene's controls, P1/P2 isolation, leaving mid-hand and layout of
every screen. Run headless from this folder:   python -m unittest test_neon21_integration
"""
import json
import os
import shutil
import tempfile
import unittest
from datetime import date

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from blackjack_testing import stacked_deck
from blackjack import Card, Outcome  # noqa: E402
from game import Game  # noqa: E402
from game_clock import GameClock  # noqa: E402
from local_session import LocalSession  # noqa: E402
from neon21 import TICKETS, Neon21Table  # noqa: E402
from neon21_scene import Neon21Scene  # noqa: E402
from prize_plaza import LUCKY_POS, PrizePlazaScene  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402
from stations import (ChanceStation, Neon21Station, Station,  # noqa: E402
                      SoonStation)

DT = 1 / 60
DAY1 = date(2026, 3, 10)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def stack(*labels):
    return stacked_deck(*labels)



WIN = ("10", "10", "9", "8")
LOSE = ("10", "10", "7", "9")
NATURAL = ("A", "9", "K", "7")


class HubBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")
        self.game = Game(save_path=self.path, clock=GameClock(lambda: DAY1))
        self.frames(3, [key(pygame.K_ESCAPE)])
        self.frames(3, [key(pygame.K_ESCAPE)])
        self.game.profile.add_tokens(30, "TEST")

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

    def open_table(self):
        room = self.plaza()
        station = next(p for p in room.props if isinstance(p, Neon21Station))
        room.player.x, room.player.y = station.zone.centerx, station.zone.bottom - 2
        self.frames(5)
        self.assertIs(room.nearby, station)
        self.frames(30, [key(pygame.K_e)])
        self.frames(40)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, Neon21Scene)
        return room, scene

    def rig(self, scene, labels):
        scene.table.deck_source = lambda: stack(*labels)


class LuckyCornerLayoutTests(HubBase):
    def test_arrangement_is_spin_hilo_neon21_and_two_soon_bays(self):
        room = self.plaza()
        cabinets = sorted((p for p in room.props if isinstance(p, (ChanceStation, Neon21Station))),
                          key=lambda p: (p.rect.y, p.rect.x))
        self.assertEqual([c.prompt_label for c in cabinets], ["PLAY SPIN", "PLAY HI-LO", "PLAY NEON 21"])
        self.assertEqual([c.rect.topleft for c in cabinets],
                         [(LUCKY_POS[0] + 40 * i, LUCKY_POS[1]) for i in range(3)])
        soon = [p for p in room.props if isinstance(p, SoonStation)]
        self.assertEqual(len(soon), 2)
        self.assertTrue(all(p.rect.y > LUCKY_POS[1] + 40 for p in soon))
        for s in soon:
            self.assertNotIn(s, room.interactables)

    def test_spin_and_hilo_keep_their_games(self):
        room = self.plaza()
        names = {p.game_cls.__name__ for p in room.props if isinstance(p, ChanceStation)}
        self.assertEqual(names, {"LuckyWheelGame", "HighLowGame"})
        self.assertEqual(sum(isinstance(p, Neon21Station) for p in room.props), 1)

    def test_the_new_cabinet_is_interactable_and_does_not_overlap_anything(self):
        room = self.plaza()
        n21 = next(p for p in room.props if isinstance(p, Neon21Station))
        self.assertIn(n21, room.interactables)
        self.assertIn(n21.footprint, room.solids)
        for other in room.props:
            if other is not n21 and getattr(other, "solid", True):
                self.assertFalse(n21.footprint.colliderect(other.footprint), type(other).__name__)
        sign = next(p for p in room.props if p.__class__.__name__ == "LuckySign")
        self.assertFalse(sign.footprint.colliderect(n21.rect.inflate(0, -2).move(0, 2)))
        self.assertLessEqual(n21.rect.right, VIEW_W - 20)

    def test_cabinets_leave_walkable_gaps_between_them(self):
        room = self.plaza()
        feet = sorted((p.footprint for p in room.props if isinstance(p, (ChanceStation, Neon21Station))),
                      key=lambda r: r.x)
        for a, b in zip(feet, feet[1:]):
            self.assertGreaterEqual(b.left - a.right, 8)          # wider than the player

    def test_every_lucky_cabinet_has_its_own_look(self):
        from lucky_cabinets import KINDS, build_cabinet
        images = {k: pygame.image.tobytes(build_cabinet(k), "RGBA") for k in KINDS}
        self.assertEqual(len(set(images.values())), 3)
        self.assertTrue(all(build_cabinet(k).get_size() == (28, 40) for k in KINDS))

    def test_every_animation_frame_draws(self):
        room = self.plaza()
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        for t in (0.0, 0.5, 1.3, 2.6, 3.9, 4.7):
            for st in room.props:
                if isinstance(st, Station) and hasattr(st, "kind"):
                    st.time = t
                    st.draw(canvas)


class LaunchTests(HubBase):
    def test_launch_charges_nothing_then_deal_charges_once(self):
        room, scene = self.open_table()
        self.assertEqual(self.game.profile.tokens, 40)
        self.rig(scene, WIN)
        self.frames(1, [key(pygame.K_e)] * 8)                       # mash E
        self.assertEqual(self.game.profile.tokens, 38)              # default wager 2, once
        self.assertEqual(self.game.profile.chance_games_played, 1)

    def test_full_hand_through_the_keyboard_then_return_to_the_hub(self):
        room, scene = self.open_table()
        self.rig(scene, WIN)
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        self.frames(1, [key(pygame.K_d)] * 4)                       # STAND, mashed
        self.frames(200)
        self.assertEqual(scene.table.result.outcome, Outcome.WIN)
        self.assertEqual(self.game.profile.tokens, 42)
        self.frames(1, [key(pygame.K_e)] * 5)
        self.assertEqual(self.game.profile.tokens, 42)              # next-hand + mashed E must not also deal
        self.assertEqual(scene.table.phase, scene.table.IDLE)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        self.assertIsInstance(self.game.scenes.current, PrizePlazaScene)
        self.assertEqual(self.saved()["tokens"], 42)

    def test_hit_stand_double_are_ignored_while_cards_are_still_dealing(self):
        room, scene = self.open_table()
        self.rig(scene, ("5", "10", "6", "7", "10"))
        self.frames(1, [key(pygame.K_e)])
        self.frames(5, [key(pygame.K_a), key(pygame.K_w), key(pygame.K_d)])
        self.assertEqual((len(scene.table.round.player), scene.table.phase), (2, scene.table.PLAYING))
        self.assertEqual(self.game.profile.tokens, 38)

    def test_double_down_through_the_keyboard(self):
        room, scene = self.open_table()
        self.rig(scene, ("5", "10", "6", "7", "10"))
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        self.frames(1, [key(pygame.K_w)] * 3)
        self.assertEqual(self.game.profile.tokens, 40 - 4 + 8)      # 2+2 staked, win returns 8
        self.assertEqual(scene.table.result.stake, 4)

    def test_wager_and_currency_keys_then_ticket_payout(self):
        room, scene = self.open_table()
        self.frames(1, [key(pygame.K_d)])                            # wager 2 -> 5
        self.frames(1, [key(pygame.K_s)])                            # TICKETS
        self.assertEqual((scene.table.wager, scene.table.currency), (5, TICKETS))
        self.rig(scene, WIN)
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        self.frames(1, [key(pygame.K_s)])                         # the currency key does nothing mid-hand
        self.assertEqual(scene.table.currency, TICKETS)
        self.frames(1, [key(pygame.K_d)])
        self.frames(200)
        p = self.game.profile
        self.assertEqual((p.tokens, p.tickets, p.lifetime_tickets_earned), (40, 5, 0))

    def test_leaving_takes_two_escapes_mid_hand_and_settles_once(self):
        room, scene = self.open_table()
        self.rig(scene, LOSE)
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(5)
        self.assertIs(self.game.scenes.current, scene)               # first ESC only warns
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(60)
        self.assertIsInstance(self.game.scenes.current, PrizePlazaScene)
        p = self.game.profile
        self.assertEqual(p.tokens, 38)                               # stake lost to the settled hand, not refunded
        self.assertIsNone(p.neon21_pending)
        self.assertEqual(self.saved()["tokens"], 38)
        self.assertTrue(self.game.scenes.current.notice.visible)     # the hub says how it settled

    def test_leave_warning_expires(self):
        room, scene = self.open_table()
        self.rig(scene, WIN)
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.frames(int(2.5 / DT))
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.assertIs(self.game.scenes.current, scene)

    def test_closing_the_window_mid_hand_settles_exactly_once(self):
        room, scene = self.open_table()
        self.rig(scene, WIN)
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        self.game.step([pygame.event.Event(pygame.QUIT)], DT)
        self.game.quit()
        self.assertEqual(self.saved()["tokens"], 42)
        self.assertNotIn("pending", self.saved()["neon21"])

    def test_killing_the_game_mid_hand_cannot_reroll_the_wager(self):
        room, scene = self.open_table()
        self.rig(scene, LOSE)
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        # no quit, no finish: the process just dies. A new run starts from the file.
        game2 = Game(save_path=self.path, clock=GameClock(lambda: DAY1))
        profile = game2.profile
        self.assertEqual(profile.tokens, 38)
        self.assertIsNotNone(profile.neon21_pending)
        scene2 = Neon21Scene(game2)
        scene2.table.deck_source = lambda: stack(*WIN)              # a lucky reshuffle must be useless
        self.assertEqual((scene2.table.result.outcome, scene2.table.result.recovered),
                         (Outcome.LOSE, True))
        self.assertEqual(profile.tokens, 38)
        self.assertIsNone(profile.neon21_pending)
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["tokens"], 38)

    def test_recovered_round_is_shown_on_reopen(self):
        room, scene = self.open_table()
        self.rig(scene, NATURAL)
        scene.table.set_wager(5)
        self.frames(1, [key(pygame.K_e)])
        self.frames(200)
        self.assertEqual(scene.table.result.outcome, Outcome.BLACKJACK)
        self.assertEqual(self.game.profile.tokens, 30 + 10 + 7)
        # a stand-alone scene over the same profile has nothing to recover
        self.assertIsNone(Neon21Scene(self.game).table.round)

    def test_stale_scene_cannot_pay_twice_after_a_transition(self):
        room, scene = self.open_table()
        self.rig(scene, WIN)
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        self.frames(1, [key(pygame.K_d)])
        self.frames(200)
        tokens = self.game.profile.tokens
        scene.on_exit()
        scene.on_quit()
        scene.table.finish()
        self.frames(1, [key(pygame.K_d), key(pygame.K_a)])
        self.assertEqual(self.game.profile.tokens, tokens)

    def test_not_enough_tokens_blocks_the_deal(self):
        self.game.profile.spend_tokens(self.game.profile.tokens - 1, "TEST")
        room, scene = self.open_table()
        self.frames(1, [key(pygame.K_e)] * 4)
        self.assertEqual((self.game.profile.tokens, scene.table.phase), (1, scene.table.IDLE))
        self.assertEqual(scene.table.affordable_wagers(), [1])

    def test_mouse_buttons_work(self):
        room, scene = self.open_table()
        self.rig(scene, WIN)
        self.frames(2)
        self.click(scene, "chip5")
        self.assertEqual(scene.table.wager, 5)
        self.click(scene, "tickets")
        self.assertEqual(scene.table.currency, TICKETS)
        self.click(scene, "deal")
        self.assertEqual(self.game.profile.tokens, 35)
        self.frames(90)
        self.click(scene, "stand")
        self.frames(200)
        self.assertEqual(self.game.profile.tickets, 5)

    def click(self, scene, name):
        self.frames(1)
        rect = scene.buttons[name][0]
        self.frames(1, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                           pos=(rect.centerx * 2, rect.centery * 2))])


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

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def scene_for(self, player):
        scene = Neon21Scene(self.game, player)
        self.game.scenes.push(scene, fade=False)
        scene.table.deck_source = lambda: stack(*WIN)
        return scene

    def test_the_other_player_only_spectates(self):
        scene = self.scene_for(self.p2)
        self.assertEqual(scene.spectators, [self.p1])
        self.frames(1, [key(pygame.K_e), key(pygame.K_w), key(pygame.K_a), key(pygame.K_d)])   # P1's keys
        self.assertEqual((scene.table.phase, self.b.tokens, self.a.tokens), (scene.table.IDLE, 20, 20))
        self.frames(1, [key(pygame.K_RETURN)])                                                 # P2's confirm
        self.assertEqual((self.b.tokens, self.a.tokens), (18, 20))
        self.frames(90)
        self.frames(1, [key(pygame.K_d)])                                                      # P1's stand: ignored
        self.assertEqual(scene.table.phase, scene.table.PLAYING)
        self.frames(1, [key(pygame.K_RIGHT)])                                                  # P2's stand
        self.frames(200)
        self.assertEqual((self.b.tokens, self.a.tokens), (22, 20))

    def test_winnings_and_cap_stay_on_the_playing_profile(self):
        scene = self.scene_for(self.p1)
        scene.table.set_currency(TICKETS)
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        self.frames(1, [key(pygame.K_RIGHT)])                                                  # P2 key: ignored
        self.frames(1, [key(pygame.K_d)])
        self.frames(200)
        self.assertEqual((self.a.tickets, self.a.neon21_tickets_today()), (2, 2))
        self.assertEqual((self.b.tickets, self.b.neon21_tickets_today(), self.b.tokens), (0, 0, 20))

    def test_two_players_can_take_turns_and_keep_separate_pending_rounds(self):
        ta, tb = Neon21Table(self.a), Neon21Table(self.b)
        ta.deck_source = lambda: stack(*WIN)
        tb.deck_source = lambda: stack(*LOSE)
        ta.deal()
        tb.deal()
        self.assertEqual(self.a.neon21_pending["round"]["player"][1][0], 9)
        self.assertEqual(self.b.neon21_pending["round"]["player"][1][0], 7)
        ta.stand()
        self.assertIsNone(self.a.neon21_pending)
        self.assertIsNotNone(self.b.neon21_pending)


class ScreenLayoutTests(HubBase):
    """All text sits inside the 400x300 canvas and no two strings overlap."""

    def check(self, scene, label):
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        bounds = canvas.get_rect()
        rects = scene.text_rects
        for r in rects:
            self.assertTrue(bounds.contains(r), f"{label}: text {r} leaves the screen")
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                self.assertFalse(a.colliderect(b), f"{label}: text overlap {a} vs {b}")

    def test_every_state_fits(self):
        room, scene = self.open_table()
        t = scene.table
        for tokens in (40, 3):
            pass
        self.check(scene, "betting tokens")
        t.set_currency(TICKETS)
        t.set_wager(10)
        self.check(scene, "betting tickets")
        self.rig(scene, ("5", "10", "6", "7", "2", "2", "2", "2", "3", "3", "3", "3"))
        t.set_wager(5)
        self.frames(1, [key(pygame.K_e)])
        self.frames(5)
        self.check(scene, "dealing")
        self.frames(90)
        self.check(scene, "playing")
        self.frames(1, [key(pygame.K_ESCAPE)])
        self.check(scene, "leave confirm")
        for _ in range(4):                                           # many cards
            self.frames(1, [key(pygame.K_a)])
            self.frames(40)
            self.check(scene, "hit")
            if scene.table.phase != scene.table.PLAYING:
                break
        self.frames(250)
        self.check(scene, "result")

    def test_result_screens_fit_for_every_outcome_including_the_cap_message(self):
        room, scene = self.open_table()
        p = self.game.profile
        cases = {"win": WIN, "lose": LOSE, "natural": NATURAL,
                 "push": ("10", "10", "8", "8"), "bust": ("10", "10", "6", "8", "K")}
        for name, labels in cases.items():
            self.rig(scene, labels)
            scene.table.set_currency(TICKETS)
            scene.table.set_wager(10)
            self.frames(1, [key(pygame.K_e)])
            self.frames(90)
            if scene.table.phase == scene.table.PLAYING:
                self.frames(1, [key(pygame.K_a if name == "bust" else pygame.K_d)])
            self.frames(250)
            self.check(scene, name)
            self.frames(60)
            self.frames(1, [key(pygame.K_e)])
        # the daily cap was hit by now: the explanation must be on screen and fit
        self.assertTrue(any(l[0].startswith("DAILY TICKET CAP") for l in scene._detail_lines(
            type("R", (), {"outcome": Outcome.WIN, "stake": 10, "stake_returned": 10, "tickets_paid": 0,
                           "profit_tokens": 10, "capped": True})())))
        self.assertEqual(p.neon21_ticket_room(), 30 - p.neon21_tickets_today())

    def draw_with_views(self, scene, n_player, n_dealer):
        """Put n cards on each side (no engine needed) and draw one frame."""
        from neon21_scene import CardView
        scene.table.phase = scene.table.PLAYING
        scene.table.round = Neon21Table(scene.profile).round or __import__("blackjack").BlackjackRound(2)
        cards = [Card((i % 13) + 1, "SHDC"[i % 4]) for i in range(12)]
        scene.player_views = [CardView(c, -9) for c in cards[:n_player]]
        scene.dealer_views = [CardView(c, -9, hole=i == 1) for i, c in enumerate(cards[:n_dealer])]
        if n_dealer > 1:
            scene.dealer_views[1].flip_at = -9
        scene.busy_until = -1
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        scene.draw(canvas)
        return canvas

    def test_the_spectating_tag_never_covers_the_controls(self):
        """Two players: the other player's SPECTATING tag sits bottom-right."""
        from font import get_font
        room, scene = self.open_table()
        scene.spectators = [type("P", (), {"tag": "P1 ALICE"})()]
        tag = get_font().render_glow("P1 ALICE - SPECTATING", (0, 0, 0), (0, 0, 0)).get_rect()
        tag.bottomright = (VIEW_W - 4, VIEW_H - 3)
        states = []
        for name in ("betting", "playing", "result"):
            if name == "playing":
                self.rig(scene, WIN)
                self.frames(1, [key(pygame.K_e)])
                self.frames(90)
            if name == "result":
                self.frames(1, [key(pygame.K_d)])
                self.frames(250)
            canvas = pygame.Surface((VIEW_W, VIEW_H))
            scene.draw(canvas)
            for r in scene.text_rects:
                self.assertFalse(r.colliderect(tag), f"{name}: {r} under the spectating tag {tag}")
            for _name, (rect, _l, _e) in scene.buttons.items():
                self.assertFalse(rect.colliderect(tag), name)

    def test_two_to_eleven_cards_fit_for_both_hands(self):
        from neon21_scene import CARD_W, DEALER_BOUNDS, MIN_SPACING, PLAYER_BOUNDS, SHOE
        room, scene = self.open_table()
        shoe = pygame.Rect(SHOE[0] - 3, SHOE[1] - 3, CARD_W + 6, 60)
        for n in range(2, 12):
            self.draw_with_views(scene, n, n)
            for side, bounds in (("dealer", DEALER_BOUNDS), ("player", PLAYER_BOUNDS)):
                rects = scene.card_rects[side]
                self.assertEqual(len(rects), n)
                for r in rects:
                    self.assertGreaterEqual(r.left, bounds[0], (side, n))
                    self.assertLessEqual(r.right, bounds[1], (side, n))
                for a, b in zip(rects, rects[1:]):
                    self.assertGreaterEqual(b.left - a.left, MIN_SPACING, (side, n))   # corner index stays visible
                    if n <= 7:
                        self.assertGreaterEqual(b.left - a.right, 0, (side, n))         # no overlap at all
                for r in rects:
                    for t in scene.text_rects:
                        self.assertFalse(r.colliderect(t), f"{side} card {r} hits text {t} (n={n})")
                    for name, (button, _label, _enabled) in scene.buttons.items():
                        self.assertFalse(r.colliderect(button), f"{side} card hits button {name} (n={n})")
                    self.assertGreater(r.top, 24)
                    self.assertLess(r.bottom, 232)                     # inside the felt, above the panel
            for r in scene.card_rects["dealer"]:
                self.assertFalse(r.colliderect(shoe), f"dealer card {r} hits the shoe (n={n})")
            for r in scene.card_rects["player"]:
                self.assertFalse(r.colliderect(shoe), f"player card {r} hits the shoe (n={n})")

    def test_a_real_eleven_card_hand_and_a_long_dealer_hand_render(self):
        room, scene = self.open_table()
        # player: A A A A 2 2 2 2 3 3 3 = 21 in eleven cards (all legal: four Aces, four 2s ...)
        self.rig(scene, ("A", "5", "A", "6", "A", "A", "2", "2", "2", "2", "3", "3", "3", "4", "3"))
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        for _ in range(9):
            if scene.table.phase != scene.table.PLAYING:
                break
            self.frames(1, [key(pygame.K_a)])
            self.frames(30)
        self.frames(400)
        self.assertGreaterEqual(len(scene.table.round.player), 10)
        self.check(scene, "eleven cards")
        self.assertGreaterEqual(len(scene.card_rects["player"]), 10)
        for side in ("player", "dealer"):
            for r in scene.card_rects[side]:
                self.assertTrue(pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(r))

    def test_long_hands_stay_on_screen(self):
        room, scene = self.open_table()
        self.rig(scene, ("A", "2", "A", "3") + ("A", "A", "2", "2", "2", "4", "4", "4"))
        self.frames(1, [key(pygame.K_e)])
        self.frames(90)
        for _ in range(6):
            if scene.table.phase != scene.table.PLAYING:
                break
            self.frames(1, [key(pygame.K_a)])
            self.frames(40)
        self.check(scene, "long hand")


if __name__ == "__main__":
    unittest.main()
