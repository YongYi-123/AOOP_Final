"""PRIZE PLAZA: the flashy room right of HOME, for TICKET rewards.

A working prize counter, personal garage terminal, shelves of prizes,
glass display cases for cosmetics and decorations, ticket signage and the
Lucky Corner with a free bay for the next chance game. Tickets earned in
the arcade unlock personal racing content here.
"""
import pygame

from backdrop import (AmbientAnimator, BackgroundRenderer, DustMotes,
                      LightingOverlay, StringLights)
from font import get_font
from gfx import neon_rect_glow, outlined, scale_color
from room import Prop, make_gumball, make_plant
from lucky_cabinets import KINDS
from neon21_art import suit_icon
from room_art import HubBackdrop, Twinkles
from room_scene import BaseRoomScene, RoomExit
from settings import Col, Lofi, VIEW_H, VIEW_W
from stations import PrizeCounter, SoonStation, build_lucky_corner
from racing_progression.station import GarageStation
from racing_progression.ui import PrizeCounterScene, GarageScene

# three zones, left to right: PRIZE COUNTER, DISPLAY SHELVES, LUCKY CORNER
COUNTER_POS = (36, 104)
LUCKY_POS = (268, 98)
PRIZE_COLORS = ((255, 140, 190), (120, 220, 255), (255, 214, 90), (160, 240, 150),
                (190, 150, 255), (255, 120, 120))


def _prize(color, kind):
    """One little prize for a shelf: a plush, a gift box or a trophy."""
    s = pygame.Surface((9, 9), pygame.SRCALPHA)
    if kind == 0:                                           # plush bear
        pygame.draw.circle(s, color, (4, 5), 3)
        s.fill(color, (1, 1, 2, 2))
        s.fill(color, (6, 1, 2, 2))
        s.fill((30, 20, 50), (3, 5, 1, 1))
        s.fill((30, 20, 50), (5, 5, 1, 1))
    elif kind == 1:                                         # gift box
        s.fill(color, (1, 3, 7, 6))
        s.fill(scale_color(color, 0.6), (4, 3, 1, 6))
        s.fill((255, 244, 200), (1, 5, 7, 1))
        s.fill((255, 244, 200), (3, 1, 3, 2))
    else:                                                   # trophy
        s.fill(color, (2, 1, 5, 4))
        s.fill(color, (4, 5, 1, 2))
        s.fill(scale_color(color, 0.6), (2, 7, 5, 2))
        s.fill((255, 255, 255), (3, 2, 1, 2))
    return s


class PlazaBackdrop(HubBackdrop):
    """Prize shelves, the TICKET PRIZES sign and a gold-edged carpet."""
    SHELVES = ((146, 28), (146, 46))                        # (x, y) of each shelf board
    SHELF_W = 104

    def paint_floor(self, surf):
        super().paint_floor(surf)
        carpet = pygame.Rect(20, 208, 190, 36)               # from the HOME door to the counter
        surf.fill((120, 30, 90), carpet)
        surf.fill((160, 50, 120), carpet.inflate(-4, -4))
        pygame.draw.rect(surf, (255, 214, 90), carpet.inflate(-2, -2), 1)
        for x in range(carpet.x + 14, carpet.right - 8, 20):
            pygame.draw.polygon(surf, (255, 190, 120), [(x, carpet.centery - 3), (x + 3, carpet.centery),
                                                        (x, carpet.centery + 3), (x - 3, carpet.centery)])
        self.paint_lucky_corner(surf)

    def paint_lucky_corner(self, surf):
        """The Lucky Corner's own floor: a plum rug with a gold edge, card
        suits in its corners, scattered coins and a neon pool under each
        cabinet. Paint only - nothing here is solid or blocks a path."""
        rug = pygame.Rect(LUCKY_POS[0] - 14, LUCKY_POS[1] - 20, 122, 128)
        rug.right = min(rug.right, VIEW_W - 22)
        surf.fill((30, 12, 50), rug)
        for ty in range(rug.top + 2, rug.bottom - 2, 8):                  # soft checker
            for tx in range(rug.left + 2, rug.right - 2, 8):
                if ((tx - rug.left) // 8 + (ty - rug.top) // 8) % 2:
                    surf.fill((38, 16, 62), (tx, ty, 8, 8))
        pygame.draw.rect(surf, (255, 190, 70), rug, 1)
        pygame.draw.rect(surf, (150, 40, 130), rug.inflate(-4, -4), 1)
        for suit, (cx, cy) in zip("SHDC", ((rug.left + 6, rug.top + 6), (rug.right - 13, rug.top + 6),
                                          (rug.left + 6, rug.bottom - 13), (rug.right - 13, rug.bottom - 13))):
            color = (255, 120, 140) if suit in "HD" else (120, 230, 190)
            surf.blit(suit_icon(suit, color, big=True), (cx, cy))
        for cx, cy in ((rug.left + 12, rug.centery + 6), (rug.right - 18, rug.centery - 8),
                       (rug.centerx - 4, rug.bottom - 8)):                  # dropped coins
            pygame.draw.circle(surf, (255, 190, 70), (cx, cy), 2)
            surf.fill((255, 244, 190), (cx - 1, cy - 1, 1, 1))
        for kind, x in zip(("spin", "hilo", "neon21"), (LUCKY_POS[0] + 40 * i for i in range(3))):
            neon = KINDS[kind]["neon"]
            pool = pygame.Surface((30, 14), pygame.SRCALPHA)
            for yy in range(14):                                            # floor reflection, fading out
                pool.fill((*neon, int(70 * (1 - yy / 14) ** 2)), (0, yy, 30, 1))
            surf.blit(pool, (x - 1, LUCKY_POS[1] + 40))

    def paint_room(self, surf):
        for i, (x, y) in enumerate(self.SHELVES):
            surf.fill((120, 78, 90), (x, y, self.SHELF_W, 3))
            surf.fill((176, 128, 110), (x, y, self.SHELF_W, 1))
            surf.fill((60, 36, 56), (x + 2, y + 3, self.SHELF_W - 4, 1))
            for j, px in enumerate(range(x + 4, x + self.SHELF_W - 12, 14)):
                surf.blit(_prize(PRIZE_COLORS[(i * 3 + j) % len(PRIZE_COLORS)], (i + j) % 3),
                          (px, y - 9))
            for px in (x + 2, x + self.SHELF_W - 4):           # brackets
                surf.fill((60, 36, 56), (px, y + 3, 2, 5))
        # ticket-shaped sign
        w, h = 92, 24
        sx, sy = 32, 10                                         # above the prize counter
        pygame.draw.rect(surf, (255, 190, 70), (sx, sy, w, h), border_radius=3)
        pygame.draw.rect(surf, (90, 20, 80), (sx + 2, sy + 2, w - 4, h - 4), border_radius=2)
        for yy in range(sy + 4, sy + h - 3, 4):                 # perforations
            surf.fill((255, 190, 70), (sx + 12, yy, 1, 2))
            surf.fill((255, 190, 70), (sx + w - 13, yy, 1, 2))
        for cx in (sx, sx + w - 1):                             # notches
            pygame.draw.circle(surf, self.theme.wall, (cx, sy + h // 2), 3)
        font = get_font()
        word = font.render_glow("TICKETS", (255, 236, 160), (200, 110, 30), scale=2)
        surf.blit(word, ((w - word.get_width()) // 2 + sx, sy + (h - word.get_height()) // 2))
        self.add_light(neon_rect_glow(w, h, (255, 170, 60), 8, self.style.strength(0.3)), (sx - 8, sy - 8))
        label = font.render_glow("DISPLAY", (255, 190, 230), (170, 50, 130))   # over the shelves
        surf.blit(label, (146 + (self.SHELF_W - label.get_width()) // 2, 9))


def _display_case(color):
    s = pygame.Surface((26, 38), pygame.SRCALPHA)
    s.fill((46, 30, 80), (0, 4, 26, 34))
    s.fill((16, 10, 40), (2, 6, 22, 22))
    s.fill(color, (0, 4, 26, 1))
    for i, c in enumerate(PRIZE_COLORS[:3]):
        s.blit(_prize(c, (i + 1) % 3), (3 + i * 7, 17))
    s.fill((200, 240, 255), (3, 7, 1, 14))                     # glass shine
    s.fill((30, 22, 60), (0, 29, 26, 9))
    s.fill(color, (0, 36, 26, 1))
    s.fill(Col.YELLOW, (11, 31, 4, 2))
    return outlined(s)


class PrizePlazaScene(BaseRoomScene):
    room_id = "prize_plaza"
    ambience_mix = {"arcade_buzz": 0.1, "machine_hum": 0.06}
    exits = (RoomExit("left", "home", "right"),)
    cat_spots = {}              # nobody lives here yet
    hint_rows = (
        [("MOVE: WASD", Col.TEXT)],
        [("E :", Col.TEXT), ("INTERACT", Col.YELLOW)],
        [("I :", Col.TEXT), ("BAG", Col.YELLOW)],
    )

    # ------------------------------------------------------------ building
    def build_props(self):
        counter = PrizeCounter(COUNTER_POS)
        cases = [Prop(_display_case(color), (x, 112), (x + 1, 140, 26, 8),
                      neon_rect_glow(26, 38, color, 6, self.style.strength(0.22)), (x - 6, 106))
                 for x, color in ((164, (255, 140, 190)), (200, (120, 220, 255)))]
        lucky = build_lucky_corner(*LUCKY_POS)
        spare_bays = [SoonStation((LUCKY_POS[0] + 40 * i, LUCKY_POS[1] + 70)) for i in range(2)]
        plant = make_plant(Lofi.TERRACOTTA, Lofi.TERRACOTTA_HI)
        return ([counter, GarageStation((146,186))] + cases + lucky + spare_bays + [
            Prop(plant, (24, 76), (27, 92, 13, 10)),
            Prop(plant, (358, 244), (361, 260, 13, 10)),
            Prop(make_gumball(), (176, 252), (177, 268, 12, 6)),
            Prop(make_gumball(), (196, 252), (197, 268, 12, 6)),
        ])

    def build_renderer(self):
        style, t = self.style, self.theme
        backdrop = PlazaBackdrop((VIEW_W, VIEW_H), t, {"left": ("HOME", (190, 150, 255))}, style)
        animator = AmbientAnimator()
        animator.add(StringLights(20, VIEW_W - 20, 2, span=40, sag=4,
                                  colors=((255, 214, 90), (255, 110, 190), (190, 150, 255))), "overlay")
        spots = [(x, y, (x * 7 + y * 3) % 6) for y in (21, 39) for x in range(150, 246, 14)]
        animator.add(Twinkles(spots), "overlay")
        corner = [(LUCKY_POS[0] + dx, LUCKY_POS[1] + dy, (dx * 5 + dy) % 7)
                  for dx, dy in ((-8, -12), (30, -14), (70, -12), (112, -10), (-10, 30), (112, 40),
                                 (-8, 74), (34, 120), (74, 96), (112, 110))]
        animator.add(Twinkles(corner, ((255, 214, 90), (255, 140, 220), (120, 255, 190))), "overlay")
        animator.add(DustMotes((30, 70, 340, 200), count=14), "overlay")
        pools = [((200, 170), 150, (24, 10, 30), 0.8),
                 ((198, 44), 70, (40, 24, 14), 0.5),              # display shelves
                 ((76, 126), 60, (44, 28, 10), 0.6),              # prize counter
                 ((322, 118), 56, (40, 14, 34), 0.6),             # lucky corner
                 ((308, 188), 50, (30, 10, 30), 0.6)]
        lighting = LightingOverlay((VIEW_W, VIEW_H), edge=t.light_edge, center=t.light_center,
                                   pools=[(pos, r, style.light(c), sq) for pos, r, c, sq in pools])
        return BackgroundRenderer(backdrop, animator, lighting)

    # ------------------------------------------------------------ prize counter
    def open_prize_counter(self):
        owner = self.session.player_for_avatar(self._actor())
        self.game.scenes.push(PrizeCounterScene(self.game,owner))

    def open_garage(self):
        owner = self.session.player_for_avatar(self._actor())
        self.game.scenes.push(GarageScene(self.game,owner))
