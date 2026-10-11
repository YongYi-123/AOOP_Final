"""Programmatic pixel art for Starfall Assault: a futuristic fighter, alien drones, a mothership and
glowing energy cores. Sprites are drawn from small character grids (only the left half is written;
it is mirrored) and cached per (name, flash) so nothing is rebuilt per frame."""
import pygame

NAVY = (12, 8, 38)
CYAN, BLUE, VIOLET = (80, 235, 255), (70, 130, 255), (165, 110, 255)
MAGENTA, ORANGE, YELLOW = (255, 100, 200), (255, 160, 60), (255, 226, 100)
WHITE, LIME, STEEL = (245, 242, 255), (130, 255, 150), (118, 128, 200)

# half-sprite rows; '.' is empty, the letters index the sprite's palette
_HALVES = {
    "player": [
        ".........o",
        "........oc",
        "........oa",
        ".......oab",
        ".......oek",
        ".......oek",
        "o.....oaab",
        "oo...oaaab",
        "oaooooaabb",
        "oaaaaaaabo",
        "opaabbaaoo",
        "opo.oabbo.",
        "....oaoof.",
        "....ooo.f.",
    ],
    "scout": [
        "....oooo",
        "...oaccc",
        "..oaaaaa",
        "..oaeeee",
        ".oaaewwe",
        "oaaaaeee",
        "obbbbbbb",
        "oowoowow",
        ".o.oo.oo",
    ],
    "scout_b": [
        "....oooo",
        "...oaccc",
        "..oaaaaa",
        "..oaeeee",
        ".oaaewwe",
        "oaaaaeee",
        "obbbbbbb",
        "oooworwo",
        "..o.oo.o",
    ],
    "dash": [
        ".......o",
        "......oa",
        "......oa",
        ".....oac",
        "o....oaa",
        "oo..oaaa",
        "oao.oaee",
        ".oaoobbe",
        ".oabbbbb",
        "..obbaaa",
        "...oofff",
    ],
    "dash_b": [
        ".......o",
        "......oa",
        "......oa",
        ".....oac",
        "o....oaa",
        "oo..oaaa",
        "oao.oaee",
        ".oaoobbe",
        ".oabbbbb",
        "..obbaaa",
        "...oo.f.",
    ],
    "tank": [
        "....oooooo",
        "...oaaaaaa",
        "..oaaccccc",
        "oaoaabbbbb",
        "oaoakkkkkk",
        "oaoakeeeee",
        "oaoakkkkkk",
        "oaoabbbbbb",
        "oaoaaaaaaa",
        "oaowowowow",
        "...oobooob",
        "....oo.oo.",
    ],
    "tank_b": [
        "....oooooo",
        "...oaaaaaa",
        "..oaaccccc",
        "oaoaabbbbb",
        "oaoakkkkkk",
        "oaokeeeeee",
        "oaoakkkkkk",
        "oaoabbbbbb",
        "oaoaaaaaaa",
        "oaowowowow",
        "...oobooob",
        "....o.oo.o",
    ],
    "boss": [
        "...........................ooo",
        ".........................oooaaa",
        "..................oooooooaaaccc",
        "................ooaaaaaaaaaaaaa",
        "..............ooaaaaaaaccccccaaa",
        ".............oaaaaaaccaaaaaaaaaa",
        "............oaaaaaaaaaaaaaaaaaaa",
        "...........oaaeeeaaeeeaaeeeaaaaa",
        "...........oaaewwaaewwaaewwaaaaa",
        "...ooooooooooaaaaaaaaaaaaaaaaaaa",
        "..oaaaaaaaaaaabbbbbbbbbbbbbbbbbb",
        ".oaabbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "oaabkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
        "oaabkwkwkwkwkwkwkwkwkwkwkwkwkwkw",
        ".oaabbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "..ooooaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "......oobbbbbbbbbbbbbbbbbbbbbbbb",
        ".......ooooooooooooooopoopooooop",
        "...............oo..oo...ooffooff",
    ],
}

_PALETTES = {
    "player": dict(o=NAVY, a=CYAN, b=BLUE, c=WHITE, e=WHITE, k=(40, 70, 190), p=ORANGE, f=ORANGE),
    "scout": dict(o=NAVY, a=VIOLET, b=(100, 70, 200), c=(215, 190, 255), e=LIME, w=WHITE, r=YELLOW),
    "dash": dict(o=NAVY, a=MAGENTA, b=(190, 60, 150), c=WHITE, e=YELLOW, f=ORANGE),
    "tank": dict(o=NAVY, a=STEEL, b=(76, 84, 150), c=(180, 190, 240), k=(34, 26, 80), e=MAGENTA, w=YELLOW),
    "boss": dict(o=NAVY, a=(150, 140, 230), b=(96, 88, 180), c=WHITE, e=CYAN, w=YELLOW, k=(40, 30, 96),
                 p=ORANGE, f=ORANGE),
}
for _name in ("scout_b", "dash_b", "tank_b"):
    _PALETTES[_name] = _PALETTES[_name[:-2]]


def _build(rows, palette):
    half = max(len(r) for r in rows)
    surf = pygame.Surface((half * 2, len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row.ljust(half, ".")):
            color = palette.get(ch)
            if ch != "." and color:
                surf.set_at((x, y), color)
                surf.set_at((half * 2 - 1 - x, y), color)
    return surf


_cache = {}


def sprite(name, flash=False):
    """The Surface for `name` ('player', 'scout', 'scout_b', ...); flash=True gives a white hit flash."""
    key = (name, flash)
    surf = _cache.get(key)
    if surf is None:
        surf = _build(_HALVES[name], _PALETTES[name])
        if name.startswith("dash"):                   # drawn as a dart pointing up; the drones dive down
            surf = pygame.transform.flip(surf, False, True)
        if flash:
            surf = surf.copy()
            surf.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)
        _cache[key] = surf
    return surf


POWER_COLORS = {"rapid": YELLOW, "spread": CYAN, "pierce": MAGENTA, "shield": BLUE, "repair": LIME}


def _glyph(surf, kind, color):
    """The 6x6 symbol inside an energy core."""
    c = (255, 255, 255)
    if kind == "rapid":                               # lightning bolt
        for p in ((4, 1), (3, 2), (2, 3), (3, 3), (4, 3), (3, 4), (2, 5)):
            surf.set_at(p, c)
    elif kind == "spread":                            # three-way fan
        for p in ((4, 1), (4, 2), (4, 3), (2, 2), (3, 3), (6, 2), (5, 3), (4, 5), (4, 4)):
            surf.set_at(p, c)
    elif kind == "pierce":                            # lance through a bar
        for p in ((4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (3, 2), (5, 2), (2, 4), (3, 4), (5, 4), (6, 4)):
            surf.set_at(p, c)
    elif kind == "shield":
        for p in ((2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (2, 2), (6, 2), (2, 3), (6, 3), (3, 4), (5, 4), (4, 5)):
            surf.set_at(p, c)
    else:                                             # repair: plus
        for p in ((4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (2, 3), (3, 3), (5, 3), (6, 3)):
            surf.set_at(p, c)


def power_icon(kind):
    """A 10x10 energy core: a dark capsule with a coloured rim and a white symbol."""
    key = ("power", kind)
    surf = _cache.get(key)
    if surf is None:
        color = POWER_COLORS[kind]
        surf = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(surf, NAVY, (5, 5), 5)
        pygame.draw.circle(surf, color, (5, 5), 5, 1)
        pygame.draw.circle(surf, tuple(v // 3 for v in color), (5, 5), 4)
        _glyph(surf, kind, color)
        surf.set_at((2, 2), WHITE)
        _cache[key] = surf
    return surf


def carrier_glow(tick):
    """The pulsing yellow core ring drawn over a Cargo Drone."""
    key = ("carrier", tick % 4)
    surf = _cache.get(key)
    if surf is None:
        surf = pygame.Surface((9, 9), pygame.SRCALPHA)
        pygame.draw.circle(surf, YELLOW if tick % 4 < 2 else ORANGE, (4, 4), 4, 1)
        surf.set_at((4, 4), WHITE)
        _cache[key] = surf
    return surf
