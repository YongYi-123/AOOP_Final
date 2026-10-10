"""Original closed circuits: one sampled centreline drives road and map.

Control points are authored in plan view (positive y down, positive turns
right). Periodic cubic B-splines give smooth curvature transitions; uniform
distance sampling matches Road's fixed-length segments. CURVE_GAIN converts
the centreline's heading change to the existing arcade steering convention.
No independent minimap outline or geometry correction is used.
"""
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
import math
from terrain import ELEVATION_PROFILES

CURVE_GAIN = 40.0


@dataclass(frozen=True)
class CircuitRoute:
    key: str
    points: tuple
    curves: tuple
    segment_length: float
    heights: tuple = ()

    @property
    def length(self):
        return len(self.curves) * self.segment_length

    def point_at(self, z):
        progress = (z % self.length) / self.segment_length
        i = int(progress)
        fraction = progress - i
        a, b = self.points[i], self.points[i + 1]
        return (a[0] + (b[0] - a[0]) * fraction,
                a[1] + (b[1] - a[1]) * fraction)

    def elevation_at(self,z):
        if not self.heights:
            return 0.0
        progress=(z%self.length)/self.segment_length
        i=int(progress)
        return self.heights[i]+(self.heights[i+1]-self.heights[i])*(progress-i)


@dataclass(frozen=True)
class TrackDefinition:
    key: str
    name: str
    tagline: str
    controls: tuple
    segments: int

    @lru_cache(maxsize=16)
    def build(self, segment_length=200):
        if segment_length <= 0:
            raise ValueError("segment length must be positive")
        dense = []
        n = len(self.controls)
        for i in range(n):
            p0, p1, p2, p3 = [self.controls[j % n] for j in (i - 1, i, i + 1, i + 2)]
            for step in range(256):
                t = step / 256
                dense.append(tuple(((1-t)**3*p0[k] + (3*t**3-6*t*t+4)*p1[k]
                                   + (-3*t**3+3*t*t+3*t+1)*p2[k] + t**3*p3[k])/6
                                   for k in (0, 1)))
        dense.append(dense[0])
        distances = [0.0]
        for a, b in zip(dense, dense[1:]):
            distances.append(distances[-1] + math.dist(a, b))
        scale = self.segments * segment_length / distances[-1]
        points = []
        for i in range(self.segments):
            target = i * distances[-1] / self.segments
            j = min(len(dense) - 2, bisect_right(distances, target) - 1)
            f = (target - distances[j]) / (distances[j + 1] - distances[j])
            a, b = dense[j], dense[j + 1]
            points.append(tuple((a[k] + (b[k] - a[k]) * f) * scale for k in (0, 1)))
        curves = []
        for i, b in enumerate(points):
            a, c = points[i - 1], points[(i + 1) % self.segments]
            u, v = (b[0]-a[0], b[1]-a[1]), (c[0]-b[0], c[1]-b[1])
            curves.append(math.atan2(u[0]*v[1]-u[1]*v[0], u[0]*v[0]+u[1]*v[1]) * CURVE_GAIN)
        profile = ELEVATION_PROFILES.get(self.key)
        heights = profile.sample(self.segments) if profile else ()
        return CircuitRoute(self.key, tuple(points + [points[0]]), tuple(curves), segment_length, heights)


TRACKS = (
    TrackDefinition("emerald", "EMERALD GP", "FLOWING ESSES / DOUBLE APEX",
        ((0,-300),(300,-300),(460,-280),(510,-170),(450,-90),(520,-10),
         (450,70),(520,150),(440,235),(320,275),(150,275),(100,170),(20,150),(-70,240),
         (-260,290),(-440,220),(-500,80),(-460,-80),(-500,-220),(-300,-300)), 1280),
    TrackDefinition("harbor", "HARBOR SPRINT", "LONG STRAIGHT / TIGHT HAIRPIN",
        ((0,-240),(360,-240),(620,-240),(680,-210),(710,-150),(670,-90),(600,-85),(520,-95),(430,-110),
         (320,-40),(440,30),(300,110),(470,180),(620,180),(700,230),
         (650,300),(310,330),(0,330),(-220,230),(-330,60),(-520,40),
         (-560,-60),(-520,-240),(-300,-240)), 1440),
    TrackDefinition("summit", "SUMMIT RING", "TECHNICAL S / COMPOUND CORNERS",
        ((0,-320),(250,-320),(440,-260),(420,-170),(290,-140),(180,-90),(140,-20),
         (240,60),(200,130),(300,180),(370,160),(430,240),(410,320),(300,350),(180,300),
         (80,220),(-20,160),(-180,230),(-350,280),(-460,180),(-420,60),
         (-300,20),(-340,-100),(-480,-200),(-380,-320),(-200,-320)), 1360),
)
