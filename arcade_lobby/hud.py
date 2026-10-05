"""Compact TOKENS / TICKETS readout for the arcade room, in the bottom-right
corner (mirroring the controls box on the left), plus little '-1 TOKEN' /
'+5 TICKETS' floaters that rise from it when the wallet changes."""
import pygame

from font import get_font
from gfx import scale_color, shade
from player_profile import PlayerProfile
from settings import Col, VIEW_H, VIEW_W
from ui import neon_panel

H = 30          # same height as the controls box
PAD = 7
ROW_Y = (6, 17)
MIN_DIGITS = "000"  # value column is at least this wide, so it rarely resizes


def _token_icon():
    s = pygame.Surface((7, 7), pygame.SRCALPHA)
    pygame.draw.circle(s, shade(Col.YELLOW, -0.45), (3, 3), 3)
    pygame.draw.circle(s, Col.YELLOW, (3, 3), 2)
    s.fill(shade(Col.YELLOW, 0.6), (2, 1, 1, 2))
    return s


def _ticket_icon():
    s = pygame.Surface((9, 7), pygame.SRCALPHA)
    s.fill(Col.MAGENTA, (0, 1, 9, 5))
    s.fill(shade(Col.MAGENTA, 0.5), (1, 2, 7, 3))
    for x in (0, 8):                     # notched ends
        s.fill((0, 0, 0, 0), (x, 3, 1, 1))
    s.fill(Col.MAGENTA, (3, 2, 1, 3))   # perforation
    return s


class Floater:
    """A short-lived '+5 TICKETS' label that drifts up and fades."""
    LIFE = 1.3
    RISE = 16

    def __init__(self, image, pos):
        self.image = image
        self.x, self.y = pos
        self.age = 0.0

    @property
    def alive(self):
        return self.age < self.LIFE

    def update(self, dt):
        self.age += dt

    def draw(self, surf):
        k = self.age / self.LIFE
        rect = self.image.get_rect(midbottom=(self.x, self.y - int(self.RISE * (1 - (1 - k) ** 2))))
        rect.right = min(rect.right, VIEW_W - 2)
        self.image.set_alpha(int(255 * min(1.0, (1 - k) * 2.5)))
        surf.blit(self.image, rect)


class CurrencyHUD:
    """Reads the profile every frame (so it is always current) and listens
    for changes to spawn floaters and briefly flash the changed value."""
    FLASH = 0.45
    COLORS = {PlayerProfile.TOKEN: Col.YELLOW, PlayerProfile.TICKET: Col.MAGENTA}

    def __init__(self, profile):
        self.profile = profile
        self.token_icon = _token_icon()
        self.ticket_icon = _ticket_icon()
        self.floaters = []
        self.flash = {PlayerProfile.TOKEN: 0.0, PlayerProfile.TICKET: 0.0}
        self.slots = {}         # field -> centre x of its value, for floaters
        self._key = None
        self.image = None
        profile.subscribe(self.on_change)

    def close(self):
        self.profile.unsubscribe(self.on_change)

    def on_change(self, change):
        if change.field not in self.COLORS:
            return
        self._rebuild()
        if change.field == PlayerProfile.TOKEN:
            unit = "TOKEN" if abs(change.delta) == 1 else "TOKENS"
        else:
            unit = "TICKET" if abs(change.delta) == 1 else "TICKETS"
        color = self.COLORS[change.field] if change.delta > 0 else Col.TEXT_MUTED
        img = get_font().render_glow(f"{change.delta:+d} {unit}", color, scale_color(color, 0.35)).copy()
        self.floaters.append(Floater(img, (self.slots[change.field], self.rect.top - 1)))
        self.flash[change.field] = self.FLASH

    def clear_effects(self):
        self.floaters.clear()
        for field in self.flash:
            self.flash[field] = 0.0

    # ------------------------------------------------------------ build
    def _rebuild(self):
        """Re-render the panel when either value (or a flash) changes."""
        flashing = tuple(self.flash[f] > 0 for f in self.flash)
        key = (self.profile.tokens, self.profile.tickets, flashing)
        if key == self._key:
            return
        self._key = key
        font = get_font()
        parts = [  # (field, icon, label, value)
            (PlayerProfile.TOKEN, self.token_icon, "TOKENS", f"{self.profile.tokens:02d}"),
            (PlayerProfile.TICKET, self.ticket_icon, "TICKETS", f"{self.profile.tickets:03d}"),
        ]
        rendered = []
        for field, icon, label, value in parts:
            lit = self.flash[field] > 0
            value_color = Col.TEXT if lit else self.COLORS[field]
            rendered.append((field, icon, font.render(label, Col.TEXT_MUTED),
                             font.render_glow(value, value_color, scale_color(self.COLORS[field], 0.4))))
        icon_w = max(i.get_width() for _, i, _, _ in rendered)
        label_w = max(l.get_width() for _, _, l, _ in rendered)
        value_w = max([v.get_width() for _, _, _, v in rendered] + [font.size(MIN_DIGITS)[0] + 2])
        w = PAD * 2 + icon_w + 3 + label_w + 5 + value_w
        self.image = neon_panel(w, H, Col.CYAN, None, 235).copy()
        self.rect = self.image.get_rect(bottomright=(VIEW_W - 4, VIEW_H - 4))
        for (field, icon, label, value), y in zip(rendered, ROW_Y):
            self.image.blit(icon, (PAD + (icon_w - icon.get_width()) // 2, y))
            self.image.blit(label, (PAD + icon_w + 3, y))
            self.image.blit(value, value.get_rect(topright=(w - PAD + 1, y - 1)))
            self.slots[field] = self.rect.right - PAD - value.get_width() // 2

    # ------------------------------------------------------------ frame
    def update(self, dt):
        for field in self.flash:
            self.flash[field] = max(0.0, self.flash[field] - dt)
        for f in self.floaters:
            f.update(dt)
        self.floaters = [f for f in self.floaters if f.alive]

    def draw(self, surf):
        self._rebuild()
        surf.blit(self.image, self.rect)
        for f in self.floaters:
            f.draw(surf)
