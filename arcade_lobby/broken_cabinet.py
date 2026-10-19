"""BROKEN CAT-CADE: the old cabinet on the Arcade Floor that is plainly out of order.

It stands where a dark SOON cabinet used to (the island_2 slot, same footprint and walking paths), so nothing
that was walkable before is blocked now. It is an ordinary Station: walk up, press the use key, and the room
opens the fake maintenance screen (staff_ui.py) for whoever pressed it. Nothing on it says what that screen
can do. The only hints are in-world: a marker-pen MEOW sticker with a paw, a CRT that blips "5151" now and
then, and (in the PRIZE PLAZA) a mumble from Mochi.

Everything animated here is drawn per frame from `self.time` with small fixed-seed noise, so it costs a
handful of pixel fills and never allocates a surface.
"""
import math
import random

import pygame

from font import get_font
from gfx import scale_color
from machine import FOOTPRINT_H, H, W, cabinet_footprint
from settings import Col
from stations import Station

NAME = "BROKEN CAT-CADE"
SLOT = "island_2"                    # arcade_layout.ARCADE_SLOTS entry this cabinet takes over

NAVY, NAVY_SIDE = (30, 28, 70), (18, 16, 46)
PURPLE, PURPLE_DIM = (110, 80, 170), (60, 46, 100)
BEZEL = pygame.Rect(4, 13, 28, 20)
CRT = pygame.Rect(5, 14, 26, 18)          # the glass, inside the bezel
MARQUEE = pygame.Rect(2, 1, W - 4, 10)
STATIC_EVERY, STATIC_FOR = 3.6, 0.28      # seconds between bursts of pixel static, and how long one lasts
MESSAGES = ("404", "404", "404", "NO OP", "404", "5151")      # what the dead CRT blips (the clue is the last one)
MESSAGE_TIME = 1.1


def _paw(s, x, y, color):
    """A tiny cat paw: one pad and three toes (5x5)."""
    s.fill(color, (x + 1, y + 2, 3, 3))
    for tx in (x, x + 2, x + 4):
        s.fill(color, (tx, y + (0 if tx == x + 2 else 1), 1, 1 if tx != x + 2 else 2))


def build_sprite():
    """The cabinet body: old navy / purple, a bent joystick, taped-up token door, sticker."""
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    s.fill(NAVY_SIDE, (0, 12, W, H - 12))
    s.fill(NAVY, (3, 12, W - 6, H - 12))
    s.fill(PURPLE_DIM, (0, 12, 1, H - 12))
    s.fill(PURPLE_DIM, (W - 1, 12, 1, H - 12))
    s.fill(NAVY, (0, 0, W, 12))                          # marquee housing (the lettering is drawn live)
    s.fill((10, 8, 24), MARQUEE)
    s.fill(PURPLE_DIM, (0, 0, W, 1))
    s.fill((6, 4, 14), BEZEL)
    pygame.draw.rect(s, PURPLE_DIM, BEZEL, 1)
    for x, y in ((6, 20), (27, 26), (12, 30)):           # scuffs on the bezel
        s.fill((52, 44, 84), (x, y + 14, 3, 1))
    s.fill((46, 34, 80), (2, 34, W - 4, 7))              # control panel, a little scratched
    s.fill(PURPLE_DIM, (2, 40, W - 4, 1))
    pygame.draw.line(s, (130, 120, 160), (9, 36), (6, 31))        # the joystick, bent over
    pygame.draw.circle(s, (190, 60, 90), (6, 31), 2)
    for i, c in enumerate((Col.YELLOW, (60, 54, 80), Col.MAGENTA)):    # one button is dead
        pygame.draw.circle(s, scale_color(c, 0.6), (18 + i * 5, 37), 1)
    s.fill((18, 12, 34), (5, 43, 26, 14))                # token door ...
    s.fill((6, 4, 14), (15, 46, 6, 7))
    pygame.draw.line(s, (170, 160, 110), (5, 43), (30, 56), 2)     # ... held shut with duct tape
    pygame.draw.line(s, (150, 140, 96), (30, 43), (5, 56), 2)
    s.fill((244, 236, 250), (5, 48, 26, 9))              # marker-pen sticker: MEOW, with a paw stuck on its corner
    s.fill((222, 190, 220), (5, 56, 26, 1))
    s.blit(get_font().render("MEOW", (96, 54, 150)), (7, 49))
    _paw(s, 25, 44, (240, 110, 170))
    s.fill(PURPLE_DIM, (0, H - 3, W, 1))                 # kick plate
    s.fill((10, 6, 20), (0, H - 2, W, 2))
    return s


def build_sign():
    """The crooked OUT OF ORDER paper sign, taped over the screen."""
    font = get_font()
    top, bottom = font.render("OUT OF", (190, 30, 50)), font.render("ORDER", (190, 30, 50))
    w = max(top.get_width(), bottom.get_width()) + 6
    paper = pygame.Surface((w, 19), pygame.SRCALPHA)
    paper.fill((246, 240, 214))
    pygame.draw.rect(paper, (190, 30, 50), paper.get_rect(), 1)
    paper.blit(top, ((w - top.get_width()) // 2, 2))
    paper.blit(bottom, ((w - bottom.get_width()) // 2, 10))
    paper.fill((200, 196, 150), (w // 2 - 3, 0, 6, 2))   # strip of tape
    return pygame.transform.rotate(paper, 6)             # crooked


class BrokenCatCade(Station):
    prompt_label = "INSPECT"

    def __init__(self, pos):
        x, y = pos
        super().__init__(build_sprite(), pos, cabinet_footprint(pygame.Rect(x, y, W, H)),
                         PURPLE_DIM, PURPLE, 0.12)
        self.rect = pygame.Rect(x, y, W, H)
        self.sign = build_sign()
        self._rng = random.Random()

    def interact(self, scene):
        scene.open_maintenance()

    # ------------------------------------------------------------ live bits
    def _static_on(self):
        return (self.time % STATIC_EVERY) < STATIC_FOR

    def _draw_marquee(self, surf, ox, oy):
        t = self.time
        if math.sin(t * 23) * math.sin(t * 7.3) > 0.55:             # now and then the whole sign drops out
            return
        word = ("CAT", "CADE")[int(t / 0.8) % 2]                     # too wide for the glass in one go: one word at a time
        if int(t * 1.3) % 4 == 0 and (t * 14) % 1 < 0.5:             # ... and it buzzes on and off
            return
        img = get_font().render(word, (150, 120, 220))
        surf.blit(img, (ox + MARQUEE.centerx - img.get_width() // 2, oy + 3))

    def _draw_screen(self, surf, ox, oy):
        t = self.time
        glass = CRT.move(ox, oy)
        level = 0.55 + 0.25 * math.sin(t * 31) * math.sin(t * 5.1)    # a worn tube, never fully steady
        surf.fill(scale_color((70, 80, 130), max(0.2, level)), glass)
        for y in range(glass.y, glass.bottom, 2):
            surf.fill((10, 8, 24), (glass.x, y, glass.w, 1))
        bar = glass.y + int(t * 9) % glass.h                          # the rolling bar
        surf.fill((90, 100, 150), (glass.x, bar, glass.w, 1), special_flags=pygame.BLEND_RGB_ADD)
        slot = int(t / MESSAGE_TIME)
        text = MESSAGES[slot % len(MESSAGES)]
        if (t / MESSAGE_TIME) % 1 < 0.82 and not self._static_on():
            img = get_font().render(text, (255, 90, 120) if text == "404" else (150, 255, 190))
            surf.blit(img, img.get_rect(center=glass.center))
        if self._static_on():                                         # pixel static: fixed-seed, so it is cheap
            self._rng.seed(int(t * 40))
            for _ in range(70):
                v = self._rng.randrange(70, 255)
                surf.fill((v, v, min(255, v + 20)), (glass.x + self._rng.randrange(glass.w),
                                                     glass.y + self._rng.randrange(glass.h), 1, 1))

    def draw(self, surf):
        super().draw(surf)
        ox, oy = self.rect.topleft
        self._draw_marquee(surf, ox, oy)
        self._draw_screen(surf, ox, oy)
        surf.blit(self.sign, (ox + 20 - self.sign.get_width() // 2 + 2, oy + 24))   # leaning off the glass
