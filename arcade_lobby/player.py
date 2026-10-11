"""The top-down hub character (HubPlayer). Frames are painted procedurally
once per PlayerLook into a small sprite sheet (idle + walk for 4 directions)
and played through an AnimationController.

One class serves every local player: what differs between P1 and P2 is data -
a PlayerLook (clothes / outline colours), a ControlScheme (keys) and the
profile reference - never a subclass. A HubPlayer is the in-world body; the
saved progress it plays for lives in its PlayerProfile.
"""
from dataclasses import dataclass

import pygame

from animation import Animation, AnimatedSprite
from controls import SOLO_CONTROLS
from cosmetics import ACCESSORY, FACE, HAT, PALETTE, apply_palette, resolve_appearance
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


DEFAULT_LOOK = PlayerLook("default")    # the one-player look: exactly the original character
P1_LOOK = PlayerLook("p1", outline=(24, 120, 150), accent=Col.CYAN)
P2_LOOK = PlayerLook("p2", shirt=(255, 168, 70), shirt_dark=(214, 118, 50), beanie=(110, 230, 120),
                     beanie_dark=(60, 170, 90), pom=(255, 244, 150), outline=(150, 70, 20),
                     accent=(255, 168, 70))
LOOKS = {1: (DEFAULT_LOOK,), 2: (P1_LOOK, P2_LOOK)}

FACINGS = ("down", "up", "left", "right")
IDLE_DURATION = 0.4
WALK_DURATION = 0.12


NO_OUTFIT = (None, None, None)      # (hat, face accessory, pin): the default outfit
CAP, CAP_BAND, CAP_DARK = (255, 70, 200), (80, 240, 255), (190, 40, 150)
EAR_INNER, SHADES, SHADES_GLINT, PIN_GOLD = (255, 140, 190), (28, 22, 60), (80, 240, 255), (255, 214, 90)


def _draw_hat(px, hat, facing, b):
    """A hat replaces the beanie: bare hair under it, then the hat itself."""
    px(HAIR, 2, 3 + b, 8, 2)
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
            px(HAIR, tip, 1 + b, 1, 1)
            px(HAIR, tip - (ox >= 5), 2 + b, 2, 1)
            px(HAIR, tip - (ox >= 5) * 2, 3 + b, 3, 1)
            px(EAR_INNER, tip + (1 if ox < 5 else -1), 2 + b, 1, 1)


def _draw_face(px, face, facing, b):
    if face != "retro_sunglasses":
        return
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


def _draw_pin(px, pin, facing, b):
    if pin != "star_pin" or facing == "up":
        return
    x = 7 if facing == "down" else 4
    px(PIN_GOLD, x, 10 + b, 2, 2)
    px((255, 250, 200), x, 10 + b)


def _draw_frame(facing, step=0, bob=0, blink=False, look=DEFAULT_LOOK, outfit=NO_OUTFIT):
    """Paint one 12x18 frame. step: 0 standing, 1/2 left/right foot forward.
    bob: pixels the upper body sinks (walk bounce / idle breathing).
    outfit: (hat, face, pin) cosmetic ids, painted in layers over the body with
    the same bob as the part of the body they sit on."""
    hat, face, pin = outfit
    s = pygame.Surface((12, 18), pygame.SRCALPHA)

    def px(color, x, y, w=1, h=1):
        s.fill(color, (x, y, w, h))

    side = facing in ("left", "right")
    b = bob

    # Legs and shoes stay planted; everything above bobs.
    if side:
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
    px(look.shirt, 3, 9 + b, 6, 5)
    px(look.shirt_dark, 3, 13 + b, 6, 1)
    px(look.beanie, 5, 11 + b, 2, 1)  # little heart logo
    if side:
        swing = (0, -1, 1)[step]
        px(look.shirt_dark, 5 + swing, 10 + b, 2, 3)
        px(SKIN, 5 + swing, 13 + b, 2, 1)
    else:
        arm = (0, 1, -1)[step]
        px(look.shirt_dark, 2, 10 + b + max(0, arm), 1, 3)
        px(look.shirt_dark, 9, 10 + b + max(0, -arm), 1, 3)
        px(SKIN, 2, 13 + b + max(0, arm))
        px(SKIN, 9, 13 + b + max(0, -arm))

    # Head
    eye_h = 1 if blink else 2
    eye_y = 7 if blink else 6
    if facing == "up":
        px(HAIR, 2, 5 + b, 8, 4)
    else:
        px(SKIN, 2, 5 + b, 8, 4)
        if facing == "down":
            px(HAIR, 2, 5 + b, 1, 2)
            px(HAIR, 9, 5 + b, 1, 2)
            px(EYE, 4, eye_y + b, 1, eye_h)
            px(EYE, 7, eye_y + b, 1, eye_h)
            px(BLUSH, 3, 8 + b)
            px(BLUSH, 8, 8 + b)
        else:  # profile facing left
            px(HAIR, 6, 5 + b, 4, 3)
            px(HAIR, 8, 8 + b, 2, 1)
            px(EYE, 3, eye_y + b, 1, eye_h)
            px(BLUSH, 4, 8 + b)

    if hat:
        _draw_hat(px, hat, facing, b)
    else:                           # Beanie with a glowing pom-pom
        px(look.beanie, 2, 1 + b, 8, 3)
        px(look.beanie_dark, 2, 4 + b, 8, 1)
        px(look.pom, 5, 0 + b, 2, 1)
    _draw_face(px, face, facing, b)
    _draw_pin(px, pin, facing, b)

    if facing == "right":
        s = pygame.transform.flip(s, True, False)
    return outlined(s, look.outline)


_SHEETS = {}


def outfit_of(appearance):
    """(hat, face, pin) from a {slot: item id} appearance."""
    return (appearance.get(HAT), appearance.get(FACE), appearance.get(ACCESSORY))


def player_sheet(look=DEFAULT_LOOK, outfit=NO_OUTFIT):
    """{facing: {"idle": [...], "walk": [...]}} built once per (look, outfit) and shared."""
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
    return sheet


def styled_sheet(look, appearance):
    """The sheet for a base look wearing `appearance` (palette recolours the look)."""
    return player_sheet(apply_palette(look, appearance.get(PALETTE)), outfit_of(appearance))


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
        self.look = look                # the base look (P1 / P2 identity colours)
        self.appearance = {}            # cosmetics worn right now ({slot: item id})
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
        if change.field in ("appearance", "inventory"):
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
        return animations

    def set_appearance(self, appearance):
        """Wear `appearance` ({slot: cosmetic id}; {} is the default outfit).
        Only the frames change: position, facing, the running animation and the
        collision box (FEET_W x FEET_H) are untouched."""
        appearance = dict(appearance)
        if appearance == self.appearance:
            return
        self.appearance = appearance
        state, facing_anim = self.anim.name, self.anim.current
        frame, elapsed = facing_anim.current_frame, facing_anim.time
        self.anim.animations = self._animations(styled_sheet(self.look, appearance))
        self.anim.current = self.anim.animations[state]
        self.anim.current.current_frame = frame % len(self.anim.current.frames)
        self.anim.current.time = elapsed

    def refresh_appearance(self):
        """Re-read what the profile owns and has chosen to wear."""
        self.set_appearance(resolve_appearance(self.profile))

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
        if self.moving:
            if dx:
                self.facing = "left" if dx < 0 else "right"
            else:
                self.facing = "up" if dy < 0 else "down"
            length = (dx * dx + dy * dy) ** 0.5
            step = PLAYER_SPEED * dt / length
            self._move_axis(dx * step, 0, solids)
            self._move_axis(0, dy * step, solids)

        state = "walk" if self.moving else "idle"
        self.anim.play(f"{state}_{self.facing}", sync=self.moving and was_moving)
        self.anim.update(dt)
        self.tag_left = max(0.0, self.tag_left - dt)

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
        surf.blit(frame, (int(self.x) - frame.get_width() // 2,
                          int(self.y) - frame.get_height() + 1))

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
