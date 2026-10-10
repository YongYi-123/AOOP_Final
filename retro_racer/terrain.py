"""Smooth periodic presentation-only elevation profiles."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ElevationProfile:
    amplitude: float
    waves: int

    def sample(self,count):
        heights = tuple(self.amplitude*(math.sin(2*math.pi*self.waves*i/count)
                        +.2*math.sin(4*math.pi*self.waves*i/count)) for i in range(count))
        return heights+(heights[0],)


ELEVATION_PROFILES = {'emerald':ElevationProfile(65,2), 'harbor':ElevationProfile(25,1),
                      'summit':ElevationProfile(180,3)}
