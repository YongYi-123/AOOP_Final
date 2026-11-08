"""Coin-bell lamp studies for Miao Meow (design only; the game and Mochi are untouched).

    python3 design_preview/build_lamp.py

Composed 1:1: the 6X sprites are really 6 screen pixels per sprite pixel; 2X matches the game's view.
The warm light pool behind the chest is a separate soft layer (preview only), not part of the sprite.
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

OUT = os.path.join(HERE, "lamp")
SPRITES = os.path.join(OUT, "sprites")
os.makedirs(SPRITES, exist_ok=True)
FLOOR = Col.FLOOR_ALT
MAIN_LAMP = os.environ.get("MIAO_LAMP", "gold")
OUTFITS = (("BLACK CAT", None), ("A VARSITY", "varsity"), ("B SCARF", "neckerchief"), ("C OVERALLS", "overalls"),
           ("D STAFF VEST", "vest"))


def up(img, k):
    return pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))


def sprite(outfit, lamp):
    return art.miao_meow_sprite(0, "open", outfit, "original", lamp)


def mochi():
    return art._mochi.mochi_frame("sit")


def soft_glow(radius, color, max_alpha):
    """A smooth warm falloff (no visible rings): alpha fades with the square of the distance."""
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for y in range(radius * 2):
        for x in range(radius * 2):
            d = ((x + 0.5 - radius) ** 2 + (y + 0.5 - radius) ** 2) ** 0.5 / radius
            if d < 1:
                s.set_at((x, y), (*color, int(max_alpha * (1 - d) ** 2)))
    return s


def place(c, img, cell, k, lit_color=None):
    """Draw one sprite on a floor cell with a shadow and, when lit, a faint warm light pool at the coin."""
    x, y, w, h = cell
    c.fill(FLOOR, cell)
    big = up(img, k)
    rect = big.get_rect(midbottom=(x + w // 2, y + h - 5))
    c.blit(soft_shadow(max(8, big.get_width() - 4 * k), 2 * k + 2, 120), (rect.centerx - (big.get_width() - 4 * k) // 2, y + h - 9 - k))
    if lit_color:
        cx, cy = rect.x + 5 * k, rect.y + 11 * k          # the coin
        glow = soft_glow(int(4.5 * k), lit_color, 54 if k > 2 else 70)
        clip = c.get_clip()
        c.set_clip(pygame.Rect(cell))
        c.blit(glow, glow.get_rect(center=(cx, cy)))
        c.set_clip(clip)
    c.blit(big, rect)
    return rect


def frame(w, h, title, sub):
    c = pygame.Surface((w, h))
    c.fill((24, 18, 48))
    pygame.draw.rect(c, Col.CYAN, (3, 3, w - 6, h - 6), 2)
    draw_text(c, title, (20, 14), Col.YELLOW, 3, glow=scale_color(Col.MAGENTA, 0.7))
    draw_text(c, sub, (22, 44), Col.TEXT_MUTED, 1)
    return c


def comparison(lamp_key):
    lamp = art.LAMPS[lamp_key]
    cols = [("MOCHI", None, True)] + [(t, o, False) for t, o in OUTFITS]
    left, colw = 112, 196
    top = 82
    rows = (("6X", "LAMP OFF", 140, 6, "off"), ("6X", "LAMP ON", 140, 6, "on"),
            ("2X", "LAMP OFF", 62, 2, "off"), ("2X", "LAMP ON", 62, 2, "on"))
    W = left + colw * len(cols) + 8
    H = top + sum(r[2] + 10 for r in rows) + 70
    c = frame(W, H, "MIAO MEOW  COIN-BELL LAMP", f"LAMP COLOUR: {lamp['label']}.  THE COIN IS DULL WHEN OFF AND LIGHTS WARM WHEN A PLAYER WALKS UP.")
    y = top
    ys = []
    for label, sub, h, k, state in rows:
        draw_text(c, label, (22, y + h // 2 - 14), Col.CYAN, 3)
        draw_text(c, sub, (22, y + h // 2 + 12), Col.YELLOW if state == "on" else Col.TEXT_MUTED, 1)
        ys.append(y)
        y += h + 10
    for i, (title, outfit, is_mochi) in enumerate(cols):
        x = left + i * colw
        cw = colw - 6
        draw_text(c, title, (x + cw // 2, 62), Col.CYAN if i < 2 else Col.YELLOW, 2, "midtop")
        for (label, sub, h, k, state), yy in zip(rows, ys):
            img = mochi() if is_mochi else sprite(outfit, "off" if state == "off" else lamp_key)
            place(c, img, (x, yy, cw, h), k, None if (is_mochi or state == "off") else lamp["glow"])
    draw_text(c, "MOCHI IS THE UNCHANGED REFERENCE (NO LAMP).  EYES, EARS, BODY, TAIL AND OUTFITS ARE THE APPROVED VERSION.",
              (22, H - 46), Col.TEXT_MUTED, 1)
    draw_text(c, "THE LIGHT WASH ONLY TOUCHES THE PIXELS NEXT TO THE COIN. NOTHING ELSE GLOWS.", (22, H - 32), Col.TEXT_MUTED, 1)
    pygame.image.save(c, os.path.join(OUT, "01_lamp_off_on_comparison.png"))
    print("wrote lamp/01_lamp_off_on_comparison.png", c.get_size())


def colour_study():
    keys = list(art.LAMPS)
    left = 252
    W = left + 5 * 112 + 5 * 54 + 22
    rowh = 118
    top = 82
    H = top + rowh * len(keys) + 54
    c = frame(W, H, "LAMP COLOUR STUDY", "LIT STATE ONLY, ON EVERY OUTFIT. OFF IS THE SAME DULL BRONZE COIN FOR ALL THREE.")
    draw_text(c, "COIN 16X", (22, 64), Col.CYAN, 1)
    for i, (t, o) in enumerate(OUTFITS):
        draw_text(c, t, (left + i * 112 + 52, 64), Col.CYAN, 1, "midtop")
        draw_text(c, t.split()[0], (left + 5 * 112 + i * 54 + 25, 64), Col.CYAN, 1, "midtop")
    for n, key in enumerate(keys):
        lamp = art.LAMPS[key]
        y = top + n * rowh
        c.fill(FLOOR, (14, y, 232, rowh - 8))
        draw_text(c, f"{n + 1} {lamp['label']}", (22, y + 8), Col.YELLOW, 2)
        for j, (name, cfg) in enumerate((("OFF", art.LAMP_OFF), ("ON", lamp))):
            bx = 26 + j * 100
            base = c.subsurface(pygame.Rect(bx, y + 34, 76, 56))
            base.fill((58, 62, 104))                        # the black cat's fur behind the coin
            pts = ((0, 0, "hl"), (1, 0, "main"), (0, 1, "main"), (1, 1, "edge"))
            for dx, dy, part in pts:
                c.fill(cfg[part], (bx + 12 + dx * 26, y + 38 + dy * 26, 26, 26))
            draw_text(c, name, (bx + 38, y + 94), Col.TEXT_MUTED, 1, "midtop")
        draw_text(c, "#%02X%02X%02X" % lamp["main"], (170, y + 12), Col.TEXT_MUTED, 1)
        for i, (t, o) in enumerate(OUTFITS):
            place(c, sprite(o, key), (left + i * 112, y, 106, rowh - 8), 4, lamp["glow"])
            place(c, sprite(o, key), (left + 5 * 112 + i * 54, y + 30, 48, 56), 2, lamp["glow"])
    draw_text(c, "ALL THREE STAY SMALL AND SOFT. BRIGHTER IS EASIER TO SPOT IN THE DARK, WARMER IS COSIER.", (22, H - 36), Col.TEXT_MUTED, 1)
    pygame.image.save(c, os.path.join(OUT, "02_lamp_colour_study.png"))
    print("wrote lamp/02_lamp_colour_study.png", c.get_size())


def export_sprites():
    for o in (None, "varsity", "neckerchief", "overalls", "vest"):
        for lamp in ("off", "cream", "gold", "apricot"):
            pygame.image.save(sprite(o, lamp), os.path.join(SPRITES, f"miao_meow_{o or 'plain'}_lamp_{lamp}_20x17.png"))


if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((1, 1))
    colour_study()
    comparison(MAIN_LAMP)
    export_sprites()
