"""Pixel art for NEON CLAW: the plushies (big, for the game screen, and tiny, for the cabinet in the room), the claw
itself, and the room cabinet's sprite. Procedural and cached, like the rest of the hub's art."""
import math

import pygame

from font import get_font
from gfx import outlined, scale_color, shade
from settings import Col

PINK = (255, 110, 200)
HOT_PINK = (255, 70, 170)
PURPLE = (96, 44, 160)
PURPLE_DARK = (58, 24, 104)
CYAN = (90, 240, 255)
GOLD = (255, 214, 90)
GLASS = (18, 14, 50)
METAL = (200, 206, 230)
METAL_DARK = (120, 124, 160)

_cache = {}


# ------------------------------------------------------------------ plushies
def plush_sprite(spec):
    """The plushie at its own size (spec.width x spec.height), outlined. Cached per kind."""
    key = ("plush", spec.item_id)
    img = _cache.get(key)
    if img is None:
        img = outlined(_paint_plush(spec.width, spec.height, spec.look))
        _cache[key] = img
    return img


def _paint_plush(w, h, look):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    kind = look.get("kind", "cat")
    body, dark, accent, eye = look["body"], look["dark"], look["accent"], look["eye"]
    hi = shade(body, 0.35)
    if kind == "bunny":
        ear_h = h - 11
        for ex in (w // 2 - 4, w // 2 + 1):                        # two tall ears
            s.fill(body, (ex, 0, 3, ear_h + 2))
            s.fill(accent, (ex + 1, 1, 1, ear_h - 1))
        top = ear_h
    else:
        top = 3
        for x0, x1 in ((1, 5), (w - 6, w - 2)):                    # pointy ears
            pygame.draw.polygon(s, body, [(x0, top + 2), (x0 + 1, 0), (x1, top + 1)])
            s.fill(accent, ((x0 + x1) // 2, 2, 1, 1))
    head = pygame.Rect(0, top, w, h - top - 2)
    pygame.draw.ellipse(s, body, head)
    pygame.draw.ellipse(s, hi, head.inflate(-w // 2, -head.h // 2).move(-w // 6, -head.h // 5))
    s.fill(body, (1, h - 4, w - 2, 3))                                 # the sitting body / feet
    for fx in (3, w - 6):
        s.fill(dark, (fx, h - 2, 3, 2))
    if kind == "tabby":
        for dx in (-2, 0, 2):                                          # forehead stripes
            s.fill(dark, (w // 2 + dx, top + 1, 1, 2))
        s.fill(dark, (1, top + head.h // 2, 2, 1))
        s.fill(dark, (w - 3, top + head.h // 2, 2, 1))
    cy = top + head.h // 2
    gap = 3 if w < 20 else 4
    for ex in (w // 2 - gap - 1, w // 2 + gap):                        # eyes with a shine
        s.fill(eye, (ex, cy - 1, 2, 3))
        s.fill((255, 255, 255), (ex, cy - 1, 1, 1))
    s.fill(accent if kind != "chonk" else shade(accent, -0.1), (w // 2 - 1, cy + 2, 2, 1))      # little mouth
    for bx in (w // 2 - gap - 3, w // 2 + gap + 2):                    # blush
        if 0 <= bx < w - 1:
            s.fill((255, 150, 190), (bx, cy + 2, 2, 1))
    if kind == "chonk":
        s.fill(shade(body, 0.5), (w // 2 - 3, h - 5, 6, 2))            # a pale round tummy
    return s


def mini_plush(look):
    """A 5x5 plushie for the little cabinet in the room (just ears, a face colour and two eyes)."""
    key = ("mini", look["body"], look.get("kind"))
    img = _cache.get(key)
    if img is None:
        s = pygame.Surface((5, 5), pygame.SRCALPHA)
        body = look["body"]
        if look.get("kind") == "bunny":
            s.fill(body, (1, 0, 1, 2))
            s.fill(body, (3, 0, 1, 2))
        else:
            s.fill(body, (0, 0, 1, 1))
            s.fill(body, (4, 0, 1, 1))
        s.fill(body, (0, 1, 5, 4))
        s.fill(shade(body, -0.35), (0, 4, 5, 1))
        s.fill(look["eye"], (1, 2, 1, 1))
        s.fill(look["eye"], (3, 2, 1, 1))
        img = s
        _cache[key] = img
    return img


# ------------------------------------------------------------------ the claw
def draw_claw(surf, x, y, open_k, scale=1, color=METAL):
    """Three prongs hanging from a hub at (x, y-top). `open_k` 1 = wide open, 0 = shut. Returns the tips' y."""
    x, y = int(round(x)), int(round(y))
    dark = shade(color, -0.4)
    hub_w = 8 * scale
    surf.fill(dark, (x - hub_w // 2, y, hub_w, 3 * scale))
    surf.fill(color, (x - hub_w // 2, y, hub_w, 1 * scale))
    surf.fill(PINK, (x - 1 * scale, y + 1 * scale, 2 * scale, 1 * scale))       # a pink status light on the hub
    spread = (2 + 5 * open_k) * scale
    arm = 7 * scale
    base = y + 3 * scale
    for side in (-1, 1):
        mid = (x + side * (2 * scale + spread * 0.6), base + arm * 0.55)
        tip = (x + side * (1 * scale + spread * 0.35), base + arm)
        pygame.draw.line(surf, color, (x + side * 2 * scale, base), mid, max(1, scale + (scale > 1)))
        pygame.draw.line(surf, color, mid, tip, max(1, scale + (scale > 1)))
        surf.fill(dark, (int(tip[0]) - (side < 0) * scale, int(tip[1]), 2 * scale, 1 * scale))
    surf.fill(color, (x - scale // 2 - 0, base, max(1, scale), arm - 2 * scale))  # the middle prong (seen side on)
    return base + arm


# ------------------------------------------------------------------ the cabinet in the room
CABINET_SIZE = (44, 64)
GLASS_RECT = pygame.Rect(3, 13, 38, 28)            # inside of the glass, in the sprite
RAIL_Y = 15
PILE_Y = 39                                         # where the mini plushies' feet are
CHUTE_RECT = pygame.Rect(4, 31, 9, 10)              # the acrylic prize hole, front left inside the glass


def cabinet_sprite(cost):
    w, h = CABINET_SIZE
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    font = get_font()
    # marquee: a rounded plate with the name in lights and a heart each side
    pygame.draw.rect(s, PURPLE, (0, 0, w, 12), border_top_left_radius=4, border_top_right_radius=4)
    pygame.draw.rect(s, PURPLE_DARK, (2, 2, w - 4, 9), border_radius=2)
    pygame.draw.rect(s, PINK, (0, 0, w, 12), 1, border_top_left_radius=4, border_top_right_radius=4)
    word = font.render_glow("CLAW", GOLD, scale_color(HOT_PINK, 0.8))
    s.blit(word, ((w - word.get_width()) // 2, 2))
    for hx in (3, w - 7):
        s.fill(PINK, (hx, 4, 2, 2))
        s.fill(PINK, (hx + 2, 4, 2, 2))
        s.fill(PINK, (hx, 5, 4, 2))
        s.fill(PINK, (hx + 1, 7, 2, 1))
    s.fill(CYAN, (0, 12, w, 1))
    # the glass box: neon posts either side, a dark velvet back that gets a little lighter near the floor
    s.fill(HOT_PINK, (0, 13, 3, 29))
    s.fill(HOT_PINK, (w - 3, 13, 3, 29))
    s.fill(shade(HOT_PINK, 0.45), (1, 13, 1, 29))
    s.fill(shade(HOT_PINK, 0.45), (w - 2, 13, 1, 29))
    g = GLASS_RECT
    for y in range(g.top, g.bottom):
        k = (y - g.top) / g.h
        s.fill((int(18 + 22 * k), int(14 + 10 * k), int(50 + 34 * k)), (g.x, y, g.w, 1))
    s.fill(METAL_DARK, (g.x, RAIL_Y, g.w, 1))                     # the gantry rail
    s.fill(scale_color(CYAN, 0.55), (g.x, g.y, g.w, 1))
    s.fill((60, 40, 110), (g.x, PILE_Y, g.w, 2))                   # the floor of the box
    c = CHUTE_RECT                                                 # the prize hole: a see-through acrylic wall
    s.fill((8, 4, 20), (c.x, c.bottom - 2, c.w, 2))
    pygame.draw.rect(s, scale_color(PINK, 0.8), (c.x, c.y, c.w, c.h), 1)
    s.fill(shade(PINK, 0.4), (c.x, c.y, c.w, 1))
    # control panel: a sloped ledge with a joystick, a button and the price plate
    s.fill((130, 64, 196), (0, 42, w, 3))
    s.fill(CYAN, (0, 42, w, 1))
    s.fill(PURPLE, (0, 45, w, 6))
    s.fill(PURPLE_DARK, (0, 50, w, 1))
    s.fill((30, 20, 40), (9, 43, 2, 3))                            # joystick: a stick and a red ball
    pygame.draw.circle(s, (255, 80, 110), (10, 43), 2)
    s.fill((255, 200, 210), (9, 42, 1, 1))
    pygame.draw.circle(s, CYAN, (19, 47), 2)                       # the DROP button
    s.fill((220, 255, 255), (18, 46, 1, 1))
    plate = pygame.Rect(26, 44, 15, 8)
    s.fill((10, 6, 26), plate)
    pygame.draw.rect(s, GOLD, plate, 1)
    s.fill(GOLD, (plate.x + 2, plate.y + 3, 2, 2))                 # a token dot ...
    s.blit(font.render(str(cost), GOLD), (plate.x + 7, plate.y + 1))    # ... and the price
    # base: the cabinet body with a prize door and a paw print
    s.fill(PURPLE, (0, 51, w, h - 51))
    s.fill(PURPLE_DARK, (0, h - 2, w, 2))
    s.fill(scale_color(PINK, 0.7), (0, 51, w, 1))
    door = pygame.Rect(4, 53, 13, 8)
    s.fill((8, 4, 20), door)
    pygame.draw.rect(s, PINK, door, 1)
    s.fill(shade(PINK, 0.5), (door.x + 2, door.y + 2, door.w - 4, 1))   # the flap
    px, py = 30, 55                                                 # paw print
    s.fill(PINK, (px, py + 2, 4, 3))
    for dx in (-1, 1, 3, 5):
        s.fill(PINK, (px + dx, py if dx in (1, 3) else py + 1, 1, 1))
    s.fill(HOT_PINK, (0, 51, 1, h - 53))
    s.fill(HOT_PINK, (w - 1, 51, 1, h - 53))
    return s


def pile_layout():
    """Where the mini plushies sit in the room cabinet: a back row and a front row, all right of the chute."""
    back = [(15 + i * 6, PILE_Y - 7) for i in range(4)]
    front = [(15 + i * 6 + 3, PILE_Y - 4) for i in range(4)]
    return back + front


def glass_shine(surf, ox, oy, t):
    """A slow diagonal shine across the small cabinet's glass."""
    phase = (t % 6.0) / 1.4
    if phase < 1:
        gx = ox + GLASS_RECT.x + 1 + int(phase * (GLASS_RECT.w - 6))
        for i in range(GLASS_RECT.h // 2):
            surf.fill((210, 240, 255), (gx - i // 3, oy + GLASS_RECT.y + 1 + i * 2, 1, 1))


def sway(t):
    """The idle demo of the cabinet's claw: (x offset 0..1, dip 0..1, open 0..1) at time t."""
    cycle = t % 7.0
    x = 0.5 + 0.45 * math.sin(t * 0.7)
    dip = 0.0
    if 4.6 < cycle < 6.0:
        dip = math.sin((cycle - 4.6) / 1.4 * math.pi)
    open_k = 1.0 if dip < 0.8 else 0.4
    return x, dip, open_k
