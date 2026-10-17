"""CAPSULE screen: pull from CAT CAPSULE or RETRO CAPSULE with your own Tickets.

Opened from the machine in Prize Plaza for ONE local player; only their keys (and ESC)
drive it and only their profile pays. E pulls one capsule: CapsuleService.pull() takes the
Tickets and grants the prize in one step, then the screen just plays the reveal. While a
capsule is dropping / opening E does nothing, so a held key can never pull twice.

Keys: E pull, UP/DOWN scroll the prize list, ESC leave.
"""
import math

import pygame

from capsule import CAPSULE_MACHINES, CapsuleService
from font import LINE_H
from gfx import scale_color
from item_icons import item_icon
from item_registry import COMMON, EPIC, ITEM_REGISTRY, RARE, UNCOMMON
from menu_kit import FRAME, GOLD, ROW_H, MenuScene, fit_text, item_icon_for_ticket
from plaza_stations import _LOOK, _PODS, _capsule_sprite
from preview_art import scaled
from settings import Col
from ui import draw_text

STAGE = pygame.Rect(14, 60, 196, 162)
LIST = pygame.Rect(216, 60, FRAME.right - 216 - 8, 162)
VISIBLE = 8
DROP_TIME, OPEN_TIME = 0.7, 0.4
TURN_TIME = 0.35            # the first part of the drop phase: the handle turns, then the capsule falls
INPUT_DELAY = 0.35          # E is ignored this long after the screen opens (the press that opened it)
RARITY_COLOR = {COMMON: Col.TEXT_MUTED, UNCOMMON: (120, 235, 150), RARE: (110, 210, 255), EPIC: (255, 120, 220)}
RARITY_ORDER = {COMMON: 0, UNCOMMON: 1, RARE: 2, EPIC: 3}


class CapsuleScene(MenuScene):
    def __init__(self, game, owner, kind, rng=None):
        super().__init__(game, owner)
        self.kind = kind
        self.spec = CAPSULE_MACHINES[kind]
        self.look = _LOOK[kind]
        self.accent, self.glow = self.look["trim"], self.look["accent"]
        self.title = self.spec.name
        self.service = CapsuleService(owner.profile, rng=rng)
        self.first = 0
        self.phase = "idle"             # idle / drop / open / shown
        self.phase_time = 0.0
        self.dropped = False
        self.result = None              # the CapsuleResult being (or last) revealed
        self.lock = INPUT_DELAY
        self.hints = ("UP/DOWN PRIZES", f"{owner.controls.label('interact') or 'E'} PULL", "ESC LEAVE")

    # ------------------------------------------------------------ data
    @property
    def rows(self):
        """The machine's prizes, commonest first (the exact odds are not shown)."""
        items = [ITEM_REGISTRY.get(p.item_id) for p in self.spec.prizes]
        return sorted((d for d in items if d is not None), key=lambda d: RARITY_ORDER[d.rarity])

    @property
    def busy(self):
        return self.phase in ("drop", "open") or self.lock > 0

    # ------------------------------------------------------------ input
    def on_action(self, action):
        if action == "back":
            self.play("cancel")
            self.close()
        elif action in ("up", "down"):
            step = -1 if action == "up" else 1
            self.first = max(0, min(len(self.rows) - VISIBLE, self.first + step))
        elif action == "interact":
            self.pull()

    def pull(self):
        if self.busy:
            return
        result = self.service.pull(self.kind)
        if not result.success:
            self.say(result.message, Col.MAGENTA)
            self.play("cancel")
            return
        self.result = result
        self.phase, self.phase_time = "drop", 0.0
        self.dropped = False
        self.lock = DROP_TIME + OPEN_TIME
        self.play("capsule_turn")

    def update(self, dt):
        super().update(dt)
        self.lock = max(0.0, self.lock - dt)
        if self.phase == "idle" or self.phase == "shown":
            return
        self.phase_time += dt
        if self.phase == "drop" and not self.dropped and self.phase_time >= TURN_TIME:
            self.dropped = True
            self.play("capsule_drop")
        if self.phase == "drop" and self.phase_time >= DROP_TIME:
            self.phase, self.phase_time = "open", 0.0
            self.play(f"capsule_pop_{self.kind}")
        elif self.phase == "open" and self.phase_time >= OPEN_TIME:
            self.phase, self.phase_time = "shown", 0.0
            result = self.result
            self.say(f"{result.name}  {result.message}", Col.CYAN if result.duplicate else Col.GREEN, 3.5)
            if result.duplicate:
                self.play("confirm")          # (a new item's fanfare is the pop itself)
            if not result.duplicate:
                self.owner.avatar.play_action("cheer", "down", emote="sparkle")

    # ------------------------------------------------------------ draw
    def idle_message(self):
        if not self.service.can_afford(self.kind):
            return f"NEED {self.spec.cost - self.profile.tickets} MORE TICKETS"
        return f"ONE CAPSULE: {self.spec.cost} TICKETS"

    def draw_body(self, surf):
        self.draw_frame(surf, subtitle=self.owner.tag)
        self._draw_stage(surf)
        self._draw_list(surf)
        self.draw_footer(surf)

    def _draw_stage(self, surf):
        box = STAGE
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(self.accent, 0.5), box, 1)
        machine = scaled(_capsule_sprite(self.kind), 2)
        pos = (box.x + 8, box.bottom - machine.get_height() - 4)
        surf.blit(machine, pos)
        for i, (px, py, phase) in enumerate(_PODS):                  # the capsules shuffling in the dome
            top, bottom = self.look["pods"][i % len(self.look["pods"])]
            bob = int(round(math.sin(self.time * 2.4 + phase * 1.7) * 1.4))
            _pod_big(surf, (pos[0] + px * 2, pos[1] + py * 2 + bob), top, bottom, radius=7)
        if self.phase == "drop" and self.phase_time < TURN_TIME:      # the knob turns a full circle
            a = self.phase_time / TURN_TIME * 2 * math.pi
            kx, ky = pos[0] + 20, pos[1] + 94
            pygame.draw.line(surf, (255, 255, 255), (kx, ky), (kx + math.sin(a) * 8, ky - math.cos(a) * 8), 2)
        cx, cy = box.x + 144, box.y + 70
        if self.phase in ("drop", "open"):
            self._draw_pull(surf, cx, cy)
        elif self.result is not None:
            self._draw_prize(surf, cx, box)
        else:
            draw_text(surf, "PRESS E", (cx, cy - 12), Col.TEXT, 2, anchor="midtop", glow=scale_color(self.glow, 0.5))
            draw_text(surf, "TO PULL A", (cx, cy + 8), Col.TEXT_MUTED, anchor="midtop")
            draw_text(surf, "CAPSULE", (cx, cy + 18), Col.TEXT_MUTED, anchor="midtop")
        self._draw_price(surf, box)

    def _draw_price(self, surf, box):
        afford = self.service.can_afford(self.kind)
        color = GOLD if afford else (255, 110, 190)
        y = box.bottom - 16
        text = f"{self.spec.cost}"
        w = draw_text(surf, text, (box.x + 144, y), color, 2, anchor="midtop", glow=(120, 80, 10)).left
        surf.blit(item_icon_for_ticket(color), (w - 13, y + 3))
        draw_text(surf, "TICKETS", (box.x + 144 + 16, y + 4), Col.TEXT_MUTED)

    def _draw_pull(self, surf, cx, cy):
        top, bottom = self.look["pods"][1]
        if self.phase == "drop":
            fall = max(0.0, (self.phase_time - TURN_TIME) / (DROP_TIME - TURN_TIME))
            y = cy - 40 + int(60 * fall * fall)
            wobble = int(math.sin(self.phase_time * 30) * 2) if fall else 0
            if self.phase_time >= TURN_TIME:
                _pod_big(surf, (cx + wobble, y), top, bottom)
        else:
            k = self.phase_time / OPEN_TIME
            _pod_big(surf, (cx, cy + 20), top, bottom, open_k=k)
            for i in range(8):                                           # sparkles bursting out
                a = i * math.pi / 4
                r = 6 + 22 * k
                x, y = cx + math.cos(a) * r, cy + 16 + math.sin(a) * r
                surf.fill(self.look["accent"] if i % 2 else (255, 255, 255), (int(x), int(y), 2, 2))

    def _draw_prize(self, surf, cx, box):
        result = self.result
        definition = ITEM_REGISTRY.get(result.item_id)
        pulse = 0.5 + 0.5 * math.sin(self.time * 5)
        stage = pygame.Rect(cx - 36, box.y + 8, 72, 66)
        pygame.draw.rect(surf, scale_color(self.accent, 0.3 + 0.3 * pulse), stage, 1)
        icon = scaled(item_icon(definition), 3)
        surf.blit(icon, icon.get_rect(center=(stage.centerx, stage.centery - 2 + int(math.sin(self.time * 3)))))
        tag = pygame.Rect(stage.x, stage.bottom + 4, stage.w, 11)
        if result.duplicate:
            surf.fill((30, 90, 120), tag)
            draw_text(surf, f"DUPLICATE X{result.count}", tag.center, Col.TEXT, anchor="center")
        else:
            surf.fill((30, 120, 70), tag)
            draw_text(surf, "NEW!", tag.center, Col.TEXT, anchor="center")
        draw_text(surf, fit_text(result.name, 92), (cx, tag.bottom + 5), Col.TEXT, anchor="midtop")
        draw_text(surf, definition.rarity, (cx, tag.bottom + 5 + LINE_H), RARITY_COLOR[definition.rarity],
                  anchor="midtop")

    def _draw_list(self, surf):
        box = LIST
        surf.fill((14, 9, 34), box)
        pygame.draw.rect(surf, scale_color(self.accent, 0.5), box, 1)
        draw_text(surf, "WHAT'S INSIDE", (box.x + 6, box.y + 4), self.accent)
        rows = self.rows
        for slot in range(VISIBLE):
            i = self.first + slot
            if i >= len(rows):
                break
            definition = rows[i]
            rect = pygame.Rect(box.x + 3, box.y + 16 + slot * (ROW_H - 1), box.w - 9, ROW_H - 3)
            owned = self.service.quantity(definition.id)
            self.draw_row_bg(surf, rect, False, owned=owned > 0)
            icon = item_icon(definition)
            surf.blit(icon, icon.get_rect(midleft=(rect.x + 3, rect.centery)))
            color = RARITY_COLOR[definition.rarity] if owned else scale_color(RARITY_COLOR[definition.rarity], 0.7)
            draw_text(surf, fit_text(definition.name, rect.w - 46), (rect.x + 21, rect.y + 4), color)
            if owned:
                draw_text(surf, f"X{owned}" if definition.stackable else "OWNED", (rect.right - 3, rect.y + 4),
                          Col.CYAN if definition.stackable else Col.GREEN, anchor="topright")
            else:
                draw_text(surf, "NEW", (rect.right - 3, rect.y + 4), GOLD, anchor="topright")
        self.draw_scrollbar(surf, pygame.Rect(box.x, box.y + 16, box.w, VISIBLE * (ROW_H - 1)),
                            self.first, VISIBLE, len(rows))


def _pod_big(surf, center, top, bottom, open_k=0.0, radius=9):
    """A capsule drawn at 2x scale; with open_k > 0 the lid lifts off the base."""
    x, y = center
    lift = int(10 * open_k)
    pygame.draw.circle(surf, bottom, (x, y), radius)
    pygame.draw.circle(surf, top, (x, y - lift), radius, draw_top_left=True, draw_top_right=True)
    surf.fill(scale_color(bottom, 0.6), (x - radius, y - lift, radius * 2 + 1, 2))
    surf.fill((255, 255, 255), (x - radius // 2, y - radius * 2 // 3 - lift, 3, 2))
