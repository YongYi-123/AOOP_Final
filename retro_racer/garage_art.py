"""Small pixel car showcase using the racer's original assets and stat data."""
import pygame
import assets
from car_specs import CAR_CATALOG, player_livery


class GaragePreview:
    def __init__(self):
        self.catalog = CAR_CATALOG

    def spec(self,key):
        return next(spec for spec in self.catalog if spec.key == key)

    def draw(self,surface,key,center,livery=None):
        spec = self.spec(key)
        sprite = assets.car_sprite(spec.style.key,84,0,livery or player_livery(spec))
        surface.blit(sprite,sprite.get_rect(center=center))
