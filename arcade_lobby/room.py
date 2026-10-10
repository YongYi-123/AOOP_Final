"""Shared room furniture: the Prop base class (depth-sorted, collidable,
glowing furniture), a few prop sprites and the wall collision rects."""

import pygame

from font import get_font
from gfx import outlined, shade, soft_shadow
from settings import (Col, FLOOR_BOTTOM, FLOOR_TOP, SIDE_DOOR_H, SIDE_DOOR_Y,
                      VIEW_H, VIEW_W, WALL_SIDE)

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
    s.fill(Col.YELLOW, (24, 24, 2, 4))                    # token slot
    s.fill((8, 8, 24), (4, 46, 22, 7))                    # pick-up bin
    s.fill(Col.CYAN, (0, 0, w, 1))
    s.fill(Col.CYAN, (0, h - 2, w, 1))
    return outlined(s)


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
    return s


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

    solid = True            # False: decoration the player and cats walk through

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


# ------------------------------------------------------------------------ walls
def room_walls(door_sides=()):
    """Collision rects for the back, side and bottom walls. A side named in
    `door_sides` ("left" / "right") has a doorway gap, and a solid just
    off-screen keeps the player from walking out of the world through it."""
    gap_top, gap_bottom = SIDE_DOOR_Y, SIDE_DOOR_Y + SIDE_DOOR_H
    walls = [
        pygame.Rect(0, 0, VIEW_W, FLOOR_TOP),
        pygame.Rect(0, FLOOR_BOTTOM, VIEW_W, VIEW_H - FLOOR_BOTTOM),
    ]
    for side, x in (("left", 0), ("right", VIEW_W - WALL_SIDE)):
        if side in door_sides:
            walls.append(pygame.Rect(x, 0, WALL_SIDE, gap_top))
            walls.append(pygame.Rect(x, gap_bottom, WALL_SIDE, VIEW_H - gap_bottom))
            edge = -WALL_SIDE if side == "left" else VIEW_W
            walls.append(pygame.Rect(edge, 0, WALL_SIDE, VIEW_H))
        else:
            walls.append(pygame.Rect(x, 0, WALL_SIDE, VIEW_H))
    return walls
