"""Original neon court and original cat athletes using the lobby bitmap font."""
import math
import pygame
from arcade_lobby.font import get_font
from .model import FLOOR, NET_TOP, NET_X, MatchState
from .cat_art import CatAthleteRenderer, YarnRenderer

CYAN, PINK, YELLOW = (90, 240, 255), (255, 110, 210), (255, 224, 90)


class VolleyRenderer:
    def __init__(self):
        self.font = get_font()
        self.cats = CatAthleteRenderer()
        self.yarn = YarnRenderer()

    def text(self, surface, text, center, color=CYAN, scale=1):
        image = self.font.render_glow(text, color, (35, 20, 65), scale)
        surface.blit(image, image.get_rect(center=center))

    def draw(self, surface, match, effects=None):
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
        for player in match.players:
            self.cats.draw(surface, player, match)
        if effects is not None:
            effects.draw(surface)
        self.yarn.draw(surface, match.ball)
        self.text(surface, "CAT VOLLEYBALL", (200, 16), PINK, 2)
        self.text(surface, f"P1  {match.points[0]} : {match.points[1]}  {'SANDRA' if match.local_players == 1 else 'P2'}",
                  (200, 39), YELLOW, 2)
        self.text(surface, "MOVE LEFT/RIGHT  UP JUMP  ITEM SMASH", (200, 280))
        self.text(surface, "MENU PAUSE  BACKSPACE RESTART  ESC LOBBY", (200, 293))
        if match.state is MatchState.TITLE:
            self.panel(surface, ("FIRST TO FIVE", "CHALLENGE SANDRA" if match.local_players == 1 else "LOCAL TWO PLAYER", "E / ENTER TO START"))
        elif match.state is MatchState.PAUSED:
            self.panel(surface, ("PAUSED", "E / ENTER TO RESUME"))
        elif match.state is MatchState.FINISHED:
            winner = "P1" if match.outcome.winner == 0 else ("SANDRA" if match.local_players == 1 else "P2")
            self.panel(surface, ("SANDRA TAKES THE CROWN!" if winner == "SANDRA" else f"{winner} WINS!",
                                 "PURRFECT SPIKES, SANDRA!" if winner == "SANDRA" else "PURRFECT VICTORY!",
                                 "E / ENTER REMATCH  ESC RETURN"))
        elif match.serve_delay > 0:
            self.text(surface, "READY!", (200, 100), YELLOW, 2)

    def panel(self, surface, lines):
        pygame.draw.rect(surface, (12, 8, 30), (38, 90, 324, 88))
        pygame.draw.rect(surface, PINK, (38, 90, 324, 88), 1)
        for i, line in enumerate(lines):
            self.text(surface, line, (200, 108 + i * 26), YELLOW, 2 if i == 0 else 1)
