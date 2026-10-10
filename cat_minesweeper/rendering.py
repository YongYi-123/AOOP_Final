"""Original cat tiles and low-resolution neon UI using the lobby's pixel font."""
import pygame
from arcade_lobby.font import get_font
from .model import BoardState, DIFFICULTIES

CYAN, PINK, GOLD = (90, 240, 255), (255, 110, 210), (255, 224, 90)
NUMBER_COLORS = ((0, 0, 0), CYAN, (110, 240, 160), PINK, (180, 150, 255),
                 GOLD, (255, 160, 100), (220, 220, 240), (180, 180, 200))


class MineGridLayout:
    def __init__(self, size):
        self.size = size
        self.cell_size = min(32, 216 // size)
        width = size * self.cell_size
        self.rect = pygame.Rect(200 - width // 2, 60, width, width)

    def cell_at(self, point):
        if not self.rect.collidepoint(point):
            return None
        return ((point[0] - self.rect.x) // self.cell_size,
                (point[1] - self.rect.y) // self.cell_size)

    def cell_rect(self, x, y):
        return pygame.Rect(self.rect.x + x * self.cell_size,
                           self.rect.y + y * self.cell_size, self.cell_size, self.cell_size)


class MineRenderer:
    def __init__(self):
        self.font = get_font()

    def text(self, surface, text, center, color=CYAN, scale=1):
        image = self.font.render_glow(text, color, (38, 20, 62), scale)
        surface.blit(image, image.get_rect(center=center))

    @staticmethod
    def cat(surface, center, color, blink=False, sad=False):
        x, y = center
        pygame.draw.rect(surface, color, (x - 8, y - 5, 16, 12))
        pygame.draw.polygon(surface, color, [(x - 8, y - 4), (x - 8, y - 11), (x - 2, y - 5)])
        pygame.draw.polygon(surface, color, [(x + 8, y - 4), (x + 8, y - 11), (x + 2, y - 5)])
        for dx in (-4, 3):
            surface.fill((20, 12, 36), (x + dx, y - 2, 2, 1 if blink else 3))
        surface.fill((255, 165, 190), (x - 1, y + 2, 2, 2))
        if sad:
            pygame.draw.line(surface, (20, 12, 36), (x - 3, y + 5), (x + 3, y + 5))

    def draw(self, surface, game):
        surface.fill((12, 7, 30))
        for y in range(0, 300, 8):
            surface.fill((15 + y // 24, 8, 34 + y // 18), (0, y, 400, 4))
        self.text(surface, "CAT MINESWEEPER", (200, 16), PINK, 2)
        blink = int(game.time * 3) % 15 == 0
        self.cat(surface, (355, 20), GOLD, blink, game.board.state is BoardState.LOST)
        if game.selecting:
            for i, difficulty in enumerate(DIFFICULTIES):
                rect = pygame.Rect(75, 66 + i * 53, 250, 42)
                pygame.draw.rect(surface, (28, 18, 55), rect)
                pygame.draw.rect(surface, GOLD if i == game.difficulty_index else (70, 45, 95), rect, 2)
                self.text(surface, difficulty.name, rect.center, CYAN, 2)
            self.text(surface, "FIRST CLICK + NEIGHBORS ARE SAFE", (200, 235))
            self.text(surface, "UP/DOWN SELECT  E/ENTER PLAY  ESC LOBBY", (200, 268), GOLD)
            return
        board = game.board
        self.text(surface, f"FLAGS {board.flag_count}/{board.difficulty.mines}", (55, 40))
        self.text(surface, f"SCORE {board.score}", (200, 40), GOLD)
        self.text(surface, f"TIME {int(board.elapsed)}", (350, 40))
        for y, row in enumerate(board.cells):
            for x, cell in enumerate(row):
                rect = game.layout.cell_rect(x, y).inflate(-2, -2)
                color = (32, 22, 58) if cell.revealed else (73, 49, 102)
                if board.exploded == (x, y):
                    color = (160, 40, 80)
                pygame.draw.rect(surface, color, rect)
                if not cell.revealed:
                    pygame.draw.line(surface, (130, 95, 165), rect.topleft, rect.topright)
                if cell.mine and board.state is BoardState.LOST:
                    self.cat(surface, rect.center, PINK, sad=True)
                elif cell.flagged:
                    cx, cy = rect.center
                    pygame.draw.line(surface, GOLD, (cx - 3, cy - 5), (cx - 3, cy + 5), 2)
                    pygame.draw.polygon(surface, PINK, [(cx - 2, cy - 5), (cx + 5, cy - 2), (cx - 2, cy)])
                elif cell.revealed and cell.adjacent:
                    self.text(surface, str(cell.adjacent), rect.center, NUMBER_COLORS[cell.adjacent])
                elif not cell.revealed and game.layout.cell_size >= 24:
                    # Tiny paw print on unopened tiles; no hidden mine information.
                    cx, cy = rect.center
                    surface.fill((100, 71, 130), (cx - 2, cy, 4, 3))
                    for dx in (-4, 0, 4):
                        surface.fill((100, 71, 130), (cx + dx - 1, cy - 4, 2, 2))
        self.text(surface, "LEFT REVEAL  RIGHT FLAG  MENU PAUSE  ESC LOBBY", (200, 290))
        if game.paused:
            self.panel(surface, "CAT NAP - PAUSED", "E/ENTER RESUME")
        elif board.state in (BoardState.WON, BoardState.LOST):
            self.panel(surface, "PURRFECT!" if board.state is BoardState.WON else "OOPS! A HIDDEN CAT!",
                       "E/ENTER REPLAY  BACKSPACE DIFFICULTY")

    def panel(self, surface, title, subtitle):
        pygame.draw.rect(surface, (12, 8, 30), (36, 120, 328, 60))
        pygame.draw.rect(surface, PINK, (36, 120, 328, 60), 1)
        self.text(surface, title, (200, 137), GOLD, 2)
        self.text(surface, subtitle, (200, 162))
