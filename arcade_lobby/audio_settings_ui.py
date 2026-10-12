"""Player-facing AUDIO SETTINGS screen (F4 anywhere in the arcade) and the developer AUDIO DEBUG HUD (F10).

The screen edits the one shared AudioManager, so every change is heard at once and saved through its
existing preference file. It is a pushed scene without a music theme of its own, so the music of whatever is
underneath keeps playing. Keyboard: UP/DOWN pick a row, LEFT/RIGHT change a slider, E/ENTER press a button,
ESC closes. Mouse: click or drag a slider, click a button, wheel over a slider.
"""
import pygame

from display import screen_to_canvas
from font import LINE_H, get_font
from gfx import scale_color, shade
from display_settings_ui import DisplayPage
from scene_base import BaseScene
from settings import BACK_KEYS, CONFIRM_KEYS, VIEW_H, VIEW_W, Col
from ui import draw_text, neon_panel

FRAME = pygame.Rect(6, 6, VIEW_W - 12, VIEW_H - 12)
GOLD, ROSE = Col.YELLOW, (255, 110, 190)
STEP = 0.05
ROW_Y, ROW_H = 62, 28
SLIDER_X, SLIDER_W = 132, 190
ROWS = ("MUSIC", "SFX", "MUTE", "TEST SOUND", "RESTORE DEFAULTS", "BACK")
UP_KEYS, DOWN_KEYS = (pygame.K_UP, pygame.K_w), (pygame.K_DOWN, pygame.K_s)
LEFT_KEYS, RIGHT_KEYS = (pygame.K_LEFT, pygame.K_a), (pygame.K_RIGHT, pygame.K_d)


class AudioSettingsScene(BaseScene):
    own_audio = True            # it plays its own click sounds
    audio_hud_anchor = "bottomleft"
    spectator_corner = "topleft"

    def __init__(self, game):
        super().__init__(game)
        self.audio = game.audio
        self.row = 0
        self.time = 0.0
        self.dragging = None            # 0 / 1: the slider under the mouse
        self.message, self.message_time = "", 0.0
        self.rects = {}                 # row index -> clickable Rect, rebuilt every draw
        self.tab = 0                    # 0 AUDIO, 1 DISPLAY
        self.display_page = DisplayPage(self)

    # ------------------------------------------------------------ model
    def value(self, row):
        return self.audio.bgm_volume if row == 0 else self.audio.sfx_volume

    def set_value(self, row, value, save=True):
        value = round(max(0.0, min(1.0, value)) / 0.01) * 0.01        # whole percents
        self.audio.set_volumes(bgm=value if row == 0 else None, sfx=value if row == 1 else None, save=save)

    def adjust(self, row, direction):
        if row in (0, 1):
            self.set_value(row, self.value(row) + STEP * direction)
            if row == 1:
                self.audio.play("confirm")                                  # hear the new effects level
        elif row == 2 and direction:
            self.toggle_mute()

    def toggle_mute(self):
        self.audio.toggle_mute()
        self.say("MUTED" if self.audio.muted else "SOUND ON")

    def activate(self, row):
        if row in (0, 1):
            return
        if row == 2:
            self.toggle_mute()
        elif row == 3:
            if not self.audio.enabled:
                self.say("NO AUDIO DEVICE", Col.MAGENTA)
            elif self.audio.muted:
                self.say("MUTED - UNMUTE TO HEAR IT", Col.YELLOW)
            else:
                self.audio.play_test_sound()
                self.say("PLAYING TEST SOUND")
        elif row == 4:
            self.audio.restore_defaults()
            self.say("DEFAULTS RESTORED")
            self.audio.play("confirm")
        elif row == 5:
            self.close()

    def say(self, text, color=Col.TEXT_MUTED):
        self.message, self.message_time, self.message_color = text, 2.5, color

    def close(self):
        if self.display_page.confirming:
            self.display_page.revert()                # leaving mid-countdown puts the old display back
        self.audio.play("cancel")
        self.audio.save_prefs()
        self.game.scenes.pop()

    # ------------------------------------------------------------ input
    TAB_NAMES = ("AUDIO", "DISPLAY")

    def tab_rect(self, i):
        return pygame.Rect(236 + i * 76, 14, 70, 14)

    def set_tab(self, tab):
        self.tab = tab
        self.dragging = None
        if tab == 1:
            self.display_page.sync()

    def handle_event(self, event):
        page = self.display_page
        if page.confirming:                           # the KEEP / REVERT box owns every key and click
            page.handle_event(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.set_tab(1 - self.tab)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.mouse_pos(event.pos)
            for i in range(2):
                if self.tab_rect(i).collidepoint(pos):
                    self.set_tab(i)
                    return
        if self.tab == 1:
            page.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            key = event.key
            if key in BACK_KEYS or key == pygame.K_F4:
                self.close()
            elif key in UP_KEYS:
                self.row = (self.row - 1) % len(ROWS)
            elif key in DOWN_KEYS:
                self.row = (self.row + 1) % len(ROWS)
            elif key in LEFT_KEYS:
                self.adjust(self.row, -1)
            elif key in RIGHT_KEYS:
                self.adjust(self.row, 1)
            elif key in CONFIRM_KEYS:
                self.activate(self.row)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._press(self.mouse_pos(event.pos))
        elif event.type == pygame.MOUSEMOTION and self.dragging is not None:
            self._drag(self.mouse_pos(event.pos))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging is not None:
            self.dragging = None
            self.audio.save_prefs()                  # saved once, when the slider is let go
        elif event.type == pygame.MOUSEWHEEL:
            if self.row in (0, 1):
                self.adjust(self.row, 1 if event.y > 0 else -1)

    def mouse_pos(self, pos):
        return screen_to_canvas(pos, self.game.screen.get_size())

    def slider_rect(self, row):
        return pygame.Rect(SLIDER_X, ROW_Y + row * ROW_H + 9, SLIDER_W, 8)

    def row_rect(self, row):
        return pygame.Rect(16, ROW_Y + row * ROW_H, FRAME.w - 20, ROW_H - 4)

    def _press(self, pos):
        for row in range(len(ROWS)):
            if row in (0, 1) and self.slider_rect(row).inflate(8, 14).collidepoint(pos):
                self.row, self.dragging = row, row
                self._drag(pos)
                return
            if self.row_rect(row).collidepoint(pos):
                self.row = row
                self.activate(row)
                return

    def _drag(self, pos):
        rect = self.slider_rect(self.dragging)
        self.set_value(self.dragging, (pos[0] - rect.x) / rect.w, save=False)

    # ------------------------------------------------------------ frame
    def update(self, dt):
        self.time += dt
        self.message_time = max(0.0, self.message_time - dt)
        self.display_page.update(dt)

    def draw(self, surf):
        a = self.audio
        surf.fill((12, 7, 30))
        for y in range(0, VIEW_H, 12):
            pygame.draw.line(surf, (24, 15, 46), (0, y), (VIEW_W, y))
        surf.blit(neon_panel(FRAME.w, FRAME.h, GOLD, ROSE, 235), FRAME.topleft)
        draw_text(surf, "DISPLAY SETTINGS" if self.tab else "AUDIO SETTINGS", (16, 12), shade(GOLD, 0.4), 2,
                  glow=scale_color(ROSE, 0.8))
        for i, name in enumerate(self.TAB_NAMES):
            rect = self.tab_rect(i)
            surf.fill(scale_color(GOLD, 0.35) if i == self.tab else (26, 18, 52), rect)
            if i == self.tab:
                surf.fill(GOLD, (rect.x, rect.bottom - 1, rect.w, 1))
            draw_text(surf, name, rect.center, Col.TEXT if i == self.tab else Col.TEXT_MUTED, anchor="center")
        if self.tab == 1:
            self._draw_footer(surf, ("UP/DOWN SELECT   LEFT/RIGHT CHANGE   E OK   ESC BACK",
                                     "TAB: AUDIO / DISPLAY   ALT+ENTER OR F11: FULLSCREEN"))
            self.display_page.draw(surf)
            return
        if not a.enabled:
            draw_text(surf, "NO AUDIO DEVICE - RUN audio_diagnostics.py", (16, 32), Col.MAGENTA)
        else:
            now = a.track_title or "-"
            draw_text(surf, f"NOW PLAYING: {now}" + ("   (MUTED)" if a.muted else ""), (16, 32),
                      Col.MAGENTA if a.muted else Col.CYAN)
        for row, name in enumerate(ROWS):
            rect = self.row_rect(row)
            selected = row == self.row
            surf.fill(scale_color(GOLD, 0.28) if selected else (18, 12, 40), rect)
            if selected:
                pygame.draw.rect(surf, scale_color(GOLD, 0.65 + 0.35 * abs(((self.time * 3) % 2) - 1)), rect, 1)
            if row in (0, 1):
                self._draw_slider(surf, row, name, selected)
            elif row == 2:
                draw_text(surf, name, (rect.x + 8, rect.centery - 3), Col.TEXT if selected else Col.TEXT_MUTED)
                on = a.muted
                box = pygame.Rect(SLIDER_X, rect.centery - 5, 44, 10)
                surf.fill((150, 40, 80) if on else (34, 90, 60), box)
                draw_text(surf, "MUTED" if on else "SOUND ON", box.center, Col.TEXT, anchor="center")
            else:
                draw_text(surf, name, rect.center, Col.TEXT if selected else Col.TEXT_MUTED, anchor="center")
        self._draw_footer(surf, ("UP/DOWN SELECT   LEFT/RIGHT CHANGE   E OK   ESC BACK   TAB DISPLAY",
                                 "ANYWHERE: F6/F7 MUSIC   F8/F9 SFX   M MUTE   F10 DEBUG"))

    def _draw_footer(self, surf, hints):
        box = pygame.Rect(14, 244, FRAME.w - 16, 12)
        surf.fill((16, 10, 36), box)
        pygame.draw.rect(surf, scale_color(GOLD, 0.4), box, 1)
        if self.message_time > 0:
            draw_text(surf, self.message, box.center, self.message_color, anchor="center")
        for i, line in enumerate(hints):
            draw_text(surf, line, (VIEW_W // 2, 260 + i * (LINE_H + 2)), scale_color(Col.TEXT_MUTED, 0.9), anchor="midtop")

    def _draw_slider(self, surf, row, name, selected):
        rect, track = self.row_rect(row), self.slider_rect(row)
        value = self.value(row)
        draw_text(surf, name, (rect.x + 8, rect.centery - 3), Col.TEXT if selected else Col.TEXT_MUTED)
        surf.fill((30, 22, 60), track)
        fill = track.copy()
        fill.w = round(track.w * value)
        surf.fill(Col.CYAN if not self.audio.muted else (90, 80, 120), fill)
        pygame.draw.rect(surf, scale_color(GOLD, 0.5), track, 1)
        knob = pygame.Rect(0, 0, 5, 12)
        knob.center = (track.x + fill.w, track.centery)
        surf.fill(GOLD, knob)
        draw_text(surf, f"{round(value * 100)}", (track.right + 10, rect.centery - 3), GOLD)


# ---------------------------------------------------------------- developer HUD
def debug_lines(game):
    """The text of the AUDIO DEBUG HUD: a list of short lines (kept separate from drawing so it can be tested)."""
    a = game.audio
    scene = game.scenes.current
    machine = getattr(scene, "machine", None)
    name = (type(scene).__name__.replace("Scene", "") + (f" [{machine.id}]" if machine is not None else "")) if scene else "-"
    st = a.status()
    mixer = st["mixer"]
    lines = [f"SCENE  {name}",
             f"MUSIC  {a.theme or '-'}  {('PLAYING' + (' (MUTED)' if a.muted else '')) if st['music_playing'] else 'SILENT'}  {a.fade_state}",
             f"VOL    MUSIC {round(a.bgm_volume * 100)}  SFX {round(a.sfx_volume * 100)}  "
             f"{'MUTED' if a.muted else 'ON'}",
             f"FADE   A {a.mix[0]:.2f}>{a.mix_to[0]:.0f}  B {a.mix[1]:.2f}>{a.mix_to[1]:.0f}  DUCK {round(a.duck * 100)}"
             + ("  STUCK AT 0!" if st["fade_stuck"] else "")]
    from game import Game
    want = Game.music_for(game.scenes.stack)
    if want and a.theme and want != a.theme:
        lines.append(f"TRACK  WANT {want}  GOT {a.theme}  WRONG!")
    if mixer:
        lines.append(f"MIXER  {st['driver'] or '?'} {mixer[0]}HZ {'ST' if mixer[2] == 2 else 'MONO'}")
    else:
        lines.append(f"MIXER  UNAVAILABLE  {(st['init_error'] or '')[:34]}")
    if mixer:
        if st["device_state"] == "STALLED":
            lines.append(f"DEVICE STALLED!  REOPENS {st['reopens']}")
        else:
            probe = f"{st['probe_ms']}MS" if st["probe_ms"] is not None else "..."
            lines.append(f"DEVICE {st['device_state']} {probe}  STALLS {st['device_stalls']} REOPEN {st['reopens']}")
    if st["missing_music"] or st["missing_sfx"]:
        lines.append(f"FILES  MISSING {len(st['missing_music'])} MUSIC {len(st['missing_sfx'])} SFX")
    busy = a.sfx_busy()
    lines.append(f"SFX    {len(busy)} PLAYING" + (f"  CH {','.join(map(str, busy[:8]))}" if busy else ""))
    owners = a.sfx_owners()
    lines.append("OWNER  " + (" ".join(f"{ch}={who}" + (f":{fx}" if fx else "") for ch, who, fx in owners[:3]) if owners else "-")
                 + (f"  STUCK {st['stuck_sfx']}" if st["stuck_sfx"] else ""))
    others = [c for c in busy if c not in {o[0] for o in owners}]
    if others:
        lines.append(f"OTHER  CH {','.join(map(str, others[:8]))} (VOICES/RACER)")
    racer = getattr(scene, "racer", None)
    if racer is not None and hasattr(racer, "audio"):
        ra = racer.audio
        if mixer and getattr(ra, "enabled", False):
            ch = [(pygame.mixer.Channel(i).get_busy(), pygame.mixer.Channel(i).get_volume()) for i in (0, 1)]
            racing = getattr(getattr(racer, "state", None), "name", "") in ("PLAYING", "COUNTDOWN") and not racer.paused
            lines.append("ENGINE " + ("RUNNING " if any(b for b, _ in ch) else ("STOPPED! " if racing else "OFF ")) +
                         " ".join(f"{v:.2f}" for _, v in ch) + f"  BOOST {ra.engine_boost:.1f}")
        else:
            lines.append("ENGINE UNAVAILABLE")
    if st["last_error"] or st["recoveries"]:
        lines.append(f"ERR    {st['recoveries']} RESTARTS  {(st['last_error'] or '')[:30]}")
    return lines


def draw_debug_hud(game, surf):
    """Small translucent panel in the top-left corner (clear of the room's bottom HUD, the top-right badge and the
    top-centre volume readout), drawn over the finished frame. A scene can move it with `audio_hud_anchor`:
    the settings screen uses the bottom-left, Retro Racer the middle of the left edge (its stats fill the corner)."""
    font = get_font()
    px = max(1, surf.get_height() // VIEW_H)
    lines = ["AUDIO DEBUG  (F10)"] + debug_lines(game)
    width = max(font.size(line)[0] for line in lines) + 6
    height = len(lines) * (LINE_H + 1) + 4
    panel = pygame.Surface((width * px, height * px), pygame.SRCALPHA)
    panel.fill((8, 4, 20, 190))
    y = 2
    for i, line in enumerate(lines):
        panel.blit(font.render(line, Col.YELLOW if i == 0 else Col.TEXT, px), (3 * px, y * px))
        y += LINE_H + 1
    anchor = getattr(game.scenes.current, "audio_hud_anchor", "topleft")      # a scene with a busy corner picks another
    if anchor == "bottomleft":
        pos = (2 * px, surf.get_height() - panel.get_height() - 2 * px)
    elif anchor == "midleft":
        pos = (2 * px, int(surf.get_height() * 0.36))
    else:
        pos = (2 * px, 2 * px)
    surf.blit(panel, pos)
