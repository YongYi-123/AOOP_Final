"""Optional profile access adapter; standalone racing retains its full catalogue."""
from assets import CarLivery


class RacerProgression:
    def __init__(self, garage=None):
        self.garage = garage

    def owns(self, kind, key):
        return self.garage is None or self.garage.owns(kind,key)

    def lock_message(self, kind, key):
        return '' if self.owns(kind,key) else self.garage.lock_message(kind,key)

    def select(self, kind, key):
        if self.garage is not None:
            self.garage.select(kind,key)

    def livery(self, spec):
        if self.garage is None:
            return None
        color = self.garage.paint_color
        if color is None:
            return None
        return CarLivery(f'{spec.key}-{self.garage.selected("paint")}', color,
                         tuple(int(c*.5) for c in color), tuple(min(255,c+35) for c in color),
                         (90,240,255),(120,255,90))
