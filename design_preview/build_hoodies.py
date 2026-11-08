"""Hoodie try-on previews for Miao Meow (design only; the game and Mochi are untouched).

    python3 design_preview/build_hoodies.py

Miao Meow is Mochi's own sprite pipeline (cat_sprites.draw_cat + Mochi's eye painter) with a black fur colour
and a hoodie painted over the body. Everything is drawn at native pixel size and scaled with nearest-neighbour.
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

OUT = os.path.join(HERE, "hoodies")
SPRITES = os.path.join(OUT, "sprites")
os.makedirs(SPRITES, exist_ok=True)
FLOOR = Col.FLOOR_ALT
NAMES = list(art.HOODIES)
LETTERS = "ABCD"


def up(img, k):
    return pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))


def save(canvas, name, scale):
    big = up(canvas, scale)
    pygame.image.save(big, os.path.join(OUT, name))
    print("wrote hoodies/" + name, big.get_size())


def base(w, h, title, sub):
    c = pygame.Surface((w, h))
    c.fill((24, 18, 48))
    pygame.draw.rect(c, Col.CYAN, (2, 2, w - 4, h - 4), 1)
    draw_text(c, title, (12, 9), Col.YELLOW, 2, glow=scale_color(Col.MAGENTA, 0.7))
    draw_text(c, sub, (12, 28), Col.TEXT_MUTED)
    return c


def chip(c, rgb, x, y):
    c.fill(Col.OUTLINE, (x - 1, y - 1, 12, 8))
    c.fill(rgb, (x, y, 10, 6))


def comparison():
    mochi = art._mochi.mochi_frame("sit")
    plain = art.miao_meow_sprite(0, "open", None)
    c = base(480, 300, "MIAO MEOW  HOODIE TRY-ON", "A BLACK CAT WITH MOCHI'S FACE, EYES AND PROPORTIONS. FOUR HOODIES TO PICK FROM.")

    # reference
    draw_text(c, "REFERENCE", (12, 42), Col.CYAN)
    for i, (label, img) in enumerate((("MOCHI (ORIGINAL)", mochi), ("MIAO MEOW, NO HOODIE", plain))):
        x = 12 + i * 112
        c.fill(FLOOR, (x, 52, 104, 66))
        c.blit(soft_shadow(60, 8, 120), (x + 22, 52 + 52))
        c.blit(up(img, 3), up(img, 3).get_rect(midbottom=(x + 52, 52 + 62)))
        draw_text(c, label, (x + 52, 121), Col.TEXT_MUTED, anchor="midtop")
    for i, line in enumerate(("SAME BODY, HEAD, EARS, EYES AS MOCHI.",
                              "ONLY THE FUR COLOUR CHANGES:",
                              "SOFT NAVY-BLACK + PALE MUZZLE.",
                              "EYES: MOCHI'S WARM GOLD.",
                              "NO GLOWING TAIL / HEADSET / NEON.")):
        draw_text(c, line, (240, 58 + i * 12), Col.TEXT if i != 3 else Col.YELLOW)

    # four hoodies
    for i, name in enumerate(NAMES):
        h = art.HOODIES[name]
        x = 12 + i * 116
        c.blit(__import__("ui").neon_panel(110, 126, Col.PURPLE, None, 240), (x, 138))
        c.fill(FLOOR, (x + 4, 142, 102, 70))
        img = art.miao_meow_sprite(0, "open", name)
        big = up(img, 4)
        c.blit(soft_shadow(64, 8, 120), (x + 23, 142 + 54))
        c.blit(big, big.get_rect(midbottom=(x + 55, 142 + 62)))
        draw_text(c, LETTERS[i], (x + 8, 146), Col.YELLOW, 2, glow=scale_color(Col.MAGENTA, 0.6))
        draw_text(c, h["label"], (x + 55, 216), Col.TEXT, anchor="midtop")
        for j, key in enumerate(("main", "shade", "light")):
            chip(c, h[key], x + 30 + j * 16, 228)
        detail = {"pocket": "POCKET + STRINGS", "heart": "HEART PATCH", "zip": "ZIP + POCKET LINE",
                  "stripe": "CREAM CHEST BAND"}[h["style"]]
        draw_text(c, detail, (x + 55, 240), Col.TEXT_MUTED, anchor="midtop")

    # true size
    draw_text(c, "TRUE GAME PIXELS (1X, THE GAME SHOWS THIS AT 2X)", (12, 270), Col.CYAN)
    c.fill(FLOOR, (12, 280, 440, 16))
    x = 18
    for img in [mochi] + [art.miao_meow_sprite(0, "open", n) for n in NAMES] + [art.miao_meow_sprite(1, "happy", n) for n in NAMES]:
        c.blit(img, (x, 280 + 15 - img.get_height()))
        x += 24
    save(c, "01_miao_meow_hoodie_comparison.png", 3)


def expressions():
    c = base(480, 372, "MIAO MEOW  HOODIE EXPRESSIONS", "SAME THREE EXPRESSIONS FOR EVERY HOODIE: HAPPY, SURPRISED, SLEEPY-GENTLE.")
    moods = (("happy", "HAPPY"), ("surprised", "SURPRISED"), ("sleepy", "GENTLE"))
    for i, name in enumerate(NAMES):
        x = 12 + i * 116
        draw_text(c, f"{LETTERS[i]} {art.HOODIES[name]['label'].split()[0]}", (x, 44), Col.YELLOW)
        for j, (mood, label) in enumerate(moods):
            y = 58 + j * 104
            c.fill((14, 10, 34), (x, y, 108, 100))
            c.blit(up(art.portrait_framed(mood, name), 2), (x + 10, y + 2))
            draw_text(c, label, (x + 54, y + 91), Col.TEXT_MUTED, anchor="midtop")
    save(c, "02_hoodie_expressions.png", 3)


def closeups():
    """One bigger poster per hoodie: idle, happy, gentle sprites on the floor colour + the portrait."""
    for i, name in enumerate(NAMES):
        h = art.HOODIES[name]
        c = base(340, 150, f"{LETTERS[i]}  {h['label']}", "MIAO MEOW")
        x = 12
        for mood, label in (("open", "IDLE"), ("happy", "HAPPY"), ("sleepy", "GENTLE")):
            c.fill(FLOOR, (x, 44, 70, 62))
            img = up(art.miao_meow_sprite(0, mood, name), 3)
            c.blit(soft_shadow(46, 7, 120), (x + 12, 44 + 46))
            c.blit(img, img.get_rect(midbottom=(x + 35, 44 + 56)))
            draw_text(c, label, (x + 35, 110), Col.TEXT_MUTED, anchor="midtop")
            x += 76
        c.blit(up(art.portrait_framed("happy", name), 2), (240, 40))
        draw_text(c, "PORTRAIT", (284, 132), Col.TEXT_MUTED, anchor="midtop")
        for j, key in enumerate(("main", "shade", "light")):
            chip(c, h[key], 14 + j * 16, 128)
        save(c, f"03_closeup_{LETTERS[i]}_{name}.png", 4)


def export_sprites():
    for name in NAMES:
        for mood in ("open", "happy", "sleepy", "surprised"):
            pygame.image.save(art.miao_meow_sprite(0, mood, name), os.path.join(SPRITES, f"miao_meow_{name}_{mood}_20x17.png"))
        pygame.image.save(art.portrait_framed("happy", name), os.path.join(SPRITES, f"miao_meow_{name}_portrait_44.png"))


if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((1, 1))
    comparison()
    expressions()
    closeups()
    export_sprites()
