"""Regression tests for the Prize Plaza polish pass: capsule sounds, the showcase car in the player's
own paint, the discoverable GARAGE / CUSTOMIZE CAR entry, and the centre layout (paths, cats, prompts).

Run headless from this folder:   python -m unittest test_plaza_polish -v
"""
import os
import unittest
import wave
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import audio_manager as am  # noqa: E402
import audio_synth  # noqa: E402
import car_preview  # noqa: E402
import capsule_ui  # noqa: E402
import shop_ui  # noqa: E402
from audio_manager import AudioManager  # noqa: E402
from capsule import CAT, RETRO  # noqa: E402
from capsule_ui import DROP_TIME, OPEN_TIME, TURN_TIME, CapsuleScene  # noqa: E402
from game import Game  # noqa: E402
from local_session import LocalSession  # noqa: E402
from player_profile import PlayerProfile  # noqa: E402
from plaza_stations import CapsuleStation, ShowcaseStation, option_icon  # noqa: E402
from prize_plaza import LUCKY_POS, PrizePlazaScene  # noqa: E402
from racing_progression.service import PrizeService  # noqa: E402
from racing_progression.ui import GarageScene, PrizeCounterScene  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import VIEW_H, VIEW_W  # noqa: E402
from showcase import CAR, ShowcaseService  # noqa: E402
from shop_ui import RACING, TABS, ShopScene  # noqa: E402
from stations import PrizeCounter  # noqa: E402

DT = 1 / 60
CAPSULE_SOUNDS = ("capsule_turn", "capsule_drop", "capsule_pop_cat", "capsule_pop_retro")


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def pixels(surface):
    return pygame.image.tobytes(surface, "RGBA")


class SoundTests(unittest.TestCase):
    def test_every_capsule_sound_is_registered_generated_and_within_the_asset_limits(self):
        for name in CAPSULE_SOUNDS:
            with self.subTest(sound=name):
                self.assertIn(name, am.SFX_FILES)
                self.assertIn(name, audio_synth.SFX)
                self.assertIn(name, am.PRIORITY)
                self.assertIn(name, am.SFX_GAIN)
                path = os.path.join(am.ASSET_DIR, "sfx", f"{name}.wav")
                with wave.open(path) as w:
                    seconds = w.getnframes() / w.getframerate()
                self.assertLess(seconds, 0.8)
                self.assertGreater(seconds, 0.3)

    def test_the_crank_never_cuts_off_the_drop_or_the_pop(self):
        self.assertLess(am.PRIORITY["capsule_turn"], am.PRIORITY["capsule_drop"])
        self.assertGreaterEqual(am.PRIORITY["capsule_pop_cat"], am.PRIORITY["capsule_drop"])

    def test_the_two_machines_have_different_pops(self):
        cat, retro = audio_synth.sfx_capsule_pop_cat(), audio_synth.sfx_capsule_pop_retro()
        self.assertNotEqual(cat, retro)

    def test_the_sounds_play_through_the_audio_manager_and_obey_mute_and_volume(self):
        pygame.mixer.init()
        a = AudioManager()
        self.addCleanup(a.stop)
        a.preload()
        for name in CAPSULE_SOUNDS:
            self.assertIn(name, a.sounds)
        a.set_muted(True)
        a.time += 1
        a.play("capsule_pop_cat")
        self.assertEqual(a.effective_sfx, 0.0)
        a.set_muted(False)
        a.set_volumes(sfx=0.25)
        self.assertEqual(a.effective_sfx, 0.25)


class RoomBase(unittest.TestCase):
    def setUp(self):
        self.profiles = [PlayerProfile(profile_id="pol_a", tickets=500), PlayerProfile(profile_id="pol_b", tickets=500)]
        self.game = Game(session=LocalSession(self.profiles))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "prize_plaza")
        for cat in self.room.cats:
            cat.x, cat.y = -50.0, -50.0

    def frames(self, n=30):
        for _ in range(n):
            self.game.step([], DT)

    def key(self, k):
        self.game.step([key_event(k)], DT)


class CapsuleSoundSequenceTests(RoomBase):
    def sounds_for(self, kind):
        scene = CapsuleScene(self.game, self.game.session.primary, kind)
        played = []
        scene.play = played.append
        scene.lock = 0
        scene.pull()
        for _ in range(int((DROP_TIME + OPEN_TIME) * 60) + 10):
            scene.update(DT)
        return played, scene

    def test_turn_then_drop_then_pop_in_that_order_for_each_machine(self):
        for kind in (CAT, RETRO):
            played, scene = self.sounds_for(kind)
            self.assertEqual(played[:3], ["capsule_turn", "capsule_drop", f"capsule_pop_{kind}"], kind)
            self.assertEqual(scene.phase, "shown")

    def test_a_refused_pull_makes_only_the_cancel_sound(self):
        self.profiles[0].spend_tickets(495)
        scene = CapsuleScene(self.game, self.game.session.primary, RETRO)
        played = []
        scene.play = played.append
        scene.lock = 0
        scene.pull()
        self.assertEqual(played, ["cancel"])

    def test_each_sound_plays_once_per_pull(self):
        played, _ = self.sounds_for(CAT)
        self.assertEqual(sorted(played), sorted(set(played)))

    def test_the_knob_turns_and_the_capsule_only_falls_after_the_turn(self):
        scene = CapsuleScene(self.game, self.game.session.primary, CAT)
        scene.lock = 0
        scene.pull()
        surf = pygame.Surface((VIEW_W, VIEW_H))
        scene.update(TURN_TIME / 2)
        scene.draw(surf)
        self.assertFalse(scene.dropped)
        scene.update(TURN_TIME)
        scene.draw(surf)
        self.assertTrue(scene.dropped)

    def test_the_owned_count_and_duplicate_indicator_show_after_pulling_the_same_item_twice(self):
        texts = []
        real = capsule_ui.draw_text

        def spy(surf, text, *a, **k):
            texts.append(text)
            return real(surf, text, *a, **k)

        from test_capsule import Picks
        scene = CapsuleScene(self.game, self.game.session.primary, CAT, rng=Picks("cat_bell_charm"))
        with mock.patch.object(capsule_ui, "draw_text", spy):
            for _ in range(2):
                scene.lock = 0
                scene.pull()
                scene.update(DROP_TIME + 0.01)
                scene.update(OPEN_TIME + 0.01)
                scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertIn("NEW!", texts)
        self.assertIn("DUPLICATE X2", texts)
        self.assertIn("X2", texts)                                  # the prize list's owned count


class ShowcasePaintTests(RoomBase):
    def paint(self, profile, key):
        PrizeService(profile).buy("paint", key)
        profile.set_racing_selection("paint", key)

    def test_the_showcase_car_uses_the_saved_paint(self):
        p = self.profiles[0]
        factory = car_preview.car_image(p, "falcon", 30)
        self.assertIsNotNone(factory)
        self.paint(p, "ice")
        painted = car_preview.car_image(p, "falcon", 30)
        self.assertNotEqual(pixels(factory), pixels(painted))
        self.assertEqual(car_preview.paint_key(p), "ice")

    def test_it_is_the_same_sprite_the_garage_preview_uses(self):
        from racing_progression.service import RacingGarage
        p = self.profiles[0]
        self.paint(p, "crimson")
        scene = GarageScene(self.game, self.game.session.primary)
        spec = scene.preview.spec("falcon")
        livery = scene.progression_factory(RacingGarage(p)).livery(spec)
        self.assertEqual(livery.primary, (225, 45, 70))             # the catalogue's CRIMSON RED
        mine = car_preview.car_image(p, "falcon", 30)
        self.assertEqual(pixels(mine), pixels(car_preview._racer[2].car_sprite(spec.style.key, 30, 0, livery)))

    def test_p1_and_p2_cars_use_their_own_paint(self):
        a, b = self.profiles
        self.paint(a, "neon")
        self.paint(b, "amber")
        self.assertNotEqual(pixels(car_preview.car_image(a, "falcon", 30)), pixels(car_preview.car_image(b, "falcon", 30)))
        self.assertEqual(b.racing_selection["paint"], "amber")
        self.assertEqual(a.racing_selection["paint"], "neon")

    def test_every_owned_car_renders_in_every_owned_paint(self):
        p = self.profiles[0]
        for car in ("comet", "viper", "titan"):
            PrizeService(p).buy("car", car)
        self.paint(p, "violet")
        for car in ("falcon", "comet", "viper", "titan"):
            image = car_preview.car_image(p, car, 30)
            self.assertIsNotNone(image, car)
            self.assertEqual(image.get_width(), 30)
            self.assertEqual(option_icon(ShowcaseService(p).displayed(CAR) or ShowcaseService(p).options(CAR)[0], 1, p).get_width(), 22)

    def test_the_room_stand_changes_when_the_paint_changes(self):
        p = self.profiles[0]
        ShowcaseService(p).choose(CAR, "falcon")
        stand = next(s for s in self.room.props if isinstance(s, ShowcaseStation))
        stand.time = 100.0

        def snap():
            stand.refresh()
            surf = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            stand.draw(surf)
            return pixels(surf)

        before = snap()
        self.paint(p, "neon")
        self.assertNotEqual(before, snap())

    def test_without_the_racer_the_simple_car_is_used(self):
        p = self.profiles[0]
        option = ShowcaseService(p).options(CAR)[0]
        with mock.patch.object(car_preview, "_load", return_value=None):
            icon = option_icon(option, 1, p)
        self.assertIsNotNone(icon)
        stand = next(s for s in self.room.props if isinstance(s, ShowcaseStation))
        ShowcaseService(p).choose(CAR, "falcon")
        with mock.patch.object(car_preview, "_load", return_value=None):
            stand.refresh()
            stand.draw(pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA))

    def test_the_showcase_screen_draws_cars_in_paint(self):
        from showcase_ui import ShowcaseScene
        self.paint(self.profiles[0], "tuxedo")
        scene = ShowcaseScene(self.game, self.game.session.primary)
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))


class GarageDiscoverabilityTests(RoomBase):
    def racing_tab(self):
        self.room.open_prize_counter()
        self.frames()
        scene = self.game.scenes.current
        self.assertIsInstance(scene, ShopScene)
        scene.set_tab(TABS.index(RACING))
        return scene

    def drawn_text(self, module, scene):
        texts = []
        real = module.draw_text

        def spy(surf, text, *a, **k):
            texts.append(text)
            return real(surf, text, *a, **k)

        with mock.patch.object(module, "draw_text", spy):
            scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        return texts

    def test_the_racing_tab_labels_the_garage_clearly(self):
        scene = self.racing_tab()
        texts = self.drawn_text(shop_ui, scene)
        self.assertIn("GARAGE / CUSTOMIZE CAR", texts)
        self.assertTrue(any("GARAGE" in t and "CHOOSE" in t for t in texts))
        self.assertIn("OPEN RACING PRIZES", texts)
        self.assertIn("GARAGE / CUSTOMIZE CAR", scene.idle_message())

    def test_the_bag_key_on_the_racing_tab_opens_the_garage_for_the_same_player(self):
        scene = self.racing_tab()
        self.key(pygame.K_i)
        self.frames(40)
        garage = self.game.scenes.current
        self.assertIsInstance(garage, GarageScene)
        self.assertIs(garage.owner, scene.owner)
        self.key(pygame.K_ESCAPE)
        self.frames(40)
        self.assertIs(self.game.scenes.current, scene)

    def test_clicking_the_garage_button_opens_it(self):
        scene = self.racing_tab()
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        rect, callback = next((r, c) for r, c in scene._hit if r.w == 140 and r.y > 100 and r.y < 200
                              and c == scene.open_garage)
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                              pos=self._canvas_to_screen(rect.center)))
        self.frames(40)
        self.assertIsInstance(self.game.scenes.current, GarageScene)

    def _canvas_to_screen(self, pos):
        w, h = self.game.screen.get_size()
        from display import screen_to_canvas
        for x in range(0, w, 2):                               # find the screen pixel that maps onto `pos`
            for y in range(0, h, 2):
                if screen_to_canvas((x, y), (w, h)) == pos:
                    return (x, y)
        self.fail("no screen position maps to the button")

    def test_p2_reaches_their_own_garage(self):
        self.room.acting_player = self.room.players[1]
        self.room.open_prize_counter()
        self.frames()
        scene = self.game.scenes.current
        scene.set_tab(TABS.index(RACING))
        scene.on_action("menu")
        self.frames(40)
        garage = self.game.scenes.current
        self.assertIsInstance(garage, GarageScene)
        self.assertIs(garage.profile if hasattr(garage, "profile") else garage.owner.profile, self.profiles[1])

    def test_the_racing_counter_hint_names_the_garage_and_the_players_own_key(self):
        self.room.open_racing_counter()
        self.frames()
        scene = self.game.scenes.current
        self.assertIsInstance(scene, PrizeCounterScene)
        shown = []
        real = scene.text
        scene.text = lambda surface, text, pos, *a, **k: (shown.append(text), real(surface, text, pos, *a, **k))[1]
        scene.draw(pygame.Surface((VIEW_W, VIEW_H)))
        self.assertTrue(any("GARAGE / CUSTOMIZE CAR" in t and " I " in t for t in shown), shown)

    def test_garage_still_selects_cars_and_paints(self):
        PrizeService(self.profiles[0]).buy("car", "viper")
        scene = GarageScene(self.game, self.game.session.primary)
        self.game.scenes.push(scene)
        self.frames(40)
        self.key(pygame.K_s)
        self.key(pygame.K_e)
        self.assertEqual(self.profiles[0].racing_selection["car"], "viper")


class LayoutTests(RoomBase):
    def solids(self):
        return self.room.solids + self.room.cats.blockers(self.room.players[0])

    def test_every_station_zone_can_be_reached_on_foot_from_the_home_door(self):
        """Flood-fill the walkable floor (feet-sized steps) from where the player arrives."""
        avatar = self.room.players[0]
        solids = self.room.solids
        size = avatar.feet.size
        step = 4

        def free(x, y):
            rect = pygame.Rect(0, 0, *size)
            rect.midbottom = (x, y)
            return rect.collidelist(solids) == -1 and pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(rect)

        start = (int(avatar.x), int(avatar.y))
        self.assertTrue(free(*start))
        seen, todo = {start}, [start]
        while todo:
            x, y = todo.pop()
            for nx, ny in ((x + step, y), (x - step, y), (x, y + step), (x, y - step)):
                if (nx, ny) not in seen and free(nx, ny):
                    seen.add((nx, ny))
                    todo.append((nx, ny))
        targets = [p for p in self.room.props if isinstance(p, (CapsuleStation, ShowcaseStation, PrizeCounter))]
        targets += [p for p in self.room.interactables if hasattr(p, "kind")]          # the Lucky Corner machines
        self.assertGreaterEqual(len(targets), 9)
        for t in targets:
            reachable = [pt for pt in seen if t.zone.collidepoint(pt)]
            self.assertTrue(reachable, f"{t.prompt_label} cannot be reached")

    def test_walkways_stay_open_between_the_zones(self):
        stand = next(p for p in self.room.props if isinstance(p, ShowcaseStation))
        counter = next(p for p in self.room.props if isinstance(p, PrizeCounter))
        capsules = [p for p in self.room.props if isinstance(p, CapsuleStation)]
        lucky = [p for p in self.room.props if hasattr(p, "kind")]
        self.assertGreaterEqual(stand.rect.left - counter.rect.right, 12)                   # counter | showcase
        self.assertGreaterEqual(min(c.rect.left for c in capsules) - stand.rect.right, 12)  # showcase | capsules
        self.assertGreaterEqual(min(m.rect.left for m in lucky) - stand.rect.right, 12)     # showcase | lucky corner
        top_row = [m for m in lucky if m.rect.top < LUCKY_POS[1] + 20]
        bottom_row = [m for m in lucky if m.rect.top >= LUCKY_POS[1] + 20]
        self.assertGreaterEqual(min(m.rect.top for m in bottom_row) - max(m.rect.bottom for m in top_row), 20)

    def test_cat_resting_spots_stay_clear_of_the_new_machines_and_their_prompt_zones(self):
        cats = PrizePlazaScene.cat_spots
        pieces = [p for p in self.room.props if isinstance(p, (CapsuleStation, ShowcaseStation))]
        for name, spots in cats.items():
            for spot in spots:
                self.assertTrue(self.room.cats.is_free(spot), (name, spot))
                for piece in pieces:
                    self.assertFalse(piece.zone.collidepoint(spot), (name, spot, piece.prompt_label))

    def test_the_cats_walk_the_room_without_ending_up_inside_the_new_furniture(self):
        room = goto_room(self.game, "prize_plaza")
        pieces = [p.footprint for p in room.props if isinstance(p, (CapsuleStation, ShowcaseStation))]
        for cat in room.cats:                                      # let them wander
            cat.x, cat.y = 150.0, 168.0
        self.frames(600)
        for cat in room.cats:
            self.assertEqual(cat.feet.collidelist(pieces), -1, cat.name)

    def test_prompts_for_the_new_machines_cover_no_other_machine_or_sign(self):
        avoid_all = self.room.prompt_avoid_rects()
        canvas = pygame.Surface((VIEW_W, VIEW_H))
        for target in [p for p in self.room.props if isinstance(p, (CapsuleStation, ShowcaseStation))]:
            avatar = self.room.players[0]
            avatar.x, avatar.y = float(target.zone.centerx), float(target.zone.bottom - 2)
            self.frames(8)
            self.assertIs(avatar.nearby, target)
            self.room.draw(canvas)
            rect = avatar.prompt.place(avoid_all + [target.rect], below_first=True)[0]
            self.assertTrue(pygame.Rect(0, 0, VIEW_W, VIEW_H).contains(rect), target.prompt_label)
            for other in self.room.props:
                if other is not target and getattr(other, "rect", None) is not None:
                    self.assertFalse(rect.colliderect(other.rect), (target.prompt_label, other.prompt_label))
            self.assertFalse(rect.colliderect(target.rect), target.prompt_label)
            for cabinet in (c for c in self.room.props if hasattr(c, "kind")):          # Lucky Corner machines
                self.assertFalse(rect.colliderect(cabinet.rect), (target.prompt_label, cabinet.prompt_label))

    def test_the_capsule_and_showcase_prompts_name_the_right_thing(self):
        labels = sorted(p.prompt_label for p in self.room.props if isinstance(p, (CapsuleStation, ShowcaseStation)))
        self.assertEqual(labels, ["CAT CAPSULE", "RETRO CAPSULE", "SHOWCASE"])

    def test_nothing_else_enters_the_lucky_corner_block(self):
        lucky = pygame.Rect(LUCKY_POS[0] - 14, LUCKY_POS[1] - 20, 122, 128)
        for p in self.room.props:
            if isinstance(p, (CapsuleStation, ShowcaseStation, PrizeCounter)):
                self.assertFalse(lucky.colliderect(p.rect), p.prompt_label)
        for cat in self.room.cats:
            for spot in cat.spots:
                self.assertFalse(lucky.collidepoint(spot), (cat.name, spot))


if __name__ == "__main__":
    unittest.main()
