"""The NEON VEND-O-MATIC machine standing on the Arcade Floor.

Same size, position and colours as the original prop (room.make_vending); what is new is a lit
ticker marquee, a softly pulsing product window with little twinkling goods, and a blinking
ticket slot. It is an ordinary Station: walk up, press the use key, and the scene opens the
vending screen (vending_ui.py) for whoever pressed it.
"""
import math

import pygame

from font import get_font
from gfx import outlined, scale_color, shade
from settings import Col
from stations import Station

NAME = "NEON VEND-O-MATIC"
SIZE = (30, 58)
TICKER = "VEND-O-MATIC"
TICKER_PAGES = ("VEND", "-O-", "MATIC")
TICKER_COLORS = (Col.MAGENTA, Col.CYAN, Col.YELLOW, Col.GREEN)
SHELF_COLORS = (Col.MAGENTA, Col.CYAN, Col.YELLOW, Col.GREEN)
ROWS, COLS = 4, 4


def make_vending_sprite():
    """The original machine, with a marquee strip at the top (the glass shortened to four shelves)."""
    w, h = SIZE
    s = pygame.Surface(SIZE, pygame.SRCALPHA)
    s.fill((30, 40, 90), (0, 0, w, h))
    s.fill((44, 60, 130), (0, 0, 2, h))
    s.fill((8, 10, 28), (2, 2, w - 4, 8))                 # marquee (the ticker scrolls over it)
    s.fill((12, 16, 40), (3, 11, 17, 32))                 # glass front
    for row in range(ROWS):
        y = 13 + row * 7
        s.fill((80, 90, 150), (3, y + 5, 17, 1))
        for col in range(COLS):
            c = SHELF_COLORS[(row + col) % 4]
            s.fill(c, (5 + col * 4, y, 2, 5))
            s.fill(shade(c, 0.5), (5 + col * 4, y, 1, 1))
    s.fill((200, 250, 255), (4, 12, 1, 30))               # glass shine
    s.fill((50, 70, 150), (22, 11, 6, 14))                # keypad
    for i in range(6):
        s.fill(Col.CYAN if i % 2 else (160, 190, 255), (23 + (i % 2) * 2, 13 + (i // 2) * 3, 1, 1))
    s.fill((16, 20, 50), (22, 28, 6, 8))                  # ticket slot plate
    s.fill((8, 8, 24), (4, 46, 22, 7))                    # pick-up tray
    s.fill(Col.CYAN, (0, 0, w, 1))
    s.fill(Col.CYAN, (0, h - 2, w, 1))
    return s


def _outlined(sprite):
    return outlined(sprite)


def _outlined_with(sprite, color):
    return outlined(sprite, color)


class VendingMachine(Station):
    prompt_label = "VEND-O-MATIC"

    def interact(self, scene):
        scene.open_vending()

    def __init__(self, pos=(332, 32), footprint=(333, 0, 30, 26)):
        inner = make_vending_sprite()
        super().__init__(_outlined(inner), pos, footprint, Col.CYAN, Col.MAGENTA, 0.4, outline=False)
        self.highlighted = _outlined_with(inner, shade(self.accent, 0.5))    # selected: a bright outline, not a wash
        font = get_font()
        self._pages = []                 # "VEND", "-O-", "MATIC": each fits the 24px window whole, so it reads at a glance
        for text in TICKER_PAGES:
            parts = [font.render(ch, TICKER_COLORS[n % 4]) for n, ch in enumerate(text)]
            width = sum(p.get_width() + 1 for p in parts) - 1
            img = pygame.Surface((width, 7), pygame.SRCALPHA)
            x = 0
            for p in parts:
                img.blit(p, (x, 0))
                x += p.get_width() + 1
            self._pages.append(img)
        self._glass = pygame.Surface((17, 32))

    def draw(self, surf):
        super().draw(surf)
        ox, oy = self.pos[0] + 1, self.pos[1] + 1          # content origin inside the outlined art
        # ticker marquee: VEND / -O- / MATIC, one word at a time, with a quick blink between words
        page = int(self.time / 0.9) % len(self._pages)
        if (self.time % 0.9) > 0.12:
            img = self._pages[page]
            surf.blit(img, (ox + 3 + (24 - img.get_width()) // 2, oy + 3))
        # the window breathes: a soft additive pulse, plus a sheen sliding down the glass
        pulse = 0.10 + 0.07 * math.sin(self.time * 2.2)
        self._glass.fill(scale_color(Col.CYAN, pulse))
        sheen = int(self.time * 9) % 46 - 6
        if 0 <= sheen < 32:
            pygame.draw.line(self._glass, scale_color((200, 250, 255), 0.4), (0, sheen), (16, sheen))
        surf.blit(self._glass, (ox + 3, oy + 11), special_flags=pygame.BLEND_RGB_ADD)
        # a few goods twinkle
        for k in range(3):
            phase = (self.time * 0.9 + k * 0.37) % 1.0
            if phase < 0.18:
                row, col = (int(self.time * 0.9 + k * 0.37) * 5 + k * 3) % ROWS, (k * 2 + 1) % COLS
                surf.fill((255, 255, 255), (ox + 5 + col * 4, oy + 13 + row * 7, 1, 1))
        # ticket slot blinks
        lit = int(self.time * 2) % 2
        surf.fill(Col.YELLOW if lit else shade(Col.YELLOW, -0.5), (ox + 24, oy + 31, 2, 3))
