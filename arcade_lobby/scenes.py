"""The placeholder minigame scene and the registry that maps machines to
their minigame scenes. (The rooms that host the machines are in room_scene.py,
home_room.py, arcade_floor.py and prize_plaza.py.)

To plug in a real minigame, write a MinigameScene subclass (minigame.py) whose
constructor takes (game, machine), register it in MINIGAME_SCENES under the
machine's game id, override get_reward() with its scoring, and call
`self.game.scenes.pop()` when the player quits.
"""
import math

import pygame

from font import LINE_H, get_font
from gfx import lerp_color, scale_color, shade
from minigame import MinigameScene
from retro_racer_scene import RetroRacerScene
from settings import BACK_KEYS, Col, VIEW_H, VIEW_W
from ui import draw_text, neon_panel, wrap_text


class MinigamePlaceholderScene(MinigameScene):
    """Stand-in for a machine's minigame: a synthwave-style title card in the
    machine's own neon colours. ESC returns to the arcade (and pays the
    temporary flat reward from MinigameScene.get_reward)."""
    HORIZON = 132

    def __init__(self, game, machine):
        super().__init__(game, machine)
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
        # SceneManager ignores input during the wipe, so ESC pops only once.
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


# Game id (a machine's "game_id", by default its id) -> scene class. Anything not listed uses the placeholder, so real
# minigames can be dropped in one at a time.
MINIGAME_SCENES = {"retro_racer": RetroRacerScene}


def create_minigame_scene(game, machine):
    scene_cls = MINIGAME_SCENES.get(machine.game_id, MinigamePlaceholderScene)
    return scene_cls(game, machine)
