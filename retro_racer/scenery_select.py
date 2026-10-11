"""Additional scenery strip below the existing, unchanged track cards."""
import pygame
import settings as S
from assets import YELLOW
from hud import DIM, PINK
from menu_layout import MARGIN
from scenery import SceneryPreviewRenderer


class SceneryGallery:
    """The scenery strip: six equal cells, the selected one framed, a LOCKED tag under (never over)
    the thumbnail of a locked scenery."""
    THUMBNAIL_SIZE = (92, 60)
    TOP = 420

    def __init__(self, themes):
        self.themes = themes
        self.renderer = SceneryPreviewRenderer(themes)

    def thumbnail_rects(self):
        count = len(self.themes)
        cell = (S.WIDTH - 2 * MARGIN) / count
        width, height = self.THUMBNAIL_SIZE
        return tuple(pygame.Rect(round(MARGIN + (i + 0.5) * cell - width / 2),
                                 self.TOP, width, height) for i in range(count))

    def draw(self, surface, hud, route, index, markers=True, progression=None):
        for i, (theme, rect) in enumerate(zip(self.themes.themes, self.thumbnail_rects())):
            on = i == index
            preview = self.renderer.preview(theme, route, self.THUMBNAIL_SIZE, markers)
            pygame.draw.rect(surface, YELLOW if on else (40, 40, 70), rect.inflate(8 if on else 4, 8 if on else 4))
            surface.blit(preview, rect)
            if not on:
                shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                shade.fill((0, 0, 20, 90))
                surface.blit(shade, rect)
            hud.text(surface, theme.name, (rect.centerx, rect.bottom + 6), YELLOW if on else DIM, hud.small, "center")
            if progression is not None and not progression.owns('scenery', theme.key):
                hud.text(surface, 'LOCKED', (rect.centerx, rect.bottom + 23), PINK, hud.small, "center")
