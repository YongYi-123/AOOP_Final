"""The CAT TERRITORY and CAT VOLLEYBALL cabinets: their look, layout and hub integration.

Run with:  python -m unittest test_machine_themes
"""
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import machine_themes as themes  # noqa: E402
from scenes import create_minigame_scene  # noqa: E402  (puts the project root on sys.path)
from cat_territory_scene import CatTerritoryScene  # noqa: E402
from game import Game  # noqa: E402
from machine import H, STYLES, W, ArcadeMachine  # noqa: E402
from pixel_volleyball_scene import PixelVolleyballScene  # noqa: E402
from room_testing import goto_room  # noqa: E402
from settings import MACHINES  # noqa: E402

DT = 1 / 60


def machine_data(machine_id):
    return next(d for d in MACHINES if d["id"] == machine_id)


class CabinetArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def machine(self, machine_id):
        data = dict(machine_data(machine_id), x=100, y=30)
        return ArcadeMachine(data)

    def test_the_two_games_use_their_own_cabinet_styles(self):
        self.assertEqual(machine_data("cat_minesweeper")["screen"], "cat")
        self.assertEqual(machine_data("pixel_volleyball")["screen"], "volley")
        self.assertEqual(machine_data("cat_minesweeper")["name"], "Cat Territory")
        self.assertEqual(machine_data("pixel_volleyball")["name"], "Cat Volleyball")
        self.assertEqual(machine_data("pixel_volleyball")["marquee"], "CAT VOLLEYBALL")
        for style in ("cat", "volley"):
            self.assertIn(style, STYLES)

    def test_collision_and_interaction_use_the_standard_cabinet_box(self):
        standard = ArcadeMachine(dict(machine_data("retro_racer"), x=100, y=30))
        for machine_id in ("cat_minesweeper", "pixel_volleyball"):
            m = self.machine(machine_id)
            self.assertEqual(m.rect.size, (W, H))
            self.assertEqual(m.footprint.size, standard.footprint.size)
            self.assertEqual(m.zone.size, standard.zone.size)

    def test_cat_ears_stand_above_the_marquee_without_moving_the_collision_box(self):
        cat, volley = self.machine("cat_minesweeper"), self.machine("pixel_volleyball")
        self.assertGreater(cat.art["pad"], 0)
        self.assertEqual(volley.art["pad"], 0)
        sprite = cat.art["cabinet"][0]
        self.assertEqual(sprite.get_height(), H + cat.art["pad"] + 2)
        ear_rows = sprite.subsurface((0, 0, sprite.get_width(), cat.art["pad"]))
        self.assertGreater(pygame.mask.from_surface(ear_rows).count(), 10)       # ears are drawn up there

    def test_the_cabinets_animate(self):
        for machine_id in ("cat_minesweeper", "pixel_volleyball"):
            m = self.machine(machine_id)
            screens, marquees = set(), set()
            for _ in range(240):
                m.update(DT)
                screens.add(pygame.image.tobytes(m.image, "RGB"))
                marquees.add(pygame.image.tobytes(m.art["cabinet"][m.marquee.image], "RGBA"))
            self.assertGreater(len(screens), 8, machine_id)         # attract-mode screen moves
            self.assertGreater(len(marquees), 2, machine_id)        # marquee / lights move

    def test_the_volleyball_marquee_scrolls_the_whole_name_and_loops_seamlessly(self):
        label = "CAT VOLLEYBALL"
        frames = themes.marquee_frames("volley", label)
        self.assertGreater(frames, 20)
        first, again = pygame.Surface((36, 12)), pygame.Surface((36, 12))
        themes.marquee_volley(first, pygame.Rect(2, 1, 32, 10), label, 0, (0, 0, 0), (0, 0, 0))
        themes.marquee_volley(again, pygame.Rect(2, 1, 32, 10), label, frames, (0, 0, 0), (0, 0, 0))
        self.assertEqual(pygame.image.tobytes(first, "RGB"), pygame.image.tobytes(again, "RGB"))

    def test_other_styles_keep_four_marquee_frames(self):
        for style in ("racer", "space", "puzzle", "cat"):
            self.assertEqual(themes.marquee_frames(style, "X"), 4)


class HubIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.game = Game(save_path=os.path.join(self.dir, "s.json"))
        self.addCleanup(self.game.quit)
        self.room = goto_room(self.game, "arcade_floor")

    def test_cabinets_do_not_overlap_each_other_or_the_other_props(self):
        boxes = [m.footprint for m in self.room.machines]
        boxes += [p.footprint for p in self.room.props if p.solid]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                self.assertFalse(a.colliderect(b), (a, b))

    def test_each_machine_launches_its_own_scene(self):
        for machine_id, scene_cls in (("cat_minesweeper", CatTerritoryScene),
                                      ("pixel_volleyball", PixelVolleyballScene)):
            machine = next(m for m in self.room.machines if m.id == machine_id)
            scene = create_minigame_scene(self.game, machine)
            self.assertIsInstance(scene, scene_cls)

    def test_the_high_score_plate_clears_the_cat_ears(self):
        cat = next(m for m in self.room.machines if m.id == "cat_minesweeper")
        surf = pygame.Surface((400, 300))
        self.room.draw_under_sprites(surf)             # must not raise with padded cabinets
        plate_top = cat.rect.y - self.room.plates.H - 4 - cat.art["pad"]
        ear_top = cat.rect.y - 1 - cat.art["pad"]
        self.assertLess(plate_top + self.room.plates.H, ear_top)

    def test_switching_between_the_two_games_and_the_hub_is_stable(self):
        profile = self.game.profile
        tickets = profile.tickets
        for round_ in range(3):
            for machine_id in ("cat_minesweeper", "pixel_volleyball"):
                machine = next(m for m in self.room.machines if m.id == machine_id)
                self.room._start_game(machine, player=self.room.players[0])
                for _ in range(60):
                    self.game.step([], DT)
                self.assertIsNot(self.game.scenes.current, self.room, (round_, machine_id))
                esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")
                self.game.step([esc], DT)
                for _ in range(90):
                    self.game.step([], DT)
                self.assertIs(self.game.scenes.current, self.room, (round_, machine_id))
        self.assertEqual(profile.tickets, tickets)            # leaving unplayed earns nothing

    def test_walking_up_to_a_machine_offers_play(self):
        for machine_id in ("cat_minesweeper", "pixel_volleyball"):
            machine = next(m for m in self.room.machines if m.id == machine_id)
            player = self.room.players[0]
            avatar = self.game.session.primary.avatar
            avatar.x = float(machine.rect.centerx)
            avatar.y = float(machine.rect.bottom + 12)
            for _ in range(5):
                self.game.step([], DT)
            self.assertIs(player.nearby, machine)


class SpectatorTagTests(unittest.TestCase):
    def test_the_tag_moves_off_the_help_text_for_both_games(self):
        for cls in (CatTerritoryScene, PixelVolleyballScene):
            self.assertEqual(cls.spectator_corner, "topleft")


if __name__ == "__main__":
    unittest.main()
