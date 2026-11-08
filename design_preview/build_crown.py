"""Simple pixel crown study for Miao Meow (design only; the game and Mochi are untouched).

    python3 design_preview/build_crown.py

The approved black cat (body, face, ears, warm eyes, grey details, coin-bell lamp) plus a tiny gold crown that sits
between the ear tips. Composed 1:1: 6X is really 6 screen pixels per sprite pixel, 2X matches the game's view.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame  # noqa: E402

import build_lamp as L  # noqa: E402
import miao_meow_art as art  # noqa: E402
from settings import Col  # noqa: E402
from ui import draw_text  # noqa: E402

OUT = os.path.join(HERE, "crown")
SPRITES = os.path.join(OUT, "sprites")
os.makedirs(SPRITES, exist_ok=True)
LAMP = "gold"
COLS = (("NO CROWN", None, "THE APPROVED BLACK CAT"), ("CROWN, NO GEM", ("b", False), "GOLD ONLY"),
        ("CROWN, SMALL GEM", ("b", True), "ONE LILAC PIXEL"))


def sprite(crown, on):
    return art.miao_meow_sprite(0, "open", None, "original", LAMP if on else "off", None, crown)


def sheet():
    left, colw = 112, 236
    top = 82
    rows = (("HEAD", "12X CLOSE-UP", 150, 12, True), ("6X", "LAMP OFF", 140, 6, False), ("6X", "LAMP ON", 140, 6, True),
            ("2X", "LAMP OFF", 62, 2, False), ("2X", "LAMP ON", 62, 2, True))
    W = left + colw * len(COLS) + 8
    H = top + sum(r[2] + 10 for r in rows) + 92
    c = L.frame(W, H, "MIAO MEOW  TINY CROWN", "BLACK CAT + A SMALL PIXEL CROWN BETWEEN THE EARS + COIN-BELL LAMP (SOFT GOLD).")
    ys, y = [], top
    for label, sub, h, k, on in rows:
        draw_text(c, label, (22, y + h // 2 - 14), Col.CYAN, 3 if len(label) < 4 else 2)
        draw_text(c, sub, (22, y + h // 2 + (12 if len(label) < 4 else 8)), Col.YELLOW if on and k < 12 else Col.TEXT_MUTED, 1)
        ys.append(y)
        y += h + 10
    for i, (title, crown, note) in enumerate(COLS):
        x = left + i * colw
        cw = colw - 6
        draw_text(c, title, (x + cw // 2, 62), Col.CYAN if crown is None else Col.YELLOW, 2, "midtop")
        for (label, sub, h, k, on), yy in zip(rows, ys):
            img = sprite(crown, on)
            if k == 12:
                c.fill(L.FLOOR, (x, yy, cw, h))
                big = L.up(img.subsurface(pygame.Rect(0, 0, 12, 12)).copy(), 12)
                c.blit(big, big.get_rect(center=(x + cw // 2, yy + h // 2)))
            else:
                L.place(c, img, (x, yy, cw, h), k, art.LAMPS[LAMP]["glow"] if on else None)
        draw_text(c, note, (x + cw // 2, H - 78), Col.TEXT_MUTED, 1, "midtop")
    for j, (name, rgb) in enumerate((("GOLD", art.CROWN["gold"]), ("LIGHT", art.CROWN["light"]), ("BAND", art.CROWN["shade"]),
                                     ("GEM", art.CROWN["gem"]))):
        cx = left + colw + 20 + j * 74
        c.fill(Col.OUTLINE, (cx - 2, H - 62, 22, 18))
        c.fill(rgb, (cx, H - 60, 18, 14))
        draw_text(c, name, (cx + 24, H - 57), Col.TEXT_MUTED, 1)
    draw_text(c, "THE CROWN IS 3 PIXELS WIDE AND 3 TALL: IT SITS BETWEEN THE EAR TIPS AND STOPS ABOVE THE EYES.",
              (22, H - 34), Col.TEXT_MUTED, 1)
    draw_text(c, "THE SOFT LIGHT POOL IN THE LAMP-ON ROWS IS A PREVIEW LAYER, NOT PART OF THE SPRITE.", (22, H - 21), Col.TEXT_MUTED, 1)
    pygame.image.save(c, os.path.join(OUT, "01_crown_comparison.png"))
    print("wrote crown/01_crown_comparison.png", c.get_size())


def export_sprites():
    for name, crown in (("nocrown", None), ("crown", ("b", False)), ("crown_gem", ("b", True))):
        for on in (False, True):
            pygame.image.save(sprite(crown, on), os.path.join(SPRITES, f"miao_meow_{name}_lamp_{'on' if on else 'off'}_20x17.png"))


if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((1, 1))
    sheet()
    export_sprites()
