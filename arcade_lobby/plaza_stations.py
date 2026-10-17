"""The centre of PRIZE PLAZA: the CAT CAPSULE and RETRO CAPSULE machines and the SHOWCASE stand.

Both are Stations (furniture the player walks up to and presses E on). Like the Lucky Corner
machines they are shared world furniture: the capsule machines show nothing about any profile
and the scene that opens decides who pulls; the showcase paints the picks of the people in the
room (one big row for one player, a row each for two) read live from their profiles.
"""
import math

import pygame

from car_preview import car_image
from capsule import CAPSULE_MACHINES, CAT, RETRO
from font import get_font
from gfx import neon_rect_glow, outlined, scale_color, shade
from item_icons import item_icon
from item_registry import ITEM_REGISTRY
from settings import Col
from showcase import CAR, COLLECTIBLE_SLOT, SHOWCASE_SLOTS, TROPHY, ShowcaseService
from stations import Station

CAPSULE_SIZE = (38, 58)
SHOWCASE_SIZE = (112, 72)

# per machine: body, body shade, trim, glow/neon, accent, dome glass, capsule colours (top, bottom)
_LOOK = {
    CAT: dict(body=(112, 56, 168), dark=(70, 34, 112), trim=(255, 120, 200), neon=(255, 110, 210),
              accent=(255, 214, 240), glass=(52, 26, 84),
              pods=(((255, 170, 215), (255, 100, 175)), ((215, 175, 255), (150, 100, 235)),
                    ((255, 245, 250), (255, 150, 200)), ((255, 205, 230), (190, 130, 250)))),
    RETRO: dict(body=(26, 70, 150), dark=(14, 40, 100), trim=(90, 240, 255), neon=(80, 220, 255),
                accent=(255, 214, 90), glass=(10, 32, 70),
                pods=(((140, 245, 255), (30, 150, 230)), ((255, 232, 130), (230, 160, 30)),
                      ((255, 255, 255), (70, 130, 230)), ((200, 235, 255), (255, 190, 60)))),
}
# where the capsules sit in the dome (x, y of centres), and which bob
_PODS = ((10, 35, 0), (18, 35, 1), (26, 35, 2), (14, 28, 3), (22, 28, 1), (18, 22, 2), (28, 27, 0))
DOME = pygame.Rect(4, 19, 30, 21)


def _pod(surf, center, top, bottom, kind=None):
    """One two-tone capsule (a ball cut in half) 4px in radius; retro ones carry a tiny star."""
    x, y = center
    pygame.draw.circle(surf, shade(bottom, -0.55), (x, y), 5)       # a dark rim keeps neighbours apart
    pygame.draw.circle(surf, bottom, (x, y), 4)
    pygame.draw.circle(surf, top, (x, y), 4, draw_top_left=True, draw_top_right=True)
    surf.fill(shade(bottom, -0.35), (x - 4, y, 9, 1))
    surf.fill(shade(top, 0.7), (x - 2, y - 3, 2, 1))
    if kind == RETRO:
        surf.fill((255, 255, 255), (x, y - 2, 1, 1))
    elif kind == CAT:
        surf.fill(shade(top, 0.6), (x - 3, y - 4, 1, 1))        # a tiny ear on the lid
        surf.fill(shade(top, 0.6), (x + 3, y - 4, 1, 1))


def _capsule_sprite(kind):
    look = _LOOK[kind]
    w, h = CAPSULE_SIZE
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    body, dark, trim, accent = look["body"], look["dark"], look["trim"], look["accent"]
    font = get_font()
    # head: cat ears, or a stepped retro crest with a trophy
    if kind == CAT:
        for x0 in (3, 25):
            pygame.draw.polygon(s, body, [(x0, 8), (x0 + 5, 0), (x0 + 10, 8)])
            pygame.draw.polygon(s, trim, [(x0 + 3, 7), (x0 + 5, 3), (x0 + 7, 7)])
    else:
        for i, x0 in enumerate((6, 12, 18, 24)):
            s.fill(dark if i % 3 == 0 else body, (x0, 5 - (1 if i in (1, 2) else 0) * 3, 7, 4))
        s.fill(look["accent"], (16, 0, 6, 3))                       # a little gold cup on the crest
        s.fill(look["accent"], (18, 3, 2, 3))
        s.fill(look["accent"], (14, 1, 2, 1))
        s.fill(look["accent"], (22, 1, 2, 1))
    s.fill(body, (0, 6, w, 12))                                      # marquee head
    s.fill(dark, (1, 7, w - 2, 10))
    s.fill(trim, (0, 6, w, 1))
    s.fill(trim, (0, 17, w, 1))
    if kind == CAT:                                                  # a face: eyes, nose, mouth, whiskers
        for ex in (10, 25):
            s.fill((255, 255, 255), (ex, 9, 3, 3))
            s.fill(Col.OUTLINE, (ex + 1, 10, 2, 2))
        s.fill(trim, (18, 12, 3, 2))
        s.fill(trim, (17, 14, 1, 1))
        s.fill(trim, (21, 14, 1, 1))
        s.fill(trim, (19, 14, 1, 1))
        for dy in (0, 2):
            s.fill(accent, (3, 11 + dy, 5, 1))
            s.fill(accent, (31, 11 + dy, 5, 1))
    else:
        label = font.render("RETRO", look["accent"])
        s.blit(label, ((w - label.get_width()) // 2, 9))
        for sx in (4, 32):
            s.fill(trim, (sx, 11, 3, 1))
            s.fill(trim, (sx + 1, 10, 1, 3))
    # dome
    s.fill(body, (0, 18, w, 25))
    s.fill(trim, (0, 18, 1, 25))
    s.fill(trim, (w - 1, 18, 1, 25))
    pygame.draw.rect(s, look["glass"], DOME.inflate(2, 2), border_radius=6)
    pygame.draw.rect(s, shade(look["glass"], 0.35), DOME.inflate(2, 2), 1, border_radius=6)
    # control panel: a big knob, the price plaque and a coin slot
    s.fill(dark, (1, 41, w - 2, 12))
    s.fill(trim, (0, 41, w, 1))
    pygame.draw.circle(s, shade(trim, 0.15), (10, 47), 5)
    pygame.draw.circle(s, scale_color(trim, 0.55), (10, 47), 5, 1)
    s.fill(shade(trim, 0.7), (9, 43, 2, 4))
    plaque = pygame.Rect(19, 43, 17, 8)
    s.fill((10, 6, 26), plaque)
    pygame.draw.rect(s, accent, plaque, 1)
    price = str(CAPSULE_MACHINES[kind].cost)
    text = font.render(price, accent)
    s.blit(text, (plaque.x + 2, plaque.y + 1))
    # tray
    s.fill(dark, (0, 53, w, 5))
    s.fill((8, 4, 20), (8, 54, 22, 4))
    s.fill(trim, (8, 54, 22, 1))
    return s


class CapsuleStation(Station):
    """A capsule machine. E opens its pull screen for the player who pressed it."""

    def __init__(self, pos, kind):
        x, y = pos
        look = _LOOK[kind]
        spec = CAPSULE_MACHINES[kind]
        self.capsule_kind = kind                    # (not `kind`: that names a Lucky Corner cabinet)
        self.look = look
        super().__init__(_capsule_sprite(kind), pos, (x + 3, y + 48, 32, 10), look["neon"], look["trim"], 0.26)
        self.prompt_label = spec.name

    def interact(self, scene):
        scene.open_capsule(self.capsule_kind)

    def draw(self, surf):
        super().draw(surf)
        ox, oy = self.rect.topleft
        look, t = self.look, self.time
        for i, (px, py, phase) in enumerate(_PODS):                    # capsules shuffle gently in the dome
            top, bottom = look["pods"][i % len(look["pods"])]
            bob = int(round(math.sin(t * 2.4 + phase * 1.7) * 0.9))
            _pod(surf, (ox + px, oy + py + bob), top, bottom, self.capsule_kind)
        surf.fill((235, 245, 255), (ox + DOME.x + 2, oy + DOME.y + 3, 1, 6))     # glass shine
        surf.fill((235, 245, 255), (ox + DOME.x + 2, oy + DOME.y + 11, 1, 1))
        for i in range(0, CAPSULE_SIZE[0] - 4, 6):                       # marquee bulbs chasing
            if int(t * 3 + i / 6) % 3 == 0:
                surf.fill(look["accent"], (ox + 2 + i, oy + 6, 2, 1))
        if int(t * 1.5) % 6 == 0:                                        # a pod peeks out of the tray now and then
            _pod(surf, (ox + 18, oy + 56), *look["pods"][1], self.capsule_kind)


# ------------------------------------------------------------------ showcase
def car_sprite(color, scale=1):
    """A little pixel sports car seen from the side, painted `color` (cached per colour/scale)."""
    key = (tuple(color), scale)
    img = _car_cache.get(key)
    if img is None:
        s = pygame.Surface((16, 9), pygame.SRCALPHA)
        dark = shade(color, -0.4)
        s.fill(color, (1, 4, 14, 3))
        pygame.draw.polygon(s, color, [(3, 4), (5, 1), (11, 1), (13, 4)])
        pygame.draw.polygon(s, (170, 230, 255), [(5, 4), (6, 2), (8, 2), (8, 4)])
        pygame.draw.polygon(s, (130, 200, 245), [(9, 4), (9, 2), (11, 2), (12, 4)])
        s.fill(shade(color, 0.5), (2, 4, 12, 1))
        s.fill(dark, (1, 6, 14, 1))
        s.fill((255, 244, 160), (14, 4, 2, 1))
        s.fill((255, 80, 90), (0, 4, 1, 1))
        for wx in (3, 11):
            pygame.draw.circle(s, (20, 14, 30), (wx + 1, 7), 2)
            s.fill((190, 200, 220), (wx + 1, 7, 1, 1))
        img = outlined(s)
        if scale != 1:
            img = pygame.transform.scale_by(img, scale)
        _car_cache[key] = img
    return img


_car_cache = {}


def option_icon(option, scale=1, profile=None):
    """The picture of one ShowcaseOption (a car, or the item's own icon). With the owning
    `profile` a car is the real Retro Racer car in that profile's selected paint."""
    if option.shape == "car":
        if profile is not None:
            image = car_image(profile, option.value, CAR_WIDTHS.get(scale, 30))
            if image is not None:
                return image
        return car_sprite(option.color, scale)
    definition = ITEM_REGISTRY.get(option.value)
    return item_icon(definition, scale)


CAR_WIDTHS = {1: 22, 2: 30}     # px wide per display scale (the racer's own rear-view sprite is 30 px)
SLOT_X = (3, 38, 73)             # left edge of each of the three display bays, 36px wide
BAY_W = 36
GLASS = pygame.Rect(3, 14, SHOWCASE_SIZE[0] - 6, 46)
BAY_LABELS = {CAR: "CAR", COLLECTIBLE_SLOT: "ITEM", TROPHY: "CUP"}


def _showcase_sprite():
    w, h = SHOWCASE_SIZE
    gold, plum = (255, 200, 80), (46, 20, 78)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill(plum, (0, 0, w, h))
    s.fill(gold, (0, 0, w, 1))
    # marquee
    s.fill((26, 10, 52), (1, 1, w - 2, 12))
    label = get_font().render_glow("SHOWCASE", (255, 238, 170), (190, 110, 30))
    s.blit(label, ((w - label.get_width()) // 2, 4))
    for sx in (5, w - 9):
        pygame.draw.polygon(s, gold, [(sx + 2, 2), (sx + 3, 5), (sx + 5, 6), (sx + 3, 7), (sx + 2, 10), (sx + 1, 7), (sx - 1, 6), (sx + 1, 5)])
    s.fill(gold, (0, 13, w, 1))
    s.fill(scale_color(gold, 0.5), (0, 1, w, 1))
    # glass cabinet: a dark velvet back with a soft spotlight per bay
    for y in range(GLASS.top, GLASS.bottom):
        k = (y - GLASS.top) / GLASS.h
        s.fill((int(22 + 30 * k), int(10 + 8 * k), int(48 + 30 * k)), (GLASS.x, y, GLASS.w, 1))
    for i, bx in enumerate(SLOT_X):
        cone = pygame.Surface((BAY_W, GLASS.h), pygame.SRCALPHA)
        for y in range(GLASS.h):
            half = 4 + int(11 * y / GLASS.h)
            cone.fill((255, 235, 190, int(46 * (1 - y / GLASS.h) ** 0.8)), (BAY_W // 2 - half, y, half * 2, 1))
        s.blit(cone, (bx, GLASS.y))
        if i:
            s.fill(scale_color(gold, 0.45), (bx - 1, GLASS.y, 1, GLASS.h))
        s.fill(scale_color(gold, 0.7), (bx + 3, GLASS.bottom - 8, BAY_W - 6, 2))       # pedestal
        s.fill((120, 40, 110), (bx + 3, GLASS.bottom - 6, BAY_W - 6, 6))
    pygame.draw.rect(s, gold, (0, 13, w, 48), 1)
    # plinth with the bay names engraved on it
    s.fill((30, 12, 54), (0, 61, w, 11))
    s.fill(gold, (0, 61, w, 1))
    s.fill(scale_color(gold, 0.6), (0, h - 1, w, 1))
    font = get_font()
    for slot, bx in zip(SHOWCASE_SLOTS, SLOT_X):
        text = font.render(BAY_LABELS[slot], scale_color(gold, 0.9))
        s.blit(text, (bx + (BAY_W - text.get_width()) // 2, 64))
    return s


class ShowcaseStation(Station):
    """The SHOWCASE: a lit display stand. E lets the player choose what stands on it.

    `owners` is a callable giving [(label, profile), ...] for the people in the room; their
    picks are read from the profiles every REFRESH seconds (and on refresh()), so the stand
    always shows what each profile has saved."""
    prompt_label = "SHOWCASE"
    REFRESH = 0.2

    def __init__(self, pos, owners=None):
        x, y = pos
        super().__init__(_showcase_sprite(), pos, (x + 2, y + 60, SHOWCASE_SIZE[0] - 4, 12),
                         (255, 190, 90), (255, 110, 190), 0.5)
        self.sign_rect = pygame.Rect(self.rect)         # nor the showcase and the item standing in it
        self.owners = owners or (lambda: [])
        self._shown = []
        self._since = self.REFRESH
        self.refresh()

    def interact(self, scene):
        scene.open_showcase()

    def refresh(self):
        """Re-read what each person has on display."""
        self._shown = [(label, ShowcaseService(profile).all_displayed(), profile) for label, profile in self.owners()]
        self._since = 0.0

    def update(self, dt):
        super().update(dt)
        self._since += dt
        if self._since >= self.REFRESH:
            self.refresh()

    def draw(self, surf):
        super().draw(surf)
        ox, oy = self.rect.topleft
        two = len(self._shown) > 1
        row_h = GLASS.h // max(1, len(self._shown)) if self._shown else GLASS.h
        for r, (label, picks, profile) in enumerate(self._shown):
            top = oy + GLASS.y + r * row_h
            if two:
                tag = get_font().render(label, (255, 214, 240))
                surf.blit(tag, (ox + 4, top + 1))
            for slot, bx in zip(SHOWCASE_SLOTS, SLOT_X):
                option = picks.get(slot)
                cx = ox + bx + BAY_W // 2
                if two:
                    base = top + row_h - 2
                else:
                    base = oy + GLASS.bottom - 9
                if option is None:
                    q = get_font().render("?", (120, 90, 170))
                    surf.blit(q, (cx - q.get_width() // 2, base - 10))
                    continue
                icon = option_icon(option, 1 if two else 2, profile)
                bob = int(round(math.sin(self.time * 2.0 + bx) * 1.0)) if not two else 0
                surf.blit(icon, icon.get_rect(midbottom=(cx, base + bob)))
                if option.count > 1 and not two:
                    n = get_font().render(f"X{option.count}", (255, 238, 170))
                    surf.blit(n, (cx + 6, oy + GLASS.y + 2))
        # a slow glass shine and sparkles over the cabinet
        phase = (self.time % 5.0) / 1.6
        if phase < 1:
            gx = ox + GLASS.x + 2 + int(phase * (GLASS.w - 8))
            for i in range(GLASS.h // 2):
                surf.fill((200, 235, 255), (gx - i // 4, oy + GLASS.y + 1 + i * 2, 1, 1))
        for k, (sx, sy) in enumerate(((14, 20), (54, 24), (96, 19), (32, 44), (80, 42))):
            if int(self.time * 2 + k * 1.3) % 4 == 0:
                x, y = ox + sx, oy + sy
                surf.fill((255, 244, 200), (x, y - 1, 1, 3))
                surf.fill((255, 244, 200), (x - 1, y, 3, 1))
