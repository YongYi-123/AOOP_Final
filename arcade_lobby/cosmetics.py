"""Avatar cosmetics: what can be worn, where, and who may wear it.

A cosmetic is an ordinary inventory item (see item_registry.py) that also has
a slot here. The profile saves WHAT is worn per slot (PlayerProfile.appearance);
CosmeticService is the only thing that decides whether an item may be worn:
it must be owned and made for that slot. Nothing here touches collision boxes,
speed or any gameplay stat - cosmetics only change the sprite frames
(player.py paints the layers) and the colours of the outfit.

Slots:  palette (outfit colours), hat, face, accessory (a pin or badge on the chest),
clip (hair clip), tail (worn behind) and jacket (replaces the torso colours).

Skin tone, eye style, hair and the base shirt colour are NOT cosmetics: they are
free choices (avatar_style.py) that need no ownership.
"""
from dataclasses import dataclass, replace

PALETTE, HAT, FACE, ACCESSORY = "palette", "hat", "face", "accessory"
CLIP, TAIL, JACKET = "clip", "tail", "jacket"
SLOTS = (PALETTE, HAT, FACE, ACCESSORY, CLIP, TAIL, JACKET)
SLOT_NAMES = {PALETTE: "COLORS", HAT: "HAT", FACE: "FACE", ACCESSORY: "PIN",
              CLIP: "CLIP", TAIL: "TAIL", JACKET: "COAT"}


@dataclass(frozen=True)
class Cosmetic:
    item_id: str
    slot: str
    # palette only: the outfit colours that replace the player's own
    colors: tuple = ()          # ((shirt), (shirt_dark), (beanie), (beanie_dark), (pom))


COSMETICS = {c.item_id: c for c in (
    Cosmetic("neon_cap", HAT),
    Cosmetic("cat_ears", HAT),
    Cosmetic("retro_sunglasses", FACE),
    Cosmetic("star_pin", ACCESSORY),
    Cosmetic("neon_headphones", HAT),
    Cosmetic("pixel_crown", HAT),
    Cosmetic("glowing_visor", FACE),
    Cosmetic("champion_badge", ACCESSORY),
    Cosmetic("star_hair_clip", CLIP),
    Cosmetic("cat_tail", TAIL),
    Cosmetic("rainbow_jacket", JACKET),
    Cosmetic("palette_sunset", PALETTE, ((255, 150, 70), (214, 100, 50), (255, 100, 160), (200, 60, 120), (255, 240, 170))),
    Cosmetic("palette_mint", PALETTE, ((90, 230, 170), (50, 170, 130), (240, 250, 245), (180, 210, 200), (255, 180, 220))),
    Cosmetic("palette_grape", PALETTE, ((140, 90, 230), (96, 60, 180), (255, 214, 90), (210, 160, 40), (255, 250, 200))),
    Cosmetic("palette_cherry", PALETTE, ((235, 60, 90), (170, 36, 66), (255, 235, 220), (214, 190, 180), (255, 214, 90))),
)}


def cosmetic(item_id):
    return COSMETICS.get(item_id)


def cosmetics_for(slot):
    """Every cosmetic made for `slot`, in catalogue order."""
    return [c for c in COSMETICS.values() if c.slot == slot]


def apply_palette(look, palette_id):
    """`look` recoloured by a palette (its outline and UI accent stay, so P1 and
    P2 can still be told apart). An unknown id gives the look unchanged."""
    c = COSMETICS.get(palette_id)
    if c is None or c.slot != PALETTE:
        return look
    shirt, dark, beanie, beanie_dark, pom = c.colors
    return replace(look, shirt=shirt, shirt_dark=dark, beanie=beanie, beanie_dark=beanie_dark, pom=pom)


class CosmeticService:
    """Wear and take off cosmetics for one profile."""

    def __init__(self, profile):
        self.profile = profile

    def owns(self, item_id):
        return self.profile.inventory.has_item(item_id)

    def can_equip(self, slot, item_id):
        c = COSMETICS.get(item_id)
        return c is not None and c.slot == slot and self.owns(item_id)

    def equip(self, slot, item_id):
        """Wear `item_id` in `slot`. False (nothing changes) if the item is
        unknown, not owned, or made for another slot."""
        if not self.can_equip(slot, item_id):
            return False
        self.profile.set_appearance(slot, item_id)
        return True

    def unequip(self, slot):
        if slot not in SLOTS:
            return False
        return self.profile.set_appearance(slot, None)

    def worn(self):
        """{slot: item id} of what is really worn: a saved item that is no
        longer owned (or no longer fits its slot) is simply ignored."""
        return {slot: item for slot, item in self.profile.appearance.items()
                if self.can_equip(slot, item)}

    def worn_in(self, slot):
        return self.worn().get(slot)


def resolve_appearance(profile):
    """What a profile's avatar should wear right now ({} for no profile)."""
    return CosmeticService(profile).worn() if profile is not None else {}
