"""The DISPLAY page of the F4 settings screen: window mode, window size, scaling, with APPLY / CANCEL, a
confirmation countdown that puts the old display back if nobody confirms, and RESTORE DEFAULTS.

The page edits a *draft*; nothing changes until APPLY. After APPLY the new display is live and a KEEP / REVERT
box counts down from CONFIRM_SECONDS - if the new mode left the player with an unreadable screen they only have
to wait. Dragging the real window edges stays possible (and is shown in the SIZE row as CURRENT).
"""
import pygame

from display import DEFAULTS, MODES, SCALINGS, DisplaySettings
from gfx import scale_color
from settings import BACK_KEYS, CONFIRM_KEYS, VIEW_W, Col
from ui import dim_screen, draw_text

CONFIRM_SECONDS = 12
ROWS = ("MODE", "SIZE", "SCALING", "APPLY", "CANCEL", "RESTORE DEFAULTS", "BACK")
GOLD = Col.YELLOW
MODE_LABELS = {"windowed": "WINDOWED", "borderless": "BORDERLESS", "fullscreen": "FULLSCREEN"}
SCALING_LABELS = {"integer": "INTEGER", "fit": "FIT TO WINDOW"}
UP, DOWN = (pygame.K_UP, pygame.K_w), (pygame.K_DOWN, pygame.K_s)
LEFT, RIGHT = (pygame.K_LEFT, pygame.K_a), (pygame.K_RIGHT, pygame.K_d)
TOP, ROW_H = 54, 25


class DisplayPage:
    def __init__(self, scene):
        self.scene = scene
        self.row = 0
        self.confirm_left = 0.0                 # > 0 while the KEEP / REVERT box is up
        self.previous = None                    # the settings to go back to
        self.sync()

    @property
    def display(self):
        return self.scene.game.display

    @property
    def confirming(self):
        return self.confirm_left > 0

    # ------------------------------------------------------------ draft
    def sync(self):
        """The draft starts as the display as it is now."""
        s = self.display.settings
        self.mode, self.scaling = s.mode, s.scaling
        self.size = tuple(self.display.windowed_size)

    def sizes(self):
        return self.display.presets()

    def draft(self):
        return DisplaySettings(self.mode, self.scaling, tuple(self.size))

    def current(self):
        s = self.display.settings
        return DisplaySettings(s.mode, s.scaling, tuple(self.display.windowed_size))

    def cycle(self, row, step):
        if row == 0:
            self.mode = MODES[(MODES.index(self.mode) + step) % len(MODES)]
            if self.mode != "windowed":
                self.display.preferred_fullscreen = self.mode
        elif row == 1 and self.mode == "windowed":
            sizes = self.sizes()
            i = sizes.index(self.size) if self.size in sizes else 0
            self.size = sizes[(i + step) % len(sizes)]
        elif row == 2:
            self.scaling = SCALINGS[(SCALINGS.index(self.scaling) + step) % len(SCALINGS)]

    # ------------------------------------------------------------ actions
    def activate(self, row):
        name = ROWS[row]
        if name in ("MODE", "SIZE", "SCALING"):
            self.cycle(row, 1)
        elif name == "APPLY":
            self.apply(self.draft())
        elif name == "CANCEL":
            self.sync()
            self.scene.say("CHANGES DISCARDED")
        elif name == "RESTORE DEFAULTS":
            self.mode, self.scaling, self.size = DEFAULTS.mode, DEFAULTS.scaling, DEFAULTS.size
            self.apply(self.draft())
        elif name == "BACK":
            self.scene.close()

    def apply(self, settings):
        if settings == self.current():
            self.scene.say("NOTHING TO APPLY")
            return False
        self.previous = self.current()
        ok = self.display.apply(settings)
        self.sync()
        if not ok:
            self.scene.say("DISPLAY CHANGE FAILED - SAFE WINDOW", Col.MAGENTA)
            self.previous = None
            return False
        self.confirm_left = CONFIRM_SECONDS
        return True

    def keep(self):
        self.confirm_left, self.previous = 0.0, None
        self.display.save()
        self.scene.say("DISPLAY SETTINGS SAVED")

    def revert(self):
        previous, self.confirm_left, self.previous = self.previous, 0.0, None
        if previous is not None:
            self.display.apply(previous)
            self.sync()
            self.scene.say("REVERTED TO THE PREVIOUS DISPLAY", Col.YELLOW)

    def update(self, dt):
        if self.confirming:
            self.confirm_left -= dt
            if self.confirm_left <= 0:
                self.revert()

    # ------------------------------------------------------------ input
    def row_rect(self, row):
        return pygame.Rect(16, TOP + row * ROW_H, 368, ROW_H - 4)

    def arrow_rects(self, row):
        r = self.row_rect(row)
        return pygame.Rect(150, r.y + 2, 12, r.h - 4), pygame.Rect(r.right - 20, r.y + 2, 12, r.h - 4)

    def keep_rect(self):
        return pygame.Rect(VIEW_W // 2 - 90, 168, 80, 16)

    def revert_rect(self):
        return pygame.Rect(VIEW_W // 2 + 10, 168, 80, 16)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            key = event.key
            if self.confirming:
                if key in CONFIRM_KEYS:
                    self.keep()
                elif key in BACK_KEYS or key == pygame.K_F4:
                    self.revert()
                return
            if key in BACK_KEYS or key == pygame.K_F4:
                self.scene.close()
            elif key in UP:
                self.row = (self.row - 1) % len(ROWS)
            elif key in DOWN:
                self.row = (self.row + 1) % len(ROWS)
            elif key in LEFT:
                self.cycle(self.row, -1)
            elif key in RIGHT:
                self.cycle(self.row, 1)
            elif key in CONFIRM_KEYS:
                self.activate(self.row)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.scene.mouse_pos(event.pos)
            if self.confirming:
                if self.keep_rect().collidepoint(pos):
                    self.keep()
                elif self.revert_rect().collidepoint(pos):
                    self.revert()
                return
            for row in range(len(ROWS)):
                if self.row_rect(row).collidepoint(pos):
                    self.row = row
                    back, fwd = self.arrow_rects(row)
                    if row < 3 and back.collidepoint(pos):
                        self.cycle(row, -1)
                    else:
                        self.activate(row)
                    return
        elif event.type == pygame.MOUSEWHEEL and not self.confirming and self.row < 3:
            self.cycle(self.row, 1 if event.y > 0 else -1)

    # ------------------------------------------------------------ drawing
    def value_text(self, row):
        if row == 0:
            return MODE_LABELS[self.mode]
        if row == 1:
            if self.mode != "windowed":
                w, h = self.display.desktop_size()
                return f"DESKTOP {w}X{h}"
            w, h = self.size
            return f"{w} X {h}" + ("  (CURRENT)" if self.size == tuple(self.display.windowed_size) else "")
        return SCALING_LABELS[self.scaling]

    def draw(self, surf):
        t = self.scene.time
        for row, name in enumerate(ROWS):
            rect = self.row_rect(row)
            selected = row == self.row and not self.confirming
            surf.fill(scale_color(GOLD, 0.28) if selected else (18, 12, 40), rect)
            if selected:
                pygame.draw.rect(surf, scale_color(GOLD, 0.65 + 0.35 * abs(((t * 3) % 2) - 1)), rect, 1)
            dim = row == 1 and self.mode != "windowed"
            if row < 3:
                draw_text(surf, name, (rect.x + 8, rect.centery - 3),
                          Col.TEXT_MUTED if dim or not selected else Col.TEXT)
                back, fwd = self.arrow_rects(row)
                if not dim:
                    draw_text(surf, "<", back.center, GOLD if selected else Col.TEXT_MUTED, anchor="center")
                    draw_text(surf, ">", fwd.center, GOLD if selected else Col.TEXT_MUTED, anchor="center")
                draw_text(surf, self.value_text(row), (rect.centerx + 22, rect.centery - 3),
                          Col.TEXT_MUTED if dim else Col.CYAN, anchor="midtop")
            else:
                changed = name == "APPLY" and self.draft() != self.current()
                draw_text(surf, name, rect.center, GOLD if changed else (Col.TEXT if selected else Col.TEXT_MUTED),
                          anchor="center")
        live = self.display.layout
        w, h = live.window
        info = (f"WINDOW {w}X{h}   VIEW {live.rect.w}X{live.rect.h}   "
                f"{'EXACT ' + str(live.scale) + 'X' if live.exact else 'SCALED %.2fX' % (live.rect.w / 400)}")
        draw_text(surf, info, (VIEW_W // 2, 232), Col.TEXT_MUTED, anchor="midtop")
        if self.confirming:
            dim_screen(surf, 150)
            box = pygame.Rect(VIEW_W // 2 - 120, 112, 240, 84)
            surf.fill((20, 12, 46), box)
            pygame.draw.rect(surf, GOLD, box, 1)
            draw_text(surf, "KEEP THESE DISPLAY SETTINGS?", (box.centerx, box.y + 10), Col.TEXT, anchor="midtop")
            draw_text(surf, f"REVERTING IN {int(self.confirm_left) + 1}", (box.centerx, box.y + 28), Col.YELLOW,
                      anchor="midtop")
            for rect, label, ok in ((self.keep_rect(), "KEEP (E)", True), (self.revert_rect(), "REVERT (ESC)", False)):
                surf.fill((34, 90, 60) if ok else (120, 40, 70), rect)
                draw_text(surf, label, rect.center, Col.TEXT, anchor="center")
