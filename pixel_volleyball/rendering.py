"""Original neon court and tiny robot athletes using the lobby bitmap font."""
import math
import pygame
from arcade_lobby.font import get_font
from .model import FLOOR, NET_TOP, NET_X, MatchState

CYAN, PINK, YELLOW = (90, 240, 255), (255, 110, 210), (255, 224, 90)


class VolleyRenderer:
    def __init__(self):
        self.font = get_font()

    def text(self, surface, text, center, color=CYAN, scale=1):
        image = self.font.render_glow(text, color, (35, 20, 65), scale)
        surface.blit(image, image.get_rect(center=center))

    def draw(self, surface, match):
        surface.fill((10, 5, 28))
        for y in range(48, 180, 8):
            surface.fill((25 + y // 9, 12, 50 + y // 4), (0, y, 400, 8))
        for x in range(0, 400, 24):
            pygame.draw.rect(surface, (20, 15, 45), (x, 158 - (x * 17 % 42), 20, 70))
            for y in range(132, 190, 12):
                surface.fill((90, 60, 115), (x + 6, y, 3, 3))
        pygame.draw.rect(surface, (26, 19, 48), (20, FLOOR, 360, 10))
        pygame.draw.line(surface, PINK, (20, FLOOR), (380, FLOOR), 2)
        pygame.draw.line(surface, CYAN, (NET_X, NET_TOP), (NET_X, FLOOR), 5)
        for y in range(NET_TOP + 8, FLOOR, 8):
            pygame.draw.line(surface, (70, 110, 140), (194, y), (206, y))
        for player, color in zip(match.players, (CYAN, PINK)):
            x, y = round(player.x), round(player.y)
            pygame.draw.rect(surface, (3, 3, 12), (x - 14, y - 14, 28, 28))
            pygame.draw.rect(surface, color, (x - 12, y - 12, 24, 24))
            pygame.draw.rect(surface, (20, 25, 55), (x - 9, y - 7, 18, 8))
            for dx in (-5, 4):
                surface.fill(YELLOW, (x + dx, y - 5, 3, 3))
            surface.fill((230, 235, 255), (x - 6, y + 6, 12, 2))
            arm_y = y - 18 if player.spike_time else y + 2
            for dx in (-17, 14):
                surface.fill(color, (x + dx, arm_y, 4, 10))
            bob = int(math.sin(match.elapsed * 18) * 2) if player.vy == 0 else 0
            for dx in (-9, 5):
                surface.fill(color, (x + dx, y + 14 + bob, 5, 3))
        ball = match.ball
        pygame.draw.circle(surface, (25, 15, 45), (round(ball.x), round(ball.y)), 8)
        pygame.draw.circle(surface, YELLOW, (round(ball.x), round(ball.y)), ball.radius)
        pygame.draw.line(surface, (255, 250, 220), (ball.x - 4, ball.y - 2), (ball.x + 4, ball.y - 2))
        self.text(surface, "PIXEL VOLLEYBALL", (200, 16), PINK, 2)
        self.text(surface, f"P1  {match.points[0]} : {match.points[1]}  {'AI' if match.local_players == 1 else 'P2'}",
                  (200, 39), YELLOW, 2)
        self.text(surface, "MOVE LEFT/RIGHT  UP JUMP  ITEM SPIKE", (200, 280))
        self.text(surface, "MENU PAUSE  BACKSPACE RESTART  ESC LOBBY", (200, 293))
        if match.state is MatchState.TITLE:
            self.panel(surface, ("FIRST TO FIVE", "E / ENTER TO START"))
        elif match.state is MatchState.PAUSED:
            self.panel(surface, ("PAUSED", "E / ENTER TO RESUME"))
        elif match.state is MatchState.FINISHED:
            winner = "P1" if match.outcome.winner == 0 else ("AI" if match.local_players == 1 else "P2")
            self.panel(surface, (f"{winner} WINS!", "E / ENTER REMATCH  ESC RETURN"))
        elif match.serve_delay > 0:
            self.text(surface, "READY!", (200, 100), YELLOW, 2)

    def panel(self, surface, lines):
        pygame.draw.rect(surface, (12, 8, 30), (38, 96, 324, 68))
        pygame.draw.rect(surface, PINK, (38, 96, 324, 68), 1)
        for i, line in enumerate(lines):
            self.text(surface, line, (200, 116 + i * 27), YELLOW, 2 if i == 0 else 1)
