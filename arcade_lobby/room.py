"""The neon arcade room: background art, furniture props, collision, neon
signs, animated floor strips and pre-baked lighting layers."""
import math
import random

import pygame

from font import get_font
from gfx import (glow_line, lerp_color, neon_rect_glow, outlined, radial_glow,
                 scale_color, shade, soft_shadow)
from settings import (Col, DOOR_W, DOOR_X, FLOOR_BOTTOM, FLOOR_TOP, VIEW_H,
                      VIEW_W, WALL_SIDE)

LEAF = (60, 170, 110)
LEAF_DARK = (36, 120, 90)
LEAF_LIGHT = (110, 230, 150)
POT = (90, 60, 170)


# ---------------------------------------------------------------- prop sprites
def make_plant(pot=POT, rim=Col.MAGENTA):
    s = pygame.Surface((18, 26), pygame.SRCALPHA)
    pygame.draw.ellipse(s, LEAF_DARK, (0, 7, 9, 11))
    pygame.draw.ellipse(s, LEAF_DARK, (9, 7, 9, 11))
    pygame.draw.ellipse(s, LEAF, (4, 1, 10, 14))
    pygame.draw.ellipse(s, LEAF, (1, 9, 6, 7))
    pygame.draw.ellipse(s, LEAF, (11, 9, 6, 7))
    pygame.draw.ellipse(s, LEAF_LIGHT, (6, 3, 4, 5))
    pygame.draw.polygon(s, pot, [(3, 17), (14, 17), (12, 25), (5, 25)])
    s.fill(rim, (3, 16, 12, 2))
    s.fill(shade(pot, -0.3), (5, 23, 7, 2))
    return outlined(s)


def make_stool():
    s = pygame.Surface((12, 14), pygame.SRCALPHA)
    s.fill((70, 64, 100), (5, 6, 2, 8))
    s.fill((90, 84, 124), (2, 12, 8, 2))
    pygame.draw.ellipse(s, (30, 22, 56), (0, 1, 12, 7))
    pygame.draw.ellipse(s, (52, 36, 96), (0, 0, 12, 6))
    pygame.draw.ellipse(s, Col.CYAN, (0, 0, 12, 6), 1)
    s.fill((200, 250, 255), (3, 1, 3, 1))
    return outlined(s)


def make_table():
    s = pygame.Surface((22, 24), pygame.SRCALPHA)
    s.fill((70, 64, 100), (10, 8, 2, 14))
    s.fill((90, 84, 124), (5, 21, 12, 3))
    pygame.draw.ellipse(s, (30, 22, 56), (0, 5, 22, 10))
    pygame.draw.ellipse(s, (60, 42, 108), (0, 4, 22, 9))
    pygame.draw.ellipse(s, Col.MAGENTA, (0, 4, 22, 9), 1)
    # a glowing soda and a slice of pizza
    s.fill((120, 240, 255), (6, 0, 4, 7))
    s.fill((255, 255, 255), (6, 0, 4, 1))
    s.fill(Col.MAGENTA, (8, 0, 1, 1))
    pygame.draw.polygon(s, Col.YELLOW, [(12, 6), (18, 6), (15, 10)])
    s.fill((230, 70, 70), (14, 7, 1, 1))
    return outlined(s)


def make_vending():
    w, h = 30, 58
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((30, 40, 90), (0, 0, w, h))
    s.fill((44, 60, 130), (0, 0, 2, h))
    s.fill((12, 16, 40), (3, 4, 17, 38))                 # glass front
    for row in range(5):
        y = 6 + row * 7
        s.fill((80, 90, 150), (3, y + 5, 17, 1))
        for col in range(4):
            c = (Col.MAGENTA, Col.CYAN, Col.YELLOW, Col.GREEN)[(row + col) % 4]
            s.fill(c, (5 + col * 4, y, 2, 5))
            s.fill(shade(c, 0.5), (5 + col * 4, y, 1, 1))
    s.fill((200, 250, 255), (4, 5, 1, 30))                # glass shine
    s.fill((50, 70, 150), (22, 6, 6, 14))                 # keypad
    for i in range(6):
        s.fill(Col.CYAN if i % 2 else (160, 190, 255), (23 + (i % 2) * 2, 8 + (i // 2) * 3, 1, 1))
    s.fill(Col.YELLOW, (24, 24, 2, 4))                    # coin slot
    s.fill((8, 8, 24), (4, 46, 22, 7))                    # pick-up bin
    s.fill(Col.CYAN, (0, 0, w, 1))
    s.fill(Col.CYAN, (0, h - 2, w, 1))
    return outlined(s)


def make_claw_base():
    w, h = 36, 60
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((70, 20, 80), (0, 34, w, h - 34))               # base cabinet
    s.fill((50, 14, 60), (3, 38, w - 6, h - 42))
    s.fill((16, 10, 36), (1, 4, w - 2, 30))                # glass box
    s.fill((60, 40, 110), (1, 0, w - 2, 5))                # roof
    s.fill(Col.MAGENTA, (0, 0, w, 1))
    s.fill(Col.MAGENTA, (0, 34, w, 1))
    for x in (0, w - 1):
        s.fill(Col.MAGENTA, (x, 0, 1, h))
    # plushies in the pile (one is a tiny cat!)
    for x, c in ((4, (255, 140, 190)), (11, (120, 220, 255)), (18, (255, 214, 90)),
                 (25, (160, 240, 150)), (8, (190, 150, 255)), (21, (255, 120, 120))):
        y = 26 if x in (8, 21) else 29
        pygame.draw.circle(s, c, (x + 3, y), 3)
        s.fill(Col.OUTLINE, (x + 2, y - 1, 1, 1))
        s.fill(Col.OUTLINE, (x + 4, y - 1, 1, 1))
    pygame.draw.circle(s, (246, 164, 86), (29, 25), 3)
    pygame.draw.polygon(s, (246, 164, 86), [(26, 23), (27, 20), (29, 23)])
    pygame.draw.polygon(s, (246, 164, 86), [(29, 23), (31, 20), (32, 23)])
    s.fill((200, 240, 255), (3, 6, 1, 18))                 # glass shine
    s.fill(Col.YELLOW, (8, 40, 20, 5))                     # prize chute sign
    s.fill((16, 10, 36), (12, 49, 12, 8))
    return s


def make_prize_counter():
    w, h = 80, 34
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((40, 30, 80), (0, 0, w, 14))                    # glass-topped display
    s.fill((20, 16, 46), (2, 2, w - 4, 10))
    for i, c in enumerate(((255, 140, 190), (120, 220, 255), (255, 214, 90),
                           (160, 240, 150), (190, 150, 255), (255, 120, 120))):
        x = 6 + i * 12
        pygame.draw.circle(s, c, (x + 3, 7), 3)
        s.fill(Col.OUTLINE, (x + 2, 6, 1, 1))
        s.fill(Col.OUTLINE, (x + 4, 6, 1, 1))
    s.fill((200, 240, 255), (4, 3, w - 8, 1))
    s.fill(Col.YELLOW, (0, 13, w, 1))
    s.fill((30, 22, 60), (0, 14, w, h - 14))               # front face
    font = get_font()
    label = font.render_glow("PRIZES", Col.YELLOW, (140, 90, 20))
    s.blit(label, (w // 2 - label.get_width() // 2, 19))
    s.fill(Col.MAGENTA, (0, h - 3, w, 1))
    return outlined(s)


def make_gumball():
    s = pygame.Surface((12, 22), pygame.SRCALPHA)
    s.fill((200, 40, 120), (3, 11, 6, 9))
    s.fill((150, 30, 100), (1, 19, 10, 3))
    s.fill(Col.YELLOW, (5, 14, 2, 2))
    pygame.draw.circle(s, (200, 230, 255), (6, 6), 6)
    for gx, gy, c in ((4, 5, Col.MAGENTA), (7, 4, Col.YELLOW), (5, 8, Col.CYAN),
                      (8, 7, Col.GREEN), (3, 8, Col.YELLOW), (6, 2, Col.PURPLE)):
        s.fill(c, (gx, gy, 2, 2))
    s.fill((255, 255, 255), (3, 2, 1, 2))
    return outlined(s)


class Prop:
    """A piece of furniture that is depth-sorted with the player.
    `glow` is an optional pre-rendered additive halo drawn after lighting."""

    def __init__(self, sprite, pos, footprint, glow=None, glow_pos=None):
        self.sprite = sprite
        self.pos = pos
        self.footprint = pygame.Rect(footprint)
        self.shadow = soft_shadow(self.footprint.w + 4, 6)
        self.glow = glow
        self.glow_pos = glow_pos

    @property
    def sort_y(self):
        return self.footprint.bottom

    def update(self, dt):
        pass

    def draw_under(self, surf):
        surf.blit(self.shadow, (self.footprint.x - 2, self.footprint.bottom - 4))

    def draw(self, surf):
        surf.blit(self.sprite, self.pos)

    def draw_glow(self, surf):
        if self.glow:
            surf.blit(self.glow, self.glow_pos, special_flags=pygame.BLEND_RGB_ADD)


class ClawMachine(Prop):
    """Prize grabber whose claw lazily swings back and forth."""

    def __init__(self, pos, glow_strength=0.45):
        x, y = pos
        glow = neon_rect_glow(36, 60, Col.MAGENTA, 8, glow_strength)
        super().__init__(outlined(make_claw_base()), (x - 1, y - 1),
                         (x, FLOOR_TOP, 36, y + 60 - FLOOR_TOP), glow, (x - 8, y - 8))
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        super().draw(surf)
        x, y = self.pos[0] + 1, self.pos[1] + 1
        cx = x + 18 + int(math.sin(self.time * 0.9) * 11)
        drop = int(max(0.0, math.sin(self.time * 0.45)) * 6)
        surf.fill((170, 170, 200), (cx, y + 5, 1, 6 + drop))
        surf.fill((220, 220, 240), (cx - 2, y + 11 + drop, 5, 1))
        surf.fill((220, 220, 240), (cx - 2, y + 12 + drop, 1, 2))
        surf.fill((220, 220, 240), (cx + 2, y + 12 + drop, 1, 2))


# ------------------------------------------------------------------------ room
def room_walls():
    """Collision rects for the back, side and bottom walls."""
    return [
        pygame.Rect(0, 0, VIEW_W, FLOOR_TOP),
        pygame.Rect(0, 0, WALL_SIDE, VIEW_H),
        pygame.Rect(VIEW_W - WALL_SIDE, 0, WALL_SIDE, VIEW_H),
        pygame.Rect(0, FLOOR_BOTTOM, VIEW_W, VIEW_H - FLOOR_BOTTOM),
    ]


class Room:
    """The original bright neon room ("neon" style)."""
    SIGN_POS = (112, 8)
    cat_spots = ()          # extra cozy places the cat likes to visit

    def __init__(self, machines):
        self.machines = machines
        self.props = self._build_props()
        self.walls = room_walls()
        self.solids = (self.walls + [p.footprint for p in self.props]
                       + [m.footprint for m in machines])

        # Neon floor strips: (rect, colour). Pulsed and chased every frame.
        self.strips = [
            (pygame.Rect(40, 120, 196, 1), Col.CYAN),
            (pygame.Rect(DOOR_X - 4, 236, 1, FLOOR_BOTTOM - 236), Col.MAGENTA),
            (pygame.Rect(DOOR_X + DOOR_W + 3, 236, 1, FLOOR_BOTTOM - 236), Col.MAGENTA),
        ]
        self.background = self._build_background()
        self._build_sign()
        self.shade, self.glow = self._build_lighting()

        rng = random.Random(7)
        self.motes = [[rng.uniform(30, 370), rng.uniform(70, 270), rng.uniform(0, 6.28)]
                      for _ in range(14)]
        self.time = 0.0
        self.sign_on = True

    def _build_props(self):
        stool = make_stool()
        vend_glow = neon_rect_glow(30, 58, Col.CYAN, 7, 0.4)
        prize_glow = neon_rect_glow(80, 34, Col.YELLOW, 6, 0.25)
        return [
            Prop(make_plant(), (22, 40), (24, FLOOR_TOP, 14, 4)),
            Prop(make_plant(), (360, 40), (362, FLOOR_TOP, 14, 4)),
            Prop(make_vending(), (248, 32), (249, FLOOR_TOP, 30, 26),
                 vend_glow, (242, 27)),
            ClawMachine((288, 30)),
            Prop(make_prize_counter(), (294, 166), (295, 176, 80, 24),
                 prize_glow, (289, 161)),
            Prop(make_table(), (58, 184), (62, 198, 14, 10)),
            Prop(stool, (40, 192), (41, 200, 12, 6)),
            Prop(stool, (84, 192), (85, 200, 12, 6)),
            Prop(stool, (108, 140), (109, 148, 12, 6)),
            Prop(make_plant(), (22, 148), (25, 164, 13, 10)),
            Prop(make_plant(), (356, 248), (359, 264, 13, 10)),
            Prop(make_gumball(), (236, 252), (237, 268, 12, 6)),
        ]

    # ------------------------------------------------------------ background
    def _build_background(self):
        bg = pygame.Surface((VIEW_W, VIEW_H))
        self._paint_floor(bg)
        self._paint_back_wall(bg)
        self._paint_walls(bg)
        self._paint_strip_glows(bg)
        return bg

    def _paint_strip_glows(self, bg):
        """Neon strip halos are baked under the sprites so cabinets occlude them."""
        def add(surf, pos):
            bg.blit(surf, pos, special_flags=pygame.BLEND_RGB_ADD)

        add(glow_line(VIEW_W, Col.MAGENTA, spread=6, strength=0.35), (-6, 38))
        add(glow_line(VIEW_W, Col.CYAN, spread=4, strength=0.3), (-4, -1))
        for rect, color in self.strips:
            vertical = rect.h > rect.w
            g = glow_line(max(rect.w, rect.h), color, vertical, spread=5, strength=0.3)
            add(g, (rect.x - 5, rect.y - 5))

    def _paint_floor(self, bg):
        """Dark arcade carpet with a scatter of little neon shapes."""
        bg.fill(Col.FLOOR, (0, FLOOR_TOP, VIEW_W, FLOOR_BOTTOM - FLOOR_TOP))
        for y in range(FLOOR_TOP, FLOOR_BOTTOM, 20):
            for x in range(0, VIEW_W, 20):
                if (x // 20 + y // 20) % 2:
                    bg.fill(Col.FLOOR_ALT, (x, y, 20, 20))
        rng = random.Random(3)
        colors = [scale_color(c, 0.38) for c in (Col.MAGENTA, Col.CYAN, Col.PURPLE, Col.YELLOW)]
        for _ in range(70):
            x = rng.randrange(WALL_SIDE + 2, VIEW_W - WALL_SIDE - 6)
            y = rng.randrange(FLOOR_TOP + 4, FLOOR_BOTTOM - 6)
            c = rng.choice(colors)
            kind = rng.randrange(4)
            if kind == 0:      # tiny triangle
                pygame.draw.polygon(bg, c, [(x, y + 3), (x + 2, y), (x + 4, y + 3)], 1)
            elif kind == 1:    # squiggle
                for i in range(5):
                    bg.fill(c, (x + i, y + (i % 2), 1, 1))
            elif kind == 2:    # plus
                bg.fill(c, (x + 1, y, 1, 3))
                bg.fill(c, (x, y + 1, 3, 1))
            else:              # dot pair
                bg.fill(c, (x, y, 1, 1))
                bg.fill(c, (x + 2, y + 2, 1, 1))

        # shadow at the base of the back wall
        shadow = pygame.Surface((VIEW_W, 6), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 90), (0, 0, VIEW_W, 3))
        shadow.fill((0, 0, 0, 45), (0, 3, VIEW_W, 3))
        bg.blit(shadow, (0, FLOOR_TOP))

        # dim base colour of the neon strips (brightened per frame)
        for rect, color in self.strips:
            bg.fill(scale_color(color, 0.3), rect.inflate(2, 2) if rect.w > 1 else rect.inflate(2, 0))

        # doorway and mat
        bg.fill((14, 10, 30), (DOOR_X, FLOOR_BOTTOM, DOOR_W, VIEW_H - FLOOR_BOTTOM))
        mat = pygame.Rect(DOOR_X + 4, FLOOR_BOTTOM - 14, DOOR_W - 8, 12)
        bg.fill((40, 26, 70), mat)
        pygame.draw.rect(bg, scale_color(Col.CYAN, 0.6), mat, 1)
        for x in range(mat.x + 4, mat.right - 4, 4):
            bg.fill((58, 40, 100), (x, mat.y + 3, 2, mat.h - 6))

    def _paint_back_wall(self, bg):
        bg.fill(Col.WALL, (0, 0, VIEW_W, FLOOR_TOP))
        for x in range(0, VIEW_W, 16):
            bg.fill(Col.WALL_PANEL, (x, 4, 1, FLOOR_TOP - 8))
        for y in (16, 30):
            bg.fill(shade(Col.WALL, -0.2), (0, y, VIEW_W, 1))
        bg.fill(Col.WALL_CAP, (0, 0, VIEW_W, 3))
        bg.fill(Col.CYAN, (0, 3, VIEW_W, 1))                      # ceiling neon
        bg.fill(scale_color(Col.MAGENTA, 0.5), (0, 43, VIEW_W, 3))  # wall neon strip
        bg.fill(Col.MAGENTA, (0, 44, VIEW_W, 1))
        bg.fill(Col.WALL_CAP, (0, FLOOR_TOP - 4, VIEW_W, 4))
        bg.fill(scale_color(Col.PURPLE, 0.6), (0, FLOOR_TOP - 4, VIEW_W, 1))

        self._paint_cat_poster(bg, pygame.Rect(30, 9, 22, 28))
        self._paint_scoreboard(bg, pygame.Rect(330, 8, 22, 26))
        # little lightning bolts either side of the sign
        for bx in (100, 190):
            pygame.draw.polygon(bg, Col.YELLOW, [(bx + 3, 8), (bx, 15), (bx + 3, 15),
                                                 (bx + 1, 22), (bx + 6, 13), (bx + 3, 13), (bx + 5, 8)])

    def _paint_cat_poster(self, bg, r):
        bg.fill(Col.CYAN, r.inflate(2, 2))
        bg.fill((30, 14, 60), r)
        cx, cy = r.centerx, r.centery + 1
        pygame.draw.circle(bg, Col.MAGENTA, (cx, cy), 7)
        pygame.draw.polygon(bg, Col.MAGENTA, [(cx - 7, cy - 2), (cx - 6, cy - 10), (cx - 2, cy - 6)])
        pygame.draw.polygon(bg, Col.MAGENTA, [(cx + 7, cy - 2), (cx + 6, cy - 10), (cx + 2, cy - 6)])
        bg.fill((30, 14, 60), (cx - 4, cy - 1, 2, 2))
        bg.fill((30, 14, 60), (cx + 2, cy - 1, 2, 2))
        bg.fill(Col.YELLOW, (cx - 1, cy + 2, 2, 1))
        for sx, sy in ((3, 3), (18, 4), (4, 23), (17, 24)):
            bg.fill(Col.YELLOW, (r.x + sx, r.y + sy, 1, 1))

    def _paint_scoreboard(self, bg, r):
        bg.fill(Col.PURPLE, r.inflate(2, 2))
        bg.fill((8, 6, 20), r)
        font = get_font()
        bg.blit(font.render("HI", Col.CYAN), (r.x + 6, r.y + 3))
        for i, w in enumerate((14, 12, 10)):
            bg.fill(Col.YELLOW if i == 0 else Col.TEXT_MUTED, (r.x + 4, r.y + 13 + i * 4, w, 2))

    def _paint_walls(self, bg):
        for x in (0, VIEW_W - WALL_SIDE):
            bg.fill(Col.WALL_CAP, (x, 0, WALL_SIDE, VIEW_H))
            bg.fill(shade(Col.WALL_CAP, 0.12), (x + 3, 0, WALL_SIDE - 6, VIEW_H))
        bg.fill(Col.PURPLE, (WALL_SIDE - 1, FLOOR_TOP, 1, FLOOR_BOTTOM - FLOOR_TOP))
        bg.fill(Col.PURPLE, (VIEW_W - WALL_SIDE, FLOOR_TOP, 1, FLOOR_BOTTOM - FLOOR_TOP))
        for x0, x1 in ((0, DOOR_X), (DOOR_X + DOOR_W, VIEW_W)):
            bg.fill(Col.WALL_CAP, (x0, FLOOR_BOTTOM, x1 - x0, VIEW_H - FLOOR_BOTTOM))
            bg.fill(shade(Col.WALL_CAP, 0.12), (x0, FLOOR_BOTTOM + 3, x1 - x0, VIEW_H - FLOOR_BOTTOM - 6))
            bg.fill(Col.PURPLE, (x0, FLOOR_BOTTOM, x1 - x0, 1))
        for x in (DOOR_X - 2, DOOR_X + DOOR_W):
            bg.fill(Col.OUTLINE, (x, FLOOR_BOTTOM, 2, VIEW_H - FLOOR_BOTTOM))
        # glowing EXIT sign beside the door
        exit_sign = get_font().render_glow("EXIT", (170, 255, 190), (30, 140, 70))
        self.exit_pos = (DOOR_X + DOOR_W + 6, FLOOR_BOTTOM + 5)
        bg.fill((8, 20, 14), pygame.Rect(self.exit_pos, exit_sign.get_size()).inflate(4, 2))
        bg.blit(exit_sign, self.exit_pos)

    def _build_sign(self):
        """Big 'ARCADE' neon sign: on/off versions plus its glow."""
        font = get_font()
        self.sign_on_img = font.render_glow("ARCADE", (255, 170, 235), Col.MAGENTA, scale=2)
        self.sign_off_img = font.render_glow("ARCADE", (90, 40, 90), (60, 26, 64), scale=2)
        w, h = self.sign_on_img.get_size()
        self.sign_glow = neon_rect_glow(w, h, Col.MAGENTA, 10, 0.5)

    # --------------------------------------------------------------- lighting
    def _build_lighting(self):
        # Multiply layer: cool purple tint with a pixel-banded vignette.
        shade_layer = pygame.Surface((VIEW_W, VIEW_H))
        edge, center = (110, 90, 150), (236, 230, 255)
        shade_layer.fill(edge)
        bands = 9
        for i in range(bands):
            k = (i + 1) / bands
            rect = pygame.Rect(0, 0, int(VIEW_W * (1.5 - 0.9 * k)), int(VIEW_H * (1.5 - 0.9 * k)))
            rect.center = (VIEW_W // 2, VIEW_H // 2 + 10)
            pygame.draw.ellipse(shade_layer, lerp_color(edge, center, k), rect)

        # Additive layer for static lights: wall neon, strips, exit, pools.
        glow = pygame.Surface((VIEW_W, VIEW_H))
        glow.fill((0, 0, 0))

        def add(surf, pos):
            glow.blit(surf, pos, special_flags=pygame.BLEND_RGB_ADD)

        add(radial_glow(18, (20, 80, 40), bands=4), (self.exit_pos[0] - 6, self.exit_pos[1] - 14))
        for pos, radius, color in (((200, 180), 110, (26, 14, 40)), ((330, 200), 60, (40, 30, 10)),
                                   ((200, 300), 40, (20, 30, 50))):
            add(radial_glow(radius, color), (pos[0] - radius, pos[1] - radius))
        return shade_layer, glow

    # ------------------------------------------------------------ per frame
    def update(self, dt):
        self.time += dt
        for prop in self.props:
            prop.update(dt)
        for mote in self.motes:
            mote[0] += math.sin(self.time * 0.5 + mote[2]) * 3 * dt
            mote[1] -= 4 * dt
            if mote[1] < 66:
                mote[1] = 270
        # The sign stutters off for a moment every ~7 seconds.
        cycle = self.time % 7.0
        self.sign_on = not (6.2 < cycle < 6.28 or 6.4 < cycle < 6.5)

    def draw_background(self, surf):
        surf.blit(self.background, (0, 0))
        surf.blit(self.sign_on_img if self.sign_on else self.sign_off_img, self.SIGN_POS)
        self._draw_strips(surf)

    def _draw_strips(self, surf):
        pulse = 0.65 + 0.35 * math.sin(self.time * 1.6)
        for i, (rect, color) in enumerate(self.strips):
            surf.fill(scale_color(color, pulse), rect)
            # a bright spark chasing along the strip
            length = max(rect.w, rect.h)
            pos = int((self.time * 60 + i * 37) % (length + 20)) - 10
            if rect.w > rect.h:
                spark = pygame.Rect(rect.x + pos, rect.y, 6, 1).clip(rect)
            else:
                spark = pygame.Rect(rect.x, rect.y + pos, 1, 6).clip(rect)
            if spark.w and spark.h:
                surf.fill(shade(color, 0.7), spark)

    def drawables(self):
        return self.props + self.machines

    def draw_lighting(self, surf):
        surf.blit(self.shade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        surf.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if self.sign_on:
            sx, sy = self.SIGN_POS
            surf.blit(self.sign_glow, (sx - 10, sy - 10), special_flags=pygame.BLEND_RGB_ADD)
        for prop in self.props:
            prop.draw_glow(surf)
        for x, y, phase in self.motes:
            if math.sin(self.time * 1.7 + phase * 3) > 0.3:
                surf.fill((200, 180, 255), (int(x), int(y), 1, 1))
