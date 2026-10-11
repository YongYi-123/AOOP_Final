"""CarSelectMenu: cursor state and drawing for the CAR SELECT screen (no physics in here)."""
import pygame
import assets
from assets import YELLOW, CYAN, RED, GREEN
from hud import PINK
from menu_layout import fit_font, panel
from car_specs import BAR_SEGMENTS, player_livery

STAGE = pygame.Rect(40, 126, 400, 252)          # the car showcase (left) ...
STATS = pygame.Rect(456, 126, 304, 252)         # ... and its five stat bars (right)
NAMEPLATE = pygame.Rect(40, 392, 720, 112)      # name, tagline, position dots, lock status
STAGE_CX = STAGE.centerx
BLOCK_W, BLOCK_H, BLOCK_GAP = 22, 18, 3
EMPTY_BLOCK = (40, 44, 84)


class CarSelectMenu:
    def __init__(self, catalog):
        self.catalog = catalog
        self.index = 0

    @property
    def selected(self):
        return self.catalog.at(self.index)

    def select(self, spec):
        self.index = self.catalog.index(spec)

    def move(self, step):
        self.index = (self.index + step) % len(self.catalog)

    # ---- drawing ----------------------------------------------------------------------------------
    def draw(self, hud, surf, t, lock=""):
        """`lock` is the lock message (with price) of the selected car, or '' when it is available."""
        spec = self.selected
        k = hud.keys
        hud.menu_frame(surf, "SELECT CAR")
        hud.footer_hints(surf, [(k["steer"], "CAR"), (k["confirm"], "OK"), (k["back"], "BACK")])
        self._draw_stage(hud, surf, spec, t)
        self._draw_stats(hud, surf, spec)
        self._draw_nameplate(hud, surf, spec, t, lock)

    def _draw_stage(self, hud, surf, spec, t):
        panel(surf, STAGE, edge=YELLOW, alpha=235)
        bottom = STAGE.y + 176
        floor = [(STAGE.x + 40, bottom), (STAGE.right - 40, bottom), (STAGE.right - 14, bottom + 56), (STAGE.x + 14, bottom + 56)]
        pygame.draw.polygon(surf, (36, 40, 90), floor)
        pygame.draw.lines(surf, (90, 96, 170), True, floor, 2)
        pygame.draw.ellipse(surf, (0, 0, 10), (STAGE_CX - 150, bottom - 14, 300, 30))          # shadow
        car = assets.car_sprite(spec.style.key, int(300 * spec.width), int(t * 6) % 2, player_livery(spec))   # big pixel-art preview
        surf.blit(car, (STAGE_CX - car.get_width() // 2, bottom + 6 - car.get_height()))
        if int(t * 3) % 2 == 0:                                                                 # blinking side arrows
            hud.text(surf, "<", (STAGE.x + 14, STAGE.centery - 27), RED, hud.huge)
            hud.text(surf, ">", (STAGE.right - 14 - 33, STAGE.centery - 27), RED, hud.huge)

    def _draw_stats(self, hud, surf, spec):
        panel(surf, STATS)
        for row, (label, blocks) in enumerate(spec.bars()):
            y = STATS.y + 14 + row * 46
            hud.text(surf, label, (STATS.x + 18, y), CYAN, hud.small)
            for i in range(BAR_SEGMENTS):
                rect = (STATS.x + 18 + i * (BLOCK_W + BLOCK_GAP), y + 20, BLOCK_W, BLOCK_H)
                pygame.draw.rect(surf, YELLOW if i < blocks else EMPTY_BLOCK, rect)
                pygame.draw.rect(surf, (0, 0, 0), rect, 2)

    def _draw_nameplate(self, hud, surf, spec, t, lock):
        panel(surf, NAMEPLATE)
        cx = NAMEPLATE.centerx
        hud.text(surf, spec.name, (cx, NAMEPLATE.y + 10), YELLOW, fit_font((hud.big, hud.font), spec.name, 330), "center")
        hud.text(surf, lock or "AVAILABLE", (NAMEPLATE.right - 18, NAMEPLATE.y + 22), PINK if lock else GREEN,
                 hud.small, "right")
        hud.text(surf, spec.tagline, (cx, NAMEPLATE.y + 58), CYAN, hud.small, "center")
        count = len(self.catalog)
        for i in range(count):                                                                  # position dots
            on = i == self.index
            pygame.draw.rect(surf, YELLOW if on else EMPTY_BLOCK, (cx - count * 14 + i * 28 + 4, NAMEPLATE.y + 86, 20, 10))
