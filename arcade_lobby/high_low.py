"""HighLowGame: pay 1 token, guess whether the next card is higher or lower.

Each correct guess raises the prize held (settings.HIGH_LOW_PAYOUTS: 2, 4, 8
tokens). After a win the player may CASH OUT or risk it on another guess; the
streak stops at the last payout so prizes cannot grow without limit. A wrong
guess - or a tie - ends the round with nothing.

The next card is drawn when the guess is made (the flip is only the reveal), a
wrong guess pays nothing, and every way out of the round goes through
ChanceGame._resolve(), so a prize can be paid only once.
"""
import pygame

from chance_game import (ChanceGame, draw_centered, draw_chance_backdrop,
                         token_text)
from font import get_font
from gfx import scale_color, shade
from settings import (CONFIRM_KEYS, HIGH_LOW_COST, HIGH_LOW_PAYOUTS,
                      HIGH_LOW_RANKS, NEXT_KEYS, PREV_KEYS, Col)

HIGHER, LOWER = "higher", "lower"
FLIP_TIME = 0.7
CARD_W, CARD_H = 56, 78


def rank_label(rank):
    return {1: "A", 11: "J", 12: "Q", 13: "K"}.get(rank, str(rank))


class HighLowGame(ChanceGame):
    id = "high_low"
    name = "HIGH-LOW"
    ready_text = "DEAL"

    def __init__(self, payouts=HIGH_LOW_PAYOUTS, ranks=HIGH_LOW_RANKS, cost=HIGH_LOW_COST, rng=None):
        super().__init__(cost, rng)
        if not payouts or any(p <= 0 for p in payouts) or ranks < 2:
            raise ValueError("High-Low needs positive payouts and at least 2 ranks")
        self.payouts = tuple(payouts)
        self.ranks = ranks
        self.card = None            # rank on the table
        self.streak = 0             # correct guesses so far
        self.pending = None         # (next rank, win?) while the flip plays
        self.flip = 0.0
        self.time = 0.0

    @property
    def max_streak(self):
        return len(self.payouts)

    @property
    def prize(self):
        """Tokens held right now (what CASH OUT pays)."""
        return self.payouts[self.streak - 1] if self.streak else 0

    @property
    def can_cash_out(self):
        return self.phase == self.PLAYING and self.pending is None and self.streak > 0

    @property
    def can_guess(self):
        return self.phase == self.PLAYING and self.pending is None

    # ------------------------------------------------------------ round
    def _begin(self):
        self.card = self.rng.randint(1, self.ranks)

    def guess(self, direction):
        """Bet the next card is HIGHER or LOWER. Ignored while a flip is under
        way or the round is over, so mashing keys cannot guess twice."""
        if not self.can_guess or direction not in (HIGHER, LOWER):
            return False
        nxt = self.rng.randint(1, self.ranks)
        win = nxt > self.card if direction == HIGHER else nxt < self.card
        self.pending = (nxt, win)
        self.flip = 0.0
        return True

    def cash_out(self):
        if not self.can_cash_out:
            return False
        self._resolve(self.prize, f"CASHED OUT {token_text(self.prize)}!")
        return True

    def _apply_pending(self):
        """The flip is over: move the card, extend the streak or end the round."""
        nxt, win = self.pending
        self.pending = None
        self.card = nxt
        if not win:
            self._resolve(0, "WRONG GUESS - NO PRIZE")
            return
        self.streak += 1
        if self.streak >= self.max_streak:
            self._resolve(self.prize, f"MAX STREAK! WON {token_text(self.prize)}!")

    def _settle_unfinished(self):
        if self.pending is not None:       # a guess is already decided: honour it
            self._apply_pending()
        if self.phase == self.PLAYING:
            if self.streak:
                self._resolve(self.prize, f"CASHED OUT {token_text(self.prize)}!")
            else:                           # never guessed: the entry is returned
                self._resolve(0, "ROUND CANCELLED - ENTRY RETURNED", refund=True)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in PREV_KEYS:
            self.guess(HIGHER)
        elif event.key in NEXT_KEYS:
            self.guess(LOWER)
        elif event.key in CONFIRM_KEYS:
            self.cash_out()

    def update(self, dt):
        self.time += dt
        if self.pending is not None:
            self.flip += dt
            if self.flip >= FLIP_TIME:
                self._apply_pending()

    # ------------------------------------------------------------ draw
    def _card(self, label, face_up=True, width=CARD_W, tint=Col.CYAN):
        card = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        pygame.draw.rect(card, (246, 240, 255) if face_up else (40, 22, 90), card.get_rect(), border_radius=5)
        pygame.draw.rect(card, tint, card.get_rect(), 2, border_radius=5)
        font = get_font()
        if face_up:
            img = font.render(label, (70, 44, 110), 4 if len(label) < 2 else 3)
            card.blit(img, img.get_rect(center=card.get_rect().center))
            small = font.render(label, (70, 44, 110))
            card.blit(small, (5, 5))
        else:
            for k in range(3):
                pygame.draw.rect(card, scale_color(tint, 0.5), card.get_rect().inflate(-14 - k * 8, -14 - k * 8), 1)
        return pygame.transform.scale(card, (max(2, int(width)), CARD_H))

    def _blit_card(self, surf, img, cx):
        surf.blit(img, img.get_rect(center=(cx, 130)))

    def draw(self, surf):
        draw_chance_backdrop(surf, (6, 14, 36), (10, 36, 56), Col.CYAN, self.time)
        draw_centered(surf, "HIGH-LOW", 12, shade(Col.CYAN, 0.55), 2, scale_color(Col.CYAN, 0.8))
        font = get_font()
        mid = surf.get_width() // 2
        if self.phase == self.IDLE:
            self._blit_card(surf, self._card("", False), mid)
            draw_centered(surf, f"GUESS HIGHER OR LOWER - WIN UP TO {token_text(self.payouts[-1])}", 40,
                          Col.TEXT_MUTED)
            self._draw_ladder(surf)
            return
        if self.pending is None:
            self._blit_card(surf, self._card(rank_label(self.card)), mid - 40)
            self._blit_card(surf, self._card("", False), mid + 40)
        else:                                       # flip the new card over
            nxt, _ = self.pending
            k = min(1.0, self.flip / FLIP_TIME)
            self._blit_card(surf, self._card(rank_label(self.card)), mid - 40)
            squeeze = abs(1 - 2 * k)                # 1 -> 0 -> 1
            self._blit_card(surf, self._card(rank_label(nxt), k >= 0.5, CARD_W * squeeze), mid + 40)
        self._draw_ladder(surf)
        self._draw_prompt(surf, font)

    def _draw_ladder(self, surf):
        font = get_font()
        y = 190
        for i, payout in enumerate(self.payouts):
            lit = self.phase != self.IDLE and self.streak == i + 1
            won = self.streak > i + 1 or (self.streak == i + 1 and self.phase == self.DONE and self.get_result().payout)
            color = Col.GREEN if lit or won else Col.TEXT_MUTED
            text = f"{i + 1} WIN: {token_text(payout)}"
            surf.blit(font.render(text, color), (surf.get_width() // 2 - 42, y + i * 10))

    def _draw_prompt(self, surf, font):
        if self.phase == self.DONE:
            result = self.get_result()
            color = Col.GREEN if result.payout else Col.MAGENTA
            draw_centered(surf, result.summary, 224, color, 1, scale_color(color, 0.4))
            draw_centered(surf, "E: PLAY AGAIN", 244, Col.YELLOW)
        elif self.pending is not None:
            draw_centered(surf, "...", 228, Col.CYAN)
        else:
            held = f"HOLDING {token_text(self.prize)}   " if self.streak else ""
            draw_centered(surf, f"{held}UP: HIGHER   DOWN: LOWER", 224, Col.TEXT)
            if self.streak:
                draw_centered(surf, f"E: CASH OUT {token_text(self.prize)}", 240, Col.YELLOW,
                              glow=scale_color(Col.YELLOW, 0.35))
