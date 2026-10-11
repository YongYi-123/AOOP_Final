"""Original synthesized arcade music and effects with separate volume controls."""
from array import array
import json
import math
import os
import pygame


ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
# theme -> music file (assets/music/<file>.wav, composed by audio_synth.py). The hub's own
# theme keeps its old name "lobby". Minigame themes below are short synthesized loops.
MUSIC_FILES = {"lobby": "arcade_floor", "prize_plaza": "prize_plaza", "lucky_corner": "lucky_corner",
               "home": "home"}
SFX_FILES = ("footstep", "confirm", "cancel", "machine", "token", "ticket", "purchase", "card", "equip",
             "pet", "emote", "sit", "meow")
# some effects are meant to be barely there
SFX_GAIN = {"footstep": 0.3, "card": 0.7, "confirm": 0.8, "cancel": 0.8, "sit": 0.7, "emote": 0.8, "meow": 0.6}
MIN_GAP = {"footstep": 0.16, "meow": 1.2}            # seconds between two plays of the same effect (default .06)
DEFAULT_BGM, DEFAULT_SFX = .22, .7
FADE_MS = 700


def _unit(value, default):
    """A saved volume if it is a number in 0..1, else the default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        return default
    return float(value)


class AudioManager:
    """Music (one looping theme at a time, crossfaded) and effects with independent
    volumes and a mute. Every call is safe without an audio device: `enabled` is
    False and everything quietly does nothing - the game never waits on sound.

    Music: set_track()/switch() ignores a request for the theme that is already
    playing, so opening a menu never restarts the song. Preferences (volumes and
    mute) are saved to `prefs_path` when one is given."""
    THEMES = {'lobby': (262, 330, 392, 330, 294, 349, 440, 349),
              'retro_racer': (196, 247, 294, 392, 196, 294, 247, 392),
              'pixel_volleyball': (330, 392, 440, 523, 440, 392, 330, 294),
              'cat_minesweeper': (262, 392, 330, 440, 349, 330, 294, 392),
              'galaxy_defender': (220, 262, 330, 262, 247, 294, 370, 294)}
    EFFECTS = {'machine': (440, 660), 'confirm': (660, 880), 'cancel': (440, 220),
               'hit': (560,), 'spike': (1480, 880, 440), 'bounce': (240,), 'point': (660, 880),
               'win': (523, 659, 784), 'loss': (440, 330, 220),
               'laser': (990, 760), 'boom': (180, 120), 'powerup': (660, 990), 'reveal': (700,), 'flag': (420, 560), 'skid': (480, 320, 160)}

    def __init__(self, bgm_volume=DEFAULT_BGM, sfx_volume=DEFAULT_SFX, prefs_path=None, asset_dir=ASSET_DIR):
        self.bgm_volume, self.sfx_volume, self.muted = bgm_volume, sfx_volume, False
        self.prefs_path, self.asset_dir = prefs_path, asset_dir
        self.theme = None
        self.sounds, self.music = {}, {}
        self.channels = []
        self.enabled, self.active, self.time = False, 0, 0.0
        self.last_effect = {}
        self.music_starts = 0           # how many times a track was (re)started: lets tests see "no restart"
        self.load_prefs()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2)
            self.rate, sample_format, self.stereo = pygame.mixer.get_init()
            if sample_format != -16:
                return
            pygame.mixer.set_num_channels(max(16, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(4)  # 0/1 engine, 2/3 music crossfade
            self.channels = [pygame.mixer.Channel(2), pygame.mixer.Channel(3)]
            self.enabled = True
        except (pygame.error, TypeError, ValueError):
            pass

    # ------------------------------------------------------------ preferences
    def load_prefs(self):
        """Read saved volumes / mute; a missing or damaged file keeps the defaults."""
        if not self.prefs_path:
            return
        try:
            with open(self.prefs_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            self.bgm_volume = _unit(data.get("music"), self.bgm_volume)
            self.sfx_volume = _unit(data.get("sfx"), self.sfx_volume)
            self.muted = data.get("muted") is True

    def save_prefs(self):
        if not self.prefs_path:
            return False
        tmp = self.prefs_path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.prefs_path) or ".", exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"music": round(self.bgm_volume, 3), "sfx": round(self.sfx_volume, 3),
                           "muted": self.muted}, f)
            os.replace(tmp, self.prefs_path)
        except OSError:
            return False
        return True

    # ------------------------------------------------------------ sound building
    def _sound(self, notes, beat, music=False):
        samples = array('h')
        length = int(self.rate * beat)
        for note in notes:
            for i in range(length):
                phase = i / self.rate
                envelope = min(1, i / max(1, self.rate * .01)) * (1 - i / length)
                value = math.sin(2 * math.pi * note * phase)
                if music:
                    value += .25 * math.sin(2 * math.pi * note / 2 * phase)
                samples.extend([int(value * envelope * (2600 if music else 6000))] * self.stereo)
        return pygame.mixer.Sound(buffer=samples)

    def _load(self, folder, name):
        """A Sound from assets/<folder>/<name>.wav, or None if the file is missing / unreadable."""
        path = os.path.join(self.asset_dir, folder, f"{name}.wav")
        try:
            return pygame.mixer.Sound(path)
        except (pygame.error, FileNotFoundError, OSError):
            return None

    def _music_sound(self, theme):
        sound = self._load("music", MUSIC_FILES[theme]) if theme in MUSIC_FILES else None
        return sound or self._sound(self.THEMES.get(theme, self.THEMES['lobby']), .24, True)

    def _effect_sound(self, name):
        sound = self._load("sfx", name) if name in SFX_FILES else None
        if sound is None and name in self.EFFECTS:
            sound = self._sound(self.EFFECTS[name], .07)
        return sound

    # ------------------------------------------------------------ volumes / mute
    def _music_level(self):
        return 0.0 if self.muted else self.bgm_volume

    def _apply_volumes(self):
        if not self.enabled:
            return
        try:
            for channel in self.channels:
                channel.set_volume(self._music_level())
            for name, sound in self.sounds.items():
                sound.set_volume(self.sfx_volume * SFX_GAIN.get(name, 1.0))
        except pygame.error:
            self.enabled = False

    def set_volumes(self, bgm=None, sfx=None):
        if bgm is not None:
            self.bgm_volume = max(0, min(1, bgm))
        if sfx is not None:
            self.sfx_volume = max(0, min(1, sfx))
        self._apply_volumes()
        self.save_prefs()

    def set_muted(self, muted):
        self.muted = bool(muted)
        self._apply_volumes()
        self.save_prefs()

    def toggle_mute(self):
        self.set_muted(not self.muted)
        return self.muted

    @property
    def effective_sfx(self):
        """The effect volume games should use right now (0 when muted)."""
        return 0.0 if self.muted else self.sfx_volume

    # ------------------------------------------------------------ music
    def switch(self, theme):
        """Crossfade to `theme`. The same theme is left alone (no restart); None keeps
        whatever is playing (menus and dialogs have no music of their own)."""
        if theme is None:
            return
        theme = theme if theme in self.THEMES or theme in MUSIC_FILES else 'lobby'
        if theme == self.theme:
            return
        self.theme = theme
        if not self.enabled:
            return
        try:
            if theme not in self.music:
                self.music[theme] = self._music_sound(theme)
            self.channels[self.active].fadeout(FADE_MS)
            self.active = 1 - self.active
            channel = self.channels[self.active]
            channel.set_volume(self._music_level())
            channel.play(self.music[theme], loops=-1, fade_ms=FADE_MS)
            self.music_starts += 1
        except (pygame.error, MemoryError):
            self.enabled = False

    set_track = switch

    # ------------------------------------------------------------ effects
    def play(self, name):
        if not self.enabled or self.muted or (name not in self.EFFECTS and name not in SFX_FILES):
            return
        if self.time - self.last_effect.get(name, -100) < MIN_GAP.get(name, .06):
            return
        try:
            if name not in self.sounds:
                sound = self._effect_sound(name)
                if sound is None:
                    return
                self.sounds[name] = sound
            self.sounds[name].set_volume(self.sfx_volume * SFX_GAIN.get(name, 1.0))
            self.sounds[name].play()
            self.last_effect[name] = self.time
        except pygame.error:
            self.enabled = False

    def update(self, dt):
        self.time += max(0, dt)

    def stop(self):
        if self.enabled:
            try:
                for channel in self.channels:
                    channel.stop()
                for sound in self.sounds.values():
                    sound.stop()
            except pygame.error:
                pass


class GameSoundBus:
    """Route game events through shared SFX mixing without owning lobby music."""
    def __init__(self, manager):
        self.manager = manager

    def play(self, events, now=None):
        for name in ([events] if isinstance(events, str) else events):
            self.manager.play(name)

    def stop(self):
        pass
