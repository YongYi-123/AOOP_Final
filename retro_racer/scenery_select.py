"""Additional scenery strip below the existing, unchanged track cards."""
import pygame
import settings as S
from assets import CYAN, YELLOW
from hud import DIM
from scenery import SceneryPreviewRenderer


class SceneryGallery:
    THUMBNAIL_SIZE = (92, 69)
    TOP = 452

    def __init__(self, themes):
        self.themes = themes
        self.renderer = SceneryPreviewRenderer(themes)

    def thumbnail_rects(self):
        count = len(self.themes)
        cell = (S.WIDTH - 32) / count
        width, height = self.THUMBNAIL_SIZE
        return tuple(pygame.Rect(round(16 + (i + 0.5) * cell - width / 2),
                                 self.TOP, width, height) for i in range(count))

    def draw(self, surface, hud, route, index, markers=True):
        for i, (theme, rect) in enumerate(zip(self.themes.themes, self.thumbnail_rects())):
            preview = self.renderer.preview(theme, route, self.THUMBNAIL_SIZE, markers)
            pygame.draw.rect(surface, YELLOW if i == index else (40, 40, 70), rect.inflate(6, 6))
            surface.blit(preview, rect)
            hud.text(surface, theme.name, (rect.centerx, rect.bottom + 4),
                     CYAN if i == index else DIM, hud.small, "center")
