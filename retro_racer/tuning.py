"""Developer tuning mode (F1): edit gameplay constants live and print them back for settings.py.

Values are changed directly on the `settings` module. Gameplay code reads `S.NAME` every frame,
so a change takes effect immediately.
"""
from dataclasses import dataclass
import pygame
import settings as S


@dataclass
class Param:
    label: str
    name: str        # attribute on the settings module
    step: float
    big: float       # step used while Shift is held
    lo: float
    hi: float
    decimals: int = 0

    def fmt(self, v):
        return f"{v:.{self.decimals}f}"


PARAMS = [
    Param("ACCELERATION", "ACCEL", 100, 500, 100, 30000),
    Param("BRAKING", "BRAKING", 100, 500, 100, 40000),
    Param("MAX SPEED", "MAX_SPEED", 200, 1000, 2000, 24000),
    Param("STEERING RATE", "STEER_RATE", 0.1, 0.5, 0.1, 6, 2),
    Param("CENTRIFUGAL", "CENTRIFUGAL", 0.05, 0.2, 0.0, 2, 2),
    Param("OFF-ROAD DECEL", "OFFROAD_DECEL", 100, 500, 0, 30000),
    Param("COLLISION PENALTY", "COLLISION_SPEED_PENALTY", 0.05, 0.2, 0.0, 1.0, 2),
    Param("CHECKPOINT BONUS", "CHECKPOINT_BONUS", 1, 5, 0, 60),
    Param("START TIME", "START_TIME", 1, 5, 5, 300),
]


class Tuner:
    ROW_H = 24
    WIDTH = 410

    def __init__(self, on_change=None):
        self.enabled = False
        self.selected = 0
        self.defaults = {p.name: getattr(S, p.name) for p in PARAMS}
        self.on_change = on_change      # callback(name, old, new) so the game can react live
        self.message = ""
        self.message_time = 0.0

    # ---- state --------------------------------------------------------------
    def toggle(self):
        self.enabled = not self.enabled
        # Key repeat lets you hold A/D to sweep a value; only while tuning so ENTER etc. stay normal.
        pygame.key.set_repeat(300, 40) if self.enabled else pygame.key.set_repeat()

    def value(self, param):
        return getattr(S, param.name)

    def set_value(self, param, new):
        new = round(max(param.lo, min(param.hi, new)), 4)
        if isinstance(self.defaults[param.name], int) and param.decimals == 0:
            new = int(round(new))
        old = self.value(param)
        if new != old:
            setattr(S, param.name, new)
            if self.on_change:
                self.on_change(param.name, old, new)

    def handle_key(self, event):
        """Handle a KEYDOWN while tuning is on. Returns True if the key was consumed."""
        key, shift = event.key, bool(event.mod & pygame.KMOD_SHIFT)
        param = PARAMS[self.selected]
        if key == pygame.K_w:
            self.selected = (self.selected - 1) % len(PARAMS)
        elif key == pygame.K_s:
            self.selected = (self.selected + 1) % len(PARAMS)
        elif key in (pygame.K_a, pygame.K_d):
            step = param.big if shift else param.step
            self.set_value(param, self.value(param) + (step if key == pygame.K_d else -step))
        elif key == pygame.K_r:
            for p in PARAMS:
                self.set_value(p, self.defaults[p.name])
            self._say("RESET TO DEFAULTS")
        elif key == pygame.K_p:
            self.print_values()
            self._say("PRINTED TO CONSOLE")
        else:
            return False
        return True

    def _say(self, msg):
        self.message, self.message_time = msg, 2.0

    def print_values(self):
        print("\n# --- tuned values: copy into settings.py ---", flush=True)
        for p in PARAMS:
            v = self.value(p)
            note = "" if v == self.defaults[p.name] else f"    # default {p.fmt(self.defaults[p.name])}"
            print(f"{p.name} = {p.fmt(v) if p.decimals else int(v)}{note}", flush=True)
        print("# --- end ---\n", flush=True)

    # ---- drawing ------------------------------------------------------------
    def draw(self, surf, hud, dt):
        if not self.enabled:
            return
        self.message_time = max(0.0, self.message_time - dt)
        x0, y0 = 10, 150
        h = 34 + len(PARAMS) * self.ROW_H + 84
        panel = pygame.Surface((self.WIDTH, h), pygame.SRCALPHA)
        panel.fill((0, 0, 20, 205))
        surf.blit(panel, (x0, y0))
        pygame.draw.rect(surf, (0, 200, 255), (x0, y0, self.WIDTH, h), 2)
        hud.text(surf, "TUNING MODE  (F1 = CLOSE)", (x0 + 10, y0 + 6), (0, 220, 255), hud.small)
        for i, p in enumerate(PARAMS):
            y = y0 + 34 + i * self.ROW_H
            v = self.value(p)
            changed = v != self.defaults[p.name]
            if i == self.selected:
                pygame.draw.rect(surf, S.HUD_YELLOW, (x0 + 4, y - 2, self.WIDTH - 8, self.ROW_H - 2))
                hud.text(surf, ">", (x0 + 10, y), (0, 0, 0), hud.small, shadow=False)
                hud.text(surf, p.label, (x0 + 30, y), (0, 0, 0), hud.small, shadow=False)
                hud.text(surf, ("* " if changed else "") + p.fmt(v), (x0 + self.WIDTH - 12, y), (0, 0, 0), hud.small, "right", shadow=False)
            else:
                color = (120, 255, 120) if changed else S.WHITE
                hud.text(surf, p.label, (x0 + 30, y), S.WHITE, hud.small)
                hud.text(surf, ("* " if changed else "") + p.fmt(v), (x0 + self.WIDTH - 12, y), color, hud.small, "right")
        y = y0 + 34 + len(PARAMS) * self.ROW_H + 4
        hud.text(surf, "W/S SELECT  A/D CHANGE  SHIFT=BIG", (x0 + 10, y), S.WHITE, hud.small)
        hud.text(surf, "R RESET  P PRINT  (* = CHANGED)", (x0 + 10, y + 22), S.WHITE, hud.small)
        if self.message_time > 0:
            hud.text(surf, self.message, (x0 + self.WIDTH - 12, y + 44 - 2), (255, 160, 60), hud.small, "right")
