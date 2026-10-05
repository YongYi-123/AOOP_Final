"""ARCADE FLOOR: the main gameplay room, left of HOME.

Rows of cabinets under strong cyan / magenta light, with each machine's
high score on a little LED plate above it. The machines come from
arcade_layout.py (data-driven), so adding a game never touches this file.
Tokens are spent here; the payment flow lives in BaseRoomScene.
"""
import pygame

from arcade_layout import ArcadeLayout
from backdrop import (AmbientAnimator, BackgroundRenderer, DustMotes,
                      LightingOverlay, NeonLight, Scanlines, StringLights, neon_tube)
from font import get_font
from gfx import neon_rect_glow, scale_color, shade
from lofi_props import make_stool
from room import Prop, make_vending
from room_art import FloorStrips, HubBackdrop
from room_scene import BaseRoomScene, RoomExit
from settings import FLOOR_TOP, Col, VIEW_H, VIEW_W

SIGN_POS = (300, 8)


def _poster(size, border, fill, title, accent):
    s = pygame.Surface(size)
    s.fill(border)
    s.fill(fill, (1, 1, size[0] - 2, size[1] - 2))
    font = get_font()
    s.blit(font.render(title, accent), ((size[0] - font.size(title)[0]) // 2, 4))
    s.fill(scale_color(accent, 0.5), (3, 13, size[0] - 6, 1))
    s.fill(accent, (size[0] // 2 - 4, 17, 8, 6))              # a chunky pixel mascot
    s.fill(fill, (size[0] // 2 - 2, 19, 1, 2))
    s.fill(fill, (size[0] // 2 + 1, 19, 1, 2))
    return s


class ArcadeBackdropArt(HubBackdrop):
    """Posters on the free wall space and the neon ARCADE sign's mount."""

    def paint_room(self, surf):
        surf.blit(_poster((26, 30), (255, 70, 200), (28, 16, 60), "GO!", (255, 214, 90)), (212, 8))
        surf.blit(_poster((26, 30), (80, 240, 255), (16, 20, 60), "1UP", (90, 255, 150)), (262, 8))
        for x in (300, 322, 344, 366):                         # chase-light bulbs under the sign
            surf.fill((120, 60, 110), (x, 25, 2, 1))


class HighScorePlates:
    """A small LED plate above each machine showing its best score. Plates are
    re-rendered only when a score changes."""
    PLATE = (34, 10)

    def __init__(self, machines, profile):
        self.machines = machines
        self.profile = profile
        self._cache = {}

    def _plate(self, machine, score):
        key = (machine.game_id, score)
        plate = self._cache.get(key)
        if plate is None:
            w, h = self.PLATE
            plate = pygame.Surface(self.PLATE)
            plate.fill((8, 4, 18))
            pygame.draw.rect(plate, scale_color(machine.neon, 0.8), plate.get_rect(), 1)
            text = f"{score:05d}" if score else "-----"
            font = get_font()
            plate.blit(font.render(text, shade(machine.accent, 0.2) if score else
                                   scale_color(machine.accent, 0.45)),
                       ((w - font.size(text)[0]) // 2 + 1, 2))
            self._cache[key] = plate
        return plate

    def draw(self, surf):
        for m in self.machines:
            plate = self._plate(m, self.profile.high_score(m.game_id))
            surf.blit(plate, (m.rect.centerx - plate.get_width() // 2, m.rect.y - 14))


class ArcadeFloorScene(BaseRoomScene):
    room_id = "arcade_floor"
    ambience_mix = {"machine_hum": 0.2, "arcade_buzz": 0.14}
    exits = (RoomExit("right", "home", "left"),)
    cat_spots = {
        "pixel": ((120, 124), (250, 124), (324, 196), (330, 244)),   # curious: patrols the corridor
    }
    hint_rows = (
        [("MOVE: WASD", Col.TEXT)],
        [("E :", Col.TEXT), ("PLAY", Col.YELLOW)],
        [("I :", Col.TEXT), ("BAG", Col.YELLOW)],
    )

    def __init__(self, game, hub):
        self.layout = ArcadeLayout.from_settings()
        super().__init__(game, hub)
        self.plates = HighScorePlates(self.machines, self.profile)

    # ------------------------------------------------------------ building
    def build_machines(self):
        return self.layout.build_machines()

    def build_props(self):
        stool = make_stool()
        vend = Prop(make_vending(), (332, 32), (333, FLOOR_TOP, 30, 26),
                    neon_rect_glow(30, 58, Col.CYAN, 7, 0.4), (325, 27))
        stools = [Prop(stool, (x, 184), (x + 1, 192, 12, 5)) for x in (123, 207, 291)]
        return self.layout.build_idle_cabinets() + [vend] + stools

    def build_renderer(self):
        style = self.style
        backdrop = ArcadeBackdropArt((VIEW_W, VIEW_H), self.theme, {"right": ("HOME", (190, 150, 255))},
                                     style)
        animator = AmbientAnimator()
        font = get_font()
        sign = neon_tube(font.render("ARCADE", (255, 255, 255), 2), (200, 252, 255), (60, 200, 235))
        animator.add(NeonLight(sign, SIGN_POS, Col.CYAN, spread=8, strength=style.strength(0.55), speed=0.9,
                               depth=0.2, flicker=(9.0, ((7.2, 7.3, 0.4), (7.5, 7.65, 0.5)))), "overlay")
        animator.add(FloorStrips([
            (pygame.Rect(30, 118, 340, 1), Col.CYAN),
            (pygame.Rect(30, 123, 340, 1), Col.MAGENTA),
            (pygame.Rect(24, 270, 352, 1), Col.MAGENTA),
        ], gain=style.palette.glow), "wall")
        animator.add(StringLights(20, VIEW_W - 20, 2, span=60, sag=3,
                                  colors=((255, 70, 200), (80, 240, 255), (255, 214, 90))), "overlay")
        animator.add(DustMotes((30, 70, 340, 200), count=12), "overlay")
        animator.add(Scanlines((VIEW_W, VIEW_H), alpha=style.scanline_alpha(22)), "overlay")
        pools = [((m.rect.centerx, m.rect.bottom + 14), 36,
                  style.light(scale_color(m.neon, 0.16)), 0.5) for m in self.machines]
        pools += [((200, 170), 150, style.light((10, 6, 30)), 0.7),
                  ((340, 120), 40, style.light((6, 24, 30)), 0.6)]
        lighting = LightingOverlay((VIEW_W, VIEW_H), edge=self.theme.light_edge,
                                   center=self.theme.light_center, pools=pools)
        return BackgroundRenderer(backdrop, animator, lighting)

    # ------------------------------------------------------------ drawing
    def draw_under_sprites(self, surf):
        self.plates.draw(surf)
