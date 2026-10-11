"""Draws Starfall Assault onto a 400x300 canvas with the lobby's bitmap font and neon palette."""
import math

import pygame

from arcade_lobby.font import get_font
from . import art
from . import config as cfg

BG_TOP, BG_BOTTOM = (8, 6, 32), (30, 14, 70)
CYAN, PINK, VIOLET, BLUE = art.CYAN, art.MAGENTA, art.VIOLET, art.BLUE
YELLOW, WHITE, ORANGE, MUTED = art.YELLOW, art.WHITE, art.ORANGE, (140, 130, 190)
LIME = art.LIME
PANEL = (14, 10, 42)
POWER_ORDER = ("rapid", "spread", "pierce")
POWER_SHORT = {"rapid": "RAPID", "spread": "SPREAD", "pierce": "PIERCE"}


class Renderer:
    def __init__(self):
        self.font = get_font()
        self.backdrop = self._backdrop()
        self.dim = pygame.Surface((cfg.FIELD_W, cfg.FIELD_H), pygame.SRCALPHA)
        self.dim.fill((8, 4, 24, 170))

    @staticmethod
    def _backdrop():
        """Banded navy-to-purple sky, soft nebula clouds and a distant ringed planet, built once."""
        surf = pygame.Surface((cfg.FIELD_W, cfg.FIELD_H))
        for y in range(0, cfg.FIELD_H, 4):
            k = y / cfg.FIELD_H
            surf.fill(tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * k) for i in range(3)), (0, y, cfg.FIELD_W, 4))
        haze = pygame.Surface((cfg.FIELD_W, cfg.FIELD_H), pygame.SRCALPHA)
        for cx, cy, r, color in ((70, 90, 70, (120, 60, 200)), (130, 130, 50, (60, 90, 220)),
                                 (330, 210, 80, (150, 60, 190)), (290, 250, 50, (40, 140, 200)),
                                 (210, 40, 60, (70, 60, 190)), (40, 240, 55, (60, 70, 200))):
            for step in range(14, 0, -1):
                pygame.draw.circle(haze, (*color, 4), (cx, cy), r * step // 14)
        surf.blit(haze, (0, 0))
        planet, ring = (340, 62), pygame.Rect(306, 56, 68, 14)             # a small ringed planet
        pygame.draw.ellipse(surf, (44, 34, 100), ring, 1)
        pygame.draw.circle(surf, (62, 48, 128), planet, 14)
        pygame.draw.circle(surf, (86, 68, 156), (planet[0] - 4, planet[1] - 4), 7)
        pygame.draw.circle(surf, (46, 34, 104), (planet[0] + 5, planet[1] + 5), 7)
        pygame.draw.arc(surf, (90, 76, 170), ring, math.pi, math.tau, 1)
        return surf

    # ------------------------------------------------------------ text helpers
    def text(self, surface, text, pos, color=CYAN, scale=1, anchor="center"):
        image = self.font.render_glow(str(text), color, (35, 20, 65), scale)
        surface.blit(image, image.get_rect(**{anchor: pos}))

    def plain(self, surface, text, pos, color=CYAN, scale=1, anchor="topleft"):
        image = self.font.render(str(text), color, scale)
        surface.blit(image, image.get_rect(**{anchor: pos}))

    # ------------------------------------------------------------ frame
    def draw(self, surface, game):
        screen = game.screen.value
        target = surface
        dx, dy = game.fx.offset() if screen == "playing" else (0, 0)
        if dx or dy:
            target = pygame.Surface(surface.get_size())
        target.blit(self.backdrop, (0, 0))
        self._stars(target, game)
        if screen in ("playing", "paused", "over"):
            self._world(target, game)
            self._hud(target, game)
        if screen == "title":
            self._title(target, game)
        elif screen == "howto":
            self._howto(target, game)
        elif screen == "paused":
            self._overlay(target, game, "PAUSED")
        elif screen == "over":
            self._game_over(target, game)
        if dx or dy:
            surface.fill((10, 5, 28))
            surface.blit(target, (dx, dy))
        if game.fx.flash > 0 and not game.fx.reduced:
            veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            veil.fill((255, 90, 160, int(min(1, game.fx.flash / 0.12) * 70)))
            surface.blit(veil, (0, 0))

    def _stars(self, surface, game):
        for i, (x, y, _, color) in enumerate(game.stars.stars):
            if i % 7 == 0 and int(game.time * 3 + i) % 4 == 0:      # a few twinkle
                color = (255, 255, 255)
            surface.fill(color, (int(x), int(y), 1, 1))
        for i in range(0, 5):                       # a few plus-shaped stars
            sx, sy = (i * 83 + 31) % cfg.FIELD_W, (i * 59 + 40) % cfg.FIELD_H
            if int(game.time * 2 + i) % 3:
                surface.fill((200, 190, 255), (sx - 1, sy, 3, 1))
                surface.fill((200, 190, 255), (sx, sy - 1, 1, 3))

    # ------------------------------------------------------------ gameplay
    def _world(self, surface, game):
        run, t = game.run, game.time
        line = cfg.DEFENSE_LINE
        for x in range(0, cfg.FIELD_W, 8):                           # the defence line: a dashed force field
            surface.fill((70, 130, 255) if (x // 8) % 2 else (50, 50, 140), (x, line, 4, 1))
        for e in run.enemies:
            frame = art.sprite(f"{e.kind}_b" if int(t * 2.5 + e.col) % 2 else e.kind, e.flash > 0)
            rect = frame.get_rect(center=(round(e.x), round(e.y)))
            surface.blit(frame, rect)
            if e.carrier:
                glow = art.carrier_glow(int(t * 6))
                surface.blit(glow, glow.get_rect(center=(rect.centerx, rect.centery)))
                pygame.draw.circle(surface, (120, 100, 40), rect.center, rect.w // 2 + 2, 1)
            if e.max_hp > 1 and e.hp < e.max_hp:
                w = e.spec["width"]
                bar_y = round(e.y + e.spec["height"] / 2 + 1)
                surface.fill((60, 20, 70), (round(e.x - w / 2), bar_y, w, 1))
                surface.fill(PINK, (round(e.x - w / 2), bar_y, round(w * e.hp / e.max_hp), 1))
        if run.boss:
            self._boss(surface, run.boss, t)
        for p in run.powerups:
            icon = art.power_icon(p.kind)
            color = art.POWER_COLORS[p.kind]
            pulse = 8 + int(math.sin(t * 8) * 1.5)
            pygame.draw.circle(surface, tuple(v // 3 for v in color), (round(p.x), round(p.y)), pulse, 1)
            surface.blit(icon, icon.get_rect(center=(round(p.x), round(p.y))))
        for b in run.player_bolts:
            self._laser(surface, b)
        for i, b in enumerate(run.enemy_bolts):                      # plasma orbs
            color = PINK if (i + int(t * 10)) % 2 else VIOLET
            pos = (round(b.x), round(b.y))
            pygame.draw.circle(surface, (70, 30, 110), pos, 4)
            pygame.draw.circle(surface, color, pos, 3)
            surface.fill(WHITE, (pos[0] - 1, pos[1] - 1, 2, 2))
            surface.fill((90, 40, 130), (pos[0], pos[1] - 8, 1, 4))
        for x, y, age, life, radius, color in game.fx.rings:
            k = age / life
            pygame.draw.circle(surface, tuple(int(v * (1 - k * 0.7)) for v in color), (round(x), round(y)),
                               max(1, int(radius * k)), 1)
        if not run.over:
            self._player(surface, run, t)
        for x, y, vx, vy, life, max_life, color, size in game.fx.particles:
            fade = life / max_life
            c = tuple(int(v * (0.35 + 0.65 * fade)) for v in color)
            surface.fill(c, (round(x), round(y), size, size))
        for text, x, y, age, color in game.fx.popups:
            self.text(surface, text, (round(min(max(x, 40), cfg.FIELD_W - 40)), round(y - 10 - age * 18)), color)
        if run.banner_active and game.screen.value == "playing":
            self._banner(surface, run)
        if run.combo >= cfg.COMBO["step"] and game.screen.value != "over":
            self._combo(surface, run)

    def _laser(self, surface, b):
        x, y = round(b.x), round(b.y)
        if b.pierce:                                             # a long magenta lance
            surface.fill((120, 40, 110), (x - 2, y - 8, 5, 18))
            surface.fill(PINK, (x - 1, y - 8, 3, 18))
            surface.fill(WHITE, (x, y - 8, 1, 12))
        else:
            surface.fill((30, 90, 170), (x - 2, y - 5, 5, 12))
            surface.fill(CYAN, (x - 1, y - 5, 3, 10))
            surface.fill(WHITE, (x, y - 5, 1, 5))

    def _player(self, surface, run, t):
        if run.invuln > 0 and int(t * 14) % 2:
            return
        sprite = art.sprite("player")
        rect = sprite.get_rect(center=(round(run.x), cfg.PLAYER_Y))
        flame = 2 + int(t * 20) % 3 + (2 if run.power["rapid"] > 0 else 0)
        for dx in (-2, 2):
            surface.fill(ORANGE, (round(run.x) + dx - 1, rect.bottom, 2, flame))
            surface.fill(YELLOW, (round(run.x) + dx - 1, rect.bottom, 2, 1))
        surface.blit(sprite, rect)
        wing = round(run.x)
        if run.power["spread"] > 0:                                # wing guns glow while spread is active
            for dx in (-9, 9):
                surface.fill(CYAN if int(t * 12) % 2 else WHITE, (wing + dx, rect.top + 6, 1, 2))
        if run.power["pierce"] > 0:
            surface.fill(PINK, (wing - 1, rect.top - 2, 2, 2))
        if run.power["rapid"] > 0:
            for dx in (-13, 12):
                surface.fill(YELLOW if int(t * 16) % 2 else ORANGE, (wing + dx, rect.top + 8, 1, 3))
        if run.shield:
            pulse = 14 + int(math.sin(t * 6) * 1)
            pygame.draw.circle(surface, (60, 140, 255), (round(run.x), cfg.PLAYER_Y), pulse, 1)
            pygame.draw.circle(surface, (150, 200, 255), (round(run.x), cfg.PLAYER_Y), pulse - 2, 1)

    def _boss(self, surface, boss, t):
        sprite = art.sprite("boss", boss.flash > 0)
        rect = sprite.get_rect(center=(round(boss.x), round(boss.y)))
        if boss.enraged:
            pygame.draw.rect(surface, (200, 60, 90) if int(t * 6) % 2 else (120, 40, 110), rect.inflate(6, 6), 1)
        surface.blit(sprite, rect)
        glow = ORANGE if int(t * 4) % 2 else YELLOW
        for dx in (-12, 0, 12):
            surface.fill(glow, (rect.centerx + dx - 1, rect.bottom, 3, 2 + int(t * 8 + dx) % 2))

    def _banner(self, surface, run):
        boss = run.is_boss_wave
        label = "WARNING!" if boss else f"WAVE {run.wave}"
        color = ORANGE if boss else CYAN
        self.text(surface, label, (cfg.FIELD_W // 2, 128), color, 3)
        sub = "MOTHERSHIP APPROACHING" if boss else ("GET READY" if run.wave == 1 else "SECTOR CLEAR - NEXT WAVE")
        self.text(surface, sub, (cfg.FIELD_W // 2, 154), YELLOW if boss else WHITE)

    def _combo(self, surface, run):
        right = cfg.FIELD_W - 6
        mult = run.multiplier
        label = f"COMBO {run.combo}  X{mult:.2f}".rstrip("0").rstrip(".") if mult != 1 else f"COMBO {run.combo}"
        self.plain(surface, label, (right, 286), ORANGE if mult > 1 else YELLOW, anchor="topright")
        width = round(90 * max(0.0, run.combo_time) / cfg.COMBO["window"])
        surface.fill((60, 40, 80), (right - 90, 295, 90, 2))
        surface.fill(ORANGE, (right - width, 295, width, 2))

    # ------------------------------------------------------------ HUD
    def _hud(self, surface, game):
        run = game.run
        surface.fill((8, 4, 26), (0, 0, cfg.FIELD_W, cfg.HUD_H))
        surface.fill((70, 60, 150), (0, cfg.HUD_H - 1, cfg.FIELD_W, 1))
        self.plain(surface, f"SCORE {run.score:06d}", (6, 3), CYAN)
        self.plain(surface, f"WAVE {run.wave}", (cfg.FIELD_W // 2, 3), YELLOW, anchor="midtop")
        self.plain(surface, f"HI {game.personal_best:06d}", (cfg.FIELD_W - 6, 3), PINK, anchor="topright")
        self.plain(surface, "HP", (6, 14), MUTED)
        for i in range(cfg.MAX_HP):                                  # hull cells
            x = 20 + i * 12
            on = i < run.hp
            pygame.draw.rect(surface, LIME if on else (50, 44, 90), (x, 13, 10, 7), 0 if on else 1)
            if on:
                surface.fill((200, 255, 215), (x + 1, 14, 8, 1))
        x = 62
        if run.shield:
            surface.blit(art.power_icon("shield"), (x, 11))
            self.plain(surface, "ON", (x + 12, 14), (150, 200, 255))
            x += 30
        for name in POWER_ORDER:
            left = run.power[name]
            if left > 0:
                surface.blit(art.power_icon(name), (x, 11))
                color = art.POWER_COLORS[name] if left > 2 or int(game.time * 6) % 2 else MUTED
                self.plain(surface, f"{left:0.0f}S", (x + 12, 14), color)
                x += 34
        if run.boss:
            self._boss_bar(surface, run.boss)

    def _boss_bar(self, surface, boss):
        x, y, w = 238, 13, 156
        self.plain(surface, "BOSS", (x - 4, 14), ORANGE, anchor="topright")
        surface.fill((50, 20, 70), (x, y, w, 7))
        fill = round((w - 2) * boss.hp / boss.max_hp)
        surface.fill(ORANGE if not boss.enraged else (255, 90, 90), (x + 1, y + 1, fill, 5))
        pygame.draw.rect(surface, WHITE, (x, y, w, 7), 1)

    # ------------------------------------------------------------ menus
    def _menu(self, surface, game, top, labels=None):
        for i, label in enumerate(labels or game.menu()):
            selected = i == game.cursor
            y = top + i * 18
            if selected:
                surface.fill((40, 40, 120), (cfg.FIELD_W // 2 - 80, y - 7, 160, 15))
                pygame.draw.rect(surface, CYAN, (cfg.FIELD_W // 2 - 80, y - 7, 160, 15), 1)
                self.text(surface, ">", (cfg.FIELD_W // 2 - 70, y), ORANGE)
            self.text(surface, label, (cfg.FIELD_W // 2, y), WHITE if selected else MUTED)

    def _title(self, surface, game):
        cx = cfg.FIELD_W // 2
        self.text(surface, "RETRO SPACE SHOOTER", (cx, 30), ORANGE, 1)
        self.text(surface, "STARFALL", (cx, 60), CYAN, 4)
        self.text(surface, "ASSAULT", (cx, 94), VIOLET, 4)
        bob = int(math.sin(game.time * 3) * 3)
        ship = pygame.transform.scale_by(art.sprite("player"), 3)
        rect = ship.get_rect(center=(cx, 150 + bob))
        for dx in (-6, 6):
            surface.fill(ORANGE, (cx + dx - 2, rect.bottom, 4, 5 + int(game.time * 18) % 4))
        surface.blit(ship, rect)
        for i, (kind, side) in enumerate((("scout", -1), ("dash", 1), ("tank", -1), ("scout", 1))):
            drone = pygame.transform.scale_by(art.sprite(kind), 2)
            surface.blit(drone, drone.get_rect(center=(cx + side * (90 + (i // 2) * 52),
                                                       132 + int(math.sin(game.time * 2 + i) * 6) + (i // 2) * 14)))
        self._menu(surface, game, 196)
        self.text(surface, f"HIGH SCORE {game.personal_best:06d}   BEST WAVE {game.best_wave}", (cx, 244), YELLOW)
        self.text(surface, "W/S OR UP/DOWN + ENTER    ESC: LOBBY", (cx, 268), MUTED)
        self.text(surface, "F: REDUCED EFFECTS " + ("ON" if game.fx.reduced else "OFF"), (cx, 281), MUTED)

    def _howto(self, surface, game):
        cx = cfg.FIELD_W // 2
        surface.blit(self.dim, (0, 0))
        self.text(surface, "HOW TO PLAY", (cx, 16), CYAN, 2)
        rows = (("A/D OR LEFT/RIGHT", "MOVE"), ("SPACE (HOLD)", "FIRE"), ("ESC", "PAUSE"), ("ENTER", "CONFIRM"))
        for i, (key, what) in enumerate(rows):
            self.plain(surface, key, (70, 34 + i * 11), YELLOW)
            self.plain(surface, what, (230, 34 + i * 11), WHITE)
        foes = (("scout", "SCOUT DRONE - 10 PTS"), ("dash", "DART DRONE - FAST SHOTS, 25 PTS"),
                ("tank", "ARMOR BOT - 3 HITS, 40 PTS"), ("boss", "MOTHERSHIP - EVERY 5TH WAVE"))
        for i, (kind, label) in enumerate(foes):
            sprite = art.sprite(kind)
            if kind == "boss":
                sprite = pygame.transform.scale_by(sprite, 0.5)
            surface.blit(sprite, sprite.get_rect(center=(52, 92 + i * 17)))
            self.plain(surface, label, (80, 88 + i * 17), WHITE)
        cores = (("rapid", "RAPID FIRE: SHOOT FASTER (8S)"), ("spread", "SPREAD SHOT: 3-WAY LASER (10S)"),
                 ("pierce", "PIERCE: LASERS GO THROUGH (8S)"), ("shield", "SHIELD: BLOCKS ONE HIT"),
                 ("repair", "REPAIR: +1 HP (MAX 3)"))
        for i, (kind, label) in enumerate(cores):
            surface.blit(art.power_icon(kind), (47, 160 + i * 14))
            self.plain(surface, label, (80, 162 + i * 14), WHITE)
        self.text(surface, "GLOWING DRONES ALWAYS DROP A CORE", (cx, 240), YELLOW)
        self.text(surface, "CHAIN KILLS FOR A SCORE COMBO!", (cx, 252), ORANGE)
        self.text(surface, "DON'T LET THEM REACH THE BLUE LINE!", (cx, 264), PINK)
        self.text(surface, "ENTER OR ESC: BACK", (cx, 284), MUTED)

    def _panel(self, surface, rect):
        pygame.draw.rect(surface, PANEL, rect)
        pygame.draw.rect(surface, CYAN, rect, 1)
        pygame.draw.rect(surface, (90, 70, 190), rect.inflate(-4, -4), 1)

    def _overlay(self, surface, game, title):
        surface.blit(self.dim, (0, 0))
        cx = cfg.FIELD_W // 2
        self._panel(surface, pygame.Rect(cx - 100, 90, 200, 128))
        self.text(surface, title, (cx, 108), CYAN, 2)
        self._menu(surface, game, 142)
        self.text(surface, "ESC: RESUME    F: REDUCED FX " + ("ON" if game.fx.reduced else "OFF"), (cx, 232), MUTED)

    def _game_over(self, surface, game):
        surface.blit(self.dim, (0, 0))
        cx = cfg.FIELD_W // 2
        run = game.run
        self._panel(surface, pygame.Rect(cx - 120, 50, 240, 200))
        self.text(surface, "GAME OVER", (cx, 68), ORANGE, 3)
        reason = "THE DRONES BREACHED THE LINE!" if run.over_reason == "breach" else "YOUR SHIP WAS DESTROYED!"
        self.text(surface, reason, (cx, 90), MUTED)
        result = game.best
        rows = (("FINAL SCORE", f"{run.score}", WHITE),
                ("PERSONAL BEST", f"{game.personal_best}", YELLOW),
                ("HIGHEST WAVE", f"{max(game.best_wave, run.reached)}", CYAN),
                ("TICKETS EARNED", f"{result.tickets}", LIME))
        for i, (label, value, color) in enumerate(rows):
            y = 110 + i * 16
            self.plain(surface, label, (cx - 100, y), MUTED)
            self.plain(surface, value, (cx + 100, y), color, anchor="topright")
        if game.new_record:
            self.text(surface, "NEW PERSONAL BEST!", (cx, 178), YELLOW if int(game.time * 3) % 2 else ORANGE)
        elif run.result().tickets < result.tickets:
            self.text(surface, "BEST RUN OF THIS PLAY PAYS", (cx, 178), MUTED)
        self._menu(surface, game, 200)
