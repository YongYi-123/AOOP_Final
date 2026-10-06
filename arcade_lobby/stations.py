"""Interactable furniture that is not a minigame cabinet: the daily challenge
board and the Lucky Corner machines. A Station is a Prop (so rooms depth-sort,
collide with and light it like any furniture) that the player can walk up to
and press E on; the scene calls `interact(scene)` once the flash has played."""
import math

import pygame

from font import get_font
from gfx import neon_rect_glow, outlined, scale_color, shade
from high_low import HighLowGame
from lucky_wheel import LuckyWheelGame
from room import Prop, make_prize_counter
from settings import INTERACT_FLASH, Col


class Station(Prop):
    """A prop with an [E] prompt. Subclasses supply the sprite and interact()."""
    prompt_label = "USE"
    REACH = (26, 24)        # how far beyond its footprint the prompt appears

    def __init__(self, sprite, pos, footprint, neon, accent, glow_strength=0.3):
        x, y = pos
        w, h = sprite.get_size()
        glow = neon_rect_glow(w, h, neon, 7, glow_strength)
        super().__init__(outlined(sprite), (x - 1, y - 1), footprint, glow, (x - 7, y - 7))
        self.neon, self.accent = neon, accent
        self.rect = pygame.Rect(x, y, w, h)
        self.zone = self.footprint.inflate(*self.REACH)
        self.highlighted = outlined(sprite, shade(accent, 0.5))
        self.highlight = False
        self.flash_time = 0.0
        self.time = 0.0

    def update(self, dt):
        self.time += dt
        self.flash_time = max(0.0, self.flash_time - dt)

    def activate(self):
        """Brief ring when the player presses E."""
        self.flash_time = INTERACT_FLASH

    def interact(self, scene):
        raise NotImplementedError

    def draw(self, surf):
        surf.blit(self.highlighted if self.highlight else self.sprite, self.pos)
        if self.flash_time > 0:
            k = self.flash_time / INTERACT_FLASH
            radius = int(6 + (1 - k) * 26)
            center = self.rect.center
            pygame.draw.circle(surf, shade(self.accent, 0.4), center, radius, 1)
            pygame.draw.circle(surf, self.neon, center, max(1, radius - 4), 1)


# ----------------------------------------------------------------- daily board
BOARD_SIZE = (30, 40)


def _board_sprite():
    s = pygame.Surface(BOARD_SIZE, pygame.SRCALPHA)
    w, h = BOARD_SIZE
    s.fill(Col.CABINET_SIDE, (0, 6, w, h - 6))
    s.fill(Col.CABINET, (2, 6, w - 4, h - 6))
    s.fill(Col.CYAN, (0, 6, 1, h - 6))
    s.fill(Col.CYAN, (w - 1, 6, 1, h - 6))
    s.fill(Col.CABINET, (0, 0, w, 7))                      # header
    s.fill(Col.CYAN, (0, 0, w, 1))
    s.blit(get_font().render("DAILY", Col.YELLOW), ((w - get_font().size("DAILY")[0]) // 2, 1))
    s.fill((6, 4, 14), (3, 9, w - 6, 20))                   # screen bezel
    pygame.draw.rect(s, scale_color(Col.CYAN, 0.55), (3, 9, w - 6, 20), 1)
    s.fill((46, 34, 80), (2, 31, w - 4, 3))                 # keyboard ledge
    s.fill(Col.MAGENTA, (4, 32, 2, 1))
    s.fill(Col.YELLOW, (8, 32, 2, 1))
    s.fill((10, 6, 20), (0, h - 2, w, 2))
    return s


class DailyBoard(Station):
    """The notice-board terminal. It is world furniture shared by everyone in
    the room, so it shows nothing about any one profile: a generic checklist
    that ticks itself in a loop. Whoever uses it sees their own progress in
    the panel that opens (scene.open_task_panel)."""
    prompt_label = "DAILY CHALLENGES"

    def __init__(self, pos, profile=None):      # `profile` is accepted for old callers and ignored
        x, y = pos
        super().__init__(_board_sprite(), pos, (x + 1, y + 32, 28, 8), Col.CYAN, Col.YELLOW, 0.3)

    def interact(self, scene):
        scene.open_task_panel()

    def draw(self, surf):
        super().draw(surf)
        x, y = self.rect.topleft
        step = int(self.time * 1.2) % 4                # 0..3: how many rows are ticked right now
        for i in range(3):
            row = y + 12 + i * 6
            ticked = i < step
            surf.fill(Col.GREEN if ticked else Col.TEXT_MUTED, (x + 6, row, 3, 3))
            surf.fill(scale_color(Col.CYAN, 0.7), (x + 12, row + 1, 13, 1))


# ---------------------------------------------------------------- lucky corner
LUCKY_SIZE = (28, 40)


def _lucky_sprite(label, neon, accent):
    s = pygame.Surface(LUCKY_SIZE, pygame.SRCALPHA)
    w, h = LUCKY_SIZE
    s.fill(Col.CABINET_SIDE, (0, 8, w, h - 8))
    s.fill(Col.CABINET, (3, 8, w - 6, h - 8))
    s.fill(neon, (0, 8, 1, h - 8))
    s.fill(neon, (w - 1, 8, 1, h - 8))
    s.fill(Col.CABINET, (0, 0, w, 9))                       # marquee
    s.fill(neon, (0, 0, w, 1))
    tw = get_font().size(label)[0]
    s.blit(get_font().render(label, Col.YELLOW), ((w - tw) // 2, 2))
    s.fill((6, 4, 14), (4, 10, w - 8, 14))                  # screen bezel
    pygame.draw.rect(s, scale_color(accent, 0.55), (4, 10, w - 8, 14), 1)
    s.fill((46, 34, 80), (2, 26, w - 4, 5))                 # control panel
    for i, c in enumerate((Col.YELLOW, Col.CYAN, Col.MAGENTA)):
        pygame.draw.circle(s, c, (8 + i * 6, 28), 1)
    s.fill((18, 12, 34), (6, 33, w - 12, 5))                # token slot
    s.fill(accent, (12, 35, 4, 1))
    s.fill((10, 6, 20), (0, h - 2, w, 2))
    return s


class ChanceStation(Station):
    """A Lucky Corner machine. `game_cls` builds a fresh ChanceGame for each
    round; the station knows nothing about the rules."""
    prompt_label = "PLAY"

    def __init__(self, pos, game_cls, label, neon, accent):
        x, y = pos
        super().__init__(_lucky_sprite(label, neon, accent), pos, (x + 1, y + 28, 28, 12),
                         neon, accent, 0.4)
        self.game_cls = game_cls
        self.prompt_label = f"PLAY {label}"

    def interact(self, scene):
        scene.open_chance_game(self.game_cls)

    def draw(self, surf):
        super().draw(surf)
        x, y = self.rect.topleft
        for i in range(5):                                  # chase lights on the marquee
            lit = int(self.time * 6) % 5 == i
            surf.fill(Col.YELLOW if lit else self.neon, (x + 3 + i * 5, y + 7, 2, 1))
        screen = pygame.Rect(x + 5, y + 11, self.rect.w - 10, 12)
        hue = int(self.time * 4) % 3
        surf.fill(scale_color((Col.MAGENTA, Col.CYAN, Col.YELLOW)[hue], 0.5), screen.inflate(-4, -4))


class LuckySign(Prop):
    """The glowing LUCKY CORNER plaque above the machines. Decoration only:
    it is not solid and has no prompt."""
    solid = False

    def __init__(self, pos):
        text = "LUCKY CORNER"
        img = get_font().render_glow(text, Col.YELLOW, scale_color(Col.MAGENTA, 0.8))
        w, h = img.get_width() + 8, img.get_height() + 4
        plate = pygame.Surface((w, h), pygame.SRCALPHA)
        plate.fill((18, 8, 40, 235))
        pygame.draw.rect(plate, Col.MAGENTA, plate.get_rect(), 1)
        plate.blit(img, (4, 2))
        x, y = pos
        super().__init__(plate, pos, (x, y, w, 1),
                         neon_rect_glow(w, h, Col.MAGENTA, 6, 0.3), (x - 6, y - 6))
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def draw_under(self, surf):
        pass

    def draw(self, surf):
        super().draw(surf)
        for i in range(0, self.sprite.get_width() - 2, 6):   # blinking bulbs along the top
            if int(self.time * 3 + i / 6) % 2:
                surf.fill(Col.YELLOW, (self.pos[0] + 2 + i, self.pos[1] - 1, 2, 1))


class SoonStation(Prop):
    """A switched-off Lucky Corner bay waiting for a future chance game."""

    def __init__(self, pos):
        x, y = pos
        dim = (74, 62, 116)
        sprite = _lucky_sprite("SOON", dim, dim)
        sprite.fill((10, 8, 22), (5, 11, LUCKY_SIZE[0] - 10, 12))
        super().__init__(outlined(sprite), (x - 1, y - 1), (x + 1, y + 28, 28, 12))
        self.rect = pygame.Rect(x, y, *LUCKY_SIZE)


class PrizeCounter(Station):
    """The prize counter in the PRIZE PLAZA. Only a placeholder for now: it
    opens a 'coming soon' notice (the shop comes later)."""
    prompt_label = "PRIZE COUNTER"

    def __init__(self, pos):
        x, y = pos
        super().__init__(make_prize_counter(), pos, (x + 1, y + 20, 80, 16),
                         Col.YELLOW, Col.MAGENTA, 0.25)

    def interact(self, scene):
        scene.open_prize_counter()


def build_daily_board(profile, pos):
    """The daily challenge board that lives in HOME."""
    return DailyBoard(pos, profile)


def build_lucky_corner(x, y, spacing=40):
    """The Lucky Corner in the PRIZE PLAZA: its sign, the two chance games and
    a dark bay for the next one. (x, y) is the top-left of the first machine."""
    return [
        LuckySign((x - 1, y - 15)),
        ChanceStation((x, y), LuckyWheelGame, "SPIN", (255, 70, 200), (255, 214, 90)),
        ChanceStation((x + spacing, y), HighLowGame, "HI-LO", (80, 240, 255), (90, 255, 150)),
        SoonStation((x + spacing * 2, y)),
    ]
