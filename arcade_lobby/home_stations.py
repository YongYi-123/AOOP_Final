"""The three personal stations in HOME's right-hand corner: the WARDROBE (change
the avatar), the DECOR table (decoration mode) and the COLLECTION case (show off
collectibles). Each is a Station: walk up, press E, and the room opens the
matching screen for whoever pressed.
"""
import pygame

from collection import CollectionService
from font import get_font
from gfx import scale_color
from item_icons import item_icon
from item_registry import ITEM_REGISTRY
from settings import Col
from stations import Station

SIZE = (30, 38)
POS_Y = 80
SPOTS = (284, 316, 348)       # x of the WARDROBE, DECOR table and COLLECTION case


def _base(accent, label):
    w, h = SIZE
    s = pygame.Surface(SIZE, pygame.SRCALPHA)
    s.fill(Col.CABINET_SIDE, (0, 6, w, h - 6))
    s.fill(Col.CABINET, (2, 8, w - 4, h - 10))
    s.fill(accent, (0, 6, 1, h - 6))
    s.fill(accent, (w - 1, 6, 1, h - 6))
    s.fill(Col.CABINET, (0, 0, w, 7))
    s.fill(accent, (0, 0, w, 1))
    if label:
        font = get_font()
        s.blit(font.render(label, Col.YELLOW), ((w - font.size(label)[0]) // 2, 1))
    s.fill((10, 6, 20), (0, h - 2, w, 2))
    return s


def _wardrobe_sprite():
    s = _base(Col.MAGENTA, "WEAR")
    mirror = pygame.Rect(4, 10, 22, 22)
    s.fill((16, 12, 40), mirror)
    for i in range(5):                                     # a tall, slightly slanted shine
        s.fill((120, 190, 230), (8 + i, 28 - i * 4, 2, 3))
    pygame.draw.rect(s, scale_color(Col.MAGENTA, 0.9), mirror, 1)
    pygame.draw.circle(s, (255, 214, 90), (21, 22), 1)     # door knob
    s.fill((255, 70, 200), (12, 12, 6, 2))                  # a cap peeking over the mirror
    s.fill((80, 240, 255), (12, 14, 6, 1))
    return s


def _decor_sprite():
    s = _base(Col.CYAN, "DECOR")
    s.fill((16, 12, 40), (4, 10, 22, 14))                  # a little blueprint board
    for x in range(5, 25, 4):
        s.fill((30, 60, 110), (x, 11, 1, 12))
    s.fill((110, 220, 235), (7, 14, 7, 5))                  # tiny framed picture
    s.fill((16, 12, 40), (8, 15, 5, 3))
    s.fill((255, 214, 90), (18, 14, 4, 4))                  # a lamp
    s.fill((255, 110, 190), (6, 21, 16, 1))
    s.fill((60, 46, 100), (4, 26, 22, 5))                   # drawer with tools
    s.fill(Col.CYAN, (13, 28, 4, 1))
    return s


def _collection_sprite():
    w, h = SIZE
    s = _base(Col.YELLOW, None)
    s.fill((255, 214, 90), (12, 2, 6, 3))                  # a gold cup on the header
    s.fill((255, 214, 90), (14, 5, 2, 1))
    s.fill((16, 12, 40), (3, 9, w - 6, 24))                # glass case
    s.fill((60, 44, 100), (3, 21, w - 6, 1))               # shelf
    s.fill((60, 44, 100), (3, 32, w - 6, 1))
    return s


class _HomeStation(Station):
    def __init__(self, sprite, x, neon, accent):
        pos = (x, POS_Y)
        super().__init__(sprite, pos, (x + 1, POS_Y + 30, SIZE[0], 8), neon, accent, 0.25)


class WardrobeStation(_HomeStation):
    prompt_label = "WARDROBE"

    def __init__(self, x=SPOTS[0]):
        super().__init__(_wardrobe_sprite(), x, Col.MAGENTA, Col.CYAN)

    def interact(self, scene):
        scene.open_wardrobe()


class DecorStation(_HomeStation):
    prompt_label = "DECORATE"

    def __init__(self, x=SPOTS[1]):
        super().__init__(_decor_sprite(), x, Col.CYAN, Col.MAGENTA)

    def interact(self, scene):
        scene.open_decoration_mode()


class CollectionStation(_HomeStation):
    """A glass case that shows the home owner's pinned collectibles."""
    prompt_label = "COLLECTION"

    def __init__(self, profile, x=SPOTS[2]):
        super().__init__(_collection_sprite(), x, Col.YELLOW, Col.MAGENTA)
        self.profile = profile
        self.service = CollectionService(profile)

    def interact(self, scene):
        scene.open_collection()

    def draw(self, surf):
        super().draw(surf)
        picks = self.service.displayed()
        x0, y0 = self.pos[0] + 1, self.pos[1] + 1               # the sprite has a 1px outline
        for slot in range(3):
            cell = pygame.Rect(x0 + 4 + slot * 8, y0 + 12, 8, 8)
            if slot < len(picks):
                icon = item_icon(ITEM_REGISTRY.get(picks[slot]))
                small = pygame.transform.scale(icon, (8, 8))
                surf.blit(small, cell)
            else:
                surf.fill((30, 22, 60), (cell.x + 3, cell.y + 3, 2, 2))       # an empty slot
        glint = int(self.time * 14) % 40
        if glint < 14:                                           # a sheen sliding over the glass
            surf.fill((200, 240, 255), (x0 + 4 + glint, y0 + 10, 1, 22))
