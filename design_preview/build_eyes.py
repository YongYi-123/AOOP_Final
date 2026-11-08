"""Eye colour studies for Miao Meow (design only; the game and Mochi are untouched).

    python3 design_preview/build_eyes.py

Composed 1:1: the 6X sprites are really 6 screen pixels per sprite pixel, the 2X sprites match the game's view.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "arcade_lobby"))
os.chdir(os.path.join(os.path.dirname(HERE), "arcade_lobby"))

import pygame  # noqa: E402

import miao_meow_art as art  # noqa: E402
from gfx import scale_color, soft_shadow  # noqa: E402
from settings import Col  # noqa: E402
from ui import draw_text  # noqa: E402

OUT = os.path.join(HERE, "eyes")
SPRITES = os.path.join(OUT, "sprites")
os.makedirs(SPRITES, exist_ok=True)
FLOOR = Col.FLOOR_ALT
OUTFITS = (("BLACK CAT", None), ("A VARSITY", "varsity"), ("B SCARF", "neckerchief"), ("C OVERALLS", "overalls"))


def up(img, k):
    return pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def chip(c, rgb, x, y, label, value=None):
    c.fill(Col.OUTLINE, (x - 2, y - 2, 24, 20))
    c.fill(rgb, (x, y, 20, 16))
    draw_text(c, label, (x + 30, y + 1), Col.TEXT, 1)
    if value:
        draw_text(c, value, (x + 30, y + 10), Col.TEXT_MUTED, 1)


def sheet():
    left, colw, zoomw = 24, 196, 232
    styles = list(art.EYE_STYLES)
    W = left + zoomw + colw * len(OUTFITS) + 14
    top = 70
    block_h = 24 + 140 + 8 + 62 + 16
    H = top + block_h * len(styles) + 40
    c = pygame.Surface((W, H))
    c.fill((24, 18, 48))
    pygame.draw.rect(c, Col.CYAN, (3, 3, W - 6, H - 6), 2)
    draw_text(c, "MIAO MEOW  EYE COLOUR STUDY", (20, 14), Col.YELLOW, 3, glow=scale_color(Col.MAGENTA, 0.7))
    draw_text(c, "ONLY THE SHINE PIXEL AND THE IRIS CHANGE. PUPIL, FACE, BODY AND OUTFITS ARE UNTOUCHED.", (22, 44), Col.TEXT_MUTED, 1)
    for i, (title, _) in enumerate(OUTFITS):
        draw_text(c, title, (left + zoomw + i * colw + (colw - 6) // 2, 56), Col.CYAN, 1, "midtop")
    draw_text(c, "EYE 16X", (left + zoomw // 2, 56), Col.CYAN, 1, "midtop")

    for n, key in enumerate(styles):
        es = art.EYE_STYLES[key]
        y0 = top + n * block_h
        draw_text(c, f"{n + 1}  {es['label']}", (left, y0 + 4), Col.YELLOW, 2)
        draw_text(c, es["note"], (left + 260, y0 + 9), Col.TEXT_MUTED, 1)
        y6, y2 = y0 + 24, y0 + 24 + 148

        # eye zoom: the black cat's face at 16x
        plain = art.miao_meow_sprite(0, "open", None, key)
        face = plain.subsurface(pygame.Rect(1, 4, 8, 6)).copy()
        c.fill(FLOOR, (left, y6, zoomw - 8, 140))
        c.blit(up(face, 14), (left + 6, y6 + 28))
        chip(c, es["shine"], left + 130, y6 + 6, "SHINE", "%02X%02X%02X" % es["shine"])
        chip(c, es["iris"], left + 130, y6 + 40, "IRIS", "%02X%02X%02X" % es["iris"])
        chip(c, es["pupil"], left + 130, y6 + 74, "PUPIL", "%02X%02X%02X" % es["pupil"])
        draw_text(c, "SHINE/IRIS %.1f:1" % ratio(es["shine"], es["iris"]), (left + 130, y6 + 100), Col.TEXT_MUTED, 1)
        draw_text(c, "IRIS/PUPIL %.1f:1" % ratio(es["iris"], es["pupil"]), (left + 130, y6 + 111), Col.TEXT_MUTED, 1)
        c.fill(FLOOR, (left, y2, zoomw - 8, 62))
        draw_text(c, "6X ABOVE  /  2X BELOW", (left + (zoomw - 8) // 2, y2 + 26), Col.TEXT_MUTED, 1, "midtop")

        for i, (title, outfit) in enumerate(OUTFITS):
            x = left + zoomw + i * colw
            cw = colw - 6
            img = art.miao_meow_sprite(0, "open", outfit, key)
            for (yy, hh, k) in ((y6, 140, 6), (y2, 62, 2)):
                c.fill(FLOOR, (x, yy, cw, hh))
                big = up(img, k)
                c.blit(soft_shadow(max(8, big.get_width() - 4 * k), 2 * k + 2, 120),
                       (x + cw // 2 - (big.get_width() - 4 * k) // 2, yy + hh - 9 - k))
                c.blit(big, big.get_rect(midbottom=(x + cw // 2, yy + hh - 5)))
            pygame.image.save(img, os.path.join(SPRITES, f"miao_meow_{outfit or 'plain'}_eyes_{key}_20x17.png"))
    draw_text(c, "THE THREE EYE BLOCKS (SHINE / IRIS / PUPIL) KEEP THREE DIFFERENT TONES IN EVERY STUDY.",
              (22, H - 24), Col.TEXT_MUTED, 1)
    pygame.image.save(c, os.path.join(OUT, "01_eye_colour_comparison.png"))
    print("wrote eyes/01_eye_colour_comparison.png", c.get_size())
    for key in styles:
        es = art.EYE_STYLES[key]
        print(f"{key:11s} shine/iris {ratio(es['shine'], es['iris']):.2f}  iris/pupil {ratio(es['iris'], es['pupil']):.2f}")


if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((1, 1))
    sheet()
