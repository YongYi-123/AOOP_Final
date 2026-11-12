"""NEON CLAW (the claw machine in Prize Plaza): the rules and money (claw_machine.py), the game screen (claw_scene.py)
driven with real key events through the hub, its place in the room, the smaller capsule machines, and saving.

Run headless from this folder:   python3 -m unittest test_claw_machine -v
"""
import os
import random
import shutil
import tempfile
import unittest
import wave
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
import audio_synth  # noqa: E402
import claw_machine as cm  # noqa: E402
from claw_scene import ClawScene  # noqa: E402
from game import Game  # noqa: E402
from item_registry import COLLECTIBLE, ITEM_REGISTRY  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile, ProfileStore  # noqa: E402
from plaza_stations import COMPACT, FULL, CapsuleStation, ClawStation, ShowcaseStation  # noqa: E402
from prize_plaza import CLAW_POS, PrizePlazaScene  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import CLAW_PLAY_COST, CLAW_PLUSH_TICKETS, FLOOR_BOTTOM, SIDE_DOOR_H, SIDE_DOOR_Y, VIEW_H, VIEW_W  # noqa: E402
from stations import PrizeCounter, Station  # noqa: E402

DT = 1 / 60
K = pygame
CLAW_SOUNDS = ("claw_move", "claw_drop", "claw_grab", "claw_slip", "claw_chute", "claw_win", "claw_lose")


class FixedRoll(random.Random):
    """A Random whose random() always gives `value` (the grab roll); everything else is a normal seeded Random."""

    def __init__(self, value, seed=1):
        super().__init__(seed)
        self.value = value

    def random(self):
        return self.value


HOLDS, SLIPS = 0.0, 0.999


def key(k, up=False):
    return pygame.event.Event(pygame.KEYUP if up else pygame.KEYDOWN, key=k, mod=0, unicode="")


def profile(tokens=10, tickets=0, pid="claw"):
    return PlayerProfile(profile_id=pid, display_name="CLAWY", tokens=tokens, tickets=tickets)


def run(game, seconds, direction=0):
    for _ in range(int(round(seconds / DT))):
        game.update(DT, direction)


def aim_at(game, x):
    """Put the claw over x (as if steered there) while aiming."""
    assert game.phase == cm.AIM
    game.x = min(cm.MAX_X, max(cm.MIN_X, x))


def play(game, offset=0.0, target=1):
    """One whole attempt over plushie number `target` (left to right), `offset` px off its centre."""
    assert game.start()
    plush = sorted(game.plushies, key=lambda p: p.x)[target]
    aim_at(game, plush.x + offset)
    game.drop()
    for _ in range(3000):
        if game.phase == cm.IDLE:
            break
        game.update(DT)
    return game.attempt


# ===================================================================== rules
class MovementTests(unittest.TestCase):
    def setUp(self):
        self.p = profile()
        self.g = cm.ClawGame(self.p, rng=FixedRoll(HOLDS))

    def test_the_claw_only_moves_while_aiming(self):
        run(self.g, 1.0, direction=1)
        self.assertEqual(self.g.x, cm.HOME_X)                   # idle: the stick does nothing
        self.g.start()
        run(self.g, 0.5, direction=1)
        self.assertGreater(self.g.x, cm.HOME_X + 10)

    def test_movement_is_smooth_it_speeds_up_and_slows_down(self):
        self.g.start()
        self.g.update(DT, 1)
        self.assertLess(self.g.vx, cm.MOVE_SPEED)               # one frame does not reach full speed
        run(self.g, 0.5, direction=1)
        self.assertAlmostEqual(self.g.vx, cm.MOVE_SPEED)
        self.g.update(DT, 0)
        self.assertGreater(self.g.vx, 0)                         # letting go glides to a stop ...
        run(self.g, 0.5, direction=0)
        self.assertEqual(self.g.vx, 0)                           # ... quickly

    def test_the_claw_stops_at_both_walls(self):
        self.g.aim_time = 99
        self.g.start()
        run(self.g, 8, direction=1)
        self.assertEqual(self.g.x, cm.MAX_X)
        self.assertEqual(self.g.vx, 0)
        run(self.g, 8, direction=-1)
        self.assertEqual(self.g.x, cm.MIN_X)
        self.assertLess(cm.MAX_X, cm.FIELD_W)
        self.assertGreaterEqual(cm.MIN_X, 0)

    def test_the_claw_drops_by_itself_when_the_aim_timer_runs_out(self):
        self.g.start()
        run(self.g, cm.CLAW_AIM_TIME + 0.1)
        self.assertNotEqual(self.g.phase, cm.AIM)


class GrabTests(unittest.TestCase):
    def test_grab_odds_reward_a_centred_claw(self):
        for spec in cm.PLUSHIES:
            half = spec.width / 2
            centre = cm.grab_odds(0, spec)
            fair = cm.grab_odds(half - 0.5, spec)
            edge = cm.grab_odds(half + cm.PRONG_REACH - 0.5, spec)
            self.assertEqual(centre, spec.grip)
            self.assertGreater(centre, fair)
            self.assertGreater(fair, edge)
            self.assertGreater(edge, 0)
            self.assertEqual(cm.grab_odds(half + cm.PRONG_REACH + 0.5, spec), 0.0)
            self.assertEqual(cm.grab_odds(-2, spec), cm.grab_odds(2, spec))     # either side is the same

    def test_the_odds_are_fair_not_frustrating(self):
        for spec in cm.PLUSHIES:
            self.assertGreaterEqual(spec.grip, 0.7, spec.name)                 # a good drop usually works
            self.assertLessEqual(spec.grip, 0.95, spec.name)                   # but it is never certain

    def test_a_careful_player_wins_most_tries_and_a_careless_one_fewer(self):
        def wins(offset):
            g = cm.ClawGame(profile(tokens=1000), rng=random.Random(5))
            return sum(play(g, offset, target=i % 6).won for i in range(120))
        careful, sloppy = wins(0), wins(9)
        self.assertGreater(careful, 120 * 0.7)
        self.assertLess(sloppy, careful)

    def test_the_drop_aims_at_the_nearest_plushie_under_the_claw(self):
        g = cm.ClawGame(profile())
        g.start()
        plush = sorted(g.plushies, key=lambda p: p.x)[2]
        aim_at(g, plush.x + 1)
        self.assertIs(g.target_under(), plush)
        aim_at(g, cm.HOME_X)                                     # over the chute: nothing to grab
        self.assertIsNone(g.target_under())

    def test_a_drop_over_nothing_closes_on_air_and_pays_nothing(self):
        p = profile()
        g = cm.ClawGame(p, rng=FixedRoll(HOLDS))
        g.start()
        aim_at(g, cm.HOME_X)
        g.drop()
        run(g, 15)
        self.assertFalse(g.attempt.won)
        self.assertEqual((p.tickets, p.tokens), (0, 10 - CLAW_PLAY_COST))

    def test_hidden_prizes_are_never_stocked(self):
        secret = cm.PlushSpec("future_secret", "SECRET", 16, 14, 0.9, 1000, cm.PLUSHIES[0].look, hidden=True)
        rng = random.Random(1)
        picks = {cm.default_stock(rng, cm.PLUSHIES + (secret,)).item_id for _ in range(500)}
        self.assertNotIn("future_secret", picks)
        self.assertEqual(picks, {s.item_id for s in cm.PLUSHIES})


class MoneyTests(unittest.TestCase):
    def setUp(self):
        self.p = profile(tokens=10)

    def test_an_attempt_costs_exactly_the_configured_tokens_once(self):
        g = cm.ClawGame(self.p, rng=FixedRoll(SLIPS))
        self.assertEqual(CLAW_PLAY_COST, 2)
        self.assertTrue(g.start())
        self.assertEqual(self.p.tokens, 8)
        self.assertFalse(g.start())                              # already playing: refused, nothing charged
        g.drop()
        self.assertFalse(g.drop())
        run(g, 15)
        self.assertEqual(self.p.tokens, 8)
        self.assertEqual(self.p.lifetime_tokens_spent, 2)

    def test_the_cost_is_configurable(self):
        g = cm.ClawGame(self.p, cost=3)
        g.start()
        self.assertEqual(self.p.tokens, 7)

    def test_without_enough_tokens_nothing_happens(self):
        poor = profile(tokens=1)
        g = cm.ClawGame(poor)
        self.assertFalse(g.can_start())
        self.assertEqual(g.start_block_reason(), "NO TOKENS")
        self.assertFalse(g.start())
        self.assertEqual((poor.tokens, g.phase, g.attempts), (1, cm.IDLE, 0))

    def test_a_successful_grab_pays_its_tickets_and_puts_the_plushie_in_the_bag(self):
        g = cm.ClawGame(self.p, rng=FixedRoll(HOLDS))
        attempt = play(g)
        spec = attempt.target.spec
        self.assertTrue(attempt.won)
        self.assertEqual(self.p.tickets, CLAW_PLUSH_TICKETS[spec.item_id])
        self.assertEqual(self.p.inventory.get_quantity(spec.item_id), 1)
        self.assertTrue(attempt.item_added)
        self.assertEqual(g.session_tickets, attempt.tickets)

    def test_a_failed_grab_slips_back_and_pays_nothing(self):
        g = cm.ClawGame(self.p, rng=FixedRoll(SLIPS))
        before = len(g.plushies)
        g.start()
        target = sorted(g.plushies, key=lambda p: p.x)[1]
        aim_at(g, target.x)
        g.drop()
        events = []
        for _ in range(3000):
            g.update(DT)
            events += g.take_events()
            if g.phase == cm.IDLE:
                break
        self.assertIn("slip", events)
        self.assertIn("lose", events)
        self.assertNotIn("win", events)
        self.assertFalse(g.attempt.won)
        self.assertEqual(self.p.tickets, 0)
        self.assertEqual(sum(self.p.inventory.get_quantity(s.item_id) for s in cm.PLUSHIES), 0)
        self.assertIn(target, g.plushies)                        # it fell back into the machine
        self.assertEqual(len(g.plushies), before)
        self.assertLessEqual(abs(target.x - cm.SLOTS[target.slot]), 2.0)

    def test_a_prize_is_paid_once_even_if_settling_is_asked_again(self):
        g = cm.ClawGame(self.p, rng=FixedRoll(HOLDS))
        g.start()
        aim_at(g, sorted(g.plushies, key=lambda p: p.x)[0].x)
        g.drop()
        for _ in range(3000):
            g.update(DT)
            if g.phase == cm.WON:
                break
        paid = self.p.tickets
        self.assertGreater(paid, 0)
        g._settle(True)                                          # a second settle of the same attempt
        g._settle(True)
        run(g, 5)
        self.assertEqual(self.p.tickets, paid)
        self.assertEqual(g.wins, 1)

    def test_the_machine_restocks_after_a_win(self):
        g = cm.ClawGame(self.p, rng=FixedRoll(HOLDS))
        play(g)
        self.assertEqual(sorted(p.slot for p in g.plushies), list(range(len(cm.SLOTS))))

    def test_a_full_stack_still_pays_the_tickets(self):
        g = cm.ClawGame(self.p, rng=FixedRoll(HOLDS))
        for spec in cm.PLUSHIES:
            self.p.inventory.add_item(spec.item_id, ITEM_REGISTRY.get(spec.item_id).limit)
        attempt = play(g)
        self.assertTrue(attempt.won)
        self.assertFalse(attempt.item_added)
        self.assertEqual(self.p.tickets, attempt.tickets)

    def test_leaving_mid_attempt_plays_it_out_and_pays_what_it_wins(self):
        g = cm.ClawGame(self.p, rng=FixedRoll(HOLDS))
        g.start()
        aim_at(g, sorted(g.plushies, key=lambda p: p.x)[2].x)
        attempt = g.finish()                                     # the claw drops where it is
        self.assertEqual(g.phase, cm.IDLE)
        self.assertTrue(attempt.settled and attempt.won)
        self.assertEqual(self.p.tokens, 8)
        self.assertEqual(self.p.tickets, attempt.tickets)
        g.finish()                                               # nothing left to play: changes nothing
        self.assertEqual(self.p.tickets, attempt.tickets)

    def test_ticket_values_are_small_and_differ_by_plushie(self):
        values = [s.tickets for s in cm.PLUSHIES]
        self.assertEqual(len(cm.PLUSHIES), 6)
        self.assertEqual((min(values), max(values)), (3, 8))
        self.assertGreater(len(set(values)), 2)
        for spec in cm.PLUSHIES:
            self.assertEqual(spec.tickets, CLAW_PLUSH_TICKETS[spec.item_id])

    def test_no_new_currency_and_no_secret_reward(self):
        g = cm.ClawGame(self.p, rng=FixedRoll(HOLDS))
        for _ in range(4):
            play(g)
        self.assertIsNone(ITEM_REGISTRY.get("claw_secret_reward"))
        for spec in cm.PLUSHIES:
            self.assertFalse(spec.hidden)
        source = open(cm.__file__, encoding="utf-8").read() + open(ClawScene.__module__ + ".py", encoding="utf-8").read()
        self.assertNotIn("secret_item_found", source)
        self.assertNotIn('"claw_secret_reward"', source)


class SpecialHookTests(unittest.TestCase):
    def test_a_special_prize_can_be_stocked_and_heard_without_changing_the_machine(self):
        """The future hidden prize plugs in through `special`; nothing in the game uses it yet."""
        seen = []
        prize = cm.PlushSpec(cm.PLUSHIES[0].item_id, "TEST PRIZE", 16, 14, 0.9, 1, cm.PLUSHIES[0].look, hidden=True)

        class Special:
            def stock(self, game, slot):
                return prize if slot == 0 else None

            def on_win(self, game, spec, profile):
                seen.append(spec.name)
        p = profile()
        g = cm.ClawGame(p, rng=FixedRoll(HOLDS), special=Special())
        self.assertIs(next(q for q in g.plushies if q.slot == 0).spec, prize)
        play(g, target=0)
        self.assertEqual(seen, ["TEST PRIZE"])

    def test_the_ordinary_machine_has_no_special(self):
        self.assertIsNone(cm.ClawGame(profile()).special)


class LifetimeTests(unittest.TestCase):
    def test_claw_tickets_count_as_lifetime_tickets_but_not_as_an_arcade_floor_win(self):
        p = profile()
        attempt = play(cm.ClawGame(p, rng=FixedRoll(HOLDS)))
        self.assertEqual(p.lifetime_tickets_received, attempt.tickets)
        self.assertEqual(p.lifetime_tickets_won, attempt.tickets)
        self.assertEqual(p.lifetime_tickets_earned, 0)           # the "win Tickets from an Arcade Floor game" counter

    def test_a_claw_win_does_not_complete_the_arcade_floor_ticket_quest(self):
        p = profile()
        game = Game(session=LocalSession(p))
        self.addCleanup(game.quit)
        m = game.hub.story.manager
        with mock.patch.object(m, "handle", wraps=m.handle) as handle:
            play(cm.ClawGame(p, rng=FixedRoll(HOLDS)))
            game.step([], DT)
        self.assertNotIn(mock.call("tickets_earned"), handle.call_args_list)

    def test_saving_and_loading_keeps_the_prize(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        path = os.path.join(tmp, "p.json")
        store = ProfileStore(path)
        p = store.load()
        p.add_tokens(10, "TEST")
        store.autosave(p)
        attempt = play(cm.ClawGame(p, rng=FixedRoll(HOLDS)))
        again = ProfileStore(path).load()
        spec = attempt.target.spec
        self.assertEqual(again.tokens, p.tokens)
        self.assertEqual(again.tickets, attempt.tickets)
        self.assertEqual(again.inventory.get_quantity(spec.item_id), 1)
        self.assertEqual(again.lifetime_tickets_won, attempt.tickets)
        self.assertEqual(ProfileStore(path).load().tickets, attempt.tickets)    # reloading adds nothing


class ItemTests(unittest.TestCase):
    def test_every_plushie_is_a_stackable_collectible_with_an_icon(self):
        from item_icons import item_icon
        for spec in cm.PLUSHIES:
            d = ITEM_REGISTRY.get(spec.item_id)
            self.assertIsNotNone(d, spec.item_id)
            self.assertEqual(d.category, COLLECTIBLE)
            self.assertTrue(d.stackable)
            self.assertEqual(d.name, spec.name)
            self.assertIn(d.icon["shape"], ("plush", "bunny"))
            item_icon(d)

    def test_a_won_plushie_shows_in_the_collection_and_can_go_on_the_showcase(self):
        from collection import CollectionService
        from showcase import COLLECTIBLE_SLOT, ShowcaseService
        p = profile()
        spec = play(cm.ClawGame(p, rng=FixedRoll(HOLDS))).target.spec
        owned = {d.id for d, have in CollectionService(p).entries() if have}
        self.assertIn(spec.item_id, owned)
        self.assertTrue(ShowcaseService(p).choose(COLLECTIBLE_SLOT, spec.item_id))


class SoundTests(unittest.TestCase):
    def test_every_claw_sound_is_registered_generated_and_short(self):
        for name in CLAW_SOUNDS:
            with self.subTest(sound=name):
                self.assertIn(name, am.SFX_FILES)
                self.assertIn(name, audio_synth.SFX)
                self.assertIn(name, am.PRIORITY)
                with wave.open(os.path.join(am.ASSET_DIR, "sfx", f"{name}.wav")) as w:
                    seconds = w.getnframes() / w.getframerate()
                self.assertLess(seconds, 0.8)
                self.assertGreater(seconds, 0.3)

    def test_the_motor_never_cuts_off_anything_and_never_repeats_too_fast(self):
        self.assertEqual(am.PRIORITY["claw_move"], 0)
        self.assertGreaterEqual(am.MIN_GAP["claw_move"], 0.25)
        self.assertGreater(am.PRIORITY["claw_win"], am.PRIORITY["claw_grab"])


# ===================================================================== the hub
class HubBase(unittest.TestCase):
    tokens = 10

    def setUp(self):
        self.profile = profile(tokens=self.tokens)
        self.game = Game(session=LocalSession(self.profile))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "prize_plaza")
        self.room.popup = None
        self.claw = next(p for p in self.room.props if isinstance(p, ClawStation))
        self.played = []
        real = self.game.audio.play
        self.game.audio.play = lambda name, *a, **k: (self.played.append(name), real(name, *a, **k))[1]

    def frames(self, n=1, events=()):
        self.game.step(list(events), DT)
        for _ in range(n - 1):
            self.game.step([], DT)

    def walk_up(self):
        avatar = self.room.players[0]
        avatar.x, avatar.y = float(self.claw.zone.centerx), float(self.claw.zone.bottom - 2)
        self.frames(8)
        return avatar

    def open(self):
        self.walk_up()
        self.frames(1, [key(K.K_e)])
        self.frames(70)                                           # the wipe, then the short input delay
        scene = self.game.scenes.current
        self.assertIsInstance(scene, ClawScene)
        self.played.clear()                                       # (the room's own blip for the E that opened it)
        return scene


class PlacementTests(HubBase):
    def others(self):
        return [p for p in self.room.props if p is not self.claw and getattr(p, "rect", None) is not None
                and isinstance(p, Station) and p.rect.x >= 0]          # (Miao is a Station too, off-screen here)

    def test_the_claw_machine_stands_in_the_room_once(self):
        claws = [p for p in self.room.props if isinstance(p, ClawStation)]
        self.assertEqual(len(claws), 1)
        self.assertEqual(self.claw.rect.topleft, CLAW_POS)
        self.assertEqual(self.claw.prompt_label, "CLAW MACHINE")
        self.assertTrue(pygame.Rect(0, 64, VIEW_W, FLOOR_BOTTOM - 64).contains(self.claw.rect))

    def test_it_overlaps_no_other_machine_or_its_prompt_area(self):
        for other in self.others():
            self.assertFalse(self.claw.rect.colliderect(other.rect), other.prompt_label)
            self.assertFalse(self.claw.footprint.colliderect(other.footprint), other.prompt_label)
            self.assertFalse(self.claw.zone.colliderect(other.footprint), other.prompt_label)
            self.assertFalse(other.zone.colliderect(self.claw.footprint), other.prompt_label)

    def test_it_leaves_room_round_the_showcase_counter_and_doorway(self):
        stand = next(p for p in self.room.props if isinstance(p, ShowcaseStation))
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        self.assertGreaterEqual(self.claw.rect.top - 158, 12)                    # under the showcase dais
        self.assertGreaterEqual(self.claw.rect.top - stand.rect.bottom, 30)
        self.assertGreaterEqual(self.claw.rect.left - counter.rect.right, 20)
        door = pygame.Rect(0, SIDE_DOOR_Y, 70, SIDE_DOOR_H)                     # the HOME doorway and its mat
        self.assertFalse(self.claw.zone.colliderect(door))
        self.assertGreaterEqual(FLOOR_BOTTOM - self.claw.footprint.bottom, 40)  # a walkway in front of it

    def test_it_can_be_reached_on_foot_from_the_home_door(self):
        avatar = self.room.players[0]
        solids = self.room.solids
        size, step = avatar.feet.size, 4

        def free(x, y):
            rect = pygame.Rect(0, 0, *size)
            rect.midbottom = (x, y)
            return rect.collidelist(solids) == -1 and pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(rect)
        start = (int(avatar.x), int(avatar.y))
        seen, todo = {start}, [start]
        while todo:
            x, y = todo.pop()
            for nx, ny in ((x + step, y), (x - step, y), (x, y + step), (x, y - step)):
                if (nx, ny) not in seen and free(nx, ny):
                    seen.add((nx, ny))
                    todo.append((nx, ny))
        for target in [self.claw] + self.others():
            self.assertTrue([pt for pt in seen if target.zone.collidepoint(pt)], target.prompt_label)

    def test_its_prompt_covers_no_machine_and_stays_on_screen(self):
        avatar = self.walk_up()
        self.assertIs(avatar.nearby, self.claw)
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        self.room.draw(canvas)
        rect = avatar.prompt.place(self.room.prompt_avoid_rects() + [self.claw.rect], below_first=True)[0]
        self.assertTrue(pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(rect))
        for other in self.others() + [self.claw]:
            self.assertFalse(rect.colliderect(other.rect), other.prompt_label)

    def test_cats_and_miao_rest_outside_its_prompt_area(self):
        import miao_meow
        for name, spots in PrizePlazaScene.cat_spots.items():
            for spot in spots:
                self.assertFalse(self.claw.zone.collidepoint(spot), (name, spot))
        for name, spot in miao_meow.SPOTS[miao_meow.PLAZA].items():
            self.assertFalse(self.claw.zone.collidepoint(spot), name)

    def test_the_room_draws_with_the_machine_animating(self):
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        self.room.draw(canvas)
        before = pygame.image.tobytes(canvas.subsurface(self.claw.rect), "RGB")
        self.frames(90)
        self.room.draw(canvas)
        self.assertNotEqual(before, pygame.image.tobytes(canvas.subsurface(self.claw.rect), "RGB"))


class CapsuleSizeTests(HubBase):
    def test_the_capsule_machines_in_the_room_are_smaller_with_the_same_proportions(self):
        capsules = [p for p in self.room.props if isinstance(p, CapsuleStation)]
        self.assertEqual(len(capsules), 2)
        fw, fh = FULL["size"]
        for c in capsules:
            self.assertEqual(c.rect.size, COMPACT["size"])
            self.assertLess(c.rect.w * c.rect.h, fw * fh * 0.85)
            self.assertAlmostEqual(c.rect.w / c.rect.h, fw / fh, delta=0.02)
            self.assertLessEqual(c.footprint.w, 32)

    def test_the_pull_screen_still_shows_the_full_size_machine_and_works(self):
        from capsule import CAT
        from capsule_ui import CapsuleScene
        from plaza_stations import _capsule_sprite
        self.assertEqual(_capsule_sprite(CAT).get_size(), FULL["size"])
        self.profile.add_tickets(40)
        cat = next(p for p in self.room.props if isinstance(p, CapsuleStation) and p.capsule_kind == CAT)
        avatar = self.room.players[0]
        avatar.x, avatar.y = float(cat.zone.centerx), float(cat.zone.bottom - 2)
        self.frames(8)
        self.assertIs(avatar.nearby, cat)
        self.frames(1, [key(K.K_e)])
        self.frames(70)
        self.assertIsInstance(self.game.scenes.current, CapsuleScene)
        self.frames(1, [key(K.K_e)])
        self.frames(90)
        self.assertEqual(self.profile.tickets, 40 - 15)


class SceneTests(HubBase):
    def test_e_at_the_machine_opens_it_for_free_and_esc_goes_back_to_the_plaza(self):
        scene = self.open()
        self.assertIs(scene.profile, self.profile)
        self.assertEqual(self.profile.tokens, 10)                 # opening costs nothing
        self.assertEqual(self.game.music_for(self.game.scenes.stack), "prize_plaza")
        self.frames(1, [key(K.K_ESCAPE)])
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)

    def test_a_whole_attempt_with_real_keys(self):
        scene = self.open()
        scene.claw.rng = FixedRoll(HOLDS)
        self.frames(1, [key(K.K_e)])                              # START
        self.assertEqual(self.profile.tokens, 8)
        target = sorted(scene.claw.plushies, key=lambda p: p.x)[0]
        self.frames(1, [key(K.K_d)])                              # hold D ...
        for _ in range(600):
            if scene.claw.x >= target.x - 4.0:                    # let go a little early: it coasts
                break
            self.frames(1)
        self.frames(1, [key(K.K_d, up=True)])                     # ... let go
        self.frames(20)
        self.assertLessEqual(abs(scene.claw.x - target.x), 3)
        for _ in range(5):
            self.frames(1, [key(K.K_e)])                          # DROP, mashed: still one drop
        self.assertEqual(self.profile.tokens, 8)
        for _ in range(900):
            self.frames(1)
            if scene.claw.phase == cm.IDLE:
                break
        self.assertTrue(scene.claw.attempt.won)
        self.assertEqual(self.profile.tickets, target.spec.tickets)
        for name in ("token", "claw_move", "claw_drop", "claw_grab", "claw_chute", "claw_win"):
            self.assertIn(name, self.played)
        self.assertEqual(self.played.count("claw_win"), 1)
        self.assertLess(self.played.count("claw_move"), 12)       # the motor whirrs now and then, not every frame
        self.assertNotIn("confirm", self.played)                  # the machine makes its own sounds

    def test_arrow_keys_and_the_item_key_play_too(self):
        scene = self.open()
        self.frames(1, [key(K.K_SPACE)])                          # the item key starts
        self.assertEqual(scene.claw.phase, cm.AIM)
        x = scene.claw.x
        self.frames(1, [key(K.K_RIGHT)])
        self.frames(30)
        self.frames(1, [key(K.K_RIGHT, up=True)])
        self.assertGreater(scene.claw.x, x)
        self.frames(1, [key(K.K_RETURN)])                         # ENTER drops
        self.assertEqual(scene.claw.phase, cm.DROP)

    def test_the_press_that_opened_the_machine_is_not_a_start(self):
        self.walk_up()
        self.frames(1, [key(K.K_e)])
        self.frames(2, [key(K.K_e)])                              # a second quick press while it opens
        self.frames(30)
        self.assertEqual(self.profile.tokens, 10)

    def test_a_failed_attempt_shows_and_pays_nothing(self):
        scene = self.open()
        scene.claw.rng = FixedRoll(SLIPS)
        self.frames(1, [key(K.K_e)])
        aim_at(scene.claw, sorted(scene.claw.plushies, key=lambda p: p.x)[1].x)
        self.frames(1, [key(K.K_e)])
        lost = False
        for _ in range(900):
            self.frames(1)
            lost = lost or scene.claw.phase == cm.LOST
            if scene.claw.phase == cm.IDLE:
                break
        self.assertTrue(lost)
        self.assertTrue(scene.slipped)
        self.assertEqual((self.profile.tokens, self.profile.tickets), (8, 0))
        self.assertIn("claw_slip", self.played)
        self.assertIn("claw_lose", self.played)

    def test_leaving_mid_attempt_returns_safely_and_settles_it(self):
        scene = self.open()
        scene.claw.rng = FixedRoll(HOLDS)
        self.frames(1, [key(K.K_e)])
        aim_at(scene.claw, sorted(scene.claw.plushies, key=lambda p: p.x)[3].x)
        self.frames(1, [key(K.K_ESCAPE)])
        self.frames(40)
        self.assertIs(self.game.scenes.current, self.room)
        self.assertEqual(scene.claw.phase, cm.IDLE)
        self.assertTrue(scene.claw.attempt.settled)
        self.assertEqual(self.profile.tokens, 8)
        self.assertEqual(self.profile.tickets, scene.claw.attempt.tickets)
        self.assertTrue(scene.left_early)

    def test_closing_the_game_mid_attempt_settles_it(self):
        scene = self.open()
        scene.claw.rng = FixedRoll(HOLDS)
        self.frames(1, [key(K.K_e)])
        scene.on_quit()
        self.assertTrue(scene.claw.attempt.settled)
        self.assertEqual(self.profile.tokens, 8)

    def test_the_screen_draws_in_every_phase(self):
        scene = self.open()
        scene.claw.rng = FixedRoll(HOLDS)
        surf = pygame.Surface((VIEW_W, VIEW_H))
        self.frames(1, [key(K.K_e)])
        aim_at(scene.claw, sorted(scene.claw.plushies, key=lambda p: p.x)[2].x)
        self.frames(1, [key(K.K_e)])
        phases = set()
        for _ in range(900):
            self.frames(1)
            scene.draw(surf)
            phases.add(scene.claw.phase)
            if scene.claw.phase == cm.IDLE:
                break
        self.assertTrue({cm.DROP, cm.GRAB, cm.LIFT, cm.CARRY, cm.RELEASE, cm.WON} <= phases)


class NoTokensTests(HubBase):
    tokens = 1

    def test_without_tokens_it_opens_but_refuses_to_start(self):
        scene = self.open()
        self.frames(1, [key(K.K_e)])
        self.assertEqual(scene.claw.phase, cm.IDLE)
        self.assertEqual(self.profile.tokens, 1)
        self.assertEqual(scene.alert, "NOT ENOUGH TOKENS")
        self.assertIn("cancel", self.played)
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))


class ChapterTests(unittest.TestCase):
    def test_it_is_open_in_every_main_quest_state_and_never_reports_a_secret(self):
        for veteran in (False, True):
            p = profile(tokens=10)
            if veteran:
                p.record_game_played("puzzle_drop")
            game = Game(session=LocalSession(p))
            self.addCleanup(game.quit)
            sent = []
            real = game.session.dispatch
            game.session.dispatch = lambda e: (sent.append(e.type), real(e))[1]
            room = goto_room(game, "prize_plaza")
            room.open_claw()
            for _ in range(40):
                game.step([], DT)
            scene = game.scenes.current
            self.assertIsInstance(scene, ClawScene)
            scene.claw.rng = FixedRoll(HOLDS)
            scene.press()
            aim_at(scene.claw, scene.claw.plushies[0].x)
            scene.claw.finish()
            self.assertTrue(scene.claw.attempt.won)
            self.assertNotIn("secret_item_found", sent)


if __name__ == "__main__":
    unittest.main()
