"""Reusable background building blocks: cached layer compositing, soft neon
lights and small ambient effects.

Layering, back to front:
  1. floor layer       tiles, rugs                         (baked once)
  2. wall layer        back/side walls, baseboards         (baked once)
  3. decor layer       posters, window frame, sconces      (baked once)
  4. animated backdrop rain window, wall neon strip        (cached frames)
     --- furniture / machines / player / cat, depth-sorted by the scene ---
  5. lighting overlay  multiply vignette + additive pools  (baked once)
  6. emissive overlay  neon signs, string lights, dust, scanlines

Everything expensive is rendered once at load. Per frame the effects only
pick a pre-rendered frame or brightness level and blit it.
"""
import math
import random
from functools import lru_cache

import pygame

from gfx import lerp_color, radial_glow, scale_color, shade


# ------------------------------------------------------------------ helpers
def level_copies(surf, levels):
    """Copies of `surf` with RGB scaled by each k in `levels` (alpha kept)."""
    out = []
    for k in levels:
        copy = surf.copy()
        v = max(0, min(255, int(255 * k)))
        copy.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
        out.append(copy)
    return out


def posterize(surf, step=10):
    """Snap colours to `step` increments so smooth glows read as pixel-art
    bands. Load-time only (per-pixel Python loop)."""
    w, h = surf.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, *a = surf.get_at((x, y))
            surf.set_at((x, y), (r // step * step, g // step * step, b // step * step, *a))
    return surf


def mask_glow(sprite, color, spread=6, strength=0.6):
    """Soft additive halo following the opaque pixels of `sprite`.
    The result is `spread` px larger on every side (blit with BLEND_RGB_ADD)."""
    w, h = sprite.get_size()
    size = (w + spread * 2, h + spread * 2)
    base = pygame.Surface(size)
    base.fill((0, 0, 0))
    silhouette = pygame.mask.from_surface(sprite).to_surface(
        setcolor=(*color[:3], 255), unsetcolor=(0, 0, 0, 0))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            base.blit(silhouette, (spread + dx, spread + dy))
    blur = getattr(pygame.transform, "gaussian_blur", None)
    if blur:
        base = blur(base, max(1, spread // 2))
    else:  # older pygame: cheap down/up-scale blur
        small = pygame.transform.smoothscale(base, (max(1, size[0] // 4), max(1, size[1] // 4)))
        base = pygame.transform.smoothscale(small, size)
    v = int(255 * strength)
    base.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    return posterize(base, 6)


def neon_tube(shape, core, rim):
    """Turn a drawn shape (any opaque pixels) into a neon tube: bright core
    with a 1px coloured rim around it."""
    w, h = shape.get_size()
    mask = pygame.mask.from_surface(shape)
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    rim_s = mask.to_surface(setcolor=(*rim, 255), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(rim_s, (dx, dy))
    out.blit(mask.to_surface(setcolor=(*core, 255), unsetcolor=(0, 0, 0, 0)), (1, 1))
    return out


@lru_cache(maxsize=16)
def small_glow(color, radius=3):
    """Tiny banded dot of light for LEDs and bulbs (BLEND_RGB_ADD)."""
    return radial_glow(radius, color, bands=3)


def banded_vignette(size, edge, center, bands=9, offset=(0, 10)):
    """Multiply layer: `center` colour in the middle fading to `edge`, in
    visible pixel-art bands."""
    w, h = size
    surf = pygame.Surface(size)
    surf.fill(edge)
    for i in range(bands):
        k = (i + 1) / bands
        rect = pygame.Rect(0, 0, int(w * (1.5 - 0.9 * k)), int(h * (1.5 - 0.9 * k)))
        rect.center = (w // 2 + offset[0], h // 2 + offset[1])
        pygame.draw.ellipse(surf, lerp_color(edge, center, k), rect)
    return surf


# ------------------------------------------------------------- neon + LEDs
class NeonLight:
    """A neon tube with a soft halo that gently pulses (and can briefly dip
    for a soft flicker). Tube and halo are pre-rendered at a handful of
    brightness levels; update() just picks one."""
    LEVELS = (0.35, 0.5, 0.62, 0.74, 0.86, 1.0)

    def __init__(self, tube, pos, color, spread=7, strength=0.55,
                 speed=0.8, depth=0.2, phase=0.0, flicker=None):
        self.pos = pos
        self.spread = spread
        self.tubes = level_copies(tube, self.LEVELS)
        self.halos = level_copies(mask_glow(tube, color, spread, strength), self.LEVELS)
        self.speed, self.depth, self.phase = speed, depth, phase
        # flicker: (period seconds, ((start, end, brightness), ...))
        self.flicker = flicker
        self.level = len(self.LEVELS) - 1

    def brightness(self, t):
        k = 1.0 - self.depth * (0.5 + 0.5 * math.sin(t * self.speed + self.phase))
        if self.flicker:
            period, dips = self.flicker
            c = t % period
            for start, end, low in dips:
                if start <= c < end:
                    k = min(k, low)
        return k

    def update(self, t):
        k = self.brightness(t)
        self.level = min(range(len(self.LEVELS)), key=lambda i: abs(self.LEVELS[i] - k))

    def draw(self, surf):
        x, y = self.pos
        surf.blit(self.halos[self.level], (x - self.spread, y - self.spread),
                  special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(self.tubes[self.level], (x, y))


class BlinkLED:
    """A 1px status light that blinks on a fixed rhythm."""

    def __init__(self, offset, color, period=1.6, duty=0.5, phase=0.0):
        self.offset = offset
        self.color = color
        self.dim = scale_color(color, 0.3)
        self.glow = small_glow(scale_color(color, 0.35), 3)
        self.period, self.duty, self.phase = period, duty, phase

    def on(self, t):
        return (t + self.phase) % self.period < self.period * self.duty

    def draw(self, surf, origin, t):
        """Core pixel - call from the owning sprite's draw()."""
        x, y = origin[0] + self.offset[0], origin[1] + self.offset[1]
        surf.fill(self.color if self.on(t) else self.dim, (x, y, 1, 1))

    def draw_glow(self, surf, origin, t):
        """Additive halo - call after the lighting pass."""
        if self.on(t):
            x, y = origin[0] + self.offset[0], origin[1] + self.offset[1]
            surf.blit(self.glow, (x - 3, y - 3), special_flags=pygame.BLEND_RGB_ADD)
            surf.fill(shade(self.color, 0.4), (x, y, 1, 1))


# ----------------------------------------------------------- ambient effects
class RainWindow:
    """A night-city window with falling rain, a sliding droplet, twinkling
    city lights and a slow glass shimmer - pre-rendered as a seamless loop."""
    FRAMES = 36
    FPS = 12
    FRAME = (40, 32, 70)
    FRAME_HI = (62, 50, 100)

    def __init__(self, rect, seed=11):
        self.rect = pygame.Rect(rect)
        self.index = 0
        self.frames = self._build(random.Random(seed))

    def _build(self, rng):
        w, h = self.rect.size
        inner = pygame.Rect(2, 2, w - 4, h - 4)
        iw, ih = inner.size

        sky = pygame.Surface(inner.size)
        top, mid, low = (16, 18, 48), (40, 32, 86), (112, 58, 122)
        for y in range(ih):
            k = (y // 3 * 3) / ih
            c = lerp_color(top, mid, k * 1.6) if k < 0.6 else lerp_color(mid, low, (k - 0.6) / 0.4)
            sky.fill(c, (0, y, iw, 1))
        for _ in range(8):
            sky.fill((150, 150, 200), (rng.randrange(iw), rng.randrange(ih // 2), 1, 1))
        pygame.draw.circle(sky, (230, 226, 200), (iw - 7, 6), 3)      # crescent moon
        pygame.draw.circle(sky, top, (iw - 6, 5), 3)

        # far and near skylines; near buildings carry lit windows
        x = 0
        while x < iw:
            bw, bh = rng.randint(4, 7), rng.randint(7, 13)
            sky.fill((50, 40, 96), (x, ih - bh, bw, bh))
            x += bw
        lights = []
        x = -1
        while x < iw:
            bw, bh = rng.randint(5, 9), rng.randint(4, 10)
            sky.fill((24, 20, 54), (x, ih - bh, bw, bh))
            for wy in range(ih - bh + 2, ih - 1, 2):
                for wx in range(x + 1, x + bw - 1, 2):
                    if rng.random() < 0.35:
                        c = rng.choice(((255, 200, 120), (255, 170, 110), (130, 210, 235)))
                        blink = rng.randrange(self.FRAMES) if rng.random() < 0.25 else None
                        lights.append((wx, wy, scale_color(c, 0.85), blink))
            x += bw

        streaks = [(rng.randrange(-4, iw), rng.randrange(ih), rng.choice((8, 10, 12)),
                    rng.randint(2, 3)) for _ in range(16)]
        drops = [(rng.randrange(2, iw - 2), rng.randrange(ih)) for _ in range(6)]
        slider_x = rng.randrange(4, iw - 4)

        frames = []
        for i in range(self.FRAMES):
            p = i / self.FRAMES
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill(self.FRAME)
            s.fill(self.FRAME_HI, (0, 0, w, 1))
            glass = sky.copy()
            for lx, ly, c, blink in lights:
                if blink is None or not (blink <= i < blink + 5):
                    glass.fill(c, (lx, ly, 1, 1))
            for sx, sy, k, length in streaks:                # rain, loops k times
                y = int(sy + p * ih * k) % (ih + length) - length
                for j in range(length):
                    yy = y + j
                    if 0 <= yy < ih:
                        glass.fill(lerp_color((90, 100, 170), (180, 196, 250), j / length),
                                   ((sx + yy // 6) % iw, yy, 1, 1))
            for dx, dy in drops:                              # beads on the glass
                glass.fill((160, 170, 230), (dx, dy, 1, 1))
            sy = int(p * (ih + 4)) - 2                        # one droplet sliding down
            for j, c in enumerate(((90, 100, 160), (120, 130, 190), (190, 200, 240))):
                if 0 <= sy + j < ih:
                    glass.fill(c, (slider_x, sy + j, 1, 1))
            shimmer = int(p * (iw + ih)) - ih                  # slow diagonal sheen
            for j in range(ih):
                gx = shimmer + j // 2
                if 0 <= gx < iw:
                    glass.fill((14, 14, 22), (gx, j, 2, 1), special_flags=pygame.BLEND_RGB_ADD)
            s.blit(glass, inner.topleft)
            # mullions + static glass highlight
            s.fill(self.FRAME, (inner.x + iw // 2, inner.y, 1, ih))
            s.fill(self.FRAME, (inner.x, inner.y + ih // 2, iw, 1))
            s.fill((60, 60, 100), (inner.x + 2, inner.y + 2, 1, 4), special_flags=pygame.BLEND_RGB_ADD)
            s.fill((40, 40, 70), (inner.x + 3, inner.y + 1, 1, 2), special_flags=pygame.BLEND_RGB_ADD)
            frames.append(s)
        return frames

    def update(self, t):
        self.index = int(t * self.FPS) % self.FRAMES

    def draw(self, surf):
        surf.blit(self.frames[self.index], self.rect.topleft)


class StringLights:
    """Fairy lights sagging between hooks, each bulb softly twinkling."""
    LEVELS = (0.45, 0.72, 1.0)

    def __init__(self, x0, x1, y, span=60, sag=4, spacing=9, colors=None, seed=5):
        rng = random.Random(seed)
        colors = colors or ((255, 196, 120), (255, 160, 200), (130, 215, 235))
        self.origin = (x0, y)

        def wire_y(x):
            return y + int(sag * math.sin(math.pi * ((x - x0) % span) / span))

        self.wire = pygame.Surface((x1 - x0 + 1, sag + 2), pygame.SRCALPHA)
        for x in range(x0, x1 + 1):
            self.wire.fill((52, 44, 70), (x - x0, wire_y(x) - y, 1, 1))
        # per colour: (core colour, glow surface) at each level
        self.looks = {c: [(scale_color(shade(c, 0.3), k), small_glow(scale_color(c, 0.3 * k), 3))
                          for k in self.LEVELS] for c in colors}
        self.bulbs = []
        for i, x in enumerate(range(x0 + 4, x1 - 2, spacing)):
            self.bulbs.append([x, wire_y(x) + 1, colors[i % len(colors)],
                               rng.uniform(0, math.tau), rng.uniform(0.8, 1.6), 2])

    def update(self, t):
        for bulb in self.bulbs:
            v = math.sin(t * bulb[4] + bulb[3])
            bulb[5] = 2 if v > -0.2 else (1 if v > -0.75 else 0)

    def draw(self, surf):
        surf.blit(self.wire, self.origin)
        for x, y, color, _, _, level in self.bulbs:
            core, glow = self.looks[color][level]
            surf.blit(glow, (x - 3, y - 2), special_flags=pygame.BLEND_RGB_ADD)
            surf.fill(core, (x, y, 1, 2))


class DustMotes:
    """Slow drifting specks that softly fade in and out."""

    def __init__(self, area, count=18, seed=7):
        rng = random.Random(seed)
        self.area = pygame.Rect(area)
        self.colors = ((200, 180, 255), (255, 214, 170), (170, 220, 255))
        self.motes = [[rng.uniform(self.area.left, self.area.right),
                       rng.uniform(self.area.top, self.area.bottom),
                       rng.uniform(0, math.tau), rng.randrange(3)] for _ in range(count)]
        self.t = 0.0

    def update(self, t):
        dt, self.t = t - self.t, t
        for m in self.motes:
            m[0] += math.sin(t * 0.4 + m[2]) * 2.5 * dt
            m[1] -= 3 * dt
            if m[1] < self.area.top:
                m[1] = self.area.bottom

    def draw(self, surf):
        for x, y, phase, ci in self.motes:
            v = math.sin(self.t * 1.1 + phase * 3)
            if v > 0.2:
                c = self.colors[ci] if v > 0.7 else scale_color(self.colors[ci], 0.55)
                surf.fill(c, (int(x), int(y), 1, 1))


class Scanlines:
    """Faint CRT scanlines plus a soft bright band that rolls down slowly."""

    def __init__(self, size, alpha=16, band_h=16, period=10.0):
        w, h = size
        self.h = h
        self.period = period
        self.lines = pygame.Surface(size, pygame.SRCALPHA)
        for y in range(0, h, 2):
            self.lines.fill((0, 0, 20, alpha), (0, y, w, 1))
        self.band = pygame.Surface((w, band_h))
        for y in range(band_h):
            k = 1 - abs(y - band_h / 2) / (band_h / 2)
            self.band.fill(scale_color((10, 9, 16), k), (0, y, w, 1))
        self.band_h = band_h
        self.band_y = -band_h

    def update(self, t):
        self.band_y = int((t % self.period) / self.period * (self.h + self.band_h)) - self.band_h

    def draw(self, surf):
        surf.blit(self.band, (0, self.band_y), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(self.lines, (0, 0))


class AmbientAnimator:
    """Owns the ambient effects and their shared clock. Effects are put on
    the 'wall' layer (drawn before sprites, so furniture covers them) or the
    'overlay' layer (emissive, drawn after the lighting pass)."""

    def __init__(self):
        self.time = 0.0
        self.layers = {"wall": [], "overlay": []}

    def add(self, effect, layer="overlay"):
        self.layers[layer].append(effect)
        effect.update(self.time)
        return effect

    def update(self, dt):
        self.time += dt
        for effects in self.layers.values():
            for effect in effects:
                effect.update(self.time)

    def draw(self, surf, layer):
        for effect in self.layers[layer]:
            effect.draw(surf)


# ------------------------------------------------------------ static layers
class ArcadeBackdrop:
    """Builds the static room image from separate cached layers. Subclasses
    implement the paint_* hooks; build() composites them once."""

    def __init__(self, size):
        self.size = size
        self.floor_layer = pygame.Surface(size)
        self.wall_layer = pygame.Surface(size, pygame.SRCALPHA)
        self.decor_layer = pygame.Surface(size, pygame.SRCALPHA)
        self.light_layer = pygame.Surface(size)     # baked additive light under sprites
        self.light_layer.fill((0, 0, 0))

    def paint_floor(self, surf):
        pass

    def paint_walls(self, surf):
        pass

    def paint_decor(self, surf):
        pass

    def add_light(self, glow, pos):
        self.light_layer.blit(glow, pos, special_flags=pygame.BLEND_RGB_ADD)

    def build(self):
        self.paint_floor(self.floor_layer)
        self.paint_walls(self.wall_layer)
        self.paint_decor(self.decor_layer)
        image = self.floor_layer.copy()
        image.blit(self.wall_layer, (0, 0))
        image.blit(self.decor_layer, (0, 0))
        image.blit(self.light_layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return image


class LightingOverlay:
    """Pre-baked room lighting: a multiply vignette plus additive light pools."""

    def __init__(self, size, edge, center, pools=()):
        self.shade = banded_vignette(size, edge, center)
        self.glow = pygame.Surface(size)
        self.glow.fill((0, 0, 0))
        for (x, y), radius, color, squash in pools:
            g = radial_glow(radius, color, bands=6, squash=squash)
            self.glow.blit(g, (x - g.get_width() // 2, y - g.get_height() // 2),
                           special_flags=pygame.BLEND_RGB_ADD)

    def draw(self, surf):
        surf.blit(self.shade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        surf.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


class BackgroundRenderer:
    """Glue between a backdrop, its ambient animator and the lighting.
    The room calls draw_background() before sprites, then draw_lighting()
    and draw_overlay() after them."""

    def __init__(self, backdrop, animator, lighting):
        self.backdrop = backdrop
        self.image = backdrop.build()
        self.animator = animator
        self.lighting = lighting

    def update(self, dt):
        self.animator.update(dt)

    def draw_background(self, surf):
        surf.blit(self.image, (0, 0))
        self.animator.draw(surf, "wall")

    def draw_lighting(self, surf):
        self.lighting.draw(surf)

    def draw_overlay(self, surf):
        self.animator.draw(surf, "overlay")
