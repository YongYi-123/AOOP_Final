"""The top-down hub character (HubPlayer). Frames are painted procedurally
once per PlayerLook into a small sprite sheet (idle + walk for 4 directions)
and played through an AnimationController.

One class serves every local player: what differs between P1 and P2 is data -
a PlayerLook (clothes / outline colours), a ControlScheme (keys) and the
profile reference - never a subclass. A HubPlayer is the in-world body; the
saved progress it plays for lives in its PlayerProfile.
"""
import math
from dataclasses import dataclass

import pygame

from animation import Animation, AnimatedSprite
from avatar_style import DEFAULT_BASIC, apply_basic
from controls import SOLO_CONTROLS
from cosmetics import (ACCESSORY, CLIP, FACE, HAT, JACKET, PALETTE, TAIL, apply_palette,
                       resolve_appearance)
from cat_sprites import heart_sprite
from font import get_font
from gfx import outlined, soft_shadow
from settings import PLAYER_SPEED, VIEW_W, Col
from ui import PromptBubble

SKIN = (250, 214, 180)
BLUSH = (255, 140, 170)
HAIR = (70, 50, 110)
EYE = (30, 20, 50)
BEANIE = (255, 80, 170)
BEANIE_DARK = (200, 50, 140)
POM = (120, 250, 255)
SHIRT = (80, 220, 235)
SHIRT_DARK = (50, 160, 200)
PANTS = (84, 76, 170)
SHOES = (250, 244, 255)



@dataclass(frozen=True)
class PlayerLook:
    """The colours that tell the local players apart."""
    name: str
    shirt: tuple = SHIRT
    shirt_dark: tuple = SHIRT_DARK
    beanie: tuple = BEANIE
    beanie_dark: tuple = BEANIE_DARK
    pom: tuple = POM
    outline: tuple = Col.OUTLINE        # the 1px line around the sprite
    accent: tuple = Col.CYAN            # UI colour: tag, HUD header
    # the free basic appearance (avatar_style.py); the defaults are the original character
    skin: tuple = SKIN
    blush: tuple = BLUSH
    eye: tuple = EYE
    hair: tuple = HAIR
    hair_style: str = "short"
    eyes: str = "dot"


DEFAULT_LOOK = PlayerLook("default")    # the one-player look: exactly the original character
P1_LOOK = PlayerLook("p1", outline=(24, 120, 150), accent=Col.CYAN)
P2_LOOK = PlayerLook("p2", shirt=(255, 168, 70), shirt_dark=(214, 118, 50), beanie=(110, 230, 120),
                     beanie_dark=(60, 170, 90), pom=(255, 244, 150), outline=(150, 70, 20),
                     accent=(255, 168, 70))
LOOKS = {1: (DEFAULT_LOOK,), 2: (P1_LOOK, P2_LOOK)}

FACINGS = ("down", "up", "left", "right")
IDLE_DURATION = 0.4
WALK_DURATION = 0.12
# Short action poses: name -> (seconds per frame, total seconds or None = until the player moves).
# The pose frames come from the same sheet as walking, so cosmetics stay attached.
ACTIONS = {"press": (0.11, 0.24), "pet": (0.22, 0.7), "cheer": (0.16, 0.9), "wave": (0.17, 1.0),
           "sit": (0.6, None), "equip": (0.1, 0.7)}
EQUIP_SPIN = ("down", "left", "up", "right")     # the outfit-change twirl
EMOTE_TIME = 0.9


NO_OUTFIT = (None,) * 6     # (hat, face, pin, hair clip, tail, jacket): the default outfit
CAP, CAP_BAND, CAP_DARK = (255, 70, 200), (80, 240, 255), (190, 40, 150)
EAR_INNER, SHADES, SHADES_GLINT, PIN_GOLD = (255, 140, 190), (28, 22, 60), (80, 240, 255), (255, 214, 90)
CUP, CUP_GLOW, BAND = (255, 70, 200), (80, 240, 255), (60, 52, 120)
GOLD, GOLD_DARK, GEM = (255, 214, 90), (214, 160, 40), (255, 70, 110)
VISOR_GLOW, VISOR_DARK = (90, 255, 240), (24, 54, 100)
TAIL_FUR, TAIL_DARK, TAIL_TIP = (246, 164, 86), (208, 118, 60), (255, 240, 220)
RAINBOW = ((255, 70, 90), (255, 160, 60), (255, 230, 80), (90, 230, 120), (80, 170, 255))
SLEEVE = (140, 96, 230)
POSES = ("press", "pet", "cheer", "wave", "sit")     # short action poses, see HubPlayer.ACTIONS


def _draw_hat(px, hat, facing, b, hair):
    """A hat replaces the beanie: bare hair under it, then the hat itself."""
    px(hair, 2, 3 + b, 8, 2)
    side = facing in ("left", "right")
    if hat == "neon_cap":
        px(CAP, 3, 1 + b, 6, 1)
        px(CAP, 2, 2 + b, 8, 2)
        px(CAP_BAND, 2, 4 + b, 8, 1)
        px(CAP_BAND, 5, 0 + b, 2, 1)
        if facing == "down":
            px(CAP_DARK, 3, 5 + b, 6, 1)
        elif side:
            px(CAP_DARK, 0, 4 + b, 3, 1)
            px(CAP_DARK, 1, 5 + b, 2, 1)
    elif hat == "cat_ears":
        for ox in ((2, 7) if not side else (3, 6)):
            tip = ox + (0 if ox < 5 else 2)
            px(hair, tip, 1 + b, 1, 1)
            px(hair, tip - (ox >= 5), 2 + b, 2, 1)
            px(hair, tip - (ox >= 5) * 2, 3 + b, 3, 1)
            px(EAR_INNER, tip + (1 if ox < 5 else -1), 2 + b, 1, 1)
    elif hat == "neon_headphones":
        px(BAND, 3, 1 + b, 6, 1)
        px(BAND, 2, 2 + b, 1, 2)
        px(BAND, 9, 2 + b, 1, 2)
        px(CUP_GLOW, 4, 1 + b, 2, 1)
        if side:                                    # one cup on the ear
            px(CUP, 4, 5 + b, 3, 3)
            px(CUP_GLOW, 5, 6 + b)
        else:
            for x in (0, 10):
                px(CUP, x, 4 + b, 2, 4)
                px(CUP_GLOW, x + (x == 0), 5 + b, 1, 2)
    elif hat == "pixel_crown":
        inset = 1 if side else 0
        px(GOLD, 3 + inset, 3 + b, 6 - 2 * inset, 2)
        px(GOLD_DARK, 3 + inset, 4 + b, 6 - 2 * inset, 1)
        for x in (3 + inset, 5, 8 - inset):
            px(GOLD, x, 2 + b)
        px(GOLD, 5, 1 + b, 2, 1)
        if facing != "up":
            px(GEM, 5 - side, 3 + b)
            px((255, 250, 200), 3 + inset, 2 + b)


def _draw_face(px, face, facing, b):
    if face == "retro_sunglasses":
        if facing == "down":
            px(SHADES, 3, 6 + b, 3, 2)
            px(SHADES, 6, 6 + b, 3, 2)
            px(SHADES_GLINT, 3, 6 + b)
            px(SHADES_GLINT, 6, 6 + b)
        elif facing == "up":
            px(SHADES, 2, 6 + b)
            px(SHADES, 9, 6 + b)
        else:
            px(SHADES, 2, 6 + b, 3, 2)
            px(SHADES, 5, 6 + b, 4, 1)
            px(SHADES_GLINT, 2, 6 + b)
    elif face == "glowing_visor":
        if facing == "down":
            px(VISOR_GLOW, 2, 6 + b, 8, 1)          # the eyes show through the dark lower row
            px(VISOR_DARK, 2, 7 + b, 8, 1)
            px((255, 255, 255), 3, 6 + b)
        elif facing == "up":
            px(VISOR_GLOW, 2, 6 + b)
            px(VISOR_GLOW, 9, 6 + b)
        else:
            px(VISOR_GLOW, 2, 6 + b, 4, 1)
            px(VISOR_DARK, 2, 7 + b, 4, 1)
            px(VISOR_GLOW, 6, 6 + b, 3, 1)
            px((255, 255, 255), 2, 6 + b)


def _draw_pin(px, pin, facing, b):
    if facing == "up":
        return
    if pin == "star_pin":
        x = 7 if facing == "down" else 4
        px(PIN_GOLD, x, 10 + b, 2, 2)
        px((255, 250, 200), x, 10 + b)
    elif pin == "champion_badge":
        x = 3 if facing == "down" else 4
        px(GOLD_DARK, x, 10 + b, 3, 3)
        px(GOLD, x, 10 + b, 3, 1)
        px(GEM, x + 1, 11 + b)
        px(GOLD, x + 1, 12 + b)


def _draw_clip(px, clip, facing, b):
    """A star hair clip on the hair at the side of the head."""
    if clip != "star_hair_clip":
        return
    x, y = {"down": (2, 4), "up": (3, 5), "left": (6, 4), "right": (6, 4)}[facing]
    px(GOLD, x, y + b, 2, 2)
    px((255, 250, 200), x, y + b)
    px(GOLD_DARK, x + 1, y + 1 + b)


def _draw_tail(px, tail, facing, b, front):
    """A cat tail: behind the body (drawn first) except from the back, where it
    hangs down over the back (drawn after the torso)."""
    if tail != "cat_tail" or front != (facing == "up"):
        return
    if facing == "up":
        px(TAIL_FUR, 5, 12 + b, 2, 3)
        px(TAIL_DARK, 5, 14 + b, 2, 1)
        px(TAIL_TIP, 5, 15 + b, 2, 1)
    elif facing == "down":
        for x, y in ((8, 13), (9, 12), (10, 11), (10, 10)):
            px(TAIL_FUR, x, y + b)
        px(TAIL_TIP, 10, 9 + b)
    else:
        for x, y in ((8, 13), (9, 12), (10, 11), (10, 10)):
            px(TAIL_FUR, x, y + b)
        px(TAIL_DARK, 9, 13 + b)
        px(TAIL_TIP, 10, 9 + b)


def _draw_eyes(px, look, facing, eye_y, b, blink):
    """Eyes on the front (down) or the near side (left) of the head."""
    style, EYE = look.eyes, look.eye
    xs = (4, 7) if facing == "down" else (3,)
    if blink and style not in ("dot", "sleepy"):
        style = "sleepy"
    for x in xs:
        if style == "dot":
            px(EYE, x, eye_y + b, 1, 2 if not blink else 1)
        elif style == "wide":
            px(EYE, x - (facing == "down"), 6 + b, 2, 2)
        elif style == "sparkle":
            px(EYE, x - (facing == "down"), 6 + b, 2, 2)
            px((255, 255, 255), x - (facing == "down"), 6 + b)
        elif style == "happy":                      # a small ^ arch
            if facing == "down":
                inner, outer = (4, 3) if x == 4 else (7, 8)
                px(EYE, inner, 6 + b)
                px(EYE, outer, 7 + b)
            else:
                px(EYE, x, 7 + b)
                px(EYE, x + 1, 6 + b)
        else:                                       # sleepy: a calm line
            px(EYE, x - (facing == "down"), 7 + b, 2, 1)


def _draw_hair(px, look, facing, b):
    h, s = look.hair, look.hair_style
    if facing == "down":
        rows = {"short": 2, "bob": 4, "long": 5, "spiky": 3}[s]
        px(h, 2, 5 + b, 1, rows)
        px(h, 9, 5 + b, 1, rows)
        if s == "spiky":
            px(h, 1, 7 + b)
            px(h, 10, 7 + b)
    elif facing == "up":
        px(h, 2, 5 + b, 8, 4)
        if s == "bob":
            px(h, 2, 9 + b, 8, 1)
        elif s == "long":
            px(h, 2, 9 + b, 8, 1)
            px(h, 3, 10 + b, 6, 1)
        elif s == "spiky":
            px(h, 1, 7 + b)
            px(h, 10, 7 + b)
    else:                                           # profile facing left
        px(h, 6, 5 + b, 4, 3)
        px(h, 8, 8 + b, 2, 1)
        if s == "bob":
            px(h, 7, 8 + b, 3, 2)
        elif s == "long":
            px(h, 7, 8 + b, 3, 4)
        elif s == "spiky":
            px(h, 10, 6 + b)
            px(h, 10, 8 + b)


def _draw_arms(px, look, facing, step, b, sleeve, pose, pstep):
    side = facing in ("left", "right")
    skin = look.skin
    if pose in ("press", "pet"):
        low = 2 if pose == "pet" else 0
        if side:
            px(sleeve, 3, 11 + b, 3, 2)
            px(skin, 2, 11 + b + low // 2 + pstep, 1, 1)
        elif facing == "up" and pose == "press":    # both hands up on the machine
            for x in (1, 10):
                px(sleeve, x, 8 + b, 1, 3)
                px(skin, x, 7 + b - pstep)
        else:
            px(sleeve, 2, 10 + b, 1, 3)
            px(sleeve, 9, 10 + b, 1, 3)
            px(skin, 3, 12 + b + low // 2 + pstep)
            px(skin, 8, 12 + b + low // 2 + pstep)
    elif pose == "cheer":
        if side:
            px(sleeve, 4, 8 + b, 2, 3)
            px(skin, 3, 7 + b)
        else:
            for x in (1, 10):
                px(sleeve, x, 8 + b, 1, 3)
                px(skin, x, 6 + b + (pstep == 0))
    elif pose == "wave":
        if side:
            px(sleeve, 4, 8 + b, 2, 3)
            px(skin, 3 - pstep, 7 + b)
        else:
            px(sleeve, 2, 10 + b, 1, 3)
            px(skin, 2, 13 + b)
            px(sleeve, 10, 7 + b, 1, 3)
            px(skin, 10 + pstep, 6 + b)
    elif side:
        swing = (0, -1, 1)[step]
        px(sleeve, 5 + swing, 10 + b, 2, 3)
        px(skin, 5 + swing, 13 + b, 2, 1)
    else:
        arm = (0, 1, -1)[step]
        px(sleeve, 2, 10 + b + max(0, arm), 1, 3)
        px(sleeve, 9, 10 + b + max(0, -arm), 1, 3)
        px(skin, 2, 13 + b + max(0, arm))
        px(skin, 9, 13 + b + max(0, -arm))


def _draw_frame(facing, step=0, bob=0, blink=False, look=DEFAULT_LOOK, outfit=NO_OUTFIT,
                pose=None, pstep=0):
    """Paint one 12x18 frame. step: 0 standing, 1/2 left/right foot forward.
    bob: pixels the upper body sinks (walk bounce / idle breathing).
    outfit: (hat, face, pin, clip, tail, jacket) cosmetic ids, painted in layers over the
    body with the same bob as the part of the body they sit on.
    pose: one of POSES (a short action pose; pstep alternates its 2 frames). Every
    layer is drawn through the same code, so cosmetics follow every pose."""
    hat, face, pin, clip, tail, jacket = (tuple(outfit) + (None,) * 6)[:6]
    # A cheering hop is one pixel taller (empty bottom row): bottom-anchored, the sprite rises.
    s = pygame.Surface((12, 19 if pose == "cheer" and pstep else 18), pygame.SRCALPHA)

    def px(color, x, y, w=1, h=1):
        s.fill(color, (x, y, w, h))

    side = facing in ("left", "right")
    b = 2 if pose in ("pet", "sit") else bob

    _draw_tail(px, tail, facing, b, front=False)
    # Legs and shoes stay planted; everything above bobs.
    if pose == "sit":
        px(PANTS, 3, 14, 6, 2)
        px(SHOES, 3, 16, 2, 2)
        px(SHOES, 7, 16, 2, 2)
    elif side:
        if step == 0:
            px(PANTS, 4, 14, 4, 2)
            px(SHOES, 4, 16, 5, 2)
        else:
            front, back = (2, 7) if step == 1 else (7, 2)
            px(PANTS, 3, 14, 6, 2)
            px(SHOES, front, 16, 3, 2)
            px(SHOES, back, 15, 3, 2)
    else:
        px(PANTS, 3, 14, 6, 2)
        px(SHOES, 3, 16 - (step == 1), 2, 2)
        px(SHOES, 7, 16 - (step == 2), 2, 2)

    # Torso (a cyan hoodie) and arms
    px(look.shirt, 3, 9 + b, 6, 5 - (b > 1))
    px(look.shirt_dark, 3, 13 + b - (b > 1), 6, 1)
    px(look.beanie, 5, 11 + b, 2, 1)  # little heart logo
    sleeve = look.shirt_dark
    if jacket == "rainbow_jacket":
        for i, color in enumerate(RAINBOW):
            px(color, 3, 9 + b + i, 6, 1)
        sleeve = SLEEVE
    _draw_arms(px, look, facing, step, b, sleeve, pose, pstep)
    _draw_tail(px, tail, facing, b, front=True)

    # Head
    eye_y = 7 if blink else 6
    if facing == "up":
        px(look.hair, 2, 5 + b, 8, 4)
    else:
        px(look.skin, 2, 5 + b, 8, 4)
        _draw_eyes(px, look, facing, eye_y, b, blink)
        if facing == "down":
            px(look.blush, 3, 8 + b)
            px(look.blush, 8, 8 + b)
        else:
            px(look.blush, 4, 8 + b)
    _draw_hair(px, look, facing, b)

    if hat:
        _draw_hat(px, hat, facing, b, look.hair)
    else:                           # Beanie with a glowing pom-pom
        px(look.beanie, 2, 1 + b, 8, 3)
        px(look.beanie_dark, 2, 4 + b, 8, 1)
        px(look.pom, 5, 0 + b, 2, 1)
    _draw_clip(px, clip, facing, b)
    _draw_face(px, face, facing, b)
    _draw_pin(px, pin, facing, b)

    if facing == "right":
        s = pygame.transform.flip(s, True, False)
    return outlined(s, look.outline)


_SHEETS = {}


def outfit_of(appearance):
    """(hat, face, pin, clip, tail, jacket) from a {slot: item id} appearance."""
    return (appearance.get(HAT), appearance.get(FACE), appearance.get(ACCESSORY),
            appearance.get(CLIP), appearance.get(TAIL), appearance.get(JACKET))


def player_sheet(look=DEFAULT_LOOK, outfit=NO_OUTFIT):
    """{facing: {"idle": [...], "walk": [...], <pose>: [2 frames]}} built once per
    (look, outfit) and shared."""
    key = (look, outfit)
    sheet = _SHEETS.get(key)
    if sheet is None:
        sheet = _SHEETS[key] = {}
        for f in FACINGS:
            n = _draw_frame(f, look=look, outfit=outfit)
            breathe = _draw_frame(f, bob=1, look=look, outfit=outfit)
            blink = _draw_frame(f, blink=True, look=look, outfit=outfit) if f != "up" else n
            sheet[f] = {
                "idle": [n, n, breathe, breathe, n, n, breathe, blink],
                "walk": [_draw_frame(f, 1, 1, look=look, outfit=outfit), _draw_frame(f, 0, 0, look=look, outfit=outfit),
                         _draw_frame(f, 2, 1, look=look, outfit=outfit), _draw_frame(f, 0, 0, look=look, outfit=outfit)],
            }
            for pose in POSES:
                sheet[f][pose] = [_draw_frame(f, look=look, outfit=outfit, pose=pose, pstep=i) for i in (0, 1)]
    return sheet


def styled_sheet(look, appearance, basic=None):
    """The sheet for a look wearing `appearance` (palette recolours the look). Pass
    `basic` (a BasicAppearance) to apply the free choices (skin, eyes, hair, shirt
    colour) first; a look that already has them applied needs none."""
    if basic is not None:
        look = apply_basic(look, basic)
    look = apply_palette(look, appearance.get(PALETTE))
    return player_sheet(look, outfit_of(appearance))


_SPARKLE = []


def sparkle_sprite():
    """A 5x5 gold plus-shaped twinkle (painted once)."""
    if not _SPARKLE:
        sp = pygame.Surface((5, 5), pygame.SRCALPHA)
        sp.fill((255, 214, 90), (2, 0, 1, 5))
        sp.fill((255, 214, 90), (0, 2, 5, 1))
        sp.fill((255, 255, 255), (2, 2, 1, 1))
        _SPARKLE.append(sp)
    return _SPARKLE[0]


class HubPlayer(AnimatedSprite):
    FEET_W, FEET_H = 10, 5
    TAG_TIME = 3.0          # seconds the P1 / P2 marker shows after arriving

    def __init__(self, pos, controls=SOLO_CONTROLS, profile=None, look=DEFAULT_LOOK, label=""):
        super().__init__(self._animations(player_sheet(look)), "idle_up")
        self.x, self.y = float(pos[0]), float(pos[1])  # centre-bottom of feet
        self.facing = "up"
        self.moving = False
        self.shadow = soft_shadow(12, 5)
        self.controls = controls        # which keys drive this body
        self.profile = profile          # whose progress it plays for (HubPlayer does not own it)
        self.base_look = look           # the P1 / P2 identity colours ...
        self.look = look                # ... plus the profile's free choices (skin, eyes, hair, shirt)
        self.appearance = {}            # cosmetics worn right now ({slot: item id})
        self.action = None              # a short pose (ACTIONS) or "sit"; None = walking / idle
        self.action_time = 0.0
        self.seat = None                # (x, y) feet position drawn while sitting; collision is unchanged
        self.emote = None               # (kind, seconds left): a heart / sparkle beside the head
        self.label = label              # "P1" / "P2"; empty in a one-player session
        self.tag_left = 0.0
        self.tag_note = ""              # e.g. "GUEST" while visiting P1's home
        # per-player interaction state, used by the room the player stands in
        self.held = []                  # movement keys currently held, in press order
        self.nearby = None              # machine / station in reach
        self.nearby_cat = None
        self.activating = None          # (target, time left) while the E-flash plays
        self.prompt = PromptBubble(key=controls.interact_hint or "E", tag=label,
                                   accent=look.accent if label else None)   # P1 / P2 look different
        if profile is not None:         # cosmetics follow the profile: owned + worn items
            self.refresh_appearance()
            profile.subscribe(self._on_profile_change)

    def _on_profile_change(self, change):
        if change.field in ("appearance", "inventory", "basic_appearance"):
            self.refresh_appearance()

    def detach(self):
        """Stop following the profile (the avatar is being discarded)."""
        if self.profile is not None:
            self.profile.unsubscribe(self._on_profile_change)

    @staticmethod
    def _animations(sheet):
        animations = {}
        for f in FACINGS:
            animations[f"idle_{f}"] = Animation(sheet[f]["idle"], IDLE_DURATION)
            animations[f"walk_{f}"] = Animation(sheet[f]["walk"], WALK_DURATION)
            for pose in POSES:
                animations[f"{pose}_{f}"] = Animation(sheet[f][pose], ACTIONS[pose][0])
        return animations

    def _rebuild(self, appearance, look):
        """Swap in frames for `look` + `appearance`. Only the frames change: position,
        facing, the running animation and the collision box (FEET_W x FEET_H) are untouched."""
        self.appearance, self.look = dict(appearance), look
        state, current = self.anim.name, self.anim.current
        frame, elapsed = current.current_frame, current.time
        self.anim.animations = self._animations(styled_sheet(look, self.appearance))
        self.anim.current = self.anim.animations[state]
        self.anim.current.current_frame = frame % len(self.anim.current.frames)
        self.anim.current.time = elapsed

    def set_appearance(self, appearance, look=None):
        """Wear `appearance` ({slot: cosmetic id}; {} is the default outfit)."""
        appearance = dict(appearance)
        look = look or self.look
        if appearance != self.appearance or look != self.look:
            self._rebuild(appearance, look)

    def refresh_appearance(self):
        """Re-read what the profile owns and has chosen to wear, and its free look."""
        basic = self.profile.basic_appearance if self.profile is not None else DEFAULT_BASIC
        self.set_appearance(resolve_appearance(self.profile), apply_basic(self.base_look, basic))

    # ------------------------------------------------------------ actions
    @property
    def sitting(self):
        return self.action == "sit"

    def play_action(self, name, facing=None, emote=None):
        """Start a short action pose (ACTIONS). It ends by itself, or at once when the
        player moves; starting another replaces it."""
        if name not in ACTIONS:
            raise ValueError(f"unknown action {name!r}")
        if facing in FACINGS:
            self.facing = facing
        self.action, self.action_time = name, 0.0
        if emote:
            self.emote = (emote, EMOTE_TIME)
        self._show_action_frame()

    def stop_action(self):
        """Back to walking / idle (standing up if sitting)."""
        if self.action is not None:
            self.action, self.seat = None, None
            self.anim.play(f"idle_{self.facing}")

    def sit(self, seat, facing="down"):
        """Sit at `seat` (feet x, y of the drawing); the body's real position stays put."""
        self.seat = seat
        self.play_action("sit", facing)

    def _show_action_frame(self):
        if self.action == "equip":              # a twirl in place: handled in update()
            self.anim.play(f"idle_{self._equip_facing()}")
        else:
            self.anim.play(f"{self.action}_{self.facing}")

    def _equip_facing(self):
        step = ACTIONS["equip"][0]
        return EQUIP_SPIN[int(self.action_time / step) % 4]

    @property
    def number(self):
        """1 for P1 (and for a lone player), 2 for P2."""
        return int(self.label[1:]) if self.label else 1

    @property
    def direction(self):
        return self.controls.direction(self.held)

    def show_tag(self, seconds=TAG_TIME):
        self.tag_left = seconds if self.label else 0.0

    @property
    def feet(self):
        return pygame.Rect(int(self.x) - self.FEET_W // 2, int(self.y) - self.FEET_H,
                           self.FEET_W, self.FEET_H)

    @property
    def sort_y(self):
        return self.y

    def stop(self):
        self.moving = False
        self.anim.play(f"idle_{self.facing}")

    def update(self, dt, direction, solids):
        dx, dy = direction
        was_moving = self.moving
        self.moving = bool(dx or dy)
        if self.moving and self.action is not None:
            self.stop_action()          # walking always wins: no input is ever swallowed by a pose
            was_moving = False
        if self.moving:
            if dx:
                self.facing = "left" if dx < 0 else "right"
            else:
                self.facing = "up" if dy < 0 else "down"
            length = (dx * dx + dy * dy) ** 0.5
            step = PLAYER_SPEED * dt / length
            self._move_axis(dx * step, 0, solids)
            self._move_axis(0, dy * step, solids)

        if self.action is not None:
            self._update_action(dt)
        else:
            state = "walk" if self.moving else "idle"
            self.anim.play(f"{state}_{self.facing}", sync=self.moving and was_moving)
            self.anim.update(dt)
        self.tag_left = max(0.0, self.tag_left - dt)
        if self.emote is not None:
            kind, left = self.emote
            self.emote = (kind, left - dt) if left - dt > 0 else None

    def _update_action(self, dt):
        self.action_time += dt
        total = ACTIONS[self.action][1]
        if total is not None and self.action_time >= total:
            self.stop_action()
            return
        self._show_action_frame()
        self.anim.update(dt)

    def _move_axis(self, dx, dy, solids):
        self.x += dx
        self.y += dy
        half = self.FEET_W // 2
        for solid in solids:
            if not self.feet.colliderect(solid):
                continue
            if dx > 0:
                self.x = solid.left - half
            elif dx < 0:
                self.x = solid.right + half
            elif dy > 0:
                self.y = solid.top
            elif dy < 0:
                self.y = solid.bottom + self.FEET_H

    def draw_under(self, surf):
        surf.blit(self.shadow, (int(self.x) - 6, int(self.y) - 3))

    def draw(self, surf):
        frame = self.image
        x, y = self.seat if self.sitting and self.seat else (self.x, self.y)
        surf.blit(frame, (int(x) - frame.get_width() // 2, int(y) - frame.get_height() + 1))
        if self.action == "equip":
            self._draw_sparkles(surf, x, y)
        if self.emote is not None:
            self._draw_emote(surf, x, y)

    def _draw_sparkles(self, surf, x, y):
        """Four little stars circling the avatar while the outfit changes."""
        k = self.action_time / ACTIONS["equip"][1]
        for i in range(4):
            angle = k * 9 + i * 1.5708
            px_ = int(x + math.cos(angle) * 9)
            py_ = int(y - 9 + math.sin(angle) * 8)
            surf.blit(sparkle_sprite(), (px_ - 2, py_ - 2))

    def _draw_emote(self, surf, x, y):
        """A heart / sparkle drifting up beside the head (never over the prompt bubble above it)."""
        kind, left = self.emote
        rise = int((1 - left / EMOTE_TIME) * 7)
        sprite = heart_sprite() if kind == "heart" else sparkle_sprite()
        surf.blit(sprite, (int(x) + 6, int(y) - self.image.get_height() + 2 - rise))

    def draw_tag(self, surf):
        """The brief P1 / P2 marker above the head."""
        if self.tag_left <= 0 or not self.label:
            return
        font = get_font()
        text = font.render_glow(f"{self.label} {self.tag_note}".strip(), Col.TEXT, self.look.accent)
        k = min(1.0, self.tag_left / 0.5)
        text.set_alpha(int(255 * k))
        top = int(self.y) - self.image.get_height() - 3
        rect = text.get_rect(midbottom=(int(self.x), top))
        rect.clamp_ip(pygame.Rect(2, 2, VIEW_W - 4, 400))
        surf.blit(text, rect)
        arrow = pygame.Surface((5, 3), pygame.SRCALPHA)
        for i in range(3):
            arrow.fill((*self.look.accent, int(255 * k)), (i, i, 5 - 2 * i, 1))
        surf.blit(arrow, arrow.get_rect(midtop=(int(self.x), rect.bottom)))


Player = HubPlayer      # the original name
