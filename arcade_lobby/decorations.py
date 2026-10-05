"""HOME decoration foundation: what can be placed (DecorationDefinition),
where it can go (DecorationSlot) and who keeps track (HomeDecorationManager).

There is no editor yet. The room has a fixed set of slots; each slot has a
type and a default decoration. A decoration of the matching type (and size)
can be put in a slot with HomeDecorationManager.equip(), which stores the choice
in the PlayerProfile so it is saved. Later, prizes bought with TICKETS only
need to register a DecorationDefinition in the catalogue and call equip().

How each slot type is drawn:
  wall_poster, rug   flat: baked into one cached layer under the sprites
  neon_sign          an animated glowing tube on the wall
  plant, table_decor, cat_bed
                     props: depth-sorted with the player and the cats
"""
from dataclasses import dataclass
from typing import Callable, Optional

import pygame

from backdrop import NeonLight, neon_tube
from font import get_font
from gfx import outlined, scale_color
from lofi_props import make_tall_plant
from room import Prop, make_plant
from settings import VIEW_H, VIEW_W, Lofi

WALL_POSTER, RUG, TABLE_DECOR, PLANT, NEON_SIGN, CAT_BED = (
    "wall_poster", "rug", "table_decor", "plant", "neon_sign", "cat_bed")
SLOT_TYPES = (WALL_POSTER, RUG, TABLE_DECOR, PLANT, NEON_SIGN, CAT_BED)
FLAT_TYPES = (WALL_POSTER, RUG)
PROP_TYPES = (PLANT, TABLE_DECOR, CAT_BED)


@dataclass(frozen=True)
class DecorationDefinition:
    """One decoration: what it is, which kind of slot it fits and how to
    paint it. `painter` is called once and its result cached. For a neon sign
    the painter returns the white shape of the tube and `neon` is its
    (core colour, rim colour). `ticket_cost` is for the future prize counter;
    default decorations cost nothing."""
    decoration_id: str
    name: str
    slot_type: str
    painter: Callable[[], pygame.Surface]
    ticket_cost: int = 0
    neon: Optional[tuple] = None

    def __post_init__(self):
        if self.slot_type not in SLOT_TYPES:
            raise ValueError(f"unknown slot type {self.slot_type!r}")
        if self.slot_type == NEON_SIGN and self.neon is None:
            raise ValueError("a neon sign needs neon=(core, rim) colours")


@dataclass(frozen=True)
class DecorationSlot:
    """A fixed place in HOME. `size` is the largest sprite that fits.
    `position` is where it goes: the sprite's top-left for flat things (posters,
    rugs, neon signs), the bottom-centre for props (so plants of different
    heights all stand on the same spot). A prop's `foot` (w, h) is its
    collision / depth box under that point; `solid` makes it block movement
    and `sort_bias` draws it that many pixels "closer" than its spot (for
    something standing on a table)."""
    slot_id: str
    slot_type: str
    position: tuple
    size: tuple
    default_id: str
    foot: Optional[tuple] = None
    solid: bool = False
    sort_bias: int = 0

    def __post_init__(self):
        if self.slot_type not in SLOT_TYPES:
            raise ValueError(f"unknown slot type {self.slot_type!r}")


class DecorationCatalog:
    """Every decoration that exists, by id."""

    def __init__(self, definitions=()):
        self._items = {}
        for d in definitions:
            self.register(d)

    def register(self, definition):
        if definition.decoration_id in self._items:
            raise ValueError(f"duplicate decoration {definition.decoration_id!r}")
        self._items[definition.decoration_id] = definition

    def get(self, decoration_id):
        return self._items.get(decoration_id)

    def for_slot_type(self, slot_type):
        return [d for d in self._items.values() if d.slot_type == slot_type]

    def __contains__(self, decoration_id):
        return decoration_id in self._items

    def __len__(self):
        return len(self._items)


class DecorationProp(Prop):
    """A decoration standing in the room (plant, table item, cat bed)."""

    def __init__(self, slot, sprite):
        px, py = slot.position
        w, h = sprite.get_size()
        fw, fh = slot.foot or (min(w - 4, 16), 4)
        footprint = (px - fw // 2, py - fh + slot.sort_bias, fw, fh)
        super().__init__(sprite, (px - w // 2, py - h), footprint)
        self.solid = slot.solid
        self.slot_id = slot.slot_id

    def draw_under(self, surf):
        if self.solid:
            super().draw_under(surf)


class HomeDecorationManager:
    """Resolves what is in each slot, builds the pieces to draw and keeps them
    in step with the profile. `on_change` (set by the room) is called after a
    decoration changes, so the room can pick up new props and collision."""

    def __init__(self, profile, slots, catalog):
        self.profile = profile
        slots = list(slots)
        self.slots = {s.slot_id: s for s in slots}
        if len(self.slots) != len(slots):
            raise ValueError("duplicate decoration slot ids")
        self.catalog = catalog
        self.on_change = None
        self._sprites = {}
        self.flat_layer = None
        self.props = []
        self.neon = []
        self.time = 0.0
        for slot in self.slots.values():          # a bad default is a coding error: fail early
            if self._fits(slot, catalog.get(slot.default_id)) is False:
                raise ValueError(f"default decoration for slot {slot.slot_id!r} does not fit it")
        self.rebuild()
        profile.subscribe(self._on_profile_change)

    def close(self):
        self.profile.unsubscribe(self._on_profile_change)

    # ------------------------------------------------------------ resolve
    def sprite(self, definition):
        sprite = self._sprites.get(definition.decoration_id)
        if sprite is None:
            sprite = self._sprites[definition.decoration_id] = definition.painter()
        return sprite

    def _fits(self, slot, definition):
        if definition is None or definition.slot_type != slot.slot_type:
            return False
        w, h = self.sprite(definition).get_size()
        return w <= slot.size[0] and h <= slot.size[1]

    def decoration_for(self, slot_id):
        """What is shown in a slot: the saved choice if it still exists and
        fits, otherwise the slot's default."""
        slot = self.slots[slot_id]
        chosen = self.catalog.get(self.profile.home_decorations.get(slot_id))
        if chosen is not None and self._fits(slot, chosen):
            return chosen
        return self.catalog.get(slot.default_id)

    def can_equip(self, slot_id, decoration_id):
        slot = self.slots.get(slot_id)
        return slot is not None and self._fits(slot, self.catalog.get(decoration_id))

    def equip(self, slot_id, decoration_id):
        """Put a decoration in a slot. Returns False (nothing changes) if the
        slot or decoration is unknown or they do not match."""
        if not self.can_equip(slot_id, decoration_id):
            return False
        self.profile.set_home_decoration(slot_id, decoration_id)
        return True

    def reset_slot(self, slot_id):
        if slot_id in self.slots:
            self.profile.set_home_decoration(slot_id, None)

    def _on_profile_change(self, change):
        if change.field == "decorations":
            self.rebuild()
            if self.on_change:
                self.on_change()

    # ------------------------------------------------------------ build
    def rebuild(self):
        flat = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        self.props, self.neon = [], []
        for slot in self.slots.values():
            definition = self.decoration_for(slot.slot_id)
            sprite = self.sprite(definition)
            if slot.slot_type in FLAT_TYPES:
                flat.blit(sprite, slot.position)
            elif slot.slot_type == NEON_SIGN:
                rim = definition.neon[1]
                self.neon.append(NeonLight(sprite, slot.position, rim, spread=7, strength=0.5,
                                           speed=0.7, depth=0.2, phase=len(self.neon) * 1.7))
            else:
                self.props.append(DecorationProp(slot, sprite))
        self.flat_layer = flat

    # ------------------------------------------------------------ per frame
    def update(self, dt):
        self.time += dt
        for light in self.neon:
            light.update(self.time)

    def draw_flat(self, surf):
        surf.blit(self.flat_layer, (0, 0))

    def draw_neon(self, surf):
        for light in self.neon:
            light.draw(surf)


# ------------------------------------------------------------------ painters
def _frame(size, border, fill):
    s = pygame.Surface(size, pygame.SRCALPHA)
    s.fill(border)
    s.fill(fill, (1, 1, size[0] - 2, size[1] - 2))
    return s


def _poster_cassette():
    s = _frame((28, 22), (150, 128, 206), (46, 56, 106))
    s.fill((70, 70, 130), (1, 16, 26, 5))
    s.fill((150, 84, 140), (1, 18, 26, 2))
    c = pygame.Rect(5, 4, 18, 11)
    s.fill(Lofi.CREAM, c)
    s.fill((226, 130, 170), (c.x + 2, c.y + 1, c.w - 4, 3))
    s.fill((60, 46, 70), (c.x + 4, c.y + 6, c.w - 8, 3))
    for rx in (c.x + 5, c.x + 12):
        s.fill((24, 20, 34), (rx, c.y + 6, 2, 2))
        s.fill((200, 190, 210), (rx, c.y + 6, 1, 1))
    return s


def _poster_vinyl():
    s = _frame((26, 36), Lofi.MAGENTA, (42, 28, 74))
    cx, cy = 13, 13
    pygame.draw.circle(s, (14, 12, 24), (cx, cy), 9)
    for rad in (7, 5):
        pygame.draw.circle(s, (38, 34, 58), (cx, cy), rad, 1)
    pygame.draw.circle(s, Lofi.MAGENTA, (cx, cy), 3)
    s.fill((255, 220, 240), (cx, cy, 1, 1))
    s.fill((90, 86, 120), (cx - 6, cy - 5, 2, 1))
    s.blit(get_font().render("LOFI", Lofi.PINK), (2, 27))
    return s


def _poster_cat():
    s = _frame((16, 20), (110, 180, 200), (34, 22, 60))
    cx, cy = 8, 11
    col = (246, 164, 86)
    pygame.draw.circle(s, col, (cx, cy), 5)
    pygame.draw.polygon(s, col, [(cx - 5, cy - 1), (cx - 4, cy - 7), (cx - 1, cy - 4)])
    pygame.draw.polygon(s, col, [(cx + 4, cy - 1), (cx + 3, cy - 7), (cx, cy - 4)])
    s.fill((34, 22, 60), (cx - 3, cy, 2, 1))
    s.fill((34, 22, 60), (cx + 1, cy, 2, 1))
    for sx, sy in ((3, 3), (12, 4)):
        s.fill(Lofi.WARM, (sx, sy, 1, 1))
    return s


def _poster_arcade():
    s = _frame((24, 30), (110, 220, 235), (24, 20, 56))
    s.blit(get_font().render("PLAY", Lofi.CYAN), (3, 3))
    s.fill((60, 50, 110), (4, 12, 16, 12))            # a tiny cabinet outline
    s.fill((10, 8, 22), (6, 14, 12, 6))
    s.fill(Lofi.MAGENTA, (7, 15, 3, 3))
    s.fill((255, 214, 90), (12, 17, 4, 2))
    s.fill(Lofi.PINK, (6, 22, 12, 1))
    return s


def _rug(base, border, trim, motif, size=(106, 58)):
    w, h = size
    s = pygame.Surface(size, pygame.SRCALPHA)
    r = pygame.Rect(2, 2, w - 4, h - 4)
    s.fill(base, r)
    pygame.draw.rect(s, border, r.inflate(-4, -4), 2)
    pygame.draw.rect(s, trim, r.inflate(-10, -10), 1)
    for y in range(r.y + 12, r.bottom - 10, 8):
        for x in range(r.x + 12 + (y // 8 % 2) * 6, r.right - 12, 12):
            pygame.draw.polygon(s, motif, [(x, y - 2), (x + 2, y), (x, y + 2), (x - 2, y)])
    for y in range(r.y + 3, r.bottom - 3, 2):                # fringe
        s.fill((150, 132, 170), (0, y, 2, 1))
        s.fill((150, 132, 170), (w - 2, y, 2, 1))
    return s


def _rug_lounge():
    return _rug((60, 40, 84), (88, 58, 112), (150, 96, 146), (96, 66, 126))


def _rug_teal():
    return _rug((30, 56, 78), (44, 84, 110), (120, 190, 200), (60, 110, 130))


def _table_cactus():
    s = pygame.Surface((8, 9), pygame.SRCALPHA)
    s.fill(Lofi.LEAF, (3, 1, 2, 5))
    s.fill(Lofi.LEAF, (1, 3, 2, 1))
    s.fill(Lofi.LEAF, (1, 2, 1, 2))
    s.fill(Lofi.LEAF_LIGHT, (3, 1, 1, 2))
    s.fill(Lofi.TERRACOTTA, (2, 6, 4, 3))
    s.fill(Lofi.TERRACOTTA_HI, (2, 6, 4, 1))
    return outlined(s)


def _table_candle():
    s = pygame.Surface((6, 9), pygame.SRCALPHA)
    s.fill((236, 228, 244), (1, 3, 4, 6))
    s.fill((190, 180, 210), (1, 8, 4, 1))
    s.fill((255, 214, 90), (2, 0, 2, 3))
    s.fill((255, 150, 80), (2, 2, 2, 1))
    return outlined(s)


def _table_snacks():
    s = pygame.Surface((10, 7), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (226, 130, 170), (0, 3, 10, 4))
    for x, c in ((2, (255, 214, 90)), (4, (110, 215, 235)), (6, (255, 255, 255))):
        s.fill(c, (x, 1, 2, 3))
    return outlined(s)


def _bed(fur, rim, cushion, size=(26, 16)):
    w, h = size
    s = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(s, shade_dark(rim), (0, 3, w, h - 3))
    pygame.draw.ellipse(s, rim, (0, 1, w, h - 4))
    pygame.draw.ellipse(s, cushion, (3, 3, w - 6, h - 9))
    s.fill(fur, (w // 2 - 1, 5, 3, 1))
    return outlined(s)


def shade_dark(color):
    return scale_color(color, 0.6)


def _bed_round():
    return _bed((255, 232, 210), (150, 96, 146), (226, 170, 196))


def _bed_blue():
    return _bed((230, 240, 255), (70, 100, 170), (120, 160, 220))


def _plant_monstera():
    return make_tall_plant()


def _plant_bushy():
    return make_plant(Lofi.TERRACOTTA, Lofi.TERRACOTTA_HI)


_HEART = ("0110110", "1111111", "1111111", "0111110", "0011100", "0001000")
_NOTE = ("0001110", "0001010", "0001000", "0001000", "0111000", "1111000", "0110000")
_STAR = ("000010000", "000010000", "000111000", "111111111", "011111110",
         "001111100", "001101100", "011000110")


def _shape(rows):
    s = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "1":
                s.set_at((x, y), (255, 255, 255, 255))
    return s


def _neon(rows, core, rim, scale=2):
    shape = _shape(rows)
    shape = pygame.transform.scale(shape, (shape.get_width() * scale, shape.get_height() * scale))
    return neon_tube(shape, core, rim)


def _neon_note():
    return _neon(_NOTE, (210, 248, 255), (90, 190, 215))


def _neon_heart():
    return _neon(_HEART, (255, 214, 236), (230, 90, 170))


def _neon_star():
    return _neon(_STAR, (255, 244, 190), (255, 170, 70))


def default_catalog():
    """The decorations that exist today: the defaults plus a few alternates
    (free for now) that show how slots take different items."""
    return DecorationCatalog([
        DecorationDefinition("poster_cassette", "Cassette Poster", WALL_POSTER, _poster_cassette),
        DecorationDefinition("poster_vinyl", "Vinyl Poster", WALL_POSTER, _poster_vinyl),
        DecorationDefinition("poster_cat", "Sleepy Cat Poster", WALL_POSTER, _poster_cat),
        DecorationDefinition("poster_arcade", "Play Poster", WALL_POSTER, _poster_arcade),
        DecorationDefinition("rug_lounge", "Plum Rug", RUG, _rug_lounge),
        DecorationDefinition("rug_teal", "Teal Rug", RUG, _rug_teal),
        DecorationDefinition("table_cactus", "Tiny Cactus", TABLE_DECOR, _table_cactus),
        DecorationDefinition("table_candle", "Candle", TABLE_DECOR, _table_candle),
        DecorationDefinition("table_snacks", "Snack Plate", TABLE_DECOR, _table_snacks),
        DecorationDefinition("plant_monstera", "Monstera", PLANT, _plant_monstera),
        DecorationDefinition("plant_bushy", "Bushy Plant", PLANT, _plant_bushy),
        DecorationDefinition("neon_note", "Neon Note", NEON_SIGN, _neon_note,
                             neon=((210, 248, 255), (90, 190, 215))),
        DecorationDefinition("neon_heart", "Neon Heart", NEON_SIGN, _neon_heart,
                             neon=((255, 214, 236), (230, 90, 170))),
        DecorationDefinition("neon_star", "Neon Star", NEON_SIGN, _neon_star,
                             neon=((255, 244, 190), (255, 170, 70))),
        DecorationDefinition("bed_round", "Round Cat Bed", CAT_BED, _bed_round),
        DecorationDefinition("bed_blue", "Blue Cat Bed", CAT_BED, _bed_blue),
    ])
