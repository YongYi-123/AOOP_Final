"""The top-down player character. Frames are painted procedurally once into a
small sprite sheet (idle + walk for 4 directions) and played through an
AnimationController."""
import pygame

from animation import Animation, AnimatedSprite
from gfx import outlined, soft_shadow
from settings import PLAYER_SPEED

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

FACINGS = ("down", "up", "left", "right")
IDLE_DURATION = 0.4
WALK_DURATION = 0.12


def _draw_frame(facing, step=0, bob=0, blink=False):
    """Paint one 12x18 frame. step: 0 standing, 1/2 left/right foot forward.
    bob: pixels the upper body sinks (walk bounce / idle breathing)."""
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
    px(SHIRT, 3, 9 + b, 6, 5)
    px(SHIRT_DARK, 3, 13 + b, 6, 1)
    px(BEANIE, 5, 11 + b, 2, 1)  # little heart logo
    if side:
        swing = (0, -1, 1)[step]
        px(SHIRT_DARK, 5 + swing, 10 + b, 2, 3)
        px(SKIN, 5 + swing, 13 + b, 2, 1)
    else:
        arm = (0, 1, -1)[step]
        px(SHIRT_DARK, 2, 10 + b + max(0, arm), 1, 3)
        px(SHIRT_DARK, 9, 10 + b + max(0, -arm), 1, 3)
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

    # Beanie with a glowing pom-pom
    px(BEANIE, 2, 1 + b, 8, 3)
    px(BEANIE_DARK, 2, 4 + b, 8, 1)
    px(POM, 5, 0 + b, 2, 1)

    if facing == "right":
        s = pygame.transform.flip(s, True, False)
    return outlined(s)


_SHEET = None


def player_sheet():
    """{facing: {"idle": [...], "walk": [...]}} built once and shared."""
    global _SHEET
    if _SHEET is None:
        _SHEET = {}
        for f in FACINGS:
            n = _draw_frame(f)
            breathe = _draw_frame(f, bob=1)
            blink = _draw_frame(f, blink=True) if f != "up" else n
            _SHEET[f] = {
                "idle": [n, n, breathe, breathe, n, n, breathe, blink],
                "walk": [_draw_frame(f, 1, 1), _draw_frame(f, 0, 0),
                         _draw_frame(f, 2, 1), _draw_frame(f, 0, 0)],
            }
    return _SHEET


class Player(AnimatedSprite):
    FEET_W, FEET_H = 10, 5

    def __init__(self, pos):
        sheet = player_sheet()
        animations = {}
        for f in FACINGS:
            animations[f"idle_{f}"] = Animation(sheet[f]["idle"], IDLE_DURATION)
            animations[f"walk_{f}"] = Animation(sheet[f]["walk"], WALK_DURATION)
        super().__init__(animations, "idle_up")
        self.x, self.y = float(pos[0]), float(pos[1])  # centre-bottom of feet
        self.facing = "up"
        self.moving = False
        self.shadow = soft_shadow(12, 5)

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
