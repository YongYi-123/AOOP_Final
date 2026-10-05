"""The arcade room scene, the placeholder minigame scene and the registry
that maps machines to their minigame scenes.

To plug in a real minigame, write a BaseScene subclass (scene_base.py) whose
constructor takes (game, machine), register it in MINIGAME_SCENES under the
machine id, and call `self.game.scenes.pop()` when the player quits.
"""
import math

import pygame

from ambience import AmbienceManager
from cat import CatNPC
from font import LINE_H, get_font
from gfx import lerp_color, scale_color, shade
from lofi_room import LofiRoom
from machine import ArcadeMachine
from player import Player
from retro_racer_scene import RetroRacerScene
from room import Room
from scene_base import BaseScene
from settings import (BACK_KEYS, BACKGROUND_STYLE, CAT_HOME, Col, INTERACT_FLASH, INTERACT_KEYS,
                      MACHINES, MOVE_KEYS, PLAYER_START, VIEW_H, VIEW_W)
from ui import (DialogueBox, InstructionBox, PromptBubble, draw_text,
                neon_panel, wrap_text)


# Background style name -> room class (see settings.BACKGROUND_STYLES)
ROOM_STYLES = {"lofi": LofiRoom, "neon": Room}


class ArcadeRoomScene(BaseScene):
    def __init__(self, game, style=BACKGROUND_STYLE):
        super().__init__(game)
        self.machines = [ArcadeMachine(data) for data in MACHINES]
        self.room = ROOM_STYLES[style](self.machines)
        self.player = Player(PLAYER_START)
        self.cat = CatNPC(CAT_HOME, spots=self.room.cat_spots)
        self.ambience = AmbienceManager()
        self.ambience.start()
        self.held = []          # movement keys currently held, in press order
        self.dialogue = None
        self.activating = None  # (machine, time left) while the E-flash plays
        self.nearby = None
        self.prompt = PromptBubble()
        self.instructions = InstructionBox()
        self.time = 0.0

    def on_resume(self):
        # Key-ups may have happened inside the minigame; start clean.
        self.held.clear()
        self.activating = None
        self.dialogue = None
        self.player.stop()
        self.ambience.resume()

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:
            self.held.clear()
        elif event.type == pygame.KEYUP and event.key in self.held:
            self.held.remove(event.key)

        if self.dialogue:
            self.dialogue.handle_event(event)
            return
        if event.type != pygame.KEYDOWN or self.activating:
            return
        if event.key in MOVE_KEYS and event.key not in self.held:
            self.held.append(event.key)
        elif event.key in INTERACT_KEYS and self.nearby:
            self.nearby.activate()
            self.activating = (self.nearby, INTERACT_FLASH)

    def open_dialogue(self, machine):
        self.dialogue = DialogueBox(
            machine.name, machine.description, ["Play", "Cancel"],
            on_choice=lambda choice: self._on_choice(machine, choice),
            accent=machine.accent, glow=machine.neon)

    def _on_choice(self, machine, choice):
        self.dialogue = None
        if choice == "Play":
            self.ambience.pause()
            self.game.scenes.push(create_minigame_scene(self.game, machine))

    def _direction(self):
        dx = dy = 0
        for key in self.held:
            vx, vy = MOVE_KEYS[key]
            dx, dy = dx + vx, dy + vy
        return max(-1, min(1, dx)), max(-1, min(1, dy))

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        self.room.update(dt)
        for m in self.machines:
            m.update(dt)

        if self.activating:
            machine, left = self.activating
            left -= dt
            self.activating = (machine, left)
            if left <= 0:
                self.activating = None
                self.open_dialogue(machine)

        busy = self.dialogue is not None or self.activating is not None
        if self.dialogue:
            self.dialogue.update(dt)
        self.player.update(dt, (0, 0) if busy else self._direction(), self.room.solids)
        self.cat.update(dt, self.player, self.room.solids)

        self.nearby = None if busy else self._find_nearby()
        for m in self.machines:
            m.highlight = m is self.nearby
        anchor = (int(self.player.x), int(self.player.y) - 22) if self.nearby else None
        self.prompt.update(dt, anchor)

    def _find_nearby(self):
        feet = self.player.feet
        close = [m for m in self.machines if m.zone.colliderect(feet)]
        return min(close, key=lambda m: abs(m.rect.centerx - self.player.x), default=None)

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        self.room.draw_background(surf)
        things = self.room.drawables() + [self.player, self.cat]
        things.sort(key=lambda t: t.sort_y)
        for thing in things:
            thing.draw_under(surf)
        for thing in things:
            thing.draw(surf)
        self.room.draw_lighting(surf)
        for m in self.machines:
            m.draw_glow(surf)

        self.prompt.draw(surf, self.time)
        self.instructions.draw(surf)
        if self.dialogue:
            self.dialogue.draw(surf)


class MinigamePlaceholderScene(BaseScene):
    """Stand-in for a machine's minigame: a synthwave-style title card in the
    machine's own neon colours. ESC returns to the arcade."""
    HORIZON = 132

    def __init__(self, game, machine):
        super().__init__(game)
        self.machine = machine
        self.time = 0.0
        neon, accent = machine.neon, machine.accent
        self.grid_color = scale_color(neon, 0.8)
        self.background = self._build_background(neon, accent)

        font = get_font()
        self.title = font.render_glow(machine.name, shade(accent, 0.6), neon, scale=3)
        self.panel = neon_panel(236, 108, accent, neon, 245).copy()
        draw_text(self.panel, "PROTOTYPE MINIGAME SCREEN", (10, 10), shade(accent, 0.4),
                  glow=scale_color(neon, 0.5))
        self.panel.fill(scale_color(accent, 0.6), (10, 21, 216, 1))
        y = 28
        for line in wrap_text(machine.description, 216):
            draw_text(self.panel, line, (10, y), Col.TEXT_MUTED)
            y += LINE_H
        draw_text(self.panel, "REAL GAME COMING SOON!", (10, y + 6), Col.TEXT)
        self.esc = font.render_glow("PRESS ESC TO RETURN TO ARCADE", Col.YELLOW,
                                    scale_color(Col.YELLOW, 0.35))
        self.cabinet = pygame.Surface((38, 64), pygame.SRCALPHA)
        self.cabinet_big = pygame.Surface((76, 128), pygame.SRCALPHA)

    def _build_background(self, neon, accent):
        bg = pygame.Surface((VIEW_W, VIEW_H))
        top, bottom = (8, 4, 20), scale_color(neon, 0.35)
        for y in range(self.HORIZON):                       # banded sky
            k = (y // 8 * 8) / self.HORIZON
            bg.fill(lerp_color(top, bottom, k), (0, y, VIEW_W, 1))
        sun_c = (VIEW_W // 2, self.HORIZON)
        for r, c in ((46, scale_color(neon, 0.8)), (40, accent), (30, shade(accent, 0.4))):
            pygame.draw.circle(bg, c, sun_c, r, draw_top_left=True, draw_top_right=True)
        for i, y in enumerate(range(self.HORIZON - 26, self.HORIZON, 6)):  # sun stripes
            bg.fill(lerp_color(top, bottom, y / self.HORIZON), (0, y, VIEW_W, 1 + i // 2))
        bg.fill((6, 3, 16), (0, self.HORIZON, VIEW_W, VIEW_H - self.HORIZON))
        bg.fill(accent, (0, self.HORIZON, VIEW_W, 1))
        for sx, sy in ((30, 20), (80, 50), (140, 14), (260, 30), (330, 60), (370, 18), (220, 70)):
            bg.fill(Col.TEXT, (sx, sy, 1, 1))
        return bg

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in BACK_KEYS:
            self.game.scenes.pop()

    def update(self, dt):
        self.time += dt
        self.machine.update(dt)

    def draw(self, surf):
        surf.blit(self.background, (0, 0))
        self._draw_grid(surf)

        bob = int(math.sin(self.time * 2.2) * 2)
        surf.blit(self.title, self.title.get_rect(midtop=(VIEW_W // 2, 20 + bob)))

        # cabinet preview, redrawn into reusable surfaces (no per-frame allocs)
        self.cabinet.fill((0, 0, 0, 0))
        self.machine.draw_at(self.cabinet, (1, 1))
        pygame.transform.scale(self.cabinet, self.cabinet_big.get_size(), self.cabinet_big)
        surf.blit(self.cabinet_big, (34, 132 - bob))

        surf.blit(self.panel, (136, 146))
        if int(self.time * 2.5) % 2 == 0:
            surf.blit(self.esc, self.esc.get_rect(midbottom=(136 + 118, 146 + 100)))

    def _draw_grid(self, surf):
        h0, depth = self.HORIZON, VIEW_H - self.HORIZON
        cx = VIEW_W // 2
        for x in range(-VIEW_W, VIEW_W * 2, 40):
            pygame.draw.line(surf, self.grid_color, (cx + (x - cx) * 0.08, h0), (x, VIEW_H))
        phase = (self.time * 0.8) % 1.0
        for k in range(12):
            d = (k + phase) / 12
            y = h0 + int(depth * d * d)
            surf.fill(self.grid_color, (0, y, VIEW_W, 1))


# Machine id -> scene class. Anything not listed uses the placeholder, so real
# minigames can be dropped in one at a time.
MINIGAME_SCENES = {"retro_racer": RetroRacerScene}


def create_minigame_scene(game, machine):
    scene_cls = MINIGAME_SCENES.get(machine.id, MinigamePlaceholderScene)
    return scene_cls(game, machine)
