"""Neon arcade cabinets. Every visual variant (marquee frames, attract-mode
screen frames, glow pulse levels, flash overlay) is pre-rendered once, then
played back through animations - nothing is generated per frame."""
import math

import pygame

from animation import Animation, AnimationController, AnimatedSprite
from font import get_font
from gfx import (flash_overlay, lerp_color, neon_rect_glow, outlined,
                 radial_glow, scale_color, shade)
import machine_themes as themes
from item_registry import FREE_PLAY_COUPON
from rewards import PlaySession
from room import Prop
from settings import Col, DEFAULT_PLAY_COST, FLOOR_TOP, INTERACT_FLASH

W, H = 36, 62
SCREEN = pygame.Rect(6, 15, 24, 16)          # relative to the cabinet
MARQUEE = pygame.Rect(2, 1, W - 4, 10)
FOOTPRINT_H = 28     # how deep a cabinet's collision box is (it stands against a wall or on the floor)
GLOW_SPREAD = 9
PULSE_LEVELS = (0.55, 0.7, 0.85, 1.0)
SOFT_GLOW = 0.6         # halo scale when a room asks for soft_glow

# Per-style animation timing, so every machine feels a little different.
STYLES = {
    #          screen frames, screen fps, marquee frame time, pulse frame time
    "racer": dict(frames=24, fps=12, marquee=0.07, pulse=0.14),
    "space": dict(frames=24, fps=12, marquee=0.28, pulse=0.22),
    "puzzle": dict(frames=32, fps=10, marquee=0.18, pulse=0.18),
    "cat": dict(frames=32, fps=8, marquee=0.4, pulse=0.2),
    "volley": dict(frames=32, fps=12, marquee=0.07, pulse=0.12),
}


# --------------------------------------------------------------------- screens
def _screen_racer(s, p, accent, neon):
    t = p * 2.0
    s.fill((22, 12, 44))
    road = pygame.Rect(6, 0, 12, 16)
    s.fill((44, 36, 76), road)
    s.fill(accent, (road.x, 0, 1, 16))
    s.fill(accent, (road.right - 1, 0, 1, 16))
    off = int(t * 24) % 6
    for y in range(-6, 16, 6):
        s.fill(Col.YELLOW, (road.centerx, y + off, 1, 3))
    off = int(t * 24) % 8
    for y in range(-8, 16, 8):
        s.fill(Col.MAGENTA, (1, y + off, 2, 2))
        s.fill(Col.CYAN, (21, y + off + 4, 2, 2))
    cx = road.centerx - 2 + int(math.sin(p * math.tau) * 3)
    s.fill(neon, (cx, 9, 4, 5))
    s.fill((180, 240, 255), (cx + 1, 10, 2, 1))
    s.fill(Col.YELLOW, (cx, 8, 1, 1))
    s.fill(Col.YELLOW, (cx + 3, 8, 1, 1))


_STARS = ((3, 2, 8), (11, 9, 16), (19, 5, 24), (7, 13, 8), (15, 0, 16), (22, 11, 8),
          (1, 7, 24), (13, 4, 8), (18, 14, 16))


def _screen_space(s, p, accent, neon):
    t = p * 2.0
    s.fill((10, 12, 40))
    for sx, sy, speed in _STARS:
        s.fill((210, 220, 255), (sx, int(sy + t * speed) % 16, 1, 1))
    ex = 8 + int(math.sin(p * math.tau) * 6)
    color = Col.GREEN if int(p * 6) % 2 else Col.MAGENTA
    s.fill(color, (ex, 2, 6, 3))
    s.fill(color, (ex + 1, 5, 1, 1))
    s.fill(color, (ex + 4, 5, 1, 1))
    sx = 12 + int(math.sin(p * math.tau + 0.8) * 6)
    pygame.draw.polygon(s, accent, [(sx, 11), (sx - 3, 15), (sx + 3, 15)])
    s.fill(Col.YELLOW, (sx, 10 - int(t * 32) % 16, 1, 2))


_CANDY = (Col.MAGENTA, Col.YELLOW, Col.CYAN, Col.GREEN)


def _screen_puzzle(s, p, accent, neon):
    s.fill((30, 14, 50))
    for x in range(0, 24, 3):
        s.fill((40, 22, 66), (x, 0, 1, 16))
    stack = ("0212301", "3102102", "2130231")
    for row, pattern in enumerate(stack):
        y = 16 - 3 * (row + 1)
        flash = row == 0 and p > 0.8 and int(p * 20) % 2 == 0
        for col, ch in enumerate(pattern):
            c = (255, 255, 255) if flash else _CANDY[int(ch)]
            s.fill(c, (1 + col * 3, y, 3, 3))
            s.fill(shade(c, -0.35), (1 + col * 3, y + 2, 3, 1))
    fall = min(1.0, p / 0.8)
    y = int(fall * 4)
    s.fill(accent, (10, y, 3, 3))
    s.fill(accent, (13, y, 3, 3))
    s.fill(shade(accent, -0.35), (10, y + 2, 6, 1))


_SCREEN_PAINTERS = {"racer": _screen_racer, "space": _screen_space, "puzzle": _screen_puzzle,
                    **themes.SCREEN_PAINTERS}


def _build_screen_frames(style, accent, neon):
    info = STYLES[style]
    n = info["frames"]
    scan = pygame.Surface(SCREEN.size, pygame.SRCALPHA)
    for y in range(0, SCREEN.h, 2):
        scan.fill((0, 0, 0, 55), (0, y, SCREEN.w, 1))
    frames = []
    for i in range(n):
        p = i / n
        s = pygame.Surface(SCREEN.size)
        _SCREEN_PAINTERS[style](s, p, accent, neon)
        s.blit(scan, (0, 0))
        # rolling scanline bar
        bar_y = int(p * 2 * SCREEN.h) % SCREEN.h
        s.fill((40, 40, 60), (0, bar_y, SCREEN.w, 1), special_flags=pygame.BLEND_RGB_ADD)
        if i == n - 3:  # a single-frame CRT flicker
            s.fill((30, 30, 40), special_flags=pygame.BLEND_RGB_ADD)
        frames.append(s)
    return frames


# --------------------------------------------------------------------- cabinet
def _paint_marquee(s, style, label, frame, neon, accent):
    r = MARQUEE
    if style in themes.MARQUEES:
        themes.MARQUEES[style](s, r, label, frame, neon, accent)
        return
    s.fill((12, 8, 26), r)
    font = get_font()
    tw, th = font.size(label)
    tx, ty = r.centerx - tw // 2, r.y + 1
    if style == "racer":            # chase lights under flashing text
        color = accent if frame % 2 == 0 else Col.YELLOW
        s.blit(font.render(label, color), (tx, ty))
        for i in range(8):
            lit = (i + frame) % 4 == 0
            s.fill(Col.YELLOW if lit else scale_color(neon, 0.35), (r.x + 1 + i * 4, r.bottom - 1, 2, 1))
    elif style == "space":          # slow brightness pulse
        k = (1.0, 0.8, 0.6, 0.8)[frame]
        s.fill(scale_color(neon, 0.35 * k), r.inflate(-2, -2))
        s.blit(font.render(label, lerp_color(neon, accent, k)), (tx, ty))
    else:                           # rainbow letters cycling
        x = tx
        for i, ch in enumerate(label):
            glyph = font.render(ch, _CANDY[(i + frame) % 4])
            s.blit(glyph, (x, ty))
            x += glyph.get_width() + 1


def _build_cabinet(style, label, frame, neon, accent, frames=4):
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    body, side = themes.BODY_COLORS.get(style, (Col.CABINET, Col.CABINET_SIDE))
    s.fill(side, (0, 12, W, H - 12))
    s.fill(body, (3, 12, W - 6, H - 12))
    s.fill(neon, (0, 12, 1, H - 12))                 # neon edge strips
    s.fill(neon, (W - 1, 12, 1, H - 12))
    s.fill(scale_color(neon, 0.45), (1, 12, 1, H - 12))
    s.fill(scale_color(neon, 0.45), (W - 2, 12, 1, H - 12))

    s.fill(body, (0, 0, W, 12))                      # marquee housing
    _paint_marquee(s, style, label, frame, neon, accent)
    s.fill(neon, (0, 0, W, 1))

    s.fill((6, 4, 14), (4, 13, 28, 20))              # screen bezel
    pygame.draw.rect(s, scale_color(accent, 0.55), (4, 13, 28, 20), 1)

    s.fill((46, 34, 80), (2, 34, W - 4, 7))           # control panel
    s.fill(accent, (2, 40, W - 4, 1))
    s.fill((80, 70, 110), (9, 33, 1, 4))
    pygame.draw.circle(s, neon, (9, 33), 2)
    for i, c in enumerate((Col.YELLOW, Col.CYAN, Col.MAGENTA)):
        pygame.draw.circle(s, c, (18 + i * 5, 37), 1)

    s.fill((18, 12, 34), (5, 43, 26, 14))            # token door
    s.fill((6, 4, 14), (15, 46, 6, 7))
    s.fill(accent, (17, 48, 2, 3))
    s.fill(neon, (0, H - 3, W, 1))                    # kick plate strip
    s.fill((10, 6, 20), (0, H - 2, W, 2))
    if style in themes.BODY_DECORATORS:
        themes.BODY_DECORATORS[style](s, frame, frames, neon, accent)
    return s


_CACHE = {}


def _machine_art(data):
    """Everything a machine draws, built once per machine id."""
    art = _CACHE.get(data["id"])
    if art is None:
        neon, accent, style = data["neon"], data["accent"], data["screen"]
        frames = themes.marquee_frames(style, data["marquee"])
        bases = [_build_cabinet(style, data["marquee"], f, neon, accent, frames) for f in range(frames)]
        pad = 0
        if style in themes.HEADROOM:          # e.g. cat ears standing above the marquee
            pad, painter = themes.HEADROOM[style]
            tall = []
            for f, base in enumerate(bases):
                s = pygame.Surface((W, H + pad), pygame.SRCALPHA)
                painter(s, pad, f, neon, accent)
                s.blit(base, (0, pad))
                tall.append(s)
            bases = tall
        halo = neon_rect_glow(W, H, neon, GLOW_SPREAD, 0.55)
        reflection = radial_glow(W // 2 + 14, scale_color(neon, 0.5), bands=5, squash=0.45)
        art = {
            "pad": pad,
            "marquee_frames": frames,
            "cabinet": [outlined(b) for b in bases],
            "cabinet_hi": [outlined(b, shade(accent, 0.5)) for b in bases],
            "flash": flash_overlay(outlined(bases[0])),
            "screen": _build_screen_frames(style, accent, neon),
            "halo": [_scaled_copy(halo, k) for k in PULSE_LEVELS],
            "reflection": [_scaled_copy(reflection, k) for k in PULSE_LEVELS],
            # dimmer set for the lofi room: same pulse, gentler light
            "halo_soft": [_scaled_copy(halo, k * SOFT_GLOW) for k in PULSE_LEVELS],
            "reflection_soft": [_scaled_copy(reflection, k * SOFT_GLOW) for k in PULSE_LEVELS],
        }
        _CACHE[data["id"]] = art
    return art


def _scaled_copy(surf, k):
    out = surf.copy()
    level = int(255 * k)
    out.fill((level, level, level), special_flags=pygame.BLEND_RGB_MULT)
    return out


def cabinet_footprint(rect):
    """Collision box of a cabinet whose sprite is `rect`: its lower part, but
    never above the back wall's foot."""
    top = max(FLOOR_TOP, rect.bottom - FOOTPRINT_H)
    return pygame.Rect(rect.x, top, rect.w, rect.bottom - top)


# --------------------------------------------------------------------- machine
class ArcadeMachine(AnimatedSprite):
    TOP_Y = 30
    prompt_label = "PLAY"

    def __init__(self, data):
        self.id = data["id"]
        self.game_id = data.get("game_id", self.id)   # which minigame (and high score) it runs
        self.name = data["name"]
        self.description = data["description"]
        self.neon = data["neon"]
        self.accent = data["accent"]
        self.style = data["screen"]
        self.play_cost = data.get("play_cost", DEFAULT_PLAY_COST)
        self.art = art = _machine_art(data)
        info = STYLES[self.style]

        # Main animation = attract-mode screen; two extra channels for the
        # marquee and the glow pulse (their frames are just indices).
        super().__init__({"attract": Animation(art["screen"], 1 / info["fps"])}, "attract")
        self.marquee = AnimationController({"loop": Animation(range(art["marquee_frames"]), info["marquee"])}, "loop")
        self.pulse = AnimationController(
            {"loop": Animation((0, 1, 2, 3, 3, 2, 1, 0), info["pulse"])}, "loop")

        x, y = data["x"], data.get("y", self.TOP_Y)
        self.rect = pygame.Rect(x, y, W, H)
        self.footprint = cabinet_footprint(self.rect)
        self.zone = pygame.Rect(x - 8, self.rect.bottom - 2, W + 16, 24)
        self.highlight = False
        self.soft_glow = False  # set by rooms that want gentler neon
        self.flash_time = 0.0

    @property
    def sort_y(self):
        return self.footprint.bottom

    @property
    def screen_center(self):
        return (self.rect.x + SCREEN.centerx, self.rect.y + SCREEN.centery)

    # ------------------------------------------------------------------ play
    @property
    def cost_label(self):
        return f"{self.play_cost} TOKEN" + ("" if self.play_cost == 1 else "S")

    def can_afford(self, profile):
        return profile.can_afford_tokens(self.play_cost)

    def can_use_coupon(self, profile):
        return profile.inventory.has_item(FREE_PLAY_COUPON)

    def can_play(self, profile):
        """Can the player enter at all: with tokens, or with a coupon?"""
        return self.can_afford(profile) or self.can_use_coupon(profile)

    def start_play(self, profile, use_coupon=False):
        """Pay for one play: one Free Play Coupon (no tokens) if `use_coupon`,
        else the token cost. Returns the PlaySession the minigame's reward is
        settled against, or None (nothing taken) if the player cannot pay."""
        name = self.name.upper()
        if use_coupon:
            if not profile.consume_item(FREE_PLAY_COUPON):
                return None
            return PlaySession(profile, self.game_id, 0, name, coupon=True)
        if not profile.spend_tokens(self.play_cost, name):
            return None
        return PlaySession(profile, self.game_id, self.play_cost, name)

    def activate(self):
        """Brief brighten + ring when the player presses E."""
        self.flash_time = INTERACT_FLASH

    def update(self, dt):
        self.anim.update(dt)
        self.marquee.update(dt)
        self.pulse.update(dt)
        self.flash_time = max(0.0, self.flash_time - dt)

    # ------------------------------------------------------------------ draw
    def draw_under(self, surf):
        refl = self.art["reflection_soft" if self.soft_glow else "reflection"][self.pulse.image]
        surf.blit(refl, (self.rect.centerx - refl.get_width() // 2, self.rect.bottom - 8),
                  special_flags=pygame.BLEND_RGB_ADD)

    def draw(self, surf):
        self.draw_at(surf, self.rect.topleft, self.highlight)
        if self.flash_time > 0:
            k = self.flash_time / INTERACT_FLASH
            surf.blit(self.art["flash"], (self.rect.x - 1, self.rect.y - 1 - self.art["pad"]),
                      special_flags=pygame.BLEND_RGB_ADD)
            radius = int(8 + (1 - k) * 34)
            pygame.draw.circle(surf, shade(self.accent, 0.4), self.screen_center, radius, 1)
            pygame.draw.circle(surf, self.neon, self.screen_center, max(1, radius - 5), 1)

    def draw_at(self, surf, pos, highlight=False):
        x, y = pos
        sprites = self.art["cabinet_hi"] if highlight else self.art["cabinet"]
        surf.blit(sprites[self.marquee.image], (x - 1, y - 1 - self.art["pad"]))
        surf.blit(self.image, (x + SCREEN.x, y + SCREEN.y))

    def draw_glow(self, surf):
        halo = self.art["halo_soft" if self.soft_glow else "halo"][self.pulse.image]
        level = 1 if self.flash_time > 0 or self.highlight else 0
        for _ in range(1 + level):
            surf.blit(halo, (self.rect.x - GLOW_SPREAD, self.rect.y - GLOW_SPREAD),
                      special_flags=pygame.BLEND_RGB_ADD)
        cx, cy = self.screen_center
        surf.fill(scale_color(self.accent, 0.12), (cx - 12, cy - 8, 24, 16),
                  special_flags=pygame.BLEND_RGB_ADD)


class IdleCabinet(Prop):
    """A dark, switched-off cabinet standing in an arcade slot that no game
    has claimed yet. Solid, but nothing to interact with."""

    def __init__(self, pos, label="SOON"):
        x, y = pos
        dim, dimmer = (74, 62, 116), (96, 84, 140)
        base = _build_cabinet("space", label, 0, dim, dimmer)
        base.fill((10, 8, 22), SCREEN)                      # screen off
        base.fill(scale_color(dim, 0.5), (SCREEN.x + 4, SCREEN.centery - 1, SCREEN.w - 8, 1))  # idle line
        rect = pygame.Rect(x, y, W, H)
        super().__init__(outlined(base), (x - 1, y - 1), cabinet_footprint(rect))
        self.rect = rect
