"""A reusable RPG-style dialogue box for story scenes.

    StoryDialogue([Line("MIAO MEOW", "Meow?! You're awake!", "surprised"), Line("PLAYER", "Where am I?")], ...)

* a pixel-art box along the bottom: deep-purple panel, cyan / soft-purple frame, the speaker's portrait popping over
  its top-left corner, a name tab, the text typed out letter by letter with a soft blip
* E / ENTER / SPACE finishes the line being typed, then goes to the next; the last one closes the box
* SPEAKERS is a registry: a new character (or a new expression) is one register_speaker() call; Line.mood picks
  the expression and a speaker that does not know it falls back to its normal face
* it is a room modal (the room asks `hides_hud` and covers the corner HUD while it is open, so nothing collides)
"""
import math
from dataclasses import dataclass

import pygame

from font import get_font
from gfx import scale_color, soft_shadow
from miao_meow import miao_frame
from player import player_sheet
from shopkeeper import mochi_frame
from settings import CONFIRM_KEYS, Col, VIEW_W
from ui import draw_text, neon_panel, wrap_text

CPS = 42.0                              # letters per second
BLIP_EVERY = 3                          # one soft blip per this many letters
BOX = pygame.Rect(6, 232, VIEW_W - 12, 62)
BOX_TOP = pygame.Rect(6, 8, VIEW_W - 12, 62)       # the same box along the top, for when the speakers stand low on screen
LOW_ON_SCREEN = BOX.y - 10                         # feet below this line would be hidden by a bottom box
PORTRAIT = (12, 222)                    # top-left of the 44x44 framed portrait (it overlaps the box's top edge)
TEXT_X = 66
TEXT_W = BOX.right - 14 - TEXT_X
MAX_LINES = 3
TAB_Y = BOX.y - 7


@dataclass(frozen=True)
class Line:
    speaker: str                        # a key of SPEAKERS
    text: str
    mood: str = "normal"                # normal / happy / surprised / gentle (what the speaker defines)


class Speaker:
    """One character the box can show: a display name, an accent colour and a portrait painter."""

    def __init__(self, name, accent=Col.CYAN, portrait=None, blip="vend_select"):
        self.name = name
        self.accent = accent
        self.portrait = portrait        # callable(mood, context) -> 44x44 Surface, or None for no portrait
        self.blip = blip

    def face(self, mood, context):
        return self.portrait(mood, context) if self.portrait else None


SPEAKERS = {}


def register_speaker(key, speaker):
    SPEAKERS[key] = speaker
    return speaker


# ------------------------------------------------------------------ portraits
def solid_panel(w, h, border=Col.CYAN, inner=Col.MAGENTA, alpha=246):
    """neon_panel with an opaque backing. The game's own panels let a faint row of the room show through every third
    pixel row, which is lovely for a HUD but makes story text harder to read over a busy room."""
    base = pygame.Surface((w, h), pygame.SRCALPHA)
    base.fill((*Col.PANEL, 255), (1, 1, w - 2, h - 2))
    base.blit(neon_panel(w, h, border, inner, alpha), (0, 0))
    return base


def _backdrop():
    inner = pygame.Surface((40, 40))
    for y in range(40):
        t = y / 39
        inner.fill((int(40 + 24 * t), int(24 + 10 * t), int(84 + 40 * t)), (0, y, 40, 1))
    for i in range(0, 40, 4):                                      # a row of tiny arcade lights
        inner.set_at((i, 1), Col.YELLOW if (i // 4) % 2 else Col.CYAN)
    for x, y in ((3, 9), (35, 12), (5, 20), (36, 24)):
        inner.set_at((x, y), (255, 255, 255))
    return inner


def framed_portrait(sprite, scale=2, accent=Col.CYAN):
    """A 44x44 neon-framed portrait: `sprite` enlarged `scale` times on a night-sky backdrop."""
    inner = _backdrop()
    big = pygame.transform.scale(sprite, (sprite.get_width() * scale, sprite.get_height() * scale))
    inner.blit(soft_shadow(30, 5, 110), (5, 34))
    inner.blit(big, big.get_rect(midbottom=(20, 38)))
    frame = pygame.Surface((44, 44), pygame.SRCALPHA)
    frame.blit(inner, (2, 2))
    pygame.draw.rect(frame, accent, (1, 1, 42, 42), 1)
    pygame.draw.rect(frame, (*Col.MAGENTA, 255), (0, 0, 44, 44), 1)
    for cx, cy in ((1, 1), (41, 1), (1, 42), (41, 42)):
        frame.fill(Col.YELLOW, (cx, cy, 2, 1))
    return frame


MIAO_EYES = {"normal": "open", "happy": "happy", "surprised": "surprised", "gentle": "sleepy"}
_miao_faces = {}


def miao_portrait(mood, context=None):
    eyes = MIAO_EYES.get(mood, "open")
    face = _miao_faces.get(eyes)
    if face is None:
        face = _miao_faces[eyes] = framed_portrait(miao_frame(eyes=eyes, level=3), 2)
    return face


_player_faces = {}


def player_portrait(mood, context=None):
    players = (context or {}).get("players") or ()
    if not players:
        return None
    look = players[0].look
    key = (look, mood == "gentle")
    face = _player_faces.get(key)
    if face is None:
        frames = player_sheet(look)["down"]["idle"]
        sprite = frames[7] if mood == "gentle" else frames[0]       # (the blink frame for a quiet moment)
        face = _player_faces[key] = framed_portrait(sprite, 2)
    return face


MOCHI_EYES = {"normal": "open", "happy": "happy", "surprised": "open", "gentle": "sleepy"}     # (half-lidded: dry and calm)
_mochi_faces = {}


def mochi_portrait(mood, context=None):
    """Mochi the shopkeeper, from her own frames (shopkeeper.mochi_frame, which is only read, never changed)."""
    eyes = MOCHI_EYES.get(mood, "open")
    face = _mochi_faces.get(eyes)
    if face is None:
        face = _mochi_faces[eyes] = framed_portrait(mochi_frame("sit", eyes), 2, (255, 170, 90))
    return face


register_speaker("MIAO MEOW", Speaker("MIAO MEOW", Col.YELLOW, miao_portrait))
register_speaker("MOCHI", Speaker("MOCHI", (255, 170, 90), mochi_portrait, blip="vend_select"))
register_speaker("PLAYER", Speaker("PLAYER", Col.CYAN, player_portrait))


# ------------------------------------------------------------------ the box
class StoryDialogue:
    """A sequence of Lines. `on_done()` is called once, when the last line is confirmed.
    Events are fed by the room's modal flow (`extra_players` lets every local player's confirm key continue)."""
    hides_hud = True                    # the room hides its corner HUD and prompts while this is open

    def __init__(self, lines, context=None, on_done=None, play_sound=None, extra_players=(), top=False, on_line=None):
        self.top = top                  # True: the box sits along the top edge (the room asks when the speakers stand low)
        self.box = BOX_TOP if top else BOX
        self.lines = tuple(lines)
        if not self.lines:
            raise ValueError("a dialogue needs at least one line")
        self.context = context or {}
        self.on_done = on_done
        self.on_line = on_line            # on_line(index, line): called as each line starts (cutscenes time their beats on it)
        self.play_sound = play_sound
        self.extra_players = extra_players
        self.index = 0
        self.shown = 0.0
        self.time = 0.0
        self.closed = False
        self._blipped = 0
        self._wrapped = {}
        if self.on_line is not None:
            self.on_line(0, self.lines[0])

    # ------------------------------------------------------------ state
    @property
    def line(self):
        return self.lines[self.index]

    @property
    def speaker(self):
        return SPEAKERS.get(self.line.speaker) or Speaker(self.line.speaker)

    @property
    def done_typing(self):
        return self.shown >= len(self.line.text)

    def _rows(self):
        rows = self._wrapped.get(self.index)
        if rows is None:
            rows = self._wrapped[self.index] = wrap_text(self.line.text, TEXT_W)[:MAX_LINES]
        return rows

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if self.closed or event.type != pygame.KEYDOWN or event.key not in CONFIRM_KEYS:
            return
        if not self.done_typing:
            self.shown = float(len(self.line.text))                 # first press: finish the line
            return
        self.index += 1
        if self.index >= len(self.lines):
            self.index = len(self.lines) - 1
            self.closed = True
            if self.on_done is not None:
                self.on_done()
            return
        self.shown, self._blipped = 0.0, 0
        if self.on_line is not None:
            self.on_line(self.index, self.line)

    def _sound(self, name):
        if self.play_sound is not None:
            self.play_sound(name)

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        if self.closed or self.done_typing:
            return
        before = int(self.shown)
        self.shown = min(float(len(self.line.text)), self.shown + CPS * dt)
        n = int(self.shown)
        if n // BLIP_EVERY > self._blipped // BLIP_EVERY and n > before and self.line.text[n - 1:n].strip():
            self._sound(self.speaker.blip)
        self._blipped = n

    # ------------------------------------------------------------ draw
    _panel_image = None

    @classmethod
    def _panel(cls):
        if cls._panel_image is None:
            cls._panel_image = solid_panel(BOX.w, BOX.h, Col.CYAN, Col.PURPLE, 246)
        return cls._panel_image

    def draw(self, surf):
        speaker = self.speaker
        box = self.box
        surf.blit(self._panel(), box.topleft)
        face = speaker.face(self.line.mood, self.context)
        portrait_y = box.bottom - 22 if self.top else box.y - 10       # the portrait pops out over the edge facing the room
        tab_y = box.bottom - 5 if self.top else box.y - 7
        if face is not None:
            surf.blit(face, (PORTRAIT[0], portrait_y))
            text_x = TEXT_X
        else:
            text_x = box.x + 14
        tab_x = text_x - 2
        w = get_font().size(speaker.name)[0] + 14
        surf.blit(solid_panel(w, 13, speaker.accent, None, 250), (tab_x, tab_y))
        draw_text(surf, speaker.name, (tab_x + 7, tab_y + 3), speaker.accent, glow=scale_color(Col.MAGENTA, 0.6))
        remaining = int(self.shown)
        for i, row in enumerate(self._rows()):
            part = row[:max(0, remaining)]
            remaining -= len(row) + 1
            if part:
                draw_text(surf, part, (text_x, box.y + 14 + i * 10), Col.TEXT)
        if self.done_typing:
            bob = int(1.5 + 1.5 * math.sin(self.time * 6))
            ax, ay = box.right - 16, box.bottom - 14 + bob
            pygame.draw.polygon(surf, Col.YELLOW, [(ax, ay), (ax + 7, ay), (ax + 3, ay + 4)])
            if int(self.time * 2) % 2 == 0:
                draw_text(surf, "E / ENTER / SPACE", (box.right - 24, box.bottom - 12), Col.TEXT_MUTED, anchor="topright")
        if len(self.lines) > 1:
            draw_text(surf, f"{self.index + 1}/{len(self.lines)}", (box.right - 10, box.y + 4), scale_color(Col.TEXT_MUTED, 0.7),
                      anchor="topright")
