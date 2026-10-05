"""An original 5x7 bitmap pixel font (uppercase, digits, basic punctuation).

Rendered text is cached, so drawing the same label every frame is cheap.
"""
import pygame

_GLYPHS = {
    "A": "01110 10001 10001 11111 10001 10001 10001",
    "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110",
    "D": "11110 10001 10001 10001 10001 10001 11110",
    "E": "11111 10000 10000 11110 10000 10000 11111",
    "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111",
    "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110",
    "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001",
    "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001",
    "N": "10001 10001 11001 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110",
    "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101",
    "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110",
    "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110",
    "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010",
    "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100",
    "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10001 10011 10101 11001 10001 01110",
    "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111",
    "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010",
    "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110",
    "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110",
    "9": "01110 10001 10001 01111 00001 00010 01100",
    ".": "00000 00000 00000 00000 00000 00000 00100",
    ",": "00000 00000 00000 00000 00000 00100 01000",
    "!": "00100 00100 00100 00100 00100 00000 00100",
    "?": "01110 10001 00001 00010 00100 00000 00100",
    "'": "00100 00100 01000 00000 00000 00000 00000",
    "-": "00000 00000 00000 01110 00000 00000 00000",
    ":": "00000 00100 00100 00000 00100 00100 00000",
    "/": "00001 00010 00010 00100 01000 01000 10000",
    ">": "01000 00100 00010 00001 00010 00100 01000",
    "<": "00010 00100 01000 10000 01000 00100 00010",
    "[": "01110 01000 01000 01000 01000 01000 01110",
    "]": "01110 00010 00010 00010 00010 00010 01110",
    "(": "00010 00100 01000 01000 01000 00100 00010",
    ")": "01000 00100 00010 00010 00010 00100 01000",
    "+": "00000 00100 00100 11111 00100 00100 00000",
}
GLYPH_H = 7
LINE_H = 10
SPACE_W = 3


class PixelFont:
    def __init__(self):
        self.glyphs = {ch: self._make_glyph(ch, rows) for ch, rows in _GLYPHS.items()}
        self._cache = {}

    @staticmethod
    def _make_glyph(ch, rows):
        rows = rows.split()
        cols = [x for x in range(5) if any(r[x] == "1" for r in rows)]
        # letters/digits keep a fixed 5px cell; punctuation is trimmed
        x0, x1 = (0, 4) if ch.isalnum() else (min(cols), max(cols))
        surf = pygame.Surface((x1 - x0 + 1, GLYPH_H), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x in range(x0, x1 + 1):
                if row[x] == "1":
                    surf.set_at((x - x0, y), (255, 255, 255, 255))
        return surf

    def _width(self, ch):
        g = self.glyphs.get(ch)
        return g.get_width() if g else SPACE_W

    def size(self, text, scale=1):
        text = text.upper()
        w = sum(self._width(ch) for ch in text) + max(0, len(text) - 1)
        return w * scale, GLYPH_H * scale

    def render(self, text, color, scale=1):
        key = (text, tuple(color), scale)
        surf = self._cache.get(key)
        if surf is None:
            text = text.upper()
            w, h = self.size(text)
            surf = pygame.Surface((max(1, w), h), pygame.SRCALPHA)
            x = 0
            for ch in text:
                g = self.glyphs.get(ch)
                if g:
                    surf.blit(g, (x, 0))
                x += self._width(ch) + 1
            surf.fill((*color[:3], 255), special_flags=pygame.BLEND_RGBA_MULT)
            if scale != 1:
                surf = pygame.transform.scale_by(surf, scale)
            self._cache[key] = surf
        return surf

    def render_glow(self, text, color, glow, scale=1):
        """Text with a 1px coloured halo - a cheap neon-tube look."""
        key = ("glow", text, tuple(color), tuple(glow), scale)
        surf = self._cache.get(key)
        if surf is None:
            core = self.render(text, color, scale)
            halo = self.render(text, glow, scale)
            w, h = core.get_size()
            surf = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2), (0, 0), (2, 2), (0, 2), (2, 0)):
                surf.blit(halo, (dx, dy))
            surf.blit(core, (1, 1))
            self._cache[key] = surf
        return surf


_font = None


def get_font():
    global _font
    if _font is None:
        _font = PixelFont()
    return _font
