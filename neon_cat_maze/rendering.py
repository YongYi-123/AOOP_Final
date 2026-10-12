"""Draws NEON CAT MAZE onto a 400x300 canvas with the lobby's bitmap font and neon palette."""
import math

import pygame

from arcade_lobby.font import get_font
from . import art
from . import config as cfg
from .mazes import COLS, ROWS

CYAN, PINK, GOLD, GREEN, WHITE = art.CYAN, art.PINK, art.GOLD, art.GREEN, art.WHITE
MUTED, PANEL, NAVY = (140, 130, 190), (14, 9, 40), (9, 6, 28)
TILE = cfg.TILE
OX, OY = cfg.MAZE_ORIGIN
ROBOT_TINT = {"patrol": (255, 150, 60), "chase": (255, 70, 110), "ambush": (170, 110, 255)}


def tile_center(x, y):
    """Canvas pixel of the centre of (fractional) tile coordinates."""
    return OX + round(x * TILE + TILE / 2), OY + round(y * TILE + TILE / 2)


class Renderer:
    def __init__(self):
        self.font = get_font()
        self.mazes = {}
        self.backdrop = self._backdrop()
        self.dim = pygame.Surface((cfg.FIELD_W, cfg.FIELD_H), pygame.SRCALPHA)
        self.dim.fill((8, 4, 24, 175))
        self.record = None                      # tests set this to a list to collect every text rectangle drawn

    # ------------------------------------------------------------ static art
    @staticmethod
    def _backdrop():
        surf = pygame.Surface((cfg.FIELD_W, cfg.FIELD_H))
        for y in range(0, cfg.FIELD_H, 4):
            k = y / cfg.FIELD_H
            surf.fill((int(8 + 14 * k), int(5 + 6 * k), int(30 + 30 * k)), (0, y, cfg.FIELD_W, 4))
        for x in range(0, cfg.FIELD_W, 16):                       # a faint city-grid floor
            surf.fill((20, 14, 52), (x, 0, 1, cfg.FIELD_H))
        for y in range(0, cfg.FIELD_H, 16):
            surf.fill((20, 14, 52), (0, y, cfg.FIELD_W, 1))
        return surf

    def maze_surface(self, maze):
        """The walls of one maze, drawn once: dark blocks with a glowing neon line wherever a wall meets floor."""
        surf = self.mazes.get(maze.name)
        if surf is not None:
            return surf
        surf = pygame.Surface((COLS * TILE, ROWS * TILE), pygame.SRCALPHA)
        wall, edge = maze.wall_color, maze.edge_color
        soft = tuple(int(c * 0.38) for c in edge)
        for r in range(ROWS):
            for c in range(COLS):
                x, y = c * TILE, r * TILE
                if (c, r) in maze.walls:
                    surf.fill(wall, (x, y, TILE, TILE))
                    continue
                surf.fill((10, 6, 30, 200), (x, y, TILE, TILE))
        for (c, r) in maze.walls:
            x, y = c * TILE, r * TILE
            for dx, dy, rect, rect2 in ((0, -1, (x, y, TILE, 1), (x, y + 1, TILE, 1)),
                                        (0, 1, (x, y + TILE - 1, TILE, 1), (x, y + TILE - 2, TILE, 1)),
                                        (-1, 0, (x, y, 1, TILE), (x + 1, y, 1, TILE)),
                                        (1, 0, (x + TILE - 1, y, 1, TILE), (x + TILE - 2, y, 1, TILE))):
                n = (c + dx, r + dy)
                if 0 <= n[0] < COLS and 0 <= n[1] < ROWS and n not in maze.walls:
                    surf.fill(edge, rect)
                    surf.fill(soft, rect2)
        for (c, r) in maze.den:                                   # the robot den: a tinted floor and a pink gate
            surf.fill((40, 14, 60, 255), (c * TILE, r * TILE, TILE, TILE))
        gx, gy = maze.gate
        for i in range(0, TILE, 4):
            surf.fill(maze.accent_color, (gx * TILE + i, gy * TILE + TILE // 2, 2, 1))
        self.mazes[maze.name] = surf
        return surf

    # ------------------------------------------------------------ text helpers
    def text(self, surface, text, pos, color=CYAN, scale=1, anchor="center"):
        image = self.font.render_glow(str(text), color, (35, 20, 65), scale)
        rect = image.get_rect(**{anchor: pos})
        surface.blit(image, rect)
        if self.record is not None:
            self.record.append((str(text), rect))

    def plain(self, surface, text, pos, color=CYAN, scale=1, anchor="topleft"):
        image = self.font.render(str(text), color, scale)
        rect = image.get_rect(**{anchor: pos})
        surface.blit(image, rect)
        if self.record is not None:
            self.record.append((str(text), rect))

    def panel(self, surface, rect, border=CYAN, inner=PINK):
        rect = pygame.Rect(rect)
        pygame.draw.rect(surface, (*PANEL, 235) if surface.get_flags() & pygame.SRCALPHA else PANEL, rect, border_radius=2)
        pygame.draw.rect(surface, border, rect, 1, border_radius=2)
        pygame.draw.rect(surface, tuple(int(c * 0.55) for c in inner), rect.inflate(-4, -4), 1)
        for cx, cy in ((rect.x + 1, rect.y + 1), (rect.right - 4, rect.y + 1), (rect.x + 1, rect.bottom - 2), (rect.right - 4, rect.bottom - 2)):
            surface.fill(GOLD, (cx, cy, 3, 1))
        return rect

    def menu(self, surface, items, cursor, top, gap=15, t=0.0):
        for i, label in enumerate(items):
            y = top + i * gap
            if i == cursor:
                self.text(surface, f"> {label} <", (cfg.FIELD_W // 2, y), GOLD)
            else:
                self.text(surface, label, (cfg.FIELD_W // 2, y), MUTED)

    # ------------------------------------------------------------ frame
    def draw(self, surface, game):
        name = game.screen.value
        target = surface
        dx, dy = game.fx.offset() if name == "playing" else (0, 0)
        if dx or dy:
            target = pygame.Surface(surface.get_size())
        target.blit(self.backdrop, (0, 0))
        if name in ("playing", "paused", "over"):
            self._world(target, game)
            self._hud(target, game)
        if name == "title":
            self._title(target, game)
        elif name == "howto":
            self._howto(target, game)
        elif name == "playing":
            self._phase_overlay(target, game)
        elif name == "paused":
            self._pause(target, game)
        elif name == "over":
            self._results(target, game)
        if dx or dy:
            surface.fill((10, 5, 28))
            surface.blit(target, (dx, dy))
        if game.fx.flash > 0 and not game.fx.reduced:
            veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            veil.fill((*game.fx.flash_colour, int(min(1, game.fx.flash / 0.12) * 60)))
            surface.blit(veil, (0, 0))

    # ------------------------------------------------------------ gameplay
    def _world(self, surface, game):
        run, t = game.run, game.time
        maze = run.maze
        surface.blit(self.maze_surface(maze), (OX, OY))
        if run.catnip_active and not game.fx.reduced:             # the maze edge glows green while the catnip lasts
            k = 0.5 + 0.5 * math.sin(t * 8)
            pygame.draw.rect(surface, tuple(int(c * (0.35 + 0.4 * k)) for c in GREEN),
                             (OX - 1, OY - 1, COLS * TILE + 2, ROWS * TILE + 2), 1)
        fish_a, fish_b = art.fish_sprite(False), art.fish_sprite(True)
        sparkle = int(t * 3)
        for tile in run.fish:
            x, y = tile_center(*tile)
            if tile in maze.catnip:
                halo = art.catnip_halo(int(t * 6))
                surface.blit(halo, halo.get_rect(center=(x, y)))
                spr = art.catnip_sprite(int(t * 4))
            else:
                spr = fish_b if (tile[0] * 3 + tile[1] + sparkle) % 11 == 0 else fish_a
            surface.blit(spr, spr.get_rect(center=(x, y)))
        if run.golden:
            tile, left = run.golden
            if left > 3 or int(t * 8) % 2:
                x, y = tile_center(*tile)
                bob = round(math.sin(t * 6) * 1.5)
                glow = art.catnip_halo(int(t * 6))
                surface.blit(glow, glow.get_rect(center=(x, y)))
                spr = art.golden_sprite(int(t * 5))
                surface.blit(spr, spr.get_rect(center=(x, y + bob)))
        for robot in run.robots:
            self._robot(surface, robot, run, t)
        self._cat(surface, run, t, game)
        for ring in game.fx.rings:
            pygame.draw.circle(surface, ring[6], (round(ring[0]), round(ring[1])), max(1, round(ring[2])), 1)
        for x, y, _, _, life, max_life, colour, size in game.fx.particles:
            surface.fill(colour if life > max_life * 0.3 else tuple(c // 2 for c in colour), (round(x), round(y), size, size))
        for text, x, y, life, colour in game.fx.popups:
            half = self.font.size(text)[0] // 2 + 2
            self.text(surface, text, (min(max(round(x), OX + half), OX + COLS * TILE - half), max(round(y), OY + 6)), colour)

    def _robot(self, surface, robot, run, t):
        x, y = tile_center(*robot.pos)
        flash = robot.fright and run.catnip_left < cfg.CATNIP_WARN and int(t * 8) % 2 == 0
        if robot.mode == "den":
            y += round(math.sin(t * 3 + robot.home[0]) * 1)
        wobble = round(math.sin(t * 22) * 1) if robot.fright else 0
        spr = art.robot_sprite(robot.kind, int(t * 6), robot.facing, robot.mode, robot.fright, flash)
        surface.blit(spr, spr.get_rect(center=(x + wobble, y)))
        if robot.fright and robot.mode != "eyes" and not flash:
            for ex, ey in ((x - 3, y - 2), (x + 2, y - 2)):
                surface.fill((255, 255, 255), (ex + wobble, ey, 1, 1))
        if robot.mode == "eyes" and run.phase == "run":
            surface.fill(ROBOT_TINT[robot.kind], (x - 1, y + 5, 3, 1))

    def _cat(self, surface, run, t, game):
        cat = run.cat
        x, y = tile_center(*cat.pos)
        if run.phase == "dying":
            dead = min(1.0, run.phase_time / cfg.DYING_SECONDS)
            spr = art.cat_sprite(cat.facing, 0, False, False, dead)
            surface.blit(spr, spr.get_rect(center=(x, y - round(math.sin(dead * math.pi) * 6))))
            return
        if run.phase == "run" and run.invulnerable > 0 and int(t * 12) % 2 == 0:
            return                                                   # blinking while protected
        power = run.catnip_active
        blink = int(t * 1.7) % 9 == 0
        frame = int(cat.walk * 10) if cat.dir != (0, 0) else 0
        if power:
            glow = art.cat_glow(int(t * 8))
            surface.blit(glow, glow.get_rect(center=(x, y)))
            if not game.fx.reduced and int(t * 14) % 3 == 0:
                game.fx.particles.append([x + game.fx.rng.uniform(-5, 5), y + 4, game.fx.rng.uniform(-8, 8), -22, 0.4, 0.4, GREEN, 1])
        spr = art.cat_sprite(cat.facing, frame, power, blink)
        surface.blit(spr, spr.get_rect(center=(x, y)))

    # ------------------------------------------------------------ HUD
    def _hud(self, surface, game):
        run = game.run
        self.plain(surface, f"SCORE {run.score:06d}", (8, 4), WHITE)
        self.plain(surface, f"BEST  {game.personal_best:06d}", (8, 15), MUTED)
        self.text(surface, f"LEVEL {run.level}  {run.maze.name}", (cfg.FIELD_W // 2, 8), run.maze.edge_color)
        self.text(surface, f"FISH LEFT {run.fish_left}", (cfg.FIELD_W // 2, 19), PINK)
        self.plain(surface, "LIVES", (cfg.FIELD_W - 8, 4), CYAN, anchor="topright")
        for i in range(cfg.MAX_LIVES):
            if i < max(run.lives, 0) or i < cfg.START_LIVES:
                icon = art.heart_icon(i < run.lives)
                surface.blit(icon, (cfg.FIELD_W - 8 - (i + 1) * 11 + 2, 14))
        y = OY + ROWS * TILE + 6
        if run.catnip_active:
            warn = run.catnip_left < cfg.CATNIP_WARN
            colour = GOLD if warn and int(game.time * 8) % 2 else GREEN
            self.plain(surface, "CATNIP POWER", (OX, y), colour)
            bar = pygame.Rect(OX + 78, y, 150, 7)
            surface.fill((20, 50, 40), bar)
            fill = max(1, round(bar.w * run.catnip_left / run.diff.catnip))
            surface.fill(colour, (bar.x, bar.y, fill, bar.h))
            pygame.draw.rect(surface, GREEN, bar.inflate(2, 2), 1)
            self.plain(surface, f"{run.catnip_left:.1f}", (bar.right + 8, y), colour)
        else:
            self.plain(surface, game.hint_line(), (OX, y), MUTED)

    # ------------------------------------------------------------ overlays during a run
    def _phase_overlay(self, surface, game):
        run = game.run
        cx = cfg.FIELD_W // 2
        row9 = OY + 9 * TILE + TILE // 2
        if run.phase == "ready":
            plate = pygame.Rect(0, 0, 90, 18)
            plate.center = (cx, row9)
            self.panel(surface, plate, GOLD)
            label = "READY!" if run.lives == cfg.START_LIVES or run.fish_left == run.fish_total else "TRY AGAIN!"
            self.text(surface, label, plate.center, GOLD)
        elif run.phase == "clear":
            self._clear_panel(surface, game)
        elif run.phase == "over":
            plate = pygame.Rect(0, 0, 200, 40)
            plate.center = (cx, cfg.FIELD_H // 2)
            self.panel(surface, plate, PINK, CYAN)
            self.text(surface, "GAME OVER", (cx, plate.centery - 7), PINK, 2)
            self.text(surface, f"SCORE {run.score}", (cx, plate.centery + 12), WHITE)
        elif run.golden and run.golden[1] > cfg.GOLDEN_SECONDS - 1.5:
            self.text(surface, "GOLDEN FISH!", (cx, row9), GOLD)

    def _clear_panel(self, surface, game):
        run, cx = game.run, cfg.FIELD_W // 2
        panel = self.panel(surface, pygame.Rect(cx - 110, 92, 220, 104), GOLD, CYAN)
        self.text(surface, "LEVEL CLEAR!", (cx, panel.y + 16), GOLD, 2)
        self.text(surface, f"CLEAR BONUS  +{run.last_clear_bonus}", (cx, panel.y + 40), GREEN)
        self.text(surface, f"SCORE {run.score}", (cx, panel.y + 55), WHITE)
        nxt = run.level + 1
        self.text(surface, f"NEXT: LEVEL {nxt}", (cx, panel.y + 72), CYAN)
        if run.phase_time >= cfg.CLEAR_SKIP_AFTER and int(game.time * 2.5) % 2 == 0:
            self.text(surface, "PRESS ENTER", (cx, panel.y + 90), MUTED)

    def _pause(self, surface, game):
        surface.blit(self.dim, (0, 0))
        cx = cfg.FIELD_W // 2
        panel = self.panel(surface, pygame.Rect(cx - 90, 84, 180, 126), CYAN, PINK)
        self.text(surface, "PAUSED", (cx, panel.y + 16), CYAN, 2)
        self.menu(surface, ("RESUME", "RESTART", "RETURN TO LOBBY"), game.cursor, panel.y + 44, 16, game.time)

    # ------------------------------------------------------------ title and how to play
    def _title(self, surface, game):
        cx, t = cfg.FIELD_W // 2, game.time
        maze = game.demo_maze
        # a moving cat chased by a robot along a strip of neon floor
        lane = 205
        pygame.draw.line(surface, maze.edge_color, (30, lane - 10), (cfg.FIELD_W - 30, lane - 10), 1)
        pygame.draw.line(surface, maze.edge_color, (30, lane + 10), (cfg.FIELD_W - 30, lane + 10), 1)
        span = cfg.FIELD_W - 100
        for i in range(0, span, 16):
            fx = 50 + i
            spr = art.fish_sprite(False)
            if fx > 50 + (t * 70) % span:
                surface.blit(spr, spr.get_rect(center=(fx, lane)))
        cat_x = 50 + (t * 70) % span
        glow = art.cat_glow(int(t * 8))
        power = int(t / 6) % 2 == 1
        if power:
            surface.blit(glow, glow.get_rect(center=(round(cat_x), lane)))
        surface.blit(art.cat_sprite((1, 0), int(t * 10), power), art.cat_sprite((1, 0), 0).get_rect(center=(round(cat_x), lane)))
        if power:
            rx = cat_x + 46
            surface.blit(art.robot_sprite("chase", int(t * 6), fright=True), (round(rx) - 8, lane - 8))
        else:
            rx = cat_x - 46
            surface.blit(art.robot_sprite("chase", int(t * 6)), (round(rx) - 8, lane - 8))
        bob = round(math.sin(t * 2.4) * 2)
        self.text(surface, "NEON", (cx, 40 + bob), PINK, 4)
        self.text(surface, "CAT MAZE", (cx, 76 + bob), CYAN, 4)
        self.text(surface, "EAT THE FISH - DODGE THE ROBOTS", (cx, 112), MUTED)
        self.menu(surface, ("START", "HOW TO PLAY"), game.cursor, 142, 16, t)
        best = f"BEST {game.personal_best}" + (f"   LEVEL {game.best_level}" if game.best_level else "")
        self.text(surface, best, (cx, 240), GOLD)
        self.text(surface, game.hint_line(), (cx, 258), MUTED)
        self.text(surface, "ENTER SELECT   ESC LOBBY", (cx, 272), MUTED)

    def _howto(self, surface, game):
        cx = cfg.FIELD_W // 2
        surface.blit(self.dim, (0, 0))
        panel = self.panel(surface, pygame.Rect(14, 10, cfg.FIELD_W - 28, 280), CYAN, PINK)
        self.text(surface, "HOW TO PLAY", (cx, 24), GOLD, 2)
        rows = ((art.fish_sprite(), "EAT EVERY FISH TO CLEAR THE LEVEL", PINK),
                (art.golden_sprite(0), "GOLDEN FISH: BIG BONUS, ONLY FOR A WHILE", GOLD),
                (art.catnip_sprite(0), "CATNIP: ROBOTS FLEE - TOUCH THEM TO DISABLE", GREEN))
        y = 46
        for icon, line, colour in rows:
            surface.blit(icon, (panel.x + 10, y - 5))
            self.plain(surface, line, (panel.x + 32, y), colour)
            y += 18
        y += 2
        for kind, name, line in (("patrol", "PATROL BOT", "WALKS A ROUTE, SOMETIMES TURNS"),
                                 ("chase", "CHASE BOT", "HUNTS YOU ALONG THE MAZE"),
                                 ("ambush", "AMBUSH BOT", "AIMS AHEAD OF YOUR PATH")):
            surface.blit(art.robot_sprite(kind, int(game.time * 6)), (panel.x + 10, y - 5))
            self.plain(surface, name, (panel.x + 32, y - 4), ROBOT_TINT[kind])
            self.plain(surface, line, (panel.x + 32, y + 5), MUTED)
            y += 22
        y += 2
        self.plain(surface, "3 LIVES. A ROBOT TOUCH COSTS ONE.", (panel.x + 10, y), WHITE)
        self.plain(surface, game.hint_line(), (panel.x + 10, y + 13), CYAN)
        self.plain(surface, "TURN EARLY: A KEY PRESSED BEFORE A CROSSING IS REMEMBERED", (panel.x + 10, y + 26), MUTED)
        if int(game.time * 2.5) % 2 == 0:
            self.text(surface, "ENTER BACK", (cx, panel.bottom - 12), GOLD)

    # ------------------------------------------------------------ results
    def _results(self, surface, game):
        surface.blit(self.dim, (0, 0))
        run, cx = game.run, cfg.FIELD_W // 2
        panel = self.panel(surface, pygame.Rect(cx - 125, 24, 250, 252), PINK, CYAN)
        self.text(surface, "RESULTS", (cx, panel.y + 16), PINK, 2)
        lines = (("SCORE", f"{run.score}", WHITE), ("LEVEL REACHED", f"{run.level}", CYAN),
                 ("LEVELS CLEARED", f"{run.levels_cleared}", CYAN), ("FISH EATEN", f"{run.fish_eaten}", PINK),
                 ("GOLDEN FISH", f"{run.goldens}", GOLD), ("ROBOTS DISABLED", f"{run.disabled_total}", GREEN))
        y = panel.y + 38
        for label, value, colour in lines:
            self.plain(surface, label, (panel.x + 16, y), MUTED)
            self.plain(surface, value, (panel.right - 16, y), colour, anchor="topright")
            y += 14
        y += 4
        surface.fill((70, 40, 110), (panel.x + 14, y, panel.w - 28, 1))
        y += 8
        self.plain(surface, "TICKETS EARNED", (panel.x + 16, y), GOLD)
        self.plain(surface, f"{game.best.tickets}", (panel.right - 16, y), GOLD, anchor="topright")
        y += 13
        if game.new_record:
            self.text(surface, "NEW BEST SCORE!", (cx, y + 4), GOLD if int(game.time * 3) % 2 else WHITE)
        else:
            self.text(surface, "THE BEST RUN OF THIS PLAY IS PAID", (cx, y + 4), MUTED)
        self.menu(surface, ("PLAY AGAIN", "RETURN TO LOBBY"), game.cursor, panel.bottom - 40, 16, game.time)
