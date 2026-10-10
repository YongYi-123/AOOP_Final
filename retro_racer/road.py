"""Pseudo-3D road: segments, track layout, projection and rendering."""
import random
import pygame
import settings as S
import assets
from tracks import TRACKS
from track_scenery import CircuitLandmarks
from street_details import StreetDistricts


class RoadSegment:
    def __init__(self, index, curve):
        self.index = index
        self.z = index * S.SEGMENT_LENGTH   # world depth of the segment's near edge
        self.curve = curve
        self.sprites = []                   # (kind, lateral offset in road half-widths)
        self.band = (index // S.RUMBLE_SEGMENTS) % 2     # which of the two alternating colour bands
        self.colors = None                                 # set by Road.apply(theme)
        self.start_line = False     # part of the checkered start/finish line
        self.checkpoint = False     # part of a checkpoint strip
        # Filled in by Road.project each frame
        self.sx1 = self.sy1 = self.sw1 = 0.0
        self.sx2 = self.sy2 = self.sw2 = 0.0
        self.behind = False


class Road:
    def __init__(self, theme, markers=True, route=None):
        self.route = route or TRACKS[0].build(S.SEGMENT_LENGTH)
        if self.route.segment_length != S.SEGMENT_LENGTH:
            raise ValueError("route and road segment lengths must match")
        self.segments = []
        self._build()
        self.length = self.route.length
        self.landmarks = CircuitLandmarks.for_route(self.route)
        self.apply(theme, markers)

    # ---- track construction -------------------------------------------------
    def _build(self):
        self.segments = [RoadSegment(i, curve) for i, curve in enumerate(self.route.curves)]
        self._find_markers()

    def _find_markers(self):
        """Work out where the start/finish line and checkpoint strips go (geometry only)."""
        n = len(self.segments)
        self._start_segments = (0, 1)
        self._checkpoint_segments = [int(frac * n) for frac in S.CHECKPOINT_FRACTIONS]
        self.checkpoint_z = [i * S.SEGMENT_LENGTH for i in self._checkpoint_segments]   # track position per lap

    # ---- theming ------------------------------------------------------------
    def apply(self, theme, markers=True):
        """Re-skin the same geometry: colours, roadside scenery and (optionally) the race markers.

        Cheap enough to call whenever the theme or game mode changes (~1200 segments).
        """
        self.districts = StreetDistricts.for_road(self.route,theme)
        self.theme = theme
        light, dark = theme.colors
        for seg in self.segments:
            seg.colors = dark if seg.band else light
            seg.sprites = []
            seg.start_line = markers and seg.index in self._start_segments
            seg.checkpoint = markers and any(seg.index in (i, i + 1) for i in self._checkpoint_segments)
        self._add_scenery(theme)
        if markers:
            self.segments[self._start_segments[0]].sprites.append(("finish", 0.0))
            for i in self._checkpoint_segments:
                self.segments[i].sprites.append(("gate", 0.0))

    def _add_scenery(self, theme):
        """Scatter roadside objects by the theme's placement rules (deterministic per theme)."""
        rng = random.Random(7)
        n = len(self.segments)
        for seg in self.segments:
            i = seg.index
            for rule in theme.placements:
                if (i - rule.phase) % rule.every or (rule.chance < 1.0 and rng.random() > rule.chance):
                    continue
                if rule.sides == 1:
                    sides = (-1, 1)
                elif rule.sides == 2:
                    sides = (1 if (i // rule.every) % 2 else -1,)
                else:
                    sides = (rng.choice((-1, 1)),)
                for side in sides:
                    if rule.curve_signs:        # chevron signs point the way the road is about to bend
                        ahead = self.segments[(i + 30) % n].curve
                        kind = rule.curve_signs[1] if ahead > 1.0 else rule.curve_signs[0] if ahead < -1.0 else rule.curve_signs[2]
                        side = -1 if kind == rule.curve_signs[0] else 1
                    elif rule.by_side:
                        kind = rule.by_side[0] if side < 0 else rule.by_side[1]
                    else:
                        kind = rng.choices([k for k, _ in rule.kinds], [w for _, w in rule.kinds])[0]
                    dist = rule.near if rule.far <= rule.near else rng.uniform(rule.near, rule.far)
                    seg.sprites.append((kind, side * dist))

    def segment_at(self, z):
        return self.segments[int(z // S.SEGMENT_LENGTH) % len(self.segments)]

    # ---- projection ---------------------------------------------------------
    @staticmethod
    def _project(wx, wy, wz, cam_x, cam_z):
        cx, cy, cz = wx - cam_x, wy - S.CAMERA_HEIGHT, wz - cam_z
        scale = S.CAMERA_DEPTH / cz
        sx = S.WIDTH / 2 + scale * cx * S.WIDTH / 2
        sy = S.HEIGHT / 2 - scale * cy * S.HEIGHT / 2
        sw = scale * S.ROAD_WIDTH * S.WIDTH / 2
        return sx, sy, sw

    def project(self, cam_z, player_x):
        """Project the visible segments onto the screen; returns them near-to-far."""
        n = len(self.segments)
        base_idx = int(cam_z // S.SEGMENT_LENGTH)
        base_pct = (cam_z % S.SEGMENT_LENGTH) / S.SEGMENT_LENGTH
        cam_x = player_x * S.ROAD_WIDTH
        elevation = self.route.elevation_at(cam_z+S.CAMERA_HEIGHT*S.CAMERA_DEPTH)
        x = 0.0                                   # accumulated horizontal curve offset
        dx = -self.segments[base_idx % n].curve * base_pct
        visible = []
        for i in range(S.DRAW_DISTANCE):
            seg = self.segments[(base_idx + i) % n]
            loop = self.length if base_idx + i >= n else 0   # track wraps around
            z1 = seg.z + loop
            z2 = z1 + S.SEGMENT_LENGTH
            seg.behind = (z1 - cam_z) <= S.CAMERA_DEPTH
            if not seg.behind:
                seg.sx1, seg.sy1, seg.sw1 = self._project(0, self.route.elevation_at(z1)-elevation, z1, cam_x - x, cam_z)
                seg.sx2, seg.sy2, seg.sw2 = self._project(0, self.route.elevation_at(z2)-elevation, z2, cam_x - x - dx, cam_z)
            x += dx
            dx += seg.curve
            visible.append(seg)
        return visible

    # ---- rendering ----------------------------------------------------------
    def draw(self, surf, cam_z, player_x, cars=()):
        """Draw the road far-to-near. Each segment's roadside objects and cars are drawn right
        after it, so nearer road/cars always cover farther ones."""
        visible = self.project(cam_z, player_x)
        by_segment = {}
        for car in tuple(cars)+self.landmarks+self.districts:
            by_segment.setdefault(int(car.z // S.SEGMENT_LENGTH) % len(self.segments), []).append(car)
        drawable = [s for s in visible if not s.behind and s.sy2 < s.sy1 and s.sy1 <= S.HEIGHT + 1]
        for seg in reversed(drawable):
            self._draw_segment(surf, seg)
            self._draw_sprites(surf, seg)
            for car in sorted(by_segment.get(seg.index, ()), key=lambda c: -c.z % S.SEGMENT_LENGTH):
                pct = (car.z % S.SEGMENT_LENGTH) / S.SEGMENT_LENGTH   # interpolate within the segment
                sx = seg.sx1 + (seg.sx2 - seg.sx1) * pct
                sy = seg.sy1 + (seg.sy2 - seg.sy1) * pct
                sw = seg.sw1 + (seg.sw2 - seg.sw1) * pct
                car.draw(surf, sx + sw * car.x, sy, sw)

    def _draw_segment(self, surf, seg):
        c = seg.colors
        y1, y2 = seg.sy1, seg.sy2
        top = int(y2)
        pygame.draw.rect(surf, c["grass"], (0, top, S.WIDTH, max(1, int(y1) - top + 1)))
        water = self.theme.water
        if water:       # sea on the left, beyond a strip of sand
            wc = water[1] if seg.band else water[0]
            pygame.draw.polygon(surf, wc, ((0, y1), (seg.sx1 + seg.sw1 * water[2], y1),
                                           (seg.sx2 + seg.sw2 * water[2], y2), (0, y2)))
        r1, r2 = seg.sw1 / 6, seg.sw2 / 6
        self._quad(surf, c["rumble"], seg.sx1 - seg.sw1 - r1, y1, seg.sx1 - seg.sw1, y1,
                   seg.sx2 - seg.sw2, y2, seg.sx2 - seg.sw2 - r2, y2)
        self._quad(surf, c["rumble"], seg.sx1 + seg.sw1 + r1, y1, seg.sx1 + seg.sw1, y1,
                   seg.sx2 + seg.sw2, y2, seg.sx2 + seg.sw2 + r2, y2)
        road_col = (20, 20, 20) if seg.start_line else S.CHECKPOINT_COLOR if seg.checkpoint else c["road"]
        self._quad(surf, road_col, seg.sx1 - seg.sw1, y1, seg.sx1 + seg.sw1, y1,
                   seg.sx2 + seg.sw2, y2, seg.sx2 - seg.sw2, y2)
        if seg.start_line:
            self._checker(surf, seg)
        if c["lane"] and not (seg.start_line or seg.checkpoint):
            l1, l2 = seg.sw1 / S.LANES / 24, seg.sw2 / S.LANES / 24
            for k in range(1, S.LANES):
                f = -1 + 2 * k / S.LANES
                lx1, lx2 = seg.sx1 + seg.sw1 * f, seg.sx2 + seg.sw2 * f
                self._quad(surf, c["lane"], lx1 - l1, y1, lx1 + l1, y1, lx2 + l2, y2, lx2 - l2, y2)

    def _checker(self, surf, seg, cells=10):
        for k in range(cells):
            if (k + seg.index) % 2:
                continue
            f0, f1 = -1 + 2 * k / cells, -1 + 2 * (k + 1) / cells
            self._quad(surf, S.WHITE, seg.sx1 + seg.sw1 * f0, seg.sy1, seg.sx1 + seg.sw1 * f1, seg.sy1,
                       seg.sx2 + seg.sw2 * f1, seg.sy2, seg.sx2 + seg.sw2 * f0, seg.sy2)

    @staticmethod
    def _quad(surf, color, x1, y1, x2, y2, x3, y3, x4, y4):
        pygame.draw.polygon(surf, color, ((x1, y1), (x2, y2), (x3, y3), (x4, y4)))

    def _draw_sprites(self, surf, seg):
        s = seg.sw1 / 1000      # sprite scale: shrinks with distance
        if s < 0.02:
            return
        for kind, off in seg.sprites:
            x, y = seg.sx1 + seg.sw1 * off, seg.sy1
            if x < -1300 * s or x > S.WIDTH + 1300 * s:
                continue
            painter = assets.SCENERY.get(kind)
            if painter:
                painter(surf, x, y, s)
            else:
                getattr(self, "_" + kind)(surf, x, y, s)

    @staticmethod
    def _gate(surf, x, y, s, finish=False):
        """Overhead banner across the road: yellow for checkpoints, checkered for the finish."""
        half, top, bar = 1150 * s, 700 * s, 130 * s
        for side in (-1, 1):
            pygame.draw.rect(surf, (230, 230, 230), (x + side * half - 25 * s, y - top, 50 * s, top))
        pygame.draw.rect(surf, (20, 20, 20), (x - half, y - top, 2 * half, bar))
        cells = 16
        cw = 2 * half / cells
        for k in range(cells):
            if finish:
                for row in range(2):
                    if (k + row) % 2 == 0:
                        pygame.draw.rect(surf, S.WHITE, (x - half + k * cw, y - top + row * bar / 2, cw, bar / 2))
            elif k % 2 == 0:
                pygame.draw.rect(surf, S.CHECKPOINT_COLOR, (x - half + k * cw, y - top, cw, bar))

    def _finish(self, surf, x, y, s):
        self._gate(surf, x, y, s, finish=True)
