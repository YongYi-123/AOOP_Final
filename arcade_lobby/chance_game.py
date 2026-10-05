"""ChanceGame: the shared rules of every Lucky Corner game.

A round goes IDLE -> PLAYING -> DONE and money moves exactly three ways,
each guarded here so no subclass can get it wrong:

    start(profile)   charges the entry cost once (only from IDLE)
    _resolve(...)    pays the winnings (or refunds the entry) once
    finish()         settles whatever is still open when the player leaves

Subclasses only supply their own rules: _begin(), _settle_unfinished(),
handle_event(), update() and draw(). One instance is one round; the scene
builds a new instance for the next round.

All values are fictional arcade tokens: there is no real money, nothing is
bought and tokens cannot be cashed out.
"""
import random
from dataclasses import dataclass

import pygame

from font import get_font
from gfx import lerp_color, scale_color
from settings import VIEW_H, VIEW_W, Col


@dataclass(frozen=True)
class ChanceResult:
    game_id: str
    bet: int
    payout: int     # tokens handed back to the player (the entry cost, if refunded)
    summary: str    # e.g. "YOU WON 3 TOKENS"

    @property
    def net(self):
        return self.payout - self.bet


class ChanceGame:
    IDLE, PLAYING, DONE = "idle", "playing", "done"
    id = ""
    name = ""
    ready_text = "PLAY"      # what the E prompt says before the round starts

    def __init__(self, cost, rng=None):
        self.cost = cost
        self.rng = rng or random.Random()
        self._phase = self.IDLE
        self._profile = None
        self._result = None

    @property
    def phase(self):
        return self._phase

    # ------------------------------------------------------------ interface
    def can_play(self, profile):
        """True if a round can start now: fresh round and enough tokens."""
        return self._phase == self.IDLE and profile.can_afford_tokens(self.cost)

    def start(self, profile):
        """Charge the entry cost and begin. Returns False, charging nothing,
        if the round already started or the player is short of tokens."""
        if not self.can_play(profile) or not profile.spend_tokens(self.cost, self.name):
            return False
        self._profile = profile
        self._phase = self.PLAYING
        profile.record_chance_game_played()
        self._begin()
        return True

    def handle_event(self, event):
        """Player input while the round is PLAYING."""

    def update(self, dt):
        pass

    def draw(self, surf):
        raise NotImplementedError

    def get_result(self):
        """The ChanceResult once the round is DONE, else None."""
        return self._result

    def finish(self):
        """The player is leaving. Settles an open round (at most once) and
        returns the result, or None if the round never started."""
        if self._phase == self.PLAYING:
            self._settle_unfinished()
        return self._result

    # ------------------------------------------------------------ for subclasses
    def _begin(self):
        """The entry cost was just paid: set up the round."""

    def _settle_unfinished(self):
        """The round was cut short: call _resolve() with what the player is owed."""
        raise NotImplementedError

    def _resolve(self, payout, summary, refund=False):
        """End the round: pay `payout` tokens (or refund the entry cost). Only
        the first call does anything, so a result is never paid twice."""
        if self._result is not None:
            return self._result
        self._phase = self.DONE
        if refund:
            payout = self.cost
            self._profile.refund_tokens(payout, self.name)
        elif payout:
            self._profile.add_tokens(payout, f"{self.name} WIN")
        self._result = ChanceResult(self.id, self.cost, payout, summary)
        return self._result


# ---------------------------------------------------------------- shared drawing
def token_text(n):
    return f"{n} TOKEN" + ("" if n == 1 else "S")


def draw_chance_backdrop(surf, top, bottom, accent, time):
    """A flashy night backdrop: banded gradient, a chasing light strip along
    the top and bottom edges."""
    for y in range(0, VIEW_H, 4):
        surf.fill(lerp_color(top, bottom, y / VIEW_H), (0, y, VIEW_W, 4))
    for edge in (3, VIEW_H - 5):
        for i, x in enumerate(range(6, VIEW_W - 6, 10)):
            lit = int(time * 6 + i) % 4 == 0
            surf.fill(Col.YELLOW if lit else scale_color(accent, 0.45), (x, edge, 5, 2))


def draw_centered(surf, text, y, color=Col.TEXT, scale=1, glow=None):
    font = get_font()
    img = font.render_glow(text, color, glow, scale) if glow else font.render(text, color, scale)
    surf.blit(img, img.get_rect(midtop=(VIEW_W // 2, y)))


def draw_footer(surf, game, profile, time, ready_text):
    """The bottom prompt line shared by every game: what E does right now."""
    if game.phase == game.IDLE:
        if game.can_play(profile):
            if int(time * 2.5) % 2 == 0:
                draw_centered(surf, f"E: {ready_text} - COST {token_text(game.cost)}", VIEW_H - 24,
                              Col.YELLOW, glow=scale_color(Col.YELLOW, 0.35))
        else:
            draw_centered(surf, f"NOT ENOUGH TOKENS - NEED {game.cost}", VIEW_H - 24,
                          Col.MAGENTA, glow=scale_color(Col.MAGENTA, 0.35))
    draw_centered(surf, "ESC: BACK TO ARCADE", VIEW_H - 13, scale_color(Col.TEXT_MUTED, 0.8))
