"""NEON CLAW'S PRIZE LOCK: Chapter 02's three-wheel symbol lock, on the claw machine itself.

Inside the claw machine screen (claw_scene.py) the player presses UP (W) while the claw is idle to look at the lock;
it is only there once all three of Chapter 02's symbols are found and until it is opened. Mochi's maintenance record
(maintenance_note.py) is where the player learns about it.

The lock has three wheels, numbered I, II and III. Each wheel starts EMPTY and turns through the same marks
(forgotten_games.LOCK_CHOICES: the three real symbols among decoys); nothing is ever filled in for the player.
LEFT / RIGHT picks a wheel, UP / DOWN turns it, E or ENTER tries the lock. forgotten_games.is_combination() checks
STAR, MOON, PAW. A wrong try gets a gentle line and the wheels stay as they are (no cost, no lock-out, no counter).
Q opens the Quest Log right here, on its RECOVERED SYMBOLS page, to look at what was found (it fills nothing in).
The right combination records the story flag CH2_RIDDLE_SOLVED (once) and, after a moment, goes back to the claw
machine, where the Golden Cat drops into the stock. Secret Item 02 itself is only awarded when the plushie is really
won there. ESC leaves.
"""
import math

import pygame

import forgotten_games as fg
from gfx import scale_color
from menu_kit import FRAME, MenuScene
from quest_ui import QuestLogUI
from quests import CH2_RIDDLE_SOLVED
from settings import Col
from symbol_art import symbol_image
from ui import draw_text

PLATE = pygame.Rect(0, 52, 270, 34)
PLATE.centerx = FRAME.centerx
WHEEL_W, WHEEL_H, WHEEL_GAP = 46, 46, 16
LOCK = pygame.Rect(0, 128, 3 * WHEEL_W + 2 * WHEEL_GAP + 28, WHEEL_H + 24)
LOCK.centerx = FRAME.centerx
INK = (70, 50, 34)
BRASS, BRASS_DARK, BRASS_LIGHT = (196, 150, 64), (120, 84, 30), (240, 206, 120)
REPLY_TIME = 2.6
OPEN_PAUSE = 1.6            # seconds the open lock stays on screen before the claw machine comes back


def lock_pending(manager):
    """Is the prize lock on the claw machine, waiting to be opened?"""
    return manager is not None and manager.chapter_two_open and manager.all_clues_found and not manager.riddle_solved


class ClawLockScene(MenuScene):
    title = "PRIZE LOCK"
    hints = ("LEFT/RIGHT WHEEL", "UP/DOWN TURN", "E TRY", "Q QUEST LOG", "ESC BACK")

    def __init__(self, game, owner):
        super().__init__(game, owner)
        self.manager = game.hub.story.manager
        self.wheels = [None] * len(fg.LOCK_SLOTS)      # an index into LOCK_CHOICES per wheel; None = still empty
        self.cursor = 0                                 # the wheel being turned
        self.reply = None                               # the line after a try
        self.reply_time = 0.0
        self.wrong = 0                                  # wrong tries in this visit (only picks the next gentle line)
        self.lock = 0.25                                # the key that opened the screen does not turn a wheel
        self.log = None                                 # the Quest Log, opened over the lock with Q
        self.opened_at = None                           # time the right combination was set

    # ------------------------------------------------------------ state (always read from the story)
    @property
    def can_answer(self):
        return lock_pending(self.manager)

    @property
    def solved(self):
        return self.manager.riddle_solved

    @property
    def marks(self):
        """The mark on each wheel, left to right (None for an empty wheel)."""
        return [None if i is None else fg.LOCK_CHOICES[i] for i in self.wheels]

    # ------------------------------------------------------------ input
    def open_log(self):
        """The Quest Log over the lock, on its CHAPTER 02 page: RECOVERED SYMBOLS."""
        self.log = QuestLogUI(self.manager, self.profile, on_close=self._log_closed)
        if "CHAPTER 02" in self.log.pages:
            self.log.page = self.log.pages.index("CHAPTER 02")
        self.play("confirm")

    def _log_closed(self):
        self.log = None
        self.lock = 0.15

    def handle_event(self, event):
        if self.log is not None:
            self.log.handle_event(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_q and self.opened_at is None:
            self.open_log()
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.lock <= 0:
            self.input.feed(event)
            self.on_action("interact")
            return
        super().handle_event(event)

    def on_action(self, action):
        if action == "back":
            self.play("cancel")
            self.close()
            return
        if not self.can_answer or self.lock > 0:
            return
        if action in ("left", "right"):
            self.cursor = (self.cursor + (-1 if action == "left" else 1)) % len(self.wheels)
            self.play("move")
        elif action in ("up", "down"):
            self.turn(self.cursor, -1 if action == "up" else 1)
        elif action == "interact":
            self.submit()

    def turn(self, wheel, step=1):
        """Turn one wheel by `step` marks (an empty wheel starts at the first or the last mark)."""
        n = len(fg.LOCK_CHOICES)
        current = self.wheels[wheel]
        self.wheels[wheel] = (0 if step > 0 else n - 1) if current is None else (current + step) % n
        self.play("move")

    def set_marks(self, marks):
        """Set the wheels to these marks (by name), as the player would by turning them. For tools and tests."""
        for i, mark in enumerate(marks):
            self.wheels[i] = None if mark is None else fg.LOCK_CHOICES.index(mark)

    def submit(self):
        """Try the lock. Returns True when it opens."""
        if not self.can_answer:
            return False
        if None in self.wheels:
            self.reply, self.reply_time = fg.UNSET_LINE, REPLY_TIME
            self.play("cancel")
            return False
        if fg.is_combination(self.marks):
            self.manager.handle(CH2_RIDDLE_SOLVED)
            self.reply, self.reply_time = fg.RIGHT_LINE, 99.0
            self.opened_at = self.time
            self.play("win")
            return True
        self.reply, self.reply_time = fg.WRONG_LINES[self.wrong % len(fg.WRONG_LINES)], REPLY_TIME
        self.wrong += 1
        self.play("cancel")
        return False

    def _click_wheel(self, i):
        if self.can_answer and self.lock <= 0 and self.log is None:
            if i == self.cursor:
                self.turn(i, 1)
            self.cursor = i

    # ------------------------------------------------------------ frame
    def update(self, dt):
        super().update(dt)
        self.lock = max(0.0, self.lock - dt)
        self.reply_time = max(0.0, self.reply_time - dt)
        if self.log is not None:
            self.log.update(dt)
        if self.opened_at is not None and self.time - self.opened_at >= OPEN_PAUSE and self.game.scenes.current is self:
            self.close()                                               # back to the claw machine: the Golden Cat drops in

    def idle_message(self):
        return "THE OLD LOCK IS STIFF. TURN THE WHEELS" if self.can_answer else "THE PRIZE LOCK IS OPEN"

    def wheel_rect(self, i):
        x = LOCK.x + 14 + i * (WHEEL_W + WHEEL_GAP)
        return pygame.Rect(x, LOCK.y + 14, WHEEL_W, WHEEL_H)

    def draw_body(self, surf):
        self.draw_frame(surf)
        self._draw_plate(surf)
        self._draw_lock(surf)
        if self.reply and self.reply_time > 0:
            draw_text(surf, self.reply, (FRAME.centerx, LOCK.bottom + 10), Col.YELLOW if self.solved else Col.TEXT_MUTED,
                      anchor="midtop")
        self.draw_footer(surf, None if self.can_answer else ("ESC BACK",))
        if self.log is not None:
            self.log.draw(surf)

    def _draw_plate(self, surf):
        """The little brass plate screwed above the lock."""
        surf.fill((60, 40, 16), PLATE.move(2, 2))
        surf.fill(BRASS, PLATE)
        pygame.draw.rect(surf, BRASS_DARK, PLATE, 1)
        for sx in (PLATE.x + 4, PLATE.right - 6):
            surf.fill(BRASS_DARK, (sx, PLATE.y + 4, 2, 2))
            surf.fill(BRASS_DARK, (sx, PLATE.bottom - 6, 2, 2))
        draw_text(surf, fg.LOCK_PLATE[0], (PLATE.centerx, PLATE.y + 6), INK, anchor="midtop")
        draw_text(surf, fg.LOCK_PLATE[1], (PLATE.centerx, PLATE.y + 19), INK, anchor="midtop")

    def _draw_lock(self, surf):
        open_ = self.solved
        lift = 8 if open_ else 0                                      # the shackle, raised once it opens
        shackle = pygame.Rect(LOCK.centerx - 34, LOCK.y - 22 - lift, 68, 36)
        pygame.draw.rect(surf, BRASS_DARK, shackle, 6, border_radius=14)
        pygame.draw.rect(surf, BRASS_LIGHT, shackle.inflate(-4, -4), 1, border_radius=12)
        surf.fill((60, 40, 16), LOCK.move(2, 2))
        surf.fill(BRASS, LOCK)
        pygame.draw.rect(surf, BRASS_DARK, LOCK, 2)
        surf.fill(BRASS_LIGHT, (LOCK.x + 3, LOCK.y + 3, LOCK.w - 6, 1))
        active = self.can_answer and not open_
        for i, numeral in enumerate(fg.LOCK_SLOTS):
            rect = self.wheel_rect(i)
            self.hit(rect, lambda i=i: self._click_wheel(i))
            surf.fill((24, 16, 34), rect)
            pygame.draw.rect(surf, BRASS_DARK, rect, 1)
            for k in range(1, 4):                                     # the wheel's ridges, above and below
                surf.fill((54, 40, 60), (rect.x + 2, rect.y + k * 2, rect.w - 4, 1))
                surf.fill((54, 40, 60), (rect.x + 2, rect.bottom - 1 - k * 2, rect.w - 4, 1))
            draw_text(surf, numeral, (rect.x + 3, rect.y + 3), BRASS)                      # the wheel's number
            mark = self.marks[i] if not open_ else fg.COMBINATION[i]
            if mark is None:
                draw_text(surf, "?", rect.center, scale_color(Col.TEXT_MUTED, 0.7), anchor="center")
            else:
                image = symbol_image(mark, fit=40)
                surf.blit(image, image.get_rect(center=(rect.centerx, rect.centery + 4)))   # (clear of the numeral)
            if active and i == self.cursor:
                pulse = 0.6 + 0.4 * math.sin(self.time * 7)
                pygame.draw.rect(surf, scale_color(Col.CYAN, pulse), rect.inflate(4, 4), 1)
                tip = scale_color(Col.CYAN, pulse)
                pygame.draw.polygon(surf, tip, [(rect.centerx - 4, rect.y - 3), (rect.centerx + 4, rect.y - 3),
                                                (rect.centerx, rect.y - 7)])
                pygame.draw.polygon(surf, tip, [(rect.centerx - 4, rect.bottom + 2), (rect.centerx + 4, rect.bottom + 2),
                                                (rect.centerx, rect.bottom + 6)])
