"""PRIZE PLAZA: the flashy room right of HOME, for TICKET rewards.

Four zones: the PRIZE COUNTER on the left (Mochi sells things for Tickets), the SHOWCASE in the
centre (the room's one display: a favourite car / collectible / trophy per player), the CAPSULE
CORNER at the upper right (CAT CAPSULE and RETRO CAPSULE) and the LUCKY CORNER bonus games below it.
The back wall carries only decoration (framed neon art, sconces and the two corner signs).
"""
import pygame

from backdrop import (AmbientAnimator, BackgroundRenderer, DustMotes,
                      LightingOverlay, StringLights)
import math

from capsule import CAT, RETRO
from capsule_ui import CapsuleScene
from font import get_font
from gfx import neon_rect_glow, scale_color
from room import Prop, make_gumball, make_plant
from lucky_cabinets import KINDS
from neon21_art import suit_icon
from room_art import HubBackdrop, Twinkles
from room_scene import BaseRoomScene, RoomExit
from settings import Col, Lofi, VIEW_H, VIEW_W
from plaza_stations import CAPSULE_SIZE, SHOWCASE_SIZE, CapsuleStation, ShowcaseStation
from stations import CoinPusherStation, PinballStation, PrizeCounter, build_lucky_corner
from racing_progression.ui import PrizeCounterScene
from shop_ui import ShopScene
from shopkeeper import Shopkeeper
from showcase_ui import ShowcaseScene

SIGN = (26, 6, 100, 32)                                    # the PRIZE COUNTER marquee: x, y, w, h
# left = PRIZE COUNTER, centre = SHOWCASE, upper right = CAPSULE CORNER, lower right = LUCKY CORNER
COUNTER_POS = (36, 104)
SHOWCASE_POS = (130, 66)                               # the main display focus: centred against the back wall
CAPSULE_POS = {CAT: (270, 74), RETRO: (322, 74)}       # the two capsule machines, side by side
CAPSULE_RUG = (254, 68, 122, 68)                       # the Capsule Corner's floor: x, y, w, h
CAPSULE_SIGN = (262, 30, 106, 30)                      # its marquee on the back wall
LUCKY_POS = (268, 158)                                 # the Lucky Corner block sits under the capsules
DAIS = (122, 122, 128, 36)                             # the showcase's floor stage
MOCHI_POS = (COUNTER_POS[0] + 60, COUNTER_POS[1] + 2)      # her feet: the middle of the counter top
WALL_ART = ((138, 24), (176, 24), (214, 24))           # framed neon pictures on the back wall (decoration only)


class PlazaBackdrop(HubBackdrop):
    """The PRIZE COUNTER sign, the back-wall art, the Capsule Corner and Lucky Corner rugs, the showcase dais and a gold-edged carpet."""

    def paint_floor(self, surf):
        super().paint_floor(surf)
        carpet = pygame.Rect(20, 208, 96, 36)                # a welcome mat from the HOME door
        surf.fill((120, 30, 90), carpet)
        surf.fill((160, 50, 120), carpet.inflate(-4, -4))
        pygame.draw.rect(surf, (255, 214, 90), carpet.inflate(-2, -2), 1)
        for x in range(carpet.x + 14, carpet.right - 8, 20):
            pygame.draw.polygon(surf, (255, 190, 120), [(x, carpet.centery - 3), (x + 3, carpet.centery),
                                                        (x, carpet.centery + 3), (x - 3, carpet.centery)])
        self.paint_dais(surf)
        self.paint_capsule_corner(surf)
        self.paint_lucky_corner(surf)

    def paint_dais(self, surf):
        """The showcase's stage: a plum ellipse with a gold ring, so the centre reads as the focus."""
        rect = pygame.Rect(DAIS)
        pygame.draw.ellipse(surf, (74, 24, 86), rect)
        pygame.draw.ellipse(surf, (110, 40, 112), rect.inflate(-10, -6))
        pygame.draw.ellipse(surf, (255, 214, 90), rect, 1)
        pygame.draw.ellipse(surf, (190, 120, 60), rect.inflate(-10, -6), 1)
        for x in range(rect.x + 18, rect.right - 12, 20):
            surf.fill((255, 190, 120), (x, rect.bottom - 7, 3, 1))

    def paint_capsule_corner(self, surf):
        """The Capsule Corner's floor: a rug split pink / blue under its two machines, a gold edge
        and a neon pool under each. Paint only - nothing here is solid."""
        rug = pygame.Rect(CAPSULE_RUG)
        half = rug.w // 2
        surf.fill((58, 22, 82), (rug.x, rug.y, half, rug.h))
        surf.fill((18, 34, 86), (rug.x + half, rug.y, rug.w - half, rug.h))
        for ty in range(rug.top + 2, rug.bottom - 2, 8):                  # soft checker
            for tx in range(rug.left + 2, rug.right - 2, 8):
                if ((tx - rug.left) // 8 + (ty - rug.top) // 8) % 2:
                    surf.fill((70, 30, 96) if tx < rug.centerx else (26, 46, 104), (tx, ty, 8, 8))
        pygame.draw.rect(surf, (255, 190, 70), rug, 1)
        pygame.draw.rect(surf, (255, 120, 200), (rug.x + 2, rug.y + 2, half - 2, rug.h - 4), 1)
        pygame.draw.rect(surf, (90, 230, 255), (rug.x + half, rug.y + 2, rug.w - half - 2, rug.h - 4), 1)
        for kind, (x, y) in CAPSULE_POS.items():
            neon = (255, 110, 210) if kind == CAT else (80, 220, 255)
            pool = pygame.Surface((46, 14), pygame.SRCALPHA)
            for yy in range(14):                                          # floor reflection, fading out
                pool.fill((*neon, int(80 * (1 - yy / 14) ** 2)), (0, yy, 46, 1))
            surf.blit(pool, (x - 4, y + CAPSULE_SIZE[1] - 8))

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
        for kind, x, y in (("spin", LUCKY_POS[0], 0), ("hilo", LUCKY_POS[0] + 40, 0), ("neon21", LUCKY_POS[0] + 80, 0),
                           ("pusher", LUCKY_POS[0], 70), ("pinball", LUCKY_POS[0] + 40, 70)):
            neon = KINDS[kind]["neon"]
            pool = pygame.Surface((30, 14), pygame.SRCALPHA)
            for yy in range(14):                                            # floor reflection, fading out
                pool.fill((*neon, int(70 * (1 - yy / 14) ** 2)), (0, yy, 30, 1))
            surf.blit(pool, (x - 1, LUCKY_POS[1] + y + 40))

    def paint_room(self, surf):
        for x, y in WALL_ART:
            self.paint_wall_art(surf, x, y)
        # the PRIZE COUNTER marquee: a gold-edged plate with the name in lights (bulbs chase in SignLights)
        font = get_font()
        sx, sy, w, h = SIGN
        pygame.draw.rect(surf, (255, 190, 70), (sx, sy, w, h), border_radius=3)
        pygame.draw.rect(surf, (90, 20, 80), (sx + 2, sy + 2, w - 4, h - 4), border_radius=2)
        pygame.draw.rect(surf, (150, 40, 130), (sx + 4, sy + 4, w - 8, h - 8), 1, border_radius=1)
        word = font.render_glow("PRIZE", (255, 236, 160), (200, 110, 30), scale=2)
        surf.blit(word, (sx + (w - word.get_width()) // 2, sy + 6))
        small = font.render_glow("COUNTER", (255, 190, 230), (170, 50, 130))
        surf.blit(small, (sx + (w - small.get_width()) // 2, sy + h - 12))
        self.add_light(neon_rect_glow(w, h, (255, 170, 60), 9, self.style.strength(0.34)), (sx - 9, sy - 9))
        # the CAPSULE CORNER marquee over its two machines
        sx, sy, w, h = CAPSULE_SIGN
        pygame.draw.rect(surf, (255, 190, 70), (sx, sy, w, h), border_radius=3)
        pygame.draw.rect(surf, (36, 18, 76), (sx + 2, sy + 2, w - 4, h - 4), border_radius=2)
        pygame.draw.rect(surf, (255, 120, 200), (sx + 4, sy + 4, w // 2 - 4, h - 8), 1)
        pygame.draw.rect(surf, (90, 230, 255), (sx + w // 2, sy + 4, w // 2 - 4, h - 8), 1)
        word = font.render_glow("CAPSULE", (255, 236, 250), (200, 70, 170))
        surf.blit(word, (sx + (w - word.get_width()) // 2, sy + 5))
        small = font.render_glow("CORNER", (200, 245, 255), (40, 130, 190))
        surf.blit(small, (sx + (w - small.get_width()) // 2, sy + h - 12))
        self.add_light(neon_rect_glow(w, h, (255, 150, 220), 9, self.style.strength(0.3)), (sx - 9, sy - 9))

    @staticmethod
    def paint_wall_art(surf, x, y):
        """A small framed neon picture (a star, a heart or a cat face) - wall decoration only."""
        w, h = 28, 22
        pygame.draw.rect(surf, (255, 190, 70), (x, y, w, h))
        pygame.draw.rect(surf, (24, 12, 50), (x + 2, y + 2, w - 4, h - 4))
        pygame.draw.rect(surf, (120, 50, 130), (x + 2, y + 2, w - 4, h - 4), 1)
        cx, cy = x + w // 2, y + h // 2
        kind = (x // 38) % 3
        if kind == 0:
            pygame.draw.polygon(surf, (255, 220, 110), [(cx, cy - 7), (cx + 2, cy - 2), (cx + 7, cy - 2), (cx + 3, cy + 1),
                                                        (cx + 4, cy + 6), (cx, cy + 3), (cx - 4, cy + 6), (cx - 3, cy + 1),
                                                        (cx - 7, cy - 2), (cx - 2, cy - 2)])
        elif kind == 1:
            pygame.draw.circle(surf, (255, 110, 170), (cx - 3, cy - 2), 3)
            pygame.draw.circle(surf, (255, 110, 170), (cx + 3, cy - 2), 3)
            pygame.draw.polygon(surf, (255, 110, 170), [(cx - 6, cy - 1), (cx + 6, cy - 1), (cx, cy + 6)])
        else:
            pygame.draw.circle(surf, (110, 220, 255), (cx, cy + 1), 6)
            pygame.draw.polygon(surf, (110, 220, 255), [(cx - 6, cy - 2), (cx - 5, cy - 8), (cx - 1, cy - 4)])
            pygame.draw.polygon(surf, (110, 220, 255), [(cx + 6, cy - 2), (cx + 5, cy - 8), (cx + 1, cy - 4)])
            surf.fill((24, 12, 50), (cx - 3, cy, 1, 2))
            surf.fill((24, 12, 50), (cx + 2, cy, 1, 2))


class SignLights:
    """The bulbs round the PRIZE COUNTER marquee, chasing in gold / pink / cyan,
    plus a slow overall pulse. Purely visual."""

    COLORS = ((255, 214, 90), (255, 110, 190), (120, 230, 255))

    def __init__(self, rect):
        x, y, w, h = rect
        pts = [(x + i, y + 1) for i in range(4, w - 4, 8)] + [(x + w - 2, y + j) for j in range(4, h - 4, 8)]
        pts += [(x + i, y + h - 3) for i in range(w - 6, 3, -8)] + [(x + 1, y + j) for j in range(h - 6, 3, -8)]
        self.points = pts
        self.t = 0.0

    def update(self, t):
        self.t = t

    def draw(self, surf):
        lit = int(self.t * 6)
        for i, (x, y) in enumerate(self.points):
            if (i - lit) % 3 == 0:
                color = self.COLORS[(i + lit // 3) % 3]
                surf.fill(color, (x, y, 2, 2))
                surf.fill(scale_color(color, 0.45), (x - 1, y, 4, 2))
            else:
                surf.fill((120, 80, 60), (x, y, 2, 2))


class SpotBeams:
    """Soft spotlight cones that fall on the capsule machines and the showcase and breathe slowly."""

    def __init__(self, centres, top=64, bottom=150, color=(255, 230, 190)):
        self.beams = []
        for k, cx in enumerate(centres):
            w = 44
            beam = pygame.Surface((w, bottom - top), pygame.SRCALPHA)
            for y in range(bottom - top):
                half = 4 + int(14 * y / (bottom - top))
                a = int(60 * (1 - y / (bottom - top)) ** 1.2)
                beam.fill((*color, a), (w // 2 - half, y, half * 2, 1))
            self.beams.append((beam, (cx - w // 2, top), k * 1.9))
        self.t = 0.0

    def update(self, t):
        self.t = t

    def draw(self, surf):
        for beam, pos, phase in self.beams:
            beam.set_alpha(int(150 + 90 * math.sin(self.t * 1.4 + phase)))
            surf.blit(beam, pos)


class PrizePlazaScene(BaseRoomScene):
    room_id = "prize_plaza"
    ambience_mix = {"arcade_buzz": 0.1, "machine_hum": 0.06}
    exits = (RoomExit("left", "home", "right"),)
    cat_spots = {
        "tango": ((92, 172), (62, 188), (104, 182)),          # curious: sniffs around the prize counter
        "duchess": ((236, 190), (200, 214)),                 # regal: surveys the room from the walkway
    }
    music_id = "prize_plaza"
    hint_rows = (
        [("MOVE: WASD", Col.TEXT)],
        [("E :", Col.TEXT), ("INTERACT", Col.YELLOW)],
        [("I :", Col.TEXT), ("BAG", Col.YELLOW), ("  T :", Col.TEXT), ("WAVE", Col.YELLOW)],
    )

    # ------------------------------------------------------------ building
    def build_props(self):
        self.mochi = Shopkeeper(MOCHI_POS, sound=self.play_sound, sort_y=COUNTER_POS[1] + 36.5)      # the cat on the counter (not solid)
        counter = PrizeCounter(COUNTER_POS)
        capsules = [CapsuleStation(pos, kind) for kind, pos in CAPSULE_POS.items()]
        showcase = ShowcaseStation(SHOWCASE_POS, owners=lambda: [(p.label, p.profile) for p in self.session])
        lucky = build_lucky_corner(*LUCKY_POS)
        # the two former SOON bays are NEON COIN PUSHER and LUCKY CAT PINBALL
        pusher = CoinPusherStation((LUCKY_POS[0], LUCKY_POS[1] + 70))
        pinball = PinballStation((LUCKY_POS[0] + 40, LUCKY_POS[1] + 70))
        plant = make_plant(Lofi.TERRACOTTA, Lofi.TERRACOTTA_HI)
        return ([counter] + capsules + [showcase] + lucky + [pusher, pinball] + [
            Prop(plant, (24, 76), (27, 92, 13, 10)),
            Prop(plant, (358, 244), (361, 260, 13, 10)),
            Prop(make_gumball(), (166, 254), (167, 270, 12, 6)),
            Prop(make_gumball(), (206, 254), (207, 270, 12, 6)),
        ])

    def build_renderer(self):
        style, t = self.style, self.theme
        backdrop = PlazaBackdrop((VIEW_W, VIEW_H), t, {"left": ("HOME", (190, 150, 255))}, style)
        animator = AmbientAnimator()
        animator.add(StringLights(20, VIEW_W - 20, 2, span=40, sag=4,
                                  colors=((255, 214, 90), (255, 110, 190), (190, 150, 255))), "overlay")
        spots = [(x + 14, y + 11, (x * 7 + y * 3) % 6) for x, y in WALL_ART]          # a glint on each framed picture
        animator.add(Twinkles(spots), "overlay")
        corner_sign = [(CAPSULE_SIGN[0] + dx, CAPSULE_SIGN[1] + dy, (dx * 3 + dy) % 5)
                       for dx, dy in ((6, 4), (40, 24), (70, 6), (98, 22))]
        animator.add(Twinkles(corner_sign, ((255, 190, 230), (170, 240, 255))), "overlay")
        corner = [(LUCKY_POS[0] + dx, LUCKY_POS[1] + dy, (dx * 5 + dy) % 7)
                  for dx, dy in ((-8, -12), (30, -14), (70, -12), (112, -10), (-10, 30), (112, 40),
                                 (-8, 74), (34, 108), (74, 96), (112, 100))]
        animator.add(Twinkles(corner, ((255, 214, 90), (255, 140, 220), (120, 255, 190))), "overlay")
        animator.add(SignLights(SIGN), "overlay")
        animator.add(SignLights(CAPSULE_SIGN), "overlay")
        animator.add(SpotBeams([x + CAPSULE_SIZE[0] // 2 for x, _ in CAPSULE_POS.values()],
                               top=62, bottom=120), "overlay")
        animator.add(SpotBeams([SHOWCASE_POS[0] + SHOWCASE_SIZE[0] // 2], top=132, bottom=196,
                               color=(255, 220, 190)), "overlay")
        counter = [(COUNTER_POS[0] + dx, COUNTER_POS[1] + dy, (dx * 3 + dy) % 5)
                   for dx, dy in ((4, 2), (30, 6), (56, 2), (76, 8), (14, 16), (66, 18))]
        animator.add(Twinkles(counter), "overlay")             # sparkle over the glass counter top
        animator.add(DustMotes((30, 70, 340, 200), count=14), "overlay")
        pools = [((186, 190), 150, (24, 10, 30), 0.8),
                 ((186, 102), 78, (54, 34, 18), 0.7),               # the showcase: the brightest pool in the room
                 ((186, 144), 66, (60, 24, 50), 0.5),               # its dais
                 ((192, 40), 66, (40, 24, 14), 0.5),                # the framed wall art
                 ((76, 126), 60, (44, 28, 10), 0.6),                # prize counter
                 ((294, 104), 40, (44, 16, 40), 0.55),              # cat capsule
                 ((342, 104), 40, (10, 28, 44), 0.55),              # retro capsule
                 ((322, 206), 62, (40, 14, 34), 0.6)]               # lucky corner
        lighting = LightingOverlay((VIEW_W, VIEW_H), edge=t.light_edge, center=t.light_center,
                                   pools=[(pos, r, style.light(c), sq) for pos, r, c, sq in pools])
        return BackgroundRenderer(backdrop, animator, lighting)

    def prompt_avoid_rects(self):
        """Prompt bubbles keep off every machine's FRONT here (not just its marquee): the capsule
        machines, the showcase and the Lucky Corner cabinets all stand close together."""
        rects = super().prompt_avoid_rects()
        rects += [pygame.Rect(p.rect) for p in self.props
                  if isinstance(p, (CapsuleStation, ShowcaseStation)) or hasattr(p, "kind")]
        return rects

    # ------------------------------------------------------------ Mochi
    def update_room(self, dt):
        self.mochi.update(dt, self.players)

    def drawables(self):
        return super().drawables() + [self.mochi]

    def draw_room_overlay(self, surf):
        self.mochi.draw_bubble(surf)

    # ------------------------------------------------------------ prize counter
    def open_prize_counter(self):
        owner = self.session.player_for_avatar(self._actor())
        self.game.scenes.push(ShopScene(self.game, owner, keeper=self.mochi))

    def open_racing_counter(self):
        owner = self.session.player_for_avatar(self._actor())
        self.game.scenes.push(PrizeCounterScene(self.game, owner))

    # ------------------------------------------------------------ capsules and showcase
    def open_capsule(self, kind):
        owner = self.session.player_for_avatar(self._actor())
        self.game.scenes.push(CapsuleScene(self.game, owner, kind))

    def open_showcase(self):
        owner = self.session.player_for_avatar(self._actor())
        self.game.scenes.push(ShowcaseScene(self.game, owner))

    def on_resume(self):
        super().on_resume()
        for prop in self.props:
            if isinstance(prop, ShowcaseStation):
                prop.refresh()              # show the pick that was just made
