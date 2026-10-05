"""Procedural cat sprites. Every cat uses the same poses and frame timing;
a CatLook (fur colours + markings) is the only thing that differs, and each
look's sheet is painted once and cached, so cats sharing a look share frames."""
from dataclasses import dataclass

import pygame

from gfx import outlined

CREAM = (255, 230, 190)
PINK = (255, 150, 180)
EYE = (34, 24, 50)


@dataclass(frozen=True)
class CatLook:
    """Colours and markings of one cat. Optional markings are None when absent."""
    fur: tuple
    shade: tuple                 # legs, tail tip
    belly: tuple = CREAM         # muzzle, chest, paws
    stripes: tuple = None        # tabby stripes + forehead mark
    patch: tuple = None          # big patch on the back
    cap: tuple = None            # patch over the right ear / side of the head
    tail: tuple = None           # tail colour (defaults to the fur)
    eye: tuple = EYE
    lid: tuple = EYE             # closed-eye line
    nose: tuple = PINK
    chonk: int = 0               # 1 = a slightly rounder body


# Tail pixel paths (relative to the left-facing sprite), per pose and wag frame
_STAND_TAILS = (
    ((14, 6), (15, 5), (16, 4), (16, 3), (16, 2)),
    ((14, 6), (15, 5), (16, 5), (17, 4), (17, 3)),
    ((14, 6), (15, 5), (15, 4), (15, 3), (14, 2)),
)
_SIT_TAILS = (
    ((11, 13), (12, 13), (13, 13), (14, 12), (15, 11)),
    ((11, 13), (12, 13), (13, 13), (14, 13), (15, 13)),
    ((11, 13), (12, 13), (13, 12), (14, 11), (14, 10)),
)
_NAP_TAILS = (
    ((16, 12), (16, 13), (15, 14), (14, 14), (13, 14), (12, 14), (11, 14), (10, 14)),
    ((16, 12), (16, 13), (15, 14), (14, 14), (13, 14), (12, 14), (11, 13), (10, 12)),  # flick
)
_LEGS = ((5, 7, 11, 13), (4, 7, 10, 13), (6, 8, 11, 12))


def draw_cat(look, pose, tail=0, eyes="open", legs=0, breathe=0):
    """Paint an 18x15 left-facing cat frame.
    pose: stand, sit or nap. eyes: open, closed or happy (^ ^)."""
    s = pygame.Surface((18, 15), pygame.SRCALPHA)
    fur, c = look.fur, look.chonk

    def px(color, x, y, w=1, h=1):
        s.fill(color, (x, y, w, h))

    if pose == "stand":
        path = _STAND_TAILS[tail]
        for x in _LEGS[legs]:
            px(look.shade, x, 10, 1, 3)
            px(look.belly, x, 12)
        pygame.draw.ellipse(s, fur, (4, 5 - c, 11, 6 + c))
        px(look.belly, 6, 9, 6, 1)
        if look.patch:
            pygame.draw.ellipse(s, look.patch, (9, 5 - c, 5, 3 + c))
        if look.stripes:
            px(look.stripes, 9, 5 - c, 1, 2)
            px(look.stripes, 12, 5 - c, 1, 2)
        hy = 1
    elif pose == "nap":
        # curled-up loaf, head tucked low, gently breathing
        path = _NAP_TAILS[tail]
        pygame.draw.ellipse(s, fur, (3, 7 - breathe - c, 14, 7 + breathe + c))
        if look.patch:
            pygame.draw.ellipse(s, look.patch, (10, 7 - breathe - c, 5, 3 + c))
        if look.stripes:
            px(look.stripes, 9, 7 - breathe, 1, 2)
            px(look.stripes, 12, 7 - breathe, 1, 2)
        px(look.belly, 4, 12, 6, 1)
        hy = 5
        eyes = "closed"
    else:
        path = _SIT_TAILS[tail]
        pygame.draw.ellipse(s, fur, (4 - c, 5 - c, 9 + c, 9 + c))
        if look.patch:
            pygame.draw.ellipse(s, look.patch, (8, 6 - c, 4, 4))
        if look.stripes:
            px(look.stripes, 9, 7, 1, 2)
            px(look.stripes, 11, 8, 1, 2)
        px(look.belly, 4, 8, 3, 4)
        px(fur, 4, 11, 1, 3)
        px(fur, 6, 11, 1, 3)
        px(look.belly, 4, 13)
        px(look.belly, 6, 13)
        hy = 2
    for x, y in path:
        px(look.tail or fur, x, y)
    px(look.shade, *path[-1])

    # head
    pygame.draw.ellipse(s, fur, (0, hy + 1, 8, 6))
    pygame.draw.polygon(s, fur, [(1, hy + 2), (1, hy - 1), (4, hy + 1)])
    pygame.draw.polygon(s, look.cap or fur, [(4, hy + 1), (7, hy - 1), (7, hy + 2)])
    if look.cap:
        px(look.cap, 5, hy + 1, 3, 3)
    px(look.nose, 2, hy + 1)
    px(look.nose, 6, hy + 1)
    if look.stripes:
        px(look.stripes, 3, hy + 1, 2, 1)
    px(look.belly, 0, hy + 5, 3, 1)
    px(look.nose, 0, hy + 4)
    if eyes == "closed":
        px(look.lid, 1, hy + 3, 2, 1)
        px(look.lid, 5, hy + 3, 2, 1)
    elif eyes == "happy":                        # contented ^ ^
        for x in (1, 5):
            px(look.lid, x, hy + 3)
            px(look.lid, x + 1, hy + 2)
    else:
        px(look.eye, 2, hy + 2, 1, 2)
        px(look.eye, 5, hy + 2, 1, 2)
    return s


# animation name -> seconds per frame (shared by every cat)
FRAME_TIMES = {"idle": 0.18, "sit": 0.2, "walk": 0.12, "nap": 0.32, "pet": 0.09}

_SHEETS = {}


def cat_sheet(look):
    """{(anim, side): [frames]} for one look, built once. side: 'left'/'right'."""
    sheet = _SHEETS.get(look)
    if sheet is None:
        idle_tails = (0, 0, 0, 0, 1, 2, 1, 0, 0, 0, 0, 0)
        sit_tails = (0, 0, 1, 2, 1, 0, 0, 0, 0, 0, 1, 2, 1, 0, 0, 0)
        # slow breaths, with one lazy tail flick per cycle
        nap = ((0, 0), (0, 0), (0, 1), (0, 1), (0, 0), (0, 0), (0, 1), (0, 1),
               (0, 0), (1, 0), (0, 0), (0, 1), (0, 1), (0, 0), (0, 0), (0, 1))
        raw = {
            "idle": [draw_cat(look, "stand", t, "closed" if i == 9 else "open")
                     for i, t in enumerate(idle_tails)],
            "sit": [draw_cat(look, "sit", t, "closed" if i in (7, 8) else "open")
                    for i, t in enumerate(sit_tails)],
            "walk": [draw_cat(look, "stand", i % 2, legs=l) for i, l in enumerate((1, 0, 2, 0))],
            "nap": [draw_cat(look, "nap", t, breathe=b) for t, b in nap],
            # being petted: eyes squeezed shut, tail swishing happily
            "pet": [draw_cat(look, "sit", t, "happy") for t in (0, 1, 2, 1)],
        }
        sheet = {}
        for name, frames in raw.items():
            left = [outlined(f) for f in frames]
            sheet[(name, "left")] = left
            sheet[(name, "right")] = [pygame.transform.flip(f, True, False) for f in left]
        _SHEETS[look] = sheet
    return sheet


_HEART = None


def heart_sprite():
    global _HEART
    if _HEART is None:
        s = pygame.Surface((5, 4), pygame.SRCALPHA)
        for y, row in enumerate(("01010", "11111", "01110", "00100")):
            for x, ch in enumerate(row):
                if ch == "1":
                    s.set_at((x, y), (255, 110, 170))
        _HEART = outlined(s)
    return _HEART
