"""Tests for the style layer (arcade_style.py) and how the rooms use it."""
import io
import os
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from arcade_style import (DEFAULT_STYLE, STYLE_NAMES, STYLE_PALETTES, STYLES,  # noqa: E402
                          ArcadeStyle, StyleManager, StylePalette, saturate)
from game import Game  # noqa: E402
from main import build_parser  # noqa: E402
from room_art import ROOM_THEMES  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import ROOM_IDS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


class StyleTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def game(self, **kw):
        return Game(save_path=os.path.join(self.dir, "s.json"), **kw)


class DefaultTests(StyleTest):
    def test_default_is_neon_lofi_everywhere(self):
        self.assertEqual(DEFAULT_STYLE, "neon_lofi")
        self.assertEqual(STYLES.get().name, "neon_lofi")
        self.assertEqual(self.game().style.name, "neon_lofi")
        self.assertEqual(build_parser().parse_args([]).style, "neon_lofi")

    def test_the_old_style_names_still_exist(self):
        self.assertIn("lofi", STYLE_NAMES)
        self.assertIn("neon", STYLE_NAMES)
        self.assertEqual(set(STYLE_NAMES), set(STYLE_PALETTES))


class CommandLineTests(unittest.TestCase):
    def test_every_style_parses(self):
        for name in STYLE_NAMES:
            self.assertEqual(build_parser().parse_args(["--style", name]).style, name)

    def test_unsupported_style_is_a_clean_usage_error(self):
        with redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit):
            build_parser().parse_args(["--style", "vaporwave"])
        self.assertIn("--style", err.getvalue())

    def test_debug_flag_still_parses(self):
        self.assertTrue(build_parser().parse_args(["--debug"]).debug)


class FallbackTests(StyleTest):
    def test_unknown_style_falls_back_to_the_default(self):
        with redirect_stderr(io.StringIO()) as err:
            style = STYLES.get("vaporwave")
        self.assertEqual(style.name, DEFAULT_STYLE)
        self.assertIn("vaporwave", err.getvalue())

    def test_game_with_an_unknown_style_still_runs(self):
        with redirect_stderr(io.StringIO()):
            g = self.game(style="nope")
        self.assertEqual(g.style.name, DEFAULT_STYLE)
        for _ in range(5):
            g.step([], 1 / 60)

    def test_manager_caches_and_honours_its_own_default(self):
        m = StyleManager({"a": STYLE_PALETTES["lofi"], "b": STYLE_PALETTES["neon"]}, default="b")
        self.assertIs(m.get("a"), m.get("a"))
        with redirect_stderr(io.StringIO()):
            self.assertIs(m.get("zzz"), m.get("b"))
        self.assertEqual(m.names, ("a", "b"))


class SharedConfigurationTests(StyleTest):
    def test_all_rooms_share_one_style_and_have_their_own_accents(self):
        for name in STYLE_NAMES:
            g = self.game(style=name)
            rooms = [g.hub.room(r) for r in ROOM_IDS]
            self.assertTrue(all(r.style is g.style is g.hub.style for r in rooms), name)
            self.assertEqual(g.style.name, name)
            for room in rooms:
                self.assertIs(room.theme, g.style.theme_for(room.room_id))
            accents = {r.theme.accent_a for r in rooms}
            self.assertEqual(len(accents), 3)                   # each room keeps its own accent colours

    def test_the_style_survives_room_switching(self):
        g = self.game(style="neon")
        before = {r: g.hub.room(r).theme for r in ROOM_IDS}
        for target in ROOM_IDS * 3:
            goto_room(g, target)
            for _ in range(3):
                g.step([], 1 / 60)
            self.assertIs(g.hub.style, g.style)
            self.assertEqual(g.hub.room(target).style.name, "neon")
        self.assertTrue(all(g.hub.room(r).theme is before[r] for r in ROOM_IDS))

    def test_styles_change_the_numbers_not_the_rooms(self):
        lofi, nl, neon = (STYLES.get(n) for n in ("lofi", "neon_lofi", "neon"))
        self.assertLess(lofi.palette.glow, nl.palette.glow)
        self.assertLess(nl.palette.glow, neon.palette.glow)
        self.assertLess(lofi.palette.saturation, neon.palette.saturation)
        self.assertTrue(lofi.soft_machines)
        self.assertFalse(nl.soft_machines or neon.soft_machines)
        for room_id in ROOM_IDS:
            self.assertEqual(lofi.theme_for(room_id).name, neon.theme_for(room_id).name)
            self.assertNotEqual(lofi.theme_for(room_id).wall_dot, neon.theme_for(room_id).wall_dot)
        self.assertLess(sum(lofi.light((100, 100, 100))), sum(neon.light((100, 100, 100))))
        self.assertLessEqual(neon.strength(0.9), 1.0)

    def test_style_drives_the_machines_halo_set(self):
        for name in STYLE_NAMES:
            g = self.game(style=name)
            arcade = g.hub.room("arcade_floor")
            self.assertTrue(all(m.soft_glow == STYLES.get(name).soft_machines for m in arcade.machines))

    def test_saturate_helper(self):
        self.assertEqual(saturate((100, 100, 100), 2.0), (100, 100, 100))
        r, g, b = saturate((200, 100, 100), 1.5)
        self.assertGreater(r - g, 100)
        self.assertEqual(saturate((10, 10, 10), 0.0), (10, 10, 10))


class RendererTests(StyleTest):
    def test_every_room_renders_under_every_style(self):
        backgrounds = {}
        for name in STYLE_NAMES:
            g = self.game(style=name)
            for room_id in ROOM_IDS:
                room = goto_room(g, room_id)
                for _ in range(10):
                    g.step([], 1 / 60)
                room.draw(g.canvas)
                backgrounds[name, room_id] = pygame.image.tostring(room.renderer.image, "RGB")
        for room_id in ROOM_IDS:                                # the style visibly changes the art
            self.assertNotEqual(backgrounds["lofi", room_id], backgrounds["neon", room_id])
            self.assertNotEqual(backgrounds["neon_lofi", room_id], backgrounds["lofi", room_id])
        for name in STYLE_NAMES:                                # and rooms still differ from each other
            self.assertEqual(len({backgrounds[name, r] for r in ROOM_IDS}), 3)

    def test_rooms_do_not_branch_on_a_style_name(self):
        for fname in ("room_scene.py", "home_room.py", "arcade_floor.py", "prize_plaza.py", "room_art.py"):
            with open(os.path.join(HERE, fname)) as f:
                self.assertIsNone(re.search(r"\bstyle(\.name)?\s*[=!]=|\bstyle\s+in\s", f.read()), fname)

    def test_a_custom_palette_works_without_touching_a_room(self):
        palette = StylePalette("test", neon=0.3, saturation=1.0, glow=1.0, seams=1.0,
                               scanlines=0.0, soft_machines=False)
        style = ArcadeStyle(palette)
        self.assertEqual(set(style._themes), set(ROOM_THEMES))
        self.assertEqual(style.scanline_alpha(22), 0)


if __name__ == "__main__":
    unittest.main()
