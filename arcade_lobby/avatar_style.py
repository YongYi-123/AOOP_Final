"""The FREE part of an avatar's look: skin tone, eye style, hair and base outfit colours.

This is character identity, not an unlockable. Every option here is available
to every profile for nothing - the Character Creator offers them before a new
profile enters the hub and the Wardrobe lets the player change them again at
any time. They are kept apart from cosmetics.py on purpose: a cosmetic is an
owned inventory item (bought with Tickets) while a BasicAppearance is just a
choice, saved in the profile as `basic_appearance`.

The first option of every list is the original look, so a profile saved before
this existed (no `basic_appearance`) draws exactly as it always did.
"""
from dataclasses import dataclass, replace

SKIN, EYES, HAIR, HAIR_COLOR, OUTFIT = "skin", "eyes", "hair", "hair_color", "outfit"
FIELDS = (SKIN, EYES, HAIR, HAIR_COLOR, OUTFIT)
FIELD_NAMES = {SKIN: "SKIN", EYES: "EYES", HAIR: "HAIR", HAIR_COLOR: "DYE", OUTFIT: "SHIRT"}


@dataclass(frozen=True)
class Option:
    id: str
    name: str
    value: object = None        # skin: (skin, blush, eye) / hair colour / outfit colours / None


SKIN_TONES = (
    Option("peach", "PEACH", ((250, 214, 180), (255, 140, 170), (30, 20, 50))),
    Option("porcelain", "PORCELAIN", ((255, 232, 212), (255, 150, 176), (30, 20, 50))),
    Option("tan", "TAN", ((228, 176, 128), (240, 120, 130), (30, 20, 50))),
    Option("caramel", "CARAMEL", ((190, 132, 90), (226, 112, 118), (24, 14, 40))),
    Option("brown", "BROWN", ((150, 102, 70), (214, 104, 110), (255, 244, 230))),   # light eyes stay readable
    Option("deep", "DEEP", ((106, 70, 54), (200, 98, 106), (255, 244, 230))),
)
EYE_STYLES = (
    Option("dot", "DOTS"),
    Option("sparkle", "SPARKLE"),
    Option("happy", "HAPPY"),
    Option("sleepy", "SLEEPY"),
    Option("wide", "WIDE"),
)
HAIR_STYLES = (
    Option("short", "SHORT"),
    Option("bob", "BOB"),
    Option("long", "LONG"),
    Option("spiky", "SPIKY"),
)
HAIR_COLORS = (
    Option("midnight", "MIDNIGHT", (70, 50, 110)),
    Option("black", "BLACK", (38, 32, 50)),
    Option("brown", "BROWN", (112, 70, 44)),
    Option("blonde", "BLONDE", (240, 202, 96)),
    Option("ginger", "GINGER", (214, 104, 52)),
    Option("pink", "PINK", (240, 112, 176)),
    Option("sky", "SKY", (84, 140, 240)),
    Option("silver", "SILVER", (200, 204, 224)),
)
# value: shirt, shirt shade, beanie, beanie shade, pom-pom
OUTFIT_COLORS = (
    Option("teal", "TEAL", None),               # keeps the player's own colours (P1 / P2 stay distinct)
    Option("rose", "ROSE", ((255, 122, 172), (214, 82, 132), (80, 220, 235), (50, 160, 190), (255, 244, 170))),
    Option("lemon", "LEMON", ((255, 218, 80), (214, 168, 40), (120, 110, 240), (84, 74, 190), (255, 250, 200))),
    Option("lime", "LIME", ((130, 230, 90), (84, 176, 60), (255, 120, 170), (210, 80, 130), (255, 250, 200))),
    Option("sky", "SKY", ((90, 160, 255), (56, 108, 210), (255, 214, 90), (214, 164, 40), (255, 250, 220))),
    Option("violet", "VIOLET", ((166, 110, 250), (118, 74, 200), (110, 240, 190), (60, 180, 140), (255, 240, 170))),
    Option("snow", "SNOW", ((236, 240, 252), (170, 178, 214), (255, 90, 150), (206, 60, 112), (120, 250, 255))),
    Option("ink", "INK", ((70, 66, 110), (44, 40, 80), (255, 80, 170), (200, 50, 140), (120, 250, 255))),
)

OPTIONS = {SKIN: SKIN_TONES, EYES: EYE_STYLES, HAIR: HAIR_STYLES,
           HAIR_COLOR: HAIR_COLORS, OUTFIT: OUTFIT_COLORS}


def option(field, option_id):
    """The Option for an id, or the field's first (original) option for an unknown id."""
    options = OPTIONS[field]
    return next((o for o in options if o.id == option_id), options[0])


@dataclass(frozen=True)
class BasicAppearance:
    """One choice per field, by option id. All default to the original look."""
    skin: str = SKIN_TONES[0].id
    eyes: str = EYE_STYLES[0].id
    hair: str = HAIR_STYLES[0].id
    hair_color: str = HAIR_COLORS[0].id
    outfit: str = OUTFIT_COLORS[0].id

    def get(self, field):
        return getattr(self, field)

    def with_choice(self, field, option_id):
        """A copy with `field` set; an unknown field or id changes nothing."""
        if field not in OPTIONS or all(o.id != option_id for o in OPTIONS[field]):
            return self
        return replace(self, **{field: option_id})

    def to_dict(self):
        return {f: self.get(f) for f in FIELDS}

    @classmethod
    def from_dict(cls, data):
        """Any missing, mistyped or unknown entry falls back to the original look."""
        data = data if isinstance(data, dict) else {}
        return cls(**{f: option(f, data.get(f)).id for f in FIELDS})


DEFAULT_BASIC = BasicAppearance()


def apply_basic(look, basic):
    """`look` (a player.PlayerLook) with the free choices applied. Its outline and
    UI accent stay, so P1 and P2 can still be told apart."""
    skin, blush, eye = option(SKIN, basic.skin).value
    changes = {"skin": skin, "blush": blush, "eye": eye, "eyes": basic.eyes, "hair_style": basic.hair,
               "hair": option(HAIR_COLOR, basic.hair_color).value}
    colors = option(OUTFIT, basic.outfit).value
    if colors is not None:
        changes.update(zip(("shirt", "shirt_dark", "beanie", "beanie_dark", "pom"), colors))
    return replace(look, **changes)


def random_basic(rng):
    return BasicAppearance(**{f: rng.choice(OPTIONS[f]).id for f in FIELDS})


def swatch_color(field, opt):
    """The colour a swatch of this option shows (None for fields drawn as a face)."""
    if field == SKIN:
        return opt.value[0]
    if field == HAIR_COLOR:
        return opt.value
    if field == OUTFIT:
        return opt.value[0] if opt.value else (80, 220, 235)      # TEAL = the player's own shirt
    return None
