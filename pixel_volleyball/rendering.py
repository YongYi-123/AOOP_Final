"""Original neon court and original cat athletes using the lobby bitmap font."""
import math

import pygame
from arcade_lobby.font import get_font
from .model import FLOOR, NET_TOP, NET_X, MatchState
from .cat_art import CatAthleteRenderer, YarnRenderer
from . import old_ticket as secret

CYAN, PINK, YELLOW = (90, 240, 255), (255, 110, 210), (255, 224, 90)


class VolleyRenderer:
    def __init__(self):
        self.font = get_font()
        self.cats = CatAthleteRenderer()
        self.yarn = YarnRenderer()

    def text(self, surface, text, center, color=CYAN, scale=1):
        image = self.font.render_glow(text, color, (35, 20, 65), scale)
        surface.blit(image, image.get_rect(center=center))

    def draw(self, surface, match, effects=None, hints=None, ticket=None):
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
        if ticket is not None:
            self._ticket(surface, ticket, match.elapsed)
        for player in match.players:
            self.cats.draw(surface, player, match)
        if effects is not None:
            effects.draw(surface)
        self.yarn.draw(surface, match.ball)
        if effects is not None:
            for x, y, age in effects.popups:
                self.text(surface, "SMASH!", (round(x), round(y - 20 - age * 30)),
                          YELLOW if age < .3 else PINK)
        self.text(surface, "CAT VOLLEYBALL", (200, 16), PINK, 2)
        self.text(surface, f"YOU  {match.points[0]} : {match.points[1]}  SANDRA",
                  (200, 39), YELLOW, 2)
        lines = hints or ("MOVE  JUMP  SMASH (IN AIR)",)
        for i, line in enumerate(lines):
            self.text(surface, line, (200, 293 - 10 * (len(lines) - i)))
        self.text(surface, "MENU PAUSE  BACKSPACE RESTART  ESC LOBBY", (200, 293))
        if match.state is MatchState.TITLE:
            self.panel(surface, ("FIRST TO FIVE", "CHALLENGE SANDRA", "E / ENTER TO START"))
        elif match.state is MatchState.PAUSED:
            self.panel(surface, ("PAUSED", "E / ENTER TO RESUME"))
        elif match.state is MatchState.FINISHED and ticket is not None and ticket.blocking:
            pass                                                   # the ticket scene first, then the result card
        elif match.state is MatchState.FINISHED:
            won = match.outcome.winner == 0
            self.panel(surface, ("YOU WIN!" if won else "SANDRA TAKES THE CROWN!",
                                 "PURRFECT VICTORY!" if won else "PURRFECT SPIKES, SANDRA!",
                                 "E / ENTER REMATCH  ESC RETURN"))
        elif match.serve_delay > 0:
            self.text(surface, "READY!", (200, 100), YELLOW, 2)

    def _ticket(self, surface, ticket, t):
        """THE OLD SPECTATOR TICKET after a match: the stub flutters into the cat's paws, is held up large, then pinned
        over the stands (where it stays for the rest of the result card)."""
        paper, ink = (214, 196, 150), (110, 80, 50)
        phase = ticket.phase
        if phase == "fly":
            x, y = round(ticket.x), round(ticket.y)
            tilt = 1 if math.sin(t * 12) > 0 else 0
            surface.fill(paper, (x - secret.W // 2, y - secret.H // 2 + tilt, secret.W, secret.H - tilt))
            surface.fill(ink, (x - 1, y - secret.H // 2 + tilt, 1, secret.H - tilt))      # the torn perforation
            return
        card = self._ticket_card()
        pinned = pygame.Rect(secret.PINNED)
        big = pygame.Rect(0, 0, pinned.w * 2, pinned.h * 2)
        big.center = (200, 120)
        k = 0.0 if phase == "show" else ticket.settle
        rect = pygame.Rect(round(big.x + (pinned.x - big.x) * k), round(big.y + (pinned.y - big.y) * k),
                           round(big.w + (pinned.w - big.w) * k), round(big.h + (pinned.h - big.h) * k))
        if phase == "show":                                                                # a soft glow while it is held up
            glow = pygame.Surface((rect.w + 24, rect.h + 24), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 224, 90, 50 + int(30 * math.sin(t * 8))), glow.get_rect(), border_radius=8)
            surface.blit(glow, (rect.x - 12, rect.y - 12))
        surface.fill((70, 60, 50), rect.move(1, 1))
        surface.blit(card if rect.size == card.get_size() else pygame.transform.scale(card, rect.size), rect)
        if phase == "pinned":
            surface.fill((200, 70, 60), (rect.centerx - 1, rect.y - 2, 3, 3))              # the pin

    def _ticket_card(self):
        """The stub's face, at its pinned size: ADMIT ONE, the faded PAW print and the III beside it."""
        card = getattr(self, "_card_cache", None)
        if card is None:
            paper, ink = (214, 196, 150), (110, 80, 50)
            w, h = secret.PINNED[2:]
            card = pygame.Surface((w, h))
            card.fill(paper)
            pygame.draw.rect(card, ink, card.get_rect(), 1)
            for y in range(3, h - 2, 3):                                                   # the torn perforation
                card.fill(ink, (w - 9, y, 1, 1))
            card.blit(self.font.render(secret.HEADER, (150, 90, 40)), (5, 4))
            _pixels(card, secret.PAW_PIXELS, secret.PAW_AT, ink, 2)
            _pixels(card, secret.NUMERAL_PIXELS, secret.NUMERAL_AT, ink, 2)
            self._card_cache = card
        return card

    def panel(self, surface, lines):
        pygame.draw.rect(surface, (12, 8, 30), (38, 90, 324, 88))
        pygame.draw.rect(surface, PINK, (38, 90, 324, 88), 1)
        for i, line in enumerate(lines):
            self.text(surface, line, (200, 108 + i * 26), YELLOW, 2 if i == 0 else 1)


def _pixels(surface, rows, pos, colour, scale=1):
    """Paint a little '#'-pattern at `pos`."""
    x0, y0 = pos
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == "#":
                surface.fill(colour, (x0 + dx * scale, y0 + dy * scale, scale, scale))
