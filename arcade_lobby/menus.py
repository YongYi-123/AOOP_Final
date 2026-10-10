"""The startup flow: TITLE -> PLAYER COUNT -> PROFILE SELECT (-> P2 PROFILE
SELECT) -> ARCADE HUB.

StartupFlow remembers the choices and swaps the screens; each screen is a
BaseScene that only reports what was picked. The profile list has no limit,
so it scrolls; a profile is created from the list ("+ NEW PROFILE" -> ENTER
NAME -> CREATE) and deleted only behind a NO-by-default confirmation.
"""
import math

import pygame

from gfx import lerp_color, scale_color, shade
from local_session import LocalSession
from profile_manager import ProfileError, normalize_name
from scene_base import BaseScene
from settings import (BACK_KEYS, CONFIRM_KEYS, NEXT_KEYS, PREV_KEYS, PROFILE_NAME_MAX,
                      TITLE, VIEW_H, VIEW_W, Col)
from ui import DialogueBox, draw_text, neon_panel

NEW_PROFILE = "+ NEW PROFILE"
VISIBLE_ROWS = 6
ROW_H = 15
DELETE_KEYS = (pygame.K_DELETE,)
HORIZON = 162

_backdrop = None


def menu_backdrop():
    """The synthwave sunset behind every menu (built once)."""
    global _backdrop
    if _backdrop is None:
        bg = pygame.Surface((VIEW_W, VIEW_H))
        top, bottom = (8, 4, 20), scale_color(Col.MAGENTA, 0.4)
        for y in range(HORIZON):
            bg.fill(lerp_color(top, bottom, (y // 8 * 8) / HORIZON), (0, y, VIEW_W, 1))
        centre = (VIEW_W // 2, HORIZON)
        for r, c in ((52, scale_color(Col.MAGENTA, 0.8)), (46, Col.YELLOW), (36, shade(Col.YELLOW, 0.4))):
            pygame.draw.circle(bg, c, centre, r, draw_top_left=True, draw_top_right=True)
        for i, y in enumerate(range(HORIZON - 30, HORIZON, 6)):
            bg.fill(lerp_color(top, bottom, y / HORIZON), (0, y, VIEW_W, 1 + i // 2))
        bg.fill((6, 3, 16), (0, HORIZON, VIEW_W, VIEW_H - HORIZON))
        bg.fill(Col.CYAN, (0, HORIZON, VIEW_W, 1))
        grid = scale_color(Col.CYAN, 0.45)
        for x in range(-VIEW_W, VIEW_W * 2, 40):
            pygame.draw.line(bg, grid, (VIEW_W // 2 + (x - VIEW_W // 2) * 0.08, HORIZON), (x, VIEW_H))
        for k in range(1, 9):
            bg.fill(grid, (0, HORIZON + int((VIEW_H - HORIZON) * (k / 8) ** 2), VIEW_W, 1))
        for sx, sy in ((30, 20), (80, 50), (140, 14), (260, 30), (330, 60), (370, 18), (220, 70)):
            bg.fill(Col.TEXT, (sx, sy, 1, 1))
        _backdrop = bg
    return _backdrop


def draw_centered(surf, text, y, color, scale=1, glow=None):
    return draw_text(surf, text, (VIEW_W // 2, y), color, scale, anchor="midtop", glow=glow)


class MenuScene(BaseScene):
    """Shared plumbing: the backdrop, a clock and up / down / confirm / back keys."""

    def __init__(self, game, flow):
        super().__init__(game)
        self.flow = flow
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        surf.blit(menu_backdrop(), (0, 0))

    @staticmethod
    def move_of(key):
        if key in PREV_KEYS:
            return -1
        return 1 if key in NEXT_KEYS else 0


# ------------------------------------------------------------------ title
class TitleScene(MenuScene):
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in CONFIRM_KEYS:
            self.flow.show_player_count()

    def draw(self, surf):
        super().draw(surf)
        bob = int(math.sin(self.time * 2) * 2)
        words = TITLE.upper().split(" ", 1)
        draw_centered(surf, words[0], 40 + bob, shade(Col.CYAN, 0.5), 5, scale_color(Col.CYAN, 0.6))
        draw_centered(surf, words[1] if len(words) > 1 else "", 84 + bob, shade(Col.MAGENTA, 0.5), 3,
                      scale_color(Col.MAGENTA, 0.7))
        if int(self.time * 2.5) % 2 == 0:
            draw_centered(surf, "PRESS E OR ENTER", 196, Col.YELLOW, 1, scale_color(Col.YELLOW, 0.35))
        draw_centered(surf, "1-2 PLAYERS  LOCAL", VIEW_H - 20, scale_color(Col.TEXT_MUTED, 0.8))


# ------------------------------------------------------------------ player count
class PlayerCountScene(MenuScene):
    OPTIONS = (("1 PLAYER", 1), ("2 PLAYERS", 2))

    def __init__(self, game, flow, selected=1):
        super().__init__(game, flow)
        self.selected = 0 if selected == 1 else 1

    @property
    def count(self):
        return self.OPTIONS[self.selected][1]

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        step = self.move_of(event.key)
        if step:
            self.selected = (self.selected + step) % len(self.OPTIONS)
        elif event.key in CONFIRM_KEYS:
            self.flow.choose_count(self.count)
        elif event.key in BACK_KEYS:
            self.flow.show_title()

    def draw(self, surf):
        super().draw(surf)
        panel = neon_panel(150, 82, Col.CYAN, Col.MAGENTA, 246)
        rect = panel.get_rect(center=(VIEW_W // 2, 128))
        surf.blit(panel, rect)
        draw_centered(surf, "PLAYERS", rect.y + 8, shade(Col.CYAN, 0.5), 2, scale_color(Col.MAGENTA, 0.8))
        for i, (label, _) in enumerate(self.OPTIONS):
            y = rect.y + 34 + i * 17
            chosen = i == self.selected
            if chosen:
                surf.fill((*scale_color(Col.CYAN, 0.25),), (rect.x + 14, y - 3, rect.w - 28, 13))
                draw_text(surf, ">", (rect.x + 20, y), Col.YELLOW)
            draw_text(surf, label, (rect.x + 34, y), Col.TEXT if chosen else Col.TEXT_MUTED)
        draw_centered(surf, "UP/DOWN SELECT  E OK  ESC BACK", VIEW_H - 20, scale_color(Col.TEXT_MUTED, 0.8))


# ------------------------------------------------------------------ profile select
def scroll_window(selected, top, total, rows):
    """The first visible row after moving the selection: it only scrolls when
    the selection would leave the window of `rows` rows."""
    if total <= rows:
        return 0
    if selected < top:
        top = selected
    elif selected >= top + rows:
        top = selected - rows + 1
    return max(0, min(top, total - rows))


class NameEntry:
    """The ENTER NAME box: a short name, trimmed, never blank."""

    def __init__(self):
        self.text = ""
        self.error = ""

    def type(self, char):
        if (len(self.text) < PROFILE_NAME_MAX and char and char.isprintable()
                and (char.isalnum() or char in " .'!?-")
                and not (char == " " and (not self.text or self.text.endswith(" ")))):
            self.text += char.upper()
            self.error = ""

    def backspace(self):
        self.text = self.text[:-1]
        self.error = ""


class ProfileSelectScene(MenuScene):
    """Pick the profile for player `slot` (0 = P1). Profiles in `taken` (ids
    already chosen) cannot be chosen again."""

    def __init__(self, game, flow, slot=0, taken=(), highlight=None):
        super().__init__(game, flow)
        self.manager = flow.manager
        self.slot = slot
        self.taken = set(taken)
        self.top = 0
        self.entry = None           # NameEntry while a name is being typed
        self.dialog = None          # the delete confirmation
        self.message = ""
        self.message_time = 0.0
        self.refresh(highlight)

    # ------------------------------------------------------------ list
    @property
    def title(self):
        return f"P{self.slot + 1} SELECT PROFILE" if self.flow.count > 1 else "SELECT PROFILE"

    @property
    def infos(self):
        """Recently used profiles first (most recent on top), then the rest in creation order."""
        infos = self.manager.list_profiles()
        rank = {pid: i for i, pid in enumerate(self.manager.recent_ids)}
        return sorted(infos, key=lambda i: rank.get(i.profile_id, len(rank)))

    @property
    def total(self):
        return len(self.infos) + 1          # + NEW PROFILE

    @property
    def on_new_profile(self):
        return self.selected == len(self.infos)

    @property
    def selected_info(self):
        infos = self.infos
        return infos[self.selected] if self.selected < len(infos) else None

    def refresh(self, highlight=None):
        """Rebuild the selection after the list changed. Starts on `highlight`
        (a profile id), else the most recently used free profile."""
        infos = self.infos
        want = highlight or self.manager.most_recent(exclude=self.taken)
        self.selected = next((i for i, info in enumerate(infos) if info.profile_id == want), 0)
        if want is None and infos:
            self.selected = next((i for i, info in enumerate(infos)
                                  if info.profile_id not in self.taken), 0)
        self.selected = min(self.selected, self.total - 1)
        self.top = scroll_window(self.selected, 0, self.total, VISIBLE_ROWS)

    def move(self, step):
        self.selected = (self.selected + step) % self.total
        self.top = scroll_window(self.selected, self.top, self.total, VISIBLE_ROWS)

    def jump(self, key):
        """HOME / END (first profile / + NEW PROFILE), PAGE UP / DOWN (a screenful)."""
        target = {pygame.K_HOME: 0, pygame.K_END: self.total - 1,
                  pygame.K_PAGEUP: self.selected - VISIBLE_ROWS,
                  pygame.K_PAGEDOWN: self.selected + VISIBLE_ROWS}[key]
        self.selected = max(0, min(self.total - 1, target))
        self.top = scroll_window(self.selected, self.top, self.total, VISIBLE_ROWS)

    def say(self, text):
        self.message, self.message_time = text, 2.0

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if self.dialog:
            self.dialog.handle_event(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        if self.entry is not None:
            self._entry_key(event)
            return
        key = event.key
        step = self.move_of(key)
        if step:
            self.move(step)
        elif key in (pygame.K_HOME, pygame.K_END, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            self.jump(key)
        elif key in CONFIRM_KEYS:
            self._confirm()
        elif key in DELETE_KEYS:
            self._ask_delete()
        elif key in BACK_KEYS:
            self.flow.back_from_profile_select(self.slot)

    def _confirm(self):
        if self.on_new_profile:
            self.entry = NameEntry()
            return
        info = self.selected_info
        if info.profile_id in self.taken:
            self.say("ALREADY PLAYING AS P1")
            return
        self.flow.choose_profile(self.slot, info.profile_id)

    def _entry_key(self, event):
        entry, key = self.entry, event.key
        if key in BACK_KEYS:
            self.entry = None
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._create(entry)
        elif key == pygame.K_BACKSPACE:
            entry.backspace()
        else:
            entry.type(event.unicode)

    def _create(self, entry):
        try:
            name = normalize_name(entry.text)
            profile = self.manager.create_profile(name)
        except ProfileError as e:
            entry.error = ("ENTER A NAME" if not entry.text.strip() else
                           "NAME ALREADY USED" if "already exists" in str(e) else "PICK ANOTHER NAME")
            return
        self.entry = None
        self.refresh(profile.profile_id)
        self.say(f"CREATED {name.upper()}")

    def _ask_delete(self):
        info = self.selected_info
        if info is None:
            return
        if info.profile_id in self.taken:
            self.say("P1 IS PLAYING AS THIS PROFILE")
            return
        self.dialog = DialogueBox(
            "DELETE PROFILE?", "THIS CANNOT BE UNDONE.", ["NO, KEEP IT", "YES, DELETE IT"],
            on_choice=lambda choice: self._on_delete_choice(info.profile_id, choice),
            accent=Col.MAGENTA, glow=Col.PURPLE, details=[(info.display_name.upper(), Col.YELLOW)],
            input_delay=0.4)

    def _on_delete_choice(self, profile_id, choice):
        self.dialog = None
        if choice == "YES, DELETE IT":
            self.manager.delete_profile(profile_id)
            self.refresh()
            self.say("PROFILE DELETED")

    # ------------------------------------------------------------ frame
    def update(self, dt):
        super().update(dt)
        self.message_time = max(0.0, self.message_time - dt)
        if self.dialog:
            self.dialog.update(dt)

    def draw(self, surf):
        super().draw(surf)
        infos = self.infos
        w, h = 236, 40 + VISIBLE_ROWS * ROW_H + 32
        panel = neon_panel(w, h, Col.CYAN, Col.MAGENTA, 246)
        rect = panel.get_rect(center=(VIEW_W // 2, VIEW_H // 2 - 6))
        surf.blit(panel, rect)
        draw_text(surf, self.title, (rect.centerx, rect.y + 8), shade(Col.CYAN, 0.5), 2,
                  anchor="midtop", glow=scale_color(Col.MAGENTA, 0.8))
        surf.fill(scale_color(Col.CYAN, 0.6), (rect.x + 12, rect.y + 27, w - 24, 1))
        recent = self.manager.most_recent()
        for row in range(VISIBLE_ROWS):
            index = self.top + row
            if index >= self.total:
                break
            y = rect.y + 34 + row * ROW_H
            chosen = index == self.selected
            if chosen:
                surf.fill(scale_color(Col.CYAN, 0.22), (rect.x + 10, y - 3, w - 20, ROW_H - 1))
                surf.fill(Col.CYAN, (rect.x + 10, y - 3, 2, ROW_H - 1))
                draw_text(surf, ">", (rect.x + 16, y + 1), Col.YELLOW)
            if index < len(infos):
                info = infos[index]
                used = info.profile_id in self.taken
                color = scale_color(Col.TEXT_MUTED, 0.7) if used else (Col.TEXT if chosen else Col.TEXT_MUTED)
                draw_text(surf, info.display_name, (rect.x + 28, y + 1), color)
                if used:
                    draw_text(surf, "IN USE", (rect.right - 14, y + 1), Col.MAGENTA, anchor="topright")
                elif info.profile_id == recent:
                    draw_text(surf, "LAST", (rect.right - 14, y + 1), shade(Col.YELLOW, -0.2), anchor="topright")
            else:
                draw_text(surf, NEW_PROFILE, (rect.x + 28, y + 1), Col.GREEN if chosen else
                          scale_color(Col.GREEN, 0.7))
        cx = rect.right - 10                                 # scroll arrows + position
        if self.top > 0:
            pygame.draw.polygon(surf, Col.YELLOW, [(cx, rect.y + 31), (cx - 3, rect.y + 34), (cx + 3, rect.y + 34)])
        if self.top + VISIBLE_ROWS < self.total:
            by = rect.y + 34 + VISIBLE_ROWS * ROW_H - 2
            pygame.draw.polygon(surf, Col.YELLOW, [(cx, by + 3), (cx - 3, by), (cx + 3, by)])
        draw_text(surf, f"{min(self.selected + 1, len(infos))}/{len(infos)}", (rect.x + 12, rect.bottom - 27),
                  scale_color(Col.TEXT_MUTED, 0.75))
        draw_text(surf, "UP/DOWN  E OK  END NEW  DEL DELETE", (rect.centerx, rect.bottom - 12),
                  scale_color(Col.TEXT_MUTED, 0.75), anchor="midtop")
        if self.message_time > 0:
            draw_centered(surf, self.message, rect.bottom + 6, Col.YELLOW, 1, scale_color(Col.YELLOW, 0.35))
        if self.entry is not None:
            self._draw_entry(surf)
        if self.dialog:
            self.dialog.draw(surf)

    def _draw_entry(self, surf):
        entry = self.entry
        panel = neon_panel(190, 76, Col.GREEN, Col.CYAN, 255)
        rect = panel.get_rect(center=(VIEW_W // 2, VIEW_H // 2))
        surf.blit(panel, rect)
        draw_text(surf, "ENTER NAME", (rect.centerx, rect.y + 8), shade(Col.GREEN, 0.5), 2,
                  anchor="midtop", glow=scale_color(Col.GREEN, 0.5))
        box = pygame.Rect(rect.x + 14, rect.y + 28, rect.w - 28, 14)
        surf.fill((6, 4, 14), box)
        pygame.draw.rect(surf, scale_color(Col.GREEN, 0.7), box, 1)
        cursor = "_" if int(self.time * 2.5) % 2 == 0 else " "
        draw_text(surf, entry.text + cursor, (box.x + 4, box.y + 4), Col.TEXT)
        if entry.error:
            draw_centered(surf, entry.error, rect.y + 46, Col.MAGENTA)
        draw_centered(surf, "ENTER CREATE  ESC CANCEL", rect.bottom - 14, scale_color(Col.TEXT_MUTED, 0.75))


# ------------------------------------------------------------------ the flow
class StartupFlow:
    """TITLE -> PLAYER COUNT -> PROFILE SELECT (x1 or x2) -> hub."""

    def __init__(self, game, manager):
        self.game = game
        self.manager = manager
        self.count = manager.last_player_count
        self.chosen = []                    # profile ids picked so far, P1 first

    def _show(self, scene, fade=True):
        scenes = self.game.scenes
        if scenes.stack:
            scenes.replace(scene, fade)
        else:
            scenes.push(scene, fade=False)

    def begin(self):
        self._show(TitleScene(self.game, self), fade=False)

    def show_title(self):
        self._show(TitleScene(self.game, self))

    def show_player_count(self):
        self._show(PlayerCountScene(self.game, self, self.count))

    def choose_count(self, count):
        self.count = count
        self.chosen = []
        self._show(ProfileSelectScene(self.game, self, 0))

    def choose_profile(self, slot, profile_id):
        if profile_id in self.chosen[:slot]:        # one profile cannot be two players
            return
        self.chosen = self.chosen[:slot] + [profile_id]
        if len(self.chosen) < self.count:
            self._show(ProfileSelectScene(self.game, self, 1, taken=self.chosen))
        else:
            self.finish()

    def back_from_profile_select(self, slot):
        if slot == 0:
            self.chosen = []
            self.show_player_count()
        else:
            first = self.chosen[0] if self.chosen else None
            self.chosen = []
            self._show(ProfileSelectScene(self.game, self, 0, highlight=first))

    def finish(self):
        profiles = [self.manager.load_profile(pid) for pid in self.chosen]
        self.manager.record_session(profiles, self.count)
        self.game.start_session(LocalSession(profiles), from_menu=True)
