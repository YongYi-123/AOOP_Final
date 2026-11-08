"""Outfit try-on comparison for Miao Meow (design only; the game and Mochi are untouched).

    python3 design_preview/build_outfits.py

Miao Meow = Mochi's own sprite pipeline, black fur, Mochi's gold eyes, soft-grey ears and nose, plus one outfit.
The sheet is composed 1:1: each 6X sprite is really 6 screen pixels per sprite pixel, the 1X row is the real size.
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

OUT = os.path.join(HERE, "outfits")
SPRITES = os.path.join(OUT, "sprites")
os.makedirs(SPRITES, exist_ok=True)
FLOOR = Col.FLOOR_ALT


def up(img, k):
    return pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))


def chip(c, rgb, x, y):
    c.fill(Col.OUTLINE, (x - 2, y - 2, 20, 16))
    c.fill(rgb, (x, y, 16, 12))


def columns():
    mochi = art._mochi.mochi_frame("sit")
    cols = [("MOCHI", "ORIGINAL (REFERENCE)", "", mochi, None),
            ("BLACK CAT", "NO CLOTHES", "GREY EARS + NOSE, GOLD EYES", art.miao_meow_sprite(0, "open", None), None)]
    for letter, key, short in (("A", "varsity", "VARSITY"), ("B", "neckerchief", "SCARF"),
                               ("C", "overalls", "OVERALLS"), ("D", "vest", "STAFF VEST")):
        o = art.OUTFITS[key]
        cols.append((f"{letter} {short}", o["label"], o["note"], art.miao_meow_sprite(0, "open", key), o))
    o = art.OUTFITS["neckerchief_lav"]
    cols.append(("B ALT", o["label"], o["note"], art.miao_meow_sprite(0, "open", "neckerchief_lav"), o))
    return cols


def final_sheet():
    cols = columns()
    colw, left = 196, 100
    top = 96                                       # header band with the column titles
    W = left + colw * len(cols) + 10
    H = top + 140 + 12 + 70 + 12 + 44 + 12 + 78 + 14
    c = pygame.Surface((W, H))
    c.fill((24, 18, 48))
    pygame.draw.rect(c, Col.CYAN, (3, 3, W - 6, H - 6), 2)
    draw_text(c, "MIAO MEOW  OUTFIT TRY-ON", (20, 14), Col.YELLOW, 3, glow=scale_color(Col.MAGENTA, 0.7))
    draw_text(c, "MOCHI'S SPRITE, BLACK FUR. ONE CLEAR SHAPE + 2-3 COLOURS PER OUTFIT.", (22, 42), Col.TEXT_MUTED, 2)

    rows = [("6X", top, 140, 6, "PREVIEW"), ("2X", top + 152, 70, 2, "IN-GAME"), ("1X", top + 234, 44, 1, "TRUE PIXELS")]
    for label, y, h, k, sub in rows:
        draw_text(c, label, (22, y + h // 2 - 12), Col.CYAN, 3)
        draw_text(c, sub, (22, y + h // 2 + 14), Col.TEXT_MUTED)

    for i, (title, full, note, img, o) in enumerate(cols):
        x = left + i * colw
        cw = colw - 6
        draw_text(c, title, (x + cw // 2, 66), Col.CYAN if i < 2 else Col.YELLOW, 2, "midtop")
        for label, y, h, k, sub in rows:
            c.fill(FLOOR, (x, y, cw, h))
            big = up(img, k)
            c.blit(soft_shadow(max(8, big.get_width() - 4 * k), 2 * k + 2, 120), (x + cw // 2 - (big.get_width() - 4 * k) // 2, y + h - 9 - k))
            c.blit(big, big.get_rect(midbottom=(x + cw // 2, y + h - 5)))
        ny = top + 292
        draw_text(c, full, (x + cw // 2, ny), Col.TEXT, 1, "midtop")
        if note:
            draw_text(c, note, (x + cw // 2, ny + 11), Col.TEXT_MUTED, 1, "midtop")
        if o:
            for j, key in enumerate(("main", "shade", "trim")):
                chip(c, o[key], x + cw // 2 - 28 + j * 22, ny + 26)
        else:
            for j, rgb in enumerate((art.LOOK.fur, art.FUR_HI, art.FUR_LO, art.SOFT_GREY, art.GOLD)):
                if i == 1:
                    chip(c, rgb, x + 20 + j * 30 if False else x + cw // 2 - 70 + j * 30 + 6, ny + 26)
    pygame.image.save(c, os.path.join(OUT, "01_outfit_comparison.png"))
    print("wrote outfits/01_outfit_comparison.png", c.get_size())


def faces():
    """Face close-up at 12x: Mochi vs the black cat, so the grey ears/nose and the fur layering can be checked."""
    mochi = art._mochi.mochi_frame("sit")
    plain = art.miao_meow_sprite(0, "open", None)
    c = pygame.Surface((760, 360))
    c.fill((24, 18, 48))
    pygame.draw.rect(c, Col.CYAN, (3, 3, 754, 354), 2)
    draw_text(c, "FACE CLOSE-UP (12X)", (20, 14), Col.YELLOW, 3, glow=scale_color(Col.MAGENTA, 0.7))
    for i, (label, img) in enumerate((("MOCHI", mochi), ("MIAO MEOW", plain))):
        x = 24 + i * 360
        c.fill(FLOOR, (x, 60, 340, 250))
        crop = img.subsurface(pygame.Rect(0, 0, 14, 14)).copy()
        big = up(crop, 12)
        c.blit(big, (x + 86, 66))
        draw_text(c, label, (x + 170, 318), Col.TEXT, 2, "midtop")
    pygame.image.save(c, os.path.join(OUT, "02_face_closeup.png"))
    print("wrote outfits/02_face_closeup.png", c.get_size())


def export_sprites():
    for key in ("varsity", "neckerchief", "neckerchief_lav", "overalls", "vest", None):
        for mood in ("open", "happy"):
            pygame.image.save(art.miao_meow_sprite(0, mood, key), os.path.join(SPRITES, f"miao_meow_{key or 'plain'}_{mood}_20x17.png"))


if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((1, 1))
    final_sheet()
    faces()
    export_sprites()
