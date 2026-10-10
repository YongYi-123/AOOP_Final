"""Retro Racer presentation / playability tests: logical surface, uniform scaling,
hub UI hidden, racer HUD, key labels, banner and spectator placement, return to the hub.

Run with:  python -m unittest test_racer_ui
"""
import os
import re
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from controls import P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS  # noqa: E402
from retro_racer_scene import (RACER_SIZE, SPECTATOR_Y, RetroRacerScene, fit_rect,  # noqa: E402
                               racer_key_labels)
from test_multiplayer import TwoPlayerTest, key  # noqa: E402

RETRO_SETTINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "retro_racer", "settings.py")


class ScalingTests(unittest.TestCase):
    def test_the_logical_size_is_what_the_racer_is_laid_out_for(self):
        with open(RETRO_SETTINGS) as f:
            text = f.read()
        w, h = map(int, re.search(r"WIDTH, HEIGHT = (\d+), (\d+)", text).groups())
        self.assertEqual(RACER_SIZE, (w, h))

    def test_fit_rect_scales_uniformly_and_centres(self):
        self.assertEqual(fit_rect((800, 600), (800, 600)), pygame.Rect(0, 0, 800, 600))
        self.assertEqual(fit_rect((800, 600), (1600, 1200)), pygame.Rect(0, 0, 1600, 1200))
        self.assertEqual(fit_rect((800, 600), (1200, 600)), pygame.Rect(200, 0, 800, 600))   # pillarbox
        self.assertEqual(fit_rect((800, 600), (400, 600)), pygame.Rect(0, 150, 400, 300))    # letterbox
        for size in ((640, 480), (1024, 576), (1920, 1080), (500, 500), (333, 777)):
            r = fit_rect(RACER_SIZE, size)
            self.assertLessEqual(r.w, size[0])
            self.assertLessEqual(r.h, size[1])
            self.assertTrue(r.w == size[0] or r.h == size[1])          # fills one dimension
            self.assertAlmostEqual(r.w / r.h, 800 / 600, delta=0.02)   # never stretched
            self.assertAlmostEqual(r.centerx, size[0] / 2, delta=1)
            self.assertAlmostEqual(r.centery, size[1] / 2, delta=1)


class RacerUITest(TwoPlayerTest):
    def start_racer(self, starter, other, ready=True):
        room = self.arcade()
        machine = self.machine(room, "retro_racer")
        self.stand_at(starter, machine)
        if other is not None:
            self.stand_at(other, machine, dx=-150)
        self.frames(5)
        self.use(starter)
        self.frames(1, [key(starter.controls.interact[0])])
        for _ in range(60):
            self.frames(1)
        scene = self.game.scenes.current
        self.assertIsInstance(scene, RetroRacerScene)
        for _ in range(400):
            self.frames(1)
            if scene.racer is not None:
                break
        self.assertIsNotNone(scene.racer, scene.error)
        self.frames(3)
        return room, scene

    def to_countdown(self, scene, starter):
        for _ in range(4):
            self.frames(1, [key(starter.controls.interact[0])])
            self.frames(3)
        self.assertEqual(scene.racer.state.name, "COUNTDOWN")

    def to_race(self, scene):
        for _ in range(600):
            self.frames(1)
            if scene.racer.state.name == "PLAYING":
                break
        self.assertEqual(scene.racer.state.name, "PLAYING")


class SurfaceTests(RacerUITest):
    def test_the_racer_renders_into_its_own_logical_surface(self):
        room, scene = self.start_racer(self.p1, self.p2)
        self.assertEqual(scene.surface.get_size(), RACER_SIZE)
        self.assertIs(scene.racer.screen, scene.surface)
        self.assertIsNot(scene.racer.screen, self.game.screen)

    def test_it_presents_correctly_at_other_window_sizes(self):
        room, scene = self.start_racer(self.p1, self.p2)
        self.to_countdown(scene, self.p1)
        scene.racer.screen = scene.surface
        scene.racer.render()
        for size in ((800, 600), (640, 480), (1200, 600), (400, 600), (1600, 900), (1024, 768)):
            window = pygame.Surface(size)
            window.fill((9, 9, 9))
            scene.draw(window)                                      # must not raise or crop
            rect = fit_rect(RACER_SIZE, size)
            if rect.w < size[0]:                                    # side bars are black
                self.assertEqual(window.get_at((0, size[1] // 2))[:3], (0, 0, 0), size)
            if rect.h < size[1]:
                self.assertEqual(window.get_at((size[0] // 2, 0))[:3], (0, 0, 0), size)
            self.assertNotEqual(window.get_at(rect.center)[:3], (0, 0, 0))
        self.assertEqual(scene.surface.get_size(), RACER_SIZE)      # the logical size never changes

    def test_the_default_window_is_not_scaled_at_all(self):
        room, scene = self.start_racer(self.p1, None)
        window = pygame.Surface(RACER_SIZE)
        scene.draw(window)
        self.assertEqual(pygame.image.tobytes(window, "RGB"), pygame.image.tobytes(scene.surface, "RGB"))


class HubHiddenTests(RacerUITest):
    def test_no_hub_layer_is_drawn_while_the_racer_is_active(self):
        room, scene = self.start_racer(self.p1, self.p2)
        calls = []
        room.draw = lambda surf: calls.append("room")
        for hud in self.game.hub.huds:
            hud.draw = lambda surf, hud=hud: calls.append("hud")
        self.to_countdown(scene, self.p1)
        self.frames(5)
        self.assertIs(self.game.scenes.current, scene)
        self.assertEqual(calls, [])
        self.assertTrue(scene.full_resolution)

    def test_the_hub_does_not_update_under_the_racer(self):
        room, scene = self.start_racer(self.p1, self.p2)
        before = [(p.x, p.y) for p in self.session.avatars]
        self.frames(1, [key(pygame.K_w), key(pygame.K_UP), key(pygame.K_a), key(pygame.K_LEFT)])
        self.frames(30)
        self.assertEqual([(p.x, p.y) for p in self.session.avatars], before)

    def test_the_racers_own_hud_is_drawn(self):
        room, scene = self.start_racer(self.p1, self.p2)
        self.to_countdown(scene, self.p1)
        seen = []
        hud = scene.racer.hud
        real = hud.draw_hud
        hud.draw_hud = lambda *a: (seen.append(1), real(*a))[1]
        self.frames(3)
        hud.draw_hud = real
        self.assertTrue(seen)

    def test_the_countdown_is_drawn_centred_and_the_timer_waits_for_go(self):
        room, scene = self.start_racer(self.p1, self.p2)
        self.to_countdown(scene, self.p1)
        labels = []
        hud = scene.racer.hud
        real = hud.draw_countdown
        hud.draw_countdown = lambda surf, label: (labels.append(label), real(surf, label))[1]
        manager = scene.racer.manager
        left = manager.time_left
        for _ in range(200):
            self.frames(1)
            if scene.racer.state.name == "PLAYING":
                break
            self.assertEqual(manager.time_left, left)               # no clock before GO
        hud.draw_countdown = real
        self.assertTrue({"3", "2", "1"} & set(labels))
        window = pygame.Surface(RACER_SIZE)
        scene.racer.state = type(scene.racer.state)["COUNTDOWN"]
        scene.racer.count_label = "3"
        scene.draw(window)
        digit = window.subsurface(pygame.Rect(300, 150, 200, 150))
        self.assertGreater(pygame.mask.from_threshold(digit, (255, 60, 60), (40, 40, 40, 255)).count(), 100)

    def test_the_result_screen_is_the_racers_own_and_fits(self):
        room, scene = self.start_racer(self.p1, self.p2)
        self.to_countdown(scene, self.p1)
        self.to_race(scene)
        scene.racer.manager.time_left = 0.01
        for _ in range(120):
            self.frames(1)
        self.assertEqual(scene.racer.state.name, "GAME_OVER")
        drawn = []
        hud = scene.racer.hud
        real = hud.draw_end
        hud.draw_end = lambda *a: (drawn.append(1), real(*a))[1]
        self.frames(3)
        hud.draw_end = real
        self.assertTrue(drawn)
        self.assertIs(self.game.scenes.current, scene)

    def test_leaving_restores_the_hub_and_ownership(self):
        room, scene = self.start_racer(self.p2, self.p1)
        positions = [(p.x, p.y) for p in self.session.avatars]
        self.assertEqual(self.b.tokens, self.P2_TOKENS - 1)
        self.frames(1, [key(pygame.K_ESCAPE)])                      # ESC on the racer's title quits
        for _ in range(80):
            self.frames(1)
        self.assertIs(self.game.scenes.current, room)
        self.assertEqual(len(room.players), 2)
        self.assertEqual([(p.x, p.y) for p in self.session.avatars], positions)
        self.assertEqual((self.a.tokens, self.b.tokens), (self.P1_TOKENS, self.P2_TOKENS - 1))
        self.assertEqual(self.b.total_games_played, 1)
        self.assertEqual(self.a.total_games_played, 0)
        surf = pygame.Surface((400, 300))
        room.draw(surf)                                             # the hub draws again (HUDs included)
        self.assertEqual([h.profile for h in room.huds], [self.a, self.b])


class KeyLabelTests(RacerUITest):
    def test_labels_name_the_players_own_keys(self):
        p1, p2, solo = (racer_key_labels(s) for s in (P1_CONTROLS, P2_CONTROLS, SOLO_CONTROLS))
        self.assertEqual((p1["accelerate"], p1["confirm"], p1["steer"]), ("W", "E", "A  D"))
        self.assertEqual((p2["accelerate"], p2["steer"]), ("UP", "LEFT  RIGHT"))
        self.assertIn("ENTER", p2["confirm"])
        self.assertEqual(solo["accelerate"], "W/UP")
        self.assertEqual(solo["confirm"], "E/ENTER")
        self.assertEqual(p1["item"], "SPACE/SHIFT")

    def test_the_racer_screens_show_the_starters_keys(self):
        room, scene = self.start_racer(self.p2, self.p1)
        self.assertEqual(scene.racer.hud.keys["accelerate"], "UP")
        self.assertIn("ENTER", scene.racer.hud.keys["confirm"])
        self.frames(1, [key(pygame.K_ESCAPE)])
        for _ in range(80):
            self.frames(1)
        room, scene = self.start_racer(self.p1, self.p2)           # the shared racer is relabelled
        self.assertEqual(scene.racer.hud.keys["accelerate"], "W")
        self.assertEqual(scene.racer.hud.keys["confirm"], "E")

    def test_enter_still_works_in_a_one_player_session(self):
        from game import Game
        import tempfile
        from machine import ArcadeMachine
        with tempfile.TemporaryDirectory() as d:
            g = Game(save_path=os.path.join(d, "s.json"))
            machine = ArcadeMachine({"id": "retro_racer", "name": "R", "marquee": "RACE", "description": "",
                                     "x": 36, "neon": (255, 72, 72), "accent": (255, 168, 60),
                                     "screen": "racer"})
            scene = RetroRacerScene(g, machine)
            scene.attach_players([g.session.primary])
            self.assertEqual(scene.racer_event(key(pygame.K_RETURN)).key, pygame.K_RETURN)
            self.assertEqual(scene.racer_event(key(pygame.K_e)).key, pygame.K_RETURN)
            self.assertEqual(scene.racer_event(key(pygame.K_UP)).key, pygame.K_UP)
            self.assertEqual(scene.racer_event(key(pygame.K_w)).key, pygame.K_UP)


class OverlayPlacementTests(RacerUITest):
    def test_the_banner_stays_in_the_centre_strip_clear_of_the_stat_blocks(self):
        room, scene = self.start_racer(self.p1, self.p2)
        hud = scene.racer.hud
        manager = type("M", (), {"banner": ["CHECKPOINT!", "+12 SEC"], "banner_time": 2.0,
                                 "banner_alpha": 1.0})()
        for lines in (["CHECKPOINT!", "+12 SEC"], ["LEVEL 12"], ["FASTER!", "+5", "+9"]):
            manager.banner = lines
            surf = pygame.Surface(RACER_SIZE)
            hud.draw_banner(surf, manager)
            box = pygame.mask.from_threshold(surf, (0, 0, 0), (1, 1, 1, 255))
            box.invert()
            bounds = box.get_bounding_rects()
            self.assertTrue(bounds)
            left = min(r.left for r in bounds)
            right = max(r.right for r in bounds)
            top = min(r.top for r in bounds)
            self.assertGreaterEqual(left, 200, lines)               # the left HUD column ends before 200
            self.assertLessEqual(right, 600, lines)                 # the right one starts after 600
            self.assertGreaterEqual(top, 100, lines)                # under the TIME readout

    def test_the_spectator_tag_is_small_and_in_free_space(self):
        room, scene = self.start_racer(self.p1, self.p2)
        self.to_countdown(scene, self.p1)
        self.to_race(scene)
        plain = pygame.Surface(RACER_SIZE)
        scene.racer.screen = plain
        scene.racer.render()
        tagged = pygame.Surface(RACER_SIZE)
        scene.racer.screen = tagged
        scene.racer.render()
        scene._draw_spectators(tagged)
        changed = [(x, y) for y in range(0, 140) for x in range(0, 800, 2)
                   if tagged.get_at((x, y)) != plain.get_at((x, y))]
        self.assertTrue(changed)
        xs, ys = [p[0] for p in changed], [p[1] for p in changed]
        self.assertGreaterEqual(min(ys), SPECTATOR_Y - 4)
        self.assertLessEqual(max(ys), SPECTATOR_Y + 36)
        self.assertGreater(min(xs), 220)                            # clear of the left HUD column
        self.assertLess(max(xs), 580)                               # and the right one
        self.assertLess(max(xs) - min(xs), 400)                     # small
        self.assertIn("SPECTATING", f"{self.p2.tag} - SPECTATING")

    def test_no_tag_without_a_spectator_and_menus_use_the_corner(self):
        room, scene = self.start_racer(self.p1, None)
        scene.spectators = []
        surf = pygame.Surface(RACER_SIZE)
        scene.racer.screen = surf
        scene.racer.render()
        copy = surf.copy()
        scene._draw_spectators(surf)
        self.assertEqual(pygame.image.tobytes(surf, "RGB"), pygame.image.tobytes(copy, "RGB"))
        scene.spectators = [self.p2]
        scene._draw_spectators(surf)                                # title screen: bottom-right corner
        changed = [(x, y) for y in range(0, 600, 2) for x in range(0, 800, 2)
                   if surf.get_at((x, y)) != copy.get_at((x, y))]
        self.assertTrue(changed)
        self.assertGreater(min(y for _, y in changed), 540)
        self.assertGreater(min(x for x, _ in changed), 400)


if __name__ == "__main__":
    unittest.main()
