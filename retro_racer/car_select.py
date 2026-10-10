"""CarSelectMenu: cursor state and drawing for the CAR SELECT screen (no physics in here)."""
import pygame
import assets
from assets import YELLOW, CYAN, RED
from car_specs import BAR_SEGMENTS, player_livery

STAGE = pygame.Rect(30, 150, 400, 260)
STAGE_CX = STAGE.centerx
BLOCK_W, BLOCK_H, BLOCK_GAP = 26, 18, 4
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
    def draw(self, hud, surf, t):
        spec = self.selected
        hud.menu_frame(surf, "SELECT CAR", hud.select_footer())
        self._draw_stage(hud, surf, spec, t)
        self._draw_stats(hud, surf, spec)

    def _draw_stage(self, hud, surf, spec, t):
        pygame.draw.rect(surf, (14, 16, 44), STAGE)
        pygame.draw.rect(surf, YELLOW, STAGE, 3)
        bottom = STAGE.y + 190
        floor = [(STAGE.x + 40, bottom), (STAGE.right - 40, bottom), (STAGE.right - 10, bottom + 46), (STAGE.x + 10, bottom + 46)]
        pygame.draw.polygon(surf, (36, 40, 90), floor)
        pygame.draw.lines(surf, (90, 96, 170), True, floor, 2)
        pygame.draw.ellipse(surf, (0, 0, 10), (STAGE_CX - 150, bottom - 14, 300, 30))          # shadow
        car = assets.car_sprite(spec.style.key, int(300 * spec.width), int(t * 6) % 2, player_livery(spec))   # big pixel-art preview
        surf.blit(car, (STAGE_CX - car.get_width() // 2, bottom + 6 - car.get_height()))
        hud.text(surf, spec.name, (STAGE_CX, STAGE.bottom + 12), YELLOW, hud.huge, "center")
        if int(t * 3) % 2 == 0:
            hud.text(surf, "<", (STAGE.x + 6, STAGE.bottom + 12), RED, hud.huge)
            hud.text(surf, ">", (STAGE.right - 30, STAGE.bottom + 12), RED, hud.huge)
        hud.text(surf, spec.tagline, (STAGE_CX, STAGE.bottom + 76), CYAN, hud.small, "center")
        for i in range(len(self.catalog)):                                                      # position dots
            on = i == self.index
            pygame.draw.rect(surf, YELLOW if on else EMPTY_BLOCK, (STAGE_CX - len(self.catalog) * 14 + i * 28 + 4, STAGE.bottom + 106, 20, 10))

    def _draw_stats(self, hud, surf, spec):
        x0 = 460
        for row, (label, blocks) in enumerate(spec.bars()):
            y = 165 + row * 66
            hud.text(surf, label, (x0, y), CYAN, hud.small)
            for i in range(BAR_SEGMENTS):
                rect = (x0 + i * (BLOCK_W + BLOCK_GAP), y + 26, BLOCK_W, BLOCK_H)
                pygame.draw.rect(surf, YELLOW if i < blocks else EMPTY_BLOCK, rect)
                pygame.draw.rect(surf, (0, 0, 0), rect, 2)
