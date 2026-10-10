"""Read-only circuit projection and live positions from Road's shared route."""
import pygame

PLAYER_COLOR = (80, 240, 255)
AI_COLOR = (255, 160, 70)


class RouteProjection:
    def __init__(self, route, rect):
        self.route = route
        self.rect = pygame.Rect(rect)
        xs, ys = zip(*route.points)
        self.center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        self.scale = min(self.rect.width / max(1, max(xs) - min(xs)),
                         self.rect.height / max(1, max(ys) - min(ys)))
        self.points = tuple(self.project(p) for p in route.points)

    def project(self, point):
        return (self.rect.centerx + (point[0] - self.center[0]) * self.scale,
                self.rect.centery + (point[1] - self.center[1]) * self.scale)

    def position(self, z):
        return self.project(self.route.point_at(z))


class MiniMap:
    def __init__(self, route, rect=(600, 12, 188, 140)):
        self.rect = pygame.Rect(rect)
        self.visible = True
        self.font = pygame.font.Font(None, 18)
        self.set_route(route)

    def set_route(self, route):
        self.route = route
        self.background = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.background.fill((8, 16, 30, 220))
        pygame.draw.rect(self.background, (80, 140, 170), self.background.get_rect(), 1)
        self.background.blit(self.font.render("MAP [M]    YOU / AI", True, PLAYER_COLOR), (8, 5))
        area = pygame.Rect(12, 27, self.rect.width - 24, self.rect.height - 40)
        self.projection = RouteProjection(route, area)
        self._draw_route(self.background, self.projection)

    @staticmethod
    def _draw_route(surface, projection):
        pygame.draw.lines(surface, (30, 45, 60), True, projection.points, 7)
        pygame.draw.lines(surface, (190, 205, 220), True, projection.points, 3)
        pygame.draw.circle(surface, (120, 255, 150), projection.points[0], 3)

    @classmethod
    def preview(cls, route, size):
        surface = pygame.Surface(size)
        surface.fill((8, 16, 30))
        cls._draw_route(surface, RouteProjection(route, surface.get_rect().inflate(-32, -32)))
        return surface

    def toggle(self):
        self.visible = not self.visible

    def marker_position(self, racer):
        x, y = self.projection.position(racer.front_z)
        return (x + self.rect.x, y + self.rect.y)

    def draw(self, surface, player, opponents=()):
        if not self.visible:
            return
        surface.blit(self.background, self.rect)
        for racer in opponents:
            pygame.draw.circle(surface, (0, 0, 0), self.marker_position(racer), 4)
            pygame.draw.circle(surface, AI_COLOR, self.marker_position(racer), 3)
        pygame.draw.circle(surface, (0, 0, 0), self.marker_position(player), 5)
        pygame.draw.circle(surface, PLAYER_COLOR, self.marker_position(player), 4)
