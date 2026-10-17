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
    # One line on where the item is used ("EQUIP IT AT THE WARDROBE"), shown when inspected.
    use_hint: str = field(default="", hash=False, compare=False)

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
        stackable=False, icon={"shape": "sticker", "color": (246, 164, 86), "accent": (255, 240, 220)},
        use_hint="SHOW IT IN HOME'S COLLECTION"),
    ItemDefinition(
        "neon_cap", "NEON CAP", "A glowing cap for a true arcade regular.", COSMETIC, UNCOMMON,
        stackable=False, icon={"shape": "cap", "color": (255, 70, 200), "accent": (80, 240, 255)},
        use_hint="WEAR IT AT THE WARDROBE IN HOME"),
    ItemDefinition(
        "free_play_coupon", "FREE PLAY COUPON", "One free play on an arcade cabinet, instead of a token.",
        ARCADE, COMMON, stackable=True, max_stack=99,
        icon={"shape": "ticket", "color": (90, 255, 150), "accent": (255, 214, 90)},
        use_hint="USED AT ARCADE CABINETS"),
    ItemDefinition(
        "retro_badge", "RETRO BADGE", "A shiny badge for fans of the old racing games.", COLLECTIBLE, RARE,
        stackable=False, icon={"shape": "badge", "color": (255, 168, 60), "accent": (255, 72, 72)},
        use_hint="SHOW IT IN HOME'S COLLECTION"),
)

# ---- Prize Counter goods. Decorations that the racing counter already sold keep
# their racing_decoration_* ids (so old saves and both shops agree); the rest are
# decor_*. Cosmetic ids are what the wardrobe equips (see cosmetics.py).
_PINK, _CYAN, _GOLD, _GREEN, _VIOLET = (255, 110, 190), (90, 240, 255), (255, 214, 90), (90, 255, 150), (170, 120, 255)
_DECOR_USE = "PLACE IT IN DECORATION MODE AT HOME"
_WARDROBE_USE = "WEAR IT AT THE WARDROBE IN HOME"
_COLLECT_USE = "SHOW IT IN HOME'S COLLECTION"


def _item(item_id, name, text, category, rarity, shape, color, accent, hint, stackable=False):
    return ItemDefinition(item_id, name, text, category, rarity, stackable=stackable,
                          icon={"shape": shape, "color": color, "accent": accent}, use_hint=hint)


_SHOP_ITEMS = (
    _item("decor_table_lamp", "NEON LAMP", "A little lamp that glows on the coffee table.", COSMETIC, UNCOMMON,
          "lamp", _PINK, _GOLD, _DECOR_USE),
    _item("decor_cat_plush", "CAT PLUSH", "A soft plush of the arcade cat.", COSMETIC, UNCOMMON,
          "plush", (246, 164, 86), (255, 240, 220), _DECOR_USE),
    _item("decor_pixel_plant", "PIXEL PLANT", "A leafy plant in a neat square pot.", COSMETIC, COMMON,
          "plant", _GREEN, (200, 120, 80), _DECOR_USE),
    _item("decor_retro_clock", "RETRO CLOCK", "A wall clock with a neon rim.", COSMETIC, UNCOMMON,
          "clock", _CYAN, _PINK, _DECOR_USE),
    _item("decor_table_candle", "CANDLE", "A calm candle for the table.", COSMETIC, COMMON,
          "lamp", _GOLD, (255, 150, 80), _DECOR_USE),
    _item("decor_table_snacks", "SNACK PLATE", "Arcade snacks, always fresh.", COSMETIC, COMMON,
          "plush", _PINK, _GOLD, _DECOR_USE),
    _item("cat_ears", "CAT EARS", "Pointy ears for a feline look.", COSMETIC, UNCOMMON,
          "ears", (246, 164, 86), _PINK, _WARDROBE_USE),
    _item("retro_sunglasses", "RETRO SUNGLASSES", "Dark shades with a neon glint.", COSMETIC, UNCOMMON,
          "glasses", (40, 30, 90), _CYAN, _WARDROBE_USE),
    _item("star_pin", "STAR PIN", "A small gold star for your jacket.", COSMETIC, COMMON,
          "star", _GOLD, (255, 250, 200), _WARDROBE_USE),
    _item("neon_headphones", "NEON HEADPHONES", "Big glowing cups for the arcade soundtrack.", COSMETIC, UNCOMMON,
          "headphones", (255, 70, 200), _CYAN, _WARDROBE_USE),
    _item("pixel_crown", "PIXEL CROWN", "A chunky gold crown fit for a high-score ruler.", COSMETIC, RARE,
          "crown", _GOLD, (255, 70, 110), _WARDROBE_USE),
    _item("glowing_visor", "GLOWING VISOR", "A visor with a cool cyan glow.", COSMETIC, UNCOMMON,
          "visor", (90, 255, 240), (24, 54, 100), _WARDROBE_USE),
    _item("champion_badge", "CHAMPION BADGE", "A badge for true arcade champions.", COSMETIC, RARE,
          "medal", _GOLD, (255, 70, 110), _WARDROBE_USE),
    _item("star_hair_clip", "STAR HAIR CLIP", "A tiny gold star for your hair.", COSMETIC, COMMON,
          "clip", _GOLD, (255, 250, 200), _WARDROBE_USE),
    _item("cat_tail", "CAT TAIL", "A swishy orange tail to match the cat ears.", COSMETIC, UNCOMMON,
          "tail", (246, 164, 86), (255, 240, 220), _WARDROBE_USE),
    _item("rainbow_jacket", "RAINBOW JACKET", "A jacket striped in every neon colour.", COSMETIC, EPIC,
          "jacket", (255, 160, 60), (80, 170, 255), _WARDROBE_USE),
    _item("palette_sunset", "SUNSET COLORS", "A warm orange and pink outfit.", COSMETIC, COMMON,
          "swatch", (255, 150, 70), (255, 100, 160), _WARDROBE_USE),
    _item("palette_mint", "MINT COLORS", "A cool green and white outfit.", COSMETIC, COMMON,
          "swatch", (90, 230, 170), (230, 255, 245), _WARDROBE_USE),
    _item("palette_grape", "GRAPE COLORS", "A deep purple and gold outfit.", COSMETIC, COMMON,
          "swatch", (140, 90, 230), _GOLD, _WARDROBE_USE),
    _item("palette_cherry", "CHERRY COLORS", "A bold red and cream outfit.", COSMETIC, COMMON,
          "swatch", (235, 60, 90), (255, 235, 220), _WARDROBE_USE),
    _item("arcade_trophy", "ARCADE TROPHY", "A golden cup for a proven champion.", COLLECTIBLE, RARE,
          "trophy", _GOLD, (255, 250, 200), _COLLECT_USE),
    _item("golden_token", "GOLDEN TOKEN", "A shiny token that is too nice to spend.", COLLECTIBLE, UNCOMMON,
          "coin", _GOLD, (255, 140, 40), _COLLECT_USE),
    _item("lucky_clover", "LUCKY CLOVER", "A four-leaf clover pressed in glass.", COLLECTIBLE, UNCOMMON,
          "clover", _GREEN, (200, 255, 210), _COLLECT_USE),
    _item("mini_cabinet", "MINI CABINET", "A tiny arcade cabinet that really lights up.", COLLECTIBLE, EPIC,
          "cabinet", _VIOLET, _CYAN, _COLLECT_USE),
)


# ---- CAPSULE goods (CAT CAPSULE / RETRO CAPSULE in Prize Plaza, see capsule.py). Stackable
# collectibles, so a repeat pull is a counted duplicate; they only ever sit in the bag and the
# HOME collection / showcase and change no score, price or payout.
_PINKISH, _LILAC, _SKY, _MINT = (255, 150, 200), (200, 150, 255), (110, 200, 255), (130, 255, 210)
CAPSULE_STACK = 99


def _capsule_item(item_id, name, text, rarity, shape, color, accent):
    return ItemDefinition(item_id, name, text, COLLECTIBLE, rarity, stackable=True, max_stack=CAPSULE_STACK,
                          icon={"shape": shape, "color": color, "accent": accent}, use_hint=_COLLECT_USE)


_CAPSULE_ITEMS = (
    _capsule_item("cat_paw_sticker", "PAW STICKER", "A pink paw print, still a little sticky.", COMMON,
                  "paw", _PINKISH, (255, 240, 250)),
    _capsule_item("cat_bell_charm", "CAT BELL", "Jingles when you look at it.", COMMON,
                  "bell", _GOLD, (255, 250, 200)),
    _capsule_item("cat_fish_badge", "FISH BADGE", "A tiny fish badge. The cat approves.", UNCOMMON,
                  "fish", _SKY, (230, 250, 255)),
    _capsule_item("cat_yarn_ball", "YARN BALL", "A lilac ball of yarn. Do not unroll.", UNCOMMON,
                  "yarn", _LILAC, (255, 240, 255)),
    _capsule_item("cat_mochi_plush", "MOCHI PLUSH", "A palm-sized plush of the shop cat.", RARE,
                  "plush", (255, 240, 235), _PINKISH),
    _capsule_item("cat_champion_cup", "CAT CUP", "A pink cup for the best-behaved cat.", RARE,
                  "trophy", _PINKISH, (255, 250, 230)),
    _capsule_item("retro_pixel_heart", "PIXEL HEART", "An extra life, forever.", COMMON,
                  "heart", (255, 90, 120), (255, 200, 210)),
    _capsule_item("retro_cartridge", "RETRO CARTRIDGE", "A game cartridge. Blow on it for luck.", COMMON,
                  "cartridge", _SKY, _GOLD),
    _capsule_item("retro_mini_joystick", "MINI JOYSTICK", "A joystick that fits in a pocket.", UNCOMMON,
                  "joystick", (60, 90, 200), (255, 70, 90)),
    _capsule_item("retro_star_medal", "STAR MEDAL", "Awarded for pressing start.", UNCOMMON,
                  "medal", _CYAN, _GOLD),
    _capsule_item("retro_silver_cup", "SILVER CUP", "Second place never looked this shiny.", RARE,
                  "trophy", (200, 220, 240), _CYAN),
    _capsule_item("retro_gold_trophy", "GOLD PIXEL TROPHY", "The high-score cup of legend.", EPIC,
                  "trophy", _GOLD, (255, 250, 200)),
)

# ---- NEON VEND-O-MATIC novelty goods (Arcade Floor). Pure fun: using one only plays a little effect
# (novelty.py) and never touches scores, tokens, tickets, movement or any minigame.
NOVELTY_STACK = 9
_NOVELTY_USE = "USE IT FROM THE BAG"


def _novelty(item_id, name, text, rarity, shape, color, accent):
    return ItemDefinition(item_id, name, text, CONSUMABLE, rarity, stackable=True, max_stack=NOVELTY_STACK,
                          icon={"shape": shape, "color": color, "accent": accent}, use_hint=_NOVELTY_USE)


_NOVELTY_ITEMS = (
    _novelty("suspicious_soda", "SUSPICIOUS SODA", "Fizzes more than it should. Burps are guaranteed.",
             COMMON, "soda", (120, 255, 90), (255, 255, 140)),
    _novelty("invisible_sandwich", "INVISIBLE SANDWICH", "Looks like nothing. Tastes like nothing.",
             COMMON, "sandwich", (150, 170, 230), (255, 255, 255)),
    _novelty("pocket_rainbow", "POCKET RAINBOW", "A tiny rainbow, folded for travel.",
             UNCOMMON, "rainbow", (255, 160, 60), (255, 255, 255)),
    _novelty("rubber_duck", "RUBBER DUCK", "Squeaks. That is all it does.",
             UNCOMMON, "duck", (255, 214, 60), (255, 130, 40)),
    _novelty("questionable_battery", "QUESTIONABLE BATTERY", "Powers nothing. Flickers everything.",
             RARE, "battery", (90, 255, 150), (255, 230, 80)),
    _novelty("mystery_can", "MYSTERY CAN", "The label fell off. So did the contents.",
             RARE, "mystery", (150, 110, 255), (255, 214, 90)),
)

from racing_progression.catalog import PRIZES

_RACING_ITEMS = tuple(ItemDefinition(p.item_id, p.name, f"Permanent {p.kind} unlock.",
    COSMETIC if p.kind in ('paint','decoration') else ARCADE, UNCOMMON,
    stackable=False, icon={"shape":"badge", "color":p.color, "accent":(255,224,90)}) for p in PRIZES)
_RACING_DECOR_SHAPES = {"poster_cat": "frame", "rug_teal": "rug", "neon_heart": "star", "bed_blue": "plush",
                        "poster_arcade": "frame", "neon_star": "star"}
_RACING_ITEMS = tuple(
    ItemDefinition(d.id, d.name, d.description, d.category, d.rarity, stackable=False,
                   icon={**d.icon, "shape": _RACING_DECOR_SHAPES[d.id.split("racing_decoration_")[1]]}
                   if d.id.startswith("racing_decoration_") else d.icon,
                   use_hint=_DECOR_USE if d.id.startswith("racing_decoration_") else "")
    for d in _RACING_ITEMS)
ITEM_REGISTRY = ItemRegistry(_ITEMS + _SHOP_ITEMS + _CAPSULE_ITEMS + _NOVELTY_ITEMS + _RACING_ITEMS)
