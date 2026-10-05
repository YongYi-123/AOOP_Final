"""Furniture for the lofi arcade: lounge couch, beanbag, coffee table with a
steaming mug, floor lamp, speaker, cafe counter, stools and plants.
All sprites are procedural originals, painted once at load time."""
import math

import pygame

from backdrop import BlinkLED, level_copies, mask_glow
from font import get_font
from gfx import outlined, radial_glow, scale_color, shade
from room import Prop
from settings import Lofi


# ------------------------------------------------------------------ sprites
def make_couch():
    body, dark, light = (86, 62, 132), (60, 42, 100), (112, 86, 166)
    s = pygame.Surface((58, 30), pygame.SRCALPHA)
    s.fill(body, (3, 2, 52, 11))                      # backrest
    s.fill(light, (4, 1, 50, 2))
    s.fill(dark, (3, 11, 52, 2))
    for x in (6, 29):                                 # seat cushions
        s.fill((98, 72, 150), (x, 12, 23, 9))
        s.fill(light, (x, 12, 23, 2))
        s.fill(dark, (x + 22, 12, 1, 9))
    s.fill(dark, (4, 21, 50, 6))                      # front face
    s.fill(shade(dark, -0.25), (4, 26, 50, 1))
    for x in (0, 51):                                 # armrests
        s.fill(dark, (x, 6, 7, 20))
        s.fill(light, (x, 6, 7, 3))
        s.fill(body, (x + 1, 9, 5, 2))
    for x in (5, 51):
        s.fill(Lofi.WOOD_DARK, (x, 27, 2, 3))          # legs
    s.fill((226, 138, 178), (9, 6, 10, 8))             # pillow
    s.fill((250, 180, 206), (10, 6, 8, 2))
    s.fill((190, 104, 146), (9, 13, 10, 1))
    s.fill((70, 140, 150), (38, 11, 13, 9))            # folded blanket
    for y in (13, 16):
        s.fill((110, 184, 184), (38, y, 13, 1))
    s.fill((52, 108, 120), (38, 19, 13, 1))
    return outlined(s)


def make_beanbag():
    s = pygame.Surface((22, 18), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (44, 84, 112), (0, 5, 22, 13))
    pygame.draw.ellipse(s, (62, 112, 142), (0, 3, 22, 13))
    pygame.draw.ellipse(s, (86, 140, 170), (3, 4, 13, 6))
    pygame.draw.ellipse(s, (50, 94, 124), (7, 7, 10, 5))   # the cosy dent
    s.fill((120, 176, 200), (5, 5, 3, 1))
    return outlined(s)


def make_coffee_table():
    s = pygame.Surface((30, 16), pygame.SRCALPHA)
    s.fill(Lofi.WOOD, (0, 4, 30, 7))
    s.fill(Lofi.WOOD_HI, (0, 4, 30, 1))
    s.fill(Lofi.WOOD_DARK, (1, 11, 28, 2))
    for x in (2, 26):
        s.fill(Lofi.WOOD_DARK, (x, 13, 2, 3))
    s.fill(Lofi.CREAM, (3, 6, 9, 5))                   # a cassette tape
    s.fill((226, 130, 170), (4, 6, 7, 2))
    s.fill((40, 30, 50), (5, 9, 1, 1))
    s.fill((40, 30, 50), (9, 9, 1, 1))
    s.fill((90, 130, 200), (20, 6, 7, 2))              # little book stack
    s.fill((200, 150, 90), (21, 8, 6, 2))
    s.fill((236, 228, 244), (14, 2, 4, 5))             # mug
    s.fill((120, 72, 52), (14, 2, 4, 1))
    s.fill((236, 228, 244), (18, 3, 1, 2))
    s.fill((190, 180, 210), (14, 6, 4, 1))
    return outlined(s)


def make_floor_lamp():
    s = pygame.Surface((12, 44), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (40, 34, 60), (1, 40, 10, 4))
    s.fill((82, 74, 104), (5, 11, 2, 30))
    pygame.draw.polygon(s, (240, 176, 110), [(0, 11), (11, 11), (9, 1), (2, 1)])
    s.fill((255, 216, 150), (2, 2, 8, 2))
    s.fill((255, 236, 190), (1, 10, 10, 1))            # warm light leaking out
    s.fill((214, 140, 90), (0, 11, 12, 1))
    return outlined(s)


def make_speaker(bump=False):
    s = pygame.Surface((16, 28), pygame.SRCALPHA)
    s.fill((34, 30, 52), (0, 0, 16, 28))
    s.fill((46, 40, 70), (0, 0, 2, 28))
    s.fill((24, 20, 38), (1, 26, 14, 2))
    pygame.draw.circle(s, (80, 74, 110), (8, 6), 3)    # tweeter
    pygame.draw.circle(s, (20, 18, 32), (8, 6), 2)
    s.fill((120, 110, 160), (8, 6, 1, 1))
    ring = 6 if bump else 5
    pygame.draw.circle(s, (86, 78, 120), (8, 17), ring)
    pygame.draw.circle(s, (20, 18, 32), (8, 17), ring - 1)
    pygame.draw.circle(s, (72, 64, 104) if bump else (56, 50, 84), (8, 17), 2 if not bump else 3)
    s.fill((130, 120, 170), (7, 16, 1, 1))
    return outlined(s)


def make_counter():
    w, h = 80, 38
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill(Lofi.WOOD, (0, 10, w, 6))                   # counter top
    s.fill(Lofi.WOOD_HI, (0, 10, w, 1))
    s.fill((40, 32, 70), (0, 16, w, h - 16))           # front
    for x in range(4, w, 8):
        s.fill((46, 38, 80), (x, 18, 4, h - 22))
    s.fill(scale_color(Lofi.CYAN, 0.55), (0, h - 3, w, 1))
    s.fill(Lofi.WOOD_DARK, (0, 16, w, 1))
    label = get_font().render_glow("CAFE", (255, 214, 160), (150, 80, 40))
    s.blit(label, (w // 2 - label.get_width() // 2, 21))
    # things on the counter
    pygame.draw.polygon(s, (240, 176, 110), [(2, 5), (10, 5), (8, 1), (4, 1)])   # lamp
    s.fill((255, 226, 170), (3, 4, 6, 1))
    s.fill((82, 74, 104), (5, 6, 2, 4))
    s.fill((226, 140, 180), (22, 5, 4, 5))             # iced drink + straw
    s.fill((250, 240, 250), (22, 5, 4, 1))
    s.fill(Lofi.CYAN, (24, 1, 1, 4))
    s.fill(Lofi.TERRACOTTA, (36, 7, 6, 3))             # tiny succulent
    s.fill(Lofi.LEAF, (36, 4, 2, 3))
    s.fill(Lofi.LEAF_LIGHT, (38, 3, 2, 4))
    s.fill(Lofi.LEAF, (40, 5, 2, 2))
    s.fill((150, 170, 210), (46, 4, 5, 6))             # tip jar
    s.fill((200, 220, 250), (46, 4, 5, 1))
    s.fill(Lofi.WARM, (48, 8, 2, 1))
    s.fill((70, 66, 100), (58, 3, 16, 7))              # register
    s.fill((24, 22, 40), (60, 4, 8, 3))
    s.fill(scale_color(Lofi.CYAN, 0.7), (61, 5, 5, 1))
    for i in range(3):
        s.fill((120, 112, 150), (60 + i * 3, 8, 2, 1))
    return outlined(s)


def make_stool():
    s = pygame.Surface((14, 16), pygame.SRCALPHA)
    s.fill((70, 64, 100), (6, 6, 2, 8))
    s.fill((90, 84, 124), (3, 11, 8, 1))
    s.fill((60, 54, 90), (3, 14, 8, 2))
    pygame.draw.ellipse(s, (104, 58, 96), (0, 1, 14, 7))
    pygame.draw.ellipse(s, (150, 84, 130), (0, 0, 14, 6))
    s.fill((196, 130, 170), (3, 1, 4, 1))
    return outlined(s)


def make_tall_plant():
    s = pygame.Surface((22, 38), pygame.SRCALPHA)
    for (x0, y0), (x1, y1) in (((11, 28), (5, 12)), ((11, 28), (16, 8)), ((11, 28), (11, 4))):
        pygame.draw.line(s, Lofi.LEAF_DARK, (x0, y0), (x1, y1))
    for rect, c in (((0, 10, 10, 8), Lofi.LEAF_DARK), ((12, 6, 10, 8), Lofi.LEAF_DARK),
                    ((6, 0, 10, 9), Lofi.LEAF), ((1, 16, 9, 7), Lofi.LEAF),
                    ((12, 14, 9, 7), Lofi.LEAF), ((7, 2, 4, 3), Lofi.LEAF_LIGHT),
                    ((14, 8, 4, 2), Lofi.LEAF_LIGHT), ((2, 12, 3, 2), Lofi.LEAF_LIGHT)):
        pygame.draw.ellipse(s, c, rect)
    s.fill(Lofi.LEAF_DARK, (10, 2, 1, 6))                  # monstera leaf splits
    s.fill(Lofi.LEAF_DARK, (4, 11, 1, 5))
    pygame.draw.polygon(s, Lofi.TERRACOTTA, [(5, 27), (17, 27), (15, 37), (7, 37)])
    s.fill(Lofi.TERRACOTTA_HI, (4, 26, 14, 2))
    s.fill(shade(Lofi.TERRACOTTA, -0.3), (7, 35, 8, 2))
    return outlined(s)


_NOTE = ("0110", "0101", "0100", "0100", "1100", "1100")


def make_note(color):
    s = pygame.Surface((4, 6), pygame.SRCALPHA)
    for y, row in enumerate(_NOTE):
        for x, ch in enumerate(row):
            if ch == "1":
                s.set_at((x, y), color)
    return s


# ------------------------------------------------------------ animated props
class FloorLamp(Prop):
    """Warm floor lamp whose halo breathes very slowly."""

    def __init__(self, pos):
        x, y = pos
        sprite = make_floor_lamp()
        super().__init__(sprite, pos, (x + 1, y + 38, 10, 6))
        self.halos = level_copies(radial_glow(18, (70, 44, 16), bands=5, squash=0.8),
                                  (0.8, 0.9, 1.0))
        self.halo_pos = (x + 6 - 18, y + 7 - 14)
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def draw_glow(self, surf):
        i = int((math.sin(self.time * 0.7) * 0.5 + 0.5) * 2.99)
        surf.blit(self.halos[i], self.halo_pos, special_flags=pygame.BLEND_RGB_ADD)


class Speaker(Prop):
    """A floor speaker that bumps to a slow lofi beat and lets the odd
    music note drift up. (Purely visual - no audio is played.)"""
    BPM = 78
    NOTE_LIFE = 2.2

    def __init__(self, pos):
        x, y = pos
        super().__init__(make_speaker(), pos, (x + 1, y + 20, 16, 8))
        self.frames = (self.sprite, make_speaker(bump=True))
        self.led = BlinkLED((14, 3), Lofi.CYAN, period=60 / self.BPM, duty=0.25)
        self.notes_img = [make_note(c) for c in ((255, 190, 225), (170, 225, 245), (255, 214, 160))]
        self.notes = []          # [age, image index, x offset]
        self.time = 0.0
        self.beat = 0

    def update(self, dt):
        self.time += dt
        beat = int(self.time * self.BPM / 60)
        if beat != self.beat:
            self.beat = beat
            if beat % 3 == 0 and len(self.notes) < 3:
                self.notes.append([0.0, beat % len(self.notes_img), (beat * 5) % 7 - 3])
        for note in self.notes:
            note[0] += dt
        self.notes = [n for n in self.notes if n[0] < self.NOTE_LIFE]

    def draw(self, surf):
        phase = (self.time * self.BPM / 60) % 1.0
        surf.blit(self.frames[1 if phase < 0.14 else 0], self.pos)
        self.led.draw(surf, self.pos, self.time)

    def draw_glow(self, surf):
        self.led.draw_glow(surf, self.pos, self.time)
        x, y = self.pos
        for age, idx, dx in self.notes:
            k = age / self.NOTE_LIFE
            if k > 0.8 and int(age * 12) % 2:      # soft blink-out at the end
                continue
            nx = x + 8 + dx + int(math.sin(age * 2.4) * 2)
            surf.blit(self.notes_img[idx], (nx, y - 4 - int(k * 22)))


class CoffeeTable(Prop):
    """Low table with a mug that lets out little curls of steam."""
    STEAM = (((0, 0), (1, -2), (0, -4)), ((1, -1), (0, -3), (1, -5)), ((0, -2), (1, -4), (0, -6)))

    def __init__(self, pos):
        x, y = pos
        super().__init__(make_coffee_table(), pos, (x + 1, y + 8, 30, 8))
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        super().draw(surf)
        x, y = self.pos[0] + 16, self.pos[1] + 1
        frame = self.STEAM[int(self.time * 3) % 3]
        for i, (dx, dy) in enumerate(frame):
            surf.fill((196, 186, 226) if i < 2 else (140, 132, 176), (x + dx, y + dy, 1, 1))


class CafeCounter(Prop):
    """The cafe counter: warm lamp glow and a blinking register light."""

    def __init__(self, pos):
        x, y = pos
        sprite = make_counter()
        glow = mask_glow(sprite, scale_color(Lofi.WARM, 0.5), spread=5, strength=0.3)
        super().__init__(sprite, pos, (x + 1, y + 14, 80, 24), glow, (x - 5, y - 5))
        self.lamp = radial_glow(16, (60, 38, 14), bands=5)
        self.led = BlinkLED((72, 5), (150, 255, 180), period=2.4, duty=0.7)
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        super().draw(surf)
        self.led.draw(surf, self.pos, self.time)

    def draw_glow(self, surf):
        super().draw_glow(surf)
        x, y = self.pos
        surf.blit(self.lamp, (x + 7 - 16, y + 5 - 16), special_flags=pygame.BLEND_RGB_ADD)
        self.led.draw_glow(surf, self.pos, self.time)
