"""ChanceGameScene: hosts any ChanceGame full-screen in the Lucky Corner.

The scene only routes input and draws the balance; every rule (cost, payout,
what ESC does mid-round) belongs to the game. It builds a fresh game from
`game_cls` for each round."""
import pygame

from chance_game import draw_footer
from daily_ui import token_icon
from font import get_font
from scene_base import BaseScene
from settings import BACK_KEYS, CONFIRM_KEYS, VIEW_W, Col


class ChanceGameScene(BaseScene):
    AGAIN_DELAY = 0.7       # after a result, before E can deal the next (charged) round

    def __init__(self, game, game_cls, player=None):
        """player: the LocalPlayer who walked up to the machine. Their profile
        pays and wins; the other player (if any) only watches."""
        super().__init__(game)
        self.player = player
        if player is not None:
            self.spectators = [p for p in game.session if p is not player]
        self.game_cls = game_cls
        self.round = game_cls()
        self.time = 0.0
        self.done_age = 0.0
        self.icon = token_icon()

    @property
    def profile(self):
        return self.player.profile if self.player else self.game.profile

    def on_exit(self):
        self.round.finish()      # leaving mid-round settles it, once

    def on_quit(self):
        self.round.finish()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.player and not self.game.session.allows(self.player, event.key):
            return                      # the other player's keys do nothing here (they only watch)
        if event.key in BACK_KEYS:
            self.game.scenes.pop()
        elif event.key in CONFIRM_KEYS and self.round.phase == self.round.IDLE:
            self.round.start(self.profile)           # refuses (charges nothing) if short
        elif event.key in CONFIRM_KEYS and self.round.phase == self.round.DONE:
            if self.done_age >= self.AGAIN_DELAY:    # a mashed key must not buy a round
                self.round = self.game_cls()         # next round, a new game object
                self.round.start(self.profile)
        else:
            self.round.handle_event(event)

    def update(self, dt):
        self.time += dt
        self.round.update(dt)
        self.done_age = self.done_age + dt if self.round.phase == self.round.DONE else 0.0

    def draw(self, surf):
        self.round.draw(surf)
        draw_footer(surf, self.round, self.profile, self.time, self.round.ready_text)
        self._draw_balance(surf)

    def _draw_balance(self, surf):
        font = get_font()
        who = f"{self.player.tag}  " if self.player and self.player.label else ""
        text = font.render_glow(f"{who}TOKENS {self.profile.tokens:02d}", Col.YELLOW,
                                (90, 70, 20))
        rect = text.get_rect(topright=(VIEW_W - 8, 12))
        surf.blit(text, rect)
        surf.blit(self.icon, self.icon.get_rect(midright=(rect.left - 3, rect.centery)))
