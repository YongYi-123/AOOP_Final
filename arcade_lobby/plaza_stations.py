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

# Two drawings of the same machine, pixel for pixel the same design:
#   FULL     38 x 58, the original size. The pull screen (capsule_ui) shows it at 2x.
#   COMPACT  34 x 52 (about 0.9x each way, 80% of the area), the machine standing in Prize Plaza.
# Every coordinate the sprite, its animation and its footprint use lives in one of these tables, so the two
# sizes keep the same proportions instead of a blurry rescale of the pixel art.
FULL = dict(
    size=(38, 58), ear_x=(3, 25), ear_w=10, ear_h=8, crest_x=(6, 12, 18, 24), crest_w=7, cup_x=16,
    head=(6, 12), eyes=(10, 25), eye_y=9, nose=(18, 12), mouth_y=14, whisker_x=(3, 31), whisker_w=5, whisker_y=11,
    label_y=9, sparks=(4, 32), dome_body=(18, 25), dome=(4, 19, 30, 21), panel=(41, 12), knob=(10, 47, 5),
    plaque=(19, 43, 17, 8), tray=(53, 5), tray_slot=(8, 22), bulb_y=6, peek=(18, 56), pod_r=4,
    pods=((10, 35, 0), (18, 35, 1), (26, 35, 2), (14, 28, 3), (22, 28, 1), (18, 22, 2), (28, 27, 0)),
    footprint=(3, 48, 32, 10))
COMPACT = dict(
    size=(34, 52), ear_x=(3, 22), ear_w=9, ear_h=7, crest_x=(5, 11, 17, 23), crest_w=6, cup_x=14,
    head=(5, 11), eyes=(9, 22), eye_y=8, nose=(15, 11), mouth_y=13, whisker_x=(2, 28), whisker_w=4, whisker_y=10,
    label_y=7, sparks=(), dome_body=(15, 21), dome=(4, 16, 26, 18), panel=(35, 11), knob=(9, 41, 4),
    plaque=(17, 37, 15, 8), tray=(46, 6), tray_slot=(7, 20), bulb_y=5, peek=(17, 50), pod_r=4,
    pods=((9, 30, 0), (17, 30, 1), (25, 30, 2), (13, 24, 3), (21, 24, 1), (17, 19, 2)),
    footprint=(3, 43, 28, 9))
CAPSULE_SIZE = COMPACT["size"]          # the machine in the room
# where the capsules sit in the full-size dome (x, y of centres, bob phase); the pull screen draws these at 2x
_PODS = FULL["pods"]
DOME = pygame.Rect(FULL["dome"])


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


def _capsule_sprite(kind, g=FULL):
    """The machine drawn with the geometry table `g` (FULL for the pull screen, COMPACT for the room)."""
    look = _LOOK[kind]
    w, h = g["size"]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    body, dark, trim, accent = look["body"], look["dark"], look["trim"], look["accent"]
    font = get_font()
    head_y, head_h = g["head"]
    # head: cat ears, or a stepped retro crest with a trophy
    if kind == CAT:
        ew, eh = g["ear_w"], g["ear_h"]
        for x0 in g["ear_x"]:
            pygame.draw.polygon(s, body, [(x0, eh), (x0 + ew // 2, 0), (x0 + ew, eh)])
            pygame.draw.polygon(s, trim, [(x0 + 3, eh - 1), (x0 + ew // 2, 3), (x0 + ew - 3, eh - 1)])
    else:
        cw = g["crest_w"]
        for i, x0 in enumerate(g["crest_x"]):
            s.fill(dark if i % 3 == 0 else body, (x0, head_y - 1 - (1 if i in (1, 2) else 0) * 3, cw, 4))
        cx = g["cup_x"]
        s.fill(accent, (cx, 0, 6, 3))                                  # a little gold cup on the crest
        s.fill(accent, (cx + 2, 3, 2, 3))
        s.fill(accent, (cx - 2, 1, 2, 1))
        s.fill(accent, (cx + 6, 1, 2, 1))
    s.fill(body, (0, head_y, w, head_h + 1))                         # marquee head
    s.fill(dark, (1, head_y + 1, w - 2, head_h - 1))
    s.fill(trim, (0, head_y, w, 1))
    s.fill(trim, (0, head_y + head_h, w, 1))
    if kind == CAT:                                                  # a face: eyes, nose, mouth, whiskers
        ey = g["eye_y"]
        for ex in g["eyes"]:
            s.fill((255, 255, 255), (ex, ey, 3, 3))
            s.fill(Col.OUTLINE, (ex + 1, ey + 1, 2, 2))
        nx, ny = g["nose"]
        my = g["mouth_y"]
        s.fill(trim, (nx, ny, 3, 2))
        for mx in (nx - 1, nx + 1, nx + 3):
            s.fill(trim, (mx, my, 1, 1))
        for dy in (0, 2):
            for wx in g["whisker_x"]:
                s.fill(accent, (wx, g["whisker_y"] + dy, g["whisker_w"], 1))
    else:
        label = font.render("RETRO", accent)
        s.blit(label, ((w - label.get_width()) // 2, g["label_y"]))
        for sx in g["sparks"]:
            s.fill(trim, (sx, 11, 3, 1))
            s.fill(trim, (sx + 1, 10, 1, 3))
    # dome
    dy, dh = g["dome_body"]
    dome = pygame.Rect(g["dome"])
    s.fill(body, (0, dy, w, dh))
    s.fill(trim, (0, dy, 1, dh))
    s.fill(trim, (w - 1, dy, 1, dh))
    pygame.draw.rect(s, look["glass"], dome.inflate(2, 2), border_radius=6)
    pygame.draw.rect(s, shade(look["glass"], 0.35), dome.inflate(2, 2), 1, border_radius=6)
    # control panel: a big knob, the price plaque and a coin slot
    py, ph = g["panel"]
    s.fill(dark, (1, py, w - 2, ph + 1))
    s.fill(trim, (0, py, w, 1))
    kx, ky, kr = g["knob"]
    pygame.draw.circle(s, shade(trim, 0.15), (kx, ky), kr)
    pygame.draw.circle(s, scale_color(trim, 0.55), (kx, ky), kr, 1)
    s.fill(shade(trim, 0.7), (kx - 1, ky - kr + 1, 2, kr - 1))
    plaque = pygame.Rect(g["plaque"])
    s.fill((10, 6, 26), plaque)
    pygame.draw.rect(s, accent, plaque, 1)
    text = font.render(str(CAPSULE_MACHINES[kind].cost), accent)
    s.blit(text, (plaque.x + 2, plaque.y + 1))
    # tray
    ty, th = g["tray"]
    tx, tw = g["tray_slot"]
    s.fill(dark, (0, ty, w, th))
    s.fill((8, 4, 20), (tx, ty + 1, tw, th - 1))
    s.fill(trim, (tx, ty + 1, tw, 1))
    return s


class CapsuleStation(Station):
    """A capsule machine. E opens its pull screen for the player who pressed it.

    It stands in the room at the COMPACT size; the pull screen still shows the FULL drawing."""

    def __init__(self, pos, kind, geometry=COMPACT):
        x, y = pos
        look = _LOOK[kind]
        spec = CAPSULE_MACHINES[kind]
        self.capsule_kind = kind                    # (not `kind`: that names a Lucky Corner cabinet)
        self.look = look
        self.geometry = g = geometry
        fx, fy, fw, fh = g["footprint"]
        super().__init__(_capsule_sprite(kind, g), pos, (x + fx, y + fy, fw, fh), look["neon"], look["trim"], 0.26)
        self.prompt_label = spec.name

    def interact(self, scene):
        scene.open_capsule(self.capsule_kind)

    def draw(self, surf):
        super().draw(surf)
        ox, oy = self.rect.topleft
        look, t, g = self.look, self.time, self.geometry
        for i, (px, py, phase) in enumerate(g["pods"]):                # capsules shuffle gently in the dome
            top, bottom = look["pods"][i % len(look["pods"])]
            bob = int(round(math.sin(t * 2.4 + phase * 1.7) * 0.9))
            _pod(surf, (ox + px, oy + py + bob), top, bottom, self.capsule_kind)
        dome = pygame.Rect(g["dome"])
        surf.fill((235, 245, 255), (ox + dome.x + 2, oy + dome.y + 3, 1, dome.h * 2 // 7))     # glass shine
        surf.fill((235, 245, 255), (ox + dome.x + 2, oy + dome.y + dome.h // 2, 1, 1))
        for i in range(0, g["size"][0] - 4, 6):                          # marquee bulbs chasing
            if int(t * 3 + i / 6) % 3 == 0:
                surf.fill(look["accent"], (ox + 2 + i, oy + g["bulb_y"], 2, 1))
        if int(t * 1.5) % 6 == 0:                                        # a pod peeks out of the tray now and then
            px, py = g["peek"]
            _pod(surf, (ox + px, oy + py), *look["pods"][1], self.capsule_kind)


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

    `owners` is a callable giving [(label, profile)] for the player in the room; their
    picks are read from the profile every REFRESH seconds (and on refresh()), so the stand
    always shows what the profile has saved."""
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
        for _label, picks, profile in self._shown[:1]:
            for slot, bx in zip(SHOWCASE_SLOTS, SLOT_X):
                option = picks.get(slot)
                cx = ox + bx + BAY_W // 2
                base = oy + GLASS.bottom - 9
                if option is None:
                    q = get_font().render("?", (120, 90, 170))
                    surf.blit(q, (cx - q.get_width() // 2, base - 10))
                    continue
                icon = option_icon(option, 2, profile)
                bob = int(round(math.sin(self.time * 2.0 + bx) * 1.0))
                surf.blit(icon, icon.get_rect(midbottom=(cx, base + bob)))
                if option.count > 1:
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

