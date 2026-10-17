"""A car's picture for the Prize Plaza showcase, painted with the player's own saved Retro Racer paint.

Nothing about cars or paints is duplicated here: the sprite, the car specs and the paint job come
from retro_racer (the same GaragePreview / RacerProgression / assets the Garage screen uses) and
the selected paint comes from the profile's RacingGarage. If retro_racer cannot be loaded the caller
falls back to its own small pixel car, so the room never fails to draw because of this.
"""
import sys

from racing_progression.service import RacingGarage

_racer = None           # (GaragePreview, RacerProgression, assets) once loaded; False if loading failed
_cache = {}


def _load():
    global _racer
    if _racer is None:
        try:
            from retro_racer_scene import load_retro_racer
            game_mod, _ = load_retro_racer()
            _racer = (game_mod.GaragePreview(), game_mod.RacerProgression, sys.modules["retro_racer.assets"])
        except Exception as e:      # a missing / broken racer must not break the plaza
            print(f"[showcase] retro racer cars unavailable ({e}); using the simple car")
            _racer = False
    return _racer or None


def paint_key(profile):
    """The saved paint the car is shown in (a cache key, and what the tests compare)."""
    return RacingGarage(profile).selected("paint")


def car_image(profile, car_key, width):
    """The rear-view car `car_key` in `profile`'s selected paint, `width` px wide, or None."""
    racer = _load()
    if racer is None:
        return None
    key = (car_key, paint_key(profile), width)
    image = _cache.get(key)
    if image is None:
        preview, progression, assets = racer
        try:
            spec = preview.spec(car_key)
            livery = progression(RacingGarage(profile)).livery(spec) or _default_livery(spec)
            image = assets.car_sprite(spec.style.key, width, 0, livery)
        except Exception as e:
            print(f"[showcase] could not draw car {car_key!r}: {e}")
            return None
        _cache[key] = image
    return image


def _default_livery(spec):
    """The factory look the Garage preview uses when no paint is selected."""
    from_mod = sys.modules.get("retro_racer.car_specs")
    return from_mod.player_livery(spec) if from_mod else None
