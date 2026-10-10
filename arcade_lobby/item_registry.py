"""Item definitions and the registry of every item the game knows.

An ItemDefinition is pure data: what an item is called, how it is shown and
how it stacks. It says nothing about what the item does. Adding an item later
means adding one entry to _ITEMS below; the inventory and its screen need no
changes. (The file is not called items.py because retro_racer has one.)
"""
from dataclasses import dataclass, field

COSMETIC, ARCADE, COLLECTIBLE, CONSUMABLE = "COSMETIC", "ARCADE", "COLLECTIBLE", "CONSUMABLE"
CATEGORIES = (COSMETIC, ARCADE, COLLECTIBLE, CONSUMABLE)
COMMON, UNCOMMON, RARE, EPIC = "COMMON", "UNCOMMON", "RARE", "EPIC"
RARITIES = (COMMON, UNCOMMON, RARE, EPIC)
DEFAULT_MAX_STACK = 99
FREE_PLAY_COUPON = "free_play_coupon"   # the one item machines accept as payment


@dataclass(frozen=True)
class ItemDefinition:
    id: str
    name: str
    description: str
    category: str
    rarity: str = COMMON
    stackable: bool = True
    max_stack: int = DEFAULT_MAX_STACK
    # How the inventory screen draws it: {"shape": ..., "color": (r, g, b), "accent": (r, g, b)}
    # (shapes are painted by item_icons.py)
    icon: dict = field(default_factory=dict, hash=False, compare=False)

    def __post_init__(self):
        if not self.id or self.category not in CATEGORIES or self.rarity not in RARITIES:
            raise ValueError(f"invalid item definition: {self.id!r}")
        if not self.stackable:
            object.__setattr__(self, "max_stack", 1)    # a single copy, whatever was asked
        elif self.max_stack < 1:
            raise ValueError(f"{self.id}: max_stack must be at least 1")

    @property
    def limit(self):
        """The most copies one inventory can hold."""
        return self.max_stack if self.stackable else 1


class ItemRegistry:
    """Looks items up by id. Unknown ids give None rather than an error, so a
    save that mentions a removed item never breaks the game."""

    def __init__(self, definitions=()):
        self._items = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition):
        if definition.id in self._items:
            raise ValueError(f"item {definition.id!r} is already registered")
        self._items[definition.id] = definition

    def get(self, item_id):
        return self._items.get(item_id)

    def __contains__(self, item_id):
        return item_id in self._items

    def __iter__(self):
        return iter(self._items.values())

    def __len__(self):
        return len(self._items)

# Harmless test items for the inventory screen. They have no gameplay effect.
_ITEMS = (
    ItemDefinition(
        "cat_sticker", "CAT STICKER", "A tiny sticker of the arcade cat.", COLLECTIBLE, COMMON,
        stackable=False, icon={"shape": "sticker", "color": (246, 164, 86), "accent": (255, 240, 220)}),
    ItemDefinition(
        "neon_cap", "NEON CAP", "A glowing cap for a true arcade regular.", COSMETIC, UNCOMMON,
        stackable=False, icon={"shape": "cap", "color": (255, 70, 200), "accent": (80, 240, 255)}),
    ItemDefinition(
        "free_play_coupon", "FREE PLAY COUPON", "One free play on any machine. Not usable yet.",
        ARCADE, COMMON, stackable=True, max_stack=99,
        icon={"shape": "ticket", "color": (90, 255, 150), "accent": (255, 214, 90)}),
    ItemDefinition(
        "retro_badge", "RETRO BADGE", "A shiny badge for fans of the old racing games.", COLLECTIBLE, RARE,
        stackable=False, icon={"shape": "badge", "color": (255, 168, 60), "accent": (255, 72, 72)}),
)

from racing_progression.catalog import PRIZES

_RACING_ITEMS = tuple(ItemDefinition(p.item_id, p.name, f"Permanent {p.kind} unlock.",
    COSMETIC if p.kind in ('paint','decoration') else ARCADE, UNCOMMON,
    stackable=False, icon={"shape":"badge", "color":p.color, "accent":(255,224,90)}) for p in PRIZES)
ITEM_REGISTRY = ItemRegistry(_ITEMS + _RACING_ITEMS)
