"""MOCHI'S MAINTENANCE RECORD: the old night-shift note she shows in Chapter 02. Read only.

Opened from CHAT WITH MOCHI ("Did you find something unusual?"), which only offers it once all three of Chapter 02's
symbols are found (mochi_chat.has_record). The record (forgotten_games.RECORD_LINES) says where the prize lock is (the
claw machine) and that its marks go in their numbered order, but never which marks: the lock itself lives on NEON CLAW
(claw_lock.py). ESC or E puts it away.
"""
import pygame

import forgotten_games as fg
from font import LINE_H
from menu_kit import FRAME, MenuScene
from ui import draw_text

PAPER = pygame.Rect(18, 52, FRAME.w - 24, 92)
INK, PAPER_COL, FADED = (70, 50, 34), (226, 212, 172), (150, 128, 96)


class MaintenanceNoteScene(MenuScene):
    title = "MAINTENANCE RECORD"
    hints = ("ESC BACK",)

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.manager = game.hub.story.manager

    @property
    def solved(self):
        return self.manager.riddle_solved

    def on_action(self, action):
        if action in ("back", "interact"):
            self.play("cancel")
            self.close()

    def idle_message(self):
        return "MOCHI PUTS THE RECORD AWAY CAREFULLY" if self.solved else "MOCHI WAITS, SMILING"

    def draw_body(self, surf):
        self.draw_frame(surf)
        surf.fill((60, 46, 30), PAPER.move(2, 2))
        surf.fill(PAPER_COL, PAPER)
        pygame.draw.rect(surf, FADED, PAPER, 1)
        for y in range(PAPER.y + 18, PAPER.bottom - 4, 11):           # faint ruled lines
            surf.fill((212, 196, 154), (PAPER.x + 4, y + 9, PAPER.w - 8, 1))
        draw_text(surf, fg.RECORD_TITLE, (PAPER.centerx, PAPER.y + 5), INK, anchor="midtop")
        y = PAPER.y + 19
        for line in fg.RECORD_LINES:
            draw_text(surf, line, (PAPER.x + 7, y), INK)
            y += LINE_H + 1
        if self.solved:                                                # a red stamp beside the title, clear of the lines
            stamp = pygame.Rect(0, 0, 60, 13)
            stamp.topright = (PAPER.right - 6, PAPER.y + 3)
            pygame.draw.rect(surf, (170, 60, 50), stamp, 1)
            draw_text(surf, fg.SOLVED_LINE, stamp.center, (170, 60, 50), anchor="center")
        self.draw_footer(surf, ("ESC BACK",))
