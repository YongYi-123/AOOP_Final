"""Hat studies for Miao Meow (design only; the game and Mochi are untouched).

    python3 design_preview/build_hats.py

Body, face, ears, tail, eyes and grey face details are the approved black cat. Only a tiny hat is added, plus the
coin-bell lamp (soft gold) that lights up when a player walks near. Composed 1:1: 6X is really 6 screen pixels per
sprite pixel, 2X matches the game's view.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame  # noqa: E402

import build_lamp as L  # noqa: E402  (sets up paths; reuses the soft light pool and cell drawing)
import miao_meow_art as art  # noqa: E402
from gfx import scale_color  # noqa: E402
from settings import Col  # noqa: E402
from ui import draw_text  # noqa: E402

OUT = os.path.join(HERE, "hats")
SPRITES = os.path.join(OUT, "sprites")
os.makedirs(SPRITES, exist_ok=True)
LAMP = "gold"
COLS = (("NO HAT", None), ("A BERET", "beret"), ("B BASEBALL CAP", "cap"), ("C NEWSBOY CAP", "newsboy"))


def sprite(hat, on):
    return art.miao_meow_sprite(0, "open", None, "original", LAMP if on else "off", hat)


def sheet():
    left, colw = 112, 236
    top = 82
    rows = (("HEAD", "12X CLOSE-UP", 150, 12, True), ("6X", "LAMP OFF", 140, 6, False), ("6X", "LAMP ON", 140, 6, True),
            ("2X", "LAMP OFF", 62, 2, False), ("2X", "LAMP ON", 62, 2, True))
    W = left + colw * len(COLS) + 8
    H = top + sum(r[2] + 10 for r in rows) + 96
    c = L.frame(W, H, "MIAO MEOW  TINY HATS",
                "BLACK CAT + ONE SMALL HAT + COIN-BELL LAMP (SOFT GOLD). EARS AND EYES STAY CLEAR.")
    ys, y = [], top
    for label, sub, h, k, on in rows:
        draw_text(c, label, (22, y + h // 2 - 14), Col.CYAN, 3 if len(label) < 4 else 2)
        draw_text(c, sub, (22, y + h // 2 + (12 if len(label) < 4 else 8)), Col.YELLOW if on and k < 12 else Col.TEXT_MUTED, 1)
        ys.append(y)
        y += h + 10
    for i, (title, hat) in enumerate(COLS):
        x = left + i * colw
        cw = colw - 6
        draw_text(c, title, (x + cw // 2, 62), Col.CYAN if hat is None else Col.YELLOW, 2, "midtop")
        for (label, sub, h, k, on), yy in zip(rows, ys):
            img = sprite(hat, on)
            if k == 12:                                             # head only, lamp lit so the coin shows too
                c.fill(L.FLOOR, (x, yy, cw, h))
                crop = img.subsurface(pygame.Rect(0, 0, 12, 12)).copy()
                big = L.up(crop, 12)
                c.blit(big, big.get_rect(center=(x + cw // 2, yy + h // 2)))
            else:
                L.place(c, img, (x, yy, cw, h), k, art.LAMPS[LAMP]["glow"] if on else None)
        if hat:
            hcfg = art.HATS[hat]
            for j, key in enumerate(("main", "shade", "light")):
                cx = x + cw // 2 - 36 + j * 26
                c.fill(Col.OUTLINE, (cx - 2, H - 82, 22, 18))
                c.fill(hcfg[key], (cx, H - 80, 18, 14))
            draw_text(c, hcfg["label"], (x + cw // 2, H - 60), Col.TEXT, 1, "midtop")
            draw_text(c, hcfg["note"], (x + cw // 2, H - 49), Col.TEXT_MUTED, 1, "midtop")
        else:
            draw_text(c, "REFERENCE", (x + cw // 2, H - 60), Col.TEXT, 1, "midtop")
            draw_text(c, "THE APPROVED BLACK CAT", (x + cw // 2, H - 49), Col.TEXT_MUTED, 1, "midtop")
    draw_text(c, "HATS SIT BETWEEN THE EAR TIPS AND STOP ABOVE THE EYES. THE COIN IS DULL BRONZE WHEN OFF, WARM GOLD WHEN ON.",
              (22, H - 32), Col.TEXT_MUTED, 1)
    draw_text(c, "THE SOFT LIGHT POOL IN THE LAMP-ON ROWS IS A PREVIEW LAYER, NOT PART OF THE SPRITE.", (22, H - 20), Col.TEXT_MUTED, 1)
    pygame.image.save(c, os.path.join(OUT, "01_hats_comparison.png"))
    print("wrote hats/01_hats_comparison.png", c.get_size())


def export_sprites():
    for _, hat in COLS:
        for on in (False, True):
            pygame.image.save(sprite(hat, on), os.path.join(SPRITES, f"miao_meow_{hat or 'nohat'}_lamp_{'on' if on else 'off'}_20x17.png"))


if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((1, 1))
    sheet()
    export_sprites()
